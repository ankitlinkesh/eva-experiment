from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LLMProviderName(StrEnum):
    GEMINI = "gemini"
    GROQ = "groq"
    OPENROUTER = "openrouter"
    CLAUDE = "claude"
    OLLAMA = "ollama"
    MOCK = "mock"


class LLMProviderStatus(StrEnum):
    AVAILABLE_MOCK_ONLY = "available_mock_only"
    CONFIGURED_METADATA_ONLY = "configured_metadata_only"
    DISABLED = "disabled"
    MISSING_CONFIG = "missing_config"
    BLOCKED_LIVE_CALLS = "blocked_live_calls"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class LLMFailureMode(StrEnum):
    PROVIDER_UNCONFIGURED = "provider_unconfigured"
    LIVE_CALLS_DISABLED = "live_calls_disabled"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    INVALID_OUTPUT = "invalid_output"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    TOKEN_BUDGET_EXCEEDED = "token_budget_exceeded"
    COST_BUDGET_EXCEEDED = "cost_budget_exceeded"
    UNSAFE_REQUEST = "unsafe_request"
    UNKNOWN_FAILURE = "unknown_failure"


class LLMDegradedMode(StrEnum):
    MOCK_ONLY = "mock_only"
    POLICY_STATUS_ONLY = "policy_status_only"
    REFUSE_LIVE_CALL = "refuse_live_call"


@dataclass(frozen=True)
class LLMProviderCapability:
    supports_text: bool = True
    supports_structured_output_preview: bool = True
    supports_live_calls_now: bool = False


@dataclass(frozen=True)
class LLMProviderContract:
    provider: LLMProviderName
    status: LLMProviderStatus
    capability: LLMProviderCapability
    notes: str


@dataclass(frozen=True)
class LLMRouteRequestPreview:
    request: str
    purpose: str = "general"
    structured_output_required: bool = False


@dataclass(frozen=True)
class LLMRouteDecision:
    selected_provider: LLMProviderName
    fallback_order: tuple[LLMProviderName, ...]
    live_call_allowed: bool
    degraded_mode: LLMDegradedMode
    reason: str


@dataclass(frozen=True)
class LLMRoutingPolicy:
    mode: str
    live_calls_enabled: bool
    mock_only: bool
    default_provider: LLMProviderName
    explanation: str


@dataclass(frozen=True)
class LLMFallbackPolicy:
    order: tuple[LLMProviderName, ...]
    on_failure: str


@dataclass(frozen=True)
class LLMTimeoutPolicy:
    request_timeout_seconds: int


@dataclass(frozen=True)
class LLMRetryPolicy:
    max_attempts: int
    retryable_failures: tuple[LLMFailureMode, ...]


@dataclass(frozen=True)
class LLMTokenBudget:
    max_input_tokens: int
    max_output_tokens: int


@dataclass(frozen=True)
class LLMCostBudget:
    max_cost_usd: float
    enforcement: str


@dataclass(frozen=True)
class LLMStructuredOutputContract:
    name: str
    required_fields: tuple[str, ...]
    live_validation_enabled: bool


@dataclass(frozen=True)
class LLMValidationResult:
    valid: bool
    reason: str


@dataclass(frozen=True)
class LLMRouterStatus:
    status: str
    live_calls_enabled: bool
    mode: LLMDegradedMode
    providers: tuple[LLMProviderContract, ...]
    summary: str


@dataclass(frozen=True)
class LLMCallBoundary:
    live_calls_allowed: bool
    tool_execution_allowed: bool
    network_allowed: bool
    reason: str


@dataclass(frozen=True)
class LLMFallbackStep:
    provider: LLMProviderName
    action: str


@dataclass(frozen=True)
class LLMFallbackChain:
    steps: tuple[LLMFallbackStep, ...]
    live_call_allowed: bool


@dataclass(frozen=True)
class LLMFallbackDecision:
    scenario: LLMFailureMode
    selected_provider: LLMProviderName
    live_call_allowed: bool
    degraded_mode: LLMDegradedMode
    reason: str


@dataclass(frozen=True)
class LLMSessionLimitPolicy:
    max_route_previews: int
    max_planning_steps: int
    max_retries: int


@dataclass(frozen=True)
class LLMSessionUsagePreview:
    route_previews_used: int
    planning_steps_used: int
    within_limits: bool


@dataclass(frozen=True)
class LLMDegradedModePolicy:
    mode: LLMDegradedMode
    behavior: str


@dataclass(frozen=True)
class LLMDegradedModeDecision:
    mode: LLMDegradedMode
    live_call_allowed: bool
    reason: str


@dataclass(frozen=True)
class LLMRoutingAuditPreview:
    event_type: str
    provider: LLMProviderName
    contains_secrets: bool
    summary: str


@dataclass(frozen=True)
class LLMRoutingFailureSimulation:
    scenario: LLMFailureMode
    result: LLMFallbackDecision


@dataclass(frozen=True)
class LLMProviderFailureScenario:
    failure_mode: LLMFailureMode
    description: str


@dataclass(frozen=True)
class LLMRateLimitPolicy:
    max_simulated_requests_per_minute: int
    response: str


@dataclass(frozen=True)
class LLMRunawayProtectionPolicy:
    max_router_steps: int
    stop_behavior: str
