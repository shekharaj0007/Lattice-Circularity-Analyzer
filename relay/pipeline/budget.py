"""Budget tracking and degrade-ladder selection.

Low-consumption mode engages ONLY after BUDGET_DEGRADE_THRESHOLD (default 80%)
of any tracked limit (RPM / TPM / RPD / TPD) is used. Below that: ladder 0.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Tuple

from relay.config import settings
from relay.pipeline.types import LadderLevel


@dataclass
class BudgetSnapshot:
    rpm_used: float
    tpm_used: float
    rpd_used: float
    tpd_used: float
    in_flight: int
    usage_ratio: float  # max fraction across RPM/TPM/RPD/TPD
    ladder_level: int


class BudgetTracker:
    """Thread-safe sliding-window + daily counters."""

    def __init__(
        self,
        rpm: int = settings.LIMIT_RPM,
        tpm: int = settings.LIMIT_TPM,
        rpd: int = settings.LIMIT_RPD,
        tpd: int = settings.LIMIT_TPD,
        in_flight_limit: int = settings.LIMIT_IN_FLIGHT,
        degrade_threshold: float = settings.BUDGET_DEGRADE_THRESHOLD,
    ) -> None:
        self.rpm = rpm
        self.tpm = tpm
        self.rpd = rpd
        self.tpd = tpd
        self.in_flight_limit = in_flight_limit
        self.degrade_threshold = degrade_threshold

        self._lock = threading.Lock()
        # (timestamp, tokens) for request-per-minute window (60s)
        self._minute_events: Deque[Tuple[float, int]] = deque()
        # Separate short token window: Groq x-ratelimit-reset-tokens is ~1s, not 60s.
        self.tpm_window_s = 2.0
        self._token_events: Deque[Tuple[float, int]] = deque()
        # day key YYYY-MM-DD -> (requests, tokens)
        self._day_key = self._today()
        self._day_requests = 0
        self._day_tokens = 0
        self._in_flight = 0
        self.peak_queue_length = 0

    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def _prune_minute(self, now: float) -> None:
        cutoff = now - 60.0
        while self._minute_events and self._minute_events[0][0] < cutoff:
            self._minute_events.popleft()

    def _prune_tokens(self, now: float) -> None:
        cutoff = now - self.tpm_window_s
        while self._token_events and self._token_events[0][0] < cutoff:
            self._token_events.popleft()

    def _roll_day(self) -> None:
        key = self._today()
        if key != self._day_key:
            self._day_key = key
            self._day_requests = 0
            self._day_tokens = 0

    def _usage_ratio_unlocked(self, now: float) -> float:
        self._prune_minute(now)
        self._prune_tokens(now)
        self._roll_day()
        rpm_used = len(self._minute_events) / max(1, self.rpm)
        tpm_used = sum(t for _, t in self._token_events) / max(1, self.tpm)
        rpd_used = self._day_requests / max(1, self.rpd)
        tpd_used = self._day_tokens / max(1, self.tpd)
        return max(rpm_used, tpm_used, rpd_used, tpd_used)

    def ladder_level_from_usage(self, usage_ratio: float) -> int:
        """Full quality until 80%; then map remaining band onto levels 1..5.

        Bands (default threshold 0.80):
          [0.80, 0.84) → 1 skip rewrite
          [0.84, 0.88) → 2 skip LLM verify
          [0.88, 0.92) → 3 shrink retrieval
          [0.92, 0.96) → 4 extractive
          [0.96, ∞)    → 5 try later
        """
        thr = self.degrade_threshold
        if usage_ratio < thr:
            return int(LadderLevel.FULL)
        if usage_ratio >= 1.0:
            return int(LadderLevel.TRY_LATER)
        span = max(1e-9, 1.0 - thr)
        # Use floor with tiny epsilon so boundary points (0.84, 0.88, …) land in the higher band.
        band = (usage_ratio - thr) / span
        idx = min(4, int(band * 5 + 1e-12))
        return settings.LADDER_LEVELS_AFTER_THRESHOLD[idx]

    def snapshot(self) -> BudgetSnapshot:
        with self._lock:
            now = time.time()
            usage = self._usage_ratio_unlocked(now)
            rpm_u = len(self._minute_events) / max(1, self.rpm)
            tpm_u = sum(t for _, t in self._token_events) / max(1, self.tpm)
            rpd_u = self._day_requests / max(1, self.rpd)
            tpd_u = self._day_tokens / max(1, self.tpd)
            return BudgetSnapshot(
                rpm_used=rpm_u,
                tpm_used=tpm_u,
                rpd_used=rpd_u,
                tpd_used=tpd_u,
                in_flight=self._in_flight,
                usage_ratio=usage,
                ladder_level=self.ladder_level_from_usage(usage),
            )

    def current_ladder(self) -> int:
        return self.snapshot().ladder_level

    def try_enter(self) -> bool:
        """Reserve an in-flight slot. False if at concurrency cap."""
        with self._lock:
            if self._in_flight >= self.in_flight_limit:
                return False
            self._in_flight += 1
            return True

    def leave(self) -> None:
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)

    def record_queue_depth(self, depth: int) -> None:
        with self._lock:
            if depth > self.peak_queue_length:
                self.peak_queue_length = depth

    def record_success(self, tokens: int) -> None:
        with self._lock:
            now = time.time()
            self._prune_minute(now)
            self._prune_tokens(now)
            self._roll_day()
            toks = max(0, tokens)
            self._minute_events.append((now, toks))
            self._token_events.append((now, toks))
            self._day_requests += 1
            self._day_tokens += toks

    def record_rate_limit_hit(self) -> None:
        """Count a failed attempt against RPM/RPD so we climb the ladder."""
        with self._lock:
            now = time.time()
            self._prune_minute(now)
            self._prune_tokens(now)
            self._roll_day()
            self._minute_events.append((now, 0))
            self._day_requests += 1

    def force_usage_ratio(self, ratio: float) -> None:
        """Test helper: synthesize counters so usage ≈ ratio (RPM axis)."""
        with self._lock:
            now = time.time()
            self._minute_events.clear()
            self._token_events.clear()
            n = int(round(ratio * self.rpm))
            for _ in range(max(0, n)):
                self._minute_events.append((now, 0))

    def exhausted_daily(self) -> bool:
        snap = self.snapshot()
        return snap.rpd_used >= 1.0 or snap.tpd_used >= 1.0
