from __future__ import annotations

from .models import DesktopAppCategory, DesktopAppRisk, DesktopAppRiskLevel


_APP_MARKERS = {
    DesktopAppCategory.TERMINAL: ("terminal", "powershell", "cmd", "command prompt", "bash", "wsl", "python", "node", "code execution"),
    DesktopAppCategory.SYSTEM_SETTINGS: ("settings", "control panel", "registry", "device manager", "services", "task manager"),
    DesktopAppCategory.FILE_MANAGER: ("file explorer", "explorer", "downloads", "documents", "desktop folder", "folder"),
    DesktopAppCategory.MESSAGING: ("whatsapp", "telegram", "signal", "discord", "slack", "email", "mail", "gmail"),
    DesktopAppCategory.FINANCE: ("bank", "banking", "wallet", "payment", "paypal", "stripe", "upi"),
    DesktopAppCategory.SECRET_STORE: ("password", "vault", "keychain", "secret", "token", "credential"),
    DesktopAppCategory.PERSONAL_DATA: ("photos", "contacts", "calendar", "notes", "personal", "chat"),
    DesktopAppCategory.PRODUCTIVITY: ("notepad", "word", "excel", "powerpoint", "vscode", "vs code"),
}

_RISK_BY_CATEGORY = {
    DesktopAppCategory.STATUS_SURFACE: DesktopAppRiskLevel.SAFE_STATUS_ONLY,
    DesktopAppCategory.PRODUCTIVITY: DesktopAppRiskLevel.NORMAL_APP,
    DesktopAppCategory.PERSONAL_DATA: DesktopAppRiskLevel.SENSITIVE_PERSONAL,
    DesktopAppCategory.SECRET_STORE: DesktopAppRiskLevel.CREDENTIALS_OR_SECRETS,
    DesktopAppCategory.FINANCE: DesktopAppRiskLevel.FINANCIAL_OR_PAYMENT,
    DesktopAppCategory.MESSAGING: DesktopAppRiskLevel.MESSAGING_OR_EXTERNAL_SEND,
    DesktopAppCategory.FILE_MANAGER: DesktopAppRiskLevel.FILE_SYSTEM_SENSITIVE,
    DesktopAppCategory.SYSTEM_SETTINGS: DesktopAppRiskLevel.SYSTEM_SETTINGS,
    DesktopAppCategory.TERMINAL: DesktopAppRiskLevel.TERMINAL_OR_CODE_EXECUTION,
    DesktopAppCategory.UNKNOWN: DesktopAppRiskLevel.UNKNOWN_HIGH_RISK,
}


def classify_desktop_app_risk(app_or_category: str) -> DesktopAppRisk:
    query = " ".join(str(app_or_category or "").strip().lower().split())
    category = DesktopAppCategory.UNKNOWN
    if query in {"status", "desktop status", "policy"}:
        category = DesktopAppCategory.STATUS_SURFACE
    else:
        for candidate, markers in _APP_MARKERS.items():
            if any(marker in query for marker in markers):
                category = candidate
                break
    risk = _RISK_BY_CATEGORY.get(category, DesktopAppRiskLevel.UNKNOWN_HIGH_RISK)
    allowed = category == DesktopAppCategory.STATUS_SURFACE
    return DesktopAppRisk(
        query=query or "unknown",
        category=category,
        risk_level=risk,
        allowed_for_control_now=allowed,
        reason="String classification only. Eva does not inspect running apps, windows, screen contents, files, or private app state.",
        safe_alternative="Use DesktopAgent status and policy previews until a future approved observation/control gate exists.",
    )
