from __future__ import annotations

from .models import LLMStructuredOutputContract, LLMValidationResult


def get_structured_output_contract() -> LLMStructuredOutputContract:
    return LLMStructuredOutputContract("assistant_response_preview", ("answer",), False)


def validate_mock_structured_output(value: object) -> LLMValidationResult:
    if not isinstance(value, dict):
        return LLMValidationResult(False, "Mock output must be an object.")
    answer = value.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return LLMValidationResult(False, "Mock output requires a non-empty answer field.")
    return LLMValidationResult(True, "Mock structured output matches the preview contract.")
