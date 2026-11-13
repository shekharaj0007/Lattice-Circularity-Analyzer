"""Split paper text into overlapping pieces with citation metadata."""

from __future__ import annotations

import re
from typing import Any


SECTION_RE = re.compile(
    r"(?m)^(Abstract|ABSTRACT|References|REFERENCES|"
    r"\d+(?:\.\d+)*\.?\s+[A-Z][^\n]{0,80})$"
)


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
        body = re.sub(r"\s+", " ", body).strip()
        if not body:
            continue
        if len(body) <= piece_size:
            seq += 1
            pid = f"{paper_id}::c{seq:04d}"
            pieces.append(
                {
                    "passage_id": pid,
                    "paper_id": paper_id,
                    "paper_title": paper_title,
                    "section": section[:80],
                    "text": body,
                }
            )
            continue
        start = 0
        while start < len(body):
            end = min(len(body), start + piece_size)
            chunk = body[start:end].strip()
            if chunk:
                seq += 1
                pid = f"{paper_id}::c{seq:04d}"
                pieces.append(
                    {
                        "passage_id": pid,
                        "paper_id": paper_id,
                        "paper_title": paper_title,
                        "section": section[:80],
                        "text": chunk,
                    }
                )
            if end >= len(body):
                break
            start = max(0, end - overlap)
    return pieces
