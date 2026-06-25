"""
Post-holiday forecast-accuracy metrics (deterministic formulas, §5.2).

MAPE = mean absolute percentage error = mean(|forecast - actual| / actual) * 100.
No LLM, no estimation — pure arithmetic, golden-testable.
"""


def item_accuracy(forecast: float, actual: float) -> dict:
    abs_err = abs(forecast - actual)
    mape = round(abs_err / actual * 100, 2) if actual else None
    bias = round((forecast - actual) / actual * 100, 2) if actual else None  # +over / -under
    return {
        "forecast": forecast, "actual": actual,
        "abs_error": round(abs_err, 2),
        "mape_pct": mape,        # magnitude of error
        "bias_pct": bias,        # signed: positive = over-forecast
    }


def forecast_accuracy(items: list) -> dict:
    """
    items: [{"label": "voice", "forecast": x, "actual": y}, ...]
    Returns per-item metrics + overall MAPE (mean of item MAPEs where actual > 0).
    """
    results = []
    mapes = []
    for it in items:
        m = item_accuracy(float(it.get("forecast", 0)), float(it.get("actual", 0)))
        m["label"] = it.get("label", "")
        results.append(m)
        if m["mape_pct"] is not None:
            mapes.append(m["mape_pct"])
    overall = round(sum(mapes) / len(mapes), 2) if mapes else None
    return {"items": results, "overall_mape_pct": overall, "n": len(results)}
