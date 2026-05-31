from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AppPlaybook:
    app_name: str
    aliases: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    allowed_hotkeys: tuple[str, ...]
    allowed_text_input: bool
    ui_target_hints: dict[str, tuple[str, ...]] = field(default_factory=dict)
    verification_rules: tuple[str, ...] = ()
    repair_rules: tuple[str, ...] = ()
    blocked_contexts: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


_PLAYBOOKS: dict[str, AppPlaybook] = {}


def _register(playbook: AppPlaybook) -> None:
    keys = {playbook.app_name.lower(), *(alias.lower() for alias in playbook.aliases)}
    for key in keys:
        _PLAYBOOKS[key] = playbook


_register(
    AppPlaybook(
        app_name="chrome",
        aliases=("google chrome", "browser"),
        allowed_actions=("open_url", "search_site", "copy_current_url", "new_tab", "close_tab", "reload", "back", "forward"),
        allowed_hotkeys=("ctrl+l", "ctrl+t", "ctrl+w", "f5", "alt+left", "alt+right", "tab", "enter"),
        allowed_text_input=True,
        ui_target_hints={"address_bar": ("Address and search bar", "omnibox"), "result": ("search result", "link")},
        verification_rules=("live address-bar probe must match target domain", "cached page state is never current verification"),
        repair_rules=("reopen target URL", "focus Chrome and retry live probe"),
        blocked_contexts=("cookies", "tokens", "password fields", "localStorage"),
    )
)
_register(
    AppPlaybook(
        app_name="youtube",
        aliases=("youtube in chrome", "you tube"),
        allowed_actions=("search", "activate_top_result", "verify_watch_page"),
        allowed_hotkeys=("tab", "enter"),
        allowed_text_input=False,
        ui_target_hints={"top_video": ("video", "thumbnail", "title"), "player": ("YouTube player", "watch")},
        verification_rules=("youtube.com/results verifies search", "youtube.com/watch or visible player verifies activation"),
        repair_rules=("reopen YouTube search", "ask user if top result target is low confidence"),
        blocked_contexts=("account menus", "comments posting", "purchase prompts"),
    )
)
_register(
    AppPlaybook(
        app_name="chatgpt",
        aliases=("chatgpt in chrome", "chat gpt"),
        allowed_actions=("open", "type_prompt", "submit_prompt", "read_visible_response"),
        allowed_hotkeys=("tab", "enter", "ctrl+l"),
        allowed_text_input=True,
        ui_target_hints={"prompt_box": ("Message ChatGPT", "prompt", "textbox")},
        verification_rules=("chatgpt.com must be visible", "response must be observed locally before provenance is chatgpt_in_chrome"),
        repair_rules=("open ChatGPT", "stop honestly if input or response cannot be verified"),
        blocked_contexts=("private local content without confirmation", "credentials", "files", "raw screenshots"),
    )
)
_register(
    AppPlaybook(
        app_name="spotify",
        aliases=("spotify desktop",),
        allowed_actions=("open", "search", "activate_selected_result", "pause", "next", "previous", "restart_current"),
        allowed_hotkeys=("enter", "space"),
        allowed_text_input=False,
        ui_target_hints={"top_result": ("Songs", "Top result", "Play"), "play_button": ("Play", "Pause")},
        verification_rules=("Windows media metadata if available", "Spotify window/title if available", "visible UI text if locally observed"),
        repair_rules=("retry focus then bounded activation", "report exact playback cannot be verified"),
        blocked_contexts=("API", "OAuth", "web player", "account secrets"),
    )
)
_register(
    AppPlaybook(
        app_name="whatsapp",
        aliases=("whatsapp desktop", "whatsapp web"),
        allowed_actions=("open", "search_contact", "prepare_draft", "send_after_confirmation"),
        allowed_hotkeys=("ctrl+f", "enter", "escape"),
        allowed_text_input=True,
        ui_target_hints={"search": ("Search or start new chat", "Search"), "message_box": ("Type a message", "message")},
        verification_rules=("draft text visible if readable", "sent likely only after input clears or message appears"),
        repair_rules=("clear typed unsent draft", "ask before WhatsApp Web fallback"),
        blocked_contexts=("unrelated chats", "message history reading without override", "silent send"),
    )
)
_register(
    AppPlaybook(
        app_name="notepad",
        aliases=("windows notepad",),
        allowed_actions=("open", "type_text", "save_after_confirmation"),
        allowed_hotkeys=("ctrl+s", "ctrl+a", "escape"),
        allowed_text_input=True,
        ui_target_hints={"editor": ("Text editor", "document")},
        verification_rules=("window title/process active", "text field contains expected text if readable"),
        repair_rules=("select and clear unsent text when safe",),
    )
)
_register(
    AppPlaybook(
        app_name="vscode",
        aliases=("vs code", "visual studio code"),
        allowed_actions=("open", "focus", "read_visible_state"),
        allowed_hotkeys=("ctrl+p", "ctrl+shift+p"),
        allowed_text_input=True,
        ui_target_hints={"command_palette": ("Command Palette",), "editor": ("editor",)},
        verification_rules=("VS Code window active",),
        repair_rules=("focus VS Code or ask for target file",),
        blocked_contexts=("destructive file actions in this patch",),
    )
)
_register(
    AppPlaybook(
        app_name="file explorer",
        aliases=("explorer", "windows explorer"),
        allowed_actions=("open", "focus", "read_visible_path"),
        allowed_hotkeys=("ctrl+l", "alt+left", "alt+right"),
        allowed_text_input=False,
        ui_target_hints={"address_bar": ("Address bar",), "file": ("file", "folder")},
        verification_rules=("File Explorer window active", "destructive file actions require override outside this patch"),
        repair_rules=("open known safe folder", "ask for override before destructive actions"),
        blocked_contexts=("delete", "move", "overwrite"),
    )
)


def get_playbook(name: str) -> AppPlaybook | None:
    return _PLAYBOOKS.get(str(name or "").strip().lower())


def list_playbooks() -> list[dict[str, Any]]:
    unique: dict[str, AppPlaybook] = {}
    for playbook in _PLAYBOOKS.values():
        unique[playbook.app_name] = playbook
    return [item.as_dict() for item in unique.values()]
