from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .config import data_dir, index_path
from .store import load_index, refresh_index


MAJOR_AREAS = (
    "backend/eva/runtime",
    "backend/eva/agents",
    "backend/eva/guardrails",
    "backend/eva/observability",
    "backend/eva/resources",
    "backend/eva/code_index",
    "backend/eva/browser_automation",
    "backend/eva/desktop_automation",
    "scripts",
    "docs",
)


def refresh_code_index() -> dict[str, Any]:
    index = refresh_index()
    return {
        "ok": True,
        "message": f"Code index v2 refreshed. Indexed {index.file_count} safe source/docs files.",
        "indexed": True,
        "indexed_files": index.file_count,
        "skipped": index.skipped,
        "truncated": index.truncated,
        "created_at": index.created_at,
        "data_dir": str(data_dir()),
        "index_path": str(index_path()),
        "cache_scope": "local_metadata_only",
        "stores_full_file_contents": False,
        "secrets_indexed": False,
    }


def code_index_status() -> dict[str, Any]:
    index = load_index(auto_refresh=False)
    if index is None:
        return {
            "ok": True,
            "indexed": False,
            "indexed_files": 0,
            "message": "Code index v2 status: no local metadata cache has been built yet.",
            "data_dir": str(data_dir()),
            "cache_scope": "local_metadata_only",
            "stores_full_file_contents": False,
            "secrets_indexed": False,
        }
    return {
        "ok": True,
        "indexed": True,
        "indexed_files": index.file_count,
        "skipped": index.skipped,
        "truncated": index.truncated,
        "created_at": index.created_at,
        "data_dir": str(data_dir()),
        "index_path": str(index_path()),
        "cache_scope": "local_metadata_only",
        "stores_full_file_contents": False,
        "secrets_indexed": False,
        "message": f"Code index v2 status: ready with {index.file_count} safe files.",
    }


def workspace_summary() -> dict[str, Any]:
    index = load_index()
    if index is None:
        return {"ok": False, "error": "Code index v2 is unavailable.", "major_areas": []}
    counts = Counter(record.extension or "[none]" for record in index.files)
    indexed_paths = {record.path for record in index.files}
    major_areas = [f"{area}: {'present' if any(path == area or path.startswith(area + '/') for path in indexed_paths) or Path(index.root, area).exists() else 'missing'}" for area in MAJOR_AREAS]
    return {
        "ok": True,
        "root": index.root,
        "indexed_files": index.file_count,
        "major_areas": major_areas,
        "extension_counts": dict(sorted(counts.items())),
        "safety": "No secrets, runtime databases, screenshots, checkpoints, virtualenvs, node_modules, or full file contents are stored in the code index.",
        "cache_scope": "local_metadata_only",
        "stores_full_file_contents": False,
    }
