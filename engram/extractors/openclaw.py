"""Extract conversations from OpenClaw (~/.openclaw/agents/*/sessions/*.jsonl)."""
import json
from pathlib import Path
from typing import Iterator
from .base import BaseExtractor

OPENCLAW_DIR = Path.home() / ".openclaw" / "agents"

class OpenClawExtractor(BaseExtractor):
    name = "openclaw"
    
    def is_available(self) -> bool:
        return OPENCLAW_DIR.exists() and any(OPENCLAW_DIR.glob("*/sessions/*.jsonl"))
    
    def extract_sessions(self) -> Iterator[dict]:
        if not self.is_available():
            return
        
        for jsonl_file in sorted(OPENCLAW_DIR.glob("*/sessions/*.jsonl"), 
                                  key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                messages = []
                session_meta = {}
                
                with open(jsonl_file, "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except:
                            continue
                    
                    entry_type = entry.get("type", "")
                    
                    if entry_type == "session":
                        session_meta = entry
                    
                    elif entry_type == "message":
                        msg = entry.get("message", {})
                        role = msg.get("role", "")
                        if role not in ("user", "assistant"):
                            continue
                        
                        content = msg.get("content", "")
                        if isinstance(content, list):
                            text_parts = []
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                            content = "\n".join(text_parts)
                        
                        if not content or not str(content).strip():
                            continue
                        
                        messages.append({
                            "role": role,
                            "content": str(content)[:5000],
                            "timestamp": entry.get("timestamp", ""),
                        })
                
                if not messages:
                    continue
                
                # Filter: skip heartbeat/cron sessions (too much noise)
                first_user = next((m["content"] for m in messages if m["role"] == "user"), "")
                if first_user.startswith("[cron:") or first_user.startswith("[heartbeat"):
                    continue
                
                session_id = self.make_session_id("openclaw", str(jsonl_file))
                
                first_asst = next((m["content"] for m in messages if m["role"] == "assistant"), "")
                
                yield {
                    "id": session_id,
                    "source_tool": "openclaw",
                    "source_path": str(jsonl_file),
                    "project": session_meta.get("cwd", ""),
                    "title": first_user[:100] if first_user else jsonl_file.stem,
                    "summary": first_asst[:200] if first_asst else "",
                    "created_at": session_meta.get("timestamp", ""),
                    "messages": messages,
                    "tags": [],
                }
            except Exception:
                continue
