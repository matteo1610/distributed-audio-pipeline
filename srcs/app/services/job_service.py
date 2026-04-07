"""Job service for business logic."""
from uuid import UUID

from app.infrastructure.broker import RabbitMQBroker
from app.infrastructure.storage import MinIOStorage
from app.models.audio_job import JobStatus
from app.repositories.job_repository import JobRepository


class JobService:
    """Service for job management business logic."""

    def __init__(
        self,
        job_repo: JobRepository,
        broker: RabbitMQBroker,
        storage: MinIOStorage,
    ):
        """Initialize job service.
        
        Args:
            job_repo: Job repository for data access.
            broker: RabbitMQ broker for message publishing.
            storage: MinIO storage client.
        """
        self.job_repo = job_repo
        self.broker = broker
        self.storage = storage

    def create_and_publish_job(self, owner_id: UUID, object_key: str) -> UUID:
        """Create a job and publish it to the processing queue.
        
        Args:
            owner_id: Owner user identifier.
            object_key: Object key in storage.

        Returns:
            Database-generated job identifier.
        """
        # Create job in database
        job = self.job_repo.create_job(owner_id, object_key)

        # Publish to message queue for processing
        self.broker.publish_message({
            "job_id": str(job.id),
            "object_key": object_key,
        })
        return job.id

    def get_job_details(self, job_id: UUID):
        """Get full job details including status and results.
        
        Args:
            job_id: Job identifier.
            
        Returns:
            Dictionary with job and result data, or None if not found.
        """
        job = self.job_repo.get_job(job_id)
        if not job:
            return None

        result = self.job_repo.get_processing_result(job_id)

        return {
            "job": job,
            "result": result,
        }

    def mark_job_processing(self, job_id: UUID) -> None:
        """Mark a job as processing.
        
        Args:
            job_id: Job identifier.
        """
        self.job_repo.update_job_status(job_id, JobStatus.PROCESSING)

    def mark_job_pending(self, job_id: UUID) -> None:
        """Mark a job as pending.

        Args:
            job_id: Job identifier.
        """
        self.job_repo.update_job_status(job_id, JobStatus.PENDING)

    def mark_job_completed(self, job_id: UUID) -> None:
        """Mark a job as completed successfully.
        
        Args:
            job_id: Job identifier.
        """
        self.job_repo.update_job_status(job_id, JobStatus.DONE)

    def mark_job_failed(self, job_id: UUID, error_message: str) -> None:
        """Mark a job as failed.
        
        Args:
            job_id: Job identifier.
            error_message: Error description.
        """
        self.job_repo.update_job_status(job_id, JobStatus.FAILED, error_message)

    def save_job_results(
        self,
        job_id: UUID,
        duration_seconds: float | None,
        sample_rate: int | None,
        channels: int | None,
        filename: str | None = None,
        output_path: str | None = None,
        audio_format: str | None = None,
    ) -> None:
        """Save job processing results.
        
        Args:
            job_id: Job identifier.
            duration_seconds: Audio duration.
            sample_rate: Sample rate.
            channels: Number of channels.
            filename: Optional original filename.
            output_path: Optional output storage path.
            audio_format: Optional audio format.
        """
        self.job_repo.save_processing_result(
            job_id,
            duration_seconds,
            sample_rate,
            channels,
            filename,
            output_path,
            audio_format,
        )
