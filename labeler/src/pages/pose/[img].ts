// Serves one crop of the pose sample from outputs/pose/crops/.
import type { APIRoute } from "astro";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { CROPS } from "../../lib/pose";

export const GET: APIRoute = ({ params }) => {
  const name = params.img ?? "";
  if (!/^rec\d{4}_seq\d{3}_\d+_\d+_[+-]\d+\.png$/.test(name)) return new Response("bad crop name", { status: 400 });
  const path = resolve(CROPS, name);
  if (!existsSync(path)) return new Response("crop missing: run beeflight-pose sample", { status: 404 });
  return new Response(readFileSync(path), { headers: { "Content-Type": "image/png", "Cache-Control": "max-age=3600" } });
};
