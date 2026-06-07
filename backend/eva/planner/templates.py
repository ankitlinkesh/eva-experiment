from __future__ import annotations

from dataclasses import asdict, field

from ..schemas.modeling import schema_dataclass
from .models import EvaTaskStep


@schema_dataclass
class PlanTemplate:
    template_id: str
    name: str
    description: str
    triggers: list[str]
    step_specs: list[dict[str, str]]
    safety_notes: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    model_dump = as_dict


def get_plan_templates() -> list[PlanTemplate]:
    return [
        PlanTemplate(
            template_id="saved_research_summary",
            name="Saved Research Summary",
            description="Retrieve local Research Memory notes and plan a concise summary.",
            triggers=["use my saved research", "summarize what i saved", "research memory", "my research"],
            step_specs=[
                _spec("Retrieve relevant local research", "retrieve_memory", "research_memory.retrieve", "ResearchAgent", "Relevant local snippets."),
                _spec("Summarize retrieved notes", "draft_content", "eva_v2.plan_preview", "PlannerAgent", "Summary outline."),
                _spec("State source limitations", "verification", None, "VerifierAgent", "Limitations and next search/export options."),
            ],
            safety_notes="Local Research Memory only. No private page scraping or cloud summarization.",
        ),
        PlanTemplate(
            template_id="public_demo_safety",
            name="Public Demo Safety",
            description="Preview public demo or safety-simulator behavior without execution.",
            triggers=["safety test", "demo unsafe", "public demo", "public release"],
            step_specs=[
                _spec("Classify risky request", "research", "public_release.safety_simulator", "SafetyAgent", "Risk classification."),
                _spec("Explain blocked or confirmation result", "verification", "public_release.safety_simulator", "SafetyAgent", "Safe explanation."),
                _spec("Show demo-safe alternative", "draft_content", "public_release.demo_scenarios", "SafetyAgent", "Demo-safe alternative."),
            ],
            safety_notes="Simulation only. No real browser, desktop, message, file, or system action.",
        ),
        PlanTemplate(
            template_id="coding_project_review",
            name="Coding Project Review",
            description="Plan a repo/project review or bugfix without edits or command execution.",
            triggers=["inspect project", "check repo", "fix bug", "continue project", "hackathon"],
            step_specs=[
                _spec("Identify project context and requirements", "planning", "eva_v2.plan_preview", "PlannerAgent", "Project context checklist."),
                _spec("Inspect files read-only in a future gated phase", "blocked", None, "PlannerAgent", "Read-only inspection plan."),
                _spec("Identify relevant tests or verifiers", "research", "eva_v2.plan_preview", "PlannerAgent", "Verifier checklist."),
                _spec("Plan patch boundaries", "draft_content", "eva_v2.plan_preview", "PlannerAgent", "Scoped patch plan."),
                _spec("Ask before edits or execution", "user_confirmation", None, "SafetyAgent", "Confirmation checkpoint."),
            ],
            safety_notes="Code/file actions remain preview-only here; no shell or file writes.",
        ),
        PlanTemplate(
            template_id="report_generation",
            name="Report Generation",
            description="Plan a report, summary, submission, or document without saving files.",
            triggers=["make report", "create document", "prepare submission", "write summary", "report", "submission", "summarize"],
            step_specs=[
                _spec("Gather report requirements", "planning", "eva_v2.plan_preview", "PlannerAgent", "Topic, length, audience, and format."),
                _spec("Retrieve relevant memory or research", "retrieve_memory", "research_memory.retrieve", "ResearchAgent", "Relevant local notes."),
                _spec("Draft report outline", "draft_content", "eva_v2.plan_preview", "PlannerAgent", "Report outline."),
                _spec("Draft content sections", "draft_content", "eva_v2.plan_preview", "PlannerAgent", "Section draft plan."),
                _spec("Ask before saving or exporting", "user_confirmation", None, "SafetyAgent", "File-write confirmation checkpoint."),
            ],
            safety_notes="Drafting only. Saving/exporting remains a future explicit permission-gated action.",
        ),
        PlanTemplate(
            template_id="browser_research",
            name="Browser Research",
            description="Plan public web research while keeping browser execution disabled.",
            triggers=["find latest", "search web", "compare sources", "open website", "public web"],
            step_specs=[
                _spec("Clarify public research scope", "planning", "eva_v2.plan_preview", "PlannerAgent", "Public source scope."),
                _spec("Plan public source search", "browser_open", "browser.control", "PlannerAgent", "Search plan only."),
                _spec("Collect notes if user confirms later", "local_write", "research_memory.import_note", "ResearchAgent", "Potential local note plan."),
                _spec("Compare source reliability", "verification", "eva_v2.plan_preview", "VerifierAgent", "Source comparison criteria."),
            ],
            safety_notes="Browser control is not enabled in this phase. Private/logged-in scraping remains refused.",
        ),
        PlanTemplate(
            template_id="external_message",
            name="External Message",
            description="Draft an external message and require confirmation before any future send.",
            triggers=["send whatsapp", "send email", "post", "submit form", "message"],
            step_specs=[
                _spec("Draft message content", "draft_content", None, "SafetyAgent", "Message draft preview."),
                _spec("Require explicit send confirmation", "user_confirmation", "whatsapp.send", "SafetyAgent", "Confirmation checkpoint."),
                _spec("Keep send step unavailable", "blocked", "whatsapp.send", "SafetyAgent", "No send execution in this phase."),
            ],
            safety_notes="No message is sent. Sending remains unavailable and confirmation-gated.",
        ),
        PlanTemplate(
            template_id="destructive_or_system_action",
            name="Destructive Or System Action",
            description="Detect destructive/system risk and keep execution blocked.",
            triggers=["delete", "format", "shutdown", "install", "run powershell", "change settings", "run shell"],
            step_specs=[
                _spec("Detect destructive or system risk", "blocked", "file.delete", "SafetyAgent", "Risk classification."),
                _spec("Require future override and checkpoint", "user_confirmation", "file.delete", "SafetyAgent", "Override/checkpoint requirement."),
                _spec("Suggest safe dry-run alternative", "draft_content", "eva_v2.plan_preview", "PlannerAgent", "Safe preview alternative."),
            ],
            safety_notes="No delete, shell, install, shutdown, or settings change is executed.",
        ),
    ]


