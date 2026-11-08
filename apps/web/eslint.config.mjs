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
    // The design tokens have one address: the raw HSL variables in
    // `app/globals.css`, which Tailwind reads through the `@theme inline`
    // aliases. A component writes a utility or `hsl(var(--x))` - never
    // `var(--color-*)`, which is a build-time alias and not a runtime value,
    // and never a hex literal, which no theme can move.
    name: "design-tokens",
    files: ["src/**/*.{ts,tsx}"],
    ignores: [
      // The one place the literals live: the map engines cannot read CSS.
      "src/lib/palette.ts",
      // The Google brand colours, which are a brand and not a theme.
      "src/components/auth/OAuthButtons.tsx",
      // The browser chrome colour, which lives in the metadata.
      "src/app/**/layout.tsx",
    ],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          selector: "Literal[value=/var\\(--color-/]",
          message:
            "Use the Tailwind utility or hsl(var(--token)). The --color-* aliases are a build-time mapping, not a runtime value.",
        },
        {
          selector: "Literal[value=/^#[0-9a-fA-F]{3,8}$/]",
          message:
            "A hex literal cannot follow the theme. Use a token - or lib/palette.ts when the consumer is the map engine.",
        },
        {
          selector: "JSXAttribute[value.value=/^#[0-9a-fA-F]{3,8}$/]",
          message:
            "A hex literal cannot follow the theme. Use a token - or lib/palette.ts when the consumer is the map engine.",
        },
      ],
    },
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
