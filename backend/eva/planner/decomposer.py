from __future__ import annotations

import hashlib

from ..capabilities.permissions import get_capability_permission
from ..capabilities.resource_mapping import resolve_capability
from .capability_selector import explain_capability_selection, infer_goal_intents, select_capabilities_for_goal
from .models import EvaTaskPlan, EvaTaskStep, utc_now_iso
from .risk_review import review_plan_risks
from .templates import apply_template_to_goal, get_template_for_goal


def create_task_plan(goal_text: str, context: dict | None = None) -> EvaTaskPlan:
    normalized = _normalize(goal_text)
    capabilities = select_capabilities_for_goal(normalized)
    steps = decompose_goal(normalized)
    template = get_template_for_goal(normalized)
    if template:
        template_steps = apply_template_to_goal(normalized, template.template_id)
        if template_steps and steps:
            template_steps[0].depends_on = [steps[-1].step_id]
        steps.extend(template_steps)

    for capability_id in capabilities:
        if capability_id not in {step.capability_id for step in steps if step.capability_id}:
            steps.append(build_step_for_capability(capability_id, normalized, depends_on=[steps[-1].step_id] if steps else []))

    if _needs_browser_step(normalized) and not _has_step_type(steps, "browser_open"):
        steps.append(_future_step("browser_open", "Open browser target", "Browser or Chrome control is not enabled in Phase 10A.", "browser.control", normalized, "blocked"))
    if _needs_message_step(normalized) and not any(step.permission_status == "confirmation_required" for step in steps):
        steps.extend(_message_steps(normalized, depends_on=steps[-1].step_id if steps else None))
    if _needs_destructive_step(normalized) and not any(step.capability_id == "file.delete" for step in steps):
        steps.append(_future_step("blocked", "Block destructive or system action", "Delete, shell, install, shutdown, and system-changing actions are not executable in Planner v3 Phase 10A.", "file.delete", normalized, "override_required"))
    if _needs_file_or_document_step(normalized) and not _has_step_type(steps, "local_write"):
        steps.append(_future_step("local_write", "Draft file or document work plan", "File and document writes are future permission-gated actions; this phase only plans them.", None, normalized, "preview_only"))
    if _needs_comparison_report(normalized):
        steps.extend(_comparison_report_steps(normalized, depends_on=steps[-1].step_id if steps else None))
    if _needs_hackathon_steps(normalized) and not has_title_fragment(steps, "submission requirements"):
        steps.extend(_hackathon_steps(normalized, depends_on=steps[-1].step_id if steps else None))
    if not steps:
        steps.append(_unknown_step(normalized))

    if _should_add_verification(steps):
        steps.append(_verification_step(normalized, depends_on=steps[-1].step_id))

    steps = _assign_step_ids(steps)
    required = _dedupe([step.capability_id for step in steps if step.capability_id])
    plan = EvaTaskPlan(
        plan_id=_plan_id(normalized),
        user_goal=str(goal_text or "").strip(),
        normalized_goal=normalized,
        summary=_summary_for_goal(normalized, capabilities),
        steps=steps,
        required_capabilities=required,
        blocked_capabilities=[],
        confirmation_required=False,
        override_required=False,
        can_execute_now=False,
        preview_only=True,
        safety_summary="Planner v3 Phase 10A is planning-only.",
        next_recommended_action="Review the preview plan. No task was executed.",
        created_at=utc_now_iso(),
    )
    return review_plan_risks(plan)


def decompose_goal(goal_text: str) -> list[EvaTaskStep]:
    normalized = _normalize(goal_text)
    intents = infer_goal_intents(normalized)
    steps: list[EvaTaskStep] = [
        EvaTaskStep(
            step_id="step_1",
            title="Understand user goal",
            description="Classify the request into safe planner intents without executing anything.",
            step_type="planning",
            capability_id=None,
            resource_id=None,
            agent="PlannerAgent",
            input_summary=normalized,
            expected_output=", ".join(intents),
            risk_level="low",
            permission_status="allowed",
            availability_status="available_now",
            notes="Planning-only classification.",
        )
    ]
    return steps


