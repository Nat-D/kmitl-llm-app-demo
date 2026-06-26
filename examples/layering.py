"""router -> service -> repository, in one readable file.

The mini app is intentionally FLAT (main.py + a few modules). This shows what the
three-layer "house style" looks like once an app grows enough to want it:

  - repository : pure data access (the ConversationRepository from orm_repository.py)
  - service    : the business logic — build the prompt, call the model, SAVE the turn
  - router     : HTTP only — parse the request, call the service, map errors to codes

The payoff is testability: you unit-test the SERVICE (the interesting part) by calling
a plain method with a FAKE model client and an in-memory repository — no HTTP server,
no FastAPI. The `__main__` below does exactly that.

Run it:  uv run --group pg python -m examples.layering
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from examples.orm_repository import Base, ConversationRepository


class ChatService:
    """The fat middle. Depends on its collaborators (the model client + the repo) by
    injection, which is what makes it testable in isolation."""

    def __init__(self, client, repo: ConversationRepository):
        self._client = client
        self._repo = repo

    def reply(self, user_id: str, message: str) -> str:
        answer = self._client.complete(message)   # call the model (the LLM client)
        self._repo.add(user_id, message, answer)  # persist the turn (the repository)
        return answer


# --- the router (shown for shape; needs a running server, so __main__ doesn't call it)
#
# from fastapi import APIRouter, Depends, HTTPException
# router = APIRouter(prefix="/api")
#
# @router.post("/chat")
# async def chat(req: ChatRequest, service: ChatService = Depends(get_service)):
#     try:
#         return {"reply": service.reply(req.user_id, req.message)}   # HTTP only
#     except ModelError:
#         raise HTTPException(502, "the model is unavailable")


class FakeLLM:
    """A stand-in for the model client — this is why injection matters: the test
    never touches the network."""

    def complete(self, message: str) -> str:
        return f"(stub answer to: {message})"


if __name__ == "__main__":
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        service = ChatService(FakeLLM(), ConversationRepository(session))
        # Testing the service is just a function call — no HTTP, no framework.
        print(service.reply("u1", "what is a vector store?"))
        session.commit()
        print("saved turns:", [t.message for t in ConversationRepository(session).recent("u1")])
