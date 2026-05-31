from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AgentSkill:
    name: str
    description: str
    allowed_tools: tuple[str, ...]
    steps: tuple[str, ...]
    success_criteria: str
    requires_confirmation: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


SKILLS: tuple[AgentSkill, ...] = (
    AgentSkill(
        name="open_app_and_verify",
        description="Open a known app, observe windows, and verify the target window is visible.",
        allowed_tools=("open_app", "verify_last_action", "desktop_observe"),
        steps=("open_app", "verify_last_action", "report result"),
        success_criteria="The target app has a visible window or Eva reports that verification was inconclusive.",
    ),
    AgentSkill(
        name="open_folder_and_verify",
        description="Open a known folder and verify the folder/window appears when Windows exposes it.",
        allowed_tools=("open_folder", "verify_last_action", "desktop_observe"),
        steps=("open_folder", "verify_last_action", "report result"),
        success_criteria="The target folder appears in a visible window or Eva reports that verification was inconclusive.",
    ),
    AgentSkill(
        name="search_web_and_remember_results",
        description="Run safe web search, store last results in session context, and summarize result options.",
        allowed_tools=("web_search",),
        steps=("web_search", "remember results", "summarize top results"),
        success_criteria="Search results are available for follow-up commands like open first result.",
    ),
    AgentSkill(
        name="inspect_screen_once",
        description="Capture and analyze the screen one time only after explicit user request.",
        allowed_tools=("analyze_screen", "desktop_observe"),
        steps=("analyze_screen", "observe active window", "suggest next step"),
        success_criteria="Eva provides a screen summary or a clear rate-limit/unavailable message.",
    ),
    AgentSkill(
        name="focus_or_open_app",
        description="Focus an existing app window, or open the app if no matching window is found.",
        allowed_tools=("window_focus", "window_list", "open_app", "verify_last_action"),
        steps=("window_focus", "fallback open_app if needed", "verify_last_action"),
        success_criteria="The requested app is focused/open or Eva reports what blocked verification.",
    ),
    AgentSkill(
        name="research_topic_and_save",
        description="Search sources for a topic and save normalized findings to local research SQLite.",
        allowed_tools=("research_recall", "research_web", "research_save_note", "research_summary"),
        steps=("research_recall", "research_web if needed", "research_summary"),
        success_criteria="Research sources/notes are stored locally with URLs preserved.",
    ),
    AgentSkill(
        name="inspect_project_and_suggest_next",
        description="Inspect safe workspace files and suggest project next steps without editing.",
        allowed_tools=("workspace_project_summary", "workspace_search", "workspace_read_file"),
        steps=("workspace_project_summary", "workspace_search relevant area", "summarize findings"),
        success_criteria="Eva gives grounded file references and asks before editing.",
    ),
)


def skill_status() -> dict[str, Any]:
    return {
        "ok": True,
        "count": len(SKILLS),
        "skills": [skill.as_dict() for skill in SKILLS],
        "safety": {
            "arbitrary_shell": False,
            "camera": False,
            "always_on_screen": False,
            "power_actions_need_confirmation": True,
        },
    }
