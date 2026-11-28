'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { useCapabilities } from '@/hooks/useCapabilities';
import { SettingsPanel, SettingsRow } from '@/components/settings/settings-panel';

/**
 * The identity of the person on this deployment.
 *
 * One thing, so one row: the account the session proved. The address is
 * neither typed in nor kept in the browser - it is the row behind the
 * session token, and the backend resolves it from the token on every
 * request. A field the visitor could fill in would be an assertion, and the
 * backend would not believe it.
 */
export function IdentitySettings({ userEmail }: { userEmail: string | null }) {
  const t = useTranslations('pages.settings.identity');
  const { capabilities } = useCapabilities();

  return (
    <SettingsPanel title={t('title')} description={t('description')}>
      <SettingsRow label={t('emailLabel')} description={t('hint')}>
        {userEmail ? (
          <MonoAnnotation className="text-foreground">{userEmail}</MonoAnnotation>
        ) : (
          <MonoAnnotation>{t('notSignedIn')}</MonoAnnotation>
        )}
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
