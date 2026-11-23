// Serves one crop strip of the bee check from outputs/biene/crops/.
import type { APIRoute } from "astro";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { STRIPS } from "../../lib/biene";

export const GET: APIRoute = ({ params }) => {
  const name = params.img ?? "";
  if (!/^rec\d{4}_seq\d{3}_\d+\.png$/.test(name)) return new Response("bad strip name", { status: 400 });
  const path = resolve(STRIPS, name);
  if (!existsSync(path)) return new Response("strip missing: run python -m beeflight.biene sample", { status: 404 });
  return new Response(readFileSync(path), { headers: { "Content-Type": "image/png", "Cache-Control": "max-age=3600" } });
};
