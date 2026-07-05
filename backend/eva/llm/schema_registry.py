from __future__ import annotations

from .output_contracts import OutputContract


_CONTRACTS = {
    "route_decision_preview": OutputContract(
        "route_decision_preview",
        ("intent", "capability", "reason"),
        ("intent", "capability", "reason"),
        (("intent", "string"), ("capability", "string"), ("reason", "string")),
    ),
    "action_plan_preview": OutputContract(
        "action_plan_preview",
        ("summary", "steps", "safety"),
        ("summary", "steps", "safety"),
        (("summary", "string"), ("steps", "list"), ("safety", "string")),
        (("safety", ("preview_only",)),),
    ),
    "safety_decision_preview": OutputContract(
        "safety_decision_preview",
        ("decision", "reason"),
        ("decision", "reason"),
        (("decision", "string"), ("reason", "string")),
        (("decision", ("allow_preview", "blocked", "needs_approval")),),
    ),
    "approval_request_preview": OutputContract(
        "approval_request_preview",
        ("summary", "action", "requires_confirmation"),
        ("summary", "action", "requires_confirmation"),
        (("summary", "string"), ("action", "string"), ("requires_confirmation", "boolean")),
    ),
    "clarification_request": OutputContract(
        "clarification_request",
        ("question",),
        ("question",),
        (("question", "string"),),
    ),
    "refusal_response": OutputContract(
        "refusal_response",
        ("reason",),
        ("reason", "safe_alternative"),
        (("reason", "string"), ("safe_alternative", "string")),
    ),
    "summary_response": OutputContract(
        "summary_response",
        ("summary",),
        ("summary",),
        (("summary", "string"),),
    ),
    "unknown_or_invalid": OutputContract(
        "unknown_or_invalid",
        ("reason",),
        ("reason",),
        (("reason", "string"),),
    ),
}


def get_contract(name: object) -> OutputContract | None:
    return _CONTRACTS.get(name) if isinstance(name, str) else None


def list_contracts() -> tuple[OutputContract, ...]:
    return tuple(_CONTRACTS.values())


def is_known_capability(capability_id: object) -> bool:
    """Check existing static capability metadata and fail closed on any problem."""
    if not isinstance(capability_id, str) or not capability_id.strip():
        return False
    try:
        from ..capabilities.registry import get_capability

        return get_capability(capability_id.strip()) is not None
    except Exception:
        return False
