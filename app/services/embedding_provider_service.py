"""Embedding providers for different embedding models."""

import os
from abc import ABC, abstractmethod
from typing import Any

import httpx


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (each is a list of floats)
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension for this provider."""
        pass

    @property
    @abstractmethod
    def max_batch_size(self) -> int:
        """Maximum batch size for this provider."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider using their API."""

    def __init__(self, api_key: str | None = None, model: str = "text-embedding-3-small") -> None:
        super().__init__()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.model = model
        self.base_url = "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI API."""
        if not texts:
            return []

        try:
            response = await self.client.post(
                "/embeddings",
                json={
                    "input": texts,
                    "model": self.model,
                    "encoding_format": "float",
                },
            )

            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"OpenAI API error ({response.status_code}): {error_detail}")

            data = response.json()
            embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
            return embeddings

        except httpx.RequestError as e:
            raise Exception(f"OpenAI API request failed: {e}") from e

    @property
    def dimension(self) -> int:
        """Vector dimension for OpenAI models."""
        # text-embedding-3-small: 512
        # text-embedding-3-large: 3072
        if self.model == "text-embedding-3-small":
            return 512
        elif self.model == "text-embedding-3-large":
            return 3072
        elif self.model == "text-embedding-ada-002":
            return 1536
        return 1536  # Default

    @property
    def max_batch_size(self) -> int:
        """Max batch size for OpenAI embeddings."""
        return 2048

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using Sentence Transformers (for testing/development)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        super().__init__()
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        """Lazy load model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using sentence-transformers."""
        if not texts:
            return []

        model = self._get_model()
        embeddings = model.encode(texts, convert_to_tensor=False)
        return [emb.tolist() for emb in embeddings]

    @property
    def dimension(self) -> int:
        """Vector dimension."""
        # all-MiniLM-L6-v2: 384
        # all-mpnet-base-v2: 768
        if "MiniLM" in self.model_name:
            return 384
        elif "mpnet" in self.model_name:
            return 768
        return 384  # Default

    @property
    def max_batch_size(self) -> int:
        """Max batch size."""
        return 128


class EmbeddingProviderFactory:
    """Factory for creating embedding providers."""

    _providers = {
        "openai": OpenAIEmbeddingProvider,
        "local": LocalEmbeddingProvider,
    }

    @classmethod
    def create(
        self,
        provider: str,
        config: dict[str, Any] | None = None,
    ) -> EmbeddingProvider:
        """Create an embedding provider."""
        config = config or {}

        if provider == "openai":
            api_key = config.get("api_key")
            model = config.get("model", "text-embedding-3-small")
            return OpenAIEmbeddingProvider(api_key=api_key, model=model)

        elif provider == "local":
            model_name = config.get("model_name", "all-MiniLM-L6-v2")
            return LocalEmbeddingProvider(model_name=model_name)

        raise ValueError(f"Unknown embedding provider: {provider}")

    @classmethod
    def list_providers(cls) -> list[str]:
        """List available providers."""
        return list(cls._providers.keys())
