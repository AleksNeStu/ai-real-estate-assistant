const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");
const http = require("http");

const BASE = process.argv[2] || "http://localhost:3082";
const THEME = process.argv[3] || "dark";
// The output folder and the suffix of the file names are optional: the
// repository keeps two sets - the light one in docs/screenshots and the
// dark one in assets/screenshots, which the GitHub profile page shows.
const OUT_DIR = process.argv[4]
  ? path.resolve(process.argv[4])
  : path.join(__dirname, "..", "..", "docs", "screenshots");
const NAME_SUFFIX = process.argv[5] || "";

/**
 * The design reference is a set of local pages, not routes of the running
 * application. A target that names a file or a folder is captured as it is;
 * a target that is a URL keeps the route list of the application below.
 */
function referencePages(target) {
  const resolved = path.resolve(target);
  if (!fs.existsSync(resolved)) return null;
  const isFolder = fs.statSync(resolved).isDirectory();
  const folder = isFolder ? resolved : path.dirname(resolved);
  const files = isFolder
    ? fs.readdirSync(resolved).filter((f) => f.endsWith(".dc.html")).sort()
    : [path.basename(resolved)];
  if (!files.length) return null;
  return {
    folder,
    shots: files.map((f) => ({
      name: f.replace(/\.dc\.html$/, ""),
      file: f,
      desc: "The design reference",
    })),
  };
}

/**
 * The reference pages load their parts with fetch(), and fetch() does not
 * read a file:// URL. The folder is therefore served over the loopback for
 * the time of the capture, and the server stops with the capture.
 */
function serveFolder(folder) {
  const server = http.createServer((req, res) => {
    const name = decodeURIComponent(req.url.split("?")[0]).replace(/^\/+/, "");
    const file = path.join(folder, name);
    if (!file.startsWith(folder) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404);
      res.end("not found");
      return;
    }
    const types = {
      ".html": "text/html; charset=utf-8",
      ".js": "text/javascript; charset=utf-8",
      ".css": "text/css; charset=utf-8",
      ".json": "application/json",
      ".svg": "image/svg+xml",
      ".png": "image/png",
    };
    res.writeHead(200, { "Content-Type": types[path.extname(file)] || "application/octet-stream" });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

const REFERENCE = referencePages(BASE);

// The reference is drawn at the width it was designed at; the application
// keeps the width its own screenshots were taken at.
const VIEWPORT = REFERENCE ? { width: 1440, height: 900 } : { width: 1280, height: 800 };

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
    viewport: VIEWPORT,
    locale: "en-US",
    colorScheme: THEME,
  });

  // Apply dark/light theme before any page renders. The frontend doesn't
  // respect `colorScheme: "light"` on its own, so the choice is written to
  // the storage and the class is set on the document element - without this,
  // every "light" capture was actually rendering in the default dark theme
  // (because the demo page starts dark).
  await context.addInitScript((theme) => {
    localStorage.setItem("theme", theme);
    // The design reference keeps its own choice under its own key.
    localStorage.setItem("re2-theme", theme);
    // The document element does not exist yet when an init script runs, so
    // the class is set the moment it does - before the first paint.
    const mark = () => {
      if (!document.documentElement) return false;
      document.documentElement.classList.toggle("dark", theme === "dark");
      return true;
    };
    if (!mark()) {
      const observer = new MutationObserver(() => {
        if (mark()) observer.disconnect();
      });
      observer.observe(document, { childList: true, subtree: true });
    }
  }, THEME);

  const page = await context.newPage();

  // The first-visit tour is a popup over the interface. A screenshot of the
  // product is not a screenshot of a welcome dialog, so the tour is
  // remembered as seen before the first page opens.
  await context.addInitScript(() => {
    localStorage.setItem("onboarding-tour-dismissed-v1", "1");
  });

  for (const shot of screenshots) {
    const url = shot.url || `${BASE}${shot.path}`;
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
      if (shot.path === "/en/chat") {
        try {
          // The chat input carries no `type` attribute, so a selector on
          // `input[type='text']` never matches it - the test id is the
          // stable handle.
          const input = page
            .locator("[data-testid='chat-input'], textarea, input[type='text']")
            .first();
          await input.waitFor({ state: "visible", timeout: 15000 });
          await input.fill("Find a 2-bedroom apartment in Krakow under 500000 PLN");
          await page.keyboard.press("Enter");
          // The hosted model answers in its own time; the first token of a
          // streamed reply can take a while, so the wait is generous.
          await page.waitForResponse(
            (r) => r.url().includes("/chat") && r.status() === 200,
            { timeout: 60000 }
          );
          await page.waitForTimeout(8000); // let the streamed reply paint
          // The conversation lives in its own scroll area, not in the page -
          // scroll the messages to their end, or the screenshot shows the
          // empty part of the card.
          await page.evaluate(() => {
            const pane = document.querySelector(".overflow-y-auto");
            if (pane) pane.scrollTop = pane.scrollHeight;
            // Typing scrolled the window to the input; the page belongs at
            // its top, with the conversation inside the card.
            window.scrollTo(0, 0);
          });
          await page.waitForTimeout(1000);
        } catch (err) {
          console.warn(`  Chat scripting failed (fallback to empty): ${err.message}`);
        }
      }

      const outPath = path.join(OUT_DIR, `${shot.name}${NAME_SUFFIX}.png`);
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

  // The reference is served over the loopback for the time of the capture.
  let server = null;
  let shots = SCREENSHOTS;
  if (REFERENCE) {
    server = await serveFolder(REFERENCE.folder);
    const origin = `http://127.0.0.1:${server.address().port}`;
    shots = REFERENCE.shots.map((s) => ({ ...s, url: `${origin}/${s.file}` }));
  }

  const browser = await chromium.launch({ headless: true });

  // Desktop screenshots
  const desktop = shots.filter((s) => !s.mobile);
  await captureScreenshots(browser, desktop);

  // Mobile screenshots
  const mobile = shots.filter((s) => s.mobile);
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
    } else {
      await mobileContext.addInitScript(() => {
        localStorage.setItem("theme", "light");
        document.documentElement.classList.remove("dark");
      });
    }

    // The same first-visit tour as on the desktop.
    await mobileContext.addInitScript(() => {
      localStorage.setItem("onboarding-tour-dismissed-v1", "1");
    });

    const mobilePage = await mobileContext.newPage();

    for (const shot of mobile) {
      const url = `${BASE}${shot.path}`;
      console.log(`Capturing ${shot.name} (${shot.desc}, mobile)...`);
      try {
        await mobilePage.goto(url, { waitUntil: "load", timeout: 30000 });
        await mobilePage.waitForTimeout(5000);

        const outPath = path.join(OUT_DIR, `${shot.name}${NAME_SUFFIX}.png`);
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
  if (server) server.close();
  console.log(`\nDone! Screenshots saved to ${OUT_DIR}`);
}

if (require.main === module) {
  main().catch((err) => {
    console.error("Fatal:", err);
    process.exit(1);
  });
}

// The reference pages are served and addressed here, and the check of the
// reference uses the same two.
module.exports = { referencePages, serveFolder };
