from __future__ import annotations

import html
import os
from pathlib import Path
import sys
import textwrap

import altair as alt
import pandas as pd
import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dataops_ai.config import load_settings
from dataops_ai.agents.orchestrator import AgentOrchestrator
from dataops_ai.tools.incident_tools import read_incident_history
from dataops_ai.tools.database_tools import DatabaseClient
from dataops_ai.tools.api_tools import get_api_status

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
    _apply_style()

    status = _load_system_status()
    history_records = _load_history_data()
    scenarios = _load_scenarios()

    history_df = _history_dataframe(history_records)

    # BENTO GRID - ROW 1
    top_left, top_right = st.columns([0.42, 0.58], gap="medium")
    with top_left:
        _render_hero_card(status, history_df)
    with top_right:
        _render_bento_metrics(status, history_df)

    st.markdown('<div style="height: 1.25rem;"></div>', unsafe_allow_html=True)

    # BENTO GRID - ROW 2
    bot_left, bot_right = st.columns([0.50, 0.50], gap="medium")
    with bot_left:
        _render_ecg_telemetry(history_df)
    with bot_right:
        _render_action_console(scenarios, history_df)

    st.markdown('<div class="ambient-divider"></div>', unsafe_allow_html=True)
    _render_audit_drawer(history_df)


