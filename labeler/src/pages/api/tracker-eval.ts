import type { APIRoute } from "astro";
import { VERDICTS, evalSample, removeVerdict, saveVerdict } from "../../lib/evaluation";

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });

export const POST: APIRoute = async ({ request }) => {
  const { id, verdict } = await request.json();
  const item = evalSample().items.find((i) => i.id === id);
  if (!item) return json({ error: "track not in the sample" }, 404);
  if (!VERDICTS.some((v) => v.key === verdict)) return json({ error: "unknown verdict" }, 400);
  saveVerdict(item, verdict);
  return json({ ok: true });
};

export const DELETE: APIRoute = async ({ request }) => {
  const { id } = await request.json();
  removeVerdict(String(id));
  return json({ ok: true });
};
