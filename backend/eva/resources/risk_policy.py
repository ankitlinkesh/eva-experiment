from __future__ import annotations

from .allowlist import is_builtin_blocked, is_reference_only
from .models import EvaResource, EvaResourceDecision


def evaluate_resource(resource: EvaResource) -> EvaResourceDecision:
    blocked_capabilities: list[str] = []
    if is_builtin_blocked(resource.id):
        blocked_capabilities.append("blocked_resource_id")
    if "secret" in resource.id or "credential" in resource.id:
        blocked_capabilities.append("secret_access")

    risk = _computed_risk(resource)
    status = "blocked" if blocked_capabilities else resource.status
    allowed = status not in {"blocked", "reference_only"} and not blocked_capabilities
    permission_required = status in {"allowed_with_permission", "experimental"} or resource.can_control_browser or resource.can_control_desktop or resource.can_read_files or resource.requires_api_key or resource.requires_network or resource.cloud_capable
    override_required = resource.can_delete_or_modify_system or (resource.can_write_files and resource.requires_network) or resource.can_execute_code

    if is_reference_only(resource.id):
        allowed = False
        status = "reference_only"
        permission_required = False
    if blocked_capabilities:
        allowed = False
        status = "blocked"
        permission_required = False
        override_required = False

    executable_now = _executable_now(resource, status, risk, override_required, blocked_capabilities)
    reason = _reason(resource, status, risk, permission_required, override_required, blocked_capabilities)
    return EvaResourceDecision(
        resource_id=resource.id,
        allowed=allowed,
        executable_now=executable_now,
        status=status,
        risk_level=risk,
        permission_required=permission_required,
        override_required=override_required,
        reason=reason,
        blocked_capabilities=blocked_capabilities,
    )


def _computed_risk(resource: EvaResource) -> str:
    if resource.risk_level == "critical" or is_builtin_blocked(resource.id):
        return "critical"
    if resource.can_execute_code or resource.can_control_desktop or resource.can_delete_or_modify_system or resource.can_send_external_messages or (resource.can_write_files and resource.requires_network):
        return "high"
    if resource.can_control_browser or resource.can_read_files or resource.requires_api_key or resource.requires_network or resource.cloud_capable:
        return "medium"
    return resource.risk_level or "low"


def _reason(resource: EvaResource, status: str, risk: str, permission: bool, override: bool, blocked: list[str]) -> str:
    if blocked:
        return "Blocked by resource policy: " + ", ".join(blocked)
    if status == "reference_only":
        return "Reference only. Cataloged for planning; not executable."
    if status == "experimental":
        if resource.kind == "mcp_server":
            return "MCP execution is disabled by default; explicit enablement and tests required."
        return "Experimental and disabled by default; explicit enablement and tests are required."
    if override:
        return "High-risk capability requires override before execution."
    if permission:
        return "Permission required before use because this resource can access local, network, browser, desktop, or cloud surfaces."
    return f"Allowed low-risk catalog resource ({risk})."


def _executable_now(resource: EvaResource, status: str, risk: str, override: bool, blocked: list[str]) -> bool:
    if blocked or status in {"blocked", "reference_only", "experimental"}:
        return False
    if resource.kind == "mcp_server":
        return False
    if not resource.default_enabled and resource.provider != "Eva":
        return False
    if override or risk in {"high", "critical"}:
        return False
    return status in {"allowed", "allowed_with_permission"}
