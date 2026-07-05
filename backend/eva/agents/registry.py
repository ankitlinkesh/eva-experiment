from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .base import EvaAgent
from .browser_agent import BrowserAgent
from .code_agent import CodeAgent
from .desktop_agent import DesktopAgent
from .file_agent import FileAgent
from .media_agent import MediaAgent
from .memory_agent import MemoryAgent
from .research_agent import ResearchAgent
from .safety_agent import SafetyAgent
from .supervisor_agent import SupervisorAgent


@dataclass
class AgentSelection:
    agent: EvaAgent | None
    confidence: float
    reason: str
    fallback: bool = False

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["agent"] = type(self.agent).__name__ if self.agent else None
        return payload


class PlannerAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="planner",
            description="Wraps Planner v3 templates, validation, review, and preview-only decomposition.",
            capabilities=("plan", "planner", "dry run", "review", "validate", "draft", "summary", "report"),
            delegated_core="Planner v3",
        )


class PublicReleaseAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="public_release",
            description="Wraps public release status, hardening audit, ready check, demo scenarios, and safety simulator previews.",
            capabilities=("public release", "demo", "safety simulator", "hardening", "ready check"),
            delegated_core="Public Release / Demo / Safety Simulator",
        )


def get_all_agents() -> list[EvaAgent]:
    return [
        ResearchAgent(),
        MemoryAgent(),
        SafetyAgent(),
        BrowserAgent(),
        DesktopAgent(),
        MediaAgent(),
        FileAgent(),
        CodeAgent(),
        PlannerAgent(),
        PublicReleaseAgent(),
        SupervisorAgent(),
    ]


def get_agent(agent_name: str) -> EvaAgent | None:
    wanted = _normalize_agent_name(agent_name)
    for agent in get_all_agents():
        if _normalize_agent_name(type(agent).__name__) == wanted or _normalize_agent_name(agent.name) == wanted:
            return agent
    return None


def list_agent_names() -> list[str]:
    return [type(agent).__name__ for agent in get_all_agents()]


def find_agents_for_capability(capability_id: str | None) -> list[EvaAgent]:
    text = str(capability_id or "").lower()
    if not text:
        return []
    preferred_names = _preferred_agent_names_for_capability(text)
    agents = get_all_agents()
    matches = [agent for agent in agents if type(agent).__name__ in preferred_names]
    matches.extend(agent for agent in agents if agent not in matches and _agent_matches_capability(agent, text))
    return matches


def select_agent_for_step(task_step: object) -> EvaAgent | None:
    return select_agent_for_step_with_confidence(task_step).agent


def select_agent_for_step_with_confidence(task_step: object) -> AgentSelection:
    agent_hint = getattr(task_step, "agent", None)
    capability_id = getattr(task_step, "capability_id", None)
    matches = find_agents_for_capability(capability_id)
    if matches and _is_generic_agent_hint(agent_hint):
        return AgentSelection(matches[0], 0.9, "Exact capability-to-agent mapping overrides generic planner hint.")
    if agent_hint:
        hinted = get_agent(str(agent_hint))
        if hinted:
            return AgentSelection(hinted, 0.95, "Planner step already names this agent.")
    if matches:
        return AgentSelection(matches[0], 0.9, "Exact capability-to-agent mapping.")
    text = " ".join(
        str(getattr(task_step, name, "") or "")
        for name in ("step_type", "title", "description", "input_summary", "notes")
    )
    risky = _is_risky_step_text(text, capability_id)
    if risky:
        safety = get_agent("SafetyAgent") or get_agent("SupervisorAgent")
        return AgentSelection(safety, 0.7, "Risky or external-visible step routed to safety fallback.", fallback=True)
    planner = _is_planning_step_text(text, capability_id)
    if planner:
        planner_agent = get_agent("PlannerAgent") or get_agent("SupervisorAgent")
        return AgentSelection(planner_agent, 0.7, "Planning or validation step routed to planner fallback.", fallback=True)
    scored = sorted(((agent.can_handle(text), agent) for agent in get_all_agents()), key=lambda item: item[0], reverse=True)
    if scored and scored[0][0] >= 0.5:
        return AgentSelection(scored[0][1], min(0.8, scored[0][0]), "Capability keyword match.", fallback=True)
    fallback = get_agent("SupervisorAgent") or get_agent("SafetyAgent") or get_agent("PlannerAgent")
    return AgentSelection(fallback, 0.45, "No direct match; using safe supervisor fallback.", fallback=True)


def format_agents_status() -> str:
    agents = get_all_agents()
    lines = [
        "Agent Framework v1 status",
        "",
        f"Registered agents: {len(agents)}",
        "Execution: disabled by default; dry-run/status/explain only.",
        "",
        "Registered agents:",
    ]
    for agent in agents:
        lines.append(f"- {type(agent).__name__}: {agent.description}")
    lines.extend(
        [
            "",
            "Safety:",
            "No MCP, Playwright, PyAutoGUI, browser control, screen watching, shell, file write, or message send is enabled.",
        ]
    )
    return "\n".join(lines)


