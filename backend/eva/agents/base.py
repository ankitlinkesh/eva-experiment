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
        return EvaAgentResult(
            agent_name=self.name,
            ok=True,
            message=f"{self.name.title()}Agent selected. Phase 1 will delegate to {self.delegated_core} instead of replacing existing behavior.",
            proposed_actions=[
                {
                    "agent": self.name,
                    "delegate_to": self.delegated_core,
                    "safety": "existing permission gate remains authoritative",
                }
            ],
            delegated_to=self.delegated_core,
        )

    def execute(self, state: Any) -> EvaAgentResult:
        return EvaAgentResult(
            agent_name=self.name,
            ok=True,
            message=f"{self.name.title()}Agent execution is delegated in Phase 1.",
            delegated_to=self.delegated_core,
        )
