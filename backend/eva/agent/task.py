from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

TaskStatus = Literal["planning", "running", "waiting_for_confirmation", "done", "failed", "cancelled"]
StepStatus = Literal["planned", "running", "done", "failed", "skipped"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentStep:
    index: int
    thought_summary: str
    planned_action: str
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    observation: str = ""
    status: StepStatus = "planned"
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentTask:
    user_goal: str
    id: str = field(default_factory=lambda: uuid4().hex)
    status: TaskStatus = "planning"
    steps: list[AgentStep] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    final_response: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    max_steps: int = 6
    max_tool_calls: int = 10
    max_web_searches: int = 4
    max_screen_captures: int = 2

    def touch(self) -> None:
        self.updated_at = utc_now()

    def add_step(self, step: AgentStep) -> None:
        self.steps.append(step)
        self.touch()

    def add_observation(self, observation: str) -> None:
        self.observations.append(observation)
        self.touch()

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_goal": self.user_goal,
            "status": self.status,
            "steps": [step.as_dict() for step in self.steps],
            "observations": list(self.observations),
            "final_response": self.final_response,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "max_steps": self.max_steps,
            "max_tool_calls": self.max_tool_calls,
            "max_web_searches": self.max_web_searches,
            "max_screen_captures": self.max_screen_captures,
        }
