'use client';

import { useState } from 'react';
import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { Info, Sparkles } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';

export function DemoBanner() {
  const t = useTranslations('demo');
  const { setIsDemoMode } = useAuth();
  const [isDemoMode, setIsDemoModeState] = useState(
    () => process.env.NEXT_PUBLIC_DEMO_MODE === 'true'
  );
  const [hasToggled, setHasToggled] = useState(false);

  const handleToggle = async (value: boolean) => {
    setIsDemoModeState(value);
    setHasToggled(true);
    setIsDemoMode(value);

    try {
      const sessionId = sessionStorage.getItem('demo_session_id') || 'default';
      await fetch('/api/v1/settings/demo', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId,
        },
        body: JSON.stringify({ demo_mode: value }),
      });
    } catch (error) {
      console.error('Failed to toggle demo mode:', error);
    }
  };

  if (!isDemoMode && !hasToggled) return null;

  return (
    <div
      className="bg-primary/10 border-b border-primary/20 text-sm"
      role="status"
      aria-live="polite"
    >
      <div className="container mx-auto flex items-center justify-between px-4 py-2">
        <div className="flex items-center gap-2 text-primary">
          <Info className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>Demo Mode: {isDemoMode ? 'ON' : 'OFF'}</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Switch checked={isDemoMode} onCheckedChange={handleToggle} />
            <span className="text-xs text-primary/80">{isDemoMode ? 'Enabled' : 'Disabled'}</span>
          </div>
          {!isDemoMode && (
            <Button
              variant="ghost"
              size="sm"
              className="text-primary hover:text-primary hover:bg-primary/10 gap-1.5 h-7 text-xs"
              asChild
            >
              <Link href="/auth/register">
                <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
                {t('signUpCta')}
              </Link>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
