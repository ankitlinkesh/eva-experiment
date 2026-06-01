from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..schemas.results import EvaAgentResult


@dataclass
class EvaAgent:
    name: str
    description: str
    capabilities: tuple[str, ...]
    delegated_core: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        text = str(intent or "").lower()
        score = 0.0
        for capability in self.capabilities:
            if capability.replace("_", " ") in text or capability in text:
                score = max(score, 0.6)
        return score

    def plan(self, state: Any) -> EvaAgentResult:
        action = {
            "agent": self.name,
            "action_type": f"{self.name}.delegate_existing_system",
            "summary": f"Would delegate to {self.delegated_core}.",
            "requires_permission": False,
            "side_effect_level": "proposed_only",
            "delegate_to": self.delegated_core,
            "safety": "existing permission gate remains authoritative",
        }
        return EvaAgentResult(
            agent_name=self.name,
            ok=True,
            message=f"{self.name.title()}Agent selected. Phase 2 preview would delegate to {self.delegated_core}.",
            proposed_actions=[action],
            delegated_to=self.delegated_core,
        )

    def execute(self, state: Any) -> EvaAgentResult:
        return EvaAgentResult(
            agent_name=self.name,
            ok=True,
            message=f"{self.name.title()}Agent execution is delegated in Phase 1.",
            delegated_to=self.delegated_core,
        )
