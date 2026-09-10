from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from dashboard.components.icons import icon_activity, icon_database
from dataops_ai.tools.database_tools import DatabaseClient


def render_data_viewer_tab(database_url: str) -> None:
    """Renderiza a visualização dos dados homologados na camada Gold."""
    df = _load_gold_data(database_url)

    if df.empty:
        st.info("A tabela oficial 'bcb_timeseries' ainda não possui registros homologados ou o banco está inacessível.")
        return

    total_rows = len(df)
    min_date = df["date"].min().strftime("%d/%m/%Y")
    max_date = df["date"].max().strftime("%d/%m/%Y")
    mean_val = float(df["value"].mean())
    min_val = float(df["value"].min())
    max_val = float(df["value"].max())

    # estatisticas descritivas da serie
    c1, c2, c3, c4 = st.columns(4, gap="medium")


    with c1:
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Registros Homologados</span>
                    <span>{icon_database(14, "#71717A")}</span>
                </div>
                <div class="mini-metric">{total_rows} <small>linhas</small></div>
                <div class="mini-foot">Tabela: <code>bcb_timeseries</code></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Período Homologado</span>
                    <span>{icon_activity(14, "#71717A")}</span>
                </div>
                <div class="mini-metric" style="font-size: 1.15rem; line-height: 2.2;">{min_date} → {max_date}</div>
                <div class="mini-foot">Série: <b>BCB SGS 11 (Selic)</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Valor Médio da Taxa</span>
                </div>
                <div class="mini-metric">{mean_val:.4f}<small>% a.d.</small></div>
                <div class="mini-foot">Média da amostra homologada</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Intervalo da Série</span>
                </div>
                <div class="mini-metric" style="font-size: 1.25rem; line-height: 2.1;">{min_val:.4f} ~ {max_val:.4f}</div>
                <div class="mini-foot">Mínimo e máximo observados</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="spacing-gap-md"></div>', unsafe_allow_html=True)

    # grafico de linha da serie temporal
    with st.container(border=True):
        st.markdown(
            """
            <div class="telemetry-top">
                <div>
                    <span class="card-kicker">SÉRIE TEMPORAL</span>
                    <h3 class="telemetry-title">Curva Histórica da Taxa Selic</h3>
                </div>
                <span class="live-pill"><span class="pulse-spark"></span> CONFORME</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        chart_df = df.sort_values("date").copy()
        chart_df["data_formatada"] = chart_df["date"].dt.strftime("%d/%m/%Y")

        line = (
            alt.Chart(chart_df)
            .mark_line(color="#818CF8", strokeWidth=2.2, interpolate="monotone")
            .encode(
                x=alt.X(
                    "data_formatada:O",
                    title="Data de Fechamento",
                    axis=alt.Axis(labelColor="#A1A1AA", labelAngle=-45, titleColor="#FAFAFA"),
                ),
                y=alt.Y(
                    "value:Q",
                    title="Taxa Selic Diária (%)",
                    scale=alt.Scale(zero=False),
                    axis=alt.Axis(labelColor="#A1A1AA", titleColor="#FAFAFA", gridColor="#27272A"),
                ),
                tooltip=[
                    alt.Tooltip("data_formatada:N", title="Data"),
                    alt.Tooltip("value:Q", title="Taxa (%)", format=".5f"),
                    alt.Tooltip("source:N", title="Origem"),
                ],
            )
        )

        points = (
            alt.Chart(chart_df)
            .mark_circle(color="#09090B", size=42, stroke="#818CF8", strokeWidth=2)
            .encode(
                x=alt.X("data_formatada:O"),
                y=alt.Y("value:Q"),
                tooltip=[
                    alt.Tooltip("data_formatada:N", title="Data"),
                    alt.Tooltip("value:Q", title="Taxa (%)", format=".5f"),
                ],
            )
        )

        final_chart = (line + points).properties(height=230).configure_view(strokeWidth=0).configure(background="transparent")
        st.altair_chart(final_chart, use_container_width=True)

    st.markdown('<div class="spacing-gap-md"></div>', unsafe_allow_html=True)

    # visualizacao tabular dos registros
    with st.container(border=True):
        st.markdown(
            """
            <div class="telemetry-top">
                <div>
                    <span class="card-kicker">TABELA OFICIAL (CAMADA GOLD)</span>
                    <h3 class="telemetry-title">Registros Armazenados no Banco Analítico</h3>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        display_df = df.copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        display_df = display_df.rename(
            columns={"date": "Data", "value": "Valor da Taxa", "series_code": "Código da Série", "source": "Origem da Coleta"}
        )

        st.dataframe(display_df, use_container_width=True, hide_index=True, height=280)


def _load_gold_data(database_url: str) -> pd.DataFrame:
    """Carrega os dados homologados da tabela bcb_timeseries."""
    try:
        db = DatabaseClient(database_url)
        if not db.table_exists("bcb_timeseries"):
            return pd.DataFrame()
        query = "SELECT date, value, series_code, source FROM bcb_timeseries ORDER BY date ASC;"
        df = db.query_database(query)
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        return pd.DataFrame()
