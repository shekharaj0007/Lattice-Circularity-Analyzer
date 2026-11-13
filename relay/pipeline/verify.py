"""Local citation grounding check + optional small-LLM verify."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from relay.config import settings
from relay.models.base import StreamResult
from relay.pipeline.types import Passage

CITE_RE = re.compile(r"\[([^\]]+?::c\d{4})[^\]]*\]|\[([^\]]+::c\d{4})\]")
PASSAGE_ID_RE = re.compile(r"(\d{4}\.\d{5}v\d+::c\d{4})")


@dataclass
class VerifyOutcome:
    ok: bool
    reason: str
    llm_result: StreamResult | None = None


def local_citation_check(answer: str, passages: list[Passage]) -> VerifyOutcome:
    if "the papers do not say" in answer.lower():
        return VerifyOutcome(ok=True, reason="honest_refuse")

    allowed = {p.passage_id for p in passages}
    found = set(PASSAGE_ID_RE.findall(answer))
    if not found:
        # Also accept bare [passage_id] without extras
        for p in passages:
            if p.passage_id in answer:
                found.add(p.passage_id)
    if not found:
        return VerifyOutcome(ok=False, reason="missing_citations")
    unknown = found - allowed
    if unknown:
        return VerifyOutcome(ok=False, reason=f"unknown_citations:{sorted(unknown)[:3]}")
    return VerifyOutcome(ok=True, reason="local_ok")


def llm_verify(client: Any, question: str, answer: str, passages: list[Passage]) -> VerifyOutcome:
    ctx = "\n".join(f"{p.passage_id}: {p.text[:400]}" for p in passages)
    messages = [
        {
            "role": "system",
            "content": (
                "Judge if the answer is fully grounded in the passages. "
                'JSON only: {"grounded": true|false, "reason": "..."}.'
            ),
        },
        {
            "role": "user",
            "content": f"Passages:\n{ctx}\n\nQuestion: {question}\n\nAnswer:\n{answer}",
        },
    ]
    result = client.complete(
        messages,
        model=settings.SMALL_MODEL,
        max_tokens=settings.VERIFY_MAX_TOKENS,
        temperature=0.0,
        stream=False,
    )
    if result.status != "ok":
        # Do not fail open to "ok" — skip LLM verify outcome, keep local only.
        return VerifyOutcome(ok=True, reason="llm_verify_unavailable", llm_result=result)
    low = result.text.lower()
    if '"grounded": false' in low or '"grounded":false' in low:
        return VerifyOutcome(ok=False, reason="llm_ungrounded", llm_result=result)
    return VerifyOutcome(ok=True, reason="llm_grounded", llm_result=result)
