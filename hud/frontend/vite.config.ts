import { defineConfig } from "vite";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: ".",
  base: "/",
  build: {
    outDir: resolve(rootDir, "../../src/questline/hud/static"),
    emptyOutDir: true,
    assetsDir: "assets",
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8741",
      "/live": { target: "ws://127.0.0.1:8741", ws: true },
    },
  },
});
