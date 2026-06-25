"""
GOLDEN TESTS — re-baselined to the YoY combination model (matches index.htm, the real UI).

Two independent guarantees:
  A. COMBINATION model (YoY) — verified against the old UI's exact numbers (scores 76/67/56).
  B. HC math (Erlang C + shrinkage) — fed a FIXED daily volume so it's independent of the
     forecast model; still 48 net / 57 gross for 1,300 voice on a 09:00–17:00 day.
"""

import math
from engine import (
    compound_shrinkage, gross_hc_ceil, agents_for_sl,
    generate_combinations, compute_yoy_series, distribute_volume_to_intervals,
    chat_agents_required, email_agents_required,
)

SHRINK = compound_shrinkage(8, 5, 3)["total_shrinkage_pct"]  # 15.22

# Christmas voice actuals (Y1 most recent): 3600, 5100, 5600
CHRISTMAS_VOICE = {
    "Y1": {"baseline": 8500, "actual": 3600},
    "Y2": {"baseline": 9200, "actual": 5100},
    "Y3": {"baseline": 9800, "actual": 5600},
}


# ---------- A. YoY combination model (matches the old UI exactly) ----------

def test_shrinkage_compound():
    assert SHRINK == 15.22


def test_yoy_impacts():
    yoy = compute_yoy_series(CHRISTMAS_VOICE)
    assert round(yoy["Y1"], 2) == -29.41   # (3600-5100)/5100
    assert round(yoy["Y2"], 2) == -8.93    # (5100-5600)/5600
    assert "Y3" not in yoy                  # oldest slot = baseline anchor, no YoY


def test_three_years_give_three_combos():
    # 3 populated years -> 2 YoY points -> subsets {Y1},{Y2},{Avg} = 3 combos
    combos = generate_combinations(CHRISTMAS_VOICE, [], 4200)
    assert len(combos) == 3


def test_scores_match_old_ui_unflagged():
    # No anomalies -> scores must be 76 / 67 / 56 (verified against index.htm screenshot)
    combos = {c["combo"]: c["score"] for c in generate_combinations(CHRISTMAS_VOICE, [], 4200)}
    assert combos["Y1"] == 76.0
    assert combos["Y2"] == 67.0
    assert combos["Avg(Y1+Y2)"] == 56.1   # UI displays "56" (rounded); exact value 56.1


def test_anomaly_flag_changes_recommendation():
    # Flag Y1 -> Y1 score drops; Y2 becomes the recommended combo
    combos = generate_combinations(CHRISTMAS_VOICE, ["Y1"], 4200)
    assert combos[0]["combo"] == "Y2"
    assert combos[0]["forecasted_volume"] == 3825   # 4200 * (1 - 0.0893)


def test_single_year_baseline_path():
    # Only one populated year -> 0% impact, plan passes through unchanged
    combos = generate_combinations({"Y1": {"baseline": 9000, "actual": 5000}}, [], 4200)
    assert len(combos) == 1
    assert combos[0]["blended_impact_pct"] == 0.0
    assert combos[0]["forecasted_volume"] == 4200
    assert combos[0].get("single_year_baseline") is True


# ---------- B. HC math (fixed volume, independent of forecast model) ----------

def _peak_cph(daily, start, end):
    return max(iv["calls_per_hour"] for iv in distribute_volume_to_intervals(daily, start, end, 30))


def test_voice_hc_math_unchanged():
    cph = _peak_cph(1300, "09:00", "17:00")          # 1,300 voice on a Sunday-style day
    net = agents_for_sl(cph, 360, 80, 20)
    assert net == 48
    assert gross_hc_ceil(net, SHRINK) == 57           # HC math frozen


def test_chat_hc_math_unchanged():
    cph = _peak_cph(1300, "08:00", "22:00")
    net = chat_agents_required(cph, 480, 2.5, 80)["net"]
    assert gross_hc_ceil(net, SHRINK) == math.ceil(net / (1 - SHRINK / 100))


def test_email_hc_math_unchanged():
    r = email_agents_required(785, 600, 14, 75, "08:00", "22:00")
    assert r["throughput_per_agent"] == 63.0
    assert r["net"] == 13
