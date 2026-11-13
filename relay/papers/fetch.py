"""Fetch the exact pinned arXiv PDF versions listed in manifest.json."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from relay.config import settings


def load_manifest(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or settings.MANIFEST_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data["papers"])


def pdf_path_for(paper: dict[str, Any], raw_dir: Path | None = None) -> Path:
    raw_dir = raw_dir or settings.PAPERS_RAW_DIR
    name = f"{paper['arxiv_id']}v{paper['version']}.pdf"
    return raw_dir / name


def fetch_paper(paper: dict[str, Any], raw_dir: Path | None = None, force: bool = False) -> Path:
    raw_dir = raw_dir or settings.PAPERS_RAW_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = pdf_path_for(paper, raw_dir)
    if dest.exists() and not force:
        return dest
    url = paper["source_url"]
    req = urllib.request.Request(url, headers={"User-Agent": "RelayAssignment/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())
    return dest


def fetch_all(force: bool = False) -> list[Path]:
    paths = []
    for paper in load_manifest():
        paths.append(fetch_paper(paper, force=force))
    return paths


if __name__ == "__main__":
    for p in fetch_all():
        print(f"ok {p} ({p.stat().st_size} bytes)")
