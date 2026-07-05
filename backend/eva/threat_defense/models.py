from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThreatCategory:
    id: str
    name: str
    severity: str
    description: str


@dataclass(frozen=True)
class ThreatFinding:
    category: str
    severity: str
    source_type: str
    summary: str
    action: str


@dataclass(frozen=True)
class InstructionLayer:
    name: str
    trust_level: str
    authority: str
    handling: str


@dataclass(frozen=True)
class DefenseReport:
    request_summary: str
    source_type: str
    findings: tuple[ThreatFinding, ...]
    blocked: bool
    safe_to_send_to_llm: bool
    no_llm_call_made: bool
    tool_execution_enabled: bool
    notes: tuple[str, ...]

    def format(self) -> str:
        from .report import format_defense_report

        return format_defense_report(self)


@dataclass(frozen=True)
class ThreatDefenseStatus:
    status: str
    mode: str
    live_llm_calls_enabled: bool
    provider_sdks_enabled: bool
    tool_execution_enabled: bool
    arbitrary_file_reads_enabled: bool
    secret_config_session_reads_enabled: bool
    next_phase: str
