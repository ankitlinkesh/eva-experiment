from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_safe_text(output: str, message: str) -> None:
    lowered = output.lower()
    assert_true("{'" not in output and "traceback" not in lowered, f"raw output: {message}")
    assert_true("c:\\users\\" not in lowered and "sk-" not in lowered, f"private or secret-like output: {message}")
    assert_true("live llm calls: locked" in lowered and "mock/local only" in lowered, f"missing locked boundary: {message}")
    assert_true("invalid llm output cannot execute tools" in lowered, f"missing tool-execution block: {message}")
    assert_true("repair does not execute or rewrite user intent" in lowered, f"missing repair boundary: {message}")


def main() -> int:
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.llm.formatter import (
        format_llm_repair_policy,
        format_llm_schema_registry,
        format_llm_validate_invalid_examples,
        format_llm_validate_mock,
        format_llm_validation_policy,
        format_llm_validation_readiness,
        format_llm_validation_status,
    )
    from backend.eva.tools.registry import ToolRegistry

    formatter_outputs = (
        format_llm_validation_status(),
        format_llm_schema_registry(),
        format_llm_validation_policy(),
        format_llm_repair_policy(),
        format_llm_validate_mock(),
        format_llm_validate_invalid_examples(),
        format_llm_validation_readiness(),
    )
    for output in formatter_outputs:
        assert_safe_text(output, "formatter")

    invalid_examples = formatter_outputs[5].lower()
    assert_true("malformed json: blocked" in invalid_examples, "malformed JSON example did not fail safely")
    assert_true("tool execution: blocked" in invalid_examples, "tool execution example was not blocked")
    assert_true("hallucinated capability: flagged" in invalid_examples, "hallucinated capability example was not flagged")

    commands = {
        "eva llm validation status": "LLM Structured Output Validation Status",
        "eva llm schema registry": "LLM Structured Output Schema Registry",
        "eva llm validation policy": "LLM Structured Output Validation Policy",
        "eva llm repair policy": "LLM Structured Output Repair Policy",
        "eva llm validate mock": "LLM Structured Output Mock Validation",
        "eva llm validate invalid examples": "LLM Structured Output Invalid Examples",
        "eva llm validation readiness": "LLM Structured Output Validation Readiness",
    }
    for command, heading in commands.items():
        result = maybe_handle_fast_command(command, ToolRegistry())
        assert_true(result is not None and result[0].startswith(heading), f"command missing: {command}")
        assert_safe_text(result[0], command)

    ask_routes = {
        "how does Eva validate LLM output": "llm_validation_policy",
        "what happens if the LLM returns bad JSON": "llm_validation_invalid_examples",
        "what happens if the LLM asks to execute a tool": "llm_validation_invalid_examples",
        "how does Eva handle hallucinated capabilities": "llm_validation_invalid_examples",
        "show structured output validation policy": "llm_validation_policy",
        "can invalid LLM output execute actions": "llm_validation_status",
        "show LLM validation readiness": "llm_validation_readiness",
    }
    for prompt, intent in ask_routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == intent and route.authority_category == "read" and not route.real_execution_requested, f"wrong ask route: {prompt}")
        result = maybe_handle_fast_command(f"eva ask {prompt}", ToolRegistry())
        assert_true(result is not None and "Eva ask" in result[0], f"ask command missing: {prompt}")
        assert_safe_text(result[0], prompt)

    secret_like_prompt = "how does Eva validate LLM output token: sk-example-secret-value"
    result = maybe_handle_fast_command(f"eva ask {secret_like_prompt}", ToolRegistry())
    assert_true(result is not None, "secret-like validation ask was not handled")
    assert_safe_text(result[0], "secret-like ask")

    print("PASS: Phase 15C structured-output validation commands are local, readable, and non-executing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
