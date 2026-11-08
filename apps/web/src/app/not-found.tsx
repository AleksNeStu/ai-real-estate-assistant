import Link from 'next/link';
import { Home, Search } from 'lucide-react';
import { getTranslations } from 'next-intl/server';

/**
 * Custom 404 page (Task #68).
 *
 * The copy comes from the catalogue, so the page reads in the language of the
 * site even when it is rendered outside a `[locale]` segment.
 */
export default async function NotFound() {
  const t = await getTranslations('error');
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
      <h1 className="text-6xl font-bold text-muted-foreground/30 mb-4">404</h1>
      <h2 className="text-xl font-semibold mb-2">{t('notFound')}</h2>
      <p className="text-muted-foreground mb-6 max-w-md">{t('pageNotFoundDescription')}</p>
      <div className="flex gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Home className="h-4 w-4" />
          {t('goHome')}
        </Link>
        <Link
          href="/search"
          className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
        >
          <Search className="h-4 w-4" />
          {t('searchProperties')}
        </Link>
      </div>
    </div>
  );
}
