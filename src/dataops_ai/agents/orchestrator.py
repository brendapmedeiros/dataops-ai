from __future__ import annotations

import json

from dataops_ai.agents.investigation_agent import InvestigationAgent
from dataops_ai.agents.quality_agent import DataQualityAgent
from dataops_ai.agents.resolution_agent import ResolutionAgent
from dataops_ai.config import Settings
from dataops_ai.models import PipelineRunResult
from dataops_ai.pipelines.extract import extract_bcb_series
from dataops_ai.pipelines.load import load_timeseries
from dataops_ai.pipelines.transform import transform_bcb_payload
from dataops_ai.scenarios import apply_scenario
from dataops_ai.tools.incident_tools import create_incident_report
from dataops_ai.tools.log_tools import get_last_pipeline_run, write_pipeline_log
from dataops_ai.tools.quality_tools import run_quality_checks


class AgentOrchestrator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self, scenario: str, scenario_label: str) -> PipelineRunResult:
        write_pipeline_log(self.settings.logs_dir, "pipeline_started", {"scenario": scenario})
        raw_rows = self._extract(scenario)
        transformed = transform_bcb_payload(raw_rows, self.settings.bcb_series_code)
        staged = apply_scenario(transformed, scenario)

        self.settings.processed_dir.mkdir(parents=True, exist_ok=True)
        processed_path = self.settings.processed_dir / "bcb_timeseries.csv"
        staged.to_csv(processed_path, index=False)

        rows_loaded = load_timeseries(staged, self.settings.database_url)
        quality_report = run_quality_checks(staged)
        quality_agent = DataQualityAgent(self.settings.gemini_api_key, self.settings.gemini_model)
        diagnosis = quality_agent.diagnose(
            quality_report,
            {
                "scenario": scenario,
                "rows_loaded": rows_loaded,
                "last_pipeline_run": get_last_pipeline_run(self.settings.logs_dir),
            },
        )

        write_pipeline_log(
            self.settings.logs_dir,
            "pipeline_finished",
            {
                "scenario": scenario,
                "rows_loaded": rows_loaded,
                "failed_checks": len(quality_report.failed_checks),
                "severity": diagnosis.severity,
            },
        )

        investigation = InvestigationAgent(self.settings.database_url, self.settings.logs_dir).investigate(
            quality_report,
            diagnosis,
            scenario,
        )
        resolution = ResolutionAgent().build_plan(quality_report, diagnosis, investigation)

        self.settings.curated_dir.mkdir(parents=True, exist_ok=True)
        diagnosis_report_path = self.settings.curated_dir / "quality_diagnosis.json"
        incident_report_path = create_incident_report(
            self.settings.curated_dir,
            scenario_label,
            quality_report,
            diagnosis,
            investigation,
            resolution,
        )
        diagnosis_report_path.write_text(
            json.dumps(
                {
                    "quality_report": quality_report.model_dump(mode="json"),
                    "diagnosis": diagnosis.model_dump(mode="json"),
                    "diagnosis_engine": quality_agent.engine_used,
                    "investigation": investigation.model_dump(mode="json"),
                    "resolution": resolution.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return PipelineRunResult(
            scenario=scenario,
            rows_loaded=rows_loaded,
            diagnosis_engine=quality_agent.engine_used,
            quality_report=quality_report,
            diagnosis=diagnosis,
            investigation=investigation,
            resolution=resolution,
            diagnosis_report_path=str(diagnosis_report_path),
            incident_report_path=str(incident_report_path),
        )

    def _extract(self, scenario: str) -> list[dict]:
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
                    "scenario": scenario,
                    "source": extraction_source,
                    "reason": "timeout simulado" if force_api_timeout else "falha na coleta",
                    "rows_returned": len(raw_rows),
                },
            )
        return raw_rows
