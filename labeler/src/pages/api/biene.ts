import type { APIRoute } from "astro";
import { BEE_ANSWERS, type BeeAnswer, readBeeQueue, removeBee, saveBee } from "../../lib/biene";

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });

export const POST: APIRoute = async ({ request }) => {
  const { id, answer } = await request.json();
  if (!readBeeQueue()?.items.some((i) => i.id === id)) return json({ error: "track not in the queue" }, 404);
  if (!(BEE_ANSWERS as readonly string[]).includes(answer)) return json({ error: "unknown answer" }, 400);
  saveBee(id, answer as BeeAnswer);
  return json({ ok: true });
};

export const DELETE: APIRoute = async ({ request }) => {
  const { id } = await request.json();
  removeBee(String(id));
  return json({ ok: true });
};
