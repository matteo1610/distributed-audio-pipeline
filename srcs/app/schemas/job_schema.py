"""Pydantic schemas for API requests/responses."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    """Response model for uploaded job."""
    job_id: UUID
    object_key: str
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "object_key": "550e8400-e29b-41d4-a716-446655440000/example.wav",
                "message": "Job created successfully",
            }
        }
    )


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "DONE",
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:05:00Z",
                "error_message": None,
            }
        }
    )


class AudioFeaturesResponse(BaseModel):
    """Response model for extracted audio features."""

    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    audio_format: Optional[str] = None


class ProcessedAudioResponse(BaseModel):
    """Response model for processed audio details."""

    job_id: UUID
    status: str
    filename: str
    output_path: str
    features: AudioFeaturesResponse
    error_message: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "DONE",
                "filename": "example.wav",
                "output_path": "processed/550e8400-e29b-41d4-a716-446655440000/example.wav",
                "features": {
                    "duration_seconds": 10.5,
                    "sample_rate": 44100,
                    "channels": 2,
                    "audio_format": "wav",
                },
                "error_message": None,
            }
        }
    )
