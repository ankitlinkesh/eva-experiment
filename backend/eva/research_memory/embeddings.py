from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass


@dataclass
class EmbeddingProviderStatus:
    provider: str
    enabled: bool
    local_only: bool
    cloud_capable: bool
    embedding_dim: int
    message: str


class BaseEmbeddingProvider:
    name = "base"
    embedding_dim = 0
    local_only = True
    cloud_capable = False

    def status(self) -> EmbeddingProviderStatus:
        return EmbeddingProviderStatus(
            provider=self.name,
            enabled=True,
            local_only=self.local_only,
            cloud_capable=self.cloud_capable,
            embedding_dim=self.embedding_dim,
            message="Embedding provider interface is available.",
        )

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class HashingEmbeddingProvider(BaseEmbeddingProvider):
    name = "hashing_local_fallback"
    embedding_dim = 128

    def status(self) -> EmbeddingProviderStatus:
        return EmbeddingProviderStatus(
            provider=self.name,
            enabled=True,
            local_only=True,
            cloud_capable=False,
            embedding_dim=self.embedding_dim,
            message="Lightweight local fallback embeddings are available for tests and future vector plumbing; quality is lexical, not production semantic.",
        )

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.embedding_dim
        for token in _tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            slot = int.from_bytes(digest[:4], "big") % self.embedding_dim
            sign = -1.0 if digest[4] % 2 else 1.0
            vector[slot] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            return vector
        return [round(value / norm, 8) for value in vector]


def get_embedding_provider() -> BaseEmbeddingProvider:
    return HashingEmbeddingProvider()


def _tokens(text: str) -> list[str]:
    clean = "".join(ch.lower() if ch.isalnum() else " " for ch in str(text or ""))
    return [part for part in clean.split() if len(part) > 2]


__all__ = ["BaseEmbeddingProvider", "EmbeddingProviderStatus", "HashingEmbeddingProvider", "get_embedding_provider"]
