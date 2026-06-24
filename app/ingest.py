"""Build the vector store: read corpus/*.md, split into chunks, embed each, store.

Run once before serving:  python -m app.ingest corpus

Chunking here is deliberately NAIVE — fixed-size character windows with a little
overlap. It's the obvious thing, and it's the obvious thing to improve (semantic /
sentence-aware chunking is a great experiment — see eval/ to measure whether it helps).
"""
import asyncio
import glob
import os
import sys

from app import llm, store

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Slide a fixed-size window over the text, overlapping so a fact split across a
    boundary still lands whole in at least one chunk."""
    text = " ".join(text.split())  # collapse whitespace/newlines
    step = max(1, size - overlap)
    return [text[i : i + size] for i in range(0, len(text), step) if text[i : i + size].strip()]


async def build(corpus_dir: str) -> int:
    db = store.connect()
    db.execute("DELETE FROM chunks")  # fresh rebuild each run
    db.commit()

    rows: list[tuple[str, str]] = []  # (title, chunk_text)
    for path in sorted(glob.glob(os.path.join(corpus_dir, "*.md"))):
        title = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            for ch in chunk_text(f.read()):
                rows.append((title, ch))

    if not rows:
        print(f"no .md files found in {corpus_dir!r}")
        return 0

    vectors = await llm.embed([text for _, text in rows])
    store.add(db, [(title, text, vec) for (title, text), vec in zip(rows, vectors)])
    n = store.count(db)
    print(f"ingested {n} chunks from {corpus_dir}")
    return n


if __name__ == "__main__":
    corpus = sys.argv[1] if len(sys.argv) > 1 else "corpus"
    asyncio.run(build(corpus))
