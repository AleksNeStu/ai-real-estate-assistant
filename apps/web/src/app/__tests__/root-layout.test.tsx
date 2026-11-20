import type { ReactElement, ReactNode } from 'react';

import RootLayout from '../layout';

/**
 * The measurement.
 *
 * A public site with no measurement is a site nobody can improve: there is no
 * way to tell whether a change helped. The beacon is Cloudflare Web Analytics
 * - cookieless, no personal data - and it is the only thing on the page that
 * talks to a third party.
 *
 * Two properties matter, and both are locked here: the beacon is there when
 * the deployment has a token, and it is NOT there when it does not. A site
 * that claims to measure nothing must not quietly ship a third-party script.
 *
 * The layout is called rather than rendered: it is a server component, and
 * rendering it in jsdom makes React complain about a script tag in a
 * component - a warning that says nothing about the server-rendered page.
 */
describe('the measurement beacon', () => {
  const original = process.env.CF_WEB_ANALYTICS_TOKEN;

  afterEach(() => {
    if (original === undefined) {
      delete process.env.CF_WEB_ANALYTICS_TOKEN;
    } else {
      process.env.CF_WEB_ANALYTICS_TOKEN = original;
    }
  });

  /**
   * The layout returns a fragment: the page, and the beacon (or nothing).
   */
  function renderLayout(token?: string) {
    if (token === undefined) {
      delete process.env.CF_WEB_ANALYTICS_TOKEN;
    } else {
      process.env.CF_WEB_ANALYTICS_TOKEN = token;
    }

    const tree = RootLayout({ children: 'the page' }) as ReactElement<{
      children: ReactNode[];
    }>;
    const children = tree.props.children;
    return {
      page: children[0],
      beacon: children[1] as ReactElement<{
        src?: string;
        'data-cf-beacon'?: string;
      }> | null,
    };
  }

  it('is absent when the deployment has no token', () => {
    const { beacon } = renderLayout();

    expect(beacon).toBeNull();
  });

  it('carries the token of the deployment when it has one', () => {
    const { beacon } = renderLayout('test-token');

    expect(beacon).not.toBeNull();
    expect(beacon?.props.src).toBe('https://static.cloudflareinsights.com/beacon.min.js');
    expect(beacon?.props['data-cf-beacon']).toContain('test-token');
  });

  it('does not stop the page itself from rendering', () => {
    const { page } = renderLayout();

    expect(page).toBe('the page');
  });
});
