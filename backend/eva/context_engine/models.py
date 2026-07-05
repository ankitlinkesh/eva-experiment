from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ContextSource:
    source_type: str
    name: str
    trust_level: str
    allowed: bool
    reason: str


@dataclass(frozen=True)
class ContextBudgetPolicy:
    default_budget_chars: int
    max_budget_chars: int
    section_budget_chars: int
    oversized_behavior: str
    safety_priority: str


@dataclass(frozen=True)
class RedactionResult:
    text: str
    was_redacted: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContextSection:
    section_type: str
    title: str
    content: str
    source_type: str
    source_name: str
    source_trust_level: str
    relevance_score: float
    budget_estimate_chars: int
    redaction_status: str
    safety_notes: tuple[str, ...] = ()
    grounding_notes: tuple[str, ...] = ()
    trimmed: bool = False


@dataclass(frozen=True)
class ExcludedContext:
    source_type: str
    name: str
    reason: str


@dataclass(frozen=True)
class ContextPacket:
    packet_id: str
    user_request_summary: str
    selected_sections: tuple[ContextSection, ...]
    excluded_context: tuple[ExcludedContext, ...]
    grounding_notes: tuple[str, ...]
    final_readiness: str
    no_llm_call_made: bool
    tool_execution_enabled: bool
    safety_notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GroundingReport:
    packet_id: str
    supported_sections: int
    unsupported_assumptions: int
    stale_or_unknown_notes: tuple[str, ...]
    excluded_count: int
    readiness: str


@dataclass(frozen=True)
class ContextEngineStatus:
    status: str
    mode: str
    live_llm_calls_enabled: bool
    provider_sdks_enabled: bool
    tool_execution_enabled: bool
    arbitrary_file_reads_enabled: bool
    secret_config_session_reads_enabled: bool
    next_phase: str
