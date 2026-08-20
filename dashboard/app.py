from __future__ import annotations

import html
import os

import altair as alt
import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv("DATAOPS_API_URL", "http://127.0.0.1:8000").rstrip("/")
DOCS_URL = os.getenv("DATAOPS_DOCS_URL", "http://127.0.0.1:8000/docs")

SEVERITY_LABELS = {
    "low": "baixa",
    "medium": "média",
    "high": "alta",
    "critical": "crítica",
}

SEVERITY_COLORS = {
    "baixa": "#2563eb",
    "média": "#d97706",
    "alta": "#ea580c",
    "crítica": "#dc2626",
}


st.set_page_config(page_title="DataOps AI", page_icon="DA", layout="wide")


def main() -> None:
    _apply_style()

    status = _get_json("/status")
    history = _get_json("/historico?limit=30")
    scenarios = _get_json("/cenarios")

    history_df = _history_dataframe(_history_records(history))

    _render_header()
    _render_kpis(status, history_df)

    chart_left, chart_right = st.columns([0.48, 0.52], gap="medium")
    with chart_left:
        _render_trend(history_df)
    with chart_right:
        _render_scenario_chart(history_df)

    lower_left, lower_center, lower_right = st.columns([0.27, 0.43, 0.30], gap="medium")
    with lower_left:
        _render_gemini_panel(status, history_df)
    with lower_center:
        _render_history_table(history_df)
    with lower_right:
        _render_run_panel(scenarios)


