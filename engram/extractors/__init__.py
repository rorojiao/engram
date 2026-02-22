from .claude_code import ClaudeCodeExtractor
from .openclaw import OpenClawExtractor
from .opencode import OpenCodeExtractor
from .cursor import CursorExtractor

ALL_EXTRACTORS = [
    ClaudeCodeExtractor(),
    OpenClawExtractor(),
    OpenCodeExtractor(),
    CursorExtractor(),
]

def get_available_extractors():
    return [e for e in ALL_EXTRACTORS if e.is_available()]
