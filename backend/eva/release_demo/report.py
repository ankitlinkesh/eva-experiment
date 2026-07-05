from __future__ import annotations

from .demo_profile import build_demo_profile
from .models import ReleaseDemoProfile


def build_release_demo_report() -> ReleaseDemoProfile:
    return build_demo_profile()
