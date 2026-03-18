import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "html"],
      thresholds: {
        statements: 80,
        branches: 75,
      },
      // Only enforce coverage on packages/ui (NFR-D3)
      include: ["../../packages/ui/src/**/*.{ts,tsx}"],
      exclude: ["**/*.stories.*", "**/*.d.ts"],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // Resolve workspace package directly to source during tests (pre-install)
      "@reqruit/api-client": path.resolve(__dirname, "../../packages/api-client/src/index.ts"),
      // Resolve @repo/ui to packages/ui source
      "@repo/ui": path.resolve(__dirname, "../../packages/ui/src"),
      // Resolve packages/ui's transitive deps from apps/web node_modules
      "lucide-react": path.resolve(__dirname, "node_modules/lucide-react"),
      "sonner": path.resolve(__dirname, "node_modules/sonner"),
    },
  },
});
