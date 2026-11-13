"""Model client protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional, Protocol


@dataclass
class StreamResult:
    text: str
    tokens_in: int
    tokens_out: int
    first_token_ms: Optional[float]
    total_ms: float
    raw_error: str = ""
    status: str = "ok"  # ok | rate_limited | timeout | error
    chunks: list[str] = field(default_factory=list)
    rate_limit_headers: dict[str, str] = field(default_factory=dict)


class ModelClient(Protocol):
    def complete(
        self,
        messages: list[dict],
        *,
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stream: bool = False,
    ) -> StreamResult: ...
