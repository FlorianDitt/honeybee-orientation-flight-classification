// Local-only: takes a snapshot of the result files in the repo (outputs/, labels/) into site/src/data/.
// Only numbers, labels and track coordinates are written: no video, frames, crops, notes or volunteer names.
// Test results are only copied (outputs/final/test_ergebnis.json, outputs/eval/test_*/summary.json), never recomputed.
// Run: npm run snapshot   (needs the repo's outputs/ and labels/, so it is not part of the CI build)
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("../..", import.meta.url));
const OUT = resolve(ROOT, "site", "src", "data");
const CLASSES = ["orientierung", "sammelabflug", "anflug", "artefakt"];
const SPLITS = ["train", "val", "test_same_hive", "test_other_hive"];
mkdirSync(OUT, { recursive: true });

const need = (...p) => {
  const f = resolve(ROOT, ...p);
  if (!existsSync(f)) throw new Error(`Quelle fehlt: ${f}`);
  return f;
};
const text = (...p) => readFileSync(need(...p), "utf8");
const json = (...p) => JSON.parse(text(...p));
const jsonl = (...p) => text(...p).split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l));
const write = (name, data) => writeFileSync(resolve(OUT, name), typeof data === "string" ? data : JSON.stringify(data));
const sizes = {};

// 1. plain copies of result files
const COPIES = [
  ["hp_vergleich.json", ["outputs", "hp_vergleich.json"]],
  ["setups_vergleich.json", ["outputs", "setups_vergleich.json"]],
  ["modelle2_vergleich.json", ["outputs", "modelle2_vergleich.json"]],
  ["tracker_vergleich.json", ["outputs", "tracker_vergleich.json"]],
  ["vorfilter_auswahl.json", ["outputs", "final", "vorfilter", "auswahl.json"]],
  ["test_ergebnis.json", ["outputs", "final", "test_ergebnis.json"]],
  ["test_summary_same_hive.json", ["outputs", "eval", "test_same_hive", "summary.json"]],
  ["test_summary_other_hive.json", ["outputs", "eval", "test_other_hive", "summary.json"]],
];
for (const [name, src] of COPIES) {
  JSON.parse(text(...src)); // must be valid JSON
  write(name, text(...src));
}

// 2. what the artefact tracks show (hand answers), per split; newest answer per track
{
  const queue = json("labels", "biene_queue.json");
  const split = Object.fromEntries(queue.items.map((i) => [i.id, i.split]));
  const answer = new Map();
  for (const r of jsonl("labels", "biene.jsonl")) answer.set(r.id, r.answer);
  const out = { train: {}, val: {}, total: {} };
  for (const [id, a] of answer) {
    const s = split[id];
    if (!s) continue;
    out[s] ??= {};
    out[s][a] = (out[s][a] ?? 0) + 1;
    out.total[a] = (out.total[a] ?? 0) + 1;
  }
  write("artefakt_inhalt.json", out);
}

