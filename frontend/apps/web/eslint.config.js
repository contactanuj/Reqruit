import { nextJsConfig } from "@repo/eslint-config/next-js";

/** @type {import("eslint").Linter.Config[]} */
export default [
  ...nextJsConfig,
  {
    files: ["src/shared/layouts/**/*.tsx", "src/app/**/*.tsx"],
    rules: {
      "no-restricted-syntax": [
        "warn",
        {
          selector: "Literal[value=/\\b(ml|mr|pl|pr)-/]",
          message:
            "Use logical CSS properties (ms-/me-/ps-/pe-) instead of directional (ml-/mr-/pl-/pr-) for RTL support.",
        },
      ],
    },
  },
];
