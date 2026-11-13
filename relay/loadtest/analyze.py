"""Compute Tables 1/2a/2b/3-style summaries from results.csv."""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from relay.config import settings


def _f(x: Any) -> Optional[float]:
    if x is None or x == "":
        return None
    return float(x)


def percentile(vals: list[float], p: float) -> Optional[float]:
    if not vals:
        return None
    vals = sorted(vals)
    if len(vals) == 1:
        return vals[0]
    k = (len(vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    if f == c:
        return vals[f]
    return vals[f] + (vals[c] - vals[f]) * (k - f)


def load_rows(path: Path | None = None) -> list[dict[str, str]]:
    path = path or settings.RESULTS_CSV
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarize_scenario(rows: list[dict[str, str]]) -> dict[str, Any]:
    n = len(rows)
    ft = [v for v in (_f(r["first_token_ms"]) for r in rows) if v is not None]
    tot = [v for v in (_f(r["total_ms"]) for r in rows) if v is not None]
    ok = sum(1 for r in rows if r["status"] == "ok")
    rl = sum(1 for r in rows if r["status"] == "rate_limited")
    to = sum(1 for r in rows if r["status"] in ("timeout",))
    retries = [float(r["retries"] or 0) for r in rows]
    tokens = [float(r["tokens_in"] or 0) + float(r["tokens_out"] or 0) for r in rows]

    def pct(num: int) -> float:
        return round(100.0 * num / n, 1) if n else 0.0

    return {
        "requests": n,
        "source": rows[0]["source"] if rows else "",
        "first_token_p50": percentile(ft, 50),
        "first_token_p95": percentile(ft, 95),
        "first_token_p99": percentile(ft, 99),
        "total_p50": percentile(tot, 50),
        "total_p95": percentile(tot, 95),
        "total_p99": percentile(tot, 99),
        "succeeded_pct": pct(ok),
        "rate_limited_pct": pct(rl),
        "timed_out_or_given_up_pct": pct(to),
        "retries_per_request": round(statistics.mean(retries), 3) if retries else 0.0,
        "tokens_per_answer": round(statistics.mean(tokens), 1) if tokens else 0.0,
    }


def table2(path: Path | None = None) -> dict[str, dict[str, Any]]:
    rows = load_rows(path)
    by = defaultdict(list)
    for r in rows:
        by[r["scenario"]].append(r)
    return {k: summarize_scenario(v) for k, v in sorted(by.items())}


def table3(path: Path | None = None) -> dict[str, dict[str, Any]]:
    rows = load_rows(path)
    by = defaultdict(list)
    for r in rows:
        by[r["retrieval_setting"]].append(r)
    out = {}
    for setting, rs in sorted(by.items()):
        n = len(rs)
        grades = [r["answer_grade"] for r in rs]
        def gp(name: str) -> float:
            return round(100.0 * grades.count(name) / n, 1) if n else 0.0
        s = summarize_scenario(rs)
        out[setting] = {
            "questions": n,
            "correct_and_cited_pct": gp("correct"),
            "wrong_pct": gp("wrong"),
            "correctly_refused_pct": gp("refused_correctly"),
            "tokens_per_answer": s["tokens_per_answer"],
            "first_token_p50": s["first_token_p50"],
            "first_token_p95": s["first_token_p95"],
            "total_p50": s["total_p50"],
            "total_p95": s["total_p95"],
        }
    return out


def main() -> None:
    print("Table 2a/2b by scenario:")
    for name, s in table2().items():
        print(name, s)
    print("\nTable 3 by retrieval_setting:")
    for name, s in table3().items():
        print(name, s)


if __name__ == "__main__":
    main()
