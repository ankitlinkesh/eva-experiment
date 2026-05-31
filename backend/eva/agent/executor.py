from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .planner import PlannedToolCall
from .action_model import AgentAction
from ..security.permission_gate import PermissionContext, evaluate_action
from ..tools.registry import ToolRegistry


@dataclass(frozen=True)
class ToolExecutionResult:
    ok: bool
    tool: str
    result: Any = None
    error: str | None = None
    requires_confirmation: bool = False
    action: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "ok": self.ok,
            "tool": self.tool,
            "result": self.result,
            "error": self.error,
        }
        if self.requires_confirmation:
            payload["requires_confirmation"] = True
            payload["action"] = self.action
        return payload


class ToolExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute_all(self, calls: list[PlannedToolCall]) -> list[ToolExecutionResult]:
        results: list[ToolExecutionResult] = []
        for call in calls[:3]:
            result = self.execute(call)
            results.append(result)
            if result.requires_confirmation:
                break
        return results

    def execute(self, call: PlannedToolCall) -> ToolExecutionResult:
        spec = self.registry.get(call.tool)
        if spec is None:
            return ToolExecutionResult(ok=False, tool=call.tool, error="Unknown tool.")

        args = dict(call.args or {})
        validation_error = self._validate_args(spec.args_schema, args)
        if validation_error:
            return ToolExecutionResult(ok=False, tool=call.tool, error=validation_error)

        if call.tool == "guarded_power_action" and not bool(args.get("confirmed")):
            action = str(args.get("action") or "power action")
            return ToolExecutionResult(
                ok=False,
                tool=call.tool,
                error=f"Confirmation required before {action}.",
                requires_confirmation=True,
                action=action,
            )

        permission = self._permission_decision(spec, call.tool, args)
        if permission.decision in {"ask_confirmation", "ask_override"}:
            return ToolExecutionResult(
                ok=False,
                tool=call.tool,
                error=permission.reason,
                requires_confirmation=True,
                action=call.tool,
            )
        if permission.decision == "hard_block":
            return ToolExecutionResult(ok=False, tool=call.tool, error=permission.reason)

        try:
            result = self.registry.run(call.tool, **args)
            return ToolExecutionResult(ok=True, tool=call.tool, result=result)
        except Exception as exc:
            return ToolExecutionResult(ok=False, tool=call.tool, error=str(exc))

    def _validate_args(self, schema: dict[str, Any], args: dict[str, Any]) -> str | None:
        properties = schema.get("properties", {}) or {}
        required = schema.get("required", []) or []
        additional = bool(schema.get("additionalProperties", True))

        for key in required:
            if key not in args:
                return f"Missing required argument: {key}"

        if not additional:
            unknown = sorted(set(args) - set(properties))
            if unknown:
                return f"Unknown arguments: {', '.join(unknown)}"

        for key, value in args.items():
            rules = properties.get(key)
            if not isinstance(rules, dict):
                continue
            expected_type = rules.get("type")
            if expected_type == "string" and not isinstance(value, str):
                return f"Argument {key} must be a string."
            if expected_type == "boolean" and not isinstance(value, bool):
                return f"Argument {key} must be a boolean."
            allowed = rules.get("enum")
            if allowed is not None and isinstance(value, str) and value.lower() not in {str(item).lower() for item in allowed}:
                return f"Argument {key} has unsupported value: {value}"

        return None

    def _permission_decision(self, spec, tool_name: str, args: dict[str, Any]):
        confirmed = bool(args.get("confirmed"))
        action = AgentAction(
            tool_name=tool_name,
            action_type=getattr(spec, "action_type", "SAFE_LOCAL_READ"),
            description=getattr(spec, "description", tool_name),
            params=args,
            risk_categories=list(getattr(spec, "risk_categories", ("SAFE_LOCAL_READ",))),
            destructive=getattr(spec, "action_type", "") in {"DESTRUCTIVE_FILE_ACTION", "SYSTEM_CHANGE"},
            privacy_sensitive=getattr(spec, "action_type", "") in {"PRIVACY_SCREEN_READ", "PRIVACY_FILE_READ", "PRIVACY_CHAT_READ"},
            external_visible=getattr(spec, "action_type", "") in {"EXTERNAL_MESSAGE_SEND", "EXTERNAL_POST"},
            verification={"method": getattr(spec, "verification_method", "command_result_success")},
        )
        context = PermissionContext(
            user_confirmed=confirmed,
            override_granted=confirmed,
        )
        return evaluate_action(action, context)
