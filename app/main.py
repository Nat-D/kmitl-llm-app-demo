"""FastAPI app: serve the web UI + a streaming chat endpoint.

POST /api/chat streams the reply as Server-Sent Events — one JSON frame per token
(`data: {"token": "..."}\\n\\n`), then `data: [DONE]\\n\\n`. That's exactly the wire
format the course's frontend/SSE lecture teaches, so the browser code in web/app.js
is the same buffer-and-split reader from that lecture.
"""
import asyncio
import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import llm, rag, store
from app.schemas import ChatRequest

# --- a tiny per-client rate limit -------------------------------------------------
# This endpoint is public and every request drives the shared model, so we cap it
# with an in-process token bucket (same idea as the course portal's runner). One
# process only — for multiple replicas you'd move this to Redis.
RL_CAPACITY = 20            # burst
RL_REFILL_PER_SEC = 20 / 60.0  # ~20 requests/min sustained


@dataclass
class _Bucket:
    tokens: float
    last: float


_buckets: dict[str, _Bucket] = {}
_rl_lock = asyncio.Lock()


async def _rate_ok(client: str) -> bool:
    async with _rl_lock:
        now = time.monotonic()
        b = _buckets.get(client)
        if b is None:
            _buckets[client] = _Bucket(RL_CAPACITY - 1, now)
            return True
        b.tokens = min(RL_CAPACITY, b.tokens + (now - b.last) * RL_REFILL_PER_SEC)
        b.last = now
        if b.tokens >= 1:
            b.tokens -= 1
            return True
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Open the vector store once at startup (read-only at serve time).
    app.state.db = store.connect()
    yield
    app.state.db.close()


app = FastAPI(title="KMITL LLM App Demo", lifespan=lifespan)
WEB = Path(__file__).resolve().parent.parent / "web"

SYSTEM_PROMPT = (
    "You are a concise teaching assistant for a course on building LLM apps. "
    "Answer in a few short, clear sentences."
)


def sse(obj: dict) -> str:
    """Encode one Server-Sent Events `data:` frame (terminated by a blank line)."""
    return f"data: {json.dumps(obj)}\n\n"


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request) -> StreamingResponse:
    # Behind Cloudflare the real client IP is in cf-connecting-ip; fall back locally.
    client = request.headers.get("cf-connecting-ip") or (
        request.client.host if request.client else "anon"
    )
    if not await _rate_ok(client):
        raise HTTPException(status_code=429, detail="Rate limit: ~20 requests/min. Slow down a bit.")

    async def events():
        try:
            if req.use_rag:
                # Grounded path: retrieve, cite, refuse when nothing clears the floor.
                async for event in rag.answer(app.state.db, req.message):
                    yield sse(event)
            else:
                # Plain chat (no retrieval) — useful to demo the difference live.
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": req.message},
                ]
                async for token in llm.chat_stream(messages):
                    yield sse({"token": token})
        except Exception as exc:
            # The 200 + headers are already sent, so we can't raise — surface the
            # failure as an SSE frame the browser shows instead of a silent cut-off.
            yield sse({"error": f"stream failed: {exc!r}"})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        # Tell any proxy NOT to buffer, or the live-token effect is lost.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/extract")
async def extract(request: Request, image: UploadFile = File(...)) -> dict:
    """Multimodal structured output (Lecture 2): upload a document image, get its
    fields back as validated JSON. The model reads the image directly."""
    client = request.headers.get("cf-connecting-ip") or (
        request.client.host if request.client else "anon"
    )
    if not await _rate_ok(client):
        raise HTTPException(status_code=429, detail="Rate limit: ~20 requests/min. Slow down a bit.")
    data = await image.read()
    if not data:
        raise HTTPException(status_code=422, detail="No image uploaded.")
    if len(data) > 4_000_000:
        raise HTTPException(status_code=413, detail="Image too large (max ~4 MB).")
    return await llm.extract_from_image(data, image.content_type or "image/png")


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/web", StaticFiles(directory=WEB), name="web")
