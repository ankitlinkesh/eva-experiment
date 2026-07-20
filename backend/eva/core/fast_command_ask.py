"""``eva ask`` natural-router command handling, split out of ``fast_commands.py``
in Phase 71 as a pure move -- no behavior changed.

This module owns ``_handle_eva_ask_command`` (routes a natural-language
request through ``authority``/``natural_router`` to one of ~200 read-only
status/policy/preview intents) plus every helper that exists only to serve
it: the authority-decision mapping, the capability/agent lookups, the
``_format_*_ask_response`` family that wraps each intent's body in the
"Eva ask" envelope, and three small intent-specific helpers.

Circular import note: ``fast_commands.py`` imports
``_authority_decision_from_natural_route`` and ``_handle_eva_ask_command``
from this module at top level (``maybe_handle_fast_command`` calls both
directly). This module, in turn, needs ``maybe_handle_fast_command`` for the
natural-router's "delegate to a suggested safe command" path -- that import
is deferred to call time (see inside ``_handle_eva_ask_command``) specifically
to avoid a module-level cycle; by the time it executes, ``fast_commands`` has
already finished importing this module.
"""
from __future__ import annotations

from .fast_command_helpers import _after_prefix
from ..tools.registry import ToolRegistry


def _handle_eva_ask_command(
    normalized: str,
    original: str,
    tools: ToolRegistry,
    session_context: dict | None,
    memory: object | None,
    session_id: str | None,
) -> tuple[str, str] | None:
    request = _after_prefix(original, ("eva ask ",))
    if not request:
        return None
    from ..authority.formatter import format_authority_decision
    from ..core.natural_router import NaturalRouteResult, route_natural_request

    route = route_natural_request(request)
    decision = _authority_decision_from_natural_route(route)
    if route.intent == "project_inspect":
        from ..skills.project_inspection import format_project_inspection

        return _format_eva_ask_response(route, decision, format_project_inspection()), "fast-command"
    if route.intent == "project_recent_changes":
        from ..skills.project_inspection import format_recent_project_changes

        return _format_eva_ask_response(route, decision, format_recent_project_changes()), "fast-command"
    if route.intent == "project_next_step":
        from ..skills.project_inspection import format_project_next_step

        return _format_eva_ask_response(route, decision, format_project_next_step()), "fast-command"
    if route.intent == "project_proof":
        from ..skills.reality_check import format_project_proof

        return _format_eva_ask_response(route, decision, format_project_proof()), "fast-command"
    if route.intent == "done_check":
        from ..skills.reality_check import format_done_check

        return _format_eva_ask_response(route, decision, format_done_check()), "fast-command"
    if route.intent == "project_broken_status":
        from ..skills.reality_check import format_broken_status

        return _format_eva_ask_response(route, decision, format_broken_status()), "fast-command"
    if route.intent in {"control_center_status", "locked_features", "enabled_features", "next_safe_step"}:
        if route.intent == "locked_features":
            from ..ai_os.formatter import format_ai_os_locked_features

            return _format_ai_os_ask_response(route, format_ai_os_locked_features()), "fast-command"
        if route.intent == "next_safe_step":
            from ..ai_os.formatter import format_ai_os_next_safe_step

            return _format_ai_os_ask_response(route, format_ai_os_next_safe_step()), "fast-command"
        from ..control_center.status import (
            format_control_center_summary_text,
            format_enabled_features_text,
            format_locked_features_text,
            format_next_safe_step_text,
        )

        body_map = {
            "control_center_status": format_control_center_summary_text,
            "locked_features": format_locked_features_text,
            "enabled_features": format_enabled_features_text,
            "next_safe_step": format_next_safe_step_text,
        }
        return _format_eva_ask_response(route, decision, body_map[route.intent]()), "fast-command"
    if route.intent in {"work_sessions_status", "audit_timeline", "latest_work_session"}:
        from ..work_sessions.status import format_audit_timeline, format_latest_work_session
        from ..work_sessions.formatter import format_work_sessions_status

        body_map = {
            "work_sessions_status": format_work_sessions_status,
            "audit_timeline": format_audit_timeline,
            "latest_work_session": format_latest_work_session,
        }
        return _format_eva_ask_response(route, decision, body_map[route.intent]()), "fast-command"
    if route.intent == "golden_workflow_status":
        from ..golden_workflows.status import format_golden_workflows_text

        return _format_eva_ask_response(route, decision, format_golden_workflows_text()), "fast-command"
    if route.intent in {"golden_workflow_test_plan", "golden_workflow_proof"}:
        from ..golden_workflows.status import format_golden_workflow_proof, format_golden_workflow_test_plan

        body = format_golden_workflow_proof() if route.intent == "golden_workflow_proof" else format_golden_workflow_test_plan()
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent in {"workflow_continue", "workflow_next_step"}:
        from ..skills.workflow_state import classify_next_fileagent_step, format_workflow_next_step

        body = format_workflow_next_step(classify_next_fileagent_step(request))
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent in {"phase12_verify_status", "phase12_status"}:
        from ..core.ux_messages import format_phase12_status, format_quick_status_summary

        body = format_quick_status_summary() if route.intent == "phase12_verify_status" else format_phase12_status()
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent in {"phase12_ready", "phase12_summary", "phase12_limits", "phase12_proof"}:
        from ..core.phase12_ready import format_phase12_limits, format_phase12_proof, format_phase12_ready, format_phase12_summary

        body_map = {
            "phase12_ready": format_phase12_ready,
            "phase12_summary": format_phase12_summary,
            "phase12_limits": format_phase12_limits,
            "phase12_proof": format_phase12_proof,
        }
        return _format_eva_ask_response(route, decision, body_map[route.intent]()), "fast-command"
    if route.intent in {"llm_status", "llm_providers", "llm_routing_policy", "llm_fallback_policy", "llm_limits", "llm_structured_output", "llm_readiness"}:
        from ..llm.formatter import format_llm_fallback_policy, format_llm_limits, format_llm_providers, format_llm_readiness, format_llm_routing_policy, format_llm_status, format_llm_structured_output

        body_map = {"llm_status": format_llm_status, "llm_providers": format_llm_providers, "llm_routing_policy": format_llm_routing_policy, "llm_fallback_policy": format_llm_fallback_policy, "llm_limits": format_llm_limits, "llm_structured_output": format_llm_structured_output, "llm_readiness": format_llm_readiness}
        return _format_eva_ask_response(route, decision, body_map[route.intent]()), "fast-command"
    if route.intent in {"llm_validation_status", "llm_validation_policy", "llm_validation_invalid_examples", "llm_validation_readiness"}:
        from ..llm.formatter import format_llm_validate_invalid_examples, format_llm_validation_policy, format_llm_validation_readiness, format_llm_validation_status

        body_map = {
            "llm_validation_status": format_llm_validation_status,
            "llm_validation_policy": format_llm_validation_policy,
            "llm_validation_invalid_examples": format_llm_validate_invalid_examples,
            "llm_validation_readiness": format_llm_validation_readiness,
        }
        return _format_llm_validation_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {"llm_red_team_status", "llm_red_team_run", "llm_failure_tests", "llm_safety_failure_report", "llm_red_team_readiness"}:
        from ..llm.formatter import format_llm_failure_tests, format_llm_red_team_readiness, format_llm_red_team_run, format_llm_red_team_status, format_llm_safety_failure_report
        body_map = {"llm_red_team_status": format_llm_red_team_status, "llm_red_team_run": format_llm_red_team_run, "llm_failure_tests": format_llm_failure_tests, "llm_safety_failure_report": format_llm_safety_failure_report, "llm_red_team_readiness": format_llm_red_team_readiness}
        return _format_llm_validation_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {"context_status", "context_policy", "context_budget", "context_assemble_preview", "context_grounding_report", "context_redaction_policy", "context_readiness"}:
        from ..context_engine.formatter import format_context_assemble_preview, format_context_budget, format_context_grounding_report, format_context_policy, format_context_readiness, format_context_redaction_policy, format_context_status
        body_map = {
            "context_status": format_context_status,
            "context_policy": format_context_policy,
            "context_budget": format_context_budget,
            "context_assemble_preview": format_context_assemble_preview,
            "context_grounding_report": format_context_grounding_report,
            "context_redaction_policy": format_context_redaction_policy,
            "context_readiness": format_context_readiness,
        }
        return _format_context_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {"threat_status", "threat_policy", "threat_scan_preview", "threat_exfiltration_examples", "threat_context_guard", "threat_readiness"}:
        from ..threat_defense.formatter import format_threat_context_guard, format_threat_exfiltration_examples, format_threat_policy, format_threat_readiness, format_threat_scan_preview, format_threat_status
        body_map = {
            "threat_status": format_threat_status,
            "threat_policy": format_threat_policy,
            "threat_scan_preview": format_threat_scan_preview,
            "threat_exfiltration_examples": format_threat_exfiltration_examples,
            "threat_context_guard": format_threat_context_guard,
            "threat_readiness": format_threat_readiness,
        }
        return _format_threat_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {"agent_loop_status", "agent_loop_policy", "agent_loop_run_preview", "agent_loop_safety_report", "agent_loop_stop_reasons", "agent_loop_action_previews", "agent_loop_readiness"}:
        from ..agent_loop.formatter import format_agent_loop_action_previews, format_agent_loop_policy, format_agent_loop_readiness, format_agent_loop_run_preview, format_agent_loop_safety_report, format_agent_loop_status, format_agent_loop_stop_reasons
        body_map = {
            "agent_loop_status": format_agent_loop_status,
            "agent_loop_policy": format_agent_loop_policy,
            "agent_loop_run_preview": format_agent_loop_run_preview,
            "agent_loop_safety_report": format_agent_loop_safety_report,
            "agent_loop_stop_reasons": format_agent_loop_stop_reasons,
            "agent_loop_action_previews": format_agent_loop_action_previews,
            "agent_loop_readiness": format_agent_loop_readiness,
        }
        return _format_agent_loop_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {"workflow_planner_status", "workflow_planner_policy", "workflow_planner_preview", "workflow_planner_dependencies", "workflow_planner_approvals", "workflow_planner_rollback", "workflow_planner_readiness"}:
        from ..workflow_planner.formatter import format_workflow_planner_approvals, format_workflow_planner_dependencies, format_workflow_planner_policy, format_workflow_planner_preview, format_workflow_planner_readiness, format_workflow_planner_rollback, format_workflow_planner_status
        body_map = {
            "workflow_planner_status": format_workflow_planner_status,
            "workflow_planner_policy": format_workflow_planner_policy,
            "workflow_planner_preview": format_workflow_planner_preview,
            "workflow_planner_dependencies": format_workflow_planner_dependencies,
            "workflow_planner_approvals": format_workflow_planner_approvals,
            "workflow_planner_rollback": format_workflow_planner_rollback,
            "workflow_planner_readiness": format_workflow_planner_readiness,
        }
        return _format_workflow_planner_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {"execution_gates_status", "execution_gates_policy", "execution_gates_blocked_actions", "execution_gates_approvals", "execution_gates_confirmations", "execution_gates_readiness"}:
        from ..execution_gates.formatter import (
            format_execution_gate_approvals,
            format_execution_gate_blocked_actions,
            format_execution_gate_confirmations,
            format_execution_gate_policy,
            format_execution_gate_readiness,
            format_execution_gate_status,
        )

        body_map = {
            "execution_gates_status": format_execution_gate_status,
            "execution_gates_policy": format_execution_gate_policy,
            "execution_gates_blocked_actions": format_execution_gate_blocked_actions,
            "execution_gates_approvals": format_execution_gate_approvals,
            "execution_gates_confirmations": format_execution_gate_confirmations,
            "execution_gates_readiness": format_execution_gate_readiness,
        }
        return _format_execution_gates_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {"ai_os_status", "ai_os_dashboard", "ai_os_system_map", "ai_os_capability_matrix", "ai_os_locked_features", "ai_os_next_safe_step", "ai_os_safety_boundaries", "ai_os_readiness"}:
        from ..ai_os.formatter import (
            format_ai_os_capability_matrix,
            format_ai_os_dashboard,
            format_ai_os_locked_features,
            format_ai_os_next_safe_step,
            format_ai_os_readiness,
            format_ai_os_safety_boundaries,
            format_ai_os_status,
            format_ai_os_system_map,
        )

        body_map = {
            "ai_os_status": format_ai_os_status,
            "ai_os_dashboard": format_ai_os_dashboard,
            "ai_os_system_map": format_ai_os_system_map,
            "ai_os_capability_matrix": format_ai_os_capability_matrix,
            "ai_os_locked_features": format_ai_os_locked_features,
            "ai_os_next_safe_step": format_ai_os_next_safe_step,
            "ai_os_safety_boundaries": format_ai_os_safety_boundaries,
            "ai_os_readiness": format_ai_os_readiness,
        }
        return _format_ai_os_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {"voice_status", "voice_policy", "voice_providers", "voice_listen_state", "voice_transcript_safety", "voice_confirmations", "voice_readiness"}:
        from ..voice_assistant.formatter import (
            format_voice_confirmations,
            format_voice_listen_state,
            format_voice_policy,
            format_voice_providers,
            format_voice_readiness,
            format_voice_status,
            format_voice_transcript_safety,
        )

        body_map = {
            "voice_status": format_voice_status,
            "voice_policy": format_voice_policy,
            "voice_providers": format_voice_providers,
            "voice_listen_state": format_voice_listen_state,
            "voice_transcript_safety": format_voice_transcript_safety,
            "voice_confirmations": format_voice_confirmations,
            "voice_readiness": format_voice_readiness,
        }
        return _format_voice_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {"memory_v3_status", "memory_v3_policy", "memory_v3_privacy", "memory_v3_freshness", "memory_v3_conflicts", "memory_v3_retrieval_preview", "memory_v3_readiness"}:
        from ..memory_v3.formatter import (
            format_memory_v3_conflicts,
            format_memory_v3_freshness,
            format_memory_v3_policy,
            format_memory_v3_privacy,
            format_memory_v3_readiness,
            format_memory_v3_retrieval_preview,
            format_memory_v3_status,
        )

        body_map = {
            "memory_v3_status": format_memory_v3_status,
            "memory_v3_policy": format_memory_v3_policy,
            "memory_v3_privacy": format_memory_v3_privacy,
            "memory_v3_freshness": format_memory_v3_freshness,
            "memory_v3_conflicts": format_memory_v3_conflicts,
            "memory_v3_retrieval_preview": format_memory_v3_retrieval_preview,
            "memory_v3_readiness": format_memory_v3_readiness,
        }
        return _format_memory_v3_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {
        "browser_read_status",
        "browser_read_policy",
        "browser_read_boundaries",
        "browser_read_observe",
        "browser_read_session_boundary",
        "browser_read_blocked_urls",
        "browser_read_readiness",
    }:
        from ..browser_readonly.formatter import (
            format_browser_read_blocked_urls,
            format_browser_read_observe,
            format_browser_read_policy,
            format_browser_read_readiness,
            format_browser_read_status,
        )

        body_map = {
            "browser_read_status": format_browser_read_status,
            "browser_read_policy": format_browser_read_policy,
            "browser_read_boundaries": format_browser_read_policy,
            "browser_read_observe": format_browser_read_observe,
            "browser_read_session_boundary": format_browser_read_policy,
            "browser_read_blocked_urls": format_browser_read_blocked_urls,
            "browser_read_readiness": format_browser_read_readiness,
        }
        return _format_browser_read_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {
        "news_status", "news_policy", "news_dashboard", "news_sources", "news_freshness", "news_readiness",
    }:
        from ..news_dashboard.formatter import format_news_dashboard, format_news_freshness, format_news_policy, format_news_readiness, format_news_sources, format_news_status
        body = {"news_status":format_news_status,"news_policy":format_news_policy,"news_dashboard":format_news_dashboard,"news_sources":format_news_sources,"news_freshness":format_news_freshness,"news_readiness":format_news_readiness}[route.intent]()
        return "Eva ask\n\n" + body, "fast-command"
    if route.intent in {
        "coding_status",
        "coding_policy",
        "coding_patch_plan",
        "coding_review_checklist",
        "coding_test_plan",
        "coding_risk_review",
        "coding_handoff",
        "coding_readiness",
    }:
        from ..coding_agent.formatter import (
            format_coding_handoff,
            format_coding_patch_plan,
            format_coding_policy,
            format_coding_readiness,
            format_coding_review_checklist,
            format_coding_risk_review,
            format_coding_status,
            format_coding_test_plan,
        )

        body_map = {
            "coding_status": format_coding_status,
            "coding_policy": format_coding_policy,
            "coding_patch_plan": format_coding_patch_plan,
            "coding_review_checklist": format_coding_review_checklist,
            "coding_test_plan": format_coding_test_plan,
            "coding_risk_review": format_coding_risk_review,
            "coding_handoff": format_coding_handoff,
            "coding_readiness": format_coding_readiness,
        }
        return "Eva ask\n\n" + body_map[route.intent](), "fast-command"
    if route.intent in {
        "rc_status",
        "rc_manifest",
        "rc_commit_plan",
        "rc_hardening_report",
        "rc_checklist",
        "rc_readiness",
        "rc_verification",
    }:
        from ..release_candidate.formatter import (
            format_rc_checklist,
            format_rc_commit_plan,
            format_rc_hardening_report,
            format_rc_manifest,
            format_rc_readiness,
            format_rc_status,
            format_rc_verification,
        )

        body_map = {
            "rc_status": format_rc_status,
            "rc_manifest": format_rc_manifest,
            "rc_commit_plan": format_rc_commit_plan,
            "rc_hardening_report": format_rc_hardening_report,
            "rc_checklist": format_rc_checklist,
            "rc_readiness": format_rc_readiness,
            "rc_verification": format_rc_verification,
        }
        return "Eva ask\n\n" + body_map[route.intent](), "fast-command"
    if route.intent in {
        "release_status",
        "release_demo",
        "release_commands",
        "release_capability_map",
        "release_safety_proof",
        "release_readiness",
        "release_limitations",
        "release_demo_smoke",
        "release_post_push_sync",
    }:
        from ..release_demo.formatter import (
            format_release_capability_map,
            format_release_commands,
            format_release_demo,
            format_release_demo_smoke,
            format_release_limitations,
            format_release_post_push_sync,
            format_release_readiness,
            format_release_safety_proof,
            format_release_status,
        )

        body_map = {
            "release_status": format_release_status,
            "release_demo": format_release_demo,
            "release_commands": format_release_commands,
            "release_capability_map": format_release_capability_map,
            "release_safety_proof": format_release_safety_proof,
            "release_readiness": format_release_readiness,
            "release_limitations": format_release_limitations,
            "release_demo_smoke": format_release_demo_smoke,
            "release_post_push_sync": format_release_post_push_sync,
        }
        return "Eva ask\n\n" + body_map[route.intent](), "fast-command"
    if route.intent in {
        "desktop_control_status",
        "desktop_control_policy",
        "desktop_control_dry_run",
        "desktop_control_approvals",
        "desktop_control_blocked_actions",
        "desktop_control_readiness",
    }:
        from ..desktop_control_gate.formatter import (
            format_desktop_control_approvals,
            format_desktop_control_blocked_actions,
            format_desktop_control_dry_run,
            format_desktop_control_policy,
            format_desktop_control_readiness,
            format_desktop_control_status,
        )

        body_map = {
            "desktop_control_status": format_desktop_control_status,
            "desktop_control_policy": format_desktop_control_policy,
            "desktop_control_dry_run": format_desktop_control_dry_run,
            "desktop_control_approvals": format_desktop_control_approvals,
            "desktop_control_blocked_actions": format_desktop_control_blocked_actions,
            "desktop_control_readiness": format_desktop_control_readiness,
        }
        return "Eva ask\n\n" + body_map[route.intent](), "fast-command"
    if route.intent in {
        "desktop_observe_status",
        "desktop_observe_policy",
        "desktop_observe_boundaries",
        "desktop_observe_sensitive_screens",
        "desktop_observe_mock",
        "desktop_observe_readiness",
    }:
        from ..desktop_observation.formatter import (
            format_desktop_observe_mock,
            format_desktop_observe_policy,
            format_desktop_observe_readiness,
            format_desktop_observe_sensitive_screens,
            format_desktop_observe_status,
        )

        body_map = {
            "desktop_observe_status": format_desktop_observe_status,
            "desktop_observe_policy": format_desktop_observe_policy,
            "desktop_observe_boundaries": format_desktop_observe_policy,
            "desktop_observe_sensitive_screens": format_desktop_observe_sensitive_screens,
            "desktop_observe_mock": format_desktop_observe_mock,
            "desktop_observe_readiness": format_desktop_observe_readiness,
        }
        return _format_desktop_observe_ask_response(route, body_map[route.intent]()), "fast-command"
    if route.intent in {"desktop_status", "desktop_policy", "desktop_blocked_actions", "desktop_action_safety", "desktop_app_risk", "desktop_readiness", "desktop_session_status", "desktop_session_preview", "desktop_session_plan", "desktop_window_status_preview", "desktop_active_context_preview", "desktop_observation_readiness", "desktop_screen_policy", "desktop_screen_observation_policy", "desktop_sensitive_screens", "desktop_screen_redaction_policy", "desktop_screen_capture_gate", "desktop_screen_readiness", "desktop_action_dry_run", "desktop_action_plan_preview", "desktop_action_risk", "desktop_action_approvals", "desktop_dry_run_policy", "desktop_action_readiness", "desktop_risk_score", "desktop_risk_factors", "desktop_approval_required", "desktop_safety_matrix", "desktop_high_risk_actions", "desktop_risk_readiness", "desktop_approval_policy", "desktop_approval_levels", "desktop_approval_preview", "desktop_confirmation_phrase", "desktop_forbidden_actions", "desktop_approval_audit_status", "desktop_approval_readiness", "desktop_phase14_status", "desktop_phase14_summary", "desktop_phase14_limits", "desktop_phase14_ready", "desktop_phase14_final_proof", "desktop_readiness_proof", "desktop_locked_status", "desktop_readiness_gaps"}:
        from ..desktop_agent.formatter import (
            format_desktop_active_context_preview,
            format_desktop_approval_audit_status,
            format_desktop_approval_levels,
            format_desktop_approval_model_preview,
            format_desktop_approval_model_readiness,
            format_desktop_approval_policy,
            format_desktop_approval_required,
            format_desktop_action_approvals,
            format_desktop_action_dry_run,
            format_desktop_action_plan,
            format_desktop_action_readiness,
            format_desktop_action_risk,
            format_desktop_action_safety,
            format_desktop_app_risk,
            format_desktop_blocked_actions,
            format_desktop_dry_run_policy,
            format_desktop_observation_readiness,
            format_desktop_policy,
            format_desktop_readiness,
            format_desktop_screen_capture_gate,
            format_desktop_screen_observation_policy,
            format_desktop_screen_policy,
            format_desktop_screen_readiness,
            format_desktop_screen_redaction_policy,
            format_desktop_session_plan,
            format_desktop_session_preview,
            format_desktop_session_status,
            format_desktop_sensitive_screens,
            format_desktop_status,
            format_desktop_window_status_preview,
            format_desktop_high_risk_actions,
            format_desktop_risk_factors,
            format_desktop_risk_readiness,
            format_desktop_risk_score,
            format_desktop_safety_matrix,
            format_desktop_confirmation_phrase,
            format_desktop_forbidden_actions,
            format_desktop_locked_status,
            format_desktop_phase14_final_proof,
            format_desktop_phase14_limits,
            format_desktop_phase14_ready,
            format_desktop_phase14_status,
            format_desktop_phase14_summary,
            format_desktop_readiness_gaps,
            format_desktop_readiness_proof,
        )

        if route.intent == "desktop_phase14_status":
            body = format_desktop_phase14_status()
        elif route.intent == "desktop_phase14_summary":
            body = format_desktop_phase14_summary()
        elif route.intent == "desktop_phase14_limits":
            body = format_desktop_phase14_limits()
        elif route.intent == "desktop_phase14_ready":
            body = format_desktop_phase14_ready()
        elif route.intent == "desktop_phase14_final_proof":
            body = format_desktop_phase14_final_proof()
        elif route.intent == "desktop_readiness_proof":
            body = format_desktop_readiness_proof()
        elif route.intent == "desktop_locked_status":
            body = format_desktop_locked_status()
        elif route.intent == "desktop_readiness_gaps":
            body = format_desktop_readiness_gaps()
        elif route.intent == "desktop_policy":
            body = format_desktop_policy()
        elif route.intent == "desktop_blocked_actions":
            body = format_desktop_blocked_actions()
        elif route.intent == "desktop_action_safety":
            body = format_desktop_action_safety(str(route.suggested_command or "").removeprefix("eva desktop action safety ").strip() or "unknown")
        elif route.intent == "desktop_action_dry_run":
            body = format_desktop_action_dry_run(request)
        elif route.intent == "desktop_action_plan_preview":
            body = format_desktop_action_plan(request)
        elif route.intent == "desktop_action_risk":
            body = format_desktop_action_risk(str(route.suggested_command or "").removeprefix("eva desktop action risk ").strip() or "unknown")
        elif route.intent == "desktop_action_approvals":
            body = format_desktop_action_approvals()
        elif route.intent == "desktop_dry_run_policy":
            body = format_desktop_dry_run_policy()
        elif route.intent == "desktop_action_readiness":
            body = format_desktop_action_readiness()
        elif route.intent == "desktop_risk_score":
            body = format_desktop_risk_score(request)
        elif route.intent == "desktop_risk_factors":
            body = format_desktop_risk_factors(request)
        elif route.intent == "desktop_approval_required":
            body = format_desktop_approval_required(request)
        elif route.intent == "desktop_approval_policy":
            body = format_desktop_approval_policy()
        elif route.intent == "desktop_approval_levels":
            body = format_desktop_approval_levels()
        elif route.intent == "desktop_approval_preview":
            body = format_desktop_approval_model_preview(request)
        elif route.intent == "desktop_confirmation_phrase":
            body = format_desktop_confirmation_phrase(request)
        elif route.intent == "desktop_forbidden_actions":
            body = format_desktop_forbidden_actions()
        elif route.intent == "desktop_approval_audit_status":
            body = format_desktop_approval_audit_status()
        elif route.intent == "desktop_approval_readiness":
            body = format_desktop_approval_model_readiness()
        elif route.intent == "desktop_safety_matrix":
            body = format_desktop_safety_matrix()
        elif route.intent == "desktop_high_risk_actions":
            body = format_desktop_high_risk_actions()
        elif route.intent == "desktop_risk_readiness":
            body = format_desktop_risk_readiness()
        elif route.intent == "desktop_app_risk":
            body = format_desktop_app_risk(str(route.suggested_command or "").removeprefix("eva desktop app risk ").strip() or "unknown")
        elif route.intent == "desktop_readiness":
            body = format_desktop_readiness()
        elif route.intent == "desktop_session_status":
            body = format_desktop_session_status()
        elif route.intent == "desktop_session_preview":
            body = format_desktop_session_preview("Natural desktop session request")
        elif route.intent == "desktop_session_plan":
            body = format_desktop_session_plan()
        elif route.intent == "desktop_window_status_preview":
            body = format_desktop_window_status_preview()
        elif route.intent == "desktop_active_context_preview":
            body = format_desktop_active_context_preview()
        elif route.intent == "desktop_observation_readiness":
            body = format_desktop_observation_readiness()
        elif route.intent == "desktop_screen_policy":
            body = format_desktop_screen_policy()
        elif route.intent == "desktop_screen_observation_policy":
            body = format_desktop_screen_observation_policy()
        elif route.intent == "desktop_sensitive_screens":
            body = format_desktop_sensitive_screens()
        elif route.intent == "desktop_screen_redaction_policy":
            body = format_desktop_screen_redaction_policy()
        elif route.intent == "desktop_screen_capture_gate":
            body = format_desktop_screen_capture_gate()
        elif route.intent == "desktop_screen_readiness":
            body = format_desktop_screen_readiness()
        else:
            body = format_desktop_status()
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent in {"browser_status", "browser_policy", "browser_action_safety", "browser_session_status", "browser_session_preview", "browser_session_plan", "browser_session_readiness", "browser_page_summary_policy", "browser_page_summary_preview", "browser_dom_summary_policy", "browser_observation_readiness", "browser_action_dry_run", "browser_action_plan_preview", "browser_action_risk", "browser_action_approvals", "browser_dry_run_policy", "browser_domain_check", "browser_site_risk", "browser_sensitive_sites", "browser_domain_rules", "browser_domain_approvals", "browser_readonly_readiness", "browser_readiness_proof", "browser_safety_proof", "browser_readiness_gaps", "browser_locked_status", "browser_phase13_proof", "browser_phase13_status", "browser_phase13_summary", "browser_phase13_limits", "browser_phase13_ready", "browser_phase13_final_proof"}:
        from ..browser_agent.formatter import (
            format_browser_action_safety,
            format_browser_action_approvals,
            format_browser_action_dry_run,
            format_browser_action_plan,
            format_browser_action_risk,
            format_browser_locked_status,
            format_browser_domain_approvals,
            format_browser_domain_check,
            format_browser_domain_rules,
            format_browser_dom_summary_policy,
            format_browser_dry_run_policy,
            format_browser_observation_readiness,
            format_browser_page_summary_policy,
            format_browser_page_summary_preview,
            format_browser_phase13_final_proof,
            format_browser_phase13_limits,
            format_browser_phase13_proof,
            format_browser_phase13_ready,
            format_browser_phase13_status,
            format_browser_phase13_summary,
            format_browser_policy,
            format_browser_readiness,
            format_browser_readiness_gaps,
            format_browser_readiness_proof,
            format_browser_read_only_readiness,
            format_browser_safety_proof,
            format_browser_session_plan,
            format_browser_session_preview,
            format_browser_session_status,
            format_browser_sensitive_sites,
            format_browser_site_risk,
            format_browser_status,
        )

        if route.intent == "browser_policy":
            body = format_browser_policy()
        elif route.intent == "browser_action_safety":
            action = str(route.suggested_command or "").removeprefix("eva browser action safety ").strip() or request
            body = format_browser_action_safety(action)
        elif route.intent == "browser_session_status":
            body = format_browser_session_status()
        elif route.intent == "browser_session_preview":
            body = format_browser_session_preview("Natural browser session request")
        elif route.intent == "browser_session_plan":
            body = format_browser_session_plan()
        elif route.intent == "browser_session_readiness":
            body = format_browser_readiness()
        elif route.intent == "browser_page_summary_policy":
            body = format_browser_page_summary_policy()
        elif route.intent == "browser_page_summary_preview":
            body = format_browser_page_summary_preview()
        elif route.intent == "browser_dom_summary_policy":
            body = format_browser_dom_summary_policy()
        elif route.intent == "browser_observation_readiness":
            body = format_browser_observation_readiness()
        elif route.intent == "browser_action_dry_run":
            body = format_browser_action_dry_run(request)
        elif route.intent == "browser_action_plan_preview":
            body = format_browser_action_plan(request)
        elif route.intent == "browser_action_risk":
            action = str(route.suggested_command or "").removeprefix("eva browser action risk ").strip() or request
            body = format_browser_action_risk(action)
        elif route.intent == "browser_action_approvals":
            body = format_browser_action_approvals()
        elif route.intent == "browser_dry_run_policy":
            body = format_browser_dry_run_policy()
        elif route.intent == "browser_domain_check":
            domain = str(route.suggested_command or "").removeprefix("eva browser domain check ").strip() or request
            body = format_browser_domain_check(domain)
        elif route.intent == "browser_site_risk":
            domain = str(route.suggested_command or "").removeprefix("eva browser site risk ").strip() or request
            body = format_browser_site_risk(domain)
        elif route.intent == "browser_sensitive_sites":
            body = format_browser_sensitive_sites()
        elif route.intent == "browser_domain_rules":
            body = format_browser_domain_rules()
        elif route.intent == "browser_domain_approvals":
            body = format_browser_domain_approvals()
        elif route.intent == "browser_readonly_readiness":
            body = format_browser_read_only_readiness()
        elif route.intent == "browser_readiness_proof":
            body = format_browser_readiness_proof()
        elif route.intent == "browser_safety_proof":
            body = format_browser_safety_proof()
        elif route.intent == "browser_readiness_gaps":
            body = format_browser_readiness_gaps()
        elif route.intent == "browser_locked_status":
            body = format_browser_locked_status()
        elif route.intent == "browser_phase13_proof":
            body = format_browser_phase13_proof()
        elif route.intent == "browser_phase13_status":
            body = format_browser_phase13_status()
        elif route.intent == "browser_phase13_summary":
            body = format_browser_phase13_summary()
        elif route.intent == "browser_phase13_limits":
            body = format_browser_phase13_limits()
        elif route.intent == "browser_phase13_ready":
            body = format_browser_phase13_ready()
        elif route.intent == "browser_phase13_final_proof":
            body = format_browser_phase13_final_proof()
        else:
            body = format_browser_status()
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent == "verification_before_completion":
        from ..core.ux_messages import format_phase12_status
        from ..skills.workflow_state import format_workflow_state_summary, summarize_fileagent_workflow_state

        body = "\n\n".join(
            [
                "Evidence check",
                "I can summarize the current local verification and workflow evidence, but I should not claim completion without fresh verifier output.",
                format_phase12_status(),
                format_workflow_state_summary(summarize_fileagent_workflow_state()),
                "Remaining limitations: broad file edits, source edits, browser/desktop control, shell execution, MCP, cloud calls, and normal-chat v2 routing remain locked.",
            ]
        )
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent == "golden_project_note_create":
        if _should_show_skill_workflow_plan(request):
            from ..skills.workflows import format_fileagent_project_note_workflow

            body = format_fileagent_project_note_workflow(request)
            return _format_eva_ask_response(route, decision, body), "fast-command"
        from ..golden_workflows.formatter import format_golden_workflow_result
        from ..golden_workflows.runner import start_safe_project_note_workflow

        body = format_golden_workflow_result(start_safe_project_note_workflow(request))
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent == "golden_workflow_continue":
        from ..golden_workflows.formatter import format_golden_workflow_result
        from ..golden_workflows.runner import continue_safe_project_note_workflow

        body = format_golden_workflow_result(continue_safe_project_note_workflow(request))
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent == "capability_status" and route.suggested_command == "eva capabilities safe":
        from ..capabilities.registry import format_capability_summary
        from ..authority.status import format_authority_status

        body = "\n\n".join(
            [
                "Eva safe actions right now",
                format_authority_status(),
                format_capability_summary(safe_only=True),
            ]
        )
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent in {"approval_sandbox_apply", "approval_sandbox_verify", "approval_sandbox_rollback"} and not route.suggested_command:
        resolved = _resolve_single_approved_file_approval(route.intent)
        if not resolved:
            body = (
                "I found no single approved sandbox-eligible FileAgent approval to use.\n"
                "Run `eva file approvals pending` or specify an approval id like `fap_...`."
            )
            return _format_eva_ask_response(route, decision, body), "fast-command"
        route = NaturalRouteResult(**{**route.as_dict(), "suggested_command": resolved, "routed_to": resolved})
    if route.intent == "real_create_request" and not route.suggested_command:
        body = _format_real_create_next_step()
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent == "real_create_request":
        from ..skills.workflow_state import classify_next_fileagent_step, format_workflow_next_step

        body = format_workflow_next_step(classify_next_fileagent_step(request))
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent == "real_apply_policy":
        from ..file_agent.real_apply import format_real_apply_policy

        return _format_eva_ask_response(route, decision, format_real_apply_policy()), "fast-command"
    if route.intent == "real_create_verify_latest":
        from ..skills.workflow_state import classify_next_fileagent_step, format_workflow_next_step

        body = format_workflow_next_step(classify_next_fileagent_step("verify latest real create"))
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent == "real_create_rollback_latest":
        from ..skills.workflow_state import classify_next_fileagent_step, format_workflow_next_step

        body = format_workflow_next_step(classify_next_fileagent_step("rollback latest real create"))
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.intent == "real_create_rollback_request" and not route.suggested_command:
        body = "Specify the approval id and exact phrase: `eva ask confirm rollback real create <approval_id>`."
        return _format_eva_ask_response(route, decision, body), "fast-command"
    if route.refusal_reason:
        return _format_eva_ask_response(route, decision, route.refusal_reason), "fast-command"
    if route.suggested_command:
        # Lazy/local import: fast_commands.py imports THIS module at top level
        # (for _authority_decision_from_natural_route and _handle_eva_ask_command),
        # so importing maybe_handle_fast_command back at module level here would
        # be circular. Deferring it to call time -- matching this file's existing
        # heavy use of local imports -- resolves it: by the time this line runs,
        # fast_commands has already finished importing this module.
        from .fast_commands import maybe_handle_fast_command

        delegated = maybe_handle_fast_command(route.suggested_command, tools, session_context=session_context, memory=memory, session_id=session_id)
        body = delegated[0] if delegated else f"Suggested safe command: `{route.suggested_command}`"
        return _format_eva_ask_response(route, decision, body), "fast-command"
    body = "I understood the request, but I need a more specific safe command before doing anything."
    return _format_eva_ask_response(route, decision, body), "fast-command"


