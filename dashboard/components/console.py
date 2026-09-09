from collections.abc import Callable
import html
from pathlib import Path
import pandas as pd
import streamlit as st

from dashboard.components.collaboration_view import render_collaboration_panel
from dashboard.components.icons import (
    icon_lock,
    icon_shield_alert,
    icon_shield_check,
    icon_terminal,
    icon_zap,
)
from dashboard.components.incidents import _load_run_diagnosis


def _safe(value: object) -> str:
    return html.escape(str(value))


def _default_scenario_index(scenario_names: list[str]) -> int:
    if "tipo_invalido" in scenario_names:
        return scenario_names.index("tipo_invalido")
    return 0


def render_simulation_tab(
    scenarios: dict | None,
    history_df: pd.DataFrame,
    run_pipeline_fn: Callable[[str], dict | None],
) -> None:
    """Renderiza a aba do simulador de falhas e injeção de anomalias."""
    st.markdown(
        f"""
        <div class="bento-card" style="padding: 1.35rem 1.6rem; margin-bottom: 1.25rem;">
            <span class="card-kicker">Testes</span>
            <h3 style="color: var(--text-primary); margin: 0.3rem 0 0.5rem 0; font-size: 1.3rem; font-weight: 700;">
                Simulador de falhas e injeção de anomalias
            </h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_action, col_catalog = st.columns([0.52, 0.48], gap="medium")

    scenario_items = scenarios.get("cenarios", []) if scenarios else []
    scenario_names = [item["nome"] for item in scenario_items] or ["sem_incidente"]
    descriptions = {item["nome"]: item["descricao"] for item in scenario_items}

    with col_action:
        with st.container(border=True):
            st.markdown(
                f"""
                <div class="telemetry-top">
                    <div>
                        <span class="card-kicker">DISPARO MANUAL</span>
                        <h3 class="telemetry-title" style="display: flex; align-items: center; gap: 0.45rem;">
                            Executar Cenário
                        </h3>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            selected = st.selectbox(
                "Selecione o cenário de injeção de falha",
                scenario_names,
                index=_default_scenario_index(scenario_names),
            )

            desc = descriptions.get(selected, "")
            if desc:
                st.markdown(f'<div class="console-action-desc">{_safe(desc)}</div>', unsafe_allow_html=True)

            if st.button("Disparar execução", type="primary", use_container_width=True):
                with st.spinner("Acionando pipeline, validando contratos e acionando agentes..."):
                    response = run_pipeline_fn(selected)

                if response:
                    st.session_state["simulation_response"] = response
                    st.session_state["simulation_run_id"] = response.get("run_id")
                    st.success(f"Pipeline executada com sucesso (#{response.get('run_id')})")
                else:
                    st.error("Falha ao executar pipeline.")

            # Se houver resultado da simulação atual armazenado na sessão, exibe imediatamente
            sim_resp = st.session_state.get("simulation_response")
            if sim_resp:
                render_run_inline_result(sim_resp)

            # Último Diagnóstico do Histórico Geral
            elif not history_df.empty:
                latest = history_df.iloc[0]
                quarantined = "sim" in str(latest.get("quarentena", "")).lower()
                badge_cls = "badge-quarantine" if quarantined else "badge-approved"
                badge_lbl = "ISOLADO NA QUARENTENA (DLQ)" if quarantined else "CARGA APROVADA"
                badge_icon = icon_shield_alert(13, "#E11D48") if quarantined else icon_shield_check(13, "#059669")
                hash_val = str(latest.get("audit_hash") or "")
                short_hash = f"{hash_val[:16]}..." if hash_val else "não calculado"

                st.markdown(
                    f"""
                    <div class="latest-diag-box">
                        <div class="diag-header">
                            <span class="diag-tag {badge_cls}">{badge_icon} {badge_lbl}</span>
                            <span class="diag-run">Última execução: <code>{_safe(latest.get("run_id"))}</code></span>
                        </div>
                        <p class="diag-summary">“{_safe(latest.get("resumo", ""))}”</p>
                        <div class="diag-hash-bar" style="display: flex; align-items: center; gap: 0.4rem;">
                            {icon_lock(13, "#64748B")}
                            <span class="hash-label">AUDIT SHA-256:</span>
                            <code class="hash-text">{_safe(short_hash)}</code>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with col_catalog:
        with st.container(border=True):
            st.markdown(
                """
                <div class="telemetry-top">
                    <div>
                        <span class="card-kicker">Cenários de ingestão de falha</span>
                        <h3 class="telemetry-title">Comportamento Esperado</h3>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            catalog_data = [
                {"Cenário": "sem_incidente", "Impacto": "Carga normal", "Circuit Breaker": "Liberado"},
                {"Cenário": "valores_nulos", "Impacto": "Nulos em campos obrigatórios", "Circuit Breaker": "DLQ ativada"},
                {"Cenário": "mudanca_estrutura", "Impacto": "Schema drift (coluna removida)", "Circuit Breaker": "DLQ ativada"},
                {"Cenário": "registros_duplicados", "Impacto": "Violação de unicidade", "Circuit Breaker": "DLQ ativada"},
                {"Cenário": "tipo_invalido", "Impacto": "String em campo numérico", "Circuit Breaker": "DLQ ativada"},
                {"Cenário": "timeout_api", "Impacto": "Indisponibilidade da API BCB", "Circuit Breaker": "Fallback Local"},
            ]
            st.dataframe(pd.DataFrame(catalog_data), use_container_width=True, hide_index=True)


def render_action_console(
    scenarios: dict | None,
    history_df: pd.DataFrame,
    run_pipeline_fn: Callable[[str], dict | None],
) -> None:
    """Compatibilidade para renderizar o console de simulação."""
    render_simulation_tab(scenarios, history_df, run_pipeline_fn)


def render_run_inline_result(response: dict) -> None:
    """Exibe o resultado imediato logo após a execução da pipeline com debate multiagente."""
    run_id = str(response.get("run_id", ""))
    quarantined = bool(response.get("quarentenado"))
    badge_cls = "badge-quarantine" if quarantined else "badge-approved"
    badge_lbl = "ISOLADO NA QUARENTENA (DLQ)" if quarantined else "CARGA APROVADA"
    badge_icon = icon_shield_alert(13, "#E11D48") if quarantined else icon_shield_check(13, "#059669")
    hash_val = response.get("audit_hash", "")
    short_hash = f"{hash_val[:16]}..." if hash_val else "sem hash"

    st.markdown(
        f"""
        <div class="latest-diag-box" style="margin-top: 0.8rem; margin-bottom: 0.8rem;">
            <div class="diag-header">
                <span class="diag-tag {badge_cls}">{badge_icon} {badge_lbl}</span>
                <span class="diag-run">Run: <code>#{_safe(run_id[:12])}</code> | Falhas: <b>{response.get("validacoes_com_falha", 0)}</b></span>
            </div>
            <p class="diag-summary">“{_safe(response.get("resumo", ""))}”</p>
            <div class="diag-hash-bar" style="display: flex; align-items: center; gap: 0.4rem;">
                {icon_lock(13, "#64748B")}
                <span class="hash-label">AUDIT HASH:</span>
                <code class="hash-text">{_safe(short_hash)}</code>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Busca ou extrai os dados de colaboração
    collab = response.get("collaboration")
    if not collab and run_id:
        curated_dir = Path(__file__).resolve().parents[2] / "data" / "curated"
        diag = _load_run_diagnosis(run_id, curated_dir)
        collab = diag.get("collaboration") if diag else None

    if not collab:
        collab = {
            "status": response.get("collaboration_status"),
            "supervisor_decision": response.get("collaboration_summary"),
        }

    render_collaboration_panel(
        collab,
        run_id=run_id,
        title="Debate e Consenso Multiagente Desta Execução",
    )
