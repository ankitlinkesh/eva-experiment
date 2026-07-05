from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class MemoryV3Record:
    memory_id: str
    memory_summary: str
    source_type: str
    source_trust_level: str
    created_at: str
    updated_at: str
    freshness_status: str
    confidence_score: float
    privacy_class: str
    sensitivity_flags: tuple[str, ...]
    conflict_status: str
    grounding_notes: tuple[str, ...]
    context_injection_eligibility: str
    exclusion_reason: str
    final_readiness_status: str
    local_only_statement: str
    no_live_llm_call_statement: str
    no_cloud_memory_statement: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def format(self) -> str:
        from .report import format_memory_record

        return format_memory_record(self)


@dataclass(frozen=True)
class MemoryRetrievalPreview:
    preview_id: str
    request_summary: str
    included_records: tuple[MemoryV3Record, ...]
    excluded_records: tuple[MemoryV3Record, ...]
    context_rules: tuple[str, ...]
    final_readiness_status: str
    local_only_statement: str
    no_live_llm_call_statement: str
    no_cloud_memory_statement: str
    safety_notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def format(self) -> str:
        from .report import format_retrieval_preview

        return format_retrieval_preview(self)


@dataclass(frozen=True)
class MemoryV3Status:
    status: str
    mode: str
    local_only: bool
    live_llm_calls_enabled: bool
    provider_sdks_enabled: bool
    cloud_memory_enabled: bool
    remote_sync_enabled: bool
    tool_execution_enabled: bool
    arbitrary_file_reads_enabled: bool
    arbitrary_file_writes_enabled: bool
    raw_memory_db_dumps_enabled: bool
    secret_config_session_reads_enabled: bool
    next_phase: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
