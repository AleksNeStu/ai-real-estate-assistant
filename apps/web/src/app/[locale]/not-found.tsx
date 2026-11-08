import Link from 'next/link';
import { Home, Search } from 'lucide-react';
import { getTranslations } from 'next-intl/server';

/**
 * Custom 404 page (Task #68).
 *
 * This copy lives in the [locale] segment so it can use the catalogue; the
 * root `app/not-found.tsx` stays in English because it renders outside the
 * intl provider.
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
          <Home className="w-4 h-4" />
          {t('goHome')}
        </Link>
        <Link
          href="/search"
          className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
        >
          <Search className="w-4 h-4" />
          {t('searchProperties')}
        </Link>
      </div>
    </div>
  );
}
