import { SITE_URL, absoluteUrl } from '../site';

describe('site', () => {
  describe('SITE_URL', () => {
    it('uses the correct public origin', () => {
      expect(SITE_URL.origin).toBe('https://ai-real-estate-demo.devs-scaler.workers.dev');
    });
  });

  describe('absoluteUrl', () => {
    it('builds absolute URL with leading slash', () => {
      expect(absoluteUrl('/en/search')).toBe('https://ai-real-estate-demo.devs-scaler.workers.dev/en/search');
    });

    it('builds absolute URL without leading slash', () => {
      expect(absoluteUrl('en/search')).toBe('https://ai-real-estate-demo.devs-scaler.workers.dev/en/search');
    });
  });
});

describe('site with an empty build argument', () => {
  // The public address is a BUILD argument. A build that does not pass it
  // sets the variable to an empty string, and `new URL('')` throws - which
  // fails the whole frontend build (the sitemap collection included).
  const original = process.env.NEXT_PUBLIC_SITE_URL;

  beforeEach(() => {
    jest.resetModules();
    process.env.NEXT_PUBLIC_SITE_URL = '';
  });

  afterAll(() => {
    if (original === undefined) {
      delete process.env.NEXT_PUBLIC_SITE_URL;
    } else {
      process.env.NEXT_PUBLIC_SITE_URL = original;
    }
  });

  it('falls back to the public origin instead of throwing', async () => {
    jest.resetModules();
    const { SITE_URL: siteUrl } = await import('../site');
    expect(siteUrl.origin).toBe('https://ai-real-estate-demo.devs-scaler.workers.dev');
  });
});
