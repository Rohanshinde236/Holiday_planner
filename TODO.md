# WFM Holiday Planner — TODO / Review list

Running list of changes to make. We review these together; I implement when confirmed.
Status: ⬜ pending · 🔵 in progress · ✅ done

---

## To do (added during review)

- [x] ✅ **CRITICAL — Combination/forecast model switched to YoY (matches the real UI)** — DONE.
  - Ported index.htm's YoY model: `YoY = (act[y]−act[prior])/act[prior]`; N years → N−1 points
    → subsets; single-year baseline path + 2-year special combo; scoreCombo unchanged.
  - VERIFIED LIVE vs old UI: Christmas voice → 3 combos, Y1 −29.41/Y2 −8.93/Avg −19.17,
    scores 76/67/56.1, Y1 recommended — exact match to the old-tool screenshot. 52 tests pass.
  - ✅ Sub-items now DONE: calendar-year labels ("Last Year 2025"/"2024"/"Avg(2024+2023)"),
    Override dropdown (selected_combos → recompute, verified Y1 2965 → Y2 3825), single-year caveat.

- [x] ✅ **Queue name required (*) + validation** — DONE. Red `*`, inline "Required to compute"
      hint, and Compute is blocked (jumps to Setup) when empty.
- [ ] ⬜ **(Option) Move anomaly flag into each year row** — users read the separate Anomaly
      checkbox row as "selecting years again". Consider a 🚩 toggle inside each Historical year
      row instead, so it reads as "flag this year as abnormal" (clearer; not re-selecting years).


- [x] ✅ **Per-year auto-filled + editable holiday-date fields, driven by "Years of history"** — DONE.
  - "Years of history" now lives on the plan and drives the year slots in Anomaly + Historical
    + daily/intraday grids (set 2 → only Y1,Y2 show). Calendar dates are editable per year.
    "Festival not listed — enter dates manually" button seeds today's date (editable).
  - Remaining sub-bit: show per-year dates in the dashboard year-comparison labels (minor).

- [x] ✅ **IBU% (voice) / Utilization% (chat) divisor** — DONE.
  - Matched original exactly: `gross = ceil( ceil(net/utilFrac) / (1−shrink) )`, only when
    utilFrac<1, clamped [0.30,1.0]; email/blended no divisor. Net HC stays raw (pre-util).
  - Added `ibu_pct`/`utilization_pct` params + Setup inputs + 7 tests (test_ibu.py). Golden
    48/57 unchanged at 100%; IBU 85 → higher gross. 50 tests pass.
- [x] ✅ **AHT unit selector (Minutes / Seconds)** — DONE. Per-channel unit dropdown; converts to
      seconds internally (aht_seconds stays the source of truth).

- [x] ✅ **"Years of history" drives the visible year slots everywhere** — DONE (see top item).

- [x] ✅ **Queue / Region / Queue-Type context bar** — DONE. Lightweight: labels the plan
      (name/region/type), no gate; flows into the PDF + Excel report header. Verified in report.

- [x] ✅ **Manual per-year holiday dates** — DONE via the calendar card: dates are editable, and
      "Festival not listed — enter dates manually" seeds today's date. (Standalone Historical-tab
      date fields not needed — handled in the calendar card.)
- [ ] ⬜ **(Minor) Per-year layout option for Historical** — old tool groups by year (card per
      year, channels inside); ours groups by channel (table, years inside). Same data, transposed.
      Optional toggle if a per-year view is preferred.

---

- [~] 🔵 **Report completeness** — multi-day table + intraday overlay + **queue label DONE**.
      STILL pending: accuracy (MAPE) section (needs actuals input captured first).

---

## Known pending (from the gap review — not yet UI-wired)

- [x] ✅ **Accuracy UI panel** — DONE. New "9 — Accuracy" tab: enter post-holiday actuals →
      MAPE + bias (over/under) per channel + overall, green/amber/red bands. Verified live.
- [x] ✅ **Blended channel in the UI** — DONE. Added to channel picker with seeded defaults
      (voice%/chat%/voice_aht/chat_aht); compute does voice Erlang + chat concurrency weighted. Verified (73/87).
- [x] ✅ **AI panel auto-runs both** — explanation + review now generate automatically (no buttons);
      shown side-by-side with a ↻ Regenerate option.
- [x] ✅ **LLM review polish** — DONE: prompt now states the authoritative anomaly list (stops the
      Y1/Y2 mislabel); review tags render as icons (🔵 info / 🟡 caution / 🔴 check) in the UI.
- [ ] ⬜ (old line, superseded) tighten prompt so it stops mislabelling anomaly years
      (said "Y1, Y2" when only Y1 flagged); optionally swap `[info]/[caution]/[check]` brackets for icons.

---

## Deferred (agreed v2 — revisit later)

- [ ] ⬜ Cost modelling (agents → money / budget)
- [ ] ⬜ Scenario comparison (side-by-side what-if plans)
- [ ] ⬜ Dashboard / KPI summary view

---

## Notes / decisions log
- Formulas are frozen & verified identical to the old `data_engine.py` (live comparison passed).
- Persistence is file-based (JSON/CSV/PDF/Excel) — no database, no git, local only.
- Backend must be running for dropdowns/compute; use `uvicorn api.main:app --reload --port 5050`.
