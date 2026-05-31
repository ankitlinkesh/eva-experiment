from __future__ import annotations

from ..agents.supervisor_agent import build_default_agents, select_agent_for_intent


def supervisor_status() -> dict[str, object]:
    agents = build_default_agents()
    return {
        "ok": True,
        "agent_count": len(agents),
        "agents": [agent.as_dict() for agent in agents],
        "message": "Eva v2 supervisor skeleton can select specialist agents but does not replace the current loop yet.",
    }
