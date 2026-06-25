import type { ComputeResult } from "../types";
import { DailyBarChart } from "../components/Charts";

export default function DailyBreakdown({ result }: { result: ComputeResult }) {
  return (
    <>
      {Object.entries(result.channels).map(([ch, res]) => (
        <div className="card" key={ch}>
          <h2 style={{ textTransform: "capitalize" }}>{ch} — daily breakdown</h2>
          <DailyBarChart res={res} label={ch} />
          <table style={{ marginTop: 16 }}>
            <thead><tr>{Object.keys(res.daily).map((d) => <th key={d} className="num">{d}</th>)}</tr></thead>
            <tbody><tr>{Object.entries(res.daily).map(([d, v]) => (
              <td key={d} className="num">{Math.round(v).toLocaleString()}{d === res.busiest_day ? " ★" : ""}</td>
            ))}</tr></tbody>
          </table>

          {res.days_hc && res.days_hc.length > 1 && (
            <>
              <p className="hint" style={{ marginTop: 16 }}>
                <b>Multi-day staffing</b> — each day with volume planned independently:
              </p>
              <table>
                <thead><tr><th>Day</th><th className="num">Volume</th><th className="num">Net HC</th><th className="num">Gross HC</th></tr></thead>
                <tbody>
                  {res.days_hc.map((d) => (
                    <tr key={d.day} className={d.day === res.busiest_day ? "reco" : ""}>
                      <td>{d.day}{d.day === res.busiest_day ? " ★ (peak)" : ""}</td>
                      <td className="num">{Math.round(d.volume).toLocaleString()}</td>
                      <td className="num">{d.peak_net_hc}</td>
                      <td className="num">{d.peak_gross_hc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      ))}
    </>
  );
}
