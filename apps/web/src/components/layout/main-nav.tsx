'use client';

import { useState } from 'react';
import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { usePathname } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { UserMenu } from '@/components/auth/UserMenu';
import { LanguageSwitcher } from '@/components/ui/language-switcher';
import { useAuth } from '@/contexts/AuthContext';
import {
  BarChart3,
  BookOpen,
  Building2,
  FileText,
  Heart,
  Menu,
  MessageSquare,
  Moon,
  Search,
  Settings,
  Sun,
  X,
  Globe,
  Users,
  type LucideIcon,
} from 'lucide-react';

const THEME_STORAGE_KEY = 'theme';

// Routes visible in demo mode (auth-required routes are hidden, not locked).
//
// The demo allowlist lives in `src/proxy.ts` (the `demoRoutes` array). It is the
// source of truth for what an anonymous visitor may open without a session, and
// it currently allows:
//
//   '/', '/search', '/city-overview', '/knowledge', '/analytics',
//   '/market-trends', '/cma', '/tools', '/chat', '/agents'
//
// The nav must not advertise a route the proxy would redirect to the login page.
// `/favorites` and `/documents` are in neither list — they need an account and
// stay hidden in demo mode. `/chat` is reachable in demo mode through the proxy
// but is deliberately not advertised here.
const DEMO_VISIBLE_ROUTES = new Set([
  '/search',
  '/city-overview',
  '/knowledge',
  '/analytics',
  '/market-trends',
  '/cma',
  '/tools',
  '/agents',
]);
// Routes always hidden in demo mode
const DEMO_HIDDEN_ROUTES = new Set(['/settings']);

interface RouteConfig {
  href: string;
  label: string;
  icon: LucideIcon;
}

export function MainNav() {
  const pathname = usePathname();
  const t = useTranslations('nav');
  const tCommon = useTranslations('common');
  const { isDemoMode } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const routes: RouteConfig[] = [
    {
      href: '/search',
      label: t('search'),
      icon: Search,
    },
    {
      href: '/favorites',
      label: t('favorites'),
      icon: Heart,
    },
    {
      href: '/documents',
      label: t('documents'),
      icon: FileText,
    },
    {
      href: '/city-overview',
      label: t('cities'),
      icon: Globe,
    },
    {
      href: '/chat',
      label: t('assistant'),
      icon: MessageSquare,
    },
    {
      href: '/analytics',
      label: t('analytics'),
      icon: BarChart3,
    },
    {
      href: '/agents',
      label: t('agents'),
      icon: Users,
    },
    {
      href: '/knowledge',
      label: t('knowledge'),
      icon: BookOpen,
    },
    {
      href: '/settings',
      label: t('settings'),
      icon: Settings,
    },
  ];

  const isActiveRoute = (href: string) => {
    // usePathname from next-intl/navigation returns path without locale prefix
    const currentPath = pathname || '/';
    return currentPath === href || (href !== '/' && currentPath.startsWith(href));
  };

  const isLocked = () => false;
  const isHidden = (href: string) =>
    isDemoMode && (!DEMO_VISIBLE_ROUTES.has(href) || DEMO_HIDDEN_ROUTES.has(href));

  const toggleTheme = () => {
    const isDark = document.documentElement.classList.contains('dark');
    const next = isDark ? 'light' : 'dark';
    window.localStorage.setItem(THEME_STORAGE_KEY, next);
    document.documentElement.classList.toggle('dark', !isDark);
  };

  const visibleRoutes = routes.filter((route) => !isHidden(route.href));

  return (
    <>
      <nav aria-label={t('mainNavigation')} className="flex items-center w-full">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 font-bold text-xl hover:opacity-80 transition-opacity shrink-0 mr-4 md:mr-6"
        >
          <Building2 className="w-6 h-6 text-primary" aria-hidden="true" />
          <span className="hidden sm:inline">AI Estate</span>
        </Link>

        {/* Desktop navigation links */}
        <div className="hidden md:flex items-center justify-center flex-1 space-x-4 lg:space-x-6">
          {visibleRoutes.map((route) => {
            return (
              <Link
                key={route.href}
                href={route.href}
                aria-current={isActiveRoute(route.href) ? 'page' : undefined}
                className={cn(
                  'text-sm font-medium transition-colors hover:text-primary flex items-center gap-x-1.5 whitespace-nowrap',
                  isActiveRoute(route.href) ? 'text-foreground' : 'text-muted-foreground'
                )}
              >
                <route.icon className="w-4 h-4" aria-hidden="true" />
                {route.label}
              </Link>
            );
          })}
        </div>

        {/* Mobile hamburger */}
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="md:hidden ml-auto mr-1"
          onClick={() => setMobileOpen(true)}
          aria-label={t('mainNavigation')}
        >
          <Menu className="h-5 w-5" />
        </Button>

        {/* Right-side controls (desktop) */}
        <div className="hidden md:flex items-center gap-2 shrink-0 ml-4">
          <LanguageSwitcher />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label={tCommon('toggleTheme')}
          >
            <Sun className="h-4 w-4 hidden dark:block" aria-hidden="true" />
            <Moon className="h-4 w-4 block dark:hidden" aria-hidden="true" />
          </Button>
          <UserMenu />
        </div>
      </nav>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute right-0 top-0 bottom-0 w-72 bg-background border-l shadow-xl flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <span className="font-bold text-lg">AI Estate</span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setMobileOpen(false)}
                aria-label={tCommon('close')}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto py-2">
              {visibleRoutes.map((route) => {
                return (
                  <Link
                    key={route.href}
                    href={route.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      'flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors hover:bg-accent',
                      isActiveRoute(route.href)
                        ? 'text-foreground bg-accent/50'
                        : 'text-muted-foreground'
                    )}
                  >
                    <route.icon className="w-5 h-5" aria-hidden="true" />
                    {route.label}
                  </Link>
                );
              })}
            </div>
            <div className="border-t p-4 flex items-center gap-2">
              <LanguageSwitcher />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                aria-label={tCommon('toggleTheme')}
              >
                <Sun className="h-4 w-4 hidden dark:block" aria-hidden="true" />
                <Moon className="h-4 w-4 block dark:hidden" aria-hidden="true" />
              </Button>
              <UserMenu />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
