import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { Faq } from '@/components/landing/faq';
import { LandingFooter } from '@/components/landing/footer';
import { HostedTier } from '@/components/landing/hosted-tier';
import { OpenSource } from '@/components/landing/open-source';

// The landing sections are server components: they read the catalogue
// through next-intl/server, whose server build is ESM and cannot be loaded
// by the test runtime. The catalogue is not what this test is about.
jest.mock('next-intl/server', () => ({
  getTranslations: jest.fn(async () => (key: string) => key),
}));

// The build metadata reads the live deployment; it is not what this test is
// about.
jest.mock('@/components/layout/build-metadata', () => ({
  BuildMetadata: () => null,
}));

// The waitlist posts an address; it is not what this test is about.
jest.mock('@/components/landing/waitlist-form', () => ({
  WaitlistForm: () => null,
}));

jest.mock('@/lib/visitor-tracking', () => ({
  getOrCreateVisitorId: jest.fn(() => 'visitor-uuid-1234'),
  currentLocale: jest.fn(() => 'en'),
}));

const mockFetch = global.fetch as unknown as jest.Mock;

/** The calls that reported a click. */
const outboundCalls = () =>
  mockFetch.mock.calls.filter((call) => String(call[0]).includes('/analytics/outbound'));

/** The body of the last reported click. */
function lastOutboundBody(): Record<string, unknown> {
  const call = outboundCalls()[outboundCalls().length - 1] as [string, RequestInit];
  return JSON.parse(call[1].body as string);
}

/**
 * The outbound clicks of the landing.
 *
 * A click that leaves the site cannot be measured server-side: the browser
 * is gone before the request could be counted. Every link that leaves the
 * site therefore reports its own click, and the report names the destination,
 * the slot and the campaign - otherwise the funnel knows that "somebody
 * clicked" and not where.
 */
describe('the outbound links of the landing', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
    mockFetch.mockResolvedValue(new Response('{}', { status: 204 }));
  });

  it('reports the click on the hosted tier link', async () => {
    render(await HostedTier());

    const link = screen.getByRole('link', { name: 'exits.hosted.link ↗' });
    fireEvent.click(link);

    await waitFor(() => expect(outboundCalls()).toHaveLength(1));
    expect(lastOutboundBody()).toMatchObject({
      target: 'propvector',
      campaign: 'propvector',
      slot: 'exit_hosted',
    });
  });

  it('reports the click on the fork and on the studio link', async () => {
    render(await OpenSource());

    fireEvent.click(screen.getByRole('link', { name: 'exits.run.ctaFork' }));
    await waitFor(() => expect(outboundCalls()).toHaveLength(1));
    expect(lastOutboundBody()).toMatchObject({
      target: 'github',
      campaign: 'oss',
      slot: 'exit_fork',
    });

    fireEvent.click(screen.getByRole('link', { name: 'exits.studio.ctaTalk' }));
    await waitFor(() => expect(outboundCalls()).toHaveLength(2));
    expect(lastOutboundBody()).toMatchObject({
      target: 'nestlab',
      campaign: 'studio',
      slot: 'exit_studio',
    });
  });

  it('reports the click on the question link of the FAQ', async () => {
    render(await Faq());

    fireEvent.click(screen.getByRole('link', { name: 'faq.ask →' }));

    await waitFor(() => expect(outboundCalls()).toHaveLength(1));
    expect(lastOutboundBody()).toMatchObject({
      target: 'github',
      campaign: 'oss',
      slot: 'faq_ask',
    });
  });

  it('reports the click on a link of the footer that leaves the site', async () => {
    render(await LandingFooter({ locale: 'en' }));

    fireEvent.click(screen.getByRole('link', { name: 'footer.studioNestLab' }));

    await waitFor(() => expect(outboundCalls()).toHaveLength(1));
    expect(lastOutboundBody()).toMatchObject({
      target: 'nestlab.tech',
      campaign: 'studio',
      slot: 'footer',
    });
  });

  it('does not report a link that stays on the site', async () => {
    render(await LandingFooter({ locale: 'en' }));

    fireEvent.click(screen.getByRole('link', { name: 'footer.productLiveDemo' }));

    // The link stays on the site: there is nothing to report, and the
    // arrival is reported by the page the visitor lands on.
    expect(outboundCalls()).toHaveLength(0);
  });
});
