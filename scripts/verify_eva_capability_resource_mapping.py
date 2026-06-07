from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def emit(case: str, passed: bool, **payload: Any) -> int:
    ok = bool(passed)
    print(json.dumps({"case": case, "pass": ok, **payload}, indent=2, ensure_ascii=False))
    return 0 if ok else 1


def clean_output(text: str) -> bool:
    blocked = (
        "{'",
        "Capability(",
        "CapabilityResourceLink(",
        "CapabilityResolution(",
        "CapabilityPermission(",
        "EvaResource(",
        "sqlite3.Row",
        "Traceback",
        "C:\\Users\\",
        "C:/Users/",
        "backend/eva/data",
        ".env.local",
        "raw_vector",
    )
    return bool(text and not any(marker in text for marker in blocked))


def main() -> int:
    failures = 0
    try:
        from backend.eva.capabilities.resource_mapping import (
            CapabilityResourceLink,
            CapabilityResolution,
            find_capabilities_by_resource,
            find_resources_for_capability,
            format_capability_resolution,
            format_capability_resource_matrix,
            get_capability_resource_link,
            list_capability_resource_links,
            resolve_capabilities_for_goal,
            resolve_capability,
        )
        from backend.eva.core.fast_commands import maybe_handle_fast_command
        from backend.eva.tools.registry import ToolRegistry
    except Exception as exc:
        failures += emit("resource_mapping_module_imports", False, error=str(exc))
        print(json.dumps({"overall_pass": False, "failures": failures}, indent=2))
        return 1

    failures += emit("resource_mapping_module_imports", True)

    links = list_capability_resource_links()
    failures += emit(
        "capability_resource_links_non_empty",
        bool(links) and all(isinstance(link, CapabilityResourceLink) for link in links),
        count=len(links),
    )

    retrieve = resolve_capability("research_memory.retrieve")
    failures += emit(
        "research_memory_retrieve_resolves_resource",
        isinstance(retrieve, CapabilityResolution)
        and retrieve.resource_id == "eva-research-memory-v2"
        and retrieve.agent == "ResearchAgent",
        resolution=retrieve.as_dict(),
    )
    failures += emit(
        "research_memory_retrieve_available_readonly",
        retrieve.final_status == "available_read_only"
        and retrieve.available_now
        and retrieve.allowed_in_public_mode
        and not retrieve.requires_confirmation
        and retrieve.risk_level == "low",
        resolution=retrieve.as_dict(),
    )
    failures += emit(
        "research_memory_retrieve_schema_preview_available",
        retrieve.tool_schema_available and retrieve.execution_path == "read_only_delegate",
    )

    save_resolution = resolve_capability("research_memory.save")
    import_resolution = resolve_capability("research_memory.import_note")
    failures += emit(
        "research_memory_save_import_explicit_local_write",
        save_resolution.final_status == "available_explicit_local_write"
        and import_resolution.final_status == "available_explicit_local_write"
        and save_resolution.resource_id == "eva-research-memory-v2",
        save=save_resolution.as_dict(),
        imported=import_resolution.as_dict(),
    )

    delete_resolution = resolve_capability("research_memory.delete_item")
    clear_resolution = resolve_capability("research_memory.clear_topic")
    failures += emit(
        "research_memory_delete_clear_confirmed_scoped",
        delete_resolution.requires_confirmation
        and clear_resolution.requires_confirmation
        and "confirm phrase" in clear_resolution.reason.lower(),
        delete=delete_resolution.as_dict(),
        clear=clear_resolution.as_dict(),
    )

    vector_resolution = resolve_capability("research_memory.vector_search")
    failures += emit(
        "vector_search_disabled_or_preview",
        vector_resolution.resource_id == "eva-research-memory-vector-index"
        and vector_resolution.final_status in {"disabled_experimental", "preview_only"}
        and not vector_resolution.available_now,
        resolution=vector_resolution.as_dict(),
    )

    demo_resolution = resolve_capability("public_release.demo")
    dry_run_resolution = resolve_capability("eva_v2.dry_run")
    failures += emit(
        "public_release_demo_preview_safe",
        demo_resolution.final_status == "preview_only"
        and demo_resolution.execution_path == "demo_only"
        and demo_resolution.allowed_in_public_mode,
        resolution=demo_resolution.as_dict(),
    )
    failures += emit(
        "eva_v2_dry_run_preview_available",
        dry_run_resolution.final_status == "preview_only"
        and dry_run_resolution.execution_path == "v2_dry_run"
        and dry_run_resolution.allowed_in_public_mode,
        resolution=dry_run_resolution.as_dict(),
    )

    odysseus = resolve_capability("reference.odysseus_ai_workspace")
    memos = resolve_capability("reference.memos_memory_operating_system")
    failures += emit("odysseus_remains_reference_only", odysseus.final_status == "reference_only", resolution=odysseus.as_dict())
    failures += emit("memos_remains_reference_only", memos.final_status == "reference_only", resolution=memos.as_dict())

    unknown = resolve_capability("missing.capability")
    failures += emit(
        "unknown_capability_safe",
        unknown.final_status == "unknown" and not unknown.available_now and not unknown.allowed_in_public_mode,
        resolution=unknown.as_dict(),
    )

    research_links = find_capabilities_by_resource("eva-research-memory-v2")
    resource_ids = find_resources_for_capability("research_memory.retrieve")
    failures += emit(
        "resource_capabilities_lookup_works",
        "research_memory.retrieve" in [link.capability_id for link in research_links]
        and "eva-research-memory-v2" in resource_ids,
        count=len(research_links),
        resources=resource_ids,
    )
    failures += emit(
        "get_capability_resource_link_aliases",
        get_capability_resource_link("research_memory.save") is not None
        and get_capability_resource_link("public_release.demo") is not None,
    )

    matrix = format_capability_resource_matrix()
    resolve_text = format_capability_resolution("research_memory.retrieve")
    vector_text = format_capability_resolution("research_memory.vector_search")
    outputs = [matrix, resolve_text, vector_text]
    failures += emit(
        "mapping_outputs_human_readable",
        all(clean_output(text) for text in outputs)
        and "Capability-resource matrix" in matrix
        and "available_read_only" in resolve_text
        and "disabled" in vector_text.lower(),
        matrix=matrix,
        resolve=resolve_text,
    )

    planned = resolve_capabilities_for_goal("use my saved research about Eva")
    failures += emit(
        "planner_helper_maps_saved_research",
        bool(planned) and any(item.capability_id in {"research_memory.retrieve", "research_memory.search"} for item in planned),
        planned=[item.as_dict() for item in planned],
    )

    tools = ToolRegistry()
    command_cases = {
        "eva capability resolve research_memory.retrieve": "available_read_only",
        "eva capability resources research_memory.retrieve": "eva-research-memory-v2",
        "eva resource capabilities eva-research-memory-v2": "research_memory.retrieve",
        "eva capability resource matrix": "Capability-resource matrix",
        "eva capabilities available": "Available capabilities",
        "eva capabilities preview only": "Preview-only capabilities",
        "eva capabilities blocked": "Blocked capabilities",
        "eva capability plan resources use my saved research about Eva": "Likely capability resources",
    }
    for command, expected in command_cases.items():
        handled = maybe_handle_fast_command(command, tools, {})
        text = handled[0] if handled else ""
        failures += emit(
            f"command_{re.sub(r'[^a-z0-9]+', '_', command.lower()).strip('_')}",
            handled is not None and expected in text and clean_output(text),
            output=text,
        )

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
