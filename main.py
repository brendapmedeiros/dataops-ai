from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dataops_ai.agents.orchestrator import AgentOrchestrator
from dataops_ai.config import load_settings
from dataops_ai.scenarios import SCENARIOS, apply_scenario
from dataops_ai.tools.api_tools import get_api_status
from dataops_ai.tools.database_tools import DatabaseClient
from dataops_ai.tools.incident_tools import read_incident_history, read_incident_history_from_database
from dataops_ai.tools.quality_tools import run_quality_checks


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
    parser.add_argument(
        "command",
        choices=[
            "run",
            "rodar",
            "scenarios",
            "cenarios",
            "history",
            "historico",
            "database",
            "banco",
            "status",
            "validate",
            "validar",
        ],
    )
    parser.add_argument("--scenario", default="sem_incidente")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    if args.command in {"scenarios", "cenarios"}:
        print(_format_scenarios())
        return

    settings = load_settings(PROJECT_ROOT)
    if args.command in {"history", "historico"}:
        print(_format_history(_read_history(settings, args.limit)))
        return

    if args.command in {"database", "banco"}:
        print(_format_database_check(settings.database_url))
        return

    if args.command == "status":
        print(_format_status(settings))
        return

    if args.command in {"validate", "validar"}:
        print(_format_validation(settings))
        return

    scenario = _normalize_scenario(args.scenario)
    result = AgentOrchestrator(settings).run(scenario, _scenario_label(scenario))

    print(
        _format_terminal_report(
            result,
        )
    )
    print(f"\nRelatório salvo em: {result.diagnosis_report_path}")
    print(f"Relatório de incidente salvo em: {result.incident_report_path}")
    print(f"Histórico atualizado em: {result.history_path}")


def _normalize_scenario(raw_scenario: str) -> str:
    scenario = SCENARIO_ALIASES.get(raw_scenario)
    if scenario:
        return scenario

    valid = ", ".join(_public_scenario_labels().keys())
    raise SystemExit(f"Cenário inválido: {raw_scenario}\nUse um destes: {valid}")


def _format_scenarios() -> str:
    lines = ["Cenários disponíveis:"]
    for alias, description in _public_scenario_labels().items():
        lines.append(f"- {alias}: {description}")
    return "\n".join(lines)


def _format_history(records: list[dict]) -> str:
    if not records:
        return "Nenhum histórico encontrado ainda."

    lines = ["Histórico recente de incidentes:"]
    for record in records:
        manual_review = "sim" if record.get("requires_manual_review") else "não"
        lines.append(
            "- "
            f"{record.get('run_id', 'sem run id')} | "
            f"{record.get('scenario', 'cenário desconhecido')} | "
            f"gravidade: {_severity_label(record.get('severity', ''))} | "
            f"falhas: {record.get('failed_checks', 0)} | "
            f"revisão manual: {manual_review}"
        )
    return "\n".join(lines)


def _read_history(settings, limit: int) -> list[dict]:
    try:
        records = read_incident_history_from_database(settings.database_url, limit=limit)
    except RuntimeError:
        records = []

    if records:
        return records

    return read_incident_history(settings.curated_dir, limit=limit)


def _format_database_check(database_url: str) -> str:
    DatabaseClient(database_url).ping()
    backend = "PostgreSQL" if database_url.startswith("postgresql") else "SQLite"
    return f"Banco configurado: {backend}\nConexão ok."


def _format_status(settings) -> str:
    lines = ["Status do DataOps AI", ""]

    try:
        lines.append(_format_database_check(settings.database_url))
    except RuntimeError as exc:
        lines.append(f"Banco: falhou\n{exc}")

    api_status = get_api_status(
        settings.bcb_series_code,
        settings.bcb_start_date,
        settings.bcb_end_date,
        timeout_seconds=5,
    )
    api_label = "disponível" if api_status["available"] else "indisponível"
    lines.extend(["", f"API Banco Central: {api_label}"])

    if api_status["status_code"]:
        lines.append(f"Código HTTP: {api_status['status_code']}")
    if api_status["error"]:
        lines.append(f"Erro: {api_status['error']}")

    return "\n".join(lines)


