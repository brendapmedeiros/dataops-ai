from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st


def render_ecg_telemetry(history_df: pd.DataFrame) -> None:
    """Renders the ECG Telemetry Waveform panel with continuous quality metrics."""
    with st.container(border=True):
        st.markdown(
            """
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
            return

        chart_df = history_df.sort_values("ordem").tail(16).copy()
        chart_df["idx"] = range(1, len(chart_df) + 1)
        chart_df["run_label"] = [f"#{i}" for i in chart_df["idx"]]

        base = alt.Chart(chart_df).encode(
            x=alt.X(
                "run_label:O",
                title=None,
                axis=alt.Axis(
                    labelColor="#64748B",
                    labelFontSize=10,
                    domainColor="#0B152D",
                    tickColor="#0B152D",
                ),
            ),
            y=alt.Y(
                "falhas:Q",
                title=None,
                axis=alt.Axis(
                    labelColor="#64748B",
                    labelFontSize=10,
                    gridColor="#0B152D",
                    tickMinStep=1,
                ),
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
            strokeWidth=2.6,
            interpolate="monotone",
        )

        points = base.mark_circle(
            color="#FFFFFF",
            size=44,
            stroke="#0066FF",
            strokeWidth=2.2,
        )

        chart = (
            (area + line + points)
            .properties(height=230)
            .configure_view(strokeWidth=0)
            .configure(background="transparent")
        )
        st.altair_chart(chart, use_container_width=True)

        st.markdown(
            """
            <div class="ecg-footnote">
                <span>Linha Contínua: Histórico de anomalias</span>
                <span>Limiar de Contrato: 0 falhas</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
