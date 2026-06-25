"""
IBU% (voice) / Utilization% (chat) divisor — must match the original index.htm algorithm:
    util-adjusted = ceil(net / utilFrac)   (only when utilFrac < 1, clamped to [0.30, 1.0])
    gross         = ceil(util-adjusted / (1 - shrinkage))
Email & blended get NO util divisor.
"""

import math
from api.compute import _util_adjust, compute_plan
from engine import gross_hc_ceil


def test_voice_ibu_below_100():
    # IBU 85% → ceil(48 / 0.85) = 57
    assert _util_adjust("voice", 48, {"ibu_pct": 85}) == 57


def test_voice_ibu_100_is_noop():
    assert _util_adjust("voice", 48, {"ibu_pct": 100}) == 48


def test_chat_utilization_below_100():
    # Utilization 80% → ceil(15 / 0.80) = 19
    assert _util_adjust("chat", 15, {"utilization_pct": 80}) == 19


def test_email_and_blended_no_divisor():
    assert _util_adjust("email", 13, {"occupancy_target_pct": 50}) == 13
    assert _util_adjust("blended", 30, {"ibu_pct": 50}) == 30


def test_clamped_to_30_pct_floor():
    # IBU 10% must clamp to 30% → ceil(10 / 0.30) = 34 (not ceil(10/0.10)=100)
    assert _util_adjust("voice", 10, {"ibu_pct": 10}) == 34


def test_full_chain_voice_ibu_then_shrinkage():
    # net 48, IBU 85, shrink 15.22 → ceil(ceil(48/0.85)/0.8478) = ceil(57/0.8478) = 68
    util_adj = _util_adjust("voice", 48, {"ibu_pct": 85})
    assert gross_hc_ceil(util_adj, 15.22) == 68


def test_compute_plan_ibu_raises_gross():
    base = {
        "channels": ["voice"], "shrinkage": {"planned": 8, "unplanned": 5, "training": 3},
        "anomaly_years": ["Y1"],
        "params": {"voice": {"plan_volume": 4200, "aht_seconds": 360,
                             "operating_start": "09:00", "operating_end": "17:00",
                             "sl_target_pct": 80, "sl_target_seconds": 20}},
        "historical": {"voice": {"Y1": {"baseline": 8500, "actual": 3600},
                                 "Y2": {"baseline": 9200, "actual": 5100},
                                 "Y3": {"baseline": 9800, "actual": 5600}}},
        "day_split": {"voice": [0.45, 0.55, 0, 0, 0, 0, 0]},
    }
    g100 = compute_plan(base)["channels"]["voice"]["peak_gross_hc"]            # IBU default 100
    base["params"]["voice"]["ibu_pct"] = 85
    g85 = compute_plan(base)["channels"]["voice"]["peak_gross_hc"]             # IBU 85
    assert g85 > g100                  # lower utilisation needs MORE bodies (relative check)
