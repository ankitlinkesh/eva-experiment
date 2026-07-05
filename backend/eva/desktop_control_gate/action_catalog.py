from __future__ import annotations


ACTION_CLASSES = (
    "observe_only_reference",
    "click_candidate",
    "type_candidate",
    "hotkey_candidate",
    "clipboard_candidate",
    "app_launch_candidate",
    "window_focus_candidate",
    "window_move_or_resize_candidate",
    "browser_control_candidate",
    "shell_or_terminal_candidate",
    "package_install_candidate",
    "file_write_candidate",
    "credential_or_secret_candidate",
    "destructive_or_irreversible_candidate",
    "unknown_or_hallucinated_action",
)


def classify_action(request: str) -> str:
    text = " ".join(str(request or "").lower().split())
    if any(term in text for term in ("password", "credential", "secret", "cookie", "session", "token")):
        return "credential_or_secret_candidate"
    if any(term in text for term in ("hotkey", "ctrl ", "alt ", "shortcut", "key combo")):
        return "hotkey_candidate"
    if any(term in text for term in ("delete", "erase", "destroy", "permanently", "irreversible")):
        return "destructive_or_irreversible_candidate"
    if any(term in text for term in ("pip install", "package install", "install package")):
        return "package_install_candidate"
    if any(term in text for term in ("terminal", "shell", "command prompt", "powershell", "command")):
        return "shell_or_terminal_candidate"
    if any(term in text for term in ("browser control", "control the browser", "navigate browser")):
        return "browser_control_candidate"
    if any(term in text for term in ("clipboard", "copy ", "paste ")):
        return "clipboard_candidate"
    if any(term in text for term in ("resize", "move window", "window move")):
        return "window_move_or_resize_candidate"
    if any(term in text for term in ("focus window", "focus the", "activate window")):
        return "window_focus_candidate"
    if any(term in text for term in ("launch ", "open app", "start app")):
        return "app_launch_candidate"
    if any(term in text for term in ("click", "press button", "tap ")):
        return "click_candidate"
    if any(term in text for term in ("type ", "enter text", "fill ")):
        return "type_candidate"
    if any(term in text for term in ("write file", "write this file", "save file", "edit file")):
        return "file_write_candidate"
    if any(term in text for term in ("observe", "status", "read-only", "read only", "inspect screen")):
        return "observe_only_reference"
    return "unknown_or_hallucinated_action"


def format_action_catalog() -> str:
    lines = ["Desktop control action catalog", "All classes are classification-only; no action executes."]
    lines.extend(f"- {item}" for item in ACTION_CLASSES)
    return "\n".join(lines)
