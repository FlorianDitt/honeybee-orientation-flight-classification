// Start and watch `beeflight-classify` from the local labeler. The training runs as its own process group, so it
// survives a restart of the dev server. One folder per experiment in outputs/runs/, started via run.json.
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, openSync, readFileSync, readdirSync, statSync, writeFileSync, closeSync } from "node:fs";
import { resolve } from "node:path";
import { LABELS_DIR, ROOT } from "./store";

const RUNS = resolve(ROOT, "outputs", "runs");
const PRETRAINED = resolve(RUNS, "pretrained");
export const MODELS = ["rule_fixed", "rule", "logreg", "gbm", "gru", "gru_scratch", "gru_shape"];
export const PRESETS = {
  full: { name: "Hauptlauf", seeds: 5, sizes: [25, 50, 100, 200, 0], models: MODELS },
  quick: { name: "Kurztest", seeds: 1, sizes: [25], models: MODELS },
  // for checking the page: no neural network, done in about a minute
  light: { name: "Nur Baselines", seeds: 1, sizes: [25], models: ["rule_fixed", "rule", "logreg", "gbm"] },
} as const;
export type Preset = keyof typeof PRESETS;
const PRE_EPOCHS = 30;

interface RunFile { pid: number; started: string; preset: Preset; labels: "own" | "final"; total: number }
interface Result { model: string; size: number; seed: number; n_train: number; labels_hash?: string;
  val: { macro_f1: number; recall_orientierung: number; accuracy: number } }

const validName = (g: string) => /^[\w.-]+$/.test(g) && !g.startsWith("_") && g !== "pretrained" && existsSync(resolve(RUNS, g));
const groups = () => existsSync(RUNS)
  ? readdirSync(RUNS).filter((g) => validName(g) && statSync(resolve(RUNS, g)).isDirectory())
      .sort((a, b) => statSync(resolve(RUNS, b)).mtimeMs - statSync(resolve(RUNS, a)).mtimeMs)
  : [];

function runFile(group: string): RunFile | null {
  const p = resolve(RUNS, group, "run.json");
  return existsSync(p) ? JSON.parse(readFileSync(p, "utf8")) : null;
}

/** Is this pid still our training? A pid alone is not enough: it may be reused after a reboot. */
function alive(pid: number) {
  try {
    return readFileSync(`/proc/${pid}/cmdline`, "utf8").includes("beeflight-classify");
  } catch {
    return false;
  }
}

// right after the start the new process may not show its command line yet
const justStarted = (r: RunFile) => Date.now() - Date.parse(r.started) < 5000;
export const running = () => groups().find((g) => { const r = runFile(g); return r && (alive(r.pid) || justStarted(r)); }) ?? null;

export function start(preset: Preset, labels: "own" | "final", resume?: string) {
  const busy = running();
  if (busy) throw new Error(`Es läuft schon ein Training (${busy}).`);
  if (!PRESETS[preset]) throw new Error("Unbekannte Auswahl");
  if (labels === "final" && !existsSync(resolve(LABELS_DIR, "final_train.jsonl"))) throw new Error("Noch keine Mehrheitslabels: erst beeflight-vote");
  let group = resume;
  if (group) {
    const old = group && validName(group) ? runFile(group) : null;
    if (!old) throw new Error("Dieser Lauf lässt sich nicht fortsetzen.");
    preset = old.preset;
    labels = old.labels;
  } else {
    group = new Date().toLocaleString("sv-SE").replace(" ", "_").replace(/:/g, "").slice(0, 15) + `_${preset}`;
  }
  const p = PRESETS[preset];
  const dir = resolve(RUNS, group);
  mkdirSync(dir, { recursive: true });
  const out = openSync(resolve(dir, "stdout.log"), "a");
  const args = ["-n", "10", "uv", "run", "beeflight-classify", "--group", group, "--labels", labels,
    "--seeds", String(p.seeds), "--sizes", ...p.sizes.map(String), "--models", ...p.models];
  const child = spawn("nice", args, { cwd: ROOT, detached: true, stdio: ["ignore", out, out] });
  closeSync(out);
  child.unref();
  if (!child.pid) throw new Error("Training ließ sich nicht starten.");
  const total = (p.models.includes("rule_fixed") ? 1 : 0) + p.seeds * p.sizes.length * p.models.filter((m) => m !== "rule_fixed").length;
  writeFileSync(resolve(dir, "run.json"), JSON.stringify({ pid: child.pid, started: new Date().toISOString(), preset, labels, total }));
  return group;
}

