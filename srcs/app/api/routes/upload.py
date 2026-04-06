"""Upload and job status route handlers."""
import time
import uuid
from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth.dependencies import get_current_user
from app.infrastructure.broker import RabbitMQBroker
from app.infrastructure.database import DatabaseConnection
from app.infrastructure.metrics import MetricsCollector
from app.infrastructure.storage import MinIOStorage
from app.models.user import User, UserRole
from app.repositories.job_repository import JobRepository
from app.schemas.job_schema import AudioFeaturesResponse, JobResponse, JobStatusResponse, ProcessedAudioResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/api", tags=["jobs"])

# Dependency injection - these will be provided by FastAPI dependency system
# For now, we initialize them here for clarity
_db = DatabaseConnection()
_storage = MinIOStorage()
_broker = RabbitMQBroker()
_metrics = MetricsCollector()
_job_repo = JobRepository(_db)
_job_service = JobService(_job_repo, _broker, _storage)


def _can_access_job(current_user: User, job_owner_id) -> bool:
    return current_user.role == UserRole.ADMIN or current_user.id == job_owner_id


@router.post("/uploads", response_model=JobResponse)
def upload_audio(
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Upload an audio file for processing.
    
    Args:
        file: Audio file to upload.
        
    Returns:
        Job details with job_id.
        
    Raises:
        HTTPException: If file is empty or upload fails.
    """
    start = time.perf_counter()
    object_key = f"uploads/{uuid.uuid4()}-{file.filename}"

    # Read file data
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Upload to storage
    try:
        _storage.upload_bytes(object_key, data)
        _metrics.record_upload()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(exc)}",
        ) from exc

    # Create and publish job
    try:
        job_id = _job_service.create_and_publish_job(current_user.id, object_key)
        _metrics.record_job_published()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create job: {str(exc)}",
        ) from exc

    elapsed = time.perf_counter() - start
    _metrics.record_upload_latency(elapsed)

    return JobResponse(
        job_id=job_id,
        object_key=object_key,
        message="Job created successfully",
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get the status of a job.
    
    Args:
        job_id: Job identifier.
        
    Returns:
        Job status details.
        
    Raises:
        HTTPException: If job not found.
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = _job_repo.get_job(job_uuid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _can_access_job(current_user, job.owner_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this job")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        created_at=job.created_at,
        updated_at=job.updated_at,
        error_message=job.error_message,
    )


@router.get("/jobs/{job_id}/results", response_model=ProcessedAudioResponse)
def get_job_results(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get the results of a completed job.
    
    Args:
        job_id: Job identifier.
        
    Returns:
        Processing results.
        
    Raises:
        HTTPException: If job or results not found.
    """
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = _job_repo.get_job(job_uuid)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _can_access_job(current_user, job.owner_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this job")

    result = _job_repo.get_processing_result(job_uuid)
    fallback_filename = PurePosixPath(job.object_key).name
    fallback_output_path = f"processed/{job.object_key}"
    fallback_format = PurePosixPath(fallback_filename).suffix.lower().lstrip(".") or None

    return ProcessedAudioResponse(
        job_id=job.id,
        status=job.status.value,
        filename=result.filename if result else fallback_filename,
        output_path=result.output_path if result else fallback_output_path,
        features=AudioFeaturesResponse(
            duration_seconds=result.features.duration_seconds if result else None,
            sample_rate=result.features.sample_rate if result else None,
            channels=result.features.channels if result else None,
            audio_format=result.features.audio_format if result else fallback_format,
        ),
        error_message=job.error_message,
    )
