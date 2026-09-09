from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st

from dashboard.components.collaboration_view import render_collaboration_panel
from dashboard.components.icons import (
    icon_box,
    icon_cpu,
    icon_database,
    icon_shield_check,
)
from dashboard.components.incidents import _load_run_diagnosis


def render_overview_tab(status: dict | None, history_df: pd.DataFrame, db_row_count: int = 0) -> None:
    """Renderiza a visão geral com KPIs, taxa de conformidade e timeline."""
    total_runs = len(history_df)
    clean_runs = int((history_df["falhas"] == 0).sum()) if not history_df.empty else 0
    pass_rate = (clean_runs / total_runs * 100) if total_runs > 0 else 100.0

    quarantined_count = 0
    if not history_df.empty and "quarentena" in history_df:
        quarantined_count = int(history_df["quarentena"].str.contains("sim", case=False).sum())

    manual_reviews = int((history_df["revisão_manual"] == "sim").sum()) if not history_df.empty else 0
    automated_rate = (
        ((total_runs - manual_reviews) / total_runs * 100) if total_runs > 0 else 100.0
    )

    # kpis operacionais do topo
    c1, c2, c3, c4 = st.columns(4, gap="medium")


    with c1:
        health_color = "#059669" if pass_rate >= 80 else "#E11D48"
        health_label = "CONFORME" if pass_rate >= 80 else "ATENÇÃO"
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Health Check</span>
                    <span class="mini-tag tag-blue">{icon_shield_check(13, health_color)} CONTRATOS</span>
                </div>
                <div class="mini-metric">{pass_rate:.0f}<small>%</small></div>
                <div class="mini-foot">Status: <b style="color: {health_color};">{health_label}</b> ({clean_runs}/{total_runs})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        dlq_color = "#E11D48" if quarantined_count > 0 else "#059669"
        dlq_tag_cls = "tag-cyan" if quarantined_count > 0 else "tag-blue"
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Quarentena</span>
                    <span class="mini-tag {dlq_tag_cls}">{icon_box(13, dlq_color)} PROTEÇÃO</span>
                </div>
                <div class="mini-metric">{quarantined_count} <small>lotes</small></div>
                <div class="mini-foot">Isolados da base: <b style="color: {dlq_color};">{quarantined_count} retidos</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Base de produção</span>
                    <span class="mini-tag tag-blue">{icon_database(13, "#475569")} DATABASE</span>
                </div>
                <div class="mini-metric">{db_row_count} <small>linhas</small></div>
                <div class="mini-foot">Série ativa: <b>BCB SGS 11 (Selic)</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Autonomia dos Agentes</span>
                    <span class="mini-tag tag-cyan">{icon_cpu(13, "#D59B88")} AI RES</span>
                </div>
                <div class="mini-metric">{automated_rate:.0f}<small>%</small></div>
                <div class="mini-foot">Revisão manual: <b>{manual_reviews} casos</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="spacing-gap-md"></div>', unsafe_allow_html=True)

    # Destaque de Governança: Consenso Multiagente da Execução Mais Recente
    if not history_df.empty:
        latest_row = history_df.iloc[0]
        latest_run_id = str(latest_row.get("run_id", ""))
        curated_dir = Path(__file__).resolve().parents[2] / "data" / "curated"
        latest_diag = _load_run_diagnosis(latest_run_id, curated_dir)
        latest_collab = latest_diag.get("collaboration", {}) if latest_diag else {}
        if not latest_collab and latest_row.get("collaboration_summary"):
            latest_collab = {
                "status": latest_row.get("collaboration_status"),
                "supervisor_decision": latest_row.get("collaboration_summary"),
            }
        render_collaboration_panel(
            latest_collab,
            run_id=latest_run_id,
            title="Governança Ativa: Debate e Consenso Multiagente (Última Execução)",
        )

    # timeline de execucoes e distribuicao das falhas
    col_timeline, col_pareto = st.columns([0.58, 0.42], gap="medium")


    with col_timeline:
        with st.container(border=True):
            st.markdown(
                """
                <div class="telemetry-top">
                    <div>
                        <span class="card-kicker">HISTÓRICO OPERACIONAL</span>
                        <h3 class="telemetry-title">Linha do tempo das execuções</h3>
                    </div>
                    <span class="live-pill"><span class="pulse-spark"></span> ATIVO</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if history_df.empty:
                st.info("Nenhuma execução registrada para exibir a linha do tempo.")
            else:
                chart_df = history_df.sort_values("ordem").tail(20).copy()
                chart_df["idx"] = range(1, len(chart_df) + 1)
                chart_df["run_label"] = [f"#{row.get('run_id', '')[:8]}" for _, row in chart_df.iterrows()]
                chart_df["status_cor"] = [
                    "Isolado na DLQ" if "sim" in str(q).lower() else "Carga Aprovada"
                    for q in chart_df.get("quarentena", [])
                ]
                chart_df["linhas"] = chart_df.get("rows_checked", [22] * len(chart_df))

                bars = (
                    alt.Chart(chart_df)
                    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=16)
                    .encode(
                        x=alt.X(
                            "run_label:O",
                            title="Execuções (mais antigas → mais recentes)",
                            axis=alt.Axis(labelColor="#64748B", labelAngle=-45, titleColor="#0F172A", labelFontSize=11),
                        ),
                        y=alt.Y(
                            "linhas:Q",
                            title="Linhas Avaliadas",
                            axis=alt.Axis(labelColor="#64748B", titleColor="#0F172A", gridColor="#F1F5F9"),
                        ),
                        color=alt.Color(
                            "status_cor:N",
                            scale=alt.Scale(
                                domain=["Carga Aprovada", "Isolado na DLQ"],
                                range=["#059669", "#E11D48"],
                            ),
                            legend=alt.Legend(title="Status do Lote", orient="top", labelColor="#334155", titleColor="#0F172A"),
                        ),
                        tooltip=[
                            alt.Tooltip("run_id:N", title="Run ID"),
                            alt.Tooltip("cenário:N", title="Cenário"),
                            alt.Tooltip("falhas:Q", title="Falhas"),
                            alt.Tooltip("gravidade:N", title="Gravidade"),
                            alt.Tooltip("quarentena:N", title="Quarentenado"),
                        ],
                    )
                    .properties(height=240)
                    .configure_view(strokeWidth=0)
                    .configure(background="transparent")
                )
                st.altair_chart(bars, use_container_width=True)

    with col_pareto:
        with st.container(border=True):
            st.markdown(
                """
                <div class="telemetry-top">
                    <div>
                        <span class="card-kicker">GOVERNANÇA & INCIDENTES</span>
                        <h3 class="telemetry-title">Visão geral de falhas</h3>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Contagem de quebras por categoria a partir do histórico
            pareto_data = _build_pareto_data(history_df)
            if pareto_data.empty or pareto_data["ocorrencias"].sum() == 0:
                st.info("Nenhuma falha de contrato registrada até o momento.")
            else:
                pareto_chart = (
                    alt.Chart(pareto_data)
                    .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, height=18)
                    .encode(
                        y=alt.Y(
                            "regra:N",
                            sort="-x",
                            title=None,
                            axis=alt.Axis(labelColor="#334155", labelFontSize=11),
                        ),
                        x=alt.X(
                            "ocorrencias:Q",
                            title="Frequência de Violação",
                            axis=alt.Axis(labelColor="#64748B", titleColor="#0F172A", tickMinStep=1, gridColor="#F1F5F9"),
                        ),
                        color=alt.Color(
                            "ocorrencias:Q",
                            scale=alt.Scale(range=["#F3DDD7", "#D59B88"]),
                            legend=None,
                        ),
                        tooltip=[alt.Tooltip("regra:N", title="Regra"), alt.Tooltip("ocorrencias:Q", title="Incidentes")],
                    )
                    .properties(height=240)
                    .configure_view(strokeWidth=0)
                    .configure(background="transparent")
                )
                st.altair_chart(pareto_chart, use_container_width=True)


