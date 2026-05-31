from __future__ import annotations

try:
    from pydantic.dataclasses import dataclass as schema_dataclass

    PYDANTIC_AVAILABLE = True
except Exception:
    from dataclasses import dataclass as schema_dataclass

    PYDANTIC_AVAILABLE = False


def schema_backend() -> str:
    return "pydantic" if PYDANTIC_AVAILABLE else "dataclass"
