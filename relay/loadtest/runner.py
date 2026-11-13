"""Fire scenarios and append required results.csv rows."""

from __future__ import annotations

import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, Optional

from relay.config import settings
from relay.loadtest.questions import QUESTIONS
from relay.loadtest.scenarios import SCENARIOS, Scenario
from relay.pipeline.budget import BudgetTracker
from relay.pipeline.orchestrator import Orchestrator
from relay.pipeline.types import PipelineResult

CSV_COLUMNS = [
    "request_id",
    "scenario",
    "source",
    "start_time",
    "first_token_ms",
    "total_ms",
    "status",
    "retries",
    "tokens_in",
    "tokens_out",
    "retrieval_setting",
    "answer_grade",
]


def ensure_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_COLUMNS).writeheader()


def append_results(path: Path, rows: Iterable[PipelineResult]) -> None:
    ensure_csv(path)
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        for r in rows:
            w.writerow(r.to_csv_row())


def _prepare_budget(scenario: Scenario) -> BudgetTracker:
    budget = BudgetTracker()
    if scenario.name == "per_minute_limit_halved":
        budget.rpm = max(1, budget.rpm // 2)
    if scenario.name == "daily_budget_exhausted":
        budget._day_requests = budget.rpd  # noqa: SLF001 — intentional test seed
        budget._day_tokens = budget.tpd  # noqa: SLF001
    return budget


def run_scenario(
    scenario: Scenario,
    *,
    source: Optional[str] = None,
    retrieval_setting: Optional[str] = None,
    out_csv: Optional[Path] = None,
    max_workers: int = 8,
) -> list[PipelineResult]:
    source = source or scenario.default_source
    out_csv = out_csv or settings.RESULTS_CSV
    budget = _prepare_budget(scenario)
    orch = Orchestrator(
        budget=budget,
        source=source,
        retrieval_setting=retrieval_setting or settings.DEFAULT_RETRIEVAL_SETTING,
    )

    questions = [QUESTIONS[i % len(QUESTIONS)].question for i in range(scenario.requests)]
    interval = scenario.duration_s / max(1, scenario.requests)

    results: list[PipelineResult] = []
    start = time.perf_counter()

    def one(i: int, q: str) -> PipelineResult:
        # pace offered rate
        target = start + i * interval
        delay = target - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        return orch.handle(q, scenario=scenario.name)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = [pool.submit(one, i, q) for i, q in enumerate(questions)]
        for fut in as_completed(futs):
            results.append(fut.result())

    append_results(out_csv, results)
    return results


def run_all_standin(out_csv: Optional[Path] = None) -> None:
    for sc in SCENARIOS:
        print(f"=== {sc.name} ({sc.default_source}) ===")
        rows = run_scenario(sc, out_csv=out_csv)
        ok = sum(1 for r in rows if r.status.value == "ok")
        print(f"done {len(rows)} requests, ok={ok}")


if __name__ == "__main__":
    run_all_standin()
