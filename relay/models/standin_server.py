"""Stand-in model service: slow, fail, rate-limit, load-sensitive, streaming.

Calibrate latency / limits from probe measurements (see scripts/calibrate_standin.py).
Least like real Groq: token accounting fairness, multi-tenant scheduling, exact 429 bodies.
"""

from __future__ import annotations

import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from relay.config import settings

# Calibrated defaults (overwritten by calibrate_standin.py → standin_calib.json)
CALIB = {
    "ttft_p50_ms": 180.0,
    "ttft_p95_ms": 600.0,
    "total_p50_ms": 900.0,
    "total_p95_ms": 2500.0,
    "rpm": settings.LIMIT_RPM,
    "tpm": settings.LIMIT_TPM,
    "rpd": settings.LIMIT_RPD,
    "fail_rate": 0.01,
    "load_slowdown_per_inflight": 0.08,
}


_lock = threading.Lock()
_minute: list[tuple[float, int]] = []
_day_key = time.strftime("%Y-%m-%d", time.gmtime())
_day_req = 0
_day_tok = 0
_inflight = 0


def _roll() -> None:
    global _day_key, _day_req, _day_tok
    key = time.strftime("%Y-%m-%d", time.gmtime())
    if key != _day_key:
        _day_key = key
        _day_req = 0
        _day_tok = 0


def _prune(now: float) -> None:
    cutoff = now - 60.0
    while _minute and _minute[0][0] < cutoff:
        _minute.pop(0)


def _check_limits(est_tokens: int) -> str | None:
    global _day_req, _day_tok
    now = time.time()
    _roll()
    _prune(now)
    if len(_minute) >= int(CALIB["rpm"]):
        return "rate_limit_rpm"
    if sum(t for _, t in _minute) + est_tokens > int(CALIB["tpm"]):
        return "rate_limit_tpm"
    if _day_req >= int(CALIB["rpd"]):
        return "rate_limit_rpd"
    return None


def _record(tokens: int) -> None:
    global _day_req, _day_tok
    now = time.time()
    _roll()
    _prune(now)
    _minute.append((now, tokens))
    _day_req += 1
    _day_tok += tokens


def _sample_delay_ms(p50: float, p95: float) -> float:
    # Log-normal-ish around p50 with fat tail toward p95
    u = random.random()
    if u < 0.5:
        return max(5.0, random.gauss(p50, (p95 - p50) / 6))
    return max(p50, random.uniform(p50, p95 * 1.2))


def _fake_completion(messages: list[dict], model: str) -> str:
    user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user = m.get("content") or ""
            break
    # Deterministic-ish stub that looks like a cited reply for load tests
    return (
        f"[stand-in:{model}] Based on the retrieved passages, "
        f"I answer carefully without inventing facts. "
        f"Question echo: {user[:180]} "
        f"Citation: [passage]"
    )


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # quiet
        return

    def _json(self, code: int, obj: dict) -> None:
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/health":
            self._json(200, {"ok": True, "calib": CALIB, "inflight": _inflight})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        global _inflight
        path = urlparse(self.path).path
        if path != "/v1/chat/completions":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        messages = body.get("messages") or []
        model = body.get("model") or "stand-in"
        stream = bool(body.get("stream"))
        max_tokens = int(body.get("max_tokens") or 256)
        est_out = min(max_tokens, 200)
        est_in = sum(len((m.get("content") or "").split()) for m in messages)

        with _lock:
            reason = _check_limits(est_in + est_out)
            if reason:
                self._json(
                    429,
                    {
                        "error": {
                            "message": f"Stand-in rate limit: {reason}",
                            "type": "rate_limit_exceeded",
                            "code": reason,
                        }
                    },
                )
                return
            _inflight += 1
            local_inflight = _inflight

        try:
            if random.random() < float(CALIB["fail_rate"]):
                time.sleep(0.05)
                self._json(500, {"error": {"message": "stand-in injected failure"}})
                return

            slow = 1.0 + float(CALIB["load_slowdown_per_inflight"]) * max(0, local_inflight - 1)
            ttft = _sample_delay_ms(CALIB["ttft_p50_ms"], CALIB["ttft_p95_ms"]) * slow
            total = max(
                ttft + 50,
                _sample_delay_ms(CALIB["total_p50_ms"], CALIB["total_p95_ms"]) * slow,
            )
            text = _fake_completion(messages, model)
            # Cap length roughly by max_tokens
            words = text.split()
            if len(words) > max_tokens:
                text = " ".join(words[:max_tokens])

            time.sleep(ttft / 1000.0)
            remain = max(0.0, (total - ttft) / 1000.0)

            tokens_in = max(1, est_in)
            tokens_out = max(1, len(text.split()))

            if stream:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                pieces = text.split(" ")
                gap = remain / max(1, len(pieces))
                for i, w in enumerate(pieces):
                    chunk = w + (" " if i < len(pieces) - 1 else "")
                    payload = {
                        "choices": [{"delta": {"content": chunk}}],
                    }
                    self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode())
                    self.wfile.flush()
                    if gap:
                        time.sleep(gap)
                usage = {
                    "choices": [{"delta": {}}],
                    "usage": {
                        "prompt_tokens": tokens_in,
                        "completion_tokens": tokens_out,
                    },
                }
                self.wfile.write(f"data: {json.dumps(usage)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            else:
                time.sleep(remain)
                self._json(
                    200,
                    {
                        "choices": [{"message": {"role": "assistant", "content": text}}],
                        "usage": {
                            "prompt_tokens": tokens_in,
                            "completion_tokens": tokens_out,
                        },
                    },
                )
            with _lock:
                _record(tokens_in + tokens_out)
        finally:
            with _lock:
                _inflight = max(0, _inflight - 1)


def load_calib(path=None) -> None:
    path = path or (settings.PROBES_DIR / "standin_calib.json")
    if path.exists():
        CALIB.update(json.loads(path.read_text(encoding="utf-8")))


def serve(host: str | None = None, port: int | None = None) -> None:
    load_calib()
    host = host or settings.STANDIN_HOST
    port = port or settings.STANDIN_PORT
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"stand-in listening on http://{host}:{port} calib={CALIB}")
    httpd.serve_forever()


if __name__ == "__main__":
    serve()
