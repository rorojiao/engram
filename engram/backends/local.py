from pathlib import Path
from .base import BaseBackend


class LocalBackend(BaseBackend):
    name = "local"

    def upload(self, local_path: Path, remote_name: str = None) -> bool:
        return True

    def download(self, local_path: Path, remote_name: str = None) -> bool:
        return True

    def test_connection(self) -> bool:
        return True
