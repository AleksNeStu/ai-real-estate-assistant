// Capture all 6 README grid screenshots in DARK theme with consistent
// settings (1280x800, fullPage:false). Writes to assets/screenshots/.
// Same dark-theme injection as take_screenshots.js (localStorage +
// .dark class on documentElement).
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE = process.argv[2] || "http://localhost:3082";
const OUT_DIR = path.join(__dirname, "..", "..", "assets", "screenshots");

// 6 README grid slots, all dark theme.
const SCREENSHOTS = [
  { name: "home-dark",          path: "/" },
  { name: "chat-dark",          path: "/en/chat" },
  { name: "agents-dark",        path: "/en/agents" },
  { name: "analytics-dark",     path: "/en/analytics" },
  { name: "city-overview-dark", path: "/en/city-overview" },
  { name: "knowledge-dark",     path: "/en/knowledge" },
  // Auth-gated pages (render fine in demo mode via middleware bypass)
  { name: "favorites-dark",     path: "/en/favorites" },
  { name: "documents-dark",     path: "/en/documents" },
  { name: "settings-dark",      path: "/en/settings" },
];

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: "en-US",
    colorScheme: "dark",
  });
  // Force dark theme (the page's className="dark" default makes
  // colorScheme: 'dark' work, but we set localStorage + class
  // explicitly for safety).
  await context.addInitScript(() => {
    localStorage.setItem("theme", "dark");
    document.documentElement.classList.add("dark");
  });
  const page = await context.newPage();

  for (const shot of SCREENSHOTS) {
    const url = `${BASE}${shot.path}`;
    console.log(`Capturing ${shot.name}...`);
    try {
      await page.goto(url, { waitUntil: "load", timeout: 30000 });
      // city-overview fires 5+ parallel search queries; give them time.
      const wait = shot.name === "city-overview-dark" ? 12000 : 5000;
      await page.waitForTimeout(wait);

      const outPath = path.join(OUT_DIR, `${shot.name}.png`);
      await page.screenshot({ path: outPath, fullPage: false });
      const size = fs.statSync(outPath).size;
      console.log(`  Saved: ${outPath} (${(size / 1024).toFixed(1)} KB)`);
    } catch (err) {
      console.error(`  Failed: ${err.message}`);
    }
  }

  await context.close();
  await browser.close();
  console.log("\nDone! Dark-theme captures regenerated.");
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});