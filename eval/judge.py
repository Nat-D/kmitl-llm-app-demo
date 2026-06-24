"""LLM-as-judge: a cheap proxy for ANSWER quality when you have no gold answers.

We ask the model to score, 1-5, whether an answer is (a) faithful to its sources
(no made-up facts) and (b) relevant to the question. Useful, but remember the judge
is itself a model — calibrate it against a few human judgements before trusting it.

Run:  python -m eval.judge
"""
import asyncio
import json
import re

from app import llm, rag, store

JUDGE_SYSTEM = (
    "You are a strict grader. Given a question, the SOURCES that were retrieved, and "
    "an ANSWER, score the answer from 1 (poor) to 5 (excellent) on two axes:\n"
    "- faithfulness: every claim is supported by the sources (no invented facts)\n"
    "- relevance: it actually answers the question\n"
    'Reply with ONLY JSON: {"faithfulness": n, "relevance": n}.'
)


async def judge(question: str, answer: str, sources_text: str) -> dict:
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {
            "role": "user",
            "content": f"Question:\n{question}\n\nSources:\n{sources_text}\n\nANSWER:\n{answer}",
        },
    ]
    text = "".join([t async for t in llm.chat_stream(messages, temperature=0, max_tokens=80)])
    try:
        return json.loads(re.search(r"\{.*\}", text, re.S).group())
    except (AttributeError, json.JSONDecodeError):
        return {"faithfulness": None, "relevance": None, "raw": text}


async def main() -> None:
    db = store.connect()
    questions = [
        "How does the min_score floor work?",
        "Which embedding model is used and how many dimensions?",
    ]
    for q in questions:
        answer, sources = "", []
        async for ev in rag.answer(db, q):
            if "token" in ev:
                answer += ev["token"]
            if "sources" in ev:
                sources = ev["sources"]
        sources_text = "\n".join(f"[{i+1}] {s['title']}" for i, s in enumerate(sources))
        verdict = await judge(q, answer, sources_text)
        print(f"  {verdict}   {q[:50]}")


if __name__ == "__main__":
    asyncio.run(main())
