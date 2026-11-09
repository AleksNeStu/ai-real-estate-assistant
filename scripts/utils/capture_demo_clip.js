/**
 * The three scenes of the six-second demo clip, captured from the live
 * deployment in the dark theme.
 *
 *   node scripts/utils/capture_demo_clip.js [address] [scene]
 *
 *   address  the deployment to film - the live one, never a local build
 *   scene    all (default) | landing | search | chat
 *
 * The frames land in tmp/clip/ and are the input of
 * scripts/utils/build_demo_clip.sh.
 */
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE =
  process.argv[2] && !process.argv[2].startsWith("all")
    ? process.argv[2]
    : "https://realty.kittray.com";
const SCENE = process.argv[3] || "all";
const OUT = path.join(__dirname, "..", "..", "tmp", "clip");
fs.mkdirSync(OUT, { recursive: true });

async function dismissTour(page) {
  // The tour shows 1.5 s after mount and remembers its dismissal under this
  // key. A screenshot of the product is not a screenshot of a welcome dialog.
  await page.evaluate(() => {
    try {
      localStorage.setItem("onboarding-tour-dismissed-v1", "1");
    } catch {}
  });
  const skip = page.getByRole("button", { name: /skip/i }).first();
  if (await skip.isVisible().catch(() => false)) {
    await skip.click();
    await page.waitForTimeout(400);
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: "en-US",
    colorScheme: "dark",
    deviceScaleFactor: 1,
  });

  // Two separate init scripts, and every statement guarded on its own: at
  // document-start `document.documentElement` is still null, so a bare
  // classList.add() throws and - in one script - silently skips every
  // statement after it.
  await context.addInitScript(() => {
    try {
      localStorage.setItem("theme", "dark");
    } catch {}
  });
  await context.addInitScript(() => {
    try {
      localStorage.setItem("onboarding-tour-dismissed-v1", "1");
    } catch {}
  });

  const page = await context.newPage();

  // 1 - the landing
  if (SCENE === "all" || SCENE === "landing") {
    await page.goto(`${BASE}/en`, { waitUntil: "load", timeout: 60000 });
    await page.waitForTimeout(6000);
    await dismissTour(page);
    await page.screenshot({ path: path.join(OUT, "1-landing.png") });
    console.log("scene 1: the landing");
  }

  // 2 - the search with its results
  if (SCENE === "all" || SCENE === "search") {
    await page.goto(`${BASE}/en/search?q=2-bedroom+apartment+in+Krakow`, {
      waitUntil: "load",
      timeout: 60000,
    });
    await page.waitForTimeout(9000);
    await dismissTour(page);
    await page.screenshot({ path: path.join(OUT, "2-search.png") });
    console.log("scene 2: the search");
  }

  // 3 - the assistant answering
  if (SCENE === "all" || SCENE === "chat") {
    await page.goto(`${BASE}/en/chat`, { waitUntil: "load", timeout: 60000 });
    await dismissTour(page);
    const input = page.locator("[data-testid='chat-input'], textarea, input[type='text']").first();
    await input.waitFor({ state: "visible", timeout: 20000 });
    await input.fill("Find a 2-bedroom apartment in Krakow under 500000 PLN");
    await page.keyboard.press("Enter");
    const answer = await page
      .waitForResponse((r) => r.url().includes("/chat") && r.status() === 200, { timeout: 90000 })
      .catch(() => null);
    if (!answer) {
      console.error("scene 3: the chat did not answer within 90 s");
      await context.close();
      await browser.close();
      process.exit(2);
    }
    await page.waitForTimeout(9000);
    await page.evaluate(() => {
      const pane = document.querySelector(".overflow-y-auto");
      if (pane) pane.scrollTop = pane.scrollHeight;
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(1000);

    // HTTP 200 is not enough: the free tier answers with the rate-limit
    // error INSIDE a 200 response, so a capture that only checks the status
    // code publishes the error instead of an answer. The pane itself has to
    // be read before the frame is accepted.
    const pane = await page.locator(".overflow-y-auto").first().innerText();
    if (/rate limit|429|I apologize/i.test(pane)) {
      console.error("scene 3: the pane carries a rate-limit error - the frame is rejected");
      await context.close();
      await browser.close();
      process.exit(2);
    }

    await page.screenshot({ path: path.join(OUT, "3-chat.png") });
    console.log("scene 3: the assistant answering");
  }

  await context.close();
  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
