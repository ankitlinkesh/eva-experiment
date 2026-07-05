from __future__ import annotations

from dataclasses import dataclass

from .observation_policy import get_browser_redaction_rules


@dataclass(frozen=True)
class BrowserPageSummaryPreview:
    title: str
    source: str
    summary: str
    sections: tuple[str, ...]
    redaction_applied: bool
    live_page_read: bool
    notes: tuple[str, ...]


@dataclass(frozen=True)
class BrowserTextSummaryPreview:
    source: str
    detected_blocks: tuple[str, ...]
    summary: str
    redaction_applied: bool
    live_page_read: bool


@dataclass(frozen=True)
class BrowserDomSummaryPreview:
    source: str
    schema_fields: tuple[str, ...]
    blocked_fields: tuple[str, ...]
    live_dom_read: bool
    notes: tuple[str, ...]


@dataclass(frozen=True)
class BrowserExtractionPreview:
    extraction_mode: str
    live_extraction_enabled: bool
    allowed_sources: tuple[str, ...]
    blocked_sources: tuple[str, ...]
    output_fields: tuple[str, ...]
    redaction_rules: tuple[str, ...]


def create_mock_page_summary_preview(title: str = "Example page", text: str = "User-provided mock text.") -> BrowserPageSummaryPreview:
    sanitized = _sanitize_mock_text(text)
    return BrowserPageSummaryPreview(
        title=_safe_title(title),
        source="user_provided_mock_text",
        summary=_summary_sentence(sanitized),
        sections=_mock_sections(sanitized),
        redaction_applied=sanitized != text,
        live_page_read=False,
        notes=(
            "This preview uses only text supplied to Eva, not a live webpage.",
            "Future live page summaries must label source, domain, privacy risk, and redaction status.",
            "Live browser observation is locked.",
        ),
    )


def create_mock_text_summary_preview(text: str = "Heading\nBody text\nFooter") -> BrowserTextSummaryPreview:
    sanitized = _sanitize_mock_text(text)
    blocks = tuple(line.strip() for line in sanitized.splitlines() if line.strip())[:6]
    return BrowserTextSummaryPreview(
        source="user_provided_mock_text",
        detected_blocks=blocks or ("No text blocks supplied.",),
        summary=_summary_sentence(sanitized),
        redaction_applied=sanitized != text,
        live_page_read=False,
    )


def create_schema_dom_summary_preview() -> BrowserDomSummaryPreview:
    return BrowserDomSummaryPreview(
        source="schema_design_only",
        schema_fields=("page_title", "url_domain", "headings", "main_text_summary", "links_count", "forms_present", "privacy_risk", "redaction_status"),
        blocked_fields=("cookies", "localStorage", "sessionStorage", "password fields", "browser profile data", "hidden tokens", "raw DOM dump"),
        live_dom_read=False,
        notes=(
            "DOM summary is a future schema only.",
            "Raw DOM dumps and hidden/session data are not part of the design.",
            "Live DOM access is locked.",
        ),
    )


def create_extraction_preview() -> BrowserExtractionPreview:
    return BrowserExtractionPreview(
        extraction_mode="design_preview_only",
        live_extraction_enabled=False,
        allowed_sources=("user-provided mock text", "future explicitly approved read-only observation summary"),
        blocked_sources=("live DOM", "screenshots", "cookies", "localStorage", "browser profile", "password/session/token data", "private logged-in pages"),
        output_fields=("title", "short_summary", "key_sections", "visible_link_labels", "privacy_risk", "redaction_note", "source_provenance"),
        redaction_rules=tuple(rule.name for rule in get_browser_redaction_rules()),
    )


def _safe_title(title: str) -> str:
    text = " ".join(str(title or "Example page").split())
    return text[:80] or "Example page"


def _summary_sentence(text: str) -> str:
    compact = " ".join(str(text or "").split())
    if not compact:
        return "No user-provided mock text was supplied."
    return compact[:180] + ("..." if len(compact) > 180 else "")


def _mock_sections(text: str) -> tuple[str, ...]:
    words = " ".join(str(text or "").split()).split()
    if not words:
        return ("No sections available from mock text.",)
    first = " ".join(words[:12])
    second = " ".join(words[12:24])
    return tuple(item for item in (first, second) if item)


def _sanitize_mock_text(text: str) -> str:
    sanitized = str(text or "")
    replacements = ("api_key", "bearer ", "token=", "password=", "cookie=")
    lowered = sanitized.lower()
    if any(marker in lowered for marker in replacements):
        sanitized = "[REDACTED_TOKEN_LIKE_TEXT]"
    return sanitized
