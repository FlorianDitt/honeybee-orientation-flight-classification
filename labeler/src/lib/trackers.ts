// Tracker outputs for the comparison viewer: every outputs/flights*/<seq>.json, one folder per tracker.
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { ROOT } from "./store";

const OUTPUTS = resolve(ROOT, "outputs");
// older tracker generations, kept for the slides only
const SKIP = new Set(["flights_v1", "flights_v2"]);
const NAMES: Record<string, string> = { flights: "v3 (Hintergrundmodell)", flights_sort_bee: "SORT für Bienen", flights_sort_bee_board: "SORT für Bienen mit Landebrett", flights_chiron_sort: "Chiron + SORT", flights_chiron_strict: "Chiron, strengere Schwellen", flights_chiron_linked: "Chiron + Huang 2008 (final)", flights_chiron_sort_noboard: "Chiron + SORT ohne Landebrett", flights_chiron: "Chiron et al. 2013 pur", flights_chiron_noboard: "Chiron et al. 2013 ohne Landebrett", flights_board: "v3 mit Landebrett" };

export interface Flight { t: number[]; xy: [number, number][]; start: string; end: string; dur_s: number; abs_turn_deg: number }
export interface TrackerRun { key: string; name: string; tracker: string; top: number; scale: number; rows: Flight[] }

export function trackerFolders(): string[] {
  if (!existsSync(OUTPUTS)) return [];
  return readdirSync(OUTPUTS, { withFileTypes: true })
    .filter((e) => e.isDirectory() && /^flights(_\w+)?$/.test(e.name) && !SKIP.has(e.name))
    .map((e) => e.name)
    .sort((a, b) => (a === "flights" ? -1 : b === "flights" ? 1 : a.localeCompare(b)));
}

/** Sequences with results of at least two trackers, so there is something to compare. */
export function comparableSeqs(): string[] {
  const count = new Map<string, number>();
  for (const f of trackerFolders()) {
    for (const file of readdirSync(resolve(OUTPUTS, f))) {
      const m = /^(rec\d{4}_seq\d{3})\.json$/.exec(file);
      if (m) count.set(m[1], (count.get(m[1]) ?? 0) + 1);
    }
  }
  return [...count].filter(([, n]) => n >= 2).map(([s]) => s).sort();
}

/** Sequences one tracker has results for. */
export function seqsOf(folder: string): Set<string> {
  const dir = resolve(OUTPUTS, folder);
  return new Set(existsSync(dir) ? readdirSync(dir).filter((f) => /^rec\d{4}_seq\d{3}\.json$/.test(f)).map((f) => f.slice(0, -5)) : []);
}

export function trackerRuns(seq: string): TrackerRun[] {
  if (!/^rec\d{4}_seq\d{3}$/.test(seq)) return [];
  return trackerFolders().flatMap((key) => {
    const path = resolve(OUTPUTS, key, `${seq}.json`);
    if (!existsSync(path)) return [];
    const d = JSON.parse(readFileSync(path, "utf8"));
    const rows: Flight[] = d.rows.map((r: Flight) => ({ t: r.t, xy: r.xy, start: r.start, end: r.end, dur_s: r.dur_s, abs_turn_deg: r.abs_turn_deg }));
    return [{ key, name: NAMES[key] ?? key.replace(/^flights_/, ""), tracker: d.tracker ?? key, top: d.top, scale: d.scale, rows }];
  });
}
