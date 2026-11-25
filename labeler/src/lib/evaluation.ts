// Blind hand check of tracker quality: a fixed random sample of tracks per tracker from the validation
// sequences, shown without the tracker's name and judged one by one. Stored in labels/tracker_eval.jsonl.
import { existsSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { LABELS_DIR, readSplits } from "./store";
import { trackerFolders, trackerRuns } from "./trackers";

// order matters: a new tracker goes to the end, so the samples of the others (and their verdicts) stay the same
export const EVAL_TRACKERS = ["flights_chiron_sort", "flights_chiron", "flights", "flights_chiron_linked", "flights_darian_hybrid",
  "flights_sledevic26_hybrid", "flights_darian_botsort_bee"];
export const PER_TRACKER = 30;
// 17.11.: the trackers on slide 2 (SORT, Chiron, Chiron + Huang) and the Sledevič YOLO26s hybrid get 60 tracks each,
// the Darian hybrid 30 (only for background). The first 30 per tracker are the same as before (the shuffle per tracker
// does not depend on the sample size), so the verdicts of 31.10. stay valid.
export const PER: Record<string, number> = { flights_chiron_sort: 60, flights_chiron: 60, flights_chiron_linked: 60,
  flights_sledevic26_hybrid: 60 };
export const perTracker = (k: string) => PER[k] ?? PER_TRACKER;
export const EVAL_TOTAL = EVAL_TRACKERS.reduce((a, k) => a + perTracker(k), 0);
const SEED = 2013;
export const VERDICTS = [
  { key: "korrekt", name: "Korrekt und ganz", hint: "eine Biene, von Brett/Rand bis Brett/Rand" },
  { key: "bruchstueck", name: "Korrekt, aber Bruchstück", hint: "eine Biene, aber Anfang oder Ende fehlt" },
  { key: "wechsel", name: "Bienenwechsel", hint: "springt irgendwo auf eine andere Biene (geht vor Bruchstück)" },
  { key: "keine_biene", name: "Keine Biene", hint: "Schatten, Gras, Fleck" },
] as const;
export type Verdict = (typeof VERDICTS)[number]["key"];
const EVAL_PATH = resolve(LABELS_DIR, "tracker_eval.jsonl");

export interface EvalItem {
  id: string; tracker: string; seq: string; top: number; scale: number;
  t: number[]; xy: [number, number][]; start: string; end: string;
}
export interface EvalRecord { id: string; tracker: string; seq: string; t0: number; verdict: Verdict; at: string }

function rng(seed: number) {
  // mulberry32: small, seeded, so the sample is the same on every page load
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function shuffle<T>(xs: T[], rand: () => number) {
  for (let i = xs.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [xs[i], xs[j]] = [xs[j], xs[i]];
  }
  return xs;
}

/** The sample: PER_TRACKER tracks per tracker from all validation sequences, mixed so the tracker stays hidden. */
export function evalSample(): { items: EvalItem[]; trackers: string[]; missing: string[] } {
  const val = readSplits()?.splits.val ?? [];
  const have = new Set(trackerFolders());
  const trackers = EVAL_TRACKERS.filter((k) => have.has(k));
  const pools = new Map<string, EvalItem[]>(trackers.map((k) => [k, []]));
  const missing: string[] = [];
  for (const seq of val) {
    const runs = trackerRuns(seq);
    for (const k of trackers) {
      const run = runs.find((r) => r.key === k);
      if (!run) { missing.push(`${k}/${seq}`); continue; }
      run.rows.forEach((r, i) => pools.get(k)!.push({
        id: `${k}:${seq}:${i}`, tracker: k, seq, top: run.top, scale: run.scale, t: r.t, xy: r.xy, start: r.start, end: r.end,
      }));
    }
  }
  const rand = rng(SEED);
  const items = trackers.flatMap((k) => shuffle(pools.get(k)!, rand).slice(0, perTracker(k)));
  return { items: shuffle(items, rand), trackers, missing };
}

export function readEval(): Map<string, EvalRecord> {
  const out = new Map<string, EvalRecord>();
  if (!existsSync(EVAL_PATH)) return out;
  for (const line of readFileSync(EVAL_PATH, "utf8").split("\n")) if (line.trim()) {
    const r = JSON.parse(line);
    out.set(r.id, r);
  }
  return out;
}

function writeAll(all: Map<string, object>) {
  const tmp = `${EVAL_PATH}.tmp`;
  writeFileSync(tmp, [...all.values()].map((r) => JSON.stringify(r)).join("\n") + (all.size ? "\n" : ""));
  renameSync(tmp, EVAL_PATH);
}

/** Store one verdict with the full track, so it stays meaningful if the tracker output changes later. */
export function saveVerdict(item: EvalItem, verdict: Verdict) {
  const all: Map<string, object> = readEval();
  const rec = { id: item.id, tracker: item.tracker, seq: item.seq, t0: item.t[0], verdict, at: new Date().toISOString(),
                top: item.top, scale: item.scale, t: item.t, xy: item.xy };
  all.set(item.id, rec);
  writeAll(all);
}

export function removeVerdict(id: string) {
  const all: Map<string, object> = readEval();
  all.delete(id);
  writeAll(all);
}
