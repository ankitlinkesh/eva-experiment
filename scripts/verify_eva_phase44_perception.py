"""Standalone verifier for Phase 44 (perception & grounding: situational model).

Proves, end to end and independent of pytest, that the opt-in situational model
(backend/eva/perception/situational_model.py) is correct AND actually wired into
the agent loop's grounding:

  1. Default OFF: perception_enabled() is False when the flag is unset, and the
     no-arg situational_summary() captures nothing.
  2. Metadata only + privacy: a foreground window with a sensitive title is
     redacted to "[private window]" and the raw title never appears; the
     open-apps list carries process names only, never titles.
  3. capture_situation reads window metadata (stubbed here for determinism),
     never pixels, and is fail-safe on a window-layer error.
  4. Agent-loop grounding via run_agentic_task + a capturing planner: an injected
     situation reaches task_context["situation"] and emits a "grounding" event;
     an injected sensitive title is redacted before the planner sees it; with
     perception off and no injection, the planner sees no situation and no
     grounding event is emitted (byte-identical).
  5. Source wiring: planner.py references "situation"; runner.py references
     _resolve_grounding.
  6. The new eval is registered and the whole offline suite stays green.
  7. This verifier is wired into scripts/verify_eva_all.py's profiles.

Fully offline and deterministic: no real windows, no network, no live LLM, and
every env var this file touches is restored in a ``finally`` block.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


class _CapturingPlanner:
    def __init__(self, decisions):
        self._decisions = list(decisions)
        self.calls = 0
        self.seen_situation = "unset"

    async def plan(self, goal, history, mode="agent_step", task_context=None):
        self.seen_situation = (task_context or {}).get("situation")
        decision = self._decisions[min(self.calls, len(self._decisions) - 1)]
        self.calls += 1
        return decision


def main() -> int:
    from backend.eva.agent.planner import PlannerDecision
    from backend.eva.agent.runner import run_agentic_task
    from backend.eva.evals import run_offline_evals
    from backend.eva.evals.offline_suite import offline_tasks
    from backend.eva.perception import situational_model as sm
    from backend.eva.perception.situational_model import (
        Situation,
        capture_situation,
        perception_enabled,
        situational_summary,
    )
    from backend.eva.tools.registry import ToolRegistry
    from scripts import verify_eva_all

    saved_env = {"EVA_PERCEPTION_ENABLED": os.environ.get("EVA_PERCEPTION_ENABLED")}

    try:
        # 1. Default OFF.
        os.environ.pop("EVA_PERCEPTION_ENABLED", None)
        check(perception_enabled() is False, "perception must be off by default")
        check(situational_summary() == "", "no-arg summary must be empty when perception is off")

        # 2. Metadata only + privacy redaction.
        sensitive = Situation(
            active_app="chrome.exe",
            active_title="MegaBank - Sign in",
            open_apps=["chrome.exe", "Code.exe"],
            window_count=2,
            captured_at="t",
        )
        summary = situational_summary(sensitive)
        check("[private window]" in summary, f"a sensitive foreground title must be redacted, got {summary!r}")
        check("MegaBank" not in summary, "a raw sensitive title must never appear in the summary")
        check("no screenshot" in summary.lower(), "the summary must make clear no screenshot was taken")

        # 3. capture_situation reads metadata (stubbed) and is fail-safe.
        import backend.eva.desktop.windows as win

        class _W:
            def __init__(self, title, process_name):
                self.title = title
                self.process_name = process_name

        real_active = win.get_active_window
        real_list = win.list_open_windows
        try:
            win.get_active_window = lambda: _W("First National Bank - Login", "chrome.exe")
            win.list_open_windows = lambda: [_W("First National Bank - Login", "chrome.exe"), _W("runner.py", "Code.exe")]
            snap = capture_situation()
            check(snap.active_app == "chrome.exe", f"active app must come from process metadata, got {snap.active_app!r}")
            check(snap.active_title == "[private window]", "a sensitive foreground title must be redacted at capture")
            check(snap.privacy_redacted is True, "capture must flag privacy redaction")
            check(snap.open_apps == ["chrome.exe", "Code.exe"], f"open apps must be distinct process names only, got {snap.open_apps!r}")
            check(all("Bank" not in app for app in snap.open_apps), "no window title may leak into the open-apps list")

            def _boom():
                raise RuntimeError("no windows")

            win.get_active_window = _boom
            failed = capture_situation()
            check(failed.available is False, "capture must fail safe to an unavailable situation on error")
        finally:
            win.get_active_window = real_active
            win.list_open_windows = real_list

        # 4. Agent-loop grounding.
        done = PlannerDecision(type="done", reason="x", tool_calls=[], final_response="ok", continue_after_tools=False)

        planner = _CapturingPlanner([done])
        result = asyncio.run(
            run_agentic_task(
                "do a thing",
                {"planner": planner, "registry": ToolRegistry(), "situation": Situation(active_app="Code.exe", active_title="runner.py", open_apps=["Code.exe", "chrome.exe"], window_count=2, captured_at="t"), "execute_tools": True},
            )
        )
        check(planner.seen_situation and "Code.exe" in planner.seen_situation, f"an injected situation must reach the planner, got {planner.seen_situation!r}")
        check(any(e.get("type") == "grounding" for e in result.get("events", [])), "an injected situation must emit a grounding event")

        redacted_planner = _CapturingPlanner([done])
        asyncio.run(
            run_agentic_task(
                "do a thing",
                {"planner": redacted_planner, "registry": ToolRegistry(), "situation": Situation(active_app="chrome.exe", active_title="Wells Fargo - Login", open_apps=["chrome.exe"], window_count=1, captured_at="t"), "execute_tools": True},
            )
        )
        check("Wells Fargo" not in (redacted_planner.seen_situation or ""), "a sensitive title must be redacted before the planner sees it")
        check("[private window]" in (redacted_planner.seen_situation or ""), "the redaction marker must reach the planner")

        os.environ.pop("EVA_PERCEPTION_ENABLED", None)
        off_planner = _CapturingPlanner([done])
        off_result = asyncio.run(
            run_agentic_task("do a thing", {"planner": off_planner, "registry": ToolRegistry(), "execute_tools": True})
        )
        check(off_planner.seen_situation is None, "with perception off and no injection, the planner must see no situation")
        check(not any(e.get("type") == "grounding" for e in off_result.get("events", [])), "no grounding event may be emitted when perception is off")

        # 5. Source wiring.
        planner_source = (ROOT / "backend" / "eva" / "agent" / "planner.py").read_text(encoding="utf-8")
        check('"situation"' in planner_source or "'situation'" in planner_source, "planner.py must reference the situation grounding field")
        runner_source = (ROOT / "backend" / "eva" / "agent" / "runner.py").read_text(encoding="utf-8")
        check("_resolve_grounding" in runner_source, "runner.py must reference _resolve_grounding")

        # 6. Eval registered + whole suite green.
        task_ids = {task.id for task in offline_tasks()}
        check("perception_is_metadata_only_and_opt_in" in task_ids, "the perception eval must be registered")
        eval_report = run_offline_evals()
        check(eval_report.all_passed, f"offline eval suite must stay green: {eval_report.summary_text()}")
        check(
            any(r.task_id == "perception_is_metadata_only_and_opt_in" and r.passed for r in eval_report.results),
            "perception_is_metadata_only_and_opt_in must pass",
        )

        # 7. Registered in the master verifier profiles.
        verifier_name = "verify_eva_phase44_perception.py"
        check(verifier_name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 44 perception verifier")
        check(verifier_name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 44 perception verifier")
        descriptors = getattr(verify_eva_all, "VERIFIER_DESCRIPTORS")
        check(verifier_name in descriptors, "master verifier descriptor missing the Phase 44 perception verifier")

    finally:
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    print(
        "PASS: Phase 44 perception & grounding -- the situational model is off by default and auto-captures "
        "nothing; it reads window metadata only (never pixels), redacts a sensitive foreground title to "
        "'[private window]', and lists open apps as process names only; capture_situation is fail-safe on a "
        "window-layer error; run_agentic_task grounds the planner in an injected situation (redacting a sensitive "
        "title before the planner sees it) and emits a grounding event, while perception-off with no injection "
        "leaves the planner situation-free and emits no event; planner.py and runner.py are wired to the grounding "
        "field; and the new eval plus this verifier are registered and green."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
