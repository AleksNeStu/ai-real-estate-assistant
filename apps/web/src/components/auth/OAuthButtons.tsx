'use client';

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { oauthLogin } from '@/lib/auth';
import { getCapabilities } from '@/lib/api';

type OAuthProvider = 'google' | 'apple';

interface OAuthButtonsProps {
  isLoading?: boolean;
  className?: string;
}

/**
 * The Google and Apple sign-in buttons.
 *
 * The buttons used to be rendered unconditionally: a visitor on a deployment
 * without OAuth clicked Google, got a 403 and a toast carrying the raw API
 * string "Google OAuth is not enabled". The backend knows which providers are
 * configured, so the buttons are rendered only for those, and a failed call
 * reports a sentence instead of the API detail.
 */
export function OAuthButtons({ isLoading = false, className }: OAuthButtonsProps) {
  const [isRedirecting, setIsRedirecting] = useState<OAuthProvider | null>(null);
  const [enabledProviders, setEnabledProviders] = useState<OAuthProvider[]>([]);
  const t = useTranslations('auth');

  useEffect(() => {
    let cancelled = false;

    getCapabilities()
      .then((capabilities) => {
        if (cancelled) return;
        const providers: OAuthProvider[] = [];
        if (capabilities.auth.oauth.google) providers.push('google');
        if (capabilities.auth.oauth.apple) providers.push('apple');
        setEnabledProviders(providers);
      })
      .catch(() => {
        // The capability endpoint is unreachable. Assume that no provider is
        // configured rather than offering a button that cannot work.
        if (!cancelled) setEnabledProviders([]);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleOAuthLogin = async (provider: OAuthProvider) => {
    setIsRedirecting(provider);
    try {
      await oauthLogin(provider);
    } catch {
      // The backend detail ("Google OAuth is not enabled") is not something a
      // visitor can act on — report it in the words of the interface.
      toast.error(t('oauth.failed'));
      setIsRedirecting(null);
    }
  };

  if (enabledProviders.length === 0) {
    return null;
  }

  const showGoogle = enabledProviders.includes('google');
  const showApple = enabledProviders.includes('apple');

  return (
    <div className={className}>
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            {t('login.orContinueWith')}
          </span>
        </div>
      </div>
      <div className="flex gap-2 mt-4">
        {showGoogle && (
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => handleOAuthLogin('google')}
            disabled={isLoading || isRedirecting !== null}
          >
            {isRedirecting === 'google' ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <svg
                className="mr-2 h-4 w-4"
                viewBox="0 0 24 24"
                aria-hidden="true"
                data-testid="google-icon"
              >
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"
                  fill="#EA4335"
                />
              </svg>
            )}
            Google
          </Button>
        )}
        {showApple && (
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => handleOAuthLogin('apple')}
            disabled={isLoading || isRedirecting !== null}
          >
            {isRedirecting === 'apple' ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <svg
                className="mr-2 h-4 w-4"
                viewBox="0 0 24 24"
                aria-hidden="true"
                fill="currentColor"
                data-testid="apple-icon"
              >
                <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
              </svg>
            )}
            Apple
          </Button>
        )}
      </div>
    </div>
  );
}
