from __future__ import annotations

from .models import LLMProviderName, LLMRoutingAuditPreview


def get_routing_audit_preview() -> LLMRoutingAuditPreview:
    return LLMRoutingAuditPreview("route_preview", LLMProviderName.MOCK, False, "Local metadata audit preview only; request content, secrets, and provider responses are not recorded.")
