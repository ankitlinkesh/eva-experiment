from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .path_policy import FilePathDecision, evaluate_file_path


IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
    "data",
    "models",
    "bin",
    "traces",
    "exports",
    "screenshots",
}

SAFE_TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".csv",
    ".example",
}


@dataclass(frozen=True)
class FileInspection:
    decision: FilePathDecision
    size_bytes: int | None = None
    modified_at: str | None = None
    suffix: str = ""


@dataclass(frozen=True)
class FolderEntry:
    display_path: str
    kind: str
    size_bytes: int | None = None


@dataclass(frozen=True)
class FolderInspection:
    decision: FilePathDecision
    entries: list[FolderEntry] = field(default_factory=list)
    truncated: bool = False
    skipped_count: int = 0


@dataclass(frozen=True)
class TextPreview:
    decision: FilePathDecision
    ok: bool
    text: str = ""
    truncated: bool = False
    reason: str = ""
    size_bytes: int | None = None


@dataclass(frozen=True)
class ProjectStructure:
    decision: FilePathDecision
    lines: list[str] = field(default_factory=list)
    truncated: bool = False
    skipped_count: int = 0
    summary: str = ""


def inspect_path(path_text: str, repo_root: str | Path | None = None) -> FileInspection | FolderInspection:
    decision = evaluate_file_path(path_text, repo_root=repo_root)
    if not decision.allowed:
        return FileInspection(decision=decision)
    if decision.is_dir:
        return inspect_folder(path_text, repo_root=repo_root)
    return inspect_file_metadata(path_text, repo_root=repo_root)


def inspect_file_metadata(path_text: str, repo_root: str | Path | None = None) -> FileInspection:
    decision = evaluate_file_path(path_text, repo_root=repo_root)
    size = None
    modified = None
    suffix = ""
    if decision.allowed and decision.exists and decision.is_file:
        path = Path(decision.normalized_path)
        stat = path.stat()
        size = stat.st_size
        modified = _mtime_iso(stat.st_mtime)
        suffix = _safe_suffix(path)
    return FileInspection(decision=decision, size_bytes=size, modified_at=modified, suffix=suffix)


def inspect_folder(path_text: str, repo_root: str | Path | None = None, max_entries: int = 100) -> FolderInspection:
    decision = evaluate_file_path(path_text, repo_root=repo_root)
    if not decision.allowed or not decision.exists or not decision.is_dir:
        return FolderInspection(decision=decision)
    root = Path(repo_root or Path.cwd()).resolve()
    path = Path(decision.normalized_path)
    entries: list[FolderEntry] = []
    skipped = 0
    limit = max(1, min(200, int(max_entries or 100)))
    for child in sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        if _skip_path(child, root):
            skipped += 1
            continue
        child_decision = evaluate_file_path(str(child), repo_root=root)
        if not child_decision.allowed:
            skipped += 1
            continue
        kind = "folder" if child.is_dir() else "file"
        size = child.stat().st_size if child.is_file() else None
        entries.append(FolderEntry(child_decision.display_path, kind, size))
        if len(entries) >= limit:
            return FolderInspection(decision=decision, entries=entries, truncated=True, skipped_count=skipped)
    return FolderInspection(decision=decision, entries=entries, truncated=False, skipped_count=skipped)


def preview_text_file(path_text: str, repo_root: str | Path | None = None, max_chars: int = 6000) -> TextPreview:
    decision = evaluate_file_path(path_text, repo_root=repo_root)
    if not decision.allowed:
        return TextPreview(decision=decision, ok=False, reason=decision.reason)
    if not decision.exists or not decision.is_file:
        return TextPreview(decision=decision, ok=False, reason="Path is not an existing file.")
    path = Path(decision.normalized_path)
    if not _is_safe_text_file(path):
        return TextPreview(decision=decision, ok=False, reason="File preview supports safe text/code/docs extensions only in FileAgent v1.", size_bytes=path.stat().st_size)
    size = path.stat().st_size
    if size > 512_000:
        return TextPreview(decision=decision, ok=False, reason="File is too large for FileAgent v1 preview.", size_bytes=size)
    limit = max(200, min(20_000, int(max_chars or 6000)))
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return TextPreview(decision=decision, ok=False, reason=f"Could not read file safely: {type(exc).__name__}.", size_bytes=size)
    return TextPreview(decision=decision, ok=True, text=raw[:limit], truncated=len(raw) > limit, size_bytes=size)


