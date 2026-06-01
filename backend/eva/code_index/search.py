from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import resolve_safe_path, relative_path
from .scanner import scan_file
from .store import load_index
from .text_index import query_terms


def search_code(query: str, *, limit: int = 10) -> dict[str, Any]:
    clean_query = " ".join(str(query or "").split())[:200]
    terms = query_terms(clean_query)
    if not terms:
        return {"ok": False, "query": clean_query, "error": "Search query is empty.", "matches": []}
    index = load_index()
    if index is None:
        return {"ok": False, "query": clean_query, "error": "Code index v2 is unavailable.", "matches": []}
    matches = []
    for record in index.files:
        haystack = set(record.terms)
        path_lower = record.path.lower()
        summary_lower = record.summary.lower()
        compact_path = _compact(path_lower)
        compact_summary = _compact(summary_lower)
        compact_symbols = [_compact(symbol.name.lower()) for symbol in record.symbols]
        score = 0
        for term in terms:
            compact_term = _compact(term)
            if term in haystack:
                score += 5
            if term in path_lower:
                score += 4
            if term in summary_lower:
                score += 2
            if any(term in symbol.name.lower() for symbol in record.symbols):
                score += 5
            if compact_term and (compact_term in compact_path or compact_term in compact_summary or any(compact_term in symbol for symbol in compact_symbols)):
                score += 4
        if score:
            matches.append(
                {
                    "path": record.path,
                    "score": score,
                    "summary": record.summary,
                    "symbols": [symbol.name for symbol in record.symbols[:8]],
                    "routes": record.routes[:5],
                }
            )
    matches.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
    return {
        "ok": True,
        "query": clean_query,
        "matches": matches[: max(1, min(int(limit), 50))],
        "searched_files": len(index.files),
        "cache_scope": "local_metadata_only",
    }


def _compact(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def search_symbols(query: str, *, limit: int = 10) -> dict[str, Any]:
    clean_query = " ".join(str(query or "").split())[:120]
    if not clean_query:
        return {"ok": False, "query": clean_query, "error": "Symbol query is empty.", "matches": []}
    needle = clean_query.lower()
    index = load_index()
    if index is None:
        return {"ok": False, "query": clean_query, "error": "Code index v2 is unavailable.", "matches": []}
    matches = []
    for record in index.files:
        for symbol in record.symbols:
            lower = symbol.name.lower()
            if needle == lower:
                score = 10
            elif needle in lower:
                score = 6
            else:
                continue
            matches.append(
                {
                    "name": symbol.name,
                    "kind": symbol.kind,
                    "path": record.path,
                    "line": symbol.line,
                    "parent": symbol.parent,
                    "score": score,
                    "summary": record.summary,
                }
            )
    matches.sort(key=lambda item: (-int(item["score"]), str(item["path"]), int(item["line"])))
    return {"ok": True, "query": clean_query, "matches": matches[: max(1, min(int(limit), 50))], "cache_scope": "local_metadata_only"}


def summarize_file(path: str) -> dict[str, Any]:
    safe, target, error = resolve_safe_path(path)
    if not safe or target is None:
        return {"ok": False, "path": path, "error": error, "refused": True}
    if not target.exists():
        return {"ok": False, "path": path, "error": "File does not exist.", "refused": False}
    if not target.is_file():
        return {"ok": False, "path": path, "error": "Path is not a file.", "refused": True}
    rel = relative_path(target)
    record = scan_file(target, rel)
    if record is None:
        return {"ok": False, "path": rel, "error": "File is unsupported, too large, binary-looking, or blocked by safety rules.", "refused": True}
    return {
        "ok": True,
        "path": record.path,
        "summary": record.summary,
        "line_count": record.line_count,
        "size": record.size,
        "symbols": [symbol.name for symbol in record.symbols[:30]],
        "imports": record.imports[:20],
        "routes": record.routes[:15],
        "cache_scope": "summary-only local read",
        "stores_full_file_contents": False,
    }
