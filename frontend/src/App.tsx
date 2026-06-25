import { useState } from "react";
import type { Plan, ComputeResult } from "./types";
import { api } from "./api/client";
import Setup from "./tabs/Setup";
import Historical from "./tabs/Historical";
import Combinations from "./tabs/Combinations";
import Recommendation from "./tabs/Recommendation";
import DailyBreakdown from "./tabs/DailyBreakdown";
import HcCoverage from "./tabs/HcCoverage";
import ShiftPlanner from "./tabs/ShiftPlanner";
import ShiftRecommendation from "./tabs/ShiftRecommendation";
import Accuracy from "./tabs/Accuracy";
import ExportBar from "./components/ExportBar";

// Pre-filled sample (Christmas — so the app is usable immediately).
const SAMPLE: Plan = {
  channels: ["voice", "chat", "email"],
  queue: { name: "", region: "APJ", type: "DB" },
  years_of_history: 3,
  shrinkage: { planned: 8, unplanned: 5, training: 3 },
  anomaly_years: ["Y1"],
  params: {
    voice: { plan_volume: 4200, aht_seconds: 360, operating_start: "09:00", operating_end: "17:00", sl_target_pct: 80, sl_target_seconds: 20 },
    chat: { plan_volume: 1800, aht_seconds: 480, operating_start: "09:00", operating_end: "17:00", concurrency: 2.5, occupancy_target_pct: 80 },
    email: { plan_volume: 950, aht_seconds: 600, operating_start: "09:00", operating_end: "17:00", occupancy_target_pct: 75 },
  },
  historical: {
    voice: { Y1: { baseline: 8500, actual: 3600 }, Y2: { baseline: 9200, actual: 5100 }, Y3: { baseline: 9800, actual: 5600 } },
    chat: { Y1: { baseline: 3200, actual: 1100 }, Y2: { baseline: 3600, actual: 1850 }, Y3: { baseline: 3900, actual: 2050 } },
    email: { Y1: { baseline: 1800, actual: 620 }, Y2: { baseline: 2000, actual: 940 }, Y3: { baseline: 2200, actual: 1050 } },
  },
  day_split: {
    voice: [0.45, 0.55, 0, 0, 0, 0, 0],
    chat: [0.42, 0.58, 0, 0, 0, 0, 0],
    email: [0.40, 0.60, 0, 0, 0, 0, 0],
  },
};

const TABS = [
  "1 — Setup", "2 — Historical", "3 — Combinations", "4 — Recommendation",
  "5 — Daily breakdown", "6 — HC & coverage", "7 — Shift planner", "8 — Shift recommendation",
  "9 — Accuracy",
];

export default function App() {
  const [plan, setPlan] = useState<Plan>(SAMPLE);
  const [result, setResult] = useState<ComputeResult | null>(null);
  const [active, setActive] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Drop historical years with missing baseline/actual so empty Y4/Y5 slots don't skew combos.
  function sanitize(p: Plan): Plan {
    const historical: any = {};
    for (const [ch, years] of Object.entries(p.historical)) {
      const clean: any = {};
      for (const [y, d] of Object.entries(years as any)) {
        const dd = d as any;
        if (dd && dd.baseline != null && dd.baseline !== "" && dd.actual != null && dd.actual !== "") {
          clean[y] = { baseline: +dd.baseline, actual: +dd.actual };
        }
      }
      historical[ch] = clean;
    }
    const present = new Set(Object.values(historical).flatMap((y: any) => Object.keys(y)));
    return { ...p, historical, anomaly_years: p.anomaly_years.filter((y) => present.has(y)) };
  }

  async function compute(planArg?: Plan) {
    const p = planArg ?? plan;
    if (!p.queue?.name?.trim()) {
      setErr("Queue name is required — set it on the Setup tab.");
      setActive(0);
      return;
    }
    setBusy(true); setErr(null);
    try {
      const r = await api.computePlan(sanitize(p));
      setResult(r);
      if (!planArg) setActive(3); // jump to Recommendation on a fresh compute (not on override)
    } catch (e: any) {
      setErr(e.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  function importPlan(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result));
        const loaded: Plan = parsed.plan ?? parsed;        // accept {plan,result} or a raw plan
        if (!loaded.channels || !loaded.params) throw new Error("Not a recognised plan file.");
        setPlan(loaded);
        setResult(null);
        setActive(0);
        setErr(null);
      } catch (e: any) {
        setErr("Import failed: " + (e.message ?? String(e)));
      }
    };
    reader.readAsText(file);
  }

  const needResult = active >= 2;   // Combinations (tab 3) onward require a computed result

  return (
    <div>
      <header className="app-header">
        <div>
          <h1>WFM Holiday Planner</h1>
          <div className="sub">Local · formulas frozen · ILP shifts</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <label className="btn-ghost" style={{ cursor: "pointer" }}>
            Import JSON
            <input type="file" accept="application/json,.json" style={{ display: "none" }}
              onChange={(e) => e.target.files?.[0] && importPlan(e.target.files[0])} />
          </label>
          <ExportBar plan={plan} result={result} />
          <button className="primary" onClick={() => compute()} disabled={busy}>
            {busy ? "Computing…" : "Compute plan"}
          </button>
        </div>
      </header>

      <nav className="tabs">
        {TABS.map((t, i) => (
          <button
            key={t}
            className={"tab" + (active === i ? " active" : "")}
            disabled={i >= 2 && !result}
            onClick={() => setActive(i)}
          >
            {t}
          </button>
        ))}
      </nav>

      <div className="content">
        {err && <div className="banner info">⚠️ {err}</div>}
        {needResult && !result && <div className="banner info">Click “Compute plan” to generate results.</div>}

        {active === 0 && <Setup plan={plan} setPlan={setPlan} />}
        {active === 1 && <Historical plan={plan} setPlan={setPlan} />}
        {active === 2 && result && <Combinations result={result} plan={plan} />}
        {active === 3 && result && <Recommendation result={result} plan={plan} setPlan={setPlan} onRecompute={compute} />}
        {active === 4 && result && <DailyBreakdown result={result} />}
        {active === 5 && result && <HcCoverage result={result} plan={plan} setPlan={setPlan} />}
        {active === 6 && result && <ShiftPlanner result={result} plan={plan} />}
        {active === 7 && result && <ShiftRecommendation result={result} plan={plan} />}
        {active === 8 && result && <Accuracy result={result} />}
      </div>
    </div>
  );
}
