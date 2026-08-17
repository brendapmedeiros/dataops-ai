from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dataops_ai.agents.orchestrator import AgentOrchestrator
from dataops_ai.config import load_settings
from dataops_ai.scenarios import SCENARIOS
from dataops_ai.tools.incident_tools import read_incident_history


SCENARIO_ALIASES = {
    "sem_incidente": "none",
    "valores_nulos": "scenario_01_null_values",
    "mudanca_estrutura": "scenario_02_schema_drift",
    "mudanca_schema": "scenario_02_schema_drift",
    "timeout_api": "scenario_03_api_timeout",
    "registros_duplicados": "scenario_04_duplicate_records",
    "tipo_invalido": "scenario_05_invalid_type",
    **{scenario: scenario for scenario in SCENARIOS},
}


def main() -> None:
    parser = argparse.ArgumentParser(description="DataOps AI V1")
    parser.add_argument("command", choices=["run", "rodar", "scenarios", "cenarios", "history", "historico"])
    parser.add_argument("--scenario", default="sem_incidente")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    if args.command in {"scenarios", "cenarios"}:
        print(_format_scenarios())
        return

    settings = load_settings(PROJECT_ROOT)
    if args.command in {"history", "historico"}:
        print(_format_history(read_incident_history(settings.curated_dir, limit=args.limit)))
        return

    scenario = _normalize_scenario(args.scenario)
    result = AgentOrchestrator(settings).run(scenario, _scenario_label(scenario))

    print(
        _format_terminal_report(
            result,
        )
    )
    print(f"\nRelatorio salvo em: {result.diagnosis_report_path}")
    print(f"Relatorio de incidente salvo em: {result.incident_report_path}")
    print(f"Historico atualizado em: {result.history_path}")


def _normalize_scenario(raw_scenario: str) -> str:
    scenario = SCENARIO_ALIASES.get(raw_scenario)
    if scenario:
        return scenario

    valid = ", ".join(_public_scenario_labels().keys())
    raise SystemExit(f"Cenario invalido: {raw_scenario}\nUse um destes: {valid}")


def _format_scenarios() -> str:
    lines = ["Cenarios disponiveis:"]
    for alias, description in _public_scenario_labels().items():
        lines.append(f"- {alias}: {description}")
    return _plain_terminal_text("\n".join(lines))


def _format_history(records: list[dict]) -> str:
    if not records:
        return "Nenhum historico encontrado ainda."

    lines = ["Historico recente de incidentes:"]
    for record in records:
        manual_review = "sim" if record.get("requires_manual_review") else "nao"
        lines.append(
            "- "
            f"{record.get('run_id', 'sem run id')} | "
            f"{record.get('scenario', 'cenario desconhecido')} | "
            f"gravidade: {_severity_label(record.get('severity', ''))} | "
            f"falhas: {record.get('failed_checks', 0)} | "
            f"revisao manual: {manual_review}"
        )
    return _plain_terminal_text("\n".join(lines))


def _public_scenario_labels() -> dict[str, str]:
    return {
        "sem_incidente": "roda a pipeline sem forcar erro",
        "valores_nulos": "insere valor nulo",
        "mudanca_estrutura": "renomeia uma coluna esperada",
        "timeout_api": "simula demora ou falha na origem da API",
        "registros_duplicados": "duplica uma linha",
        "tipo_invalido": "insere texto onde deveria ter numero",
    }


def _scenario_label(scenario: str) -> str:
    labels = {
        "none": "sem incidente",
        "scenario_01_null_values": "valores nulos",
        "scenario_02_schema_drift": "mudanca de estrutura",
        "scenario_03_api_timeout": "timeout na API",
        "scenario_04_duplicate_records": "registros duplicados",
        "scenario_05_invalid_type": "tipo invalido",
    }
    return labels.get(scenario, scenario)


def _severity_label(severity: str) -> str:
    labels = {
        "low": "baixa",
        "medium": "media",
        "high": "alta",
        "critical": "critica",
    }
    return labels.get(severity, severity)


