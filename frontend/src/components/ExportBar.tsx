import { useState } from "react";
import type { Plan, ComputeResult } from "../types";

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  a.remove(); URL.revokeObjectURL(url);
}

function buildCsv(result: ComputeResult, plan: Plan): string {
  const lines: string[] = [];
  lines.push(`Holiday,${plan.holiday?.name ?? "-"}`);
  lines.push(`Plan date,${plan.holiday?.plan_date ?? "-"}`);
  lines.push(`Total shrinkage %,${result.shrinkage.total_shrinkage_pct}`);
  lines.push("");
  lines.push("Channel,Combo,Weekly forecast,Busiest day,Peak Net HC,Peak Gross HC");
  for (const [ch, res] of Object.entries(result.channels)) {
    lines.push([ch, res.recommended?.combo ?? "-", res.weekly_forecast, res.busiest_day, res.peak_net_hc, res.peak_gross_hc].join(","));
  }
  for (const [ch, res] of Object.entries(result.channels)) {
    if (!res.intervals.length) continue;
    lines.push("");
    lines.push(`${ch} — interval HC`);
    lines.push("Start,End,Calls/hr,Net HC,Gross HC");
    for (const iv of res.intervals) lines.push([iv.start, iv.end, iv.calls_per_hour, iv.net_hc, iv.gross_hc].join(","));
  }
  return lines.join("\n");
}

export default function ExportBar({ plan, result }: { plan: Plan; result: ComputeResult | null }) {
  const [busy, setBusy] = useState("");
  const disabled = !result;

  const exportJson = () => download(new Blob([JSON.stringify({ plan, result }, null, 2)], { type: "application/json" }), "holiday-plan.json");
  const exportCsv = () => result && download(new Blob([buildCsv(result, plan)], { type: "text/csv" }), "holiday-plan.csv");

  async function exportServer(kind: "xlsx" | "pdf") {
    setBusy(kind);
    try {
      const r = await fetch(`/api/plan/export.${kind}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(plan),
      });
      if (!r.ok) throw new Error(await r.text());
      download(await r.blob(), `holiday-plan.${kind}`);
    } catch (e: any) {
      alert("Export failed: " + e.message);
    } finally { setBusy(""); }
  }

  return (
    <div style={{ display: "flex", gap: 8 }}>
      <button className="btn-ghost" onClick={exportJson} disabled={disabled}>JSON</button>
      <button className="btn-ghost" onClick={exportCsv} disabled={disabled}>CSV</button>
      <button className="btn-ghost" onClick={() => exportServer("xlsx")} disabled={disabled || !!busy}>{busy === "xlsx" ? "…" : "Excel"}</button>
      <button className="btn-ghost" onClick={() => exportServer("pdf")} disabled={disabled || !!busy}>{busy === "pdf" ? "…" : "PDF"}</button>
    </div>
  );
}
