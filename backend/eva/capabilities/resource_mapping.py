from __future__ import annotations

from dataclasses import asdict, dataclass

from .permissions import evaluate_capability_permission, get_capability_permission
from .registry import build_default_registry
from .tool_schemas import capability_to_tool_schema
from ..resources.registry import evaluate_resource_by_id, get_resource


@dataclass(frozen=True)
class CapabilityResourceLink:
    capability_id: str
    resource_id: str
    provider: str
    agent: str | None
    execution_path: str
    available_now: bool
    preview_only: bool
    notes: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityResolution:
    capability_id: str
    capability_name: str
    permission_summary: str
    resource_id: str | None
    resource_status: str
    provider: str
    agent: str | None
    tool_schema_available: bool
    execution_path: str
    available_now: bool
    preview_only: bool
    allowed_in_public_mode: bool
    requires_confirmation: bool
    requires_override: bool
    risk_level: str
    final_status: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


_ALIASES = {
    "research_memory.save": "research_memory.import_note",
    "research_memory.import": "research_memory.import_note",
    "research_memory.export": "research_memory.export_json",
    "public_release.status": "public_release.public_status",
    "public_release.demo": "public_release.demo_scenarios",
    "public_release.safety_test": "public_release.safety_simulator",
    "public_release.doctor": "public_release.ready_check",
    "public_release.hardening": "public_release.hardening_audit",
    "eva_v2.route": "eva_v2.route_preview",
    "eva_v2.plan": "eva_v2.plan_preview",
}

_VIRTUAL_NAMES = {
    "research_memory.delete_item": "Delete Research Memory Item",
    "research_memory.clear_topic": "Clear Research Memory Topic",
    "research_memory.vector_status": "Research Memory Vector Status",
    "research_memory.vector_search": "Research Memory Vector Search",
    "eva_v2.execute_safe": "Eva v2 Safe Execution Bridge",
    "reference.odysseus_ai_workspace": "Odysseus AI Workspace Reference",
    "reference.memos_memory_operating_system": "MemOS Memory Operating System Reference",
    "reference.tradingagents": "TradingAgents Reference",
    "reference.agency_agents": "Agency Agents Reference",
}


def _link(
    capability_id: str,
    resource_id: str,
    provider: str,
    *,
    agent: str | None = None,
    execution_path: str = "fast_command",
    available_now: bool = True,
    preview_only: bool = False,
    notes: str = "Metadata-only capability-resource link.",
) -> CapabilityResourceLink:
    return CapabilityResourceLink(
        capability_id=capability_id,
        resource_id=resource_id,
        provider=provider,
        agent=agent,
        execution_path=execution_path,
        available_now=available_now,
        preview_only=preview_only,
        notes=notes,
    )


