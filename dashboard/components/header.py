from __future__ import annotations

import base64
import html
from pathlib import Path
import pandas as pd
import streamlit as st

from dashboard.components.icons import (
    icon_activity,
    icon_cpu,
    icon_database,
    icon_shield_alert,
    icon_shield_check,
)


def _safe(value: object) -> str:
    return html.escape(str(value))


def _get_badge_base64() -> str:
    # carrego o badge oficial em base64 se existir no diretorio
    img_path = Path(__file__).resolve().parents[1] / "assets" / "dataops_badge.jpg"
    if img_path.exists():
        try:
            data = base64.b64encode(img_path.read_bytes()).decode("utf-8")
            return f"data:image/jpeg;base64,{data}"
        except Exception:
            return ""
    return ""


def render_cockpit_header(status: dict | None, history_df: pd.DataFrame) -> None:
    # renderizo o cabecalho de observabilidade sem badges excessivos
    database = status.get("banco", {}) if status else {}
    bcb_api = status.get("api_banco_central", {}) if status else {}
    gemini = status.get("gemini", {}) if status else {}

    db_ok = bool(database.get("conectado"))
    db_type = database.get("tipo", "SQLite")
    api_ok = bool(bcb_api.get("available"))
    gemini_ok = bool(gemini.get("configurado"))
    gemini_model = gemini.get("modelo", "Regras Locais")

    total_runs = len(history_df)
    failed_runs = int((history_df["falhas"] > 0).sum()) if not history_df.empty else 0
    quarantined_count = 0
    if not history_df.empty and "quarentena" in history_df:
        quarantined_count = int(history_df["quarentena"].str.contains("sim", case=False).sum())

    if total_runs == 0:
        system_status_cls = "chip-blue"
        system_status_label = "SISTEMA PRONTO"
        status_icon = icon_shield_check(14, "currentColor")
    elif quarantined_count > 0 or failed_runs > 0:
        system_status_cls = "chip-rose"
        system_status_label = f"Circuit Breaker Ativo ({quarantined_count} lotes isolados)"
        status_icon = icon_shield_alert(14, "currentColor")
    else:
        system_status_cls = "chip-emerald"
        system_status_label = "Operacional (100% íntegro)"
        status_icon = icon_shield_check(14, "currentColor")

    if not history_df.empty and "recorded_at" in history_df.columns:
        latest_time = str(history_df.iloc[0].get("recorded_at", ""))
        if "T" in latest_time:
            time_part = latest_time.split("T")[1][:8]
            date_part = latest_time.split("T")[0]
            freshness_text = f"Última carga: {date_part} {time_part} UTC"
        else:
            freshness_text = f"Última carga: #{history_df.iloc[0].get('run_id', '')[:8]}"
    else:
        freshness_text = "Aguardando ingestão"

    api_cls = "chip-emerald" if api_ok else "chip-rose"
    api_text = "API BCB: online" if api_ok else "API BCB: offline"
    api_icon = icon_activity(13, "currentColor")

    db_text = f"Storage: {db_type.upper()}" if db_ok else "Storage: desconectado"
    db_icon = icon_database(13, "currentColor")

    ai_text = "Engine: Gemini Flash" if gemini_ok else "Engine: Regras Locais"
    ai_icon = icon_cpu(13, "currentColor")

    badge_b64 = _get_badge_base64()
    badge_html = (
        f'<img src="{badge_b64}" class="brand-badge-img" alt="DataOps AI" />'
        if badge_b64
        else icon_shield_check(24, "#FAFAFA")
    )

    import os
    ambiente = status.get("ambiente", {}) if status else {}
    provedor = ambiente.get("provedor") or ("Google Cloud Run" if os.getenv("K_SERVICE") else "Localhost")
    regiao = ambiente.get("regiao") or os.getenv("GCP_REGION", "us-central1" if "Cloud" in provedor else "local")
    is_cloud = "Cloud" in provedor
    env_cls = "chip-emerald" if is_cloud else "chip-blue"
    env_text = f"Ambiente: Cloud Run ({regiao})" if is_cloud else "Ambiente: Localhost"

    st.markdown(
        f"""
        <div class="cockpit-header-bar">
            <div class="cockpit-brand">
                {badge_html}
                <div>
                    <div class="cockpit-tag">DataOps Observability</div>
                    <div class="cockpit-title" role="heading" aria-level="1">Controle de Integridade & Circuit Breaker</div>
                </div>
            </div>
            <div class="cockpit-badges">
                <span class="chip {system_status_cls}">{status_icon} {system_status_label}</span>
                <span class="chip {env_cls}">{icon_cpu(13, "currentColor")} {env_text}</span>
                <span class="chip {api_cls}">{api_icon} {api_text}</span>
                <span class="chip chip-blue">{db_icon} {db_text}</span>
                <span class="chip chip-blue">{ai_icon} {ai_text}</span>
                <span class="chip chip-blue">{_safe(freshness_text)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
