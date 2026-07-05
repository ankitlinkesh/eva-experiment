from __future__ import annotations

import json
from collections.abc import Mapping

from .output_contracts import StructuredOutputValidationResult
from .schema_registry import get_contract, is_known_capability
from .validation_policy import (
    MAX_STRUCTURED_OUTPUT_CHARS,
    collect_text,
    find_capability_claims,
    is_private_path_like_output,
    is_secret_like_output,
    requests_execution,
)


def validate_structured_output(value: object) -> StructuredOutputValidationResult:
    """Validate only local mock preview data; this function never executes output."""
    parsed, parse_issue = _parse_output(value)
    if parse_issue:
        return _invalid("unknown_or_invalid", (parse_issue,))

    assert parsed is not None
    if len(collect_text(parsed)) > MAX_STRUCTURED_OUTPUT_CHARS:
        return _invalid("unknown_or_invalid", ("output_too_large",))
    if is_secret_like_output(parsed):
        return _invalid("unknown_or_invalid", ("secret_like_output",))
    if is_private_path_like_output(parsed):
        return _invalid("unknown_or_invalid", ("private_path_like_output",))
    if requests_execution(parsed):
        return _invalid("unknown_or_invalid", ("execution_request_blocked",))

    output_type = parsed.get("type")
    contract = get_contract(output_type)
    if contract is None:
        return _invalid("unknown_or_invalid", (f"unknown_output_type:{_safe_label(output_type)}",))

    issues = _validate_shape(parsed, contract)
    issues.extend(_validate_capability_claims(parsed, output_type))
    if issues:
        return _invalid(str(output_type), tuple(issues))

    normalized = dict(parsed)
    return StructuredOutputValidationResult(
        valid=True,
        output_type=str(output_type),
        issues=(),
        blocked=False,
        normalized_output=normalized,
        safe_output={"type": str(output_type), "status": "validated_preview_only"},
    )


def _parse_output(value: object) -> tuple[dict[str, object] | None, str | None]:
    if isinstance(value, str):
        if len(value) > MAX_STRUCTURED_OUTPUT_CHARS:
            return None, "output_too_large"
        try:
            value = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None, "malformed_json"
    if not isinstance(value, Mapping):
        return None, "output_must_be_object"
    return dict(value), None


def _validate_shape(value: Mapping[str, object], contract: object) -> list[str]:
    from .output_contracts import OutputContract

    assert isinstance(contract, OutputContract)
    issues: list[str] = []
    allowed = {"type", *contract.allowed_fields}
    for field_name in value:
        if field_name not in allowed:
            issues.append(f"unknown_field:{field_name}")
    for field_name in contract.required_fields:
        field_value = value.get(field_name)
        if field_name not in value or field_value is None or (isinstance(field_value, str) and not field_value.strip()):
            issues.append(f"missing_required_field:{field_name}")
            continue
        expected_type = contract.expected_type(field_name)
        if expected_type and not _matches_type(field_value, expected_type):
            issues.append(f"invalid_type:{field_name}")
            continue
        allowed_values = contract.allowed_values(field_name)
        if allowed_values is not None and field_value not in allowed_values:
            issues.append(f"invalid_enum:{field_name}")
    if contract.name == "approval_request_preview" and value.get("requires_confirmation") is not True:
        issues.append("approval_requires_confirmation")
    if contract.name == "action_plan_preview" and isinstance(value.get("steps"), list):
        if not value["steps"] or not all(isinstance(item, str) and item.strip() for item in value["steps"]):
            issues.append("invalid_preview_steps")
    return issues


def _validate_capability_claims(value: Mapping[str, object], output_type: object) -> list[str]:
    issues: list[str] = []
    if output_type == "route_decision_preview":
        capability = value.get("capability")
        if not is_known_capability(capability):
            issues.append(f"unknown_capability:{_safe_label(capability)}")
    for capability in find_capability_claims(value):
        if not is_known_capability(capability):
            issues.append(f"hallucinated_capability_claim:{capability}")
    return list(dict.fromkeys(issues))


def _matches_type(value: object, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "list":
        return isinstance(value, list)
    if expected_type == "boolean":
        return type(value) is bool
    return False


def _invalid(output_type: str, issues: tuple[str, ...]) -> StructuredOutputValidationResult:
    return StructuredOutputValidationResult(
        valid=False,
        output_type=output_type,
        issues=issues,
        blocked=True,
        normalized_output=None,
        safe_output={
            "type": "refusal_response",
            "reason": "Structured output was blocked by the local preview validator.",
            "safe_alternative": "Return a schema-valid preview without secrets, private paths, or execution asks.",
        },
    )


def _safe_label(value: object) -> str:
    return str(value).strip().replace(" ", "_")[:80] or "missing"