def build_step_for_capability(capability_id: str, goal_text: str, depends_on: list[str] | None = None) -> EvaTaskStep:
    resolution = resolve_capability(capability_id)
    availability = _availability_from_resolution(resolution.final_status)
    permission = _permission_from_resolution(resolution)
    return EvaTaskStep(
        step_id="step_pending",
        title=_title_for_capability(resolution.capability_id),
        description=f"Use capability metadata for {resolution.capability_id}; no execution is performed.",
        step_type=_step_type_for_capability(resolution.capability_id),
        capability_id=resolution.capability_id,
        resource_id=resolution.resource_id,
        agent=resolution.agent,
        input_summary=goal_text,
        expected_output=resolution.capability_name,
        risk_level=resolution.risk_level,
        permission_status=permission,
        availability_status=availability,
        depends_on=list(depends_on or []),
        notes=resolution.reason,
    )


def enrich_step_with_resolution(step: EvaTaskStep) -> EvaTaskStep:
    if not step.capability_id:
        return step
    resolution = resolve_capability(step.capability_id)
    step.resource_id = resolution.resource_id
    step.agent = resolution.agent
    step.risk_level = resolution.risk_level
    step.permission_status = _permission_from_resolution(resolution)
    step.availability_status = _availability_from_resolution(resolution.final_status)
    step.notes = resolution.reason
    return step


def determine_plan_safety(steps: list[EvaTaskStep]) -> tuple[bool, bool, str]:
    confirmation = any(step.permission_status == "confirmation_required" for step in steps)
    override = any(step.permission_status == "override_required" for step in steps)
    blocked = any(step.permission_status == "blocked" or step.availability_status in {"blocked", "disabled", "missing"} for step in steps)
    if blocked or override:
        return confirmation, override, "Plan includes blocked or override-gated steps."
    if confirmation:
        return confirmation, override, "Plan includes confirmation-gated steps."
    return confirmation, override, "Plan is low-risk, but Phase 10A is still planning-only."


def _normalize(goal_text: str) -> str:
    return " ".join(str(goal_text or "").strip().split())


def _plan_id(goal_text: str) -> str:
    digest = hashlib.sha256(goal_text.encode("utf-8")).hexdigest()[:12]
    return f"plan_{digest}"


def _summary_for_goal(goal_text: str, capability_ids: list[str]) -> str:
    template = get_template_for_goal(goal_text)
    selection = explain_capability_selection(goal_text, capability_ids)
    if template:
        return f"Template used: {template.template_id}. {selection}"
    return selection


def _needs_browser_step(text: str) -> bool:
    text = text.lower()
    return any(term in text for term in ("open chatgpt", "open chrome", "open website", "browser", "search web"))


def _needs_message_step(text: str) -> bool:
    text = text.lower()
    return any(term in text for term in ("send whatsapp", "send email", "message ", "post ", "submit form"))


def _needs_destructive_step(text: str) -> bool:
    text = text.lower()
    return any(term in text for term in ("delete", "shutdown", "install", "run powershell", "run shell", "terminal", "remove folder"))


def _needs_file_or_document_step(text: str) -> bool:
    text = text.lower()
    return any(term in text for term in ("read file", "edit file", "make report", "create document", "write file"))


def _needs_hackathon_steps(text: str) -> bool:
    text = text.lower()
    return "hackathon" in text or "submission" in text


def _needs_comparison_report(text: str) -> bool:
    text = text.lower()
    return "compare" in text and ("report" in text or "summary" in text or "document" in text)


def _has_step_type(steps: list[EvaTaskStep], step_type: str) -> bool:
    return any(step.step_type == step_type for step in steps)


def has_title_fragment(steps: list[EvaTaskStep], fragment: str) -> bool:
    wanted = fragment.lower()
    return any(wanted in step.title.lower() or wanted in step.description.lower() for step in steps)


