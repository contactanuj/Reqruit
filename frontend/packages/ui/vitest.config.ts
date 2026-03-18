import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  resolve: {
    alias: {
      // Resolve workspace package directly to source during tests (pre-install)
      "@repo/types": path.resolve(__dirname, "../types/src/index.ts"),
      // Resolve lucide-react from apps/web where it is installed
      "lucide-react": path.resolve(__dirname, "../../apps/web/node_modules/lucide-react"),
      // Resolve sonner from apps/web where it is installed
      "sonner": path.resolve(__dirname, "../../apps/web/node_modules/sonner"),
      // Resolve @testing-library/user-event from apps/web where it is installed
      "@testing-library/user-event": path.resolve(__dirname, "../../apps/web/node_modules/@testing-library/user-event"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "html"],
      thresholds: {
        statements: 80,
        branches: 75,
      },
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["**/*.stories.*", "**/*.d.ts"],
    },
  },
});
