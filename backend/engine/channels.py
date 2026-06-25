"""
Chat (concurrency) and Email (throughput) staffing models.

PORTED VERBATIM from data_engine.py (v2.0.2). Logic frozen — do not change.
Voice uses Erlang C (see erlang.py).
"""

import math


def chat_agents_required(
    chats_per_hour: float,
    aht_seconds: float,
    concurrency: float,
    occupancy_target_pct: float
) -> dict:
    """
    Chat staffing via concurrency model.
    Net agents = ceil(offered_load / concurrency).
    Gross agents = ceil(net / (occupancy_target / 100)).
    (Browser-parity HC uses net + compound shrinkage; the occupancy-based gross
    here is the backend figure documented in the original tool.)
    """
    if chats_per_hour <= 0:
        return {"net": 0, "gross": 0, "occupancy_actual": 0.0}

    offered_load = (chats_per_hour / 3600) * aht_seconds  # in Erlangs
    net = math.ceil(offered_load / concurrency)
    occupancy_actual = (offered_load / net) * 100 if net > 0 else 0
    gross = math.ceil(net / (occupancy_target_pct / 100))
    return {
        "net": net,
        "gross": gross,
        "occupancy_actual": round(occupancy_actual, 1)
    }


def email_agents_required(
    emails_per_day: float,
    aht_seconds: float,
    operating_hours: float,
    occupancy_target_pct: float,
    operating_start: str = "08:00",
    operating_end: str = "20:00"
) -> dict:
    """
    Email staffing via daily throughput (overnight-aware operating window).
    Emails handled per agent per day = (operating_hours * 3600 * occupancy) / AHT.
    Net agents = ceil(emails_per_day / throughput_per_agent). (net == gross here;
    shrinkage is applied by the caller.)
    """
    if emails_per_day <= 0:
        return {"net": 0, "gross": 0, "throughput_per_agent": 0}

    if operating_hours <= 0:
        start_h, start_m = map(int, operating_start.split(":"))
        end_h, end_m = map(int, operating_end.split(":"))
        start_mins = start_h * 60 + start_m
        end_mins = end_h * 60 + end_m
        operating_hours = ((end_mins - start_mins) % 1440) / 60
        if operating_hours <= 0:
            operating_hours = 12  # fallback

    throughput = (operating_hours * 3600 * (occupancy_target_pct / 100)) / aht_seconds
    throughput = max(throughput, 0.01)
    net = math.ceil(emails_per_day / throughput)
    gross = net
    return {
        "net": net,
        "gross": gross,
        "throughput_per_agent": round(throughput, 1),
        "operating_hours_used": round(operating_hours, 2)
    }
