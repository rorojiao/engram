"""Base extractor interface."""
from abc import ABC, abstractmethod
from typing import Iterator

class BaseExtractor(ABC):
    name: str = ""
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def extract_sessions(self) -> Iterator[dict]:
        pass
    
    def make_session_id(self, tool: str, unique: str) -> str:
        import hashlib
        return f"{tool}_{hashlib.md5(unique.encode()).hexdigest()[:12]}"
