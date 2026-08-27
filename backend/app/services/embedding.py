import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional
import httpx

from app.core.config import settings


class EmbeddingError(Exception):
    """Base exception for embedding generation failures."""
    pass


class EmbeddingService(ABC):
    """Abstract Base Class defining the embedding provider interface."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Returns vector dimensionality (e.g. 768 for nomic-embed-text)."""
        pass

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generates embedding vector for a single text string."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a list of text strings."""
        pass


class OllamaEmbeddingProvider(EmbeddingService):
    """Ollama Local Implementation of EmbeddingService using nomic-embed-text."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        expected_dims: int = 768,
    ):
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.model = model or settings.EMBEDDING_MODEL
        self._dimensions = expected_dims

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_text(self, text: str) -> List[float]:
        if not text.strip():
            raise EmbeddingError("Cannot embed empty text.")

        payload = {
            "model": self.model,
            "prompt": text,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.base_url}/api/embeddings", json=payload)
                
            if response.status_code != 200:
                raise EmbeddingError(
                    f"Ollama embedding API error ({response.status_code}): {response.text}"
                )

            data = response.json()
            embedding = data.get("embedding", [])
            
            if not embedding:
                raise EmbeddingError("Ollama API returned empty embedding vector.")

            return embedding

        except httpx.RequestError as e:
            raise EmbeddingError(f"Failed to connect to Ollama at {self.base_url}: {str(e)}")

    async def embed_batch(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """Embeds a batch of texts in chunks to manage memory and concurrency cleanly."""
        if not texts:
            return []

        embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            # Execute embedding tasks sequentially or in small gather
            batch_tasks = [self.embed_text(t) for t in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            embeddings.extend(batch_results)

        return embeddings


def get_embedding_service() -> EmbeddingService:
    """Factory function returning the configured embedding service provider."""
    if settings.LLM_PROVIDER == "ollama":
        return OllamaEmbeddingProvider(
            base_url=settings.LLM_BASE_URL,
            model=settings.EMBEDDING_MODEL,
        )
    else:
        raise NotImplementedError(f"Embedding provider '{settings.LLM_PROVIDER}' is not implemented.")
