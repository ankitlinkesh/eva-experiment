from __future__ import annotations

from dataclasses import dataclass

from .readiness_proof import build_desktop_readiness_proof, get_locked_desktop_capability_summary


@dataclass(frozen=True)
class DesktopPhase14CompletedLayer:
    name: str
    proof: str


@dataclass(frozen=True)
class DesktopPhase14Limit:
    name: str
    reason: str


@dataclass(frozen=True)
class DesktopPhase14FinalProof:
    phase: str
    status: str
    safety_readiness_only: bool
    real_desktop_observation_enabled: bool
    real_desktop_control_enabled: bool
    approvals_unlock_execution: bool
    completed_layers: tuple[DesktopPhase14CompletedLayer, ...]
    locked_execution: tuple[str, ...]
    limits: tuple[DesktopPhase14Limit, ...]
    future_gate: str
    phase12_boundary: str
    next_phase: str
    summary: str


def get_desktop_phase14_completed_layers() -> tuple[DesktopPhase14CompletedLayer, ...]:
    return (
        DesktopPhase14CompletedLayer("Phase 14A safety model", "DesktopAgent policy/status and blocked-action previews exist."),
        DesktopPhase14CompletedLayer("Phase 14B session preview", "Preview-only app, window, session, and active-context schemas exist without real inspection."),
        DesktopPhase14CompletedLayer("Phase 14C screen observation policy", "Screen redaction, sensitive-screen, and capture-gate policy exists with all observation locked."),
        DesktopPhase14CompletedLayer("Phase 14D action dry-run", "Desktop mouse/keyboard action plans are text-only and non-executing."),
        DesktopPhase14CompletedLayer("Phase 14E risk scoring", "Desktop action risk scoring and safety matrix use request text only."),
        DesktopPhase14CompletedLayer("Phase 14F human approval model", "Approval previews and confirmation phrase classes exist without connecting approval to execution."),
        DesktopPhase14CompletedLayer("Phase 14G locked readiness proof", "Final proof, status commands, Control Center, metadata, planner, team review, and docs agree that execution remains locked."),
    )


def get_desktop_phase14_final_limits() -> tuple[DesktopPhase14Limit, ...]:
    return (
        DesktopPhase14Limit("real desktop observation", "not enabled; no screen, window, app, or active-context inspection is available"),
        DesktopPhase14Limit("real desktop control", "not enabled; mouse, keyboard, clipboard, app launch, and file-dialog actions remain locked"),
        DesktopPhase14Limit("screen interpretation", "not enabled; screen capture, screenshots, OCR, and image analysis remain locked"),
        DesktopPhase14Limit("approval boundary", "not enabled; approvals and confirmation phrases are policy previews and do not unlock execution"),
        DesktopPhase14Limit("automation runtimes", "locked; PyAutoGUI, Playwright, MCP, shell, terminal, package, browser, desktop, and cloud actions are not used"),
        DesktopPhase14Limit("private local state", "locked; .env, .env.local, secrets, tokens, cookies, passwords, browser sessions, and unrelated private content are not read"),
    )


def get_desktop_phase14_proof() -> DesktopPhase14FinalProof:
    readiness = build_desktop_readiness_proof()
    locked = (
        "screen/window/app observation, UI targeting, mouse/keyboard/clipboard/app launch/file dialog, terminal/package, browser/desktop automation, and cloud execution are locked",
        *get_locked_desktop_capability_summary().locked_actions,
    )
    return DesktopPhase14FinalProof(
        phase="Phase 14G",
        status="complete_as_locked_safety_readiness_foundation",
        safety_readiness_only=True,
        real_desktop_observation_enabled=False,
        real_desktop_control_enabled=False,
        approvals_unlock_execution=False,
        completed_layers=get_desktop_phase14_completed_layers(),
        locked_execution=locked,
        limits=get_desktop_phase14_final_limits(),
        future_gate="Future desktop observation or control requires a separate approved gate with explicit user command, local privacy classification, verified UI targeting, per-action permission, local audit evidence, target-aware verification, and safe rollback where possible.",
        phase12_boundary=readiness.phase12_boundary,
        next_phase=readiness.next_phase,
        summary="Phase 14 is safety/readiness only. Real desktop observation is not enabled. Real desktop control is not enabled. Approvals do not unlock execution.",
    )