def get_template_for_goal(goal_text: str) -> PlanTemplate | None:
    text = _normalize(goal_text)
    best: PlanTemplate | None = None
    best_hits = 0
    for template in get_plan_templates():
        hits = sum(1 for trigger in template.triggers if trigger in text)
        if hits > best_hits:
            best = template
            best_hits = hits
    return best if best_hits else None


def apply_template_to_goal(goal_text: str, template_id: str | None = None) -> list[EvaTaskStep]:
    template = _get_template_by_id(template_id) if template_id else get_template_for_goal(goal_text)
    if not template:
        return []
    steps: list[EvaTaskStep] = []
    for spec in template.step_specs:
        depends_on = [steps[-1].step_id] if steps else []
        permission = _permission_for_step(spec["step_type"], spec.get("capability_id"))
        availability = _availability_for_step(spec["step_type"], spec.get("capability_id"))
        risk = _risk_for_step(spec["step_type"], permission)
        steps.append(
            EvaTaskStep(
                step_id=f"template_{len(steps) + 1}",
                title=spec["title"],
                description=spec["description"],
                step_type=spec["step_type"],
                capability_id=spec.get("capability_id") or None,
                resource_id=None,
                agent=spec.get("agent") or "PlannerAgent",
                input_summary=_summarize_goal(goal_text),
                expected_output=spec["expected_output"],
                risk_level=risk,
                permission_status=permission,
                availability_status=availability,
                depends_on=depends_on,
                notes=f"Template: {template.template_id}. {template.safety_notes}",
            )
        )
    return steps


