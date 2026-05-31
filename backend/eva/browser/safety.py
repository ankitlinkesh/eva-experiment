from __future__ import annotations

import ipaddress
import re
import urllib.parse


SENSITIVE_HOST_MARKERS = (
    "accounts.",
    "bank",
    "billing",
    "checkout",
    "icloud",
    "login",
    "mail.",
    "paypal",
    "payment",
    "signin",
    "stripe",
    "wallet",
)
SENSITIVE_PATH_MARKERS = (
    "account",
    "auth",
    "billing",
    "checkout",
    "login",
    "oauth",
    "password",
    "payment",
    "profile",
    "reset",
    "security",
    "settings",
    "signin",
    "signup",
)


def normalize_public_url(url: str) -> str:
    target = str(url or "").strip()
    if not target:
        raise ValueError("URL is empty.")
    if re.match(r"^[a-z][a-z0-9+.-]*:", target, flags=re.IGNORECASE) and not target.lower().startswith(("http://", "https://")):
        raise ValueError("Only http and https URLs are allowed.")
    if "://" not in target:
        target = "https://" + target
    parsed = urllib.parse.urlparse(target)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Only valid http and https URLs are allowed.")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are refused.")
    return urllib.parse.urlunparse(parsed)


def safe_search_url(query: str) -> str:
    clean = str(query or "").strip()
    if not clean:
        raise ValueError("Search query is empty.")
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(clean[:400])


def is_local_or_private_host(hostname: str) -> bool:
    host = hostname.strip().lower()
    if not host:
        return True
    if host in {"localhost"} or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)


def page_read_safety(url: str) -> tuple[bool, str]:
    try:
        target = normalize_public_url(url)
    except ValueError as exc:
        return False, str(exc)
    parsed = urllib.parse.urlparse(target)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if is_local_or_private_host(host):
        return False, "local_or_private_page"
    if any(marker in host for marker in SENSITIVE_HOST_MARKERS):
        return False, "sensitive_site"
    if any(marker in path for marker in SENSITIVE_PATH_MARKERS):
        return False, "sensitive_page_path"
    return True, "safe_public_page"