def _format_validation(settings) -> str:
    lines = ["Validação rápida do core", ""]

    database = DatabaseClient(settings.database_url)
    database_ok = False
    try:
        database.ping()
        database_ok = True
        lines.append("Banco: ok")
        lines.append(_format_history_table_status(database))
    except RuntimeError as exc:
        lines.append(f"Banco: falhou\n{exc}")

    api_status = get_api_status(
        settings.bcb_series_code,
        settings.bcb_start_date,
        settings.bcb_end_date,
        timeout_seconds=5,
    )
    api_label = "ok" if api_status["available"] else "alerta"
    lines.append(f"API Banco Central: {api_label}")

    scenario_results = _validate_quality_rules()
    quality_ok = all(result["ok"] for result in scenario_results)
    lines.extend(["", "Cenários de qualidade:"])
    for result in scenario_results:
        status = "ok" if result["ok"] else "falhou"
        lines.append(f"- {result['scenario']}: {status}")

    lines.append("")
    if database_ok and quality_ok and api_status["available"]:
        lines.append("Resultado: core pronto para execução.")
    elif database_ok and quality_ok:
        lines.append("Resultado: core ok, mas a API precisa ser verificada.")
    else:
        lines.append("Resultado: revisar os itens com falha antes de continuar.")

    return "\n".join(lines)


def _format_history_table_status(database: DatabaseClient) -> str:
    if not database.table_exists("incident_history"):
        return "Histórico no banco: tabela ainda não criada"

    total_rows = database.count_rows("incident_history")
    return f"Histórico no banco: {total_rows} registro(s)"


def _validate_quality_rules() -> list[dict]:
    base_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "value": [1.0, 1.1],
            "series_code": [11, 11],
            "source": ["teste", "teste"],
        }
    )
    cases = [
        ("sem incidente", "none", set()),
        ("valores nulos", "scenario_01_null_values", {"check_nulls"}),
        ("mudança de estrutura", "scenario_02_schema_drift", {"check_schema"}),
        ("registros duplicados", "scenario_04_duplicate_records", {"check_duplicates"}),
        ("tipo inválido", "scenario_05_invalid_type", {"check_types"}),
    ]
    results = []
    for label, scenario, expected_failures in cases:
        staged = apply_scenario(base_df, scenario)
        report = run_quality_checks(staged)
        failed_names = {issue.check_name for issue in report.failed_checks}
        ok = failed_names == expected_failures if not expected_failures else expected_failures.issubset(failed_names)
        results.append({"scenario": label, "ok": ok, "failed_checks": sorted(failed_names)})

    return results


def _public_scenario_labels() -> dict[str, str]:
    return {
        "sem_incidente": "roda a pipeline sem forçar erro",
        "valores_nulos": "insere valor nulo",
        "mudanca_estrutura": "renomeia uma coluna esperada",
        "timeout_api": "simula demora ou falha na origem da API",
        "registros_duplicados": "duplica uma linha",
        "tipo_invalido": "insere texto onde deveria ter número",
    }


def _scenario_label(scenario: str) -> str:
    labels = {
        "none": "sem incidente",
        "scenario_01_null_values": "valores nulos",
        "scenario_02_schema_drift": "mudança de estrutura",
        "scenario_03_api_timeout": "timeout na API",
        "scenario_04_duplicate_records": "registros duplicados",
        "scenario_05_invalid_type": "tipo inválido",
    }
    return labels.get(scenario, scenario)


