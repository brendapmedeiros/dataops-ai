from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from dataops_ai.models import AgentDiagnosis, InvestigationReport, QualityReport, ResolutionPlan


def create_incident_report(
    output_dir: Path,
    run_id: str,
    scenario: str,
    quality_report: QualityReport,
    diagnosis: AgentDiagnosis,
    investigation: InvestigationReport,
    resolution: ResolutionPlan,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "incident_report.md"
    report_path.write_text(
        _format_report(run_id, scenario, quality_report, diagnosis, investigation, resolution),
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
    resolution: ResolutionPlan,
    diagnosis_report_path: str,
    incident_report_path: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    history_path = output_dir / "incident_history.jsonl"
    record = {
        "run_id": run_id,
        "recorded_at": datetime.now(UTC).isoformat(),
        "scenario": scenario,
        "dataset": quality_report.dataset_name,
        "rows_checked": quality_report.total_rows,
        "failed_checks": len(quality_report.failed_checks),
        "severity": diagnosis.severity,
        "diagnosis_engine": diagnosis_engine,
        "requires_manual_review": resolution.requires_manual_review,
        "summary": resolution.summary,
        "diagnosis_report_path": diagnosis_report_path,
        "incident_report_path": incident_report_path,
    }
    with history_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return history_path


def read_incident_history(output_dir: Path, limit: int = 10) -> list[dict]:
    history_path = output_dir / "incident_history.jsonl"
    if not history_path.exists():
        return []

    lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines[-limit:]]


def _format_report(
    run_id: str,
    scenario: str,
    quality_report: QualityReport,
    diagnosis: AgentDiagnosis,
    investigation: InvestigationReport,
    resolution: ResolutionPlan,
) -> str:
    failed_checks = quality_report.failed_checks
    lines = [
        "# Relatorio de incidente",
        "",
        f"- Run id: {run_id}",
        f"- Cenario: {scenario}",
        f"- Base: {quality_report.dataset_name}",
        f"- Linhas avaliadas: {quality_report.total_rows}",
        f"- Validacoes com falha: {len(failed_checks)}",
        f"- Gravidade: {_severity_label(diagnosis.severity)}",
        "",
        "## Diagnostico",
        "",
        diagnosis.summary,
        "",
        "## Investigacao",
        "",
        investigation.summary,
        "",
        "### Evidencias",
        "",
    ]
    lines.extend(f"- {_humanize(item)}" for item in investigation.evidence)
    lines.extend(
        [
            "",
            "### Hipotese",
            "",
            investigation.hypothesis,
            "",
            "## Plano de resolucao",
            "",
            resolution.summary,
            "",
            "### Impacto",
            "",
            resolution.impact,
            "",
            "### Correcoes sugeridas",
            "",
        ]
    )
    lines.extend(f"- {_humanize(item)}" for item in resolution.correction_steps)
    lines.extend(["", "### Prevencao", ""])
    lines.extend(f"- {_humanize(item)}" for item in resolution.prevention_steps)
    lines.extend(["", f"- Revisao manual necessaria: {'sim' if resolution.requires_manual_review else 'nao'}", ""])
    return "\n".join(lines)


def _severity_label(severity: str) -> str:
    labels = {
        "low": "baixa",
        "medium": "media",
        "high": "alta",
        "critical": "critica",
    }
    return labels.get(severity, severity)


def _humanize(text: str) -> str:
    replacements = {
        "check_nulls": "nulos",
        "check_duplicates": "duplicados",
        "check_schema": "estrutura",
        "check_anomalies": "anomalias",
        "date": "data",
        "value": "valor",
        "series_code": "codigo da serie",
        "source": "origem",
    }
    clean = text
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    return clean
