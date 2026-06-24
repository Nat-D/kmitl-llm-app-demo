"""End-to-end tests — drive the real FastAPI app in-process with httpx, but STUB the
model (no network, no key, runs in CI). We assert the actual SSE the browser receives.

The same pattern the course portal uses: httpx.ASGITransport against the app object,
the LLM swapped for a fake so tests are fast and deterministic.
"""
import json

import httpx
import pytest

from app import llm, main, store
from app.store import Hit


def _frames(text: str) -> list[str]:
    """The `data:` payloads out of an SSE response body."""
    return [p.strip()[len("data:"):].strip() for p in text.split("\n\n") if p.strip().startswith("data:")]


def _answer_text(text: str) -> str:
    out = ""
    for f in _frames(text):
        if f == "[DONE]":
            continue
        try:
            out += json.loads(f).get("token", "")
        except json.JSONDecodeError:
            pass
    return out


@pytest.fixture
def client(monkeypatch):
    async def fake_chat_stream(messages, **kw):
        for t in ["Grounded", " answer", " [1]"]:
            yield t

    async def fake_embed(texts):
        return [[1.0, 0.0, 0.0] for _ in texts]

    # One module, two functions — patching here covers both main and rag (same object).
    monkeypatch.setattr(llm, "chat_stream", fake_chat_stream)
    monkeypatch.setattr(llm, "embed", fake_embed)
    main.app.state.db = None  # lifespan doesn't run under ASGITransport; store is stubbed below
    transport = httpx.ASGITransport(app=main.app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_chat_streams_tokens_then_done(client):
    r = await client.post("/api/chat", json={"message": "hi", "use_rag": False})
    frames = _frames(r.text)
    assert frames[-1] == "[DONE]"
    assert "Grounded answer" in _answer_text(r.text)


async def test_rag_emits_sources_then_cited_answer(client, monkeypatch):
    monkeypatch.setattr(
        store, "search", lambda db, vec, **kw: [Hit(1, "06-min-score-floor.md", "floor text", 0.7)]
    )
    r = await client.post("/api/chat", json={"message": "what is the floor?", "use_rag": True})
    frames = _frames(r.text)
    assert any('"sources"' in f for f in frames)      # sources frame is emitted first
    assert frames[-1] == "[DONE]"
    assert "[1]" in _answer_text(r.text)              # the cited answer streamed


async def test_rag_refuses_when_nothing_clears_the_floor(client, monkeypatch):
    monkeypatch.setattr(store, "search", lambda db, vec, **kw: [])
    r = await client.post("/api/chat", json={"message": "off topic", "use_rag": True})
    assert "don't have anything" in _answer_text(r.text)


async def test_bad_request_is_rejected(client):
    r = await client.post("/api/chat", json={"message": ""})   # min_length=1 fails
    assert r.status_code == 422
