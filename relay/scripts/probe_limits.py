"""Modest real Groq probes to learn latency + limit behavior (Table 1).

Spend carefully: this shares the free-tier daily budget.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from relay.config import settings
from relay.models.groq_client import GroqClient


def probe(n: int = 6) -> dict:
    settings.PROBES_DIR.mkdir(parents=True, exist_ok=True)
    client = GroqClient()
    rows = []
    for i in range(n):
        t0 = time.perf_counter()
        res = client.complete(
            [
                {"role": "system", "content": "Say hello in five words."},
                {"role": "user", "content": f"ping {i}"},
            ],
            model=settings.SMALL_MODEL,
            max_tokens=32,
            stream=True,
        )
        rows.append(
            {
                "i": i,
                "status": res.status,
                "first_token_ms": res.first_token_ms,
                "total_ms": res.total_ms,
                "tokens_in": res.tokens_in,
                "tokens_out": res.tokens_out,
                "error": res.raw_error,
                "wall_s": time.perf_counter() - t0,
            }
        )
        print(rows[-1])
        time.sleep(1.0)
    out = {
        "model": settings.SMALL_MODEL,
        "rows": rows,
        "configured_limits": {
            "rpm": settings.LIMIT_RPM,
            "tpm": settings.LIMIT_TPM,
            "rpd": settings.LIMIT_RPD,
            "tpd": settings.LIMIT_TPD,
            "in_flight": settings.LIMIT_IN_FLIGHT,
            "note": "Replace with measured values + error bodies when limits are hit.",
        },
    }
    path = settings.PROBES_DIR / "groq_probe.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {path}")
    return out


if __name__ == "__main__":
    if not settings.GROQ_API_KEY:
        raise SystemExit("Set GROQ_API_KEY before probing the real service.")
    probe()
