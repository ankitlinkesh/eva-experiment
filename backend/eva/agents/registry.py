from __future__ import annotations

from typing import Iterable

from .base import EvaAgent
from .browser_agent import BrowserAgent
from .code_agent import CodeAgent
from .desktop_agent import DesktopAgent
from .media_agent import MediaAgent
from .memory_agent import MemoryAgent
from .research_agent import ResearchAgent
from .safety_agent import SafetyAgent
from .supervisor_agent import SupervisorAgent


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
    matches: list[EvaAgent] = []
    for agent in get_all_agents():
        if _agent_matches_capability(agent, text):
            matches.append(agent)
    return matches


def select_agent_for_step(task_step: object) -> EvaAgent | None:
    agent_hint = getattr(task_step, "agent", None)
    if agent_hint:
        hinted = get_agent(str(agent_hint))
        if hinted:
            return hinted
    capability_id = getattr(task_step, "capability_id", None)
    matches = find_agents_for_capability(capability_id)
    if matches:
        return matches[0]
    text = " ".join(
        str(getattr(task_step, name, "") or "")
        for name in ("step_type", "title", "description", "input_summary", "notes")
    )
    scored = sorted(((agent.can_handle(text), agent) for agent in get_all_agents()), key=lambda item: item[0], reverse=True)
    if scored and scored[0][0] >= 0.5:
        return scored[0][1]
    return get_agent("PlannerAgent")


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


def _agent_matches_capability(agent: EvaAgent, capability_id: str) -> bool:
    if capability_id.startswith("research_memory."):
        return isinstance(agent, ResearchAgent)
    if capability_id.startswith("public_release."):
        return isinstance(agent, PublicReleaseAgent) or isinstance(agent, SafetyAgent)
    if capability_id.startswith("eva_v2.") or capability_id in {"eva_v2.plan", "eva_v2.plan_preview"}:
        return isinstance(agent, PlannerAgent)
    if capability_id.startswith("browser.") or capability_id == "browser.control":
        return isinstance(agent, BrowserAgent)
    if capability_id.startswith("file.") or capability_id in {"file.delete", "shell.arbitrary"}:
        return isinstance(agent, SafetyAgent) or isinstance(agent, CodeAgent)
    if capability_id in {"whatsapp.send", "email.send"}:
        return isinstance(agent, SafetyAgent)
    if capability_id.startswith("media.") or "spotify" in capability_id:
        return isinstance(agent, MediaAgent)
    if capability_id.startswith("memory."):
        return isinstance(agent, MemoryAgent)
    return any(capability in capability_id for capability in agent.capabilities)
