"""Extract conversations from Cursor (app data SQLite)."""
import sqlite3
import json
import os
from pathlib import Path
from typing import Iterator
from .base import BaseExtractor
import platform

def _cursor_dirs() -> list[Path]:
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        return [home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "storage.db",
                home / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage"]
    elif system == "Linux":
        return [home / ".config" / "Cursor" / "User" / "globalStorage",
                home / ".config" / "cursor" / "User" / "globalStorage"]
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return [appdata / "Cursor" / "User" / "globalStorage"]
    return []

class CursorExtractor(BaseExtractor):
    name = "cursor"
    
    def is_available(self) -> bool:
        return any(p.exists() for p in _cursor_dirs())
    
    def extract_sessions(self) -> Iterator[dict]:
        for base_path in _cursor_dirs():
            if not base_path.exists():
                continue
            
            db_files = list(base_path.glob("**/*.db")) if base_path.is_dir() else [base_path]
            
            for db_path in db_files:
                if not db_path.is_file():
                    continue
                
                try:
                    conn = sqlite3.connect(str(db_path))
                    conn.row_factory = sqlite3.Row
                    tables = [r[0] for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()]
                    
                    chat_table = next((t for t in tables if "chat" in t.lower() or "conversation" in t.lower()), None)
                    
                    if chat_table:
                        rows = conn.execute(f"SELECT * FROM {chat_table} ORDER BY rowid DESC LIMIT 100").fetchall()
                        for row in rows:
                            d = dict(row)
                            raw = d.get("messages", d.get("history", d.get("content", "")))
                            if not raw:
                                continue
                            
                            messages = []
                            try:
                                data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
                                if isinstance(data, list):
                                    for m in data:
                                        if isinstance(m, dict):
                                            messages.append({
                                                "role": m.get("role", "user"),
                                                "content": str(m.get("content", m.get("text", "")))[:4000],
                                                "timestamp": m.get("timestamp", ""),
                                            })
                            except:
                                pass
                            
                            if not messages:
                                continue
                            
                            first_user = next((m["content"] for m in messages if m["role"] == "user"), "")
                            
                            yield {
                                "id": self.make_session_id("cursor", str(d.get("id", row["rowid"]))),
                                "source_tool": "cursor",
                                "source_path": str(db_path),
                                "project": d.get("workspace", d.get("project", "")),
                                "title": d.get("title", first_user[:80]),
                                "summary": "",
                                "created_at": d.get("created_at", d.get("timestamp", "")),
                                "messages": messages,
                                "tags": [],
                            }
                    
                    conn.close()
                except Exception:
                    continue
