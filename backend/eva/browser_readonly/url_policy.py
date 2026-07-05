from __future__ import annotations

import ipaddress
import re
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from .models import URLSafetyDecision
from .observation_policy import boundary_lines


ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_SCHEMES = ("file", "ftp", "data", "javascript", "chrome", "edge", "about")
INTERNAL_SUFFIXES = (
    ".internal",
    ".intranet",
    ".localhost",
    ".local",
    ".lan",
    ".home",
    ".corp",
)
SENSITIVE_MARKERS = (
    "api_key",
    "apikey",
    "auth",
    "bearer",
    "cookie",
    "credential",
    "password",
    "passwd",
    "secret",
    "session",
    "token",
)
COMMAND_MARKERS = (";", "|", "`", "$(", "&&", "||", "\r", "\n", "\x00")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def validate_url(value: str) -> URLSafetyDecision:
    raw = str(value or "").strip()
    safe_requested = _sanitize_url_for_output(raw)
    if not raw:
        return _blocked(safe_requested, "missing_url", "URL is required.")
    if _CONTROL_CHARS.search(raw):
        return _blocked(safe_requested, "command_injection", "Command-injection-like control characters are blocked.")

    try:
        parsed = urlsplit(raw)
    except ValueError:
        return _blocked(safe_requested, "malformed_url", "Malformed URL is blocked.")

    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        label = scheme or "missing"
        return _blocked(safe_requested, "blocked_scheme", f"Blocked URL scheme: {label}. Only http and https are allowed.")
    if parsed.username is not None or parsed.password is not None:
        return _blocked(safe_requested, "embedded_credentials", "Embedded credentials are blocked.")

    hostname = (parsed.hostname or "").rstrip(".").lower()
    if not hostname:
        return _blocked(safe_requested, "missing_hostname", "Public hostname is required.")
    if hostname == "localhost":
        return _blocked(safe_requested, "local_hostname", "Local hostname is blocked.")
    if hostname.endswith(INTERNAL_SUFFIXES) or "." not in hostname:
        return _blocked(safe_requested, "internal_hostname", "Internal hostname is blocked.")

    ip_decision = _classify_ip(hostname)
    if ip_decision is not None:
        return _blocked(safe_requested, ip_decision[0], ip_decision[1])

    decoded_target = unquote(f"{parsed.path}?{parsed.query}#{parsed.fragment}").lower()
    if any(marker in decoded_target for marker in SENSITIVE_MARKERS):
        return _blocked(safe_requested, "sensitive_url_content", "Sensitive token, password, cookie, or session URL content is blocked.")
    if any(marker in decoded_target for marker in COMMAND_MARKERS):
        return _blocked(safe_requested, "command_injection", "Command-injection-looking URL content is blocked.")

    try:
        port = parsed.port
    except ValueError:
        return _blocked(safe_requested, "malformed_port", "Malformed URL port is blocked.")

    host_display = f"[{hostname}]" if ":" in hostname else hostname
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = host_display if port is None or default_port else f"{host_display}:{port}"
    path = quote(unquote(parsed.path or "/"), safe="/:@-._~!$&'()*+,=")
    query = urlencode(parse_qsl(parsed.query, keep_blank_values=True), doseq=True)
    fragment = quote(unquote(parsed.fragment), safe="-._~!$&'()*+,;=:@/?")
    normalized = urlunsplit((scheme, netloc, path, query, fragment))
    return URLSafetyDecision(
        requested_url=safe_requested,
        normalized_url=normalized,
        allowed=True,
        reason="Allowed public HTTP(S) URL after local policy validation.",
        blocked_class="none",
    )


def url_policy_text() -> str:
    return "\n".join(
        [
            "Real Browser Read-Only Mode URL policy",
            *boundary_lines(),
            "Allowed: user-provided public http:// and https:// URLs after safe normalization.",
            "Blocked: file, ftp, data, javascript, chrome, edge, and about schemes.",
            "Blocked: localhost, non-global IPs, private LAN ranges, link-local ranges, metadata services, and internal hostnames.",
            "Blocked: embedded credentials and paths, queries, or fragments with obvious token/password/cookie/session markers.",
            "Blocked: command-injection-looking URL content and malformed URLs.",
            "Validation is local and performs no DNS or external network call.",
            "Any future backend must re-check resolved addresses and redirects before each read.",
        ]
    )


def blocked_url_classes_text() -> str:
    return "\n".join(
        [
            "Real Browser Read-Only Mode blocked URL classes",
            *boundary_lines(),
            "- Non-HTTP(S) schemes: file, ftp, data, javascript, chrome, edge, about.",
            "- Local/private targets: localhost, loopback, unspecified, private LAN, link-local, multicast, reserved, metadata IPs.",
            "- Internal names: single-label names and internal, local, intranet, lan, home, or corp suffixes.",
            "- Sensitive URLs: credentials, tokens, passwords, cookies, sessions, secrets, and auth markers.",
            "- Injection-like URLs: shell separators, command substitution, control characters, and encoded equivalents.",
        ]
    )


def _classify_ip(hostname: str) -> tuple[str, str] | None:
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return None
    if address == ipaddress.ip_address("169.254.169.254"):
        return ("metadata_service", "Metadata service IP is blocked.")
    if address.is_loopback or address.is_unspecified:
        return ("private_ip", "Private or local IP address is blocked.")
    if address.is_link_local:
        return ("link_local_ip", "Link-local IP address is blocked.")
    if not address.is_global:
        return ("private_ip", "Private, reserved, or non-global IP address is blocked.")
    return None


def _sanitize_url_for_output(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "[blocked malformed URL]"
    if not parsed.scheme:
        return value[:240]
    hostname = parsed.hostname or ""
    host_display = f"[{hostname}]" if ":" in hostname else hostname
    try:
        port = parsed.port
    except ValueError:
        port = None
    netloc = host_display + (f":{port}" if port is not None else "")
    if parsed.username is not None or parsed.password is not None:
        netloc = "[redacted credentials]@" + netloc
    pairs = []
    for key, item in parse_qsl(parsed.query, keep_blank_values=True):
        value_out = "[redacted secret-like value]" if any(marker in key.lower() for marker in SENSITIVE_MARKERS) else item
        pairs.append((key, value_out))
    query = urlencode(pairs, doseq=True)
    return urlunsplit((parsed.scheme, netloc, parsed.path, query, parsed.fragment))[:500]


def _blocked(requested_url: str, blocked_class: str, reason: str) -> URLSafetyDecision:
    return URLSafetyDecision(
        requested_url=requested_url,
        normalized_url="",
        allowed=False,
        reason=reason,
        blocked_class=blocked_class,
    )
