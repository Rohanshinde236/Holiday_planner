import type { ComputeResult, Plan } from "../types";
import { comboLabel, slotYearMap } from "../types";

export default function Combinations({ result, plan }: { result: ComputeResult; plan: Plan }) {
  const sy = slotYearMap(plan);
  return (
    <>
      {Object.entries(result.channels).map(([ch, res]) => (
        <div className="card" key={ch}>
          <h2 style={{ textTransform: "capitalize" }}>{ch} — trend combinations</h2>
          <p className="hint">Year-over-year subsets, scored. Highest score is recommended.</p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr><th>Combination</th><th className="num">Impact %</th><th className="num">Forecast</th><th className="num">Score</th><th>Anomaly</th></tr>
              </thead>
              <tbody>
                {res.combinations.map((c) => (
                  <tr key={c.combo} className={c.recommended ? "reco" : ""}>
                    <td>{comboLabel(c.combo, sy)}{c.recommended ? "  ★" : ""}</td>
                    <td className="num">{c.blended_impact_pct.toFixed(2)}%</td>
                    <td className="num">{c.forecasted_volume.toLocaleString()}</td>
                    <td className="num">{c.score.toFixed(1)}</td>
                    <td>{c.contains_anomaly ? "🚩" : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </>
  );
}
