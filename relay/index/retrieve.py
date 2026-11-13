"""Retrieval tool: lexical scoring + optional cheap re-rank."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from relay.config import settings
from relay.index.store import ChunkStore
from relay.pipeline.types import Passage

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _score(query_tokens: list[str], doc_tokens: list[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    q = Counter(query_tokens)
    d = Counter(doc_tokens)
    overlap = sum(min(q[t], d[t]) for t in q)
    # slight IDF-ish boost for rarer query terms appearing in doc
    rare = sum(1.0 / (1 + d[t]) for t in q if t in d)
    return overlap + 0.25 * rare + 0.1 * math.log(1 + len(set(query_tokens) & set(d)))


def _rerank(query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cheap re-rank: prefer denser query-term coverage near the start."""
    qset = set(tokenize(query))
    scored = []
    for c in candidates:
        text = c["text"]
        toks = tokenize(text)
        cover = len(qset & set(toks)) / max(1, len(qset))
        head = tokenize(text[:200])
        head_hit = len(qset & set(head)) / max(1, len(qset))
        scored.append((c.get("_score", 0) + 2.0 * cover + 1.0 * head_hit, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for s, c in scored:
        c = dict(c)
        c["_score"] = s
        out.append(c)
    return out


def retrieve(
    query: str,
    *,
    setting_name: str | None = None,
    shrink: bool = False,
) -> list[Passage]:
    name = setting_name or settings.DEFAULT_RETRIEVAL_SETTING
    cfg = settings.RETRIEVAL_SETTINGS[name]
    piece_size = cfg["piece_size"]
    top_k = settings.SHRUNK_TOP_K if shrink else int(cfg["top_k"])
    do_rerank = False if shrink else bool(cfg["re_rank"])
    if shrink:
        do_rerank = settings.SHRUNK_RE_RANK

    store = ChunkStore(piece_size)
    chunks = store.ensure_loaded()
    q_tokens = tokenize(query)
    scored: list[dict[str, Any]] = []
    for c in chunks:
        s = _score(q_tokens, tokenize(c["text"]))
        if s <= 0:
            continue
        row = dict(c)
        row["_score"] = s
        scored.append(row)
    scored.sort(key=lambda r: r["_score"], reverse=True)
    pool = scored[: max(top_k * 3, top_k)]
    if do_rerank and pool:
        pool = _rerank(query, pool)
    chosen = pool[:top_k]
    return [
        Passage(
            passage_id=c["passage_id"],
            paper_id=c["paper_id"],
            paper_title=c["paper_title"],
            section=c.get("section", ""),
            text=c["text"],
            score=float(c.get("_score", 0.0)),
        )
        for c in chosen
    ]


def hits_are_weak(passages: list[Passage], min_score: float = 1.5) -> bool:
    if not passages:
        return True
    return max(p.score for p in passages) < min_score
