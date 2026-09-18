from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from dataops_ai.models import (
    AgentDiagnosis,
    ConsensusReport,
    InvestigationReport,
    QualityReport,
    ResolutionPlan,
)
from dataops_ai.tools.database_tools import DatabaseClient


import hashlib


def generate_audit_hash(run_id: str, content: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(run_id.encode("utf-8"))
    hasher.update(content.encode("utf-8"))
    return hasher.hexdigest()


def create_incident_report(
    output_dir: Path,
    run_id: str,
    scenario: str,
    quality_report: QualityReport,
    diagnosis: AgentDiagnosis,
    llm_metadata: dict,
    investigation: InvestigationReport,
    resolution: ResolutionPlan,
    quarantined: bool = False,
    audit_hash: str | None = None,
    collaboration: ConsensusReport | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "incident_report.md"
    content = _format_report(
        run_id,
        scenario,
        quality_report,
        diagnosis,
        llm_metadata,
        investigation,
        resolution,
        quarantined=quarantined,
        audit_hash=audit_hash,
        collaboration=collaboration,
    )
    report_path.write_text(content, encoding="utf-8")
    return report_path


def append_incident_history(
    output_dir: Path,
    run_id: str,
    scenario: str,
    quality_report: QualityReport,
    diagnosis: AgentDiagnosis,
    diagnosis_engine: str,
    llm_metadata: dict,
    resolution: ResolutionPlan,
    diagnosis_report_path: str,
    incident_report_path: str,
    quarantined: bool = False,
    audit_hash: str = "",
) -> Path:
    record = build_incident_history_record(
        run_id,
        scenario,
        quality_report,
        diagnosis,
        diagnosis_engine,
        llm_metadata,
        resolution,
        diagnosis_report_path,
        incident_report_path,
        quarantined=quarantined,
        audit_hash=audit_hash,
    )
    return append_incident_history_record(output_dir, record)


def append_incident_history_record(output_dir: Path, record: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    history_path = output_dir / "incident_history.jsonl"
    with history_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return history_path


def build_incident_history_record(
    run_id: str,
    scenario: str,
    quality_report: QualityReport,
    diagnosis: AgentDiagnosis,
    diagnosis_engine: str,
    llm_metadata: dict,
    resolution: ResolutionPlan,
    diagnosis_report_path: str,
    incident_report_path: str,
    quarantined: bool = False,
    audit_hash: str = "",
    collaboration: ConsensusReport | None = None,
) -> dict:
    return {
        "run_id": run_id,
        "recorded_at": datetime.now(UTC).isoformat(),
        "scenario": scenario,
        "dataset": quality_report.dataset_name,
        "rows_checked": quality_report.total_rows,
        "failed_checks": len(quality_report.failed_checks),
        "severity": diagnosis.severity,
        "diagnosis_engine": diagnosis_engine,
        "quarantined": quarantined,
        "audit_hash": audit_hash,
        "collaboration_status": collaboration.status if collaboration else "consenso_direto",
        "collaboration_summary": collaboration.supervisor_decision if collaboration else "",
        "llm_provider": llm_metadata.get("provider"),
        "llm_model": llm_metadata.get("model"),
        "llm_api": llm_metadata.get("api"),
        "llm_interaction_id": llm_metadata.get("interaction_id"),
        "llm_previous_interaction_id": llm_metadata.get("previous_interaction_id"),
        "llm_response_format": llm_metadata.get("response_format"),
        "llm_prompt_version": llm_metadata.get("prompt_version"),
        "llm_latency_ms": llm_metadata.get("latency_ms"),
        "llm_tool_names": ", ".join(llm_metadata.get("tool_names") or []),
        "llm_tool_calls": ", ".join(llm_metadata.get("tool_calls") or []),
        "llm_fallback_reason": llm_metadata.get("fallback_reason"),
        "requires_manual_review": resolution.requires_manual_review,
        "summary": resolution.summary,
        "diagnosis_report_path": diagnosis_report_path,
        "incident_report_path": incident_report_path,
    }


def save_incident_history_record(
    database_url: str,
    record: dict,
    table_name: str = "incident_history",
) -> None:
    database = DatabaseClient(database_url)
    database.ensure_record_columns(record, table_name)
    database.append_record(record, table_name)


def read_incident_history(output_dir: Path, limit: int = 10) -> list[dict]:
    history_path = output_dir / "incident_history.jsonl"
    if not history_path.exists():
        return []

    lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in reversed(lines[-_normalize_limit(limit):])]


def read_incident_history_from_database(
    database_url: str,
    limit: int = 10,
    table_name: str = "incident_history",
) -> list[dict]:
    database = DatabaseClient(database_url)
    if not database.table_exists(table_name):
        return []

    safe_limit = _normalize_limit(limit)
    columns = [
        "run_id",
        "recorded_at",
        "scenario",
        "dataset",
        "rows_checked",
        "failed_checks",
        "severity",
        "diagnosis_engine",
        "quarantined",
        "audit_hash",
        "collaboration_status",
        "collaboration_summary",
        "llm_provider",
        "llm_model",
        "llm_api",
        "llm_interaction_id",
        "llm_previous_interaction_id",
        "llm_response_format",
        "llm_prompt_version",
        "llm_latency_ms",
        "llm_tool_names",
        "llm_tool_calls",
        "llm_fallback_reason",
        "requires_manual_review",
        "summary",
        "diagnosis_report_path",
        "incident_report_path",
    ]
    selected_columns = _existing_columns(database, table_name, columns)
    query = f"select {', '.join(selected_columns)} from {table_name} order by recorded_at desc limit {safe_limit}"
    rows = database.query_database(query)
    records = rows.to_dict(orient="records")
    for r in records:
        if "quarantined" in r:
            r["quarantined"] = bool(r["quarantined"]) or int(r.get("failed_checks") or 0) > 0
    return records


def _format_report(
    run_id: str,
    scenario: str,
    quality_report: QualityReport,
    diagnosis: AgentDiagnosis,
    llm_metadata: dict,
    investigation: InvestigationReport,
    resolution: ResolutionPlan,
    quarantined: bool = False,
    audit_hash: str | None = None,
    collaboration: ConsensusReport | None = None,
) -> str:
    failed_checks = quality_report.failed_checks
    status_label = "Isolado na Quarentena (DLQ) - Carga bloqueada" if quarantined else "Aprovado - Carga liberada na base"
    lines = [
        "# Relatório de incidente",
        "",
        f"- Run id: {run_id}",
        f"- Cenário: {scenario}",
        f"- Base: {quality_report.dataset_name}",
        f"- Status do lote: {status_label}",
        f"- Linhas avaliadas: {quality_report.total_rows}",
        f"- Validações com falha: {len(failed_checks)}",
        f"- Gravidade: {_severity_label(diagnosis.severity)}",
        f"- LLM: {_format_llm_metadata(llm_metadata)}",
        "",
    ]

    if collaboration:
        status_txt = "Consenso Refinado (com calibração)" if collaboration.status == "consenso_refinado" else "Consenso Direto"
        lines.extend(
            [
                "## Colaboração e Consenso Multiagente",
                "",
                f"- **Status:** {status_txt}",
                f"- **Rodadas de debate:** {collaboration.iterations}",
                f"- **Decisão do Supervisor:** {collaboration.supervisor_decision}",
                "",
                "### Diálogo entre os Agentes:",
                "",
            ]
        )
        for turn in collaboration.conversation:
            role_label = {
                "diagnosis": "Diagnóstico",
                "investigation": "Investigação",
                "calibration": "Calibração",
                "action_plan": "Plano de Ação",
            }.get(turn.role, turn.role.capitalize())
            lines.append(f"- **{turn.speaker}** *({role_label})*: {turn.message}")
        lines.append("")

    lines.extend(
        [
            "## Diagnóstico",
            "",
            diagnosis.summary,
            "",
            "## Investigação",
            "",
            investigation.summary,
            "",
            "### Evidências",
            "",
        ]
    )
    lines.extend(f"- {_humanize(item)}" for item in investigation.evidence)
    lines.extend(
        [
            "",
            "### Hipótese",
            "",
            investigation.hypothesis,
            "",
            "## Plano de resolução",
            "",
            resolution.summary,
            "",
            "### Impacto",
            "",
            resolution.impact,
            "",
            "### Correções sugeridas",
            "",
        ]
    )
    lines.extend(f"- {_humanize(item)}" for item in resolution.correction_steps)
    lines.extend(["", "### Prevenção", ""])
    lines.extend(f"- {_humanize(item)}" for item in resolution.prevention_steps)
    lines.extend(["", f"- Revisão manual necessária: {'sim' if resolution.requires_manual_review else 'não'}", ""])

    if audit_hash:
        lines.extend(
            [
                "---",
                f"**Trilha de Auditoria (SHA-256):** `{audit_hash}`",
                "",
            ]
        )

    return "\n".join(lines)


def _severity_label(severity: str) -> str:
    labels = {
        "low": "baixa",
        "medium": "média",
        "high": "alta",
        "critical": "crítica",
    }
    return labels.get(severity, severity)


def _humanize(text: str) -> str:
    replacements = {
        "check_nulls": "nulos",
        "check_duplicates": "duplicados",
        "check_schema": "estrutura",
        "check_types": "tipo",
        "check_anomalies": "anomalias",
        "date": "data",
        "value": "valor",
        "series_code": "código da série",
        "source": "origem",
    }
    clean = text
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    return clean


def _format_llm_metadata(metadata: dict) -> str:
    if metadata.get("provider") != "gemini":
        return f"regras locais ({metadata.get('fallback_reason') or 'sem chamada externa'})"

    parts = [metadata.get("model") or "modelo não informado"]
    if metadata.get("api"):
        parts.append(metadata["api"])
    if metadata.get("response_format"):
        parts.append(metadata["response_format"])
    if metadata.get("interaction_id"):
        parts.append(f"interaction {metadata['interaction_id']}")
    if metadata.get("tool_calls"):
        parts.append("tools: " + ", ".join(metadata["tool_calls"]))
    return "Gemini - " + " | ".join(parts)


def _normalize_limit(limit: int) -> int:
    return max(1, int(limit))


def _existing_columns(database: DatabaseClient, table_name: str, expected_columns: list[str]) -> list[str]:
    columns = database.column_names(table_name)
    return [column for column in expected_columns if column in columns]


def read_run_diagnosis_from_disk(run_id: str, curated_dir: Path) -> dict:
    # le o json do diagnostico pelo id do run ou cai no arquivo geral mais recente
    run_file = curated_dir / f"quality_diagnosis_{run_id}.json"
    if run_file.exists():
        try:
            return json.loads(run_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    latest_file = curated_dir / "quality_diagnosis.json"
    if latest_file.exists():
        try:
            data = json.loads(latest_file.read_text(encoding="utf-8"))
            if str(data.get("run_id")) == str(run_id):
                return data
        except Exception:
            pass

    return {}