def _severity_label(severity: str) -> str:
    labels = {
        "low": "baixa",
        "medium": "média",
        "high": "alta",
        "critical": "crítica",
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
    llm_metadata = result.llm_metadata
    failed_checks = quality_report.failed_checks
    lines = [
        "DataOps AI - diagnóstico da execução",
        "",
        f"Run id: {result.run_id}",
        f"Cenário testado: {_scenario_label(result.scenario)}",
        f"Linhas carregadas: {result.rows_loaded}",
        f"Validações com falha: {len(failed_checks)}",
        f"Gravidade: {_severity_label(diagnosis.severity)}",
        f"Motor do diagnóstico: {engine_labels.get(result.diagnosis_engine, result.diagnosis_engine)}",
        f"LLM: {_format_llm_metadata(llm_metadata)}",
        "",
    ]

    if failed_checks:
        lines.append("Validações que falharam:")
        for issue in failed_checks:
            column = f" em {_column_label(issue.column)}" if issue.column else ""
            lines.append(f"- {_check_label(issue.check_name)}{column}: {issue.details}")
    else:
        lines.append("Nenhuma validação falhou.")

    lines.extend(
        [
            "",
            "Diagnóstico:",
            _humanize_terminal_text(diagnosis.summary),
            "",
            "Possíveis causas:",
        ]
    )
    lines.extend(f"- {_humanize_terminal_text(cause)}" for cause in diagnosis.probable_causes)

    lines.extend(["", "Próximas ações:"])
    lines.extend(f"- {_humanize_terminal_text(action)}" for action in diagnosis.recommended_actions)

    if diagnosis.needs_investigation_agent:
        lines.append("\nInvestigação inicial acionada nesta execução.")

    lines.extend(
        [
            "",
            "Investigação:",
            _humanize_terminal_text(investigation.summary),
            "",
            "Evidências:",
        ]
    )
    lines.extend(f"- {_humanize_terminal_text(_replace_internal_labels(item))}" for item in investigation.evidence)

    lines.extend(
        [
            "",
            "Hipótese:",
            _humanize_terminal_text(investigation.hypothesis),
            "",
            "Ações sugeridas pela investigação:",
        ]
    )
    lines.extend(f"- {_humanize_terminal_text(item)}" for item in investigation.next_steps)

    lines.extend(
        [
            "",
            "Resolução:",
            _humanize_terminal_text(resolution.summary),
            "",
            "Impacto:",
            _humanize_terminal_text(resolution.impact),
            "",
            "Correções sugeridas:",
        ]
    )
    lines.extend(f"- {_humanize_terminal_text(item)}" for item in resolution.correction_steps)
    lines.extend(["", f"Precisa de revisão manual: {'sim' if resolution.requires_manual_review else 'não'}"])

    return "\n".join(lines)


def _check_label(check_name: str) -> str:
    labels = {
        "check_nulls": "nulos",
        "check_duplicates": "duplicados",
        "check_schema": "estrutura",
        "check_types": "tipo",
        "check_anomalies": "anomalias",
    }
    return labels.get(check_name, check_name)


def _format_llm_metadata(metadata) -> str:
    if metadata.provider != "gemini":
        return f"regras locais ({metadata.fallback_reason or 'sem chamada externa'})"

    parts = [metadata.model or "modelo não informado"]
    if metadata.api:
        parts.append(metadata.api)
    if metadata.response_format:
        parts.append(metadata.response_format)
    if metadata.interaction_id:
        parts.append(f"interaction {metadata.interaction_id}")
    return "Gemini - " + " | ".join(parts)


def _column_label(column: str) -> str:
    labels = {
        "date": "data",
        "value": "valor",
        "series_code": "código da série",
        "source": "origem",
    }
    return labels.get(column, column)


def _humanize_terminal_text(text: str) -> str:
    replacements = {
        "'value'": "valor",
        '"value"': "valor",
        " value ": " valor ",
        "dataset": "base",
        "Dataset": "Base",
        "casting": "conversão de tipo",
        "scenario_01_null_values": "valores_nulos",
        "scenario_02_schema_drift": "mudanca_estrutura",
        "scenario_04_duplicate_records": "registros_duplicados",
        "scenario_05_invalid_type": "tipo_invalido",
        "simulated_api_timeout_fallback": "fallback local",
        "local_fallback": "fallback local",
    }
    clean = text.replace("\ufffd", "")
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    return clean


def _replace_internal_labels(text: str) -> str:
    replacements = {
        "check_nulls": "nulos",
        "check_duplicates": "duplicados",
        "check_schema": "estrutura",
        "check_types": "tipo",
        "check_anomalies": "anomalias",
        "value": "valor",
        "date": "data",
        "series_code": "código da série",
        "source": "origem",
    }
    clean = text
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    return clean


if __name__ == "__main__":
    main()
