from __future__ import annotations

from .models import LLMDegradedMode, LLMRouterStatus
from .provider_contracts import list_provider_contracts


def get_llm_router_status() -> LLMRouterStatus:
    return LLMRouterStatus("mock/dry-run only", False, LLMDegradedMode.MOCK_ONLY, list_provider_contracts(), "LLM router contracts, fallback simulation, limits, degraded mode, and audit previews exist, but live LLM/API/network calls are not enabled in Phase 15B.")
