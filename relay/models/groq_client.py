"""Real Groq OpenAI-compatible client with streaming + TTFT."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from relay.config import settings
from relay.models.base import StreamResult


class GroqClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: float = settings.REQUEST_TIMEOUT_S,
    ) -> None:
        self.api_key = (api_key if api_key is not None else settings.GROQ_API_KEY).strip()
        self.base_url = (base_url or settings.GROQ_API_BASE).rstrip("/")
        self.timeout_s = timeout_s

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def complete(
        self,
        messages: list[dict],
        *,
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stream: bool = False,
    ) -> StreamResult:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers=self._headers(),
            method="POST",
        )
        t0 = time.perf_counter()
        try:
            if stream:
                return self._stream(req, t0)
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            total_ms = (time.perf_counter() - t0) * 1000.0
            text = body["choices"][0]["message"]["content"] or ""
            usage = body.get("usage") or {}
            return StreamResult(
                text=text,
                tokens_in=int(usage.get("prompt_tokens") or 0),
                tokens_out=int(usage.get("completion_tokens") or 0),
                first_token_ms=total_ms,  # non-stream: first≈total
                total_ms=total_ms,
                status="ok",
            )
        except urllib.error.HTTPError as e:
            total_ms = (time.perf_counter() - t0) * 1000.0
            err_body = e.read().decode("utf-8", errors="replace")
            status = "rate_limited" if e.code == 429 else "error"
            return StreamResult(
                text="",
                tokens_in=0,
                tokens_out=0,
                first_token_ms=None,
                total_ms=total_ms,
                raw_error=f"HTTP {e.code}: {err_body[:500]}",
                status=status,
            )
        except TimeoutError:
            total_ms = (time.perf_counter() - t0) * 1000.0
            return StreamResult(
                text="",
                tokens_in=0,
                tokens_out=0,
                first_token_ms=None,
                total_ms=total_ms,
                raw_error="timeout",
                status="timeout",
            )
        except Exception as e:  # noqa: BLE001
            total_ms = (time.perf_counter() - t0) * 1000.0
            return StreamResult(
                text="",
                tokens_in=0,
                tokens_out=0,
                first_token_ms=None,
                total_ms=total_ms,
                raw_error=str(e)[:500],
                status="error",
            )

    def _stream(self, req: urllib.request.Request, t0: float) -> StreamResult:
        chunks: list[str] = []
        first_token_ms: Optional[float] = None
        tokens_in = 0
        tokens_out = 0
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                while True:
                    line = resp.readline()
                    if not line:
                        break
                    line = line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        obj = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("usage"):
                        tokens_in = int(obj["usage"].get("prompt_tokens") or tokens_in)
                        tokens_out = int(obj["usage"].get("completion_tokens") or tokens_out)
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta = (choices[0].get("delta") or {}).get("content") or ""
                    if delta:
                        if first_token_ms is None:
                            first_token_ms = (time.perf_counter() - t0) * 1000.0
                        chunks.append(delta)
            total_ms = (time.perf_counter() - t0) * 1000.0
            text = "".join(chunks)
            if tokens_out == 0:
                tokens_out = max(1, len(text.split()))
            return StreamResult(
                text=text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                first_token_ms=first_token_ms,
                total_ms=total_ms,
                status="ok",
                chunks=chunks,
            )
        except urllib.error.HTTPError as e:
            total_ms = (time.perf_counter() - t0) * 1000.0
            err_body = e.read().decode("utf-8", errors="replace")
            status = "rate_limited" if e.code == 429 else "error"
            return StreamResult(
                text="".join(chunks),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                first_token_ms=first_token_ms,
                total_ms=total_ms,
                raw_error=f"HTTP {e.code}: {err_body[:500]}",
                status=status,
                chunks=chunks,
            )
