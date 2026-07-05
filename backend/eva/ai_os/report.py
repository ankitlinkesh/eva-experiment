from __future__ import annotations

from .models import AIOSDashboard
from .safety_boundaries import boundary_lines


def _list_text(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else "none"


def format_dashboard(dashboard: AIOSDashboard) -> str:
    return "\n".join(
        [
            "Eva AI OS dashboard",
            *boundary_lines(),
            f"Dashboard ID: {dashboard.dashboard_id}.",
            f"Current phase: {dashboard.current_phase}.",
            f"Overall readiness: {dashboard.overall_readiness}.",
            f"Master verification: {dashboard.master_verification_summary}",
            f"Phase health: {dashboard.phase_health_summary}",
            f"System map: {dashboard.system_map_summary}",
            f"Capability matrix: {dashboard.capability_matrix_summary}",
            f"Preview-only features: {_list_text(dashboard.preview_only_features)}.",
            f"Existing narrow real gate: {dashboard.existing_narrow_real_gate_summary}",
            f"Locked future gates: {_list_text(dashboard.locked_future_gates)}.",
            f"Blocked action classes: {_list_text(dashboard.blocked_action_classes)}.",
            f"Safety boundaries: {dashboard.safety_boundary_summary}",
            f"Recent limitations: {dashboard.recent_limitation_summary}",
            f"Next recommended safe step: {dashboard.next_recommended_safe_step}",
        ]
    )
