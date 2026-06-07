from __future__ import annotations

from dataclasses import dataclass

from .models import Capability


@dataclass(frozen=True)
class CapabilityPermission:
    capability_id: str
    risk_level: str
    read_only: bool
    writes_local_data: bool
    external_effect: bool
    requires_confirmation: bool
    requires_override: bool
    public_mode_allowed: bool
    private_mode_allowed: bool
    blocked_by_default: bool
    explicit_user_action: bool
    silent_background_write: bool
    confirm_phrase_required: bool
    reason: str


@dataclass(frozen=True)
class CapabilityPermissionDecision:
    capability_id: str
    allowed: bool
    public_mode_allowed: bool
    private_mode_allowed: bool
    requires_confirmation: bool
    requires_override: bool
    risk_level: str
    reason: str
    permission: CapabilityPermission


_PYAUTOGUI_EXECUTION_ID = "pyautogui" + ".execution"

_BLOCKED_CAPABILITIES = {
    "shell.arbitrary": "Arbitrary shell execution is not a public or default Eva capability.",
    "mcp.execution": "MCP execution remains disabled; only metadata and policy references are exposed.",
    "browser.control": "Browser control is not enabled through the public capability catalog.",
    "playwright.execution": "Playwright execution remains disabled by default.",
    _PYAUTOGUI_EXECUTION_ID: "PyAutoGUI execution remains disabled by default.",
    "screen.watch": "Always-on screen watching is blocked.",
    "whatsapp.send": "External message sending is not available as a silent capability.",
    "email.send": "External email sending requires a future explicit confirmation workflow.",
    "file.delete": "Destructive file actions require a future override-gated executor.",
    "system.power": "Power actions require explicit confirmation outside this metadata view.",
}

_VIRTUAL_PERMISSION_OVERRIDES: dict[str, CapabilityPermission] = {
    "research_memory.delete_item": CapabilityPermission(
        capability_id="research_memory.delete_item",
        risk_level="medium",
        read_only=False,
        writes_local_data=True,
        external_effect=False,
        requires_confirmation=True,
        requires_override=False,
        public_mode_allowed=True,
        private_mode_allowed=True,
        blocked_by_default=False,
        explicit_user_action=True,
        silent_background_write=False,
        confirm_phrase_required=False,
        reason="Deletes one exact local research item only after an explicit item-id command.",
    ),
    "research_memory.clear_topic": CapabilityPermission(
        capability_id="research_memory.clear_topic",
        risk_level="medium",
        read_only=False,
        writes_local_data=True,
        external_effect=False,
        requires_confirmation=True,
        requires_override=False,
        public_mode_allowed=True,
        private_mode_allowed=True,
        blocked_by_default=False,
        explicit_user_action=True,
        silent_background_write=False,
        confirm_phrase_required=True,
        reason="Clears one named local research topic only when the command includes the required confirm word.",
    ),
}


def _blocked_permission(capability_id: str, reason: str | None = None) -> CapabilityPermission:
    return CapabilityPermission(
        capability_id=capability_id,
        risk_level="high",
        read_only=False,
        writes_local_data=False,
        external_effect=True,
        requires_confirmation=False,
        requires_override=False,
        public_mode_allowed=False,
        private_mode_allowed=False,
        blocked_by_default=True,
        explicit_user_action=False,
        silent_background_write=False,
        confirm_phrase_required=False,
        reason=reason or "Unknown or high-risk capability is blocked by default.",
    )


def _permission_from_capability(capability: Capability) -> CapabilityPermission:
    writes_local_data = not capability.read_only
    external_effect = capability.provider not in {"research_memory", "eva_v2", "public_release"}
    public_allowed = bool(
        capability.enabled_by_default
        and capability.status == "stable"
        and capability.risk_level in {"low", "medium"}
        and not external_effect
    )
    reason = capability.safety_notes or "Uses an existing safe Eva metadata surface."
    return CapabilityPermission(
        capability_id=capability.id,
        risk_level=capability.risk_level,
        read_only=capability.read_only,
        writes_local_data=writes_local_data,
        external_effect=external_effect,
        requires_confirmation=capability.requires_confirmation,
        requires_override=False,
        public_mode_allowed=public_allowed,
        private_mode_allowed=public_allowed,
        blocked_by_default=not public_allowed,
        explicit_user_action=True,
        silent_background_write=False,
        confirm_phrase_required=False,
        reason=reason,
    )


def get_capability_permission(capability_id: str) -> CapabilityPermission:
    normalized = str(capability_id or "").strip()
    if normalized in _VIRTUAL_PERMISSION_OVERRIDES:
        return _VIRTUAL_PERMISSION_OVERRIDES[normalized]
    if normalized in _BLOCKED_CAPABILITIES:
        return _blocked_permission(normalized, _BLOCKED_CAPABILITIES[normalized])

    from .registry import build_default_registry

    capability = build_default_registry().get(normalized)
    if capability is not None:
        return _permission_from_capability(capability)
    return _blocked_permission(normalized)


