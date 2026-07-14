"""Typed data model for the objective task-eval harness (Phase 36b).

The harness exists to answer one question honestly: does Eva's real safety
gate (``ToolRegistry.run``) behave the way the product promises, right now,
without a human watching? Every :class:`EvalTask` therefore checks a live
post-condition against the real registry/router — never a mock — while
staying fully offline, deterministic, and side-effect-free so it is safe to
run in CI on every commit.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry


@dataclass
class EvalContext:
    """Shared, disposable state handed to every :class:`EvalTask` check.

    ``registry`` is a fresh :class:`~backend.eva.tools.registry.ToolRegistry`
    (the real central tool gate) and ``tmp_dir`` is a throwaway directory a
    check may use for scratch files instead of touching the real workspace.
    """

    registry: "ToolRegistry"
    tmp_dir: Path

    @classmethod
    def create(cls) -> "EvalContext":
        """Build a fresh registry and a fresh temp scratch directory."""
        from ..tools.registry import ToolRegistry

        return cls(registry=ToolRegistry(), tmp_dir=Path(tempfile.mkdtemp(prefix="eva_eval_")))


@dataclass(frozen=True)
class EvalTask:
    """One deterministic, offline check against the live gate/registry/router."""

    id: str
    description: str
    category: str
    check: Callable[[EvalContext], tuple[bool, str]]
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvalResult:
    """The outcome of running a single :class:`EvalTask`."""

    task_id: str
    category: str
    passed: bool
    detail: str
    duration_ms: float
    trace_id: str | None = None


@dataclass
class EvalReport:
    """Aggregate results for a harness run, plus a human-readable summary."""

    results: list[EvalResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for result in self.results if not result.passed)

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed_count / self.total

    @property
    def all_passed(self) -> bool:
        return self.total > 0 and self.failed_count == 0

    def as_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "pass_rate": self.pass_rate,
            "all_passed": self.all_passed,
            "results": [
                {
                    "task_id": result.task_id,
                    "category": result.category,
                    "passed": result.passed,
                    "detail": result.detail,
                    "duration_ms": result.duration_ms,
                    "trace_id": result.trace_id,
                }
                for result in self.results
            ],
        }

    def summary_text(self) -> str:
        percent = round(self.pass_rate * 100)
        lines = [f"Eva eval report: {self.passed_count}/{self.total} passed ({percent}%)."]
        for result in self.results:
            if not result.passed:
                lines.append(f"- FAILED {result.task_id} [{result.category}]: {result.detail}")
        return "\n".join(lines)
