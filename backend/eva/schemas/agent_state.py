from __future__ import annotations

from dataclasses import asdict, field
from typing import Any

from .modeling import schema_dataclass


@schema_dataclass
class EvaAgentState:
    task_id: str
    selected_agent: str | None = None
    intent: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    proposed_actions: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    final_response: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict
