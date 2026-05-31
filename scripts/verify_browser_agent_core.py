from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.eva.agent.executor import ToolExecutor
from backend.eva.browser.safety import normalize_public_url
from backend.eva.core.fast_commands import maybe_handle_fast_command
from backend.eva.core.operator_commands import handle_operator_command
from backend.eva.core.web_context import remember_web_results
from backend.eva.tools.registry import ToolRegistry


MOCK_RESULTS = {
    "ok": True,
    "provider": "tavily",
    "query": "browser agent",
    "results": [
        {
            "title": "Browser Agent Repo",
            "url": "https://github.com/example/browser-agent",
            "content": "A useful browser agent source.",
        },
        {
            "title": "Browser Agent Docs",
            "url": "https://example.com/browser-agent-docs",
            "content": "Documentation for a browser agent.",
        },
    ],
}


class DryRegistry(ToolRegistry):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[dict[str, Any]] = []

    def run(self, name: str, **kwargs: Any) -> Any:
        self.calls.append({"tool": name, "args": kwargs})
        if name == "browser_status":
            return {"ok": True, "browser_detected": True, "active_window_title": "Example Page - Google Chrome"}
        if name == "browser_open_url":
            if not kwargs.get("url") or str(kwargs.get("url")).lower().startswith("javascript:"):
                return super().run(name, **kwargs)
            return {"ok": True, "url": kwargs.get("url"), "opened": True, "verified": True}
        if name == "browser_search":
            return {
                "ok": True,
                "query": kwargs.get("query"),
                "opened": True,
                "results": MOCK_RESULTS["results"],
                "browser_url": "https://www.google.com/search?q=browser+agent",
            }
        if name == "browser_current_page":
            return {
                "ok": True,
                "current_title": "Example Page",
                "current_url": "https://example.com/page",
                "active_window_title": "Example Page - Google Chrome",
                "notes": [],
            }
        if name == "browser_summarize_page":
            if kwargs.get("url"):
                return super().run(name, **kwargs)
            return {
                "ok": True,
                "current_title": "Example Page",
                "current_url": "https://example.com/page",
                "page_summary": "Example Page explains browser agents.",
                "notes": [],
            }
        if name == "browser_extract_links":
            return {
                "ok": True,
                "current_url": "https://example.com/page",
                "extracted_links": [{"text": "Docs", "url": "https://example.com/docs"}],
            }
        if name == "browser_save_page_to_research":
            return {
                "ok": True,
                "topic": kwargs.get("topic"),
                "saved_count": 1,
                "saved_results": [{"title": "Example Page", "url": "https://example.com/page"}],
            }
        if name == "browser_observe":
            return {
                "ok": True,
                "browser_detected": True,
                "active_window_title": "Example Page - Google Chrome",
                "current_url": "https://example.com/page",
                "current_title": "Example Page",
                "tabs": [{"title": "Example Page", "url": None}],
                "page_summary": None,
                "extracted_links": [{"text": "Docs", "url": "https://example.com/docs"}],
                "notes": ["No private browser storage accessed."],
            }
        if name == "open_url":
            return f"Opening {kwargs.get('url')}."
        return super().run(name, **kwargs)


def emit(case: str, passed: bool, **payload: Any) -> int:
    print(json.dumps({"case": case, "pass": passed, **payload}, indent=2, ensure_ascii=False))
    return 0 if passed else 1


def main() -> int:
    failures = 0
    registry = DryRegistry()
    executor = ToolExecutor(registry)
    session_context: dict[str, Any] = {}

    status = registry.run("browser_status")
    failures += emit(
        "browser_status_safe_object",
        isinstance(status, dict) and "ok" in status and "browser_detected" in status,
        result=status,
    )

    safe_open = registry.run("browser_open_url", url="https://example.com")
    failures += emit(
        "browser_open_url_accepts_safe_url",
        isinstance(safe_open, dict) and safe_open.get("ok") is True,
        result=safe_open,
    )

    failures += emit(
        "browser_open_url_refuses_empty_url",
        _raises(lambda: registry.run("browser_open_url", url="")),
        calls=registry.calls[-2:],
    )

    failures += emit(
        "browser_open_url_refuses_unsafe_scheme",
        _raises(lambda: registry.run("browser_open_url", url="javascript:alert(1)")),
        calls=registry.calls[-2:],
    )

    failures += emit(
        "browser_url_normalizer_refuses_non_http_scheme",
        _raises(lambda: normalize_public_url("file:///C:/Users/HP/.env")),
    )

    registry.calls.clear()
    search = registry.run("browser_search", query="browser agent")
    failures += emit(
        "browser_search_maps_query_safely",
        bool(isinstance(search, dict) and search.get("ok") and search.get("query") == "browser agent"),
        result=search,
        calls=registry.calls,
    )

    registry.calls.clear()
    page = maybe_handle_fast_command("what page am I on", registry, session_context)
    failures += emit(
        "what_page_routes_current_page",
        bool(page and registry.calls and registry.calls[-1]["tool"] == "browser_current_page"),
        response=page,
        calls=registry.calls,
    )

    failures += emit(
        "current_page_reports_safe_url_context",
        bool(page and "https://example.com/page" in str(page[0])),
        response=page,
    )

    registry.calls.clear()
    summary = maybe_handle_fast_command("summarize this page", registry, session_context)
    failures += emit(
        "summarize_this_page_routes_summarize",
        bool(summary and registry.calls and registry.calls[-1]["tool"] == "browser_summarize_page"),
        response=summary,
        calls=registry.calls,
    )

    registry.calls.clear()
    save = maybe_handle_fast_command("save this page to research topic test browser", registry, session_context)
    failures += emit(
        "save_page_routes_research_save",
        bool(save and registry.calls and registry.calls[-1]["tool"] == "browser_save_page_to_research" and registry.calls[-1]["args"].get("topic") == "test browser"),
        response=save,
        calls=registry.calls,
    )

    remember_web_results(session_context, MOCK_RESULTS)
    registry.calls.clear()
    opened = handle_operator_command("open first result", {"registry": registry, "executor": executor, "session_context": session_context})
    failures += emit(
        "open_first_result_still_uses_last_web_results",
        bool(opened and opened.get("tool") == "open_url" and opened.get("args", {}).get("url") == "https://github.com/example/browser-agent"),
        result=opened,
        calls=registry.calls,
    )

    private = registry.run("browser_summarize_page", url="https://accounts.google.com/signin")
    failures += emit(
        "private_sensitive_page_returns_safe_limitation",
        bool(isinstance(private, dict) and private.get("ok") is False and private.get("safety_blocked") is True),
        result=private,
    )

    failures += emit(
        "no_cookie_token_password_fields",
        _no_sensitive_keys(registry.run("browser_observe", include_tabs=True, include_links=True)),
    )

    registry.calls.clear()
    shutdown = handle_operator_command("shutdown my laptop", {"registry": registry, "executor": executor, "session_context": session_context})
    failures += emit(
        "shutdown_still_requires_confirmation",
        bool(shutdown and shutdown.get("requires_confirmation") is True and shutdown.get("action") == "shutdown" and not registry.calls),
        result=shutdown,
        calls=registry.calls,
    )

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


def _raises(func: Any) -> bool:
    try:
        func()
    except Exception:
        return True
    return False


def _no_sensitive_keys(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False).lower()
    banned = ("cookie", "token", "password", "authorization", "bearer")
    return not any(word in text for word in banned)


if __name__ == "__main__":
    raise SystemExit(main())