def _render_header() -> None:
    st.markdown(
        f"""
        <header class="topbar">
            <div class="brand">
                <span class="brand-mark">DA</span>
                <div>
                    <strong>DataOps AI</strong>
                    <small>monitor de pipeline</small>
                </div>
            </div>
            <nav>
                <span class="active">Dashboard</span>
                <span>Histórico</span>
                <a href="{DOCS_URL}" target="_blank">API docs</a>
            </nav>
        </header>

        <section class="hero">
            <div>
                <p>BCB API -> PostgreSQL -> qualidade -> agentes</p>
                <h1>Saúde do pipeline</h1>
            </div>
            <div class="hero-meta">
                <span>Core V1</span>
                <span class="gemini-pill">Gemini</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_kpis(status: dict | None, history_df: pd.DataFrame) -> None:
    database = status.get("banco", {}) if status else {}
    bcb_api = status.get("api_banco_central", {}) if status else {}

    total_runs = len(history_df)
    failed_runs = int((history_df["falhas"] > 0).sum()) if not history_df.empty else 0
    manual_review = int((history_df["revisão_manual"] == "sim").sum()) if not history_df.empty else 0

    db_value = "online" if database.get("conectado") else "falhou"
    api_value = "online" if bcb_api.get("available") else "falhou"
    api_detail = f"HTTP {bcb_api.get('status_code')}" if bcb_api.get("status_code") else "sem resposta"

    col1, col2, col3, col4 = st.columns(4, gap="medium")
    with col1:
        _metric_card("Banco", db_value, database.get("tipo") or "PostgreSQL", db_value == "online")
    with col2:
        _metric_card("Banco Central", api_value, api_detail, api_value == "online")
    with col3:
        _metric_card("Execuções", str(total_runs), f"{failed_runs} com falha", failed_runs == 0)
    with col4:
        _metric_card("Revisão manual", str(manual_review), "últimos registros", manual_review == 0)


def _render_trend(history_df: pd.DataFrame) -> None:
    with st.container(border=True):
        _panel_title("Falhas por execução", "últimas 12 execuções")
        if history_df.empty:
            st.info("Sem histórico para exibir.")
            return

        chart_df = history_df.sort_values("ordem").tail(12).copy()
        chart_df["execução"] = range(1, len(chart_df) + 1)

        base = alt.Chart(chart_df).encode(
            x=alt.X("execução:O", title="execução", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("falhas:Q", title="falhas", scale=alt.Scale(domainMin=0)),
            tooltip=["run_id", "cenário", "falhas", "gravidade"],
        )
        chart = (
            base.mark_area(color="#dbeafe", opacity=0.85)
            + base.mark_line(color="#2563eb", strokeWidth=3)
            + base.mark_point(color="#ffffff", stroke="#2563eb", strokeWidth=2, size=70)
        )
        st.altair_chart(_chart_style(chart, height=260), use_container_width=True)


def _render_scenario_chart(history_df: pd.DataFrame) -> None:
    with st.container(border=True):
        _panel_title("Incidentes por cenário", "distribuição do histórico")
        if history_df.empty:
            st.info("Sem histórico para exibir.")
            return

        chart_df = history_df["cenário"].value_counts().rename_axis("cenário").reset_index(name="execuções")
        chart = (
            alt.Chart(chart_df)
            .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color="#0f172a")
            .encode(
                x=alt.X("cenário:N", title=None, sort="-y", axis=alt.Axis(labelAngle=-20)),
                y=alt.Y("execuções:Q", title="execuções", scale=alt.Scale(domainMin=0)),
                tooltip=["cenário", "execuções"],
            )
        )
        st.altair_chart(_chart_style(chart, height=260), use_container_width=True)


def _render_gemini_panel(status: dict | None, history_df: pd.DataFrame) -> None:
    with st.container(border=True):
        _panel_title("Gemini", "configuração atual")

        gemini_status = status.get("gemini", {}) if status else {}
        configured = bool(gemini_status.get("configurado"))
        current_model = gemini_status.get("modelo") or "não informado"
        status_label = "configurado" if configured else "sem chave"
        badge_class = "status-ok" if configured else "status-warn"

        st.markdown(
            f"""
            <div class="gemini-brand">
                <span>Google</span>
                <strong>Gemini</strong>
                <small class="{badge_class}">{status_label}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if history_df.empty:
            st.info("Sem execução recente.")
            return

        latest = history_df.iloc[0]
        provider = latest.get("llm_provider") or latest.get("motor") or "local"
        last_status = "usou Gemini" if provider == "gemini" else "última execução local"
        last_badge_class = "status-ok" if provider == "gemini" else "status-warn"

        items = {
            "modelo": latest.get("llm_model") or current_model,
            "api": latest.get("llm_api") or "regras locais",
            "formato": latest.get("llm_response_format") or "sem schema",
            "interaction": latest.get("llm_interaction_id") or "não armazenada",
            "tools": latest.get("llm_tool_names") or "não informado",
            "chamadas": latest.get("llm_tool_calls") or "nenhuma",
        }
        fallback = latest.get("llm_fallback_reason")

        st.markdown(
            f"""
            <div class="gemini-summary">
                <div>
                    <span>última execução</span>
                    <strong>{_safe(provider)}</strong>
                </div>
                <small class="{last_badge_class}">{last_status}</small>
            </div>
            <div class="detail-list">
                {_detail_rows(items)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if fallback:
            message = str(fallback)
            if configured and "GEMINI_API_KEY não configurada" in message:
                message = "A última execução foi feita sem chave. Rode um cenário novo para registrar Gemini no histórico."
            if configured and message == "sem falha de qualidade":
                message = "A última execução não tinha incidente, então Gemini não foi acionado."
            st.caption(message)


def _render_history_table(history_df: pd.DataFrame) -> None:
    with st.container(border=True):
        _panel_title("Histórico recente", "últimas execuções")
        if history_df.empty:
            st.info("Nenhuma execução encontrada.")
            return

        table = history_df[
            [
                "run_id",
                "cenário",
                "falhas",
                "gravidade",
                "motor",
                "llm_api",
                "revisão_manual",
                "resumo",
            ]
        ]
        st.dataframe(table, use_container_width=True, hide_index=True, height=315)


def _render_run_panel(scenarios: dict | None) -> None:
    with st.container(border=True):
        _panel_title("Nova execução", "rodar um cenário")
        scenario_items = scenarios.get("cenarios", []) if scenarios else []
        if not scenario_items:
            st.error("Nenhum cenário disponível.")
            return

        scenario_names = [item["nome"] for item in scenario_items]
        descriptions = {item["nome"]: item["descricao"] for item in scenario_items}

        selected = st.selectbox("Cenário", scenario_names, index=_default_scenario_index(scenario_names))
        st.caption(descriptions.get(selected, ""))

        if st.button("Executar pipeline", type="primary", use_container_width=True):
            with st.spinner("Executando pipeline..."):
                response = _post_json("/execucoes", {"scenario": selected})

            if not response:
                st.error("Não foi possível executar a pipeline.")
                return

            st.success(f"Execução finalizada: {response['run_id']}")
            _render_run_result(response)


def _render_run_result(response: dict) -> None:
    provider = response.get("provedor_llm") or "local"
    badge_class = "status-ok" if provider == "gemini" else "status-warn"
    badge_text = "Gemini" if provider == "gemini" else "local"
    fallback = response.get("motivo_fallback") or ""
    if fallback == "sem falha de qualidade":
        fallback = "Sem incidente: Gemini não foi acionado nesta execução."

    st.markdown(
        f"""
        <div class="run-result">
            <div>
                <span>resultado</span>
                <strong>{_safe(response.get("cenario", ""))}</strong>
            </div>
            <small class="{badge_class}">{badge_text}</small>
        </div>
        <div class="detail-list compact">
            <span>gravidade</span><b>{_safe(response.get("gravidade", ""))}</b>
            <span>falhas</span><b>{_safe(response.get("validacoes_com_falha", ""))}</b>
            <span>modelo</span><b>{_safe(response.get("modelo_llm") or "não acionado")}</b>
            <span>api</span><b>{_safe(response.get("api_llm") or "regras locais")}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if fallback:
        st.caption(fallback)


def _metric_card(title: str, value: str, detail: str, healthy: bool) -> None:
    badge_class = "status-ok" if healthy else "status-warn"
    st.markdown(
        f"""
        <div class="metric-card">
            <span>{_safe(title)}</span>
            <strong>{_safe(value)}</strong>
            <small class="{badge_class}">{_safe(detail)}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _default_scenario_index(scenario_names: list[str]) -> int:
    if "tipo_invalido" in scenario_names:
        return scenario_names.index("tipo_invalido")
    return 0


def _panel_title(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="panel-title">
            <h2>{_safe(title)}</h2>
            <span>{_safe(subtitle)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _chart_style(chart: alt.Chart, height: int) -> alt.Chart:
    return (
        chart.properties(height=height)
        .configure_axis(labelColor="#64748b", titleColor="#475569", gridColor="#eef2f7")
        .configure_view(strokeWidth=0)
        .configure(background="transparent")
    )


def _detail_rows(items: dict[str, object]) -> str:
    rows = []
    for label, value in items.items():
        rows.append(f"<span>{_safe(label)}</span><b>{_safe(value)}</b>")
    return "".join(rows)


def _history_records(history: dict | None) -> list[dict]:
    return history.get("historico", []) if history else []


def _history_dataframe(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records).copy()
    # Normalizo aqui para o dashboard não depender dos nomes crus da API.
    df["ordem"] = range(len(df), 0, -1)
    df["cenário"] = df["scenario"]
    df["falhas"] = df["failed_checks"].astype(int)
    df["gravidade"] = df["severity"].map(_severity_label)
    df["motor"] = df["diagnosis_engine"].str.replace("_", " ", regex=False)
    df["revisão_manual"] = df["requires_manual_review"].map(lambda value: "sim" if value else "não")
    df["resumo"] = df["summary"]
    df["llm_provider"] = _optional_column(df, "llm_provider")
    df["llm_model"] = _optional_column(df, "llm_model")
    df["llm_api"] = _optional_column(df, "llm_api")
    df["llm_interaction_id"] = _optional_column(df, "llm_interaction_id")
    df["llm_response_format"] = _optional_column(df, "llm_response_format")
    df["llm_tool_names"] = _optional_column(df, "llm_tool_names")
    df["llm_tool_calls"] = _optional_column(df, "llm_tool_calls")
    df["llm_fallback_reason"] = _optional_column(df, "llm_fallback_reason")
    return df


def _severity_label(value: str) -> str:
    return SEVERITY_LABELS.get(str(value), str(value))


def _optional_column(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df:
        return df[name].fillna("")
    return pd.Series([""] * len(df), index=df.index)


def _get_json(path: str) -> dict | None:
    try:
        response = requests.get(f"{API_URL}{path}", timeout=10)
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


def _apply_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #f6f7fb;
            --card: #ffffff;
            --ink: #0f172a;
            --muted: #64748b;
            --line: #e5e7eb;
            --blue: #2563eb;
            --blue-soft: #eff6ff;
            --gemini-blue: #1a73e8;
            --gemini-green: #188038;
            --green: #15803d;
            --green-soft: #dcfce7;
            --amber: #b45309;
            --amber-soft: #fef3c7;
        }

        .stApp {
            background: var(--bg);
            color: var(--ink);
            font-family: "Aptos", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
        }

        .main .block-container {
            max-width: 1360px;
            padding-top: 1rem;
            padding-bottom: 2rem;
        }

        header[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"] {
            display: none;
        }

        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.7rem;
        }

        .brand-mark {
            display: inline-grid;
            place-items: center;
            width: 36px;
            height: 36px;
            border-radius: 8px;
            background: var(--ink);
            color: white;
            font-size: 0.76rem;
            font-weight: 700;
        }

        .brand strong {
            display: block;
            color: var(--ink);
            font-size: 0.98rem;
            line-height: 1.1;
        }

        .brand small {
            color: var(--muted);
            font-size: 0.78rem;
        }

        .topbar nav {
            display: flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.32rem;
            border: 1px solid var(--line);
            border-radius: 999px;
            background: var(--card);
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
        }

        .topbar nav span,
        .topbar nav a {
            border-radius: 999px;
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 600;
            padding: 0.42rem 0.78rem;
            text-decoration: none;
            white-space: nowrap;
        }

        .topbar nav .active {
            background: var(--ink);
            color: white;
        }

        .hero {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 1rem;
            margin-bottom: 1rem;
            padding: 1.15rem 1.25rem;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--card);
            box-shadow: 0 14px 40px rgba(15, 23, 42, 0.05);
        }

        .hero p {
            color: var(--blue);
            font-size: 0.78rem;
            font-weight: 700;
            margin: 0 0 0.35rem 0;
        }

        .hero h1 {
            color: var(--ink);
            font-size: 2rem;
            font-weight: 720;
            letter-spacing: 0;
            line-height: 1.05;
            margin: 0;
        }

        .hero-meta {
            display: flex;
            gap: 0.45rem;
            flex-wrap: wrap;
            justify-content: flex-end;
        }

        .hero-meta span,
        .status-ok,
        .status-warn {
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 700;
            padding: 0.32rem 0.62rem;
            white-space: nowrap;
        }

        .hero-meta span {
            background: var(--blue-soft);
            color: var(--blue);
        }

        .hero-meta .gemini-pill {
            background: linear-gradient(135deg, #e8f0fe, #e6f4ea);
            color: var(--gemini-blue);
        }

        .metric-card {
            min-height: 118px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--card);
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
            padding: 1rem;
        }

        .metric-card span {
            color: var(--muted);
            display: block;
            font-size: 0.8rem;
            font-weight: 700;
        }

        .metric-card strong {
            color: var(--ink);
            display: block;
            font-size: 1.9rem;
            font-weight: 720;
            line-height: 1.1;
            margin: 0.45rem 0 0.7rem;
        }

        .status-ok {
            background: var(--green-soft);
            color: var(--green);
        }

        .status-warn {
            background: var(--amber-soft);
            color: var(--amber);
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
        }

        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 0.7rem 0.85rem 0.85rem;
        }

        .panel-title {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 0.55rem;
        }

        .panel-title h2 {
            color: var(--ink);
            font-size: 1rem;
            font-weight: 720;
            line-height: 1.2;
            margin: 0;
        }

        .panel-title span {
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 600;
            white-space: nowrap;
        }

        .gemini-summary {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.75rem;
            padding: 0.1rem 0 0.85rem;
        }

        .run-result {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.75rem;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #f8fafc;
            margin-top: 0.85rem;
            padding: 0.8rem;
        }

        .run-result span {
            color: var(--muted);
            display: block;
            font-size: 0.74rem;
            font-weight: 700;
        }

        .run-result strong {
            color: var(--ink);
            display: block;
            font-size: 1.1rem;
            font-weight: 760;
            line-height: 1.15;
            margin-top: 0.2rem;
        }

        .gemini-brand {
            position: relative;
            border: 1px solid #dbeafe;
            border-radius: 8px;
            background: linear-gradient(135deg, #eff6ff 0%, #ffffff 56%, #ecfdf3 100%);
            margin-bottom: 0.8rem;
            padding: 0.95rem;
        }

        .gemini-brand span {
            color: var(--gemini-blue);
            display: block;
            font-size: 0.75rem;
            font-weight: 800;
            margin-bottom: 0.1rem;
        }

        .gemini-brand strong {
            color: var(--ink);
            display: block;
            font-size: 2.15rem;
            font-weight: 780;
            letter-spacing: 0;
            line-height: 1;
        }

        .gemini-brand small {
            position: absolute;
            right: 0.85rem;
            top: 0.85rem;
        }

        .gemini-summary span,
        .detail-list span {
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 650;
        }

        .gemini-summary strong {
            color: var(--ink);
            display: block;
            font-size: 1.8rem;
            font-weight: 720;
            line-height: 1.05;
            margin-top: 0.2rem;
        }

        .detail-list {
            display: grid;
            grid-template-columns: 76px minmax(0, 1fr);
            gap: 0.45rem 0.8rem;
            border-top: 1px solid var(--line);
            padding-top: 0.75rem;
        }

        .detail-list.compact {
            border-top: 0;
            padding: 0.75rem 0 0;
        }

        .detail-list b {
            color: var(--ink);
            font-size: 0.8rem;
            font-weight: 650;
            overflow-wrap: anywhere;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
        }

        .stSelectbox label,
        .stCaptionContainer {
            color: var(--muted) !important;
            font-size: 0.82rem;
        }

        div[data-baseweb="select"] > div {
            background: #f8fafc;
            border-color: var(--line);
            color: var(--ink);
        }

        .stButton button {
            border-radius: 8px;
            border: 1px solid var(--blue);
            background: var(--blue);
            color: white;
            font-weight: 700;
        }

        .stButton button:hover {
            border-color: #1d4ed8;
            background: #1d4ed8;
            color: white;
        }

        .stAlert {
            border-radius: 8px;
        }

        @media (max-width: 820px) {
            .topbar,
            .hero {
                align-items: flex-start;
                flex-direction: column;
            }

            .topbar nav {
                flex-wrap: wrap;
            }

            .hero h1 {
                font-size: 1.55rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
