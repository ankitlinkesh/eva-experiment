from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .inspector import IGNORED_DIRS
from .path_policy import evaluate_file_path


@dataclass(frozen=True)
class FileSearchResult:
    display_path: str
    kind: str
    size_bytes: int | None = None
    modified_at: str | None = None


@dataclass(frozen=True)
class FileSearchResults:
    query: str
    root_display: str
    results: list[FileSearchResult]
    truncated: bool = False
    refused_reason: str | None = None


def search_files_by_name(query: str, root: str = ".", repo_root: str | Path | None = None, max_results: int = 50) -> FileSearchResults:
    clean_query = str(query or "").strip().lower()
    decision = evaluate_file_path(root, repo_root=repo_root)
    if not decision.allowed:
        return FileSearchResults(query=clean_query, root_display=decision.display_path, results=[], refused_reason=decision.reason)
    if not clean_query or len(clean_query) < 2:
        return FileSearchResults(query=clean_query, root_display=decision.display_path, results=[], refused_reason="Please provide a narrower filename query.")
    return _walk_name_search(clean_query, Path(decision.normalized_path), Path(repo_root or Path.cwd()).resolve(), max_results)


def find_recent_project_files(root: str = ".", repo_root: str | Path | None = None, max_results: int = 20) -> FileSearchResults:
    decision = evaluate_file_path(root, repo_root=repo_root)
    if not decision.allowed:
        return FileSearchResults(query="recent", root_display=decision.display_path, results=[], refused_reason=decision.reason)
    results = _safe_files(Path(decision.normalized_path), Path(repo_root or Path.cwd()).resolve(), max_results=300)
    results.sort(key=lambda item: item.modified_at or "", reverse=True)
    return FileSearchResults(query="recent", root_display=decision.display_path, results=results[: max(1, min(100, max_results))], truncated=len(results) > max_results)


def find_files_by_extension(extension: str, root: str = ".", repo_root: str | Path | None = None, max_results: int = 50) -> FileSearchResults:
    ext = str(extension or "").strip().lower()
    if ext and not ext.startswith("."):
        ext = "." + ext
    decision = evaluate_file_path(root, repo_root=repo_root)
    if not decision.allowed:
        return FileSearchResults(query=ext, root_display=decision.display_path, results=[], refused_reason=decision.reason)
    results = [item for item in _safe_files(Path(decision.normalized_path), Path(repo_root or Path.cwd()).resolve(), max_results=max_results) if item.display_path.lower().endswith(ext)]
    return FileSearchResults(query=ext, root_display=decision.display_path, results=results[:max_results], truncated=len(results) >= max_results)


def _walk_name_search(query: str, root: Path, repo_root: Path, max_results: int) -> FileSearchResults:
    results: list[FileSearchResult] = []
    limit = max(1, min(100, int(max_results or 50)))
    for item in _iter_safe_paths(root, repo_root):
        if query in item.name.lower():
            decision = evaluate_file_path(str(item), repo_root=repo_root)
            kind = "folder" if item.is_dir() else "file"
            size = item.stat().st_size if item.is_file() else None
            results.append(FileSearchResult(decision.display_path, kind, size, _mtime_iso(item.stat().st_mtime)))
            if len(results) >= limit:
                return FileSearchResults(query=query, root_display=evaluate_file_path(str(root), repo_root=repo_root).display_path, results=results, truncated=True)
    return FileSearchResults(query=query, root_display=evaluate_file_path(str(root), repo_root=repo_root).display_path, results=results)


def _safe_files(root: Path, repo_root: Path, max_results: int) -> list[FileSearchResult]:
    results: list[FileSearchResult] = []
    for item in _iter_safe_paths(root, repo_root):
        if item.is_file():
            decision = evaluate_file_path(str(item), repo_root=repo_root)
            results.append(FileSearchResult(decision.display_path, "file", item.stat().st_size, _mtime_iso(item.stat().st_mtime)))
            if len(results) >= max_results:
                break
    return results


def _iter_safe_paths(root: Path, repo_root: Path):
    stack = [root]
    visited = 0
    while stack and visited < 5000:
        current = stack.pop()
        visited += 1
        if _skip(current, repo_root):
            continue
        decision = evaluate_file_path(str(current), repo_root=repo_root)
        if not decision.allowed:
            continue
        yield current
        if current.is_dir():
            try:
                children = sorted(current.iterdir(), key=lambda item: item.name.lower(), reverse=True)
            except OSError:
                continue
            stack.extend(children)


def _skip(path: Path, repo_root: Path) -> bool:
    name = path.name.lower()
    if name in IGNORED_DIRS:
        return True
    try:
        rel = path.relative_to(repo_root).as_posix().lower()
    except ValueError:
        return True
    return rel.startswith("backend/eva/data")


def _mtime_iso(value: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
