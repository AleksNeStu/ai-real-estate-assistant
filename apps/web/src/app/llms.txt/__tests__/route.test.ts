import { GET } from '../route';

/**
 * The llms.txt is the document an answer engine reads when it asks "what
 * does this deployment hold?". It has no test: a route that disappeared
 * from the list, or a catalogue that stopped answering, would have emptied
 * the document while the pipeline stayed green.
 *
 * These tests hold the two things it promises: it names the live routes,
 * and it describes the catalogue of THIS deployment.
 */

jest.mock('@/lib/api/server', () => ({
  serverApiUrl: () => 'http://api.test/api/v1',
}));

jest.mock('next-intl/server', () => ({
  getTranslations: async (namespace?: string) => (key: string) => `${namespace ?? ''}.${key}`,
  setRequestLocale: () => undefined,
}));

function mockDeployment(options: { stats?: unknown; properties?: unknown } = {}) {
  global.fetch = jest.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes('/catalogue/stats')) {
      return {
        ok: true,
        json: async () =>
          options.stats ?? { total: 250, agents: 15, cities: [{ name: 'Kraków', count: 62 }] },
      } as unknown as Response;
    }
    if (url.includes('/properties')) {
      return {
        ok: true,
        json: async () =>
          options.properties ?? {
            properties: [{ id: 'prop-a', title: 'Two rooms in Kazimierz', city: 'Kraków' }],
          },
      } as unknown as Response;
    }
    return { ok: false, json: async () => ({}) } as unknown as Response;
  }) as unknown as typeof fetch;
}

describe('the llms.txt of the deployment', () => {
  it('names the live routes', async () => {
    mockDeployment();
    const response = await GET();
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toContain('/search');
    expect(body).toContain('/chat');
    expect(body).toContain('/market-trends');
    expect(body).toContain('/tools');
  });

  it('describes the catalogue of this deployment', async () => {
    mockDeployment();
    const body = await (await GET()).text();

    expect(body).toContain('250');
    expect(body).toContain('Kraków');
  });

  it('names a listing of the catalogue', async () => {
    mockDeployment();
    const body = await (await GET()).text();

    expect(body).toContain('prop-a');
  });

  it('still answers when the catalogue cannot be reached', async () => {
    global.fetch = jest.fn(async () => {
      throw new Error('unreachable');
    }) as unknown as typeof fetch;

    const response = await GET();
    const body = await response.text();

    // The document is the answer to a question; a document that fails is
    // worse than a document without the numbers.
    expect(response.status).toBe(200);
    expect(body).toContain('/search');
  });
});
