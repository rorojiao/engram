from pathlib import Path
from .base import BaseBackend


class WebDAVBackend(BaseBackend):
    name = "webdav"

    def __init__(self, url: str, username: str, password: str):
        from webdav4.client import Client
        self.client = Client(url, auth=(username, password))
        self.remote_path = "/Engram/engram.db"

    def upload(self, local_path: Path) -> bool:
        try:
            self.client.makedirs("/Engram", exist_ok=True)
            self.client.upload_file(str(local_path), self.remote_path, overwrite=True)
            return True
        except Exception as e:
            import logging; logging.getLogger("engram").warning(f"WebDAV upload failed: {e}")
            return False

    def download(self, local_path: Path) -> bool:
        try:
            self.client.download_file(self.remote_path, str(local_path))
            return True
        except Exception as e:
            import logging; logging.getLogger("engram").warning(f"WebDAV download failed: {e}")
            return False

    def test_connection(self) -> bool:
        try:
            self.client.ls("/")
            return True
        except Exception:
            return False
