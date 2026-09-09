from __future__ import annotations

import json
from datetime import UTC, datetime

from dataops_ai.agents.investigation_agent import InvestigationAgent
from dataops_ai.agents.quality_agent import DataQualityAgent
from dataops_ai.agents.resolution_agent import ResolutionAgent
from dataops_ai.config import Settings
from dataops_ai.contracts import find_default_contract
from dataops_ai.models import CollaborationTurn, ConsensusReport, PipelineRunResult
from dataops_ai.pipelines.extract import extract_bcb_series
from dataops_ai.pipelines.load import load_timeseries
from dataops_ai.pipelines.transform import transform_bcb_payload
from dataops_ai.scenarios import apply_scenario
from dataops_ai.tools.incident_tools import (
    append_incident_history_record,
    build_incident_history_record,
    create_incident_report,
    generate_audit_hash,
    save_incident_history_record,
)
from dataops_ai.tools.log_tools import get_last_pipeline_run, write_pipeline_log
from dataops_ai.tools.quality_tools import run_quality_checks
from dataops_ai.tools.storage_tools import upload_to_gcs_if_configured


class AgentOrchestrator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self, scenario: str, scenario_label: str) -> PipelineRunResult:
        run_id = _new_run_id()
        write_pipeline_log(self.settings.logs_dir, "pipeline_started", {"run_id": run_id, "scenario": scenario})
        raw_rows = self._extract(scenario, run_id)
        transformed = transform_bcb_payload(raw_rows, self.settings.bcb_series_code)
        staged = apply_scenario(transformed, scenario)

        self.settings.processed_dir.mkdir(parents=True, exist_ok=True)
        processed_path = self.settings.processed_dir / "bcb_timeseries.csv"
        staged.to_csv(processed_path, index=False)

        contract = find_default_contract(self.settings.project_root)
        quality_report = run_quality_checks(staged, contract=contract)
        failed_checks = quality_report.failed_checks

        # Circuit Breaker: isolar dados defeituosos na Quarentena (DLQ)
        if failed_checks:
            quarantined = True
            self.settings.dlq_dir.mkdir(parents=True, exist_ok=True)
            quarantine_path = self.settings.dlq_dir / f"quarantine_{run_id}.csv"
            staged.to_csv(quarantine_path, index=False)

            quarantine_meta_path = self.settings.dlq_dir / f"quarantine_{run_id}_meta.json"
            quarantine_meta_path.write_text(
                json.dumps(
                    {
                        "run_id": run_id,
                        "scenario": scenario,
                        "quarantined_at": datetime.now(UTC).isoformat(),
                        "failed_checks": [issue.model_dump(mode="json") for issue in failed_checks],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            # envio para o bucket de quarentena se configurado
            upload_to_gcs_if_configured(quarantine_path, f"quarantine_{run_id}.csv", self.settings.gcs_quarantine_bucket)
            upload_to_gcs_if_configured(quarantine_meta_path, f"quarantine_{run_id}_meta.json", self.settings.gcs_quarantine_bucket)

            rows_loaded = 0
            write_pipeline_log(
                self.settings.logs_dir,
                "circuit_breaker_tripped",
                {
                    "run_id": run_id,
                    "scenario": scenario,
                    "quarantine_path": str(quarantine_path),
                    "failed_checks": len(failed_checks),
                },
            )
        else:
            quarantined = False
            quarantine_path = None
            rows_loaded = load_timeseries(staged, self.settings.database_url)
            write_pipeline_log(
                self.settings.logs_dir,
                "clean_data_loaded",
                {"run_id": run_id, "scenario": scenario, "rows_loaded": rows_loaded},
            )

        context = {
            "scenario": scenario,
            "run_id": run_id,
            "rows_loaded": rows_loaded,
            "quarantined": quarantined,
            "quarantine_path": str(quarantine_path) if quarantine_path else None,
            "last_pipeline_run": get_last_pipeline_run(self.settings.logs_dir),
        }

        # Turno 1: Diagnóstico inicial (DataQualityAgent)
        quality_agent = DataQualityAgent(
            self.settings.gemini_api_key,
            self.settings.gemini_model,
            self.settings.gemini_store_interactions,
        )
        diagnosis = quality_agent.diagnose(quality_report, context)
        conversation: list[CollaborationTurn] = [
            quality_agent.build_turn_message(diagnosis)
        ]

        write_pipeline_log(
            self.settings.logs_dir,
            "pipeline_finished",
            {
                "run_id": run_id,
                "scenario": scenario,
                "rows_loaded": rows_loaded,
                "quarantined": quarantined,
                "failed_checks": len(failed_checks),
                "severity": diagnosis.severity,
            },
        )

        # Turno 2: Investigação técnica de logs e banco (InvestigationAgent)
        investigation_agent = InvestigationAgent(self.settings.database_url, self.settings.logs_dir)
        investigation = investigation_agent.investigate(
            quality_report,
            diagnosis,
            scenario,
            run_id,
        )
        conversation.append(investigation_agent.build_turn_message(investigation))

        # Turno 3: Avaliação de alinhamento e calibração supervisionada (Debate condicional)
        needs_refinement, alignment_reason = investigation_agent.evaluate_alignment(
            quality_report, diagnosis, investigation, context
        )

        if needs_refinement:
            diagnosis, calib_turn = quality_agent.calibrate(
                quality_report, diagnosis, investigation, context
            )
            conversation.append(calib_turn)
            status = "consenso_refinado"
            iterations = 2
            supervisor_decision = f"Supervisor recomendou calibração com base nas evidências apuradas: {alignment_reason}"
        else:
            status = "consenso_direto"
            iterations = 1
            supervisor_decision = "Supervisor aprovou consonância direta entre diagnóstico inicial e evidências apuradas."

        # Turno 4: Resolução consensual (ResolutionAgent)
        resolution_agent = ResolutionAgent()
        resolution, res_turn = resolution_agent.build_plan_with_consensus(
            quality_report, diagnosis, investigation, context
        )
        conversation.append(res_turn)

        collaboration = ConsensusReport(
            status=status,
            iterations=iterations,
            supervisor_decision=supervisor_decision,
            conversation=conversation,
        )

        audit_payload = f"{run_id}:{scenario}:{quality_report.total_rows}:{len(failed_checks)}:{diagnosis.summary}:{quarantined}:{collaboration.status}"
        audit_hash = generate_audit_hash(run_id, audit_payload)

        self.settings.curated_dir.mkdir(parents=True, exist_ok=True)
        diagnosis_report_path = self.settings.curated_dir / "quality_diagnosis.json"
        run_diagnosis_path = self.settings.curated_dir / f"quality_diagnosis_{run_id}.json"
        incident_report_path = create_incident_report(
            self.settings.curated_dir,
            run_id,
            scenario_label,
            quality_report,
            diagnosis,
            quality_agent.llm_metadata.model_dump(mode="json"),
            investigation,
            resolution,
            quarantined=quarantined,
            audit_hash=audit_hash,
            collaboration=collaboration,
        )
        diagnosis_payload = json.dumps(
            {
                "run_id": run_id,
                "quarantined": quarantined,
                "quarantine_path": str(quarantine_path) if quarantine_path else None,
                "audit_hash": audit_hash,
                "quality_report": quality_report.model_dump(mode="json"),
                "diagnosis": diagnosis.model_dump(mode="json"),
                "diagnosis_engine": quality_agent.engine_used,
                "llm_metadata": quality_agent.llm_metadata.model_dump(mode="json"),
                "investigation": investigation.model_dump(mode="json"),
                "resolution": resolution.model_dump(mode="json"),
                "collaboration": collaboration.model_dump(mode="json"),
            },
            ensure_ascii=False,
            indent=2,
        )
        diagnosis_report_path.write_text(diagnosis_payload, encoding="utf-8")
        run_diagnosis_path.write_text(diagnosis_payload, encoding="utf-8")

        # salvo copia no bucket curated caso a nuvem esteja habilitada
        upload_to_gcs_if_configured(run_diagnosis_path, f"quality_diagnosis_{run_id}.json", self.settings.gcs_curated_bucket)
        upload_to_gcs_if_configured(incident_report_path, f"incident_report_{run_id}.md", self.settings.gcs_curated_bucket)

        history_record = build_incident_history_record(
            run_id,
            scenario_label,
            quality_report,
            diagnosis,
            quality_agent.engine_used,
            quality_agent.llm_metadata.model_dump(mode="json"),
            resolution,
            str(diagnosis_report_path),
            str(incident_report_path),
            quarantined=quarantined,
            audit_hash=audit_hash,
            collaboration=collaboration,
        )
        history_path = append_incident_history_record(self.settings.curated_dir, history_record)
        save_incident_history_record(self.settings.database_url, history_record)

        return PipelineRunResult(
            run_id=run_id,
            scenario=scenario,
            rows_loaded=rows_loaded,
            quarantined=quarantined,
            quarantine_path=str(quarantine_path) if quarantine_path else None,
            audit_hash=audit_hash,
            diagnosis_engine=quality_agent.engine_used,
            llm_metadata=quality_agent.llm_metadata,
            quality_report=quality_report,
            diagnosis=diagnosis,
            investigation=investigation,
            resolution=resolution,
            collaboration=collaboration,
            diagnosis_report_path=str(diagnosis_report_path),
            incident_report_path=str(incident_report_path),
            history_path=str(history_path),
        )

    def _extract(self, scenario: str, run_id: str) -> list[dict]:
        force_api_timeout = scenario == "scenario_03_api_timeout"
        raw_rows = extract_bcb_series(
            series_code=self.settings.bcb_series_code,
            start_date=self.settings.bcb_start_date,
            end_date=self.settings.bcb_end_date,
            output_dir=self.settings.raw_dir,
            force_timeout=force_api_timeout,
        )
        extraction_source = raw_rows[0].get("source", "unknown") if raw_rows else "empty"
        if extraction_source != "bcb_api":
            write_pipeline_log(
                self.settings.logs_dir,
                "api_fallback_used",
                {
                    "run_id": run_id,
                    "scenario": scenario,
                    "source": extraction_source,
                    "reason": "timeout simulado" if force_api_timeout else "falha na coleta",
                    "rows_returned": len(raw_rows),
                },
            )
        return raw_rows


def _new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
