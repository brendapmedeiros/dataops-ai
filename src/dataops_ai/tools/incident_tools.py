from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from dataops_ai.models import AgentDiagnosis, InvestigationReport, QualityReport, ResolutionPlan
from dataops_ai.tools.database_tools import DatabaseClient


def create_incident_report(
    output_dir: Path,
    run_id: str,
    scenario: str,
    quality_report: QualityReport,
    diagnosis: AgentDiagnosis,
    llm_metadata: dict,
    investigation: InvestigationReport,
    resolution: ResolutionPlan,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "incident_report.md"
    report_path.write_text(
        _format_report(run_id, scenario, quality_report, diagnosis, llm_metadata, investigation, resolution),
        encoding="utf-8",
    )
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
    return rows.to_dict(orient="records")


def _format_report(
    run_id: str,
    scenario: str,
    quality_report: QualityReport,
    diagnosis: AgentDiagnosis,
    llm_metadata: dict,
    investigation: InvestigationReport,
    resolution: ResolutionPlan,
) -> str:
    failed_checks = quality_report.failed_checks
    lines = [
        "# Relatório de incidente",
        "",
        f"- Run id: {run_id}",
        f"- Cenário: {scenario}",
        f"- Base: {quality_report.dataset_name}",
        f"- Linhas avaliadas: {quality_report.total_rows}",
        f"- Validações com falha: {len(failed_checks)}",
        f"- Gravidade: {_severity_label(diagnosis.severity)}",
        f"- LLM: {_format_llm_metadata(llm_metadata)}",
        "",
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
