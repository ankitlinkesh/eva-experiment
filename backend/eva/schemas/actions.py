from __future__ import annotations

from dataclasses import asdict, field
from typing import Any
from uuid import uuid4

from .modeling import schema_dataclass


@schema_dataclass
class EvaAction:
    tool_name: str
    action_type: str
    description: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    risk_categories: list[str] = field(default_factory=list)
    expected_result: str = ""
    verification: dict[str, Any] = field(default_factory=dict)
    rollback: dict[str, Any] = field(default_factory=dict)
    requires_network: bool = False
    external_visible: bool = False
    destructive: bool = False
    privacy_sensitive: bool = False
    action_id: str = field(default_factory=lambda: uuid4().hex)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict

    @classmethod
    def from_existing_agent_action(cls, action: Any) -> "EvaAction":
        return cls(
            action_id=str(getattr(action, "action_id", "") or uuid4().hex),
            tool_name=str(getattr(action, "tool_name", "")),
            action_type=str(getattr(action, "action_type", "")),
            description=str(getattr(action, "description", "")),
            params=dict(getattr(action, "params", {}) or {}),
            risk_categories=list(getattr(action, "risk_categories", []) or []),
            expected_result=str(getattr(action, "expected_result", "")),
            verification=dict(getattr(action, "verification", {}) or {}),
            rollback=dict(getattr(action, "rollback", {}) or {}),
            requires_network=bool(getattr(action, "requires_network", False)),
            external_visible=bool(getattr(action, "external_visible", False)),
            destructive=bool(getattr(action, "destructive", False)),
            privacy_sensitive=bool(getattr(action, "privacy_sensitive", False)),
        )

    def to_existing_agent_action(self) -> Any:
        from ..agent.action_model import AgentAction

        return AgentAction(
            action_id=self.action_id,
            tool_name=self.tool_name,
            action_type=self.action_type,
            description=self.description,
            params=dict(self.params),
            risk_categories=list(self.risk_categories),
            expected_result=self.expected_result,
            verification=dict(self.verification),
            rollback=dict(self.rollback),
            requires_network=self.requires_network,
            external_visible=self.external_visible,
            destructive=self.destructive,
            privacy_sensitive=self.privacy_sensitive,
        )


def from_existing_agent_action(action: Any) -> EvaAction:
    return EvaAction.from_existing_agent_action(action)


def to_existing_agent_action(action: EvaAction) -> Any:
    return action.to_existing_agent_action()