export function stop() {
  const group = running();
  if (!group) throw new Error("Es läuft kein Training.");
  process.kill(-runFile(group)!.pid, "SIGTERM");
  return group;
}

function results(group: string): Result[] {
  const dir = resolve(RUNS, group);
  return readdirSync(dir).filter((f) => /_n\d+_s\d+\.json$/.test(f)).flatMap((f) => {
    try {
      return [JSON.parse(readFileSync(resolve(dir, f), "utf8"))];
    } catch {
      return []; // being written right now
    }
  });
}

const mean = (v: number[]) => v.reduce((a, b) => a + b, 0) / v.length;

/** Learning curve table: per model and number of labels the mean over the seeds done so far. */
function table(rs: Result[]) {
  const sizes = [...new Set(rs.filter((r) => r.model !== "rule_fixed").map((r) => r.n_train))].sort((a, b) => a - b);
  const models = MODELS.filter((m) => rs.some((r) => r.model === m));
  const rows = models.map((model) => ({
    model,
    cells: Object.fromEntries((model === "rule_fixed" ? [] : sizes).map((n) => {
      const hit = rs.filter((r) => r.model === model && r.n_train === n);
      return [n, hit.length ? { f1: mean(hit.map((r) => r.val.macro_f1)), recall: mean(hit.map((r) => r.val.recall_orientierung)), seeds: hit.length } : null];
    })),
    fixed: model === "rule_fixed" ? rs.find((r) => r.model === model)?.val ?? null : null,
  }));
  return { sizes, rows };
}

function tail(path: string, lines = 8) {
  return existsSync(path) ? readFileSync(path, "utf8").trim().split("\n").slice(-lines).join("\n") : "";
}

function memAvailableGb() {
  const m = readFileSync("/proc/meminfo", "utf8").match(/MemAvailable:\s+(\d+)/);
  return m ? Number(m[1]) / 1024 ** 2 : null;
}

/** State of one experiment plus what the start form needs. */
export function status(wanted?: string) {
  const all = groups();
  const active = running();
  const group = wanted && all.includes(wanted) ? wanted : active ?? all[0] ?? null;
  const base = {
    groups: all, active, memGb: memAvailableGb(),
    hasFinal: existsSync(resolve(LABELS_DIR, "final_train.jsonl")),
    pretrained: existsSync(PRETRAINED) ? readdirSync(PRETRAINED).filter((f) => f.endsWith(`_e${PRE_EPOCHS}.pt`)).length : 0,
    presets: Object.fromEntries(Object.entries(PRESETS).map(([k, p]) => [k, p.name])),
  };
  if (!group) return { ...base, group: null };
  const dir = resolve(RUNS, group);
  const run = runFile(group);
  const rs = results(group);
  const summary = existsSync(resolve(dir, "summary.md")) ? readFileSync(resolve(dir, "summary.md"), "utf8") : null;
  const state = active === group ? "running" : summary ? "done" : "aborted";
  return { ...base, group, state, run, done: rs.length, total: run?.total ?? null, table: table(rs), summary,
    canResume: state === "aborted" && !!run && !active,
    log: tail(resolve(dir, existsSync(resolve(dir, "stdout.log")) ? "stdout.log" : "log.txt")) };
}
