"""The ONE place we talk to a model. Everything else calls these helpers.

We use the OpenAI client pointed at the class LiteLLM proxy (set OPENAI_BASE_URL and
OPENAI_API_KEY in .env). That's the whole "LLM integration" — an HTTP call you can
read. Swapping providers means changing the base URL and key, nothing else.
"""
import base64
import json
import os
import re
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


async def _complete(messages: list[dict], *, max_tokens: int = 400) -> str:
    """One non-streamed completion (used by the vision extractor below)."""
    resp = await _client().chat.completions.create(
        model=CHAT_MODEL, messages=messages, temperature=0, max_tokens=max_tokens
    )
    return resp.choices[0].message.content or ""


def _parse_json(text: str) -> dict | None:
    """Pull the first JSON object out of the model's reply (it may wrap it in ``` or
    add prose). Returns None if there isn't one we can parse."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group())
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


async def extract_from_image(image_bytes: bytes, mime: str = "image/png") -> dict:
    """Multimodal structured output (Lecture 2): the model READS a document image and
    returns its fields as JSON. gemma-4-E4B-it is multimodal, so we pass the image as
    a data URL alongside the instruction.

    The proxy ignores `response_format`, so we coax JSON via the prompt and parse it
    ourselves — and if the first reply isn't valid JSON, we show the model its own bad
    output and ask again (the parse-then-repair pattern this lecture teaches)."""
    data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"
    instruction = (
        "Read this document image and extract its key information as a FLAT JSON object "
        "of string fields (for example invoice_number, date, customer, items, total). "
        "Use snake_case keys. Return ONLY the JSON object, no prose, no code fences."
    )
    content = [
        {"type": "text", "text": instruction},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]
    first = await _complete([{"role": "user", "content": content}])
    obj = _parse_json(first)
    if obj is not None:
        return obj
    # Repair: the reply wasn't valid JSON — hand it back and ask for JSON only.
    repaired = await _complete(
        [
            {"role": "user", "content": content},
            {"role": "assistant", "content": first},
            {"role": "user", "content": "That was not valid JSON. Reply with ONLY a valid flat JSON object."},
        ]
    )
    return _parse_json(repaired) or {"_error": "could not parse JSON", "_raw": first[:500]}
