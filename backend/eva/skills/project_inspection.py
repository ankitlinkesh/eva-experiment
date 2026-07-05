from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ProjectInspectionResult:
    project_summary: str
    current_phase: str
    key_systems: tuple[str, ...]
    key_files: tuple[str, ...]
    recent_completed_phases: tuple[str, ...]
    verifier_status: str
    enabled: tuple[str, ...]
    blocked: tuple[str, ...]
    risks_unknowns: tuple[str, ...]
    next_recommended_step: str
    read_only: bool = True
    evidence_sources: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def inspect_project_status() -> ProjectInspectionResult:
    from ..file_agent.project_inventory import build_project_inventory
    from ..skills.workflow_state import summarize_fileagent_workflow_state

    inventory = build_project_inventory(".", max_files=240, max_depth=4)
    workflow = summarize_fileagent_workflow_state()
    key_files = _inventory_key_files(inventory)
    key_systems = _key_systems(inventory)
    project_summary = _project_summary(inventory)
    return ProjectInspectionResult(
        project_summary=project_summary,
        current_phase="Phase 12O: Project Inspection + Reality Checker Workflow",
        key_systems=tuple(key_systems),
        key_files=tuple(key_files),
        recent_completed_phases=(
            "12G authority/router and `eva ask` safe routing",
            "12H Control Center dashboard skeleton",
            "12L narrow real create-new-text-file gate",
            "12M/12N golden workflow and workflow-state UX stabilization",
            "12O read-only project inspection and reality-check routing",
        ),
        verifier_status="Quick/full verifier commands are available; fresh pass/fail proof requires running them in the terminal.",
        enabled=(
            "read-only project inventory and explanation",
            "natural `eva ask` status/proof routing",
            "FileAgent draft, approval, sandbox, verify, rollback metadata",
            "narrow real create-new-text-file gate after exact confirmation",
            "Control Center read-only status summaries",
        ),
        blocked=(
            "broad file edits, overwrites, source edits, and arbitrary deletes",
            "browser and desktop control",
            "MCP, Playwright, PyAutoGUI, terminal execution, package installs, and cloud calls",
            "external sending/posting/submitting",
            "normal chat routing through v2 by default",
        ),
        risks_unknowns=(
            "latest verifier results are not known until the verifier sweep is run",
            "uncommitted local work may include earlier Phase 12 changes",
            workflow.safe_next_action,
        ),
        next_recommended_step="Phase 12P: evidence-backed checkpoint/readiness polish before any broader executor unlock.",
        evidence_sources=(
            "FileAgent project inventory",
            "Phase 12 status helpers",
            "workflow-state summary",
            "Control Center status surfaces",
        ),
    )


def format_project_inspection(result: ProjectInspectionResult | None = None) -> str:
    result = result or inspect_project_status()
    return "\n".join(
        [
            "Project inspection",
            "",
            "Summary:",
            result.project_summary,
            "",
            f"Current phase: {result.current_phase}",
            "",
            "Key systems:",
            *_bullets(result.key_systems),
            "",
            "Key files and folders:",
            *_bullets(result.key_files),
            "",
            "Recent completed phases:",
            *_bullets(result.recent_completed_phases),
            "",
            "Verifier status:",
            result.verifier_status,
            "",
            "Enabled now:",
            *_bullets(result.enabled),
            "",
            "Still blocked:",
            *_bullets(result.blocked),
            "",
            "Risks or unknowns:",
            *_bullets(result.risks_unknowns),
            "",
            "Next recommended step:",
            result.next_recommended_step,
            "",
            "Evidence sources:",
            *_bullets(result.evidence_sources),
            "",
            "Execution: read-only project inspection. No task was executed.",
        ]
    )


def format_recent_project_changes() -> str:
    result = inspect_project_status()
    lines = [
        "Recent Eva project changes",
        "",
        "Latest known Phase 12 progress:",
        *_bullets(result.recent_completed_phases),
        "",
        "Current addition:",
        "Phase 12O adds evidence-backed project inspection, reality checks, proof/done checks, and safer natural `eva ask` routing for project-status questions.",
        "",
        "Evidence source:",
        "This is based on local docs/status surfaces and Control Center/workflow metadata, not a git mutation scan.",
        "",
        "Execution: read-only recent-change summary. No task was executed.",
    ]
    return "\n".join(lines)


def format_project_next_step() -> str:
    result = inspect_project_status()
    return "\n".join(
        [
            "Project next step",
            "",
            "Recommended next safe phase:",
            result.next_recommended_step,
            "",
            "Why:",
            "Eva now has many metadata, routing, verification, and narrow real-create gates. The safest next move is to tighten evidence and checkpoint readiness before expanding any real executor surface.",
            "",
            "Do not do next:",
            "- do not enable broad file edits",
            "- do not enable browser/desktop control",
            "- do not enable MCP or terminal execution",
            "- do not route normal chat through v2 by default",
            "",
            "Execution: read-only next-step recommendation. No task was executed.",
        ]
    )


def _project_summary(inventory: object) -> str:
    project_types = list(getattr(inventory, "project_types", []) or [])
    if any("Eva" in item for item in project_types):
        return "This is Eva, a local AI assistant project with agent routing, FileAgent workflows, Research Memory, Control Center, safety gates, and verifier-driven Phase 12 runtime surfaces."
    if project_types:
        return "This repo appears to be: " + ", ".join(project_types[:4]) + "."
    return "This repo is a local project; FileAgent inventory could not confidently classify it within the bounded scan."


def _key_systems(inventory: object) -> list[str]:
    paths = set(_all_inventory_paths(inventory))
    candidates = [
        ("authority spine", "backend/eva/authority"),
        ("natural router", "backend/eva/core/natural_router.py"),
        ("FileAgent", "backend/eva/file_agent"),
        ("skills/workflows", "backend/eva/skills"),
        ("specialists", "backend/eva/specialists"),
        ("Control Center", "backend/eva/control_center"),
        ("capability registry", "backend/eva/capabilities"),
        ("planner", "backend/eva/planner"),
        ("Research Memory", "backend/eva/research_memory"),
        ("verifiers", "scripts"),
    ]
    output = [label for label, marker in candidates if any(path == marker or path.startswith(marker + "/") for path in paths)]
    return output[:10] or ["FileAgent read-only inventory", "Phase 12 status helpers", "verifier scripts"]


def _inventory_key_files(inventory: object) -> list[str]:
    key_files: dict[str, list[str]] = dict(getattr(inventory, "key_files", {}) or {})
    output: list[str] = []
    for label in ("docs", "configs", "source", "tests"):
        output.extend(key_files.get(label, [])[:6])
    if not output:
        output = _all_inventory_paths(inventory)[:12]
    preferred = [
        "docs/EVA_CURRENT_STATE.md",
        "docs/EVA_FILE_AGENT.md",
        "docs/EVA_CAPABILITIES.md",
        "backend/eva/core/fast_commands.py",
        "backend/eva/core/natural_router.py",
        "backend/eva/file_agent",
        "backend/eva/control_center",
        "scripts/verify_eva_all.py",
    ]
    merged = preferred + output
    return _dedupe([item for item in merged if item])[:14]


def _all_inventory_paths(inventory: object) -> list[str]:
    return [str(getattr(item, "display_path", "") or "") for item in list(getattr(inventory, "items", []) or [])]


def _bullets(items: tuple[str, ...] | list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        clean = str(item or "").replace("\\", "/").strip()
        if clean and clean not in output:
            output.append(clean)
    return output
