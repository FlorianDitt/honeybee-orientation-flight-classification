// Server side of the comparison page: all votes per track, the outcome under the rules of
// `beeflight-vote` (src/beeflight/vote.py) and agreement between annotators.
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { CLASSES, LABELS_DIR, VOTES_DIR, readLabels, readQueue, readVoteFiles, type Split } from "./store";

export const OWNER = "florian"; // same default as `beeflight-vote --owner`
export const COMPARE_SPLITS = ["train", "val"] as const satisfies readonly Split[];

export interface Vote { label: string; flags: string[]; note: string }
export interface Row {
  id: string;
  split: string;            // train, val or "practice"
  stratum: string;
  inQueue: boolean;
  votes: Record<string, Vote>;
  answer?: string;          // practice only: the owner's reference label
  result: string | null;    // majority, else owner, else null
  how: "majority" | "owner" | "open" | "single";
  agree: boolean;           // all votes the same class
}

const jsonl = (path: string) =>
  readFileSync(path, "utf8").split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));

function decide(votes: Record<string, Vote>): Pick<Row, "result" | "how"> {
  const counts = new Map<string, number>();
  for (const v of Object.values(votes)) counts.set(v.label, (counts.get(v.label) ?? 0) + 1);
  const n = Object.keys(votes).length;
  const [top, c] = [...counts].sort((a, b) => b[1] - a[1])[0];
  if (n === 1) return { result: top, how: "single" };
  if (2 * c > n) return { result: top, how: "majority" };
  if (votes[OWNER]) return { result: votes[OWNER].label, how: "owner" };
  return { result: null, how: "open" };
}

export function compare() {
  const rows: Row[] = [];
  const friends = new Set<string>();
  // friends: newest label per track and person, practice kept apart (as in vote.py)
  const theirs = new Map<string, Map<string, Vote & { at: string; split: string }>>();
  const practice = new Map<string, Record<string, Vote>>();
  for (const f of readVoteFiles()) {
    for (const r of jsonl(resolve(VOTES_DIR, f.file))) {
      const who = String(r.annotator ?? "").trim().toLowerCase() || f.file.replace(/\.jsonl$/, "");
      if (who === OWNER) continue;
      friends.add(who);
      const vote = { label: r.label, flags: r.flags ?? [], note: r.note ?? "" };
      if (r.practice) {
        (practice.get(r.id) ?? practice.set(r.id, {}).get(r.id)!)[who] = vote;
        continue;
      }
      const key = `${r.split}|${r.id}`;
      const by = theirs.get(key) ?? theirs.set(key, new Map()).get(key)!;
      const old = by.get(who);
      if (!old || old.at < r.labeled_at) by.set(who, { ...vote, at: r.labeled_at, split: r.split });
    }
  }

  for (const split of COMPARE_SPLITS) {
    const queue = new Map((readQueue(split) ?? []).map((i) => [i.id, i]));
    const mine = readLabels(split);
    const ids = new Set([...mine.keys(), ...[...theirs.keys()].filter((k) => k.startsWith(`${split}|`)).map((k) => k.slice(split.length + 1))]);
    for (const id of ids) {
      const votes: Record<string, Vote> = {};
      const m = mine.get(id);
      if (m) votes[OWNER] = { label: m.label, flags: m.flags, note: m.note };
      for (const [who, v] of theirs.get(`${split}|${id}`) ?? []) votes[who] = { label: v.label, flags: v.flags, note: v.note };
      const labels = new Set(Object.values(votes).map((v) => v.label));
      rows.push({ id, split, stratum: queue.get(id)?.stratum ?? "", inQueue: queue.has(id), votes, ...decide(votes), agree: labels.size === 1 });
    }
  }

  const practicePath = resolve(LABELS_DIR, "practice.json");
  const answers: { id: string; answer: string }[] = existsSync(practicePath) ? JSON.parse(readFileSync(practicePath, "utf8")).items : [];
  for (const { id, answer } of answers) {
    const votes = practice.get(id) ?? {};
    const right = Object.values(votes).every((v) => v.label === answer);
    rows.push({ id, split: "practice", stratum: "", inQueue: true, votes, answer, result: answer, how: "owner", agree: right });
  }

  // agreement on tracks both labeled (practice counts against the reference answer)
  const people = [OWNER, ...[...friends].sort()];
  const pairs: Record<string, Record<string, [number, number]>> = {};
  for (const a of people) {
    pairs[a] = {};
    for (const b of people) pairs[a][b] = [0, 0];
  }
  const confusion: Record<string, Record<string, number>> = Object.fromEntries(CLASSES.map((c) => [c, Object.fromEntries(CLASSES.map((d) => [d, 0]))]));
  for (const r of rows) {
    if (r.split === "practice") continue;
    const who = Object.keys(r.votes);
    for (const a of who) for (const b of who) {
      if (a === b) continue;
      pairs[a][b][0] += +(r.votes[a].label === r.votes[b].label);
      pairs[a][b][1] += 1;
    }
    const own = r.votes[OWNER];
    if (own) for (const b of who) if (b !== OWNER) confusion[own.label][r.votes[b].label] += 1;
  }
  const scores = people.slice(1).map((who) => {
    const done = answers.filter((a) => practice.get(a.id)?.[who]);
    return { who, practice: [done.filter((a) => practice.get(a.id)![who].label === a.answer).length, done.length] as [number, number] };
  });
  return { rows, people, pairs, confusion, scores };
}
