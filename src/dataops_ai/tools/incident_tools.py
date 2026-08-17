from __future__ import annotations

from pathlib import Path

from dataops_ai.models import AgentDiagnosis, InvestigationReport, QualityReport, ResolutionPlan


def create_incident_report(
    output_dir: Path,
    scenario: str,
    quality_report: QualityReport,
    diagnosis: AgentDiagnosis,
    investigation: InvestigationReport,
    resolution: ResolutionPlan,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "incident_report.md"
    report_path.write_text(
        _format_report(scenario, quality_report, diagnosis, investigation, resolution),
        encoding="utf-8",
    )
    return report_path


def _format_report(
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
