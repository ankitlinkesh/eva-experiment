from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name} failed. {detail}")
    print({"case": name, "pass": True})


def assert_clean_output(name: str, output: str) -> None:
    forbidden = ["{'", "DraftPreview(", "DraftValidationResult(", "Traceback", str(ROOT)]
    leaks = [item for item in forbidden if item and item in output]
    assert_true(name, not leaks, f"leaks={leaks}\n{output}")


def main() -> None:
    draft_preview = importlib.import_module("backend.eva.file_agent.draft_preview")
    draft_generators = importlib.import_module("backend.eva.file_agent.draft_generators")
    draft_safety = importlib.import_module("backend.eva.file_agent.draft_safety")
    assert_true("draft_preview_module_imports", draft_preview is not None)
    assert_true("draft_generators_module_imports", draft_generators is not None)
    assert_true("draft_safety_module_imports", draft_safety is not None)

    from backend.eva.agents.file_agent import FileAgent
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import build_default_registry
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.file_agent.draft_generators import (
        draft_missing_files_recommendations,
        draft_project_summary,
        draft_readme_section,
        draft_report_outline,
        draft_todo_list_from_project_inventory,
    )
    from backend.eva.file_agent.draft_preview import (
        create_append_preview,
        create_file_draft_preview,
        create_text_replacement_preview,
        create_unified_diff_preview,
        format_draft_preview,
        validate_draft_preview,
    )
    from backend.eva.file_agent.status import format_file_agent_status
    from backend.eva.planner.capability_selector import select_capabilities_for_goal

    status = format_file_agent_status()
    assert_true("file_agent_status_mentions_draft_preview", "draft previews" in status.lower() and "not written" in status.lower())

    target = ROOT / "docs" / "TEST_DRAFT_DO_NOT_CREATE.md"
    if target.exists():
        raise AssertionError("Verifier target unexpectedly exists before test.")
    create_preview = create_file_draft_preview("docs/TEST_DRAFT_DO_NOT_CREATE.md", "Hello API_KEY=FAKE_SECRET_VALUE")
    create_output = format_draft_preview(create_preview)
    assert_true("create_draft_preview_allowed", create_preview.operation == "create_preview" and not target.exists())
    assert_true("create_draft_output_preview_only", "No file was created or modified" in create_output)
    assert_true("secret_like_content_redacted_or_warned", "FAKE_SECRET_VALUE" not in create_output and create_preview.safety_warnings)
    assert_clean_output("create_draft_output_clean", create_output)

    readme_path = ROOT / "README.md"
    original_readme = readme_path.read_text(encoding="utf-8", errors="replace")
    append_preview = create_append_preview("README.md", "Draft append text")
    append_output = format_draft_preview(append_preview)
    assert_true("append_preview_does_not_modify_file", readme_path.read_text(encoding="utf-8", errors="replace") == original_readme)
    assert_true("append_preview_mentions_append", "append_preview" in append_output and "No file was created or modified" in append_output)

    replace_preview = create_text_replacement_preview("README.md", "Eva", "Eva Preview")
    replace_output = format_draft_preview(replace_preview)
    assert_true("replace_preview_does_not_modify_file", readme_path.read_text(encoding="utf-8", errors="replace") == original_readme)
    assert_true("replace_preview_has_diff", "--- README.md" in replace_output and "+++ README.md" in replace_output)

    diff_preview = create_unified_diff_preview("README.md", original_readme.replace("Eva", "Eva Preview", 1))
    diff_output = format_draft_preview(diff_preview)
    assert_true("diff_preview_unified_style", "--- README.md" in diff_output and "@@" in diff_output)

    env_preview = create_file_draft_preview(".env.local", "API_KEY=FAKE_VALUE")
    env_output = format_draft_preview(env_preview)
    assert_true("env_local_draft_refused", not env_preview.allowed and "refused" in env_output.lower())

    runtime_preview = create_file_draft_preview("backend/eva/data/test.txt", "hello")
    assert_true("runtime_data_draft_refused", not runtime_preview.allowed)

    validation = validate_draft_preview(create_preview)
    validation_output = draft_preview.format_draft_validation(validation)
    assert_true("draft_validation_warns", not validation.allowed and "warning" in validation_output.lower())
    assert_clean_output("draft_validation_output_clean", validation_output)

    for name, text in {
        "readme_section_draft_human": draft_readme_section("Safety"),
        "project_summary_draft_human": draft_project_summary(),
        "missing_files_draft_human": draft_missing_files_recommendations(),
        "report_outline_draft_human": draft_report_outline("Eva Architecture"),
        "project_todo_draft_human": draft_todo_list_from_project_inventory(),
    }.items():
        assert_true(name, len(text.splitlines()) >= 3 and "saved" not in text.lower())
        assert_clean_output(f"{name}_clean", text)

    commands = {
        "cmd_draft_create": "eva file draft create docs/TEST_DRAFT.md text Hello draft",
        "cmd_draft_append": "eva file draft append README.md text Draft append text",
        "cmd_draft_replace": "eva file draft replace README.md old Eva new Eva Preview",
        "cmd_draft_diff": "eva file draft diff README.md text # Eva Preview",
        "cmd_readme_section": "eva draft readme section Safety",
        "cmd_project_summary": "eva draft project summary",
        "cmd_report_outline": "eva draft report outline Eva Architecture",
        "cmd_project_todo": "eva draft project todo",
        "cmd_env_refused": "eva file draft create .env.local text API_KEY=FAKE_VALUE",
    }
    for name, command in commands.items():
        reply = maybe_handle_fast_command(command, tools=None, memory=None)
        assert_true(name, reply is not None, command)
        output = reply[0]
        assert_true(f"{name}_preview_only", "No file was created or modified" in output or "Draft" in output or "refused" in output.lower())
        assert_clean_output(f"{name}_clean_output", output)
    assert_true("fast_commands_did_not_create_target", not target.exists())

    execute = FileAgent().execute({"capability_id": "file.write_text", "input_summary": "write README"})
    assert_true("file_agent_execute_still_refuses_writes", execute.status == "refused" and "refused" in execute.summary.lower())

    selected = select_capabilities_for_goal("draft README section about safety")
    assert_true("planner_selects_file_draft_capability", "file.draft_readme_section" in selected, str(selected))

    review_module = importlib.import_module("backend.eva.agents.team_review")
    review_text = review_module.format_team_review("append to README")
    assert_true("team_review_routes_draft_to_file_agent", "FileAgent" in review_text and "preview" in review_text.lower())

    registry = build_default_registry()
    for capability_id in (
        "file.draft_create_preview",
        "file.draft_append_preview",
        "file.draft_replace_preview",
        "file.diff_preview",
        "file.draft_readme_section",
        "file.draft_project_summary",
        "file.draft_report_outline",
        "file.draft_project_todo",
    ):
        cap = registry.get(capability_id)
        permission = get_capability_permission(capability_id)
        resolution = resolve_capability(capability_id)
        schema = capability_to_tool_schema(capability_id)
        assert_true(f"{capability_id}_registered", cap is not None)
        assert_true(f"{capability_id}_permission_preview_readonly", permission.read_only and not permission.writes_local_data and not permission.requires_confirmation)
        assert_true(f"{capability_id}_resource_mapping", resolution.resource_id == "eva-file-agent-v1" and resolution.preview_only)
        assert_true(f"{capability_id}_schema_exists", schema is not None)

    for module_name in (
        "backend.eva.file_agent.draft_preview",
        "backend.eva.file_agent.draft_generators",
        "backend.eva.file_agent.draft_safety",
    ):
        source = (ROOT / module_name.replace(".", "/")).with_suffix(".py").read_text(encoding="utf-8")
        forbidden = ["subprocess", "playwright", "pyautogui", "mcp", ".env.local"]
        found = [item for item in forbidden if item in source.lower()]
        assert_true(f"{module_name}_forbidden_imports_absent", not found, str(found))

    for script_name in (
        "verify_eva_file_agent_understanding.py",
        "verify_eva_file_agent_readonly.py",
        "verify_eva_agent_framework_quality.py",
        "verify_eva_planner_v3_quality.py",
        "verify_eva_capability_resource_mapping.py",
        "verify_eva_stabilization_v1.py",
    ):
        assert_true(f"existing_verifier_present_{script_name}", (ROOT / "scripts" / script_name).exists())

    print({"overall_pass": True, "failures": 0})


if __name__ == "__main__":
    main()