def _authority_decision_from_natural_route(route: object) -> object:
    from ..authority.decision import (
        allow_approval_decision,
        allow_draft_decision,
        allow_preview_decision,
        allow_readonly_decision,
        allow_sandbox_decision,
        block_real_execution_decision,
        refuse_authority_decision,
    )

    category = str(getattr(route, "authority_category", "unknown"))
    intent = str(getattr(route, "intent", "unknown"))
    suggested = getattr(route, "suggested_command", None)
    capability = _capability_for_natural_intent(intent)
    reason = f"Natural router interpreted this as `{intent}`."
    if getattr(route, "refusal_reason", None):
        if category in {"destructive", "external_send", "terminal", "browser_action", "desktop_control", "system_change", "local_write"}:
            return refuse_authority_decision(action_type=intent, action_category=category, capability_id=capability, reason=reason, blocked_reason=str(getattr(route, "refusal_reason")))
        return block_real_execution_decision(action_type=intent, action_category=category, capability_id=capability, reason=reason, blocked_reason=str(getattr(route, "refusal_reason")))
    if category == "read":
        return allow_readonly_decision(action_type=intent, action_category="read", capability_id=capability, agent_name=_agent_for_capability(capability), reason=reason)
    if category == "draft":
        return allow_draft_decision(action_type=intent, action_category="draft", capability_id=capability, agent_name="FileAgent", reason=reason)
    if category == "golden_workflow":
        return allow_sandbox_decision(action_type=intent, action_category="golden_workflow", capability_id=capability, agent_name="FileAgent", reason=reason, requires_approval=True, public_mode_allowed=False)
    if category == "approve":
        return allow_approval_decision(action_type=intent, action_category="approve", capability_id=capability, agent_name="FileAgent", reason=reason, public_mode_allowed=False)
    if category in {"sandbox_apply", "verify", "rollback"}:
        return allow_sandbox_decision(action_type=intent, action_category=category, capability_id=capability, agent_name="FileAgent", reason=reason, requires_approval=True, public_mode_allowed=False)
    if category == "real_create_safe_text":
        return block_real_execution_decision(action_type=intent, action_category="local_write", capability_id=capability, agent_name="FileAgent", reason=reason, blocked_reason="Exact approval confirmation is required before narrow real create-new-text-file.", public_mode_allowed=False, risk_level="high")
    if category == "rollback_real_create":
        return block_real_execution_decision(action_type=intent, action_category="local_write", capability_id=capability, agent_name="FileAgent", reason=reason, blocked_reason="Exact rollback confirmation is required before removing an Eva-created file.", public_mode_allowed=False, risk_level="medium")
    if suggested:
        return allow_preview_decision(action_type=intent, action_category="plan", capability_id=capability, reason=reason)
    return refuse_authority_decision(action_type=intent, action_category="unknown", capability_id=capability, reason=reason, blocked_reason="No safe route was selected.")


