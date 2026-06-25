"""
Golden + unit tests for the greedy shift optimiser.

Reproduces the verified Christmas coverage result: 57 agents used, 100% green.
Also asserts the safety property: no interval left short (no 'red') when fully covered.
"""

import math
from engine import (
    compound_shrinkage, gross_hc, agents_for_sl,
    generate_combinations, distribute_volume_to_intervals, optimise_shifts,
)

SHRINK = compound_shrinkage(8, 5, 3)["total_shrinkage_pct"]
CHRISTMAS_VOICE = {
    "Y1": {"baseline": 8500, "actual": 3600},
    "Y2": {"baseline": 9200, "actual": 5100},
    "Y3": {"baseline": 9800, "actual": 5600},
}


def _christmas_gross_intervals():
    sunday = 1300   # fixed daily volume (independent of the forecast model)
    ivs = distribute_volume_to_intervals(sunday, "09:00", "17:00", 30)
    rows = []
    for i, iv in enumerate(ivs):
        net = agents_for_sl(iv["calls_per_hour"], 360, 80, 20)
        grs = math.ceil(gross_hc(net, SHRINK))
        rows.append({"interval": i + 1, "start": iv["start"], "net_hc": grs})
    return rows


def test_christmas_shift_plan_uses_57_and_full_coverage():
    rows = _christmas_gross_intervals()
    shifts = [
        {"name": "Early", "start": "07:00", "end": "15:00"},
        {"name": "Mid",   "start": "09:00", "end": "17:00"},
        {"name": "Late",  "start": "11:00", "end": "19:00"},
    ]
    res = optimise_shifts(rows, shifts, 80, "09:00", "17:00")
    assert res["total_agents_used"] == 57
    assert res["intervals_at_risk"] == 0          # no red
    assert res["coverage_pct"] == 100.0


def test_empty_inputs_return_error():
    assert "error" in optimise_shifts([], [], 10, "09:00", "17:00")
