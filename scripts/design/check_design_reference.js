/**
 * The check of the design reference (Task #67).
 *
 * The reference is the prototype the application is ported from. Three
 * things have to hold for it to be worth comparing with the application:
 *
 *   1. the palette of the reference IS the palette of the application - the
 *      same assertion as apps/web/src/lib/__tests__/palette-tokens.test.ts,
 *      applied to the reference's own CSS;
 *   2. every page of the reference renders in the dark theme, at the width
 *      it was designed at and at the width of a phone - checked on the
 *      pixels of the rendered page, not on a claim about it;
 *   3. what the repository publishes exists and is tracked, and the README
 *      names nothing that is not there.
 *
 * The reference itself is local (tmp/ is gitignored), so the first two checks
 * are skipped - and say so - when the prototype is not on this machine.
 *
 * Run it with no arguments:  node scripts/design/check_design_reference.js
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { chromium } = require("playwright");

const { referencePages, serveFolder } = require("../utils/take_screenshots");

const ROOT = path.join(__dirname, "..", "..");
const REFERENCE_DIR = path.join(ROOT, "tmp", "design", "realt2", "v2");
const GLOBALS_CSS = path.join(ROOT, "apps", "web", "src", "app", "globals.css");
const README = path.join(ROOT, "README.md");
const DESIGN_ASSETS = path.join(ROOT, "assets", "design");

// The pages that carry the story - the scope of Task #67.
const SCOPE = [
  "Landing",
  "Search",
  "Chat",
  "Tools",
  "Analytics",
  "MarketTrends",
  "CityOverview",
  "Valuation",
  "CMA",
  "Knowledge",
  "Favorites",
  "Auth",
  "TopBar",
  "Mobile",
];

// The name of a token of the reference and the token of the application it
// carries. The reference names the tokens of the design; the application
// names them the way the framework does.
const TOKENS = {
  "--bg": "--background",
  "--fg": "--foreground",
  "--mu": "--muted",
  "--mf": "--muted-foreground",
  "--bd": "--border",
  "--ac": "--action",
  "--acf": "--action-foreground",
  "--c1": "--chart-1",
  "--ok": "--success",
  "--wa": "--warning",
  "--wab": "--warning-surface",
  "--er": "--destructive",
};

// A dark background is dark; the lightest surface of the dark theme of the
// application (#27272a) sits at 0.02, the light background at 1.0.
const DARK_LUMINANCE = 0.05;

const failures = [];
const notes = [];

function fail(message) {
  failures.push(message);
  console.error(`  FAIL  ${message}`);
}

function ok(message) {
  console.log(`  ok    ${message}`);
}

/** The number of failures so far - a section reports only its own. */
function failed() {
  return failures.length;
}

/** The tokens of a CSS block, as HSL triples. */
function tokensOf(css, from, to) {
  const start = css.indexOf(from);
  const end = to ? css.indexOf(to, start) : css.length;
  if (start < 0) return null;
  const block = css.slice(start, end < 0 ? css.length : end);
  const tokens = {};
  // The application writes the channels bare, the reference writes them in a
  // hsl() - both are read here.
  const re = /--([a-z0-9-]+):\s*(?:hsl\(\s*)?([\d.]+)\s+([\d.]+)%\s+([\d.]+)%(?:\s*\))?/g;
  let match;
  while ((match = re.exec(block))) {
    tokens[`--${match[1]}`] = [Number(match[2]), Number(match[3]), Number(match[4])];
  }
  return tokens;
}

/** The same tolerance as the palette test of the application. */
function sameColour(a, b) {
  return (
    Math.abs(a[0] - b[0]) < 0.05 &&
    Math.abs(a[1] - b[1]) < 0.05 &&
    Math.abs(a[2] - b[2]) < 0.05
  );
}

