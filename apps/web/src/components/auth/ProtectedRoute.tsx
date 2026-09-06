'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { useAuth } from '@/hooks/useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  redirectTo?: string;
}

/**
 * Client-side protected route wrapper.
 *
 * This component checks if the user is authenticated on the client side.
 * If not authenticated, it redirects to the login page.
 *
 * For server-side protection, use the proxy.ts file (Next.js 16 renamed middleware.ts → proxy.ts).
 *
 * @example
 * ```tsx
 * <ProtectedRoute>
 *   <DashboardPage />
 * </ProtectedRoute>
 * ```
 */
export function ProtectedRoute({ children, redirectTo = '/auth/login' }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, isDemoMode } = useAuth();
  const router = useRouter();
  const t = useTranslations('auth');

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !isDemoMode) {
      router.push(redirectTo);
    }
  }, [isAuthenticated, isLoading, router, redirectTo]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">{t('loading')}</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated && !isDemoMode) {
    return null; // Will redirect
  }

  return <>{children}</>;
}