def _capability_for_natural_intent(intent: str) -> str | None:
    mapping = {
        "project_inspect": "eva.project_inspect",
        "project_recent_changes": "eva.project_recent_changes",
        "project_next_step": "eva.project_next_step",
        "project_proof": "eva.project_proof",
        "done_check": "eva.done_check",
        "project_broken_status": "eva.project_reality_check",
        "control_center_status": "eva.control_center_status",
        "work_sessions_status": "eva.work_sessions_status",
        "audit_timeline": "eva.audit_timeline",
        "latest_work_session": "eva.latest_work_session",
        "locked_features": "eva.locked_features",
        "enabled_features": "eva.enabled_features",
        "next_safe_step": "eva.next_safe_step",
        "file_inspect": "file.preview_text",
        "file_understand": "file.understand_text",
        "file_draft": "file.draft_readme_section",
        "file_apply_readiness": "file.apply_readiness",
        "approval_status": "file.approval_status",
        "approval_pending": "file.approval_list_pending",
        "approval_request": "file.approval_request_create",
        "approval_sandbox_apply": "file.sandbox_apply_approved",
        "approval_sandbox_verify": "file.sandbox_verify_apply",
        "approval_sandbox_rollback": "file.sandbox_rollback_apply",
        "capability_status": "eva.ask",
        "agent_status": "eva.ask",
        "planner_status": "eva.ask",
        "research_memory_status": "research_memory.status",
        "safety_status": "eva.authority_status",
        "control_center_dashboard": "eva.control_center_status",
        "golden_workflow_status": "eva.golden_workflows_status",
        "golden_workflow_test_plan": "eva.golden_workflow_test_plan",
        "golden_workflow_proof": "eva.golden_workflow_proof",
        "golden_project_note_create": "eva.golden_workflow_project_note",
        "golden_workflow_continue": "eva.golden_workflow_continue",
        "workflow_continue": "eva.workflow_next_step",
        "workflow_next_step": "eva.workflow_next_step",
        "phase12_verify_status": "eva.smoke_status",
        "phase12_status": "eva.phase12_status",
        "phase12_ready": "eva.phase12_ready",
        "phase12_summary": "eva.phase12_summary",
        "phase12_limits": "eva.phase12_limits",
        "phase12_proof": "eva.phase12_proof",
        "browser_read_status": "browser_read.status",
        "browser_read_policy": "browser_read.policy",
        "browser_read_boundaries": "browser_read.policy",
        "browser_read_observe": "browser_read.observe",
        "browser_read_session_boundary": "browser_read.policy",
        "browser_read_blocked_urls": "browser_read.blocked_urls",
        "browser_read_readiness": "browser_read.readiness",
        "desktop_observe_status": "desktop_observe.status",
        "desktop_observe_policy": "desktop_observe.policy",
        "desktop_observe_boundaries": "desktop_observe.policy",
        "desktop_observe_sensitive_screens": "desktop_observe.sensitive_screens",
        "desktop_observe_mock": "desktop_observe.mock",
        "desktop_observe_readiness": "desktop_observe.readiness",
        "desktop_control_status": "desktop_control.status",
        "desktop_control_policy": "desktop_control.policy",
        "desktop_control_dry_run": "desktop_control.dry_run",
        "desktop_control_approvals": "desktop_control.approvals",
        "desktop_control_blocked_actions": "desktop_control.blocked_actions",
        "desktop_control_readiness": "desktop_control.readiness",
        "news_status": "news.status", "news_policy": "news.policy", "news_dashboard": "news.dashboard",
        "news_sources": "news.sources", "news_freshness": "news.freshness", "news_readiness": "news.readiness",
        "coding_status": "coding.status",
        "coding_policy": "coding.policy",
        "coding_patch_plan": "coding.patch_plan",
        "coding_review_checklist": "coding.review_checklist",
        "coding_test_plan": "coding.test_plan",
        "coding_risk_review": "coding.risk_review",
        "coding_handoff": "coding.handoff",
        "coding_readiness": "coding.readiness",
        "rc_status": "rc.status",
        "rc_manifest": "rc.manifest",
        "rc_commit_plan": "rc.commit_plan",
        "rc_hardening_report": "rc.hardening_report",
        "rc_checklist": "rc.checklist",
        "rc_readiness": "rc.readiness",
        "rc_verification": "rc.verification",
        "release_status": "release.status",
        "release_demo": "release.demo",
        "release_commands": "release.commands",
        "release_capability_map": "release.capability_map",
        "release_safety_proof": "release.safety_proof",
        "release_readiness": "release.readiness",
        "release_limitations": "release.limitations",
        "release_demo_smoke": "release.demo_smoke",
        "release_post_push_sync": "release.post_push_sync",
        "verification_before_completion": "eva.workflow_plan",
        "real_apply_policy": "file.real_apply_policy",
        "real_create_request": "file.real_create_new_text_file",
        "real_create_confirm": "file.real_create_new_text_file",
        "real_create_verify": "file.real_verify_new_text_file",
        "real_create_verify_latest": "eva.file_latest_status",
        "real_create_rollback_request": "file.real_rollback_new_text_file",
        "real_create_rollback_latest": "eva.file_latest_status",
        "real_create_rollback_confirm": "file.real_rollback_new_text_file",
    }
    return mapping.get(intent)


