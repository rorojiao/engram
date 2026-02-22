"""Extract conversations from OpenCode (~/.local/share/opencode/ JSON files)."""
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterator
from .base import BaseExtractor

OPENCODE_BASE = Path.home() / ".local" / "share" / "opencode" / "storage"


class OpenCodeExtractor(BaseExtractor):
    name = "opencode"

    def is_available(self) -> bool:
        session_dir = OPENCODE_BASE / "session" / "global"
        return session_dir.exists() and any(session_dir.glob("ses_*.json"))

    def extract_sessions(self) -> Iterator[dict]:
        session_dir = OPENCODE_BASE / "session" / "global"
        if not session_dir.exists():
            return

        for ses_file in session_dir.glob("ses_*.json"):
            try:
                ses = json.loads(ses_file.read_text())
            except Exception:
                continue

            sid = ses.get("id", "")
            if not sid:
                continue

            # Read messages
            msg_dir = OPENCODE_BASE / "message" / sid
            messages = []
            msg_map = {}  # msg_id -> msg dict

            if msg_dir.exists():
                for msg_file in sorted(msg_dir.glob("msg_*.json")):
                    try:
                        msg = json.loads(msg_file.read_text())
                    except Exception:
                        continue
                    msg_id = msg.get("id", "")
                    role = msg.get("role", "user")
                    ts = ""
                    created = msg.get("time", {}).get("created")
                    if created:
                        ts = datetime.fromtimestamp(created / 1000, tz=timezone.utc).isoformat()

                    # Read parts for this message
                    part_dir = OPENCODE_BASE / "part" / msg_id
                    content_parts = []
                    if part_dir.exists():
                        for prt_file in sorted(part_dir.glob("prt_*.json")):
                            try:
                                prt = json.loads(prt_file.read_text())
                            except Exception:
                                continue
                            if prt.get("type") == "text" and prt.get("text"):
                                content_parts.append(prt["text"])

                    content = "\n".join(content_parts) if content_parts else ""
                    if not content:
                        continue

                    messages.append({
                        "role": role,
                        "content": content[:4000],
                        "timestamp": ts,
                    })
                    msg_map[msg_id] = msg

            # Title
            title = ses.get("title", "")
            if not title:
                first_user = next((m["content"] for m in messages if m["role"] == "user"), "")
                title = first_user[:80] if first_user else sid

            # Created time
            created_at = ""
            ses_created = ses.get("time", {}).get("created")
            if ses_created:
                created_at = datetime.fromtimestamp(ses_created / 1000, tz=timezone.utc).isoformat()

            yield {
                "id": self.make_session_id("opencode", sid),
                "source_tool": "opencode",
                "source_path": str(OPENCODE_BASE),
                "project": ses.get("directory", ""),
                "title": title,
                "summary": "",
                "created_at": created_at,
                "messages": messages,
                "tags": [],
            }
