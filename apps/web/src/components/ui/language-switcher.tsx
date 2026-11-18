'use client';

import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter } from '@/i18n/navigation';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Globe } from 'lucide-react';
import { locales, localeNames, localeFlags, type Locale } from '@/i18n/config';

export function LanguageSwitcher() {
  const locale = useLocale() as Locale;
  const t = useTranslations('common');
  const pathname = usePathname();
  const router = useRouter();

  const switchLocale = (newLocale: Locale) => {
    // Store preference in cookie before navigation
    const maxAge = 365 * 24 * 60 * 60; // 1 year
    // eslint-disable-next-line react-hooks/immutability -- cookie setting is a side effect needed for locale persistence
    document.cookie = `NEXT_LOCALE=${newLocale};path=/;max-age=${maxAge};SameSite=Lax`;

    // Use next-intl's router.replace with locale override for proper context switch
    router.replace(pathname, { locale: newLocale });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          // The name carries the code the button shows: a name that leaves
          // out the visible text is a name a reader cannot match to what is
          // on the screen. The code is not in brackets - a name in brackets
          // reads as an aside, and an aside is not the text on the screen.
          aria-label={`${t('changeLanguage')}: ${locale}`}
          data-testid="language-switcher"
          className="gap-1 px-2 text-xs font-medium uppercase"
        >
          <Globe className="w-3.5 h-3.5" aria-hidden="true" />
          {locale}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {locales.map((loc) => (
          <DropdownMenuItem
            key={loc}
            onClick={() => switchLocale(loc)}
            className={loc === locale ? 'bg-accent' : ''}
            aria-current={loc === locale ? 'true' : undefined}
          >
            <span className="mr-2">{localeFlags[loc]}</span>
            {localeNames[loc]}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
