"""Fit stand-in latency/limits from probe file (or settings defaults)."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from relay.config import settings


def calibrate(probe_path: Path | None = None) -> dict:
    settings.PROBES_DIR.mkdir(parents=True, exist_ok=True)
    probe_path = probe_path or (settings.PROBES_DIR / "groq_probe.json")
    ttft = []
    total = []
    if probe_path.exists():
        data = json.loads(probe_path.read_text(encoding="utf-8"))
        for r in data.get("rows") or []:
            if r.get("status") == "ok" and r.get("first_token_ms") is not None:
                ttft.append(float(r["first_token_ms"]))
            if r.get("status") == "ok" and r.get("total_ms") is not None:
                total.append(float(r["total_ms"]))

    def p50(xs, default):
        return statistics.median(xs) if xs else default

    def p95(xs, default):
        if not xs:
            return default
        xs = sorted(xs)
        idx = min(len(xs) - 1, int(round(0.95 * (len(xs) - 1))))
        return xs[idx]

    calib = {
        "ttft_p50_ms": p50(ttft, 180.0),
        "ttft_p95_ms": p95(ttft, 600.0),
        "total_p50_ms": p50(total, 900.0),
        "total_p95_ms": p95(total, 2500.0),
        "rpm": settings.LIMIT_RPM,
        "tpm": settings.LIMIT_TPM,
        "rpd": settings.LIMIT_RPD,
        "fail_rate": 0.01,
        "load_slowdown_per_inflight": 0.08,
        "least_like_real": [
            "multi-tenant scheduler / noisy neighbors",
            "exact 429 error schema and recovery timers",
            "true tokenizer-based TPM accounting",
        ],
        "source_probe": str(probe_path) if probe_path.exists() else "defaults",
    }
    out = settings.PROBES_DIR / "standin_calib.json"
    out.write_text(json.dumps(calib, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return calib


if __name__ == "__main__":
    calibrate()
