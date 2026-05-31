from __future__ import annotations

import re
import urllib.parse
from typing import Any


WEB_APPS: dict[str, dict[str, str]] = {
    "chatgpt": {"name": "ChatGPT", "url": "https://chatgpt.com"},
    "gmail": {"name": "Gmail", "url": "https://mail.google.com"},
    "youtube": {"name": "YouTube", "url": "https://www.youtube.com"},
    "google": {"name": "Google", "url": "https://www.google.com"},
    "github": {"name": "GitHub", "url": "https://github.com"},
    "google drive": {"name": "Google Drive", "url": "https://drive.google.com"},
    "google docs": {"name": "Google Docs", "url": "https://docs.google.com"},
    "google sheets": {"name": "Google Sheets", "url": "https://sheets.google.com"},
    "google calendar": {"name": "Google Calendar", "url": "https://calendar.google.com"},
    "openrouter": {"name": "OpenRouter", "url": "https://openrouter.ai"},
    "nvidia build": {"name": "NVIDIA Build", "url": "https://build.nvidia.com"},
    "hugging face": {"name": "Hugging Face", "url": "https://huggingface.co"},
    "stackoverflow": {"name": "Stack Overflow", "url": "https://stackoverflow.com"},
    "whatsapp web": {"name": "WhatsApp Web", "url": "https://web.whatsapp.com"},
    "linkedin": {"name": "LinkedIn", "url": "https://www.linkedin.com"},
    "reddit": {"name": "Reddit", "url": "https://www.reddit.com"},
    "notion": {"name": "Notion", "url": "https://www.notion.so"},
    "canva": {"name": "Canva", "url": "https://www.canva.com"},
}

WEB_APP_ALIASES: dict[str, str] = {
    "chat gpt": "chatgpt",
    "chatgpt": "chatgpt",
    "gmail": "gmail",
    "mail": "gmail",
    "youtube": "youtube",
    "you tube": "youtube",
    "google": "google",
    "github": "github",
    "git hub": "github",
    "drive": "google drive",
    "google drive": "google drive",
    "docs": "google docs",
    "google docs": "google docs",
    "sheets": "google sheets",
    "google sheets": "google sheets",
    "calendar": "google calendar",
    "google calendar": "google calendar",
    "openrouter": "openrouter",
    "open router": "openrouter",
    "nvidia build": "nvidia build",
    "build nvidia": "nvidia build",
    "huggingface": "hugging face",
    "hugging face": "hugging face",
    "stack overflow": "stackoverflow",
    "stackoverflow": "stackoverflow",
    "whatsapp": "whatsapp web",
    "whatsapp web": "whatsapp web",
    "linkedin": "linkedin",
    "reddit": "reddit",
    "notion": "notion",
    "canva": "canva",
}

SITE_SEARCH_TEMPLATES: dict[str, str] = {
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "google": "https://www.google.com/search?q={query}",
    "github": "https://github.com/search?q={query}",
    "stackoverflow": "https://stackoverflow.com/search?q={query}",
    "hugging face": "https://huggingface.co/search/full-text?q={query}",
}


def normalize_web_app_key(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip().lower())
    return WEB_APP_ALIASES.get(text, text)


def resolve_web_app(value: str) -> dict[str, Any] | None:
    key = normalize_web_app_key(value)
    app = WEB_APPS.get(key)
    if not app:
        return None
    return {"key": key, **app}


def build_site_search_url(site: str, query: str) -> str:
    key = normalize_web_app_key(site)
    template = SITE_SEARCH_TEMPLATES.get(key)
    if not template:
        raise ValueError(f"Site search is not supported for {site}.")
    clean = " ".join(str(query or "").strip().split())
    if not clean:
        raise ValueError("Search query is empty.")
    return template.format(query=urllib.parse.quote_plus(clean[:400]))


def supported_web_apps() -> list[str]:
    return sorted(WEB_APPS)


def supported_search_sites() -> list[str]:
    return sorted(SITE_SEARCH_TEMPLATES)
