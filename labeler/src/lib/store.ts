// File-backed storage. Queues come from `beeflight-sample`, labels are JSON lines that keep the
// full track geometry, so they stay usable even if the tracker changes later.
import { existsSync, mkdirSync, readdirSync, readFileSync, renameSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

export const ROOT = resolve(process.env.BEEHIVE_ROOT ?? resolve(process.cwd(), ".."));
export const LABELS_DIR = resolve(ROOT, "labels");
export const VIDEO_DIR = resolve(ROOT, "data", "thehiveisreal", "videos");

export const SPLITS = ["train", "val", "recheck", "test_same_hive", "test_other_hive"] as const;
export type Split = (typeof SPLITS)[number];
export const CLASSES = ["orientierung", "sammelabflug", "anflug", "artefakt"] as const;
export const FLAGS = ["fragment", "unsicher"] as const;
// fallback for queues from before the tracker name was stored; the queue file says which tracker made its tracks
export const TRACKER = "background-v3";
export const VOTES_DIR = resolve(LABELS_DIR, "votes");

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

/** How the tracks of a queue were made, as a short label for the labeling view. */
const TRACKER_INFO: Record<string, string> = {
  "chiron2013-2d-chiron-linked": "Chiron et al. 2013 (Hintergrund, Kalman, Hungarian) + Tracklet-Verknüpfung nach Huang et al. 2008",
  "background-v3": "Median-Hintergrund + Blobs, Hungarian-Zuordnung, Fragmente verbunden",
  "background-v3-board": "wie v3, Landebrett nicht maskiert",
};

export function readQueueTracker(split: Split): { id: string; info: string } | null {
  const id = readQueueFile(split)?.tracker;
  return id ? { id, info: TRACKER_INFO[id] ?? "" } : null;
}

function readQueueFile(split: Split): { items: QueueItem[]; core?: number; tracker?: string } | null {
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
    tracker: readQueueFile(split)?.tracker ?? TRACKER,
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

export interface VoteFile {
  file: string;
  annotator: string;
  labels: number;
  practice: number;
  splits: Record<string, number>;
  modified: string;
}

/** Exports of the web labeler in labels/votes/, as read by `beeflight-vote`. */
export function readVoteFiles(): VoteFile[] {
  if (!existsSync(VOTES_DIR)) return [];
  return readdirSync(VOTES_DIR, { withFileTypes: true })
    .filter((e) => e.isFile() && e.name.endsWith(".jsonl"))
    .map((e) => {
      const path = resolve(VOTES_DIR, e.name);
      const recs = readFileSync(path, "utf8").split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));
      const splits: Record<string, number> = {};
      for (const r of recs) if (!r.practice) splits[r.split] = (splits[r.split] ?? 0) + 1;
      return {
        file: e.name,
        annotator: recs.find((r) => r.annotator)?.annotator ?? e.name.replace(/\.jsonl$/, ""),
        labels: recs.filter((r) => !r.practice).length,
        practice: recs.filter((r) => r.practice).length,
        splits,
        modified: statSync(path).mtime.toISOString(),
      };
    })
    .sort((a, b) => a.annotator.localeCompare(b.annotator) || a.file.localeCompare(b.file));
}

/**
 * Check one export and store it in labels/votes/. Every line must be a label of the web labeler
 * (known class, practice or a known split); returns the file name or throws with a reason.
 */
export function saveVoteFile(name: string, text: string): { file: string; annotator: string; labels: number; practice: number; replaced: boolean } {
  const recs = text.split("\n").filter((l) => l.trim()).map((l, i) => {
    try {
      return JSON.parse(l);
    } catch {
      throw new Error(`Zeile ${i + 1} ist kein JSON`);
    }
  });
  if (!recs.length) throw new Error("Datei ist leer");
  const names = new Set(recs.map((r) => String(r.annotator ?? "").trim().toLowerCase()).filter(Boolean));
  if (names.size !== 1) throw new Error(names.size ? `mehrere Namen in einer Datei: ${[...names].join(", ")}` : "kein Name (annotator) in der Datei");
  recs.forEach((r, i) => {
    if (typeof r.id !== "string" || !CLASSES.includes(r.label)) throw new Error(`Zeile ${i + 1}: keine gültige Bahn/Klasse`);
    if (!r.practice && !isSplit(r.split)) throw new Error(`Zeile ${i + 1}: unbekannter Split ${r.split}`);
  });
  const annotator = [...names][0];
  const base = name.replace(/\.jsonl$/i, "").replace(/[^A-Za-z0-9_.-]+/g, "_").replace(/^[._]+/, "") ||
    `beeflight_${annotator}_${new Date().toISOString().slice(0, 10)}`;
  const file = `${base}.jsonl`;
  mkdirSync(VOTES_DIR, { recursive: true });
  const path = resolve(VOTES_DIR, file);
  const replaced = existsSync(path);
  const tmp = `${path}.tmp`;
  writeFileSync(tmp, recs.map((r) => JSON.stringify(r)).join("\n") + "\n");
  renameSync(tmp, path);
  return { file, annotator, labels: recs.filter((r) => !r.practice).length, practice: recs.filter((r) => r.practice).length, replaced };
}

/** Delete one export from labels/votes/. Only plain .jsonl names inside that folder are accepted. */
export function deleteVoteFile(name: string): { file: string } {
  if (!/^[A-Za-z0-9_.-]+\.jsonl$/.test(name) || name.startsWith(".")) throw new Error(`ungültiger Dateiname: ${name}`);
  const path = resolve(VOTES_DIR, name);
  if (!existsSync(path)) throw new Error(`Datei nicht gefunden: ${name}`);
  unlinkSync(path);
  return { file: name };
}

/** Sequence ids per split and the unused buffers, from splits.json (written by `beeflight-splits`). */
export function readSplits(): { splits: Record<string, string[]>; buffers: string[] } | null {
  const path = resolve(ROOT, "splits.json");
  return existsSync(path) ? JSON.parse(readFileSync(path, "utf8")) : null;
}
