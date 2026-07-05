from __future__ import annotations

from .fallbacks import get_fallback_chain, list_failure_scenarios, simulate_fallback
from .degraded_mode import get_degraded_mode_decision
from .limits import get_cost_budget, get_rate_limit_policy, get_runaway_protection_policy, get_token_budget
from .routing_audit import get_routing_audit_preview
from .session_limits import get_session_limit_policy
from .provider_contracts import list_provider_contracts
from .router import preview_llm_route
from .routing_policy import get_fallback_policy, get_retry_policy, get_routing_policy, get_timeout_policy
from .status import get_llm_router_status
from .structured_output import get_structured_output_contract
from .repair_policy import plan_safe_repair
from .schema_registry import list_contracts
from .validation_engine import validate_structured_output
from .validation_examples import VALID_ACTION_PLAN_PREVIEW, VALID_ROUTE_DECISION_PREVIEW
from .validation_policy import validation_policy_text
from .failure_test_policy import get_failure_test_policy
from .failure_test_report import format_failure_test_report
from .red_team_cases import list_red_team_cases
from .red_team_runner import run_local_red_team


def _boundary() -> str:
    return "Live LLM/API/network calls are not enabled in Phase 15B. No tool execution is enabled."


def format_llm_status() -> str:
    status = get_llm_router_status()
    return "\n".join(["LLM Router Status", "", f"Status: {status.status}", "Live provider calls: locked", "Mode: mock/dry-run only", status.summary, _boundary()])


def format_llm_providers() -> str:
    lines = ["LLM Provider Contracts", "", "Provider metadata only:"]
    lines.extend(f"- {item.provider.value}: {item.status.value}; {item.notes}" for item in list_provider_contracts())
    lines.extend(["", _boundary()])
    return "\n".join(lines)


def format_llm_routing_policy() -> str:
    policy = get_routing_policy()
    return "\n".join(["LLM Routing Policy", "", f"Mode: {policy.mode}", f"Default preview provider: {policy.default_provider.value}", policy.explanation, _boundary()])


def format_llm_fallback_policy() -> str:
    policy = get_fallback_policy()
    return "\n".join(["LLM Fallback Policy", "", f"Metadata order: {' -> '.join(item.value for item in policy.order)}", policy.on_failure, _boundary()])


def format_llm_limits() -> str:
    token, cost = get_token_budget(), get_cost_budget()
    retry, timeout = get_retry_policy(), get_timeout_policy()
    return "\n".join(["LLM Router Limits", "", f"Token preview budget: input {token.max_input_tokens}, output {token.max_output_tokens}", f"Cost budget: ${cost.max_cost_usd:.2f}; {cost.enforcement}", f"Timeout policy: {timeout.request_timeout_seconds}s", f"Retry preview: up to {retry.max_attempts} attempts", _boundary()])


def format_llm_structured_output() -> str:
    contract = get_structured_output_contract()
    return "\n".join(["LLM Structured Output Rules", "", f"Contract: {contract.name}", f"Required fields: {', '.join(contract.required_fields)}", "Validation: mock structured output only", _boundary()])


def format_llm_route_preview(request: str) -> str:
    decision = preview_llm_route(request)
    return "\n".join(["LLM Route Preview", "", f"Selected preview provider: {decision.selected_provider.value}", f"Fallback metadata: {' -> '.join(item.value for item in decision.fallback_order)}", f"Degraded mode: {decision.degraded_mode.value}", f"Reason: {decision.reason}", _boundary()])


def format_llm_readiness() -> str:
    return "\n".join(["LLM Router Readiness", "", "Ready now: provider contracts, routing previews, limits, fallback metadata, mock validation, and degraded-mode explanations.", "Not ready now: live provider calls, network access, SDKs, secret/config reads, and tool execution.", "Next phase: Phase 15B Router Fallbacks, Limits, and Degraded Mode, or Phase 16 Context Assembly Engine after hardening.", _boundary()])


def format_llm_fallback_chain() -> str:
    chain = get_fallback_chain()
    return "\n".join(["LLM Fallback Chain", "", f"Metadata chain: {' -> '.join(step.provider.value for step in chain.steps)}", "Fallback is simulated only. Mock/status mode is selected instead of calling a provider.", _boundary()])


def format_llm_fallback_simulation(scenario: str) -> str:
    decision = simulate_fallback(scenario)
    return "\n".join(["LLM Fallback Simulation", "", f"Scenario: {decision.scenario.value}", f"Selected simulated provider: {decision.selected_provider.value}", f"Degraded mode: {decision.degraded_mode.value}", decision.reason, _boundary()])


def format_llm_degraded_mode() -> str:
    decision = get_degraded_mode_decision()
    return "\n".join(["LLM Degraded Mode", "", f"Mode: {decision.mode.value}", decision.reason, _boundary()])


def format_llm_session_limits() -> str:
    policy = get_session_limit_policy()
    return "\n".join(["LLM Session Limits", "", f"Route previews: {policy.max_route_previews}", f"Planning steps: {policy.max_planning_steps}", f"Retry preview limit: {policy.max_retries}", _boundary()])


def format_llm_rate_limits() -> str:
    policy = get_rate_limit_policy()
    return "\n".join(["LLM Rate Limits", "", f"Simulated requests per minute: {policy.max_simulated_requests_per_minute}", policy.response, _boundary()])


