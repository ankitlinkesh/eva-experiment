from __future__ import annotations

import re
from pathlib import Path

from ..privacy.redaction import redact_secrets
from .models import CodeSymbol


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,80}|[A-Za-z0-9_.:/-]{3,120}")


def safe_decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def looks_binary(text: str) -> bool:
    return "\x00" in text[:4096]


def redact_text(text: str) -> tuple[str, int]:
    redacted, events = redact_secrets(text)
    return redacted, len(events)


def make_summary(path: str, extension: str, line_count: int, symbols: list[CodeSymbol], imports: list[str], routes: list[str]) -> str:
    name = Path(path).name
    bits = [f"{name} is a {extension or 'text'} file with {line_count} lines."]
    if symbols:
        top = ", ".join(symbol.name for symbol in symbols[:8])
        bits.append(f"Symbols: {top}.")
    if imports:
        top_imports = ", ".join(imports[:5])
        bits.append(f"Import modules: {top_imports}.")
    if routes:
        bits.append(f"Routes: {', '.join(routes[:5])}.")
    return " ".join(bits)[:700]


def make_terms(path: str, summary: str, symbols: list[CodeSymbol], imports: list[str], routes: list[str], tool_names: list[str]) -> list[str]:
    source = " ".join(
        [
            path,
            summary,
            " ".join(symbol.name for symbol in symbols),
            " ".join(symbol.kind for symbol in symbols),
            " ".join(imports),
            " ".join(routes),
            " ".join(tool_names),
        ]
    )
    terms = {match.group(0).lower() for match in TOKEN_RE.finditer(source)}
    terms.update(part.lower() for part in Path(path).parts if len(part) > 1)
    return sorted(terms)[:700]


def query_terms(query: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(str(query or "")) if len(match.group(0)) > 1]
