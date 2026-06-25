"""Tests for post-holiday forecast-accuracy metrics."""

from engine.accuracy import item_accuracy, forecast_accuracy


def test_item_mape_and_bias():
    m = item_accuracy(forecast=110, actual=100)
    assert m["abs_error"] == 10
    assert m["mape_pct"] == 10.0
    assert m["bias_pct"] == 10.0      # over-forecast by 10%


def test_under_forecast_negative_bias():
    m = item_accuracy(forecast=90, actual=100)
    assert m["bias_pct"] == -10.0     # under-forecast


def test_zero_actual_guarded():
    m = item_accuracy(forecast=50, actual=0)
    assert m["mape_pct"] is None and m["bias_pct"] is None


def test_overall_mape():
    r = forecast_accuracy([
        {"label": "voice", "forecast": 110, "actual": 100},   # 10%
        {"label": "chat", "forecast": 80, "actual": 100},     # 20%
    ])
    assert r["overall_mape_pct"] == 15.0
    assert r["n"] == 2
