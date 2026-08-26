from __future__ import annotations

import html
import os
import textwrap

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

# Acento único do tema: azul puro, a pedido. Tudo que precisa de uma
# variação suave (fundos de badge, hover) deriva dele via rgba, nunca
# de um tom "azulado" diferente.
ACCENT = "#0000FF"
ACCENT_SOFT = "rgba(0, 0, 255, 0.12)"
ACCENT_LINE = "rgba(0, 0, 255, 0.45)"

st.set_page_config(page_title="DataOps AI", page_icon="D.AI", layout="wide")


def main() -> None:
    _apply_style()

    status = _get_json("/status")
    history = _get_json("/historico?limit=30")
    scenarios = _get_json("/cenarios")

    history_df = _history_dataframe(_history_records(history))

    _render_masthead(status, history_df)

    side, main_col = st.columns([0.32, 0.68], gap="large")
    with side:
        _render_kpi_side(status, history_df)
    with main_col:
        _render_trend_figure(history_df)
        _render_scenario_figure(history_df)

    st.markdown('<hr class="c-divider">', unsafe_allow_html=True)

    box_a, box_b, box_c = st.columns(3, gap="large")
    with box_a:
        _render_gemini_box(status, history_df)
    with box_b:
        _render_last_run_box(history_df)
    with box_c:
        _render_run_box(scenarios)

    with st.expander("Ver histórico completo"):
        _render_history_table(history_df)


def _render_masthead(status: dict | None, history_df: pd.DataFrame) -> None:
    database = status.get("banco", {}) if status else {}
    bcb_api = status.get("api_banco_central", {}) if status else {}

    total_runs = len(history_df)
    failed_runs = int((history_df["falhas"] > 0).sum()) if not history_df.empty else 0

    db_ok = bool(database.get("conectado"))
    api_ok = bool(bcb_api.get("available"))

    if total_runs == 0:
        headline = "Ainda sem execuções registradas. Rode um cenário para começar o boletim."
    elif not db_ok or not api_ok:
        headline = "Uma dependência externa está fora do ar — verifique banco e API do Banco Central antes de confiar nas próximas execuções."
    elif failed_runs == 0:
        headline = f"Todas as últimas {total_runs} execuções passaram sem incidente; o motor local resolveu sozinho, sem acionar o Gemini."
    else:
        headline = (
            f"API do Banco Central está estável\n"
            f"São necessárias verificações manuais em {failed_runs} das últimas {total_runs} execuções."
        )

    st.markdown(
        f"""
        <div class="c-kicker">Boletim de saúde do fluxo · Core V1</div>
        <h1 class="c-h1">{_safe(headline)}</h1>
        <p class="c-flow">API BCB <span>→</span> PostgreSQL <span>→</span> Agente de qualidade <span>→</span> Diagnóstico Gemini</p>
        """,
        unsafe_allow_html=True,
    )


def _render_kpi_side(status: dict | None, history_df: pd.DataFrame) -> None:
    database = status.get("banco", {}) if status else {}
    bcb_api = status.get("api_banco_central", {}) if status else {}

    total_runs = len(history_df)
    failed_runs = int((history_df["falhas"] > 0).sum()) if not history_df.empty else 0
    manual_review = int((history_df["revisão_manual"] == "sim").sum()) if not history_df.empty else 0

    db_value = "online" if database.get("conectado") else "falhou"
    api_value = "online" if bcb_api.get("available") else "falhou"
    api_detail = f"HTTP {bcb_api.get('status_code')}" if bcb_api.get("status_code") else "sem resposta"

    rows = [
        ("Banco", db_value, database.get("tipo") or "PostgreSQL"),
        ("Banco Central", api_value, api_detail),
        ("Execuções", str(total_runs), f"{failed_runs} com falha"),
        ("Revisão manual", str(manual_review), "últimos registros"),
    ]

    items = "".join(
        f"""
        <dt>{_safe(label)}</dt>
        <dd>{_safe(value)} <small>{_safe(detail)}</small></dd>
        """
        for label, value, detail in rows
    )

    quote = "Sem incidente, o Gemini não é acionado — o motor local resolve sozinho."
    if not history_df.empty:
        latest = history_df.iloc[0]
        fallback = latest.get("llm_fallback_reason")
        if fallback and str(fallback) != "sem falha de qualidade":
            quote = str(fallback)

    st.markdown(
        f"""
        <dl class="c-dl">{items}</dl>
        <div class="c-quote">“{_safe(quote)}”</div>
        """,
        unsafe_allow_html=True,
    )


