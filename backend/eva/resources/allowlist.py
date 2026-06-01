from __future__ import annotations


BUILTIN_ALLOWED_RESOURCE_IDS = {
    "eva-chrome-execution-skills",
    "eva-browser-agent-core",
    "eva-desktop-agent-core",
    "eva-visual-desktop-control",
    "eva-spotify-desktop-skill",
    "eva-workspace-skills",
    "eva-code-intelligence",
    "eva-code-index",
    "eva-research-sqlite",
    "eva-memory-sqlite",
    "nvidia-nim-provider-existing",
    "tavily-existing",
    "ollama",
}

BUILTIN_REFERENCE_ONLY_RESOURCE_IDS = {
    "official-mcp-servers-registry",
    "awesome-mcp-servers",
    "docker-mcp-registry",
    "promptfoo",
}

BUILTIN_BLOCKED_RESOURCE_IDS = set()

_BLOCKED_ID_MARKERS = ("camera-always-on", "hidden-monitoring", "secret-reader", "arbitrary-shell")


def is_builtin_allowed(resource_id: str) -> bool:
    return str(resource_id or "") in BUILTIN_ALLOWED_RESOURCE_IDS


def is_builtin_blocked(resource_id: str) -> bool:
    value = str(resource_id or "")
    return value in BUILTIN_BLOCKED_RESOURCE_IDS or any(marker in value for marker in _BLOCKED_ID_MARKERS)


def is_reference_only(resource_id: str) -> bool:
    return str(resource_id or "") in BUILTIN_REFERENCE_ONLY_RESOURCE_IDS
