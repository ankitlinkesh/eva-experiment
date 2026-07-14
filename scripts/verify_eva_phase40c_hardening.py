from __future__ import annotations

import asyncio
import json
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


class ScriptedPlanner:
    """Deterministic planner for driving the agent loop in tests. Returns queued
    PlannerDecisions in order; repeats the last one once exhausted."""

    def __init__(self, decisions):
        self._decisions = list(decisions)
        self.calls = 0

    async def plan(self, goal, history, mode="agent_step", task_context=None):
        decision = self._decisions[min(self.calls, len(self._decisions) - 1)]
        self.calls += 1
        return decision


def main() -> int:
    from backend.eva.agent.planner import PlannedToolCall, PlannerDecision
    from backend.eva.agent.runner import run_agentic_task
    from backend.eva.evals.harness import run_offline_evals
    from backend.eva.evals.offline_suite import offline_tasks
    from backend.eva.mcp import trust
    from backend.eva.mcp.config import McpServerConfig, load_mcp_config
    from backend.eva.privacy.secrets_broker import (
        assert_no_secret_leak,
        contains_secret_leak,
        has_secret,
        list_secret_names,
        resolve,
        scrub_for_model,
    )
    from backend.eva.threat_defense.tool_scope import TaskToolScope
    from backend.eva.tools.registry import ToolRegistry
    from scripts import verify_eva_all

    saved_env = {
        key: os.environ.get(key)
        for key in ("EVA_MCP_TRUSTED_SERVERS", "EVA_MCP_SERVER_BUDGET", "EVA_MCP_CONFIG_PATH", "EVA_TRACING_ENABLED")
    }
    trust.reset_budgets()

    try:
        # 1. TaskToolScope: unrestricted vs restricted, plus wildcard matching.
        unrestricted = TaskToolScope.of(None)
        check(unrestricted.restricted is False, "TaskToolScope.of(None) must be unrestricted")
        check(unrestricted.is_allowed("file.delete") is True, "an unrestricted scope must allow anything")

        restricted = TaskToolScope.of(["workspace_status", "web.*"])
        check(restricted.restricted is True, "TaskToolScope.of([...]) must be restricted")
        check(restricted.is_allowed("workspace_status") is True, "an exact allowlist match must be allowed")
        check(restricted.is_allowed("web.open_url") is True, "a prefix* wildcard must match")
        check(restricted.is_allowed("file.delete") is False, "a tool outside the allowlist must be denied")

        empty_scope = TaskToolScope.of([])
        check(empty_scope.restricted is True, "an empty iterable scope must still be restricted")
        check(empty_scope.is_allowed("workspace_status") is False, "an empty allowlist must allow nothing")

        # 2. End-to-end runner enforcement: an out-of-scope tool is denied before
        #    it executes, no matter what the scripted planner proposed.
        delete_decision = PlannerDecision(
            type="tool_calls",
            reason="clean up",
            tool_calls=[PlannedToolCall(tool="file.delete", args={"path": "C:/tmp/x.txt"})],
            final_response="",
            continue_after_tools=True,
        )
        scoped_result = asyncio.run(
            run_agentic_task(
                "delete a file",
                {
                    "planner": ScriptedPlanner([delete_decision]),
                    "registry": ToolRegistry(),
                    "tool_scope": ["workspace_status"],
                    "execute_tools": True,
                },
            )
        )
        check(scoped_result["status"] == "failed", f"an out-of-scope tool call must fail the task, got {scoped_result['status']!r}")
        check("out_of_scope:file.delete" in scoped_result["safety_stops"], f"safety_stops must record the scope denial, got {scoped_result['safety_stops']!r}")
        check("file.delete" not in scoped_result["tools_executed"], "the out-of-scope file.delete must never have executed")

        status_decision = PlannerDecision(
            type="tool_calls",
            reason="check status",
            tool_calls=[PlannedToolCall(tool="workspace_status", args={})],
            final_response="",
            continue_after_tools=True,
        )
        done_decision = PlannerDecision(type="done", reason="done", tool_calls=[], final_response="All set.", continue_after_tools=False)
        allowed_result = asyncio.run(
            run_agentic_task(
                "check status",
                {
                    "planner": ScriptedPlanner([status_decision, done_decision]),
                    "registry": ToolRegistry(),
                    "tool_scope": ["workspace_status"],
                    "execute_tools": True,
                },
            )
        )
        check(allowed_result["ok"] is True, f"an in-scope tool call must still succeed, got ok={allowed_result['ok']!r}")
        check("workspace_status" in allowed_result["tools_executed"], "the in-scope workspace_status call must have executed")

        # 3. Secrets broker: names hide values, resolve gates non-secret names,
        #    scrub_for_model + assert_no_secret_leak remove a planted secret
        #    (both pattern and exact-value paths), and scrubbing is fail-safe.
        secret_env = {"K_API_KEY": "sk-abcdef1234567890", "HOME": "/home/x"}
        names = list_secret_names(secret_env)
        check(names == ["K_API_KEY"], f"list_secret_names must return only secret-looking names, got {names!r}")
        check(all("sk-abcdef1234567890" not in name for name in names), "list_secret_names must never leak a value")

        check(resolve("K_API_KEY", secret_env) == "sk-abcdef1234567890", "resolve must return the value for a secret-looking name")
        check(resolve("HOME", secret_env) is None, "resolve must gate a non-secret-looking name to None")
        check(has_secret("K_API_KEY", secret_env) is True, "has_secret must be True for a present secret-looking name")
        check(has_secret("HOME", secret_env) is False, "has_secret must be False for a non-secret name")

        raw = "leak sk-abcdef1234567890"
        check(contains_secret_leak(raw, secret_env) is True, "contains_secret_leak must detect the raw planted secret")
        scrubbed = scrub_for_model(raw, secret_env)
        check("sk-abcdef1234567890" not in scrubbed, f"scrub_for_model must remove the raw secret value, got {scrubbed!r}")
        check(contains_secret_leak(scrubbed, secret_env) is False, "scrubbed text must not still contain the live secret value")
        check(assert_no_secret_leak(raw, secret_env) is True, "assert_no_secret_leak must be True once scrubbing removes the planted secret")

        check(isinstance(scrub_for_model(None, secret_env), str), "scrub_for_model must be fail-safe on None input")
        check(isinstance(scrub_for_model(12345, secret_env), str), "scrub_for_model must be fail-safe on non-str input")

        # 4. MCP trust: no-policy trusts everything; a marked/allowlisted server
        #    is kept and an unmarked one is filtered; budgets exceed after N
        #    calls; config parses the trusted field.
        os.environ.pop("EVA_MCP_TRUSTED_SERVERS", None)
        a = McpServerConfig(name="a", transport="stdio")
        b = McpServerConfig(name="b", transport="stdio")
        check(trust.trust_configured([a, b]) is False, "with no policy configured, trust_configured must be False")
        kept = trust.filter_trusted([a, b])
        check({s.name for s in kept} == {"a", "b"}, f"with no policy configured, filter_trusted must keep every server, got {[s.name for s in kept]!r}")

        pinned = McpServerConfig(name="pinned", transport="stdio", trusted=True)
        untrusted = McpServerConfig(name="untrusted", transport="stdio", trusted=False)
        kept2 = trust.filter_trusted([pinned, untrusted])
        check([s.name for s in kept2] == ["pinned"], f"a marked-trusted server must be kept and an unmarked one filtered, got {[s.name for s in kept2]!r}")

        os.environ["EVA_MCP_TRUSTED_SERVERS"] = "pinned"
        kept3 = trust.filter_trusted([McpServerConfig(name="pinned", transport="stdio"), McpServerConfig(name="other", transport="stdio")])
        check([s.name for s in kept3] == ["pinned"], f"the env allowlist must filter to only the named server, got {[s.name for s in kept3]!r}")
        os.environ.pop("EVA_MCP_TRUSTED_SERVERS", None)

        trust.reset_budgets()
        os.environ["EVA_MCP_SERVER_BUDGET"] = "2"
        check(trust.budget_exceeded("budget-server") is False, "budget must not be exceeded before any calls")
        trust.record_call("budget-server")
        check(trust.budget_exceeded("budget-server") is False, "budget must not be exceeded after 1 of 2 calls")
        trust.record_call("budget-server")
        check(trust.budget_exceeded("budget-server") is True, "budget must be exceeded after 2 of 2 calls")
        trust.reset_budgets()
        os.environ.pop("EVA_MCP_SERVER_BUDGET", None)

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "mcp_servers.json"
            config_path.write_text(
                json.dumps({"servers": [{"name": "pinned", "transport": "stdio", "command": "run", "trusted": True}, {"name": "unpinned", "transport": "stdio", "command": "run"}]}),
                encoding="utf-8",
            )
            os.environ["EVA_MCP_CONFIG_PATH"] = str(config_path)
            servers = load_mcp_config()
            by_name = {s.name: s for s in servers}
            check(by_name["pinned"].trusted is True, "load_mcp_config must parse trusted=True")
            check(by_name["unpinned"].trusted is False, "load_mcp_config must default trusted to False")
        os.environ.pop("EVA_MCP_CONFIG_PATH", None)

        # 5. Source wiring: the cores actually call into the new modules.
        runner_source = (ROOT / "backend" / "eva" / "agent" / "runner.py").read_text(encoding="utf-8")
        check("tool_scope" in runner_source, "runner.py must reference tool_scope")
        check("is_allowed" in runner_source, "runner.py must call tool_scope.is_allowed")

        registration_source = (ROOT / "backend" / "eva" / "mcp" / "registration.py").read_text(encoding="utf-8")
        check("filter_trusted" in registration_source, "registration.py must call trust.filter_trusted")
        check("budget_exceeded" in registration_source, "registration.py must call trust.budget_exceeded")

        # 6. Both new evals are registered and the whole offline suite is green.
        task_ids = {task.id for task in offline_tasks()}
        check("least_privilege_and_secrets_enforced" in task_ids, "the least-privilege/secrets eval must be registered")
        check("mcp_trust_filters_untrusted" in task_ids, "the MCP trust eval must be registered")

        eval_report = run_offline_evals()
        check(eval_report.all_passed, f"offline eval suite must stay green: {eval_report.summary_text()}")
        check(
            any(r.task_id == "least_privilege_and_secrets_enforced" and r.passed for r in eval_report.results),
            "least_privilege_and_secrets_enforced must pass",
        )
        check(
            any(r.task_id == "mcp_trust_filters_untrusted" and r.passed for r in eval_report.results),
            "mcp_trust_filters_untrusted must pass",
        )

        # 7. Registered in the master verifier profiles.
        verifier_name = "verify_eva_phase40c_hardening.py"
        check(verifier_name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 40c hardening verifier")
        descriptors = getattr(verify_eva_all, "VERIFIER_DESCRIPTORS")
        check(verifier_name in descriptors, "master verifier descriptor missing the Phase 40c hardening verifier")

    finally:
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        trust.reset_budgets()

    print(
        "PASS: Phase 40c hardening -- TaskToolScope's unrestricted/restricted/wildcard semantics hold and "
        "run_agentic_task denies an out-of-scope file.delete via out_of_scope before it ever executes while an "
        "in-scope call still succeeds; the secrets broker hides values in list_secret_names, gates resolve() to "
        "secret-looking names, and scrub_for_model/assert_no_secret_leak remove a planted secret via both pattern "
        "and exact-value matching (fail-safe on odd input); the MCP trust model trusts everything with no policy "
        "configured, filters to marked/allowlisted servers once configured, enforces the per-server call budget, "
        "and McpServerConfig parses the trusted field; the runner/registration wiring references "
        "tool_scope/is_allowed and filter_trusted/budget_exceeded; both new security evals are registered and green; "
        "and the verifier is wired into the master profiles."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
