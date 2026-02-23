"""精炼记忆库 memory.db — 存储提炼后的记忆事实（facts）。"""
import sqlite3, json, hashlib
from pathlib import Path
from datetime import datetime

MEMORY_DB = Path.home() / ".engram" / "memory.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id          TEXT PRIMARY KEY,
    scope       TEXT NOT NULL,
    content     TEXT NOT NULL,
    source      TEXT DEFAULT 'manual',
    priority    INTEGER DEFAULT 3,
    pinned      INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now')),
    last_used   TEXT DEFAULT (datetime('now')),
    use_count   INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    id UNINDEXED,
    scope UNINDEXED,
    content
);
"""

SCOPE_LIMITS = {"global": 50, "project": 30}

_schema_initialized = False

def get_mem_db():
    global _schema_initialized
    MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(MEMORY_DB), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    if not _schema_initialized:
        conn.executescript(SCHEMA)
        _schema_initialized = True
    return conn

def _make_id(scope: str, content: str) -> str:
    return hashlib.md5(f"{scope}:{content[:100]}".encode()).hexdigest()[:12]

def add_fact(scope: str, content: str, source: str = "manual", priority: int = 3, pinned: bool = False) -> str:
    if not content or not content.strip():
        raise ValueError("content 不能为空")
    content = content.strip()
    conn = get_mem_db()
    fid = _make_id(scope, content)
    try:
        conn.execute("""
            INSERT OR REPLACE INTO facts (id, scope, content, source, priority, pinned)
            VALUES (?,?,?,?,?,?)
        """, (fid, scope, content, source, priority, int(pinned)))
        conn.execute("DELETE FROM facts_fts WHERE id=?", (fid,))
        conn.execute("INSERT INTO facts_fts (id, scope, content) VALUES (?,?,?)", (fid, scope, content))
        conn.commit()
        _enforce_limit(conn, scope)
        return fid
    finally:
        conn.close()

def _enforce_limit(conn, scope: str):
    scope_type = "project" if scope.startswith("project:") else "global"
    limit = SCOPE_LIMITS.get(scope_type, 30)
    count = conn.execute("SELECT COUNT(*) FROM facts WHERE scope=? AND pinned=0", (scope,)).fetchone()[0]
    if count > limit:
        to_delete = count - limit
        # 先找到要删除的 id，同时清理 FTS
        ids_to_del = [r[0] for r in conn.execute("""
            SELECT id FROM facts
            WHERE scope=? AND pinned=0
            ORDER BY priority ASC, use_count ASC, created_at ASC
            LIMIT ?
        """, (scope, to_delete)).fetchall()]
        if ids_to_del:
            placeholders = ",".join("?" * len(ids_to_del))
            conn.execute(f"DELETE FROM facts_fts WHERE id IN ({placeholders})", ids_to_del)
            conn.execute(f"DELETE FROM facts WHERE id IN ({placeholders})", ids_to_del)
            conn.commit()

def search_facts(query: str, scope: str = None, limit: int = 10) -> list:
    conn = get_mem_db()
    try:
        scope_filter = "AND f.scope = ?" if scope else ""
        params_base = [scope] if scope else []
        try:
            rows = conn.execute(f"""
                SELECT f.* FROM facts f
                JOIN facts_fts ff ON ff.id = f.id
                WHERE facts_fts MATCH ?
                {scope_filter}
                ORDER BY f.priority DESC, f.use_count DESC
                LIMIT ?
            """, [f'"{query}"'] + params_base + [limit]).fetchall()
        except:
            scope_clause = "WHERE scope = ? AND" if scope else "WHERE"
            rows = conn.execute(f"""
                SELECT * FROM facts
                {scope_clause} content LIKE ?
                ORDER BY priority DESC, use_count DESC LIMIT ?
            """, params_base + [f"%{query}%", limit]).fetchall()
        for r in rows:
            conn.execute("UPDATE facts SET use_count=use_count+1, last_used=datetime('now') WHERE id=?", (r["id"],))
        conn.commit()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def list_facts(scope: str = None, pinned_only: bool = False) -> list:
    conn = get_mem_db()
    try:
        where_parts = []
        params = []
        if scope:
            where_parts.append("scope = ?"); params.append(scope)
        if pinned_only:
            where_parts.append("pinned = 1")
        where = "WHERE " + " AND ".join(where_parts) if where_parts else ""
        rows = conn.execute(f"""
            SELECT * FROM facts {where}
            ORDER BY pinned DESC, priority DESC, use_count DESC
        """, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_all_scopes() -> list:
    conn = get_mem_db()
    try:
        rows = conn.execute("SELECT DISTINCT scope FROM facts ORDER BY scope").fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()

def delete_fact(fid: str) -> bool:
    conn = get_mem_db()
    try:
        conn.execute("DELETE FROM facts WHERE id=?", (fid,))
        conn.execute("DELETE FROM facts_fts WHERE id=?", (fid,))
        conn.commit()
        return True
    finally:
        conn.close()
