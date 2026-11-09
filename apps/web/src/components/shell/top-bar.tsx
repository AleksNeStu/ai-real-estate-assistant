'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { usePathname } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { LanguageSwitcher } from '@/components/ui/language-switcher';
import { UserMenu } from '@/components/auth/UserMenu';
import { withUtm } from '@/lib/utm';

const THEME_STORAGE_KEY = 'theme';

/**
 * The routes an anonymous visitor may open.
 *
 * The list mirrors the `demoRoutes` allowlist in `src/proxy.ts` — the proxy is
 * the source of truth for what the deployment answers without a session. The
 * bar must not advertise a route the proxy would redirect to the login page,
 * so the two are kept in step: the proxy allows twelve routes, the bar links
 * to eleven of them (the twelfth is the landing itself).
 */
const DEMO_VISIBLE_ROUTES = new Set([
  '/search',
  '/chat',
  '/city-overview',
  '/knowledge',
  '/analytics',
  '/market-trends',
  '/cma',
  '/tools',
  '/agents',
  '/valuation',
  '/showcase',
]);

/** Routes that stay hidden in demo mode even though the proxy allows them. */
const DEMO_HIDDEN_ROUTES = new Set(['/settings']);

/**
 * The mark of the product: a rounded plate, a chevron and a dot.
 *
 * The colours come from the current theme (`currentColor` for the plate, the
 * page background for the cut-out), so the mark inverts with the dark theme
 * without a second asset.
 */
function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 512 512"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <rect width="512" height="512" rx="112" fill="currentColor" />
      <path
        d="M136 296 L256 176 L376 296"
        fill="none"
        stroke="hsl(var(--background))"
        strokeWidth="40"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="256" cy="360" r="36" fill="hsl(var(--background))" />
    </svg>
  );
}

function isActiveRoute(pathname: string, href: string): boolean {
  return pathname === href || (href !== '/' && pathname.startsWith(`${href}/`));
}

/**
 * The top bar of the application.
 *
 * Two variants, one component:
 *
 * - the landing bar (the locale root) carries the five section anchors of
 *   the landing page, the GitHub link and the way into the app;
 * - the app bar carries the seven app links, the "More" menu, the demo pill,
 *   the locale switcher, the theme toggle and the account menu.
 */
