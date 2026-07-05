from __future__ import annotations

from .models import DesktopScreenRedactionRule


def get_desktop_screen_redaction_rules() -> tuple[DesktopScreenRedactionRule, ...]:
    return (
        DesktopScreenRedactionRule("Passwords and credentials", "passwords_or_credentials", "[REDACTED_PASSWORD]", "Future summaries must remove visible passwords, passphrases, login codes, and credential fields."),
        DesktopScreenRedactionRule("Tokens and secrets", "tokens_or_secrets", "[REDACTED_SECRET]", "Future summaries must remove API keys, bearer tokens, private keys, cookies, session IDs, and secret-looking values."),
        DesktopScreenRedactionRule("Banking and payment details", "banking_or_payment", "[REDACTED_PAYMENT]", "Future summaries must remove card numbers, account numbers, balances, transaction details, and payment forms."),
        DesktopScreenRedactionRule("Personal messages", "personal_messages", "[REDACTED_MESSAGE]", "Future summaries must minimize chat/message content and require approval before reading sensitive conversations."),
        DesktopScreenRedactionRule("Email inbox content", "email_inbox", "[REDACTED_EMAIL_CONTENT]", "Future summaries must avoid inbox dumps and redact addresses or message snippets unless explicitly approved."),
        DesktopScreenRedactionRule("Private documents", "private_documents", "[REDACTED_PRIVATE_DOCUMENT]", "Future summaries must avoid raw document text unless the user explicitly asks and confirms the scope."),
        DesktopScreenRedactionRule("Browser sessions", "browser_sessions", "[REDACTED_BROWSER_SESSION]", "Future summaries must never include cookies, localStorage, session tokens, browser profile data, or password manager contents."),
        DesktopScreenRedactionRule("Code with secrets", "code_with_secrets", "[REDACTED_CODE_SECRET]", "Future summaries must redact keys, tokens, passwords, and private configuration values visible in code."),
    )
