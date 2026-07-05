from __future__ import annotations


QUICK_VERIFY_COMMAND = r".\.venv\Scripts\python.exe scripts\verify_eva_all.py --quick"
FULL_VERIFY_COMMAND = r".\.venv\Scripts\python.exe scripts\verify_eva_all.py --full"


def format_understood_request(intent: str, summary: str) -> str:
    return "\n".join(["I understood this as:", summary or intent or "Safe Eva request."])


def format_safe_next_step(next_step: str) -> str:
    return "\n".join(["Next safe step:", next_step or "Review the status output. No action was executed."])


def format_blocked_request(reason: str, alternative: str | None = None) -> str:
    lines = ["Request blocked", "", reason or "Eva cannot safely run that request in this phase."]
    if alternative:
        lines.extend(["", "Safe alternative:", alternative])
    lines.append("No file, browser, desktop, shell, external message, or cloud action was executed.")
    return "\n".join(lines)


def format_exact_confirmation_required(action: str, approval_id: str | None = None) -> str:
    phrase = f"confirm {action} {approval_id}" if approval_id else f"confirm {action} <approval_id>"
    return "\n".join(["Exact confirmation required", "", f"Use exactly: `{phrase}`.", "Vague confirmations like `yes`, `do it`, or `go ahead` are refused."])


def format_ambiguous_approval_selection(approval_ids: list[str]) -> str:
    lines = ["Approval selection needed", ""]
    if not approval_ids:
        lines.append("No eligible approval was found. Start with `eva ask create a project note about Eva`.")
    else:
        lines.append("Multiple eligible approvals exist. Specify one approval id:")
        lines.extend(f"- {approval_id}" for approval_id in approval_ids[:10])
    return "\n".join(lines)


def format_workflow_next_step(workflow: str, next_step: str) -> str:
    return "\n".join(["Workflow next step", "", f"Workflow: {workflow}", next_step])


def format_verify_quick_command() -> str:
    return "\n".join(["Eva quick verification", "", "Manual command:", QUICK_VERIFY_COMMAND, "", "Eva did not run this command from chat."])


def format_verify_full_command() -> str:
    return "\n".join(["Eva full verification", "", "Manual command:", FULL_VERIFY_COMMAND, "", "Eva did not run this command from chat."])


def format_quick_status_summary() -> str:
    return "\n".join(
        [
            "Eva Phase 12 quick status",
            "",
            "Smoke verifier: available.",
            "Quick profile: available.",
            f"Quick command: `{QUICK_VERIFY_COMMAND}`",
            f"Full command: `{FULL_VERIFY_COMMAND}`",
            "",
            "Safety: broad writes disabled; browser/desktop control, MCP, shell execution, cloud calls, and external sending remain disabled.",
        ]
    )


def format_phase12_status() -> str:
    return "\n".join(
        [
            "Eva Phase 12 status",
            "",
            "Completed: 12F sandbox apply, 12G authority/router, 12H Control Center, 12I/12L narrow real create, 12J golden workflows, 12K smoke/profile stabilization, 12M specialists/skills, 12N workflow UX, and 12O project/reality checking.",
            "Current UX: natural-language-first through `eva ask`; explicit commands remain debug/fallback surfaces.",
            "Verification: quick and full profiles are available; the dashboard only displays commands and does not run them.",
            "",
            "Locked: BrowserAgent execution, CodingAgent real source edits, News Dashboard automation, MCP, Playwright, PyAutoGUI, screen watching, terminal execution, dependency setup, cloud calls, and message sending.",
            "File boundary: broad writes disabled; only the existing narrow real-create gate can create a new safe .md/.txt file after exact confirmation.",
        ]
    )


def format_ux_status() -> str:
    return "\n".join(
        [
            "Eva UX status",
            "",
            "`eva ask` uses cleaner summaries for status, golden workflows, exact confirmation, and blocked requests.",
            "Dangerous requests are blocked with a safe next step.",
            "Verifier commands are suggested as manual commands; Eva does not execute shell commands from chat.",
        ]
    )
