from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BrowserSiteRiskLevel(StrEnum):
    SAFE_STATIC = "safe_static"
    NORMAL_WEB = "normal_web"
    ACCOUNT_REQUIRED = "account_required"
    SENSITIVE_LOGIN = "sensitive_login"
    FINANCIAL_OR_PAYMENT = "financial_or_payment"
    FILE_TRANSFER = "file_transfer"
    MESSAGING_OR_EXTERNAL_SEND = "messaging_or_external_send"
    ADULT_OR_ILLEGAL_OR_HARMFUL = "adult_or_illegal_or_harmful"
    UNKNOWN_HIGH_RISK = "unknown_high_risk"
    BLOCKED = "blocked"


class BrowserSiteCategory(StrEnum):
    DOCUMENTATION = "documentation"
    SEARCH = "search"
    SHOPPING = "shopping"
    BANKING = "banking"
    PAYMENT = "payment"
    SOCIAL = "social"
    EMAIL = "email"
    CLOUD_STORAGE = "cloud_storage"
    GOVERNMENT = "government"
    EDUCATION = "education"
    DEVELOPER_TOOLS = "developer_tools"
    AI_TOOLS = "ai_tools"
    FILE_HOSTING = "file_hosting"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BrowserSiteRisk:
    input_value: str
    domain: str
    category: BrowserSiteCategory
    level: BrowserSiteRiskLevel
    reason: str
    approval_requirement: str
    blocked_now: bool


def classify_site_risk(domain_or_url: str) -> BrowserSiteRisk:
    domain = normalize_domain(domain_or_url)
    category = _category_for(domain)
    level = _level_for(domain, category)
    return BrowserSiteRisk(
        input_value=str(domain_or_url or "").strip(),
        domain=domain or "unknown",
        category=category,
        level=level,
        reason=_reason_for(domain, category, level),
        approval_requirement=_approval_for(level),
        blocked_now=level not in {BrowserSiteRiskLevel.SAFE_STATIC, BrowserSiteRiskLevel.NORMAL_WEB},
    )


def normalize_domain(domain_or_url: str) -> str:
    text = str(domain_or_url or "").strip().lower()
    text = text.replace("https://", "").replace("http://", "")
    text = text.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if "@" in text:
        text = text.rsplit("@", 1)[-1]
    if text.startswith("www."):
        text = text[4:]
    return "".join(ch for ch in text if ch.isalnum() or ch in ".-")[:120]


def _category_for(domain: str) -> BrowserSiteCategory:
    if not domain:
        return BrowserSiteCategory.UNKNOWN
    if domain in {"example.com", "example.org", "example.net"}:
        return BrowserSiteCategory.DOCUMENTATION
    if any(part in domain for part in ("docs.", "developer.", "readthedocs", "wikipedia", "python.org", "mozilla.org")):
        return BrowserSiteCategory.DOCUMENTATION
    if any(part in domain for part in ("github.", "gitlab.", "stackoverflow.", "huggingface.")):
        return BrowserSiteCategory.DEVELOPER_TOOLS
    if any(part in domain for part in ("openai.", "chatgpt.", "anthropic.", "perplexity.")):
        return BrowserSiteCategory.AI_TOOLS
    if any(part in domain for part in ("gmail.", "mail.", "outlook.", "proton.")):
        return BrowserSiteCategory.EMAIL
    if any(part in domain for part in ("drive.google.", "dropbox.", "onedrive.", "icloud.", "box.")):
        return BrowserSiteCategory.CLOUD_STORAGE
    if any(part in domain for part in ("google.", "bing.", "duckduckgo.", "search.")):
        return BrowserSiteCategory.SEARCH
    if any(part in domain for part in ("paypal.", "stripe.", "checkout.", "pay.")):
        return BrowserSiteCategory.PAYMENT
    if any(part in domain for part in ("bank", "chase.", "wellsfargo.", "capitalone.", "hdfcbank", "icicibank")):
        return BrowserSiteCategory.BANKING
    if any(part in domain for part in ("facebook.", "instagram.", "x.com", "twitter.", "linkedin.", "reddit.", "whatsapp.")):
        return BrowserSiteCategory.SOCIAL
    if any(part in domain for part in ("amazon.", "shop", "store", "ebay.")):
        return BrowserSiteCategory.SHOPPING
    if any(part in domain for part in ("mega.", "mediafire.", "wetransfer.", "file", "upload")):
        return BrowserSiteCategory.FILE_HOSTING
    if any(part in domain for part in (".gov", "gov.", "irs.", "uidai.", "india.gov")):
        return BrowserSiteCategory.GOVERNMENT
    if any(part in domain for part in (".edu", "edu.", "coursera.", "khanacademy.")):
        return BrowserSiteCategory.EDUCATION
    return BrowserSiteCategory.UNKNOWN


def _level_for(domain: str, category: BrowserSiteCategory) -> BrowserSiteRiskLevel:
    if any(part in domain for part in ("malware", "phishing", "adult", "illegal", "harmful", "crack", "piracy")):
        return BrowserSiteRiskLevel.BLOCKED
    if category == BrowserSiteCategory.DOCUMENTATION:
        return BrowserSiteRiskLevel.SAFE_STATIC
    if category in {BrowserSiteCategory.SEARCH, BrowserSiteCategory.DEVELOPER_TOOLS, BrowserSiteCategory.AI_TOOLS, BrowserSiteCategory.EDUCATION}:
        return BrowserSiteRiskLevel.NORMAL_WEB
    if category in {BrowserSiteCategory.BANKING, BrowserSiteCategory.PAYMENT}:
        return BrowserSiteRiskLevel.FINANCIAL_OR_PAYMENT
    if category in {BrowserSiteCategory.EMAIL, BrowserSiteCategory.SOCIAL}:
        return BrowserSiteRiskLevel.MESSAGING_OR_EXTERNAL_SEND
    if category in {BrowserSiteCategory.CLOUD_STORAGE, BrowserSiteCategory.FILE_HOSTING}:
        return BrowserSiteRiskLevel.FILE_TRANSFER
    if category in {BrowserSiteCategory.SHOPPING, BrowserSiteCategory.GOVERNMENT}:
        return BrowserSiteRiskLevel.ACCOUNT_REQUIRED
    if "login" in domain or "account" in domain or "private" in domain:
        return BrowserSiteRiskLevel.SENSITIVE_LOGIN
    return BrowserSiteRiskLevel.UNKNOWN_HIGH_RISK


def _reason_for(domain: str, category: BrowserSiteCategory, level: BrowserSiteRiskLevel) -> str:
    if level == BrowserSiteRiskLevel.SAFE_STATIC:
        return "Looks like static documentation or public reference content."
    if level == BrowserSiteRiskLevel.NORMAL_WEB:
        return "Looks like a normal public web category, but real browser access is still locked."
    if level == BrowserSiteRiskLevel.BLOCKED:
        return "Domain text suggests adult, illegal, harmful, malware, phishing, piracy, or abuse risk."
    return f"Category {category.value} can involve accounts, private data, external sends, payments, or file transfer."


def _approval_for(level: BrowserSiteRiskLevel) -> str:
    if level in {BrowserSiteRiskLevel.SAFE_STATIC, BrowserSiteRiskLevel.NORMAL_WEB}:
        return "future read-only domain gate"
    if level == BrowserSiteRiskLevel.BLOCKED:
        return "blocked; no approval in this phase"
    return "future explicit user confirmation plus privacy/safety gate"
