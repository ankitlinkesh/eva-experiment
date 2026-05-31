from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def emit(case: str, passed: bool, **payload: object) -> int:
    print(json.dumps({"case": case, "pass": passed, **payload}, indent=2, ensure_ascii=True))
    return 0 if passed else 1


def main() -> int:
    from backend.eva.api.routes import _handle_capability_route
    from backend.eva.core.fast_responses import maybe_handle_fast_response
    from backend.eva.core.intent_router import classify_capability_intent

    failures = 0

    architecture = classify_capability_intent("explain your full architecture", {})
    failures += emit(
        "architecture_classified",
        architecture.get("matched") is True
        and architecture.get("capability") == "self_architecture"
        and architecture.get("suggested_route") == "self_architecture_summary",
        result=architecture,
    )

    architecture_reply = _handle_capability_route("explain your full architecture", architecture, {}, None, "verify")
    grounded_text = architecture_reply[0] if architecture_reply else ""
    required_architecture_refs = (
        "frontend/index.html",
        "frontend/app.js",
        "frontend/styles.css",
        "backend/eva/main.py",
        "backend/eva/api/routes.py",
        "backend/eva/core/intent_router.py",
        "backend/eva/core/capabilities.py",
        "backend/eva/core/operator_commands.py",
        "backend/eva/agent/runner.py",
        "backend/eva/agent/planner.py",
        "backend/eva/agent/executor.py",
        "backend/eva/agent/cognition.py",
        "backend/eva/tools/registry.py",
        "backend/eva/llm/router.py",
        "backend/eva/llm/providers/nvidia_nim.py",
        "backend/eva/desktop/",
        "backend/eva/browser/",
        "backend/eva/research/",
        "backend/eva/code/",
        "backend/eva/workspace/",
        "backend/eva/vision/",
        "backend/eva/memory/",
        "backend/eva/data/research_knowledge.sqlite3",
        "memory SQLite",
        "backend/eva/data/code_index.json",
        "NVIDIA NIM -> Gemini -> OpenRouter -> Groq -> CLoD -> Ollama",
        ".env.local",
        "no arbitrary shell",
        "no camera",
        "screen only on request",
        "power actions require confirmation",
    )
    failures += emit(
        "architecture_route_grounded",
        all(token in grounded_text for token in required_architecture_refs)
        and "As an AI" not in grounded_text,
        missing=[token for token in required_architecture_refs if token not in grounded_text],
        snippet=grounded_text[:1000],
    )

    openrouter = classify_capability_intent("test OpenRouter API", {})
    failures += emit(
        "openrouter_provider_classified",
        openrouter.get("matched") is True
        and openrouter.get("capability") == "provider_diagnostics"
        and openrouter.get("provider") == "openrouter",
        result=openrouter,
    )

    correction_context = {"last_misinterpreted_topic": "openroute_maps"}
    corrected = classify_capability_intent("openrouter API is built in within u", correction_context)
    failures += emit(
        "openrouter_correction_classified",
        corrected.get("matched") is True
        and corrected.get("capability") == "provider_diagnostics"
        and corrected.get("provider") == "openrouter"
        and correction_context.get("last_misinterpreted_topic") is None,
        result=corrected,
        context=correction_context,
    )

    qa_after = classify_capability_intent("okay explain QA testing", correction_context)
    failures += emit(
        "correction_does_not_stick",
        qa_after.get("matched") is False,
        result=qa_after,
        context=correction_context,
    )

    page = classify_capability_intent("what page am I on", {})
    failures += emit(
        "browser_agent_classified",
        page.get("matched") is True
        and page.get("capability") == "browser_agent"
        and page.get("suggested_route") == "browser_current_page",
        result=page,
    )

    task_context_session: dict[str, object] = {}
    youtube = classify_capability_intent("play pavazhamalli from youtube", task_context_session)
    followup = classify_capability_intent("play it now", task_context_session)
    failures += emit(
        "followup_play_resolves_task_context",
        youtube.get("suggested_route") == "chrome_search_site"
        and followup.get("capability") == "browser_agent"
        and followup.get("site") == "youtube"
        and followup.get("query") == "pavazhamalli"
        and followup.get("play") is True,
        youtube=youtube,
        followup=followup,
    )

    github_context: dict[str, object] = {}
    github = classify_capability_intent("search GitHub for AI agents", github_context)
    verify = classify_capability_intent("can u verify the results", github_context)
    failures += emit(
        "verify_results_resolves_browser_target",
        github.get("suggested_route") == "chrome_search_site"
        and verify.get("suggested_route") == "verify_browser_target"
        and verify.get("target_domain") == "github.com",
        github=github,
        verify=verify,
    )

    window = classify_capability_intent("what window am I on", {})
    failures += emit(
        "desktop_agent_classified",
        window.get("matched") is True
        and window.get("capability") == "desktop_agent"
        and window.get("suggested_route") == "window_active",
        result=window,
    )

    failures += emit(
        "casual_stays_fast",
        maybe_handle_fast_response("howdy") is not None and classify_capability_intent("howdy", {}).get("matched") is False,
    )

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
