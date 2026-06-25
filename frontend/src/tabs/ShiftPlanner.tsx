import { useState } from "react";
import type { ComputeResult, Plan } from "../types";

interface Shift { name: string; start: string; end: string; agents: number; }

const toMin = (t: string) => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };
const covers = (sh: Shift, slotStart: string) => {
  const t = toMin(slotStart), s = toMin(sh.start), e = toMin(sh.end);
  return e > s ? t >= s && t < e : (t >= s || t < e); // overnight-aware
};

const DEFAULTS: Shift[] = [
  { name: "Early", start: "07:00", end: "15:00", agents: 20 },
  { name: "Mid", start: "10:00", end: "18:00", agents: 15 },
  { name: "Late", start: "13:00", end: "21:00", agents: 10 },
];

export default function ShiftPlanner({ result, plan }: { result: ComputeResult; plan: Plan }) {
  const channels = Object.entries(result.channels).filter(([, r]) => r.intervals.length > 0);
  const [ch, setCh] = useState(channels[0]?.[0] ?? "");
  const [shifts, setShifts] = useState<Shift[]>(DEFAULTS);

  const res = result.channels[ch];
  const set = (i: number, k: keyof Shift, v: string | number) =>
    setShifts(shifts.map((s, j) => (j === i ? { ...s, [k]: v } : s)));
  const addShift = () => setShifts([...shifts, { name: `Shift ${shifts.length + 1}`, start: "09:00", end: "17:00", agents: 5 }]);
  const removeShift = (i: number) => setShifts(shifts.filter((_, j) => j !== i));

  const coverage = res ? res.intervals.map((iv) => {
    const planned = shifts.reduce((a, s) => a + (covers(s, iv.start) ? s.agents : 0), 0);
    const gap = planned - iv.gross_hc;
    const risk = gap >= 0 ? "green" : (gap >= -Math.ceil(iv.gross_hc * 0.15) ? "amber" : "red");
    return { ...iv, planned, gap, risk };
  }) : [];
  const reds = coverage.filter((c) => c.risk === "red").length;
  const total = shifts.reduce((a, s) => a + s.agents, 0);

  return (
    <>
      <div className="card">
        <h2>Shift planner</h2>
        <p className="hint">Enter your shifts and agent counts; coverage is checked against Gross HC per slot.</p>
        <div className="field" style={{ maxWidth: 220 }}>
          <label>Channel</label>
          <select value={ch} onChange={(e) => setCh(e.target.value)}>
            {channels.map(([c]) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <table>
          <thead><tr><th>Shift</th><th>Start</th><th>End</th><th className="num">Agents</th><th></th></tr></thead>
          <tbody>
            {shifts.map((s, i) => (
              <tr key={i}>
                <td><input value={s.name} onChange={(e) => set(i, "name", e.target.value)} /></td>
                <td><input type="time" value={s.start} onChange={(e) => set(i, "start", e.target.value)} /></td>
                <td><input type="time" value={s.end} onChange={(e) => set(i, "end", e.target.value)} /></td>
                <td className="num"><input type="number" value={s.agents} onChange={(e) => set(i, "agents", +e.target.value)} /></td>
                <td><button className="btn-ghost" onClick={() => removeShift(i)}>✕</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <button className="btn-ghost" style={{ marginTop: 8 }} onClick={addShift}>+ Add shift</button>
      </div>

      <div className="card">
        <div className="kpi" style={{ marginBottom: 16 }}>
          <div className="item"><div className="v">{total}</div><div className="l">Agents planned</div></div>
          <div className="item"><div className="v">{res?.peak_gross_hc}</div><div className="l">Peak Gross HC needed</div></div>
          <div className="item"><div className="v">{reds}</div><div className="l">Under-staffed slots</div></div>
        </div>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Slot</th><th className="num">Required</th><th className="num">Planned</th><th className="num">Gap</th><th>Risk</th></tr></thead>
            <tbody>
              {coverage.map((c) => (
                <tr key={c.start}>
                  <td>{c.start}–{c.end}</td>
                  <td className="num">{c.gross_hc}</td>
                  <td className="num">{c.planned}</td>
                  <td className="num">{c.gap >= 0 ? "+" : ""}{c.gap}</td>
                  <td><span className={"pill " + c.risk}>{c.risk}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
