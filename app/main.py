"""FastAPI app: serve the web UI + a streaming chat endpoint.

POST /api/chat streams the reply as Server-Sent Events — one JSON frame per token
(`data: {"token": "..."}\\n\\n`), then `data: [DONE]\\n\\n`. That's exactly the wire
format the course's frontend/SSE lecture teaches, so the browser code in web/app.js
is the same buffer-and-split reader from that lecture.
"""
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import llm, rag, store
from app.schemas import ChatRequest


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
async def chat(req: ChatRequest) -> StreamingResponse:
    async def events():
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
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        # Tell any proxy NOT to buffer, or the live-token effect is lost.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/web", StaticFiles(directory=WEB), name="web")
