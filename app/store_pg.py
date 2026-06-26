"""The pgvector-backed vector store — the production swap for store.py.

It exposes the SAME interface (Hit / connect / add / search / count), so nothing
else in the app changes: set DATABASE_URL and `app/vectorstore.py` picks this module
instead of the SQLite one. The win over the brute-force NumPy store is that the
nearest-neighbour search happens IN the database and stays fast at millions of rows.

Needs the `pg` dependency group:  uv sync --group pg
Local Postgres + pgvector:        docker compose up -d   (see docker-compose.yml)

Schema note: in production the `chunks` table is owned by Alembic migrations (see
alembic/). We keep a CREATE TABLE IF NOT EXISTS here too so the demo runs even if you
skip `alembic upgrade head` — but the disciplined way to change the schema is a
migration, not editing tables by hand.
"""
import os
from dataclasses import dataclass

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

DATABASE_URL = os.environ.get("DATABASE_URL", "")
MIN_SCORE = float(os.environ.get("MIN_SCORE", "0.40"))
TOP_K = int(os.environ.get("TOP_K", "4"))
DIM = 1024  # bge-m3 embedding dimensions


@dataclass
class Hit:
    chunk_id: int
    title: str
    text: str
    score: float


def connect(url: str = DATABASE_URL) -> psycopg.Connection:
    conn = psycopg.connect(url, autocommit=True)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS chunks ("
        f"id serial PRIMARY KEY, title text, text text, embedding vector({DIM}))"
    )
    register_vector(conn)  # lets us pass/receive numpy arrays as vectors
    return conn


def add(conn: psycopg.Connection, rows: list[tuple[str, str, list[float]]]) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO chunks (title, text, embedding) VALUES (%s, %s, %s)",
            [(t, x, np.asarray(e, dtype=np.float32)) for t, x, e in rows],
        )


def count(conn: psycopg.Connection) -> int:
    return conn.execute("SELECT count(*) FROM chunks").fetchone()[0]


def search(
    conn: psycopg.Connection,
    query_vec: list[float],
    *,
    top_k: int = TOP_K,
    min_score: float = MIN_SCORE,
) -> list[Hit]:
    """Top-k by cosine similarity, with the same min_score floor as the SQLite store.
    pgvector's `<=>` is cosine DISTANCE, so cosine similarity = 1 - distance. For a big
    table you'd add an HNSW index on `embedding` to keep this fast; 21 rows don't need it.
    """
    q = np.asarray(query_vec, dtype=np.float32)
    rows = conn.execute(
        "SELECT id, title, text, 1 - (embedding <=> %s) AS score "
        "FROM chunks ORDER BY embedding <=> %s LIMIT %s",
        (q, q, top_k),
    ).fetchall()
    return [Hit(r[0], r[1], r[2], float(r[3])) for r in rows if r[3] >= min_score]