def format_llm_routing_audit_preview() -> str:
    audit = get_routing_audit_preview()
    return "\n".join(["LLM Routing Audit Preview", "", f"Event: {audit.event_type}", f"Provider: {audit.provider.value}", audit.summary, _boundary()])


def format_llm_failure_modes() -> str:
    return "\n".join(["LLM Failure Modes", "", *[f"- {item.failure_mode.value}" for item in list_failure_scenarios()], "", _boundary()])


def format_llm_runaway_protection() -> str:
    policy = get_runaway_protection_policy()
    return "\n".join(["LLM Runaway Protection", "", f"Maximum preview steps: {policy.max_router_steps}", policy.stop_behavior, _boundary()])


def _validation_boundary() -> list[str]:
    return [
        "Live LLM calls: locked.",
        "Validation: mock/local only.",
        "Invalid LLM output cannot execute tools.",
        "Repair does not execute or rewrite user intent.",
    ]


def format_llm_validation_status() -> str:
    return "\n".join(
        [
            "LLM Structured Output Validation Status",
            "",
            f"Registered preview contracts: {len(list_contracts())}.",
            "Status: local validation core is available for safe preview checks.",
            *_validation_boundary(),
        ]
    )


def format_llm_schema_registry() -> str:
    lines = ["LLM Structured Output Schema Registry", "", "Registered preview-only contracts:"]
    lines.extend(f"- {contract.name}: required {', '.join(contract.required_fields)}" for contract in list_contracts())
    lines.extend(["", *_validation_boundary()])
    return "\n".join(lines)


def format_llm_validation_policy() -> str:
    return "\n".join(["LLM Structured Output Validation Policy", "", validation_policy_text(), *_validation_boundary()])


def format_llm_repair_policy() -> str:
    rejected = validate_structured_output('{"type": "summary_response"')
    repair = plan_safe_repair(rejected, user_intent="preserve the original request")
    return "\n".join(
        [
            "LLM Structured Output Repair Policy",
            "",
            f"Repair execution enabled: {'yes' if repair.execute else 'no'}.",
            "A blocked preview asks for fresh schema-valid output instead of retrying or changing the request.",
            *_validation_boundary(),
        ]
    )


def format_llm_validate_mock() -> str:
    route_result = validate_structured_output(VALID_ROUTE_DECISION_PREVIEW)
    plan_result = validate_structured_output(VALID_ACTION_PLAN_PREVIEW)
    return "\n".join(
        [
            "LLM Structured Output Mock Validation",
            "",
            f"Route decision preview: {'accepted' if route_result.valid else 'blocked'}.",
            f"Action plan preview: {'accepted' if plan_result.valid else 'blocked'}.",
            "These are bundled local mock examples, not provider output.",
            *_validation_boundary(),
        ]
    )


def format_llm_validate_invalid_examples() -> str:
    malformed = validate_structured_output('{"type": "summary_response"')
    tool_request = validate_structured_output(
        {"type": "action_plan_preview", "summary": "preview", "steps": ["review"], "safety": "preview_only", "tool_execution": True}
    )
    hallucinated = validate_structured_output(
        {"type": "summary_response", "summary": "I can invoke capability invented.capability now."}
    )
    return "\n".join(
        [
            "LLM Structured Output Invalid Examples",
            "",
            f"Malformed JSON: {'blocked' if malformed.blocked else 'not blocked'} (refusal preview only).",
            f"Tool execution: {'blocked' if tool_request.blocked else 'not blocked'} (refusal preview only).",
            f"Hallucinated capability: {'flagged' if hallucinated.blocked else 'not flagged'} (refusal preview only).",
            *_validation_boundary(),
        ]
    )


def format_llm_validation_readiness() -> str:
    return "\n".join(
        [
            "LLM Structured Output Validation Readiness",
            "",
            "Ready now: local validation status, schema, policy, repair explanation, and bundled mock examples.",
            "Not ready now: provider calls, network access, SDK use, tool execution, and automatic repair.",
            "Phase 15C is command-surfaced only; capability, resource, tool-schema, and Control Center wiring are not included.",
            *_validation_boundary(),
        ]
    )


def _red_team_boundary() -> list[str]:
    return ["Live LLM calls: locked.", "Red-team tests: local/mock only.", "Invalid LLM-like output cannot execute tools.", "No secret/config/session reads or browser/desktop/shell execution."]


def format_llm_red_team_status() -> str:
    return "\n".join(["LLM Red-Team Status", "", f"Local cases registered: {len(list_red_team_cases())}.", "Unsafe output is blocked before any future provider integration.", *_red_team_boundary()])


def format_llm_red_team_cases() -> str:
    return "\n".join(["LLM Red-Team Cases", "", *[f"- {case.category.replace('_', ' ')}" for case in list_red_team_cases()], "", *_red_team_boundary()])


def format_llm_red_team_run() -> str:
    return "\n".join([format_failure_test_report(run_local_red_team()), "", *_red_team_boundary()])


def format_llm_failure_tests() -> str:
    policy = get_failure_test_policy()
    return "\n".join(["LLM Failure Tests", "", policy.summary, "Provider failures, timeout, rate-limit, degraded mode, and runaway loops stay simulated.", *_red_team_boundary()])


def format_llm_safety_failure_report() -> str:
    return format_llm_red_team_run()


def format_llm_red_team_readiness() -> str:
    return "\n".join(["LLM Red-Team Readiness", "", "Ready now: local case catalog, safe runner, failure report, and metadata wiring.", "Next phase: Phase 16 Context Assembly Engine.", *_red_team_boundary()])
