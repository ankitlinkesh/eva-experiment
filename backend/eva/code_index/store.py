from __future__ import annotations

import json
from typing import Any

from .config import index_path
from .models import CodeFileRecord, CodeIndex, CodeSymbol
from .scanner import build_index, ensure_data_dir


def save_index(index: CodeIndex) -> None:
    ensure_data_dir()
    index_path().write_text(json.dumps(index.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def refresh_index() -> CodeIndex:
    index = build_index()
    save_index(index)
    return index


def load_index(*, auto_refresh: bool = True) -> CodeIndex | None:
    path = index_path()
    if not path.exists():
        return refresh_index() if auto_refresh else None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return refresh_index() if auto_refresh else None
    return _from_payload(payload)


def _from_payload(payload: dict[str, Any]) -> CodeIndex:
    files: list[CodeFileRecord] = []
    for item in payload.get("files") or []:
        if not isinstance(item, dict):
            continue
        symbols = [
            CodeSymbol(
                name=str(symbol.get("name") or ""),
                kind=str(symbol.get("kind") or ""),
                line=int(symbol.get("line") or 0),
                parent=str(symbol.get("parent")) if symbol.get("parent") else None,
            )
            for symbol in item.get("symbols") or []
            if isinstance(symbol, dict) and symbol.get("name")
        ]
        files.append(
            CodeFileRecord(
                path=str(item.get("path") or ""),
                extension=str(item.get("extension") or ""),
                size=int(item.get("size") or 0),
                modified_at=str(item.get("modified_at") or ""),
                line_count=int(item.get("line_count") or 0),
                summary=str(item.get("summary") or ""),
                symbols=symbols,
                imports=[str(value) for value in item.get("imports") or []],
                routes=[str(value) for value in item.get("routes") or []],
                tool_names=[str(value) for value in item.get("tool_names") or []],
                terms=[str(value) for value in item.get("terms") or []],
            )
        )
    return CodeIndex(
        version=int(payload.get("version") or 2),
        root=str(payload.get("root") or ""),
        created_at=str(payload.get("created_at") or ""),
        file_count=int(payload.get("file_count") or len(files)),
        skipped=int(payload.get("skipped") or 0),
        truncated=bool(payload.get("truncated")),
        max_files=int(payload.get("max_files") or 0),
        stores_full_file_contents=bool(payload.get("stores_full_file_contents")),
        secrets_indexed=bool(payload.get("secrets_indexed")),
        files=files,
    )
