from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..desktop.windows import get_active_window


PRIVATE_WINDOW_MARKERS = ("whatsapp", "gmail", "mail", "bank", "password", "signin", "login", "account", "checkout")


@dataclass(frozen=True)
class ScreenFrame:
    frame_id: str
    local_path: str
    width: int
    height: int
    created_at: str
    active_window_title: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScreenObservation:
    observation_id: str
    frame_id: str
    active_window_title: str | None
    active_process: str | None
    screenshot_path: str
    local_path: str
    width: int
    height: int
    created_at: str
    local_summary: str
    privacy_risk: bool
    ui_targets: list[dict[str, Any]] = field(default_factory=list)
    source: str = "live_screen"
    verified_live: bool = True
    ok: bool = True
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_active_window_title() -> str | None:
    window = get_active_window()
    return window.title if window else None


def _active_window_info() -> tuple[str | None, str | None]:
    window = get_active_window()
    if not window:
        return None, None
    return window.title, window.process_name


def _privacy_risk(title: str | None) -> bool:
    lower = (title or "").lower()
    return any(marker in lower for marker in PRIVATE_WINDOW_MARKERS)


def capture_screen(reason: str) -> ScreenFrame:
    if not str(reason or "").strip():
        raise ValueError("Screen capture requires an active task reason.")
    try:
        from PIL import ImageGrab  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"Screen capture dependency unavailable: {exc}") from exc
    image = ImageGrab.grab()
    root = Path(__file__).resolve().parents[3] / "data" / "screen_frames"
    root.mkdir(parents=True, exist_ok=True)
    frame_id = uuid4().hex
    path = root / f"{frame_id}.png"
    image.save(path)
    title = get_active_window_title()
    return ScreenFrame(frame_id, str(path), int(image.width), int(image.height), datetime.now(timezone.utc).isoformat(), title)


def observe_current_state(reason: str) -> ScreenObservation:
    return observe_screen_once(reason)


def observe_screen_once(reason: str, task_id: str | None = None, app_hint: str | None = None) -> ScreenObservation:
    if not str(reason or "").strip():
        now = datetime.now(timezone.utc).isoformat()
        return ScreenObservation(
            observation_id=uuid4().hex,
            frame_id="",
            active_window_title=None,
            active_process=None,
            screenshot_path="",
            local_path="",
            width=0,
            height=0,
            created_at=now,
            local_summary="Screen observation refused because no active task reason was provided.",
            privacy_risk=False,
            source="live_screen",
            verified_live=False,
            ok=False,
            error="reason_required",
        )
    try:
        frame = capture_screen(reason)
    except Exception as exc:
        title, process = _active_window_info()
        now = datetime.now(timezone.utc).isoformat()
        return ScreenObservation(
            observation_id=uuid4().hex,
            frame_id="",
            active_window_title=title,
            active_process=process,
            screenshot_path="",
            local_path="",
            width=0,
            height=0,
            created_at=now,
            local_summary=f"Screen observation unavailable: {str(exc)[:160]}",
            privacy_risk=_privacy_risk(title),
            source="live_screen",
            verified_live=False,
            ok=False,
            error="screen_observation_unavailable",
        )
    title, process = _active_window_info()
    active_title = title or frame.active_window_title
    risk = _privacy_risk(active_title)
    observation = ScreenObservation(
        observation_id=uuid4().hex,
        frame_id=frame.frame_id,
        active_window_title=active_title,
        active_process=process,
        screenshot_path=frame.local_path,
        local_path=frame.local_path,
        width=frame.width,
        height=frame.height,
        created_at=frame.created_at,
        local_summary="",
        privacy_risk=risk,
        ui_targets=[],
        source="live_screen",
        verified_live=True,
        ok=True,
    )
    summary = summarize_visible_state_locally(observation)
    return ScreenObservation(**{**observation.as_dict(), "local_summary": summary})


def summarize_visible_state_locally(observation: ScreenObservation) -> str:
    title = observation.active_window_title or "unknown window"
    suffix = " Privacy-sensitive window likely." if observation.privacy_risk else ""
    return f"Captured one local screen frame for active task. Active window: {title}.{suffix}"
