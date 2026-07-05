from __future__ import annotations

import re

from .models import SensitiveScreenClassification
from .observation_policy import boundary_lines


SENSITIVE_SCREEN_CATEGORIES = (
    "password_or_login_screen",
    "payment_or_banking_screen",
    "private_chat_or_email",
    "browser_session_or_cookie_context",
    "token_or_secret_context",
    "private_file_path_context",
    "system_settings_or_security_screen",
    "terminal_or_command_prompt",
    "code_with_secret_like_content",
    "unknown_sensitive_screen",
)

_PRIVATE_PATH = re.compile(r"(?:[A-Za-z]:\\Users\\|/(?:home|Users)/)", re.IGNORECASE)
_CODE_MARKERS = ("def ", "class ", "function ", "const ", "let ", "var ", "import ", "return ")
_SECRET_MARKERS = ("api_key", "api token", "token", "secret", "password", "bearer", "credential")


def classify_sensitive_screen(
    visible_text: object,
    *,
    app_name: str = "",
    window_title: str = "",
) -> SensitiveScreenClassification:
    text = " ".join(str(item or "") for item in (app_name, window_title, visible_text)).lower()
    category, reason, confidence = _classify(text)
    return SensitiveScreenClassification(
        category=category,
        sensitive=True,
        confidence=confidence,
        reason=reason,
        handling="Redact known sensitive values, expose summary metadata only, and block raw screen content.",
    )


def sensitive_screen_policy_text() -> str:
    lines = [
        "Real Desktop Observation Mode sensitive-screen policy",
        *boundary_lines(),
        "Every observation is classified before summary output; unknown screens fail closed as sensitive.",
        "Sensitive screen categories:",
    ]
    lines.extend(f"- {category}" for category in SENSITIVE_SCREEN_CATEGORIES)
    lines.extend(
        [
            "Known secret-like and private-path-like values are redacted.",
            "Raw pixels, OCR output, credentials, and private screen dumps are not returned or saved.",
        ]
    )
    return "\n".join(lines)


def _classify(text: str) -> tuple[str, str, str]:
    if any(marker in text for marker in _CODE_MARKERS) and any(marker in text for marker in _SECRET_MARKERS):
        return ("code_with_secret_like_content", "Code-like content includes secret-like markers.", "high")
    if any(marker in text for marker in ("sign in", "login", "log in", "password", "passcode", "authentication")):
        return ("password_or_login_screen", "Login or password context detected.", "high")
    if any(marker in text for marker in ("payment", "banking", "bank transfer", "account balance", "credit card", "billing")):
        return ("payment_or_banking_screen", "Payment or banking context detected.", "high")
    if any(marker in text for marker in ("private chat", "email", "inbox", "direct message", "conversation")):
        return ("private_chat_or_email", "Private communication context detected.", "high")
    if any(marker in text for marker in ("browser cookie", "cookies", "session storage", "browser session", "local storage")):
        return ("browser_session_or_cookie_context", "Browser session or cookie context detected.", "high")
    if _PRIVATE_PATH.search(text):
        return ("private_file_path_context", "Private user path context detected.", "high")
    if any(marker in text for marker in ("system settings", "windows security", "security settings", "firewall", "permissions")):
        return ("system_settings_or_security_screen", "System or security settings context detected.", "high")
    if any(marker in text for marker in ("powershell", "terminal", "command prompt", "cmd.exe", "shell prompt")):
        return ("terminal_or_command_prompt", "Terminal or command-prompt context detected.", "high")
    if any(marker in text for marker in _SECRET_MARKERS):
        return ("token_or_secret_context", "Token, secret, or credential context detected.", "high")
    return ("unknown_sensitive_screen", "Screen sensitivity cannot be established safely.", "conservative")
