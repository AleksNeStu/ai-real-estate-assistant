'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { LogOut, User, Settings, ChevronDown } from 'lucide-react';

/**
 * User menu component that shows user info and logout option.
 * Displays when user is authenticated, shows login/register buttons when not.
 */
export function UserMenu() {
  const { user, isAuthenticated, isLoading, isDemoMode, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuItemsRef = useRef<(HTMLElement | null)[]>([]);
  const locale = useLocale();
  const t = useTranslations('auth');

  const setMenuItemRef = useCallback(
    (index: number) => (el: HTMLElement | null) => {
      menuItemsRef.current[index] = el;
    },
    []
  );

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus management: trap focus in menu when open
  useEffect(() => {
    if (isOpen) {
      // Focus the first menu item when menu opens
      const firstItem = menuItemsRef.current[0];
      firstItem?.focus();
    }
  }, [isOpen]);

  const handleMenuKeyDown = (e: React.KeyboardEvent) => {
    const items = menuItemsRef.current.filter(Boolean);
    const currentIndex = items.indexOf(document.activeElement as HTMLElement);

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        if (currentIndex < items.length - 1) {
          items[currentIndex + 1]?.focus();
        } else {
          items[0]?.focus();
        }
        break;
      case 'ArrowUp':
        e.preventDefault();
        if (currentIndex > 0) {
          items[currentIndex - 1]?.focus();
        } else {
          items[items.length - 1]?.focus();
        }
        break;
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        triggerRef.current?.focus();
        break;
      case 'Tab':
        setIsOpen(false);
        break;
    }
  };

  const handleLogout = async () => {
    setIsOpen(false);
    await logout();
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center gap-2">
        <div className="h-8 w-20 bg-muted animate-pulse rounded" aria-hidden="true" />
      </div>
    );
  }

  // Not authenticated - show login/register buttons
  if (!isAuthenticated || !user) {
    if (isDemoMode) {
      return (
        <div className="flex items-center gap-2">
          <Link href={`/${locale}/auth/login`}>
            <Button size="sm">{t('signIn')}</Button>
          </Link>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-2">
        <Link href={`/${locale}/auth/login`}>
          <Button variant="ghost" size="sm">
            {t('signIn')}
          </Button>
        </Link>
        <Link href={`/${locale}/auth/register`}>
          <Button size="sm">{t('signUp')}</Button>
        </Link>
      </div>
    );
  }

  // Authenticated - show user menu
  const initials = user.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : user.email.slice(0, 2).toUpperCase();

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-full px-3 py-1.5 hover:bg-accent transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label={t('userMenu', { defaultValue: 'User menu' })}
      >
        <div className="flex items-center justify-center h-8 w-8 rounded-full bg-primary text-primary-foreground text-sm font-medium">
          {initials}
        </div>
        <span className="hidden sm:block text-sm font-medium max-w-[100px] truncate">
          {user.full_name || user.email.split('@')[0]}
        </span>
        <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      </button>

      {isOpen && (
        <div
          className="absolute right-0 mt-2 w-56 rounded-md border bg-popover shadow-lg z-50"
          role="menu"
          aria-label={t('userMenu', { defaultValue: 'User menu' })}
          onKeyDown={handleMenuKeyDown}
        >
          <div className="p-3 border-b">
            <p className="text-sm font-medium">{user.full_name || t('user')}</p>
            <p className="text-xs text-muted-foreground truncate">{user.email}</p>
          </div>
          <div className="p-1" role="group">
            <Link
              ref={setMenuItemRef(0)}
              href={`/${locale}/settings`}
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-2 w-full px-3 py-2 text-sm rounded-sm hover:bg-accent transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              role="menuitem"
            >
              <User className="h-4 w-4" aria-hidden="true" />
              {t('profile')}
            </Link>
            <Link
              ref={setMenuItemRef(1)}
              href={`/${locale}/settings`}
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-2 w-full px-3 py-2 text-sm rounded-sm hover:bg-accent transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              role="menuitem"
            >
              <Settings className="h-4 w-4" aria-hidden="true" />
              {t('settings')}
            </Link>
          </div>
          <div className="p-1 border-t" role="group">
            <button
              ref={setMenuItemRef(2)}
              type="button"
              onClick={handleLogout}
              className="flex items-center gap-2 w-full px-3 py-2 text-sm rounded-sm hover:bg-accent transition-colors text-destructive focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              role="menuitem"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              {t('signOut')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
