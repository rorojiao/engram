"""Vector semantic search using sqlite-vec and fastembed."""
import struct
from typing import Optional

_model = None


def get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _model


def embed_text(text: str) -> bytes:
    """Embed text and return as packed float32 bytes."""
    model = get_model()
    vec = next(model.embed([text]))
    return struct.pack(f"{len(vec)}f", *vec)


def add_embedding(session_id: str, content: str):
    """Store embedding for a session's content."""
    from .db import get_db
    embedding = embed_text(content)
    conn = get_db()
    try:
        # Delete old embedding for this session
        conn.execute("DELETE FROM vec_embeddings WHERE session_id = ?", (session_id,))
        conn.execute(
            "INSERT INTO vec_embeddings (session_id, embedding) VALUES (?, ?)",
            (session_id, embedding)
        )
        conn.commit()
    finally:
        conn.close()


def vector_search(query: str, limit: int = 10) -> list[str]:
    """KNN vector search, returns list of session_ids."""
    from .db import get_db
    q_emb = embed_text(query)
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT session_id, distance
            FROM vec_embeddings
            WHERE embedding MATCH ? AND k = ?
            ORDER BY distance
        """, (q_emb, limit)).fetchall()
        return [row[0] for row in rows]
    except Exception:
        return []
    finally:
        conn.close()
