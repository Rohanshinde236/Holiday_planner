# WFM Holiday Planner — Rebuild Design Spec

**Status:** Draft for review
**Author:** Prepared with Claude Code
**Date:** 2026-06-18
**Reference implementation:** `../holiday-planning/` (existing v2.0.2 tool — kept untouched as the source of truth for behaviour)

---

## 1. Purpose & guiding principle

Rebuild the existing **Holiday Planning WFM Tool** on a modern, maintainable stack
**without changing the problem statement or any of the WFM formulas.**

> **Golden rule:** The math is sacred. Same inputs → same outputs as today.
> Everything *around* the math (UI, structure, persistence, optimisation, reporting) is modernised.

The tool's job is unchanged: help a WFM scheduler plan call-centre staffing for a
holiday period, answering three questions in sequence —
**What volume? → How many agents? → Which shifts?**

---

## 2. Goals & non-goals

### Goals
- Modern, maintainable architecture (React frontend + strong Python backend).
- **Single source of truth** for all math — kills the current JS/Python duplication.
- **Provably-optimal** shift scheduling via ILP (upgrade over today's greedy heuristic).
- **LLM-powered plan explainer** — turns computed plans into plain-English reports.
- Full automated test coverage with **golden tests** locking in verified numbers.
- Real server-side data persistence (fixes the browser last-write-wins overwrite bug).

### Non-goals (explicitly out of scope)
- ❌ Changing any WFM formula or its result.
- ❌ Letting the LLM compute any number.
- ❌ Connecting to live ACD/WFM platforms (data still entered/imported manually).
- ❌ Multi-tenant SaaS / billing.

---

## 3. Architecture — three clean layers

```
┌──────────────────────────────────────────────┐
│  React + Vite frontend   (presentation only)  │  the 8 tabs, charts, import/export
└─────────────────┬──────────────────────────────┘
                  │  REST API (JSON over HTTP)
┌─────────────────▼──────────────────────────────┐
│  Python FastAPI backend  (ALL math — authority)│  Erlang C, shrinkage, forecast,
│  + Pydantic validation   + pytest golden tests │  scoring, ILP shift optimisation,
│  + Holiday Calendar (holidays lib)             │  smart holiday search + auto-dates
└─────────────────┬──────────────────────────────┘
                  │  reads finished plan (never computes)
┌─────────────────▼──────────────────────────────┐
│  LLM assistant layer  (Grok/Gemini/NVIDIA)     │  explains plans + reviews inputs/outputs
│  pluggable · explainer + reviewer/advisor      │  with suggestions (advisory only)
└────────────────────────────────────────────────┘

           ┌──────────────────────────┐
           │  File store (no database) │  JSON (save/resume) · CSV · PDF · Excel
           └──────────────────────────┘
```

**Separation of concerns:**
- **Formulas decide** the numbers (Steps 1–7).
- **ILP arranges** the optimal shifts (Step 8) — uses the numbers, never computes volume/HC.
- **LLM explains** the finished plan in words — only reads, never computes.

---

## 4. Tech stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | **React + Vite + TypeScript** | Modern, componentised, type-safe |
| UI charts | **Chart.js** (or Recharts) | Same charts as today |
| Styling | **CSS custom properties** (keep token approach) or Tailwind | Preserve themeable design system |
| Backend | **Python 3.11 + FastAPI** | Typed, async, auto OpenAPI docs |
| Validation | **Pydantic v2** | Rejects bad inputs → guarantees accuracy |
| Math | **NumPy** | Same numerical core as today |
| Optimiser | **OR-Tools** (or PuLP) | True optimal ILP shift scheduling |
| Holiday calendar | **`holidays`** Python library | Offline holiday search + moving-date lookup (key regions) |
| Excel export | **`openpyxl`** | Multi-sheet formatted workbook |
| PDF export | **`reportlab`** / `weasyprint` | Manager-ready PDF report (+ optional LLM narrative) |
| Tests | **pytest** (backend), **Vitest** (frontend) | Golden + unit tests |
| LLM | **Pluggable** — Grok / Gemini / NVIDIA (OpenAI-compatible) | Plan explanation / review (advisory) |
| Persistence | **Files** — JSON / CSV / PDF / Excel | Import/export; no database (see §8) |

---

## 5. The formula engine — what is preserved (the heart)

Every formula is ported **verbatim** in behaviour into a pure, dependency-light Python
module (`engine/`), then locked with golden tests.

| Step | Calculation | Formula (unchanged) |
|---|---|---|
| 1 | Compound shrinkage | `1 − (1−PL)(1−UL)(1−TR)` |
| 2 | Year-on-year impact % | `(actual − baseline) / baseline × 100` |
| 3 | Combination score | `0.40·consistency + 0.30·richness + 0.30·recency − anomaly penalty` |
| 4 | Forecast volume | `plan × (1 + avg_impact/100)` |
| 5 | Daily split | day-shape decomposition / DOW split |
| 6a | Interval distribution | volume × interval weights (overnight-aware) |
| 6b-Voice | Headcount | **Erlang C** (log-space, up to 2000 agents) |
| 6b-Chat | Headcount | concurrency: `ceil(load / sessions_per_agent)` |
| 6b-Email | Headcount | throughput: `ceil(daily / ((hours·3600·occ)/AHT))` |
| 6c | Net → Gross | `gross = ceil(net / (1 − shrinkage))` |
| 7 | Coverage gap | `coverage − gross_required` |

### Domain constraints preserved (non-negotiable)
- HC vs FTE always distinct.
- Shrinkage always compound (never blended).
- Erlang C = voice only; chat = concurrency; email = throughput.
- Gross HC used in all gap analysis & shift recommendation.
- Saturday-first week ordering everywhere.
- Self-describing, grain-accurate metric labels.

### Golden tests (the accuracy guarantee)
Verified outputs captured from the existing engine become hard-asserted tests:

| Case | Expected output |
|---|---|
| Christmas voice | 48 net / **57 gross** |
| Diwali voice | 68 / **81** |
| Diwali chat | 15 / **18** |
| Diwali email | 13 / **16** |
| Shrinkage 8/5/3 | **15.22%** (×1.1796) |
| Christmas best combo | **Avg(Y2+Y3)** (Y1 COVID excluded) |
| Diwali best combo | **Avg(Y1+Y2+Y3)** |

**The build cannot ship unless every golden number matches exactly.**

---

## 5.1 Holiday Calendar & Smart Search (NEW feature)

Replace manual date entry with a **searchable global holiday calendar** that auto-fills
the correct festival dates across history — including holidays whose dates *move* each
year (lunar festivals).

### User flow
```
1. Type in search bar:  "ganesh"
        → typeahead suggests: "Ganesh Chaturthi (India)"
2. Select it + choose years of history: e.g. 2 years
3. Tool auto-fills the correct date per year (pulled from the calendar):
        Plan year 2025 → 27 Aug
        Y1 (2024)      → 07 Sep      ← moving lunar date, filled automatically
        Y2 (2023)      → 19 Sep      ← filled automatically
4. User only enters the volumes — dates are done, and correct.
```

### Why it matters
- Festivals like **Ganesh Chaturthi** and **Diwali** move every year (lunar calendar);
  **Independence Day** is fixed. Manual entry is error-prone.
- Correct dates make the **day-shape decomposition more accurate** — the engine anchors
  the volume spike/dip to the festival's actual *weekday*.

### Data source
- **`holidays` Python library** — offline, free, no API key, accurate for major festivals.
- **Scope: key regions** mapped from the queue context (APJ / EMEA / AMER / LATAM) to
  representative countries, e.g.:
  | Region | Representative countries (initial) |
  |---|---|
  | APJ | India, Australia, Japan, Singapore |
  | EMEA | UK, Germany, UAE, South Africa |
  | AMER | USA, Canada |
  | LATAM | Brazil, Mexico, Argentina |
- India is the primary/default country (matches the sample holidays).

### Backend endpoints (new)
| Endpoint | Purpose |
|---|---|
| `GET /api/holidays/search?q=&country=` | Typeahead — returns matching holiday names |
| `GET /api/holidays/dates?name=&country=&base_year=&years=N` | Returns the date of that holiday for base year + previous N years |
| `GET /api/holidays/countries` | List supported countries grouped by region |

### Accuracy note
Holiday dates are sourced from the maintained `holidays` library, not hand-entered.
Date-lookup results for moving festivals (e.g. Diwali 2023=12 Nov, 2024=01 Nov, 2025=20 Oct)
will be added to the **golden test suite** so date regressions are caught automatically.

---

## 5.2 Post-holiday actuals & forecast-accuracy tracking (NEW feature)

Close the loop: after a holiday passes, record what *actually* happened and measure how
good the forecast was — so the tool gets smarter each cycle.

### Flow
```
Before holiday:  tool forecasts volume + HC, plan is saved
After holiday:   planner enters ACTUALS (actual volume, actual HC used, actual SL hit)
        ↓
Tool computes accuracy:
   - Volume forecast error  (MAPE: |forecast − actual| / actual)
   - HC variance            (planned vs actually-needed)
   - SL achieved vs target
        ↓
The actual becomes a new historical year automatically → feeds next year's combination engine
```

### Why it matters
- Turns the tool from one-shot calculator into a **continuous-improvement loop**.
- Surfaces systematic bias (e.g. "we consistently over-forecast Diwali by 8%").
- The recorded actual auto-populates the next planning cycle's Y1 slot — no re-entry.

### Endpoints / data
| Endpoint | Purpose |
|---|---|
| `POST /api/plans/{id}/actuals` | Record post-holiday actuals |
| `GET /api/plans/{id}/accuracy` | Forecast-vs-actual accuracy report |

Accuracy metrics (MAPE, variance) are deterministic formulas — added to the golden tests.

---

## 5.3 Excel / PDF export (NEW feature)

Beyond raw JSON, produce **formatted, manager-ready deliverables**.

| Format | Contents | Library |
|---|---|---|
| **Excel (.xlsx)** | Multi-sheet workbook: Setup, Historical, Forecast, HC table (interval-level), Shift plan, Accuracy — **plus both diagrams embedded as images** | `openpyxl` |
| **PDF report** | Holiday, forecast rationale, peak HC, shift plan — **plus BOTH diagrams: (1) all-years yearly trend + forecast, and (2) intraday time-slot overlay** — optionally with the **LLM-written narrative** (§7) | `reportlab` or `weasyprint` |

> **Export must include both diagrams:** the yearly all-years chart (§5.4 chart 1) **and** the
> time-slot intraday overlay (§5.4 chart 6). The intraday chart is included whenever per-year
> intraday data (§5.3a) is available; otherwise the export notes it was not provided.

### Endpoints
| Endpoint | Purpose |
|---|---|
| `GET /api/plans/{id}/export.xlsx` | Download formatted Excel workbook |
| `GET /api/plans/{id}/export.pdf` | Download formatted PDF report |

The PDF report is the natural home for the LLM plan explanation — numbers from the engine,
narrative from the LLM, in one shareable document.

---

## 5.3a Optional per-year intraday profiles (NEW feature)

Let the user optionally supply each historical year's **volume per time-slot**
(08:00–08:30 … 11:00–12:00 …), per channel — not just the yearly total.

### Why
- **Accuracy:** the forecast's intraday distribution is then built from the **real historical
  shape** (recency-weighted) instead of a generic bell curve. If the true peak is 14:00, not
  noon, peak-interval HC reflects that.
- **Visualisation:** unlocks the all-years + forecast intraday overlay chart (§5.4, chart 6).

### How it behaves
| Provided? | Forecast intraday shape | Chart |
|---|---|---|
| **Yes** (some/all years) | Recency-weighted average of supplied historical slot shapes | Overlay of each year + forecast |
| **No** | Falls back to bell curve / day-split (current behaviour) | Forecast curve only |

### Input
- **Optional** (no asterisk) — never blocks calculation.
- Entered in a per-year slot grid, **or imported via CSV/Excel** (paste an intraday export
  rather than typing ~28 slots by hand).
- Stored in the plan JSON alongside the yearly totals.

---

## 5.4 Report visualisations (charts)

The report includes charts that **display** engine-computed numbers (they never compute).

| # | Chart | Type | Shows |
|---|---|---|---|
| 1 | **Year trend + forecast** | Line | Past years' actuals + dashed projection to the predicted year ("compare 2 old years + last year + prediction") |
| 2 | **Baseline vs Actual per year** | Grouped bar | Normal-week vs holiday volume each year (size of holiday effect) |
| 3 | **Daily staffing curve** | Line / area | Agents needed across the day (the interval peak) |
| 4 | **Coverage: required vs planned** | Bar + line | Gross HC needed vs scheduled; red where short |
| 5 | **Forecast vs Actual** (post-holiday) | Bar | Predicted vs what happened (accuracy, §5.2) |
| 6 | **Intraday overlay: all years + forecast** | Line | Each year's per-time-slot shape overlaid with the forecast (needs §5.3a intraday data) |

Chart 1 (line) is the primary "history vs forecast" view; a grouped-bar variant is offered
for direct year-to-year comparison.

### How they're generated (one definition, two outputs)
- **On screen:** **Chart.js** (same library as the current tool) — interactive, hover values.
- **In the PDF (§5.3):** the same chart rendered to a PNG and embedded in the report.
- **Guardrail:** charts are presentation only — every value plotted comes from the
  deterministic engine. No chart computes a number.

---

## 5.5 Holiday duration — single-day OR multi-day (NEW feature)

A holiday can be **one day** (default) or a **multi-day period** — chosen per holiday.
Use multi-day only when the festival needs it; everything else stays single-day and simple.

| Mode | When | Behaviour |
|---|---|---|
| **Single day** (default) | Independence Day, New Year's Day, etc. | One forecast → one HC plan → one shift plan (current behaviour) |
| **Multi-day** (opt-in) | Diwali (~5 days), Christmas–New Year week, etc. | The holiday is a **date range**; **each day is planned independently** — its own forecast, HC, and shifts — shown together |

### Multi-day flow (e.g. Diwali 20–24 Oct)
```
Diwali period
├─ 20 Oct (Dhanteras)   → forecast → HC → shifts
├─ 21 Oct               → forecast → HC → shifts
├─ 22 Oct (main day)    → forecast → HC → shifts   ← typically the peak
├─ 23 Oct               → forecast → HC → shifts
└─ 24 Oct (Bhai Dooj)   → forecast → HC → shifts
```

### How it fits the rest of the design
- **Calendar (§5.1):** for known multi-day festivals, auto-suggests the full date range.
- **Formulas:** unchanged — each day runs through the same engine (no math change).
- **History:** stores per-day actuals across years for multi-day holidays.
- **Reports/charts:** multi-day holidays show the days side by side; single-day shows one.
- **Data model:** a holiday holds `days[]` (length 1 for single-day) — single-day is just the
  N=1 case, so there is one consistent model, not two.

> Default is single-day. Multi-day is opt-in per holiday — no extra effort unless you need it.

---

## 6. ILP shift optimiser (the one upgrade to behaviour)

**Scope: Step 8 only.** ILP does not touch volume, forecast, or headcount —
those remain formula-based. It takes the gross-HC-per-interval requirement
(already computed by Erlang C et al.) as a **fixed input** and finds the
**leanest set of shifts** that covers it.

- **Variables:** agents per shift template (integers).
- **Constraints:** every interval covered (`coverage ≥ gross_required`), shift-length
  rules, optional max-pool / min-staffing rules.
- **Objective:** minimise total agents (or total cost).
- **Solver:** OR-Tools CBC/SCIP — returns a **provably optimal** roster.

**Safety test:** assert every interval's scheduled coverage ≥ required — ILP can never
optimise itself into under-staffing.

**Note on parity:** HC numbers stay identical to today; the *shift allocation* may
differ from the old greedy result (fewer/equal agents) — this is the intended accuracy
gain. Optionally keep greedy as a fast "draft" mode alongside ILP "optimal" mode.

---

## 7. LLM assistant layer — explainer + reviewer/advisor

The LLM does two jobs: **explain** the plan, and **review** the inputs/outputs with
suggestions. Both are advisory — it never computes or alters a number.

> **Hard guardrail:** review ≠ recompute. The LLM flags and suggests; the human decides
> and (if they agree) changes an input, which re-runs the **deterministic** engine. The LLM
> never substitutes its own figure or overrides the engine output.

### 7.1 Explainer (report generator)
- **Input:** the finished, formula-computed plan (JSON of locked numbers).
- **Output:** plain-English narrative — rationale for the recommendation, peak staffing,
  shift summary, manager-ready brief (also embeddable in the PDF export, §5.3).

### 7.2 Reviewer / advisor (NEW)
Acts as a senior-WFM-analyst second pair of eyes. Catches **human mistakes in inputs and
judgment** — which is where real errors occur (the math itself is golden-tested, so there
are no math errors to find).

| Review type | Example flag |
|---|---|
| Input looks off | "AHT 360s set on *chat* — chat is usually 480s+. Did you mean voice?" |
| Data quality | "Y1 is 40% below Y2/Y3 — looks like an outlier; consider flagging as anomaly." |
| Unit / consistency | "Plan volume 4,200 but baselines ~9,000 — are both weekly?" |
| Missing assumption | "No day-split entered → flat week assumed → likely understates the peak." |
| Output plausibility | "57 agents for ~384 calls/hr at 360s AHT is consistent with Erlang C — sound." |
| Suggestion | "Combo relies on a single year (low confidence) — adding Y3 would strengthen it." |

Output is a list of advisory notes (severity: info / caution / check-this), shown to the
user. Acting on a suggestion = the user edits an input → engine recomputes deterministically.

### 7.3 Two-layer input checking (clean separation)
| Layer | Type | Role | Example |
|---|---|---|---|
| **Pydantic validation** | Deterministic code | **Rejects** invalid input (hard rules) | AHT must be > 0; percentages sum to 100 |
| **LLM review** | Judgment / advisory | **Flags** unusual-but-valid input (soft) | "AHT 120s is valid but unusually low" |

### Config & API key — provider-agnostic (pluggable LLM)
- **Provider:** pluggable — **xAI Grok**, **Google Gemini**, or **NVIDIA NIM** (the user's
  existing keys). Claude/OpenAI can also slot in. Not tied to any single vendor.
- **One adapter:** Grok, NVIDIA NIM, and Gemini all expose **OpenAI-compatible** chat APIs,
  so a single OpenAI-compatible client handles all of them — configure three values:
  | Setting | Example (env var) |
  |---|---|
  | `LLM_BASE_URL` | `https://api.x.ai/v1` · `https://integrate.api.nvidia.com/v1` · Gemini OpenAI-compat URL |
  | `LLM_API_KEY` | the user's Grok / Gemini / NVIDIA key |
  | `LLM_MODEL` | e.g. `grok-2`, `gemini-1.5-pro`, an NVIDIA NIM model id |
- **Key handling:** read from a local environment variable / `.env` — **never** hardcoded.
  Swapping providers = changing these env vars; no code change.
- **Optional by design:** if no key is configured, the tool works fully — Explain/Review are
  simply hidden/disabled. The LLM is an add-on layer, never a hard dependency.
- **Cost:** pay-as-you-go per the chosen provider; explain/review are small requests.
- **Privacy:** this is the **only** outbound call — when the user clicks Explain/Review, the
  computed plan (numbers) is sent to the chosen provider to generate text. Everything else is
  100% local. Opt-in, so the user controls when any data leaves the machine.
- **Endpoints:** `POST /api/plans/{id}/explain`, `POST /api/plans/{id}/review`.

### 7.4 LLM usage map — where it IS required vs where it must NOT be used

Rule of thumb: **LLM only for language (explain / advise). Everything that produces a
number is pure formula or solver — NO LLM.** ✱ = LLM used; everything else = no LLM.

| Step / feature | Method | LLM? |
|---|---|---|
| 1. Shrinkage | Formula | ❌ No LLM |
| 2. Impact % | Formula | ❌ No LLM |
| 3. Combination scoring | Formula | ❌ No LLM |
| 4. Forecast volume | Formula | ❌ No LLM |
| 5. Daily split | Formula | ❌ No LLM |
| 6. Headcount (Erlang C / chat / email) | Formula | ❌ No LLM |
| 6c. Net → Gross | Formula | ❌ No LLM |
| 7. Coverage gap | Formula | ❌ No LLM |
| 8. Shift allocation | ILP solver | ❌ No LLM |
| Holiday calendar search & dates | `holidays` library lookup | ❌ No LLM |
| Post-holiday accuracy (MAPE, variance) | Formula | ❌ No LLM |
| Input validation (hard rules) | Pydantic | ❌ No LLM |
| JSON / CSV / Excel export | Serialisers | ❌ No LLM |
| **Explain the plan (narrative)** | LLM (Grok/Gemini/NVIDIA) | **✱ LLM required** |
| **Review inputs/outputs + suggestions** | LLM (Grok/Gemini/NVIDIA) | **✱ LLM required** |
| **PDF report narrative text** | LLM (reuses Explain output) | **✱ LLM (text only)** |

**Net result:** the LLM touches the system in exactly **two** places — *Explain* and
*Review* — both producing **words, never numbers**. The PDF just embeds the Explain text.
Every value-producing step is deterministic and golden-tested. If a feature can be done by
a formula, it **is** — the LLM is never used "just because it's there."

---

## 8. Data & persistence — file-based (no database)

**Decision:** keep it simple — persistence is via files the user imports/exports. **No
database** for now. This matches the original tool's philosophy and removes all server-state
and ops complexity. (A database can be added later if team sharing / live multi-user becomes
a requirement — see §12.)

### Plan model (in-memory; serialised to file)
Queue/Region context, Holiday, HistoricalYear (Y1–Y5), Channel params, DOW split,
Shift templates, computed results, and post-holiday actuals — all held as one plan object.

### File formats
| Format | Direction | Contents |
|---|---|---|
| **JSON** | import + export | Full session/plan state — the canonical save format (re-importable) |
| **CSV** | export | Flat tables (HC-per-interval, shift plan, historical) for spreadsheets |
| **PDF** | export | Formatted manager report (§5.3), optional LLM narrative |
| **Excel (.xlsx)** | export | Multi-sheet workbook (§5.3) |

### How "saving" works
- **Save a plan** → Export JSON (download a file the user keeps).
- **Resume a plan** → Import that JSON file back.
- **Post-holiday actuals (§5.2)** → stored inside the plan JSON; re-import to compare
  forecast vs actual and roll the actual into the next cycle's history.
- **Backward compatibility:** import existing exported JSON plans from the v2.0 tool.

> No silent overwrites, no server state — the user owns their files. Trade-off: no automatic
> cross-device sync or concurrent team editing (acceptable for now; revisit in §12).

---

## 8.1 Input fields — required (*) vs optional

Every input the user types is classified as **required** or **optional**:

- **Required fields** show a red asterisk **\*** next to the label. The form cannot proceed
  (calculate) until they are filled. An empty required field shows an inline error.
- **Optional fields** have **no asterisk** — they have sensible defaults and can be left
  blank. Leaving them blank uses the default (e.g. shrinkage, day-split).

This is enforced in **two places that agree**: the UI marks/blocks (asterisk + inline error)
and the backend **Pydantic** model declares the same fields required vs optional-with-default.

### Required (must be filled) — marked \*
| Field | Why required |
|---|---|
| Holiday name \* | Identifies the plan |
| Holiday date \* (or via calendar search) | Anchors the day-shape forecast |
| Channels \* (≥1 selected) | Nothing to compute without a channel |
| Plan volume \* (per selected channel) | The base number the forecast scales |
| AHT \* (per selected channel) | Drives all HC math |
| SL target % \* and SL seconds/hours \* (per channel) | Defines the staffing target |
| Operating hours start \* / end \* | Defines the interval grid |
| At least one historical year \* (baseline + actual) | Needed to compute impact % / forecast |

### Optional (have defaults) — no asterisk
| Field | Default if blank |
|---|---|
| Shrinkage (planned/unplanned/training) | 8% / 5% / 3% |
| Daily volume split | flat / auto day-shape |
| Anomaly flag & note | none |
| Plan source label | blank |
| Chat concurrency | 2.5 |
| Occupancy % (chat/email) | 80% / 75% |
| Blended split | 60% voice / 40% chat |
| Shift templates | standard set |
| Years of history (2–5) | as entered (min 1) |

> Convention: **\*** = required & blocking. No asterisk = optional with a default.
> Required/optional status is identical in the UI and the Pydantic schema (single source of truth).

---

## 9. Feature-parity checklist (must not be lost)

- [ ] 5-year history (Y1–Y5) in all engines & combination matrix
- [ ] All-subsets combination generation (up to 31)
- [ ] Anomaly flags + manual override ("Clean"/force-include)
- [ ] Queue/Region context gate (APJ/EMEA/AMER/LATAM, DB/OSP)
- [ ] Overnight operating windows (cross-midnight intervals & shifts)
- [ ] Blended channel (weighted voice + chat)
- [ ] Excel/CSV import + JSON import/export (server-side via openpyxl/pandas)
- [ ] Day-shape holiday decomposition (not pure DOW rotation)
- [ ] **Holiday calendar search + auto-date-fill across years (NEW)**
- [ ] **Moving lunar-festival dates handled correctly (NEW)**
- [ ] **Holiday duration: single-day (default) or multi-day period, per holiday (NEW)**
- [ ] **Multi-day holidays plan each day independently; single model (days[], N=1 default) (NEW)**
- [ ] **Post-holiday actuals capture + forecast-accuracy report (NEW)**
- [ ] **Actuals auto-feed next cycle as a new historical year (NEW)**
- [ ] **Formatted Excel (.xlsx) export (NEW)**
- [ ] **Formatted PDF report export, with optional LLM narrative (NEW)**
- [ ] **LLM plan explainer (NEW)**
- [ ] **LLM input/output reviewer + suggestions — advisory only (NEW)**
- [ ] **Pydantic hard validation vs LLM soft review — two layers (NEW)**
- [ ] Reactive UI (dependent controls update on any input change)
- [ ] **Required fields marked with \* + inline "required" errors; optional fields use defaults (NEW)**
- [ ] CSS design tokens (no hardcoded colours)
- [ ] Coverage risk colouring (green/amber/red)
- [ ] **Report charts: year-trend+forecast (line), baseline-vs-actual (bar), staffing curve, coverage, forecast-vs-actual (NEW)**
- [ ] **Charts embedded into the PDF report as images (NEW)**
- [ ] **Export (PDF + Excel) includes BOTH diagrams: yearly trend + intraday slot overlay (NEW)**
- [ ] **Optional per-year intraday slot profiles (manual + CSV/Excel import) (NEW)**
- [ ] **Forecast intraday shape derived from historical slot data when available (NEW)**
- [ ] **Intraday overlay chart: all years + forecast on one diagram (NEW)**
- [ ] Overflow/sentinel guards (no NaN/Infinity in output)

---

## 10. Hosting & version control — LOCAL ONLY

**Decision:** this project runs **entirely on the local machine.**

- ❌ **No git / no GitHub** — no repo, no commits, no push, no GitHub Pages.
- ❌ No cloud hosting / no public URL.
- ✅ Run locally: `uvicorn` for the FastAPI backend, `vite` dev server (or a local static
  build) for the frontend — both on `localhost`.
- Plans are saved/loaded as **local files** (§8). Nothing leaves the machine except the
  optional Claude API call for explain/review (§7).

(If sharing or deployment is ever needed later, it can be added — but it is explicitly out
of scope now.)

---

## 11. Phased delivery plan

| Phase | Deliverable | Usable on its own? |
|---|---|---|
| **1. Engine + golden tests** | Pure Python WFM engine; all formulas; tests pass | ✅ proven calculator |
| **2. FastAPI + ILP** | REST API, Pydantic validation, OR-Tools optimal scheduler | ✅ callable API |
| **3. React frontend** | The 8 tabs rebuilt on the tested API | ✅ full app |
| **4. LLM explainer** | "Explain this plan" endpoint + UI | ✅ reports |
| **5. Polish & local run** | File save/load, charts, import/export, run scripts | ✅ usable locally |

Each phase is independently valuable. **Phase 1 needs no infra decisions** — pure math.

---

## 12. Risks & open decisions

| Item | Decision needed | When |
|---|---|---|
| Hosting target | Where the (stateless) backend runs | Phase 2/3 |
| Database | Deferred — file-based for now (§8). Add only if team sharing/live multi-user is needed | Future |
| Greedy fallback | Keep greedy as "draft" mode alongside ILP? | Phase 2 |
| LLM model | Sonnet (quality) vs Haiku (cost) | Phase 4 |
| Auth | Do plans need user logins? | Phase 5 (if shared) |
| Styling | Keep CSS tokens vs adopt Tailwind | Phase 3 |

### Deferred features (not in current scope — revisit as v2)
- **Cost modelling** (agents → money) — explicitly **not** included now.
- **Scenario comparison** (side-by-side what-if plans).
- **Dashboard / KPI summary view.**

---

## 13. Definition of done

- **Every golden test passes — formulas produce IDENTICAL results to the existing v2.0
  tool.** This is the top, non-negotiable criterion: the math is frozen as-is; any deviation
  from the verified numbers fails the build.
- ILP returns optimal rosters; coverage-safety test passes.
- All feature-parity items checked off.
- LLM explainer/reviewer produces accurate narratives (numbers always match the engine).
- Runs locally (backend + frontend on localhost); existing JSON plans import cleanly.
- No git, no deployment — local machine only.
```
