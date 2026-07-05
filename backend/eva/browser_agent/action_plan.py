from __future__ import annotations

from dataclasses import dataclass

from .risk import BrowserActionRisk


@dataclass(frozen=True)
class BrowserActionApprovalRequirement:
    action_type: str
    requirement: str
    status: str


@dataclass(frozen=True)
class BrowserActionStepPreview:
    step_id: str
    action_type: str
    description: str
    risk: BrowserActionRisk
    would_execute_now: bool
    blocked_reason: str
    required_approval: str


@dataclass(frozen=True)
class BrowserActionPlanPreview:
    request: str
    mode: str
    real_browser_execution: str
    steps: tuple[BrowserActionStepPreview, ...]
    approvals: tuple[BrowserActionApprovalRequirement, ...]
    next_phase: str


@dataclass(frozen=True)
class BrowserActionDryRun:
    request: str
    execution_enabled: bool
    steps: tuple[BrowserActionStepPreview, ...]
    blocked_execution: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class BrowserActionDryRunResult:
    dry_run: BrowserActionDryRun
    plan: BrowserActionPlanPreview
    status: str