_LINKS: tuple[CapabilityResourceLink, ...] = (
    _link("research_memory.status", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Read-only local Research Memory status."),
    _link("research_memory.help", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Read-only local Research Memory help."),
    _link("research_memory.recent", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Read-only recent local notes."),
    _link("research_memory.topics", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Read-only topic listing."),
    _link("research_memory.search", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="read_only_delegate", notes="Lexical local Research Memory search."),
    _link("research_memory.retrieve", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="read_only_delegate", notes="Ranked local Research Memory retrieval."),
    _link("research_memory.topic_summary", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="read_only_delegate", notes="Read-only topic summary from local notes."),
    _link("research_memory.import_note", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Explicit local write through sanitized import command."),
    _link("research_memory.export_json", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Explicit local export of sanitized stored notes."),
    _link("research_memory.delete_item", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="future_permission_gated", available_now=False, preview_only=True, notes="Scoped local delete requires explicit item id and confirmation."),
    _link("research_memory.clear_topic", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="future_permission_gated", available_now=False, preview_only=True, notes="Scoped topic clear requires the confirm phrase."),
    _link("research_memory.stats", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Read-only path-free local stats."),
    _link("research_memory.tags", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Read-only tag counts."),
    _link("research_memory.quality", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Read-only quality warnings; no cleanup runs."),
    _link("research_memory.duplicates_preview", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", preview_only=True, notes="Preview duplicate groups only."),
    _link("research_memory.ranking_status", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Read-only ranking status."),
    _link("research_memory.recall_stats", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Read-only recall stats with hashed query references."),
    _link("research_memory.promote_candidates", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", preview_only=True, notes="Preview-only promotion candidates; no write."),
    _link("research_memory.review_memory", "eva-research-memory-v2", "Research Memory", agent="ResearchAgent", execution_path="fast_command", notes="Read-only local memory review."),
    _link("research_memory.vector_status", "eva-research-memory-vector-index", "Research Memory", agent="ResearchAgent", execution_path="fast_command", preview_only=True, notes="Vector interface status only; vector search remains disabled by default."),
    _link("research_memory.vector_search", "eva-research-memory-vector-index", "Research Memory", agent="ResearchAgent", execution_path="disabled_reference", available_now=False, preview_only=True, notes="Experimental vector search interface disabled by default. Lexical retrieval remains primary."),
    _link("eva_v2.agent_status", "eva-v2-runtime", "Eva v2", agent="RuntimeAgent", execution_path="fast_command", notes="Read-only bounded agent status."),
    _link("eva_v2.route_preview", "eva-v2-runtime", "Eva v2", agent="PlannerAgent", execution_path="v2_dry_run", preview_only=True, notes="Route preview only; no normal-chat v2 routing."),
    _link("eva_v2.plan_preview", "eva-v2-runtime", "Eva v2", agent="PlannerAgent", execution_path="v2_dry_run", preview_only=True, notes="Plan preview only."),
    _link("eva_v2.dry_run", "eva-v2-runtime", "Eva v2", agent="PlannerAgent", execution_path="v2_dry_run", preview_only=True, notes="Dry-run planning surface; no risky execution."),
    _link("eva_v2.read_only_delegation_status", "eva-v2-runtime", "Eva v2", agent="RuntimeAgent", execution_path="fast_command", notes="Read-only delegation status."),
    _link("eva_v2.execute_safe", "eva-v2-runtime", "Eva v2", agent="RuntimeAgent", execution_path="future_permission_gated", available_now=False, preview_only=True, notes="Safe execution bridge metadata only for future planner phases."),
    _link("public_release.public_status", "eva-public-release-mode", "Public Release", agent="SafetyAgent", execution_path="fast_command", notes="Read-only public release status."),
    _link("public_release.hardening_audit", "eva-public-release-mode", "Public Release", agent="SafetyAgent", execution_path="fast_command", notes="Read-only repo hardening audit; secret files are not read."),
    _link("public_release.ready_check", "eva-public-release-mode", "Public Release", agent="SafetyAgent", execution_path="fast_command", notes="Read-only readiness check."),
    _link("public_release.demo_scenarios", "eva-public-release-mode", "Public Release", agent="SafetyAgent", execution_path="demo_only", preview_only=True, notes="Demo-only; no real action."),
    _link("public_release.safety_simulator", "eva-public-release-mode", "Public Release", agent="SafetyAgent", execution_path="demo_only", preview_only=True, notes="Simulation-only safety result."),
    _link("public_release.resource_registry_listing", "eva-public-release-mode", "Public Release", agent="SafetyAgent", execution_path="fast_command", notes="Catalog-only resource listing."),
    _link("reference.odysseus_ai_workspace", "odysseus-ai-workspace", "Reference", execution_path="disabled_reference", available_now=False, preview_only=True, notes="Reference-only architecture entry; not executable."),
    _link("reference.memos_memory_operating_system", "memos-memory-operating-system", "Reference", execution_path="disabled_reference", available_now=False, preview_only=True, notes="Reference-only memory architecture entry; no dependency or code copied."),
)


def _canonical_id(capability_id: str) -> str:
    normalized = str(capability_id or "").strip()
    return _ALIASES.get(normalized, normalized)


def list_capability_resource_links() -> list[CapabilityResourceLink]:
    return list(_LINKS)


def get_capability_resource_link(capability_id: str) -> CapabilityResourceLink | None:
    canonical = _canonical_id(capability_id)
    return next((link for link in _LINKS if link.capability_id == canonical), None)


def find_capabilities_by_resource(resource_id: str) -> list[CapabilityResourceLink]:
    wanted = str(resource_id or "").strip()
    return [link for link in _LINKS if link.resource_id == wanted]


def find_resources_for_capability(capability_id: str) -> list[str]:
    link = get_capability_resource_link(capability_id)
    return [link.resource_id] if link else []


def resolve_capability(capability_id: str, context: dict[str, object] | None = None) -> CapabilityResolution:
    requested = str(capability_id or "").strip()
    canonical = _canonical_id(requested)
    registry = build_default_registry()
    capability = registry.get(canonical)
    link = get_capability_resource_link(canonical)
    permission = get_capability_permission(canonical)
    decision = evaluate_capability_permission(canonical, context or {"mode": "public"})
    schema = capability_to_tool_schema(canonical)

    resource = get_resource(link.resource_id) if link else None
    resource_decision = evaluate_resource_by_id(link.resource_id) if link else None

    capability_name = capability.name if capability else _VIRTUAL_NAMES.get(canonical, canonical or "Unknown capability")
    resource_status = resource_decision.status if resource_decision else "resource_missing"
    resource_reason = resource_decision.reason if resource_decision else "No resource link is registered for this capability."
    final_status = _final_status(
        capability_exists=capability is not None or canonical in _VIRTUAL_NAMES,
        permission_allowed=decision.allowed,
        permission=permission,
        link=link,
        resource_status=resource_status,
        resource_executable=bool(resource_decision.executable_now) if resource_decision else False,
    )

    available_now = bool(
        link
        and link.available_now
        and final_status in {"available_read_only", "available_explicit_local_write", "preview_only"}
        and resource_decision
        and resource_decision.status not in {"blocked", "reference_only"}
    )
    if final_status in {"disabled_experimental", "reference_only", "blocked", "unknown"}:
        available_now = False

    reason = _resolution_reason(
        final_status=final_status,
        permission_reason=permission.reason,
        resource_reason=resource_reason,
        link_notes=link.notes if link else "",
        confirm_phrase=permission.confirm_phrase_required,
    )
    return CapabilityResolution(
        capability_id=canonical or requested,
        capability_name=capability_name,
        permission_summary=_permission_summary(permission),
        resource_id=link.resource_id if link else None,
        resource_status=resource_status,
        provider=link.provider if link else (resource.provider if resource else "unknown"),
        agent=link.agent if link else None,
        tool_schema_available=schema is not None,
        execution_path=link.execution_path if link else "unknown",
        available_now=available_now,
        preview_only=bool(link.preview_only) if link else False,
        allowed_in_public_mode=permission.public_mode_allowed and final_status not in {"blocked", "unknown", "reference_only", "disabled_experimental"},
        requires_confirmation=permission.requires_confirmation,
        requires_override=permission.requires_override,
        risk_level=permission.risk_level,
        final_status=final_status,
        reason=reason,
    )


def _final_status(
    *,
    capability_exists: bool,
    permission_allowed: bool,
    permission: object,
    link: CapabilityResourceLink | None,
    resource_status: str,
    resource_executable: bool,
) -> str:
    if not capability_exists:
        return "unknown"
    if link is None:
        return "unknown"
    if resource_status == "resource_missing":
        return "resource_missing"
    if resource_status == "reference_only":
        return "reference_only"
    if resource_status == "blocked":
        return "blocked"
    if resource_status == "experimental":
        return "disabled_experimental"
    if not permission_allowed and not permission.requires_confirmation:
        return "blocked"
    if link.preview_only:
        return "preview_only"
    if permission.read_only and resource_executable:
        return "available_read_only"
    if permission.writes_local_data and resource_executable:
        return "available_explicit_local_write"
    return "preview_only"


def _permission_summary(permission: object) -> str:
    mode = "Read-only" if permission.read_only else "Explicit local write"
    allowed = "public/community allowed" if permission.public_mode_allowed else "public/community blocked"
    guards = []
    if permission.requires_confirmation:
        guards.append("confirmation required")
    if permission.requires_override:
        guards.append("override required")
    if permission.confirm_phrase_required:
        guards.append("confirm phrase required")
    guard = "; " + ", ".join(guards) if guards else ""
    return f"{mode}, {allowed}, {permission.risk_level} risk{guard}."


def _resolution_reason(*, final_status: str, permission_reason: str, resource_reason: str, link_notes: str, confirm_phrase: bool) -> str:
    parts = []
    if final_status == "disabled_experimental":
        parts.append("Resource is experimental or disabled by default.")
    elif final_status == "reference_only":
        parts.append("Resource is reference-only and not executable.")
    elif final_status == "blocked":
        parts.append("Permission or resource policy blocks this capability.")
    elif final_status == "preview_only":
        parts.append("This capability is preview-only or demo-only in this phase.")
    elif final_status == "resource_missing":
        parts.append("The mapped resource is missing from the registry.")
    elif final_status == "unknown":
        parts.append("Capability is not registered in the safe metadata view.")
    if confirm_phrase:
        parts.append("A confirm phrase is required for this scoped local action.")
    for item in (link_notes, permission_reason, resource_reason):
        if item and item not in parts:
            parts.append(item)
    return " ".join(parts)


def format_capability_resolution(capability_id: str) -> str:
    item = resolve_capability(capability_id)
    resource = item.resource_id or "none"
    schema = "available as preview" if item.tool_schema_available else "not registered"
    availability = "available now" if item.available_now else "not executable now"
    return "\n".join(
        [
            "Capability resolution",
            "",
            "Capability:",
            item.capability_id,
            f"Name: {item.capability_name}",
            "",
            "Permission:",
            item.permission_summary,
            "",
            "Resource:",
            resource,
            f"Resource status: {item.resource_status}",
            "",
            "Provider:",
            item.provider,
            f"Agent: {item.agent or 'none'}",
            "",
            "Execution:",
            f"Path: {item.execution_path}",
            f"Availability: {availability}",
            f"Preview only: {'yes' if item.preview_only else 'no'}",
            "",
            "Tool schema:",
            schema,
            "",
            "Status:",
            item.final_status,
            "",
            "Reason:",
            item.reason,
            "",
            "Scope:",
            "Metadata only. No tool, MCP server, browser, desktop, shell, or message action was executed.",
        ]
    )


def format_capability_resources(capability_id: str) -> str:
    item = resolve_capability(capability_id)
    lines = ["Capability resources", "", f"Capability: {item.capability_id}"]
    if item.resource_id:
        lines.extend(
            [
                f"- {item.resource_id}: {item.resource_status}; {item.final_status}; provider {item.provider}; path {item.execution_path}",
                "",
                "Safety:",
                item.reason,
            ]
        )
    else:
        lines.append("- No resource link is registered.")
    lines.extend(["", "Scope: metadata lookup only; nothing was executed."])
    return "\n".join(lines)


def format_resource_capabilities(resource_id: str) -> str:
    links = find_capabilities_by_resource(resource_id)
    lines = ["Resource capabilities", "", f"Resource: {resource_id}", f"Count: {len(links)}"]
    if not links:
        lines.append("No capabilities are mapped to this resource.")
    for link in links:
        resolution = resolve_capability(link.capability_id)
        lines.append(f"- {link.capability_id}: {resolution.final_status}; {link.execution_path}; {resolution.permission_summary}")
    lines.extend(["", "Scope: metadata lookup only; no resource was executed."])
    return "\n".join(lines)


def format_capability_resource_matrix(status: str | None = None) -> str:
    resolutions = [resolve_capability(link.capability_id) for link in _LINKS]
    wanted = str(status or "").strip().lower()
    if wanted == "available":
        title = "Available capabilities"
        resolutions = [item for item in resolutions if item.final_status in {"available_read_only", "available_explicit_local_write"}]
    elif wanted == "preview_only":
        title = "Preview-only capabilities"
        resolutions = [item for item in resolutions if item.final_status == "preview_only"]
    elif wanted == "blocked":
        title = "Blocked capabilities"
        resolutions = [item for item in resolutions if item.final_status in {"blocked", "disabled_experimental", "reference_only", "unknown", "resource_missing"}]
    else:
        title = "Capability-resource matrix"

    lines = [title, "", f"Count: {len(resolutions)}"]
    for item in resolutions:
        resource = item.resource_id or "none"
        lines.append(f"- {item.capability_id} -> {resource}: {item.final_status}; {item.execution_path}; {item.agent or 'no agent'}")
    lines.extend(["", "Scope: metadata-only mapping. No tools or resources were executed."])
    return "\n".join(lines)


def resolve_capabilities_for_goal(goal_text: str) -> list[CapabilityResolution]:
    text = str(goal_text or "").lower()
    capability_ids: list[str] = []
    if any(term in text for term in ("saved research", "research memory", "my research", "memory about")):
        capability_ids.extend(["research_memory.retrieve", "research_memory.search"])
    if "vector" in text or "semantic" in text:
        capability_ids.append("research_memory.vector_search")
    if "public" in text and "status" in text:
        capability_ids.append("public_release.public_status")
    if "dry run" in text or "dry-run" in text:
        capability_ids.append("eva_v2.dry_run")
    if "route" in text and "preview" in text:
        capability_ids.append("eva_v2.route_preview")
    if "plan" in text and "preview" in text:
        capability_ids.append("eva_v2.plan_preview")
    if any(term in text for term in ("demo unsafe", "safety test", "unsafe env")):
        capability_ids.append("public_release.safety_simulator")
    if "demo" in text and "scenario" in text:
        capability_ids.append("public_release.demo_scenarios")
    if not capability_ids and "status" in text:
        capability_ids.append("eva_v2.agent_status")

    deduped: list[str] = []
    for item in capability_ids:
        if item not in deduped:
            deduped.append(item)
    return [resolve_capability(item) for item in deduped]


def format_capability_plan_resources(goal_text: str) -> str:
    resolutions = resolve_capabilities_for_goal(goal_text)
    lines = ["Likely capability resources", "", f"Goal: {str(goal_text or '').strip()}"]
    if not resolutions:
        lines.append("No safe metadata capability matched this goal yet.")
    for item in resolutions:
        lines.append(f"- {item.capability_id} -> {item.resource_id or 'none'}: {item.final_status}; {item.permission_summary}")
    lines.extend(["", "Scope: planner-readiness preview only. No LLM call or tool execution occurred."])
    return "\n".join(lines)
