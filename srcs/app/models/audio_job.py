"""Audio job domain model."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class JobStatus(Enum):
    """Job status enumeration."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass
class AudioJob:
    """Represents an audio processing job."""

    id: UUID
    object_key: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    def is_processing(self) -> bool:
        """Check if job is currently processing."""
        return self.status == JobStatus.PROCESSING

    def is_completed(self) -> bool:
        """Check if job completed successfully."""
        return self.status == JobStatus.DONE

    def is_failed(self) -> bool:
        """Check if job failed."""
        return self.status == JobStatus.FAILED


@dataclass
class AudioFeatures:
    """Represents extracted audio features."""

    duration_seconds: Optional[float]
    sample_rate: Optional[int]
    channels: Optional[int]
    audio_format: Optional[str] = None

    def is_valid(self) -> bool:
        """Validate if all required features were extracted."""
        return all([
            self.duration_seconds is not None,
            self.sample_rate is not None,
            self.channels is not None,
        ])


@dataclass
class ProcessedAudio:
    """Represents processed audio output and metadata."""

    job_id: UUID
    filename: str
    output_path: str
    features: AudioFeatures

    def is_valid(self) -> bool:
        """Validate if processed audio has complete feature extraction."""
        return self.features.is_valid()
