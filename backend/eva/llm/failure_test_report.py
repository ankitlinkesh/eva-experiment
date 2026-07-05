from __future__ import annotations

from .red_team_runner import RedTeamRun


def format_failure_test_report(run: RedTeamRun) -> str:
    categories = ", ".join(item.category.replace("_", " ") for item in run.results)
    return "\n".join([
        "LLM Red-Team / Failure Test Report",
        "",
        f"Cases: {run.total}; safely handled: {run.failed_safely}.",
        "Unsafe LLM-like output cannot execute tools, browser, desktop, shell, cloud, or MCP actions.",
        "Provider failure, timeout, rate-limit, degraded-mode, and runaway cases are simulated only.",
        f"Covered categories: {categories}.",
    ])
