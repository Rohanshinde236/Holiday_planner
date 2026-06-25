"""
Plan compute orchestrator.

Runs the full pipeline for a whole plan (all channels) by calling the pure engine.
This module performs NO math itself — it only sequences engine calls and shapes the
result for the frontend. Every number comes from engine/ (the single source of truth).
"""

import math
from engine import (
    compound_shrinkage, gross_hc_ceil, agents_for_sl,
    chat_agents_required, email_agents_required,
    distribute_volume_to_intervals, generate_combinations, compute_yoy_series,
)
from engine.dayshape import compute_holiday_shaped_split, DAY_INDEX_WEIGHTS

DAYS = ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]  # Saturday-first


def _intraday_profile(intraday_ch: dict):
    """
    Recency-weighted forecast intraday profile from per-year slot history.
    intraday_ch: {year: [slot volumes]}. Returns (profile[] | None, per_year_normalised{}).
    Years must share the same slot count; zero-total years are skipped.
    """
    valid = {y: arr for y, arr in (intraday_ch or {}).items()
             if arr and sum(float(v or 0) for v in arr) > 0}
    if not valid:
        return None, {}
    length = len(next(iter(valid.values())))
    per_year, agg, w_total = {}, [0.0] * length, 0.0
    for y, arr in valid.items():
        if len(arr) != length:
            continue
        tot = sum(float(v or 0) for v in arr)
        norm = [float(v or 0) / tot for v in arr]
        per_year[y] = norm
        w = DAY_INDEX_WEIGHTS.get(y, 0.1)
        for i in range(length):
            agg[i] += w * norm[i]
        w_total += w
    if w_total <= 0:
        return None, per_year
    profile = [a / w_total for a in agg]
    s = sum(profile)
    profile = [p / s for p in profile] if s > 0 else None
    return profile, per_year


def _resolve_split(plan, ch, weekly):
    """
    Resolve the 7-day (Sat-first) split for a channel, in priority order:
      1. Holiday-shaped decomposition — when per-year daily_history is supplied (the
         richest signal; entering daily history drives the forecast shape).
      2. Manual day_split (explicit, non-flat).
      3. Flat 1/7.
    Returns (split[7], source, anchored).
    """
    # 1. Decomposition from per-year daily history (only if any year has positive volume)
    daily_history = plan.get("daily_history", {}).get(ch) or {}
    has_data = any(arr and sum(float(v or 0) for v in arr) > 0 for arr in daily_history.values())
    if has_data:
        holiday = plan.get("holiday") or {}
        target_date = holiday.get("plan_date") or ""
        holiday_dates = {h["slot"]: h.get("date") for h in holiday.get("history", []) if h.get("slot")}
        normal = (plan.get("normal_week", {}) or {}).get(ch)
        res = compute_holiday_shaped_split(daily_history, holiday_dates, target_date, normal)
        return res["values"], "decomposition:" + res["base_source"], res["anchored"]

    # 2. Manual split
    manual = plan.get("day_split", {}).get(ch)
    if manual and len(manual) == 7 and sum(manual) > 0 and len(set(manual)) > 1:
        s = sum(manual)
        return [v / s for v in manual], "manual", False

    # 3. Flat
    return [1 / 7] * 7, "flat", False


def _util_adjust(channel, net, params):
    """
    Apply the IBU% (voice) / Utilization% (chat) divisor between raw agents and shrinkage,
    EXACTLY as the original tool (index.htm): util-adjusted = ceil(net / utilFrac), only when
    utilFrac < 1, clamped to [0.30, 1.0]. Email & blended get no divisor.
    """
    if channel == "voice":
        frac = max(0.30, min(1.0, params.get("ibu_pct", 100) / 100))
    elif channel == "chat":
        frac = max(0.30, min(1.0, params.get("utilization_pct", 100) / 100))
    else:
        return net  # email / blended: no util divisor
    return math.ceil(net / frac) if frac < 1 else net


