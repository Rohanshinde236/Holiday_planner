export type Channel = "voice" | "chat" | "email" | "blended";

export interface YearData { baseline: number | null; actual: number | null; }
export type Historical = Record<string, YearData>; // Y1..Y5

export interface ChannelParams {
  plan_volume: number;
  aht_seconds: number;
  operating_start: string;
  operating_end: string;
  sl_target_pct?: number;
  sl_target_seconds?: number;
  concurrency?: number;
  occupancy_target_pct?: number;
  ibu_pct?: number;            // voice — In-Bound Utilization %
  utilization_pct?: number;    // chat — Utilization %
  voice_pct?: number;          // blended — voice share %
  chat_pct?: number;           // blended — chat share %
  voice_aht?: number;          // blended — voice AHT (sec)
  chat_aht?: number;           // blended — chat AHT (sec)
}

export interface HolidayDates {
  name: string;
  country: string;
  plan_year: number;
  plan_date: string | null;
  history: { slot: string; year: number; date: string | null }[];
}

export interface Plan {
  channels: Channel[];
  queue?: { name: string; region: string; type: string };  // plan context label
  years_of_history?: number;             // drives how many Y-slots show everywhere (default 3)
  shrinkage: { planned: number; unplanned: number; training: number };
  anomaly_years: string[];
  params: Record<string, ChannelParams>;
  historical: Record<string, Historical>;
  day_split: Record<string, number[]>; // 7 fractions Sat..Fri
  holiday?: HolidayDates;                // selected from the calendar (optional)
  daily_history?: Record<string, Record<string, number[]>>; // {channel:{year:[7 Sat-first]}}
  normal_week?: Record<string, number[]>;                    // {channel:[7]}
  intraday_history?: Record<string, Record<string, number[]>>; // {channel:{year:[slots]}}
  selected_combos?: Record<string, string>;                     // {channel: combo override}
}

/** Map year slot -> calendar year from the holiday's history (e.g. {Y1:2024, Y2:2023}). */
export function slotYearMap(plan: Plan): Record<string, number> {
  const m: Record<string, number> = {};
  for (const h of plan.holiday?.history ?? []) if (h.slot && h.year) m[h.slot] = h.year;
  return m;
}

/** Convert a combo name ("Y1", "Avg(Y1+Y2)") to calendar-year labels ("Last Year 2024", "Avg(2024+2023)"). */
export function comboLabel(name: string, sy: Record<string, number>): string {
  if (!sy || !Object.keys(sy).length) return name;
  const lab = (slot: string) => {
    const y = sy[slot];
    if (!y) return slot;
    return slot === "Y1" ? `Last Year ${y}` : `${y}`;
  };
  const avg = name.match(/^Avg\((.+)\)$/);
  if (avg) return `Avg(${avg[1].split("+").map(lab).join("+")})`;
  if (/^Y\d$/.test(name)) return lab(name);
  return name;
}

export interface Combo {
  combo: string; years: string[]; impacts: number[];
  blended_impact_pct: number; forecasted_volume: number;
  score: number; contains_anomaly: boolean; recommended: boolean;
}

export interface IntervalHC {
  start: string; end: string; calls_per_hour: number; net_hc: number; gross_hc: number;
}

export interface IntradayOverlay {
  slots: string[];
  per_year: Record<string, number[]>;
  forecast: number[];
}

export interface ChannelResult {
  impacts: Record<string, number | null>;
  combinations: Combo[];
  recommended: Combo | null;
  weekly_forecast: number;
  daily: Record<string, number>;
  busiest_day: string;
  split_source?: string;
  anchored?: boolean;
  intervals: IntervalHC[];
  peak_net_hc: number;
  peak_gross_hc: number;
  intraday_source?: string;
  intraday_overlay?: IntradayOverlay | null;
  days_hc?: { day: string; volume: number; peak_net_hc: number; peak_gross_hc: number }[];
}

export interface ComputeResult {
  shrinkage: { total_shrinkage_pct: number; gross_multiplier: number };
  channels: Record<string, ChannelResult>;
}

export const DAYS = ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"];
export const YEARS = ["Y1", "Y2", "Y3", "Y4", "Y5"];
/** Year slots driven by "years of history" (e.g. 2 → ["Y1","Y2"]). Clamped 1–5. */
export const yearSlots = (n?: number): string[] =>
  Array.from({ length: Math.max(1, Math.min(5, n ?? 3)) }, (_, i) => `Y${i + 1}`);
