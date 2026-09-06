const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE = process.argv[2] || "http://localhost:3082";
const THEME = process.argv[3] || "dark";
const OUT_DIR = path.join(__dirname, "..", "..", "docs", "screenshots");

const SCREENSHOTS = [
  { name: "home", path: "/", desc: "Landing page" },
  { name: "login", path: "/en/auth/login", desc: "Login form" },
  { name: "register", path: "/en/auth/register", desc: "Registration" },
  { name: "search", path: "/en/search", desc: "Property search" },
  { name: "search-results", path: "/en/search?q=apartment+krakow", desc: "Search results" },
  { name: "chat", path: "/en/chat", desc: "AI chat" },
  { name: "analytics", path: "/en/analytics", desc: "Analytics tools" },
  { name: "agents", path: "/en/agents", desc: "Agent directory" },
  { name: "market-trends", path: "/en/market-trends", desc: "Market trends" },
  { name: "cma", path: "/en/cma", desc: "CMA tool" },
  { name: "city-overview", path: "/en/city-overview", desc: "City overview" },
  { name: "knowledge", path: "/en/knowledge", desc: "Knowledge base" },
  { name: "favorites", path: "/en/favorites", desc: "Saved favorites" },
  { name: "saved-searches", path: "/en/saved-searches", desc: "Saved searches" },
  { name: "leads", path: "/en/leads", desc: "Lead management" },
  { name: "settings", path: "/en/settings", desc: "User settings" },
  { name: "tools", path: "/en/tools", desc: "Available tools" },
  { name: "agent-analytics", path: "/en/agent-analytics", desc: "Agent analytics" },
  { name: "documents", path: "/en/documents", desc: "Document manager" },
  { name: "usage", path: "/en/usage", desc: "Usage dashboard" },
  { name: "home-mobile", path: "/", desc: "Landing (mobile)", mobile: true },
  { name: "chat-mobile", path: "/en/chat", desc: "AI chat (mobile)", mobile: true },
  { name: "search-mobile", path: "/en/search?q=apartment+berlin", desc: "Search (mobile)", mobile: true },
];

async function captureScreenshots(browser, screenshots) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: "en-US",
    colorScheme: THEME,
  });

  // Apply dark/light theme before any page renders
  if (THEME === "dark") {
    await context.addInitScript(() => {
      localStorage.setItem("theme", "dark");
      document.documentElement.classList.add("dark");
    });
  } else {
    // Force light mode: the frontend doesn't respect `colorScheme: "light"`
    // on its own, so we explicitly set localStorage and remove the .dark
    // class. Without this, every "light" capture was actually rendering in
    // the default dark theme (because the demo page starts dark).
    await context.addInitScript(() => {
      localStorage.setItem("theme", "light");
      document.documentElement.classList.remove("dark");
    });
  }

  const page = await context.newPage();

  for (const shot of screenshots) {
    const url = `${BASE}${shot.path}`;
    console.log(`Capturing ${shot.name} (${shot.desc})...`);
    try {
      await page.goto(url, { waitUntil: "load", timeout: 30000 });
      await page.waitForTimeout(5000);

      // Dismiss cookie banners
      try {
        const btn = page.locator("button:has-text('Accept'), button:has-text('Close')");
        if (await btn.isVisible({ timeout: 1000 })) await btn.click();
      } catch {}

      // For the AI chat route, type a question and wait for the assistant
      // response so the screenshot shows a real conversation, not the empty
      // welcome screen. Without this the chat panel always captures empty.
      if (shot.name === "chat") {
        try {
          const input = page.locator("textarea, input[type='text']").first();
          await input.waitFor({ state: "visible", timeout: 5000 });
          await input.fill("Find 2-bedroom apartments under $400,000 in Madrid");
          await page.keyboard.press("Enter");
          await page.waitForResponse(
            (r) => r.url().includes("/chat") && r.status() === 200,
            { timeout: 20000 }
          );
          await page.waitForTimeout(3000); // let the streamed reply paint
        } catch (err) {
          console.warn(`  Chat scripting failed (fallback to empty): ${err.message}`);
        }
      }

      const outPath = path.join(OUT_DIR, `${shot.name}.png`);
      await page.screenshot({ path: outPath, fullPage: false });
      const size = fs.statSync(outPath).size;
      console.log(`  Saved: ${outPath} (${(size / 1024).toFixed(1)} KB)`);
    } catch (err) {
      console.error(`  Failed: ${err.message}`);
    }
  }

  await context.close();
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });

  // Desktop screenshots
  const desktop = SCREENSHOTS.filter((s) => !s.mobile);
  await captureScreenshots(browser, desktop);

  // Mobile screenshots
  const mobile = SCREENSHOTS.filter((s) => s.mobile);
  if (mobile.length) {
    const mobileContext = await browser.newContext({
      viewport: { width: 375, height: 812 },
      locale: "en-US",
      colorScheme: THEME,
      isMobile: true,
    });

    if (THEME === "dark") {
      await mobileContext.addInitScript(() => {
        localStorage.setItem("theme", "dark");
        document.documentElement.classList.add("dark");
      });
    }

    const mobilePage = await mobileContext.newPage();

    for (const shot of mobile) {
      const url = `${BASE}${shot.path}`;
      console.log(`Capturing ${shot.name} (${shot.desc}, mobile)...`);
      try {
        await mobilePage.goto(url, { waitUntil: "load", timeout: 30000 });
        await mobilePage.waitForTimeout(5000);

        const outPath = path.join(OUT_DIR, `${shot.name}.png`);
        await mobilePage.screenshot({ path: outPath, fullPage: false });
        const size = fs.statSync(outPath).size;
        console.log(`  Saved: ${outPath} (${(size / 1024).toFixed(1)} KB)`);
      } catch (err) {
        console.error(`  Failed: ${err.message}`);
      }
    }

    await mobileContext.close();
  }

  await browser.close();
  console.log("\nDone! Screenshots saved to docs/screenshots/");
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
