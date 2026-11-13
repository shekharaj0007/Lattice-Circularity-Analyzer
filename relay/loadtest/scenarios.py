"""Load shapes required by the brief (plus limit-edge cases)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    name: str
    # Prefer stand-in for anything that would burn free-tier day.
    default_source: str
    requests: int
    duration_s: float
    offered_per_min: float
    notes: str = ""


SCENARIOS: list[Scenario] = [
    Scenario(
        name="steady",
        default_source="stand-in",
        requests=30,
        duration_s=60.0,
        offered_per_min=30.0,
        notes="Even spacing",
    ),
    Scenario(
        name="burst",
        default_source="stand-in",
        requests=40,
        duration_s=10.0,
        offered_per_min=240.0,
        notes="Sudden spike",
    ),
    Scenario(
        name="sustained_overload",
        default_source="stand-in",
        requests=80,
        duration_s=40.0,
        offered_per_min=120.0,
        notes="Above calibrated RPM for a while",
    ),
    Scenario(
        name="per_minute_limit_halved",
        default_source="stand-in",
        requests=40,
        duration_s=30.0,
        offered_per_min=60.0,
        notes="Runner halves BudgetTracker.rpm / stand-in rpm",
    ),
    Scenario(
        name="daily_budget_exhausted",
        default_source="stand-in",
        requests=20,
        duration_s=20.0,
        offered_per_min=60.0,
        notes="Pre-seed RPD to exhausted before sending",
    ),
]

# Small real-service sample (budget carefully)
REAL_PROBE_SCENARIO = Scenario(
    name="real_modest_probe",
    default_source="real",
    requests=8,
    duration_s=60.0,
    offered_per_min=8.0,
    notes="Modest real requests for latency/limit learning only",
)