export function TopBar() {
  const pathname = usePathname() || '/';
  const t = useTranslations('shell');
  const tNav = useTranslations('nav');
  const [mobileOpen, setMobileOpen] = useState(false);

  const isLanding = pathname === '/';

  const appLinks = [
    { href: '/search', label: t('nav.search') },
    { href: '/chat', label: t('nav.assistant') },
    { href: '/city-overview', label: t('nav.cities') },
    { href: '/analytics', label: t('nav.analytics') },
    { href: '/tools', label: t('nav.tools') },
    { href: '/agents', label: t('nav.agents') },
    { href: '/knowledge', label: t('nav.knowledge') },
  ];

  const moreLinks = [
    { href: '/market-trends', label: t('nav.marketTrends'), route: '/market-trends' },
    { href: '/cma', label: t('nav.cma'), route: '/cma' },
    { href: '/valuation', label: t('nav.valuation'), route: '/valuation' },
    { href: '/showcase', label: t('nav.showcase'), route: '/showcase' },
  ];

  const landingLinks = [
    { href: '#features', label: t('landing.features') },
    { href: '#data', label: t('landing.data') },
    { href: '#open', label: t('landing.openSource') },
    { href: '#compare', label: t('landing.compare') },
    { href: '#faq', label: t('landing.faq') },
  ];

  const toggleTheme = () => {
    const isDark = document.documentElement.classList.contains('dark');
    const next = isDark ? 'light' : 'dark';
    window.localStorage.setItem(THEME_STORAGE_KEY, next);
    document.documentElement.classList.toggle('dark', !isDark);
  };

  const githubUrl = withUtm('https://github.com/AleksNeStu/ai-real-estate-assistant', {
    medium: 'landing',
    campaign: 'oss',
    content: 'nav_github',
  });

  return (
    <header className="sticky top-0 z-40 h-14 border-b border-border bg-background">
      <div className="mx-auto flex h-full max-w-[1248px] items-center gap-7 px-6">
        <Link
          href="/"
          className="flex shrink-0 items-center gap-2.5 text-[15px] font-semibold text-foreground"
        >
          <BrandMark className="text-foreground" />
          <span>{t('brand')}</span>
        </Link>

        {isLanding ? (
          <nav
            aria-label={tNav('mainNavigation')}
            className="hidden items-center gap-5 text-[14px] font-medium lg:flex"
          >
            {landingLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="py-[17px] text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
          </nav>
        ) : (
          <nav
            aria-label={tNav('mainNavigation')}
            className="hidden items-center gap-5 text-[14px] font-medium lg:flex"
          >
            {appLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                aria-current={isActiveRoute(pathname, link.href) ? 'page' : undefined}
                className={cn(
                  'py-[17px] whitespace-nowrap transition-colors',
                  isActiveRoute(pathname, link.href)
                    ? 'text-foreground shadow-[inset_0_-2px_0_hsl(var(--foreground))]'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {link.label}
              </Link>
            ))}
            <MoreMenu links={moreLinks} label={t('nav.more')} />
          </nav>
        )}

        <div className="ml-auto flex items-center gap-1.5">
          {!isLanding && (
            <span
              title={t('demoPill')}
              className="mr-1 hidden h-7 items-center gap-2 rounded-full border border-border px-2.5 text-[12px] text-muted-foreground xl:inline-flex"
            >
              <span className="size-1.5 rounded-full bg-success" aria-hidden="true" />
              {t('demoPill')}
            </span>
          )}

          <LanguageSwitcher />

          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label={t('toggleTheme')}
            className="size-8"
          >
            <SunIcon className="hidden dark:block" />
            <MoonIcon className="block dark:hidden" />
          </Button>

          {isLanding ? (
            <>
              <a
                href={githubUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="hidden h-8 items-center gap-2 rounded-md border border-border px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-accent sm:inline-flex"
              >
                <GithubIcon className="size-[15px]" />
                {t('github')}
              </a>
              <Link
                href="/search"
                className="hidden h-8 items-center rounded-md border border-border px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-accent sm:inline-flex"
              >
                {t('openApp')}
              </Link>
            </>
          ) : (
            <UserMenu />
          )}

          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => setMobileOpen((open) => !open)}
            aria-label={t('menu')}
            aria-expanded={mobileOpen}
            className="size-8 lg:hidden"
          >
            <MenuIcon className={cn('transition-transform', mobileOpen && 'rotate-90')} />
          </Button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-b border-border bg-background lg:hidden">
          <div className="mx-auto flex max-w-[1248px] flex-col px-6 py-4">
            {isLanding
              ? landingLinks.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileOpen(false)}
                    className="py-2 text-[14px] font-medium text-muted-foreground"
                  >
                    {link.label}
                  </a>
                ))
              : appLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileOpen(false)}
                    className="py-2 text-[14px] font-medium text-muted-foreground"
                  >
                    {link.label}
                  </Link>
                ))}
          </div>
        </div>
      )}
    </header>
  );
}

/**
 * The "More" menu of the app bar.
 *
 * Every row carries the route it opens, in the mono face — the route is part
 * of the promise the row makes, so a visitor can see where a link goes before
 * following it.
 */
function MoreMenu({
  links,
  label,
}: {
  links: { href: string; label: string; route: string }[];
  label: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="true"
        className="flex items-center gap-1 py-[17px] text-[14px] font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        {label}
        <ChevronIcon className={cn('size-3 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute left-0 top-[30px] z-50 flex w-[220px] flex-col rounded-lg border border-border bg-background p-1 shadow-[0_8px_24px_rgb(9_9_11/0.10)]">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setOpen(false)}
              className="flex items-center justify-between gap-3 rounded-md px-2.5 py-2 text-[14px] text-foreground transition-colors hover:bg-muted"
            >
              <span>{link.label}</span>
              <span className="font-mono text-[11px] text-muted-foreground">{link.route}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

/* The icons are drawn here so the bar does not pull a whole icon set in. */

function SunIcon({ className }: { className?: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}

function MoonIcon({ className }: { className?: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
  );
}

function MenuIcon({ className }: { className?: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function GithubIcon({ className }: { className?: string }) {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.4 5.4 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}
