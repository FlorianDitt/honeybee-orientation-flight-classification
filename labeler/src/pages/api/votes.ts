import type { APIRoute } from "astro";
import { deleteVoteFile, readVoteFiles, saveVoteFile } from "../../lib/store";

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });

export const GET: APIRoute = () => json(readVoteFiles());

/** Body: the raw export, file name in ?name=. */
export const POST: APIRoute = async ({ request, url }) => {
  try {
    return json({ ok: true, ...saveVoteFile(url.searchParams.get("name") ?? "", await request.text()) });
  } catch (e) {
    return json({ error: (e as Error).message }, 400);
  }
};

/** Delete the export named in ?name=. */
export const DELETE: APIRoute = ({ url }) => {
  try {
    return json({ ok: true, ...deleteVoteFile(url.searchParams.get("name") ?? "") });
  } catch (e) {
    return json({ error: (e as Error).message }, 400);
  }
};
