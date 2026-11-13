"""Centralized token channel: single queue + budget."""

from __future__ import annotations

from relay.pipeline.token_channel import TokenChannel, estimate_messages_tokens


def test_estimate_positive() -> None:
    n = estimate_messages_tokens([{"role": "user", "content": "hello world"}], 64)
    assert n >= 64


def test_daily_budget_blocks() -> None:
    ch = TokenChannel(tpm=10_000, tpd=100, rpm=100, rpd=1000)
    d1 = ch.acquire(80)
    assert d1.allowed
    ch.release(d1.reserved_tokens, 80)
    d2 = ch.acquire(50)
    assert not d2.allowed
    assert d2.reason == "daily_token_budget"


def test_tpm_queues_then_allows() -> None:
    ch = TokenChannel(tpm=100, tpd=100_000, rpm=100, rpd=1000, tpm_window_s=0.2)
    d1 = ch.acquire(90)
    assert d1.allowed
    ch.release(d1.reserved_tokens, 90)
    # Immediate second reserve should fail TPM until window slides
    d2 = ch.acquire(90, wait_s=0.0)
    assert not d2.allowed
    assert "tokens_per_minute" in d2.reason or d2.reason.startswith("queue_timeout")


def test_ladder_after_80_percent() -> None:
    ch = TokenChannel(tpm=1000, tpd=1000, rpm=1000, rpd=1000)
    # Push day tokens to 80%
    d = ch.acquire(800)
    assert d.allowed
    ch.release(d.reserved_tokens, 800)
    assert ch.ladder_level() >= 1


if __name__ == "__main__":
    test_estimate_positive()
    test_daily_budget_blocks()
    test_tpm_queues_then_allows()
    test_ladder_after_80_percent()
    print("ok")
