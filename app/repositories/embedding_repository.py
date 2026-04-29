import uuid
from typing import Any

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embedding import EmbeddingJob, EmbeddingModel


class EmbeddingModelRepository:
    """Repository for embedding model configurations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, model: EmbeddingModel) -> EmbeddingModel:
        """Create a new embedding model configuration."""
        self.session.add(model)
        await self.session.flush()
        return model

    async def get_by_id(self, model_id: uuid.UUID) -> EmbeddingModel | None:
        """Get model by ID."""
        stmt = select(EmbeddingModel).where(EmbeddingModel.id == model_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_name(self, name: str) -> EmbeddingModel | None:
        """Get model by name."""
        stmt = select(EmbeddingModel).where(EmbeddingModel.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_active(self) -> list[EmbeddingModel]:
        """List all active embedding models."""
        stmt = select(EmbeddingModel).where(EmbeddingModel.is_active).order_by(EmbeddingModel.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_provider(self, provider: str) -> list[EmbeddingModel]:
        """List models by provider."""
        stmt = (
            select(EmbeddingModel)
            .where(and_(EmbeddingModel.provider == provider, EmbeddingModel.is_active))
            .order_by(EmbeddingModel.name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, model: EmbeddingModel) -> EmbeddingModel:
        """Update an embedding model."""
        await self.session.merge(model)
        await self.session.flush()
        return model

    async def deactivate(self, model_id: uuid.UUID) -> EmbeddingModel | None:
        """Deactivate a model."""
        model = await self.get_by_id(model_id)
        if model:
            model.is_active = False
            await self.session.flush()
        return model


class EmbeddingJobRepository:
    """Repository for embedding job tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, job: EmbeddingJob) -> EmbeddingJob:
        """Create a new embedding job."""
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> EmbeddingJob | None:
        """Get job by ID."""
        stmt = select(EmbeddingJob).where(EmbeddingJob.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_latest_by_repository(self, repository_id: uuid.UUID) -> EmbeddingJob | None:
        """Get the latest embedding job for a repository."""
        stmt = (
            select(EmbeddingJob)
            .where(EmbeddingJob.repository_id == repository_id)
            .order_by(EmbeddingJob.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_repository(self, repository_id: uuid.UUID) -> list[EmbeddingJob]:
        """List all embedding jobs for a repository."""
        stmt = (
            select(EmbeddingJob)
            .where(EmbeddingJob.repository_id == repository_id)
            .order_by(EmbeddingJob.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_status(self, status: str) -> list[EmbeddingJob]:
        """List jobs by status."""
        stmt = select(EmbeddingJob).where(EmbeddingJob.status == status)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, job: EmbeddingJob) -> EmbeddingJob:
        """Update an embedding job."""
        await self.session.merge(job)
        await self.session.flush()
        return job

    async def update_progress(
        self,
        job_id: uuid.UUID,
        embedded_count: int,
        failed_count: int,
    ) -> EmbeddingJob | None:
        """Update embedding progress."""
        job = await self.get_by_id(job_id)
        if job:
            job.embedded_chunks = embedded_count
            job.failed_chunks = failed_count
            await self.session.flush()
        return job

    async def mark_completed(
        self,
        job_id: uuid.UUID,
        error_message: str | None = None,
    ) -> EmbeddingJob | None:
        """Mark a job as completed."""
        from datetime import datetime

        job = await self.get_by_id(job_id)
        if job:
            job.status = "failed" if error_message else "completed"
            job.error_message = error_message
            job.completed_at = datetime.utcnow()
            await self.session.flush()
        return job

    async def delete_by_repository(self, repository_id: uuid.UUID) -> int:
        """Delete all jobs for a repository."""
        stmt = delete(EmbeddingJob).where(EmbeddingJob.repository_id == repository_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
