from __future__ import annotations

import html
import json
from pathlib import Path
import pandas as pd
import streamlit as st

from dashboard.components.icons import (
    icon_activity,
    icon_box,
    icon_shield_alert,
    icon_shield_check,
)


def _safe(value: object) -> str:
    return html.escape(str(value))


def render_quarantine_tab(dlq_dir: Path) -> None:
    """Renderiza a quarentena (DLQ) e inspeção dos lotes rejeitados."""
    csv_files = sorted(dlq_dir.glob("quarantine_*.csv"), key=lambda f: f.stat().st_mtime, reverse=True)

    if not csv_files:
        empty_icon = icon_shield_check(32, "#059669")
        st.markdown(
            f"""
            <div class="bento-card" style="padding: 2.5rem 1.5rem; text-align: center;">
                <div class="empty-circuit-illustration">{empty_icon}</div>
                <h3 style="color: var(--text-primary); margin: 0.4rem 0; font-size: 1.25rem;">Quarentena Vazia (Circuit Breaker Saudável)</h3>
                <p style="color: var(--text-muted); max-width: 500px; margin: 0 auto; font-size: 0.88rem; line-height: 1.5;">
                    Nenhum lote foi rejeitado pelos contratos de qualidade. Todos os dados processados passaram com integridade para a base oficial.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # metricas gerais da quarentena
    total_quarantined_batches = len(csv_files)
    latest_file = csv_files[0]
    latest_time_str = pd.to_datetime(latest_file.stat().st_mtime, unit="s").strftime("%d/%m/%Y %H:%M:%S")

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Lotes isolados</span>
                    <span class="mini-tag tag-cyan">{icon_box(12, "#D59B88")} Quarentena</span>
                </div>
                <div class="mini-metric">{total_quarantined_batches} <small>lotes isolados</small></div>
                <div class="mini-foot">Diretório: <code>data/dlq/</code></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="bento-card mini-card">
                <div class="mini-top">
                    <span class="mini-label">Último incidente</span>
                    <span class="mini-tag tag-blue">{icon_activity(12, "#475569")} PROTECTION EVENT</span>
                </div>
                <div class="mini-metric" style="font-size: 1.5rem; line-height: 1.8;">{latest_time_str}</div>
                <div class="mini-foot">Arquivo: <code>{latest_file.name[:28]}...</code></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="spacing-gap-md"></div>', unsafe_allow_html=True)

    # seletor de arquivos na quarentena
    file_options = [f.name for f in csv_files]
    selected_filename = st.selectbox(
        "Selecione um lote para inspeção",
        file_options,
        index=0,
    )

    selected_csv_path = dlq_dir / selected_filename
    meta_json_path = dlq_dir / selected_filename.replace(".csv", "_meta.json")

    # metadados do lote selecionado
    if meta_json_path.exists():
        try:
            meta_data = json.loads(meta_json_path.read_text(encoding="utf-8"))
            reasons = meta_data.get("failed_checks", [])
            reasons_html = "".join(
                f"<li><b>{_safe(r.get('check_name'))}</b>: {_safe(r.get('details'))} (afetou {r.get('rows_affected', 0)} linhas)</li>"
                for r in reasons
            )
            scenario = meta_data.get("scenario", "não informado")
            quarantined_at = meta_data.get("quarantined_at", "")
            alert_svg = icon_shield_alert(15, "#E11D48")

            st.markdown(
                f"""
                <div class="dlq-meta-card">
                    <div class="dlq-meta-title" style="display: flex; align-items: center; gap: 0.45rem;">
                        {alert_svg}
                        <span> Motivo de isolamento de carga:{_safe(scenario).upper()})</span>
                    </div>
                    <p style="font-size: 0.82rem; color: var(--text-secondary); margin: 0 0 0.4rem 0;">
                        Isolado em: <code>{_safe(quarantined_at)}</code>
                    </p>
                    <ul style="margin: 0.2rem 0 0 1.2rem; font-size: 0.82rem; color: var(--text-secondary);">
                        {reasons_html}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        except Exception:
            pass

    # inspecao dos dados brutos retidos
    with st.container(border=True):
        st.markdown(
            """
            <div class="telemetry-top">
                <div>
                    <span class="card-kicker">DATA PREVIEW DO LOTE REJEITADO</span>
                    <h3 class="telemetry-title">Dados Isolados da Base Oficial</h3>
                </div>
                <span class="live-pill" style="color: var(--state-danger-text); background: var(--state-danger-bg); border-color: var(--state-danger-border);">
                    BLOQUEADO
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        try:
            quarantined_df = pd.read_csv(selected_csv_path)
            st.caption(f"Visualizando {len(quarantined_df)} linhas do arquivo '{selected_filename}':")
            st.dataframe(
                quarantined_df,
                use_container_width=True,
                hide_index=True,
                height=320,
            )
        except Exception as exc:
            st.error(f"Erro ao ler arquivo da quarentena: {exc}")
