from __future__ import annotations

from dataclasses import asdict, field
from typing import Any
from uuid import uuid4

from .modeling import schema_dataclass


@schema_dataclass
class EvaToolCall:
    tool_name: str
    args: dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: uuid4().hex)
    reason: str = ""
    provenance: str = "v2_runtime"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict
