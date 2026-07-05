from __future__ import annotations

from .models import BrowserDomainPolicy


def get_default_domain_policy() -> BrowserDomainPolicy:
    return BrowserDomainPolicy(
        policy_name="Phase 13A default browser domain policy",
        default_domain_mode="preview_only",
        public_page_preview_allowed=False,
        private_page_preview_allowed=False,
        logged_in_page_preview_allowed=False,
        cookies_allowed=False,
        local_storage_allowed=False,
        profile_access_allowed=False,
        passwords_allowed=False,
        notes=(
            "No page is opened or read in Phase 13A.",
            "Logged-in, private, account, payment, admin, Gmail, chat, and banking pages remain blocked for automation.",
            "Cookies, localStorage, session data, browser profiles, passwords, and tokens are never read.",
            "Future phases must require domain allowlists, visible user intent, observation limits, and human confirmation gates.",
        ),
    )


def is_domain_preview_allowed(domain: str) -> bool:
    _ = str(domain or "").strip()
    return False
