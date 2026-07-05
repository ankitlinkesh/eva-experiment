from __future__ import annotations

from dataclasses import dataclass

from .risk import DesktopActionRisk


@dataclass(frozen=True)
class DesktopActionTargetPreview:
    label: str
    target_type: str
    confidence: str
    notes: str


@dataclass(frozen=True)
class DesktopActionApprovalRequirement:
    action_type: str
    requirement: str
    status: str


@dataclass(frozen=True)
class DesktopActionStepPreview:
    step_id: str
    action_type: str
    description: str
    target: DesktopActionTargetPreview
    risk: DesktopActionRisk
    would_execute_now: bool
    blocked_reason: str
    required_approval: str


@dataclass(frozen=True)
class DesktopActionPlanPreview:
    request: str
    mode: str
    real_desktop_execution: str
    steps: tuple[DesktopActionStepPreview, ...]
    approvals: tuple[DesktopActionApprovalRequirement, ...]
    next_phase: str


@dataclass(frozen=True)
class DesktopActionDryRun:
    request: str
    execution_enabled: bool
    steps: tuple[DesktopActionStepPreview, ...]
    blocked_execution: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class DesktopActionDryRunResult:
    dry_run: DesktopActionDryRun
    plan: DesktopActionPlanPreview
    status: str
    executed: bool
    ready_for_real_control: bool
