from __future__ import annotations

from .models import DesktopActionCategory, DesktopActionSafetyDecision, DesktopBlockedAction


_ALIASES = {
    "status": DesktopActionCategory.DESKTOP_STATUS,
    "desktop status": DesktopActionCategory.DESKTOP_STATUS,
    "app status": DesktopActionCategory.APP_STATUS,
    "window status": DesktopActionCategory.WINDOW_STATUS,
    "screen": DesktopActionCategory.SCREEN_CAPTURE,
    "screen capture": DesktopActionCategory.SCREEN_CAPTURE,
    "screenshot": DesktopActionCategory.SCREENSHOT,
    "capture screen": DesktopActionCategory.SCREENSHOT,
    "launch": DesktopActionCategory.APP_LAUNCH,
    "open app": DesktopActionCategory.APP_LAUNCH,
    "app launch": DesktopActionCategory.APP_LAUNCH,
    "mouse move": DesktopActionCategory.MOUSE_MOVE,
    "move mouse": DesktopActionCategory.MOUSE_MOVE,
    "click": DesktopActionCategory.MOUSE_CLICK,
    "mouse click": DesktopActionCategory.MOUSE_CLICK,
    "drag": DesktopActionCategory.MOUSE_DRAG,
    "mouse drag": DesktopActionCategory.MOUSE_DRAG,
    "type": DesktopActionCategory.KEYBOARD_TYPE,
    "keyboard type": DesktopActionCategory.KEYBOARD_TYPE,
    "hotkey": DesktopActionCategory.HOTKEY,
    "shortcut": DesktopActionCategory.HOTKEY,
    "clipboard read": DesktopActionCategory.CLIPBOARD_READ,
    "read clipboard": DesktopActionCategory.CLIPBOARD_READ,
    "clipboard write": DesktopActionCategory.CLIPBOARD_WRITE,
    "write clipboard": DesktopActionCategory.CLIPBOARD_WRITE,
    "file dialog": DesktopActionCategory.FILE_DIALOG,
    "file picker": DesktopActionCategory.FILE_DIALOG,
    "terminal": DesktopActionCategory.TERMINAL_SHELL,
    "shell": DesktopActionCategory.TERMINAL_SHELL,
    "command prompt": DesktopActionCategory.TERMINAL_SHELL,
    "powershell": DesktopActionCategory.TERMINAL_SHELL,
    "install": DesktopActionCategory.INSTALL_PACKAGE,
    "package install": DesktopActionCategory.INSTALL_PACKAGE,
    "send": DesktopActionCategory.EXTERNAL_SEND,
    "external send": DesktopActionCategory.EXTERNAL_SEND,
}

_PREVIEW_ALLOWED = {
    DesktopActionCategory.DESKTOP_STATUS,
    DesktopActionCategory.APP_STATUS,
    DesktopActionCategory.WINDOW_STATUS,
}

_BLOCK_REASONS = {
    DesktopActionCategory.SCREEN_CAPTURE: "Real screen observation is locked in Phase 14A.",
    DesktopActionCategory.SCREENSHOT: "Screenshots are real screen observation and are locked in Phase 14A.",
    DesktopActionCategory.APP_LAUNCH: "Launching apps is real desktop control and is locked.",
    DesktopActionCategory.MOUSE_MOVE: "Mouse movement is real desktop control and is locked.",
    DesktopActionCategory.MOUSE_CLICK: "Mouse clicking is real desktop control and is locked.",
    DesktopActionCategory.MOUSE_DRAG: "Mouse dragging is real desktop control and is locked.",
    DesktopActionCategory.KEYBOARD_TYPE: "Keyboard typing is real desktop control and is locked.",
    DesktopActionCategory.HOTKEY: "Hotkeys are real desktop control and are locked.",
    DesktopActionCategory.CLIPBOARD_READ: "Clipboard reads can expose private data and are locked.",
    DesktopActionCategory.CLIPBOARD_WRITE: "Clipboard writes change local state and are locked.",
    DesktopActionCategory.FILE_DIALOG: "File dialog automation can expose or move local files and is locked.",
    DesktopActionCategory.TERMINAL_SHELL: "Terminal and shell execution are blocked.",
    DesktopActionCategory.INSTALL_PACKAGE: "Package installs are blocked.",
    DesktopActionCategory.EXTERNAL_SEND: "External sends require future confirmation-gated design and are locked.",
    DesktopActionCategory.UNKNOWN: "Unknown desktop actions are blocked by default.",
}


def normalize_desktop_action(action: str) -> DesktopActionCategory:
    text = " ".join(str(action or "").strip().lower().replace("-", " ").split())
    if not text:
        return DesktopActionCategory.UNKNOWN
    if text in _ALIASES:
        return _ALIASES[text]
    for key, category in _ALIASES.items():
        if key in text:
            return category
    return DesktopActionCategory.UNKNOWN


def evaluate_desktop_action_safety(action: str) -> DesktopActionSafetyDecision:
    category = normalize_desktop_action(action)
    if category in _PREVIEW_ALLOWED:
        return DesktopActionSafetyDecision(
            action=str(action or "").strip() or category.value,
            category=category,
            decision="preview_only",
            allowed_now=True,
            reason="Allowed only as a status/policy preview. No screen, window, app, mouse, keyboard, or clipboard state is read or changed.",
            required_future_gate="Future DesktopAgent observation/control gate with explicit user command, privacy checks, app risk policy, and verification.",
            safe_alternative="Use `eva desktop policy` or `eva desktop readiness` for current locked status.",
        )
    reason = _BLOCK_REASONS.get(category, _BLOCK_REASONS[DesktopActionCategory.UNKNOWN])
    return DesktopActionSafetyDecision(
        action=str(action or "").strip() or category.value,
        category=category,
        decision="blocked",
        allowed_now=False,
        reason=reason,
        required_future_gate="Future permission-gated DesktopAgent executor; not enabled in Phase 14A.",
        safe_alternative="Use `eva desktop action safety <action>` for a preview, or keep the task manual.",
    )


def list_blocked_desktop_actions() -> list[DesktopBlockedAction]:
    categories = [
        DesktopActionCategory.SCREEN_CAPTURE,
        DesktopActionCategory.SCREENSHOT,
        DesktopActionCategory.APP_LAUNCH,
        DesktopActionCategory.MOUSE_MOVE,
        DesktopActionCategory.MOUSE_CLICK,
        DesktopActionCategory.MOUSE_DRAG,
        DesktopActionCategory.KEYBOARD_TYPE,
        DesktopActionCategory.HOTKEY,
        DesktopActionCategory.CLIPBOARD_READ,
        DesktopActionCategory.CLIPBOARD_WRITE,
        DesktopActionCategory.FILE_DIALOG,
        DesktopActionCategory.TERMINAL_SHELL,
        DesktopActionCategory.INSTALL_PACKAGE,
        DesktopActionCategory.EXTERNAL_SEND,
        DesktopActionCategory.UNKNOWN,
    ]
    return [
        DesktopBlockedAction(
            action=category.value,
            category=category,
            reason=_BLOCK_REASONS.get(category, _BLOCK_REASONS[DesktopActionCategory.UNKNOWN]),
            future_gate="Future DesktopAgent executor with human-in-the-loop permission gates.",
        )
        for category in categories
    ]
