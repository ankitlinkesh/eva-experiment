from __future__ import annotations


WEBAPP_PLAYBOOKS: dict[str, dict[str, object]] = {
    "chatgpt": {
        "url": "https://chatgpt.com",
        "allowed_actions": ["open", "type_prompt_after_user_intent", "submit_after_user_intent"],
        "blocked_actions": ["read_credentials", "read_storage", "silent_private_prompt_submit"],
        "verification_signals": ["chatgpt.com domain", "visible composer", "visible response"],
        "confirmation_requirements": ["private/local content sent to ChatGPT cloud"],
    },
    "youtube": {
        "url": "https://www.youtube.com",
        "allowed_actions": ["open", "search", "activate_top_visible_result"],
        "blocked_actions": ["read_account_data", "random_coordinate_click"],
        "verification_signals": ["youtube.com/results", "youtube.com/watch", "visible player"],
        "confirmation_requirements": [],
    },
    "gmail": {
        "url": "https://mail.google.com",
        "allowed_actions": ["open"],
        "blocked_actions": ["read_mail_without_override", "send_without_confirmation"],
        "verification_signals": ["mail.google.com domain"],
        "confirmation_requirements": ["reading private mail", "sending mail"],
    },
    "github": {
        "url": "https://github.com",
        "allowed_actions": ["open", "search_public"],
        "blocked_actions": ["submit_private_change_without_confirmation"],
        "verification_signals": ["github.com domain", "search query in url"],
        "confirmation_requirements": ["posting or changing repository state"],
    },
    "generic": {
        "url": "",
        "allowed_actions": ["open_public_page", "verify_public_url"],
        "blocked_actions": ["storage_reads", "credential_reads", "payment_or_admin_submit"],
        "verification_signals": ["http url", "title"],
        "confirmation_requirements": ["private page reading", "form submission"],
    },
}


def get_webapp_playbook(name: str) -> dict[str, object] | None:
    return WEBAPP_PLAYBOOKS.get(str(name or "").lower())
