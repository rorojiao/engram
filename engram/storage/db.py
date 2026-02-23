"""SQLite storage with FTS5 full-text search and vector semantic search."""
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

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    message_id INTEGER,
    chunk TEXT NOT NULL,
    embedding BLOB,
    source_type TEXT DEFAULT 'message'
);

CREATE VIRTUAL TABLE IF NOT EXISTS vec_embeddings USING vec0(
    session_id TEXT,
    embedding FLOAT[384]
);
"""

def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception:
        pass
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
        messages = session.get("messages", [])   # 修复: get 不 pop，不破坏调用方的 dict
        session_data = {k: v for k, v in session.items() if k != "messages"}  # 安全副本
        conn.execute("""
            INSERT OR REPLACE INTO sessions 
            (id, source_tool, source_path, project, title, summary, message_count, created_at, tags)
            VALUES (:id, :source_tool, :source_path, :project, :title, :summary, :message_count, :created_at, :tags)
        """, {**session_data, "tags": json.dumps(session_data.get("tags", [])), "message_count": len(messages)})
        
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
        
        # Add vector embedding (lazy - don't fail if model not available)
        try:
            from .vector import add_embedding
            # Build content from title + summary + first 2 messages
            parts = [session.get("title", ""), session.get("summary", "")]
            for m in messages[:2]:
                parts.append(m.get("content", "")[:500])
            content = " ".join(p for p in parts if p)
            if content.strip():
                add_embedding(sid, content)
        except Exception:
            pass
        
        return sid
    finally:
        conn.close()

def search_sessions(query: str, tool: str = None, limit: int = 10) -> list:
    # Try vector search first for candidate session_ids
    vector_ids = []
    try:
        from .vector import vector_search
        vector_ids = vector_search(query, limit=limit)
    except Exception:
        pass

    conn = get_db()
    try:
        # Escape double quotes in query for FTS5 MATCH safety
        safe_query = query.replace('"', '""')
        fts_query = f'"{safe_query}"'
        params = [fts_query, fts_query, limit]
        tool_filter = "AND s.source_tool = ?" if tool else ""
        if tool:
            params = [fts_query, fts_query, tool, limit]
        
        rows = conn.execute(f"""
            SELECT DISTINCT s.*, snippet(messages_fts, 1, '[', ']', '...', 20) as snippet
            FROM sessions s
            JOIN messages_fts mf ON mf.session_id = s.id
            WHERE (messages_fts MATCH ? OR s.id IN (
                SELECT id FROM sessions_fts WHERE sessions_fts MATCH ?
            ))
            {tool_filter}
            ORDER BY s.imported_at DESC
            LIMIT ?
        """, params).fetchall()
        fts_results = [dict(r) for r in rows]
    except:
        q = f"%{query}%"
        tool_clause = "AND s.source_tool = ?" if tool else ""
        extra_params = [tool] if tool else []
        rows = conn.execute(f"""
            SELECT DISTINCT s.* FROM sessions s
            JOIN messages m ON m.session_id = s.id
            WHERE (m.content LIKE ? OR s.title LIKE ? OR s.summary LIKE ?)
            {tool_clause}
            ORDER BY s.imported_at DESC LIMIT ?
        """, (q, q, q, *extra_params, limit)).fetchall()
        fts_results = [dict(r) for r in rows]
    finally:
        conn.close()

    # Merge vector results with FTS results (deduplicated)
    seen = {r["id"] for r in fts_results}
    if vector_ids:
        conn = get_db()
        try:
            for vid in vector_ids:
                if vid not in seen:
                    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (vid,)).fetchone()
                    if row:
                        r = dict(row)
                        if not tool or r.get("source_tool") == tool:
                            fts_results.append(r)
                            seen.add(vid)
        finally:
            conn.close()

    return fts_results[:limit]

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
        safe_query = query.replace('"', '""')
        rows = conn.execute("""
            SELECT m.* FROM memories m
            JOIN memories_fts mf ON mf.id = CAST(m.id AS TEXT)
            WHERE memories_fts MATCH ?
            ORDER BY m.created_at DESC LIMIT ?
        """, (f'"{safe_query}"', limit)).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT * FROM memories WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_sessions_since(since_iso: str) -> list:
    """获取某时间点之后导入的会话。"""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, source_tool, project, title, summary, imported_at
            FROM sessions
            WHERE imported_at > ?
            ORDER BY imported_at DESC
        """, (since_iso,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
