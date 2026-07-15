"""Perception & grounding — a lightweight, opt-in situational model (Phase 44).

See :mod:`eva.perception.situational_model`. The one design rule: **awareness
is built from window/app metadata, never from pixels.** Continuous perception
must not mean continuously screenshotting the user; pixel capture stays the
override-class ``screen.observe`` tool behind the permission gate.
"""

from __future__ import annotations

from .situational_model import (
    Situation,
    capture_situation,
    ground_observation,
    perception_enabled,
    situational_summary,
)

__all__ = [
    "Situation",
    "capture_situation",
    "ground_observation",
    "perception_enabled",
    "situational_summary",
]
