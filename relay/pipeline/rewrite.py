"""Optional rewrite with small model — first step the degrade ladder drops."""

from __future__ import annotations

from typing import Any

from relay.config import settings
from relay.models.base import StreamResult

SYSTEM = """Rewrite for clarity only. Keep every citation id unchanged.
Do not add claims. Do not remove hedges like "The papers do not say."
Return only the rewritten answer."""


def rewrite(client: Any, draft_text: str) -> StreamResult:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": draft_text},
    ]
    return client.complete(
        messages,
        model=settings.SMALL_MODEL,
        max_tokens=settings.REWRITE_MAX_TOKENS,
        temperature=0.0,
        stream=False,
    )
