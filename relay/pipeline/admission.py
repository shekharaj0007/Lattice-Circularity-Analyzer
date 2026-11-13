"""Admission control: short queue, then try-later — never guess to stay fast."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

from relay.config import settings
from relay.pipeline.budget import BudgetTracker


@dataclass
class AdmissionDecision:
    admitted: bool
    waited_ms: float
    reason: str
    queue_depth: int


class AdmissionController:
    def __init__(self, budget: BudgetTracker) -> None:
        self.budget = budget
        self._cv = threading.Condition()
        self._waiting = 0

    def acquire(self, give_up_s: Optional[float] = None) -> AdmissionDecision:
        give_up_s = settings.QUEUE_WAIT_S if give_up_s is None else give_up_s
        start = time.time()

        # Daily budget gone → do not queue for generative work.
        if self.budget.exhausted_daily():
            return AdmissionDecision(
                admitted=False,
                waited_ms=0.0,
                reason="daily_budget_exhausted",
                queue_depth=self._waiting,
            )

        with self._cv:
            self._waiting += 1
            self.budget.record_queue_depth(self._waiting)
            try:
                deadline = start + give_up_s
                while True:
                    if self.budget.try_enter():
                        waited = (time.time() - start) * 1000.0
                        return AdmissionDecision(
                            admitted=True,
                            waited_ms=waited,
                            reason="ok",
                            queue_depth=self._waiting - 1,
                        )
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        waited = (time.time() - start) * 1000.0
                        return AdmissionDecision(
                            admitted=False,
                            waited_ms=waited,
                            reason="queue_timeout",
                            queue_depth=self._waiting - 1,
                        )
                    self._cv.wait(timeout=min(0.05, remaining))
            finally:
                self._waiting -= 1

    def release(self) -> None:
        self.budget.leave()
        with self._cv:
            self._cv.notify_all()
