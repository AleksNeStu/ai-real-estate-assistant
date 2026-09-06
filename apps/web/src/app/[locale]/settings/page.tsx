'use client';

import { useEffect, useState } from 'react';
import { RefreshCw, AlertCircle, Loader2, Database, Sparkles } from 'lucide-react';
import { IdentitySettings } from '@/components/settings/identity-settings';
import { ModelSettings } from '@/components/settings/model-settings';
import { TaskModelSettings } from '@/components/settings/task-model-settings';
import { NotificationSettings } from '@/components/settings/notification-settings';
import { ProfileSettings } from '@/components/settings/profile-settings';
import { PrivacySettings } from '@/components/settings/privacy-settings';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
  return (
    <div className="grid gap-6">
      {catalog.map((provider) => (
        <Card key={provider.name}>
          <CardHeader>
            <CardTitle className="text-xl">{provider.display_name}</CardTitle>
            <CardDescription>
              <span className="mr-3">Provider: {provider.name}</span>
              <span className="mr-3">{provider.is_local ? 'Local' : 'Hosted'}</span>
              <span>{provider.requires_api_key ? 'API key required' : 'No API key required'}</span>
            </CardDescription>
          </CardHeader>
          <CardContent>
            {provider.is_local ? (
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card px-4 py-3 text-sm">
                <div className="flex-1">
                  <div className="font-medium">Runtime check</div>
                  {runtimeTests[provider.name] ? (
                    <div
                      className={
                        runtimeTests[provider.name].status === 'success'
                          ? 'text-xs text-emerald-600'
                          : 'text-xs text-red-600'
                      }
                    >
                      {runtimeTests[provider.name].message}
                    </div>
                  ) : (
                    <div className="text-xs text-muted-foreground">
                      Run a targeted runtime check for this provider.
                    </div>
                  )}
                </div>
                <Button
                  variant="outline"
                  onClick={() => onRuntimeTest(provider.name)}
                  disabled={runtimeTests[provider.name]?.loading === true}
                >
                  {runtimeTests[provider.name]?.loading ? 'Testing...' : 'Test Connection'}
                </Button>
              </div>
            ) : null}
            <div className="w-full overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium" scope="col">
                      Model
                    </th>
                    <th className="pb-2 pr-4 font-medium" scope="col">
                      Context
                    </th>
                    <th className="pb-2 pr-4 font-medium" scope="col">
                      Input / 1M
                    </th>
                    <th className="pb-2 pr-4 font-medium" scope="col">
                      Output / 1M
                    </th>
                    <th className="pb-2 pr-4 font-medium" scope="col">
                      Capabilities
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
                <p className="text-xs text-muted-foreground">
                  Local models run on your machine. Token pricing is not applicable; costs depend on
                  your hardware and runtime settings.
                </p>
                <div className="rounded-lg border bg-card p-4 text-sm">
                  <div className="font-medium">Local models & offline usage</div>
                  {runtimeTests[provider.name] &&
                  runtimeTests[provider.name].availableModels.length ? (
                    <div className="mt-1 text-xs text-muted-foreground">
                      Runtime check detected models:{' '}
                      {runtimeTests[provider.name].availableModels.join(', ')}
                    </div>
                  ) : null}
                  <div className="mt-1 text-muted-foreground">
                    {provider.runtime_available === false
                      ? 'Local runtime not detected. Start your local runtime and ensure the API can reach it.'
                      : provider.runtime_available === true
                        ? `Local runtime detected. Downloaded models: ${provider.available_models?.length ?? 0}.`
                        : 'Local runtime status is unknown.'}
                  </div>
                  <div className="mt-3 space-y-2 text-muted-foreground">
                    <div>
                      1. Install Ollama:{' '}
                      <a
                        className="underline underline-offset-4"
                        href="https://ollama.com/download"
                        target="_blank"
                        rel="noreferrer"
                      >
                        ollama.com/download
                      </a>
                    </div>
                    <div>2. Start Ollama, then download a model:</div>
                    <div className="rounded-md bg-muted px-3 py-2 font-mono text-xs text-foreground">
                      ollama pull llama3.3:8b
                    </div>
                    <div>
                      3. If the API runs in Docker, set{' '}
                      <span className="font-mono">OLLAMA_BASE_URL</span> to{' '}
                      <span className="font-mono">http://host.docker.internal:11434</span>.
                    </div>
                  </div>
                  {provider.available_models?.length ? (
                    <div className="mt-3">
                      <div className="text-xs font-medium text-foreground">Downloaded models</div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {provider.available_models.join(', ')}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            ) : provider.models.some((m) => !m.pricing) ? (
              <p className="mt-4 text-xs text-muted-foreground">
                Pricing may be unavailable for some hosted models.
              </p>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function SettingsPage() {
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
        message: 'Testing connection...',
        availableModels: prev[providerName]?.availableModels ?? [],
      },
    }));

    try {
      const result = await testModelRuntime(providerName);
      const ok = result.runtime_available === true;
      const models = Array.isArray(result.available_models) ? result.available_models : [];
      const message = ok ? 'Connection successful.' : result.runtime_error || 'Connection failed.';
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
      let msg = 'Connection failed.';

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
      let msg = 'Failed to load model catalog. Please try again.';
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
    <div className="container mx-auto px-4 py-10">
      <div className="flex flex-col space-y-4 mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings and notification preferences.
        </p>
      </div>

      <div className="grid gap-8">
        {/* Identity Section - Always populated */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Identity</h2>
          <IdentitySettings onChange={(email) => setUserEmail(email)} />
        </section>

        {/* Profile Section - Task #88 */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Profile</h2>
          <ProfileSettings userEmail={userEmail} />
        </section>

        {/* Privacy & Data Section - Task #88 */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Privacy & Data</h2>
          <PrivacySettings userEmail={userEmail} />
        </section>

        {/* Notifications Section - Always populated */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Notifications</h2>
          <NotificationSettings userEmail={userEmail} />
        </section>

        {/* Models Section - 4 Mandated States */}
        <section>
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h2 className="text-lg font-semibold">Models</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Select your default model and compare pricing/capabilities across providers.
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
                  Refreshing...
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <RefreshCw className="h-4 w-4" />
                  Refresh Catalog
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
                <h3 className="text-base font-semibold text-foreground mb-2">Model Catalog</h3>
                <p className="text-sm text-muted-foreground max-w-sm mx-auto mb-4">
                  No models are currently configured. Add your API keys in the Identity section
                  above to get started.
                </p>
                <div className="text-xs text-muted-foreground max-w-md">
                  <p className="font-medium mb-1">Supported providers:</p>
                  <p>OpenAI, Anthropic, Google, Grok, DeepSeek, and Ollama (local).</p>
                </div>
              </div>
            )}

            {/* STATE 2: Loading state */}
            {catalogLoading && (
              <div role="status" aria-live="polite" aria-label="Loading model catalog">
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
                  Failed to Load Catalog
                </h3>
                <p className="text-sm text-destructive/90 max-w-md mb-4">{catalogError}</p>
                {requestId && (
                  <p className="text-xs text-muted-foreground mb-4 font-mono">
                    request_id={requestId}
                  </p>
                )}
                <Button variant="outline" onClick={() => fetchCatalog('initial')} className="gap-2">
                  <RefreshCw className="h-4 w-4" />
                  Retry
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
                <p className="text-sm text-muted-foreground">No models available.</p>
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
