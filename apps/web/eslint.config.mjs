import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = [
  ...nextVitals,
  ...nextTs,
  {
    name: "global-ignores",
    ignores: [
      ".next/**",
      "out/**",
      "build/**",
      "coverage/**",
      "next-env.d.ts",
    ],
  },
  {
    rules: {
      // Disable the pages directory check for monorepo setup
      "@next/next/no-html-link-for-pages": "off",
      // Allow unused vars with _ prefix (intentionally unused parameters)
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      // Allow <img> for dynamic external URLs where Next.js Image optimization isn't applicable
      "@next/next/no-img-element": "off",
      // Disabled 2026-08-15 after eslint-plugin-react-hooks bump pulled in
      // these new opt-in rules. 15 admin/chat/agent pages violate them
      // (loadXxx() in useEffect, StatusBadge declared inside parent, etc.).
      // Re-enable per-page as code is refactored to use a data-fetching
      // library (SWR / React Query) instead of the manual fetch + setState
      // pattern. Tracked in CHANGELOG `[Unreleased]` 2026-08-15.
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/static-components": "off",
      "react-hooks/immutability": "off",
      "react-hooks/preserve-manual-memoization": "off",
    },
  },
];

export default eslintConfig;
