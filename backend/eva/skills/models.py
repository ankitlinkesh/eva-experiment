from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class SkillStep:
    id: str
    title: str
    description: str
    capability_id: str | None
    specialist_id: str | None
    mode: str
    authority_category: str
    requires_confirmation: bool = False
    verification_required: bool = False
    rollback_available: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class EvaSkill:
    id: str
    name: str
    description: str
    category: str
    specialists: tuple[str, ...]
    capabilities: tuple[str, ...]
    safe_modes: tuple[str, ...]
    status: str = "stable"
    safety_notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class EvaWorkflow:
    id: str
    name: str
    description: str
    skill_id: str
    specialists: tuple[str, ...]
    steps: tuple[SkillStep, ...]
    mode: str
    authority_category: str
    real_execution_scope: str
    target_hint: str | None = None
    content_hint: str | None = None
    next_step: str = ""
    safety_notes: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
