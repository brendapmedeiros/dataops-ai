from __future__ import annotations

import pandas as pd
import streamlit as st


def render_bento_metrics(status: dict | None, history_df: pd.DataFrame) -> None:
    """Renders the top-right 2x2 Bento Metric Cards."""
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
        health_status = "Normal" if pass_rate >= 80 else "Atenção"
        health_color = "#34D399" if pass_rate >= 80 else "#FBBF24"

        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Pipeline Health</span>
                    <span class="mini-tag tag-blue">HEALTH</span>
                </div>
                <div class="mini-metric">{pass_rate:.0f}<small>%</small></div>
                <div class="mini-foot">Status: <b style="color: {health_color};">{health_status}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="spacing-gap-sm"></div>', unsafe_allow_html=True)

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

        st.markdown('<div class="spacing-gap-sm"></div>', unsafe_allow_html=True)

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
