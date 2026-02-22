"""Extract conversations from OpenCode (~/.opencode/ SQLite)."""
import sqlite3
import json
from pathlib import Path
from typing import Iterator
from .base import BaseExtractor

OPENCODE_DIRS = [
    Path.home() / ".opencode",
    Path.home() / ".config" / "opencode",
    Path.home() / "Library" / "Application Support" / "opencode",
]

class OpenCodeExtractor(BaseExtractor):
    name = "opencode"
    
    def is_available(self) -> bool:
        return self._find_db() is not None
    
    def _find_db(self) -> Path | None:
        for d in OPENCODE_DIRS:
            for db in d.glob("**/*.db"):
                return db
            for db in d.glob("**/*.sqlite"):
                return db
        return None
    
    def extract_sessions(self) -> Iterator[dict]:
        db_path = self._find_db()
        if not db_path:
            return
        
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            
            session_table = next((t for t in tables if "session" in t.lower()), None)
            message_table = next((t for t in tables if "message" in t.lower()), None)
            
            if not session_table:
                conn.close()
                return
            
            sessions = conn.execute(f"SELECT * FROM {session_table} ORDER BY rowid DESC LIMIT 200").fetchall()
            
            for row in sessions:
                s = dict(row)
                sid = str(s.get("id", s.get("session_id", row["rowid"])))
                
                messages = []
                if message_table:
                    col_names = [desc[0] for desc in conn.execute(f"SELECT * FROM {message_table} LIMIT 1").description or []]
                    session_col = next((c for c in col_names if "session" in c.lower()), None)
                    
                    if session_col:
                        msg_rows = conn.execute(
                            f"SELECT * FROM {message_table} WHERE {session_col} = ? ORDER BY rowid",
                            (sid,)
                        ).fetchall()
                        for m in msg_rows:
                            md = dict(m)
                            role = md.get("role", "user")
                            content = md.get("content", md.get("text", ""))
                            if isinstance(content, bytes):
                                content = content.decode("utf-8", errors="replace")
                            messages.append({
                                "role": role,
                                "content": str(content)[:4000],
                                "timestamp": md.get("created_at", md.get("timestamp", "")),
                            })
                
                first_user = next((m["content"] for m in messages if m["role"] == "user"), "")
                title = s.get("title", s.get("name", first_user[:80] if first_user else sid))
                
                yield {
                    "id": self.make_session_id("opencode", sid),
                    "source_tool": "opencode",
                    "source_path": str(db_path),
                    "project": s.get("project", s.get("workspace", "")),
                    "title": title,
                    "summary": "",
                    "created_at": s.get("created_at", s.get("timestamp", "")),
                    "messages": messages,
                    "tags": [],
                }
            
            conn.close()
        except Exception:
            pass
