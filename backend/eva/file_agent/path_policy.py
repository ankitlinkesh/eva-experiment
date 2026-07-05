from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


SENSITIVE_NAME_MARKERS = (
    "password",
    "token",
    "secret",
    "credential",
    "cookie",
    "session",
    "localstorage",
    "keychain",
    "private key",
    "id_rsa",
    "id_ed25519",
)

SENSITIVE_PARTS = {
    ".ssh",
    ".gnupg",
    "cookies",
    "sessions",
    "session storage",
    "local storage",
    "user data",
    "default",
    "login data",
    "browser profile",
}

RUNTIME_PARTS = (
    ("backend", "eva", "data"),
    ("backend", "data", "checkpoints"),
    ("data",),
    ("models",),
    ("bin",),
    ("traces",),
    ("exports",),
    ("screenshots",),
)


@dataclass(frozen=True)
class FilePathDecision:
    original_input: str
    normalized_path: str
    display_path: str
    exists: bool
    is_file: bool
    is_dir: bool
    allowed: bool
    reason: str
    risk_level: str
    requires_confirmation: bool
    blocked_patterns: list[str] = field(default_factory=list)


def normalize_user_path(path_text: str) -> str:
    text = str(path_text or "").strip().strip('"').strip("'")
    text = text.replace("\\", os.sep).replace("/", os.sep)
    return text or "."


def evaluate_file_path(path_text: str, repo_root: str | Path | None = None) -> FilePathDecision:
    root = Path(repo_root or Path.cwd()).resolve()
    original = str(path_text or "").strip()
    normalized = normalize_user_path(original)
    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        resolved = candidate.absolute()

    exists = resolved.exists()
    is_file = resolved.is_file()
    is_dir = resolved.is_dir()
    display = _display_path(resolved, root)
    blocked = _blocked_patterns(resolved, root)
    outside = not _is_relative_to(resolved, root)
    whole_drive = _looks_like_drive_root(resolved)

    if whole_drive:
        return _decision(original, resolved, display, exists, is_file, is_dir, False, "Whole-drive scans are refused by FileAgent v1.", "high", False, ["whole_drive"])
    if outside:
        return _decision(original, resolved, "outside repo path", exists, is_file, is_dir, False, "FileAgent v1 is repo/project-scoped by default.", "medium", True, ["outside_repo"])
    if blocked:
        return _decision(original, resolved, display, exists, is_file, is_dir, False, "Sensitive or runtime paths are refused by FileAgent v1.", "high", False, blocked)
    return _decision(original, resolved, display, exists, is_file, is_dir, True, "Allowed repo-scoped read-only path.", "medium", False, [])


def is_sensitive_path(path: str) -> bool:
    root = Path.cwd().resolve()
    decision = evaluate_file_path(path, repo_root=root)
    return bool(decision.blocked_patterns)


def is_allowed_read_path(path: str, repo_root: str | Path | None = None) -> bool:
    return evaluate_file_path(path, repo_root=repo_root).allowed


def format_path_decision(decision: FilePathDecision) -> str:
    status = "allowed" if decision.allowed else "refused"
    lines = [
        "File path policy",
        "",
        f"Path: {decision.display_path}",
        f"Status: {status}.",
        f"Risk: {decision.risk_level}.",
        f"Exists: {'yes' if decision.exists else 'no'}.",
        f"Type: {'folder' if decision.is_dir else 'file' if decision.is_file else 'unknown'}.",
        f"Confirmation needed: {'yes' if decision.requires_confirmation else 'no'}.",
        "",
        f"Reason: {decision.reason}",
    ]
    if decision.blocked_patterns:
        lines.append(f"Blocked by: {', '.join(decision.blocked_patterns[:4])}.")
    return "\n".join(lines)


def _decision(
    original: str,
    resolved: Path,
    display: str,
    exists: bool,
    is_file: bool,
    is_dir: bool,
    allowed: bool,
    reason: str,
    risk_level: str,
    requires_confirmation: bool,
    blocked: list[str],
) -> FilePathDecision:
    return FilePathDecision(
        original_input=original,
        normalized_path=str(resolved),
        display_path=display,
        exists=exists,
        is_file=is_file,
        is_dir=is_dir,
        allowed=allowed,
        reason=reason,
        risk_level=risk_level,
        requires_confirmation=requires_confirmation,
        blocked_patterns=blocked,
    )


def _blocked_patterns(path: Path, root: Path) -> list[str]:
    display = _display_path(path, root)
    lowered_display = display.lower().replace("\\", "/")
    name = path.name.lower()
    parts = [part.lower() for part in path.parts]
    joined = " ".join(parts)
    blocked: list[str] = []

    if name.startswith(".env") and name != ".env.example":
        blocked.append(".env")
    if name == ".env.example":
        return blocked
    for marker in SENSITIVE_NAME_MARKERS:
        if marker in joined or marker in lowered_display:
            blocked.append(marker)
    for marker in SENSITIVE_PARTS:
        if marker in parts or marker in joined:
            blocked.append(marker)
    rel_parts = tuple(Path(display).parts)
    normalized_rel = tuple(part.lower() for part in rel_parts)
    for pattern in RUNTIME_PARTS:
        if _starts_with_parts(normalized_rel, pattern):
            blocked.append("/".join(pattern))
    if ".git" in parts:
        blocked.append(".git")
    return _dedupe(blocked)


def _display_path(path: Path, root: Path) -> str:
    if _is_relative_to(path, root):
        rel = path.relative_to(root)
        return "." if str(rel) == "." else rel.as_posix()
    return path.name or "outside repo path"


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _looks_like_drive_root(path: Path) -> bool:
    anchor = path.anchor
    return bool(anchor and str(path).rstrip("\\/") == anchor.rstrip("\\/"))


def _starts_with_parts(parts: tuple[str, ...], pattern: tuple[str, ...]) -> bool:
    if len(parts) < len(pattern):
        return False
    return any(parts[index : index + len(pattern)] == pattern for index in range(0, len(parts) - len(pattern) + 1))


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item not in output:
            output.append(item)
    return output
