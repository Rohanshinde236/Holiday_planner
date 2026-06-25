"""
Shift optimisation — TRUE OPTIMAL via Integer Linear Programming (OR-Tools).

This is the Phase 2 accuracy upgrade over the greedy heuristic (shifts.py).
It does NOT change any WFM formula — it only arranges the (already-computed) HC
requirement into the leanest set of shifts.

Model:
  variables   x[s] >= 0 integer  — agents assigned to shift s
  constraints for each interval i:  sum_{s covers i} x[s] >= required[i]   (no slot short)
  objective   minimise  sum_s x[s]                                         (fewest agents)

ortools is imported lazily so the core engine stays usable without it.
"""

import math


def _coverage_matrix(hc_requirements, available_shifts, operating_start, interval_minutes):
    n_intervals = len(hc_requirements)

    def time_to_slot(t_str, base_start):
        bh, bm = map(int, base_start.split(":"))
        th, tm = map(int, t_str.split(":"))
        delta = (th * 60 + tm) - (bh * 60 + bm)
        return delta // interval_minutes

    cov = [[0] * n_intervals for _ in available_shifts]
    for si, sh in enumerate(available_shifts):
        s_slot = time_to_slot(sh["start"], operating_start)
        e_slot = time_to_slot(sh["end"], operating_start)
        for iv in range(max(0, s_slot), min(n_intervals, e_slot)):
            cov[si][iv] = 1
    return cov


def optimise_shifts_ilp(
    hc_requirements: list,
    available_shifts: list,
    operating_start: str,
    operating_end: str,
    interval_minutes: int = 30,
    max_agents: int | None = None,
) -> dict:
    """
    Provably-optimal shift plan: minimum total agents that fully cover every interval.
    Same return shape as engine.shifts.optimise_shifts so callers are interchangeable.

    If max_agents is given and full coverage is infeasible within it, falls back to
    maximising covered demand under the cap (and flags pool_exhausted).
    """
    if not hc_requirements or not available_shifts:
        return {"error": "Missing requirements or shift templates"}

    from ortools.linear_solver import pywraplp

    n_intervals = len(hc_requirements)
    req = [r["net_hc"] for r in hc_requirements]
    cov = _coverage_matrix(hc_requirements, available_shifts, operating_start, interval_minutes)

    solver = pywraplp.Solver.CreateSolver("CBC")
    if solver is None:
        return {"error": "ILP solver unavailable"}

    n_shifts = len(available_shifts)
    x = [solver.IntVar(0, solver.infinity(), f"x{s}") for s in range(n_shifts)]

    # Coverage per interval
    cover_expr = [solver.Sum(cov[s][i] * x[s] for s in range(n_shifts)) for i in range(n_intervals)]

    pool_exhausted = False
    feasible_full = True

    if max_agents is not None:
        solver.Add(solver.Sum(x) <= max_agents)

    # Try full coverage first
    for i in range(n_intervals):
        solver.Add(cover_expr[i] >= req[i])
    solver.Minimize(solver.Sum(x))
    status = solver.Solve()

    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        # Full coverage infeasible under the pool cap → maximise coverage instead
        feasible_full = False
        pool_exhausted = max_agents is not None
        solver.Clear()
        x = [solver.IntVar(0, solver.infinity(), f"x{s}") for s in range(n_shifts)]
        cover_expr = [solver.Sum(cov[s][i] * x[s] for s in range(n_shifts)) for i in range(n_intervals)]
        covered = [solver.IntVar(0, req[i], f"c{i}") for i in range(n_intervals)]
        for i in range(n_intervals):
            solver.Add(covered[i] <= cover_expr[i])
        if max_agents is not None:
            solver.Add(solver.Sum(x) <= max_agents)
        solver.Maximize(solver.Sum(covered))
        status = solver.Solve()

    assigned = [int(round(v.solution_value())) for v in x]

    result_shifts = []
    for si, sh in enumerate(available_shifts):
        if assigned[si] > 0:
            result_shifts.append({
                "shift_name": sh["name"],
                "start": sh["start"],
                "end": sh["end"],
                "agents_assigned": assigned[si],
            })

    interval_results = []
    for i, iv in enumerate(hc_requirements):
        planned = sum(cov[s][i] * assigned[s] for s in range(n_shifts))
        required = iv["net_hc"]
        delta = planned - required
        risk = "green" if delta >= 0 else ("amber" if delta >= -math.ceil(max(required, 1) * 0.15) else "red")
        interval_results.append({
            "interval": iv["interval"],
            "start": iv["start"],
            "required_net_hc": required,
            "planned_hc": planned,
            "delta": delta,
            "sl_risk": risk,
        })

    green = sum(1 for r in interval_results if r["sl_risk"] == "green")
    return {
        "mode": "ilp",
        "optimal": feasible_full,
        "pool_exhausted": pool_exhausted,
        "recommended_shifts": result_shifts,
        "total_agents_used": sum(assigned),
        "interval_coverage": interval_results,
        "intervals_at_risk": sum(1 for r in interval_results if r["sl_risk"] == "red"),
        "intervals_amber": sum(1 for r in interval_results if r["sl_risk"] == "amber"),
        "coverage_pct": round(100 * green / len(interval_results), 1) if interval_results else 0,
    }
