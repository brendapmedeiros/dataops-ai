"""Minimalist fine-line SVG iconography for DataOps AI Dashboard.

Clean, refined, editorial line vectors designed for minimal, high-clarity interfaces.
"""

from __future__ import annotations


def icon_shield(size: int = 16, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        '</svg>'
    )


def icon_shield_check(size: int = 16, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        '<path d="m9 12 2 2 4-4"/>'
        '</svg>'
    )


def icon_shield_alert(size: int = 16, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        '<line x1="12" y1="8" x2="12" y2="12"/>'
        '<line x1="12" y1="16" x2="12.01" y2="16"/>'
        '</svg>'
    )


def icon_alert_triangle(size: int = 16, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/>'
        '<line x1="12" y1="17" x2="12.01" y2="17"/>'
        '</svg>'
    )


def icon_database(size: int = 16, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
        '<path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>'
        '<path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>'
        '</svg>'
    )


def icon_terminal(size: int = 16, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<polyline points="4 17 10 11 4 5"/>'
        '<line x1="12" y1="19" x2="20" y2="19"/>'
        '</svg>'
    )


def icon_box(size: int = 16, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
        '<polyline points="3.27 6.96 12 12.01 20.73 6.96"/>'
        '<line x1="12" y1="22.08" x2="12" y2="12"/>'
        '</svg>'
    )


def icon_check(size: int = 15, color: str = "currentColor", stroke_width: float = 1.6) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<polyline points="20 6 9 17 4 12"/>'
        '</svg>'
    )


def icon_x(size: int = 15, color: str = "currentColor", stroke_width: float = 1.6) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<line x1="18" y1="6" x2="6" y2="18"/>'
        '<line x1="6" y1="6" x2="18" y2="18"/>'
        '</svg>'
    )


def icon_activity(size: int = 16, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'
        '</svg>'
    )


def icon_cpu(size: int = 16, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<rect x="4" y="4" width="16" height="16" rx="3"/>'
        '<rect x="9" y="9" width="6" height="6" rx="1"/>'
        '<path d="M9 1v3"/><path d="M15 1v3"/><path d="M9 20v3"/><path d="M15 20v3"/>'
        '<path d="M20 9h3"/><path d="M20 14h3"/><path d="M1 9h3"/><path d="M1 14h3"/>'
        '</svg>'
    )


def icon_lock(size: int = 15, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<rect x="3" y="11" width="18" height="11" rx="3" ry="3"/>'
        '<path d="M7 11V7a5 5 0 0 1 10 0v4"/>'
        '</svg>'
    )


def icon_hash(size: int = 15, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<line x1="4" y1="9" x2="20" y2="9"/>'
        '<line x1="4" y1="15" x2="20" y2="15"/>'
        '<line x1="10" y1="3" x2="8" y2="21"/>'
        '<line x1="16" y1="3" x2="14" y2="21"/>'
        '</svg>'
    )


def icon_zap(size: int = 16, color: str = "currentColor", stroke_width: float = 1.4) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
        '</svg>'
    )


def icon_arrow_right(size: int = 15, color: str = "currentColor", stroke_width: float = 1.5) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align: middle; display: inline-block;">'
        '<line x1="5" y1="12" x2="19" y2="12"/>'
        '<polyline points="12 5 19 12 12 19"/>'
        '</svg>'
    )
