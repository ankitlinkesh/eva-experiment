from __future__ import annotations

from .models import LLMCallBoundary


def get_llm_call_boundary() -> LLMCallBoundary:
    return LLMCallBoundary(False, False, False, "Phase 15A is mock/dry-run metadata only. It does not read environment files or invoke providers.")
