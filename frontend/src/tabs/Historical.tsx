import type { Plan, Channel } from "../types";
import { yearSlots, DAYS } from "../types";

export default function Historical({ plan, setPlan }: { plan: Plan; setPlan: (p: Plan) => void }) {
  const YEARS = yearSlots(plan.years_of_history);   // driven by "Years of history"
  const setVal = (ch: Channel, y: string, key: "baseline" | "actual", val: number) =>
    setPlan({
      ...plan,
      historical: { ...plan.historical, [ch]: { ...plan.historical[ch], [y]: { ...plan.historical[ch][y], [key]: val } } },
    });
  const toggleAnom = (y: string) => {
    const has = plan.anomaly_years.includes(y);
    setPlan({ ...plan, anomaly_years: has ? plan.anomaly_years.filter((x) => x !== y) : [...plan.anomaly_years, y] });
  };

  const impact = (b?: number | null, a?: number | null) =>
    b && a != null ? (((a - b) / b) * 100).toFixed(1) + "%" : "—";

  const setDaily = (ch: Channel, y: string, d: number, val: number) => {
    const dh = { ...(plan.daily_history ?? {}) };
    const chMap = { ...(dh[ch] ?? {}) };
    const row = [...(chMap[y] ?? [0, 0, 0, 0, 0, 0, 0])];
    row[d] = val;
    chMap[y] = row;
    dh[ch] = chMap;
    setPlan({ ...plan, daily_history: dh });
  };

  return (
    <>
      <div className="card">
        <h2>Anomaly years</h2>
        <p className="hint">Flagged years are excluded from the recommended combination (e.g. COVID).</p>
        <div style={{ display: "flex", gap: 16 }}>
          {YEARS.map((y) => (
            <label key={y} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <input type="checkbox" checked={plan.anomaly_years.includes(y)} onChange={() => toggleAnom(y)} /> {y}
            </label>
          ))}
        </div>
      </div>

      {plan.channels.map((ch) => (
        <div className="card" key={ch}>
          <h2 style={{ textTransform: "capitalize" }}>{ch} — historical (baseline vs actual)</h2>
          <table>
            <thead>
              <tr><th>Year</th><th className="num req">Baseline</th><th className="num req">Actual</th><th className="num">Impact %</th></tr>
            </thead>
            <tbody>
              {YEARS.map((y) => {
                const d = plan.historical[ch]?.[y] ?? { baseline: null, actual: null };
                return (
                  <tr key={y}>
                    <td>{y}{plan.anomaly_years.includes(y) ? " 🚩" : ""}</td>
                    <td className="num"><input type="number" value={d.baseline ?? ""} onChange={(e) => setVal(ch, y, "baseline", +e.target.value)} /></td>
                    <td className="num"><input type="number" value={d.actual ?? ""} onChange={(e) => setVal(ch, y, "actual", +e.target.value)} /></td>
                    <td className="num">{impact(d.baseline, d.actual)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <details style={{ marginTop: "var(--sp-4)" }}>
            <summary style={{ cursor: "pointer", fontSize: 13, color: "var(--color-primary)" }}>
              Daily volume history (optional) — enables holiday-anchored forecasting
            </summary>
            <p className="hint" style={{ marginTop: "var(--sp-2)" }}>
              Enter each year's actual volume per day (Sat-first). With this + a holiday date
              (from the calendar), the forecast anchors the spike/dip to the festival's weekday.
              Leave blank to use the manual split / flat.
            </p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr><th>Year</th>{DAYS.map((d) => <th key={d} className="num">{d}</th>)}</tr>
                </thead>
                <tbody>
                  {YEARS.map((y) => {
                    const row = plan.daily_history?.[ch]?.[y] ?? [];
                    return (
                      <tr key={y}>
                        <td>{y}</td>
                        {DAYS.map((_, d) => (
                          <td key={d} className="num">
                            <input type="number" value={row[d] ?? ""} style={{ minWidth: 64 }}
                              onChange={(e) => setDaily(ch, y, d, +e.target.value)} />
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </details>
        </div>
      ))}
    </>
  );
}
