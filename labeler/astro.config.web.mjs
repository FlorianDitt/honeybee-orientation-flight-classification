import { defineConfig } from "astro/config";

// Static build for GitHub Pages: friends label in the browser, labels stay in localStorage and are
// exported as a file. Clips and data come from `beeflight-clips` (public-web/, not versioned).
export default defineConfig({
  srcDir: "./web",
  publicDir: "./public-web",
  outDir: "./dist-web",
  output: "static",
  site: "https://florianditt.github.io",
  base: process.env.SITE_BASE ?? "/BeeHive",
  server: { host: "127.0.0.1", port: 4322 },
  devToolbar: { enabled: false },
});
