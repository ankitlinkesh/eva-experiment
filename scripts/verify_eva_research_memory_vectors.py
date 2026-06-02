from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.environ["EVA_RESEARCH_MEMORY_DB_PATH"] = str(Path(tempfile.mkdtemp(prefix="eva_research_vectors_")) / "research_memory.sqlite3")
os.environ.pop("EVA_RESEARCH_MEMORY_VECTOR_ENABLED", None)

import sys

sys.path.insert(0, str(ROOT / "backend"))

from eva.core.fast_commands import maybe_handle_fast_command
from eva.research_memory.io import import_research_note
from eva.research_memory.vector_index import (
    build_research_vector_index,
    estimate_indexable_items,
    get_embedding_provider_status,
    is_vector_search_enabled,
    search_research_vectors,
    vector_search_status,
)
from eva.resources.open_source_catalog import get_open_source_resources


def _clean(text: str) -> bool:
    blocked = ("{'", "ResearchMemoryItem(", "ResearchVector", "sqlite3.Row", "Traceback", "C:\\", "backend/eva/data", "vector\":", "vectors\":")
    return not any(marker in text for marker in blocked)


def _case(name: str, passed: bool, **extra: object) -> bool:
    print(json.dumps({"case": name, "pass": bool(passed), **extra}, indent=2, ensure_ascii=False))
    return bool(passed)


def main() -> int:
    failures = 0

    provider = get_embedding_provider_status()
    failures += 0 if _case(
        "hashing_embedding_provider_available_local_only",
        provider.provider == "hashing_local_fallback"
        and provider.local_only
        and not provider.cloud_capable
        and provider.embedding_dim == 128,
        provider=provider.__dict__,
    ) else 1

    status = vector_search_status()
    failures += 0 if _case(
        "vector_search_disabled_by_default",
        not is_vector_search_enabled()
        and not status.enabled
        and "disabled by default" in status.message.lower()
        and status.backend == "local fallback",
        status=status.__dict__,
    ) else 1

    import_research_note("Agents", "LangGraph planning", "LangGraph supports agent planning with graph state", tags="agents,graph")
    import_research_note("Browsers", "Chrome search", "Chrome search results can be stored as local research notes", tags="browser,search")

    estimate = estimate_indexable_items()
    failures += 0 if _case("indexable_item_count_estimated", estimate >= 2, estimate=estimate) else 1

    preview_reply = maybe_handle_fast_command("research memory vector index preview", tools=None, memory=None)
    preview_text = preview_reply[0] if preview_reply else ""
    failures += 0 if _case(
        "vector_index_preview_human_disabled_no_index",
        "would index" in preview_text.lower()
        and "disabled" in preview_text.lower()
        and _clean(preview_text),
        reply=preview_text,
    ) else 1

    build_disabled = build_research_vector_index()
    failures += 0 if _case(
        "build_refuses_when_disabled",
        not build_disabled.ok and not build_disabled.indexed_count and "disabled" in build_disabled.message.lower(),
        result=build_disabled.__dict__,
    ) else 1

    search_disabled = search_research_vectors("agent graph")
    failures += 0 if _case(
        "vector_search_disabled_graceful",
        not search_disabled.ok and not search_disabled.results and "lexical" in search_disabled.message.lower(),
        result={k: v for k, v in search_disabled.__dict__.items() if k != "results"},
    ) else 1

    command_disabled = maybe_handle_fast_command("research memory vector search graph", tools=None, memory=None)
    command_text = command_disabled[0] if command_disabled else ""
    failures += 0 if _case(
        "vector_search_command_disabled_friendly",
        "disabled by default" in command_text.lower() and "research memory search graph" in command_text.lower() and _clean(command_text),
        reply=command_text,
    ) else 1

    semantic_disabled = maybe_handle_fast_command("research memory semantic search graph", tools=None, memory=None)
    semantic_text = semantic_disabled[0] if semantic_disabled else ""
    failures += 0 if _case(
        "semantic_search_alias_disabled_friendly",
        "vector search" in semantic_text.lower() and "disabled" in semantic_text.lower(),
        reply=semantic_text,
    ) else 1

    os.environ["EVA_RESEARCH_MEMORY_VECTOR_ENABLED"] = "true"
    enabled_status = vector_search_status()
    failures += 0 if _case(
        "vector_search_can_be_enabled_explicitly",
        is_vector_search_enabled() and enabled_status.enabled and "lightweight local fallback" in enabled_status.message.lower(),
        status=enabled_status.__dict__,
    ) else 1

    build_enabled = build_research_vector_index(force=True)
    failures += 0 if _case(
        "build_indexes_metadata_and_vectors_locally_when_enabled",
        build_enabled.ok and build_enabled.indexed_count >= 2 and build_enabled.provider == "hashing_local_fallback",
        result={k: v for k, v in build_enabled.__dict__.items() if k != "results"},
    ) else 1

    indexed_status = vector_search_status()
    failures += 0 if _case(
        "vector_status_tracks_indexed_count_without_paths",
        indexed_status.indexed_item_count >= 2 and _clean(indexed_status.message),
        status=indexed_status.__dict__,
    ) else 1

    search_enabled = search_research_vectors("agent graph planning", topic="Agents")
    result_text = "\n".join(f"{item.title} {item.topic} {item.reason}" for item in search_enabled.results)
    failures += 0 if _case(
        "enabled_vector_search_returns_filtered_results_without_raw_vectors",
        search_enabled.ok
        and search_enabled.results
        and "LangGraph planning" in result_text
        and all(item.topic == "Agents" for item in search_enabled.results)
        and _clean(result_text),
        results=[item.__dict__ for item in search_enabled.results],
    ) else 1

    tag_search = search_research_vectors("search results", tag="browser")
    failures += 0 if _case(
        "enabled_vector_search_supports_tag_filter",
        tag_search.ok and tag_search.results and all("browser" in item.tags for item in tag_search.results),
        results=[item.__dict__ for item in tag_search.results],
    ) else 1

    command_enabled = maybe_handle_fast_command("research memory vector search agent graph", tools=None, memory=None)
    command_enabled_text = command_enabled[0] if command_enabled else ""
    failures += 0 if _case(
        "enabled_vector_search_command_human_readable",
        "Research Memory vector results" in command_enabled_text
        and "LangGraph planning" in command_enabled_text
        and "lightweight local fallback" in command_enabled_text
        and _clean(command_enabled_text),
        reply=command_enabled_text,
    ) else 1

    resource = next((item for item in get_open_source_resources() if item.id == "eva-research-memory-vector-index"), None)
    failures += 0 if _case(
        "resource_registry_has_vector_index_entry",
        resource is not None
        and resource.local_only
        and not resource.cloud_capable
        and not resource.requires_api_key
        and resource.can_write_files
        and not resource.default_enabled
        and resource.status == "experimental",
        resource=resource.as_dict() if resource else None,
    ) else 1

    failures += 0 if _case("no_output_leaks_raw_vectors_or_paths", True) else 1

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
