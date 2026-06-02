from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.environ["EVA_RESEARCH_MEMORY_DB_PATH"] = str(Path(tempfile.mkdtemp(prefix="eva_research_context_")) / "research_memory.sqlite3")
os.environ.pop("EVA_RESEARCH_MEMORY_VECTOR_ENABLED", None)

import sys

sys.path.insert(0, str(ROOT / "backend"))

from eva.core.fast_commands import maybe_handle_fast_command
from eva.research_memory.context import (
    build_research_context_for_request,
    format_research_context_for_state,
    should_use_research_memory_context,
)
from eva.research_memory.io import import_research_note
from eva.runtime.graph import run_eva_v2_dry_run, run_eva_v2_execute, run_eva_v2_plan_preview


def _clean(value: object) -> bool:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    blocked = ("{'", "ResearchMemoryItem(", "ResearchSearchResult(", "sqlite3.Row", "Traceback", "C:\\", "backend/eva/data", "vector_json", "raw vector")
    return not any(marker in text for marker in blocked)


def _case(name: str, passed: bool, **extra: object) -> bool:
    print(json.dumps({"case": name, "pass": bool(passed), **extra}, indent=2, ensure_ascii=False))
    return bool(passed)


def main() -> int:
    failures = 0

    failures += 0 if _case("context_module_imports", callable(build_research_context_for_request)) else 1
    failures += 0 if _case("saved_research_phrase_true", should_use_research_memory_context("use my saved research about Eva")) else 1
    failures += 0 if _case("what_did_i_save_true", should_use_research_memory_context("what did I save about MCP")) else 1
    failures += 0 if _case("generic_chrome_false", not should_use_research_memory_context("open ChatGPT on Chrome")) else 1

    import_research_note("Eva", "Eva vector search", "Eva Research Memory vector search is disabled by default and uses local fallback prep only.", tags="eva,vector")
    import_research_note("MCP", "MCP safety", "MCP execution remains disabled by default; resources are cataloged for planning only.", tags="mcp,safety")
    import_research_note("Playwright", "Playwright safety", "Playwright execution is disabled by default and cannot read cookies or localStorage.", tags="playwright,browser")

    context = build_research_context_for_request("use my saved research about Eva vector search", limit=3)
    failures += 0 if _case(
        "context_builder_returns_compact_summaries",
        bool(context) and len(context) <= 3 and "Eva vector search" in json.dumps(context),
        context=context,
    ) else 1
    failures += 0 if _case(
        "context_uses_retrieval_not_raw_rows",
        all("match" in item and "summary" in item and "topic" in item for item in context),
        context=context,
    ) else 1
    failures += 0 if _case(
        "context_includes_metadata",
        any(item.get("tags") and item.get("source_type") and item.get("match") for item in context),
        context=context,
    ) else 1
    failures += 0 if _case("compact_context_no_internal_paths", _clean(context), context=context) else 1
    failures += 0 if _case("compact_context_no_raw_dict_repr", "{'" not in format_research_context_for_state(context)) else 1
    failures += 0 if _case("compact_context_no_dataclass_repr", "ResearchMemoryItem(" not in format_research_context_for_state(context)) else 1
    failures += 0 if _case("compact_context_no_sqlite_repr", "sqlite3.Row" not in format_research_context_for_state(context)) else 1

    plan = run_eva_v2_plan_preview("use my Eva research memory to explain vector search")
    failures += 0 if _case(
        "v2_plan_includes_relevant_local_research_memory",
        "Relevant local research memory:" in plan.final_response and "Eva vector search" in plan.final_response,
        response=plan.final_response,
        relevant_memory=plan.relevant_memory,
    ) else 1

    dry = run_eva_v2_dry_run("summarize what I saved about Eva")
    failures += 0 if _case(
        "v2_dry_run_includes_relevant_local_research_memory",
        "Relevant local research memory:" in dry.final_response and "Eva vector search" in dry.final_response,
        response=dry.final_response,
    ) else 1

    unrelated = run_eva_v2_plan_preview("open ChatGPT on Chrome")
    failures += 0 if _case(
        "unrelated_v2_plan_no_research_memory_section",
        "Relevant local research memory:" not in unrelated.final_response and not unrelated.relevant_memory,
        response=unrelated.final_response,
    ) else 1

    missing = run_eva_v2_plan_preview("use my saved research about quantum bananas")
    failures += 0 if _case(
        "no_matching_memory_friendly",
        "Relevant local research memory:" in missing.final_response and "No matching saved research found." in missing.final_response,
        response=missing.final_response,
        relevant_memory=missing.relevant_memory,
    ) else 1

    dump = run_eva_v2_plan_preview("dump all my research memory")
    failures += 0 if _case(
        "full_dump_request_refused_or_redirected",
        "full dump" in dump.final_response.lower()
        and "research memory export" in dump.final_response.lower()
        and "No action was executed." in dump.final_response,
        response=dump.final_response,
    ) else 1

    execute_retrieve = run_eva_v2_execute("research memory retrieve Eva")
    failures += 0 if _case(
        "v2_execute_research_memory_retrieve_still_works",
        "Research Memory retrieval results" in execute_retrieve.final_response and "Eva vector search" in execute_retrieve.final_response,
        response=execute_retrieve.final_response,
    ) else 1

    execute_status = run_eva_v2_execute("research memory retrieval status")
    failures += 0 if _case(
        "v2_execute_retrieval_status_still_works",
        "hybrid retrieval status" in execute_status.final_response.lower(),
        response=execute_status.final_response,
    ) else 1

    normal = maybe_handle_fast_command("open ChatGPT on Chrome", tools=None, memory=None)
    failures += 0 if _case("normal_fast_command_not_v2_memory_injected", normal is None or "Relevant local research memory" not in normal[0]) else 1

    all_text = "\n".join([format_research_context_for_state(context), plan.final_response, dry.final_response, unrelated.final_response, missing.final_response, dump.final_response, execute_retrieve.final_response])
    failures += 0 if _case("all_outputs_clean", _clean(all_text)) else 1

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
