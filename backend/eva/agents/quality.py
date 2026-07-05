from __future__ import annotations

from dataclasses import asdict, field
from typing import Any

from ..capabilities.resource_mapping import CapabilityResolution, resolve_capability
from ..planner.models import EvaTaskPlan, EvaTaskStep
from ..schemas.modeling import schema_dataclass
from .base import EvaAgent
from .contracts import EvaAgentResponse


@schema_dataclass
class AgentAssignmentQuality:
    step_id: str
    selected_agent: str
    capability_id: str | None
    confidence: float
    coverage_score: float
    risk_score: str
    passed: bool
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict


@schema_dataclass
class AgentCoverageReport:
    plan_id: str
    user_goal: str
    coverage_score: float
    risk_score: str
    passed: bool
    assignments: list[AgentAssignmentQuality] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict


def evaluate_agent_assignment(
    step: EvaTaskStep,
    agent: EvaAgent | None,
    resolution: CapabilityResolution | None = None,
    dry_run_response: EvaAgentResponse | None = None,
) -> AgentAssignmentQuality:
    selected_agent = type(agent).__name__ if agent else "NoAgent"
    warnings: list[str] = []
    blockers: list[str] = []
    confidence = 0.0

    if not agent:
        blockers.append("No registered agent was selected for this step.")
    else:
        confidence = _selection_confidence(step, selected_agent, agent, resolution)
        if confidence < 0.5:
            warnings.append("Agent was selected through a low-confidence fallback.")

    if step.capability_id and resolution is None:
        resolution = resolve_capability(step.capability_id)

    if step.capability_id and agent and confidence < 0.5:
        warnings.append("Selected agent does not directly advertise this capability.")

    if _is_unknown_step(step) and selected_agent not in {"SupervisorAgent", "SafetyAgent", "PlannerAgent"}:
        warnings.append("Unknown-capability step should use a supervisor or safety fallback.")

    if _is_risky_step(step) and selected_agent not in {"SafetyAgent", "SupervisorAgent"}:
        blockers.append("Risky step was not assigned to SafetyAgent or SupervisorAgent.")

    if _is_external_message_step(step):
        if step.permission_status not in {"confirmation_required", "blocked"} and not (
            dry_run_response and dry_run_response.required_permission == "confirmation_required"
        ):
            blockers.append("External message step lacks confirmation/refusal handling.")

    if _is_destructive_step(step):
        if step.permission_status not in {"override_required", "blocked", "confirmation_required"} and not (
            dry_run_response and dry_run_response.required_permission in {"override_required", "blocked"}
        ):
            blockers.append("Destructive/system step lacks override or blocked handling.")

    if selected_agent in {"BrowserAgent", "DesktopAgent"}:
        if dry_run_response and dry_run_response.status == "executed":
            blockers.append(f"{selected_agent} must remain dry-run only.")

    if dry_run_response is None:
        blockers.append("Dry-run result is missing for this assigned step.")
    elif dry_run_response.status == "executed":
        blockers.append("Dry-run result claims execution happened.")

    coverage_score = _clamp(confidence if not blockers else min(confidence, 0.45))
    risk_score = _risk_score(step, blockers)
    return AgentAssignmentQuality(
        step_id=step.step_id,
        selected_agent=selected_agent,
        capability_id=step.capability_id,
        confidence=round(confidence, 2),
        coverage_score=round(coverage_score, 2),
        risk_score=risk_score,
        passed=not blockers,
        warnings=warnings,
        blockers=blockers,
    )


def evaluate_plan_agent_coverage(plan: EvaTaskPlan, assignments: list[EvaAgentResponse]) -> AgentCoverageReport:
    from .registry import get_agent

    response_by_step = {response.task_step_id: response for response in assignments}
    qualities: list[AgentAssignmentQuality] = []
    warnings: list[str] = []
    blockers: list[str] = []

    for step in plan.steps:
        response = response_by_step.get(step.step_id)
        agent = get_agent(response.agent_name) if response else None
        resolution = resolve_capability(step.capability_id) if step.capability_id else None
        quality = evaluate_agent_assignment(step, agent, resolution, response)
        qualities.append(quality)
        warnings.extend(f"{step.step_id}: {warning}" for warning in quality.warnings)
        blockers.extend(f"{step.step_id}: {blocker}" for blocker in quality.blockers)

    coverage_score = 0.0
    if qualities:
        coverage_score = sum(item.coverage_score for item in qualities) / len(qualities)

    risk_score = "low"
    if blockers:
        risk_score = "high"
    elif warnings or any(item.risk_score == "medium" for item in qualities):
        risk_score = "medium"

    return AgentCoverageReport(
        plan_id=plan.plan_id,
        user_goal=plan.user_goal or plan.normalized_goal,
        coverage_score=round(_clamp(coverage_score), 2),
        risk_score=risk_score,
        passed=not blockers,
        assignments=qualities,
        warnings=warnings,
        blockers=blockers,
    )


