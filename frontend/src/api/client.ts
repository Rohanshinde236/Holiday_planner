import type { Plan, ComputeResult } from "../types";

async function post<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = await r.text();
    throw new Error(`${r.status}: ${detail}`);
  }
  return r.json();
}

export const api = {
  health: () => fetch("/health").then((r) => r.json()),

  computePlan: (plan: Plan) => post<ComputeResult>("/api/plan/compute", plan),

  holidayCountries: () =>
    fetch("/api/holidays/countries").then((r) => r.json()),

  searchHolidays: (q: string, country: string, baseYear: number) =>
    fetch(`/api/holidays/search?q=${encodeURIComponent(q)}&country=${country}&base_year=${baseYear}`).then((r) => r.json()),

  holidayDates: (name: string, country: string, baseYear: number, years: number) =>
    fetch(`/api/holidays/dates?name=${encodeURIComponent(name)}&country=${country}&base_year=${baseYear}&years=${years}`).then((r) => r.json()),

  accuracy: (items: { label: string; forecast: number; actual: number }[]) =>
    post<any>("/api/accuracy", { items }),

  llmStatus: () => fetch("/api/llm/status").then((r) => r.json()),
  explain: (plan: Plan) => post<{ available: boolean; text: string }>("/api/plan/explain", plan),
  review: (plan: Plan) => post<{ available: boolean; text: string }>("/api/plan/review", plan),

  shiftOptimise: (body: {
    hc_requirements: { interval: number; start: string; net_hc: number }[];
    available_shifts: { name: string; start: string; end: string }[];
    operating_start: string;
    operating_end: string;
    mode: "greedy" | "ilp";
    available_agents: number;
  }) => post<any>("/api/shift_optimise", body),
};
