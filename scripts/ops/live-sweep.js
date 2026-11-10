/**
 * The live sweep of the deployed demo.
 *
 *   node scripts/ops/live-sweep.js
 *
 * The repository's end-to-end suite mocks the API, so nothing proves that the
 * DEPLOYED demo answers for every route with the real backend, the real model
 * and the real catalogue. This walks every route of the deployment with a
 * browser and prints one line per route: the route, the page's HTTP status,
 * the API calls it made and the console errors.
 *
 * It never writes to the demo: it asks questions, it registers no account and
 * it creates no lead. The address comes from SITE_URL; the public demo is the
 * default.
 *
 *   SITE_URL      the deployment to sweep - the public one by default
 *   SITE_LOCALE   the locale to walk - English by default
 */
const { chromium } = require("playwright");

const BASE = (process.env.SITE_URL || "https://realty.kittray.com").replace(/\/+$/, "");
const LOCALE = process.env.SITE_LOCALE || "en";

/** The routes a visitor may reach without an account. */
const PUBLIC_ROUTES = [
  "",
  "search",
  "chat",
  "tools",
  "analytics",
  "market-trends",
  "city-overview",
  "valuation",
  "cma",
  "knowledge",
  "showcase",
  "agents",
];

/** The account groups: the gate stands in front of them for an anonymous visitor. */
const GATED_ROUTES = [
  "favorites",
  "saved-searches",
  "documents",
  "settings",
  "leads",
  "agent-analytics",
  "usage",
  "admin/bulk-jobs",
  "admin/connectors",
  "admin/data-sources",
  "admin/monitoring",
];

/** The six auth screens. */
const AUTH_ROUTES = [
  "auth/login",
  "auth/register",
  "auth/forgot-password",
  "auth/reset-password",
  "auth/verify-email",
  "auth/oauth/callback",
];

/** An anonymous visitor gets 401 from the account endpoints - that is the answer, not a failure. */
const EXPECTED_API_STATUS = new Set([200, 201, 202, 204, 401]);

const SETTLE_MS = 1200;

