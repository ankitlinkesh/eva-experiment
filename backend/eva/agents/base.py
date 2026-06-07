from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..schemas.results import EvaAgentResult
from .contracts import EvaAgentRequest, EvaAgentResponse, request_from_any


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

    def dry_run(self, request: Any) -> EvaAgentResponse:
        agent_request = request_from_any(request)
        try:
            planned = self.plan(_PreviewState(agent_request.user_goal, agent_request.input_summary))
            summary = planned.message
            details = {
                "delegated_to": planned.delegated_to or self.delegated_core,
                "proposed_actions": planned.proposed_actions[:3],
                "execution_enabled": False,
            }
        except Exception as exc:
            summary = f"{type(self).__name__} dry-run is unavailable."
            details = {"execution_enabled": False}
            return EvaAgentResponse(
                agent_name=type(self).__name__,
                request_id=agent_request.request_id,
                task_step_id=agent_request.task_step_id,
                action=f"{self.name}.dry_run",
                status="unavailable",
                summary=summary,
                details=details,
                required_permission=None,
                risk_level="low",
                capability_id=agent_request.capability_id,
                resource_id=agent_request.resource_id,
                errors=[str(exc)],
                next_action="No task was executed.",
            )
        return EvaAgentResponse(
            agent_name=type(self).__name__,
            request_id=agent_request.request_id,
            task_step_id=agent_request.task_step_id,
            action=f"{self.name}.dry_run",
            status="dry_run",
            summary=summary,
            details=details,
            required_permission=_required_permission_for(agent_request.capability_id, agent_request.input_summary),
            risk_level=_risk_for(agent_request.capability_id, agent_request.input_summary),
            capability_id=agent_request.capability_id,
            resource_id=agent_request.resource_id,
            next_action="No task was executed. This was an agent dry-run preview.",
        )

    def execute(self, request: Any) -> EvaAgentResponse:
        agent_request = request_from_any(request)
        return EvaAgentResponse(
            agent_name=type(self).__name__,
            request_id=agent_request.request_id,
            task_step_id=agent_request.task_step_id,
            action=f"{self.name}.execute",
            status="refused",
            summary="Execution disabled in Agent Framework v1.",
            details={"execution_enabled": False, "delegated_core": self.delegated_core},
            required_permission=_required_permission_for(agent_request.capability_id, agent_request.input_summary),
            risk_level=_risk_for(agent_request.capability_id, agent_request.input_summary),
            capability_id=agent_request.capability_id,
            resource_id=agent_request.resource_id,
            next_action="Use dry-run/status commands only in this phase.",
        )

    def observe(self, request: Any) -> EvaAgentResponse:
        agent_request = request_from_any(request)
        return self._unavailable(agent_request, "observe", "Observation is unavailable in Agent Framework v1 preview.")

    def verify(self, request: Any) -> EvaAgentResponse:
        agent_request = request_from_any(request)
        return self._unavailable(agent_request, "verify", "Verification preview is unavailable until a future executor phase.")

    def rollback(self, request: Any) -> EvaAgentResponse:
        agent_request = request_from_any(request)
        return self._unavailable(agent_request, "rollback", "Rollback unavailable because no action was executed.")

    def explain(self) -> str:
        return "\n".join(
            [
                f"{type(self).__name__}",
                "",
                self.description,
                "",
                f"Capabilities: {', '.join(self.capabilities)}",
                f"Delegates to: {self.delegated_core}",
                "Execution: disabled in Agent Framework v1 except future explicit safe read-only delegates.",
            ]
        )

    def _unavailable(self, request: EvaAgentRequest, action: str, summary: str) -> EvaAgentResponse:
        return EvaAgentResponse(
            agent_name=type(self).__name__,
            request_id=request.request_id,
            task_step_id=request.task_step_id,
            action=f"{self.name}.{action}",
            status=f"{action}_unavailable",
            summary=summary,
            details={"execution_enabled": False},
            capability_id=request.capability_id,
            resource_id=request.resource_id,
            next_action="No task was executed.",
        )


@dataclass
class _PreviewState:
    normalized_intent: str
    user_request: str


def _required_permission_for(capability_id: str | None, text: str) -> str | None:
    joined = f"{capability_id or ''} {text}".lower()
    if any(term in joined for term in ("whatsapp", "email.send", "post", "submit")):
        return "confirmation_required"
    if any(term in joined for term in ("delete", "file.delete", "shutdown", "install", "shell", "powershell")):
        return "override_required"
    if "browser.control" in joined or "pyautogui" in joined or "playwright" in joined:
        return "blocked"
    return None


def _risk_for(capability_id: str | None, text: str) -> str:
    permission = _required_permission_for(capability_id, text)
    if permission in {"override_required", "blocked"}:
        return "high"
    if permission == "confirmation_required":
        return "medium"
    return "low"
