from __future__ import annotations

import os
from pathlib import Path
import sys

import pandas as pd
import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataops_ai.config import load_settings
from dataops_ai.agents.orchestrator import AgentOrchestrator
from dataops_ai.tools.incident_tools import read_incident_history
from dataops_ai.tools.database_tools import DatabaseClient
from dataops_ai.tools.api_tools import get_api_status

from dashboard.components import (
    render_hero_card,
    render_bento_metrics,
    render_ecg_telemetry,
    render_action_console,
    render_audit_drawer,
)

API_URL = os.getenv("DATAOPS_API_URL", "http://127.0.0.1:8000").rstrip("/")
DOCS_URL = os.getenv("DATAOPS_DOCS_URL", "http://127.0.0.1:8000/docs")

SEVERITY_LABELS = {
    "low": "baixa",
    "medium": "média",
    "high": "alta",
    "critical": "crítica",
}

SCENARIO_ALIASES = {
    "sem_incidente": "none",
    "valores_nulos": "scenario_01_null_values",
    "mudanca_estrutura": "scenario_02_missing_column",
    "registros_duplicados": "scenario_03_duplicate_records",
    "timeout_api": "scenario_04_api_timeout",
    "tipo_invalido": "scenario_05_invalid_type",
}

PUBLIC_SCENARIOS = [
    {"nome": "sem_incidente", "descricao": "executa a pipeline sem forçar erro"},
    {"nome": "valores_nulos", "descricao": "força valor nulo em coluna obrigatória"},
    {"nome": "mudanca_estrutura", "descricao": "remove coluna obrigatória do schema"},
    {"nome": "registros_duplicados", "descricao": "duplica registros da série"},
    {"nome": "tipo_invalido", "descricao": "insere texto em coluna numérica"},
    {"nome": "timeout_api", "descricao": "simula falha de rede e fallback local"},
]

st.set_page_config(
    page_title="DataOps AI // Mission Pulse",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main() -> None:
    _apply_theme()

    status = _load_system_status()
    history_records = _load_history_data()
    scenarios = _load_scenarios()

    history_df = _history_dataframe(history_records)

    # BENTO GRID - ROW 1
    top_left, top_right = st.columns([0.42, 0.58], gap="medium")
    with top_left:
        render_hero_card(status, history_df)
    with top_right:
        render_bento_metrics(status, history_df)

    st.markdown('<div class="spacing-gap-md"></div>', unsafe_allow_html=True)

    # BENTO GRID - ROW 2
    bot_left, bot_right = st.columns([0.50, 0.50], gap="medium")
    with bot_left:
        render_ecg_telemetry(history_df)
    with bot_right:
        render_action_console(scenarios, history_df, _run_pipeline)

    st.markdown('<div class="ambient-divider"></div>', unsafe_allow_html=True)
    render_audit_drawer(history_df)


# -----------------------------------------------------------------------------
# THEME INJECTION
# -----------------------------------------------------------------------------
def _apply_theme() -> None:
    """Loads the centralized CSS theme and injects it into Streamlit."""
    css_path = Path(__file__).resolve().parent / "styles" / "theme.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>\n{css_content}\n</style>", unsafe_allow_html=True)
    else:
        st.warning("Arquivo de tema 'theme.css' não encontrado.")


# -----------------------------------------------------------------------------
# HYBRID DATA & EXECUTION (API with Seamless Local Fallback)
# -----------------------------------------------------------------------------
def _run_pipeline(scenario: str) -> dict | None:
    """Executes the pipeline either through the FastAPI backend or via local orchestrator fallback."""
    # 1. Tenta disparar via API FastAPI (se estiver online)
    api_resp = _post_json("/execucoes", {"scenario": scenario})
    if api_resp:
        return api_resp

    # 2. Fallback autônomo: dispara direto pelo Orquestrador Python local
    try:
        settings = load_settings(PROJECT_ROOT)
        scenario_alias = SCENARIO_ALIASES.get(scenario, scenario)
        result = AgentOrchestrator(settings).run(scenario_alias, scenario)
        return {
            "run_id": result.run_id,
            "cenario": scenario,
            "linhas_carregadas": result.rows_loaded,
            "validacoes_com_falha": len(result.quality_report.failed_checks),
            "gravidade": result.diagnosis.severity,
            "motor_do_diagnostico": result.diagnosis_engine,
            "quarentenado": result.quarantined,
            "audit_hash": result.audit_hash,
            "resumo": result.resolution.summary,
        }
    except Exception as exc:
        st.error(f"Erro ao executar localmente: {exc}")
        return None


def _load_system_status() -> dict:
    """Loads operational health status from API or evaluates local connectors."""
    api_status = _get_json("/status")
    if api_status:
        return api_status

    # Fallback local direto
    try:
        settings = load_settings(PROJECT_ROOT)
        db = DatabaseClient(settings.database_url)
        try:
            db_ok = bool(db.ping())
        except Exception:
            db_ok = False

        api_res = get_api_status(
            settings.bcb_series_code,
            settings.bcb_start_date,
            settings.bcb_end_date,
            timeout_seconds=5,
        )
        api_ok = bool(api_res.get("available"))
        gemini_ok = bool(settings.gemini_api_key)

        return {
            "banco": {"conectado": db_ok, "tipo": "SQLite" if "sqlite" in settings.database_url else "PostgreSQL"},
            "api_banco_central": {"available": api_ok},
            "gemini": {"configurado": gemini_ok, "modelo": settings.gemini_model if gemini_ok else "regras locais"},
        }
    except Exception:
        return {}


def _load_history_data() -> list[dict]:
    """Retrieves incident history records from API or local storage."""
    api_history = _get_json("/historico?limit=30")
    if api_history and "historico" in api_history:
        return api_history["historico"]

    # Fallback local
    try:
        settings = load_settings(PROJECT_ROOT)
        return read_incident_history(settings.incident_history_path, limit=30)
    except Exception:
        return []


def _load_scenarios() -> dict:
    """Retrieves available test scenarios."""
    api_scenarios = _get_json("/cenarios")
    if api_scenarios:
        return api_scenarios
    return {"cenarios": PUBLIC_SCENARIOS}


def _history_dataframe(records: list[dict]) -> pd.DataFrame:
    """Transforms raw records into a normalized DataFrame for charts and tables."""
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records).copy()
    df["ordem"] = range(len(df), 0, -1)
    df["cenário"] = df["scenario"]
    df["falhas"] = df["failed_checks"].astype(int)
    df["gravidade"] = df["severity"].map(_severity_label)
    df["quarentena"] = df.get("quarantined", pd.Series([False] * len(df))).map(
        lambda value: "sim (DLQ)" if value else "não"
    )
    df["audit_hash"] = _optional_column(df, "audit_hash")
    df["motor"] = df["diagnosis_engine"].str.replace("_", " ", regex=False)
    df["revisão_manual"] = df["requires_manual_review"].map(lambda value: "sim" if value else "não")
    df["resumo"] = df["summary"]
    return df


def _severity_label(value: str) -> str:
    return SEVERITY_LABELS.get(str(value), str(value))


def _optional_column(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df:
        return df[name].fillna("")
    return pd.Series([""] * len(df), index=df.index)


def _get_json(path: str) -> dict | None:
    try:
        response = requests.get(f"{API_URL}{path}", timeout=2)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def _post_json(path: str, payload: dict) -> dict | None:
    try:
        response = requests.post(f"{API_URL}{path}", json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


if __name__ == "__main__":
    main()