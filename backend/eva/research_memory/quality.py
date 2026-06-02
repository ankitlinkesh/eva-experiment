from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher

from .config import MAX_TAGS


def normalize_tags(tags: object, limit: int = MAX_TAGS) -> list[str]:
    if isinstance(tags, str):
        parts = re.split(r"[,;\s]+", tags)
    elif isinstance(tags, (list, tuple, set)):
        parts = [str(item) for item in tags]
    else:
        parts = []
    seen: list[str] = []
    for part in parts:
        tag = re.sub(r"[^a-z0-9+#.-]+", "", str(part).strip().lower())[:40]
        if len(tag) < 2 or tag in seen:
            continue
        seen.append(tag)
        if len(seen) >= max(1, min(MAX_TAGS, int(limit or MAX_TAGS))):
            break
    return seen


def normalized_content(title: str, text: str) -> str:
    combined = f"{title or ''} {text or ''}".lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", combined).split())


def content_hash(title: str, text: str) -> str:
    return hashlib.sha256(normalized_content(title, text).encode("utf-8")).hexdigest()


def quality_warnings(title: str, text: str, content_hash_value: str = "") -> list[str]:
    clean_title = str(title or "").strip()
    clean_text = str(text or "").strip()
    words = re.findall(r"[A-Za-z0-9]+", clean_text)
    urls = re.findall(r"https?://\S+", clean_text)
    warnings: list[str] = []
    if not clean_title or clean_title.lower() in {"untitled", "note", "general"}:
        warnings.append("missing title")
    if len(words) < 4:
        warnings.append("very short note")
    if urls and len(" ".join(urls)) >= max(1, int(len(clean_text) * 0.7)):
        warnings.append("mostly urls only")
    if content_hash_value:
        warnings.append("hash available")
    return warnings


def quality_score(title: str, text: str, warnings: list[str] | None = None) -> float:
    penalty = len([warning for warning in (warnings or []) if warning != "hash available"]) * 0.2
    word_bonus = min(0.4, len(re.findall(r"[A-Za-z0-9]+", str(text or ""))) / 80)
    return round(max(0.0, min(1.0, 0.7 + word_bonus - penalty)), 2)


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalized_content("", left), normalized_content("", right)).ratio()


def find_duplicate_groups() -> tuple[list[list[object]], list[tuple[object, object, float]]]:
    from .store import list_research_items

    items = list_research_items(limit=5000)
    by_hash: dict[str, list[object]] = {}
    for item in items:
        if item.content_hash:
            by_hash.setdefault(item.content_hash, []).append(item)
    exact = [group for group in by_hash.values() if len(group) > 1]
    near: list[tuple[object, object, float]] = []
    for index, left in enumerate(items):
        left_text = f"{left.title} {left.summary}"
        for right in items[index + 1 :]:
            if left.content_hash and right.content_hash and left.content_hash == right.content_hash:
                continue
            score = similarity(left_text, f"{right.title} {right.summary}")
            if score >= 0.68:
                near.append((left, right, score))
                if len(near) >= 10:
                    return exact, near
    return exact, near


def low_quality_items() -> list[object]:
    from .store import list_research_items

    exact, near = find_duplicate_groups()
    duplicate_ids = {item.id for group in exact for item in group}
    duplicate_ids.update(item.id for pair in near for item in pair[:2])
    items = []
    for item in list_research_items(limit=5000):
        warnings = list(item.quality_warnings)
        if item.id in duplicate_ids and "duplicate-like" not in warnings:
            warnings.append("duplicate-like")
        meaningful = [warning for warning in warnings if warning != "hash available"]
        if meaningful:
            item.quality_warnings = meaningful
            items.append(item)
    return items


def format_research_tags() -> str:
    from .store import list_research_items

    counts: dict[str, int] = {}
    for item in list_research_items(limit=5000):
        for tag in item.tags:
            counts[tag] = counts.get(tag, 0) + 1
    if not counts:
        return "Research memory tags: no tags saved yet."
    lines = ["Research memory tags:"]
    for tag, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
        lines.append(f"- {tag}: {count}")
    return "\n".join(lines)


def format_duplicates_preview() -> str:
    exact, near = find_duplicate_groups()
    if not exact and not near:
        return "Research memory duplicates: no exact or near-duplicate groups found. No items were deleted."
    lines = ["Research memory duplicates preview:"]
    for group in exact[:8]:
        titles = ", ".join(f"{item.title} ({item.id})" for item in group[:4])
        lines.append(f"- Exact duplicate: {titles}")
    for left, right, score in near[:8]:
        lines.append(f"- Near duplicate ({score:.2f}): {left.title} ({left.id}) ~ {right.title} ({right.id})")
    if not near:
        lines.append("Near-duplicate preview is exact-only for this result set.")
    lines.append("Preview only. No duplicate items were merged or deleted.")
    return "\n".join(lines)


def format_quality_report() -> str:
    items = low_quality_items()
    if not items:
        return "Research memory quality: no low-quality notes found."
    lines = ["Research memory quality warnings:"]
    for item in items[:20]:
        warnings = ", ".join(item.quality_warnings)
        lines.append(f"- {item.title} [{item.topic}] ({item.id}): {warnings}")
    lines.append("No items were changed or deleted.")
    return "\n".join(lines)