def _agent_for_capability(capability_id: str | None) -> str | None:
    if not capability_id:
        return None
    if capability_id.startswith("file."):
        return "FileAgent"
    if capability_id.startswith("research_memory."):
        return "ResearchAgent"
    return "PlannerAgent"


def _format_eva_ask_response(route: object, decision: object, body: str) -> str:
    from ..authority.formatter import format_authority_decision
    from ..core.ux_messages import format_safe_next_step, format_understood_request
    from ..skills.selector import select_skills_for_request, select_workflow_for_request
    from ..specialists.selector import select_specialists_for_request

    intent = str(getattr(route, "intent", "unknown"))
    mode = str(getattr(decision, "mode", "preview"))
    allowed = bool(getattr(decision, "allowed", False))
    sandbox_only = bool(getattr(decision, "sandbox_only", False))
    request_text = str(getattr(route, "original_text", ""))
    specialists = select_specialists_for_request(request_text)
    skills = select_skills_for_request(request_text)
    workflow = select_workflow_for_request(request_text)
    if not allowed:
        next_step = "Use a safe read-only status, preview, or exact confirmation command. Nothing was executed."
    elif sandbox_only:
        next_step = "Review the sandbox or approval output before any exact confirmation step."
    elif mode in {"read_only", "preview_only", "draft_only", "approval_only"}:
        next_step = "Review the result below. No real file, browser, desktop, shell, or external action was executed."
    else:
        next_step = "Review the result below before taking any manual action."
    work_session_id = ""
    try:
        from ..work_sessions.timeline import finalize_work_session, record_eva_ask_work_session

        work_session_id = record_eva_ask_work_session(
            request_text=request_text,
            route=route,
            decision=decision,
            specialists=specialists,
            skills=skills,
            workflow=workflow,
            next_safe_step=next_step,
        )
        finalize_work_session(work_session_id, body)
    except Exception:
        work_session_id = "unavailable"
    return "\n".join(
        [
            "Eva ask",
            "",
            format_understood_request(intent, f"Intent `{intent}` routed to `{getattr(route, 'routed_to', 'authority_preview')}`."),
            "",
            f"Work session: {work_session_id}",
            f"Request: {getattr(route, 'original_text', '')}",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            f"Confidence: {float(getattr(route, 'confidence', 0.0)):.2f}",
            "",
            format_authority_decision(decision),
            "",
            "Specialist route:",
            ", ".join(item.id for item in specialists[:4]) if specialists else "none",
            "Skill route:",
            ", ".join(item.id for item in skills[:4]) if skills else "none",
            "Workflow route:",
            workflow.id if workflow else "none",
            "",
            format_safe_next_step(next_step),
            "",
            "Result:",
            body,
        ]
    )