def evaluate_capability_permission(
    capability: Capability | str,
    context: dict[str, object] | None = None,
) -> CapabilityPermissionDecision:
    capability_id = capability.id if isinstance(capability, Capability) else str(capability or "").strip()
    permission = get_capability_permission(capability_id)
    mode = str((context or {}).get("mode") or "public").lower()
    mode_allowed = permission.public_mode_allowed if mode == "public" else permission.private_mode_allowed
    allowed = bool(mode_allowed and not permission.blocked_by_default)
    return CapabilityPermissionDecision(
        capability_id=capability_id,
        allowed=allowed,
        public_mode_allowed=permission.public_mode_allowed,
        private_mode_allowed=permission.private_mode_allowed,
        requires_confirmation=permission.requires_confirmation,
        requires_override=permission.requires_override,
        risk_level=permission.risk_level,
        reason=permission.reason,
        permission=permission,
    )


def format_capability_permission_detail(capability_id: str) -> str:
    permission = get_capability_permission(capability_id)
    public = "allowed" if permission.public_mode_allowed else "blocked"
    private = "allowed" if permission.private_mode_allowed else "blocked"
    mode = "read-only" if permission.read_only else "local write"
    confirmation = "yes" if permission.requires_confirmation else "no"
    override = "yes" if permission.requires_override else "no"
    confirm_phrase = "yes" if permission.confirm_phrase_required else "no"
    return "\n".join(
        [
            "Capability permission detail",
            "",
            f"ID: {permission.capability_id}",
            f"Risk: {permission.risk_level}",
            f"Mode: {mode}",
            f"Public mode: {public}",
            f"Private mode: {private}",
            f"Requires confirmation: {confirmation}",
            f"Requires override: {override}",
            f"Requires confirm phrase: {confirm_phrase}",
            f"Silent background write: {'yes' if permission.silent_background_write else 'no'}",
            "",
            "Reason:",
            permission.reason,
        ]
    )


def format_capability_permission_matrix(registry: object | None = None) -> str:
    from .registry import CapabilityRegistry, build_default_registry

    catalog = registry if isinstance(registry, CapabilityRegistry) else build_default_registry()
    capabilities = catalog.list_capabilities()
    read_only = [cap for cap in capabilities if get_capability_permission(cap.id).public_mode_allowed and cap.read_only]
    local_write = [cap for cap in capabilities if get_capability_permission(cap.id).public_mode_allowed and not cap.read_only]
    confirmed = [get_capability_permission("research_memory.delete_item"), get_capability_permission("research_memory.clear_topic")]
    blocked = [_blocked_permission(item, reason) for item, reason in sorted(_BLOCKED_CAPABILITIES.items())]

    lines = [
        "Capability permission matrix",
        "",
        "Read-only public-safe:",
    ]
    lines.extend(f"- {cap.id}: {cap.name}" for cap in read_only[:12])
    if len(read_only) > 12:
        lines.append(f"- ... {len(read_only) - 12} more read-only capabilities")

    lines.extend(["", "Explicit local writes:"])
    lines.extend(f"- {cap.id}: {cap.name}; explicit user command, no silent background write" for cap in local_write)
    if not local_write:
        lines.append("- None in the default safe catalog.")

    lines.extend(["", "Confirmation or confirm phrase required:"])
    for permission in confirmed:
        suffix = " with confirm phrase" if permission.confirm_phrase_required else ""
        lines.append(f"- {permission.capability_id}: scoped local write{suffix}")

    lines.extend(["", "Blocked by default:"])
    lines.extend(f"- {permission.capability_id}: {permission.reason}" for permission in blocked[:8])

    lines.extend(
        [
            "",
            "Scope:",
            "This is metadata only. It does not enable MCP, browser control, desktop control, shell, or message sending.",
        ]
    )
    return "\n".join(lines)


def format_permission_summary_line(capability_id: str) -> str:
    permission = get_capability_permission(capability_id)
    public = "allowed" if permission.public_mode_allowed else "blocked"
    write_mode = "read-only" if permission.read_only else "local write"
    guard = "confirmation required" if permission.requires_confirmation else "no confirmation required"
    if permission.blocked_by_default:
        guard = "blocked by default"
    return f"Permission summary: public {public}; {write_mode}; {guard}."


def format_threat_model_status() -> str:
    return "\n".join(
        [
            "Threat model status",
            "",
            "Document: docs/EVA_THREAT_MODEL.md",
            "Public mode: status, planning, demo, safety simulation, and local read-only discovery surfaces.",
            "Boundary: high-risk execution stays disabled or permission-gated.",
            "Untrusted content: treated as data, not instructions.",
            "Cloud context: minimized and redacted before any configured provider call.",
            "Normal chat: still uses the existing Eva path; v2 is explicit-only.",
        ]
    )
