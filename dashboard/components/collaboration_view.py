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


def _agent_meta(speaker: str) -> tuple[str, str, str, str, object]:
    # metadados de cor e icone dos agentes para o trace do rca no dark mode
    normalized = speaker.lower()
    if "quality" in normalized or "qualidade" in normalized:
        return (
            "Auditoria de Contratos (Agente de Qualidade)",
            "#E4E4E7",
            "#27272A",
            "#71717A",
            icon_cpu(14, "#A1A1AA"),
        )
    if "investigation" in normalized or "investig" in normalized:
        return (
            "Rastreamento de Causa Raiz (Agente de Investigação)",
            "#93C5FD",
            "rgba(59, 130, 246, 0.15)",
            "#3B82F6",
            icon_activity(14, "#60A5FA"),
        )
    return (
        "Mitigação & Circuit Breaker (Agente de Resolução)",
        "#86EFAC",
        "rgba(16, 185, 129, 0.15)",
        "#10B981",
        icon_terminal(14, "#4ADE80"),
    )


def _translate_role_label(role: str, action: str) -> str:
    # padronizo o rotulo do estagio tecnico de investigacao
    combined = f"{role} {action}".lower()
    if "calib" in combined:
        return "RECALIBRAÇÃO DE IMPACTO"
    if "diag" in combined:
        return "DIAGNÓSTICO INICIAL"
    if "investig" in combined or "evidence" in combined or "evid" in combined:
        return "EVIDÊNCIAS TÉCNICAS"
    if "action" in combined or "plano" in combined or "resol" in combined or "consenso" in combined:
        return "PLANO DE MITIGAÇÃO"
    return role.upper()


def _render_html(html_str: str) -> None:
    # renderizo html nativo sem disparar formatacao markdown acidental
    if hasattr(st, "html"):
        st.html(html_str)
    else:
        clean_html = "\n".join(line.strip() for line in html_str.splitlines() if line.strip())
        st.markdown(clean_html, unsafe_allow_html=True)


