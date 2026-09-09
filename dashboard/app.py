from __future__ import annotations

import importlib
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

from dataops_ai.agents.orchestrator import AgentOrchestrator
from dataops_ai.config import load_settings
from dataops_ai.tools.api_tools import get_api_status
from dataops_ai.tools.database_tools import DatabaseClient
from dataops_ai.tools.incident_tools import generate_audit_hash, read_incident_history

import dashboard.components.audit
import dashboard.components.collaboration_view
import dashboard.components.console
import dashboard.components.data_viewer
import dashboard.components.header
import dashboard.components.icons
import dashboard.components.incidents
import dashboard.components.overview
import dashboard.components.quarantine

# Força o recarregamento dos componentes do disco em cada execução do Streamlit
importlib.reload(dashboard.components.icons)
importlib.reload(dashboard.components.collaboration_view)
importlib.reload(dashboard.components.header)
importlib.reload(dashboard.components.overview)
importlib.reload(dashboard.components.incidents)
importlib.reload(dashboard.components.quarantine)
importlib.reload(dashboard.components.data_viewer)
importlib.reload(dashboard.components.console)
importlib.reload(dashboard.components.audit)

from dashboard.components.audit import render_audit_drawer
from dashboard.components.console import render_simulation_tab
from dashboard.components.data_viewer import render_data_viewer_tab
from dashboard.components.header import render_cockpit_header
from dashboard.components.incidents import render_incidents_tab
from dashboard.components.overview import render_overview_tab
from dashboard.components.quarantine import render_quarantine_tab

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

ICON_PATH = PROJECT_ROOT / "dashboard" / "assets" / "dataops_badge.jpg"
PAGE_ICON = str(ICON_PATH) if ICON_PATH.exists() else None

st.set_page_config(
    page_title="DataOps AI",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main() -> None:
    _apply_theme()

    settings = load_settings(PROJECT_ROOT)
    status = _load_system_status()
    history_records = _load_history_data()
    scenarios = _load_scenarios()

    history_df = _history_dataframe(history_records)
    db_count = _load_db_count(settings.database_url)

    # Header
    render_cockpit_header(status, history_df)

    # Abas
    (
        tab_overview,
        tab_incidents,
        tab_quarantine,
        tab_gold,
        tab_simulation,
    ) = st.tabs(
        [
            "Visão Geral",
            "Incidentes",
            "Quarentena",
            "Base",
            "Simulador",
        ]
    )

    with tab_overview:
        render_overview_tab(status, history_df, db_row_count=db_count)

    with tab_incidents:
        render_incidents_tab(history_df, settings.curated_dir)

    with tab_quarantine:
        render_quarantine_tab(settings.dlq_dir, database_url=settings.database_url)

    with tab_gold:
        render_data_viewer_tab(settings.database_url)

    with tab_simulation:
        render_simulation_tab(scenarios, history_df, _run_pipeline)

    # Auditoria
    st.markdown('<div class="ambient-divider"></div>', unsafe_allow_html=True)
    render_audit_drawer(history_df)


# Tema

def _apply_theme() -> None:
    """Injeta o tema visual no Streamlit."""
    css_path = Path(__file__).resolve().parent / "styles" / "theme.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>\n{css_content}\n</style>", unsafe_allow_html=True)
    else:
        st.warning("Arquivo de tema 'theme.css' não encontrado.")


# Execução híbrida 

def _run_pipeline(scenario: str) -> dict | None:
    """Executa a pipeline via API ou pelo orquestrador local."""
    # Tenta disparar via API se estiver on
    api_resp = _post_json("/execucoes", {"scenario": scenario})
    if api_resp:
        return api_resp

    # Fallback pra orquestrador local
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
            "collaboration_status": result.collaboration.status if result.collaboration else None,
            "collaboration_summary": result.collaboration.supervisor_decision if result.collaboration else None,
            "collaboration": result.collaboration.model_dump() if result.collaboration else None,
            "resumo": result.resolution.summary,
        }
    except Exception as exc:
        # limpa excecoes e protege contra vazamento
        st.error(f"Erro ao executar a pipeline ({type(exc).__name__}). Verifique os logs para detalhes.")
        return None



def _load_system_status() -> dict:
    """Carrega o status operacional da API ou dos conectores locais."""
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
    """Busca os registros de incidentes na API ou no armazenamento local."""
    api_history = _get_json("/historico?limit=30")
    if api_history and "historico" in api_history:
        return api_history["historico"]

    # Fallback local
    try:
        settings = load_settings(PROJECT_ROOT)
        return read_incident_history(settings.curated_dir, limit=30)
    except Exception:
        return []


def _load_scenarios() -> dict:
    """Busca os cenários de teste disponíveis."""
    api_scenarios = _get_json("/cenarios")
    if api_scenarios:
        return api_scenarios
    return {"cenarios": PUBLIC_SCENARIOS}


def _load_db_count(database_url: str) -> int:
    """Carrega a contagem total de registros na tabela bcb_timeseries."""
    try:
        db = DatabaseClient(database_url)
        if db.table_exists("bcb_timeseries"):
            return db.count_rows("bcb_timeseries")
    except Exception:
        pass
    return 0


def _history_dataframe(records: list[dict]) -> pd.DataFrame:
    """Normaliza o histórico para visualização em gráficos e tabelas."""
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records).copy()
    df["ordem"] = range(len(df), 0, -1)
    df["cenário"] = df["scenario"]
    df["falhas"] = df["failed_checks"].astype(int)
    df["gravidade"] = df["severity"].map(_severity_label)
    # Determina quarentena
    # Se a flag estiver True/1 ou se houve falhas de contrato (Circuit Breaker ativado)
    is_quarantined = df.apply(
        lambda r: bool(r.get("quarantined")) or int(r.get("falhas", 0)) > 0,
        axis=1,
    )
    df["quarentena"] = is_quarantined.map(lambda value: "sim (DLQ)" if value else "não")
    # garante hash determinístico mesmo em registros legados
    def _resolve_hash(r):
        val = str(r.get("audit_hash") or "").strip()
        if val and val != "None":
            return val
        run_id = str(r.get("run_id") or "")
        if not run_id:
            return ""
        scenario = str(r.get("scenario") or "sem incidente")
        rows = str(r.get("rows_checked", 22))
        fails = str(r.get("falhas", 0))
        summary = str(r.get("summary", ""))
        quarantined = str(r.get("quarentena") == "sim (DLQ)").lower()
        payload = f"{run_id}:{scenario}:{rows}:{fails}:{summary}:{quarantined}"
        return generate_audit_hash(run_id, payload)

    df["audit_hash"] = df.apply(_resolve_hash, axis=1)
    df["motor"] = df["diagnosis_engine"].str.replace("_", " ", regex=False)
    df["revisão_manual"] = df["requires_manual_review"].map(lambda value: "sim" if value else "não")
    df["resumo"] = df["summary"]
    df["collaboration_status"] = _optional_column(df, "collaboration_status")
    df["collaboration_summary"] = _optional_column(df, "collaboration_summary")
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
    api_key = os.getenv("DATAOPS_API_KEY", "dataops-secret-key")
    headers = {"X-API-Key": api_key} if api_key else None
    try:
        response = requests.post(f"{API_URL}{path}", json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None



if __name__ == "__main__":
    main()