"""Budget ladder: full quality until 80%, then levels 1..5."""

from __future__ import annotations

from relay.pipeline.budget import BudgetTracker
from relay.pipeline.types import LadderLevel


def test_below_80_is_full() -> None:
    b = BudgetTracker(rpm=100, tpm=1_000_000, rpd=1_000_000, tpd=1_000_000)
    b.force_usage_ratio(0.79)
    assert b.current_ladder() == LadderLevel.FULL


def test_at_80_starts_low_consumption() -> None:
    b = BudgetTracker(rpm=100, tpm=1_000_000, rpd=1_000_000, tpd=1_000_000)
    b.force_usage_ratio(0.80)
    assert b.current_ladder() == LadderLevel.SKIP_REWRITE


def test_bands_map_to_ladder() -> None:
    b = BudgetTracker(rpm=100, tpm=1_000_000, rpd=1_000_000, tpd=1_000_000)
    # 80–84% → 1, 84–88% → 2, ... 96–100% → 5
    cases = [
        (0.80, 1),
        (0.84, 2),
        (0.88, 3),
        (0.92, 4),
        (0.96, 5),
        (1.00, 5),
        (1.10, 5),
    ]
    for ratio, expected in cases:
        b.force_usage_ratio(min(ratio, 0.99) if ratio < 1 else ratio)
        if ratio >= 1.0:
            # force_usage_ratio caps via rpm count; set day exhausted style
            b.rpm = 100
            b.force_usage_ratio(1.0)
            # exactly at 1.0 via ladder_level_from_usage
            assert b.ladder_level_from_usage(ratio) == expected
        else:
            assert b.ladder_level_from_usage(ratio) == expected, ratio


def test_threshold_configurable() -> None:
    b = BudgetTracker(
        rpm=100,
        tpm=1_000_000,
        rpd=1_000_000,
        tpd=1_000_000,
        degrade_threshold=0.80,
    )
    assert b.ladder_level_from_usage(0.799) == 0
    assert b.ladder_level_from_usage(0.80) >= 1


if __name__ == "__main__":
    test_below_80_is_full()
    test_at_80_starts_low_consumption()
    test_bands_map_to_ladder()
    test_threshold_configurable()
    print("ok")