def _build_pareto_data(history_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates violation frequencies based on scenarios and failures in history."""
    if history_df.empty:
        return pd.DataFrame(columns=["regra", "ocorrencias"])

    counts = {
        "Valores Nulos (check_nulls)": 0,
        "Schema Drift (check_schema)": 0,
        "Tipo Inválido (check_types)": 0,
        "Duplicatas (check_duplicates)": 0,
        "Timeout de API (fallback)": 0,
        "Outros Incidentes": 0,
    }

    for _, row in history_df.iterrows():
        scen = str(row.get("cenário", "")).lower()
        fails = int(row.get("falhas", 0))
        if fails > 0 or "timeout" in scen:
            if "nulo" in scen:
                counts["Valores Nulos (check_nulls)"] += 1
            elif "estrutura" in scen or "schema" in scen:
                counts["Schema Drift (check_schema)"] += 1
            elif "tipo" in scen:
                counts["Tipo Inválido (check_types)"] += 1
            elif "duplicado" in scen:
                counts["Duplicatas (check_duplicates)"] += 1
            elif "timeout" in scen:
                counts["Timeout de API (fallback)"] += 1
            else:
                counts["Outros Incidentes"] += 1

    df = pd.DataFrame(list(counts.items()), columns=["regra", "ocorrencias"])
    return df[df["ocorrencias"] > 0]
