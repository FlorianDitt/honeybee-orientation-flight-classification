// Browser side of both apps: plays one track in a loop, draws it in sync and handles labeling.
// The local app streams the full videos, the web app (GitHub Pages) short cropped clips; `Media`
// describes how a video maps to the original 1080x1920 frame, everything else is shared.

export const FPS = 60000 / 1001;
export const W = 1080, H = 1920;
export const CLASSES = ["orientierung", "sammelabflug", "anflug", "artefakt"] as const;
export const FLAGS = ["fragment", "unsicher"] as const;
const COLORS: Record<string, string> = { orientierung: "#e0662a", sammelabflug: "#3d93c9", anflug: "#3f9d6b", artefakt: "#8a8f98" };
const PAD_FRAMES = 20;

type Pt = [number, number];
type Box = { x: number; y: number; s: number };
type Rect = { x: number; y: number; w: number; h: number };

export interface Track { id: string; t0: number; t1: number; t: number[]; pts: Pt[] }  // pts in full-res pixels
export interface Media {
  src: string;
  offset: number;     // original frame index of the video's first frame
  last: number;       // last original frame in the video
  region: Rect;       // part of the original frame the video shows
  k: number;          // video pixels per original pixel
  overview?: string;  // still of the full frame; without it the overview draws the video itself
}
export interface Label { label: string; flags: string[]; note: string }
export interface Backend {
  save(track: Track, label: Label): Promise<void>;  // throws with a readable message on failure
  clear(track: Track): Promise<void>;
}
export interface Options {
  tracks: Track[];
  labels: Record<string, Label>;
  media(track: Track): Media;
  backend: Backend;
  /** practice mode: a message shown after saving instead of moving on */
  feedback?(track: Track, label: Label): string | null;
  onDone?(): void;
}

export const fullFrame = (src: string): Media => ({ src, offset: 0, last: 1799, region: { x: 0, y: 0, w: W, h: H }, k: 1 });

/** Square view around the track, clamped into the region the video covers. */
export function fitBox(pts: Pt[], wide: boolean, region: Rect): Box {
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const margin = wide ? 260 : 90;
  const x0 = Math.min(...xs) - margin, x1 = Math.max(...xs) + margin;
  const y0 = Math.min(...ys) - margin, y1 = Math.max(...ys) + margin;
  const s = Math.min(region.w, region.h, Math.max(240, x1 - x0, y1 - y0));
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const clamp = (v: number, lo: number, hi: number) => Math.min(Math.max(lo, v), hi);
  return { s, x: clamp(cx - s / 2, region.x, region.x + region.w - s), y: clamp(cy - s / 2, region.y, region.y + region.h - s) };
}

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

