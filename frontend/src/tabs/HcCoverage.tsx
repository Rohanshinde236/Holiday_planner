import type { ComputeResult, Plan } from "../types";
import { StaffingCurveChart, IntradayOverlayChart } from "../components/Charts";

export default function HcCoverage({ result, plan, setPlan }: { result: ComputeResult; plan: Plan; setPlan: (p: Plan) => void }) {
  // Parse a textarea of "Y1: 10,20,30 ..." lines into {year:[numbers]} for one channel.
  function setIntraday(ch: string, text: string) {
    const map: Record<string, number[]> = {};
    for (const line of text.split("\n")) {
      const m = line.split(":");
      if (m.length < 2) continue;
      const year = m[0].trim().toUpperCase();
      const nums = m.slice(1).join(":").split(/[\s,]+/).map(Number).filter((n) => !isNaN(n));
      if (year && nums.length) map[year] = nums;
    }
    setPlan({ ...plan, intraday_history: { ...(plan.intraday_history ?? {}), [ch]: map } });
  }
  const intradayText = (ch: string) =>
    Object.entries(plan.intraday_history?.[ch] ?? {}).map(([y, arr]) => `${y}: ${arr.join(",")}`).join("\n");

  return (
    <>
      {Object.entries(result.channels).map(([ch, res]) => (
        <div className="card" key={ch}>
          <h2 style={{ textTransform: "capitalize" }}>{ch} — HC &amp; coverage</h2>
          <div className="kpi" style={{ marginBottom: 16 }}>
            <div className="item"><div className="v">{res.peak_net_hc}</div><div className="l">Peak Net HC</div></div>
            <div className="item"><div className="v">{res.peak_gross_hc}</div><div className="l">Peak Gross HC (roster)</div></div>
            <div className="item"><div className="v" style={{ fontSize: 14 }}>{res.intraday_source}</div><div className="l">Intraday shape source</div></div>
          </div>
          <StaffingCurveChart res={res} label={ch} />

          {res.intervals.length > 0 && (
            <>
              <div style={{ height: 16 }} />
              <IntradayOverlayChart res={res} label={ch} />

              <details style={{ marginTop: 16 }}>
                <summary style={{ cursor: "pointer", fontSize: 13, color: "var(--color-primary)" }}>
                  Intraday history (optional) — paste per-year slot volumes to drive the shape + overlay
                </summary>
                <p className="hint" style={{ marginTop: 8 }}>
                  One line per year: <code>Y1: 10,20,35,...</code> (one value per 30-min slot, in operating-window order).
                  Must match the slot count of the window. Then click <b>Compute plan</b>.
                </p>
                <textarea rows={5} style={{ width: "100%", fontFamily: "var(--font-mono)", fontSize: 12 }}
                  defaultValue={intradayText(ch)} onBlur={(e) => setIntraday(ch, e.target.value)}
                  placeholder={"Y1: 5,8,12,20,28,34,40,44,46,44,40,33,25,18,12,8\nY2: ..."} />
              </details>

              <div className="table-scroll" style={{ marginTop: 16 }}>
                <table>
                  <thead><tr><th>Slot</th><th className="num">Calls/hr</th><th className="num">Net HC</th><th className="num">Gross HC</th></tr></thead>
                  <tbody>
                    {res.intervals.map((iv) => (
                      <tr key={iv.start}>
                        <td>{iv.start}–{iv.end}</td>
                        <td className="num">{iv.calls_per_hour}</td>
                        <td className="num">{iv.net_hc}</td>
                        <td className="num">{iv.gross_hc}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      ))}
    </>
  );
}
