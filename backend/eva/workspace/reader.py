from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .config import WorkspaceSafetyError, assert_safe_file, relative_to_root, resolve_workspace_path


def _modified_at(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def safe_read_file(path: str, *, max_chars: int = 30_000) -> dict[str, object]:
    try:
        target = resolve_workspace_path(path)
        assert_safe_file(target)
        raw = target.read_bytes()
    except WorkspaceSafetyError as exc:
        return {"ok": False, "path": path, "error": str(exc), "refused": True}
    except OSError as exc:
        return {"ok": False, "path": path, "error": str(exc), "refused": False}

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")

    if "\x00" in text[:2048]:
        return {"ok": False, "path": path, "error": "Binary-looking file refused.", "refused": True}

    truncated = len(text) > max_chars
    content = text[:max_chars]
    return {
        "ok": True,
        "path": relative_to_root(target),
        "size": len(raw),
        "modified_at": _modified_at(target),
        "line_count": text.count("\n") + 1 if text else 0,
        "truncated": truncated,
        "content": content,
    }