def _format_llm_validation_ask_response(route: object, body: str) -> str:
    """Render local validation status without creating a work-session record."""
    return "\n".join(
        [
            "Eva ask",
            "",
            "Request: structured-output validation status.",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            "Mode: read-only local validation status.",
            "No work session was recorded and no action was executed.",
            "",
            "Result:",
            body,
        ]
    )


def _format_context_ask_response(route: object, body: str) -> str:
    """Render local context assembly status without creating a work-session record."""
    return "\n".join(
        [
            "Eva ask",
            "",
            "Request: context assembly status/policy/preview.",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            "Mode: read-only local/mock context preview.",
            "No work session was recorded and no action was executed.",
            "No live LLM call was made.",
            "Assembled context cannot execute tools.",
            "",
            "Result:",
            body,
        ]
    )


def _format_threat_ask_response(route: object, body: str) -> str:
    """Render local threat-defense status without creating a work-session record."""
    return "\n".join(
        [
            "Eva ask",
            "",
            "Request: LLM threat defense status/policy/preview.",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            "Mode: read-only local/mock threat-defense preview.",
            "No work session was recorded and no action was executed.",
            "No live LLM call was made.",
            "Untrusted context cannot override trusted policy/instruction hierarchy.",
            "Secrets/config/session data are blocked.",
            "Defended context cannot execute tools.",
            "",
            "Result:",
            body,
        ]
    )


