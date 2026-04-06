"""MinIO object storage management."""
import os

from minio import Minio
from minio.error import S3Error


class MinIOStorage:
    """Manages MinIO object storage operations."""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool = False,
    ):
        """Initialize MinIO storage client.
        
        Args:
            endpoint: MinIO endpoint. If None, reads from MINIO_ENDPOINT env var.
            access_key: MinIO access key. If None, reads from MINIO_ACCESS_KEY env var.
            secret_key: MinIO secret key. If None, reads from MINIO_SECRET_KEY env var.
            bucket: Default bucket name. If None, reads from MINIO_BUCKET env var.
            secure: Whether to use HTTPS.
        """
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "minio:9000")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minio")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minio123")
        self.bucket = bucket or os.getenv("MINIO_BUCKET", "raw-audio")
        self.secure = secure

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

    def ensure_bucket_exists(self) -> None:
        """Ensure the default bucket exists, create if not.
        
        Raises:
            S3Error: If bucket operations fail.
        """
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as exc:
            raise RuntimeError(f"Unable to prepare MinIO bucket '{self.bucket}': {exc}") from exc

    def upload_bytes(self, object_key: str, data: bytes, bucket: str | None = None) -> None:
        """Upload bytes to storage.
        
        Args:
            object_key: Object key/path.
            data: Bytes to upload.
            bucket: Bucket name. If None, uses default bucket.
            
        Raises:
            S3Error: If upload fails.
        """
        import io
        target_bucket = bucket or self.bucket
        self.client.put_object(
            bucket_name=target_bucket,
            object_name=object_key,
            data=io.BytesIO(data),
            length=len(data),
        )

    def download_bytes(self, object_key: str, bucket: str | None = None) -> bytes:
        """Download bytes from storage.
        
        Args:
            object_key: Object key/path.
            bucket: Bucket name. If None, uses default bucket.
            
        Returns:
            Downloaded bytes.
            
        Raises:
            S3Error: If download fails.
        """
        target_bucket = bucket or self.bucket
        obj = self.client.get_object(target_bucket, object_key)
        try:
            data = obj.read()
            return data
        finally:
            obj.close()
            obj.release_conn()

    def object_exists(self, object_key: str, bucket: str | None = None) -> bool:
        """Check if object exists.
        
        Args:
            object_key: Object key/path.
            bucket: Bucket name. If None, uses default bucket.
            
        Returns:
            True if object exists, False otherwise.
        """
        target_bucket = bucket or self.bucket
        try:
            self.client.stat_object(target_bucket, object_key)
            return True
        except S3Error:
            return False

    def is_healthy(self) -> bool:
        """Check storage health.
        
        Returns:
            True if storage is accessible, False otherwise.
        """
        try:
            self.client.list_buckets()
            return True
        except Exception:
            return False
