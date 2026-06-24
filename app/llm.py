"""The ONE place we talk to a model. Everything else calls these helpers.

We use the OpenAI client pointed at the class LiteLLM proxy (set OPENAI_BASE_URL and
OPENAI_API_KEY in .env). That's the whole "LLM integration" — an HTTP call you can
read. Swapping providers means changing the base URL and key, nothing else.
"""
import os
from collections.abc import AsyncIterator
from functools import lru_cache

from openai import AsyncOpenAI

CHAT_MODEL = os.environ.get("CHAT_MODEL", "gemma-4-E4B-it")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")


@lru_cache(maxsize=1)
def _client() -> AsyncOpenAI:
    # Created on first use, not at import — so tests (which stub these functions) and
    # CI can import the app without needing a key. Reads OPENAI_BASE_URL +
    # OPENAI_API_KEY from the environment.
    return AsyncOpenAI()


async def embed(texts: list[str]) -> list[list[float]]:
    """Turn a batch of texts into vectors. Used both to index the corpus (once) and
    to embed the user's question at query time. Same model for both — queries and
    documents MUST share an embedding space or their similarity is meaningless."""
    resp = await _client().embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


async def chat_stream(
    messages: list[dict], *, temperature: float = 0.3, max_tokens: int = 512
) -> AsyncIterator[str]:
    """Yield the assistant's reply one token at a time (so the caller can stream it
    to the browser). `stream=True` is the only difference from a normal call."""
    stream = await _client().chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        stream=True,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    async for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            yield token
