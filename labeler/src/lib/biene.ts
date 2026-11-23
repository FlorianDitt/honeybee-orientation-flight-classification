// Is there a honey bee on the track? One answer per artefakt track of train/val (pre-classifier labels).
// The queue and the crop strips come from `python -m beeflight.biene sample`; answers go to labels/biene.jsonl.
import { existsSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { LABELS_DIR, ROOT } from "./store";

const QUEUE = resolve(LABELS_DIR, "biene_queue.json");
const PATH = resolve(LABELS_DIR, "biene.jsonl");
export const STRIPS = resolve(ROOT, "outputs", "biene", "crops");
export const BEE_ANSWERS = ["honigbiene", "anderes_insekt", "kein_tier", "unklar"] as const;
export type BeeAnswer = (typeof BEE_ANSWERS)[number];

export interface BeeItem { id: string; name: string; split: string; seq: string; frames: number }
export interface BeeRecord { id: string; answer: BeeAnswer; at: string }

export function readBeeQueue(): { crop: number; k: number; items: BeeItem[] } | null {
  if (!existsSync(QUEUE)) return null;
  const q = JSON.parse(readFileSync(QUEUE, "utf8"));
  return { crop: q.crop, k: q.k, items: q.items };
}

export function readBee(): Map<string, BeeRecord> {
  const out = new Map<string, BeeRecord>();
  if (!existsSync(PATH)) return out;
  for (const line of readFileSync(PATH, "utf8").split("\n")) {
    if (line.trim()) { const r = JSON.parse(line); out.set(r.id, r); }
  }
  return out;
}

function write(all: Map<string, BeeRecord>) {
  const tmp = `${PATH}.tmp`;
  writeFileSync(tmp, [...all.values()].map((r) => JSON.stringify(r)).join("\n") + (all.size ? "\n" : ""));
  renameSync(tmp, PATH);
}

export function saveBee(id: string, answer: BeeAnswer) {
  const all = readBee();
  all.set(id, { id, answer, at: new Date().toISOString() });
  write(all);
}

export function removeBee(id: string) {
  const all = readBee();
  if (all.delete(id)) write(all);
}
