// Head/tail clicks on single-frame crops of flying bees (pilot: can the body axis be read from the video?).
// The sample and the crops come from `beeflight-pose sample`; clicks are stored in labels/pose.jsonl.
import { existsSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { LABELS_DIR, ROOT } from "./store";

const QUEUE = resolve(LABELS_DIR, "pose_queue.json");
const PATH = resolve(LABELS_DIR, "pose.jsonl");
export const CROPS = resolve(ROOT, "outputs", "pose", "crops");
export const POSE_FLAGS = ["richtung_unsicher", "unklar"] as const;

// deliberately without the automatic estimate (`est`): the labeler must not see it
export interface PoseItem { id: string; name: string; seq: string; t: number; px: number; py: number }
export interface PoseRecord {
  id: string; head: [number, number] | null; tail: [number, number] | null; flags: string[]; at: string;
}

export function readPoseQueue(): { crop: number; context: number; items: PoseItem[] } | null {
  if (!existsSync(QUEUE)) return null;
  const q = JSON.parse(readFileSync(QUEUE, "utf8"));
  return {
    crop: q.crop, context: q.context,
    items: q.items.map((i: PoseItem) => ({ id: i.id, name: i.name, seq: i.seq, t: i.t, px: i.px, py: i.py })),
  };
}

export function readPose(): Map<string, PoseRecord> {
  const out = new Map<string, PoseRecord>();
  if (!existsSync(PATH)) return out;
  for (const line of readFileSync(PATH, "utf8").split("\n")) {
    if (line.trim()) { const r = JSON.parse(line); out.set(r.id, r); }
  }
  return out;
}

function write(all: Map<string, PoseRecord>) {
  const tmp = `${PATH}.tmp`;
  writeFileSync(tmp, [...all.values()].map((r) => JSON.stringify(r)).join("\n") + (all.size ? "\n" : ""));
  renameSync(tmp, PATH);
}

export function savePose(rec: Omit<PoseRecord, "at">) {
  const all = readPose();
  all.set(rec.id, { ...rec, at: new Date().toISOString() });
  write(all);
}

export function removePose(id: string) {
  const all = readPose();
  if (all.delete(id)) write(all);
}
