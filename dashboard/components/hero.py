from __future__ import annotations

import html
import pandas as pd
import streamlit as st


def _safe(value: object) -> str:
    return html.escape(str(value))


def render_hero_card(status: dict | None, history_df: pd.DataFrame) -> None:
    """Renders the top-left Hero Card with dynamic state and bioluminescent glow core."""
    database = status.get("banco", {}) if status else {}
    bcb_api = status.get("api_banco_central", {}) if status else {}

    db_ok = bool(database.get("conectado"))
    api_ok = bool(bcb_api.get("available"))

    total_runs = len(history_df)
    failed_runs = int((history_df["falhas"] > 0).sum()) if not history_df.empty else 0

    if total_runs == 0:
        headline = "Sistema Pronto"
        sub = "Inicie uma execução no console para monitorar a telemetria em tempo real."
    elif failed_runs == 0:
        headline = "100% Saudável"
        sub = f"Todas as últimas {total_runs} execuções passaram com contratos de dados íntegros."
    else:
        headline = "Proteção Ativa"
        sub = f"Circuit breaker isolou {failed_runs} anomalias na quarentena."

    api_chip_class = "chip-cyan" if api_ok else "chip-rose"
    api_chip_text = "ONLINE" if api_ok else "OFFLINE"

    db_chip_class = "chip-blue" if db_ok else "chip-rose"
    db_chip_text = "CONECTADO" if db_ok else "DESCONECTADO"

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
                    <span class="chip {api_chip_class}">API BCB SGS: {api_chip_text}</span>
                    <span class="chip {db_chip_class}">BANCO: {db_chip_text}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
