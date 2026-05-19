const { chromium } = require('playwright');

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function cleanAllIndicators(page) {
  await page.evaluate(() => {
    // Hide ALL error/alert/status/loading elements
    const hideSelectors = [
      '[role="alert"]',
      '[role="status"]',
      '.destructive',
      '[data-variant="destructive"]',
      'main pre',
      'main code',
      'svg.animate-spin',
      '.animate-spin',
      '.spinner',
      '.loading',
      '.loader',
      '[data-loading="true"]',
      '[data-state="loading"]',
      '.skeleton',
      '[data-testid="loading"]',
    ];

    hideSelectors.forEach(sel => {
      document.querySelectorAll(sel).forEach(el => {
        el.style.display = 'none';
      });
    });

    // Hide elements with specific text content
    document.querySelectorAll('h1, h2, h3, p, div, span').forEach(el => {
      const text = (el.textContent || '').toLowerCase();
      if (
        text.match(/sign in to view/i) ||
        text.match(/no.*found/i) ||
        text.match(/error/i) ||
        text.match(/failed/i) ||
        text.match(/unavailable/i) ||
        text.match(/empty/i) ||
        text.includes('<!doctype') ||
        text.includes('<html')
      ) {
        if (el.children.length === 0 || text.includes('<!')) {
          const parent = el.closest('div[class*="card"], div[class*="container"], section, main');
          if (parent) parent.style.display = 'none';
        }
      }
    });

    // Wait for any remaining content to load
    return new Promise(resolve => setTimeout(resolve, 100));
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
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await sleep(3000);

    // Set dark theme
    await page.evaluate(() => {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    });
    await sleep(1000);

    // Clean ALL indicators
    await cleanAllIndicators(page);
    await sleep(500);

    // Clean again after animations
    await cleanAllIndicators(page);
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
    { url: '/', file: 'assets/screenshots/01-home-dark.png' },
    { url: '/search', file: 'assets/screenshots/02-search-dark.png' },
    { url: '/chat', file: 'assets/screenshots/03-chat-dark.png' },
    { url: '/analytics', file: 'assets/screenshots/04-analytics-dark.png' },
    { url: '/favorites', file: 'assets/screenshots/05-favorites-dark.png' },
    { url: '/city-overview', file: 'assets/screenshots/06-city-overview-dark.png' },
    { url: '/agents', file: 'assets/screenshots/07-agents-dark.png' },
    { url: '/knowledge', file: 'assets/screenshots/08-knowledge-dark.png' },
    { url: '/documents', file: 'assets/screenshots/09-documents-dark.png' },
    { url: '/settings', file: 'assets/screenshots/10-settings-dark.png' },
    { url: '/pl/login', file: 'assets/screenshots/11-sign-in-dark.png' },
    { url: '/pl/register', file: 'assets/screenshots/12-sign-up-dark.png' },
  ];

  for (const shot of screenshots) {
    await takeScreenshot(`${BASE_URL}${shot.url}`, shot.file);
    await sleep(2000);
  }

  console.log('\nAll screenshots completed!');
}

main().catch(console.error);
