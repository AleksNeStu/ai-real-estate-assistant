import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['pl', 'en', 'ru', 'de', 'es', 'it', 'pt', 'tr', 'uk'],
  defaultLocale: 'pl',
  localePrefix: 'always',
  /**
   * The middleware's own hreflang header is switched off on purpose.
   *
   * Next-intl resolves it against the REQUEST's host. Behind a proxy that is
   * the origin's internal name: the demo answered with
   * `http://141.147.62.106.sslip.io:3100/pl` while the page's own alternates
   * carried `https://realty.kittray.com/pl`. A crawler that reads the HTTP
   * `Link` header therefore saw a second hreflang cluster on an address
   * nobody should see - and the two clusters disagreed about the canonical.
   *
   * The application publishes its own absolute alternates in the locale
   * layout (see `@/lib/metadata`), so the header is redundant: one cluster,
   * on the public address.
   */
  alternateLinks: false,
});
