"""Score the RETRIEVER against a labelled set: Recall@k, MRR, nDCG.

Run:  python -m eval.eval        (needs the proxy for embeddings; ingest first)

"Relevant" is judged by source DOC (the .md filename), because one doc becomes
several chunks. Note we search with min_score=0 here: the floor is a *serve-time
safety* knob, but eval measures *ranking quality*, so we don't want the floor to
hide a bad ranking. Improve chunking/retrieval, re-run this, and watch the numbers.
"""
import asyncio
import json
import math
import os

from app import llm, store

K = int(os.environ.get("EVAL_K", "4"))
QRELS = os.path.join(os.path.dirname(__file__), "qrels.jsonl")


def load_qrels(path: str = QRELS) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def ranked_docs(hits: list[store.Hit]) -> list[str]:
    """Collapse retrieved chunks to a ranked list of distinct doc titles."""
    seen, docs = set(), []
    for h in hits:
        if h.title not in seen:
            seen.add(h.title)
            docs.append(h.title)
    return docs


def recall_at_k(ranked: list[str], relevant: list[str], k: int) -> float:
    return len(set(ranked[:k]) & set(relevant)) / len(relevant)


def mrr(ranked: list[str], relevant: list[str]) -> float:
    for i, doc in enumerate(ranked):
        if doc in relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(ranked: list[str], relevant: list[str], k: int) -> float:
    dcg = sum((1.0 if d in relevant else 0.0) / math.log2(i + 2) for i, d in enumerate(ranked[:k]))
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / ideal if ideal else 0.0


async def main() -> None:
    db = store.connect()
    if store.count(db) == 0:
        print("store is empty — run `make ingest` first.")
        return
    qrels = load_qrels()
    totals = {"recall": 0.0, "mrr": 0.0, "ndcg": 0.0}
    for ex in qrels:
        vec = (await llm.embed([ex["query"]]))[0]
        ranked = ranked_docs(store.search(db, vec, top_k=K, min_score=0.0))
        r = recall_at_k(ranked, ex["relevant"], K)
        m = mrr(ranked, ex["relevant"])
        n = ndcg_at_k(ranked, ex["relevant"], K)
        totals["recall"] += r
        totals["mrr"] += m
        totals["ndcg"] += n
        print(f"  R@{K}={r:.2f}  MRR={m:.2f}  nDCG={n:.2f}   {ex['query'][:52]}")
    n = len(qrels)
    print(
        f"\nMEAN over {n} queries:  "
        f"Recall@{K}={totals['recall']/n:.3f}  "
        f"MRR={totals['mrr']/n:.3f}  "
        f"nDCG@{K}={totals['ndcg']/n:.3f}"
    )


if __name__ == "__main__":
    asyncio.run(main())
