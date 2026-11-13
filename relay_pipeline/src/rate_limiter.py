"""Centralized rate limiting with token budget tracking."""
import time
from collections import deque
from typing import Optional, Dict
import threading
from datetime import datetime, timedelta


class TokenBudgetTracker:
    """Track token usage against daily budget."""
    
    def __init__(self, daily_token_limit: int, budget_threshold: float = 0.8):
        self.daily_token_limit = daily_token_limit
        self.budget_threshold = budget_threshold
        self.token_usage = []  # List of (timestamp, tokens) tuples
        self.lock = threading.Lock()
        self.refusal_count = 0
    
    def add_usage(self, tokens: int):
        """Record token usage."""
        with self.lock:
            now = time.time()
            self.token_usage.append((now, tokens))
            self._cleanup_old_usage()
    
    def get_daily_usage(self) -> int:
        """Get token usage in the last 24 hours."""
        with self.lock:
            self._cleanup_old_usage()
            return sum(tokens for _, tokens in self.token_usage)
    
    def can_proceed(self, estimated_tokens: int = 0) -> tuple[bool, str]:
        """Check if request can proceed given current budget."""
        current_usage = self.get_daily_usage()
        projected_usage = current_usage + estimated_tokens
        threshold_limit = self.daily_token_limit * self.budget_threshold
        
        if projected_usage > threshold_limit:
            with self.lock:
                self.refusal_count += 1
            return False, f"Budget limit reached: {current_usage}/{self.daily_token_limit} tokens used ({current_usage/self.daily_token_limit*100:.1f}%)"
        
        return True, f"Budget OK: {current_usage}/{self.daily_token_limit} tokens used"
    
    def get_stats(self) -> Dict:
        """Get budget statistics."""
        usage = self.get_daily_usage()
        return {
            "daily_usage": usage,
            "daily_limit": self.daily_token_limit,
            "usage_percent": usage / self.daily_token_limit * 100,
            "threshold": self.budget_threshold * 100,
            "refusal_count": self.refusal_count,
            "remaining": self.daily_token_limit - usage
        }
    
    def _cleanup_old_usage(self):
        """Remove usage data older than 24 hours."""
        cutoff = time.time() - 86400  # 24 hours
        self.token_usage = [(ts, tokens) for ts, tokens in self.token_usage if ts > cutoff]


class RateLimiter:
    """Rate limiter with RPM and TPM tracking."""
    
    def __init__(self, rpm_limit: int, tpm_limit: int):
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.request_times = deque()  # Request timestamps
        self.token_usage = deque()   # (timestamp, tokens) tuples
        self.lock = threading.Lock()
        
        # Metrics
        self.total_requests = 0
        self.total_tokens = 0
        self.total_wait_time = 0.0
        self.wait_events = 0
    
    def acquire(self, estimated_tokens: int = 100) -> float:
        """
        Acquire permission to make a request.
        Returns wait time in seconds.
        """
        with self.lock:
            now = time.time()
            
            # Clean up old entries
            self._cleanup_old_entries(now)
            
            # Check RPM limit
            rpm_wait = self._check_rpm_limit(now)
            
            # Check TPM limit
            tpm_wait = self._check_tpm_limit(now, estimated_tokens)
            
            # Wait for the longer duration
            wait_time = max(rpm_wait, tpm_wait)
            
            if wait_time > 0:
                self.wait_events += 1
                self.total_wait_time += wait_time
            
            # Record this request
            self.request_times.append(now + wait_time)
            self.token_usage.append((now + wait_time, estimated_tokens))
            self.total_requests += 1
            self.total_tokens += estimated_tokens
            
            return wait_time
    
    def record_actual_tokens(self, estimated: int, actual: int):
        """Update token count with actual usage."""
        with self.lock:
            # Find and update the last entry
            if self.token_usage:
                ts, _ = self.token_usage[-1]
                self.token_usage[-1] = (ts, actual)
                self.total_tokens += (actual - estimated)
    
    def _check_rpm_limit(self, now: float) -> float:
        """Check if we're within RPM limit."""
        minute_ago = now - 60
        recent_requests = sum(1 for ts in self.request_times if ts > minute_ago)
        
        if recent_requests >= self.rpm_limit:
            # Calculate wait time until oldest request expires
            oldest = min(ts for ts in self.request_times if ts > minute_ago)
            return max(0, (oldest + 60) - now)
        
        return 0
    
    def _check_tpm_limit(self, now: float, tokens: int) -> float:
        """Check if we're within TPM limit."""
        minute_ago = now - 60
        recent_tokens = sum(tok for ts, tok in self.token_usage if ts > minute_ago)
        
        if recent_tokens + tokens > self.tpm_limit:
            # Calculate wait time until we have enough budget
            if self.token_usage:
                oldest_ts = min(ts for ts, tok in self.token_usage if ts > minute_ago)
                return max(0, (oldest_ts + 60) - now)
        
        return 0
    
    def _cleanup_old_entries(self, now: float):
        """Remove entries older than 1 minute."""
        minute_ago = now - 60
        
        while self.request_times and self.request_times[0] < minute_ago:
            self.request_times.popleft()
        
        while self.token_usage and self.token_usage[0][0] < minute_ago:
            self.token_usage.popleft()
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        with self.lock:
            now = time.time()
            self._cleanup_old_entries(now)
            
            minute_ago = now - 60
            recent_requests = sum(1 for ts in self.request_times if ts > minute_ago)
            recent_tokens = sum(tok for ts, tok in self.token_usage if ts > minute_ago)
            
            return {
                "rpm_current": recent_requests,
                "rpm_limit": self.rpm_limit,
                "tpm_current": recent_tokens,
                "tpm_limit": self.tpm_limit,
                "total_requests": self.total_requests,
                "total_tokens": self.total_tokens,
                "wait_events": self.wait_events,
                "total_wait_time": self.total_wait_time,
                "avg_wait_time": self.total_wait_time / self.wait_events if self.wait_events > 0 else 0
            }


if __name__ == "__main__":
    # Test rate limiter
    limiter = RateLimiter(rpm_limit=5, tpm_limit=1000)
    budget = TokenBudgetTracker(daily_token_limit=10000)
    
    print("Testing rate limiter...")
    for i in range(10):
        wait = limiter.acquire(estimated_tokens=100)
        can_proceed, msg = budget.can_proceed(100)
        
        print(f"Request {i}: wait={wait:.2f}s, {msg}")
        
        if wait > 0:
            time.sleep(wait)
        
        if can_proceed:
            budget.add_usage(100)
        else:
            print(f"  REFUSED")
    
    print("\nRate limiter stats:", limiter.get_stats())
    print("Budget stats:", budget.get_stats())
