from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    id: str
    name: str
    description: str
    provider: str
    category: str
    risk_level: str
    read_only: bool
    requires_confirmation: bool
    enabled_by_default: bool
    status: str
    safety_notes: str
    verifier_name: str | None = None

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "provider": self.provider,
            "category": self.category,
            "risk_level": self.risk_level,
            "read_only": self.read_only,
            "requires_confirmation": self.requires_confirmation,
            "enabled_by_default": self.enabled_by_default,
            "status": self.status,
            "safety_notes": self.safety_notes,
            "verifier_name": self.verifier_name,
        }
