from __future__ import annotations

import html
import streamlit as st

from dashboard.components.icons import (
    icon_activity,
    icon_cpu,
    icon_lock,
    icon_shield_alert,
    icon_shield_check,
    icon_terminal,
)


def _safe(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def _translate_agent_name(speaker: str) -> tuple[str, str, str, str, object]:
    """Retorna (nome_traduzido, cor_texto, cor_fundo_badge, cor_borda, icone_svg)."""
    normalized = speaker.lower()
    if "quality" in normalized or "qualidade" in normalized:
        return (
            "Agente de qualidade de dados",
            "#C58875",
            "#FDF4F2",
            "#D59B88",
            icon_cpu(15, "#D59B88"),
        )
    if "investigation" in normalized or "investig" in normalized:
        return (
            "Agente de investigação",
            "#1D4ED8",
            "#EFF6FF",
            "#3B82F6",
            icon_activity(15, "#2563EB"),
        )
    return (
        "Agente de resolução",
        "#047857",
        "#ECFDF5",
        "#10B981",
        icon_terminal(15, "#059669"),
    )


def _translate_role_label(role: str, action: str) -> str:
    """Traduz o papel/ação do turno para português."""
    combined = f"{role} {action}".lower()
    if "calib" in combined:
        return "CALIBRAÇÃO DE SEVERIDADE"
    if "diag" in combined:
        return "DIAGNÓSTICO INICIAL"
    if "investig" in combined or "evidence" in combined or "evid" in combined:
        return "INVESTIGAÇÃO & EVIDÊNCIAS"
    if "action" in combined or "plano" in combined or "resol" in combined or "consenso" in combined:
        return "PLANO DE AÇÃO"
    return role.upper()


def _render_html(html_str: str) -> None:
    """Renderiza HTML nativo no Streamlit sem risco de o Markdown converter linhas indentadas em blocos de código."""
    if hasattr(st, "html"):
        st.html(html_str)
    else:
        # Fallback para versões legadas: remove recuos para não disparar regra de 4 espaços do Markdown
        clean_html = "\n".join(line.strip() for line in html_str.splitlines() if line.strip())
        st.markdown(clean_html, unsafe_allow_html=True)


def render_collaboration_panel(
    collab_info: dict | None,
    run_id: str = "",
    title: str = "Diálogo e Consenso Multiagente (Debate Supervisionado)",
    expanded_default: bool = True,
    show_container: bool = True,
) -> None:
    """Renderiza a visualização completa do debate, calibragem e consenso multiagente sem emojis."""
    if not collab_info:
        collab_info = {}

    status_val = collab_info.get("status")
    conversation = collab_info.get("conversation") or []
    supervisor_decision = collab_info.get("supervisor_decision") or ""

    # Caso 1: Temos o diálogo estruturado com rodadas
    if conversation:
        is_refined = status_val == "consenso_refinado" or len(conversation) > 2
        badge_text = "CONSENSO REFINADO (2 RODADAS)" if is_refined else "CONSENSO DIRETO (1 RODADA)"
        badge_style = (
            "background: #FDF4F2; color: #C58875; border: 1px solid #F3DDD7;"
            if is_refined
            else "background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0;"
        )

        turns_html = []
        for idx, turn in enumerate(conversation, 1):
            speaker = str(turn.get("speaker", "Agente"))
            role = str(turn.get("role", "mensagem"))
            msg = str(turn.get("message", ""))
            action = str(turn.get("action_taken", ""))

            label_name, pill_color, pill_bg, border_accent, svg_icon = _translate_agent_name(speaker)
            role_label = _translate_role_label(role, action)

            turns_html.append(
                f"""<div style="display: flex; gap: 0.85rem; padding: 0.85rem 1rem; border-left: 3px solid {border_accent}; background: #FFFFFF; border-radius: 0 8px 8px 0; border-top: 1px solid #F1F5F9; border-right: 1px solid #F1F5F9; border-bottom: 1px solid #F1F5F9; box-shadow: 0 1px 2px rgba(15,23,42,0.02);">
<div style="flex-shrink: 0; margin-top: 2px;">{svg_icon}</div>
<div style="flex-grow: 1;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem; flex-wrap: wrap; gap: 0.4rem;">
<span style="font-size: 0.86rem; font-weight: 700; color: {pill_color}; font-family: var(--font-ui, sans-serif);">{label_name}</span>
<span style="font-size: 0.7rem; font-weight: 600; padding: 2px 8px; border-radius: 4px; background: {pill_bg}; color: {pill_color}; border: 1px solid {pill_color}33;">Rodada {idx} • {role_label}</span>
</div>
<p style="margin: 0; font-size: 0.86rem; line-height: 1.5; color: #334155;">{_safe(msg)}</p>
</div>
</div>"""
            )

        content_html = f"""<div style="background: #FFFFFF; border: 1px solid var(--border-card, #EAECEF); border-radius: 12px; padding: 1.1rem 1.3rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(15,23,42,0.04);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; flex-wrap: wrap; gap: 0.5rem; border-bottom: 1px solid var(--border-divider, #E2E8F0); padding-bottom: 0.6rem;">
<div style="display: flex; align-items: center; gap: 0.5rem;">
<span style="font-weight: 700; font-size: 0.95rem; color: var(--text-primary, #0F172A); font-family: var(--font-heading, inherit);">{_safe(title)}</span>
{f'<code style="font-size: 0.76rem; background: #F1F5F9; padding: 2px 6px; border-radius: 4px; color: #64748B;">#{_safe(run_id[:12])}</code>' if run_id else ''}
</div>
<span style="font-size: 0.72rem; font-weight: 700; padding: 3px 10px; border-radius: 6px; letter-spacing: 0.03em; {badge_style}">{badge_text}</span>
</div>
<div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem;">
<div style="display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.25rem;">
<span style="font-size: 0.74rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: #64748B;">Decisão do Supervisor da Orquestração</span>
</div>
<p style="margin: 0; font-size: 0.88rem; color: var(--text-primary, #0F172A); line-height: 1.45; font-weight: 500;">“{_safe(supervisor_decision or 'Consenso alcançado e homologado pelos 3 agentes.')}”</p>
</div>
<div style="display: flex; flex-direction: column; gap: 0.75rem;">
{''.join(turns_html)}
</div>
</div>"""

        _render_html(content_html)

    # Caso 2: Temos apenas o sumário de colaboração registrado
    elif supervisor_decision or status_val:
        is_refined = status_val == "consenso_refinado"
        badge_text = "CONSENSO REFINADO" if is_refined else "CONSENSO DIRETO"
        badge_style = (
            "background: #FDF4F2; color: #C58875; border: 1px solid #F3DDD7;"
            if is_refined
            else "background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0;"
        )

        content_html = f"""<div style="background: #FFFFFF; border: 1px solid var(--border-card, #EAECEF); border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(15,23,42,0.04);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.4rem;">
<span style="font-weight: 700; font-size: 0.92rem; color: var(--text-primary, #0F172A);">{_safe(title)}</span>
<span style="font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; {badge_style}">{badge_text}</span>
</div>
<p style="margin: 0; font-size: 0.88rem; color: var(--text-primary, #0F172A); line-height: 1.45;">“{_safe(supervisor_decision or 'Consenso multiagente validado com sucesso.')}”</p>
</div>"""
        _render_html(content_html)

    # Caso 3: Execução legada sem dados de colaboração
    else:
        content_html = """<div style="background: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 12px; padding: 1rem 1.2rem; margin-bottom: 1rem;">
<div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.35rem;">
<b style="font-size: 0.88rem; color: #475569;">Debate Multiagente Ativo para Novas Execuções</b>
</div>
<p style="margin: 0; font-size: 0.84rem; color: #64748B; line-height: 1.45;">
Esta execução selecionada foi gerada antes da arquitetura de colaboração multiagente.
Acesse a aba <b>Simulador</b> para disparar um novo teste em tempo real, ou selecione a execução mais recente no topo do seletor para visualizar as 4 rodadas de diálogo entre os 3 agentes.
</p>
</div>"""
        _render_html(content_html)

