/**
 * @jest-environment node
 */

/**
 * The proxy, as a visitor meets it.
 *
 * The classification of the routes lives in `src/lib/public-routes.ts` and is
 * read by a test of its own. This test is the other half: it calls the proxy
 * the way a browser calls it and asks what it answers.
 *
 * The claim is the one the product makes to a visitor who has no account:
 * the public pages answer, and the pages that need an account ask for one
 * rather than pretending the page does not exist.
 */

import { NextRequest } from 'next/server';

import { proxy } from '@/proxy';

// The internationalisation of the request is not what this test is about: the
// proxy asks the middleware for the localised response and then decides
// whether the visitor may have it. The middleware is replaced with the
// simplest answer it can give - the request continues - so the decision of
// the proxy is what is measured.
jest.mock('next-intl/middleware', () => {
  const { NextResponse } = jest.requireActual<typeof import('next/server')>('next/server');
  return {
    __esModule: true,
    default: () => () => NextResponse.next(),
  };
});

jest.mock('next-intl/routing', () => ({
  defineRouting: (config: unknown) => config,
}));

/** The answer of the proxy to a request for a path, without a session. */
async function answerFor(path: string): Promise<{ status: number; location: string }> {
  const request = new NextRequest(new URL(`http://localhost:3000${path}`));
  const response = await proxy(request);
  return {
    status: response.status,
    location: response.headers.get('location') ?? '',
  };
}

describe('the proxy and a visitor without an account', () => {
  const previousDemoMode = process.env.NEXT_PUBLIC_DEMO_MODE;

  beforeEach(() => {
    // The demo mode of the development stack lets every route through, so a
    // test of the routing must switch it off - otherwise it proves nothing.
    process.env.NEXT_PUBLIC_DEMO_MODE = 'false';
  });

  afterAll(() => {
    // The variable is removed when it was not there before - assigning
    // `undefined` to it would leave the string "undefined" behind.
    if (previousDemoMode === undefined) {
      delete process.env.NEXT_PUBLIC_DEMO_MODE;
    } else {
      process.env.NEXT_PUBLIC_DEMO_MODE = previousDemoMode;
    }
  });

  it('lets the visitor into the public pages', async () => {
    for (const path of ['/en', '/en/search', '/en/property', '/en/privacy', '/en/terms']) {
      const answer = await answerFor(path);
      expect(answer.location).not.toContain('/auth/login');
      expect(answer.status).toBe(200);
    }
  });

  it('lets the visitor into the pages of an account, which explain the account', async () => {
    // The pages that hold what belongs to an account are not sent to the
    // sign-in: the redirect threw the context away, so the visitor was told
    // to sign in without ever hearing what a favourite is. The page renders
    // and the gate explains what the account gives.
    const answer = await answerFor('/en/favorites');
    expect(answer.status).toBe(200);
    expect(answer.location).not.toContain('/auth/login');
  });

  it('asks a visitor for an account on a page nobody classified', async () => {
    const answer = await answerFor('/en/a-page-nobody-classified');
    expect(answer.status).toBe(307);
    expect(answer.location).toContain('/auth/login');
  });
});
