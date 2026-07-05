from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserRedactionRule:
    name: str
    applies_to: str
    replacement: str
    note: str


@dataclass(frozen=True)
class BrowserObservationPolicy:
    mode: str
    live_page_reads_allowed: bool
    dom_reads_allowed: bool
    screenshots_allowed: bool
    browser_launch_allowed: bool
    allowed_now: tuple[str, ...]
    blocked_now: tuple[str, ...]
    future_requirements: tuple[str, ...]
    redaction_rules: tuple[BrowserRedactionRule, ...]


@dataclass(frozen=True)
class BrowserObservationSafetyDecision:
    action: str
    decision: str
    allowed_now: bool
    reason: str
    safe_alternative: str


def get_browser_redaction_rules() -> tuple[BrowserRedactionRule, ...]:
    return (
        BrowserRedactionRule("cookies and session tokens", "headers, page text, forms, and future extraction buffers", "[REDACTED_SESSION]", "Never expose browser cookies, sessions, CSRF tokens, auth headers, or login artifacts."),
        BrowserRedactionRule("API keys and bearer tokens", "page text and user-provided mock text", "[REDACTED_TOKEN]", "Token-like strings are redacted before summaries or previews."),
        BrowserRedactionRule("password fields", "forms and visible text", "[REDACTED_PASSWORD]", "Password-like data must not be summarized or stored."),
        BrowserRedactionRule("private contact data", "page text", "[REDACTED_PRIVATE_CONTACT]", "Emails and phone-like text should be minimized unless user explicitly requests local handling."),
        BrowserRedactionRule("payment and account data", "forms, tables, and page text", "[REDACTED_SENSITIVE_ACCOUNT]", "Payment, banking, account, and admin pages require future refusal or explicit gates."),
    )


def get_browser_observation_policy() -> BrowserObservationPolicy:
    return BrowserObservationPolicy(
        mode="design_only",
        live_page_reads_allowed=False,
        dom_reads_allowed=False,
        screenshots_allowed=False,
        browser_launch_allowed=False,
        allowed_now=(
            "define page/text/DOM summary schemas",
            "create summaries from user-provided mock text only",
            "explain future read-only observation design",
            "show redaction and privacy rules",
            "show screenshot, DOM, and live-read locked status",
        ),
        blocked_now=(
            "live page reads",
            "DOM access or page extraction from a browser",
            "screenshots or screen capture",
            "browser launch or navigation",
            "click, type, submit, login, payment, upload, or download",
            "cookie, localStorage, profile, session, password, or token reads",
            "Playwright, browser-use, Stagehand, Maxun, MCP, PyAutoGUI, desktop, shell, package, or cloud calls",
        ),
        future_requirements=(
            "explicit user-commanded read-only mode",
            "domain and private-page policy before observation",
            "local-only redaction before any summary",
            "no cookies, localStorage, passwords, sessions, or browser profile access",
            "clear provenance that summaries came from live observation versus user-provided text",
            "human confirmation before any future private or external content handling",
        ),
        redaction_rules=get_browser_redaction_rules(),
    )


def evaluate_observation_safety(action: str) -> BrowserObservationSafetyDecision:
    normalized = " ".join(str(action or "unknown").strip().lower().replace("-", "_").split())
    if normalized in {"mock_text_preview", "schema_preview", "redaction_policy", "observation_policy"}:
        return BrowserObservationSafetyDecision(
            action=normalized,
            decision="preview_only",
            allowed_now=True,
            reason="Preview-only schema and user-provided mock text handling are allowed because no browser or live page is touched.",
            safe_alternative="Use browser page summary preview with user-provided mock text.",
        )
    return BrowserObservationSafetyDecision(
        action=normalized,
        decision="locked",
        allowed_now=False,
        reason="Live browser observation is locked in Phase 13C. Eva cannot read pages, DOM, screenshots, browser sessions, or profiles.",
        safe_alternative="Use the page/text/DOM summary policy or a user-provided mock-text preview.",
    )
