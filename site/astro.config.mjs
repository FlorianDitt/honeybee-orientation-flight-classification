import { defineConfig } from "astro/config";

// Static results site for GitHub Pages (https://florianditt.github.io/honeybee-orientation-flight-classification/).
export default defineConfig({
  output: "static",
  site: "https://florianditt.github.io",
  base: process.env.SITE_BASE ?? "/honeybee-orientation-flight-classification",
  trailingSlash: "ignore",
  // IPv4 on purpose: "localhost" binds only to [::1], which SSH/JetBrains port forwarding (127.0.0.1) cannot reach
  server: { host: "127.0.0.1", port: 4321 },
  devToolbar: { enabled: false },
});
