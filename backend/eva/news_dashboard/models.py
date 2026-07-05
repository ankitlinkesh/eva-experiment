from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class SourceCard:
    source_id: str; source_title: str; source_type: str; public_url: str; freshness_label: str
    reliability_note: str; summary: str; citation_metadata: str; safety_status: str; exclusion_reason: str

@dataclass(frozen=True)
class EventCard:
    event_id: str; event_title: str; event_summary: str; related_sources: tuple[str, ...]
    freshness_label: str; confidence_uncertainty_label: str; duplicate_group_id: str
    what_changed_why_it_matters: str; safety_notes: str

@dataclass(frozen=True)
class NewsDashboard:
    dashboard_id: str; topic: str; query_summary: str; backend_mode: str
    source_cards: tuple[SourceCard, ...]; event_cards: tuple[EventCard, ...]
    freshness_labels: tuple[str, ...]; source_reliability_notes: tuple[str, ...]
    duplicate_grouping_notes: tuple[str, ...]; uncertainty_notes: tuple[str, ...]
    safety_notes: tuple[str, ...]; blocked_source_notes: tuple[str, ...]
    citation_source_metadata: tuple[str, ...]; final_status: str
    no_unrestricted_crawling_statement: str; no_login_session_cookie_profile_statement: str
    no_browser_control_statement: str; no_live_llm_call_statement: str
    no_tool_execution_statement: str; no_new_write_path_statement: str

@dataclass(frozen=True)
class NewsStatus:
    available: bool; backend_mode: str; live_backend_available: bool; readiness: str; next_phase: str
