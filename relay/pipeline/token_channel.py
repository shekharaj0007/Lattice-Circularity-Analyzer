"""Centralized token channel: every model call queues through one gate.

Why: concurrent classify/draft/rewrite/verify used to hit Groq independently and
blow TPM/TPD before the pipeline-level admission controller noticed. Measured
reality on gpt-oss-120b: TPD=200000, TPM≈8000 with ~1s reset.

Policy:
- Single process-wide channel (one lock + condition).
- Reserve estimated tokens before the HTTP call; settle with actual usage after.
- Low-consumption / degrade ladder still owned by BudgetTracker (80% gate).
- Channel refuses (does not guess) when daily token budget cannot cover the reserve.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Optional, Tuple, TypeVar

from relay.config import settings
from relay.pipeline.budget import BudgetTracker

T = TypeVar("T")


@dataclass
class ChannelDecision:
    allowed: bool
    waited_ms: float
    reason: str
    queue_depth: int
    reserved_tokens: int = 0


class TokenChannel:
    """Single-file queue + rolling token budgets for all provider calls."""

    _instance: Optional["TokenChannel"] = None
    _instance_lock = threading.Lock()

    def __init__(
        self,
        *,
        tpm: int = settings.LIMIT_TPM,
        tpd: int = settings.LIMIT_TPD,
        rpm: int = settings.LIMIT_RPM,
        rpd: int = settings.LIMIT_RPD,
        tpm_window_s: float = 2.0,
        max_queue_wait_s: float = settings.QUEUE_WAIT_S,
        budget: Optional[BudgetTracker] = None,
    ) -> None:
        self.tpm = tpm
        self.tpd = tpd
        self.rpm = rpm
        self.rpd = rpd
        self.tpm_window_s = tpm_window_s
        self.max_queue_wait_s = max_queue_wait_s
        # Shared budget drives the 80% degrade ladder for callers that ask.
        self.budget = budget or BudgetTracker(
            rpm=rpm, tpm=tpm, rpd=rpd, tpd=tpd
        )

        self._cv = threading.Condition()
        self._waiting = 0
        self.peak_queue_length = 0

        self._token_events: Deque[Tuple[float, int]] = deque()  # short TPM window
        self._minute_events: Deque[Tuple[float, int]] = deque()  # RPM
        self._day_key = time.strftime("%Y-%m-%d", time.gmtime())
        self._day_tokens = 0
        self._day_requests = 0
        self._reserved = 0  # tokens reserved by in-flight calls

    @classmethod
    def shared(cls) -> "TokenChannel":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_shared(cls) -> "TokenChannel":
        """Test/load helper: replace the process singleton."""
        with cls._instance_lock:
            cls._instance = cls()
            return cls._instance

    def _roll_day(self, now: float | None = None) -> None:
        key = time.strftime("%Y-%m-%d", time.gmtime(now or time.time()))
        if key != self._day_key:
            self._day_key = key
            self._day_tokens = 0
            self._day_requests = 0

    def _prune(self, now: float) -> None:
        tpm_cut = now - self.tpm_window_s
        while self._token_events and self._token_events[0][0] < tpm_cut:
            self._token_events.popleft()
        rpm_cut = now - 60.0
        while self._minute_events and self._minute_events[0][0] < rpm_cut:
            self._minute_events.popleft()

    def _can_reserve(self, need: int, now: float) -> tuple[bool, str]:
        self._roll_day(now)
        self._prune(now)
        if self._day_tokens + self._reserved + need > self.tpd:
            return False, "daily_token_budget"
        used_tpm = sum(t for _, t in self._token_events) + self._reserved
        if used_tpm + need > self.tpm:
            return False, "tokens_per_minute"
        if len(self._minute_events) >= self.rpm:
            return False, "requests_per_minute"
        if self._day_requests >= self.rpd:
            return False, "requests_per_day"
        return True, "ok"

    def acquire(
        self,
        estimated_tokens: int,
        *,
        wait_s: Optional[float] = None,
    ) -> ChannelDecision:
        need = max(1, int(estimated_tokens))
        wait_s = self.max_queue_wait_s if wait_s is None else wait_s
        start = time.time()

        with self._cv:
            # Hard daily refuse: do not queue forever when TPD is gone.
            now = time.time()
            self._roll_day(now)
            if self._day_tokens + self._reserved + need > self.tpd:
                return ChannelDecision(
                    allowed=False,
                    waited_ms=0.0,
                    reason="daily_token_budget",
                    queue_depth=self._waiting,
                )

            self._waiting += 1
            if self._waiting > self.peak_queue_length:
                self.peak_queue_length = self._waiting
            self.budget.record_queue_depth(self.peak_queue_length)
            try:
                deadline = start + wait_s
                while True:
                    now = time.time()
                    ok, reason = self._can_reserve(need, now)
                    if ok:
                        self._reserved += need
                        waited = (now - start) * 1000.0
                        return ChannelDecision(
                            allowed=True,
                            waited_ms=waited,
                            reason="ok",
                            queue_depth=self._waiting - 1,
                            reserved_tokens=need,
                        )
                    # Daily / RPD: fail fast (queueing cannot help today).
                    if reason in ("daily_token_budget", "requests_per_day"):
                        waited = (now - start) * 1000.0
                        return ChannelDecision(
                            allowed=False,
                            waited_ms=waited,
                            reason=reason,
                            queue_depth=self._waiting - 1,
                        )
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        waited = (time.time() - start) * 1000.0
                        return ChannelDecision(
                            allowed=False,
                            waited_ms=waited,
                            reason=f"queue_timeout:{reason}",
                            queue_depth=self._waiting - 1,
                        )
                    self._cv.wait(timeout=min(0.05, remaining))
            finally:
                self._waiting -= 1

    def release(self, reserved_tokens: int, actual_tokens: int) -> None:
        actual = max(0, int(actual_tokens))
        reserved = max(0, int(reserved_tokens))
        with self._cv:
            now = time.time()
            self._roll_day(now)
            self._prune(now)
            self._reserved = max(0, self._reserved - reserved)
            self._token_events.append((now, actual))
            self._minute_events.append((now, actual))
            self._day_tokens += actual
            self._day_requests += 1
            # Keep pipeline BudgetTracker in sync for the 80% ladder.
            self.budget.record_success(actual)
            self._cv.notify_all()

    def release_failed(self, reserved_tokens: int) -> None:
        """Call was not charged (or 429): free reservation; optionally count RPM hit."""
        reserved = max(0, int(reserved_tokens))
        with self._cv:
            self._reserved = max(0, self._reserved - reserved)
            self._cv.notify_all()

    def run(
        self,
        estimated_tokens: int,
        fn: Callable[[], T],
        *,
        actual_tokens_fn: Callable[[T], int],
        wait_s: Optional[float] = None,
        on_denied: Optional[Callable[[ChannelDecision], T]] = None,
    ) -> T:
        decision = self.acquire(estimated_tokens, wait_s=wait_s)
        if not decision.allowed:
            if on_denied is not None:
                return on_denied(decision)
            raise RuntimeError(f"token_channel_denied:{decision.reason}")
        try:
            result = fn()
            self.release(decision.reserved_tokens, actual_tokens_fn(result))
            return result
        except Exception:
            self.release_failed(decision.reserved_tokens)
            raise

    def usage_ratio(self) -> float:
        with self._cv:
            now = time.time()
            self._roll_day(now)
            self._prune(now)
            tpm_u = (sum(t for _, t in self._token_events) + self._reserved) / max(1, self.tpm)
            tpd_u = (self._day_tokens + self._reserved) / max(1, self.tpd)
            rpm_u = len(self._minute_events) / max(1, self.rpm)
            rpd_u = self._day_requests / max(1, self.rpd)
            return max(tpm_u, tpd_u, rpm_u, rpd_u)

    def ladder_level(self) -> int:
        return self.budget.ladder_level_from_usage(self.usage_ratio())


def estimate_messages_tokens(messages: list[dict], max_tokens: int) -> int:
    """Cheap estimate: words≈tokens for reservation; prefer overshoot to undershoot."""
    words = 0
    for m in messages:
        words += len(str(m.get("content") or "").split())
    # prompt + expected completion (+ reasoning headroom for gpt-oss)
    return max(32, int(words * 1.3) + int(max_tokens))
