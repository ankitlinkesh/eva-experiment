from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class SpecialistRole:
    id: str
    name: str
    description: str
    category: str
    primary_capabilities: tuple[str, ...]
    safe_modes: tuple[str, ...]
    unavailable_actions: tuple[str, ...] = field(default_factory=tuple)
    safety_notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
