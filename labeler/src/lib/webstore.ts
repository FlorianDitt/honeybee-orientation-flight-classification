// Label storage of the web app: one annotator per browser, everything in localStorage, exported as
// JSON lines (one label per line) that `beeflight-vote` merges with the owner's labels.
import type { Label } from "./labeler";

const KEY = "beeflight:v1";

export interface Rec extends Label { split: string; labeled_at: string; practice?: boolean }
interface State { name: string; labels: Record<string, Rec>; practice: Record<string, Rec>; exported_at: string | null }

export interface Site {
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
  return res.json();
}

export function unexported(s: State) {
  return [...Object.values(s.labels), ...Object.values(s.practice)].filter((r) => !s.exported_at || r.labeled_at > s.exported_at).length;
}

const slug = (name: string) => name.trim().toLowerCase().replace(/[^a-z0-9äöüß]+/g, "-").replace(/^-|-$/g, "") || "anonym";

export function exportFile(s: State): { name: string; text: string } {
  const lines = [
    ...Object.entries(s.practice).map(([id, r]) => ({ id, ...r, practice: true })),
    ...Object.entries(s.labels).map(([id, r]) => ({ id, ...r })),
  ].map((r) => JSON.stringify({ ...r, annotator: s.name.trim() }));
  const day = new Date().toISOString().slice(0, 10);
  return { name: `beeflight_${slug(s.name)}_${day}.jsonl`, text: lines.join("\n") + "\n" };
}

/** Merge an earlier export (e.g. from another browser); the newer label of a track wins. */
export function importText(s: State, text: string) {
  let n = 0;
  for (const line of text.split("\n")) {
    if (!line.trim()) continue;
    const { id, annotator, practice, ...rec } = JSON.parse(line);
    if (!s.name && annotator) s.name = annotator;
    const target = practice ? s.practice : s.labels;
    if (!target[id] || target[id].labeled_at < rec.labeled_at) { target[id] = rec; n++; }
  }
  return n;
}
