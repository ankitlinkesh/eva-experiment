from __future__ import annotations

from .action_catalog import classify_action
from .models import RiskAssessment


_BASE = {
    "observe_only_reference": 5,
    "click_candidate": 45,
    "type_candidate": 55,
    "hotkey_candidate": 65,
    "clipboard_candidate": 70,
    "app_launch_candidate": 60,
    "window_focus_candidate": 45,
    "window_move_or_resize_candidate": 55,
    "browser_control_candidate": 75,
    "shell_or_terminal_candidate": 90,
    "package_install_candidate": 95,
    "file_write_candidate": 80,
    "credential_or_secret_candidate": 100,
    "destructive_or_irreversible_candidate": 100,
    "unknown_or_hallucinated_action": 85,
}


def score_action_risk(request: str, *, sensitive_screen: bool = False) -> RiskAssessment:
    action_class = classify_action(request)
    factors = [action_class]
    score = _BASE[action_class]
    if sensitive_screen:
        score = min(100, score + 25)
        factors.append("sensitive_screen_context")
    level = "low" if score < 25 else "medium" if score < 60 else "high" if score < 90 else "critical"
    return RiskAssessment(score=score, level=level, factors=tuple(factors))


def risk_scoring_policy_text() -> str:
    return "\n".join((
        "Desktop control risk scoring",
        "Scores are deterministic metadata only.",
        "Sensitive-screen context raises risk; secrets, destructive actions, and shell/package actions are critical.",
    ))
