from __future__ import annotations

from dataclasses import asdict, dataclass


ALLOWED_DESKTOP_STATUS_ACTIONS = (
    "desktop status",
    "desktop policy summary",
    "blocked action explanation",
    "desktop action safety preview",
    "app risk string classification",
    "locked feature explanation",
)


BLOCKED_DESKTOP_ACTIONS = (
    "real screen capture",
    "screenshots",
    "real app/window enumeration",
    "launching apps",
    "mouse movement",
    "mouse clicking",
    "mouse dragging",
    "keyboard typing",
    "hotkeys",
    "clipboard read/write",
    "file dialog automation",
    "terminal/shell execution",
    "package installs",
    "browser/desktop automation",
    "PyAutoGUI/Playwright/MCP calls",
    "cloud calls",
    "message sending",
    "secret, password, token, browser-session, and private-data reads",
)


@dataclass(frozen=True)
class DesktopCapabilityPolicy:
    real_screen_observation_enabled: bool
    real_desktop_control_enabled: bool
    screen_capture_allowed: bool
    screenshot_allowed: bool
    window_inspection_allowed: bool
    app_launch_allowed: bool
    mouse_allowed: bool
    keyboard_allowed: bool
    clipboard_allowed: bool
    file_dialog_allowed: bool
    terminal_allowed: bool
    package_install_allowed: bool
    automation_backends_enabled: tuple[str, ...]
    allowed_status_actions: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def get_desktop_capability_policy() -> DesktopCapabilityPolicy:
    return DesktopCapabilityPolicy(
        real_screen_observation_enabled=False,
        real_desktop_control_enabled=False,
        screen_capture_allowed=False,
        screenshot_allowed=False,
        window_inspection_allowed=False,
        app_launch_allowed=False,
        mouse_allowed=False,
        keyboard_allowed=False,
        clipboard_allowed=False,
        file_dialog_allowed=False,
        terminal_allowed=False,
        package_install_allowed=False,
        automation_backends_enabled=(),
        allowed_status_actions=ALLOWED_DESKTOP_STATUS_ACTIONS,
    )


def desktop_policy_summary() -> str:
    return "DesktopAgent is safety/status only. Real screen observation and real desktop control are locked."
