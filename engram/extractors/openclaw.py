"""Extract conversations from OpenClaw (~/.openclaw/ SQLite)."""
import json
import sqlite3
from pathlib import Path
from typing import Iterator
from .base import BaseExtractor

OPENCLAW_DIR = Path.home() / ".openclaw"

class OpenClawExtractor(BaseExtractor):
    name = "openclaw"
    
    def is_available(self) -> bool:
        return any(OPENCLAW_DIR.glob("*.db")) or (OPENCLAW_DIR / "sessions.db").exists()
    
    def _find_db(self) -> Path | None:
        for db_file in OPENCLAW_DIR.glob("*.db"):
            return db_file
        sessions_db = OPENCLAW_DIR / "sessions.db"
        if sessions_db.exists():
            return sessions_db
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
            
            if "sessions" in tables or "conversation" in tables:
                table = "sessions" if "sessions" in tables else "conversation"
                try:
                    sessions = conn.execute(
                        f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 200"
                    ).fetchall()
                    
                    for row in sessions:
                        s = dict(row)
                        session_id = self.make_session_id("openclaw", str(s.get("id", s.get("key", ""))))
                        
                        messages = []
                        if "messages" in tables:
                            msg_rows = conn.execute(
                                "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id",
                                (s.get("id", s.get("key", "")),)
                            ).fetchall()
                            for m in msg_rows:
                                messages.append({
                                    "role": m["role"],
                                    "content": str(m["content"])[:4000],
                                    "timestamp": m.get("created_at", ""),
                                })
                        
                        if not messages and "history" in s:
                            try:
                                history = json.loads(s["history"]) if isinstance(s["history"], str) else s["history"]
                                for m in (history or []):
                                    if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
                                        messages.append({
                                            "role": m["role"],
                                            "content": str(m.get("content",""))[:4000],
                                            "timestamp": "",
                                        })
                            except:
                                pass
                        
                        first_user = next((m["content"] for m in messages if m["role"] == "user"), "")
                        
                        yield {
                            "id": session_id,
                            "source_tool": "openclaw",
                            "source_path": str(db_path),
                            "project": s.get("channel", s.get("label", "")),
                            "title": s.get("label", s.get("title", first_user[:80])),
                            "summary": "",
                            "created_at": s.get("created_at", ""),
                            "messages": messages,
                            "tags": [],
                        }
                except Exception:
                    pass
            
            conn.close()
        except Exception:
            pass
