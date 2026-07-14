"""Post-condition verification — the heart of verification-first execution (Phase 38).

Until now a tool call was reported "done" the moment its handler returned
without raising. That conflates *ran* with *worked*: a write handler can return
a tidy ``{"ok": true}`` while the file on disk is unchanged. Phase 38 closes that
gap by giving every action a **declared post-condition** and checking it against
real state *after* the handler runs, so Eva never claims an unproven effect.

The load-bearing idea here is **provenance** — how much we actually know:

  * ``independent`` — verified against real OS/file state we read ourselves
    (the file exists / is gone / contains the expected text). This is proof.
  * ``self_reported`` — we only trust the tool's own success flag (e.g. a local
    read returning a dict). Fine for reads, but not proof of a world change.
  * ``observed`` — a local UI/network effect (a click, a keystroke, a launch)
    we cannot confirm without perception; the operator should eyeball it.
  * ``unverified`` — no verification method applies; we say so plainly.

Only ``independent`` failure is treated as a hard "the action did not happen";
the weaker classes never *upgrade* confidence into a false claim of success.
Everything here is pure (no registry import → no import cycle) and fail-safe.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROVENANCE_INDEPENDENT = "independent"
PROVENANCE_SELF_REPORTED = "self_reported"
PROVENANCE_OBSERVED = "observed"
PROVENANCE_UNVERIFIED = "unverified"

# Verification methods (from ToolSpec.verification_method) we can check against
# real file state ourselves. Everything else is self-reported or observed.
_OBSERVED_METHODS = {
    "screen_state_changed",
    "text_field_contains",
    "app_window_active",
    "url_opened",
    "message_draft_prepared",
    "message_sent_likely",
}


@dataclass(frozen=True)
class PostCondition:
    """What must be true after an action for it to count as done."""

    method: str
    params: dict[str, Any]
    description: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PostConditionResult:
    """The outcome of independently checking a post-condition."""

    method: str
    verified: bool
    independent: bool
    provenance: str
    confidence: float
    detail: str
    remediation: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _first(args: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = args.get(key)
        if value:
            return str(value)
    return ""


def derive_postcondition(tool_name: str, verification_method: str, args: dict[str, Any]) -> PostCondition:
    """Turn a tool's declared verification_method + call args into a concrete
    post-condition. File semantics are derived from the *tool*, not blindly from
    the metadata: a delete's real post-condition is that the file is now gone,
    even though its declared method is ``file_exists``.
    """
    name = (tool_name or "").lower()
    method = (verification_method or "command_result_success").strip()

    if "delete" in name:
        path = _first(args, "path", "target")
        return PostCondition("file_absent", {"path": path}, f"{path or 'target'} no longer exists")

    if method == "file_contains":
        path = _first(args, "path", "target")
        text = _first(args, "content", "replace", "new_text", "new", "text")
        if text:
            return PostCondition("file_contains", {"path": path, "text": text}, f"{path or 'file'} contains the written text")
        # A patch/write with no recoverable expected text degrades to existence.
        return PostCondition("file_exists", {"path": path}, f"{path or 'file'} exists after write")

    if method == "file_exists":
        # copy/move target is the destination; a bare write target is the path.
        path = _first(args, "dst", "dest", "destination", "target", "path")
        return PostCondition("file_exists", {"path": path}, f"{path or 'file'} exists")

    if method in _OBSERVED_METHODS:
        return PostCondition(method, {}, "local UI/network effect (not independently verifiable)")

    if method in {"no_verification_available", "none", ""}:
        return PostCondition("no_verification_available", {}, "no verification method available")

    return PostCondition("command_result_success", {}, "tool reported success")


def _result_reports_success(result: Any) -> bool:
    """Whether a tool's own return value indicates success (self-report)."""
    if isinstance(result, dict):
        if result.get("ok") is False:
            return False
        if result.get("hard_blocked") or result.get("requires_confirmation"):
            return False
        if result.get("error"):
            return False
    return True


def verify_postcondition(post: PostCondition, result: Any) -> PostConditionResult:
    """Independently check a post-condition against real state where we can.

    Fail-safe: any error reading the filesystem yields an ``unverified`` result
    rather than raising into the caller.
    """
    method = post.method
    try:
        if method == "file_exists":
            path = str(post.params.get("path") or "")
            ok = bool(path) and Path(path).exists()
            return PostConditionResult(
                method, ok, True, PROVENANCE_INDEPENDENT,
                0.97 if ok else 0.05, f"file_exists({path})={ok}",
                None if ok else "the file was not created; restore checkpoint or retry",
            )
        if method == "file_absent":
            path = str(post.params.get("path") or "")
            ok = bool(path) and not Path(path).exists()
            return PostConditionResult(
                method, ok, True, PROVENANCE_INDEPENDENT,
                0.97 if ok else 0.05, f"file_absent({path})={ok}",
                None if ok else "the file still exists; the delete did not take effect",
            )
        if method == "file_contains":
            path = str(post.params.get("path") or "")
            text = str(post.params.get("text") or "")
            exists = bool(path) and Path(path).exists()
            ok = exists and text in Path(path).read_text(encoding="utf-8", errors="replace")
            return PostConditionResult(
                method, ok, True, PROVENANCE_INDEPENDENT,
                0.95 if ok else 0.1, f"file_contains({path})={ok}",
                None if ok else "expected content not found; restore checkpoint or rewrite",
            )
    except Exception as exc:  # filesystem hiccup — be honest, don't crash
        return PostConditionResult(
            method, False, False, PROVENANCE_UNVERIFIED, 0.2,
            f"verification error: {type(exc).__name__}: {exc}", "verify manually",
        )

    if method in _OBSERVED_METHODS:
        ok = _result_reports_success(result)
        return PostConditionResult(
            method, ok, False, PROVENANCE_OBSERVED,
            0.5 if ok else 0.3, f"{method}: local effect not independently verifiable",
            "confirm the visible state (Eva cannot prove this without perception)",
        )

    if method == "no_verification_available":
        return PostConditionResult(
            method, False, False, PROVENANCE_UNVERIFIED, 0.2,
            "no verification method available for this action", "verify manually",
        )

    # command_result_success — trust the tool's own success flag only.
    ok = _result_reports_success(result)
    return PostConditionResult(
        method, ok, False, PROVENANCE_SELF_REPORTED,
        0.6 if ok else 0.3, "tool self-reported success" if ok else "tool self-reported failure",
        None if ok else "the tool reported an error",
    )


def verify_tool_effect(tool_name: str, verification_method: str, args: dict[str, Any], result: Any) -> PostConditionResult:
    """Derive a post-condition for a tool call and verify it. Fail-safe."""
    try:
        post = derive_postcondition(tool_name, verification_method, args)
        return verify_postcondition(post, result)
    except Exception as exc:
        return PostConditionResult(
            "error", False, False, PROVENANCE_UNVERIFIED, 0.2,
            f"could not derive/verify post-condition: {type(exc).__name__}: {exc}", "verify manually",
        )
