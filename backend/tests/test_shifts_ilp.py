"""
Tests for the ILP optimal shift optimiser (Phase 2).

Key properties:
  - FULL coverage (no interval short → 0 red, 100% green) when feasible.
  - OPTIMAL: uses <= the greedy result for the same problem (provably no worse).
"""

import math
from engine import (
    compound_shrinkage, gross_hc, agents_for_sl,
    generate_combinations, distribute_volume_to_intervals, optimise_shifts,
)
from engine.shifts_ilp import optimise_shifts_ilp

SHRINK = compound_shrinkage(8, 5, 3)["total_shrinkage_pct"]
CHRISTMAS_VOICE = {
    "Y1": {"baseline": 8500, "actual": 3600},
    "Y2": {"baseline": 9200, "actual": 5100},
    "Y3": {"baseline": 9800, "actual": 5600},
}
SHIFTS = [
    {"name": "Early", "start": "07:00", "end": "15:00"},
    {"name": "Mid",   "start": "09:00", "end": "17:00"},
    {"name": "Late",  "start": "11:00", "end": "19:00"},
]


def _rows():
    sunday = 1300   # fixed daily volume (independent of the forecast model)
    ivs = distribute_volume_to_intervals(sunday, "09:00", "17:00", 30)
    return [
        {"interval": i + 1, "start": iv["start"],
         "net_hc": math.ceil(gross_hc(agents_for_sl(iv["calls_per_hour"], 360, 80, 20), SHRINK))}
        for i, iv in enumerate(ivs)
    ]


def test_ilp_full_coverage():
    res = optimise_shifts_ilp(_rows(), SHIFTS, "09:00", "17:00", max_agents=200)
    assert res["optimal"] is True
    assert res["intervals_at_risk"] == 0          # no slot short
    assert res["coverage_pct"] == 100.0


def test_ilp_no_worse_than_greedy():
    rows = _rows()
    greedy = optimise_shifts(rows, SHIFTS, 200, "09:00", "17:00")
    ilp = optimise_shifts_ilp(rows, SHIFTS, "09:00", "17:00", max_agents=200)
    # ILP is provably optimal → never uses more agents than greedy for full coverage
    assert ilp["total_agents_used"] <= greedy["total_agents_used"]