def _format_agent_loop_ask_response(route: object, body: str) -> str:
    """Render local agent-loop status without creating a work-session record."""
    return "\n".join(
        [
            "Eva ask",
            "",
            "Request: Agent Loop v1 status/policy/preview.",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            "Mode: read-only local/mock agent loop preview.",
            "No work session was recorded and no action was executed.",
            "No live LLM call was made.",
            "Agent loop is local/mock preview only.",
            "Actions are preview-only.",
            "Tools are not executed.",
            "Secrets/config/session data are blocked.",
            "Browser/desktop/shell/cloud/MCP execution remains locked.",
            "",
            "Result:",
            body,
        ]
    )


def _format_workflow_planner_ask_response(route: object, body: str) -> str:
    """Render local workflow-planner status without creating a work-session record."""
    return "\n".join(
        [
            "Eva ask",
            "",
            "Request: Agentic Workflow Planner status/policy/preview.",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            "Mode: read-only local/mock workflow planner preview.",
            "No work session was recorded and no action was executed.",
            "No live LLM call was made.",
            "Workflow planner is local/mock preview only.",
            "Workflow steps are preview-only.",
            "Tools are not executed.",
            "Secrets/config/session data are blocked.",
            "Arbitrary file reads/writes are blocked.",
            "Browser/desktop/shell/cloud/MCP execution remains locked.",
            "Phase 12L remains a gated write path.",
            "",
            "Result:",
            body,
        ]
    )


