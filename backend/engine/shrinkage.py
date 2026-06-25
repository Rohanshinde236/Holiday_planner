"""
Compound shrinkage build-up and net->gross conversion.

PORTED VERBATIM from data_engine.py (v2.0.2). Logic frozen — do not change.
"""


def compound_shrinkage(
    planned_leave_pct: float,
    unplanned_leave_pct: float,
    training_pct: float
) -> dict:
    """
    Compound shrinkage = 1 - (1-PL)(1-UL)(1-TR)
    Returns total shrinkage % and gross multiplier.
    """
    pl = planned_leave_pct / 100
    ul = unplanned_leave_pct / 100
    tr = training_pct / 100
    total = 1 - (1 - pl) * (1 - ul) * (1 - tr)
    return {
        "planned_leave_pct": planned_leave_pct,
        "unplanned_leave_pct": unplanned_leave_pct,
        "training_pct": training_pct,
        "total_shrinkage_pct": round(total * 100, 2),
        "gross_multiplier": round(1 / (1 - total), 4) if total < 1 else None
    }


import math

# Sentinel used when shrinkage >= 100% makes gross HC mathematically infinite.
# Mirrors the original tool's 9999 overflow cap so output never contains Infinity/NaN.
GROSS_SENTINEL = 9999


def gross_hc(net_hc: float, total_shrinkage_pct: float) -> float:
    """Inflate net HC by compound shrinkage. Returns inf if shrinkage >= 100%."""
    s = total_shrinkage_pct / 100
    if s >= 1:
        return float("inf")
    return net_hc / (1 - s)


def gross_hc_ceil(net_hc: float, total_shrinkage_pct: float) -> int:
    """Safe integer gross HC. Returns the 9999 sentinel instead of crashing on inf."""
    g = gross_hc(net_hc, total_shrinkage_pct)
    if g == float("inf") or g != g:  # inf or NaN
        return GROSS_SENTINEL
    return math.ceil(g)
