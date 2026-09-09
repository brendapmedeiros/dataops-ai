"""DataOps AI Dashboard"""

from dashboard.components.header import render_cockpit_header
from dashboard.components.overview import render_overview_tab
from dashboard.components.incidents import render_incidents_tab
from dashboard.components.quarantine import render_quarantine_tab
from dashboard.components.data_viewer import render_data_viewer_tab
from dashboard.components.console import render_simulation_tab, render_action_console, render_run_inline_result
from dashboard.components.hero import render_hero_card
from dashboard.components.metrics import render_bento_metrics
from dashboard.components.telemetry import render_ecg_telemetry
from dashboard.components.audit import render_audit_drawer

__all__ = [
    "render_cockpit_header",
    "render_overview_tab",
    "render_incidents_tab",
    "render_quarantine_tab",
    "render_data_viewer_tab",
    "render_simulation_tab",
    "render_action_console",
    "render_run_inline_result",
    "render_hero_card",
    "render_bento_metrics",
    "render_ecg_telemetry",
    "render_audit_drawer",
]
