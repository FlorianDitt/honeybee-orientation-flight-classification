// Streams a dataset video with HTTP range support, so the browser can seek inside 100 MB files.
import type { APIRoute } from "astro";
import { createReadStream, existsSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { Readable } from "node:stream";
import { VIDEO_DIR } from "../../lib/store";

export const GET: APIRoute = ({ params, request }) => {
  const seq = params.seq ?? "";
  if (!/^rec\d{4}_seq\d{3}$/.test(seq)) return new Response("bad sequence id", { status: 400 });
  const path = resolve(VIDEO_DIR, `${seq}.mp4`);
  if (!existsSync(path)) return new Response(`video ${seq}.mp4 not downloaded`, { status: 404 });

  const size = statSync(path).size;
  const range = /bytes=(\d*)-(\d*)/.exec(request.headers.get("range") ?? "");
  const headers: Record<string, string> = { "Content-Type": "video/mp4", "Accept-Ranges": "bytes" };
  if (!range) {
    headers["Content-Length"] = String(size);
    return new Response(Readable.toWeb(createReadStream(path)) as ReadableStream, { headers });
  }
  const start = range[1] ? Number(range[1]) : Math.max(0, size - Number(range[2]));
  const end = range[1] && range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
  if (start >= size || start > end) {
    return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
  }
  headers["Content-Range"] = `bytes ${start}-${end}/${size}`;
  headers["Content-Length"] = String(end - start + 1);
  const stream = createReadStream(path, { start, end });
  return new Response(Readable.toWeb(stream) as ReadableStream, { status: 206, headers });
};
