import { SITE_URL, absoluteUrl } from '../site';

describe('site', () => {
  describe('SITE_URL', () => {
    it('uses the correct Render origin', () => {
      expect(SITE_URL.origin).toBe('https://realestate-web-dz1y.onrender.com');
    });
  });

  describe('absoluteUrl', () => {
    it('builds absolute URL with leading slash', () => {
      expect(absoluteUrl('/en/search')).toBe(
        'https://realestate-web-dz1y.onrender.com/en/search'
      );
    });

    it('builds absolute URL without leading slash', () => {
      expect(absoluteUrl('en/search')).toBe(
        'https://realestate-web-dz1y.onrender.com/en/search'
      );
    });
  });
});