def format_plan_templates() -> str:
    lines = ["Plan templates", "", f"Count: {len(get_plan_templates())}"]
    for template in get_plan_templates():
        lines.extend(
            [
                f"- {template.template_id}: {template.name}",
                f"  Use when: {', '.join(template.triggers[:4])}",
                f"  Safety: {template.safety_notes}",
            ]
        )
    lines.extend(["", "Scope: templates are planning metadata only. No task steps are executed."])
    return "\n".join(lines)


def _spec(title: str, step_type: str, capability_id: str | None, agent: str, expected_output: str) -> dict[str, str]:
    return {
        "title": title,
        "description": _description_for_title(title),
        "step_type": step_type,
        "capability_id": capability_id or "",
        "agent": agent,
        "expected_output": expected_output,
    }


def _description_for_title(title: str) -> str:
    descriptions = {
        "Retrieve relevant local research": "Plan retrieval from local Research Memory.",
        "Summarize retrieved notes": "Plan a concise answer from retrieved local notes.",
        "State source limitations": "Include what was and was not checked.",
        "Classify risky request": "Classify the requested action against public safety rules.",
        "Explain blocked or confirmation result": "Explain why an action is blocked or confirmation-gated.",
        "Show demo-safe alternative": "Suggest a safe demonstration path.",
        "Identify project context and requirements": "List required project, repo, and acceptance details.",
        "Inspect files read-only in a future gated phase": "Plan read-only inspection without opening files here.",
        "Identify relevant tests or verifiers": "Name the verification evidence needed later.",
        "Plan patch boundaries": "Define a scoped patch before any edits.",
        "Ask before edits or execution": "Require explicit user approval before future edits or commands.",
        "Gather report requirements": "Ask for topic, format, audience, and length.",
        "Retrieve relevant memory or research": "Plan local retrieval before drafting.",
        "Draft report outline": "Plan report sections and comparison criteria.",
        "Draft content sections": "Plan the content draft without writing a file.",
        "Ask before saving or exporting": "Require confirmation before future file creation or export.",
        "Clarify public research scope": "Clarify whether only public web sources are acceptable.",
        "Plan public source search": "Plan browser research without controlling the browser.",
        "Collect notes if user confirms later": "Plan optional Research Memory save after confirmation.",
        "Compare source reliability": "Define source comparison checks.",
        "Draft message content": "Prepare message text only.",
        "Require explicit send confirmation": "Require explicit confirmation before any future send.",
        "Keep send step unavailable": "Keep send execution unavailable in this phase.",
        "Detect destructive or system risk": "Identify destructive or system-changing intent.",
        "Require future override and checkpoint": "Require override, exact target, and rollback plan in a later executor.",
        "Suggest safe dry-run alternative": "Offer a preview-only alternative.",
    }
    return descriptions.get(title, "Plan this step without execution.")


def _get_template_by_id(template_id: str | None) -> PlanTemplate | None:
    wanted = _normalize(template_id or "")
    for template in get_plan_templates():
        if template.template_id == wanted:
            return template
    return None


def _normalize(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _summarize_goal(goal_text: str) -> str:
    text = " ".join(str(goal_text or "").strip().split())
    return text[:180]


def _permission_for_step(step_type: str, capability_id: str | None) -> str:
    if step_type == "user_confirmation":
        return "confirmation_required"
    if step_type == "blocked":
        return "override_required" if capability_id == "file.delete" else "blocked"
    if capability_id == "browser.control":
        return "blocked"
    return "preview_only" if step_type in {"local_write", "browser_open"} else "allowed"


def _availability_for_step(step_type: str, capability_id: str | None) -> str:
    if step_type == "blocked" or capability_id in {"browser.control", "whatsapp.send", "file.delete"}:
        return "blocked"
    return "preview_only"


def _risk_for_step(step_type: str, permission: str) -> str:
    if permission in {"blocked", "override_required"}:
        return "high"
    if permission == "confirmation_required" or step_type in {"local_write", "browser_open"}:
        return "medium"
    return "low"

