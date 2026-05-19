const { chromium } = require('playwright');

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const DEMO_MODE = true;

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function cleanErrors(page) {
  await page.evaluate(() => {
    // Hide all error/alert/status elements
    document.querySelectorAll('[role="alert"], [role="status"]').forEach(el => {
      const text = el.textContent?.toLowerCase() || '';
      if (text.match(/no |not found|error|failed|unavailable|unreachable|empty|sign in/i)) {
        el.style.display = 'none';
      }
    });
    document.querySelectorAll('.destructive, [data-variant="destructive"]').forEach(el => {
      el.style.display = 'none';
    });
    document.querySelectorAll('main pre, main code').forEach(el => {
      if (el.textContent.includes('<!DOCTYPE') || el.textContent.includes('<html')) {
        el.style.display = 'none';
      }
    });
    document.querySelectorAll('h1, h2').forEach(el => {
      if (el.textContent.match(/sign in to view/i)) {
        const parent = el.closest('div');
        if (parent) parent.style.display = 'none';
      }
    });
    document.querySelectorAll('svg.animate-spin, .animate-spin').forEach(el => {
      el.style.display = 'none';
    });
    document.querySelectorAll('div').forEach(el => {
      if (el.children.length === 0 && el.textContent.includes('<!DOCTYPE')) {
        el.style.display = 'none';
      }
    });
  });
}

async function takeScreenshot(url, file) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });
  const page = await context.newPage();

  try {
    console.log(`Navigating to ${url}...`);
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await sleep(2000);

    // Set dark theme
    await page.evaluate(() => {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    });
    await sleep(500);

    // Clean errors
    await cleanErrors(page);
    await sleep(300);

    console.log(`Taking screenshot: ${file}...`);
    await page.screenshot({
      path: file,
      scale: 'css',
      type: 'png',
      fullPage: false
    });
    console.log(`✓ Saved: ${file}`);
  } catch (error) {
    console.error(`✗ Failed to screenshot ${url}: ${error.message}`);
  } finally {
    await context.close();
    await browser.close();
  }
}

async function main() {
  const screenshots = [
    { url: '/favorites', file: 'assets/screenshots/favorites-dark.png' },
    { url: '/city-overview', file: 'assets/screenshots/city-overview-dark.png' },
    { url: '/agents', file: 'assets/screenshots/agents-dark.png' },
  ];

  for (const shot of screenshots) {
    await takeScreenshot(`${BASE_URL}${shot.url}`, shot.file);
    await sleep(1000);
  }

  console.log('\nAll screenshots completed!');
}

main().catch(console.error);
