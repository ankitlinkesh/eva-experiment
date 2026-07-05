from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_clean(text: str, label: str) -> None:
    forbidden = [
        "{'",
        "WorkSession(",
        "WorkSessionEvent(",
        "sqlite3.Row",
        "Traceback",
        "C:\\Users\\",
        ".env.local",
        "api_key",
        "Bearer ",
        "sk-",
        "raw_vector",
    ]
    for token in forbidden:
        assert_true(token not in text, f"{label} leaked unsafe/internal token: {token}")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["EVA_WORK_SESSIONS_DB_PATH"] = str(Path(tmp) / "work_sessions.sqlite3")

        from backend.eva.agents.team_review import format_team_review
        from backend.eva.capabilities.permissions import get_capability_permission
        from backend.eva.capabilities.registry import build_default_registry
        from backend.eva.capabilities.resource_mapping import resolve_capability
        from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
        from backend.eva.control_center.collector import collect_control_center_status
        from backend.eva.control_center.formatter import format_control_center_status
        from backend.eva.core.fast_commands import maybe_handle_fast_command
        from backend.eva.core.natural_router import route_natural_request
        from backend.eva.planner.capability_selector import select_capabilities_for_goal
        from backend.eva.planner.decomposer import create_task_plan
        from backend.eva.tools.registry import ToolRegistry
        from backend.eva.work_sessions.formatter import (
            format_work_session,
            format_work_session_timeline,
            format_work_sessions_status,
            summarize_recent_work_sessions,
            summarize_work_session,
        )
        from backend.eva.work_sessions.store import (
            add_session_event,
            close_work_session,
            create_work_session,
            find_latest_active_work_session,
            get_work_session,
            list_recent_work_sessions,
        )

        session = create_work_session(
            r"inspect this project using C:\Users\HP\secret\.env.local with Bearer sk-test",
            source="verifier",
        )
        assert_true(session.session_id.startswith("ws_"), "session id created")
        add_session_event(session.session_id, "intent_routed", "Routed to project inspection", {"path": r"C:\Users\HP\secret\.env.local", "token": "Bearer sk-test"})
        add_session_event(session.session_id, "specialist_selected", "Selected ProjectInspectorAgent", {"specialist": "ProjectInspectorAgent"})
        add_session_event(session.session_id, "authority_decision", "Read-only status decision", {"mode": "read_only"})
        add_session_event(session.session_id, "verification_seen", "Verification not run by status layer", {"status": "not_run"})
        fetched = get_work_session(session.session_id)
        assert_true(fetched is not None, "session can be read")
        recent = list_recent_work_sessions(limit=5)
        assert_true(any(item.session_id == session.session_id for item in recent), "session appears in recent list")
        latest = find_latest_active_work_session()
        assert_true(latest is not None and latest.session_id == session.session_id, "latest active session found")

        detail = format_work_session(session.session_id)
        timeline = format_work_session_timeline(session.session_id)
        status = format_work_sessions_status()
        summary = summarize_work_session(session.session_id)
        recent_text = summarize_recent_work_sessions()
        for label, output in [
            ("detail", detail),
            ("timeline", timeline),
            ("status", status),
            ("summary", summary),
            ("recent", recent_text),
        ]:
            assert_clean(output, label)
            assert_true("Work session" in output or "Work sessions" in output, f"{label} is human-readable")
        assert_true(timeline.index("request_received") < timeline.index("intent_routed") < timeline.index("authority_decision"), "timeline preserves event order")

        closed = close_work_session(session.session_id, "reported", "Verifier summary complete")
        assert_true(closed.status == "reported", "session closes")
        assert_true(find_latest_active_work_session() is None, "closed session is not active")

        tools = ToolRegistry()
        commands = [
            "eva sessions status",
            "eva sessions recent",
            "eva session latest",
            f"eva session {session.session_id}",
            f"eva session timeline {session.session_id}",
            "eva audit timeline",
            "eva work status",
            "eva ask inspect this project",
            "eva ask are we actually done",
            "eva ask what happened last",
        ]
        for command in commands:
            result = maybe_handle_fast_command(command, tools)
            assert_true(result is not None, f"{command} handled")
            assert_clean(result[0], command)
            assert_true("Work session" in result[0] or "Eva ask" in result[0] or "Done check" in result[0], f"{command} returns friendly session/status text")
        ask_output = maybe_handle_fast_command("eva ask inspect this project", tools)[0]
        assert_true("Work session:" in ask_output, "eva ask includes session id")
        assert_true("Project" in ask_output or "project" in ask_output, "eva ask still returns delegated body")

        route = route_natural_request("what happened last")
        assert_true(route.intent == "latest_work_session", "latest session route exists")
        route = route_natural_request("show audit timeline")
        assert_true(route.intent == "audit_timeline", "audit timeline route exists")

        cc = collect_control_center_status()
        cc_text = format_control_center_status(cc)
        assert_clean(cc_text, "control center")
        assert_true("Work Sessions / Audit Timeline" in cc_text, "control center includes work session panel")

        registry = build_default_registry()
        for cap_id in [
            "eva.work_sessions_status",
            "eva.work_sessions_recent",
            "eva.work_session_timeline",
            "eva.audit_timeline",
            "eva.latest_work_session",
        ]:
            assert_true(registry.get(cap_id) is not None, f"{cap_id} registered")
            permission = get_capability_permission(cap_id)
            assert_true(permission.read_only, f"{cap_id} is read-only")
            assert_true(not permission.external_effect, f"{cap_id} has no external effect")
            assert_true(resolve_capability(cap_id).resource_id is not None, f"{cap_id} maps to a resource")
            assert_true(capability_to_tool_schema(cap_id) is not None, f"{cap_id} schema exists")

        caps = select_capabilities_for_goal("show the work session audit timeline")
        assert_true("eva.audit_timeline" in caps, "planner selects audit timeline")
        plan = create_task_plan("what happened last in Eva")
        assert_true(any(step.capability_id == "eva.latest_work_session" for step in plan.steps), "planner includes latest session step")
        review = format_team_review("show work session audit timeline")
        assert_clean(review, "team review")
        assert_true("WorkSession/audit route" in review, "team review includes WorkSession route")

        source_files = [
            ROOT / "backend/eva/work_sessions/store.py",
            ROOT / "backend/eva/work_sessions/timeline.py",
            ROOT / "backend/eva/core/natural_router.py",
            ROOT / "backend/eva/control_center/collector.py",
        ]
        joined = "\n".join(path.read_text(encoding="utf-8") for path in source_files if path.exists()).lower()
        for forbidden in [
            "import playwright",
            "from playwright",
            "import pyautogui",
            "from pyautogui",
            "import subprocess",
            "subprocess.",
            "requests.",
            "httpx.",
            "pip install",
        ]:
            assert_true(forbidden not in joined, f"no forbidden feature code: {forbidden}")

    print("verify_eva_work_sessions_audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
