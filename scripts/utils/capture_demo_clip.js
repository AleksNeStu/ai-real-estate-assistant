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
    // The hero asks the live catalogue for the demo query, and the frame is
    // taken after that answer - a picture of the instrument mid-flight is a
    // picture of a loading panel.
    const searched = page
      .waitForResponse((r) => r.url().includes("/api/v1/search"), { timeout: 60000 })
      .catch(() => null);
    await page.goto(`${BASE}/en`, { waitUntil: "load", timeout: 60000 });
    await searched;
    await page.waitForTimeout(2000);
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
    // Every status the chat answers with, so a rejected frame can say what
    // the deployment actually replied instead of "it did not answer".
    const statuses = [];
    const onResponse = (r) => {
      if (r.url().includes("/api/v1/chat")) statuses.push(r.status());
    };
    page.on("response", onResponse);

    await page.goto(`${BASE}/en/chat`, { waitUntil: "load", timeout: 60000 });
    await dismissTour(page);
    const input = page.locator("[data-testid='chat-input'], textarea, input[type='text']").first();
    await input.waitFor({ state: "visible", timeout: 20000 });
    await input.fill("Find a 2-bedroom apartment in Krakow under 500000 PLN");
    await page.keyboard.press("Enter");
    const answer = await page
      .waitForResponse((r) => r.url().includes("/api/v1/chat") && r.status() === 200, {
        timeout: 90000,
      })
      .catch(() => null);
    page.off("response", onResponse);
    if (!answer) {
      console.error(
        `scene 3: the chat answered with [${statuses.join(", ") || "no response"}] - the frame is rejected`
      );
      await context.close();
      await browser.close();
      process.exit(2);
    }

    // The answer streams: the citations arrive with the last chunk. The
    // frame is accepted only when the pane carries them - an answer without
    // sources is not the third scene of the clip.
    const citations = page.locator('[data-testid="chat-assistant-message"] details ol li');
    await citations
      .first()
      .waitFor({ state: "attached", timeout: 120000 })
      .catch(() => null);
    await page.waitForTimeout(3000);

    // The sources are shown, not only counted: the clip is the answer WITH
    // its citations, so the list is opened before the frame is taken.
    const summary = page.locator('[data-testid="chat-assistant-message"] details summary').first();
    if (await summary.count()) {
      await summary.click().catch(() => {});
      await page.waitForTimeout(800);
    }
    await page.evaluate(() => {
      const pane = document.querySelector(".overflow-y-auto");
      if (pane) pane.scrollTop = 0;
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(1000);

    // HTTP 200 is not enough: the free tier answers with the rate-limit
    // error INSIDE a 200 response, so a capture that only checks the status
    // code publishes the error instead of an answer. The pane itself has to
    // be read before the frame is accepted.
    const pane = await page.locator(".overflow-y-auto").first().innerText();
    if (/rate limit|429|hourly limit|daily limit|I apologize/i.test(pane)) {
      console.error("scene 3: the pane carries a rate-limit error - the frame is rejected");
      await context.close();
      await browser.close();
      process.exit(2);
    }
    const errors = await page.locator('[data-testid="chat-assistant-message"][role="alert"]').count();
    if (errors > 0) {
      console.error("scene 3: the pane carries an error answer - the frame is rejected");
      await context.close();
      await browser.close();
      process.exit(2);
    }
    const cited = await citations.count();
    if (cited === 0) {
      console.error("scene 3: the answer carries no sources - the frame is rejected");
      await context.close();
      await browser.close();
      process.exit(2);
    }

    await page.screenshot({ path: path.join(OUT, "3-chat.png") });
    console.log(`scene 3: the assistant answering, ${cited} source(s)`);
  }

  await context.close();
  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
