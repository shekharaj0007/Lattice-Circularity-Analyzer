"""Cheap classify with small model: answerable from the three papers?"""

from __future__ import annotations

import json
import re
from typing import Any

from relay.config import settings
from relay.models.base import StreamResult

SYSTEM = """You classify questions for a library of exactly three papers:
1) Attention Is All You Need (arXiv 1706.03762v7) — Transformers, attention, training details
2) Moshi (arXiv 2410.00037v1) — speech-text foundation model, real-time / full-duplex dialogue, audio+text modalities
3) Dynamic Chunking (arXiv 2507.07955v2) — hierarchical sequence modeling, learned chunk boundaries

Reply with JSON only: {"answerable": true|false, "reason": "..."}.
answerable=true if ANY of these papers could plausibly contain the answer (including architecture, training, modalities, duplex/real-time claims in Moshi).
answerable=false only for outside knowledge (prices, restaurants, post-paper events, other papers' citations not claimed here)."""


def classify(client: Any, question: str) -> tuple[bool, str, StreamResult]:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    result = client.complete(
        messages,
        model=settings.SMALL_MODEL,
        max_tokens=settings.CLASSIFY_MAX_TOKENS,
        temperature=0.0,
        stream=False,
    )
    if result.status != "ok":
        # Fail open to retrieval — correctness of refusal decided later from passages.
        return True, f"classify_failed:{result.status}", result
    answerable, reason = _parse(result.text)
    return answerable, reason, result


def _parse(text: str) -> tuple[bool, str]:
    text = text.strip()
    try:
        obj = json.loads(text)
        return bool(obj.get("answerable")), str(obj.get("reason") or "")
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                obj = json.loads(m.group(0))
                return bool(obj.get("answerable")), str(obj.get("reason") or "")
            except json.JSONDecodeError:
                pass
    # Heuristic fallback
    low = text.lower()
    if "false" in low and "true" not in low:
        return False, "heuristic_false"
    return True, "heuristic_true"
