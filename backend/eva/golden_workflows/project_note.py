from __future__ import annotations

import re
from pathlib import Path

from ..file_agent.real_apply_policy import is_safe_real_create_target


def infer_project_note_topic(request_text: str) -> tuple[str, str]:
    text = " ".join(str(request_text or "").strip().split())
    lowered = text.lower()
    if "fileagent" in lowered or "file agent" in lowered:
        return "Eva FileAgent Note", "docs/eva_file_agent_note.md"
    if "control center" in lowered or "dashboard" in lowered:
        return "Eva Control Center Note", "docs/eva_control_center_note.md"
    if "current status" in lowered or "current state" in lowered or "status" in lowered:
        return "Eva Current Status Note", "docs/eva_current_status_note.md"
    if "safety" in lowered:
        return "Eva Safety Note", "docs/eva_safety_note.md"
    if "demo" in lowered:
        return "Eva Demo Note", "samples/eva_demo_note.md"
    return "Eva Project Note", "docs/eva_project_note.md"


def suggest_safe_target_path(request_text: str, repo_root: str | Path | None = None) -> str:
    _, base = infer_project_note_topic(request_text)
    root = Path(repo_root or Path.cwd()).resolve()
    candidate = _safe_relative_path(base)
    if not is_safe_real_create_target(candidate, repo_root=root).allowed:
        candidate = "docs/eva_project_note.md"
    path = root / candidate
    if not path.exists():
        return candidate
    stem = Path(candidate).stem
    suffix = Path(candidate).suffix
    parent = Path(candidate).parent.as_posix()
    for index in range(2, 100):
        alternate = f"{parent}/{stem}_{index}{suffix}"
        if not (root / alternate).exists() and is_safe_real_create_target(alternate, repo_root=root).allowed:
            return alternate
    return f"{parent}/{stem}_100{suffix}"


def build_project_note_draft(request_text: str) -> str:
    title, _ = infer_project_note_topic(request_text)
    focus = _focus_line(title)
    return "\n".join(
        [
            f"# {title}",
            "",
            "## Summary",
            "",
            "This note was drafted by Eva as part of a safe FileAgent workflow.",
            focus,
            "",
            "## Current System State",
            "",
            "- FileAgent supports read-only inspection, draft previews, approvals, sandbox apply, and narrow real create.",
            "- Real create is limited to new Markdown/text files in approved folders.",
            "- Existing files cannot be edited or overwritten.",
            "- The Control Center shows workflow status and safety boundaries without executing actions.",
            "",
            "## Safety Boundaries",
            "",
            "- No source/config/runtime writes.",
            "- No broad file edits.",
            "- Exact confirmation is required for real create.",
            "- Rollback is available only for unchanged Eva-created files.",
            "",
            "## Next Step",
            "",
            "Review this note, approve it, test it in sandbox, then use exact confirmation if real creation is desired.",
            "",
        ]
    )


def _safe_relative_path(path_text: str) -> str:
    text = str(path_text or "").strip().replace("\\", "/").strip("/")
    text = re.sub(r"/+", "/", text)
    if Path(text).is_absolute() or ".." in Path(text).parts:
        return "docs/eva_project_note.md"
    return text


def _focus_line(title: str) -> str:
    if "FileAgent" in title:
        return "Focus: FileAgent approvals, sandbox verification, narrow real create, and rollback."
    if "Control Center" in title:
        return "Focus: Control Center visibility for safety, approvals, and workflow readiness."
    if "Status" in title:
        return "Focus: Eva's current safe runtime state and execution boundaries."
    if "Safety" in title:
        return "Focus: safe routing, exact confirmation, and blocked broad execution."
    return "Focus: the current Eva project safety workflow."
