from __future__ import annotations

from collections.abc import Callable
import html
import pandas as pd
import streamlit as st


def _safe(value: object) -> str:
    return html.escape(str(value))


def _default_scenario_index(scenario_names: list[str]) -> int:
    if "tipo_invalido" in scenario_names:
        return scenario_names.index("tipo_invalido")
    return 0


def render_action_console(
    scenarios: dict | None,
    history_df: pd.DataFrame,
    run_pipeline_fn: Callable[[str], dict | None],
) -> None:
    """Renders the Action Console inside a border container for manual pipeline trigger and latest diagnostic display."""
    with st.container(border=True):
        st.markdown(
            """
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
                response = run_pipeline_fn(selected)

            if response:
                st.success(f"Execução finalizada com sucesso (#{response.get('run_id')})")
                render_run_inline_result(response)
                st.rerun()
            else:
                st.error("Falha ao executar pipeline.")

        # Último Diagnóstico do Histórico
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


def render_run_inline_result(response: dict) -> None:
    """Renders the immediate result box right after a pipeline execution."""
    quarantined = bool(response.get("quarentenado"))
    badge_cls = "badge-quarantine" if quarantined else "badge-approved"
    badge_lbl = "ISOLADO NA QUARENTENA (DLQ)" if quarantined else "CARGA APROVADA"
    hash_val = response.get("audit_hash", "")
    short_hash = f"{hash_val[:14]}..." if hash_val else "sem hash"

    st.markdown(
        f"""
        <div class="latest-diag-box" style="margin-top: 0.6rem; border-color: rgba(0, 212, 255, 0.45);">
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
