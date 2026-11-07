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
