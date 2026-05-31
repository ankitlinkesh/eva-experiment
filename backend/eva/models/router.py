from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
    reason: str
