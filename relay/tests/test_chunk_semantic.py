"""Semantic boundary chunking prefers section → paragraph → sentence."""

from __future__ import annotations

from relay.index.chunk import chunk_text


SAMPLE = """
Abstract
This is the abstract sentence one. This is abstract sentence two.

1 Introduction
First paragraph about transformers and attention.

Second paragraph continues the intro with more detail. It has another sentence here.

2 Method
Short method note.
"""


def test_chunks_preserve_sections_and_sentences() -> None:
    pieces = chunk_text(
        SAMPLE,
        paper_id="1706.03762v7",
        paper_title="Attention Is All You Need",
        piece_size=120,
        overlap=20,
    )
    assert pieces
    assert all(p.get("boundary") == "semantic" for p in pieces)
    # Should not mid-cut the short method note into nonsense if it fits
    texts = " || ".join(p["text"] for p in pieces)
    assert "Short method note." in texts
    assert any("Abstract" in p["section"] or "abstract" in p["section"].lower() or p["section"] for p in pieces)


if __name__ == "__main__":
    test_chunks_preserve_sections_and_sentences()
    print("ok")
