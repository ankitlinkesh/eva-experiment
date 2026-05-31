from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .indexer import safe_code_read, search_code


TRACE_FILE_RE = re.compile(r'File\s+"([^"]+)",\s+line\s+(\d+)(?:,\s+in\s+([^\n]+))?')
EXCEPTION_RE = re.compile(r"^([A-Za-z_][\w.]*Error|Exception|RuntimeError|ValueError|TypeError|KeyError|ImportError|ModuleNotFoundError):\s*(.+)$", re.MULTILINE)


def _workspace_rel(path: str) -> str:
    normalized = path.replace("\\", "/")
    marker = "/eva-agent/"
    if marker in normalized:
        return normalized.split(marker, 1)[1]
    return normalized


def debug_traceback(traceback: str) -> dict[str, Any]:
    text = (traceback or "").strip()
    if not text:
        return {"ok": False, "error": "Traceback/error text is empty."}
    frames: list[dict[str, Any]] = []
    for match in TRACE_FILE_RE.finditer(text):
        rel = _workspace_rel(match.group(1))
        frames.append({"path": rel, "line": int(match.group(2)), "function": (match.group(3) or "").strip()})
    exc = EXCEPTION_RE.search(text)
    exception_type = exc.group(1) if exc else ""
    exception_message = exc.group(2).strip() if exc else text.splitlines()[-1][:300]

    snippets: list[dict[str, Any]] = []
    for frame in frames[-3:]:
        rel = str(frame.get("path") or "")
        if Path(rel).suffix.lower() not in {".py", ".js"}:
            continue
        read = safe_code_read(rel)
        if not read.get("ok"):
            snippets.append({"path": rel, "line": frame.get("line"), "refused": True, "error": read.get("error")})
            continue
        lines = str(read.get("content") or "").splitlines()
        line_no = int(frame.get("line") or 1)
        start = max(1, line_no - 3)
        end = min(len(lines), line_no + 3)
        excerpt = "\n".join(f"{idx}: {lines[idx - 1]}" for idx in range(start, end + 1))
        snippets.append({"path": rel, "line": line_no, "function": frame.get("function"), "snippet": excerpt})

    related = search_code(exception_type or exception_message, limit=5).get("matches", [])
    likely_files = [str(item.get("path")) for item in related if isinstance(item, dict)]
    for frame in frames:
        path = str(frame.get("path") or "")
        if path and path not in likely_files:
            likely_files.insert(0, path)

    return {
        "ok": True,
        "exception_type": exception_type,
        "exception_message": exception_message,
        "frames": frames,
        "snippets": snippets,
        "likely_files": likely_files[:8],
        "likely_cause": "The failing frame and exception message point to the files above. Inspect the nearest changed code first; this is a best-effort static read, not certainty.",
        "suggested_tests": [
            ".\\.venv\\Scripts\\python.exe -m compileall backend",
            ".\\.venv\\Scripts\\python.exe scripts\\verify_agentic_v2.py",
        ],
    }
