from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def emit(case: str, passed: bool, **extra: object) -> int:
    import json

    payload = {"case": case, "pass": bool(passed), **extra}
    print(json.dumps(payload, indent=2, default=str))
    return 0 if passed else 1


def clean_output(text: str) -> bool:
    blocked = [
        "{'",
        "FilePathDecision(",
        "FileInspection(",
        "FolderInspection(",
        "TextPreview(",
        "ProjectStructure(",
        "Traceback",
        "sqlite3.Row",
        "C:\\",
        str(ROOT),
    ]
    return not any(marker in str(text) for marker in blocked)


def command_text(command: str) -> str:
    from backend.eva.core.fast_commands import maybe_handle_fast_command

    result = maybe_handle_fast_command(command, tools=None, memory=None)
    if result is None:
        return ""
    return str(result[0])


def main() -> int:
    failures = 0

    modules = [
        "backend.eva.file_agent.path_policy",
        "backend.eva.file_agent.inspector",
        "backend.eva.file_agent.search",
        "backend.eva.file_agent.formatter",
        "backend.eva.file_agent.status",
    ]
    imported = []
    try:
        for module_name in modules:
            imported.append(importlib.import_module(module_name).__name__)
        failures += emit("file_agent_package_imports", True, imported=imported)
    except Exception as exc:
        failures += emit("file_agent_package_imports", False, error=str(exc), imported=imported)
        print('{"overall_pass": false, "failures": %d}' % failures)
        return 1

    from backend.eva.agents.delegation import format_agent_dry_run_for_goal
    from backend.eva.agents.registry import get_agent, select_agent_for_step
    from backend.eva.agents.team_review import review_plan_with_agent_team
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import build_default_registry
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.file_agent.formatter import (
        format_file_search_results,
        format_folder_inspection,
        format_path_inspection,
        format_project_structure,
        format_text_preview,
    )
    from backend.eva.file_agent.inspector import (
        explain_project_structure,
        inspect_folder,
        inspect_path,
        preview_text_file,
    )
    from backend.eva.file_agent.path_policy import evaluate_file_path
    from backend.eva.file_agent.search import search_files_by_name
    from backend.eva.file_agent.status import format_file_agent_status
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.resources.registry import get_resource

    env_local = evaluate_file_path(".env.local", repo_root=ROOT)
    failures += emit("path_policy_blocks_env_local", not env_local.allowed and ".env.local" in env_local.display_path, decision=env_local.__dict__)

    env_example = evaluate_file_path(".env.example", repo_root=ROOT)
    failures += emit("path_policy_allows_env_example", env_example.allowed and env_example.display_path == ".env.example", decision=env_example.__dict__)

    key_decision = evaluate_file_path("id_rsa", repo_root=ROOT)
    failures += emit("path_policy_blocks_private_key_style_path", not key_decision.allowed, decision=key_decision.__dict__)

    runtime_decision = evaluate_file_path("backend/eva/data/research_memory/research_memory.sqlite3", repo_root=ROOT)
    failures += emit("path_policy_blocks_runtime_db_path", not runtime_decision.allowed, decision=runtime_decision.__dict__)

    status = format_file_agent_status()
    failures += emit("file_status_output_human_readable", "FileAgent v1" in status and "read-only" in status.lower() and clean_output(status), output=status)

    inspected = format_path_inspection(inspect_path("docs/EVA_AGENT_FRAMEWORK.md", repo_root=ROOT))
    failures += emit("inspect_docs_file_returns_metadata", "Path inspection" in inspected and "allowed" in inspected.lower() and clean_output(inspected), output=inspected)

    folder = format_folder_inspection(inspect_folder("backend/eva", repo_root=ROOT, max_entries=40))
    failures += emit(
        "folder_inspect_backend_eva_limited_skips_runtime",
        "Folder inspection" in folder and "backend/eva/data" not in folder and "__pycache__" not in folder and clean_output(folder),
        output=folder,
    )

    search = search_files_by_name("planner", repo_root=ROOT, max_results=20)
    search_text = format_file_search_results(search)
    failures += emit(
        "file_search_planner_returns_repo_relative_paths",
        "File search results" in search_text and "planner" in search_text.lower() and "C:\\" not in search_text and clean_output(search_text),
        output=search_text,
    )

    preview = format_text_preview(preview_text_file("docs/EVA_PLANNER.md", repo_root=ROOT, max_chars=1200))
    failures += emit(
        "text_preview_docs_planner_limited",
        "Text preview" in preview and ("truncated" in preview.lower() or len(preview) < 1800) and clean_output(preview),
        output=preview[:900],
    )

    binary_preview = format_text_preview(preview_text_file("backend/eva/data/research_memory/research_memory.sqlite3", repo_root=ROOT))
    failures += emit("binary_or_runtime_preview_refused", "refused" in binary_preview.lower() or "not allowed" in binary_preview.lower(), output=binary_preview)

    structure = format_project_structure(explain_project_structure(".", repo_root=ROOT, max_depth=2))
    failures += emit(
        "project_structure_human_limited",
        "Project structure" in structure and "backend/eva/data" not in structure and clean_output(structure),
        output=structure,
    )

    combined_outputs = "\n".join([status, inspected, folder, search_text, preview, binary_preview, structure])
    failures += emit("outputs_no_raw_reprs_or_paths", clean_output(combined_outputs))

    file_agent = get_agent("FileAgent")
    failures += emit("file_agent_registered", file_agent is not None and "file" in getattr(file_agent, "capabilities", ()), agent=type(file_agent).__name__ if file_agent else None)

    if file_agent is not None:
        execute_response = file_agent.execute({"input_summary": "write file README.md", "capability_id": "file.preview_text"})
        failures += emit("file_agent_execute_refuses_writes", execute_response.status == "refused" and "write" in execute_response.summary.lower(), response=execute_response.as_dict())

    plan = create_task_plan("inspect README")
    cap_ids = [step.capability_id for step in plan.steps if step.capability_id]
    failures += emit("planner_inspect_readme_selects_file_capability", any(str(cap).startswith("file.") for cap in cap_ids), capabilities=cap_ids)

    file_step = next((step for step in plan.steps if step.capability_id and step.capability_id.startswith("file.")), None)
    selected = select_agent_for_step(file_step) if file_step else None
    failures += emit("agent_selection_file_step_file_agent_or_code", type(selected).__name__ in {"FileAgent", "CodeAgent"} if selected else False, agent=type(selected).__name__ if selected else None)

    review = review_plan_with_agent_team(create_task_plan("inspect README and explain project structure"))
    review_agents = {finding.reviewer for finding in review.findings}
    failures += emit("team_review_file_goal_mentions_file_or_code_agent", bool(review_agents & {"FileAgent", "CodeAgent"}), agents=sorted(review_agents))

    registry = build_default_registry()
    capability = registry.get("file.inspect_path")
    failures += emit("capability_registry_includes_file_inspect", capability is not None and capability.read_only and capability.risk_level == "medium", capability=capability.__dict__ if capability else None)

    permission = get_capability_permission("file.preview_text")
    failures += emit("file_permission_readonly_medium_private_safe", permission.read_only and permission.risk_level == "medium" and permission.private_mode_allowed, permission=permission.__dict__)

    resource = get_resource("eva-file-agent-v1")
    failures += emit("resource_registry_includes_file_agent", resource is not None and resource.can_read_files and not resource.can_write_files, resource=resource.as_dict() if resource else None)

    resolution = resolve_capability("file.inspect_path")
    failures += emit("resource_mapping_resolves_file_inspect", resolution.resource_id == "eva-file-agent-v1" and resolution.agent == "FileAgent", resolution=resolution.as_dict())

    schema_preview = capability_to_tool_schema("file.preview_text")
    schema_search = capability_to_tool_schema("file.search_name")
    failures += emit("tool_schema_previews_file_preview_search", schema_preview is not None and schema_search is not None, preview=schema_preview, search=schema_search)

    fast_cases = {
        "eva file status": "FileAgent v1",
        "eva file inspect docs/EVA_AGENT_FRAMEWORK.md": "Path inspection",
        "eva folder inspect backend/eva": "Folder inspection",
        "eva file search planner": "File search results",
        "eva file preview docs/EVA_PLANNER.md": "Text preview",
        "eva project structure": "Project structure",
        "eva file preview .env.local": "refused",
    }
    for command, marker in fast_cases.items():
        output = command_text(command)
        failures += emit(f"fast_command_{command.replace(' ', '_').replace('.', '_').replace('/', '_')}", marker.lower() in output.lower() and clean_output(output), output=output[:1200])

    source_files = [
        ROOT / "backend" / "eva" / "file_agent" / "inspector.py",
        ROOT / "backend" / "eva" / "file_agent" / "search.py",
        ROOT / "backend" / "eva" / "file_agent" / "path_policy.py",
    ]
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in source_files if path.exists())
    forbidden = [
        "subprocess.",
        "os.system",
        "popen(",
        "import playwright",
        "import pyautogui",
        "from playwright",
        "from pyautogui",
        "import mcp",
        "from mcp",
        ".env.local).read",
    ]
    failures += emit("no_shell_mcp_playwright_pyautogui_calls", not any(item.lower() in source_text.lower() for item in forbidden))

    for verifier in [
        "scripts/verify_eva_agent_framework_quality.py",
        "scripts/verify_eva_planner_v3_quality.py",
        "scripts/verify_eva_capability_resource_mapping.py",
        "scripts/verify_eva_stabilization_v1.py",
    ]:
        failures += emit(f"existing_verifier_present_{Path(verifier).name}", (ROOT / verifier).exists())

    print('{"overall_pass": %s, "failures": %d}' % ("true" if failures == 0 else "false", failures))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
