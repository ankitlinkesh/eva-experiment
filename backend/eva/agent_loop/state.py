from __future__ import annotations

import hashlib


def make_loop_id(request: str) -> str:
    digest = hashlib.sha256(("phase18|" + str(request or "")).encode("utf-8")).hexdigest()[:12]
    return "loop_" + digest


def summarize_request(request: str) -> str:
    clean = " ".join(str(request or "").split())
    if not clean:
        return "No request supplied."
    if len(clean) <= 240:
        return clean
    return clean[:220].rstrip() + " ... [trimmed]"
