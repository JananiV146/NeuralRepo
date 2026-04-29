"""Qdrant vector database integration."""

import os
from typing import Any
from uuid import UUID

try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    AsyncQdrantClient = None  # type: ignore
    Distance = None
    PointStruct = None
    VectorParams = None


class QdrantVectorDB:
    """Qdrant vector database client for storing and retrieving code embeddings."""

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """
        Initialize Qdrant client.

        Args:
            url: Qdrant server URL (default from QDRANT_URL env var or localhost)
            api_key: API key for authentication (optional)
        """
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.client = AsyncQdrantClient(url=self.url, api_key=self.api_key)

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
    ) -> None:
        """
        Create a collection for storing embeddings.

        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors
        """
        try:
            # Check if collection exists
            collections = await self.client.get_collections()
            if any(c.name == collection_name for c in collections.collections):
                return  # Collection already exists

            # Create collection
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        except Exception as e:
            raise Exception(f"Failed to create collection {collection_name}: {e}") from e

    async def store_embedding(
        self,
        collection_name: str,
        chunk_id: UUID,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Store a single embedding.

        Args:
            collection_name: Collection name
            chunk_id: ID of the chunk (used as point ID)
            embedding: Embedding vector
            metadata: Metadata to associate with the embedding
        """
        metadata = metadata or {}

        point = PointStruct(
            id=int(chunk_id.int % (2**63)),  # Convert UUID to unsigned 64-bit int
            vector=embedding,
            payload={
                "chunk_id": str(chunk_id),
                **metadata,
            },
        )

        await self.client.upsert(
            collection_name=collection_name,
            points=[point],
        )

    async def store_embeddings_batch(
        self,
        collection_name: str,
        embeddings_data: list[tuple[UUID, list[float], dict[str, Any]]],
    ) -> None:
        """
        Store multiple embeddings.

        Args:
            collection_name: Collection name
            embeddings_data: List of (chunk_id, embedding, metadata) tuples
        """
        if not embeddings_data:
            return

        points = []
        for chunk_id, embedding, metadata in embeddings_data:
            metadata = metadata or {}
            point = PointStruct(
                id=int(chunk_id.int % (2**63)),
                vector=embedding,
                payload={
                    "chunk_id": str(chunk_id),
                    **metadata,
                },
            )
            points.append(point)

        await self.client.upsert(
            collection_name=collection_name,
            points=points,
        )

    async def search_similar(
        self,
        collection_name: str,
        embedding: list[float],
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar embeddings.

        Args:
            collection_name: Collection name
            embedding: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of search results with scores and metadata
        """
        results = await self.client.search(
            collection_name=collection_name,
            query_vector=embedding,
            limit=limit,
            score_threshold=score_threshold,
        )

        return [
            {
                "chunk_id": result.payload.get("chunk_id"),
                "score": result.score,
                "metadata": {k: v for k, v in result.payload.items() if k != "chunk_id"},
            }
            for result in results
        ]

    async def delete_embeddings(
        self,
        collection_name: str,
        chunk_ids: list[UUID],
    ) -> None:
        """
        Delete embeddings for specified chunks.

        Args:
            collection_name: Collection name
            chunk_ids: List of chunk IDs to delete
        """
        if not chunk_ids:
            return

        point_ids = [int(cid.int % (2**63)) for cid in chunk_ids]
        await self.client.delete(
            collection_name=collection_name,
            points_selector=point_ids,
        )

    async def collection_info(self, collection_name: str) -> dict[str, Any]:
        """Get collection statistics."""
        info = await self.client.get_collection(collection_name)
        return {
            "name": collection_name,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "config": {
                "vector_size": info.config.params.vectors.size,
                "distance": str(info.config.params.vectors.distance),
            },
        }

    async def delete_collection(self, collection_name: str) -> None:
        """Delete a collection."""
        await self.client.delete_collection(collection_name)

    async def close(self) -> None:
        """Close the client."""
        await self.client.close()
