import html
import json
import os
from pathlib import Path
import pandas as pd
import requests
import streamlit as st

from dashboard.components.collaboration_view import render_collaboration_panel
from dashboard.components.icons import (
    icon_activity,
    icon_cpu,
    icon_lock,
    icon_shield_alert,
    icon_shield_check,
    icon_terminal,
)


def _safe(value: object) -> str:
    return html.escape(str(value))


def render_incidents_tab(history_df: pd.DataFrame, curated_dir: Path) -> None:
    """Renderiza o raio-x de contratos e análise de incidentes dos agentes."""
    if history_df.empty:
        st.info("Nenhuma execução registrada no histórico para análise detalhada de incidentes.")
        return

    # Seletor de Execução
    options = []
    run_map = {}
    for idx, row in history_df.iterrows():
        run_id = str(row.get("run_id", f"run_{idx}"))
        cenario = str(row.get("cenário", ""))
        quarentenado = "sim" in str(row.get("quarentena", "")).lower()
        status_txt = "[DLQ]" if quarentenado else "[OK]"
        falhas = int(row.get("falhas", 0))
        falhas_txt = f"{falhas} falhas" if falhas != 1 else "1 falha"
        label = f"{status_txt} | #{run_id[:12]} | {cenario} | {falhas_txt}"
        options.append(label)
        run_map[label] = row

    selected_label = st.selectbox(
        "Selecione para exibir detalhes de uma execução",
        options,
        index=0,
    )
    selected_row = run_map[selected_label]
    selected_run_id = str(selected_row.get("run_id", ""))

    # Tenta carregar o JSON completo de diagnóstico da execução
    diagnosis_data = _load_run_diagnosis(selected_run_id, curated_dir)

    quarantined = "sim" in str(selected_row.get("quarentena", "")).lower()
    badge_cls = "badge-quarantine" if quarantined else "badge-approved"
    badge_lbl = "ISOLADO NA QUARENTENA (CIRCUIT BREAKER)" if quarantined else "CARGA APROVADA NO BANCO"
    badge_icon = icon_shield_alert(14, "#E11D48") if quarantined else icon_shield_check(14, "#059669")

    gravidade = str(selected_row.get("gravidade", "baixa")).upper()
    gravidade_cls = "chip-rose" if gravidade in ["ALTA", "CRÍTICA"] else "chip-blue"

    hash_val = str(selected_row.get("audit_hash", ""))
    motor = str(selected_row.get("motor", "regras locais"))

    # Header Card do Incidente Selecionado
    st.markdown(
        f"""
        <div class="latest-diag-box" style="margin-bottom: 1.2rem;">
            <div class="diag-header">
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    <span class="diag-tag {badge_cls}">{badge_icon} {badge_lbl}</span>
                    <span class="chip {gravidade_cls}">GRAVIDADE: {gravidade}</span>
                </div>
                <span class="diag-run">Run ID: <code>{_safe(selected_run_id)}</code></span>
            </div>
            <p class="diag-summary" style="font-size: 0.92rem; margin: 0.5rem 0;">
                “{_safe(selected_row.get("resumo", "Sem resumo registrado para este lote.")) }”
            </p>
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                <div class="diag-hash-bar" style="display: flex; align-items: center; gap: 0.4rem;">
                    {icon_lock(13, "#64748B")}
                    <span class="hash-label">AUDIT SHA-256:</span>
                    <code class="hash-text">{_safe(hash_val or "não assinado")}</code>
                </div>
                <span style="font-family: var(--font-ui); font-size: 0.76rem; color: var(--text-muted);">
                    Modelo: <b style="color: var(--text-primary);">{motor.upper()}</b>
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    diag_info = diagnosis_data.get("diagnosis", {}) if diagnosis_data else {}
    inv_info = diagnosis_data.get("investigation", {}) if diagnosis_data else {}
    res_info = diagnosis_data.get("resolution", {}) if diagnosis_data else {}
    collab_info = diagnosis_data.get("collaboration", {}) if diagnosis_data else {}
    if not collab_info and selected_row.get("collaboration_summary"):
        collab_info = {
            "status": selected_row.get("collaboration_status"),
            "supervisor_decision": selected_row.get("collaboration_summary"),
        }

    # 1. Painel de Diálogo e Consenso Multiagente em Destaque
    render_collaboration_panel(collab_info, run_id=selected_run_id)

    # 2. Diagnóstico individual dos 3 agentes
    st.markdown(
        """
        <div class="telemetry-top">
            <div>
                <span class="card-kicker">ANÁLISE DE CAUSA RAIZ & RESOLUÇÃO AUTÔNOMA</span>
                <h3 class="telemetry-title">Tríade de Agentes DataOps</h3>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_diag, col_inv, col_res = st.columns(3, gap="medium")

    with col_diag:
        causes = diag_info.get("probable_causes", [])
        causes_html = "".join(f"<li>{_safe(c)}</li>" for c in causes) if causes else "<li>Nenhuma causa de anomalia identificada.</li>"
        st.markdown(
            f"""
            <div class="agent-card">
                <div class="agent-card-header">
                    <span class="agent-name">{icon_cpu(14, "#D59B88")} Agente de qualidade de dados</span>
                    <span class="mini-tag tag-cyan">DIAGNÓSTICO</span>
                </div>
                <p><b>Resumo do Diagnóstico:</b></p>
                <p>{_safe(diag_info.get("summary", selected_row.get("resumo", "Sem diagnóstico detalhado.")))}</p>
                <p><b>Causas Prováveis:</b></p>
                <ul>{causes_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_inv:
        evidence = inv_info.get("evidence", [])
        evidence_html = "".join(f"<li>{_safe(e)}</li>" for e in evidence) if evidence else "<li>Sem evidências adicionais registradas.</li>"
        hypothesis = inv_info.get("hypothesis", "Aguardando investigação detalhada.")
        st.markdown(
            f"""
            <div class="agent-card">
                <div class="agent-card-header">
                    <span class="agent-name">{icon_activity(14, "#475569")} Agente de investigação</span>
                    <span class="mini-tag tag-blue">EVIDÊNCIAS</span>
                </div>
                <p><b>Hipótese Técnica:</b></p>
                <p>{_safe(hypothesis)}</p>
                <p><b>Evidências Coletadas:</b></p>
                <ul>{evidence_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_res:
        steps = res_info.get("correction_steps", [])
        steps_html = "".join(f"<li>{_safe(s)}</li>" for s in steps) if steps else "<li>Nenhuma ação corretiva urgente necessária.</li>"
        manual = "SIM (Atenção)" if res_info.get("requires_manual_review", selected_row.get("revisão_manual") == "sim") else "NÃO (Autônomo)"
        manual_color = "#E11D48" if "SIM" in manual else "#059669"
        st.markdown(
            f"""
            <div class="agent-card">
                <div class="agent-card-header">
                    <span class="agent-name">{icon_terminal(14, "#334155")} Agente de resolução</span>
                    <span class="mini-tag tag-blue">PLANO DE AÇÃO</span>
                </div>
                <p><b>Revisão Manual Necessária:</b> <b style="color: {manual_color};">{manual}</b></p>
                <p><b>Passos de Correção:</b></p>
                <ul>{steps_html}</ul>
                <p><b>Impacto:</b> {_safe(res_info.get("impact", "Carga processada dentro dos limites de governança."))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="spacing-gap-md"></div>', unsafe_allow_html=True)

    # 3. Tabela com validações dos contratos de dados
    with st.container(border=True):
        st.markdown(
            """
            <div class="telemetry-top">
                <div>
                    <span class="card-kicker">QUALIDADE & VALIDAÇÕES DECLARATIVAS</span>
                    <h3 class="telemetry-title">Raio-X de Contratos de Dados</h3>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if diagnosis_data and "quality_report" in diagnosis_data:
            report = diagnosis_data["quality_report"]
            passed = report.get("passed_checks", [])
            failed = report.get("failed_checks", [])

            table_rows = []
            for check in passed:
                table_rows.append({"Regra": check, "Status": "PASSOU", "Mensagem": "Validação concluída sem divergências."})
            for check in failed:
                table_rows.append({"Regra": check, "Status": "FALHOU", "Mensagem": "Violação declarativa de contrato detectada."})

            if table_rows:
                contract_df = pd.DataFrame(table_rows)
                st.dataframe(contract_df, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma checagem estruturada encontrada para este run.")
        else:
            falhas = int(selected_row.get("falhas", 0))
            if falhas == 0:
                st.success("Todas as 5 regras de contrato declarativo foram aprovadas com sucesso nesta execução.")
            elif falhas == 1:
                st.error("Foi detectada 1 violação de contrato nos dados brutos desta execução.")
            else:
                st.error(f"Foram detectadas {falhas} violações de contrato nos dados brutos desta execução.")

    col_diag, col_inv, col_res = st.columns(3, gap="medium")

    with col_diag:
        causes = diag_info.get("probable_causes", [])
        causes_html = "".join(f"<li>{_safe(c)}</li>" for c in causes) if causes else "<li>Nenhuma causa de anomalia identificada.</li>"
        st.markdown(
            f"""
            <div class="agent-card">
                <div class="agent-card-header">
                    <span class="agent-name">{icon_cpu(14, "#D59B88")} Agente de qualidade de dados</span>
                    <span class="mini-tag tag-cyan">DIAGNÓSTICO</span>
                </div>
                <p><b>Resumo do Diagnóstico:</b></p>
                <p>{_safe(diag_info.get("summary", selected_row.get("resumo", "Sem diagnóstico detalhado.")))}</p>
                <p><b>Causas Prováveis:</b></p>
                <ul>{causes_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_inv:
        evidence = inv_info.get("evidence", [])
        evidence_html = "".join(f"<li>{_safe(e)}</li>" for e in evidence) if evidence else "<li>Sem evidências adicionais registradas.</li>"
        hypothesis = inv_info.get("hypothesis", "Aguardando investigação detalhada.")
        st.markdown(
            f"""
            <div class="agent-card">
                <div class="agent-card-header">
                    <span class="agent-name">{icon_activity(14, "#475569")} Agente de investigação</span>
                    <span class="mini-tag tag-blue">EVIDÊNCIAS</span>
                </div>
                <p><b>Hipótese Técnica:</b></p>
                <p>{_safe(hypothesis)}</p>
                <p><b>Evidências Coletadas:</b></p>
                <ul>{evidence_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_res:
        steps = res_info.get("correction_steps", [])
        steps_html = "".join(f"<li>{_safe(s)}</li>" for s in steps) if steps else "<li>Nenhuma ação corretiva urgente necessária.</li>"
        manual = "SIM (Atenção)" if res_info.get("requires_manual_review", selected_row.get("revisão_manual") == "sim") else "NÃO (Autônomo)"
        manual_color = "#E11D48" if "SIM" in manual else "#059669"
        st.markdown(
            f"""
            <div class="agent-card">
                <div class="agent-card-header">
                    <span class="agent-name">{icon_terminal(14, "#334155")} Agente de resolução</span>
                    <span class="mini-tag tag-blue">PLANO DE AÇÃO</span>
                </div>
                <p><b>Revisão Manual Necessária:</b> <b style="color: {manual_color};">{manual}</b></p>
                <p><b>Passos de Correção:</b></p>
                <ul>{steps_html}</ul>
                <p><b>Impacto:</b> {_safe(res_info.get("impact", "Carga processada dentro dos limites de governança."))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _load_run_diagnosis(run_id: str, curated_dir: Path) -> dict:
    """Attempts to find the specific or latest diagnosis JSON file for the given run_id."""
    # 1. Tenta buscar via API se disponível (crucial quando roda no Docker)
    api_url = os.getenv("DATAOPS_API_URL", "http://127.0.0.1:8000").rstrip("/")
    if api_url:
        try:
            res = requests.get(f"{api_url}/execucoes/{run_id}/diagnostico", timeout=2)
            if res.status_code == 200:
                data = res.json()
                if data and isinstance(data, dict) and str(data.get("run_id")) == str(run_id):
                    return data
        except Exception:
            pass

    # 2. Arquivo individual do run no disco
    run_file = curated_dir / f"quality_diagnosis_{run_id}.json"
    if run_file.exists():
        try:
            return json.loads(run_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 3. Arquivo geral se bater o run_id
    latest_file = curated_dir / "quality_diagnosis.json"
    if latest_file.exists():
        try:
            data = json.loads(latest_file.read_text(encoding="utf-8"))
            if str(data.get("run_id")) == str(run_id):
                return data
        except Exception:
            pass

    return {}
