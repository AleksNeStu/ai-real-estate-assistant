import { chromium } from 'playwright';

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  // Navigate to running app
  const url = process.env.APP_URL || 'http://localhost:8501';
  await page.goto(url, { waitUntil: 'load', timeout: 30000 });

  // Home screenshot (dark mode UI, preferences shown)
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'assets/screen.png', fullPage: true });

  // Navigate to Market Insights tab and capture Expert Panel
  try {
    await page.getByText('Market Insights', { exact: false }).click();
  } catch (e) {
    // Fallback: try emoji label
    try { await page.getByText('📈 Market Insights', { exact: false }).click(); } catch {}
  }

  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'assets/screen2.png', fullPage: true });

  await browser.close();
}

run().catch((err) => {
  console.error('Screenshot capture failed:', err);
  process.exit(1);
});

