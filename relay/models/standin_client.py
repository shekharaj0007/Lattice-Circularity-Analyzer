"""Client pointing at the local stand-in (same shape as GroqClient)."""

from __future__ import annotations

from typing import Optional

from relay.config import settings
from relay.models.groq_client import GroqClient


class StandinClient(GroqClient):
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_s: float = settings.REQUEST_TIMEOUT_S,
    ) -> None:
        # Stand-in ignores auth; pass a dummy key so GroqClient headers succeed.
        super().__init__(
            api_key="stand-in-local",
            base_url=(base_url or settings.STANDIN_BASE).rstrip("/"),
            timeout_s=timeout_s,
        )
