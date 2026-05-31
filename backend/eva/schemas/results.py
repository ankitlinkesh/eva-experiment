from __future__ import annotations

from dataclasses import asdict, field
from typing import Any

from .modeling import schema_dataclass


@schema_dataclass
class EvaToolResult:
    tool_name: str
    ok: bool
    result: Any = None
    message: str = ""
    error: str | None = None
    provenance: str = "tool_result"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict

    @classmethod
    def from_tool_result(cls, tool_name: str, result: Any) -> "EvaToolResult":
        if isinstance(result, dict):
            return cls(
                tool_name=tool_name,
                ok=bool(result.get("ok", True)),
                result=result,
                message=str(result.get("message") or result.get("summary") or ""),
                error=result.get("error"),
            )
        return cls(tool_name=tool_name, ok=True, result=result, message=str(result))


@schema_dataclass
class EvaVerificationResult:
    action_id: str
    verified: bool
    confidence: float
    evidence: str
    failure_reason: str | None = None
    suggested_repair: str | None = None
    source: str = "no_verification_available"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict


@schema_dataclass
class EvaAgentResult:
    agent_name: str
    ok: bool
    message: str
    proposed_actions: list[dict[str, Any]] = field(default_factory=list)
    delegated_to: str | None = None
    provenance: str = "v2_runtime"
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict


@schema_dataclass
class EvaFinalResponse:
    text: str
    provenance: str
    ok: bool = True
    trace_id: str | None = None
    needs_user_input: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict


def from_tool_result(tool_name: str, result: Any) -> EvaToolResult:
    return EvaToolResult.from_tool_result(tool_name, result)