def _render_trend_figure(history_df: pd.DataFrame) -> None:
    st.markdown(
        """
        <h3 class="c-fig-title">Figura 1 — Falhas por execução</h3>
        <div class="c-fig-cap">Série das últimas 12 execuções registradas no histórico</div>
        """,
        unsafe_allow_html=True,
    )
    if history_df.empty:
        st.info("Sem histórico para exibir.")
        return

    chart_df = history_df.sort_values("ordem").tail(12).copy()
    chart_df["execução"] = range(1, len(chart_df) + 1)

    base = alt.Chart(chart_df).encode(
        x=alt.X("execução:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("falhas:Q", title=None, scale=alt.Scale(domainMin=0)),
        tooltip=["run_id", "cenário", "falhas", "gravidade"],
    )
    chart = base.mark_line(color=ACCENT, strokeWidth=2) + base.mark_point(
        color=ACCENT, size=40
    )
    st.altair_chart(_chart_style(chart, height=170), use_container_width=True)
    st.markdown(
        '<div class="c-fig-foot">eixo x: execuções mais recentes → mais antigas · eixo y: nº de falhas</div>',
        unsafe_allow_html=True,
    )


def _render_scenario_figure(history_df: pd.DataFrame) -> None:
    st.markdown(
        """
        <h3 class="c-fig-title" style="margin-top:2.2rem;">Figura 2 — Incidentes por cenário</h3>
        <div class="c-fig-cap">Distribuição acumulada do histórico</div>
        """,
        unsafe_allow_html=True,
    )
    if history_df.empty:
        st.info("Sem histórico para exibir.")
        return

    chart_df = history_df["cenário"].value_counts().rename_axis("cenário").reset_index(name="execuções")
    chart = (
        alt.Chart(chart_df)
        .mark_bar(color=ACCENT, opacity=0.88)
        .encode(
            x=alt.X("cenário:N", title=None, sort="-y", axis=alt.Axis(labelAngle=-20)),
            y=alt.Y("execuções:Q", title=None, scale=alt.Scale(domainMin=0)),
            tooltip=["cenário", "execuções"],
        )
    )
    st.altair_chart(_chart_style(chart, height=150), use_container_width=True)


def _render_gemini_box(status: dict | None, history_df: pd.DataFrame) -> None:
    gemini_status = status.get("gemini", {}) if status else {}
    configured = bool(gemini_status.get("configurado"))
    current_model = gemini_status.get("modelo") or "não informado"

    latest = history_df.iloc[0] if not history_df.empty else pd.Series(dtype=object)
    items = {
        "modelo": latest.get("llm_model") or current_model,
        "api": latest.get("llm_api") or "regras locais",
        "formato": latest.get("llm_response_format") or "sem schema",
        "interação": latest.get("llm_interaction_id") or "não armazenada",
    }
    st.markdown(
        f"""
        <div class="c-box">
            <div class="c-box-n">Modelo utilizado</div>
            <h4>{_safe(current_model if configured else "sem chave configurada")}</h4>
            {_kv_rows(items)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_last_run_box(history_df: pd.DataFrame) -> None:
    if history_df.empty:
        st.markdown(
            """
            <div class="c-box">
                <div class="c-box-n">Última execução</div>
                <h4>nenhuma ainda</h4>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    latest = history_df.iloc[0]
    items = {
        "falhas": latest.get("falhas"),
        "gravidade": latest.get("gravidade"),
        "revisão": latest.get("revisão_manual"),
    }
    st.markdown(
        f"""
        <div class="c-box">
            <div class="c-box-n">Última execução</div>
            <h4>{_safe(latest.get("run_id"))} · {_safe(latest.get("cenário"))}</h4>
            {_kv_rows(items)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_run_box(scenarios: dict | None) -> None:
    st.markdown(
        """
        <div class="c-box">
            <div class="c-box-n">Nova execução</div>
            <h4>Rodar cenário</h4>
        </div>
        """,
        unsafe_allow_html=True,
    )
    scenario_items = scenarios.get("cenarios", []) if scenarios else []
    if not scenario_items:
        st.error("Nenhum cenário disponível.")
        return

    scenario_names = [item["nome"] for item in scenario_items]
    descriptions = {item["nome"]: item["descricao"] for item in scenario_items}

    selected = st.selectbox(
        "Cenário", scenario_names, index=_default_scenario_index(scenario_names), label_visibility="collapsed"
    )
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
    fallback = response.get("motivo_fallback") or ""
    if fallback == "sem falha de qualidade":
        fallback = "Sem incidente: Gemini não foi acionado nesta execução."

    items = {
        "gravidade": response.get("gravidade", ""),
        "falhas": response.get("validacoes_com_falha", ""),
        "modelo": response.get("modelo_llm") or "não acionado",
        "api": response.get("api_llm") or "regras locais",
        "provedor": provider,
    }
    st.markdown(f'<div class="c-kv2-block">{_kv_rows(items)}</div>', unsafe_allow_html=True)
    if fallback:
        st.caption(fallback)


def _render_history_table(history_df: pd.DataFrame) -> None:
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
    st.dataframe(table, use_container_width=True, hide_index=True, height=340)


def _kv_rows(items: dict[str, object]) -> str:
    rows = []
    for label, value in items.items():
        rows.append(f'<div class="c-kv2"><span>{_safe(label)}</span><b>{_safe(value)}</b></div>')
    return "".join(rows)


def _default_scenario_index(scenario_names: list[str]) -> int:
    if "tipo_invalido" in scenario_names:
        return scenario_names.index("tipo_invalido")
    return 0


def _chart_style(chart: alt.Chart, height: int) -> alt.Chart:
    return (
        chart.properties(height=height)
        .configure_axis(labelColor="#8a7f6f", titleColor="#c9bfae", gridColor="#241f18", domainColor="#332c22")
        .configure_view(strokeWidth=0)
        .configure(background="transparent")
    )


def _history_records(history: dict | None) -> list[dict]:
    return history.get("historico", []) if history else []


def _history_dataframe(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records).copy()
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
    css = """
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    :root {
        --bg: #15120E;
        --ink: #f2ede6;
        --muted: #8a7f6f;
        --muted2: #c9bfae;
        --line: #332c22;
        --accent: ACCENT_PLACEHOLDER;
        --accent-soft: ACCENT_SOFT_PLACEHOLDER;
        --accent-line: ACCENT_LINE_PLACEHOLDER;
    }

    .stApp {
        background: var(--bg);
        color: var(--ink);
        font-family: "Inter", system-ui, sans-serif;
    }

    .main .block-container {
        max-width: 1120px;
        padding-top: 3rem;
        padding-bottom: 3rem;
    }

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        display: none;
    }

    .c-kicker {
        font-family: "IBM Plex Mono", monospace;
        font-weight: 600;
        font-size: 0.7rem;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--accent);
        margin: 0 0 0.6rem;
    }

    .c-h1 {
        font-family: "Fraunces", serif;
        font-weight: 500;
        font-size: 2.35rem;
        line-height: 1.1;
        color: var(--ink);
        margin: 0 0 1rem;
        max-width: 46rem;
        letter-spacing: -0.01em;
    }

    .c-flow {
        font-size: 0.85rem;
        color: var(--muted);
        border-top: 1px solid var(--line);
        padding-top: 1.4rem;
        margin: 0 0 0.5rem;
    }
    .c-flow span { color: var(--accent); padding: 0 0.3rem; }

    .c-dl dt {
        font-family: "IBM Plex Mono", monospace;
        font-weight: 600;
        font-size: 0.7rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 0.15rem;
    }
    .c-dl dd {
        margin: 0 0 1.15rem;
        font-size: 1rem;
        color: var(--ink);
        font-weight: 500;
    }
    .c-dl dd small {
        display: block;
        font-family: "Inter", sans-serif;
        font-weight: 400;
        font-size: 0.72rem;
        color: var(--muted);
        margin-top: 0.15rem;
    }

    .c-quote {
        font-family: "Fraunces", serif;
        font-style: italic;
        font-size: 0.86rem;
        color: var(--muted2);
        border-left: 2px solid var(--accent);
        padding-left: 0.75rem;
        margin-top: 0.6rem;
    }

    .c-fig-title {
        font-family: "Fraunces", serif;
        font-weight: 500;
        font-size: 1.1rem;
        color: var(--ink);
        margin: 0 0 0.2rem;
    }
    .c-fig-cap {
        font-size: 0.76rem;
        color: var(--muted);
        font-style: italic;
        margin-bottom: 0.8rem;
    }
    .c-fig-foot {
        font-size: 0.7rem;
        color: var(--muted);
        margin-top: 0.2rem;
    }

    .c-divider {
        border: 0;
        border-top: 1px solid var(--line);
        margin: 2.2rem 0;
    }

    .c-box-n {
        font-family: "IBM Plex Mono", monospace;
        font-weight: 600;
        font-size: 0.7rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--accent);
        margin-bottom: 0.5rem;
    }
    .c-box h4 {
        font-family: "Fraunces", serif;
        font-weight: 500;
        font-size: 1.05rem;
        color: var(--ink);
        margin: 0 0 0.7rem;
    }

    .c-kv2, .c-kv2-block .c-kv2 {
        font-size: 0.8rem;
        color: var(--muted2);
        display: flex;
        justify-content: space-between;
        gap: 0.75rem;
        border-bottom: 1px dotted var(--line);
        padding: 0.4rem 0;
    }
    .c-kv2 b {
        color: var(--ink);
        font-weight: 500;
        text-align: right;
        overflow-wrap: anywhere;
    }

    /* Selects, botoes, tabela, expander e alerts do Streamlit no tema */
    div[data-baseweb="select"] > div {
        background: transparent;
        border-color: var(--line);
        color: var(--ink);
        border-radius: 3px;
    }
    .stButton button {
        border-radius: 3px;
        border: 1px solid var(--accent);
        background: transparent;
        color: var(--accent);
        font-weight: 600;
    }
    .stButton button:hover {
        background: var(--accent-soft);
        border-color: var(--accent);
        color: var(--ink);
    }
    .stCaptionContainer, .stSelectbox label {
        color: var(--muted) !important;
        font-size: 0.78rem;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 4px;
        overflow: hidden;
    }
    div[data-testid="stExpander"] {
        border: 1px solid var(--line);
        border-radius: 4px;
    }
    .stAlert {
        background: var(--accent-soft);
        border: 1px solid var(--accent-line);
        border-radius: 4px;
        color: var(--ink);
    }
    """
    css = (
        css.replace("ACCENT_PLACEHOLDER", ACCENT)
        .replace("ACCENT_SOFT_PLACEHOLDER", ACCENT_SOFT)
        .replace("ACCENT_LINE_PLACEHOLDER", ACCENT_LINE)
    )
    st.markdown(f"<style>\n{textwrap.dedent(css)}\n</style>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()