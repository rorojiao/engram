"""Extract conversations from Cursor (workspaceStorage state.vscdb)."""
import sqlite3
import json
import os
import platform
from pathlib import Path
from typing import Iterator
from .base import BaseExtractor


def _workspace_storage_dir() -> Path | None:
    system = platform.system()
    home = Path.home()
    candidates = []
    if system == "Darwin":
        candidates.append(home / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage")
    elif system == "Linux":
        candidates.append(home / ".config" / "Cursor" / "User" / "workspaceStorage")
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        candidates.append(appdata / "Cursor" / "User" / "workspaceStorage")
    for c in candidates:
        if c.exists():
            return c
    return None


class CursorExtractor(BaseExtractor):
    name = "cursor"

    def is_available(self) -> bool:
        d = _workspace_storage_dir()
        return d is not None and d.exists()

    def extract_sessions(self) -> Iterator[dict]:
        ws_dir = _workspace_storage_dir()
        if not ws_dir:
            return

        for db_path in ws_dir.glob("*/state.vscdb"):
            try:
                conn = sqlite3.connect(str(db_path), timeout=3)
                conn.execute("PRAGMA journal_mode=WAL")  # avoid lock conflicts with running Cursor
                row = conn.execute(
                    "SELECT value FROM ItemTable WHERE key = 'workbench.panel.aichat.view.aichat.chatdata'"
                ).fetchone()
                conn.close()
                if not row or not row[0]:
                    continue
            except (sqlite3.OperationalError, Exception):
                continue

            try:
                data = json.loads(row[0])
            except Exception:
                continue

            # data can be a dict with "tabs" or similar structure, or a list
            conversations = []
            if isinstance(data, dict):
                # Try common structures
                if "tabs" in data:
                    for tab in data["tabs"]:
                        if isinstance(tab, dict) and "chat" in tab:
                            conversations.append(tab["chat"])
                        elif isinstance(tab, dict) and "bubbles" in tab:
                            conversations.append(tab)
                elif "messages" in data:
                    conversations.append(data)
                elif "bubbles" in data:
                    conversations.append(data)
                else:
                    # Try all values that look like conversation objects
                    for v in data.values():
                        if isinstance(v, list):
                            conversations.append({"messages": v})
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        conversations.append(item)

            workspace_hash = db_path.parent.name

            for idx, conv in enumerate(conversations):
                messages = []
                # Try "bubbles" format (Cursor AI chat)
                bubbles = conv.get("bubbles", [])
                if bubbles:
                    for b in bubbles:
                        if not isinstance(b, dict):
                            continue
                        role = "assistant" if b.get("type") == "ai" or b.get("type") == "response" else "user"
                        content = b.get("text", b.get("content", ""))
                        if not content:
                            continue
                        messages.append({
                            "role": role,
                            "content": str(content)[:4000],
                            "timestamp": "",
                        })
                else:
                    # Try "messages" format
                    for m in conv.get("messages", []):
                        if not isinstance(m, dict):
                            continue
                        role = m.get("role", m.get("type", "user"))
                        content = m.get("content", m.get("text", ""))
                        if not content:
                            continue
                        if isinstance(content, list):
                            content = " ".join(str(c.get("text", c)) for c in content if isinstance(c, (dict, str)))
                        messages.append({
                            "role": str(role),
                            "content": str(content)[:4000],
                            "timestamp": "",
                        })

                if not messages:
                    continue

                first_user = next((m["content"] for m in messages if m["role"] == "user"), "")
                title = conv.get("title", conv.get("name", first_user[:80] if first_user else f"cursor-{workspace_hash[:8]}-{idx}"))

                unique_id = f"{workspace_hash}_{idx}"
                yield {
                    "id": self.make_session_id("cursor", unique_id),
                    "source_tool": "cursor",
                    "source_path": str(db_path),
                    "project": "",
                    "title": title,
                    "summary": "",
                    "created_at": "",
                    "messages": messages,
                    "tags": [],
                }
