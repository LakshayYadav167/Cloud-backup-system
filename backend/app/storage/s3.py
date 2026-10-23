"""S3-compatible object storage provider adapter.

Connects to any S3-compatible service (e.g. self-hosted MinIO Community,
LocalStack, Ceph, SeaweedFS) using boto3.
"""

from io import BytesIO
from typing import BinaryIO, Dict, Optional
import hashlib
import os

from app.core.config import settings
from app.storage.base import StorageItemInfo, StorageProvider, StorageStatsInfo

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError, EndpointConnectionError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    ClientError = Exception
    EndpointConnectionError = Exception


class S3CompatibleStorage(StorageProvider):
    """S3-compatible object storage driver."""

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
        use_ssl: Optional[bool] = None,
        auto_create_bucket: bool = True,
    ):
        if not BOTO3_AVAILABLE:
            raise RuntimeError(
                "boto3 is required for S3CompatibleStorage. "
                "Install it via 'pip install boto3'."
            )

        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.access_key = access_key or settings.S3_ACCESS_KEY
        self.secret_key = secret_key or settings.S3_SECRET_KEY
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.region = region or settings.S3_REGION
        self.use_ssl = use_ssl if use_ssl is not None else settings.S3_USE_SSL

        # Configure boto3 client with path-style addressing and fast timeouts
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            use_ssl=self.use_ssl,
            config=Config(
                s3={"addressing_style": "path"},
                connect_timeout=1,
                read_timeout=3,
                retries={"max_attempts": 1},
            ),
        )
        if auto_create_bucket:
            self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create bucket if it does not already exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchBucket"):
                try:
                    if self.region == "us-east-1":
                        self.client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": self.region},
                        )
                except Exception:
                    pass
        except Exception:
            # Service may not be reachable during initialization in testing
            pass

    def _sanitize_key(self, object_key: str) -> str:
        if not object_key or not object_key.strip():
            raise ValueError("Object key cannot be empty")
        return object_key.replace("\x00", "").lstrip("/")

    def save_file(
        self,
        object_key: str,
        content: BinaryIO,
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageItemInfo:
        key = self._sanitize_key(object_key)
        hasher = hashlib.sha256()

        buffer = BytesIO()
        total_bytes = 0
        while True:
            chunk = content.read(64 * 1024)
            if not chunk:
                break
            buffer.write(chunk)
            hasher.update(chunk)
            total_bytes += len(chunk)

        buffer.seek(0)
        checksum = hasher.hexdigest()

        extra_args: Dict[str, str] = {}
        if metadata:
            extra_args["Metadata"] = metadata

        self.client.upload_fileobj(
            Fileobj=buffer,
            Bucket=self.bucket_name,
            Key=key,
            ExtraArgs=extra_args if extra_args else None,
        )

        return StorageItemInfo(
            stored_path_or_key=key,
            object_key=key,
            size_bytes=total_bytes,
            sha256_checksum=checksum,
        )

    def get_file(self, object_key: str) -> BinaryIO:
        key = self._sanitize_key(object_key)
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            content_bytes = response["Body"].read()
            return BytesIO(content_bytes)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                raise FileNotFoundError(f"Object not found in S3 bucket: '{key}'")
            raise

    def delete_file(self, object_key: str) -> bool:
        key = self._sanitize_key(object_key)
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def file_exists(self, object_key: str) -> bool:
        key = self._sanitize_key(object_key)
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def get_storage_stats(self) -> StorageStatsInfo:
        total_files = 0
        total_bytes = 0

        try:
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket_name):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        total_files += 1
                        total_bytes += obj.get("Size", 0)
        except Exception:
            pass

        return StorageStatsInfo(
            provider_name="s3",
            total_files=total_files,
            total_bytes=total_bytes,
            base_location=f"s3://{self.bucket_name}",
        )
