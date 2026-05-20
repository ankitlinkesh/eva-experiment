from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from ..core.config import ModelSettings
from ..llm.router import attempts_as_dicts, complete_with_fallback
from ..tools.registry import ToolRegistry

DecisionType = Literal["answer", "tool_calls", "confirmation_required", "done"]
PlannerMode = Literal["single_turn", "agent_step"]


@dataclass(frozen=True)
class PlannedToolCall:
    tool: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlannerDecision:
    type: DecisionType
    reason: str
    tool_calls: list[PlannedToolCall]
    final_response: str
    requires_confirmation: bool = False
    action: str | None = None
    continue_after_tools: bool = True


class PlannerError(RuntimeError):
    pass


class ToolCallPlanner:
    def __init__(self, settings: ModelSettings, registry: ToolRegistry) -> None:
        self.settings = settings
        self.registry = registry
        self.last_llm_attempts: list[dict] = []

    async def plan(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        *,
        mode: PlannerMode = "single_turn",
        task_context: dict[str, Any] | None = None,
    ) -> PlannerDecision:
        forced = self._forced_decision(message)
        if forced is not None:
            return forced
        prompt = self._prompt(message, history or [], mode=mode, task_context=task_context or {})
        routed = await complete_with_fallback(
            [{"role": "system", "content": "Return strict JSON only for Eva planner decisions."}, {"role": "user", "content": prompt}],
            self.settings,
            purpose="planner",
            temperature=0.1,
            max_tokens=800,
        )
        self.last_llm_attempts = attempts_as_dicts(routed.attempts)
        if routed.response.ok:
            try:
                data = self._parse_json(routed.response.text)
                return self._validate(data, mode=mode)
            except PlannerError:
                fallback = self._local_agent_step_decision(message, task_context or {}) if mode == "agent_step" else self._local_tool_decision(message)
                if fallback is not None:
                    return fallback
                raise
        fallback = self._local_agent_step_decision(message, task_context or {}) if mode == "agent_step" else self._local_tool_decision(message)
        if fallback is not None:
            return fallback
        raise PlannerError("I could not plan that safely. Try a simpler command.")

    def _forced_decision(self, message: str) -> PlannerDecision | None:
        text = " ".join(message.lower().strip().split())
        power_actions = {
            "shutdown": ("shutdown", "shut down", "turn off"),
            "restart": ("restart", "reboot"),
            "sleep": ("sleep",),
            "sign_out": ("sign out", "log out", "logout"),
        }
        for action, phrases in power_actions.items():
            if any(phrase in text for phrase in phrases):
                return PlannerDecision(
                    type="confirmation_required",
                    reason=f"{action} requires explicit confirmation.",
                    tool_calls=[],
                    final_response=f"This will {action.replace('_', ' ')} your laptop. Confirm?",
                    requires_confirmation=True,
                    action=action,
                    continue_after_tools=False,
                )

        screen_verbs = ("look at", "check", "inspect", "analyze", "analyse", "capture", "see", "view")
        screen_words = ("screen", "display", "what is open", "what's open", "error")
        if any(verb in text for verb in screen_verbs) and any(word in text for word in screen_words):
            return PlannerDecision(
                type="tool_calls",
                reason="User explicitly requested one-time screen inspection.",
                tool_calls=[PlannedToolCall(tool="capture_screen", args={})],
                final_response="",
            )

        return None

    def _local_tool_decision(self, message: str) -> PlannerDecision | None:
        text = " ".join(message.lower().strip().split())
        app_aliases = self._app_aliases()
        for prefix in ("open ", "launch ", "start "):
            if text.startswith(prefix):
                target = text.removeprefix(prefix).strip()
                if target in app_aliases:
                    return PlannerDecision(
                        type="tool_calls",
                        reason="Local fallback mapped a known app request.",
                        tool_calls=[PlannedToolCall(tool="open_app", args={"app": app_aliases[target]})],
                        final_response="",
                    )
                folder = target.removesuffix(" folder").strip()
                if folder in self._known_folders():
                    return PlannerDecision(
                        type="tool_calls",
                        reason="Local fallback mapped a known folder request.",
                        tool_calls=[PlannedToolCall(tool="open_folder", args={"folder": folder})],
                        final_response="",
                    )

        for prefix in ("search web for ", "web search ", "search for ", "google ", "look up "):
            if text.startswith(prefix):
                query = message.strip()[len(prefix):].strip()
                if query:
                    return PlannerDecision(
                        type="tool_calls",
                        reason="Local fallback mapped a web search request.",
                        tool_calls=[PlannedToolCall(tool="web_search", args={"query": query})],
                        final_response="",
                    )

        if text in {"mute", "volume up", "volume down", "play", "pause", "next song", "previous song"}:
            action_map = {
                "mute": "mute",
                "volume up": "volume_up",
                "volume down": "volume_down",
                "play": "play_pause",
                "pause": "play_pause",
                "next song": "next",
                "previous song": "previous",
            }
            return PlannerDecision(
                type="tool_calls",
                reason="Local fallback mapped a media control request.",
                tool_calls=[PlannedToolCall(tool="media_control", args={"action": action_map[text]})],
                final_response="",
            )

        if text in {"lock", "lock laptop", "lock screen", "lock pc"}:
            return PlannerDecision(
                type="tool_calls",
                reason="Local fallback mapped a lock request.",
                tool_calls=[PlannedToolCall(tool="lock_laptop", args={})],
                final_response="",
            )

        return None

    def _local_agent_step_decision(self, message: str, task_context: dict[str, Any]) -> PlannerDecision | None:
        goal = self._clean_agent_goal(message)
        text = " ".join(goal.lower().split())
        observations = [str(item) for item in task_context.get("observations") or []]
        observed_blob = "\n".join(observations).lower()
        app_aliases = self._app_aliases()

        if any(word in text for word in ("hello", "hi ", "say hello")) and not observations:
            return PlannerDecision(
                type="done",
                reason="Simple greeting goal can be answered directly.",
                tool_calls=[],
                final_response="Hello! I am Eva, online and ready to help.",
                continue_after_tools=False,
            )

        for prefix in ("open ", "launch ", "start "):
            if text.startswith(prefix):
                target = text.removeprefix(prefix).split(" and ", 1)[0].strip()
                if target in app_aliases and "open_app" not in observed_blob:
                    return PlannerDecision(
                        type="tool_calls",
                        reason="Need to open a known app.",
                        tool_calls=[PlannedToolCall(tool="open_app", args={"app": app_aliases[target]})],
                        final_response="",
                    )
                folder = target.removesuffix(" folder").strip()
                if folder in self._known_folders() and "open_folder" not in observed_blob:
                    return PlannerDecision(
                        type="tool_calls",
                        reason="Need to open a known folder.",
                        tool_calls=[PlannedToolCall(tool="open_folder", args={"folder": folder})],
                        final_response="",
                    )

        if self._looks_like_web_goal(text):
            query = self._search_query(goal)
            if "web_search observed" not in observed_blob and "web_search opened browser fallback" not in observed_blob:
                return PlannerDecision(
                    type="tool_calls",
                    reason="Need current web results.",
                    tool_calls=[PlannedToolCall(tool="web_search", args={"query": query})],
                    final_response="",
                )
            return PlannerDecision(
                type="done",
                reason="Web search observation is available.",
                tool_calls=[],
                final_response=self._final_from_observations(observations),
                continue_after_tools=False,
            )

        if observations:
            return PlannerDecision(
                type="done",
                reason="Observed tool result is enough to finish.",
                tool_calls=[],
                final_response=self._final_from_observations(observations),
                continue_after_tools=False,
            )

        return PlannerDecision(
            type="answer",
            reason="Goal does not need a tool or is outside safe tools.",
            tool_calls=[],
            final_response="I can help with that, but I need a more specific safe action or research question.",
            continue_after_tools=False,
        )

    def _prompt(self, message: str, history: list[dict[str, str]], *, mode: PlannerMode, task_context: dict[str, Any]) -> str:
        if mode == "agent_step":
            return self._agent_step_prompt(message, history, task_context)
        return self._single_turn_prompt(message, history)

    def _single_turn_prompt(self, message: str, history: list[dict[str, str]]) -> str:
        recent = [
            {"role": item.get("role"), "content": item.get("content", "")[:500]}
            for item in history[-4:]
            if item.get("role") in {"user", "assistant"}
        ]
        return f"""
You are Eva's tool-calling planner. Return strict JSON only. No markdown.

User message:
{message}

Recent chat context:
{json.dumps(recent, ensure_ascii=False)}

Available tool registry:
{json.dumps(self.registry.planner_specs(), ensure_ascii=False)}

Required JSON shape:
{{
  "type": "answer" | "tool_calls" | "confirmation_required",
  "reason": "short internal explanation",
  "tool_calls": [
    {{"tool": "tool_name", "args": {{}}}}
  ],
  "final_response": "natural language response to user if no tool is needed"
}}

Rules:
- If no tool is needed, use type "answer" and put the user-facing response in final_response.
- If tools are needed, use type "tool_calls".
- Maximum 3 tool calls.
- Never call tools outside the registry.
- Never invent tool names.
- Use open_app for known apps such as chrome, spotify, vscode, codex, settings, notepad.
- Use open_folder for known folders such as downloads, documents, desktop, eva folder.
- Use web_search for web searches; use open_url for explicit URLs.
- Use media_control for volume, mute, play/pause, next, previous.
- Use lock_laptop for lock requests.
- For shutdown, restart, sleep, sign out, or log out, do not call a tool unless the user explicitly confirms in this same message. If not confirmed, use type "confirmation_required" and final_response should ask for confirmation.
- For screen capture, only call capture_screen when the user explicitly asks Eva to look at, check, inspect, analyze, or capture the screen.
- No arbitrary shell commands. No camera. No always-on screen watching.
""".strip()

    def _agent_step_prompt(self, message: str, history: list[dict[str, str]], task_context: dict[str, Any]) -> str:
        recent = [
            {"role": item.get("role"), "content": item.get("content", "")[:500]}
            for item in history[-4:]
            if item.get("role") in {"user", "assistant"}
        ]
        compact_context = {
            "goal": task_context.get("goal") or message,
            "observations": (task_context.get("observations") or [])[-6:],
            "steps": (task_context.get("steps") or [])[-6:],
            "limits": task_context.get("limits") or {},
        }
        return f"""
You are Eva's bounded agent-step planner. Return strict JSON only. No markdown. Do not reveal hidden chain-of-thought.

User goal:
{message}

Recent chat context:
{json.dumps(recent, ensure_ascii=False)}

Current task state:
{json.dumps(compact_context, ensure_ascii=False)}

Available safe tool registry:
{json.dumps(self.registry.planner_specs(), ensure_ascii=False)}

Required JSON shape:
{{
  "type": "tool_calls" | "answer" | "confirmation_required" | "done",
  "reason": "short visible-safe summary",
  "tool_calls": [
    {{"tool": "tool_name", "args": {{}}}}
  ],
  "final_response": "only if answering or done",
  "continue_after_tools": true
}}

Rules:
- Plan only the next bounded step toward the goal.
- Prefer 1 tool call. Maximum 2 tool calls in one step.
- Never call tools outside the registry. Never invent tool names.
- Do not repeat the same web_search query already present in observations.
- Use web_search for research/current web information.
- Use open_app/open_folder/open_url only for explicit desktop/navigation goals.
- Do not call capture_screen unless the user explicitly asks to inspect/look/check/analyze the screen.
- For shutdown, restart, sleep, sign out, or log out, return confirmation_required and do not call a power tool.
- If observations are enough, return type "done" with a concise final_response.
- No arbitrary shell commands. No camera. No hidden screen watching.
""".strip()

    def _parse_json(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            raise PlannerError(f"Planner returned invalid JSON: {raw[:240]}") from exc

    def _validate(self, data: dict[str, Any], *, mode: PlannerMode) -> PlannerDecision:
        decision_type = data.get("type")
        allowed_types = {"answer", "tool_calls", "confirmation_required"} if mode == "single_turn" else {"answer", "tool_calls", "confirmation_required", "done"}
        if decision_type not in allowed_types:
            raise PlannerError(f"Unsupported planner type: {decision_type}")

        calls = []
        raw_calls = data.get("tool_calls") or []
        if not isinstance(raw_calls, list):
            raise PlannerError("tool_calls must be a list.")
        max_calls = 3 if mode == "single_turn" else 2
        if len(raw_calls) > max_calls:
            raise PlannerError(f"Planner requested more than {max_calls} tool calls.")

        for item in raw_calls:
            if not isinstance(item, dict):
                raise PlannerError("Each tool call must be an object.")
            name = str(item.get("tool", "")).strip()
            args = item.get("args") or {}
            if not isinstance(args, dict):
                raise PlannerError(f"Tool args for {name} must be an object.")
            if self.registry.get(name) is None:
                raise PlannerError(f"Planner requested unknown tool: {name}")
            calls.append(PlannedToolCall(tool=name, args=args))

        final_response = str(data.get("final_response") or "").strip()
        reason = str(data.get("reason") or "").strip()[:260]
        continue_after_tools = bool(data.get("continue_after_tools", True))

        if decision_type in {"answer", "done"} and not final_response:
            raise PlannerError("Planner answer is missing final_response.")
        if decision_type == "tool_calls" and not calls:
            raise PlannerError("Planner selected tool_calls without tool calls.")
        if decision_type == "confirmation_required":
            action = self._extract_action(data, final_response)
            return PlannerDecision(
                type="confirmation_required",
                reason=reason,
                tool_calls=[],
                final_response=final_response or f"This requires confirmation before I can {action}.",
                requires_confirmation=True,
                action=action,
                continue_after_tools=False,
            )

        return PlannerDecision(
            type=decision_type,  # type: ignore[arg-type]
            reason=reason,
            tool_calls=calls,
            final_response=final_response,
            continue_after_tools=continue_after_tools,
        )

    def _extract_action(self, data: dict[str, Any], fallback_text: str) -> str:
        action = str(data.get("action") or "").strip().lower().replace(" ", "_")
        if action:
            return action
        text = fallback_text.lower()
        candidates = {
            "shutdown": ("shutdown", "shut down", "turn off"),
            "restart": ("restart", "reboot"),
            "sleep": ("sleep",),
            "sign_out": ("sign out", "log out", "logout"),
        }
        for normalized, phrases in candidates.items():
            if any(phrase in text for phrase in phrases):
                return normalized
        return "dangerous_action"

    def _app_aliases(self) -> dict[str, str]:
        return {
            "chrome": "chrome",
            "google chrome": "chrome",
            "spotify": "spotify",
            "vscode": "vscode",
            "vs code": "vscode",
            "visual studio code": "vscode",
            "codex": "codex",
            "settings": "settings",
            "notepad": "notepad",
            "calculator": "calculator",
            "edge": "edge",
            "terminal": "terminal",
            "powershell": "powershell",
        }

    def _known_folders(self) -> set[str]:
        return {"downloads", "documents", "desktop", "pictures", "videos", "music", "eva", "eva folder"}

    def _clean_agent_goal(self, message: str) -> str:
        clean = message.strip()
        lowered = clean.lower()
        if lowered.startswith("agent mode:"):
            return clean.split(":", 1)[1].strip() or clean
        if lowered.startswith("eva, handle this"):
            return clean.split("this", 1)[-1].strip(" :") or clean
        return clean

    def _looks_like_web_goal(self, text: str) -> bool:
        return any(word in text for word in ("research", "find", "summarize", "search", "compare", "latest", "best", "github", "repos", "rate limits"))

    def _search_query(self, goal: str) -> str:
        clean = self._clean_agent_goal(goal)
        lowered = clean.lower()
        for marker in ("search web for", "search for", "look up", "google"):
            if marker in lowered:
                index = lowered.index(marker) + len(marker)
                return clean[index:].strip(" :") or clean
        replacements = (
            "find and summarize",
            "research",
            "compare",
            "figure out",
            "plan this",
            "do this task",
            "step by step",
            "summarize",
            "find",
        )
        query = clean
        for item in replacements:
            query = re.sub(rf"\b{re.escape(item)}\b", "", query, flags=re.IGNORECASE)
        query = " ".join(query.strip(" :").split())
        return query or clean

    def _final_from_observations(self, observations: list[str]) -> str:
        if not observations:
            return "I finished the task."
        return "I finished the task. " + " ".join(observations[-3:])
