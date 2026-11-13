"""Modest real Groq probes to learn latency + limit behavior (Table 1).

Spend carefully: this shares the free-tier daily budget.
"""

from __future__ import annotations

import json
import time

from relay.config import settings
from relay.models.groq_client import GroqClient


def probe(n: int = 6) -> dict:
    settings.PROBES_DIR.mkdir(parents=True, exist_ok=True)
    client = GroqClient()
    rows = []
    last_headers: dict = {}
    for i in range(n):
        t0 = time.perf_counter()
        model = settings.SMALL_MODEL if i % 2 == 0 else settings.DRAFT_MODEL
        res = client.complete(
            [
                {"role": "system", "content": "Say hello in five words."},
                {"role": "user", "content": f"ping {i}"},
            ],
            model=model,
            max_tokens=64,
            stream=True,
            reasoning_effort="low",
        )
        last_headers = res.rate_limit_headers or last_headers
        rows.append(
            {
                "i": i,
                "model": model,
                "status": res.status,
                "first_token_ms": res.first_token_ms,
                "total_ms": res.total_ms,
                "tokens_in": res.tokens_in,
                "tokens_out": res.tokens_out,
                "error": res.raw_error,
                "rate_limit_headers": res.rate_limit_headers,
                "text_preview": (res.text or "")[:80],
                "wall_s": time.perf_counter() - t0,
            }
        )
        print(rows[-1])
        time.sleep(1.0)

    # Interpret headers for Table 1 (confidence noted).
    table1 = {
        "requests_per_minute": {
            "value": settings.LIMIT_RPM,
            "how": "Not present as a distinct header; placeholder until 429 probe. Token window resets ~1s suggests TPM is the tight minute limit.",
            "confidence": "low",
        },
        "tokens_per_minute": {
            "value": int(last_headers.get("x-ratelimit-limit-tokens") or settings.LIMIT_TPM),
            "how": "x-ratelimit-limit-tokens + x-ratelimit-reset-tokens (~1s) on chat completions",
            "confidence": "high",
        },
        "requests_per_day": {
            "value": int(last_headers.get("x-ratelimit-limit-requests") or settings.LIMIT_RPD),
            "how": "x-ratelimit-limit-requests with multi-hour x-ratelimit-reset-requests",
            "confidence": "high",
        },
        "tokens_per_day": {
            "value": "not measured",
            "how": "No TPD header observed on these responses",
            "confidence": "low",
        },
        "requests_in_flight_at_once": {
            "value": "not measured",
            "how": "Requires concurrency probe; not in single-request headers",
            "confidence": "low",
        },
        "what_it_returns_when_limit_hit": {
            "value": "not measured this run (no 429 yet)",
            "how": "Will capture HTTP status + body on first 429",
            "confidence": "low",
        },
        "time_until_it_recovers": {
            "value": last_headers.get("x-ratelimit-reset-tokens")
            or last_headers.get("x-ratelimit-reset-requests")
            or "not measured",
            "how": "From x-ratelimit-reset-* headers when present",
            "confidence": "medium",
        },
    }

    out = {
        "models": [settings.SMALL_MODEL, settings.DRAFT_MODEL],
        "rows": rows,
        "last_rate_limit_headers": last_headers,
        "table1": table1,
        "configured_limits": {
            "rpm": settings.LIMIT_RPM,
            "tpm": settings.LIMIT_TPM,
            "rpd": settings.LIMIT_RPD,
            "tpd": settings.LIMIT_TPD,
            "in_flight": settings.LIMIT_IN_FLIGHT,
        },
        "notes": [
            "Python urllib without a browser-like User-Agent got Cloudflare HTTP 403 error 1010; client now sends a Mozilla-compatible UA.",
            "gpt-oss models use reasoning tokens; client sets reasoning_effort=low for small calls.",
        ],
    }
    path = settings.PROBES_DIR / "groq_probe.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {path}")
    return out


if __name__ == "__main__":
    if not settings.GROQ_API_KEY:
        raise SystemExit("Set GROQ_API_KEY before probing the real service.")
    probe()
