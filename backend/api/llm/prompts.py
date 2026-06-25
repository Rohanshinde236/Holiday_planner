"""
Prompt builders for the LLM explain + review features.

The model is given the FINISHED, formula-computed numbers and asked only to put them
into words (explain) or to advise on inputs/assumptions (review). It is explicitly told
never to compute or change a number.
"""

import json

_GUARDRAIL = (
    "CRITICAL RULES:\n"
    "- Use ONLY the numbers provided in the data. Never invent, estimate, or recompute any figure.\n"
    "- If you reference a number, it must appear verbatim in the data.\n"
    "- You are a workforce-management (WFM) domain expert writing for call-centre planners.\n"
)


def _compact(result: dict, plan: dict) -> str:
    """Compact JSON of the plan + result for the model (drop bulky interval lists)."""
    channels = {}
    for ch, res in result.get("channels", {}).items():
        channels[ch] = {
            "recommended_combo": (res.get("recommended") or {}).get("combo"),
            "impact_pct": (res.get("recommended") or {}).get("blended_impact_pct"),
            "weekly_forecast": res.get("weekly_forecast"),
            "busiest_day": res.get("busiest_day"),
            "peak_net_hc": res.get("peak_net_hc"),
            "peak_gross_hc": res.get("peak_gross_hc"),
            "impacts_by_year": res.get("impacts"),
            "params": plan.get("params", {}).get(ch),
        }
    payload = {
        "holiday": plan.get("holiday", {}).get("name") if plan.get("holiday") else None,
        "shrinkage_pct": result.get("shrinkage", {}).get("total_shrinkage_pct"),
        "anomaly_years": plan.get("anomaly_years"),
        "channels": channels,
    }
    return json.dumps(payload, indent=2)


def explain_messages(result: dict, plan: dict) -> list:
    data = _compact(result, plan)
    return [
        {"role": "system", "content": _GUARDRAIL +
         "\nWrite a concise, manager-ready plain-English summary of this holiday staffing plan. "
         "Cover: how busy the holiday is expected to be vs normal, why that trend was chosen "
         "(mention excluded anomaly years if any), the peak staffing needed per channel, and one "
         "clear takeaway. 150-220 words. No bullet headers, flowing prose."},
        {"role": "user", "content": f"Plan data:\n{data}\n\nWrite the summary."},
    ]


def review_messages(result: dict, plan: dict) -> list:
    data = _compact(result, plan)
    anomalies = plan.get("anomaly_years") or []
    anomaly_note = (
        f"The ONLY anomaly-flagged years are: {anomalies}. Do NOT describe any other year as an "
        "anomaly or flagged. If a year is not in that list, it is treated as clean."
        if anomalies else
        "No years are flagged as anomalies. Do NOT claim any year is flagged."
    )
    return [
        {"role": "system", "content": _GUARDRAIL +
         "\nAct as a senior WFM analyst reviewing a colleague's plan. Identify: inputs that look "
         "unusual for the channel (e.g. AHT, SL, occupancy out of typical range), data-quality "
         "issues (outlier years, missing/odd values), missing assumptions, and whether the outputs "
         "look plausible given the inputs. Then give concise suggestions. You MUST NOT recompute or "
         "change any number — only flag and advise; the planner decides.\n"
         f"{anomaly_note}\n"
         "Output 4-8 short bullet points. Prefix each EXACTLY with one tag: [info], [caution], or [check]."},
        {"role": "user", "content": f"Plan data:\n{data}\n\nReview it."},
    ]
