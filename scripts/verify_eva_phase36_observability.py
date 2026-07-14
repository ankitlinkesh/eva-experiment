from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    import backend.eva.observability.local_trace_store as local_trace_store
    from backend.eva.observability import context
    from backend.eva.tools.registry import ToolRegistry
    from scripts import verify_eva_all

    check(
        all(
            hasattr(context, name)
            for name in (
                "tracing_enabled",
                "task_trace",
                "get_current_trace_id",
                "trace_gate_decision",
                "trace_tool_call",
                "summarize_result",
            )
        ),
        "backend.eva.observability.context is missing one of the required exports",
    )

    env_had_key = "EVA_TRACING_ENABLED" in os.environ
    env_prior_value = os.environ.get("EVA_TRACING_ENABLED")
    original_root = local_trace_store.DEFAULT_TRACE_ROOT
    temp_root = Path(tempfile.mkdtemp(prefix="eva_phase36_traces_"))

    try:
        local_trace_store.DEFAULT_TRACE_ROOT = temp_root

        # --- OFF path: default-off, byte-identical, no trace files written ---
        os.environ.pop("EVA_TRACING_ENABLED", None)
        check(context.tracing_enabled() is False, "tracing must default to off")
        with context.task_trace("verify-off", "verify off goal") as trace_id:
            check(trace_id is None, "task_trace must yield None while tracing is off")
        check(context.get_current_trace_id() is None, "context var must stay unset while tracing is off")

        registry = ToolRegistry()
        result = registry.run("workspace_status")
        check(isinstance(result, dict), "workspace_status must still return its normal dict result while off")
        check(list(temp_root.glob("*.jsonl")) == [], "no jsonl trace files may be written while tracing is off")

        # --- ON path: allowed tool call produces a readable tool_call event ---
        os.environ["EVA_TRACING_ENABLED"] = "1"
        from backend.eva.observability import traces

        with context.task_trace("verify-on", "verify on goal") as trace_id:
            check(bool(trace_id), "task_trace must yield a truthy trace id while tracing is on")
            registry = ToolRegistry()
            status_result = registry.run("workspace_status")
            check(isinstance(status_result, dict), "workspace_status must return a dict while tracing is on")

        traced = traces.read_trace(trace_id)
        check(traced["found"] is True, "a traced run must be readable back from the store")
        events = traced["events"]
        check(
            any(
                event.get("type") == "tool_call" and event["payload"].get("tool_name") == "workspace_status"
                for event in events
            ),
            "traced run is missing a tool_call event for workspace_status",
        )

        # --- ON path: a gated tool records permission(override) but no tool_call ---
        with context.task_trace("verify-gated", "verify gated goal") as gated_trace_id:
            check(bool(gated_trace_id), "gated trace must also yield a truthy trace id")
            registry = ToolRegistry()
            gated_result = registry.run("screen.observe", reason="verifier-observation")
            check(gated_result.get("requires_confirmation") is True, "screen.observe must be gated, not executed directly")

        gated_trace = traces.read_trace(gated_trace_id)
        check(gated_trace["found"] is True, "gated trace must be readable back from the store")
        gated_events = gated_trace["events"]
        check(
            any(
                event.get("type") == "permission"
                and event["payload"].get("tool_name") == "screen.observe"
                and event["payload"].get("decision") == "override"
                for event in gated_events
            ),
            "gated trace is missing an override permission event for screen.observe",
        )
        check(
            not any(
                event.get("type") == "tool_call" and event["payload"].get("tool_name") == "screen.observe"
                for event in gated_events
            ),
            "gated trace must not contain a tool_call event for screen.observe (it was never invoked)",
        )
    finally:
        local_trace_store.DEFAULT_TRACE_ROOT = original_root
        if env_had_key:
            os.environ["EVA_TRACING_ENABLED"] = env_prior_value or ""
        else:
            os.environ.pop("EVA_TRACING_ENABLED", None)

    registry_source = (ROOT / "backend" / "eva" / "tools" / "registry.py").read_text(encoding="utf-8")
    check("trace_gate_decision" in registry_source, "registry.py must call trace_gate_decision")
    check("trace_tool_call" in registry_source, "registry.py must call trace_tool_call")

    verifier_name = "verify_eva_phase36_observability.py"
    check(verifier_name in verify_eva_all.FULL_VERIFIERS, "full profile is missing the Phase 36 observability verifier")
    check(verifier_name in verify_eva_all.QUICK_VERIFIERS, "quick profile is missing the Phase 36 observability verifier")
    check(hasattr(verify_eva_all, "VERIFIER_DESCRIPTORS"), "master verifier descriptors missing")
    descriptors = getattr(verify_eva_all, "VERIFIER_DESCRIPTORS")
    check(verifier_name in descriptors, "master verifier descriptor missing the Phase 36 observability verifier")

    print("PASS: Phase 36a observability tracing is default-off, fail-safe, and records permission/tool_call events through the real tool gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
