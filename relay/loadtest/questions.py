"""Hand-written eval questions (≥15) with expected grading intent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalQuestion:
    qid: str
    question: str
    # expected: answerable | unanswerable
    expect: str
    notes: str = ""


QUESTIONS: list[EvalQuestion] = [
    EvalQuestion(
        "q01",
        "In Attention Is All You Need, what are the two sub-layers in each encoder layer?",
        "answerable",
        "multi-head self-attention + FFN",
    ),
    EvalQuestion(
        "q02",
        "What residual connection pattern does the Transformer encoder use around sub-layers?",
        "answerable",
    ),
    EvalQuestion(
        "q03",
        "According to Attention Is All You Need, what is the dimensionality d_model used in the base model?",
        "answerable",
    ),
    EvalQuestion(
        "q04",
        "What positional encoding approach do the authors of Attention Is All You Need use?",
        "answerable",
    ),
    EvalQuestion(
        "q05",
        "What is Moshi, according to its paper abstract or introduction?",
        "answerable",
    ),
    EvalQuestion(
        "q06",
        "Does Moshi support real-time full-duplex spoken dialogue according to the paper?",
        "answerable",
    ),
    EvalQuestion(
        "q07",
        "What modalities does Moshi jointly model?",
        "answerable",
    ),
    EvalQuestion(
        "q08",
        "What problem does Dynamic Chunking for End-to-End Hierarchical Sequence Modeling address?",
        "answerable",
    ),
    EvalQuestion(
        "q09",
        "How does the dynamic chunking paper relate chunking to hierarchical sequence modeling?",
        "answerable",
    ),
    EvalQuestion(
        "q10",
        "What evaluation datasets or tasks does the dynamic chunking paper report?",
        "answerable",
    ),
    # Unanswerable / traps
    EvalQuestion(
        "q11",
        "What is the stock price impact of releasing Moshi?",
        "unanswerable",
        "not in papers",
    ),
    EvalQuestion(
        "q12",
        "Which GPU did Vaswani et al. recommend buying in 2024 for fine-tuning Moshi?",
        "unanswerable",
        "cross-paper nonsense + outside knowledge",
    ),
    EvalQuestion(
        "q13",
        "What is the exact carbon footprint in kg CO2e of training the base Transformer in Attention Is All You Need?",
        "unanswerable",
        "likely not stated",
    ),
    EvalQuestion(
        "q14",
        "Did the Moshi authors cite Dynamic Chunking (2507.07955) as a dependency?",
        "unanswerable",
        "timeline / not claimed",
    ),
    EvalQuestion(
        "q15",
        "What restaurant did the Attention authors celebrate at after NeurIPS?",
        "unanswerable",
    ),
    EvalQuestion(
        "q16",
        "Compare attention in Transformers to attention in Moshi's audio stack using only these papers — if one paper lacks detail, say so.",
        "answerable",
        "partial / must not invent",
    ),
    EvalQuestion(
        "q17",
        "What learning rate schedule is used in Attention Is All You Need?",
        "answerable",
    ),
]


def as_prompt_list() -> list[str]:
    return [q.question for q in QUESTIONS]