# -----------------------------------------------------------------------------
# 1. HERO BENTO CARD
# -----------------------------------------------------------------------------
def _render_hero_card(status: dict | None, history_df: pd.DataFrame) -> None:
    database = status.get("banco", {}) if status else {}
    bcb_api = status.get("api_banco_central", {}) if status else {}

    db_ok = bool(database.get("conectado"))
    api_ok = bool(bcb_api.get("available"))

    total_runs = len(history_df)
    failed_runs = int((history_df["falhas"] > 0).sum()) if not history_df.empty else 0

    if total_runs == 0:
        headline = "Sistema Pronto"
        sub = "Inicie uma execução no console para monitorar a telemetria."
    elif failed_runs == 0:
        headline = "100% Saudável"
        sub = f"Todas as últimas {total_runs} execuções passaram com contratos íntegros."
    else:
        headline = "Proteção Ativa"
        sub = f"Circuit breaker isolou {failed_runs} anomalia(s) na Quarentena (DLQ)."

    st.markdown(
        f"""
        <div class="bento-card hero-card">
            <div class="hero-glow-sphere">
                <div class="glow-layer layer-3"></div>
                <div class="glow-layer layer-2"></div>
                <div class="glow-layer layer-1"></div>
                <div class="glow-center">
                    <div class="core-spark"></div>
                </div>
            </div>
            <div class="hero-content">
                <div class="hero-tag">DATAOPS AI // LIVE GOVERNANCE</div>
                <h2 class="hero-headline">{_safe(headline)}</h2>
                <p class="hero-sub">{_safe(sub)}</p>
                <div class="hero-badges">
                    <span class="chip chip-blue">API BCB SGS: {'ONLINE' if api_ok else 'OFFLINE'}</span>
                    <span class="chip chip-cyan">BANCO: {'CONECTADO' if db_ok else 'DESCONECTADO'}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# 2. BENTO 2x2 MINI CARDS
# -----------------------------------------------------------------------------
def _render_bento_metrics(status: dict | None, history_df: pd.DataFrame) -> None:
    total_runs = len(history_df)
    failed_runs = int((history_df["falhas"] > 0).sum()) if not history_df.empty else 0
    clean_runs = total_runs - failed_runs
    pass_rate = (clean_runs / total_runs * 100) if total_runs > 0 else 100.0

    quarantined_count = 0
    if not history_df.empty and "quarentena" in history_df:
        quarantined_count = int(history_df["quarentena"].str.contains("sim", case=False).sum())

    manual_reviews = int((history_df["revisão_manual"] == "sim").sum()) if not history_df.empty else 0

    c1, c2 = st.columns(2, gap="medium")

    with c1:
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Pipeline Health</span>
                    <span class="mini-tag tag-blue">HEALTH</span>
                </div>
                <div class="mini-metric">{pass_rate:.0f}<small>%</small></div>
                <div class="mini-foot">Status: <b>{'Normal' if pass_rate >= 80 else 'Alerta'}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div style="height: 0.85rem;"></div>', unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Quarentena / DLQ</span>
                    <span class="mini-tag tag-cyan">CIRCUIT</span>
                </div>
                <div class="mini-metric">{quarantined_count} <small>lotes</small></div>
                <div class="mini-foot">Circuit breaker: <b>Ativo</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Volume Monitorado</span>
                    <span class="mini-tag tag-blue">SGS 11</span>
                </div>
                <div class="mini-metric">{total_runs} <small>runs</small></div>
                <div class="mini-foot">Série: <b>BCB SGS 11</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div style="height: 0.85rem;"></div>', unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Ações dos Agentes</span>
                    <span class="mini-tag tag-cyan">AGENTS</span>
                </div>
                <div class="mini-metric">{manual_reviews} <small>revisões</small></div>
                <div class="mini-foot">Motor: <b>Gemini + Local</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------------------------------------------------------
# 3. ECG TELEMETRY WAVEFORM
# -----------------------------------------------------------------------------
def _render_ecg_telemetry(history_df: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="bento-card panel-telemetry">
            <div class="telemetry-top">
                <div>
                    <span class="card-kicker">PULSO TELEMÉTRICO</span>
                    <h3 class="telemetry-title">Registro de Qualidade da Pipeline</h3>
                </div>
                <span class="live-pill">
                    <span class="pulse-spark"></span> LIVE
                </span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    if history_df.empty:
        st.info("Nenhuma execução registrada para exibir a telemetria contínua.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    chart_df = history_df.sort_values("ordem").tail(16).copy()
    chart_df["idx"] = range(1, len(chart_df) + 1)
    chart_df["run_label"] = [f"#{i}" for i in chart_df["idx"]]

    base = alt.Chart(chart_df).encode(
        x=alt.X(
            "run_label:O",
            title=None,
            axis=alt.Axis(labelColor="#475569", domainColor="#0F172A", tickColor="#0F172A"),
        ),
        y=alt.Y(
            "falhas:Q",
            title=None,
            axis=alt.Axis(labelColor="#475569", gridColor="#0F172A", tickMinStep=1),
        ),
        tooltip=["run_id", "cenário", "falhas", "gravidade", "quarentena"],
    )

    area = base.mark_area(
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color="rgba(0, 102, 255, 0.45)", offset=0),
                alt.GradientStop(color="rgba(0, 212, 255, 0.12)", offset=0.6),
                alt.GradientStop(color="rgba(0, 102, 255, 0.0)", offset=1),
            ],
            x1=1,
            x2=1,
            y1=0,
            y2=1,
        ),
        interpolate="monotone",
    )

    line = base.mark_line(
        color="#00D4FF",
        strokeWidth=2.8,
        interpolate="monotone",
    )

    points = base.mark_circle(
        color="#FFFFFF",
        size=45,
        stroke="#0066FF",
        strokeWidth=2.5,
    )

    chart = (area + line + points).properties(height=240).configure_view(strokeWidth=0).configure(background="transparent")
    st.altair_chart(chart, use_container_width=True)

    st.markdown(
        """
        <div class="ecg-footnote">
            <span>Linha Contínua: Histórico de anomalias</span>
            <span>Limiar de Contrato: 0 falhas</span>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# 4. ACTION CONSOLE & DIAGNOSTICS
# -----------------------------------------------------------------------------
def _render_action_console(scenarios: dict | None, history_df: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="bento-card panel-console">
            <div class="telemetry-top">
                <div>
                    <span class="card-kicker">DISPARO & ANOMALIAS</span>
                    <h3 class="telemetry-title">Console de Operações</h3>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    scenario_items = scenarios.get("cenarios", []) if scenarios else []
    scenario_names = [item["nome"] for item in scenario_items] or ["sem_incidente"]
    descriptions = {item["nome"]: item["descricao"] for item in scenario_items}

    selected = st.selectbox(
        "Cenário de Teste",
        scenario_names,
        index=_default_scenario_index(scenario_names),
        label_visibility="collapsed",
    )

    desc = descriptions.get(selected, "")
    if desc:
        st.markdown(f'<div class="console-action-desc">{_safe(desc)}</div>', unsafe_allow_html=True)

    if st.button("EXECUTAR DISPARO DE PIPELINE", type="primary", use_container_width=True):
        with st.spinner("Acionando pipeline, validando contratos e executando agentes..."):
            response = _run_pipeline(selected)

        if response:
            st.success(f"Execução finalizada com sucesso (#{response.get('run_id')})")
            _render_run_inline_result(response)
            st.rerun()
        else:
            st.error("Falha ao executar pipeline.")

    # Último Diagnóstico
    if not history_df.empty:
        latest = history_df.iloc[0]
        quarantined = "sim" in str(latest.get("quarentena", "")).lower()
        badge_cls = "badge-quarantine" if quarantined else "badge-approved"
        badge_lbl = "ISOLADO NA QUARENTENA (DLQ)" if quarantined else "CARGA APROVADA"
        hash_val = str(latest.get("audit_hash") or "")
        short_hash = f"{hash_val[:14]}..." if hash_val else "não calculado"

        st.markdown(
            f"""
            <div class="latest-diag-box">
                <div class="diag-header">
                    <span class="diag-tag {badge_cls}">{badge_lbl}</span>
                    <span class="diag-run">Run: <code>{_safe(latest.get("run_id"))}</code></span>
                </div>
                <p class="diag-summary">“{_safe(latest.get("resumo", ""))}”</p>
                <div class="diag-hash-bar">
                    <span class="hash-label">SHA-256:</span>
                    <code class="hash-text">{_safe(short_hash)}</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_run_inline_result(response: dict) -> None:
    quarantined = bool(response.get("quarentenado"))
    badge_cls = "badge-quarantine" if quarantined else "badge-approved"
    badge_lbl = "ISOLADO NA QUARENTENA (DLQ)" if quarantined else "CARGA APROVADA"
    hash_val = response.get("audit_hash", "")
    short_hash = f"{hash_val[:14]}..." if hash_val else "sem hash"

    st.markdown(
        f"""
        <div class="latest-diag-box" style="margin-top: 0.8rem; border-color: rgba(0, 212, 255, 0.4);">
            <div class="diag-header">
                <span class="diag-tag {badge_cls}">{badge_lbl}</span>
                <span class="diag-run">Falhas: <b>{response.get("validacoes_com_falha", 0)}</b></span>
            </div>
            <p class="diag-summary">“{_safe(response.get("resumo", ""))}”</p>
            <div class="diag-hash-bar">
                <span class="hash-label">AUDIT HASH:</span>
                <code class="hash-text">{_safe(short_hash)}</code>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# 5. AUDIT DRAWER
# -----------------------------------------------------------------------------
def _render_audit_drawer(history_df: pd.DataFrame) -> None:
    with st.expander("Trilha Completa de Auditoria Imutável (Histórico Detalhado)", expanded=False):
        if history_df.empty:
            st.info("Nenhuma execução gravada.")
            return

        table = history_df[
            [
                "run_id",
                "cenário",
                "falhas",
                "gravidade",
                "quarentena",
                "audit_hash",
                "motor",
                "revisão_manual",
                "resumo",
            ]
        ]
        st.dataframe(table, use_container_width=True, hide_index=True, height=260)


# -----------------------------------------------------------------------------
# HYBRID DATA & EXECUTION (API with Seamless Local Fallback)
# -----------------------------------------------------------------------------
def _run_pipeline(scenario: str) -> dict | None:
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
    api_scenarios = _get_json("/cenarios")
    if api_scenarios:
        return api_scenarios
    return {"cenarios": PUBLIC_SCENARIOS}


def _history_dataframe(records: list[dict]) -> pd.DataFrame:
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


def _default_scenario_index(scenario_names: list[str]) -> int:
    if "tipo_invalido" in scenario_names:
        return scenario_names.index("tipo_invalido")
    return 0


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


def _safe(value: object) -> str:
    return html.escape(str(value))


# -----------------------------------------------------------------------------
# HIGH-TECH OLED BLUE STYLING
# -----------------------------------------------------------------------------
def _apply_style() -> None:
    css = """
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap');

    :root {
        --oled-bg: #03060E;
        --card-bg: #070D1A;
        --card-border: rgba(0, 102, 255, 0.14);
        --card-border-hover: rgba(0, 212, 255, 0.40);
        --blue-primary: #0066FF;
        --blue-glow: #00D4FF;
        --blue-deep: #0D214A;
        --text-white: #FFFFFF;
        --text-muted: #8E9BAE;
        --text-dim: #4B5563;
        --pill-red: #F43F5E;
        --pill-green: #10B981;
    }

    .stApp {
        background-color: var(--oled-bg) !important;
        color: var(--text-white) !important;
        font-family: 'Outfit', -apple-system, sans-serif;
    }

    .main .block-container {
        max-width: 1260px;
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
    }

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        display: none;
    }

    /* BENTO CARD CONTAINER */
    .bento-card {
        background: linear-gradient(155deg, rgba(11, 20, 38, 0.85) 0%, rgba(5, 10, 20, 0.95) 100%);
        border: 1px solid var(--card-border);
        border-radius: 22px;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.55);
        transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
        position: relative;
        overflow: hidden;
    }
    .bento-card:hover {
        transform: translateY(-2px);
        border-color: var(--card-border-hover);
        box-shadow: 0 16px 42px rgba(0, 102, 255, 0.16);
    }

    /* HERO CARD WITH AMBIENT GLOW CORE */
    .hero-card {
        padding: 2.2rem 2.2rem;
        min-height: 275px;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
    }
    .hero-glow-sphere {
        position: absolute;
        top: -30px;
        right: -30px;
        width: 220px;
        height: 220px;
        pointer-events: none;
    }
    .glow-layer {
        position: absolute;
        border-radius: 50%;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }
    .layer-3 {
        width: 190px;
        height: 190px;
        background: radial-gradient(circle, rgba(0, 102, 255, 0.28) 0%, rgba(0, 212, 255, 0.08) 50%, transparent 75%);
        filter: blur(14px);
    }
    .layer-2 {
        width: 120px;
        height: 120px;
        background: radial-gradient(circle, rgba(0, 153, 255, 0.45) 0%, rgba(0, 102, 255, 0.2) 65%, transparent 80%);
        filter: blur(8px);
    }
    .layer-1 {
        width: 68px;
        height: 68px;
        background: radial-gradient(circle, #00D4FF 0%, #0066FF 65%, rgba(0, 102, 255, 0.2) 100%);
        box-shadow: 0 0 25px rgba(0, 212, 255, 0.7);
    }
    .glow-center {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }
    .core-spark {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #FFFFFF;
        box-shadow: 0 0 16px #00D4FF;
    }

    .hero-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.14em;
        color: var(--blue-glow);
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    .hero-headline {
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0 0 0.4rem;
        line-height: 1.1;
        color: #FFFFFF;
    }
    .hero-sub {
        font-size: 0.92rem;
        color: var(--text-muted);
        margin: 0 0 1.2rem;
        line-height: 1.4;
        max-width: 320px;
    }
    .hero-badges {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
    }
    .chip {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        padding: 0.25rem 0.65rem;
        border-radius: 999px;
        font-weight: 600;
    }
    .chip-blue {
        background: rgba(0, 102, 255, 0.12);
        color: #60A5FA;
        border: 1px solid rgba(0, 102, 255, 0.3);
    }
    .chip-cyan {
        background: rgba(0, 212, 255, 0.1);
        color: var(--blue-glow);
        border: 1px solid rgba(0, 212, 255, 0.28);
    }

    /* MINI BENTO CARDS */
    .mini-card {
        padding: 1.15rem 1.35rem;
        min-height: 130px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .mini-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .mini-label {
        font-size: 0.85rem;
        color: var(--text-muted);
        font-weight: 500;
    }
    .mini-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
    }
    .tag-blue {
        color: #60A5FA;
        background: rgba(0, 102, 255, 0.14);
        border: 1px solid rgba(0, 102, 255, 0.3);
    }
    .tag-cyan {
        color: var(--blue-glow);
        background: rgba(0, 212, 255, 0.1);
        border: 1px solid rgba(0, 212, 255, 0.3);
    }

    .mini-metric {
        font-size: 2.1rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.03em;
        line-height: 1;
        margin: 0.25rem 0;
    }
    .mini-metric small {
        font-size: 0.95rem;
        color: var(--text-muted);
        font-weight: 400;
        margin-left: 0.2rem;
    }
    .mini-foot {
        font-size: 0.76rem;
        color: var(--text-muted);
    }
    .mini-foot b {
        color: #E2E8F0;
    }

    /* TELEMETRY & CONSOLE PANELS */
    .panel-telemetry, .panel-console {
        padding: 1.5rem 1.65rem;
        min-height: 360px;
    }
    .telemetry-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 0.8rem;
    }
    .card-kicker {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        letter-spacing: 0.12em;
        color: var(--blue-glow);
        font-weight: 600;
        display: block;
        margin-bottom: 0.15rem;
    }
    .telemetry-title {
        font-size: 1.22rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0;
    }
    .live-pill {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        font-weight: 700;
        color: var(--blue-glow);
        background: rgba(0, 212, 255, 0.08);
        border: 1px solid rgba(0, 212, 255, 0.25);
        padding: 0.25rem 0.65rem;
        border-radius: 999px;
    }
    .pulse-spark {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--blue-glow);
        box-shadow: 0 0 8px var(--blue-glow);
        animation: pulseLive 2s infinite ease-in-out;
    }
    @keyframes pulseLive {
        0% { transform: scale(0.9); opacity: 0.5; }
        50% { transform: scale(1.3); opacity: 1; }
        100% { transform: scale(0.9); opacity: 0.5; }
    }

    .ecg-footnote {
        display: flex;
        justify-content: space-between;
        font-size: 0.72rem;
        color: var(--text-dim);
        border-top: 1px solid rgba(255, 255, 255, 0.04);
        padding-top: 0.75rem;
        margin-top: 0.4rem;
    }

    /* CONSOLE & RESULT */
    .console-action-desc {
        font-size: 0.8rem;
        color: var(--text-muted);
        background: rgba(0, 102, 255, 0.06);
        border-left: 2px solid var(--blue-primary);
        padding: 0.45rem 0.75rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.9rem;
    }
    .latest-diag-box {
        background: rgba(3, 7, 18, 0.6);
        border: 1px solid rgba(0, 102, 255, 0.18);
        border-radius: 14px;
        padding: 0.95rem 1.15rem;
        margin-top: 1rem;
    }
    .diag-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.4rem;
    }
    .diag-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        font-weight: 700;
        padding: 0.2rem 0.55rem;
        border-radius: 6px;
        letter-spacing: 0.06em;
    }
    .badge-approved {
        background: rgba(16, 185, 129, 0.12);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-quarantine {
        background: rgba(244, 63, 94, 0.14);
        color: #FB7185;
        border: 1px solid rgba(244, 63, 94, 0.35);
    }
    .diag-run {
        font-size: 0.75rem;
        color: var(--text-muted);
    }
    .diag-run code {
        font-family: 'JetBrains Mono', monospace;
        color: #93C5FD;
    }
    .diag-summary {
        font-size: 0.8rem;
        color: var(--text-muted);
        line-height: 1.35;
        margin: 0.35rem 0 0.6rem;
    }
    .diag-hash-bar {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        background: rgba(0, 0, 0, 0.4);
        padding: 0.3rem 0.6rem;
        border-radius: 6px;
        border: 1px dashed rgba(255, 255, 255, 0.08);
    }
    .hash-label { color: var(--text-dim); }
    .hash-text { color: var(--blue-glow); }

    /* BUTTONS & CONTROLS */
    div[data-baseweb="select"] > div {
        background: rgba(11, 20, 38, 0.75) !important;
        border-color: rgba(0, 102, 255, 0.22) !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        font-size: 0.88rem !important;
    }
    .stButton button {
        background: linear-gradient(135deg, #0066FF 0%, #00D4FF 100%) !important;
        color: #030712 !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.06em !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.4rem !important;
        box-shadow: 0 4px 20px rgba(0, 102, 255, 0.45) !important;
        transition: all 0.2s ease !important;
    }
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px rgba(0, 212, 255, 0.65) !important;
        color: #000000 !important;
    }

    div[data-testid="stExpander"] {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 16px;
    }
    .ambient-divider {
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        margin: 1.75rem 0;
    }
    """
    st.markdown(f"<style>\n{textwrap.dedent(css)}\n</style>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()