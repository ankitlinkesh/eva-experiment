from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class OutputContract:
    name: str
    required_fields: tuple[str, ...]
    allowed_fields: tuple[str, ...]
    field_types: tuple[tuple[str, str], ...] = ()
    enum_values: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def expected_type(self, field_name: str) -> str | None:
        return dict(self.field_types).get(field_name)

    def allowed_values(self, field_name: str) -> tuple[str, ...] | None:
        return dict(self.enum_values).get(field_name)


@dataclass(frozen=True)
class StructuredOutputValidationResult:
    """A validation result that can only describe safe preview output."""

    valid: bool
    output_type: str
    issues: tuple[str, ...]
    blocked: bool
    normalized_output: Mapping[str, object] | None
    safe_output: Mapping[str, object]
