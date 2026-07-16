"""Standalone verifier for Phase 45 (durable/background task queue).

Proves, end to end and independent of pytest, that the durable task queue
(backend/eva/tasks/) survives a restart and never becomes a way to replay a
privileged action unattended:

  1. Lifecycle: enqueue -> claim (priority then FIFO, status running, attempts
     incremented) -> complete (succeeded); fail retries while attempts remain
     then marks failed; a terminal state is immutable.
  2. CRASH RECOVERY: a task left 'running' when a fresh queue instance opens the
     same DB file (a 'restart') is recovered back to 'queued'; a task that has
     exhausted its attempts is abandoned as 'failed' (no infinite crash loop).
  3. SAFETY: recovery only restores the request — it never completes/approves a
     task (no finished_at, no result_summary), so durability cannot replay a
     privileged action unattended.
  4. Worker: drains queued tasks through an INJECTED executor (the gate-governed
     path in production) and records outcomes; an executor error fails/retries;
     with no executor the worker is inert (task left queued, never run).
  5. Default OFF + startup wiring: durable_queue_enabled() is False by default;
     open_default_queue() returns None when off; main.py references
     _recover_durable_tasks_if_enabled.
  6. The new eval is registered and the whole offline suite stays green.
  7. This verifier is wired into scripts/verify_eva_all.py's profiles.

Fully offline and deterministic: temp DBs only, no network, no live LLM; every
env var touched is restored in a ``finally`` block.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    from backend.eva.evals import run_offline_evals
    from backend.eva.evals.offline_suite import offline_tasks
    from backend.eva.tasks import durable_queue_enabled, open_default_queue
    from backend.eva.tasks.durable_queue import DurableTaskQueue
    from backend.eva.tasks.worker import DurableTaskWorker
    from scripts import verify_eva_all

    saved_env = {"EVA_DURABLE_QUEUE_ENABLED": os.environ.get("EVA_DURABLE_QUEUE_ENABLED")}
    scratch = Path(tempfile.mkdtemp(prefix="eva_phase45_durable_"))

    try:
        # 1. Lifecycle.
        q = DurableTaskQueue(scratch / "life.sqlite3")
        q.enqueue("low", priority=0)
        high = q.enqueue("high", priority=5)
        claimed = q.claim()
        check(claimed.id == high.id, "claim must take the highest priority task first")
        check(claimed.status == "running" and claimed.attempts == 1, "a claimed task is running with attempts=1")
        done = q.complete(claimed.id, "ok")
        check(done.status == "succeeded" and done.finished_at, "complete must mark succeeded with finished_at")

        # A dedicated queue per check: a shared one still holds earlier queued
        # tasks, and claim() would take those instead of the one under test.
        fq = DurableTaskQueue(scratch / "flaky.sqlite3")
        flaky = fq.enqueue("flaky", max_attempts=2)
        fq.claim()
        check(fq.fail(flaky.id, "e1").status == "queued", "fail with attempts remaining must retry (queued)")
        fq.claim()
        check(fq.fail(flaky.id, "e2").status == "failed", "fail with no attempts left must mark failed")

        tq = DurableTaskQueue(scratch / "terminal.sqlite3")
        term = tq.enqueue("terminal")
        tq.claim()
        tq.complete(term.id, "done")
        check(tq.fail(term.id, "late").status == "succeeded", "a terminal (succeeded) task must be immutable")
        check(tq.cancel(term.id).status == "succeeded", "cancelling a terminal task must not resurrect it")

        # 2 + 3. Crash recovery + safety (recovery never approves).
        recovery_path = scratch / "recover.sqlite3"
        rq = DurableTaskQueue(recovery_path)
        orphan = rq.enqueue("interrupted work")
        rq.claim()  # running; 'crash' before completion
        check(rq.get(orphan.id).status == "running", "task must be running before the simulated crash")
        del rq

        restarted = DurableTaskQueue(recovery_path)  # 'restart' over the same file
        result = restarted.recover_orphans()
        check(result["recovered"] == 1 and result["abandoned"] == 0, f"a running task must be recovered on restart, got {result!r}")
        resumed = restarted.get(orphan.id)
        check(resumed.status == "queued", f"a recovered task must return to queued, got {resumed.status!r}")
        check(not resumed.finished_at and not resumed.result_summary, "recovery must NEVER complete/approve a task — only restore its request")

        loop_path = scratch / "loop.sqlite3"
        lq = DurableTaskQueue(loop_path)
        crashy = lq.enqueue("crash loop", max_attempts=1)
        lq.claim()  # attempts == max_attempts, left running
        abandoned = DurableTaskQueue(loop_path).recover_orphans()
        check(abandoned["abandoned"] == 1, "a task out of attempts must be abandoned, not resumed forever")
        check(DurableTaskQueue(loop_path).get(crashy.id).status == "failed", "an abandoned task must be failed")

        # 4. Worker via injected executor + inert without one.
        wq = DurableTaskQueue(scratch / "worker.sqlite3")
        wq.enqueue("one")
        wq.enqueue("two")
        seen: list[str] = []

        async def executor(request):
            seen.append(request)
            return {"ok": True, "final_response": f"handled {request}"}

        drained = asyncio.run(DurableTaskWorker(wq, executor).drain(max_tasks=10))
        check(drained["ran"] == 2 and drained["succeeded"] == 2, f"the worker must drain both tasks via the executor, got {drained!r}")
        check(seen == ["one", "two"], "the worker must run only through the injected executor, in order")

        async def bad(request):
            raise RuntimeError("kaboom")

        eq = DurableTaskQueue(scratch / "err.sqlite3")
        errored = eq.enqueue("will fail", max_attempts=1)
        failed_task = asyncio.run(DurableTaskWorker(eq, bad).run_next())
        check(failed_task.status == "failed" and "kaboom" in failed_task.error, "an executor error must fail the task")

        iq = DurableTaskQueue(scratch / "inert.sqlite3")
        iq.enqueue("unrunnable")
        inert = asyncio.run(DurableTaskWorker(iq, None).run_next())
        check(inert.status == "queued", "a worker with no executor must leave the task queued, never run it")
        check(iq.stats()["succeeded"] == 0, "a worker with no executor must never mark anything succeeded")

        # 5. Default OFF + startup wiring.
        os.environ.pop("EVA_DURABLE_QUEUE_ENABLED", None)
        check(durable_queue_enabled() is False, "durable queue must be off by default")
        check(open_default_queue() is None, "open_default_queue must be None when disabled")
        os.environ["EVA_DURABLE_QUEUE_ENABLED"] = "1"
        check(durable_queue_enabled() is True, "durable queue must report enabled when the flag is set")

        main_source = (ROOT / "backend" / "eva" / "main.py").read_text(encoding="utf-8")
        check("_recover_durable_tasks_if_enabled" in main_source, "main.py must wire durable-task recovery at startup")

        # 6. Eval registered + suite green.
        task_ids = {task.id for task in offline_tasks()}
        check("durable_queue_recovers_and_never_auto_approves" in task_ids, "the durable-queue eval must be registered")
        eval_report = run_offline_evals()
        check(eval_report.all_passed, f"offline eval suite must stay green: {eval_report.summary_text()}")
        check(
            any(r.task_id == "durable_queue_recovers_and_never_auto_approves" and r.passed for r in eval_report.results),
            "durable_queue_recovers_and_never_auto_approves must pass",
        )

        # 7. Registered in master profiles.
        verifier_name = "verify_eva_phase45_durable.py"
        check(verifier_name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 45 durable verifier")
        check(verifier_name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 45 durable verifier")
        descriptors = getattr(verify_eva_all, "VERIFIER_DESCRIPTORS")
        check(verifier_name in descriptors, "master verifier descriptor missing the Phase 45 durable verifier")

    finally:
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    print(
        "PASS: Phase 45 durable task queue -- the lifecycle (enqueue -> claim by priority -> complete, with "
        "retry-then-fail and immutable terminal states) is correct; a task left running when a fresh instance "
        "opens the same DB is RECOVERED to queued on restart while a task out of attempts is abandoned as failed "
        "(no crash loop); recovery only restores the request and never completes/approves it, so no privileged "
        "action is replayed unattended; the worker drains queued tasks solely through an injected gate-governed "
        "executor, fails on executor error, and is inert without one; the queue is off by default with "
        "open_default_queue() None and startup recovery wired in main.py; and the new eval plus this verifier are "
        "registered and green."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
