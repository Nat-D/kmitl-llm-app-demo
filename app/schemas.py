"""Request/response shapes. Pydantic validates the untrusted browser input for us
(Lecture 2: structured output / validation) — a bad body is rejected with a 422
before any of our code runs."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """One chat turn sent from the browser."""

    message: str = Field(..., min_length=1, max_length=4_000)
    # Toggle retrieval on/off so a demo can show the SAME question answered with and
    # without RAG. (Used from the l06-rag stage onward.)
    use_rag: bool = True
