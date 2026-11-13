"""Run load scenarios (stand-in by default)."""

from __future__ import annotations

import argparse

from relay.loadtest.runner import run_all_standin, run_scenario
from relay.loadtest.scenarios import SCENARIOS, REAL_PROBE_SCENARIO


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", default="all")
    p.add_argument("--source", default=None)
    p.add_argument("--real-probe", action="store_true")
    args = p.parse_args()

    if args.real_probe:
        rows = run_scenario(REAL_PROBE_SCENARIO, source="real")
        print(f"real probe done: {len(rows)}")
        return

    if args.scenario == "all":
        run_all_standin()
        return

    sc = next(s for s in SCENARIOS if s.name == args.scenario)
    rows = run_scenario(sc, source=args.source)
    print(f"done {sc.name}: {len(rows)}")


if __name__ == "__main__":
    main()
