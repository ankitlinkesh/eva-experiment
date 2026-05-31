from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..privacy.redaction import redact_secrets


DEFAULT_TRACE_ROOT = Path(__file__).resolve().parents[1] / "data" / "traces"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize(value: Any) -> Any:
    text = json.dumps(value, ensure_ascii=False, default=str)
    redacted, _events = redact_secrets(text)
    try:
        return json.loads(redacted)
    except Exception:
        return redacted


class LocalTraceStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or DEFAULT_TRACE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, trace_id: str) -> Path:
        safe = "".join(ch for ch in trace_id if ch.isalnum() or ch in {"-", "_"})[:80] or "trace"
        return self.root / f"{safe}.jsonl"

    def append(self, trace_id: str, event_type: str, payload: dict[str, Any]) -> None:
        event = {"created_at": _now(), "type": event_type, "payload": _sanitize(payload)}
        with self.path_for(trace_id).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def status(self) -> dict[str, Any]:
        count = len(list(self.root.glob("*.jsonl"))) if self.root.exists() else 0
        return {"ok": True, "backend": "local", "path": str(self.root), "trace_files": count}
