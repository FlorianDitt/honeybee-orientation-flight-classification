import { defineConfig } from "astro/config";
import node from "@astrojs/node";

// Local-only tool: reads videos and queues from the repo, writes labels/*.jsonl.
export default defineConfig({
  output: "server",
  adapter: node({ mode: "standalone" }),
  server: { host: "127.0.0.1", port: 4321 },
  devToolbar: { enabled: false },
});
