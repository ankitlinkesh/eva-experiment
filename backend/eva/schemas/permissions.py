from __future__ import annotations

from dataclasses import asdict, field

from .modeling import schema_dataclass


@schema_dataclass
class EvaPermissionDecision:
    decision: str
    reason: str
    required_phrase: str | None = None
    expires_after_seconds: int | None = None
    risk_categories: list[str] = field(default_factory=list)
    safe_alternative: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    model_dump = as_dict
