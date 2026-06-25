"""Unit tests for the Erlang C voice formulas."""

import math
from engine import erlang_c, service_level_at_agents, agents_for_sl, log_factorial


def test_log_factorial_small():
    assert math.isclose(log_factorial(5), math.log(120), rel_tol=1e-9)


def test_erlang_c_overload_returns_one():
    # intensity >= agents => everyone waits
    assert erlang_c(5, 5) == 1.0
    assert erlang_c(5, 9) == 1.0


def test_erlang_c_in_range():
    p = erlang_c(14, 10.0)
    assert 0.0 <= p <= 1.0


def test_agents_for_sl_zero_guards():
    assert agents_for_sl(0, 360, 80, 20) == 0      # no calls
    assert agents_for_sl(100, 0, 80, 20) == 0      # AHT=0 guard


def test_agents_for_sl_meets_target():
    cph, aht, sl_pct, sl_sec = 260, 360, 80, 20
    n = agents_for_sl(cph, aht, sl_pct, sl_sec)
    # the chosen n meets the target; n-1 does not
    assert service_level_at_agents(n, cph, aht, sl_sec) >= 0.80
    assert service_level_at_agents(n - 1, cph, aht, sl_sec) < 0.80


def test_high_agent_count_no_overflow():
    # log-space must not blow up for large agent counts
    n = agents_for_sl(5000, 360, 80, 20)
    assert isinstance(n, int) and n > 0
