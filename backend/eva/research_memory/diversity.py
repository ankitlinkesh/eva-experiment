from __future__ import annotations

import re
from typing import Iterable


def tokenize_for_diversity(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(text or "").lower())
        if len(token) > 2
    }


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def compute_mmr_score(relevance: float, similarity: float, lambda_param: float = 0.65) -> float:
    safe_lambda = max(0.0, min(1.0, float(lambda_param)))
    return (safe_lambda * float(relevance or 0.0)) - ((1.0 - safe_lambda) * float(similarity or 0.0))


def rerank_for_diversity(results: Iterable[object], limit: int = 5, lambda_param: float = 0.65) -> list[object]:
    candidates = list(results or [])
    if len(candidates) <= 1:
        return candidates
    safe_limit = max(1, min(len(candidates), int(limit or 5)))
    sorted_candidates = sorted(candidates, key=_relevance_score, reverse=True)
    max_relevance = max((_relevance_score(candidate) for candidate in sorted_candidates), default=1.0) or 1.0
    selected = [sorted_candidates.pop(0)]
    selected_tokens = [_tokens_for_result(selected[0])]

    while sorted_candidates and len(selected) < safe_limit:
        best_index = 0
        best_score = float("-inf")
        for index, candidate in enumerate(sorted_candidates):
            tokens = _tokens_for_result(candidate)
            similarity = max((jaccard_similarity(tokens, existing) for existing in selected_tokens), default=0.0)
            score = compute_mmr_score(_relevance_score(candidate) / max_relevance, similarity, lambda_param=lambda_param)
            if score > best_score:
                best_index = index
                best_score = score
        choice = sorted_candidates.pop(best_index)
        selected.append(choice)
        selected_tokens.append(_tokens_for_result(choice))

    selected.extend(sorted_candidates)
    return selected


def _relevance_score(result: object) -> float:
    score = getattr(result, "score", None)
    if score is not None:
        try:
            return float(score)
        except (TypeError, ValueError):
            pass
    quality = getattr(result, "quality_score", 0.0)
    try:
        return float(quality or 0.0) * 10.0
    except (TypeError, ValueError):
        return 0.0


def _tokens_for_result(result: object) -> set[str]:
    parts = [
        getattr(result, "title", ""),
        getattr(result, "summary", ""),
        getattr(result, "snippet", ""),
        getattr(result, "text", ""),
        getattr(result, "content_preview", ""),
    ]
    return tokenize_for_diversity(" ".join(str(part or "") for part in parts))
