"""Durable task worker — drains the queue through the permission gate (Phase 45).

The :class:`~eva.tasks.durable_queue.DurableTaskQueue` only remembers work; it
never runs anything. This worker is the (opt-in) piece that actually executes a
queued task — and it does so through an *injected* executor, which in production
is the ordinary gate-governed agent runner. That is the whole safety story:

  * A worker claims a task, runs it via the executor, and records the outcome.
  * The executor is ``run_agentic_task`` (or a wrapper), so every tool call the
    task makes still passes the permission gate, and any confirmation it needs
    still goes through the ledger. The queue replays the *request*, never an
    approval — a recovered task cannot silently perform a privileged action.
  * With no executor configured the worker is inert: it recovers orphans and
    reports, but runs nothing.

Draining is deliberate and bounded (``drain(max_tasks=...)``); nothing here
starts an unattended background loop. Fully fail-safe.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from .durable_queue import DurableTaskQueue, DurableTask

# An executor takes a task request string and returns a result dict; it is
# expected to be gate-governed (e.g. a thin wrapper over run_agentic_task).
Executor = Callable[[str], Awaitable[dict[str, Any]]]


class DurableTaskWorker:
    def __init__(self, queue: DurableTaskQueue, executor: Executor | None = None) -> None:
        self.queue = queue
        self._executor = executor

    def recover_on_start(self) -> dict[str, Any]:
        """Reconcile crash-orphaned tasks. Call this once at startup."""
        return self.queue.recover_orphans()

    async def run_next(self) -> DurableTask | None:
        """Claim and execute one queued task through the gate-governed executor.

        Returns the task in its resulting terminal/queued state, or ``None`` if
        nothing is queued or no executor is configured (the task is left queued
        in that case). Any executor error fails the task (which retries or is
        abandoned by the queue's own policy) — it never propagates."""
        task = self.queue.claim()
        if task is None:
            return None
        if self._executor is None:
            # Cannot run without an executor: hand the claim back so the task is
            # not lost. fail() re-queues while attempts remain.
            return self.queue.fail(task.id, error="no executor configured")
        try:
            result = await self._executor(task.request)
        except Exception as exc:  # executor blew up
            return self.queue.fail(task.id, error=f"executor error: {str(exc)[:200]}")
        ok = bool(result.get("ok")) if isinstance(result, dict) else bool(result)
        if ok:
            summary = ""
            if isinstance(result, dict):
                summary = str(result.get("final_response") or result.get("summary") or "")[:1000]
            return self.queue.complete(task.id, summary=summary)
        error = ""
        if isinstance(result, dict):
            error = str(result.get("error") or result.get("status") or "task did not succeed")[:500]
        return self.queue.fail(task.id, error=error or "task did not succeed")

    async def drain(self, *, max_tasks: int = 25) -> dict[str, Any]:
        """Run queued tasks one at a time until the queue is empty or the budget
        is spent. Bounded and attended-only — never an infinite loop."""
        ran = 0
        succeeded = 0
        failed = 0
        for _ in range(max(0, int(max_tasks))):
            task = await self.run_next()
            if task is None:
                break
            ran += 1
            if task.status == "succeeded":
                succeeded += 1
            elif task.status in {"failed", "queued"}:
                failed += 1
        return {"ran": ran, "succeeded": succeeded, "failed_or_retried": failed}


__all__ = ["DurableTaskWorker", "Executor"]
