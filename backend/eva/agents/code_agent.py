from __future__ import annotations

from typing import Any

from .base import EvaAgent
from ..schemas.results import EvaAgentResult


class CodeAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="code",
            description="Routes implementation-location, symbol, traceback, and patch-plan tasks to Code Intelligence.",
            capabilities=("code", "symbol", "traceback", "implemented", "where is", "patch", "debug"),
            delegated_core="Code Intelligence v1",
        )

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        text = str(intent or "").lower()
        if any(word in text for word in ("code", "symbol", "traceback", "implemented", "where is", "debug", "patch", "repo", "project", "files", "bug", "structure", "inspect", "workspace")):
            return 0.9
        return 0.04

    def plan(self, state: Any) -> EvaAgentResult:
        text = str(getattr(state, "normalized_intent", "") or getattr(state, "user_request", "")).lower()
        action_type = "code.inspect_structure"
        summary = "Would inspect the workspace structure through read-only Code Intelligence / Workspace Skills."
        if any(marker in text for marker in ("status", "code status", "code intelligence status")):
            action_type = "code.status"
            summary = "Would read safe Code Intelligence status."
        elif any(marker in text for marker in ("summarize workspace", "summarise workspace", "workspace skills", "project summary", "workspace summary")):
            action_type = "code.summarize_workspace"
            summary = "Would summarize workspace skills and project structure without reading secrets."
        elif _looks_like_file_summary(text):
            action_type = "code.summarize_file"
            summary = "Would summarize one allowed source file without dumping full contents."
        elif any(marker in text for marker in ("find symbol", "where is symbol", "symbol search", "code symbols")):
            action_type = "code.find_symbols"
            summary = "Would search symbols in the safe code index."
        elif any(marker in text for marker in ("search files", "search project", "search workspace", "search code", "code search", "find file")):
            action_type = "code.search_files"
            summary = "Would search safe indexed workspace file metadata."
        elif any(marker in text for marker in ("edit", "patch", "write", "rename", "move", "delete", "install", "run ", "shell", "powershell", "commit", "push", "merge")):
            if any(marker in text for marker in ("install", "package")):
                action_type = "code.install_package"
            elif any(marker in text for marker in ("run ", "shell", "powershell", "script")):
                action_type = "code.run_shell"
            elif "delete" in text:
                action_type = "code.delete_file"
            elif "rename" in text:
                action_type = "code.rename_file"
            elif "move" in text:
                action_type = "code.move_file"
            elif "commit" in text:
                action_type = "code.git_commit"
            elif "push" in text:
                action_type = "code.git_push"
            elif "merge" in text:
                action_type = "code.git_merge"
            else:
                action_type = "code.edit_file"
            summary = "Would require a file-changing or command action, which v2 read-only execution must refuse."
        return EvaAgentResult(
            agent_name=self.name,
            ok=True,
            message="CodeAgent selected for a local code/project preview.",
            proposed_actions=[
                {
                    "agent": self.name,
                    "action_type": action_type,
                    "summary": summary,
                    "requires_permission": False,
                    "side_effect_level": "read_only",
                    "delegate_to": self.delegated_core,
                }
            ],
            delegated_to=self.delegated_core,
        )


def _looks_like_file_summary(text: str) -> bool:
    if not any(marker in text for marker in ("summarize ", "summarise ", "file summary", "summarize file", "summarise file")):
        return False
    return any(extension in text for extension in (".py", ".js", ".ts", ".html", ".css", ".md", ".json", ".toml", ".yaml", ".yml"))
