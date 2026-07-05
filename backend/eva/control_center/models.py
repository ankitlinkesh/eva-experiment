from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ControlCenterStatus:
    app_name: str
    phase: str
    authority_summary: dict[str, object]
    natural_router_summary: dict[str, object]
    llm_router_summary: dict[str, object]
    llm_validation_summary: dict[str, object]
    llm_red_team_summary: dict[str, object]
    context_engine_summary: dict[str, object]
    threat_defense_summary: dict[str, object]
    agent_loop_summary: dict[str, object]
    workflow_planner_summary: dict[str, object]
    execution_gates_summary: dict[str, object]
    memory_v3_summary: dict[str, object]
    voice_assistant_summary: dict[str, object]
    ai_os_summary: dict[str, object]
    browser_readonly_summary: dict[str, object]
    desktop_observation_mode_summary: dict[str, object]
    desktop_control_gate_summary: dict[str, object]
    news_dashboard_summary: dict[str, object]
    coding_agent_summary: dict[str, object]
    release_demo_summary: dict[str, object]
    release_candidate_summary: dict[str, object]
    file_agent_summary: dict[str, object]
    approval_summary: dict[str, object]
    sandbox_apply_summary: dict[str, object]
    real_apply_summary: dict[str, object]
    golden_workflow_summary: dict[str, object]
    phase12_health_summary: dict[str, object]
    browser_agent_summary: dict[str, object]
    browser_session_summary: dict[str, object]
    browser_observation_summary: dict[str, object]
    browser_action_summary: dict[str, object]
    browser_domain_summary: dict[str, object]
    browser_readiness_proof_summary: dict[str, object]
    desktop_agent_summary: dict[str, object]
    desktop_session_summary: dict[str, object]
    desktop_screen_summary: dict[str, object]
    desktop_action_summary: dict[str, object]
    desktop_risk_summary: dict[str, object]
    desktop_approval_summary: dict[str, object]
    desktop_readiness_proof_summary: dict[str, object]
    capability_summary: dict[str, object]
    specialist_summary: dict[str, object]
    skill_summary: dict[str, object]
    workflow_summary: dict[str, object]
    latest_workflow_summary: dict[str, object]
    work_session_summary: dict[str, object]
    project_reality_summary: dict[str, object]
    locked_feature_summary: dict[str, object]
    agent_summary: dict[str, object]
    planner_summary: dict[str, object]
    verifier_summary: dict[str, object]
    safety_summary: dict[str, object]
    future_modules: list[dict[str, object]]
    warnings: list[str] = field(default_factory=list)
    generated_at: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def unavailable_summary(name: str, reason: str = "Not configured") -> dict[str, object]:
    return {
        "name": name,
        "status": "Unavailable",
        "summary": reason,
    }
