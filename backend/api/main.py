"""
FastAPI app — wraps the pure engine. The API computes nothing itself; it validates
input (Pydantic) and delegates every number to engine/ (the single source of truth).

Run locally:
    cd backend
    uvicorn api.main:app --reload --port 5050
Docs at http://localhost:5050/docs
"""

import math
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from export.excel import build_workbook
from export.pdf import build_pdf
from .llm import client as llm, prompts as llm_prompts

from engine import (
    compound_shrinkage, gross_hc_ceil, agents_for_sl, service_level_at_agents,
    chat_agents_required, email_agents_required,
    distribute_volume_to_intervals, generate_combinations, optimise_shifts,
)
from engine.shifts_ilp import optimise_shifts_ilp
from engine import calendar as cal
from engine.accuracy import forecast_accuracy
from pydantic import BaseModel
from .models import (
    ShrinkageIn, ErlangIn, ChatIn, EmailIn, IntervalIn,
    CombinationsIn, ShiftOptimiseIn, PlanIn,
)
from .compute import compute_plan

app = FastAPI(title="WFM Holiday Planning Engine", version="3.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "WFM Holiday Planning Engine", "version": "3.0"}


@app.post("/api/shrinkage")
def api_shrinkage(body: ShrinkageIn):
    return compound_shrinkage(body.planned_leave_pct, body.unplanned_leave_pct, body.training_pct)


@app.post("/api/erlang_c")
def api_erlang_c(body: ErlangIn):
    net = agents_for_sl(body.calls_per_hour, body.aht_seconds, body.sl_target_pct, body.sl_target_seconds)
    grs = gross_hc_ceil(net, body.total_shrinkage_pct)
    intensity = (body.calls_per_hour / 3600) * body.aht_seconds if body.calls_per_hour > 0 else 0
    actual_sl = service_level_at_agents(net, body.calls_per_hour, body.aht_seconds, body.sl_target_seconds) * 100
    return {
        "calls_per_hour": body.calls_per_hour,
        "aht_seconds": body.aht_seconds,
        "intensity_erlangs": round(intensity, 2),
        "net_hc": net,
        "gross_hc": grs,
        "actual_sl_pct": round(actual_sl, 1),
        "shrinkage_pct": body.total_shrinkage_pct,
    }


@app.post("/api/chat_hc")
def api_chat_hc(body: ChatIn):
    result = chat_agents_required(body.chats_per_hour, body.aht_seconds, body.concurrency, body.occupancy_target_pct)
    result["gross_hc"] = gross_hc_ceil(result["net"], body.total_shrinkage_pct)
    result["shrinkage_pct"] = body.total_shrinkage_pct
    return result


@app.post("/api/email_hc")
def api_email_hc(body: EmailIn):
    result = email_agents_required(
        body.emails_per_day, body.aht_seconds, body.operating_hours,
        body.occupancy_target_pct, body.operating_start, body.operating_end,
    )
    result["gross_hc"] = gross_hc_ceil(result["net"], body.total_shrinkage_pct)
    result["shrinkage_pct"] = body.total_shrinkage_pct
    return result


@app.post("/api/interval_distribution")
def api_interval_distribution(body: IntervalIn):
    result = distribute_volume_to_intervals(
        body.daily_volume, body.operating_start, body.operating_end,
        body.interval_minutes, body.profile,
    )
    return {"intervals": result, "total_intervals": len(result)}


@app.post("/api/combinations")
def api_combinations(body: CombinationsIn):
    historical = {k: {"actual": v.actual, "baseline": v.baseline} for k, v in body.historical.items()}
    combos = generate_combinations(historical, body.anomaly_years, body.plan_volume)
    return {"combinations": combos, "total": len(combos)}


@app.get("/api/holidays/countries")
def api_holiday_countries():
    return cal.list_countries()


@app.get("/api/holidays/search")
def api_holiday_search(q: str = "", country: str = "IN", base_year: int = 2025):
    return {"matches": cal.search(q, country, base_year)}


@app.get("/api/holidays/dates")
def api_holiday_dates(name: str, country: str = "IN", base_year: int = 2025, years: int = 2):
    return cal.dates(name, country, base_year, years)


@app.post("/api/plan/compute")
def api_plan_compute(body: PlanIn):
    """Full pipeline for a whole plan — forecast, daily split, interval HC, peaks per channel."""
    return compute_plan(body.model_dump())


class AccuracyIn(BaseModel):
    items: list[dict]   # [{label, forecast, actual}]


@app.post("/api/accuracy")
def api_accuracy(body: AccuracyIn):
    """Post-holiday forecast-vs-actual accuracy (MAPE + bias)."""
    return forecast_accuracy(body.items)


@app.get("/api/llm/status")
def api_llm_status():
    return {"available": llm.available(), "model": llm.MODEL_CHAT}


@app.post("/api/plan/explain")
def api_plan_explain(body: PlanIn):
    if not llm.available():
        return {"available": False, "text": "No LLM key configured (set GROQ_API_KEY_* in backend/.env)."}
    plan = body.model_dump()
    result = compute_plan(plan)
    text = llm.chat(llm_prompts.explain_messages(result, plan), temperature=0.4)
    return {"available": True, "text": text}


@app.post("/api/plan/review")
def api_plan_review(body: PlanIn):
    if not llm.available():
        return {"available": False, "text": "No LLM key configured (set GROQ_API_KEY_* in backend/.env)."}
    plan = body.model_dump()
    result = compute_plan(plan)
    text = llm.chat(llm_prompts.review_messages(result, plan), temperature=0.2)
    return {"available": True, "text": text}


def _ai_texts(result, plan, include: bool):
    """Generate LLM explanation + review for the report (best-effort)."""
    if not include or not llm.available():
        return None, None
    explanation = review = None
    try:
        explanation = llm.chat(llm_prompts.explain_messages(result, plan), temperature=0.4)
    except Exception:
        pass
    try:
        review = llm.chat(llm_prompts.review_messages(result, plan), temperature=0.2)
    except Exception:
        pass
    return explanation, review


@app.post("/api/plan/export.xlsx")
def api_export_xlsx(body: PlanIn, ai: bool = True):
    plan = body.model_dump()
    result = compute_plan(plan)
    explanation, review = _ai_texts(result, plan, ai)
    data = build_workbook(result, plan, explanation, review)
    return Response(content=data,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=holiday-plan.xlsx"})


@app.post("/api/plan/export.pdf")
def api_export_pdf(body: PlanIn, ai: bool = True):
    plan = body.model_dump()
    result = compute_plan(plan)
    explanation, review = _ai_texts(result, plan, ai)
    data = build_pdf(result, plan, explanation, review)
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=holiday-plan.pdf"})


@app.post("/api/shift_optimise")
def api_shift_optimise(body: ShiftOptimiseIn):
    reqs = [r.model_dump() for r in body.hc_requirements]
    shifts = [s.model_dump() for s in body.available_shifts]
    if body.mode == "ilp":
        return optimise_shifts_ilp(
            reqs, shifts, body.operating_start, body.operating_end,
            body.interval_minutes, max_agents=body.available_agents,
        )
    return optimise_shifts(
        reqs, shifts, body.available_agents,
        body.operating_start, body.operating_end, body.interval_minutes,
    )