export function startLabeler(opt: Options) {
  const { tracks, labels } = opt;
  const video = $<HTMLVideoElement>("video");
  const viewport = $<HTMLDivElement>("viewport");
  const zoom = $<HTMLCanvasElement>("zoom").getContext("2d")!;
  const over = $<HTMLCanvasElement>("overview").getContext("2d")!;
  const note = $<HTMLInputElement>("note");
  const flagEls = { fragment: $<HTMLInputElement>("flag-fragment"), unsicher: $<HTMLInputElement>("flag-unsicher") };
  const still = new Image();

  let idx = Math.max(0, tracks.findIndex((t) => !labels[t.id]));
  let rate = 0.25;
  let wide = false;
  let media: Media = opt.media(tracks[idx]);
  let box: Box = { x: 0, y: 0, s: 1 };
  let seg = { start: 0, end: 0 };
  let frameCb = 0;
  let busy = false;

  const frameTime = (f: number) => (f - media.offset + 0.5) / FPS;
  const toFrame = (seconds: number) => media.offset + Math.round(seconds * FPS);

  function setup(i: number) {
    idx = (i + tracks.length) % tracks.length;
    const tr = tracks[idx];
    const next = opt.media(tr);
    const srcChanged = next.src !== media.src || !video.src;
    media = next;
    box = fitBox(tr.pts, wide, media.region);
    place();
    seg = { start: Math.max(media.offset, tr.t0 - PAD_FRAMES), end: Math.min(media.last, tr.t1 + PAD_FRAMES) };
    if (srcChanged) {
      showStatus("Video lädt …");
      zoom.clearRect(0, 0, zoom.canvas.width, zoom.canvas.height);
      over.fillStyle = "#111";
      over.fillRect(0, 0, over.canvas.width, over.canvas.height);
      video.style.visibility = "hidden";  // no stale frame of the previous video under the new overlay
      video.src = media.src;
      if (media.overview) still.src = media.overview;
    }
    video.currentTime = frameTime(seg.start);
    video.playbackRate = rate;
    play();
    const l = labels[tr.id];
    flagEls.fragment.checked = !!l?.flags.includes("fragment");
    flagEls.unsicher.checked = !!l?.flags.includes("unsicher");
    note.value = l?.note ?? "";
    renderUi();
  }

  /** Scale and shift the video so that the view box fills the viewport. */
  function place() {
    if (!video.videoWidth) return;
    const { region: r, k: vk } = media;
    const sc = viewport.clientWidth / (box.s * vk);
    video.style.width = `${video.videoWidth}px`;
    video.style.height = `${video.videoHeight}px`;
    video.style.transform = `scale(${sc}) translate(${-(box.x - r.x) * vk}px, ${-(box.y - r.y) * vk}px)`;
  }

  // autoplay can be blocked (iOS low power mode): then one tap starts it
  // (an AbortError only means a new src interrupted the old play() call)
  const play = () => video.play().catch((e: DOMException) => {
    if (e.name === "NotAllowedError") showStatus("Zum Abspielen auf das Video tippen", "tap");
  });
  viewport.addEventListener("click", () => {
    if ($("status").dataset.kind === "tap") { hideStatus(); video.play(); }
  });

  function currentIndex(frame: number) {
    const t = tracks[idx].t;
    let k = -1;
    while (k + 1 < t.length && t[k + 1] <= frame) k++;
    return k;
  }

  function path(ctx: CanvasRenderingContext2D, pts: Pt[], to: number, map: (p: Pt) => Pt) {
    ctx.beginPath();
    for (let k = 0; k <= to; k++) {
      const [x, y] = map(pts[k]);
      k === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  function draw(frame: number) {
    if (video.readyState < 2) return;  // no decoded frame of the current video yet
    const tr = tracks[idx], pts = tr.pts;
    const k = currentIndex(frame);
    const color = COLORS[labels[tr.id]?.label] ?? "#d99a1e";
    const zs = zoom.canvas.width / box.s;
    const zmap = (p: Pt): Pt => [(p[0] - box.x) * zs, (p[1] - box.y) * zs];

    zoom.clearRect(0, 0, zoom.canvas.width, zoom.canvas.height);
    zoom.lineJoin = zoom.lineCap = "round";
    zoom.setLineDash([6, 6]);
    zoom.strokeStyle = "rgba(255,255,255,.55)";
    zoom.lineWidth = 1.5;
    path(zoom, pts, pts.length - 1, zmap);
    zoom.setLineDash([]);
    if (k >= 1) {
      zoom.strokeStyle = color;
      zoom.lineWidth = 3;
      path(zoom, pts, k, zmap);
    }
    if (k >= 0 && frame <= tr.t1) {
      const [x, y] = zmap(pts[k]);
      zoom.strokeStyle = "#fff";
      zoom.lineWidth = 2;
      zoom.beginPath();
      zoom.arc(x, y, 22, 0, Math.PI * 2);
      zoom.stroke();
    }
    const [sx, sy] = zmap(pts[0]);
    zoom.fillStyle = "#fff";
    zoom.fillRect(sx - 4, sy - 4, 8, 8);

    const os = over.canvas.width / W;
    if (!media.overview) over.drawImage(video, 0, 0, over.canvas.width, over.canvas.height);
    else if (still.complete && still.naturalWidth) over.drawImage(still, 0, 0, over.canvas.width, over.canvas.height);
    over.strokeStyle = "#fff";
    over.lineWidth = 1;
    over.strokeRect(box.x * os, box.y * os, box.s * os, box.s * os);
    over.strokeStyle = color;
    over.lineWidth = 1.5;
    path(over, pts, pts.length - 1, (p) => [p[0] * os, p[1] * os]);

    $("frame").textContent = `Frame ${frame} · Bahn ${tr.t0}–${tr.t1}`;
    $("phase").textContent = frame < tr.t0 ? "vor der Bahn" : frame > tr.t1 ? "nach der Bahn" : "";
  }

  function onFrame(_: number, meta: VideoFrameCallbackMetadata) {
    const frame = toFrame(meta.mediaTime);
    draw(Math.min(frame, media.last));
    if (frame >= seg.end) video.currentTime = frameTime(seg.start);
    frameCb = video.requestVideoFrameCallback(onFrame);
  }
  if (typeof video.requestVideoFrameCallback === "function") {
    frameCb = video.requestVideoFrameCallback(onFrame);
    // a new src can drop pending callbacks in some browsers: re-arm exactly one
    video.addEventListener("loadeddata", () => {
      video.cancelVideoFrameCallback(frameCb);
      frameCb = video.requestVideoFrameCallback(onFrame);
    });
  } else {
    // fallback: less exact, but keeps the overlay roughly in sync
    const tick = () => {
      if (video.readyState >= 2) {
        const frame = media.offset + Math.floor(video.currentTime * FPS);
        draw(frame);
        if (frame >= seg.end) video.currentTime = frameTime(seg.start);
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  video.addEventListener("loadedmetadata", place);
  video.addEventListener("loadeddata", () => { video.style.visibility = ""; });
  new ResizeObserver(place).observe(viewport);
  video.addEventListener("seeked", () => draw(media.offset + Math.floor(video.currentTime * FPS)));
  video.addEventListener("canplay", () => { if ($("status").dataset.kind === "load") hideStatus(); });
  video.addEventListener("error", () => showStatus(`Video zu ${tracks[idx].id} fehlt oder lässt sich nicht laden.`, "error"));
  still.addEventListener("load", () => draw(media.offset + Math.floor(video.currentTime * FPS)));

  function renderUi() {
    const tr = tracks[idx];
    const done = tracks.filter((t) => labels[t.id]).length;
    $("pos").textContent = `Bahn ${idx + 1} / ${tracks.length}`;
    $("done").textContent = String(done);
    $("progress-bar").style.width = `${(100 * done) / tracks.length}%`;
    for (const b of document.querySelectorAll<HTMLButtonElement>(".cls")) {
      b.classList.toggle("active", labels[tr.id]?.label === b.dataset.class);
    }
    for (const b of document.querySelectorAll<HTMLButtonElement>("[data-rate]")) {
      b.classList.toggle("active", Number(b.dataset.rate) === rate);
    }
  }

  function showStatus(msg: string, kind = msg.endsWith("…") ? "load" : "info") {
    const s = $("status");
    s.textContent = msg;
    s.dataset.kind = kind;
    s.hidden = false;
  }
  function hideStatus() { $("status").hidden = true; }

  async function save(cls: string) {
    if (busy) return;
    const tr = tracks[idx];
    const label = { label: cls, flags: FLAGS.filter((f) => flagEls[f].checked), note: note.value };
    busy = true;
    try {
      await opt.backend.save(tr, label);
    } catch (e) {
      showStatus(`Speichern fehlgeschlagen: ${(e as Error).message}`, "error");
      return;
    } finally {
      busy = false;
    }
    labels[tr.id] = label;
    const msg = opt.feedback?.(tr, label);
    if (msg) { renderUi(); showStatus(msg, "feedback"); return; }
    nextOpen();
  }

  async function clear() {
    const tr = tracks[idx];
    await opt.backend.clear(tr);
    delete labels[tr.id];
    setup(idx);
  }

  function go(i: number) { hideStatus(); setup(i); }

  function nextOpen() {
    hideStatus();
    for (let k = 1; k <= tracks.length; k++) {
      const j = (idx + k) % tracks.length;
      if (!labels[tracks[j].id]) return setup(j);
    }
    renderUi();
    if (opt.onDone) opt.onDone();
    else showStatus("Alle Bahnen dieser Warteschlange sind gelabelt.");
  }

  const togglePlay = () => (video.paused ? play() : video.pause());
  const setRate = (r: number) => { rate = r; video.playbackRate = r; renderUi(); };
  const restart = () => { video.currentTime = frameTime(seg.start); play(); };
  const toggleWide = () => { wide = !wide; box = fitBox(tracks[idx].pts, wide, media.region); place(); };

  for (const b of document.querySelectorAll<HTMLButtonElement>(".cls")) b.onclick = () => save(b.dataset.class!);
  for (const b of document.querySelectorAll<HTMLButtonElement>("[data-rate]")) b.onclick = () => setRate(Number(b.dataset.rate));
  $("play").onclick = togglePlay;
  $("restart").onclick = restart;
  $("zoom-toggle").onclick = toggleWide;
  $("prev").onclick = () => go(idx - 1);
  $("next").onclick = () => go(idx + 1);
  $("next-open").onclick = nextOpen;
  $("clear").onclick = clear;

  document.addEventListener("keydown", (e) => {
    if (e.target === note) {
      if (e.key === "Escape" || e.key === "Enter") note.blur();
      return;
    }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const n = Number(e.key);
    if (n >= 1 && n <= CLASSES.length) return void save(CLASSES[n - 1]);
    switch (e.key.toLowerCase()) {
      case " ": e.preventDefault(); togglePlay(); break;
      case "r": restart(); break;
      case "s": setRate(rate === 0.25 ? 0.5 : rate === 0.5 ? 1 : 0.25); break;
      case "z": toggleWide(); break;
      case "f": flagEls.fragment.checked = !flagEls.fragment.checked; break;
      case "u": flagEls.unsicher.checked = !flagEls.unsicher.checked; break;
      case "n": nextOpen(); break;
      case "arrowleft": go(idx - 1); break;
      case "arrowright": go(idx + 1); break;
    }
  });

  setup(idx);
}
