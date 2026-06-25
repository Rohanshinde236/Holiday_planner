"""
WFM Holiday Planner — pure formula engine.

This package is framework-free (no FastAPI, React, or LLM dependencies). It is the
single source of truth for all WFM math, ported verbatim from the verified v2.0.2 tool
and locked by golden tests. Do not change the logic.
"""

from .erlang import (
    log_factorial,
    erlang_c,
    service_level_at_agents,
    agents_for_sl,
)
from .shrinkage import compound_shrinkage, gross_hc, gross_hc_ceil, GROSS_SENTINEL
from .channels import chat_agents_required, email_agents_required
from .distribution import distribute_volume_to_intervals, day_index_forecast
from .forecast import (
    compute_impact_pct,
    compute_yoy_series,
    score_combination,
    get_all_subsets,
    generate_combinations,
)
from .shifts import optimise_shifts

__all__ = [
    "log_factorial", "erlang_c", "service_level_at_agents", "agents_for_sl",
    "compound_shrinkage", "gross_hc", "gross_hc_ceil", "GROSS_SENTINEL",
    "chat_agents_required", "email_agents_required",
    "distribute_volume_to_intervals", "day_index_forecast",
    "compute_impact_pct", "compute_yoy_series", "score_combination", "get_all_subsets", "generate_combinations",
    "optimise_shifts",
]
