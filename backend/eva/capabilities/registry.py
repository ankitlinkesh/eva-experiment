from __future__ import annotations

from dataclasses import dataclass

from .models import Capability
from .provider import BaseCapabilityProvider


@dataclass(frozen=True)
class StaticCapabilityProvider:
    provider_id: str
    provider_name: str
    capabilities: tuple[Capability, ...]

    def list_capabilities(self) -> list[Capability]:
        return list(self.capabilities)


class CapabilityRegistry:
    def __init__(self, providers: list[BaseCapabilityProvider] | None = None) -> None:
        self._providers = list(providers or [])
        self._capabilities: list[Capability] = []
        for provider in self._providers:
            self._capabilities.extend(provider.list_capabilities())

    def list_capabilities(
        self,
        *,
        provider: str | None = None,
        category: str | None = None,
        risk_level: str | None = None,
        status: str | None = None,
        enabled: bool | None = None,
    ) -> list[Capability]:
        capabilities = self._capabilities
        if provider is not None:
            capabilities = [cap for cap in capabilities if cap.provider == provider]
        if category is not None:
            capabilities = [cap for cap in capabilities if cap.category == category]
        if risk_level is not None:
            capabilities = [cap for cap in capabilities if cap.risk_level == risk_level]
        if status is not None:
            capabilities = [cap for cap in capabilities if cap.status == status]
        if enabled is not None:
            capabilities = [cap for cap in capabilities if cap.enabled_by_default is enabled]
        return list(capabilities)

    def get(self, capability_id: str) -> Capability | None:
        normalized = str(capability_id or "").strip()
        return next((cap for cap in self._capabilities if cap.id == normalized), None)

    def providers(self) -> list[str]:
        return sorted({provider.provider_id for provider in self._providers})

    def provider_names(self) -> dict[str, str]:
        return {provider.provider_id: provider.provider_name for provider in self._providers}

    def validate_unique_ids(self) -> bool:
        ids = [capability.id for capability in self._capabilities]
        return len(ids) == len(set(ids))


def build_default_registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        [
            StaticCapabilityProvider("research_memory", "Research Memory", tuple(_research_memory_capabilities())),
            StaticCapabilityProvider("eva_v2", "Eva v2", tuple(_eva_v2_capabilities())),
            StaticCapabilityProvider("public_release", "Public Release", tuple(_public_release_capabilities())),
        ]
    )


def format_capability_summary(
    registry: CapabilityRegistry | None = None,
    *,
    safe_only: bool = False,
    experimental_only: bool = False,
) -> str:
    registry = registry or build_default_registry()
    if safe_only:
        title = "Safe enabled capabilities"
        capabilities = [
            cap
            for cap in registry.list_capabilities(enabled=True)
            if cap.risk_level in {"low", "medium"} and cap.status == "stable" and not cap.requires_confirmation
        ]
    elif experimental_only:
        title = "Experimental capabilities"
        capabilities = registry.list_capabilities(status="experimental")
    else:
        title = "Eva capabilities"
        capabilities = registry.list_capabilities()

    lines = [title, "", f"Count: {len(capabilities)}"]
    if not capabilities:
        lines.extend(["", "No matching capabilities are registered in this safe metadata view."])
    else:
        for cap in capabilities:
            flags = []
            flags.append("enabled" if cap.enabled_by_default else "disabled")
            flags.append("read-only" if cap.read_only else "local-write")
            if cap.requires_confirmation:
                flags.append("confirmation")
            lines.append(f"- {cap.id}: {cap.name} ({cap.provider}, {cap.risk_level}, {', '.join(flags)})")
    lines.extend(
        [
            "",
            "Scope:",
            "Metadata/discovery only. No tools were executed and no private runtime data was read.",
        ]
    )
    return "\n".join(lines)


def format_capability_providers(registry: CapabilityRegistry | None = None) -> str:
    registry = registry or build_default_registry()
    names = registry.provider_names()
    lines = ["Capability providers", "", f"Count: {len(names)}"]
    for provider_id in sorted(names):
        count = len(registry.list_capabilities(provider=provider_id))
        lines.append(f"- {provider_id}: {names[provider_id]} ({count} capabilities)")
    lines.extend(["", "Scope: catalog view only; no provider action was executed."])
    return "\n".join(lines)


