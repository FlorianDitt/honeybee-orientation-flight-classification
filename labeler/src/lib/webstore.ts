// Label storage of the web app: one annotator per browser, everything in localStorage, exported as
// JSON lines (one label per line) that `beeflight-vote` merges with the owner's labels.
import type { Label } from "./labeler";

const KEY = "beeflight:v1";

export interface Rec extends Label { split: string; labeled_at: string; practice?: boolean }
interface State {
  name: string; labels: Record<string, Rec>; practice: Record<string, Rec>; exported_at: string | null;
  /** tracker of the tracks the labels refer to; missing = from before it was stored */
  tracker?: string;
}
// the tracker of the online tracks before the name was stored in site.json
const FIRST_TRACKER = "background-v3";

export interface Site {
  tracker?: string;
  /** old tracker -> {old id: new id}: labels made on earlier tracks move to the same flights */
  id_map?: Record<string, Record<string, string>>;
  fps: [number, number];
  items: Record<string, SiteItem>;
  packages: { id: string; split: string; name: string; items: string[] }[];
  practice: { id: string; answer: string }[];
}
export interface SiteItem {
  id: string; split: string; seq: string; t0: number; t1: number; t: number[]; pts: [number, number][];
  offset: number; last: number; region: { x: number; y: number; s: number }; k: number; clip: string; still: string;
}

export const BASE = import.meta.env.BASE_URL.replace(/\/?$/, "/");

let memory: State | null = null;
export let persistent = true;

function empty(): State {
  return { name: "", labels: {}, practice: {}, exported_at: null };
}

export function load(): State {
  if (memory) return memory;
  try {
    const raw = localStorage.getItem(KEY);
    memory = raw ? { ...empty(), ...JSON.parse(raw) } : empty();
  } catch {
    persistent = false;
    memory = empty();
  }
  return memory!;
}

export function store(s: State) {
  memory = s;
  try {
    localStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    persistent = false;
  }
}

export async function site(): Promise<Site> {
  const res = await fetch(`${BASE}data/site.json`);
  if (!res.ok) throw new Error(`site.json: HTTP ${res.status}`);
  const data: Site = await res.json();
  migrate(load(), data);
  return data;
}

/**
 * The online tracks were replaced by another tracker: move the labels of this browser to the same flights
 * on the new tracks. Labels without a matching flight are dropped (`beeflight-vote` drops them too); the
 * state before is kept under its own key in case anything goes wrong.
 */
function migrate(s: State, data: Site) {
  const now = data.tracker ?? FIRST_TRACKER;
  const was = s.tracker ?? FIRST_TRACKER;
  if (was === now) {
    if (!s.tracker) { s.tracker = now; store(s); }
    return;
  }
  const map = data.id_map?.[was];
  if (!map) return;  // no way to translate: leave the labels alone
  try { localStorage.setItem(`${KEY}:backup:${was}`, JSON.stringify(s)); } catch { /* best effort */ }
  const move = (recs: Record<string, Rec>) =>
    Object.fromEntries(Object.entries(recs).flatMap(([id, r]) => (map[id] ? [[map[id], r]] : [])));
  s.labels = move(s.labels);
  s.practice = move(s.practice);
  s.tracker = now;
  s.exported_at = null;  // everything counts as new, so the next export carries the new ids
  store(s);
}

export function unexported(s: State) {
  return [...Object.values(s.labels), ...Object.values(s.practice)].filter((r) => !s.exported_at || r.labeled_at > s.exported_at).length;
}

const slug = (name: string) => name.trim().toLowerCase().replace(/[^a-z0-9äöüß]+/g, "-").replace(/^-|-$/g, "") || "anonym";

export function exportFile(s: State): { name: string; text: string } {
  const lines = [
    ...Object.entries(s.practice).map(([id, r]) => ({ id, ...r, practice: true })),
    ...Object.entries(s.labels).map(([id, r]) => ({ id, ...r })),
  ].map((r) => JSON.stringify({ ...r, tracker: s.tracker ?? FIRST_TRACKER, annotator: s.name.trim() }));
  const day = new Date().toISOString().slice(0, 10);
  return { name: `beeflight_${slug(s.name)}_${day}.jsonl`, text: lines.join("\n") + "\n" };
}

/** Merge an earlier export (e.g. from another browser); the newer label of a track wins. */
export function importText(s: State, text: string) {
  let n = 0;
  for (const line of text.split("\n")) {
    if (!line.trim()) continue;
    const { id, annotator, practice, tracker, ...rec } = JSON.parse(line);
    if ((tracker ?? FIRST_TRACKER) !== (s.tracker ?? FIRST_TRACKER)) continue;  // made on other tracks
    if (!s.name && annotator) s.name = annotator;
    const target = practice ? s.practice : s.labels;
    if (!target[id] || target[id].labeled_at < rec.labeled_at) { target[id] = rec; n++; }
  }
  return n;
}
