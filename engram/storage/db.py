"""SQLite storage with FTS5 full-text search."""
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

DB_PATH = Path.home() / ".engram" / "engram.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    source_tool TEXT NOT NULL,
    source_path TEXT,
    project TEXT,
    title TEXT,
    summary TEXT,
    message_count INTEGER DEFAULT 0,
    created_at TEXT,
    imported_at TEXT DEFAULT (datetime('now')),
    tags TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT,
    has_images INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
    id UNINDEXED,
    title,
    summary
);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    session_id UNINDEXED,
    content
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    source_tool TEXT,
    source_session_id TEXT,
    tags TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    id UNINDEXED,
    content
);
"""

def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

def upsert_session(session: dict) -> str:
    conn = get_db()
    try:
        sid = session["id"]
        messages = session.pop("messages", [])
        conn.execute("""
            INSERT OR REPLACE INTO sessions 
            (id, source_tool, source_path, project, title, summary, message_count, created_at, tags)
            VALUES (:id, :source_tool, :source_path, :project, :title, :summary, :message_count, :created_at, :tags)
        """, {**session, "tags": json.dumps(session.get("tags", [])), "message_count": len(messages)})
        
        # Clean old messages and FTS entries
        conn.execute("DELETE FROM messages_fts WHERE session_id = ?", (sid,))
        conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
        for msg in messages:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (sid, msg["role"], msg["content"], msg.get("timestamp"))
            )
            conn.execute("INSERT INTO messages_fts (session_id, content) VALUES (?, ?)",
                        (sid, msg["content"]))
        
        # Update sessions FTS
        conn.execute("DELETE FROM sessions_fts WHERE id = ?", (sid,))
        conn.execute("INSERT INTO sessions_fts (id, title, summary) VALUES (?, ?, ?)",
                    (sid, session.get("title",""), session.get("summary","")))
        conn.commit()
        return sid
    finally:
        conn.close()

def search_sessions(query: str, tool: str = None, limit: int = 10) -> list:
    conn = get_db()
    try:
        params = [f'"{query}"', f'"{query}"', limit]
        tool_filter = "AND s.source_tool = ?" if tool else ""
        if tool:
            params = [f'"{query}"', f'"{query}"', tool, limit]
        
        rows = conn.execute(f"""
            SELECT DISTINCT s.*, snippet(messages_fts, 1, '[', ']', '...', 20) as snippet
            FROM sessions s
            JOIN messages_fts mf ON mf.session_id = s.id
            WHERE messages_fts MATCH ? OR s.id IN (
                SELECT id FROM sessions_fts WHERE sessions_fts MATCH ?
            )
            {tool_filter}
            ORDER BY s.imported_at DESC
            LIMIT ?
        """, params).fetchall()
        return [dict(r) for r in rows]
    except:
        q = f"%{query}%"
        rows = conn.execute("""
            SELECT DISTINCT s.* FROM sessions s
            JOIN messages m ON m.session_id = s.id
            WHERE m.content LIKE ? OR s.title LIKE ? OR s.summary LIKE ?
            ORDER BY s.imported_at DESC LIMIT ?
        """, (q, q, q, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def list_sessions(tool: str = None, project: str = None, limit: int = 20) -> list:
    conn = get_db()
    try:
        where = []
        params = []
        if tool:
            where.append("source_tool = ?"); params.append(tool)
        if project:
            where.append("project LIKE ?"); params.append(f"%{project}%")
        where_clause = "WHERE " + " AND ".join(where) if where else ""
        params.append(limit)
        rows = conn.execute(f"""
            SELECT id, source_tool, project, title, summary, message_count, created_at, imported_at
            FROM sessions {where_clause}
            ORDER BY imported_at DESC LIMIT ?
        """, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_session(session_id: str) -> Optional[dict]:
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return None
        session = dict(row)
        msgs = conn.execute(
            "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,)
        ).fetchall()
        session["messages"] = [dict(m) for m in msgs]
        return session
    finally:
        conn.close()

def add_memory(content: str, source_tool: str = None, session_id: str = None, tags: list = None) -> int:
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO memories (content, source_tool, source_session_id, tags) VALUES (?, ?, ?, ?)",
            (content, source_tool, session_id, json.dumps(tags or []))
        )
        mid = cursor.lastrowid
        conn.execute("INSERT INTO memories_fts (id, content) VALUES (?, ?)", (str(mid), content))
        conn.commit()
        return mid
    finally:
        conn.close()

def search_memories(query: str, limit: int = 10) -> list:
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT m.* FROM memories m
            JOIN memories_fts mf ON mf.id = CAST(m.id AS TEXT)
            WHERE memories_fts MATCH ?
            ORDER BY m.created_at DESC LIMIT ?
        """, (f'"{query}"', limit)).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
