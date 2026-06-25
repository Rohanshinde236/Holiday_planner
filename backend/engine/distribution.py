"""
Volume distribution: daily volume -> 30-min intervals (overnight-aware),
and the weighted day-of-week index forecast.

PORTED VERBATIM from data_engine.py (v2.0.2). Logic frozen — do not change.
"""

from typing import Optional
import numpy as np


def distribute_volume_to_intervals(
    daily_volume: float,
    operating_start: str,
    operating_end: str,
    interval_minutes: int = 30,
    profile: Optional[list] = None
) -> list:
    """
    Distribute daily volume to 30-min intervals. Supports overnight windows.
    profile: per-interval weights (auto-normalised). If None, uses a bell-curve
    distribution peaking just before midday.
    """
    start_h, start_m = map(int, operating_start.split(":"))
    end_h, end_m = map(int, operating_end.split(":"))
    start_total = start_h * 60 + start_m
    end_total = end_h * 60 + end_m

    total_minutes = (end_total - start_total) % 1440
    if total_minutes == 0:
        total_minutes = 1440  # full 24-hour window
    n_intervals = total_minutes // interval_minutes

    if n_intervals <= 0:
        return []

    if profile and len(profile) == n_intervals:
        weights = np.array(profile, dtype=float)
    else:
        x = np.linspace(0, 1, n_intervals)
        weights = np.exp(-((x - 0.45) ** 2) / (2 * 0.18 ** 2))

    weights = weights / weights.sum()

    results = []
    for i in range(n_intervals):
        slot_start_min = (start_total + i * interval_minutes) % 1440
        slot_end_min = (start_total + (i + 1) * interval_minutes) % 1440
        vol = daily_volume * weights[i]
        results.append({
            "interval": i + 1,
            "start": f"{slot_start_min // 60:02d}:{slot_start_min % 60:02d}",
            "end": f"{slot_end_min // 60:02d}:{slot_end_min % 60:02d}",
            "volume": round(vol, 1),
            "calls_per_hour": round(vol * (60 / interval_minutes), 1)
        })

    return results


# WEIGHT SYNC: must match DAY_INDEX_WEIGHTS in the JS engine.
_DAY_INDEX_WEIGHTS = {"Y1": 0.40, "Y2": 0.30, "Y3": 0.20, "Y4": 0.07, "Y5": 0.03}


def day_index_forecast(years_data: dict, plan_volume: float) -> list:
    """
    Weighted day-of-week index forecast. Returns 7 floats (Sat..Fri) summing to
    plan_volume. Flat split when no usable history. Never raises / never NaN/Inf.
    """
    if plan_volume == 0:
        return [0.0] * 7

    weighted_index = [0.0] * 7
    total_weight = 0.0

    for slot, w in _DAY_INDEX_WEIGHTS.items():
        if slot not in years_data:
            continue
        arr = years_data[slot]
        if not isinstance(arr, (list, tuple)) or len(arr) != 7:
            continue
        week_total = sum(float(v) for v in arr if v is not None)
        if week_total <= 0:
            continue
        for d in range(7):
            v = float(arr[d]) if arr[d] is not None else 0.0
            weighted_index[d] += w * (v / week_total)
        total_weight += w

    if total_weight <= 0:
        flat = plan_volume / 7.0
        return [flat] * 7

    index_sum = sum(weighted_index)
    if index_sum <= 0:
        flat = plan_volume / 7.0
        return [flat] * 7

    norm_index = [v / index_sum for v in weighted_index]
    return [norm_index[d] * plan_volume for d in range(7)]
