import { useState } from "react";
import type { Plan, Channel } from "../types";
import HolidaySearch from "../components/HolidaySearch";

const ALL: Channel[] = ["voice", "chat", "email", "blended"];

// Default params seeded when a channel is first ticked (so the form never reads undefined).
const DEFAULT_PARAMS: Record<string, any> = {
  voice: { plan_volume: 0, aht_seconds: 360, operating_start: "09:00", operating_end: "17:00", sl_target_pct: 80, sl_target_seconds: 20, ibu_pct: 100 },
  chat: { plan_volume: 0, aht_seconds: 480, operating_start: "09:00", operating_end: "17:00", concurrency: 2.5, occupancy_target_pct: 80, utilization_pct: 100 },
  email: { plan_volume: 0, aht_seconds: 600, operating_start: "09:00", operating_end: "17:00", occupancy_target_pct: 75 },
  blended: { plan_volume: 0, aht_seconds: 360, operating_start: "09:00", operating_end: "17:00", sl_target_pct: 80, sl_target_seconds: 20, concurrency: 2.5, occupancy_target_pct: 80, voice_pct: 60, chat_pct: 40, voice_aht: 360, chat_aht: 480 },
};

export default function Setup({ plan, setPlan }: { plan: Plan; setPlan: (p: Plan) => void }) {
  // AHT display unit per channel (UI only — aht_seconds stays the stored source of truth)
  const [ahtUnit, setAhtUnit] = useState<Record<string, "sec" | "min">>({});
  const unitOf = (ch: string) => ahtUnit[ch] ?? "sec";
  const ahtDisplay = (ch: Channel) => {
    const s = plan.params[ch].aht_seconds || 0;
    return unitOf(ch) === "min" ? +(s / 60).toFixed(2) : s;
  };

  const toggle = (ch: Channel) => {
    const has = plan.channels.includes(ch);
    if (has) {
      setPlan({ ...plan, channels: plan.channels.filter((c) => c !== ch) });
    } else {
      // seed default params if this channel has none yet
      const params = plan.params[ch] ? plan.params : { ...plan.params, [ch]: { ...DEFAULT_PARAMS[ch] } };
      setPlan({ ...plan, channels: [...plan.channels, ch], params });
    }
  };
  const setParam = (ch: Channel, key: string, val: number | string) =>
    setPlan({ ...plan, params: { ...plan.params, [ch]: { ...plan.params[ch], [key]: val } } });
  const setShrink = (key: string, val: number) =>
    setPlan({ ...plan, shrinkage: { ...plan.shrinkage, [key]: val } });

  const q = plan.queue ?? { name: "", region: "APJ", type: "DB" };
  const setQueue = (k: string, v: string) => setPlan({ ...plan, queue: { ...q, [k]: v } });

  return (
    <>
      <div className="card">
        <h2>Queue context</h2>
        <p className="hint">Labels this plan (shown in the report). Region also sets the calendar's country group.</p>
        <div className="grid grid-3">
          <div className="field"><label className="req">Queue name</label>
            <input type="text" placeholder="e.g. Billing Support" value={q.name}
              style={!q.name.trim() ? { borderColor: "var(--color-red)" } : undefined}
              onChange={(e) => setQueue("name", e.target.value)} />
            {!q.name.trim() && <span style={{ fontSize: 11, color: "var(--color-red)" }}>Required to compute</span>}</div>
          <div className="field"><label>Region</label>
            <select value={q.region} onChange={(e) => setQueue("region", e.target.value)}>
              {["APJ", "EMEA", "AMER", "LATAM"].map((r) => <option key={r} value={r}>{r}</option>)}
            </select></div>
          <div className="field"><label>Queue type</label>
            <select value={q.type} onChange={(e) => setQueue("type", e.target.value)}>
              <option value="DB">DB (Internal)</option>
              <option value="OSP">OSP (Outsourced)</option>
            </select></div>
        </div>
      </div>

      <HolidaySearch plan={plan} setPlan={setPlan} />

      <div className="card">
        <h2>Channels</h2>
        <p className="hint">Pick at least one channel to plan for.</p>
        <div style={{ display: "flex", gap: 16 }}>
          {ALL.map((ch) => (
            <label key={ch} style={{ display: "flex", alignItems: "center", gap: 6, textTransform: "capitalize" }}>
              <input type="checkbox" checked={plan.channels.includes(ch)} onChange={() => toggle(ch)} /> {ch}
            </label>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>Shrinkage</h2>
        <p className="hint">Compound: 1 − (1−PL)(1−UL)(1−TR). Optional — defaults shown.</p>
        <div className="grid grid-3">
          <div className="field"><label>Planned leave %</label>
            <input type="number" value={plan.shrinkage.planned} onChange={(e) => setShrink("planned", +e.target.value)} /></div>
          <div className="field"><label>Unplanned leave %</label>
            <input type="number" value={plan.shrinkage.unplanned} onChange={(e) => setShrink("unplanned", +e.target.value)} /></div>
          <div className="field"><label>Training %</label>
            <input type="number" value={plan.shrinkage.training} onChange={(e) => setShrink("training", +e.target.value)} /></div>
        </div>
      </div>

      {plan.channels.map((ch) => (
        <div className="card" key={ch}>
          <h2 style={{ textTransform: "capitalize" }}>{ch} setup</h2>
          <div className="grid grid-4">
            <div className="field"><label className="req">Plan volume (weekly)</label>
              <input type="number" value={plan.params[ch].plan_volume} onChange={(e) => setParam(ch, "plan_volume", +e.target.value)} /></div>
            <div className="field"><label className="req">AHT</label>
              <div style={{ display: "flex", gap: 6 }}>
                <input type="number" style={{ flex: 1 }} value={ahtDisplay(ch)}
                  onChange={(e) => setParam(ch, "aht_seconds", unitOf(ch) === "min" ? +e.target.value * 60 : +e.target.value)} />
                <select value={unitOf(ch)} style={{ width: 90 }}
                  onChange={(e) => setAhtUnit({ ...ahtUnit, [ch]: e.target.value as "sec" | "min" })}>
                  <option value="sec">sec</option>
                  <option value="min">min</option>
                </select>
              </div></div>
            <div className="field"><label className="req">Operating start</label>
              <input type="time" value={plan.params[ch].operating_start} onChange={(e) => setParam(ch, "operating_start", e.target.value)} /></div>
            <div className="field"><label className="req">Operating end</label>
              <input type="time" value={plan.params[ch].operating_end} onChange={(e) => setParam(ch, "operating_end", e.target.value)} /></div>
            {ch === "voice" && <>
              <div className="field"><label>SL target %</label>
                <input type="number" value={plan.params[ch].sl_target_pct} onChange={(e) => setParam(ch, "sl_target_pct", +e.target.value)} /></div>
              <div className="field"><label>SL seconds</label>
                <input type="number" value={plan.params[ch].sl_target_seconds} onChange={(e) => setParam(ch, "sl_target_seconds", +e.target.value)} /></div>
              <div className="field"><label className="req">IBU %</label>
                <input type="number" min={30} max={100} value={plan.params[ch].ibu_pct ?? 100} onChange={(e) => setParam(ch, "ibu_pct", +e.target.value)} title="In-Bound Utilization — % of paid time agents are on contacts. Divides raw agents before shrinkage. 100 = no adjustment." /></div>
            </>}
            {ch === "chat" && <>
              <div className="field"><label>Concurrency</label>
                <input type="number" step="0.1" value={plan.params[ch].concurrency} onChange={(e) => setParam(ch, "concurrency", +e.target.value)} /></div>
              <div className="field"><label>Occupancy %</label>
                <input type="number" value={plan.params[ch].occupancy_target_pct} onChange={(e) => setParam(ch, "occupancy_target_pct", +e.target.value)} /></div>
              <div className="field"><label className="req">Utilization %</label>
                <input type="number" min={30} max={100} value={plan.params[ch].utilization_pct ?? 100} onChange={(e) => setParam(ch, "utilization_pct", +e.target.value)} title="% of paid time agents are on chats. Divides raw agents before shrinkage. 100 = no adjustment." /></div>
            </>}
            {ch === "email" && <div className="field"><label>Occupancy %</label>
              <input type="number" value={plan.params[ch].occupancy_target_pct} onChange={(e) => setParam(ch, "occupancy_target_pct", +e.target.value)} /></div>}
            {ch === "blended" && <>
              <div className="field"><label className="req">Voice %</label>
                <input type="number" value={plan.params[ch].voice_pct} onChange={(e) => setParam(ch, "voice_pct", +e.target.value)} /></div>
              <div className="field"><label className="req">Chat %</label>
                <input type="number" value={plan.params[ch].chat_pct} onChange={(e) => setParam(ch, "chat_pct", +e.target.value)} /></div>
              <div className="field"><label>Voice AHT (sec)</label>
                <input type="number" value={plan.params[ch].voice_aht} onChange={(e) => setParam(ch, "voice_aht", +e.target.value)} /></div>
              <div className="field"><label>Chat AHT (sec)</label>
                <input type="number" value={plan.params[ch].chat_aht} onChange={(e) => setParam(ch, "chat_aht", +e.target.value)} /></div>
            </>}
          </div>
        </div>
      ))}
    </>
  );
}
