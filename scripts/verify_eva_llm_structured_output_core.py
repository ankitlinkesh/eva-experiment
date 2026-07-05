from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    from backend.eva.llm.repair_policy import plan_safe_repair
    from backend.eva.llm.schema_registry import list_contracts
    from backend.eva.llm.validation_engine import validate_structured_output
    from backend.eva.llm.validation_examples import VALID_ACTION_PLAN_PREVIEW, VALID_ROUTE_DECISION_PREVIEW

    contract_names = {contract.name for contract in list_contracts()}
    assert_true(
        contract_names == {
            "route_decision_preview",
            "action_plan_preview",
            "safety_decision_preview",
            "approval_request_preview",
            "clarification_request",
            "refusal_response",
            "summary_response",
            "unknown_or_invalid",
        },
        "structured-output contracts are incomplete",
    )

    assert_true(validate_structured_output(VALID_ROUTE_DECISION_PREVIEW).valid, "valid mock route decision was rejected")
    assert_true(validate_structured_output(VALID_ACTION_PLAN_PREVIEW).valid, "valid mock action plan was rejected")

    malformed = validate_structured_output('{"type": "summary_response"')
    assert_true(not malformed.valid and malformed.safe_output["type"] == "refusal_response", "malformed JSON did not fail safely")

    missing_required = validate_structured_output({"type": "summary_response"})
    assert_true(not missing_required.valid and "missing_required_field:summary" in missing_required.issues, "missing field was accepted")

    invalid_enum = validate_structured_output(
        {"type": "safety_decision_preview", "decision": "ship_it", "reason": "not a supported safety decision"}
    )
    assert_true(not invalid_enum.valid and "invalid_enum:decision" in invalid_enum.issues, "invalid enum was accepted")

    unknown_capability = validate_structured_output(
        {"type": "route_decision_preview", "intent": "status", "capability": "invented.capability", "reason": "hallucinated"}
    )
    assert_true(not unknown_capability.valid and "unknown_capability:invented.capability" in unknown_capability.issues, "unknown capability was accepted")

    tool_request = validate_structured_output(
        {"type": "action_plan_preview", "summary": "run it", "steps": ["do a preview"], "safety": "preview_only", "tool_execution": True}
    )
    assert_true(not tool_request.valid and tool_request.blocked and tool_request.safe_output["type"] == "refusal_response", "tool execution was not blocked")

    hallucinated_claim = validate_structured_output(
        {"type": "summary_response", "summary": "I can invoke capability invented.capability now."}
    )
    assert_true(not hallucinated_claim.valid and "hallucinated_capability_claim:invented.capability" in hallucinated_claim.issues, "hallucinated capability claim was not flagged")

    secret_output = validate_structured_output(
        {"type": "summary_response", "summary": "token: sk-example-secret-value"}
    )
    assert_true(not secret_output.valid and "secret_like_output" in secret_output.issues, "secret-like output was not flagged")

    private_path = validate_structured_output(
        {"type": "summary_response", "summary": "Saved under C:\\Users\\HP\\private\\notes.txt"}
    )
    assert_true(not private_path.valid and "private_path_like_output" in private_path.issues, "private path was not flagged")

    oversized = validate_structured_output(
        {"type": "summary_response", "summary": "x" * 12_001}
    )
    assert_true(not oversized.valid and "output_too_large" in oversized.issues, "oversized output was accepted")

    intent = "summarize current status"
    repair = plan_safe_repair(malformed, user_intent=intent)
    assert_true(not repair.execute and repair.user_intent == intent and repair.repaired_output is None, "repair policy changed intent or enabled execution")
    assert_true(json.dumps(repair.__dict__, sort_keys=True), "repair decision is not serializable")

    print("PASS: Phase 15C structured-output validation core is safe and mock-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
