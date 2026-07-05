from __future__ import annotations

from .models import StepLimitPolicy


DEFAULT_MAX_STEPS = 10
HARD_MAX_STEPS = 16


def get_step_limit_policy() -> StepLimitPolicy:
    return StepLimitPolicy(
        default_max_steps=DEFAULT_MAX_STEPS,
        hard_max_steps=HARD_MAX_STEPS,
        runaway_detection="stop when a preview exceeds the hard max or repeats unsafe expansion",
        repeated_step_detection="stop when the same preview stage repeats without new evidence",
        no_progress_detection="stop when observations do not change the preview plan",
        stop_behavior="safe failure with a human-readable stop report",
    )


def clamp_step_limit(max_steps: int | None = None) -> int:
    policy = get_step_limit_policy()
    if max_steps is None:
        return policy.default_max_steps
    try:
        requested = int(max_steps)
    except (TypeError, ValueError):
        return policy.default_max_steps
    return max(1, min(requested, policy.hard_max_steps))


def step_limit_policy_text() -> str:
    policy = get_step_limit_policy()
    return "\n".join(
        [
            "Agent Loop v1 step limit policy",
            "Agent loop is local/mock preview only.",
            "No live LLM call was made.",
            "Actions are preview-only.",
            "Tools are not executed.",
            "Secrets/config/session data are blocked.",
            "Browser/desktop/shell/cloud/MCP execution remains locked.",
            f"Default max steps: {policy.default_max_steps}.",
            f"Hard max steps: {policy.hard_max_steps}.",
            "Step limits, runaway detection, repeated-step detection, and no-progress stop behavior are enforced.",
            f"Stop behavior: {policy.stop_behavior}.",
        ]
    )
