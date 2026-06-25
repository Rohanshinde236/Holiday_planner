import type { ComputeResult, Plan } from "../types";
import { comboLabel, slotYearMap } from "../types";
import { YearTrendChart, DailyBarChart, StaffingCurveChart } from "../components/Charts";
import AiPanel from "../components/AiPanel";

export default function Recommendation({
  result, plan, setPlan, onRecompute,
}: {
  result: ComputeResult; plan: Plan; setPlan: (p: Plan) => void; onRecompute: (p: Plan) => void;
}) {
  const sy = slotYearMap(plan);

  const setOverride = (ch: string, name: string) => {
    const next = { ...plan, selected_combos: { ...(plan.selected_combos ?? {}), [ch]: name } };
    setPlan(next);
    onRecompute(next);   // recompute with the override so HC updates downstream
  };

  return (
    <>
      <AiPanel plan={plan} />

      <div className="card">
        <h2>Recommendation summary</h2>
        <div className="kpi">
          <div className="item"><div className="v">{result.shrinkage.total_shrinkage_pct}%</div><div className="l">Total shrinkage</div></div>
          {Object.entries(result.channels).map(([ch, res]) => (
            <div className="item" key={ch}>
              <div className="v">{res.weekly_forecast.toLocaleString()}</div>
              <div className="l" style={{ textTransform: "capitalize" }}>{ch} forecast · {comboLabel(res.recommended?.combo ?? "-", sy)}</div>
            </div>
          ))}
        </div>
      </div>

      {Object.entries(result.channels).map(([ch, res]) => {
        const chosen = res.recommended?.combo;
        const single = res.recommended?.years?.length === 1;
        return (
          <div className="card" key={ch}>
            <h2 style={{ textTransform: "capitalize" }}>{ch} — recommendation &amp; diagrams</h2>

            <div className="grid grid-2" style={{ alignItems: "end", marginBottom: "var(--sp-3)" }}>
              <div className="field"><label>Recommended (override to change)</label>
                <select value={chosen} onChange={(e) => setOverride(ch, e.target.value)}>
                  {res.combinations.map((c) => (
                    <option key={c.combo} value={c.combo}>
                      {comboLabel(c.combo, sy)} ({c.blended_impact_pct.toFixed(1)}%){c.recommended ? " ★ recommended" : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div className="kpi">
                <div className="item"><div className="v">{res.peak_gross_hc}</div><div className="l">Peak Gross HC · busiest {res.busiest_day}</div></div>
              </div>
            </div>

            {single && (
              <div className="banner info">
                Single year — trend stability cannot be assessed from one data point. Blended impact:
                {" "}{Math.abs(res.recommended?.blended_impact_pct ?? 0).toFixed(1)}% volume {(res.recommended?.blended_impact_pct ?? 0) < 0 ? "drop" : "rise"}.
              </div>
            )}

            <YearTrendChart res={res} label={ch} />
            <div style={{ height: "var(--sp-6)" }} />
            <DailyBarChart res={res} label={ch} />
            <div style={{ height: "var(--sp-6)" }} />
            <StaffingCurveChart res={res} label={ch} />
          </div>
        );
      })}
    </>
  );
}
