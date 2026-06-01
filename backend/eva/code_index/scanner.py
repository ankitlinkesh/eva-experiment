from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

from .config import SAFE_EXTENSIONS, data_dir, is_skipped_path, project_root, relative_path
from .models import CodeFileRecord, CodeIndex
from .python_symbols import extract_text_symbols
from .text_index import looks_binary, make_summary, make_terms, redact_text, safe_decode


MAX_FILE_BYTES = 220_000
MAX_INDEX_FILES = 2500


def build_index(*, max_files: int = MAX_INDEX_FILES, max_file_bytes: int = MAX_FILE_BYTES) -> CodeIndex:
    root = project_root()
    files: list[CodeFileRecord] = []
    skipped = 0
    truncated = False

    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        safe_dirs: list[str] = []
        for dirname in dirs:
            candidate = current_path / dirname
            try:
                rel = relative_path(candidate, root)
            except ValueError:
                skipped += 1
                continue
            if is_skipped_path(rel, candidate):
                skipped += 1
                continue
            safe_dirs.append(dirname)
        dirs[:] = safe_dirs

        for name in sorted(names, key=str.lower):
            if len(files) >= max_files:
                truncated = True
                break
            path = current_path / name
            try:
                rel = relative_path(path, root)
            except ValueError:
                skipped += 1
                continue
            record = scan_file(path, rel, max_file_bytes=max_file_bytes)
            if record is None:
                skipped += 1
                continue
            files.append(record)
        if truncated:
            break

    return CodeIndex(
        version=2,
        root=str(root),
        created_at=datetime.now(timezone.utc).isoformat(),
        file_count=len(files),
        skipped=skipped,
        truncated=truncated,
        max_files=max_files,
        stores_full_file_contents=False,
        secrets_indexed=False,
        files=sorted(files, key=lambda item: item.path.lower()),
    )


def scan_file(path: Path, rel: str, *, max_file_bytes: int = MAX_FILE_BYTES) -> CodeFileRecord | None:
    suffix = path.suffix.lower()
    if suffix not in SAFE_EXTENSIONS:
        return None
    if is_skipped_path(rel, path):
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    if stat.st_size > max_file_bytes:
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    text = safe_decode(raw)
    if looks_binary(text):
        return None
    redacted, redaction_count = redact_text(text)
    symbols, imports, routes, tool_names = extract_text_symbols(redacted, suffix)
    line_count = redacted.count("\n") + 1 if redacted else 0
    summary = make_summary(rel, suffix, line_count, symbols, imports, routes)
    if redaction_count:
        summary = f"{summary} Sensitive-looking text was redacted before indexing."
    return CodeFileRecord(
        path=rel,
        extension=suffix,
        size=int(stat.st_size),
        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        line_count=line_count,
        summary=summary,
        symbols=symbols,
        imports=imports,
        routes=routes,
        tool_names=tool_names,
        terms=make_terms(rel, summary, symbols, imports, routes, tool_names),
    )


def ensure_data_dir() -> Path:
    target = data_dir()
    target.mkdir(parents=True, exist_ok=True)
    return target