def _format_execution_gates_ask_response(route: object, body: str) -> str:
    """Render local execution-gate status without creating a work-session record."""
    return "\n".join(
        [
            "Eva ask",
            "",
            "Request: Controlled Execution Gates status/policy/evaluation.",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            "Mode: read-only local/mock execution-gate policy preview.",
            "No work session was recorded and no action was executed.",
            "No live LLM call was made.",
            "Execution gates are local/mock policy preview only.",
            "Tools are not executed.",
            "Approval alone does not execute.",
            "Confirmation alone does not execute unless an existing implemented gate accepts it.",
            "Browser/desktop/shell/cloud/MCP/package execution remains locked.",
            "Secrets/config/session data are blocked.",
            "Phase 12L narrow real-create remains a gated write path.",
            "",
            "Result:",
            body,
        ]
    )


def _format_ai_os_ask_response(route: object, body: str) -> str:
    """Render local AI OS status without activating any runtime surface."""
    return "\n".join(
        [
            "Eva ask",
            "",
            "Request: AI OS dashboard/status/report.",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            "No live LLM call was made.",
            "AI OS dashboard is local/status only.",
            "Preview-only features do not execute.",
            "Tools are not executed.",
            "Browser/desktop/shell/cloud/MCP execution remains locked.",
            "Secrets/config/session data are blocked.",
            "Phase 12L remains a gated write path.",
            "",
            "Result:",
            body,
        ]
    )


