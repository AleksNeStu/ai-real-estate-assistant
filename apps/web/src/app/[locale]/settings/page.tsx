'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { RefreshCw, AlertCircle, Loader2, Database, Sparkles } from 'lucide-react';
import { IdentitySettings } from '@/components/settings/identity-settings';
import { ModelSettings } from '@/components/settings/model-settings';
import { TaskModelSettings } from '@/components/settings/task-model-settings';
import { NotificationSettings } from '@/components/settings/notification-settings';
import { ProfileSettings } from '@/components/settings/profile-settings';
import { PrivacySettings } from '@/components/settings/privacy-settings';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/ui/page-header';
import { getModelsCatalog, testModelRuntime, ApiError } from '@/lib/api';
import type { ModelProviderCatalog } from '@/lib/types';

function formatMoneyPer1m(value: number, currency: string): string {
  if (!Number.isFinite(value)) return '—';
  return `${currency} ${value.toFixed(2)}`;
}

// Skeleton component for loading state
function CatalogSkeleton() {
  return (
    <div className="grid gap-6">
      {[1, 2, 3].map((i) => (
        <Card key={i} className="animate-pulse">
          <CardHeader>
            <div className="h-6 bg-muted rounded w-1/3 mb-2" />
            <div className="h-4 bg-muted rounded w-2/3" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="h-10 bg-muted rounded" />
              <div className="h-32 bg-muted rounded" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ModelCatalogComparisonTable({
  catalog,
  onRuntimeTest,
  runtimeTests,
}: {
  catalog: ModelProviderCatalog[];
  onRuntimeTest: (providerName: string) => void;
  runtimeTests: Record<
    string,
    { loading: boolean; status: 'success' | 'error'; message: string; availableModels: string[] }
  >;
}) {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');

  return (
    <div className="grid gap-6">
      {catalog.map((provider) => (
        <Card key={provider.name}>
          <CardHeader>
            <CardTitle className="text-xl">{provider.display_name}</CardTitle>
            <CardDescription>
              <span className="mr-3">
                {t('models.provider')} {provider.name}
              </span>
              <span className="mr-3">
                {provider.is_local ? t('models.local') : t('models.hosted')}
              </span>
              <span>
                {provider.requires_api_key
                  ? t('models.apiKeyRequired')
                  : t('models.noApiKeyRequired')}
              </span>
            </CardDescription>
          </CardHeader>
          <CardContent>
            {provider.is_local ? (
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card px-4 py-3 text-sm">
                <div className="flex-1">
                  <div className="font-medium">{t('models.runtimeCheck')}</div>
                  {runtimeTests[provider.name] ? (
                    <div
                      className={
                        runtimeTests[provider.name].status === 'success'
                          ? 'text-xs text-success'
                          : 'text-xs text-destructive'
                      }
                    >
                      {runtimeTests[provider.name].message}
                    </div>
                  ) : (
                    <div className="text-xs text-muted-foreground">
                      {t('models.runtimeCheckDesc')}
                    </div>
                  )}
                </div>
                <Button
                  variant="outline"
                  onClick={() => onRuntimeTest(provider.name)}
                  disabled={runtimeTests[provider.name]?.loading === true}
                >
                  {runtimeTests[provider.name]?.loading
                    ? tCommon('testing')
                    : t('models.testConnection')}
                </Button>
              </div>
            ) : null}
            <div className="w-full overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium" scope="col">
                      {t('models.model')}
                    </th>
                    <th className="pb-2 pr-4 font-medium" scope="col">
                      {t('models.context')}
                    </th>
                    <th className="pb-2 pr-4 font-medium" scope="col">
                      {t('models.inputPer1m')}
                    </th>
                    <th className="pb-2 pr-4 font-medium" scope="col">
                      {t('models.outputPer1m')}
                    </th>
                    <th className="pb-2 pr-4 font-medium" scope="col">
                      {t('models.capabilities')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {provider.models.map((model) => (
                    <tr key={model.id} className="border-t">
                      <td className="py-3 pr-4 font-medium">
                        <div className="leading-tight">
                          <div>{model.display_name || model.id}</div>
                          <div className="text-xs text-muted-foreground">{model.id}</div>
                        </div>
                      </td>
                      <td className="py-3 pr-4">{model.context_window.toLocaleString()}</td>
                      <td className="py-3 pr-4">
                        {model.pricing
                          ? formatMoneyPer1m(
                              model.pricing.input_price_per_1m,
                              model.pricing.currency
                            )
                          : '—'}
                      </td>
                      <td className="py-3 pr-4">
                        {model.pricing
                          ? formatMoneyPer1m(
                              model.pricing.output_price_per_1m,
                              model.pricing.currency
                            )
                          : '—'}
                      </td>
                      <td className="py-3 pr-4">
                        {model.capabilities.length ? model.capabilities.join(', ') : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {provider.is_local ? (
              <div className="mt-4 space-y-3">
                <p className="text-xs text-muted-foreground">{t('models.localModelsDesc')}</p>
                <div className="rounded-lg border bg-card p-4 text-sm">
                  <div className="font-medium">{t('models.localModelsOffline')}</div>
                  {runtimeTests[provider.name] &&
                  runtimeTests[provider.name].availableModels.length ? (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {t('models.runtimeDetectedModels')}{' '}
                      {runtimeTests[provider.name].availableModels.join(', ')}
                    </div>
                  ) : null}
                  <div className="mt-1 text-muted-foreground">
                    {provider.runtime_available === false
                      ? t('models.runtimeNotDetected')
                      : provider.runtime_available === true
                        ? t('models.runtimeDetected', {
                            count: provider.available_models?.length ?? 0,
                          })
                        : t('models.runtimeUnknown')}
                  </div>
                  <div className="mt-3 space-y-2 text-muted-foreground">
                    <div>
                      {t('models.ollamaStep1')}{' '}
                      <a
                        className="underline underline-offset-4"
                        href="https://ollama.com/download"
                        target="_blank"
                        rel="noreferrer"
                      >
                        ollama.com/download
                      </a>
                    </div>
                    <div>{t('models.ollamaStep2')}</div>
                    <div className="rounded-md bg-muted px-3 py-2 font-mono text-xs text-foreground">
                      ollama pull llama3.3:8b
                    </div>
                    <div className="font-mono text-xs">{t('models.ollamaStep3')}</div>
                  </div>
                  {provider.available_models?.length ? (
                    <div className="mt-3">
                      <div className="text-xs font-medium text-foreground">
                        {t('models.downloadedModels')}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {provider.available_models.join(', ')}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            ) : provider.models.some((m) => !m.pricing) ? (
              <p className="mt-4 text-xs text-muted-foreground">{t('models.pricingUnavailable')}</p>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function SettingsPage() {
  const t = useTranslations('pages.settings');
  const tSettings = useTranslations('settings');
  const tCommon = useTranslations('common');
  const tAuth = useTranslations('auth');
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<ModelProviderCatalog[] | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogRefreshing, setCatalogRefreshing] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | undefined>(undefined);

  const [runtimeTests, setRuntimeTests] = useState<
    Record<
      string,
      { loading: boolean; status: 'success' | 'error'; message: string; availableModels: string[] }
    >
  >({});

  const runRuntimeTest = async (providerName: string) => {
    setRuntimeTests((prev) => ({
      ...prev,
      [providerName]: {
        loading: true,
        status: 'success',
        message: tCommon('testing'),
        availableModels: prev[providerName]?.availableModels ?? [],
      },
    }));

    try {
      const result = await testModelRuntime(providerName);
      const ok = result.runtime_available === true;
      const models = Array.isArray(result.available_models) ? result.available_models : [];
      const message = ok
        ? tSettings('models.connectionSuccess')
        : result.runtime_error || tSettings('models.connectionFailed');
      setRuntimeTests((prev) => ({
        ...prev,
        [providerName]: {
          loading: false,
          status: ok ? 'success' : 'error',
          message,
          availableModels: models,
        },
      }));
    } catch (err) {
      let msg = tSettings('models.connectionFailed');

      if (err instanceof ApiError) {
        msg = err.message;
      } else if (err instanceof Error) {
        msg = err.message;
      }

      setRuntimeTests((prev) => ({
        ...prev,
        [providerName]: {
          loading: false,
          status: 'error',
          message: msg,
          availableModels: prev[providerName]?.availableModels ?? [],
        },
      }));
    }
  };

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
      let msg = tSettings('models.loadFailed');
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

  return (
    <div className="container mx-auto px-4 py-8">
      <PageHeader className="mb-8" title={t('title')} description={t('description')} />

      <div className="grid gap-8">
        {/* Identity Section - Always populated */}
        <section>
          <h2 className="text-lg font-semibold mb-4">{tSettings('identity.title')}</h2>
          <IdentitySettings onChange={(email) => setUserEmail(email)} />
        </section>

        {/* Profile Section - Task #88 */}
        <section>
          <h2 className="text-lg font-semibold mb-4">{tAuth('profile')}</h2>
          <ProfileSettings userEmail={userEmail} />
        </section>

        {/* Privacy & Data Section - Task #88 */}
        <section>
          <h2 className="text-lg font-semibold mb-4">{tSettings('privacy.title')}</h2>
          <PrivacySettings userEmail={userEmail} />
        </section>

        {/* Notifications Section - Always populated */}
        <section>
          <h2 className="text-lg font-semibold mb-4">{tSettings('notifications.title')}</h2>
          <NotificationSettings userEmail={userEmail} />
        </section>

        {/* Models Section - 4 Mandated States */}
        <section>
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h2 className="text-lg font-semibold">{tSettings('models.title')}</h2>
              <p className="text-sm text-muted-foreground mt-1">
                {tSettings('models.description')}
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => fetchCatalog(catalog ? 'refresh' : 'initial')}
              disabled={catalogLoading || catalogRefreshing}
            >
              {catalogRefreshing ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {tSettings('models.refreshing')}
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <RefreshCw className="h-4 w-4" />
                  {tSettings('models.refreshCatalog')}
                </span>
              )}
            </Button>
          </div>

          <div className="grid gap-6">
            {/* Always show model settings component */}
            <ModelSettings catalog={catalogLoading ? null : catalog} userEmail={userEmail} />

            {/* Task #87: Per-Task Model Preferences */}
            <TaskModelSettings catalog={catalog} userEmail={userEmail} />

            {/* STATE 1: Empty state (no catalog loaded yet) */}
            {!catalogLoading && !catalog && !catalogError && (
              <div
                className="flex flex-col items-center justify-center h-64 text-center border rounded-lg border-dashed bg-muted/20"
                role="status"
                aria-live="polite"
              >
                <Database className="h-10 w-10 text-muted-foreground mb-3" aria-hidden="true" />
                <h3 className="text-base font-semibold text-foreground mb-2">
                  {tSettings('models.modelCatalog')}
                </h3>
                <p className="text-sm text-muted-foreground max-w-sm mx-auto mb-4">
                  {tSettings('models.emptyCatalog')}
                </p>
                <div className="text-xs text-muted-foreground max-w-md">
                  <p className="font-medium mb-1">{tSettings('models.supportedProviders')}</p>
                  <p>{tSettings('providers.supported')}</p>
                  <p className="mt-2">{tSettings('models.emptyCatalogHint')}</p>
                </div>
              </div>
            )}

            {/* STATE 2: Loading state */}
            {catalogLoading && (
              <div role="status" aria-live="polite" aria-label={t('loadingModelCatalog')}>
                <CatalogSkeleton />
              </div>
            )}

            {/* STATE 3: Error state */}
            {catalogError && (
              <div
                className="flex flex-col items-center justify-center h-64 text-center border rounded-lg bg-destructive/10"
                role="alert"
                aria-live="assertive"
              >
                <AlertCircle className="h-10 w-10 text-destructive mb-3" aria-hidden="true" />
                <h3 className="text-base font-semibold text-destructive mb-2">
                  {tSettings('models.failedToLoadCatalog')}
                </h3>
                <p className="text-sm text-destructive/90 max-w-md mb-4">{catalogError}</p>
                {requestId && (
                  <p className="text-xs text-muted-foreground mb-4 font-mono">
                    request_id={requestId}
                  </p>
                )}
                <Button variant="outline" onClick={() => fetchCatalog('initial')} className="gap-2">
                  <RefreshCw className="h-4 w-4" />
                  {tCommon('retry')}
                </Button>
              </div>
            )}

            {/* STATE 4: Populated state */}
            {catalog && !catalogError && catalog.length === 0 && (
              <div
                className="rounded-lg border bg-card p-6 text-center"
                role="status"
                aria-live="polite"
              >
                <Sparkles
                  className="h-8 w-8 text-muted-foreground mx-auto mb-3"
                  aria-hidden="true"
                />
                <p className="text-sm text-muted-foreground">{tSettings('models.noModels')}.</p>
              </div>
            )}

            {catalog && !catalogError && catalog.length > 0 && (
              <ModelCatalogComparisonTable
                catalog={catalog}
                onRuntimeTest={runRuntimeTest}
                runtimeTests={runtimeTests}
              />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
