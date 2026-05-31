from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from typing import Any

from .controller import discover_current_url, get_current_title, get_current_url, list_browser_tabs
from .safety import normalize_public_url, page_read_safety
from .state import make_observation, remember_page


MAX_PAGE_BYTES = 600_000
MAX_LINKS = 40


def _safe_failure(error: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": error, **extra}


def _target_url(url: str | None = None) -> tuple[str | None, dict[str, Any] | None]:
    target = str(url or "").strip()
    if not target:
        discovered = discover_current_url()
        if discovered.get("ok") and discovered.get("verified") and discovered.get("url"):
            target = str(discovered.get("url") or "").strip()
    if not target:
        return None, _safe_failure(
            "current_url_unavailable",
            fallback="ask_for_url_or_page_text",
            summary="I can't verify the current Chrome page right now. Send me the URL or open it through Eva first.",
        )
    allowed, reason = page_read_safety(target)
    if not allowed:
        return None, _safe_failure(
            reason,
            safety_blocked=True,
            fallback="ask_for_explicit_text",
            summary="I will not read that page automatically. If you want help with it, paste the visible text or a safe public URL.",
        )
    return normalize_public_url(target), None


def _fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "EvaAgent/1.0 (+local desktop assistant)"})
    with urllib.request.urlopen(request, timeout=8) as response:
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            raise ValueError(f"Unsupported page content type: {content_type or 'unknown'}")
        data = response.read(MAX_PAGE_BYTES + 1)
    if len(data) > MAX_PAGE_BYTES:
        data = data[:MAX_PAGE_BYTES]
    return data.decode("utf-8", errors="replace")


def _clean_text(markup: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", markup)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


def _title(markup: str, fallback: str = "") -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", markup)
    if match:
        return _clean_text(match.group(1))[:250]
    meta = re.search(r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', markup)
    if meta:
        return html.unescape(meta.group(1)).strip()[:250]
    return fallback[:250]


def _summary_from_text(title: str, text: str) -> str:
    compact = " ".join(text.split())
    if not compact:
        return f"{title} loaded, but I could not extract readable body text."
    sentences = re.split(r"(?<=[.!?])\s+", compact)
    useful = [sentence for sentence in sentences if len(sentence) > 40][:3]
    summary = " ".join(useful) if useful else compact[:700]
    return summary[:1200]


def summarize_current_page(url: str | None = None) -> dict[str, Any]:
    target, failure = _target_url(url)
    if failure:
        return failure
    assert target is not None
    try:
        markup = _fetch_html(target)
        title = _title(markup, fallback=get_current_title() or target)
        text = _clean_text(markup)
        summary = _summary_from_text(title, text)
        remember_page(title=title, url=target)
        return {
            "ok": True,
            "current_url": target,
            "current_title": title,
            "page_summary": summary,
            "read_method": "public_http_fetch",
            "notes": ["Read only safe public page content. Private browser storage was not accessed."],
        }
    except Exception as exc:
        return _safe_failure(
            "page_read_failed",
            current_url=target,
            current_title=get_current_title(),
            summary=f"I could not read that public page directly: {str(exc)[:240]}",
            fallback="send_url_or_page_text",
        )


def extract_links_from_page(url: str | None = None, limit: int = MAX_LINKS) -> dict[str, Any]:
    target, failure = _target_url(url)
    if failure:
        return failure
    assert target is not None
    try:
        markup = _fetch_html(target)
        title = _title(markup, fallback=get_current_title() or target)
        links: list[dict[str, str]] = []
        for match in re.finditer(r'(?is)<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', markup):
            href = html.unescape(match.group(1)).strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            absolute = urllib.parse.urljoin(target, href)
            try:
                absolute = normalize_public_url(absolute)
            except ValueError:
                continue
            label = _clean_text(match.group(2))[:160] or absolute
            links.append({"text": label, "url": absolute})
            if len(links) >= max(1, min(100, int(limit or MAX_LINKS))):
                break
        remember_page(title=title, url=target)
        return {
            "ok": True,
            "current_url": target,
            "current_title": title,
            "extracted_links": links,
            "count": len(links),
            "notes": ["Extracted links from safe public HTML only."],
        }
    except Exception as exc:
        return _safe_failure("link_extract_failed", current_url=target, error_detail=str(exc)[:240])


def current_page_observation(include_tabs: bool = False, include_page_summary: bool = False, include_links: bool = False) -> dict[str, Any]:
    discovered = discover_current_url()
    current_url = str(discovered.get("url") or "") if discovered.get("ok") and discovered.get("verified") else ""
    source = str(discovered.get("source") or "unknown")
    current_title = get_current_title()
    tabs = list_browser_tabs().get("tabs", []) if include_tabs else []
    page_summary = None
    extracted_links: list[dict[str, str]] = []
    notes = ["Direct browser DOM access is not used in v1."]
    if source:
        notes.append(f"Current URL source: {source}.")
    if not current_url:
        notes.append(str(discovered.get("summary") or "I can't verify the current Chrome page right now."))
    if include_page_summary:
        summary = summarize_current_page(current_url)
        if summary.get("ok"):
            page_summary = str(summary.get("page_summary") or "")
        else:
            notes.append(str(summary.get("summary") or summary.get("error") or "Page summary unavailable."))
    if include_links:
        links = extract_links_from_page(current_url)
        if links.get("ok"):
            extracted_links = links.get("extracted_links") or []
        else:
            notes.append(str(links.get("summary") or links.get("error") or "Links unavailable."))
    return make_observation(
        browser_detected=bool(current_title or tabs),
        active_window_title=current_title,
        current_url=current_url or None,
        current_title=current_title,
        source=source,
        verified=bool(discovered.get("ok") and discovered.get("verified")),
        stale=bool(discovered.get("stale") or not discovered.get("ok")),
        captured_at=discovered.get("captured_at"),
        age_seconds=discovered.get("age_seconds"),
        message=str(discovered.get("summary") or ""),
        tabs=tabs if isinstance(tabs, list) else [],
        page_summary=page_summary,
        extracted_links=extracted_links,
        notes=notes,
    )