def format_capability_detail(registry: CapabilityRegistry | None, capability_id: str) -> str:
    registry = registry or build_default_registry()
    capability = registry.get(capability_id)
    if capability is None:
        return "\n".join(
            [
                "Capability detail",
                "",
                f"Capability `{capability_id}` was not found.",
                "Use `eva capabilities` to list available metadata.",
            ]
        )
    enabled = "yes" if capability.enabled_by_default else "no"
    read_only = "yes" if capability.read_only else "no"
    confirmation = "yes" if capability.requires_confirmation else "no"
    verifier = capability.verifier_name or "not specified"
    from .permissions import format_permission_summary_line
    from .tool_schemas import capability_to_tool_schema

    schema_status = "available" if capability_to_tool_schema(capability.id) else "not registered"
    resource_lines: list[str] = []
    try:
        from .resource_mapping import resolve_capability

        resolution = resolve_capability(capability.id)
        resource_lines = [
            f"Resource: {resolution.resource_id or 'none'}",
            f"Resolution status: {resolution.final_status}",
            f"Execution path: {resolution.execution_path}",
        ]
    except Exception:
        resource_lines = ["Resource: mapping unavailable"]
    return "\n".join(
        [
            "Capability detail",
            "",
            f"ID: {capability.id}",
            f"Name: {capability.name}",
            f"Provider: {capability.provider}",
            f"Category: {capability.category}",
            f"Risk: {capability.risk_level}",
            f"Status: {capability.status}",
            f"Enabled by default: {enabled}",
            f"Read-only: {read_only}",
            f"Requires confirmation: {confirmation}",
            f"Verifier: {verifier}",
            format_permission_summary_line(capability.id),
            f"Tool schema preview: {schema_status}",
            *resource_lines,
            "",
            "Description:",
            capability.description,
            "",
            "Safety:",
            capability.safety_notes,
            "",
            "Scope:",
            "Metadata only. Inspecting this capability does not execute the underlying command.",
        ]
    )


def _cap(
    capability_id: str,
    name: str,
    description: str,
    provider: str,
    category: str,
    *,
    risk_level: str = "low",
    read_only: bool = True,
    requires_confirmation: bool = False,
    enabled_by_default: bool = True,
    status: str = "stable",
    safety_notes: str = "Uses existing safe Eva command surfaces only.",
    verifier_name: str | None = None,
) -> Capability:
    return Capability(
        id=capability_id,
        name=name,
        description=description,
        provider=provider,
        category=category,
        risk_level=risk_level,
        read_only=read_only,
        requires_confirmation=requires_confirmation,
        enabled_by_default=enabled_by_default,
        status=status,
        safety_notes=safety_notes,
        verifier_name=verifier_name,
    )


def _research_memory_capabilities() -> list[Capability]:
    verifier = "verify_eva_research_memory_help.py"
    local_notes = "Local Research Memory metadata only; no private page scraping, cloud embeddings, or path output."
    return [
        _cap("research_memory.status", "Research Memory Status", "Show local Research Memory status.", "research_memory", "research_memory", verifier_name=verifier, safety_notes=local_notes),
        _cap("research_memory.help", "Research Memory Help", "Show Research Memory command help.", "research_memory", "research_memory", verifier_name=verifier, safety_notes=local_notes),
        _cap("research_memory.recent", "Recent Research Notes", "List recent sanitized research notes.", "research_memory", "research_memory", verifier_name=verifier, safety_notes=local_notes),
        _cap("research_memory.topics", "Research Topics", "List saved research topics.", "research_memory", "research_memory", verifier_name=verifier, safety_notes=local_notes),
        _cap("research_memory.search", "Search Research Memory", "Lexically search saved local research notes.", "research_memory", "research_memory", verifier_name=verifier, safety_notes=local_notes),
        _cap("research_memory.retrieve", "Retrieve Research Memory", "Retrieve ranked local research snippets.", "research_memory", "research_memory", verifier_name="verify_eva_research_memory_retrieval.py", safety_notes=local_notes),
        _cap("research_memory.topic_summary", "Research Topic Summary", "Summarize a saved research topic from local notes.", "research_memory", "research_memory", verifier_name=verifier, safety_notes=local_notes),
        _cap("research_memory.import_note", "Import Research Note", "Import a user-provided local note after sanitization.", "research_memory", "research_memory", risk_level="medium", read_only=False, verifier_name="verify_eva_research_memory_io.py", safety_notes="Writes only a sanitized local note through the existing Research Memory command."),
        _cap("research_memory.export_json", "Export Research Memory JSON", "Export sanitized saved research to local runtime export storage.", "research_memory", "research_memory", risk_level="medium", read_only=False, verifier_name="verify_eva_research_memory_io.py", safety_notes="Exports sanitized stored notes only and normal output shows filenames, not private paths."),
        _cap("research_memory.stats", "Research Memory Stats", "Show path-free storage statistics.", "research_memory", "research_memory", verifier_name="verify_eva_research_memory_io.py", safety_notes=local_notes),
        _cap("research_memory.tags", "Research Memory Tags", "List normalized tags with counts.", "research_memory", "research_memory", verifier_name="verify_eva_research_memory_quality.py", safety_notes=local_notes),
        _cap("research_memory.quality", "Research Memory Quality", "Preview low-value or duplicate-like notes.", "research_memory", "research_memory", verifier_name="verify_eva_research_memory_quality.py", safety_notes=local_notes),
        _cap("research_memory.duplicates_preview", "Research Memory Duplicates Preview", "Preview duplicate groups without deleting anything.", "research_memory", "research_memory", verifier_name="verify_eva_research_memory_quality.py", safety_notes="Preview only; no merge or delete action is performed."),
        _cap("research_memory.ranking_status", "Research Memory Ranking Status", "Show local ranking, recency, penalty, and diversity status.", "research_memory", "research_memory", verifier_name="verify_eva_research_memory_ranking.py", safety_notes="Read-only ranking status; no notes are changed."),
        _cap("research_memory.recall_stats", "Research Memory Recall Stats", "Show local recall counts without raw queries.", "research_memory", "research_memory", verifier_name="verify_eva_research_memory_ranking.py", safety_notes="Read-only recall metadata; raw query strings are not shown."),
        _cap("research_memory.promote_candidates", "Research Memory Promotion Candidates", "Preview useful long-term note candidates without promotion.", "research_memory", "research_memory", verifier_name="verify_eva_research_memory_ranking.py", safety_notes="Preview only; no auto-promotion or auto-write is performed."),
        _cap("research_memory.review_memory", "Research Memory Review", "Show a local memory review with safe next commands.", "research_memory", "research_memory", verifier_name="verify_eva_research_memory_ranking.py", safety_notes="Read-only review; no delete, merge, or promotion action is performed."),
    ]


