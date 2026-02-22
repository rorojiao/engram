from abc import ABC, abstractmethod
from pathlib import Path


class BaseBackend(ABC):
    name: str = "base"

    @abstractmethod
    def upload(self, local_path: Path, remote_name: str = None) -> bool:
        pass

    @abstractmethod
    def download(self, local_path: Path, remote_name: str = None) -> bool:
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        pass
