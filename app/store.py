"""A tiny vector store. SQLite holds the chunks + their embeddings; retrieval ranks
by cosine similarity computed in NumPy. For a small corpus that's all "a vector
database" is — embed everything once, then compare the query with cosine.

Production swap (same `add` / `search` shape): pgvector or sqlite-vec do this
nearest-neighbour search inside the database, which matters at millions of rows.
Here, brute-force over a few hundred chunks is instant and far easier to read.
"""
import os
import sqlite3
from dataclasses import dataclass

import numpy as np

DB_PATH = os.environ.get("DB_PATH", "data/store.db")
MIN_SCORE = float(os.environ.get("MIN_SCORE", "0.45"))
TOP_K = int(os.environ.get("TOP_K", "4"))


@dataclass
class Hit:
    """One retrieved chunk and how similar it was to the query (0..1)."""

    chunk_id: int
    title: str
    text: str
    score: float


def connect(path: str = DB_PATH) -> sqlite3.Connection:
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    # check_same_thread=False: the web app opens the connection at startup and reads
    # it from async request handlers; reads are safe and we never write at serve time.
    db = sqlite3.connect(path, check_same_thread=False)
    db.execute(
        "CREATE TABLE IF NOT EXISTS chunks("
        "id INTEGER PRIMARY KEY, title TEXT, text TEXT, embedding BLOB)"
    )
    return db


def add(db: sqlite3.Connection, rows: list[tuple[str, str, list[float]]]) -> None:
    """rows = [(title, text, embedding)]. Embeddings are stored as raw float32 bytes."""
    db.executemany(
        "INSERT INTO chunks(title, text, embedding) VALUES(?, ?, ?)",
        [(t, x, np.asarray(e, dtype=np.float32).tobytes()) for t, x, e in rows],
    )
    db.commit()


def count(db: sqlite3.Connection) -> int:
    return db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]


def _load(db: sqlite3.Connection):
    rows = db.execute("SELECT id, title, text, embedding FROM chunks").fetchall()
    ids = [r[0] for r in rows]
    titles = [r[1] for r in rows]
    texts = [r[2] for r in rows]
    mat = (
        np.vstack([np.frombuffer(r[3], dtype=np.float32) for r in rows])
        if rows
        else np.zeros((0, 1), dtype=np.float32)
    )
    return ids, titles, texts, mat


def search(
    db: sqlite3.Connection,
    query_vec: list[float],
    *,
    top_k: int = TOP_K,
    min_score: float = MIN_SCORE,
) -> list[Hit]:
    """Return the top-k chunks by cosine similarity that clear the min_score floor.

    The floor is the single most important RAG safety knob: if NOTHING clears it we
    return [] and the caller answers "I don't know" rather than grounding on junk.
    """
    ids, titles, texts, mat = _load(db)
    if not ids:
        return []
    scores = _cosine(np.asarray(query_vec, dtype=np.float32), mat)
    order = np.argsort(scores)[::-1][:top_k]
    hits = [Hit(ids[i], titles[i], texts[i], float(scores[i])) for i in order]
    return [h for h in hits if h.score >= min_score]


def _cosine(q: np.ndarray, mat: np.ndarray) -> np.ndarray:
    """Cosine similarity of vector q against every row of mat = the normalised dot
    product (direction, not magnitude). The 1e-9 guards a zero-norm vector."""
    qn = q / (np.linalg.norm(q) + 1e-9)
    mn = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
    return mn @ qn
