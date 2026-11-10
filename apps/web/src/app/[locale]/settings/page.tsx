'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { AccountGate } from '@/components/shell/gate';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import { ErrorState } from '@/components/ui/states';
import { IdentitySettings } from '@/components/settings/identity-settings';
import { ModelSettings } from '@/components/settings/model-settings';
import { TaskModelSettings } from '@/components/settings/task-model-settings';
import { ModelCatalogue, LocalRuntimeNote } from '@/components/settings/model-catalogue';
import { NotificationSettings } from '@/components/settings/notification-settings';
import { ProfileSettings } from '@/components/settings/profile-settings';
import { PrivacySettings } from '@/components/settings/privacy-settings';
import { getModelsCatalog, ApiError } from '@/lib/api';
import type { ModelProviderCatalog } from '@/lib/types';

/**
 * The settings screen.
 *
 * Five things about the account, and only one of them is on the screen at a
 * time: the tab strip is a row of labels with a rule under the one that is
 * open - the same shape the analytics console draws.
 *
 * The Models tab is the instrument of the route: the per-task picker over
 * the catalogue, the catalogue itself with its context size and its price
 * per million tokens, and the probe that says whether a provider answers.
 */

const TABS = ['identity', 'models', 'notifications', 'profile', 'privacy'] as const;
type Tab = (typeof TABS)[number];

export default function SettingsPage() {
  const t = useTranslations('pages.settings');
  const tCommon = useTranslations('common');
  const [tab, setTab] = useState<Tab>('models');
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<ModelProviderCatalog[] | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogRefreshing, setCatalogRefreshing] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | undefined>(undefined);

  const fetchCatalog = async (mode: 'initial' | 'refresh' = 'initial') => {
    if (mode === 'initial') {
      setCatalogLoading(true);
    } else {
      setCatalogRefreshing(true);
    }
    setCatalogError(null);
    setRequestId(undefined);
    try {
      const data = await getModelsCatalog();
      setCatalog(data);
    } catch (err) {
      let msg = t('models.loadFailed');
      let reqId: string | undefined = undefined;

      if (err instanceof ApiError) {
        msg = err.message;
        reqId = err.request_id;
      } else if (err instanceof Error) {
        msg = err.message;
      }

      if (mode === 'initial') {
        setCatalog(null);
      }
      setCatalogError(msg);
      setRequestId(reqId);
    } finally {
      if (mode === 'initial') {
        setCatalogLoading(false);
      } else {
        setCatalogRefreshing(false);
      }
    }
  };

  useEffect(() => {
    const email = window.localStorage.getItem('userEmail');
    setUserEmail(email && email.trim() ? email.trim() : null);
    fetchCatalog('initial');
  }, []);

  const renderPanel = () => {
    switch (tab) {
      case 'identity':
        return <IdentitySettings onChange={(email) => setUserEmail(email)} />;
      case 'models':
        return (
          <div className="flex flex-col gap-8">
            <TaskModelSettings catalog={catalog} userEmail={userEmail} />
            <ModelSettings catalog={catalogLoading ? null : catalog} userEmail={userEmail} />
            {catalogLoading ? (
              <MonoAnnotation>{t('loadingModelCatalog')}</MonoAnnotation>
            ) : catalogError ? (
              <ErrorState
                title={t('models.failedToLoadCatalog')}
                description={catalogError}
                onRetry={() => fetchCatalog('initial')}
                retryLabel={tCommon('retry')}
              />
            ) : catalog && catalog.length > 0 ? (
              <>
                <ModelCatalogue catalog={catalog} />
                <LocalRuntimeNote />
              </>
            ) : (
              <MonoAnnotation>{t('models.noModels')}</MonoAnnotation>
            )}
          </div>
        );
      case 'notifications':
        return <NotificationSettings userEmail={userEmail} />;
      case 'profile':
        return <ProfileSettings userEmail={userEmail} />;
      case 'privacy':
        return <PrivacySettings userEmail={userEmail} />;
      default:
        return null;
    }
  };

  return (
    <AccountGate route="settings">
      <div className="mx-auto flex max-w-[1100px] flex-col gap-5 px-6 py-7">
        <PageHeader
          title={t('title')}
          description={t('description')}
          actions={
            tab === 'models' ? (
              <button
                type="button"
                onClick={() => fetchCatalog(catalog ? 'refresh' : 'initial')}
                disabled={catalogLoading || catalogRefreshing}
                className="inline-flex h-[34px] items-center rounded-md border border-border bg-transparent px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-muted disabled:opacity-60"
              >
                {catalogRefreshing ? t('models.refreshing') : t('models.refreshCatalog')}
              </button>
            ) : null
          }
        />

        <div
          role="tablist"
          aria-label={t('tabs.label')}
          className="flex flex-wrap gap-x-6 gap-y-1 border-b border-border"
        >
          {TABS.map((id) => {
            const isActive = id === tab;
            return (
              <button
                key={id}
                type="button"
                role="tab"
                id={`settings-tab-${id}`}
                aria-selected={isActive}
                aria-controls="settings-panel"
                onClick={() => setTab(id)}
                className={[
                  '-mb-px border-b-2 py-2.5 text-[14px] font-medium transition-colors',
                  isActive
                    ? 'border-foreground text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground',
                ].join(' ')}
              >
                {t(`tabs.${id}`)}
              </button>
            );
          })}
        </div>

        <div id="settings-panel" role="tabpanel" aria-labelledby={`settings-tab-${tab}`}>
          {renderPanel()}
        </div>

        {requestId ? <MonoAnnotation>request_id={requestId}</MonoAnnotation> : null}
      </div>
    </AccountGate>
  );
}
