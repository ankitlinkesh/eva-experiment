from __future__ import annotations

from .approval_model import DesktopConfirmationPhrase, preview_desktop_approval_request


def preview_desktop_confirmation_phrase(request: str) -> DesktopConfirmationPhrase:
    return preview_desktop_approval_request(request).decision.confirmation_phrase
