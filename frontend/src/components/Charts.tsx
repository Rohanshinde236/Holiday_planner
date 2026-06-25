import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, Title, Tooltip, Legend, Filler,
} from "chart.js";
import { Line, Bar } from "react-chartjs-2";
import type { ChannelResult } from "../types";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler);

const css = (v: string) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

/** DIAGRAM 1 — all years (actuals) + forecast, yearly totals (line). */
export function YearTrendChart({ res, label }: { res: ChannelResult; label: string }) {
  const years = Object.keys(res.impacts);                 // Y1..Y3
  const reco = res.recommended;
  // actual volume per year = baseline*(1+impact) is not stored; use impact% magnitude instead.
  // We plot the recommended forecast against the historical impact% trend for clarity.
  const labels = [...years, "Forecast"];
  const impacts = years.map((y) => res.impacts[y] ?? 0);
  const data = {
    labels,
    datasets: [
      {
        label: "Historical impact %",
        data: [...impacts, null],
        borderColor: css("--color-text-secondary"),
        backgroundColor: css("--color-text-secondary"),
        spanGaps: true,
      },
      {
        label: "Forecast impact %",
        data: [...years.map(() => null), reco ? reco.blended_impact_pct : 0],
        borderColor: css("--color-primary"),
        backgroundColor: css("--color-primary"),
        pointRadius: 6,
      },
    ],
  };
  return (
    <div className="chart-wrap">
      <Line data={data as any} options={{ maintainAspectRatio: false, plugins: { title: { display: true, text: `${label} — year impact % + forecast (${reco?.combo ?? "-"})` } } }} />
    </div>
  );
}

/** DIAGRAM 2 — intraday staffing curve: gross HC per 30-min slot (line/area). */
export function StaffingCurveChart({ res, label }: { res: ChannelResult; label: string }) {
  if (!res.intervals.length) {
    return <p className="hint">Email uses a flat daily figure — no interval curve.</p>;
  }
  const data = {
    labels: res.intervals.map((i) => i.start),
    datasets: [
      {
        label: "Gross HC",
        data: res.intervals.map((i) => i.gross_hc),
        borderColor: css("--color-primary"),
        backgroundColor: css("--color-primary-weak"),
        fill: true, tension: 0.3,
      },
      {
        label: "Net HC",
        data: res.intervals.map((i) => i.net_hc),
        borderColor: css("--color-text-secondary"),
        fill: false, tension: 0.3, borderDash: [5, 4],
      },
    ],
  };
  return (
    <div className="chart-wrap">
      <Line data={data as any} options={{ maintainAspectRatio: false, plugins: { title: { display: true, text: `${label} — staffing per 30-min slot (busiest day: ${res.busiest_day})` } } }} />
    </div>
  );
}

/** DIAGRAM 6 — intraday overlay: each year's per-slot shape + the forecast shape. */
export function IntradayOverlayChart({ res, label }: { res: ChannelResult; label: string }) {
  const ov = res.intraday_overlay;
  if (!ov) {
    return <p className="hint">Enter per-year intraday history below to see the all-years overlay.</p>;
  }
  const palette = ["#9aa3b5", "#b8c0d0", "#c9a0dc", "#a0c9b0", "#d6b88a"];
  const yearSets = Object.entries(ov.per_year).map(([y, arr], i) => ({
    label: y,
    data: arr.map((v) => +(v * 100).toFixed(2)),     // % of day
    borderColor: palette[i % palette.length],
    borderWidth: 1.5, pointRadius: 0, tension: 0.3,
  }));
  const data = {
    labels: ov.slots,
    datasets: [
      ...yearSets,
      {
        label: "Forecast", data: ov.forecast.map((v) => +(v * 100).toFixed(2)),
        borderColor: css("--color-primary"), borderWidth: 3, pointRadius: 0, tension: 0.3,
      },
    ],
  };
  return (
    <div className="chart-wrap">
      <Line data={data as any} options={{ maintainAspectRatio: false, plugins: { title: { display: true, text: `${label} — intraday shape: all years + forecast (% of day per slot)` } } }} />
    </div>
  );
}

/** Daily volume bar (Sat-first). */
export function DailyBarChart({ res, label }: { res: ChannelResult; label: string }) {
  const labels = Object.keys(res.daily);
  const data = {
    labels,
    datasets: [{ label: "Volume", data: Object.values(res.daily), backgroundColor: css("--color-primary") }],
  };
  return (
    <div className="chart-wrap">
      <Bar data={data as any} options={{ maintainAspectRatio: false, plugins: { title: { display: true, text: `${label} — daily volume (Sat-first)` } } }} />
    </div>
  );
}
