'use client';

import Link from 'next/link';
import { useTranslations, useLocale } from 'next-intl';
import { ArrowRight, LogIn } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export function HomeCTAs() {
  const t = useTranslations('home');
  const locale = useLocale();
  const { isDemoMode } = useAuth();

  return (
    <div className="flex gap-4">
      <Link
        href={`/${locale}/search`}
        className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-8 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:pointer-events-none disabled:opacity-50"
      >
        {t('startSearching')}
      </Link>
      {isDemoMode ? (
        <Link
          href={`/${locale}/auth/login?redirect=/${locale}/chat`}
          className="inline-flex h-10 items-center justify-center rounded-md border border-input bg-background px-8 text-sm font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:pointer-events-none disabled:opacity-50 gap-2"
        >
          <LogIn className="w-4 h-4" />
          {t('askAssistantDemo')}
        </Link>
      ) : (
        <Link
          href={`/${locale}/chat`}
          className="inline-flex h-10 items-center justify-center rounded-md border border-input bg-background px-8 text-sm font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:pointer-events-none disabled:opacity-50 gap-2"
        >
          {t('askAssistant')} <ArrowRight className="w-4 h-4" />
        </Link>
      )}
    </div>
  );
}
