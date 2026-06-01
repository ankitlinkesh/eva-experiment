from __future__ import annotations

from .mcp_catalog import get_mcp_resources
from .models import EvaResource, EvaResourceCatalogStatus, EvaResourceDecision
from .open_source_catalog import get_open_source_resources
from .risk_policy import evaluate_resource


def get_all_resources() -> list[EvaResource]:
    merged: dict[str, EvaResource] = {}
    for resource in [*get_open_source_resources(), *get_mcp_resources()]:
        merged[resource.id] = resource
    return list(merged.values())


def get_resource(resource_id: str) -> EvaResource | None:
    wanted = str(resource_id or "").strip()
    for resource in get_all_resources():
        if resource.id == wanted:
            return resource
    return None


def list_resources(category: str | None = None, kind: str | None = None) -> list[EvaResource]:
    resources = get_all_resources()
    if category:
        resources = [resource for resource in resources if resource.category == category]
    if kind:
        resources = [resource for resource in resources if resource.kind == kind]
    return resources


def evaluate_resource_by_id(resource_id: str) -> EvaResourceDecision:
    resource = get_resource(resource_id)
    if resource is None:
        return EvaResourceDecision(
            resource_id=str(resource_id or ""),
            allowed=False,
            executable_now=False,
            status="blocked",
            risk_level="critical",
            permission_required=False,
            override_required=False,
            reason="Unknown resource id.",
            blocked_capabilities=["unknown_resource"],
        )
    return evaluate_resource(resource)


def resource_registry_status() -> EvaResourceCatalogStatus:
    resources = get_all_resources()
    decisions = [evaluate_resource(resource) for resource in resources]
    return EvaResourceCatalogStatus(
        total_resources=len(resources),
        allowed_count=sum(1 for decision in decisions if decision.allowed),
        experimental_count=sum(1 for resource in resources if resource.status == "experimental"),
        blocked_count=sum(1 for decision in decisions if decision.status == "blocked"),
        reference_only_count=sum(1 for decision in decisions if decision.status == "reference_only"),
        high_risk_count=sum(1 for decision in decisions if decision.risk_level in {"high", "critical"}),
        default_enabled_count=sum(1 for resource in resources if resource.default_enabled),
        summary="Catalog-only registry. External and MCP resources are disabled by default unless explicitly enabled later.",
    )


def find_resources_for_capability(capability: str) -> list[EvaResource]:
    text = str(capability or "").lower()
    if not text:
        return []
    return [
        resource
        for resource in get_all_resources()
        if text in resource.id.lower()
        or text in resource.name.lower()
        or text in resource.category.lower()
        or text in resource.notes.lower()
    ]


def is_resource_allowed(resource_id: str) -> EvaResourceDecision:
    return evaluate_resource_by_id(resource_id)
