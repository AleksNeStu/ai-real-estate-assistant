import { buildStructuredData } from '../structured-data';
import { SITE_URL } from '../site';

describe('buildStructuredData', () => {
  const locale = 'en' as const;
  const result = buildStructuredData(locale);

  it('returns an object with @context set to schema.org', () => {
    expect(result['@context']).toBe('https://schema.org');
  });

  it('returns an @graph array', () => {
    expect(Array.isArray(result['@graph'])).toBe(true);
  });

  it('@graph contains exactly one Organization', () => {
    const graph = result['@graph'] as unknown[];
    const organizations = graph.filter(
      (item) => typeof item === 'object' && item !== null && (item as Record<string, unknown>)['@type'] === 'Organization'
    );
    expect(organizations).toHaveLength(1);
  });

  it('@graph contains exactly one WebSite', () => {
    const graph = result['@graph'] as unknown[];
    const websites = graph.filter(
      (item) => typeof item === 'object' && item !== null && (item as Record<string, unknown>)['@type'] === 'WebSite'
    );
    expect(websites).toHaveLength(1);
  });

  it('@graph contains exactly one SoftwareApplication', () => {
    const graph = result['@graph'] as unknown[];
    const apps = graph.filter(
      (item) => typeof item === 'object' && item !== null && (item as Record<string, unknown>)['@type'] === 'SoftwareApplication'
    );
    expect(apps).toHaveLength(1);
  });

  it('SoftwareApplication has offers.price of 0 (MIT free)', () => {
    const graph = result['@graph'] as Record<string, unknown>[];
    const app = graph.find((item) => item['@type'] === 'SoftwareApplication');
    expect(app).toBeDefined();
    const offer = app!.offers as Record<string, unknown>;
    expect(offer).toBeDefined();
    expect(offer.price).toBe('0');
  });

  it('SoftwareApplication has codeRepository pointing to the GitHub repo', () => {
    const graph = result['@graph'] as Record<string, unknown>[];
    const app = graph.find((item) => item['@type'] === 'SoftwareApplication');
    expect(app).toBeDefined();
    expect((app as Record<string, unknown>)['codeRepository']).toBe('https://github.com/AleksNeStu/ai-real-estate-assistant');
  });

  it('SoftwareApplication lists 9 supported languages', () => {
    const graph = result['@graph'] as Record<string, unknown>[];
    const app = graph.find((item) => item['@type'] === 'SoftwareApplication');
    expect(app).toBeDefined();
    const langs = app!.availableLanguage as unknown[];
    expect(langs).toHaveLength(9);
  });

  it('Organization has name AI Real Estate Assistant', () => {
    const graph = result['@graph'] as Record<string, unknown>[];
    const org = graph.find((item) => item['@type'] === 'Organization');
    expect(org).toBeDefined();
    expect(org!.name).toBe('AI Real Estate Assistant');
  });

  it('WebSite has name AI Real Estate Assistant', () => {
    const graph = result['@graph'] as Record<string, unknown>[];
    const site = graph.find((item) => item['@type'] === 'WebSite');
    expect(site).toBeDefined();
    expect(site!.name).toBe('AI Real Estate Assistant');
  });

  it('uses the SITE_URL origin for @id anchors', () => {
    const graph = result['@graph'] as Record<string, unknown>[];
    const origin = SITE_URL.origin;
    for (const item of graph) {
      const id = item['@id'] as string;
      expect(id).toBeDefined();
      expect(id.startsWith(origin)).toBe(true);
    }
  });

  it('does not contain dynamic star or test counts', () => {
    const json = JSON.stringify(result);
    // No runtime-derived dynamic claims
    expect(json).not.toMatch(/star/i);
    expect(json).not.toMatch(/test count/i);
    expect(json).not.toMatch(/[0-9]+["']\s*(stars?|tests?)/i);
  });

  it('links PropVector AI as a sameAs related URL, not as the canonical app', () => {
    const graph = result['@graph'] as Record<string, unknown>[];
    const org = graph.find((item) => item['@type'] === 'Organization') as Record<string, unknown>;
    const sameAs = org!.sameAs as string[];
    expect(sameAs).toContain('https://propvectorai.com');
    // PropVector AI is NOT the canonical URL of the application
    const canonicalUrls = graph.map((item) => item['@id'] as string);
    expect(canonicalUrls).not.toContain('https://propvectorai.com');
  });

  it('WebSite.inLanguage reflects the locale parameter', () => {
    const locale = 'pl' as const;
    const result = buildStructuredData(locale);
    const graph = result['@graph'] as Record<string, unknown>[];
    const site = graph.find((item) => item['@type'] === 'WebSite') as Record<string, unknown>;
    expect(site).toBeDefined();
    expect(site.inLanguage).toBe('pl');
  });
});
