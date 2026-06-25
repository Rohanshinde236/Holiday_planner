"""Tests for the holiday-effect day-shape decomposition (ported from index.htm)."""

from engine.dayshape import parse_date_col, compute_holiday_shaped_split


def test_parse_date_col_saturday_first():
    # 2025-12-25 is a Thursday -> Sat-first col: Sat0 Sun1 Mon2 Tue3 Wed4 Thu5 Fri6 -> 5
    assert parse_date_col("2025-12-25") == 5
    # 2025-08-15 (Independence Day) is a Friday -> 6
    assert parse_date_col("2025-08-15") == 6
    assert parse_date_col("") == -1
    assert parse_date_col("not-a-date") == -1


def test_split_sums_to_one_and_finite():
    daily = {"Y1": [100, 120, 0, 0, 0, 0, 0], "Y2": [110, 130, 0, 0, 0, 0, 0]}
    dates = {"Y1": "2024-12-25", "Y2": "2023-12-25"}
    res = compute_holiday_shaped_split(daily, dates, "2025-12-25")
    assert abs(sum(res["values"]) - 1.0) < 1e-9
    assert all(v == v and v != float("inf") for v in res["values"])  # no NaN/Inf


def test_flat_when_no_history():
    res = compute_holiday_shaped_split({}, {}, "2025-12-25")
    assert res["base_source"] == "flat"
    assert res["anchored"] is False
    assert all(abs(v - 1 / 7) < 1e-9 for v in res["values"])


def test_anchored_shifts_peak_to_holiday_weekday():
    # History: a WEEKDAY spike ON the holiday day (Tuesday). The auto-weekend base
    # smooths weekdays flat, so the holiday spike lives in the multiplier — which then
    # projects onto the TARGET holiday's weekday (Thursday). Peak should move to Thu.
    daily = {"Y1": [10, 10, 10, 200, 10, 10, 10]}   # peak at col 3 = Tuesday
    dates = {"Y1": "2023-12-26"}                     # 2023-12-26 is a Tuesday -> col 3
    res = compute_holiday_shaped_split(daily, dates, "2025-12-25")  # Thursday -> col 5
    assert res["anchored"] is True
    peak_day = max(range(7), key=lambda i: res["values"][i])
    assert peak_day == 5   # peak moved to Thursday (the target holiday weekday)
