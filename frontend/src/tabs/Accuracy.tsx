import { useState } from "react";
import type { ComputeResult } from "../types";
import { api } from "../api/client";

export default function Accuracy({ result }: { result: ComputeResult }) {
  const channels = Object.keys(result.channels);
  const [actuals, setActuals] = useState<Record<string, number>>({});
  const [out, setOut] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function run() {
    setBusy(true); setErr("");
    try {
      const items = channels.map((ch) => ({
        label: ch, forecast: result.channels[ch].weekly_forecast, actual: actuals[ch] ?? 0,
      }));
      setOut(await api.accuracy(items));
    } catch (e: any) { setErr(e.message ?? String(e)); } finally { setBusy(false); }
  }

  const band = (m: number | null) =>
    m == null ? "" : m <= 5 ? "green" : m <= 15 ? "amber" : "red";

  return (
    <>
      <div className="card">
        <h2>Post-holiday accuracy</h2>
        <p className="hint">After the holiday, enter what actually happened. We compare it to the forecast (MAPE = error %, bias = over/under).</p>
        <table>
          <thead><tr><th>Channel</th><th className="num">Forecast (weekly)</th><th className="num">Actual (weekly)</th></tr></thead>
          <tbody>
            {channels.map((ch) => (
              <tr key={ch}>
                <td style={{ textTransform: "capitalize" }}>{ch}</td>
                <td className="num">{result.channels[ch].weekly_forecast.toLocaleString()}</td>
                <td className="num"><input type="number" value={actuals[ch] ?? ""} placeholder="0"
                  onChange={(e) => setActuals({ ...actuals, [ch]: +e.target.value })} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        <button className="primary" style={{ marginTop: 12 }} onClick={run} disabled={busy}>
          {busy ? "Computing…" : "Compute accuracy"}
        </button>
        {err && <div className="banner info" style={{ marginTop: 12 }}>⚠️ {err}</div>}
      </div>

      {out && (
        <div className="card">
          <div className="kpi" style={{ marginBottom: 16 }}>
            <div className="item"><div className="v">{out.overall_mape_pct ?? "—"}%</div><div className="l">Overall MAPE (lower = better)</div></div>
          </div>
          <table>
            <thead><tr><th>Channel</th><th className="num">Forecast</th><th className="num">Actual</th><th className="num">Error</th><th className="num">MAPE %</th><th className="num">Bias %</th><th>Band</th></tr></thead>
            <tbody>
              {out.items.map((i: any) => (
                <tr key={i.label}>
                  <td style={{ textTransform: "capitalize" }}>{i.label}</td>
                  <td className="num">{i.forecast.toLocaleString()}</td>
                  <td className="num">{i.actual.toLocaleString()}</td>
                  <td className="num">{i.abs_error.toLocaleString()}</td>
                  <td className="num">{i.mape_pct ?? "—"}</td>
                  <td className="num">{i.bias_pct == null ? "—" : (i.bias_pct > 0 ? "+" : "") + i.bias_pct + " (" + (i.bias_pct > 0 ? "over" : "under") + ")"}</td>
                  <td>{i.mape_pct != null && <span className={"pill " + band(i.mape_pct)}>{band(i.mape_pct)}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="hint" style={{ marginTop: 12 }}>Tip: a consistent positive bias means you over-forecast — nudge next year's plan down; negative means under-forecast.</p>
        </div>
      )}
    </>
  );
}