def _future_step(step_type: str, title: str, description: str, capability_id: str | None, goal_text: str, permission_status: str) -> EvaTaskStep:
    resource_id = None
    agent = "PlannerAgent"
    risk = "medium"
    availability = "preview_only"
    notes = "Future capability. No execution was attempted."
    if capability_id:
        permission = get_capability_permission(capability_id)
        risk = permission.risk_level
        notes = permission.reason
        if permission.blocked_by_default:
            availability = "blocked"
    return EvaTaskStep(
        step_id="step_pending",
        title=title,
        description=description,
        step_type=step_type,
        capability_id=capability_id,
        resource_id=resource_id,
        agent=agent,
        input_summary=goal_text,
        expected_output="Planner preview only.",
        risk_level=risk,
        permission_status=permission_status,
        availability_status=availability,
        notes=notes,
    )


def _message_steps(goal_text: str, depends_on: str | None) -> list[EvaTaskStep]:
    draft = EvaTaskStep(
        step_id="step_pending",
        title="Draft external message",
        description="Identify recipient and draft message content without sending.",
        step_type="draft_content",
        capability_id=None,
        resource_id=None,
        agent="SafetyAgent",
        input_summary=goal_text,
        expected_output="Message draft preview.",
        risk_level="medium",
        permission_status="allowed",
        availability_status="preview_only",
        depends_on=[depends_on] if depends_on else [],
        notes="Drafting is planning-only here.",
    )
    confirm = EvaTaskStep(
        step_id="step_pending",
        title="Require send confirmation",
        description="External messages require explicit confirmation before any future send action.",
        step_type="user_confirmation",
        capability_id="whatsapp.send" if "whatsapp" in goal_text else "email.send",
        resource_id=None,
        agent="SafetyAgent",
        input_summary=goal_text,
        expected_output="Confirmation checkpoint.",
        risk_level="high",
        permission_status="confirmation_required",
        availability_status="blocked",
        depends_on=["step_pending"],
        notes="External sending is not enabled in Phase 10A.",
    )
    return [draft, confirm]


def _hackathon_steps(goal_text: str, depends_on: str | None) -> list[EvaTaskStep]:
    first_dep = [depends_on] if depends_on else []
    return [
        EvaTaskStep(
            step_id="step_pending",
            title="Outline submission requirements",
            description="Break the submission into checklist items and required artifacts.",
            step_type="research",
            capability_id="eva_v2.plan",
            resource_id="eva-v2-runtime",
            agent="PlannerAgent",
            input_summary=goal_text,
            expected_output="Submission checklist.",
            risk_level="low",
            permission_status="allowed",
            availability_status="preview_only",
            depends_on=first_dep,
            notes="Planning-only checklist; no files are created.",
        ),
        EvaTaskStep(
            step_id="step_pending",
            title="Draft submission content",
            description="Plan content sections such as project summary, demo flow, and final checklist.",
            step_type="draft_content",
            capability_id="eva_v2.plan",
            resource_id="eva-v2-runtime",
            agent="PlannerAgent",
            input_summary=goal_text,
            expected_output="Draft outline.",
            risk_level="low",
            permission_status="allowed",
            availability_status="preview_only",
            depends_on=["step_pending"],
            notes="No document or file write occurs.",
        ),
    ]


def _comparison_report_steps(goal_text: str, depends_on: str | None) -> list[EvaTaskStep]:
    first_dep = [depends_on] if depends_on else []
    return [
        EvaTaskStep(
            step_id="step_pending",
            title="Identify comparison items and specs",
            description="List the exact models/specs to compare before drafting.",
            step_type="planning",
            capability_id="eva_v2.plan",
            resource_id="eva-v2-runtime",
            agent="PlannerAgent",
            input_summary=goal_text,
            expected_output="Comparison inputs and assumptions.",
            risk_level="low",
            permission_status="allowed",
            availability_status="preview_only",
            depends_on=first_dep,
            notes="For drone motors, ask for motor models, KV, thrust, weight, battery voltage, and prop size.",
        ),
        EvaTaskStep(
            step_id="step_pending",
            title="Compare technical criteria",
            description="Compare thrust, efficiency, weight, battery voltage, prop compatibility, and constraints.",
            step_type="draft_content",
            capability_id="eva_v2.plan",
            resource_id="eva-v2-runtime",
            agent="PlannerAgent",
            input_summary=goal_text,
            expected_output="Comparison matrix outline.",
            risk_level="low",
            permission_status="allowed",
            availability_status="preview_only",
            depends_on=["step_pending"],
            notes="Planning-only comparison criteria; no web search or file write happens here.",
        ),
        EvaTaskStep(
            step_id="step_pending",
            title="Draft report recommendation structure",
            description="Plan report sections for findings, tradeoffs, recommendation, and assumptions.",
            step_type="draft_content",
            capability_id="eva_v2.plan",
            resource_id="eva-v2-runtime",
            agent="PlannerAgent",
            input_summary=goal_text,
            expected_output="Report recommendation outline.",
            risk_level="low",
            permission_status="allowed",
            availability_status="preview_only",
            depends_on=["step_pending"],
            notes="Ask before saving or exporting any report.",
        ),
    ]