/** The relative luminance of a colour, as the WCAG defines it. */
function luminance([r, g, b]) {
  const channel = (v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

function checkTokens() {
  console.log("\nThe palette of the reference is the palette of the application");
  const before = failed();
  const globals = fs.readFileSync(GLOBALS_CSS, "utf-8");
  const theme = fs.readFileSync(path.join(REFERENCE_DIR, "theme.css"), "utf-8");

  const appLight = tokensOf(globals, ":root {", ".dark {");
  const appDark = tokensOf(globals, ".dark {", "@theme inline");
  const refLight = tokensOf(theme, ":root {", ".dark {");
  const refDark = tokensOf(theme, ".dark {", ".light {");
  const refMedia = tokensOf(theme, "@media (prefers-color-scheme: dark)", null);

  if (!appLight || !appDark || !refLight || !refDark || !refMedia) {
    fail("the token blocks of globals.css or theme.css could not be read");
    return;
  }

  for (const [ref, app] of Object.entries(TOKENS)) {
    if (!refLight[ref]) fail(`${ref} is not defined in the light palette of the reference`);
    else if (!appLight[app]) fail(`${app} is not defined in the light palette of the application`);
    else if (!sameColour(refLight[ref], appLight[app]))
      fail(`${ref} (light) is ${refLight[ref]} and ${app} is ${appLight[app]}`);

    if (!refDark[ref]) fail(`${ref} is not defined in the dark palette of the reference`);
    else if (!appDark[app]) fail(`${app} is not defined in the dark palette of the application`);
    else if (!sameColour(refDark[ref], appDark[app]))
      fail(`${ref} (dark) is ${refDark[ref]} and ${app} is ${appDark[app]}`);

    if (!refMedia[ref]) fail(`${ref} is not defined in the prefers-color-scheme block`);
    else if (!sameColour(refMedia[ref], refDark[ref]))
      fail(`${ref} differs between the .dark class and the prefers-color-scheme block`);
  }
  if (failed() === before)
    ok(`${Object.keys(TOKENS).length} tokens match in light and in dark`);

  // Every page of the reference has to load the palette.
  const pages = fs.readdirSync(REFERENCE_DIR).filter((f) => f.endsWith(".dc.html"));
  const missing = pages.filter(
    (f) => !fs.readFileSync(path.join(REFERENCE_DIR, f), "utf-8").includes("./theme.css")
  );
  if (missing.length) fail(`these pages do not load theme.css: ${missing.join(", ")}`);
  else ok(`all ${pages.length} pages load theme.css`);
}

/**
 * The rendered page, not a claim about it: the screenshot is decoded and the
 * colour that covers the page is looked at.
 */
async function checkRendered(browser, origin) {
  console.log("\nEvery page renders in the dark theme");
  const before = failed();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    colorScheme: "dark",
  });
  await context.addInitScript(() => {
    localStorage.setItem("re2-theme", "dark");
    document.documentElement.classList.add("dark");
  });
  const page = await context.newPage();

  for (const name of SCOPE) {
    const file = path.join(REFERENCE_DIR, `${name}.dc.html`);
    if (!fs.existsSync(file)) {
      fail(`${name}.dc.html is missing from the reference`);
      continue;
    }
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
      await page.goto(`${origin}/${name}.dc.html`, { waitUntil: "load", timeout: 30000 });
      await page.waitForTimeout(2500);

      const shot = await page.screenshot({ type: "png" });
      const dominant = await page.evaluate(async (base64) => {
        const image = new Image();
        image.src = `data:image/png;base64,${base64}`;
        await image.decode();
        const canvas = document.createElement("canvas");
        canvas.width = image.width;
        canvas.height = image.height;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(image, 0, 0);
        const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        const counts = new Map();
        for (let i = 0; i < data.length; i += 16) {
          // Four bits per channel: the eye cannot tell the difference, and
          // the count stays small enough to be fast.
          const key =
            ((data[i] >> 4) << 8) | ((data[i + 1] >> 4) << 4) | (data[i + 2] >> 4);
          counts.set(key, (counts.get(key) || 0) + 1);
        }
        let best = null;
        let bestCount = 0;
        for (const [key, count] of counts) {
          if (count > bestCount) {
            bestCount = count;
            best = key;
          }
        }
        return [(best >> 8) & 15, (best >> 4) & 15, best & 15].map((v) => v * 17);
      }, shot.toString("base64"));

      const lum = luminance(dominant);
      if (lum >= DARK_LUMINANCE) {
        fail(`${name} at ${width} renders a light background (rgb(${dominant.join(",")}), luminance ${lum.toFixed(3)})`);
      }
    }
  }
  if (failed() === before) ok(`${SCOPE.length} pages render dark at 1440 and at 390`);
  await context.close();
}

function checkAssets() {
  console.log("\nThe published screenshots exist and are tracked");
  const before = failed();
  const tracked = new Set(
    execFileSync("git", ["ls-files", "assets/design"], { cwd: ROOT, encoding: "utf-8" })
      .split("\n")
      .filter(Boolean)
  );
  let count = 0;
  for (const name of SCOPE) {
    const file = `assets/design/${name}-dark.png`;
    if (!fs.existsSync(path.join(ROOT, file))) {
      fail(`${file} does not exist`);
      continue;
    }
    if (!tracked.has(file)) {
      fail(`${file} is not tracked by git`);
      continue;
    }
    count += 1;
  }
  if (failed() === before) ok(`${count} screenshots exist and are tracked`);
}

function checkReadme() {
  console.log("\nThe README names only files that exist");
  const before = failed();
  const readme = fs.readFileSync(README, "utf-8");
  const names = new Set();
  const re = /!?\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;
  let match;
  while ((match = re.exec(readme))) {
    const target = match[1];
    if (/^(https?:|mailto:|#)/.test(target)) continue;
    names.add(target.split("#")[0]);
  }
  const missing = [...names].filter((name) => !fs.existsSync(path.join(ROOT, name)));
  if (missing.length) fail(`the README names files that do not exist: ${missing.join(", ")}`);
  else if (failed() === before) ok(`${names.size} local links and images of the README all exist`);
}

async function main() {
  const reference = referencePages(REFERENCE_DIR);
  if (!reference) {
    notes.push(
      "the design reference is not on this machine (tmp/ is gitignored) - the palette and the rendering are not checked here"
    );
    console.log("\nThe design reference is not on this machine - its palette and its rendering are not checked.");
  } else {
    await checkTokens();
    const server = await serveFolder(reference.folder);
    const origin = `http://127.0.0.1:${server.address().port}`;
    const browser = await chromium.launch({ headless: true });
    try {
      await checkRendered(browser, origin);
    } finally {
      await browser.close();
      server.close();
    }
  }

  checkAssets();
  checkReadme();

  console.log("");
  if (failures.length) {
    console.error(`${failures.length} check(s) failed`);
    process.exit(1);
  }
  console.log("The design reference is in order.");
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
