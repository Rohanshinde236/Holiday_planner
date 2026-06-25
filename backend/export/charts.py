"""
Render the report diagrams to PNG bytes (server-side, headless matplotlib).
These are the same charts shown in the UI — embedded into the PDF/Excel exports.
Charts only DISPLAY engine numbers; they compute nothing.
"""

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PRIMARY = "#3a5bd9"
GREY = "#5b6577"
WEAK = "#eef2ff"


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def year_trend_png(res: dict, channel: str) -> bytes:
    """DIAGRAM 1 — historical impact % per year + forecast point."""
    impacts = res.get("impacts", {})
    years = list(impacts.keys())
    vals = [impacts[y] if impacts[y] is not None else 0 for y in years]
    reco = res.get("recommended") or {}
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    ax.plot(years, vals, "-o", color=GREY, label="Historical impact %")
    ax.plot(["Forecast"], [reco.get("blended_impact_pct", 0)], "o", color=PRIMARY, markersize=10, label="Forecast")
    ax.axhline(0, color="#ccc", lw=0.8)
    ax.set_title(f"{channel.capitalize()} — year impact % + forecast ({reco.get('combo', '-')})", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7, loc="best")
    return _png(fig)


def staffing_curve_png(res: dict, channel: str) -> bytes:
    """DIAGRAM 2 — net/gross HC per 30-min slot (busiest day)."""
    ivs = res.get("intervals", [])
    if not ivs:
        return b""
    xs = [iv["start"] for iv in ivs]
    net = [iv["net_hc"] for iv in ivs]
    gross = [iv["gross_hc"] for iv in ivs]
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    ax.fill_between(range(len(xs)), gross, color=WEAK)
    ax.plot(range(len(xs)), gross, color=PRIMARY, label="Gross HC")
    ax.plot(range(len(xs)), net, color=GREY, ls="--", label="Net HC")
    step = max(1, len(xs) // 8)
    ax.set_xticks(range(0, len(xs), step))
    ax.set_xticklabels([xs[i] for i in range(0, len(xs), step)], fontsize=7, rotation=45)
    ax.set_title(f"{channel.capitalize()} — staffing per 30-min slot (busiest: {res.get('busiest_day')})", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7, loc="best")
    return _png(fig)


def intraday_overlay_png(res: dict, channel: str) -> bytes:
    """Intraday overlay — each year's per-slot shape + the forecast (% of day)."""
    ov = res.get("intraday_overlay")
    if not ov:
        return b""
    slots = ov["slots"]
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    palette = ["#9aa3b5", "#b8c0d0", "#c9a0dc", "#a0c9b0", "#d6b88a"]
    for i, (yr, arr) in enumerate(ov["per_year"].items()):
        ax.plot(range(len(arr)), [v * 100 for v in arr], color=palette[i % len(palette)],
                linewidth=1.2, label=yr)
    ax.plot(range(len(ov["forecast"])), [v * 100 for v in ov["forecast"]],
            color=PRIMARY, linewidth=2.5, label="Forecast")
    step = max(1, len(slots) // 8)
    ax.set_xticks(range(0, len(slots), step))
    ax.set_xticklabels([slots[i] for i in range(0, len(slots), step)], fontsize=7, rotation=45)
    ax.set_title(f"{channel.capitalize()} — intraday shape: all years + forecast (% of day)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7, loc="best")
    return _png(fig)


def daily_bar_png(res: dict, channel: str) -> bytes:
    """Daily volume bar (Sat-first)."""
    daily = res.get("daily", {})
    fig, ax = plt.subplots(figsize=(6.4, 2.2))
    ax.bar(list(daily.keys()), list(daily.values()), color=PRIMARY)
    ax.set_title(f"{channel.capitalize()} — daily volume (Sat-first)", fontsize=9)
    ax.tick_params(labelsize=8)
    return _png(fig)
