"""
Forecast engine: year-on-year impact %, combination scoring, and all-subset
combination generation.

PORTED VERBATIM from data_engine.py (v2.0.2). Logic frozen — do not change.
Scoring weights (0.40 / 0.30 / 0.30) and recency weights (Y1=1.0 .. Y5=0.1)
are the authoritative values aligned to the JS engine.
"""

from typing import Optional
import numpy as np


def compute_impact_pct(actual: float, baseline: float) -> Optional[float]:
    if not baseline or baseline == 0:
        return None
    return round((actual - baseline) / baseline * 100, 2)


def score_combination(
    combo_name: str,
    impacts: list,
    years_available: list,
    anomaly_years: list
) -> float:
    """Score a combination 0..100: consistency, richness, recency, anomaly penalty."""
    if not impacts:
        return 0.0

    clean = [i for i in impacts if i is not None]
    if not clean:
        return 0.0

    mean = np.mean(clean)
    std = np.std(clean) if len(clean) > 1 else 0
    cv = (std / abs(mean)) if mean != 0 else 1.0
    consistency_score = max(0, 1 - min(cv, 1.0))

    richness_score = min(len(clean) / 5.0, 1.0)

    year_weights = {"Y1": 1.0, "Y2": 0.7, "Y3": 0.5, "Y4": 0.3, "Y5": 0.1}
    recency_total = 0
    recency_count = 0
    for y in years_available:
        if y not in anomaly_years:
            recency_total += year_weights.get(y, 0.1)
            recency_count += 1
    recency_score = (recency_total / recency_count) if recency_count else 0

    positive_component = 0.40 * consistency_score + 0.30 * richness_score + 0.30 * recency_score
    raw_penalty = 0.3 * len([y for y in years_available if y in anomaly_years])
    penalty_cap = max(0.0, positive_component - 0.01)
    anomaly_penalty = min(raw_penalty, penalty_cap)

    raw = positive_component - anomaly_penalty
    return float(round(max(0, min(100, raw * 100)), 1))


def get_all_subsets(items: list) -> list:
    """Return all non-empty subsets of items (mirrors JS getAllSubsets)."""
    result = []
    n = len(items)
    for mask in range(1, 1 << n):
        subset = [items[i] for i in range(n) if mask & (1 << i)]
        result.append(subset)
    return result


YEAR_ORDER = ["Y1", "Y2", "Y3", "Y4", "Y5"]  # Y1 = most recent


def compute_yoy_series(historical: dict) -> dict:
    """
    Year-over-year change per slot, matching index.htm _computeYoYSeries (the authoritative UI):
        YoY[y] = (actual[y] - actual[next_older]) / actual[next_older] * 100
    The oldest populated slot is the baseline anchor and gets NO YoY value.
    Uses ACTUAL volumes only (baseline is not used for the forecast).
    """
    populated = [y for y in YEAR_ORDER if y in historical and (historical[y].get("actual") or 0) > 0]
    yoy = {}
    for i in range(len(populated) - 1):
        y, y_prev = populated[i], populated[i + 1]
        act = historical[y].get("actual") or 0
        act_prev = historical[y_prev].get("actual") or 0
        if act_prev > 0:
            yoy[y] = (act - act_prev) / act_prev * 100
    return yoy


def generate_combinations(
    historical: dict,
    anomaly_years: list,
    plan_volume: float
) -> list:
    """
    YoY combination engine — ported from index.htm generateCombinations (v2.0 "re-arch").
    Impact metric = YoY change (this year's actual vs prior year's actual). N populated years
    → N−1 YoY points (oldest excluded). Combinations are all subsets of those YoY points.
    forecast = plan_volume × (1 + mean(YoY)/100).
    Returns sorted list (highest score first; top = recommended).
    """
    populated = [y for y in YEAR_ORDER if y in historical and (historical[y].get("actual") or 0) > 0]
    yoy = compute_yoy_series(historical)
    avail = [y for y in populated if y in yoy]   # ordered, excludes oldest baseline slot

    # Single-year baseline path: <2 populated years → no YoY → 0% impact, plan passes through.
    if not avail:
        if len(populated) == 1:
            sy = populated[0]
            score = score_combination(sy, [0], [sy], anomaly_years)
            return [{
                "combo": sy, "years": [sy], "impacts": [0.0], "blended_impact_pct": 0.0,
                "forecasted_volume": round(plan_volume) if plan_volume > 0 else 0,
                "score": score, "contains_anomaly": False, "recommended": True,
                "single_year_baseline": True,
            }]
        return []

    def mk(subset, name_override=None):
        vi = [yoy[y] for y in subset if yoy.get(y) is not None]
        if not vi:
            return None
        blended = round(float(np.mean(vi)), 2)
        forecasted = round(plan_volume * (1 + blended / 100)) if plan_volume > 0 else 0
        name = name_override or (subset[0] if len(subset) == 1 else f"Avg({'+'.join(subset)})")
        return {
            "combo": name, "years": subset, "impacts": [round(v, 2) for v in vi],
            "blended_impact_pct": blended, "forecasted_volume": forecasted,
            "score": score_combination(name, vi, subset, anomaly_years),
            "contains_anomaly": any(y in anomaly_years for y in subset), "recommended": False,
        }

    combos = [c for c in (mk(s) for s in get_all_subsets(avail)) if c]

    # 2-year special: with exactly 1 YoY point, add a distinct "Average of available data" row.
    if len(avail) == 1 and len(combos) == 1:
        avg = mk([avail[0]], "Average of available data (1 YoY point)")
        if avg and avg["combo"] != combos[0]["combo"]:
            combos.append(avg)

    combos.sort(key=lambda x: x["score"], reverse=True)
    if combos:
        combos[0]["recommended"] = True
    return combos
