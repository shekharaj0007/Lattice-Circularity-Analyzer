"""Split paper text into pieces preferring semantic boundaries.

Order of boundaries (coarse → fine):
1. Section headers (Abstract, numbered headings, References)
2. Paragraph breaks
3. Sentence endings (. ? !)
4. Hard character cap with overlap (last resort)

We do **not** use embedding-based semantic chunking (extra model/tokens).
For this three-paper library, structure-aware splits buy most of the gain.
"""

from __future__ import annotations

import re
from typing import Any


SECTION_RE = re.compile(
    r"(?m)^(Abstract|ABSTRACT|References|REFERENCES|"
    r"\d+(?:\.\d+)*\.?\s+[A-Z][^\n]{0,80})$"
)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\[\(])")


def _guess_sections(text: str) -> list[tuple[str, str]]:
    """Return list of (section_name, body)."""
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return [("body", text)]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        sections.append(("front", text[: matches[0].start()]))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        name = m.group(1).strip()
        body = text[m.end() : end].strip()
        sections.append((name, body))
    return sections


def _paragraphs(body: str) -> list[str]:
    # Keep blank-line paragraphs when PDF extract preserved them; else soft-wrap on long runs.
    parts = re.split(r"\n\s*\n+", body)
    parts = [re.sub(r"\s+", " ", p).strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        # Single blob from PDF: still try sentence-aware packing later.
        blob = re.sub(r"\s+", " ", body).strip()
        return [blob] if blob else []
    return parts


def _pack_units(units: list[str], piece_size: int, overlap: int) -> list[str]:
    """Pack semantic units into pieces ≤ piece_size; split oversized units on sentences."""
    pieces: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf.strip():
            pieces.append(buf.strip())
        buf = ""

    def emit_sentences(text: str) -> None:
        nonlocal buf
        sents = SENTENCE_RE.split(text) if len(text) > piece_size else [text]
        if len(sents) == 1 and len(text) > piece_size:
            # Hard wrap last resort
            start = 0
            while start < len(text):
                end = min(len(text), start + piece_size)
                chunk = text[start:end].strip()
                if chunk:
                    pieces.append(chunk)
                if end >= len(text):
                    break
                start = max(0, end - overlap)
            return
        for sent in sents:
            sent = sent.strip()
            if not sent:
                continue
            if len(sent) > piece_size:
                # recurse hard-wrap path
                emit_sentences(sent)
                continue
            candidate = f"{buf} {sent}".strip() if buf else sent
            if len(candidate) <= piece_size:
                buf = candidate
            else:
                flush()
                buf = sent

    for unit in units:
        if not unit:
            continue
        if len(unit) <= piece_size:
            candidate = f"{buf} {unit}".strip() if buf else unit
            if len(candidate) <= piece_size:
                buf = candidate
            else:
                flush()
                buf = unit
        else:
            flush()
            emit_sentences(unit)
            flush()
    flush()

    # Light overlap: append head of next piece onto previous when helpful for citation context
    if overlap > 0 and len(pieces) > 1:
        overlapped: list[str] = [pieces[0]]
        for prev, cur in zip(pieces, pieces[1:]):
            prefix = prev[-overlap:] if len(prev) > overlap else prev
            # Only prefix if it looks like a broken sentence tail
            if cur.startswith(prefix.strip()):
                overlapped.append(cur)
            else:
                merged = (prefix + " " + cur).strip()
                if len(merged) <= int(piece_size * 1.15):
                    overlapped.append(merged)
                else:
                    overlapped.append(cur)
        pieces = overlapped
    return pieces


def chunk_text(
    text: str,
    *,
    paper_id: str,
    paper_title: str,
    piece_size: int = 800,
    overlap: int = 120,
) -> list[dict[str, Any]]:
    pieces: list[dict[str, Any]] = []
    seq = 0
    for section, body in _guess_sections(text):
        if not body.strip():
            continue
        for chunk in _pack_units(_paragraphs(body), piece_size, overlap):
            if not chunk:
                continue
            seq += 1
            pid = f"{paper_id}::c{seq:04d}"
            pieces.append(
                {
                    "passage_id": pid,
                    "paper_id": paper_id,
                    "paper_title": paper_title,
                    "section": section[:80],
                    "text": chunk,
                    "boundary": "semantic",  # section → paragraph → sentence → hard
                }
            )
    return pieces
