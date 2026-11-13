"""CLI: fetch pinned PDFs → extract text → chunk for each retrieval preset."""

from __future__ import annotations

import sys
from pathlib import Path

from relay.config import settings
from relay.index.chunk import chunk_text
from relay.index.store import index_path, save_chunks
from relay.papers.fetch import fetch_all, load_manifest, pdf_path_for


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise SystemExit("pypdf is required: pip install pypdf") from e
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def build(force_fetch: bool = False) -> None:
    settings.PAPERS_RAW_DIR.mkdir(parents=True, exist_ok=True)
    settings.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    fetch_all(force=force_fetch)
    papers = load_manifest()

    # Unique piece sizes across presets
    sizes = sorted({cfg["piece_size"] for cfg in settings.RETRIEVAL_SETTINGS.values()})
    for piece_size in sizes:
        overlap = next(
            cfg["overlap"]
            for cfg in settings.RETRIEVAL_SETTINGS.values()
            if cfg["piece_size"] == piece_size
        )
        all_chunks = []
        for paper in papers:
            pdf = pdf_path_for(paper)
            text = extract_pdf_text(pdf)
            paper_id = f"{paper['arxiv_id']}v{paper['version']}"
            all_chunks.extend(
                chunk_text(
                    text,
                    paper_id=paper_id,
                    paper_title=paper["title"],
                    piece_size=piece_size,
                    overlap=overlap,
                )
            )
        path = index_path(piece_size)
        n = save_chunks(all_chunks, path)
        print(f"wrote {n} chunks → {path}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    build(force_fetch=force)
