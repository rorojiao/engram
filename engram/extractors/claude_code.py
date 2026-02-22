"""Extract conversations from Claude Code (~/.claude/projects/)."""
import json
from pathlib import Path
from typing import Iterator
from .base import BaseExtractor

CLAUDE_DIR = Path.home() / ".claude" / "projects"

class ClaudeCodeExtractor(BaseExtractor):
    name = "claude_code"
    
    def is_available(self) -> bool:
        return CLAUDE_DIR.exists()
    
    def extract_sessions(self) -> Iterator[dict]:
        if not self.is_available():
            return
        
        for project_dir in CLAUDE_DIR.iterdir():
            if not project_dir.is_dir():
                continue
            
            project_path = ""
            meta_file = project_dir / "project.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                    project_path = meta.get("path", "")
                except:
                    pass
            
            for jsonl_file in project_dir.glob("*.jsonl"):
                try:
                    messages = []
                    created_at = None
                    
                    for line in jsonl_file.read_text(encoding="utf-8", errors="replace").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except:
                            continue
                        
                        role = entry.get("role", "")
                        if role not in ("user", "assistant"):
                            continue
                        
                        content = entry.get("content", "")
                        if isinstance(content, list):
                            text_parts = []
                            for block in content:
                                if isinstance(block, dict):
                                    if block.get("type") == "text":
                                        text_parts.append(block.get("text", ""))
                                    elif block.get("type") == "tool_use":
                                        text_parts.append(f"[Tool: {block.get('name','')}]")
                            content = "\n".join(text_parts)
                        
                        ts = entry.get("timestamp", "")
                        if not created_at and ts:
                            created_at = ts
                        
                        messages.append({
                            "role": role,
                            "content": content[:4000],
                            "timestamp": ts,
                        })
                    
                    if not messages:
                        continue
                    
                    first_user = next((m["content"] for m in messages if m["role"] == "user"), "")
                    title = first_user[:80] if first_user else jsonl_file.stem
                    first_asst = next((m["content"] for m in messages if m["role"] == "assistant"), "")
                    summary = first_asst[:200] if first_asst else ""
                    session_id = self.make_session_id("claude_code", str(jsonl_file))
                    
                    yield {
                        "id": session_id,
                        "source_tool": "claude_code",
                        "source_path": str(jsonl_file),
                        "project": project_path or str(project_dir.name),
                        "title": title,
                        "summary": summary,
                        "created_at": created_at,
                        "messages": messages,
                        "tags": [],
                    }
                except Exception:
                    continue
