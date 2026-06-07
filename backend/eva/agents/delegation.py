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


def dry_run_plan_with_agents(plan: EvaTaskPlan) -> AgentDryRunResult:
    responses = [dry_run_step_with_agent(plan, step) for step in plan.steps]
    return AgentDryRunResult(plan_id=plan.plan_id, user_goal=plan.user_goal or plan.normalized_goal, responses=responses)


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
    lines.extend(["", "Execution:", "No task was executed. This was an Agent Framework v1 dry-run only."])
    return "\n".join(lines)


def format_agent_dry_run_for_goal(goal_text: str) -> str:
    plan = create_task_plan(goal_text)
    result = dry_run_plan_with_agents(plan)
    return format_agent_dry_run_result(result)

