from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.eva.agent.executor import ToolExecutor
from backend.eva.core.operator_commands import handle_operator_command
from backend.eva.core.web_context import remember_web_results
import backend.eva.tools.desktop as desktop
from backend.eva.tools.registry import ToolRegistry


MOCK_RESULTS = {
    "ok": True,
    "provider": "tavily",
    "query": "Ankit L profile",
    "results": [
        {
            "title": "Ankit L - GitHub",
            "url": "https://github.com/example-ankit-l",
            "content": "Possible GitHub profile.",
        },
        {
            "title": "Ankit L on Instagram",
            "url": "https://www.instagram.com/example_ankit_l/",
            "content": "Possible Instagram profile.",
        },
    ],
}


class DryRegistry(ToolRegistry):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[dict[str, Any]] = []

    def run(self, name: str, **kwargs: Any) -> Any:
        self.calls.append({"tool": name, "args": kwargs})
        if name == "open_app":
            return f"Opening {kwargs.get('app') or kwargs.get('app_name')}."
        if name == "close_app":
            return super().run(name, **kwargs)
        if name == "open_folder":
            return f"Opening folder {kwargs.get('folder') or kwargs.get('folder_name')}."
        if name == "open_url":
            return f"Opening {kwargs.get('url')}."
        if name == "web_search":
            return {
                "ok": True,
                "provider": "tavily",
                "query": kwargs.get("query", ""),
                "answer": "Mock search answer.",
                "results": MOCK_RESULTS["results"],
            }
        if name == "media_control":
            return f"Media {kwargs.get('action')}."
        if name == "lock_laptop":
            return "Locked."
        if name == "analyze_screen":
            return {"ok": True, "summary": "A browser window is open.", "suggested_actions": ["Continue in the browser."]}
        return super().run(name, **kwargs)


def emit(case: str, passed: bool, **payload: Any) -> int:
    print(json.dumps({"case": case, "pass": passed, **payload}, indent=2, ensure_ascii=False))
    return 0 if passed else 1


def run_case(message: str, context: dict[str, Any]) -> dict[str, Any] | None:
    return handle_operator_command(message, context)


def main() -> int:
    failures = 0
    previous_allowlist = os.environ.get("EVA_CLOSE_APP_ALLOWLIST")
    os.environ["EVA_CLOSE_APP_ALLOWLIST"] = "calculator,chrome,discord,edge,notepad,spotify,vscode,codex,terminal,powershell,word,excel,powerpoint"
    original_subprocess_run = desktop.subprocess.run
    kill_calls: list[list[str]] = []

    class FakeCompletedProcess:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_subprocess_run(command: list[str], *args: Any, **kwargs: Any) -> FakeCompletedProcess:
        kill_calls.append(command)
        return FakeCompletedProcess()

    desktop.subprocess.run = fake_subprocess_run  # type: ignore[assignment]
    registry = DryRegistry()
    executor = ToolExecutor(registry)
    session_context: dict[str, Any] = {}
    context = {"registry": registry, "executor": executor, "session_context": session_context}

    checks = [
        ("open_chrome", "open chrome", "open_app", {"app": "chrome"}),
        ("open_downloads", "open downloads", "open_folder", {"folder": "downloads"}),
        ("volume_up", "volume up", "media_control", {"action": "volume_up"}),
        ("mute", "mute", "media_control", {"action": "mute"}),
        ("play_pause", "play pause", "media_control", {"action": "play_pause"}),
        ("search_web", "search web for AI agents", "web_search", {"query": "AI agents"}),
        ("show_screen", "show screen", "analyze_screen", {"question": "show screen"}),
    ]
    try:
        for case_name, message, expected_tool, expected_args in checks:
            registry.calls.clear()
            result = run_case(message, context)
            failures += emit(
                case_name,
                bool(result and result.get("handled") and result.get("tool") == expected_tool and result.get("args") == expected_args),
                result=result,
                calls=registry.calls,
            )

        # Phase 82: closing an ALLOWLISTED app now asks first (it can discard
        # unsaved work), so the operator surfaces a confirmation and does NOT
        # kill until the user confirms.
        for case_name, message in (
            ("close_chrome_asks_first", "close chrome"),
            ("close_notepad_asks_first", "close notepad"),
        ):
            registry.calls.clear()
            kill_calls.clear()
            result = run_case(message, context)
            failures += emit(
                case_name,
                bool(
                    result
                    and result.get("tool") == "close_app"
                    and result.get("requires_confirmation") is True
                    and not kill_calls
                ),
                result=result,
                calls=registry.calls,
                kill_calls=kill_calls,
            )

        # A non-allowlisted or system app is refused BEFORE the gate (Phase 82 /
        # Phase 74 lesson): it is not asked to be confirmed only to be rejected.
        for case_name, message in (
            ("close_unknown_refused", "close unknownapp"),
            ("close_system_refused", "close system process"),
        ):
            registry.calls.clear()
            kill_calls.clear()
            result = run_case(message, context)
            failures += emit(
                case_name,
                bool(
                    result
                    and result.get("tool") == "close_app"
                    and not result.get("requires_confirmation")
                    and "safe close allowlist" in result.get("response", "")
                    and not kill_calls
                ),
                result=result,
                calls=registry.calls,
                kill_calls=kill_calls,
            )

        registry.calls.clear()
        shutdown = run_case("shutdown my laptop", context)
        failures += emit(
            "shutdown_requires_confirmation",
            bool(
                shutdown
                and shutdown.get("requires_confirmation") is True
                and shutdown.get("action") == "shutdown"
                and not registry.calls
            ),
            result=shutdown,
            calls=registry.calls,
        )

        remember_web_results(session_context, MOCK_RESULTS)
        registry.calls.clear()
        first = run_case("open first result", context)
        failures += emit(
            "open_first_result_from_context",
            bool(first and first.get("tool") == "open_url" and first.get("args", {}).get("url") == "https://github.com/example-ankit-l"),
            result=first,
            calls=registry.calls,
        )

        registry.calls.clear()
        instagram = run_case("open the Instagram one", context)
        failures += emit(
            "open_instagram_result_from_context",
            bool(instagram and instagram.get("tool") == "open_url" and instagram.get("args", {}).get("url") == "https://www.instagram.com/example_ankit_l/"),
            result=instagram,
            calls=registry.calls,
        )

        registry.calls.clear()
        profile = run_case("open my profile", {"registry": registry, "executor": executor, "session_context": {}})
        failures += emit(
            "open_my_profile_missing_url_asks",
            bool(profile and not profile.get("tool") and "don't have your profile URL saved" in profile.get("response", "")),
            result=profile,
            calls=registry.calls,
        )

        registry.calls.clear()
        status = run_case("operator status", context)
        failures += emit(
            "operator_status",
            bool(
                status
                and "Operator mode:" in status.get("response", "")
                and "confirmation required" in status.get("response", "")
                and "Close-app allowlist:" in status.get("response", "")
                and "codex" in status.get("response", "")
            ),
            result=status,
            calls=registry.calls,
        )
    finally:
        desktop.subprocess.run = original_subprocess_run  # type: ignore[assignment]
        if previous_allowlist is None:
            os.environ.pop("EVA_CLOSE_APP_ALLOWLIST", None)
        else:
            os.environ["EVA_CLOSE_APP_ALLOWLIST"] = previous_allowlist

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