def understand_file(path_text: str, repo_root: str | Path | None = None, max_chars: int = 12000):
    from .understanding import FileUnderstanding, understand_text_file

    preview = preview_text_file(path_text, repo_root=repo_root, max_chars=max_chars)
    if not preview.ok:
        return FileUnderstanding(
            path=preview.decision.display_path,
            ok=False,
            purpose="Refused or unsupported path.",
            summary=preview.reason or preview.decision.reason,
            warnings=["FileAgent did not read this file."],
        )
    return understand_text_file(preview.decision.display_path, preview.text)


def explain_project(path_text: str = ".", repo_root: str | Path | None = None):
    from .project_inventory import build_project_inventory

    return build_project_inventory(path_text, repo_root=repo_root)


def explain_project_structure(path_text: str = ".", repo_root: str | Path | None = None, max_depth: int = 3) -> ProjectStructure:
    decision = evaluate_file_path(path_text, repo_root=repo_root)
    if not decision.allowed:
        return ProjectStructure(decision=decision, summary=decision.reason)
    if not decision.exists or not decision.is_dir:
        return ProjectStructure(decision=decision, summary="Project structure needs an existing folder.")
    root = Path(repo_root or Path.cwd()).resolve()
    start = Path(decision.normalized_path)
    lines: list[str] = []
    skipped = 0
    max_lines = 120
    depth_limit = max(1, min(5, int(max_depth or 3)))

    def walk(folder: Path, depth: int) -> bool:
        nonlocal skipped
        if len(lines) >= max_lines:
            return True
        children = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        for child in children:
            if _skip_path(child, root):
                skipped += 1
                continue
            child_decision = evaluate_file_path(str(child), repo_root=root)
            if not child_decision.allowed:
                skipped += 1
                continue
            prefix = "  " * depth + ("- " if depth else "")
            marker = "/" if child.is_dir() else ""
            lines.append(f"{prefix}{child.name}{marker}")
            if len(lines) >= max_lines:
                return True
            if child.is_dir() and depth + 1 < depth_limit:
                if walk(child, depth + 1):
                    return True
        return False

    truncated = walk(start, 0)
    summary = _project_summary(lines)
    return ProjectStructure(decision=decision, lines=lines, truncated=truncated, skipped_count=skipped, summary=summary)


def _skip_path(path: Path, repo_root: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    if path.name.lower() in IGNORED_DIRS:
        return True
    if {"backend", "eva", "data"}.issubset(parts):
        try:
            rel = path.relative_to(repo_root).as_posix().lower()
        except ValueError:
            rel = path.as_posix().lower()
        if rel.startswith("backend/eva/data"):
            return True
    return False


def _is_safe_text_file(path: Path) -> bool:
    if path.name in {".gitignore"}:
        return True
    if path.name == ".env.example":
        return True
    return path.suffix.lower() in SAFE_TEXT_EXTENSIONS


def _safe_suffix(path: Path) -> str:
    if path.name == ".gitignore":
        return ".gitignore"
    if path.name == ".env.example":
        return ".env.example"
    return path.suffix.lower()


def _mtime_iso(value: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _project_summary(lines: list[str]) -> str:
    lowered = "\n".join(lines).lower()
    hints = []
    if "backend" in lowered:
        hints.append("backend")
    if "frontend" in lowered:
        hints.append("frontend")
    if "docs" in lowered:
        hints.append("docs")
    if "scripts" in lowered:
        hints.append("verification scripts")
    if not hints:
        return "Basic project structure preview."
    return "Detected: " + ", ".join(hints) + "."
