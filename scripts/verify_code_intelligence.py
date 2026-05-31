from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.eva.code import (  # noqa: E402
    build_code_index,
    code_project_map,
    code_status,
    debug_traceback,
    find_symbol,
    plan_code_change,
)
from backend.eva.code.skills import code_explain_feature  # noqa: E402
from backend.eva.workspace.reader import safe_read_file  # noqa: E402


def check(name: str, condition: bool, detail: str = "") -> None:
    prefix = "PASS" if condition else "FAIL"
    print(f"{prefix}: {name}{' - ' + detail if detail else ''}")
    if not condition:
        raise SystemExit(1)


def contains_path(index: dict, fragment: str) -> bool:
    return any(fragment.replace("\\", "/") in str(item.get("path") or "") for item in index.get("files", []) if isinstance(item, dict))


def no_secret_markers(index: dict) -> bool:
    raw = json.dumps(index)
    forbidden = ("AIza", "nvapi-", "sk-or-v1-", "TAVILY_API_KEY", "NVIDIA_NIM_API_KEY")
    return not any(marker in raw for marker in forbidden)


def main() -> None:
    print("== Code Intelligence verifier ==")
    status_before = code_status()
    check("code_status returns ok", bool(status_before.get("ok")))

    index = build_code_index()
    check("reindex_code ok", bool(index.get("ok")), str(index.get("error") or ""))
    index_path = ROOT / "backend" / "eva" / "data" / "code_index.json"
    check("code_index.json created", index_path.exists(), str(index_path))

    required_paths = [
        "backend/eva/agent/runner.py",
        "backend/eva/llm/router.py",
        "backend/eva/tools/registry.py",
        "backend/eva/browser",
        "backend/eva/desktop",
        "frontend/app.js",
    ]
    for fragment in required_paths:
        check(f"index includes {fragment}", contains_path(index, fragment))

    symbol = find_symbol("run_agentic_task")
    symbol_paths = [str(item.get("path") or "") for item in symbol.get("matches", []) if isinstance(item, dict)]
    check("find symbol run_agentic_task", any("backend/eva/agent/runner.py" in path for path in symbol_paths), ", ".join(symbol_paths[:3]))

    nim = code_explain_feature("NIM provider implemented")
    nim_files = " ".join(str(path) for path in nim.get("related_files", []))
    check("NIM provider lookup includes nvidia_nim.py", "nvidia_nim.py" in nim_files, nim_files[:240])
    check("NIM provider lookup includes router.py", "router.py" in nim_files, nim_files[:240])

    browser = code_explain_feature("Browser Agent implemented")
    browser_files = " ".join(str(path) for path in browser.get("related_files", []))
    check("Browser Agent lookup includes backend/eva/browser", "backend/eva/browser" in browser_files, browser_files[:240])

    fake_traceback = (
        'Traceback (most recent call last):\n'
        '  File "C:\\Users\\HP\\Documents\\Codex\\eva-agent\\backend\\eva\\agent\\runner.py", line 10, in run_agentic_task\n'
        "    raise ValueError('bad planner result')\n"
        "ValueError: bad planner result\n"
    )
    debug = debug_traceback(fake_traceback)
    check("debug traceback parses exception", debug.get("exception_type") == "ValueError", str(debug.get("exception_type")))
    check("debug traceback extracts runner.py", any("backend/eva/agent/runner.py" in str(path) for path in debug.get("likely_files", [])))

    plan = plan_code_change("make Eva summarize browser pages better")
    check("plan change returns files", bool(plan.get("likely_files")))
    check("plan change returns steps", bool(plan.get("proposed_steps")))
    check("plan change returns risks", bool(plan.get("risks")))

    forbidden = safe_read_file(".env")
    check("forbidden .env refused", not forbidden.get("ok") and bool(forbidden.get("refused")), str(forbidden.get("error") or ""))
    traversal = safe_read_file("../../.env")
    check("path traversal refused", not traversal.get("ok") and bool(traversal.get("refused")), str(traversal.get("error") or ""))

    check("index does not contain obvious API key markers", no_secret_markers(index))
    print("Code Intelligence verifier complete.")


if __name__ == "__main__":
    main()
