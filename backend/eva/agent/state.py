from __future__ import annotations

from dataclasses import dataclass, field

from .planner import PlannedToolCall
from .policies import tool_signature


@dataclass
class AgentRunState:
    tool_calls: int = 0
    web_searches: int = 0
    screen_captures: int = 0
    invalid_json_errors: int = 0
    signatures: list[str] = field(default_factory=list)

    def repeated_without_progress(self, call: PlannedToolCall) -> bool:
        signature = tool_signature(call)
        return self.signatures.count(signature) >= 2

    def record_tool(self, call: PlannedToolCall) -> None:
        self.tool_calls += 1
        if call.tool in {"web_search", "research_web", "browser_search"}:
            self.web_searches += 1
        if call.tool in {"capture_screen", "analyze_screen"} or (call.tool == "desktop_observe" and bool(call.args.get("include_screen"))):
            self.screen_captures += 1
        self.signatures.append(tool_signature(call))

    def record_invalid_json(self) -> None:
        self.invalid_json_errors += 1
