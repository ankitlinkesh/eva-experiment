"""Durable task worker: drains through an injected (gate-governed) executor (Phase 45)."""

from __future__ import annotations

import asyncio

import pytest

from eva.tasks.durable_queue import DurableTaskQueue
from eva.tasks.worker import DurableTaskWorker


@pytest.fixture()
def queue(tmp_path):
    return DurableTaskQueue(tmp_path / "q.sqlite3")


def test_worker_drains_via_executor(queue):
    seen = []

    async def executor(request):
        seen.append(request)
        return {"ok": True, "final_response": f"handled {request}"}

    queue.enqueue("task one")
    queue.enqueue("task two")
    result = asyncio.run(DurableTaskWorker(queue, executor).drain(max_tasks=10))
    assert result["ran"] == 2
    assert result["succeeded"] == 2
    assert seen == ["task one", "task two"]
    assert queue.stats()["succeeded"] == 2


def test_worker_uses_the_injected_executor_exclusively(queue):
    # The safety story: the worker never runs anything itself; it only calls the
    # executor it was given (which in production is the gate-governed runner).
    called = {"n": 0}

    async def executor(request):
        called["n"] += 1
        return {"ok": True}

    queue.enqueue("only via executor")
    asyncio.run(DurableTaskWorker(queue, executor).run_next())
    assert called["n"] == 1


def test_executor_failure_marks_task_failed_or_retried(queue):
    async def bad_executor(request):
        raise RuntimeError("kaboom")

    t = queue.enqueue("will fail", max_attempts=1)
    task = asyncio.run(DurableTaskWorker(queue, bad_executor).run_next())
    assert task.status == "failed"
    assert "kaboom" in task.error


def test_unsuccessful_result_retries(queue):
    async def unsuccessful(request):
        return {"ok": False, "error": "nope"}

    t = queue.enqueue("retry me", max_attempts=2)
    task = asyncio.run(DurableTaskWorker(queue, unsuccessful).run_next())
    assert task.status == "queued"  # retried, attempts remain


def test_no_executor_is_inert(queue):
    queue.enqueue("unrunnable")
    task = asyncio.run(DurableTaskWorker(queue, None).run_next())
    # The task is not lost — handed back to the queue (re-queued while attempts remain).
    assert task.status == "queued"
    assert queue.stats()["succeeded"] == 0


def test_run_next_returns_none_when_empty(queue):
    async def executor(request):
        return {"ok": True}

    assert asyncio.run(DurableTaskWorker(queue, executor).run_next()) is None


def test_recover_on_start_delegates_to_queue(tmp_path):
    path = tmp_path / "durable.sqlite3"
    q = DurableTaskQueue(path)
    t = q.enqueue("interrupted")
    q.claim()  # RUNNING (crash)

    async def executor(request):
        return {"ok": True}

    worker = DurableTaskWorker(DurableTaskQueue(path), executor)
    assert worker.recover_on_start()["recovered"] == 1
    # After recovery the worker can drain the resumed task to success.
    asyncio.run(worker.drain(max_tasks=5))
    assert DurableTaskQueue(path).get(t.id).status == "succeeded"
