from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from ..screen.capture import capture_primary_screen_jpeg
from .desktop import close_app, media_key, open_app, open_folder, open_url, system_power, system_status, web_search

SafetyLevel = Literal["safe", "sensitive", "dangerous"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_schema: dict[str, Any]
    safety_level: SafetyLevel
    handler: Callable[..., Any]

    @property
    def safe_by_default(self) -> bool:
        return self.safety_level == "safe"


POWER_ACTIONS = {"shutdown", "restart", "sleep", "sign_out", "log_out"}
MEDIA_ACTIONS = {"mute", "volume_up", "volume_down", "play_pause", "next", "previous"}
KNOWN_APPS = {
    "calculator",
    "chrome",
    "cmd",
    "codex",
    "discord",
    "edge",
    "explorer",
    "notepad",
    "paint",
    "powershell",
    "settings",
    "spotify",
    "task manager",
    "terminal",
    "vscode",
    "vs code",
    "visual studio code",
    "whatsapp",
    "word",
    "excel",
    "powerpoint",
}
KNOWN_FOLDERS = {"desktop", "documents", "downloads", "pictures", "videos", "music", "eva", "eva folder"}


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or [], "additionalProperties": False}


def _status() -> dict[str, Any]:
    return asdict(system_status())


def _media_control(action: str) -> str:
    normalized = action.strip().lower().replace(" ", "_")
    if normalized not in MEDIA_ACTIONS:
        raise ValueError(f"Unsupported media action: {action}")
    return media_key(normalized)


def _lock_laptop() -> str:
    return system_power("lock")


def _guarded_power_action(action: str, confirmed: bool = False) -> str:
    normalized = action.strip().lower().replace(" ", "_")
    if normalized not in POWER_ACTIONS:
        raise ValueError(f"Unsupported power action: {action}")
    return system_power(normalized, confirmed=confirmed)


def _capture_screen() -> dict[str, Any]:
    image = capture_primary_screen_jpeg()
    data_dir = Path(__file__).resolve().parents[3] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / "latest_screen.jpg"
    output_path.write_bytes(image)
    return {
        "image_path": str(output_path),
        "bytes": len(image),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "note": "One-time screenshot captured. No continuous screen watching is active.",
    }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {
            "status": ToolSpec(
                name="status",
                description="Return basic laptop runtime status.",
                args_schema=_schema({}),
                safety_level="safe",
                handler=_status,
            ),
            "system_status": ToolSpec(
                name="system_status",
                description="Alias for status used by deterministic commands.",
                args_schema=_schema({}),
                safety_level="safe",
                handler=_status,
            ),
            "open_app": ToolSpec(
                name="open_app",
                description="Open a known desktop app by common name. Supported examples: chrome, spotify, vscode, codex, settings, notepad.",
                args_schema=_schema({"app": {"type": "string", "enum": sorted(KNOWN_APPS)}}, ["app"]),
                safety_level="safe",
                handler=lambda app=None, app_name=None: open_app(str(app or app_name or "")),
            ),
            "close_app": ToolSpec(
                name="close_app",
                description="Close a small allowlist of common apps.",
                args_schema=_schema({"app": {"type": "string"}, "app_name": {"type": "string"}}, []),
                safety_level="sensitive",
                handler=lambda app=None, app_name=None: close_app(str(app or app_name or "")),
            ),
            "open_folder": ToolSpec(
                name="open_folder",
                description="Open a known folder: Downloads, Documents, Desktop, Pictures, Videos, Music, or Eva folder.",
                args_schema=_schema({"folder": {"type": "string", "enum": sorted(KNOWN_FOLDERS)}, "folder_name": {"type": "string"}}, []),
                safety_level="safe",
                handler=lambda folder=None, folder_name=None: open_folder(str(folder or folder_name or "")),
            ),
            "open_url": ToolSpec(
                name="open_url",
                description="Open an http or https URL in the default browser.",
                args_schema=_schema({"url": {"type": "string"}}, ["url"]),
                safety_level="safe",
                handler=open_url,
            ),
            "web_search": ToolSpec(
                name="web_search",
                description="Search the web with Tavily when configured, otherwise open a safe browser search fallback.",
                args_schema=_schema({"query": {"type": "string"}}, ["query"]),
                safety_level="safe",
                handler=web_search,
            ),
            "media_control": ToolSpec(
                name="media_control",
                description="Send media keys: mute, volume_up, volume_down, play_pause, next, previous.",
                args_schema=_schema({"action": {"type": "string", "enum": sorted(MEDIA_ACTIONS)}}, ["action"]),
                safety_level="safe",
                handler=_media_control,
            ),
            "media_key": ToolSpec(
                name="media_key",
                description="Alias for media_control used by deterministic commands.",
                args_schema=_schema({"action": {"type": "string", "enum": sorted(MEDIA_ACTIONS)}}, ["action"]),
                safety_level="safe",
                handler=_media_control,
            ),
            "lock_laptop": ToolSpec(
                name="lock_laptop",
                description="Lock the laptop immediately. This is allowed without confirmation.",
                args_schema=_schema({}),
                safety_level="safe",
                handler=_lock_laptop,
            ),
            "capture_screen": ToolSpec(
                name="capture_screen",
                description="Capture one on-demand screenshot only when the user explicitly asks Eva to look at, check, analyze, or inspect the screen.",
                args_schema=_schema({}),
                safety_level="sensitive",
                handler=_capture_screen,
            ),
            "guarded_power_action": ToolSpec(
                name="guarded_power_action",
                description="Shutdown, restart, sleep, or sign out. Requires explicit confirmation before execution.",
                args_schema=_schema(
                    {
                        "action": {"type": "string", "enum": sorted(POWER_ACTIONS)},
                        "confirmed": {"type": "boolean"},
                    },
                    ["action", "confirmed"],
                ),
                safety_level="dangerous",
                handler=_guarded_power_action,
            ),
            "system_power": ToolSpec(
                name="system_power",
                description="Alias for lock/guarded power actions used by deterministic commands.",
                args_schema=_schema({"action": {"type": "string"}, "confirmed": {"type": "boolean"}}, ["action"]),
                safety_level="dangerous",
                handler=system_power,
            ),
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return [self._public_spec(spec) for spec in self._tools.values()]

    def planner_specs(self) -> list[dict[str, Any]]:
        visible = [
            "status",
            "open_app",
            "open_folder",
            "open_url",
            "web_search",
            "media_control",
            "lock_laptop",
            "capture_screen",
            "guarded_power_action",
        ]
        return [self._public_spec(self._tools[name]) for name in visible]

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def run(self, name: str, **kwargs: Any) -> Any:
        spec = self._tools.get(name)
        if spec is None:
            raise KeyError(f"Unknown tool: {name}")
        result = spec.handler(**kwargs)
        return asdict(result) if hasattr(result, "__dataclass_fields__") else result

    def _public_spec(self, spec: ToolSpec) -> dict[str, Any]:
        return {
            "name": spec.name,
            "description": spec.description,
            "args_schema": spec.args_schema,
            "safety_level": spec.safety_level,
            "safe_by_default": spec.safe_by_default,
        }

