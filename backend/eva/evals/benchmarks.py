"""Honest, gated adapter stubs for public agent benchmarks (Phase 36b).

These adapters exist to make the *shape* of integrating public benchmarks
(GAIA, WebArena, OSWorld, tau-bench) explicit in the codebase, without ever
downloading a dataset, launching a browser, or calling a live LLM in CI. Each
adapter is inert by default: it only reports itself ``available`` when its
env flag points at an existing local path (or, for WebArena, is simply set),
and ``run()`` never does real work — it either reports ``skipped`` (the
default, everywhere CI runs) or, if someone opts in locally, reports
``not_implemented`` rather than silently pretending to execute a benchmark.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


_NOT_CONFIGURED_REASON = "not configured: requires external dataset + live LLM + explicit opt-in"


@dataclass(frozen=True)
class BenchmarkAdapter:
    """Structure-only adapter for a public agent benchmark.

    ``env_flag`` names the environment variable that would opt this benchmark
    into local (never CI) execution. In CI the flag is always unset, so
    ``availability()`` reports ``False`` and ``run()`` reports ``skipped``.
    """

    name: str
    description: str
    env_flag: str

    def availability(self) -> dict[str, object]:
        raw = os.environ.get(self.env_flag, "").strip()
        if not raw:
            return {"name": self.name, "available": False, "reason": _NOT_CONFIGURED_REASON}
        if not Path(raw).exists():
            return {
                "name": self.name,
                "available": False,
                "reason": f"{self.env_flag} is set but the path does not exist: {raw}",
            }
        return {"name": self.name, "available": True, "reason": f"{self.env_flag} points at an existing path"}

    def run(self) -> dict[str, object]:
        status = self.availability()
        if not status["available"]:
            return {"name": self.name, "status": "skipped", "reason": status["reason"]}
        return {
            "name": self.name,
            "status": "not_implemented",
            "reason": "adapter present; execution deliberately not wired in CI",
        }


def benchmark_adapters() -> list[BenchmarkAdapter]:
    """The public agent benchmarks Eva has a (deliberately inert) adapter for."""
    return [
        BenchmarkAdapter(
            name="GAIA",
            description="General AI Assistants benchmark: multi-step tool-use question answering.",
            env_flag="EVA_BENCH_GAIA_PATH",
        ),
        BenchmarkAdapter(
            name="WebArena",
            description="Realistic web environments for autonomous agent tasks.",
            env_flag="EVA_BENCH_WEBARENA_URL",
        ),
        BenchmarkAdapter(
            name="OSWorld",
            description="Real computer environments (files, apps, OS) for GUI agent tasks.",
            env_flag="EVA_BENCH_OSWORLD_PATH",
        ),
        BenchmarkAdapter(
            name="tau-bench",
            description="Tool-agent-user benchmark for realistic customer-service style dialogues.",
            env_flag="EVA_BENCH_TAUBENCH_PATH",
        ),
    ]
