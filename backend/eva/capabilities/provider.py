from __future__ import annotations

from typing import Protocol

from .models import Capability


class BaseCapabilityProvider(Protocol):
    provider_id: str
    provider_name: str

    def list_capabilities(self) -> list[Capability]:
        ...
