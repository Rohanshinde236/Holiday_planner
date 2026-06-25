"""
Holiday-effect day-shape decomposition.

PORTED VERBATIM (behaviour) from the original computeHolidayShapedSplit() in index.htm.
Replaces pure DOW rotation with a calendar-anchored base × holiday-multiplier model:

  base shape (normalWeek > auto-weekend from history > flat)
    × multiplier learned per distance-from-holiday (delta -3..+3)
    projected onto the target holiday's weekday
  → normalised 7-day split (Sat-first), summing to 1.0.

This produces the DAILY split only; it never touches the HC formulas. Output is always
finite (no NaN/Inf), Saturday-first (Sat=0 … Fri=6).
"""

import math
import datetime

# Recency weights (must match the JS DAY_INDEX_WEIGHTS).
DAY_INDEX_WEIGHTS = {"Y1": 0.40, "Y2": 0.30, "Y3": 0.20, "Y4": 0.07, "Y5": 0.03}


def parse_date_col(date_str: str) -> int:
    """'YYYY-MM-DD' → Saturday-first column (Sat=0,Sun=1,…,Fri=6), or -1 if invalid."""
    if not date_str:
        return -1
    parts = str(date_str).split("-")
    if len(parts) != 3:
        return -1
    try:
        d = datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, TypeError):
        return -1
    js_dow = d.isoweekday() % 7         # Mon..Sun(1..7) → Sun=0..Sat=6 (matches JS getDay)
    return 0 if js_dow == 6 else js_dow + 1


def compute_holiday_shaped_split(
    daily_volumes: dict,          # {year_slot: [7 Sat-first volumes]} for ONE channel
    holiday_dates: dict,          # {year_slot: "YYYY-MM-DD"} per-year holiday date
    target_date: str,             # plan-year holiday date
    normal_week: list | None = None,   # optional [7] typical non-holiday week
) -> dict:
    """Returns {values:[7 fractions summing to 1.0], base_source, anchored}."""

    # ── 1. Resolve base shape: normalWeek > auto-weekend > flat ──
    base = None
    base_source = "flat"
    if normal_week and len(normal_week) == 7:
        s = sum(float(v or 0) for v in normal_week)
        if s > 0:
            base = [float(v or 0) / s for v in normal_week]
            base_source = "normalWeek"

    if base is None:
        agg = [0.0] * 7
        agg_w = 0.0
        for y, arr in daily_volumes.items():
            w = DAY_INDEX_WEIGHTS.get(y, 0)
            if w <= 0 or not isinstance(arr, (list, tuple)) or len(arr) != 7:
                continue
            wk = sum(float(v or 0) for v in arr)
            if wk <= 0:
                continue
            for d in range(7):
                agg[d] += w * (float(arr[d] or 0) / wk)
            agg_w += w
        if agg_w > 0:
            for d in range(7):
                agg[d] /= agg_w
            weekday_level = (agg[2] + agg[3] + agg[4] + agg[5] + agg[6]) / 5
            if weekday_level > 0:
                auto = [agg[0], agg[1]] + [weekday_level] * 5
                asum = sum(auto)
                if asum > 0:
                    base = [v / asum for v in auto]
                    base_source = "auto-weekend"
        if base is None:
            base = [1 / 7] * 7
            base_source = "flat"

    # ── 2. Learn holiday multipliers per delta (-3..+3) ──
    mult_sum = [0.0] * 7
    mult_wgt = [0.0] * 7
    c_t = parse_date_col(target_date or "")

    contributing = []
    for y, arr in daily_volumes.items():
        if not isinstance(arr, (list, tuple)) or len(arr) != 7:
            continue
        if sum(float(v or 0) for v in arr) <= 0:
            continue
        if parse_date_col(holiday_dates.get(y, "")) < 0:
            continue
        contributing.append(y)

    anchored = len(contributing) > 0 and c_t >= 0

    for y in contributing:
        w = DAY_INDEX_WEIGHTS.get(y, 0)
        if w <= 0:
            continue
        arr = daily_volumes[y]
        wk = sum(float(v or 0) for v in arr)
        if wk <= 0:
            continue
        c_y = parse_date_col(holiday_dates.get(y, ""))
        if c_y < 0:
            continue
        obs = [float(v or 0) / wk for v in arr]
        for d in range(7):
            delta = ((d - c_y + 3 + 7) % 7) - 3
            i = delta + 3
            if base[d] > 0:
                raw = obs[d] / base[d]
                mult_sum[i] += w * max(0.05, min(5.0, raw))
            else:
                mult_sum[i] += w * 1.0
            mult_wgt[i] += w

    mult = [(mult_sum[i] / mult_wgt[i]) if mult_wgt[i] > 0 else 1.0 for i in range(7)]

    # ── 3. Project onto target holiday weekday ──
    shape = [0.0] * 7
    if anchored:
        for d in range(7):
            delta = ((d - c_t + 3 + 7) % 7) - 3
            i = delta + 3
            shape[d] = base[d] * (mult[i] if mult[i] > 0 else 1.0)
            if not math.isfinite(shape[d]):
                shape[d] = base[d]
    else:
        shape = base[:]

    # ── 4. Renormalise to sum 1.0 (with NaN guard) ──
    ssum = sum(shape)
    values = [v / ssum for v in shape] if ssum > 0 else [1 / 7] * 7
    values = [v if math.isfinite(v) else 1 / 7 for v in values]

    return {"values": values, "base_source": base_source, "anchored": anchored}
