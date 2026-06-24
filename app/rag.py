"""Retrieval-Augmented Generation: find relevant chunks, put them in the prompt as a
numbered list, and stream a CITED answer. This is the whole of "RAG" — retrieve, then
format, then call. No framework, no magic.

`answer()` yields plain dict events; the web layer turns them into SSE frames:
  - first a  {"sources": [...]}  event (so the UI can show what fed the answer),
  - then a stream of  {"token": "..."}  events.
"""
import sqlite3
from collections.abc import AsyncIterator

from app import llm, store

RAG_SYSTEM = (
    "You are a teaching assistant for a course on building LLM apps. Answer ONLY "
    "from the numbered sources below, and cite each claim with its number like [1]. "
    "If the sources do not contain the answer, say you don't know — never use outside "
    "knowledge.\n\nSources:\n{context}"
)

# Said when nothing clears the min_score floor. Refusing beats confidently making
# something up — this is the behaviour the floor exists to produce.
NO_CONTEXT = (
    "I don't have anything in my notes about that. Try rephrasing, or ask about the "
    "course stack — LiteLLM, embeddings, SSE streaming, RAG, evaluation, or agents."
)


def _format_context(hits: list[store.Hit]) -> str:
    return "\n".join(f"[{i + 1}] ({h.title}) {h.text}" for i, h in enumerate(hits))


async def answer(
    db: sqlite3.Connection,
    question: str,
    *,
    top_k: int | None = None,
    min_score: float | None = None,
) -> AsyncIterator[dict]:
    # 1. embed the question and 2. retrieve the chunks that clear the floor.
    kwargs = {}
    if top_k is not None:
        kwargs["top_k"] = top_k
    if min_score is not None:
        kwargs["min_score"] = min_score
    query_vec = (await llm.embed([question]))[0]
    hits = store.search(db, query_vec, **kwargs)

    if not hits:
        for word in NO_CONTEXT.split(" "):
            yield {"token": word + " "}
        return

    # 3. show the sources, then 4. format them into the prompt and stream the answer.
    yield {"sources": [{"title": h.title, "score": round(h.score, 3)} for h in hits]}
    messages = [
        {"role": "system", "content": RAG_SYSTEM.format(context=_format_context(hits))},
        {"role": "user", "content": question},
    ]
    async for token in llm.chat_stream(messages):
        yield {"token": token}
