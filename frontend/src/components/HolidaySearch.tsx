import { useEffect, useState } from "react";
import type { Plan } from "../types";
import { api } from "../api/client";

const today = () => new Date().toISOString().slice(0, 10);

export default function HolidaySearch({ plan, setPlan }: { plan: Plan; setPlan: (p: Plan) => void }) {
  const [countries, setCountries] = useState<Record<string, { code: string; name: string }[]>>({});
  const [country, setCountry] = useState("IN");
  const [baseYear, setBaseYear] = useState(new Date().getFullYear());
  const [q, setQ] = useState("");
  const [matches, setMatches] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const years = plan.years_of_history ?? 3;
  const setYears = (n: number) =>
    setPlan({ ...plan, years_of_history: Math.max(1, Math.min(5, n || 1)) });

  useEffect(() => { api.holidayCountries().then(setCountries).catch(() => {}); }, []);

  useEffect(() => {
    if (!q.trim()) { setMatches([]); return; }
    const t = setTimeout(async () => {
      try { setMatches((await api.searchHolidays(q, country, baseYear)).matches.slice(0, 8)); }
      catch { setMatches([]); }
    }, 250);
    return () => clearTimeout(t);
  }, [q, country, baseYear]);

  async function pick(name: string) {
    setBusy(true); setQ(name); setMatches([]);
    try {
      const d = await api.holidayDates(name, country, baseYear, years);
      setPlan({ ...plan, holiday: d });
    } finally { setBusy(false); }
  }

  // Manual fallback: festival not in the calendar → seed today's date for each year (editable).
  function manualDates() {
    const history = Array.from({ length: years }, (_, i) => ({
      slot: `Y${i + 1}`, year: baseYear - (i + 1), date: today(),
    }));
    setPlan({ ...plan, holiday: { name: q || "Custom holiday", country, plan_year: baseYear, plan_date: today(), history } });
  }

  // Editable dates
  const setPlanDate = (date: string) =>
    plan.holiday && setPlan({ ...plan, holiday: { ...plan.holiday, plan_date: date } });
  const setHistDate = (idx: number, date: string) => {
    if (!plan.holiday) return;
    const history = plan.holiday.history.map((h, i) => (i === idx ? { ...h, date } : h));
    setPlan({ ...plan, holiday: { ...plan.holiday, history } });
  };

  const h = plan.holiday;

  return (
    <div className="card">
      <h2>🗓️ Holiday calendar</h2>
      <p className="hint">Search a festival — dates auto-fill for the plan year and each past year (editable). Not listed? Use “manual dates”.</p>

      <div className="grid grid-3" style={{ marginBottom: "var(--sp-3)" }}>
        <div className="field"><label>Country</label>
          <select value={country} onChange={(e) => setCountry(e.target.value)}>
            {Object.entries(countries).map(([region, list]) => (
              <optgroup key={region} label={region}>
                {list.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
              </optgroup>
            ))}
          </select>
        </div>
        <div className="field"><label>Plan year</label>
          <input type="number" value={baseYear} onChange={(e) => setBaseYear(+e.target.value)} /></div>
        <div className="field"><label className="req">Years of history</label>
          <input type="number" min={1} max={5} value={years} onChange={(e) => setYears(+e.target.value)} /></div>
      </div>

      <div className="field" style={{ position: "relative" }}>
        <label>Search festival</label>
        <input type="text" placeholder="e.g. Diwali, Ganesh, Independence…" value={q} onChange={(e) => setQ(e.target.value)} />
        {matches.length > 0 && (
          <div style={{ position: "absolute", zIndex: 5, background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 8, width: "100%", marginTop: 2, boxShadow: "0 4px 12px rgba(0,0,0,.08)" }}>
            {matches.map((m) => (
              <div key={m} onClick={() => pick(m)} style={{ padding: "8px 10px", cursor: "pointer", fontSize: 14, borderBottom: "1px solid var(--color-border)" }}>{m}</div>
            ))}
          </div>
        )}
      </div>
      <button className="btn-ghost" onClick={manualDates} style={{ marginTop: 4 }}>Festival not listed — enter dates manually</button>
      {busy && <p className="hint">Looking up dates…</p>}

      {h && (
        <div style={{ marginTop: "var(--sp-4)" }}>
          <div className="banner info"><b>{h.name}</b> ({h.country}) — dates (editable):</div>
          <table>
            <thead><tr><th>Slot</th><th>Year</th><th>Date</th></tr></thead>
            <tbody>
              <tr className="reco"><td>Plan</td><td>{h.plan_year}</td>
                <td><input type="date" value={h.plan_date ?? ""} onChange={(e) => setPlanDate(e.target.value)} /></td></tr>
              {h.history.map((row, i) => (
                <tr key={row.slot}>
                  <td>{row.slot}</td><td>{row.year}</td>
                  <td><input type="date" value={row.date ?? ""} onChange={(e) => setHistDate(i, e.target.value)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
