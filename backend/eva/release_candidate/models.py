from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReleaseCandidateReport:
    release_candidate_id: str
    phase: str
    head_reference: str
    dirty_tree_summary: str
    milestone_summary: tuple[str, ...]
    changed_area_groups: tuple[str, ...]
    untracked_area_groups: tuple[str, ...]
    commit_grouping_plan: tuple[str, ...]
    verification_status: str
    docs_consistency_status: str
    safety_boundary_status: str
    known_warnings: tuple[str, ...]
    blocking_issues: tuple[str, ...]
    non_blocking_warnings: tuple[str, ...]
    release_candidate_checklist: tuple[str, ...]
    recommended_next_action: str
    final_readiness_status: str
    no_commit_statement: str
    no_tag_statement: str
    no_push_statement: str
    no_publish_statement: str
    no_secret_read_statement: str
    no_runtime_execution_unlock_statement: str
    no_new_write_path_statement: str


@dataclass(frozen=True)
class ReleaseCandidateStatus:
    available: bool
    mode: str
    git_operations_enabled: bool
    publishing_enabled: bool
    runtime_execution_enabled: bool
    readiness: str
    next_safe_step: str
