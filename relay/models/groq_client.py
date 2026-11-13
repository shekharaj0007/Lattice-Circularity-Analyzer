"""Real Groq OpenAI-compatible client with streaming + TTFT."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from relay.config import settings
from relay.models.base import StreamResult
from relay.pipeline.token_channel import TokenChannel, estimate_messages_tokens

# Cloudflare WAF rejects the default Python-urllib signature (HTTP 403 / error 1010).
_USER_AGENT = "Mozilla/5.0 (compatible; LatticeRelay/1.0; +https://github.com/shekharaj0007/Lattice-Circularity-Analyzer)"


def _rate_limit_headers(headers) -> dict[str, str]:
    out: dict[str, str] = {}
    if headers is None:
        return out
    for k, v in headers.items():
        lk = k.lower()
        if lk.startswith("x-ratelimit-") or lk in ("retry-after", "x-request-id"):
            out[lk] = v
    return out


def _message_text(message: dict[str, Any]) -> str:
    content = (message.get("content") or "").strip()
    if content:
        return content
    # Some gpt-oss responses put visible text only after reasoning; never treat
    # reasoning as the user-facing answer.
    return ""


class GroqClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: float = settings.REQUEST_TIMEOUT_S,
        use_token_channel: bool = True,
        token_channel: Optional[TokenChannel] = None,
    ) -> None:
        import os

        env_key = os.environ.get("GROQ_API_KEY", "").strip()
        self.api_key = (api_key if api_key is not None else (env_key or settings.GROQ_API_KEY)).strip()
        self.base_url = (base_url or settings.GROQ_API_BASE).rstrip("/")
        self.timeout_s = timeout_s
        self.last_rate_limit_headers: dict[str, str] = {}
        self.use_token_channel = use_token_channel
        self.token_channel = token_channel

    def _channel(self) -> TokenChannel:
        return self.token_channel or TokenChannel.shared()

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        }

    def complete(
        self,
        messages: list[dict],
        *,
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stream: bool = False,
        reasoning_effort: Optional[str] = "low",
        bypass_channel: bool = False,
    ) -> StreamResult:
        """All provider calls go through the centralized TokenChannel by default."""

        def _do() -> StreamResult:
            return self._complete_uncached(
                messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream,
                reasoning_effort=reasoning_effort,
            )

        if bypass_channel or not self.use_token_channel:
            return _do()

        est = estimate_messages_tokens(messages, max_tokens)
        channel = self._channel()

        def on_denied(decision) -> StreamResult:
            return StreamResult(
                text="",
                tokens_in=0,
                tokens_out=0,
                first_token_ms=None,
                total_ms=decision.waited_ms,
                raw_error=f"token_channel:{decision.reason}",
                status="rate_limited",
            )

        decision = channel.acquire(est)
        if not decision.allowed:
            return on_denied(decision)
        try:
            result = _do()
            actual = int(result.tokens_in or 0) + int(result.tokens_out or 0)
            if result.status == "ok" and actual > 0:
                channel.release(decision.reserved_tokens, actual)
            elif result.status == "rate_limited":
                # Provider 429: free reservation; do not pretend tokens were spent.
                channel.release_failed(decision.reserved_tokens)
                channel.budget.record_rate_limit_hit()
            else:
                channel.release_failed(decision.reserved_tokens)
            return result
        except Exception:
            channel.release_failed(decision.reserved_tokens)
            raise

    def _complete_uncached(
        self,
        messages: list[dict],
        *,
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stream: bool = False,
        reasoning_effort: Optional[str] = "low",
    ) -> StreamResult:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
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
                rl = _rate_limit_headers(resp.headers)
                self.last_rate_limit_headers = rl
                body = json.loads(resp.read().decode("utf-8"))
            total_ms = (time.perf_counter() - t0) * 1000.0
            text = _message_text(body["choices"][0]["message"])
            usage = body.get("usage") or {}
            return StreamResult(
                text=text,
                tokens_in=int(usage.get("prompt_tokens") or 0),
                tokens_out=int(usage.get("completion_tokens") or 0),
                first_token_ms=total_ms,  # non-stream: first≈total
                total_ms=total_ms,
                status="ok",
                rate_limit_headers=rl,
            )
        except urllib.error.HTTPError as e:
            total_ms = (time.perf_counter() - t0) * 1000.0
            err_body = e.read().decode("utf-8", errors="replace")
            rl = _rate_limit_headers(getattr(e, "headers", None))
            self.last_rate_limit_headers = rl
            status = "rate_limited" if e.code == 429 else "error"
            return StreamResult(
                text="",
                tokens_in=0,
                tokens_out=0,
                first_token_ms=None,
                total_ms=total_ms,
                raw_error=f"HTTP {e.code}: {err_body[:500]}",
                status=status,
                rate_limit_headers=rl,
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
        rl: dict[str, str] = {}
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                rl = _rate_limit_headers(resp.headers)
                self.last_rate_limit_headers = rl
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
                    delta = choices[0].get("delta") or {}
                    piece = delta.get("content") or ""
                    if piece:
                        if first_token_ms is None:
                            first_token_ms = (time.perf_counter() - t0) * 1000.0
                        chunks.append(piece)
            total_ms = (time.perf_counter() - t0) * 1000.0
            text = "".join(chunks)
            if tokens_out == 0 and text:
                tokens_out = max(1, len(text.split()))
            return StreamResult(
                text=text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                first_token_ms=first_token_ms,
                total_ms=total_ms,
                status="ok",
                chunks=chunks,
                rate_limit_headers=rl,
            )
        except urllib.error.HTTPError as e:
            total_ms = (time.perf_counter() - t0) * 1000.0
            err_body = e.read().decode("utf-8", errors="replace")
            rl = _rate_limit_headers(getattr(e, "headers", None)) or rl
            self.last_rate_limit_headers = rl
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
                rate_limit_headers=rl,
            )
