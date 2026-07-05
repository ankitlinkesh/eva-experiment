from __future__ import annotations

from .models import MockObservation


def make_mock_observations(*, context_summary: str, threat_summary: str, selected_capabilities: tuple[str, ...]) -> tuple[MockObservation, ...]:
    capabilities = ", ".join(selected_capabilities) if selected_capabilities else "none"
    return (
        MockObservation(
            observation_id="obs_01",
            source="context_preview",
            summary=f"Context summary: {context_summary}",
            trusted=False,
        ),
        MockObservation(
            observation_id="obs_02",
            source="threat_preview",
            summary=f"Threat summary: {threat_summary}",
            trusted=True,
        ),
        MockObservation(
            observation_id="obs_03",
            source="capability_preview",
            summary=f"Selected preview capabilities: {capabilities}",
            trusted=True,
        ),
    )