function pathOf(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

/** The first agent of the catalogue - the directory needs a real id for its detail route. */
async function firstAgentId() {
  try {
    const response = await fetch(`${BASE}/api/v1/agents?page_size=1`);
    if (!response.ok) return null;
    const payload = await response.json();
    const agents = Array.isArray(payload) ? payload : payload.agents || payload.items || [];
    return agents.length ? agents[0].id : null;
  } catch {
    return null;
  }
}

/**
 * One route, one browser page.
 *
 * The listeners are attached before the navigation and detached after it, so
 * a route is judged on its own calls and console - never on the previous
 * route's leftovers.
 */
async function visit(page, route, expectation) {
  const consoleErrors = [];
  const apiCalls = [];
  let pageStatus = 0;

  const onConsole = (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  };
  const onPageError = (error) => consoleErrors.push(`uncaught: ${error.message}`);
  const onResponse = (response) => {
    if (response.url().includes("/api/")) {
      apiCalls.push({ path: pathOf(response.url()), status: response.status() });
    }
  };

  page.on("console", onConsole);
  page.on("pageerror", onPageError);
  page.on("response", onResponse);

  const reasons = [];
  try {
    const response = await page.goto(`${BASE}/${LOCALE}${route ? `/${route}` : ""}`, {
      waitUntil: "load",
      timeout: 60000,
    });
    pageStatus = response ? response.status() : 0;
    await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(SETTLE_MS);

    if (pageStatus >= 400) reasons.push(`the page answered ${pageStatus}`);

    const body = await page.locator("body").innerText().catch(() => "");
    if (!body.trim()) reasons.push("the page rendered nothing");
    if (/Application error|Internal Server Error/i.test(body)) {
      reasons.push("the page shows an application error");
    }

    for (const call of apiCalls) {
      if (!EXPECTED_API_STATUS.has(call.status)) {
        reasons.push(`${call.path} answered ${call.status}`);
      }
    }

    if (expectation === "gate") {
      // The gate's two ways in are links to the sign-in and the register
      // screen. They carry the locale and the route the visitor asked for,
      // so the link is matched by its path, not by an exact address.
      const gate = page.locator('a[href*="/auth/login"], a[href*="/auth/register"]').first();
      const visible = await gate.isVisible().catch(() => false);
      if (!visible) reasons.push("the gate did not appear");
    }

    if (expectation === "catalogue") {
      // The landing reads the catalogue after it is painted, so the call is
      // waited for rather than looked for in the first second.
      let stats = apiCalls.find((call) => call.path.includes("/catalogue/stats"));
      for (let waited = 0; !stats && waited < 8000; waited += 500) {
        await page.waitForTimeout(500);
        stats = apiCalls.find((call) => call.path.includes("/catalogue/stats"));
      }
      if (!stats) reasons.push("the landing did not read the catalogue");
      else if (stats.status !== 200) reasons.push(`the catalogue answered ${stats.status}`);
    }

    if (expectation === "chat") {
      const answer = await askTheAssistant(page);
      if (answer === "no-input") reasons.push("the chat carried no input");
      else if (answer === "no-answer") reasons.push("the assistant did not answer within 90 s");
      else if (answer === "rate-limited") reasons.push("the pane carries a rate-limit error");
    }
  } catch (error) {
    reasons.push(`the navigation failed: ${error.message}`);
  } finally {
    page.off("console", onConsole);
    page.off("pageerror", onPageError);
    page.off("response", onResponse);
  }

  return { route, pageStatus, apiCalls, consoleErrors, reasons };
}

/**
 * The chat route gets a real question and a real answer.
 *
 * A 200 is not enough: the free tier answers with its rate-limit error INSIDE
 * a 200 response, so the pane itself has to be read before the answer counts.
 */
async function askTheAssistant(page) {
  const input = page.locator("[data-testid='chat-input'], textarea, input[type='text']").first();
  if (!(await input.isVisible().catch(() => false))) return "no-input";

  await input.fill("Find a 2-bedroom apartment in Krakow under 500000 PLN");
  await page.keyboard.press("Enter");

  const answer = await page
    .waitForResponse((r) => r.url().includes("/chat") && r.status() === 200, { timeout: 90000 })
    .catch(() => null);
  if (!answer) return "no-answer";

  await page.waitForTimeout(2500);
  const body = await page.locator("body").innerText().catch(() => "");
  if (/rate limit|429|I apologize/i.test(body)) return "rate-limited";
  return "answered";
}

function line(result) {
  const api = result.apiCalls.map((call) => call.status).join(",") || "-";
  const status = result.reasons.length ? "FAIL" : "OK  ";
  const reason = result.reasons.length ? `  ${result.reasons.join("; ")}` : "";
  return `${status} /${result.route.padEnd(24)} page:${result.pageStatus} api:${api} console:${result.consoleErrors.length}${reason}`;
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: "en-US",
    colorScheme: "dark",
  });

  // The welcome tour is not a defect of the deployment, and it would cover
  // the very screens the sweep looks at.
  await context.addInitScript(() => {
    try {
      localStorage.setItem("onboarding-tour-dismissed-v1", "1");
    } catch {}
  });

  const page = await context.newPage();
  const results = [];

  const agentId = await firstAgentId();
  if (agentId) results.push(await visit(page, `agents/${agentId}`, "public"));

  for (const route of PUBLIC_ROUTES) {
    const expectation = route === "" ? "catalogue" : route === "chat" ? "chat" : "public";
    results.push(await visit(page, route, expectation));
  }
  for (const route of GATED_ROUTES) {
    results.push(await visit(page, route, "gate"));
  }
  for (const route of AUTH_ROUTES) {
    results.push(await visit(page, route, "public"));
  }

  for (const result of results) console.log(line(result));

  const failed = results.filter((result) => result.reasons.length);
  console.log(
    `\n${BASE} - ${results.length} routes, ${results.length - failed.length} ok, ${failed.length} failed`
  );

  await context.close();
  await browser.close();

  if (failed.length) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
