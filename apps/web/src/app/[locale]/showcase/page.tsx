import { getTranslations } from 'next-intl/server';
import { Code2, Star, Building2, Quote } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import type { Metadata } from 'next';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    title: 'Showcase · Built With This',
    description:
      'Forks, real-world deployments, and case studies of AI Real Estate Assistant.',
    alternates: {
      canonical: `/${locale}/showcase`,
    },
  };
}

/**
 * /<locale>/showcase — public-facing social-proof page.
 *
 * Currently a placeholder. Two sections render an explicit empty state
 * ("no forks or quotes yet — be the first") so the route is reachable
 * from external sources (Show HN thread replies, Product Hunt, Reddit
 * posts) without showing fake data.
 *
 * Intended future content:
 *  - Forks: pull from GitHub API (`repos/AleksNeStu/ai-real-estate-assistant/forks`)
 *    once the repo has > 0 forks and operator authorizes the public listing.
 *    Filter out low-quality forks (no commits, archived, etc.).
 *  - Companies: opt-in testimonials from operators who deployed this stack
 *    in production. Requires explicit permission per Rule 281 (no internal
 *    infra disclosure).
 *  - Quotes: GitHub issue / PR comments from users, or tweet quotes (with
 *    permission) — never fabricated.
 */
export default async function ShowcasePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations('showcase');

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="flex flex-col space-y-12 max-w-4xl mx-auto">
        {/* Hero */}
        <header className="flex flex-col items-center text-center space-y-3">
          <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
            {t('heroTitle')}
          </h1>
          <p className="text-muted-foreground md:text-lg max-w-2xl">
            {t('heroSubtitle')}
          </p>
        </header>

        {/* Forks / Built With This */}
        <section aria-labelledby="forks-heading" className="space-y-4">
          <div className="flex items-center gap-2">
            <Code2 className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
            <h2
              id="forks-heading"
              className="text-2xl font-semibold tracking-tight"
            >
              {t('forksTitle')}
            </h2>
          </div>
          <Card>
            <CardContent className="pt-6 text-center text-muted-foreground">
              <p className="mb-3">{t('forksEmpty')}</p>
              <p className="text-sm">
                {t('forksEmptyHelper')}
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Companies / Production Deployments */}
        <section aria-labelledby="companies-heading" className="space-y-4">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
            <h2
              id="companies-heading"
              className="text-2xl font-semibold tracking-tight"
            >
              {t('companiesTitle')}
            </h2>
          </div>
          <Card>
            <CardContent className="pt-6 text-center text-muted-foreground">
              <p className="mb-3">{t('companiesEmpty')}</p>
              <p className="text-sm">{t('companiesEmptyHelper')}</p>
            </CardContent>
          </Card>
        </section>

        {/* Quotes / Testimonials */}
        <section aria-labelledby="quotes-heading" className="space-y-4">
          <div className="flex items-center gap-2">
            <Quote className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
            <h2
              id="quotes-heading"
              className="text-2xl font-semibold tracking-tight"
            >
              {t('quotesTitle')}
            </h2>
          </div>
          <Card>
            <CardContent className="pt-6 text-center text-muted-foreground">
              <p className="mb-3">{t('quotesEmpty')}</p>
              <p className="text-sm">{t('quotesEmptyHelper')}</p>
            </CardContent>
          </Card>
        </section>

        {/* CTA — star the repo */}
        <section className="text-center space-y-3 py-8 border-t">
          <h2 className="text-2xl font-semibold tracking-tight">
            {t('ctaTitle')}
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            {t('ctaSubtitle')}
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Button asChild>
              <Link
                href="https://github.com/AleksNeStu/ai-real-estate-assistant"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Star className="h-4 w-4 mr-2" aria-hidden="true" />
                {t('ctaStar')}
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href={`/${locale}/chat`}>{t('ctaTryDemo')}</Link>
            </Button>
          </div>
        </section>
      </div>
    </div>
  );
}