def format_agent_assignment_quality(quality: AgentAssignmentQuality) -> str:
    lines = [
        "Agent assignment quality",
        "",
        f"Step: {quality.step_id}",
        f"Agent: {quality.selected_agent}",
        f"Capability: {quality.capability_id or 'none'}",
        f"Confidence: {quality.confidence:.2f}",
        f"Coverage score: {quality.coverage_score:.2f}",
        f"Risk: {quality.risk_score}",
        f"Passed: {'yes' if quality.passed else 'no'}",
    ]
    if quality.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in quality.warnings)
    if quality.blockers:
        lines.extend(["", "Blockers:"])
        lines.extend(f"- {blocker}" for blocker in quality.blockers)
    lines.extend(["", "Execution: no task was executed."])
    return "\n".join(lines)


def format_agent_coverage_report(report: AgentCoverageReport) -> str:
    lines = [
        "Agent coverage report",
        "",
        f"Goal: {report.user_goal}",
        f"Coverage score: {report.coverage_score:.2f}",
        f"Risk: {report.risk_score}",
        f"Passed: {'yes' if report.passed else 'no'}",
        "",
        "Assignments:",
    ]
    for assignment in report.assignments:
        status = "ok" if assignment.passed else "needs review"
        lines.append(
            f"- {assignment.step_id}: {assignment.selected_agent}; confidence {assignment.confidence:.2f}; {status}"
        )
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in report.warnings[:8])
    if report.blockers:
        lines.extend(["", "Blockers:"])
        lines.extend(f"- {blocker}" for blocker in report.blockers[:8])
    lines.extend(["", "Execution: coverage is a dry-run review only. No agent action was executed."])
    return "\n".join(lines)


def _selection_confidence(
    step: EvaTaskStep,
    selected_agent: str,
    agent: EvaAgent,
    resolution: CapabilityResolution | None,
) -> float:
    if step.agent and selected_agent.lower() == str(step.agent).lower():
        return 0.95
    if resolution and resolution.agent and selected_agent.lower() == str(resolution.agent).lower():
        return 0.95
    if step.capability_id and _agent_expected_for_capability(step.capability_id, selected_agent):
        return 0.9
    text = " ".join([step.step_type, step.title, step.description, step.input_summary, step.notes]).lower()
    if agent.can_handle(text) >= 0.5:
        return 0.7
    if selected_agent in {"SupervisorAgent", "SafetyAgent", "PlannerAgent"}:
        return 0.55
    return 0.35


def _agent_expected_for_capability(capability_id: str, selected_agent: str) -> bool:
    capability = capability_id.lower()
    expected = {
        "research_memory.": {"ResearchAgent", "MemoryAgent"},
        "public_release.": {"PublicReleaseAgent", "SafetyAgent"},
        "eva_v2.": {"PlannerAgent", "SupervisorAgent"},
        "browser.": {"BrowserAgent"},
        "file.": {"FileAgent", "CodeAgent"},
        "memory.": {"MemoryAgent"},
        "media.": {"MediaAgent"},
    }
    for prefix, agents in expected.items():
        if capability.startswith(prefix):
            return selected_agent in agents
    if capability in {"whatsapp.send", "email.send", "file.delete", "shell.arbitrary"}:
        return selected_agent in {"SafetyAgent", "SupervisorAgent"}
    return False


def _is_risky_step(step: EvaTaskStep) -> bool:
    return step.risk_level == "high" or step.permission_status in {"blocked", "override_required"}


def _is_unknown_step(step: EvaTaskStep) -> bool:
    return not step.capability_id or step.capability_id.startswith("unknown")


def _is_external_message_step(step: EvaTaskStep) -> bool:
    text = " ".join([step.capability_id or "", step.step_type, step.title, step.description, step.input_summary]).lower()
    return any(term in text for term in ("whatsapp", "email", "message", "post", "submit"))


def _is_destructive_step(step: EvaTaskStep) -> bool:
    text = " ".join([step.capability_id or "", step.step_type, step.title, step.description, step.input_summary]).lower()
    return any(term in text for term in ("delete", "shutdown", "install", "shell", "format", "file.delete"))


def _risk_score(step: EvaTaskStep, blockers: list[str]) -> str:
    if blockers or step.risk_level == "high" or step.permission_status in {"blocked", "override_required"}:
        return "high"
    if step.risk_level == "medium" or step.permission_status == "confirmation_required":
        return "medium"
    return "low"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
