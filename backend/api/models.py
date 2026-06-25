"""
Pydantic request/response schemas — the HARD validation layer (§7.3, §8.1).

Required fields have no default (must be supplied); optional fields carry the
documented defaults. Invalid input (e.g. AHT <= 0) is rejected here before any math runs.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class ShrinkageIn(BaseModel):
    planned_leave_pct: float = Field(0, ge=0, le=100)
    unplanned_leave_pct: float = Field(0, ge=0, le=100)
    training_pct: float = Field(0, ge=0, le=100)


class ErlangIn(BaseModel):
    calls_per_hour: float = Field(..., ge=0)          # required *
    aht_seconds: float = Field(..., gt=0)             # required *
    sl_target_pct: float = Field(80, ge=0, le=100)
    sl_target_seconds: float = Field(20, gt=0)
    total_shrinkage_pct: float = Field(0, ge=0, lt=100)


class ChatIn(BaseModel):
    chats_per_hour: float = Field(..., ge=0)          # required *
    aht_seconds: float = Field(..., gt=0)             # required *
    concurrency: float = Field(2.5, gt=0)
    occupancy_target_pct: float = Field(80, gt=0, le=100)
    total_shrinkage_pct: float = Field(0, ge=0, lt=100)


class EmailIn(BaseModel):
    emails_per_day: float = Field(..., ge=0)          # required *
    aht_seconds: float = Field(..., gt=0)             # required *
    operating_hours: float = Field(0, ge=0)           # 0 = auto-derive
    operating_start: str = "08:00"
    operating_end: str = "20:00"
    occupancy_target_pct: float = Field(75, gt=0, le=100)
    total_shrinkage_pct: float = Field(0, ge=0, lt=100)


class IntervalIn(BaseModel):
    daily_volume: float = Field(..., ge=0)            # required *
    operating_start: str = "08:00"
    operating_end: str = "20:00"
    interval_minutes: int = Field(30, gt=0)
    profile: Optional[list[float]] = None


class YearData(BaseModel):
    actual: float
    baseline: float


class CombinationsIn(BaseModel):
    historical: dict[str, YearData] = Field(..., min_length=1)  # required *
    anomaly_years: list[str] = []
    plan_volume: float = Field(..., ge=0)             # required *


class ShiftDef(BaseModel):
    name: str
    start: str
    end: str


class HcReq(BaseModel):
    interval: int
    start: str
    net_hc: float


class ShiftOptimiseIn(BaseModel):
    hc_requirements: list[HcReq] = Field(..., min_length=1)     # required *
    available_shifts: list[ShiftDef] = Field(..., min_length=1) # required *
    operating_start: str = "08:00"
    operating_end: str = "20:00"
    interval_minutes: int = Field(30, gt=0)
    mode: Literal["greedy", "ilp"] = "ilp"            # default: optimal
    available_agents: int = Field(100, ge=0)          # used by greedy / ILP cap


class ShrinkageParts(BaseModel):
    planned: float = Field(8, ge=0, le=100)
    unplanned: float = Field(5, ge=0, le=100)
    training: float = Field(3, ge=0, le=100)


class PlanIn(BaseModel):
    """Full-plan compute request. params/historical/day_split are keyed by channel."""
    channels: list[str] = Field(..., min_length=1)              # required *
    queue: dict | None = None                                   # {name, region, type} label
    shrinkage: ShrinkageParts = ShrinkageParts()
    anomaly_years: list[str] = []
    params: dict[str, dict] = Field(..., min_length=1)          # required *
    historical: dict[str, dict] = Field(default_factory=dict)
    day_split: dict[str, list[float]] = Field(default_factory=dict)
    # Optional richer history (enables day-shape decomposition, §5 step 5)
    daily_history: dict[str, dict[str, list[float]]] = Field(default_factory=dict)  # {ch:{year:[7]}}
    normal_week: dict[str, list[float]] = Field(default_factory=dict)               # {ch:[7]}
    intraday_history: dict[str, dict[str, list[float]]] = Field(default_factory=dict)  # {ch:{year:[slots]}}
    selected_combos: dict[str, str] = Field(default_factory=dict)  # {channel: combo name override}
    holiday: dict | None = None                                  # {name, plan_date, history:[{slot,date}]}