def format_agent_detail(agent_name: str) -> str:
    agent = get_agent(agent_name)
    if not agent:
        return "\n".join(["Agent detail", "", f"Agent `{agent_name}` was not found.", "Use `eva agent list` to view registered agents."])
    lines = [
        "Agent detail",
        "",
        f"Name: {type(agent).__name__}",
        f"Internal id: {agent.name}",
        f"Description: {agent.description}",
        f"Delegated core: {agent.delegated_core}",
        "",
        "Capabilities:",
    ]
    lines.extend(f"- {capability}" for capability in agent.capabilities)
    lines.extend(
        [
            "",
            "Lifecycle:",
            "- plan: available as preview metadata",
            "- dry_run: available",
            "- execute: refused by default in Agent Framework v1",
            "- observe: unavailable preview",
            "- verify: unavailable preview",
            "- rollback: unavailable because no action is executed",
            "- explain: available",
            "",
            "Scope: no real task execution is enabled by this agent detail view.",
        ]
    )
    if type(agent).__name__ == "FileAgent":
        lines.extend(
            [
                "",
                "FileAgent safety:",
                "Writes, edits, deletes, moves, renames, copies, secrets, runtime databases, and whole-drive scans are not enabled.",
            ]
        )
    return "\n".join(lines)


def format_agent_capability_matrix() -> str:
    lines = ["Agent capability matrix", ""]
    for agent in get_all_agents():
        lines.append(f"- {type(agent).__name__}: {', '.join(agent.capabilities)}")
    lines.extend(["", "Scope: matrix is metadata only. No agent action was executed."])
    return "\n".join(lines)


def format_agent_capabilities(agent_name: str) -> str:
    agent = get_agent(agent_name)
    if not agent:
        return "\n".join(["Agent capabilities", "", f"Agent `{agent_name}` was not found."])
    lines = ["Agent capabilities", "", f"Agent: {type(agent).__name__}"]
    lines.extend(f"- {capability}" for capability in agent.capabilities)
    lines.extend(["", "Execution: capabilities are discovery metadata only in Phase 11A."])
    return "\n".join(lines)


def _normalize_agent_name(value: str) -> str:
    return str(value or "").strip().lower().replace("_", "").replace("-", "").replace(" ", "")


def _is_generic_agent_hint(agent_hint: object) -> bool:
    normalized = _normalize_agent_name(str(agent_hint or ""))
    return normalized in {"", "planneragent", "verifieragent"}


def _agent_matches_capability(agent: EvaAgent, capability_id: str) -> bool:
    if capability_id.startswith("research_memory."):
        return isinstance(agent, ResearchAgent)
    if capability_id.startswith("public_release."):
        return isinstance(agent, PublicReleaseAgent) or isinstance(agent, SafetyAgent)
    if capability_id.startswith("eva_v2.") or capability_id in {"eva_v2.plan", "eva_v2.plan_preview"}:
        return isinstance(agent, PlannerAgent)
    if capability_id.startswith("browser.") or capability_id == "browser.control":
        return isinstance(agent, BrowserAgent)
    if capability_id.startswith("file."):
        if capability_id in {"file.delete", "file.write", "file.move", "file.rename"}:
            return isinstance(agent, SafetyAgent) or isinstance(agent, CodeAgent)
        return isinstance(agent, FileAgent) or isinstance(agent, CodeAgent)
    if capability_id == "shell.arbitrary":
        return isinstance(agent, SafetyAgent) or isinstance(agent, CodeAgent)
    if capability_id in {"whatsapp.send", "email.send"}:
        return isinstance(agent, SafetyAgent)
    if capability_id.startswith("media.") or "spotify" in capability_id:
        return isinstance(agent, MediaAgent)
    if capability_id.startswith("memory."):
        return isinstance(agent, MemoryAgent)
    return any(capability in capability_id for capability in agent.capabilities)


def _preferred_agent_names_for_capability(capability_id: str) -> list[str]:
    if capability_id.startswith("research_memory."):
        return ["ResearchAgent", "MemoryAgent"]
    if capability_id.startswith("public_release."):
        return ["PublicReleaseAgent", "SafetyAgent", "SupervisorAgent"]
    if capability_id.startswith("eva_v2.") or capability_id in {"eva_v2.plan", "eva_v2.plan_preview"}:
        return ["PlannerAgent", "SupervisorAgent"]
    if capability_id.startswith("browser.") or capability_id == "browser.control":
        return ["BrowserAgent", "SupervisorAgent"]
    if capability_id.startswith("desktop.") or capability_id == "screen.watch":
        return ["DesktopAgent", "SafetyAgent", "SupervisorAgent"]
    if capability_id.startswith("file."):
        if capability_id in {"file.delete", "file.write", "file.move", "file.rename"}:
            return ["SafetyAgent", "SupervisorAgent", "CodeAgent"]
        return ["FileAgent", "CodeAgent", "SupervisorAgent"]
    if capability_id == "shell.arbitrary":
        return ["SafetyAgent", "SupervisorAgent", "CodeAgent"]
    if capability_id in {"whatsapp.send", "email.send"}:
        return ["SafetyAgent", "SupervisorAgent"]
    if capability_id.startswith("media.") or "spotify" in capability_id or "youtube" in capability_id:
        return ["MediaAgent", "BrowserAgent", "SupervisorAgent"]
    if capability_id.startswith("memory."):
        return ["MemoryAgent", "ResearchAgent"]
    if capability_id.startswith("code.") or "project" in capability_id:
        return ["CodeAgent", "SupervisorAgent"]
    return []


def _is_risky_step_text(text: str, capability_id: str | None) -> bool:
    joined = f"{capability_id or ''} {text}".lower()
    return any(
        term in joined
        for term in (
            "whatsapp",
            "email",
            "send",
            "post",
            "submit",
            "delete",
            "shutdown",
            "install",
            "shell",
            "override",
            "blocked",
        )
    )


def _is_planning_step_text(text: str, capability_id: str | None) -> bool:
    joined = f"{capability_id or ''} {text}".lower()
    return any(term in joined for term in ("plan", "planner", "review", "validate", "template", "draft", "summary"))
