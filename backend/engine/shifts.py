"""
Shift optimisation — greedy heuristic.

PORTED VERBATIM from data_engine.py (v2.0.2). Logic frozen — do not change.
NOTE: the true-optimal ILP optimiser is added in Phase 2 as an ALTERNATIVE mode;
this greedy implementation is preserved unchanged as the baseline/fallback.
"""

import numpy as np


def optimise_shifts(
    hc_requirements: list,
    available_shifts: list,
    available_agents: int,
    operating_start: str,
    operating_end: str,
    interval_minutes: int = 30
) -> dict:
    """
    Greedy shift optimisation.
    hc_requirements: [{"interval": 1, "start": "08:00", "net_hc": 12}, ...]
    available_shifts: [{"name": "Early", "start": "08:00", "end": "16:00"}, ...]
    Assigns each agent to the shift that reduces the largest remaining deficit.
    """
    if not hc_requirements or not available_shifts:
        return {"error": "Missing requirements or shift templates"}

    n_intervals = len(hc_requirements)
    req = np.array([r["net_hc"] for r in hc_requirements], dtype=float)

    def time_to_slot(t_str, base_start, interval_minutes):
        bh, bm = map(int, base_start.split(":"))
        th, tm = map(int, t_str.split(":"))
        delta = (th * 60 + tm) - (bh * 60 + bm)
        return delta // interval_minutes

    base = operating_start
    coverage = np.zeros((len(available_shifts), n_intervals), dtype=int)
    for si, sh in enumerate(available_shifts):
        s_slot = time_to_slot(sh["start"], base, interval_minutes)
        e_slot = time_to_slot(sh["end"], base, interval_minutes)
        for iv in range(max(0, s_slot), min(n_intervals, e_slot)):
            coverage[si, iv] = 1

    assigned = np.zeros(len(available_shifts), dtype=float)
    current_coverage = np.zeros(n_intervals, dtype=float)

    for _ in range(available_agents):
        deficit = req - current_coverage
        if np.all(deficit <= 0):
            break
        best_shift = -1
        best_gain = 0
        for si in range(len(available_shifts)):
            gain = np.sum(np.maximum(0, deficit) * coverage[si])
            if gain > best_gain:
                best_gain = gain
                best_shift = si
        if best_shift == -1:
            break
        assigned[best_shift] += 1
        current_coverage += coverage[best_shift]

    result_shifts = []
    for si, sh in enumerate(available_shifts):
        if assigned[si] > 0:
            result_shifts.append({
                "shift_name": sh["name"],
                "start": sh["start"],
                "end": sh["end"],
                "agents_assigned": int(assigned[si])
            })

    final_coverage = current_coverage
    interval_results = []
    for i, iv in enumerate(hc_requirements):
        planned = int(final_coverage[i])
        required = iv["net_hc"]
        delta = planned - required
        risk = "green" if delta >= 0 else ("amber" if delta >= -2 else "red")
        interval_results.append({
            "interval": iv["interval"],
            "start": iv["start"],
            "required_net_hc": required,
            "planned_hc": planned,
            "delta": delta,
            "sl_risk": risk
        })

    return {
        "recommended_shifts": result_shifts,
        "total_agents_used": int(assigned.sum()),
        "interval_coverage": interval_results,
        "intervals_at_risk": sum(1 for r in interval_results if r["sl_risk"] == "red"),
        "intervals_amber": sum(1 for r in interval_results if r["sl_risk"] == "amber"),
        "coverage_pct": round(
            100 * sum(1 for r in interval_results if r["sl_risk"] == "green") / len(interval_results), 1
        ) if interval_results else 0
    }
