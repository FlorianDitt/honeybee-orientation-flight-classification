import type { APIRoute } from "astro";
import { PRESETS, type Preset, start, status, stop } from "../../lib/training";

const json = (data: unknown, code = 200) =>
  new Response(JSON.stringify(data), { status: code, headers: { "Content-Type": "application/json" } });

export const GET: APIRoute = ({ url }) => json(status(url.searchParams.get("group") ?? undefined));

/** Body: { action: "start", preset, labels, resume? } or { action: "stop" }. JSON only, so other sites cannot trigger it. */
export const POST: APIRoute = async ({ request }) => {
  if (!request.headers.get("content-type")?.includes("application/json")) return json({ error: "JSON erwartet" }, 415);
  try {
    const b = await request.json();
    if (b.action === "stop") return json({ ok: true, group: stop() });
    if (b.action !== "start") return json({ error: "Unbekannte Aktion" }, 400);
    const preset = (b.preset in PRESETS ? b.preset : "full") as Preset;
    return json({ ok: true, group: start(preset, b.labels === "final" ? "final" : "own", typeof b.resume === "string" ? b.resume : undefined) });
  } catch (e) {
    return json({ error: (e as Error).message }, 400);
  }
};
