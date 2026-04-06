"""Prometheus metrics collection."""
from prometheus_client import Counter, Histogram


class MetricsCollector:
    """Collects application metrics using Prometheus."""

    def __init__(self):
        """Initialize metrics collector."""
        # Upload metrics
        self.uploads_total = Counter(
            "uploads_total",
            "Total uploaded audio files",
        )
        self.upload_seconds = Histogram(
            "upload_seconds",
            "Upload request latency",
        )

        # Job metrics
        self.jobs_published_total = Counter(
            "jobs_published_total",
            "Total jobs published to queue",
        )
        self.jobs_completed_total = Counter(
            "jobs_completed_total",
            "Total completed jobs",
        )
        self.jobs_failed_total = Counter(
            "jobs_failed_total",
            "Total failed jobs",
        )
        self.job_processing_seconds = Histogram(
            "job_processing_seconds",
            "Time taken to process a job",
        )

    def record_upload(self) -> None:
        """Record an upload event."""
        self.uploads_total.inc()

    def record_upload_latency(self, seconds: float) -> None:
        """Record upload latency.
        
        Args:
            seconds: Time taken for upload.
        """
        self.upload_seconds.observe(seconds)

    def record_job_published(self) -> None:
        """Record a job published to queue."""
        self.jobs_published_total.inc()

    def record_job_completed(self) -> None:
        """Record a completed job."""
        self.jobs_completed_total.inc()

    def record_job_failed(self) -> None:
        """Record a failed job."""
        self.jobs_failed_total.inc()

    def record_job_processing_time(self, seconds: float) -> None:
        """Record job processing time.
        
        Args:
            seconds: Time taken to process job.
        """
        self.job_processing_seconds.observe(seconds)

    def get_all_metrics(self) -> str:
        """Get all metrics in Prometheus format.
        
        Returns:
            Prometheus metrics as string.
        """
        from prometheus_client import generate_latest
        return generate_latest().decode("utf-8")