def render_collaboration_panel(
    collab_info: dict | None,
    run_id: str = "",
    title: str = "Governança & Análise de Causa Raiz (RCA)",
    expanded_default: bool = True,
    show_container: bool = True,
) -> None:
    # renderizo o painel executivo de rca no padrao sleek dark
    if not collab_info:
        collab_info = {}

    status_val = collab_info.get("status")
    conversation = collab_info.get("conversation") or []
    supervisor_decision = collab_info.get("supervisor_decision") or ""

    if conversation:
        is_refined = status_val == "consenso_refinado" or len(conversation) > 2
        badge_text = "MITIGAÇÃO REFINADA (2 CICLOS)" if is_refined else "AUTOMAÇÃO DIRETA (1 CICLO)"
        badge_style = (
            "background: rgba(245, 158, 11, 0.12); color: #FCD34D; border: 1px solid rgba(245, 158, 11, 0.3);"
            if is_refined
            else "background: rgba(16, 185, 129, 0.12); color: #4ADE80; border: 1px solid rgba(16, 185, 129, 0.3);"
        )

        stages_html = []
        for idx, turn in enumerate(conversation, 1):
            speaker = str(turn.get("speaker", "Agente"))
            role = str(turn.get("role", "etapa"))
            msg = str(turn.get("message", ""))
            action = str(turn.get("action_taken", ""))

            label_name, text_color, tag_bg, border_color, svg_icon = _agent_meta(speaker)
            role_label = _translate_role_label(role, action)

            stages_html.append(
                f"""<div style="display: flex; gap: 0.75rem; padding: 0.8rem 1rem; border-left: 3px solid #FAFAFA; background: #16161A; border-radius: 0 6px 6px 0; border-top: 1px solid #27272A; border-right: 1px solid #27272A; border-bottom: 1px solid #27272A;">
<div style="flex-shrink: 0; margin-top: 2px;">{svg_icon}</div>
<div style="flex-grow: 1;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem; flex-wrap: wrap; gap: 0.35rem;">
<span style="font-size: 0.82rem; font-weight: 700; color: #FAFAFA; font-family: var(--font-ui, sans-serif);">{label_name}</span>
<span style="font-size: 0.68rem; font-weight: 600; padding: 2px 7px; border-radius: 4px; background: {tag_bg}; color: {text_color}; border: 1px solid #27272A;">Ciclo {idx} • {role_label}</span>
</div>
<p style="margin: 0; font-size: 0.84rem; line-height: 1.5; color: #A1A1AA;">{_safe(msg)}</p>
</div>
</div>"""
            )

        content_html = f"""<div style="background: #111114; border: 1px solid #27272A; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem; border-bottom: 1px solid #27272A; padding-bottom: 0.55rem;">
<div style="display: flex; align-items: center; gap: 0.5rem;">
<span style="font-weight: 700; font-size: 0.92rem; color: #FAFAFA; font-family: var(--font-ui, sans-serif);">{_safe(title)}</span>
{f'<code style="font-size: 0.74rem; background: #18181B; padding: 2px 6px; border-radius: 4px; color: #A1A1AA; border: 1px solid #27272A;">#{_safe(run_id[:12])}</code>' if run_id else ''}
</div>
<span style="font-size: 0.7rem; font-weight: 700; padding: 3px 8px; border-radius: 4px; letter-spacing: 0.02em; {badge_style}">{badge_text}</span>
</div>
<div style="background: #18181B; border: 1px solid #27272A; border-left: 3px solid #FAFAFA; border-radius: 0 6px 6px 0; padding: 0.65rem 0.95rem; margin-bottom: 0.85rem;">
<div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: #FAFAFA; margin-bottom: 0.2rem;">
Homologação e Despacho do Supervisor
</div>
<p style="margin: 0; font-size: 0.85rem; color: #F4F4F5; line-height: 1.45; font-weight: 500;">{_safe(supervisor_decision or 'Consenso operacional validado e homologado com os agentes especialistas.')}</p>
</div>
<div style="display: flex; flex-direction: column; gap: 0.65rem;">
{''.join(stages_html)}
</div>
</div>"""

        _render_html(content_html)

    elif supervisor_decision or status_val:
        is_refined = status_val == "consenso_refinado"
        badge_text = "MITIGAÇÃO REFINADA" if is_refined else "AUTOMAÇÃO DIRETA"
        badge_style = (
            "background: rgba(245, 158, 11, 0.12); color: #FCD34D; border: 1px solid rgba(245, 158, 11, 0.3);"
            if is_refined
            else "background: rgba(16, 185, 129, 0.12); color: #4ADE80; border: 1px solid rgba(16, 185, 129, 0.3);"
        )

        content_html = f"""<div style="background: #111114; border: 1px solid #27272A; border-radius: 8px; padding: 0.95rem 1.2rem; margin-bottom: 1rem; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem; flex-wrap: wrap; gap: 0.4rem;">
<span style="font-weight: 700; font-size: 0.90rem; color: #FAFAFA;">{_safe(title)}</span>
<span style="font-size: 0.7rem; font-weight: 700; padding: 2px 7px; border-radius: 4px; {badge_style}">{badge_text}</span>
</div>
<p style="margin: 0; font-size: 0.85rem; color: #A1A1AA; line-height: 1.45;">{_safe(supervisor_decision or 'Consenso multiagente validado com sucesso.')}</p>
</div>"""
        _render_html(content_html)

    else:
        content_html = """<div style="background: #111114; border: 1px dashed #3F3F46; border-radius: 8px; padding: 0.95rem 1.2rem; margin-bottom: 1rem;">
<div style="font-size: 0.84rem; font-weight: 600; color: #E4E4E7; margin-bottom: 0.25rem;">
Trilha de Governança e RCA
</div>
<p style="margin: 0; font-size: 0.82rem; color: #71717A; line-height: 1.45;">
Esta execução foi registrada sem log detalhado de estágios de RCA. Execute um novo cenário no <b>Simulador</b> para visualizar o fluxo completo de diagnóstico e mitigação em tempo real.
</p>
</div>"""
        _render_html(content_html)
