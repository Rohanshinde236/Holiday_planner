import { useState } from "react";
import type { ComputeResult, Plan } from "../types";
import { api } from "../api/client";

export default function ShiftRecommendation({ result, plan }: { result: ComputeResult; plan: Plan }) {
  const channels = Object.entries(result.channels).filter(([, r]) => r.intervals.length > 0);
  const [ch, setCh] = useState(channels[0]?.[0] ?? "");
  const [pool, setPool] = useState(200);
  const [out, setOut] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    const res = result.channels[ch];
    if (!res) return;
    setBusy(true); setErr(null);
    const p = plan.params[ch as keyof typeof plan.params];
    const hc_requirements = res.intervals.map((iv, i) => ({ interval: i + 1, start: iv.start, net_hc: iv.gross_hc }));
    // build 8-hour shift templates every hour across the operating window
    const [sh] = p.operating_start.split(":").map(Number);
    const [eh] = p.operating_end.split(":").map(Number);
    const shifts = [];
    for (let h = sh; h + 8 <= eh + 6 && h <= eh; h++) {
      shifts.push({ name: `S${String(h).padStart(2, "0")}`, start: `${String(h).padStart(2, "0")}:00`, end: `${String(Math.min(h + 8, 24)).padStart(2, "0")}:00` });
    }
    try {
      const r = await api.shiftOptimise({
        hc_requirements, available_shifts: shifts,
        operating_start: p.operating_start, operating_end: p.operating_end,
        mode: "ilp", available_agents: pool,
      });
      setOut(r);
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <>
      <div className="card">
        <h2>Shift recommendation (ILP — optimal)</h2>
        <p className="hint">Provably-minimum agents that fully cover the Gross HC requirement.</p>
        <div className="grid grid-3" style={{ alignItems: "end" }}>
          <div className="field"><label>Channel</label>
            <select value={ch} onChange={(e) => setCh(e.target.value)}>
              {channels.map(([c]) => <option key={c} value={c}>{c}</option>)}
            </select></div>
          <div className="field"><label>Agent pool (cap)</label>
            <input type="number" value={pool} onChange={(e) => setPool(+e.target.value)} /></div>
          <div className="field"><button className="primary" onClick={run} disabled={busy}>{busy ? "Solving…" : "Optimise shifts"}</button></div>
        </div>
        {err && <div className="banner info">⚠️ {err}</div>}
      </div>

      {out && (
        <div className="card">
          <div className="kpi" style={{ marginBottom: 16 }}>
            <div className="item"><div className="v">{out.total_agents_used}</div><div className="l">Agents used (optimal)</div></div>
            <div className="item"><div className="v">{out.coverage_pct}%</div><div className="l">Slots fully covered</div></div>
            <div className="item"><div className="v">{out.intervals_at_risk}</div><div className="l">Under-staffed slots</div></div>
          </div>
          <h2>Recommended shifts</h2>
          <table>
            <thead><tr><th>Shift</th><th>Start</th><th>End</th><th className="num">Agents</th></tr></thead>
            <tbody>
              {out.recommended_shifts.map((s: any) => (
                <tr key={s.shift_name}>
                  <td>{s.shift_name}</td><td>{s.start}</td><td>{s.end}</td>
                  <td className="num">{s.agents_assigned}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!out.optimal && <div className="banner info" style={{ marginTop: 12 }}>⚠️ Pool too small for full coverage — showing best achievable.</div>}
        </div>
      )}
    </>
  );
}