def _format_terminal_report(result) -> str:
    engine_labels = {
        "gemini": "Gemini",
        "regras_locais": "regras locais",
    }

    quality_report = result.quality_report
    diagnosis = result.diagnosis
    investigation = result.investigation
    resolution = result.resolution
    failed_checks = quality_report.failed_checks
    lines = [
        "DataOps AI - diagnostico da execucao",
        "",
        f"Run id: {result.run_id}",
        f"Cenario testado: {_scenario_label(result.scenario)}",
        f"Linhas carregadas: {result.rows_loaded}",
        f"Validacoes com falha: {len(failed_checks)}",
        f"Gravidade: {_severity_label(diagnosis.severity)}",
        f"Motor do diagnostico: {engine_labels.get(result.diagnosis_engine, result.diagnosis_engine)}",
        "",
    ]

    if failed_checks:
        lines.append("Validacoes que falharam:")
        for issue in failed_checks:
            column = f" em {_column_label(issue.column)}" if issue.column else ""
            lines.append(f"- {_check_label(issue.check_name)}{column}: {issue.details}")
    else:
        lines.append("Nenhuma validacao falhou.")

    lines.extend(
        [
            "",
            "Diagnostico:",
            _humanize_terminal_text(diagnosis.summary),
            "",
            "Possiveis causas:",
        ]
    )
    lines.extend(f"- {_humanize_terminal_text(cause)}" for cause in diagnosis.probable_causes)

    lines.extend(["", "Proximas acoes:"])
    lines.extend(f"- {_humanize_terminal_text(action)}" for action in diagnosis.recommended_actions)

    if diagnosis.needs_investigation_agent:
        lines.append("\nInvestigacao inicial acionada nesta execucao.")

    lines.extend(
        [
            "",
            "Investigacao:",
            _humanize_terminal_text(investigation.summary),
            "",
            "Evidencias:",
        ]
    )
    lines.extend(f"- {_humanize_terminal_text(_replace_internal_labels(item))}" for item in investigation.evidence)

    lines.extend(
        [
            "",
            "Hipotese:",
            _humanize_terminal_text(investigation.hypothesis),
            "",
            "Acoes sugeridas pela investigacao:",
        ]
    )
    lines.extend(f"- {_humanize_terminal_text(item)}" for item in investigation.next_steps)

    lines.extend(
        [
            "",
            "Resolucao:",
            _humanize_terminal_text(resolution.summary),
            "",
            "Impacto:",
            _humanize_terminal_text(resolution.impact),
            "",
            "Correcoes sugeridas:",
        ]
    )
    lines.extend(f"- {_humanize_terminal_text(item)}" for item in resolution.correction_steps)
    lines.extend(["", f"Precisa de revisao manual: {'sim' if resolution.requires_manual_review else 'nao'}"])

    return "\n".join(lines)


def _check_label(check_name: str) -> str:
    labels = {
        "check_nulls": "nulos",
        "check_duplicates": "duplicados",
        "check_schema": "estrutura",
        "check_anomalies": "anomalias",
    }
    return labels.get(check_name, check_name)


def _column_label(column: str) -> str:
    labels = {
        "date": "data",
        "value": "valor",
        "series_code": "codigo da serie",
        "source": "origem",
    }
    return labels.get(column, column)


def _plain_terminal_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.replace("\ufffd", ""))
    return normalized.encode("ascii", "ignore").decode("ascii")


def _humanize_terminal_text(text: str) -> str:
    replacements = {
        "'value'": "valor",
        '"value"': "valor",
        " value ": " valor ",
        "dataset": "base",
        "Dataset": "Base",
        "casting": "conversao de tipo",
        "scenario_01_null_values": "valores_nulos",
        "scenario_02_schema_drift": "mudanca_estrutura",
        "scenario_04_duplicate_records": "registros_duplicados",
        "scenario_05_invalid_type": "tipo_invalido",
        "simulated_api_timeout_fallback": "fallback local",
        "local_fallback": "fallback local",
    }
    clean = _plain_terminal_text(text)
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    return clean


def _replace_internal_labels(text: str) -> str:
    replacements = {
        "check_nulls": "nulos",
        "check_duplicates": "duplicados",
        "check_schema": "estrutura",
        "check_anomalies": "anomalias",
        "value": "valor",
        "date": "data",
        "series_code": "codigo da serie",
        "source": "origem",
    }
    clean = text
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    return clean


if __name__ == "__main__":
    main()
