from pathlib import Path
from .base import BaseBackend


class S3Backend(BaseBackend):
    name = "s3"

    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket: str):
        import boto3
        self.bucket = bucket
        self.key = "engram.db"
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def upload(self, local_path: Path) -> bool:
        try:
            self.s3.upload_file(str(local_path), self.bucket, self.key)
            return True
        except Exception as e:
            import logging; logging.getLogger("engram").warning(f"S3 upload failed: {e}")
            return False

    def download(self, local_path: Path) -> bool:
        try:
            self.s3.download_file(self.bucket, self.key, str(local_path))
            return True
        except Exception as e:
            import logging; logging.getLogger("engram").warning(f"S3 download failed: {e}")
            return False

    def test_connection(self) -> bool:
        try:
            self.s3.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False
