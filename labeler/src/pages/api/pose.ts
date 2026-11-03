import type { APIRoute } from "astro";
import { POSE_FLAGS, readPoseQueue, removePose, savePose } from "../../lib/pose";

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
const point = (p: unknown) =>
  Array.isArray(p) && p.length === 2 && p.every((v) => typeof v === "number" && Number.isFinite(v))
    ? ([p[0], p[1]] as [number, number]) : null;

export const POST: APIRoute = async ({ request }) => {
  const { id, head, tail, flags } = await request.json();
  if (!readPoseQueue()?.items.some((i) => i.id === id)) return json({ error: "crop not in the sample" }, 404);
  const f = (Array.isArray(flags) ? flags : []).filter((x: string) => (POSE_FLAGS as readonly string[]).includes(x));
  const h = point(head), t = point(tail);
  if (!f.includes("unklar") && (!h || !t)) return json({ error: "head and tail needed (or flag unklar)" }, 400);
  savePose({ id, head: f.includes("unklar") ? null : h, tail: f.includes("unklar") ? null : t, flags: f });
  return json({ ok: true });
};

export const DELETE: APIRoute = async ({ request }) => {
  const { id } = await request.json();
  removePose(String(id));
  return json({ ok: true });
};