def _eva_v2_capabilities() -> list[Capability]:
    notes = "Explicit v2 command metadata only; normal chat is not routed through v2."
    return [
        _cap("eva_v2.agent_status", "Agent Status", "Show bounded agent status.", "eva_v2", "v2", verifier_name="verify_eva_stabilization_v1.py", safety_notes=notes),
        _cap("eva_v2.route_preview", "Route Preview", "Preview an explicit v2 route without executing it.", "eva_v2", "v2", verifier_name="verify_eva_v2_dry_run.py", safety_notes=notes),
        _cap("eva_v2.plan_preview", "Plan Preview", "Preview an explicit v2 plan without executing it.", "eva_v2", "v2", verifier_name="verify_eva_v2_dry_run.py", safety_notes=notes),
        _cap("eva_v2.dry_run", "Dry Run", "Run explicit v2 dry-run planning with no risky execution.", "eva_v2", "v2", verifier_name="verify_eva_v2_dry_run.py", safety_notes=notes),
        _cap("eva_v2.read_only_delegation_status", "Read-only Delegation Status", "Show read-only delegation availability.", "eva_v2", "v2", verifier_name="verify_eva_v2_readonly_delegation.py", safety_notes=notes),
    ]


def _public_release_capabilities() -> list[Capability]:
    notes = "Public/community surface only; no real send, delete, browser automation, desktop automation, or external tool execution."
    return [
        _cap("public_release.public_status", "Public Release Status", "Show public/community release status.", "public_release", "public_release", verifier_name="verify_eva_public_release.py", safety_notes=notes),
        _cap("public_release.hardening_audit", "Public Hardening Audit", "Run repo-local public hardening checks.", "public_release", "public_release", verifier_name="verify_eva_public_release_hardening.py", safety_notes="Reads repo source/docs only; secret files are reported by name and not read."),
        _cap("public_release.ready_check", "Public Ready Check", "Summarize push readiness from the hardening audit.", "public_release", "public_release", verifier_name="verify_eva_public_repo_cleanup.py", safety_notes="Readiness summary only; no staging, commit, push, or network action."),
        _cap("public_release.demo_scenarios", "Demo Scenarios", "List safe simulated public demo scenarios.", "public_release", "public_release", verifier_name="verify_eva_public_release.py", safety_notes=notes),
        _cap("public_release.safety_simulator", "Safety Simulator", "Preview public-mode safety decisions for risky requests.", "public_release", "public_release", verifier_name="verify_eva_public_release.py", safety_notes="Simulation only; no real risky action is executed."),
        _cap("public_release.resource_registry_listing", "Resource Registry Listing", "Show catalog-only resource registry views.", "public_release", "public_release", verifier_name="verify_eva_resource_registry.py", safety_notes="Catalog view only; MCP and external tools remain disabled by default."),
    ]
