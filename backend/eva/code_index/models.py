from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CodeSymbol:
    name: str
    kind: str
    line: int
    parent: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CodeFileRecord:
    path: str
    extension: str
    size: int
    modified_at: str
    line_count: int
    summary: str
    symbols: list[CodeSymbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    routes: list[str] = field(default_factory=list)
    tool_names: list[str] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["symbols"] = [symbol.as_dict() if hasattr(symbol, "as_dict") else symbol for symbol in self.symbols]
        return data


@dataclass
class CodeIndex:
    version: int
    root: str
    created_at: str
    file_count: int
    skipped: int
    truncated: bool
    max_files: int
    stores_full_file_contents: bool
    secrets_indexed: bool
    files: list[CodeFileRecord]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["files"] = [record.as_dict() if hasattr(record, "as_dict") else record for record in self.files]
        return data