def _format_voice_ask_response(route: object, body: str) -> str:
    """Render local Voice Assistant status without touching audio devices."""
    return "\n".join(
        [
            "Eva ask",
            "",
            "Request: Voice Assistant Foundation status/policy/preview.",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            "Voice Assistant is local/mock preview only.",
            "No microphone access happened.",
            "No audio playback happened.",
            "No live ASR/TTS happened.",
            "No live LLM call was made.",
            "Voice commands cannot execute tools.",
            "Secrets/config/session data are blocked.",
            "Browser/desktop/shell/cloud/MCP execution remains locked.",
            "Phase 12L remains a gated write path.",
            "",
            "Result:",
            body,
        ]
    )


def _format_memory_v3_ask_response(route: object, body: str) -> str:
    """Render local Memory v3 status without exposing raw memory storage."""
    return "\n".join(
        [
            "Eva ask",
            "",
            "Request: Memory v3 status/policy/retrieval preview.",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            "Mode: read-only local memory policy preview.",
            "No work session was recorded and no memory record was written.",
            "Memory v3 is local only.",
            "No live LLM call was made.",
            "No cloud memory is used.",
            "Secrets/config/session data are blocked.",
            "Memory cannot override system/developer/safety policy.",
            "Memory cannot execute tools.",
            "Memory context injection is preview/policy only.",
            "",
            "Result:",
            body,
        ]
    )


def _format_browser_read_ask_response(route: object, body: str) -> str:
    """Render Phase 24 observation/report output without recording a work session."""
    return "\n".join(
        [
            "Eva ask",
            "",
            "Request: Real Browser Read-Only Mode observation/status/policy.",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            "Browser mode is read-only.",
            "No clicking.",
            "No typing.",
            "No form submission.",
            "No downloads or uploads.",
            "No cookies, sessions, or browser profiles.",
            "No logged-in browser access.",
            "No browser control.",
            "No tool execution.",
            "No work session was recorded and no browser action was executed.",
            "Phase 12L remains a gated write path.",
            "",
            "Result:",
            body,
        ]
    )


def _format_desktop_observe_ask_response(route: object, body: str) -> str:
    """Render Phase 25 observation/report output without recording a work session."""
    return "\n".join(
        [
            "Eva ask",
            "",
            "Request: Real Desktop Observation Mode observation/status/policy.",
            f"Interpreted intent: {getattr(route, 'intent', 'unknown')}",
            "Desktop mode is observation-only.",
            "No clicking.",
            "No typing.",
            "No hotkeys.",
            "No app or window control.",
            "No continuous monitoring.",
            "No saved screenshots.",
            "No cookies, sessions, or browser profiles.",
            "No tool execution.",
            "No work session was recorded and no desktop action was executed.",
            "Phase 12L remains a gated write path.",
            "",
            "Result:",
            body,
        ]
    )


def _resolve_single_approved_file_approval(intent: str) -> str | None:
    from ..file_agent.approval_ledger import list_file_approval_requests

    approvals = list_file_approval_requests(status="approved_for_future_apply", limit=20)
    if len(approvals) != 1:
        return None
    approval_id = approvals[0].approval_id
    if intent == "approval_sandbox_verify":
        return f"eva file approval sandbox verify {approval_id}"
    if intent == "approval_sandbox_rollback":
        return f"eva file approval sandbox rollback {approval_id}"
    return f"eva file approval sandbox apply {approval_id}"


def _format_real_create_next_step() -> str:
    from ..file_agent.approval_ledger import list_file_approval_requests
    from ..file_agent.real_apply import evaluate_real_apply_eligibility, format_real_apply_eligibility

    eligible = []
    for approval in list_file_approval_requests(status="approved_for_future_apply", limit=50):
        item = evaluate_real_apply_eligibility(approval.approval_id)
        if item.allowed:
            eligible.append(item)
    if len(eligible) == 1:
        return "\n".join(
            [
                format_real_apply_eligibility(eligible[0]),
                "",
                f"To create it, run: `eva ask confirm real create {eligible[0].approval_id}`.",
            ]
        )
    if not eligible:
        return "No eligible narrow real-create approval was found. Use `eva file real apply eligibility <approval_id>` to inspect a specific approval. Exact creation requires `confirm real create <approval_id>`."
    lines = ["Multiple eligible real-create approvals exist. Specify one approval id:"]
    lines.extend(f"- {item.approval_id}: {item.display_path}" for item in eligible[:10])
    return "\n".join(lines)


def _should_show_skill_workflow_plan(request_text: str) -> bool:
    text = " ".join(str(request_text or "").lower().split())
    return any(term in text for term in ("docs note", "phase note", "latest fileagent phase", "latest phase"))