// 3. blind hand check of the trackers: counts per verdict only (no tracks, no times, no sequences)
{
  const names = Object.fromEntries([...text("site", "src", "lib", "names.ts").matchAll(/(\w+): "([^"]*)"/g)].map((m) => [m[1], m[2]]));
  const ORDER = ["flights_chiron_sort", "flights_chiron", "flights", "flights_chiron_linked", "flights_darian_hybrid", "flights_sledevic26_hybrid", "flights_darian_botsort_bee"];
  const byId = new Map();
  for (const r of jsonl("labels", "tracker_eval.jsonl")) byId.set(r.id, r);
  const per = {};
  for (const r of byId.values()) {
    const t = (per[r.tracker] ??= { n: 0, korrekt: 0, bruchstueck: 0, wechsel: 0, keine_biene: 0 });
    if (!(r.verdict in t)) throw new Error(`unbekanntes Urteil: ${r.verdict}`);
    t.n += 1;
    t[r.verdict] += 1;
  }
  const keys = [...ORDER.filter((k) => per[k]), ...Object.keys(per).filter((k) => !ORDER.includes(k))];
  write("tracker_bewertung.json", keys.map((k) => ({ key: k, name: names[k] ?? k, ...per[k] })));
}

// 4. agreement between labelers (port of compare() in labeler/src/lib/compare.ts, aggregates only)
{
  const OWNER = "florian";
  const display = (who) => {
    if (who === OWNER) return "Florian";
    const m = /labeler\s*(\d)/i.exec(who);
    if (m) return `Labeler ${m[1]}`;
    throw new Error("unbekannter Name in labels/votes (erlaubt: florian, labelerN)");
  };
  const mine = {};
  for (const split of ["train", "val"]) mine[split] = new Map(jsonl("labels", `${split}.jsonl`).map((r) => [r.id, r.label]));

  const friends = new Set();
  const theirs = new Map(); // "split|id" -> Map(who -> {label, at})
  const practice = new Map(); // id -> {who: label}
  const votesDir = need("labels", "votes");
  for (const file of readdirSync(votesDir).filter((f) => f.endsWith(".jsonl")).sort()) {
    for (const r of jsonl("labels", "votes", file)) {
      const who = String(r.annotator ?? "").trim().toLowerCase() || file.replace(/\.jsonl$/, "").toLowerCase();
      if (who === OWNER) continue;
      friends.add(who);
      if (r.practice) {
        const p = practice.get(r.id) ?? practice.set(r.id, {}).get(r.id);
        p[who] = r.label;
        continue;
      }
      const key = `${r.split}|${r.id}`;
      const by = theirs.get(key) ?? theirs.set(key, new Map()).get(key);
      const old = by.get(who);
      if (!old || old.at < r.labeled_at) by.set(who, { label: r.label, at: r.labeled_at });
    }
  }

  const people = [OWNER, ...[...friends].sort()];
  const pairs = {};
  for (const a of people) {
    pairs[a] = {};
    for (const b of people) pairs[a][b] = [0, 0];
  }
  const confusion = Object.fromEntries(CLASSES.map((c) => [c, Object.fromEntries(CLASSES.map((d) => [d, 0]))]));
  for (const split of ["train", "val"]) {
    const ids = new Set([...mine[split].keys(), ...[...theirs.keys()].filter((k) => k.startsWith(`${split}|`)).map((k) => k.slice(split.length + 1))]);
    for (const id of ids) {
      const votes = {};
      if (mine[split].has(id)) votes[OWNER] = mine[split].get(id);
      for (const [who, v] of theirs.get(`${split}|${id}`) ?? []) votes[who] = v.label;
      const who = Object.keys(votes);
      for (const a of who) for (const b of who) {
        if (a === b) continue;
        pairs[a][b][0] += +(votes[a] === votes[b]);
        pairs[a][b][1] += 1;
      }
      if (votes[OWNER]) for (const b of who) if (b !== OWNER) confusion[votes[OWNER]][votes[b]] += 1;
    }
  }
  const answers = json("labels", "practice.json").items.map((i) => ({ id: i.id, answer: i.answer }));
  const scores = people.slice(1).map((who) => {
    const done = answers.filter((a) => practice.get(a.id)?.[who]);
    return { who: display(who), practice: [done.filter((a) => practice.get(a.id)[who] === a.answer).length, done.length] };
  });
  const names = people.map(display);
  const outPairs = {};
  people.forEach((a, i) => {
    outPairs[names[i]] = {};
    people.forEach((b, j) => (outPairs[names[i]][names[j]] = pairs[a][b]));
  });
  write("label_agreement.json", { people: names, pairs: outPairs, confusion, scores });
}

// 5. class counts per split and 6. tracks for the viewer (class + coordinates only)
{
  const counts = {};
  const tracks = [];
  const MAXPTS = 48;
  for (const split of SPLITS) {
    counts[split] = Object.fromEntries(CLASSES.map((c) => [c, 0]));
    for (const r of jsonl("labels", `final_${split}.jsonl`)) {
      if (!CLASSES.includes(r.label)) throw new Error(`unbekannte Klasse: ${r.label}`);
      counts[split][r.label] += 1;
      const n = r.xy.length;
      const idx = n <= MAXPTS ? [...r.xy.keys()] : Array.from({ length: MAXPTS }, (_, k) => Math.round((k * (n - 1)) / (MAXPTS - 1)));
      // full-resolution frame pixels: x / scale, (y + top) / scale
      const p = idx.flatMap((i) => [r.xy[i][0] / r.scale, (r.xy[i][1] + r.top) / r.scale].map((v) => Math.round(v * 10) / 10));
      tracks.push({ id: r.id, s: split, c: r.label, p });
    }
  }
  write("class_counts.json", counts);
  write("tracks.json", tracks);
}

// self check: nothing that must not be published
const FORBIDDEN = [/annotator/, /"note"/, /\/home\//, /\.mp4/, /\.jpe?g/, /\.png/, /\banni\b/i, /\bviktoria\b/i];
let bad = 0;
let total = 0;
for (const f of readdirSync(OUT).filter((f) => f.endsWith(".json"))) {
  const t = readFileSync(resolve(OUT, f), "utf8");
  sizes[f] = t.length;
  total += t.length;
  for (const re of FORBIDDEN) {
    const m = re.exec(t);
    if (m) {
      bad += 1;
      console.error(`VERBOTEN in ${f}: ${re} bei ${m.index}: ...${t.slice(Math.max(0, m.index - 30), m.index + 30)}...`);
    }
  }
}
for (const [f, n] of Object.entries(sizes)) console.log(`${f}: ${(n / 1024).toFixed(1)} KB`);
console.log(`gesamt: ${(total / 1024).toFixed(1)} KB`);
if (bad) {
  console.error(`${bad} Treffer, Abbruch`);
  process.exit(1);
}
console.log("Selbstcheck ok");
