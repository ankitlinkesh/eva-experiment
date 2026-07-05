from __future__ import annotations

from ..planner.capability_selector import select_capabilities_for_goal


def select_loop_capabilities(request: str) -> tuple[str, ...]:
    selected = tuple(select_capabilities_for_goal(request))
    return selected or ("agent_loop.run_preview",)


def preview_plan_steps(request: str, selected_capabilities: tuple[str, ...], *, blocked: bool) -> tuple[str, ...]:
    if blocked:
        return (
            "receive request",
            "assemble safe context preview",
            "run threat-defense preview",
            "create refusal or blocked-action preview",
            "verify no execution",
            "produce final blocked status",
        )
    capability_text = ", ".join(selected_capabilities)
    return (
        "receive request",
        "classify route intent",
        "assemble safe context preview",
        "run threat-defense preview",
        f"create bounded plan preview for {capability_text}",
        "create action previews only",
        "create mock observations only",
        "verify plan/action safety",
        "produce final status/report",
        "stop safely",
    )
