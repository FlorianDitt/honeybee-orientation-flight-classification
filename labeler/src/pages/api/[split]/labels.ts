import type { APIRoute } from "astro";
import { CLASSES, FLAGS, isSplit, readLabels, readQueue, removeLabel, writeLabel } from "../../../lib/store";

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });

export const GET: APIRoute = ({ params }) => {
  if (!isSplit(params.split)) return json({ error: "unknown split" }, 404);
  return json(Object.fromEntries(readLabels(params.split)));
};

export const POST: APIRoute = async ({ params, request }) => {
  const split = params.split;
  if (!isSplit(split)) return json({ error: "unknown split" }, 404);
  const body = await request.json();
  const item = readQueue(split)?.find((i) => i.id === body.id);
  if (!item) return json({ error: "track not in queue" }, 404);
  if (!CLASSES.includes(body.label)) return json({ error: "unknown class" }, 400);
  const flags = (Array.isArray(body.flags) ? body.flags : []).filter((f: string) => FLAGS.includes(f as never));
  const note = typeof body.note === "string" ? body.note.slice(0, 500) : "";
  const rec = writeLabel(split, item, { label: body.label, flags, note });
  return json({ ok: true, labeled_at: rec.labeled_at });
};

export const DELETE: APIRoute = async ({ params, request }) => {
  if (!isSplit(params.split)) return json({ error: "unknown split" }, 404);
  const { id } = await request.json();
  removeLabel(params.split, String(id));
  return json({ ok: true });
};
