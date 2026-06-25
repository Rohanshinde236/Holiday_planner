"""
Erlang C — voice staffing.

PORTED VERBATIM from the existing tool's data_engine.py (v2.0.2).
DO NOT change the logic/arithmetic — these formulas are frozen and golden-tested.
Only reorganised into a module; every result must match the original exactly.
"""

import math


def log_factorial(n: int) -> float:
    """Log-space factorial; Stirling approximation for n > 20 (error < 0.001%)."""
    if n <= 1:
        return 0.0
    if n <= 20:
        return sum(math.log(i) for i in range(2, n + 1))
    return (n * math.log(n) - n + 0.5 * math.log(2 * math.pi * n) + 1 / (12 * n))


def erlang_c(agents: int, intensity: float) -> float:
    """
    Erlang C probability that a call will wait.
    Pure log-space arithmetic -- correct for any agent count up to 2000.
    No factorial overflow, no ValueError for agents >= 171.
    """
    if agents <= 0 or intensity <= 0:
        return 1.0
    if intensity >= agents:
        return 1.0

    rho = intensity / agents
    safe_i = max(intensity, 1e-10)

    log_num = (agents * math.log(safe_i)
               - log_factorial(agents)
               + math.log(agents / (agents - intensity)))

    log_terms = [k * math.log(safe_i) - log_factorial(k) for k in range(agents)]

    max_log = max(log_num, max(log_terms) if log_terms else log_num)
    ec_num = math.exp(log_num - max_log)
    ec_den = ec_num + (1 - rho) * sum(math.exp(t - max_log) for t in log_terms)
    return min(1.0, max(0.0, ec_num / ec_den)) if ec_den > 0 else 1.0


def service_level_at_agents(
    agents: int,
    calls_per_hour: float,
    aht_seconds: float,
    sl_target_seconds: float
) -> float:
    """
    SL% achieved at a given agent count. Returns SL as fraction (0..1).
    mu carries per-HOUR units; the /3600 converts to the per-second rate inline.
    Algebraically identical to the JS slAtAgents() formula.
    """
    if calls_per_hour <= 0:
        return 1.0
    intensity = (calls_per_hour / 3600) * aht_seconds
    ec = erlang_c(agents, intensity)
    if agents <= intensity:
        return 0.0
    mu = 3600 / aht_seconds  # service rate per agent per HOUR (calls/hour)
    exponent = -(agents - intensity) * mu * sl_target_seconds / 3600
    sl = 1.0 - ec * math.exp(exponent)
    return max(0.0, min(1.0, sl))


def agents_for_sl(
    calls_per_hour: float,
    aht_seconds: float,
    sl_target_pct: float,
    sl_target_seconds: float,
    max_agents: int = 2000
) -> int:
    """
    Minimum agents required to meet SL target. Binary/linear search from
    ceil(intensity) upward. Guards against AHT=0 or calls=0.
    """
    if calls_per_hour <= 0 or aht_seconds <= 0:
        return 0
    intensity = (calls_per_hour / 3600) * aht_seconds
    min_agents = max(1, math.ceil(intensity) + 1)
    target = sl_target_pct / 100.0

    for n in range(min_agents, max_agents + 1):
        if service_level_at_agents(n, calls_per_hour, aht_seconds, sl_target_seconds) >= target:
            return n
    return max_agents
