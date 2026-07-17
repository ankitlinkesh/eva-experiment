"""Turn a typed sentence into a standing rule (Phase 54).

Phase 46 built the rule engine and Phase 53 gave it a loop to run in, but a rule
could only be created from Python — there was no way for a human to say "remind
me every morning to summarize my news" and have that become a real rule. This is
that front door.

It is deliberately a **pure, deterministic parser** — no LLM, no network. A rule
is a durable, standing thing that will fire unattended, so the path that creates
one must be inspectable and reproducible: the same sentence always yields the
same rule, and a sentence it does not understand yields ``None`` rather than a
guess. The caller (a typed-console fast-command) is what turns a parse into a
persisted rule; nothing here writes anything.

Trust boundary: this is reached only from the human-typed console path, never
from the planner. Web pages and tool results (untrusted, per Phase 40) can
already neither authorize nor fire a rule; keeping creation off the planner means
they cannot *stand one up* either. Only the person at the keyboard makes rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .models import (
    DAILY,
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_MAX_FIRES_PER_DAY,
    FILE_CHANGE,
    INTERVAL,
    MAX_FIRES_PER_DAY_CEILING,
)

# Named times of day → 24h "HH:MM". Chosen to match how people actually use the
# words, not clock quadrants (nobody means 00:00 by "morning").
_NAMED_TIMES = {
    "morning": "08:00",
    "noon": "12:00",
    "midday": "12:00",
    "afternoon": "14:00",
    "evening": "18:00",
    "tonight": "20:00",
    "night": "21:00",
    "midnight": "00:00",
}

_UNIT_SECONDS = {
    "second": 1, "seconds": 1, "sec": 1, "secs": 1,
    "minute": 60, "minutes": 60, "min": 60, "mins": 60,
    "hour": 3600, "hours": 3600, "hr": 3600, "hrs": 3600,
}

# Leading command noise stripped off both the whole sentence and the leftover
# request. Longest first so "remind me to" wins over "remind me".
_LEAD_PHRASES = (
    "set a reminder to", "set a reminder", "create a rule to", "create a rule",
    "make a rule to", "make a rule", "remind me to", "remind me", "please",
    "can you", "could you", "schedule",
)

# Filler words peeled off the edges of the extracted request.
_EDGE_WORDS = frozenset({"to", "and", "then", "me", "that", "please", ",", ":", "-", "so", "will", "would"})

# Reasonable interval floor. A rule that proposes work every second is a
# denial-of-service on the user's attention; the scheduler also floors its own
# loop at 5s (Phase 53), so anything below that could never fire that fast anyway.
_MIN_INTERVAL_SECONDS = 5


@dataclass(frozen=True)
class ParsedRule:
    """A rule recovered from a sentence, ready to be persisted by the caller.

    Holds only the fields :meth:`ProactivityStore.add_rule` needs plus a
    human-readable ``summary`` for echoing back what was understood. It is not a
    ``ProactiveRule`` — it carries no id, no fire bookkeeping — precisely because
    parsing must not look like creation.
    """

    kind: str
    spec: dict[str, Any]
    request: str
    name: str
    summary: str
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS
    max_fires_per_day: int = DEFAULT_MAX_FIRES_PER_DAY
    matched: str = field(default="", compare=False)  # the trigger substring, for debugging

    def as_add_rule_kwargs(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "spec": dict(self.spec),
            "request": self.request,
            "cooldown_seconds": self.cooldown_seconds,
            "max_fires_per_day": self.max_fires_per_day,
        }


def _normalize(text: object) -> str:
    return " ".join(str(text or "").split())


def _strip_lead(text: str) -> str:
    """Remove one leading command phrase (case-insensitive), repeatedly."""
    changed = True
    while changed:
        changed = False
        low = text.lower()
        for phrase in _LEAD_PHRASES:
            if low.startswith(phrase + " ") or low == phrase:
                text = text[len(phrase):].lstrip(" ,:-")
                changed = True
                break
    return text


def _clean_request(text: str) -> str:
    """Peel command noise and connective words off both ends of a request."""
    text = _strip_lead(text).strip(" ,:-")
    words = text.split()
    while words and words[0].lower() in _EDGE_WORDS:
        words.pop(0)
    while words and words[-1].lower() in _EDGE_WORDS:
        words.pop()
    return " ".join(words)


def _time_to_hhmm(hour_s: str, minute_s: str | None, meridiem: str | None) -> str | None:
    try:
        hour = int(hour_s)
        minute = int(minute_s) if minute_s else 0
    except (TypeError, ValueError):
        return None
    mer = (meridiem or "").lower()
    if mer == "pm" and hour < 12:
        hour += 12
    elif mer == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return f"{hour:02d}:{minute:02d}"


def _short_name(request: str, kind: str) -> str:
    words = request.split()
    stub = " ".join(words[:6]) if words else kind
    return (stub[:60] or kind).strip()


# -- the three shapes -------------------------------------------------------
# Ordered most-specific first. FILE_CHANGE owns the word "change(s)"; INTERVAL
# owns "every <N> <unit>"; DAILY owns "every day/<named time>" and bare "at TIME".

_FILE_RE = re.compile(
    r"\b(?:when(?:ever)?|if)\s+(?P<path>\S.*?)\s+(?:is\s+)?(?:changes?|changed|is\s+modified|updates?|is\s+updated)\b",
    re.IGNORECASE,
)
_INTERVAL_RE = re.compile(
    r"\bevery\s+(?P<n>\d+)\s+(?P<unit>seconds?|secs?|minutes?|mins?|hours?|hrs?)\b",
    re.IGNORECASE,
)
_TIME_RE = r"(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<mer>am|pm)?"
_DAILY_NAMED_RE = re.compile(
    r"\b(?:every|each)\s+(?P<word>morning|noon|midday|afternoon|evening|tonight|night|midnight)\b"
    r"(?:\s+at\s+" + _TIME_RE + r")?",
    re.IGNORECASE,
)
_DAILY_EVERYDAY_RE = re.compile(
    r"\b(?:every\s*day|everyday|each\s+day|daily)\b(?:\s+at\s+" + _TIME_RE + r")?",
    re.IGNORECASE,
)
_DAILY_AT_RE = re.compile(r"\bat\s+" + _TIME_RE + r"\b", re.IGNORECASE)


def _parse_file_change(text: str) -> ParsedRule | None:
    m = _FILE_RE.search(text)
    if not m:
        return None
    path = m.group("path").strip().strip("'\"")
    # The path grabs greedily-then-lazily; trim a trailing verb it may have eaten.
    if not path:
        return None
    request = _clean_request(text[: m.start()] + " " + text[m.end():])
    if not request:
        request = f"tell me that {path} changed"
    return ParsedRule(
        kind=FILE_CHANGE,
        spec={"path": path},
        request=request,
        name=_short_name(request, "watch"),
        summary=f"When '{path}' changes, propose: {request}",
        matched=m.group(0),
    )


def _parse_interval(text: str) -> ParsedRule | None:
    m = _INTERVAL_RE.search(text)
    if not m:
        return None
    unit = m.group("unit").lower()
    seconds = int(m.group("n")) * _UNIT_SECONDS.get(unit, 0)
    if seconds < _MIN_INTERVAL_SECONDS:
        seconds = _MIN_INTERVAL_SECONDS
    request = _clean_request(text[: m.start()] + " " + text[m.end():])
    if not request:
        return None
    return ParsedRule(
        kind=INTERVAL,
        spec={"seconds": seconds},
        request=request,
        name=_short_name(request, "interval"),
        summary=f"Every {seconds}s, propose: {request}",
        # The interval itself paces firing; a 60s cooldown would double-space
        # short intervals. Cap the daily budget instead so it cannot run away.
        cooldown_seconds=0,
        max_fires_per_day=MAX_FIRES_PER_DAY_CEILING,
        matched=m.group(0),
    )


def _parse_daily(text: str) -> ParsedRule | None:
    for regex, default_time in ((_DAILY_NAMED_RE, None), (_DAILY_EVERYDAY_RE, "09:00")):
        m = regex.search(text)
        if not m:
            continue
        groups = m.groupdict()
        at = _time_to_hhmm(groups.get("h"), groups.get("m"), groups.get("mer")) if groups.get("h") else None
        if at is None:
            word = groups.get("word")
            at = _NAMED_TIMES.get((word or "").lower(), default_time or "09:00")
        request = _clean_request(text[: m.start()] + " " + text[m.end():])
        if not request:
            return None
        return ParsedRule(
            kind=DAILY,
            spec={"at": at},
            request=request,
            name=_short_name(request, "daily"),
            summary=f"Every day at {at}, propose: {request}",
            matched=m.group(0),
        )
    # Bare "at HH:MM" with no cadence word — treat as a daily reminder.
    m = _DAILY_AT_RE.search(text)
    if m and re.search(r"\bremind|reminder|every\s*day|daily\b", text, re.IGNORECASE):
        at = _time_to_hhmm(m.group("h"), m.group("m"), m.group("mer"))
        if at is None:
            return None
        request = _clean_request(text[: m.start()] + " " + text[m.end():])
        if not request:
            return None
        return ParsedRule(
            kind=DAILY,
            spec={"at": at},
            request=request,
            name=_short_name(request, "daily"),
            summary=f"Every day at {at}, propose: {request}",
            matched=m.group(0),
        )
    return None


def parse_rule_request(text: object) -> ParsedRule | None:
    """Parse a typed sentence into a :class:`ParsedRule`, or ``None``.

    Deterministic and side-effect free. ``None`` means "I did not recognise a
    schedule or trigger here" — the caller should then leave the input alone
    rather than invent a rule. Tries file-change, then interval, then daily.
    """
    normalized = _normalize(text)
    if not normalized:
        return None
    # Strip leading command noise before matching so "remind me to X every
    # morning" and "every morning remind me to X" parse the same.
    stripped = _strip_lead(normalized)
    for parser in (_parse_file_change, _parse_interval, _parse_daily):
        try:
            parsed = parser(stripped)
        except Exception:
            parsed = None
        if parsed is not None and parsed.request:
            return parsed
    return None


__all__ = ["ParsedRule", "parse_rule_request"]