def _channel_hc_for_day(channel, daily_volume, params, shrink, profile=None):
    """Return (intervals[], peak_net, peak_gross) for one channel on one day."""
    start = params["operating_start"]
    end = params["operating_end"]
    aht = params["aht_seconds"]

    if channel == "email":
        r = email_agents_required(daily_volume, aht, params.get("operating_hours", 0),
                                  params.get("occupancy_target_pct", 75), start, end)
        net = r["net"]
        gross = gross_hc_ceil(net, shrink)
        return [], net, gross  # email = flat daily figure (no interval peak)

    ivs = distribute_volume_to_intervals(daily_volume, start, end, 30, profile)
    rows = []
    peak_net = peak_gross = 0
    voice_pct = params.get("voice_pct", 60) / 100
    chat_pct = params.get("chat_pct", 40) / 100
    for iv in ivs:
        cph = iv["calls_per_hour"]
        if channel == "chat":
            net = chat_agents_required(cph, aht, params.get("concurrency", 2.5),
                                       params.get("occupancy_target_pct", 80))["net"]
        elif channel == "blended":
            # Weighted voice (Erlang C) + chat (concurrency) on their volume shares.
            v_net = agents_for_sl(cph * voice_pct, params.get("voice_aht", 360),
                                  params.get("sl_target_pct", 80), params.get("sl_target_seconds", 20))
            c_net = chat_agents_required(cph * chat_pct, params.get("chat_aht", 480),
                                         params.get("concurrency", 2.5),
                                         params.get("occupancy_target_pct", 80))["net"]
            net = v_net + c_net
        else:  # voice
            net = agents_for_sl(cph, aht, params.get("sl_target_pct", 80),
                                params.get("sl_target_seconds", 20))
        # IBU/Utilization divisor (voice/chat) applied between raw agents and shrinkage
        gross = gross_hc_ceil(_util_adjust(channel, net, params), shrink)
        rows.append({"start": iv["start"], "end": iv["end"],
                     "calls_per_hour": cph, "net_hc": net, "gross_hc": gross})
        peak_net = max(peak_net, net)
        peak_gross = max(peak_gross, gross)
    return rows, peak_net, peak_gross


def compute_plan(plan: dict) -> dict:
    """
    plan: {
      channels: ["voice","chat","email"],
      shrinkage: {planned, unplanned, training},
      anomaly_years: [...],
      params: { <channel>: {plan_volume, aht_seconds, operating_start, operating_end, ...} },
      historical: { <channel>: {Y1:{baseline,actual}, ...} },
      day_split: { <channel>: [7 fractions Sat..Fri] }   # optional
    }
    """
    sh = plan.get("shrinkage", {})
    shrink_info = compound_shrinkage(sh.get("planned", 0), sh.get("unplanned", 0), sh.get("training", 0))
    shrink = shrink_info["total_shrinkage_pct"]
    anomalies = plan.get("anomaly_years", [])

    out = {"shrinkage": shrink_info, "channels": {}}

    for ch in plan.get("channels", []):
        params = plan.get("params", {}).get(ch, {})
        plan_vol = params.get("plan_volume", 0)
        hist = plan.get("historical", {}).get(ch, {})

        # impacts (YoY, for the year-trend chart) + combinations
        impacts = compute_yoy_series(hist)
        combos = generate_combinations(hist, anomalies, plan_vol)
        # Override: use the user-selected combo if given, else the recommended (top) one.
        selected_name = plan.get("selected_combos", {}).get(ch)
        best = next((c for c in combos if c["combo"] == selected_name), None) if selected_name else None
        if best is None:
            best = combos[0] if combos else None
        if best is not None:
            best["selected"] = True
        weekly = best["forecasted_volume"] if best else 0

        # daily split (Saturday-first): manual > decomposition > flat
        split, split_source, anchored = _resolve_split(plan, ch, weekly)
        daily = [round(weekly * f, 1) for f in split]
        busiest_idx = max(range(7), key=lambda i: daily[i]) if weekly else 0

        # intraday profile from per-year slot history (drives the interval shape if supplied)
        intraday_ch = plan.get("intraday_history", {}).get(ch) or {}
        profile, per_year_intraday = _intraday_profile(intraday_ch)

        intervals, peak_net, peak_gross = _channel_hc_for_day(
            ch, daily[busiest_idx], params, shrink, profile)

        # Multi-day: plan EACH day that has volume independently (Diwali etc.).
        days_hc = []
        for i, day_name in enumerate(DAYS):
            if daily[i] <= 0:
                continue
            d_iv, d_net, d_gross = _channel_hc_for_day(ch, daily[i], params, shrink, profile)
            days_hc.append({
                "day": day_name, "volume": daily[i],
                "peak_net_hc": d_net, "peak_gross_hc": d_gross,
            })

        # overlay data for the chart (only when shapes align with the interval count)
        intraday_overlay = None
        if profile and intervals and len(profile) == len(intervals):
            intraday_overlay = {
                "slots": [iv["start"] for iv in intervals],
                "per_year": per_year_intraday,
                "forecast": profile,
            }

        out["channels"][ch] = {
            "impacts": impacts,
            "combinations": combos,
            "recommended": best,
            "weekly_forecast": weekly,
            "daily": dict(zip(DAYS, daily)),
            "busiest_day": DAYS[busiest_idx],
            "split_source": split_source,
            "anchored": anchored,
            "intervals": intervals,
            "peak_net_hc": peak_net,
            "peak_gross_hc": peak_gross,
            "intraday_source": "history" if profile else "bell-curve",
            "intraday_overlay": intraday_overlay,
            "days_hc": days_hc,
        }

    return out
