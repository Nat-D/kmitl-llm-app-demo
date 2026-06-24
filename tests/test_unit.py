"""Unit tests — pure functions, no network. Fast, deterministic, run anywhere.

These cover the bits with real logic: chunking, cosine ranking + the min_score floor,
prompt formatting, and the eval metrics.
"""
import math

from app import rag, store
from app.ingest import chunk_text
from app.store import Hit
from eval import eval as ev


def test_chunk_text_windows_are_bounded_and_overlap():
    chunks = chunk_text("word " * 400, size=800, overlap=150)
    assert len(chunks) >= 2
    assert all(len(c) <= 800 for c in chunks)


def test_search_ranks_by_similarity_and_applies_floor():
    db = store.connect(":memory:")
    store.add(db, [("a", "cat", [1, 0, 0]), ("b", "dog", [0, 1, 0]), ("c", "mid", [0.7, 0.7, 0])])
    hits = store.search(db, [1, 0, 0], top_k=3, min_score=0.5)
    assert hits[0].title == "a"                       # most similar first
    assert all(h.score >= 0.5 for h in hits)          # floor enforced
    assert "b" not in [h.title for h in hits]         # orthogonal chunk dropped


def test_floor_can_drop_everything():
    db = store.connect(":memory:")
    store.add(db, [("a", "x", [0, 1, 0])])
    assert store.search(db, [1, 0, 0], min_score=0.5) == []   # -> caller says "I don't know"


def test_format_context_numbers_the_sources():
    ctx = rag._format_context([Hit(1, "a.md", "alpha", 0.9), Hit(2, "b.md", "beta", 0.8)])
    assert "[1] (a.md) alpha" in ctx
    assert "[2] (b.md) beta" in ctx


def test_eval_metrics():
    ranked, relevant = ["x.md", "y.md", "z.md"], ["y.md"]
    assert ev.recall_at_k(ranked, relevant, 3) == 1.0
    assert ev.recall_at_k(ranked, relevant, 1) == 0.0
    assert ev.mrr(ranked, relevant) == 0.5            # first hit at rank 2
    assert math.isclose(ev.ndcg_at_k(ranked, relevant, 3), 1 / math.log2(3))
