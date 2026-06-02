from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.environ["EVA_RESEARCH_MEMORY_DB_PATH"] = str(Path(tempfile.mkdtemp(prefix="eva_research_retrieval_")) / "research_memory.sqlite3")
os.environ.pop("EVA_RESEARCH_MEMORY_VECTOR_ENABLED", None)

import sys

sys.path.insert(0, str(ROOT / "backend"))

from eva.core.fast_commands import maybe_handle_fast_command
from eva.research_memory.io import import_research_note
from eva.research_memory.models import ResearchMemoryItem
from eva.research_memory.retrieval import (
    explain_retrieval_plan,
    format_retrieval_results,
    rank_research_results,
    retrieval_status,
    retrieve_research,
)
from eva.research_memory.store import add_research_item, list_research_items
from eva.runtime.graph import run_eva_v2_execute, run_eva_v2_plan_preview


def _clean(text: str) -> bool:
    blocked = ("{'", "ResearchMemoryItem(", "RetrievalResult(", "sqlite3.Row", "Traceback", "C:\\", "backend/eva/data", "vector_json", "raw vector")
    return not any(marker in str(text) for marker in blocked)


def _case(name: str, passed: bool, **extra: object) -> bool:
    print(json.dumps({"case": name, "pass": bool(passed), **extra}, indent=2, ensure_ascii=False))
    return bool(passed)


def main() -> int:
    failures = 0

    failures += 0 if _case("retrieval_module_imports", callable(retrieve_research)) else 1

    add_research_item(
        ResearchMemoryItem(
            id="",
            topic="Agents",
            title="High quality agent planning",
            summary="LangGraph agent planning uses typed graph state, checkpoints, and verifier loops for reliable agent workflows.",
            content_preview="LangGraph agent planning uses typed graph state, checkpoints, and verifier loops for reliable agent workflows.",
            source_type="imported_note",
            tags=["agents", "planner"],
            confidence="high",
            quality_score=0.96,
            provenance="verifier",
        )
    )
    add_research_item(
        ResearchMemoryItem(
            id="",
            topic="Agents",
            title="Tiny",
            summary="agent graph",
            content_preview="agent graph",
            source_type="imported_note",
            tags=["agents", "tiny"],
            confidence="medium",
            quality_score=0.25,
            quality_warnings=["very short note"],
            provenance="verifier",
        )
    )
    import_research_note("Browsers", "Chrome retrieval", "Chrome search results can be saved as local research notes", tags="browser,search")
    import_research_note("Dupes", "Duplicate A", "same duplicate note for retrieval planner", tags="dupe")
    import_research_note("Dupes", "Duplicate B", "same duplicate note for retrieval planner", tags="dupe")

    status = retrieval_status()
    failures += 0 if _case(
        "retrieval_status_human_readable",
        "hybrid retrieval" in status.lower() and "lexical baseline" in status.lower() and _clean(status),
        status=status,
    ) else 1

    baseline = retrieve_research("agent planning", limit=3)
    failures += 0 if _case(
        "retrieval_works_with_lexical_baseline",
        baseline.results and baseline.results[0].title == "High quality agent planning" and baseline.mode == "local_hybrid",
        results=[item.__dict__ for item in baseline.results],
    ) else 1

    topic = retrieve_research("agent planning", topic="Agents", limit=5)
    failures += 0 if _case(
        "retrieval_topic_filter_works",
        topic.results and all(item.topic == "Agents" for item in topic.results),
        results=[item.__dict__ for item in topic.results],
    ) else 1

    tag = retrieve_research("search results", tag="browser", limit=5)
    failures += 0 if _case(
        "retrieval_tag_filter_works",
        tag.results and all("browser" in item.tags for item in tag.results),
        results=[item.__dict__ for item in tag.results],
    ) else 1

    source = retrieve_research("Chrome", source_type="imported_note", limit=5)
    failures += 0 if _case(
        "retrieval_source_filter_works",
        source.results and all(item.source_type == "imported_note" for item in source.results),
        results=[item.__dict__ for item in source.results],
    ) else 1

    ranked = rank_research_results(list_research_items(limit=10), "agent planning")
    failures += 0 if _case(
        "ranking_boosts_higher_quality_items",
        ranked and ranked[0].title == "High quality agent planning",
        ranked=[item.title for item in ranked[:4]],
    ) else 1

    dupes = retrieve_research("duplicate retrieval", tag="dupe", limit=5)
    duplicate_marked = any("duplicate-like" in item.quality_warnings for item in dupes.results)
    failures += 0 if _case(
        "duplicate_like_items_marked_deprioritized_not_deleted",
        len(dupes.results) >= 1 and duplicate_marked and len(list_research_items(topic="Dupes", limit=10)) == 2,
        results=[item.__dict__ for item in dupes.results],
    ) else 1

    plan = explain_retrieval_plan("agent planning")
    failures += 0 if _case(
        "retrieval_plan_explains_lexical_and_vector_disabled",
        "lexical baseline" in plan.lower() and "vector search: disabled" in plan.lower() and _clean(plan),
        plan=plan,
    ) else 1

    command = maybe_handle_fast_command("research memory retrieve agent planning", tools=None, memory=None)
    command_text = command[0] if command else ""
    failures += 0 if _case(
        "retrieve_command_human_readable",
        "Research Memory retrieval results" in command_text and "High quality agent planning" in command_text and _clean(command_text),
        reply=command_text,
    ) else 1

    command_plan = maybe_handle_fast_command("research memory retrieval plan agent planning", tools=None, memory=None)
    command_plan_text = command_plan[0] if command_plan else ""
    failures += 0 if _case(
        "retrieval_plan_command_human_readable",
        "Research Memory retrieval plan" in command_plan_text and "lexical baseline" in command_plan_text.lower() and _clean(command_plan_text),
        reply=command_plan_text,
    ) else 1

    formatted = format_retrieval_results(baseline)
    failures += 0 if _case(
        "format_no_raw_reprs_paths_or_vectors",
        _clean(formatted) and "Match:" in formatted,
        formatted=formatted,
    ) else 1

    v2_plan = run_eva_v2_plan_preview("search research memory agent planning").final_response
    failures += 0 if _case(
        "research_agent_plan_mentions_hybrid_retrieval",
        "hybrid retrieval" in v2_plan.lower(),
        response=v2_plan,
    ) else 1

    v2_execute = run_eva_v2_execute("search research memory agent planning").final_response
    failures += 0 if _case(
        "readonly_delegation_uses_retrieval_layer",
        "Research Memory retrieval results" in v2_execute and "High quality agent planning" in v2_execute,
        response=v2_execute,
    ) else 1

    os.environ["EVA_RESEARCH_MEMORY_VECTOR_ENABLED"] = "true"
    enabled = retrieve_research("agent planning", limit=5)
    failures += 0 if _case(
        "vector_enabled_state_merges_gracefully",
        enabled.results and any("vector" in note.lower() for note in enabled.plan_notes),
        notes=enabled.plan_notes,
    ) else 1

    all_outputs = "\n".join([status, plan, command_text, command_plan_text, formatted, v2_plan, v2_execute])
    failures += 0 if _case("all_outputs_clean", _clean(all_outputs)) else 1

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
