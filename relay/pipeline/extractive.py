"""Extractive answer: quoted spans + citations; no generative synthesis."""

from __future__ import annotations

from relay.pipeline.types import Passage


def extractive_answer(question: str, passages: list[Passage]) -> str:
    if not passages:
        return (
            "I cannot complete a safe generative answer right now, and I have no "
            "retrieved passages to quote. Please try later."
        )
    lines = [
        "Budget is tight, so here is an extractive answer (quotes only; no synthesis):",
        f"Question: {question}",
        "",
    ]
    for p in passages:
        quote = p.text.strip()
        if len(quote) > 400:
            quote = quote[:400].rstrip() + "…"
        lines.append(f"{p.cite()}")
        lines.append(f"\"{quote}\"")
        lines.append("")
    lines.append(
        "If these quotes do not answer the question, the papers may not say — I will not guess."
    )
    return "\n".join(lines)


def try_later_message(reason: str) -> str:
    return (
        "I can't safely answer right now without guessing "
        f"({reason}). Please try again later when budget/capacity recovers. "
        "I will not invent an answer just to stay fast."
    )
