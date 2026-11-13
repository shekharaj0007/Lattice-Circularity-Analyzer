"""Draft cited answer with the large model (streaming)."""

from __future__ import annotations

from typing import Any

from relay.config import settings
from relay.models.base import StreamResult
from relay.pipeline.types import Passage

SYSTEM = """You are a research assistant. Answer ONLY from the provided passages.
Rules:
- Every factual claim must include a citation like [passage_id].
- If the passages do not contain the answer, say exactly:
  "The papers do not say." and do not guess.
- Do not use outside knowledge.
- Be concise."""


def draft(client: Any, question: str, passages: list[Passage]) -> StreamResult:
    ctx = "\n\n".join(
        f"{p.cite()}\n{p.text}" for p in passages
    )
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": f"Passages:\n{ctx}\n\nQuestion: {question}\n\nCited answer:",
        },
    ]
    return client.complete(
        messages,
        model=settings.DRAFT_MODEL,
        max_tokens=settings.DRAFT_MAX_TOKENS,
        temperature=0.1,
        stream=True,
    )
