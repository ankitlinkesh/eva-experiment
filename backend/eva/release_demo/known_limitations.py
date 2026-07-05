from __future__ import annotations


KNOWN_LIMITATIONS = (
    "Eva is a local-first agent foundation, not an unrestricted autonomous operator.",
    "Live provider use is not part of the Phase 29 demo profile.",
    "Browser observation is public-URL read-only; clicking, typing, login, and sessions are unavailable.",
    "Desktop observation is one-shot and redacted; desktop control is unavailable.",
    "News reports are local/mock or safe-read-only and do not provide unrestricted crawling.",
    "CodingAgent prepares previews and reports but cannot edit source or apply patches.",
    "Voice remains a locked/mock foundation without microphone or audio execution.",
    "No publishing, uploading, installer creation, package release, or git release operation is available.",
    "Broad file mutation is blocked; Phase 12L is the only narrow real write path.",
)


def known_limitations_text() -> str:
    return "\n".join(("Eva known limitations", *[f"- {item}" for item in KNOWN_LIMITATIONS]))
