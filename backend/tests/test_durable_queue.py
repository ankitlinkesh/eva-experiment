"""Durable task queue: lifecycle + crash recovery (Phase 45)."""

from __future__ import annotations

import pytest

from eva.tasks.durable_queue import (
    CANCELLED,
    FAILED,
    QUEUED,
    RUNNING,
    SUCCEEDED,
    DurableTaskQueue,
)


@pytest.fixture()
def queue(tmp_path):
    return DurableTaskQueue(tmp_path / "q.sqlite3")


def test_enqueue_and_stats(queue):
    queue.enqueue("do a thing")
    s = queue.stats()
    assert s["queued"] == 1 and s["total"] == 1


def test_empty_request_is_rejected(queue):
    assert queue.enqueue("   ") is None
    assert queue.stats()["total"] == 0


def test_claim_is_priority_then_fifo(queue):
    queue.enqueue("low", priority=0)
    high = queue.enqueue("high", priority=5)
    claimed = queue.claim()
    assert claimed.id == high.id
    assert claimed.status == RUNNING
    assert claimed.attempts == 1


def test_complete_marks_succeeded(queue):
    t = queue.enqueue("x")
    queue.claim()
    done = queue.complete(t.id, "all good")
    assert done.status == SUCCEEDED
    assert done.result_summary == "all good"
    assert done.finished_at


def test_fail_retries_then_exhausts(queue):
    t = queue.enqueue("flaky", max_attempts=2)
    queue.claim()
    r1 = queue.fail(t.id, "boom1")
    assert r1.status == QUEUED  # retried
    queue.claim()
    r2 = queue.fail(t.id, "boom2")
    assert r2.status == FAILED  # attempts exhausted
    assert r2.error == "boom2"


def test_cancel_from_queued(queue):
    t = queue.enqueue("cancel me")
    c = queue.cancel(t.id)
    assert c.status == CANCELLED


def test_terminal_state_is_immutable(queue):
    t = queue.enqueue("x")
    queue.claim()
    queue.complete(t.id, "done")
    # A later fail must not resurrect a succeeded task.
    assert queue.fail(t.id, "late error").status == SUCCEEDED
    assert queue.cancel(t.id).status == SUCCEEDED


def test_recover_orphans_requeues_running_after_restart(tmp_path):
    path = tmp_path / "durable.sqlite3"
    q = DurableTaskQueue(path)
    t = q.enqueue("interrupted work")
    q.claim()  # now RUNNING; process 'crashes' before completion
    assert q.get(t.id).status == RUNNING
    del q

    # 'Restart' — a fresh instance over the same DB file.
    q2 = DurableTaskQueue(path)
    result = q2.recover_orphans()
    assert result["recovered"] == 1
    assert result["abandoned"] == 0
    assert q2.get(t.id).status == QUEUED  # resumed, ready to run again


def test_recover_abandons_task_that_exhausted_attempts(tmp_path):
    path = tmp_path / "durable.sqlite3"
    q = DurableTaskQueue(path)
    t = q.enqueue("crash loop", max_attempts=1)
    q.claim()  # attempts now 1 == max_attempts, left RUNNING (crash)
    result = DurableTaskQueue(path).recover_orphans()
    assert result["abandoned"] == 1
    assert DurableTaskQueue(path).get(t.id).status == FAILED


def test_recovery_only_restores_request_never_completes(tmp_path):
    # The safety property: recovery re-queues, it never marks a task succeeded
    # or otherwise "approves" it.
    path = tmp_path / "durable.sqlite3"
    q = DurableTaskQueue(path)
    t = q.enqueue("privileged-looking task")
    q.claim()
    DurableTaskQueue(path).recover_orphans()
    assert DurableTaskQueue(path).get(t.id).status == QUEUED


def test_list_and_get(queue):
    a = queue.enqueue("a")
    queue.enqueue("b")
    assert queue.get(a.id).request == "a"
    assert len(queue.list_tasks()) == 2
    assert len(queue.list_tasks(status=QUEUED)) == 2
