// File-backed storage. Queues come from `beeflight-sample`, labels are JSON lines that keep the
// full track geometry, so they stay usable even if the tracker changes later.
import { existsSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

export const ROOT = resolve(process.env.BEEHIVE_ROOT ?? resolve(process.cwd(), ".."));
export const LABELS_DIR = resolve(ROOT, "labels");
export const VIDEO_DIR = resolve(ROOT, "data", "thehiveisreal", "videos");

export const SPLITS = ["train", "val", "recheck", "test_same_hive", "test_other_hive"] as const;
export type Split = (typeof SPLITS)[number];
export const CLASSES = ["orientierung", "sammelabflug", "anflug", "artefakt"] as const;
export const FLAGS = ["fragment", "unsicher"] as const;
export const TRACKER = "background-v2";

export interface QueueItem {
  id: string;
  seq: string;
  t0: number;
  t1: number;
  top: number;
  scale: number;
  t: number[];
  xy: [number, number][];
  stratum: string;
}

export interface Label {
  id: string;
  label: (typeof CLASSES)[number];
  flags: string[];
  note: string;
  labeled_at: string;
}

export const isSplit = (s: unknown): s is Split => SPLITS.includes(s as Split);

export function readQueue(split: Split): QueueItem[] | null {
  return readQueueFile(split)?.items ?? null;
}

/** Number of leading items that form the stratified sample (the rest is everything else, for completeness). */
export function readCore(split: Split): number {
  const q = readQueueFile(split);
  return q?.core ?? q?.items.length ?? 0;
}

function readQueueFile(split: Split): { items: QueueItem[]; core?: number } | null {
  const path = resolve(LABELS_DIR, `queue_${split}.json`);
  if (!existsSync(path)) return null;
  return JSON.parse(readFileSync(path, "utf8"));
}

function labelPath(split: Split) {
  return resolve(LABELS_DIR, `${split}.jsonl`);
}

export function readLabels(split: Split): Map<string, Label> {
  const path = labelPath(split);
  const out = new Map<string, Label>();
  if (!existsSync(path)) return out;
  for (const line of readFileSync(path, "utf8").split("\n")) {
    if (!line.trim()) continue;
    const rec = JSON.parse(line);
    out.set(rec.id, rec);
  }
  return out;
}

/** Insert or replace one label; the file is rewritten atomically so a crash never leaves half a line. */
export function writeLabel(split: Split, item: QueueItem, label: Omit<Label, "id" | "labeled_at">) {
  const path = labelPath(split);
  const all = new Map<string, object>();
  if (existsSync(path)) {
    for (const line of readFileSync(path, "utf8").split("\n")) {
      if (line.trim()) all.set(JSON.parse(line).id, JSON.parse(line));
    }
  }
  const rec = {
    id: item.id,
    ...label,
    labeled_at: new Date().toISOString(),
    split,
    seq: item.seq,
    t0: item.t0,
    tracker: TRACKER,
    top: item.top,
    scale: item.scale,
    t: item.t,
    xy: item.xy,
  };
  all.set(item.id, rec);
  const tmp = `${path}.tmp`;
  writeFileSync(tmp, [...all.values()].map((r) => JSON.stringify(r)).join("\n") + "\n");
  renameSync(tmp, path);
  return rec;
}

export function removeLabel(split: Split, id: string) {
  const path = labelPath(split);
  if (!existsSync(path)) return;
  const keep = readFileSync(path, "utf8")
    .split("\n")
    .filter((l: string) => l.trim() && JSON.parse(l).id !== id);
  const tmp = `${path}.tmp`;
  writeFileSync(tmp, keep.length ? keep.join("\n") + "\n" : "");
  renameSync(tmp, path);
}
