from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    from backend.eva.llm.fallbacks import get_fallback_chain, simulate_fallback
    from backend.eva.llm.degraded_mode import get_degraded_mode_decision
    from backend.eva.llm.session_limits import get_session_limit_policy
    from backend.eva.llm.limits import get_rate_limit_policy, get_runaway_protection_policy
    from backend.eva.llm.routing_audit import get_routing_audit_preview
    from backend.eva.llm.formatter import format_llm_fallback_chain, format_llm_fallback_simulation, format_llm_degraded_mode, format_llm_session_limits, format_llm_rate_limits, format_llm_routing_audit_preview, format_llm_failure_modes, format_llm_runaway_protection
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry

    decision = simulate_fallback("timeout")
    assert_true(decision.live_call_allowed is False, "fallback simulation must never call a provider")
    assert_true(get_fallback_chain().live_call_allowed is False, "fallback chain enabled live calls")
    for scenario in ("provider_unconfigured", "timeout", "rate_limited", "invalid_output", "token_budget_exceeded", "all_providers_unavailable"):
        assert_true(simulate_fallback(scenario).live_call_allowed is False, f"live call enabled for {scenario}")
    assert_true(get_degraded_mode_decision().live_call_allowed is False, "degraded mode enabled live calls")
    assert_true(get_session_limit_policy().max_route_previews > 0 and get_rate_limit_policy().max_simulated_requests_per_minute > 0 and get_runaway_protection_policy().max_router_steps > 0, "limit policies missing")
    assert_true(get_routing_audit_preview().contains_secrets is False, "audit preview exposes secrets")
    outputs = [format_llm_fallback_chain(), format_llm_fallback_simulation("timeout"), format_llm_degraded_mode(), format_llm_session_limits(), format_llm_rate_limits(), format_llm_routing_audit_preview(), format_llm_failure_modes(), format_llm_runaway_protection()]
    for output in outputs:
        assert_true("{'" not in output and "Traceback" not in output and "C:\\Users\\" not in output, "unsafe output")
        assert_true("live" in output.lower() and ("locked" in output.lower() or "not enabled" in output.lower()), "missing live lock")
    for command in ("eva llm fallback chain", "eva llm fallback simulate timeout", "eva llm fallback simulate all_providers_unavailable", "eva llm degraded mode", "eva llm session limits", "eva llm rate limits", "eva llm routing audit preview", "eva llm failure modes", "eva llm runaway protection"):
        result = maybe_handle_fast_command(command, ToolRegistry())
        assert_true(result is not None, f"command missing: {command}")
    print("verify_eva_llm_router_fallbacks_limits: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
