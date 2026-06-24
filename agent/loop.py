"""A minimal agent loop: the model can call a tool (search the notes), read the
result, and decide what to do next — call -> run -> feed-the-result-back, with a stop
condition. This is the same shape as native tool-calling, written plainly so the loop
itself is visible (no framework deciding things for you).

We use a tiny text protocol instead of the provider's function-calling API so it works
with any model: each turn the model emits ONE line, either an ACTION or an ANSWER.

Run:  python -m agent.loop "how are answers evaluated?"
"""
import asyncio
import re
import sys

from app import llm, store

MAX_STEPS = 4

SYSTEM = """You answer questions using a tool.

TOOL
  search_notes("query")  ->  returns relevant snippets from the course notes.

Each turn reply with EXACTLY ONE line, nothing else:
  ACTION: search_notes("your search query")     # to look something up
  ANSWER: your final answer                      # once you can answer

Rules: search at least once; do NOT repeat the same search; as soon as a TOOL
RESULT lets you answer, reply with ANSWER. Keep the answer to a few sentences."""

# When the loop runs out of steps without an ANSWER, we make one final turn that
# forces the model to answer from what it has — a real loop needs a stop condition
# that still produces something useful, not just "I gave up".
FORCE_ANSWER = "Stop searching. Using the TOOL RESULTs above, reply now with `ANSWER: ...`."

ACTION_RE = re.compile(r'ACTION:\s*search_notes\(\s*"(.+?)"\s*\)', re.S)


async def _say(messages: list[dict]) -> str:
    """One full (non-streamed) model turn."""
    return "".join([t async for t in llm.chat_stream(messages, temperature=0, max_tokens=200)]).strip()


async def search_notes(db, query: str, k: int = 3) -> str:
    """The one tool: embed the query, return the top chunks as text the model reads."""
    vec = (await llm.embed([query]))[0]
    hits = store.search(db, vec, top_k=k, min_score=0.0)
    if not hits:
        return "(no results)"
    return "\n".join(f"[{h.title}] {h.text[:240]}" for h in hits)


async def run(db, question: str, *, max_steps: int = MAX_STEPS, trace: list | None = None) -> str:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    for _ in range(max_steps):
        reply = await _say(messages)
        if trace is not None:
            trace.append(reply)
        m = ACTION_RE.search(reply)
        if not m:  # ANSWER (or anything that isn't a tool call) -> we're done
            return re.sub(r"^ANSWER:\s*", "", reply).strip()
        observation = await search_notes(db, m.group(1))
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content": f"TOOL RESULT:\n{observation}"})

    # Stop condition reached: force a final answer from what we gathered.
    messages.append({"role": "user", "content": FORCE_ANSWER})
    final = await _say(messages)
    if trace is not None:
        trace.append(final)
    return re.sub(r"^ANSWER:\s*", "", final).strip()


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "How are answers evaluated, and what metrics are used?"
    db = store.connect()
    steps: list[str] = []
    final = asyncio.run(run(db, question, trace=steps))
    for i, s in enumerate(steps, 1):
        print(f"--- step {i} ---\n{s}\n")
    print(f"=== answer ===\n{final}")
