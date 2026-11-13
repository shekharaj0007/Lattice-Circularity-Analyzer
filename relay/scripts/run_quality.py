"""Run ≥15 questions across ≥3 retrieval settings; grade and log CSV."""

from __future__ import annotations

import uuid

from relay.config import settings
from relay.loadtest.grade import apply_grades
from relay.loadtest.questions import QUESTIONS
from relay.loadtest.runner import append_results
from relay.pipeline.budget import BudgetTracker
from relay.pipeline.orchestrator import Orchestrator


def run(source: str = "stand-in") -> None:
    settings.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for setting in settings.RETRIEVAL_SETTINGS:
        print(f"=== retrieval {setting} ===")
        budget = BudgetTracker()
        orch = Orchestrator(budget=budget, source=source, retrieval_setting=setting)
        results = []
        for q in QUESTIONS:
            r = orch.handle(
                q.question,
                scenario=f"quality_{setting}",
                request_id=str(uuid.uuid4()),
            )
            results.append(r)
            print(q.qid, r.status.value, r.ladder_level, r.answer_text[:80].replace("\n", " "))
        apply_grades(QUESTIONS, results)
        append_results(settings.RESULTS_CSV, results)
        all_rows.extend(results)
    print(f"wrote {len(all_rows)} rows → {settings.RESULTS_CSV}")


if __name__ == "__main__":
    import sys

    src = "real" if "--real" in sys.argv else "stand-in"
    run(source=src)
