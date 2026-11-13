"""On-disk chunk store (JSONL per retrieval piece-size family)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from relay.config import settings


def index_path(piece_size: int, index_dir: Path | None = None) -> Path:
    index_dir = index_dir or settings.INDEX_DIR
    return index_dir / f"chunks_ps{piece_size}.jsonl"


def save_chunks(chunks: Iterable[dict[str, Any]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
            n += 1
    return n


def load_chunks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


class ChunkStore:
    def __init__(self, piece_size: int) -> None:
        self.piece_size = piece_size
        self.path = index_path(piece_size)
        self._chunks: list[dict[str, Any]] | None = None

    def load(self) -> list[dict[str, Any]]:
        if self._chunks is None:
            self._chunks = load_chunks(self.path)
        return self._chunks

    def ensure_loaded(self) -> list[dict[str, Any]]:
        chunks = self.load()
        if not chunks:
            raise FileNotFoundError(
                f"No index at {self.path}. Run: python -m relay.index.build_index"
            )
        return chunks
