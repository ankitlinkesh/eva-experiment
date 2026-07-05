from __future__ import annotations

from dataclasses import dataclass

from .readiness_proof import build_browser_readiness_proof, get_locked_browser_execution_summary


@dataclass(frozen=True)
class BrowserPhase13CompletedLayer:
    name: str
    proof: str


@dataclass(frozen=True)
class BrowserPhase13Limit:
    name: str
    reason: str


@dataclass(frozen=True)
class BrowserPhase13FinalProof:
    phase: str
    status: str
    safety_readiness_only: bool
    real_readonly_enabled: bool
    real_control_enabled: bool
    completed_layers: tuple[BrowserPhase13CompletedLayer, ...]
    locked_execution: tuple[str, ...]
    limits: tuple[BrowserPhase13Limit, ...]
    future_gate: str
    phase12_boundary: str
    next_phase: str
    summary: str


def get_browser_phase13_completed_layers() -> tuple[BrowserPhase13CompletedLayer, ...]:
    return (
        BrowserPhase13CompletedLayer("Phase 13A safety model", "BrowserAgent policy/status and blocked-action previews exist."),
        BrowserPhase13CompletedLayer("Phase 13B session preview", "Preview-only session records exist without launching a browser."),
        BrowserPhase13CompletedLayer("Phase 13C observation design", "Page/text/DOM summary schemas and redaction policy exist as mock/status surfaces."),
        BrowserPhase13CompletedLayer("Phase 13D action dry-run", "Browser actions can be described as dry-run plans without execution."),
        BrowserPhase13CompletedLayer("Phase 13E domain policy", "Domain/site-risk strings can be classified locally without DNS or network calls."),
        BrowserPhase13CompletedLayer("Phase 13F readiness proof", "Read-only readiness checks and gaps prove real browser mode remains locked."),
        BrowserPhase13CompletedLayer("Phase 13G hardening", "Final proof commands, Control Center wording, planner/capability metadata, and docs align on locked status."),
    )


def get_browser_phase13_final_limits() -> tuple[BrowserPhase13Limit, ...]:
    return (
        BrowserPhase13Limit("real browser read-only mode", "not enabled; a separate approved gate is required before live page observation"),
        BrowserPhase13Limit("real browser control", "not enabled; click, type, submit, login, upload, download, and payment actions remain locked"),
        BrowserPhase13Limit("network and DNS", "locked; BrowserAgent Phase 13 does not fetch, resolve, or open live websites"),
        BrowserPhase13Limit("live page, DOM, and screenshots", "locked; no live page read, DOM read, screen capture, or screenshot observation is enabled"),
        BrowserPhase13Limit("browser private state", "locked; no cookie, localStorage, session, profile, password, or token reads are allowed"),
        BrowserPhase13Limit("automation runtimes", "locked; Playwright, browser-use, Stagehand, Maxun, MCP, PyAutoGUI, shell, package, desktop, and cloud calls are not used"),
    )


def build_browser_phase13_final_proof() -> BrowserPhase13FinalProof:
    readiness = build_browser_readiness_proof()
    locked = (
        "network/DNS/live page read/DOM/screenshot/action execution are locked",
        *get_locked_browser_execution_summary(),
    )
    return BrowserPhase13FinalProof(
        phase="Phase 13G",
        status="complete_as_safety_readiness_foundation",
        safety_readiness_only=True,
        real_readonly_enabled=False,
        real_control_enabled=False,
        completed_layers=get_browser_phase13_completed_layers(),
        locked_execution=locked,
        limits=get_browser_phase13_final_limits(),
        future_gate="Future real browser read-only mode must go through a separate approved gate with explicit user approval, domain policy, redaction, target verification, and audit.",
        phase12_boundary=readiness.phase12_boundary,
        next_phase="Phase 14: DesktopAgent Safety Model. News/Web Intelligence and Coding Specialist/CodingAgent remain later roadmap items.",
        summary="Phase 13 is safety/readiness only. Real browser read-only mode is not enabled. Real browser control is not enabled.",
    )
