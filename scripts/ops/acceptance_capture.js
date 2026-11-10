/**
 * The design acceptance capture.
 *
 *   node scripts/ops/acceptance_capture.js
 *
 * The acceptance compares the application against the prototype page by page
 * at 1440 and at 390, in light and in dark, and the screenshots live next to
 * the report. This walks every route and writes them out.
 *
 *   SITE_URL   the deployment to capture - the local one by default
 *   OUT_DIR    where the shots land - docs/reviews/design-acceptance-<date> by default
 *
 * The theme is set the way the application sets it: the `theme` key in
 * localStorage and the `dark` class on the document element. Every statement
 * has its own guard, because at document-start the document element is still
 * null and one throw would skip every statement after it.
 */
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE = (process.env.SITE_URL || "http://localhost:3000").replace(/\/+$/, "");
const DAY = new Date().toISOString().slice(0, 10);
const OUT = process.env.OUT_DIR
  ? path.resolve(process.env.OUT_DIR)
  : path.join(__dirname, "..", "..", "docs", "reviews", `design-acceptance-${DAY}`);

/** The route, the prototype page it is compared against, and the file name. */
const ROUTES = [
  { name: "landing", url: "/en", prototype: "Landing.dc.html" },
  { name: "search", url: "/en/search?q=apartment+krakow", prototype: "Search.dc.html" },
  { name: "chat", url: "/en/chat", prototype: "Chat.dc.html" },
  { name: "tools", url: "/en/tools", prototype: "Tools.dc.html" },
  { name: "analytics", url: "/en/analytics", prototype: "Analytics.dc.html" },
  { name: "market-trends", url: "/en/market-trends", prototype: "MarketTrends.dc.html" },
  { name: "city-overview", url: "/en/city-overview", prototype: "CityOverview.dc.html" },
  { name: "valuation", url: "/en/valuation", prototype: "Valuation.dc.html" },
  { name: "cma", url: "/en/cma", prototype: "CMA.dc.html" },
  { name: "knowledge", url: "/en/knowledge", prototype: "Knowledge.dc.html" },
  { name: "showcase", url: "/en/showcase", prototype: "Showcase.dc.html" },
  { name: "agents", url: "/en/agents", prototype: "Agents.dc.html" },
  { name: "favorites", url: "/en/favorites", prototype: "Favorites.dc.html" },
  { name: "saved-searches", url: "/en/saved-searches", prototype: "SavedSearches.dc.html" },
  { name: "documents", url: "/en/documents", prototype: "Documents.dc.html" },
  { name: "leads", url: "/en/leads", prototype: "Leads.dc.html" },
  { name: "usage", url: "/en/usage", prototype: "Usage.dc.html" },
  { name: "agent-analytics", url: "/en/agent-analytics", prototype: "AgentAnalytics.dc.html" },
  { name: "settings", url: "/en/settings", prototype: "Settings.dc.html" },
  { name: "auth-login", url: "/en/auth/login", prototype: "Auth.dc.html" },
  { name: "admin-bulk-jobs", url: "/en/admin/bulk-jobs", prototype: "Admin.dc.html" },
  { name: "admin-connectors", url: "/en/admin/connectors", prototype: "Admin.dc.html" },
  { name: "admin-data-sources", url: "/en/admin/data-sources", prototype: "Admin.dc.html" },
  { name: "admin-monitoring", url: "/en/admin/monitoring", prototype: "Admin.dc.html" },
];

/** The two measures the acceptance is taken at. */
const VIEWPORTS = [
  { name: "1440", width: 1440, height: 900 },
  { name: "390", width: 390, height: 844 },
];

/** The two themes. */
const THEMES = ["light", "dark"];

async function capture(browser, viewport, theme) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    locale: "en-US",
    colorScheme: theme,
  });

  // The theme is set the way the application sets it: the `theme` key in
  // localStorage. The application's own script reads that key and puts the
  // `dark` class on the document element, so setting the key is enough.
  // Every statement has its own guard, because at document-start the document
  // element is still null and one throw would skip every statement after it.
  await context.addInitScript((wanted) => {
    try {
      localStorage.setItem("theme", wanted);
    } catch {}
  }, theme);
  await context.addInitScript(() => {
    try {
      localStorage.setItem("onboarding-tour-dismissed-v1", "1");
    } catch {}
  });

  const page = await context.newPage();
  const failures = [];

  for (const route of ROUTES) {
    const file = path.join(OUT, `${route.name}-${viewport.name}-${theme}.png`);
    try {
      await page.goto(`${BASE}${route.url}`, { waitUntil: "load", timeout: 45000 });
      await page.waitForTimeout(2500);
      await page.screenshot({ path: file, fullPage: false });
      console.log(`  ${route.name} ${viewport.name} ${theme}`);
    } catch (error) {
      failures.push(`${route.name} (${viewport.name} ${theme}): ${error.message}`);
      console.error(`  FAILED ${route.name} ${viewport.name} ${theme}: ${error.message}`);
    }
  }

  await context.close();
  return failures;
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const failures = [];

  for (const theme of THEMES) {
    for (const viewport of VIEWPORTS) {
      console.log(`\n${viewport.name} ${theme}`);
      failures.push(...(await capture(browser, viewport, theme)));
    }
  }

  await browser.close();

  const index = ROUTES.map(
    (route) =>
      `| ${route.name} | ${route.prototype} | \`${route.name}-1440-light.png\` | \`${route.name}-1440-dark.png\` | \`${route.name}-390-light.png\` | \`${route.name}-390-dark.png\` |`
  ).join("\n");
  fs.writeFileSync(
    path.join(OUT, "index.md"),
    `# The captured shots\n\nEvery route, at 1440 and 390, in light and in dark.\n\n| Route | Prototype page | 1440 light | 1440 dark | 390 light | 390 dark |\n|---|---|---|---|---|---|\n${index}\n`
  );

  console.log(`\n${ROUTES.length} routes, ${ROUTES.length * 4} shots, in ${OUT}`);
  if (failures.length) {
    console.log(`\n${failures.length} failed:`);
    for (const failure of failures) console.log(`  ${failure}`);
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
