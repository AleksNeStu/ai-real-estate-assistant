import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';

import { languageAlternates } from '@/lib/metadata';
import { absoluteUrl } from '@/lib/site';

import { CompareTable } from '@/components/landing/compare-table';
import { DataCoverage } from '@/components/landing/data-coverage';
import { DemoSection } from '@/components/landing/demo-section';
import { ExitCards } from '@/components/landing/exit-cards';
import { Faq } from '@/components/landing/faq';
import { LandingFooter } from '@/components/landing/footer';
import { FeatureLedger } from '@/components/landing/feature-ledger';
import { Hero } from '@/components/landing/hero';
import { StudioStrip } from '@/components/landing/studio-strip';

/**
 * The landing of the open-source version.
 *
 * It is the root of the public address, so it has to do two jobs at once:
 * explain what the thing is, and get the visitor into it. The demo needs no
 * account, so the deepest ask on the page is an e-mail address - and the
 * three ways forward are all open.
 */
/**
 * The metadata of the landing page.
 *
 * The landing is the one page every visitor arrives at, and the one page
 * whose address has to be unambiguous: it is the root of the public domain,
 * and it exists in nine languages. It declares its own canonical and its own
 * hreflang cluster, because the layout - which every route inherits - cannot
 * know which route it is rendering.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'pages' });
  const title = t('home.title' as never);
  const description = t('home.description' as never);
  const url = absoluteUrl(`/${locale}`);

  return {
    title,
    description,
    alternates: {
      canonical: url,
      languages: languageAlternates('/'),
    },
    openGraph: {
      title,
      description,
      url,
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
  };
}

export default async function Home({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('landing');

  const limits = [1, 2, 3];

  return (
    <div className="flex flex-col">
      <Hero locale={locale} />
      <DemoSection locale={locale} />
      <FeatureLedger locale={locale} />
      <DataCoverage />

      <section className="mx-auto max-w-[1248px] px-6 pt-24">
        <div className="grid grid-cols-1 gap-14 lg:grid-cols-[360px_minmax(0,1fr)]">
          <h2 className="text-section font-semibold">{t('limits.title')}</h2>
          <dl className="m-0 border-t border-foreground">
            {limits.map((index) => (
              <div
                key={index}
                className="grid grid-cols-1 items-baseline gap-6 border-b border-border py-[18px] sm:grid-cols-[230px_minmax(0,1fr)]"
              >
                <dt className="font-semibold">{t(`limits.${index}.title`)}</dt>
                <dd className="m-0 text-muted-foreground">{t(`limits.${index}.text`)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <ExitCards />
      <CompareTable />
      <StudioStrip />
      <Faq />
      <LandingFooter locale={locale} />
    </div>
  );
}
