import { useEffect, useState } from "react";
import type { Plan } from "../types";
import { api } from "../api/client";

function renderReview(text: string) {
  return text.split("\n").filter((l) => l.trim()).map((line, i) => {
    const clean = line.replace(/^[•\-*\s]+/, "");
    const icon = /\[caution\]/i.test(clean) ? "🟡" : /\[check\]/i.test(clean) ? "🔴" : /\[info\]/i.test(clean) ? "🔵" : "•";
    return <div key={i} style={{ marginBottom: 4 }}>{icon} {clean.replace(/\[(info|caution|check)\]/i, "").trim()}</div>;
  });
}

export default function AiPanel({ plan }: { plan: Plan }) {
  const [explain, setExplain] = useState("");
  const [review, setReview] = useState("");
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState("");
  const [nonce, setNonce] = useState(0);   // bump to regenerate

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setBusy(true); setErr("");
      try {
        const [e, r] = await Promise.all([api.explain(plan), api.review(plan)]);
        if (cancelled) return;
        if (e.available === false) { setErr(e.text); }
        else { setExplain(e.text); setReview(r.text); }
      } catch (ex: any) {
        if (!cancelled) setErr(ex.message ?? String(ex));
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => { cancelled = true; };
    // run on mount + when regenerate is pressed (not on every plan change, to avoid cost)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce]);

  const box = { background: "var(--color-primary-weak)", padding: "var(--sp-4)", borderRadius: 8, fontSize: 14, lineHeight: 1.6 } as const;
  const cap = { fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--color-text-secondary)", marginBottom: 6 } as const;

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>🤖 AI assistant <span style={{ fontSize: 12, fontWeight: 400, color: "var(--color-text-secondary)" }}>· explains &amp; reviews — never computes the numbers</span></h2>
        <button className="btn-ghost" onClick={() => setNonce((n) => n + 1)} disabled={busy}>{busy ? "Generating…" : "↻ Regenerate"}</button>
      </div>

      {busy && <p className="hint" style={{ marginTop: 12 }}>Generating explanation &amp; review…</p>}
      {err && <div className="banner info" style={{ marginTop: 12 }}>⚠️ {err}</div>}

      {!busy && !err && (
        <div className="grid grid-2" style={{ marginTop: "var(--sp-3)" }}>
          <div style={box as any}>
            <div style={cap as any}>Plan explanation</div>
            <div style={{ whiteSpace: "pre-wrap" }}>{explain}</div>
          </div>
          <div style={box as any}>
            <div style={cap as any}>Analyst review</div>
            {renderReview(review)}
          </div>
        </div>
      )}
    </div>
  );
}
