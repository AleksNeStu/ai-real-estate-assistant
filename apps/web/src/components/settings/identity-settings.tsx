'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { useCapabilities } from '@/hooks/useCapabilities';
import { SettingsPanel, SettingsRow } from '@/components/settings/settings-panel';
import { Input } from '@/components/ui/input';

const USER_EMAIL_STORAGE_KEY = 'userEmail';

function isValidEmail(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) return false;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed);
}

/**
 * The identity of the person on this deployment.
 *
 * One thing, so one row: the address the server scopes the account by. The
 * address lives in this browser and travels as a header - the row says so,
 * because the reader needs to know where it is.
 */
export function IdentitySettings({ onChange }: { onChange?: (userEmail: string | null) => void }) {
  const t = useTranslations('pages.settings.identity');
  const { capabilities } = useCapabilities();
  const [email, setEmail] = useState(() => {
    if (typeof window === 'undefined') return '';
    return window.localStorage.getItem(USER_EMAIL_STORAGE_KEY) || '';
  });
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const normalized = useMemo(() => email.trim(), [email]);
  const valid = useMemo(() => (normalized ? isValidEmail(normalized) : true), [normalized]);

  const handleSave = () => {
    setError(null);
    setSaved(null);

    if (normalized && !isValidEmail(normalized)) {
      setError(t('invalidEmail'));
      return;
    }

    if (!normalized) {
      window.localStorage.removeItem(USER_EMAIL_STORAGE_KEY);
      setSaved(t('cleared'));
      onChange?.(null);
      return;
    }

    window.localStorage.setItem(USER_EMAIL_STORAGE_KEY, normalized);
    setSaved(t('saved'));
    onChange?.(normalized);
  };

  return (
    <SettingsPanel title={t('title')} description={t('description')}>
      <SettingsRow
        label={t('emailLabel')}
        description={t('hint', { header: 'X-User-Email' })}
        action={
          <>
            {saved ? <MonoAnnotation tone="success">{saved}</MonoAnnotation> : null}
            {error ? <MonoAnnotation tone="destructive">{error}</MonoAnnotation> : null}
            <button
              type="button"
              onClick={handleSave}
              className="rounded-sm text-app font-medium text-foreground transition-colors hover:underline"
            >
              {t('save')}
            </button>
          </>
        }
      >
        <Input
          id="settings_user_email"
          type="email"
          aria-label={t('emailLabel')}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          aria-invalid={!valid}
          className="max-w-[360px]"
        />
      </SettingsRow>

      <SettingsRow
        label={t('methodsLabel')}
        description={t('methodsDesc')}
      >
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          {capabilities?.auth.jwt_enabled ? (
            <MonoAnnotation className="text-foreground">{t('methodPassword')}</MonoAnnotation>
          ) : null}
          {capabilities?.auth.oauth.google ? (
            <MonoAnnotation className="text-foreground">Google</MonoAnnotation>
          ) : null}
          {capabilities?.auth.oauth.apple ? (
            <MonoAnnotation className="text-foreground">Apple</MonoAnnotation>
          ) : null}
        </div>
      </SettingsRow>
    </SettingsPanel>
  );
}
