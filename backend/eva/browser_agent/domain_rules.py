from __future__ import annotations

from dataclasses import dataclass

from .site_risk import BrowserSiteRisk, classify_site_risk


@dataclass(frozen=True)
class BrowserDomainRule:
    name: str
    applies_to: str
    decision: str
    note: str


@dataclass(frozen=True)
class BrowserSensitiveActionMarker:
    name: str
    examples: tuple[str, ...]
    requirement: str


@dataclass(frozen=True)
class BrowserDomainDecision:
    domain: str
    risk: BrowserSiteRisk
    allowed_now: bool
    real_browser_access: str
    decision: str
    reason: str
    approval_requirement: str


@dataclass(frozen=True)
class BrowserDomainPolicyResult:
    status: str
    rules: tuple[BrowserDomainRule, ...]
    sensitive_markers: tuple[BrowserSensitiveActionMarker, ...]
    blocked_now: tuple[str, ...]


def get_domain_rules() -> tuple[BrowserDomainRule, ...]:
    return (
        BrowserDomainRule("documentation/search", "documentation, search, developer docs", "low/normal risk preview", "Can be classified from strings only; future read-only access still needs gates."),
        BrowserDomainRule("accounts/private", "email, social, government, shopping, account pages", "sensitive", "Requires future explicit user confirmation and privacy policy."),
        BrowserDomainRule("financial/payment", "banking, payment, checkout", "high risk", "Payment and banking flows remain blocked for automation."),
        BrowserDomainRule("file transfer", "cloud storage, file hosting, upload/download", "high risk", "Upload/download needs future file/path/privacy gates."),
        BrowserDomainRule("harmful", "adult, illegal, malware, phishing, piracy, harmful", "blocked", "No browser execution or approval in this phase."),
    )


def get_sensitive_action_markers() -> tuple[BrowserSensitiveActionMarker, ...]:
    return (
        BrowserSensitiveActionMarker("login", ("sign in", "password", "account"), "future privacy gate; blocked now"),
        BrowserSensitiveActionMarker("external send", ("email", "message", "post", "comment"), "future explicit send confirmation; blocked now"),
        BrowserSensitiveActionMarker("payment", ("checkout", "pay", "bank", "card"), "blocked for automation"),
        BrowserSensitiveActionMarker("file transfer", ("upload", "download", "drive", "dropbox"), "future file/path confirmation; blocked now"),
    )


def evaluate_domain_policy(domain_or_url: str) -> BrowserDomainDecision:
    risk = classify_site_risk(domain_or_url)
    return BrowserDomainDecision(
        domain=risk.domain,
        risk=risk,
        allowed_now=False,
        real_browser_access="locked",
        decision="policy/status only",
        reason=risk.reason,
        approval_requirement=risk.approval_requirement,
    )


def get_domain_policy_result() -> BrowserDomainPolicyResult:
    return BrowserDomainPolicyResult(
        status="policy/status only",
        rules=get_domain_rules(),
        sensitive_markers=get_sensitive_action_markers(),
        blocked_now=(
            "DNS/network calls",
            "browser launch/navigation",
            "live website fetch/read",
            "screenshots/screen capture",
            "DOM access",
            "cookies/localStorage/session/profile/password reads",
            "click/type/submit/login/payment/upload/download",
            "Playwright/browser-use/Stagehand/Maxun/MCP/PyAutoGUI/desktop/shell/package/cloud calls",
        ),
    )
