"""Job repository for data access."""
from pathlib import PurePosixPath
from datetime import datetime, timezone
from uuid import UUID

from app.infrastructure.database import DatabaseConnection
from app.models.audio_job import AudioFeatures, AudioJob, JobStatus, ProcessedAudio


class JobRepository:
    """Repository for job data access."""

    def __init__(self, db: DatabaseConnection):
        """Initialize job repository.
        
        Args:
            db: Database connection manager.
        """
        self.db = db

    def create_job(self, owner_id: UUID, object_key: str) -> AudioJob:
        """Create a new job.
        
        Args:
            owner_id: Owner user identifier.
            object_key: Object key in storage.
            
        Returns:
            Created AudioJob instance.
        """
        row = self.db.fetch_one(
            """
            INSERT INTO jobs (owner_id, object_key, status)
            VALUES (%s, %s, %s)
            RETURNING id, owner_id, object_key, status, created_at, updated_at, error_message
            """,
            (str(owner_id), object_key, JobStatus.PENDING.value),
        )

        if not row:
            raise ValueError("Failed to create job")

        return AudioJob(
            id=UUID(str(row[0])),
            owner_id=UUID(str(row[1])),
            object_key=row[2],
            status=JobStatus(row[3]),
            created_at=row[4],
            updated_at=row[5],
            error_message=row[6],
        )

    def get_job(self, job_id: UUID) -> AudioJob | None:
        """Get job by ID.
        
        Args:
            job_id: Job identifier.
            
        Returns:
            AudioJob or None if not found.
        """
        row = self.db.fetch_one(
            """
            SELECT id, owner_id, object_key, status, created_at, updated_at, error_message
            FROM jobs
            WHERE id = %s
            """,
            (str(job_id),),
        )
        if not row:
            return None

        return AudioJob(
            id=UUID(str(row[0])),
            owner_id=UUID(str(row[1])),
            object_key=row[2],
            status=JobStatus(row[3]),
            created_at=row[4],
            updated_at=row[5],
            error_message=row[6],
        )

    def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        error_message: str | None = None,
    ) -> None:
        """Update job status.
        
        Args:
            job_id: Job identifier.
            status: New job status.
            error_message: Error message if failed.
        """
        self.db.execute_query(
            """
            UPDATE jobs
            SET status = %s, error_message = %s, updated_at = %s
            WHERE id = %s
            """,
            (status.value, error_message, datetime.now(timezone.utc), str(job_id)),
        )

    def save_processing_result(
        self,
        job_id: UUID,
        duration_seconds: float | None,
        sample_rate: int | None,
        channels: int | None,
        filename: str | None = None,
        output_path: str | None = None,
        audio_format: str | None = None,
    ) -> ProcessedAudio:
        """Save audio processing results.
        
        Args:
            job_id: Job identifier.
            duration_seconds: Audio duration in seconds.
            sample_rate: Sample rate in Hz.
            channels: Number of audio channels.
            filename: Optional original filename.
            output_path: Optional output storage path.
            audio_format: Optional audio format.
            
        Returns:
            ProcessedAudio instance.
        """
        job = self.get_job(job_id)
        object_key = job.object_key if job else ""
        default_filename, default_output_path, default_format = self._derive_audio_metadata(object_key)
        persisted_filename = filename or default_filename
        persisted_output_path = output_path or default_output_path
        persisted_audio_format = audio_format or default_format

        self.db.execute_query(
            """
            INSERT INTO processing_results (
                job_id,
                filename,
                output_path,
                duration_seconds,
                sample_rate,
                channels,
                audio_format
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (job_id) DO UPDATE
            SET filename = EXCLUDED.filename,
                output_path = EXCLUDED.output_path,
                duration_seconds = EXCLUDED.duration_seconds,
                sample_rate = EXCLUDED.sample_rate,
                channels = EXCLUDED.channels,
                audio_format = EXCLUDED.audio_format
            """,
            (
                str(job_id),
                persisted_filename,
                persisted_output_path,
                duration_seconds,
                sample_rate,
                channels,
                persisted_audio_format,
            ),
        )

        return self._build_processed_audio(
            job_id=job_id,
            duration_seconds=duration_seconds,
            sample_rate=sample_rate,
            channels=channels,
            object_key=object_key,
            filename=persisted_filename,
            output_path=persisted_output_path,
            audio_format=persisted_audio_format,
        )

    def get_processing_result(self, job_id: UUID) -> ProcessedAudio | None:
        """Get processing result for a job.
        
        Args:
            job_id: Job identifier.
            
        Returns:
            ProcessedAudio or None if not found.
        """
        row = self.db.fetch_one(
            """
            SELECT
                pr.job_id,
                pr.filename,
                pr.output_path,
                pr.duration_seconds,
                pr.sample_rate,
                pr.channels,
                pr.audio_format,
                j.object_key
            FROM processing_results pr
            JOIN jobs j ON j.id = pr.job_id
            WHERE pr.job_id = %s
            """,
            (str(job_id),),
        )
        if not row:
            return None

        return self._build_processed_audio(
            job_id=UUID(row[0]),
            duration_seconds=row[3],
            sample_rate=row[4],
            channels=row[5],
            object_key=row[7],
            filename=row[1],
            output_path=row[2],
            audio_format=row[6],
        )

    @staticmethod
    def _derive_audio_metadata(object_key: str) -> tuple[str, str, str | None]:
        """Derive filename, output path, and format from storage object key."""
        filename = PurePosixPath(object_key).name
        output_path = f"processed/{object_key}"
        audio_format = PurePosixPath(filename).suffix.lower().lstrip(".") or None
        return filename, output_path, audio_format

    def _build_processed_audio(
        self,
        job_id: UUID,
        duration_seconds: float | None,
        sample_rate: int | None,
        channels: int | None,
        object_key: str,
        filename: str | None = None,
        output_path: str | None = None,
        audio_format: str | None = None,
    ) -> ProcessedAudio:
        """Build ProcessedAudio entity with sensible defaults."""
        default_filename, default_output_path, default_format = self._derive_audio_metadata(object_key)
        return ProcessedAudio(
            job_id=job_id,
            filename=filename or default_filename,
            output_path=output_path or default_output_path,
            features=AudioFeatures(
                duration_seconds=duration_seconds,
                sample_rate=sample_rate,
                channels=channels,
                audio_format=audio_format or default_format,
            ),
        )
