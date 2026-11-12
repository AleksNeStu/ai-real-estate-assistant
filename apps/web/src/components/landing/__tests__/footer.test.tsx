import { render, screen } from '@testing-library/react';

import { LandingFooter } from '@/components/landing/footer';

// The footer is a server component: it reads the catalogue through
// next-intl/server, whose server build is ESM and cannot be loaded by the
// test runtime. The catalogue is not what this test is about.
jest.mock('next-intl/server', () => ({
  getTranslations: jest.fn(async () => (key: string) => key),
}));

// The build metadata reads the live deployment; it is not what this test is
// about.
jest.mock('@/components/layout/build-metadata', () => ({
  BuildMetadata: () => null,
}));

/**
 * The footer of the landing.
 *
 * The Google brand verification asks that the home page links to the privacy
 * policy and the terms of service - the consent screen carries both links,
 * and the page they point at has to be reachable from the page the reviewer
 * lands on. The two documents exist; this test says that the home page
 * actually links to them.
 */
describe('the landing footer', () => {
  it('links the privacy policy and the terms of service', async () => {
    render(await LandingFooter({ locale: 'en' }));

    const privacy = screen.getByRole('link', { name: 'footer.privacy' });
    expect(privacy).toHaveAttribute('href', expect.stringContaining('/en/privacy'));

    const terms = screen.getByRole('link', { name: 'footer.terms' });
    expect(terms).toHaveAttribute('href', expect.stringContaining('/en/terms'));
  });
});
