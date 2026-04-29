"""Helper to initialize default embedding models."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import EmbeddingModel
from app.repositories.embedding_repository import EmbeddingModelRepository


async def initialize_default_embedding_models(session: AsyncSession) -> None:
    """Initialize default embedding models in database."""
    repo = EmbeddingModelRepository(session)

    # Define default models
    default_models = [
        {
            "name": "text-embedding-3-small",
            "provider": "openai",
            "model_identifier": "text-embedding-3-small",
            "vector_dimension": 512,
            "context_length": 8191,
            "max_batch_size": 2048,
            "cost_per_1k_tokens": 0.02 / 1000,  # $0.02 per 1M tokens
        },
        {
            "name": "text-embedding-3-large",
            "provider": "openai",
            "model_identifier": "text-embedding-3-large",
            "vector_dimension": 3072,
            "context_length": 8191,
            "max_batch_size": 2048,
            "cost_per_1k_tokens": 0.13 / 1000,  # $0.13 per 1M tokens
        },
        {
            "name": "all-MiniLM-L6-v2",
            "provider": "local",
            "model_identifier": "sentence-transformers/all-MiniLM-L6-v2",
            "vector_dimension": 384,
            "context_length": 256,
            "max_batch_size": 128,
            "cost_per_1k_tokens": None,
        },
        {
            "name": "all-mpnet-base-v2",
            "provider": "local",
            "model_identifier": "sentence-transformers/all-mpnet-base-v2",
            "vector_dimension": 768,
            "context_length": 384,
            "max_batch_size": 128,
            "cost_per_1k_tokens": None,
        },
    ]

    for model_config in default_models:
        existing = await repo.get_by_name(model_config["name"])
        if not existing:
            model = EmbeddingModel(
                id=uuid4(),
                **model_config,
            )
            await repo.create(model)

    await session.commit()
