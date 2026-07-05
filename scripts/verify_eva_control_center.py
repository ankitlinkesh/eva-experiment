from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def report(case: str, passed: bool, **extra: object) -> bool:
    payload = {"case": case, "pass": bool(passed)}
    payload.update(extra)
    print(payload)
    return bool(passed)


def clean_output(text: str) -> bool:
    private_root = str(ROOT).lower()
    lowered = str(text or "").lower()
    forbidden = [
        "{'",
        "ControlCenterStatus(",
        "Traceback",
        ".env.local contents",
        private_root,
        "http://fonts.",
        "https://fonts.",
        "google-analytics",
        "gtag(",
    ]
    return not any(item.lower() in lowered for item in forbidden)


def assert_contains(text: str, *terms: str) -> bool:
    lowered = text.lower()
    return all(term.lower() in lowered for term in terms)


def run_fast_command(message: str) -> str:
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry

    handled = maybe_handle_fast_command(message, ToolRegistry(), session_context={}, memory=None)
    if handled is None:
        return ""
    return handled[0]


def main() -> int:
    results: list[bool] = []

    from backend.eva.control_center.collector import collect_control_center_status
    from backend.eva.control_center.formatter import format_control_center_status, render_control_center_html
    from backend.eva.control_center.routes import get_control_center_routes
    from backend.eva.control_center.status import format_control_center_text, format_control_center_url

    status = collect_control_center_status()
    text = format_control_center_status(status)
    html = render_control_center_html(status)

    results.append(report("control_center_imports", True))
    results.append(report("collect_returns_structured_object", hasattr(status, "app_name") and hasattr(status, "generated_at")))
    results.append(report("formatter_human_readable", assert_contains(text, "Eva Control Center", "Authority", "Safety")))
    results.append(report("formatter_contains_title", "Eva Control Center" in text))
    results.append(report("formatter_says_real_execution_disabled", assert_contains(text, "real execution", "disabled")))
    results.append(report("routes_import", get_control_center_routes() is not None))

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(get_control_center_routes())
    route_paths = {getattr(route, "path", "") for route in app.routes}
    results.append(report("fastapi_routes_registered", "/control" in route_paths and "/control/status.json" in route_paths))
    client = TestClient(app)
    status_response = client.get("/control/status.json")
    results.append(report("status_endpoint_safe_json", status_response.status_code == 200 and status_response.json().get("app_name") == "Eva Control Center"))
    dashboard_response = client.get("/control")
    dashboard_html = dashboard_response.text
    results.append(report("dashboard_html_no_external_cdn", "cdn." not in dashboard_html.lower()))
    results.append(report("dashboard_html_no_remote_font", "fonts.googleapis" not in dashboard_html.lower() and "fonts.gstatic" not in dashboard_html.lower()))
    results.append(report("dashboard_html_no_analytics", "analytics" not in dashboard_html.lower() and "gtag" not in dashboard_html.lower()))

    for case, term in [
        ("dashboard_authority_section", "Authority"),
        ("dashboard_fileagent_section", "FileAgent"),
        ("dashboard_approvals_section", "Approvals"),
        ("dashboard_sandbox_apply_section", "Sandbox Apply"),
        ("dashboard_capabilities_section", "Capabilities"),
        ("dashboard_agents_section", "Agents"),
        ("dashboard_planner_section", "Planner"),
        ("dashboard_verifiers_section", "Verifiers"),
        ("dashboard_future_locked_section", "Future Locked Modules"),
    ]:
        results.append(report(case, term in dashboard_html))

    results.append(report("browseragent_locked", assert_contains(dashboard_html, "BrowserAgent", "locked")))
    results.append(report("news_dashboard_locked", assert_contains(dashboard_html, "News", "locked")))
    results.append(report("real_file_writes_disabled", assert_contains(dashboard_html, "real file writes", "disabled")))

    url_output = format_control_center_url()
    results.append(report("dashboard_url_local_only", "http://127.0.0.1:8765/control" in url_output and clean_output(url_output)))
    command_status = run_fast_command("eva control center status")
    results.append(report("fast_command_control_status", "Eva Control Center" in command_status and clean_output(command_status)))
    ask_output = run_fast_command("eva ask show control center")
    results.append(report("eva_ask_show_control_center_routes", "Control Center" in ask_output and "status" in ask_output.lower() and clean_output(ask_output)))
    ask_open = run_fast_command("eva ask open dashboard")
    results.append(report("eva_ask_open_dashboard_no_browser", "did not open" in ask_open.lower() and "http://127.0.0.1:8765/control" in ask_open and clean_output(ask_open)))

    combined = "\n".join([text, html, url_output, command_status, ask_output, ask_open, format_control_center_text()])
    results.append(report("output_no_raw_dict_repr", "{'" not in combined))
    results.append(report("output_no_dataclass_repr", "ControlCenterStatus(" not in combined))
    results.append(report("output_no_stack_trace", "Traceback" not in combined))
    results.append(report("output_no_env_local_contents", ".env.local contents" not in combined))
    results.append(report("output_no_absolute_private_paths", str(ROOT).lower() not in combined.lower()))

    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import build_default_registry
    from backend.eva.capabilities.resource_mapping import resolve_capability_resource
    from backend.eva.capabilities.tool_schemas import get_tool_schema_preview

    registry = build_default_registry()
    for cap_id in [
        "eva.control_center_status",
        "eva.control_center_dashboard",
        "eva.control_center_status_json",
        "eva.dashboard_url",
    ]:
        cap = registry.get(cap_id)
        permission = get_capability_permission(cap_id)
        results.append(report(f"capability_registered_{cap_id}", cap is not None))
        results.append(report(f"capability_read_only_{cap_id}", permission.read_only and permission.public_mode_allowed))
        results.append(report(f"resource_mapping_{cap_id}", resolve_capability_resource(cap_id).resource_id == "eva-control-center"))
        results.append(report(f"tool_schema_{cap_id}", get_tool_schema_preview(cap_id) is not None))

    from backend.eva.planner.capability_selector import infer_goal_intents, select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.agents.team_review import format_team_review

    intents = infer_goal_intents("show dashboard")
    selected = select_capabilities_for_goal("show dashboard")
    results.append(report("planner_recognizes_dashboard_goal", "control_center" in intents and "eva.control_center_status" in selected))
    review = format_team_review("show Eva system state dashboard")
    results.append(report("team_review_routes_dashboard_safely", ("ControlCenterAgent" in review or "SafetyAgent" in review) and clean_output(review), output=review[:400]))

    master = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_eva_all.py"), "--list"], cwd=str(ROOT), text=True, capture_output=True)
    results.append(report("master_verifier_lists_control_center", master.returncode == 0 and "verify_eva_control_center.py" in master.stdout))
    results.append(report("authority_verifier_present", (ROOT / "scripts" / "verify_eva_authority_natural_router.py").exists()))
    results.append(report("fileagent_sandbox_verifier_present", (ROOT / "scripts" / "verify_eva_file_agent_sandbox_apply.py").exists()))
    results.append(report("stabilization_verifier_present", (ROOT / "scripts" / "verify_eva_stabilization_v1.py").exists()))

    overall = all(results)
    print({"overall_pass": overall, "failures": len([item for item in results if not item])})
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