def _unknown_step(goal_text: str) -> EvaTaskStep:
    return EvaTaskStep(
        step_id="step_1",
        title="Create safe preview-only plan",
        description="No registered safe capability directly matched the goal.",
        step_type="blocked",
        capability_id=None,
        resource_id=None,
        agent="PlannerAgent",
        input_summary=goal_text,
        expected_output="Ask for a more specific capability or use a preview command.",
        risk_level="medium",
        permission_status="unknown",
        availability_status="preview_only",
        notes="Unknown capabilities are not executed.",
    )


def _verification_step(goal_text: str, depends_on: str) -> EvaTaskStep:
    return EvaTaskStep(
        step_id="step_pending",
        title="Verify planned outcome",
        description="Define what evidence would prove the task succeeded in a later executor phase.",
        step_type="verification",
        capability_id=None,
        resource_id=None,
        agent="VerifierAgent",
        input_summary=goal_text,
        expected_output="Verification criteria.",
        risk_level="low",
        permission_status="allowed",
        availability_status="preview_only",
        depends_on=[depends_on],
        notes="Verification criteria only; no observation is performed.",
    )


def _should_add_verification(steps: list[EvaTaskStep]) -> bool:
    return bool(steps) and steps[-1].step_type != "verification"


def _title_for_capability(capability_id: str) -> str:
    return capability_id.replace("_", " ").replace(".", " ").title()


def _step_type_for_capability(capability_id: str) -> str:
    if capability_id.startswith("research_memory."):
        if capability_id in {"research_memory.import_note", "research_memory.export_json"}:
            return "local_write"
        return "retrieve_memory"
    if capability_id.startswith("public_release."):
        return "research"
    if capability_id.startswith("eva_v2."):
        return "draft_content"
    return "research"


def _availability_from_resolution(final_status: str) -> str:
    if final_status in {"available_read_only", "available_explicit_local_write"}:
        return "available_now"
    if final_status == "disabled_experimental":
        return "disabled"
    if final_status == "reference_only":
        return "reference_only"
    if final_status in {"blocked", "unknown"}:
        return "blocked"
    if final_status == "resource_missing":
        return "missing"
    return "preview_only"


def _permission_from_resolution(resolution: object) -> str:
    if resolution.requires_override:
        return "override_required"
    if resolution.requires_confirmation:
        return "confirmation_required"
    if resolution.final_status in {"blocked", "unknown", "disabled_experimental", "reference_only"}:
        return "blocked"
    if resolution.final_status == "preview_only":
        return "preview_only"
    return "allowed"


def _dedupe(items: list[str | None]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item and item not in output:
            output.append(item)
    return output


def _assign_step_ids(steps: list[EvaTaskStep]) -> list[EvaTaskStep]:
    old_to_new: dict[str, str] = {}
    for index, step in enumerate(steps, start=1):
        old_id = step.step_id
        new_id = f"step_{index}"
        if old_id not in old_to_new:
            old_to_new[old_id] = new_id
        step.step_id = new_id
    for step in steps:
        step.depends_on = [old_to_new.get(dep, dep) for dep in step.depends_on if dep]
    return steps
