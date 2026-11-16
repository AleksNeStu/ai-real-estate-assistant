import fs from 'node:fs';
import path from 'node:path';

import { SITE_URL } from '@/lib/site';

/**
 * The robots.txt is the policy the deployment publishes to every crawler.
 *
 * It had no test, and it carries two couplings that nothing guarded: the
 * sitemap line names the public address, and the private areas are listed
 * one by one. A deployment on another address would have pointed the
 * crawlers at a sitemap that does not exist there.
 */

const robotsTxt = fs.readFileSync(
  path.join(process.cwd(), 'public', 'robots.txt'),
  'utf-8'
);

describe('the robots.txt of the deployment', () => {
  it('points at the sitemap of this deployment', () => {
    expect(robotsTxt).toContain(`Sitemap: ${SITE_URL.origin}/sitemap.xml`);
  });

  it('lets the crawlers in', () => {
    expect(robotsTxt).toContain('User-agent: *');
    expect(robotsTxt).toMatch(/User-agent: \*\s*\nAllow: \//);
  });

  it('keeps the private areas out', () => {
    for (const privatePath of ['/api/', '/admin/', '/*/auth/', '/*/settings/']) {
      expect(robotsTxt).toContain(`Disallow: ${privatePath}`);
    }
  });

  it('names the AI crawlers it wants to be cited by', () => {
    for (const bot of ['GPTBot', 'ClaudeBot', 'PerplexityBot', 'Google-Extended']) {
      expect(robotsTxt).toContain(`User-agent: ${bot}`);
    }
  });
});
