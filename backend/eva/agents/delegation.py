from __future__ import annotations

from dataclasses import asdict, field
from typing import Any

from ..planner.decomposer import create_task_plan
from ..planner.models import EvaTaskPlan, EvaTaskStep
from ..schemas.modeling import schema_dataclass
from .contracts import EvaAgentRequest, EvaAgentResponse
from .registry import select_agent_for_step


@schema_dataclass
class AgentDryRunResult:
    plan_id: str
    user_goal: str
    responses: list[EvaAgentResponse] = field(default_factory=list)
    summary: str = "Agent dry-run completed. No task was executed."
    validation: AgentDryRunValidation | None = None
    coverage_score: float | None = None
    team_review_summary: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict


@schema_dataclass
class AgentDryRunValidation:
    plan_id: str
    passed: bool
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict


def build_agent_request_from_step(plan: EvaTaskPlan, step: EvaTaskStep) -> EvaAgentRequest:
    return EvaAgentRequest(
        request_id=f"{plan.plan_id}_{step.step_id}",
        user_goal=plan.user_goal or plan.normalized_goal,
        task_step_id=step.step_id,
        capability_id=step.capability_id,
        resource_id=step.resource_id,
        input_summary=step.input_summary or step.description,
        context={
            "step_title": step.title,
            "step_type": step.step_type,
            "permission_status": step.permission_status,
            "availability_status": step.availability_status,
        },
        dry_run=True,
        execution_allowed=False,
    )


def dry_run_step_with_agent(plan: EvaTaskPlan, step: EvaTaskStep) -> EvaAgentResponse:
    agent = select_agent_for_step(step)
    request = build_agent_request_from_step(plan, step)
    if not agent:
        return EvaAgentResponse(
            agent_name="NoAgent",
            request_id=request.request_id,
            task_step_id=step.step_id,
            action="agent.dry_run",
            status="unavailable",
            summary="No registered agent matched this step.",
            capability_id=step.capability_id,
            resource_id=step.resource_id,
            next_action="Review the plan manually. No task was executed.",
        )
    response = agent.dry_run(request)
    if step.permission_status in {"confirmation_required", "override_required", "blocked"}:
        response.required_permission = step.permission_status
        response.status = "refused" if step.availability_status == "blocked" else response.status
        response.next_action = "Permission-gated or blocked step. No task was executed."
    return response


def dry_run_plan_with_agents(plan: EvaTaskPlan, include_quality: bool = True) -> AgentDryRunResult:
    responses = [dry_run_step_with_agent(plan, step) for step in plan.steps]
    validation = validate_agent_dry_run_results(plan, responses)
    result = AgentDryRunResult(
        plan_id=plan.plan_id,
        user_goal=plan.user_goal or plan.normalized_goal,
        responses=responses,
        validation=validation,
    )
    if include_quality:
        from .quality import evaluate_plan_agent_coverage
        from .team_review import review_plan_with_agent_team

        coverage = evaluate_plan_agent_coverage(plan, responses)
        result.coverage_score = coverage.coverage_score
        review = review_plan_with_agent_team(plan)
        result.team_review_summary = review.recommended_next_action
    return result


def validate_agent_dry_run_results(plan: EvaTaskPlan, dry_run_results: list[EvaAgentResponse]) -> AgentDryRunValidation:
    warnings: list[str] = []
    blockers: list[str] = []
    by_step = {response.task_step_id: response for response in dry_run_results}
    for step in plan.steps:
        response = by_step.get(step.step_id)
        if not response:
            blockers.append(f"{step.step_id}: missing dry-run result.")
            continue
        if response.status == "executed":
            blockers.append(f"{step.step_id}: dry-run result claimed execution.")
        if response.agent_name in {"BrowserAgent", "DesktopAgent"} and response.status == "executed":
            blockers.append(f"{step.step_id}: visible-control agent must remain dry-run only.")
        if step.permission_status in {"confirmation_required", "override_required", "blocked"}:
            if response.required_permission not in {"confirmation_required", "override_required", "blocked"}:
                warnings.append(f"{step.step_id}: permission-gated step lacks a matching dry-run permission marker.")
    return AgentDryRunValidation(plan_id=plan.plan_id, passed=not blockers, warnings=warnings, blockers=blockers)


def format_agent_dry_run_result(result: AgentDryRunResult) -> str:
    lines = [
        "Agent dry-run plan",
        "",
        f"Goal: {result.user_goal}",
        f"Steps: {len(result.responses)}",
        "",
        "Assignments:",
    ]
    for index, response in enumerate(result.responses, start=1):
        permission = f"; permission: {response.required_permission}" if response.required_permission else ""
        lines.extend(
            [
                f"{index}. {response.task_step_id or 'step'} -> {response.agent_name}",
                f"   Status: {response.status}{permission}",
                f"   Would do: {response.summary}",
            ]
        )
    if result.validation:
        lines.extend(["", "Validation:"])
        lines.append("Passed: yes" if result.validation.passed else "Passed: no")
        if result.validation.warnings:
            lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in result.validation.warnings[:5])
        if result.validation.blockers:
            lines.append("Blockers:")
            lines.extend(f"- {blocker}" for blocker in result.validation.blockers[:5])
    if result.coverage_score is not None:
        lines.extend(["", f"Coverage score: {result.coverage_score:.2f}"])
    if result.team_review_summary:
        lines.extend(["", "Team review:", result.team_review_summary])
    lines.extend(["", "Execution:", "No task was executed. This was an Agent Framework v1 dry-run only."])
    return "\n".join(lines)


def format_agent_dry_run_for_goal(goal_text: str) -> str:
    plan = create_task_plan(goal_text)
    result = dry_run_plan_with_agents(plan)
    return format_agent_dry_run_result(result)
