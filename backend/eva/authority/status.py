from __future__ import annotations


def format_authority_status() -> str:
    return "\n".join(
        [
            "Authority spine status",
            "",
            "Mode: local deterministic decision layer.",
            "Default: preview/refuse unless a safe existing capability route is selected.",
            "Allowed now: read-only inspection, draft previews, approval metadata, and FileAgent sandbox-only apply harness operations.",
            "Blocked now: real file writes, browser control, desktop control, terminal execution, external sending, system changes, and destructive actions.",
            "Real execution: disabled by default.",
            "Normal chat v2 routing: disabled by default.",
        ]
    )
