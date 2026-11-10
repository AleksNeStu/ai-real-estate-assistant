'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { SettingsPanel, SettingsRow } from '@/components/settings/settings-panel';
import { getModelPreferences, updateModelPreferences } from '@/lib/api';
import type { ModelPreferences, ModelProviderCatalog } from '@/lib/types';

function storageKeyForEmail(userEmail: string): string {
  return `modelPrefs:${userEmail}`;
}

function loadLocalPreferences(userEmail: string): ModelPreferences | null {
  const raw = window.localStorage.getItem(storageKeyForEmail(userEmail));
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;
    const obj = parsed as { preferred_provider?: unknown; preferred_model?: unknown };
    return {
      preferred_provider: typeof obj.preferred_provider === 'string' ? obj.preferred_provider : null,
      preferred_model: typeof obj.preferred_model === 'string' ? obj.preferred_model : null,
    };
  } catch {
    return null;
  }
}

function persistLocalPreferences(userEmail: string, prefs: ModelPreferences) {
  window.localStorage.setItem(storageKeyForEmail(userEmail), JSON.stringify(prefs));
}

/**
 * The default model.
 *
 * The model a task falls back to when it has no preference of its own. It is
 * one row of a ledger - a provider, a model and the button that stores them -
 * and the catalogue it is drawn from is the same ledger the Models tab shows.
 */
export function ModelSettings({
  catalog,
  userEmail,
}: {
  catalog: ModelProviderCatalog[] | null;
  userEmail: string | null;
}) {
  const t = useTranslations('settings.models');
  const td = useTranslations('pages.settings.models.default');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [preferredProvider, setPreferredProvider] = useState<string | null>(null);
  const [preferredModel, setPreferredModel] = useState<string | null>(null);

  const providers = useMemo(() => (catalog ? catalog.map((p) => p.name) : []), [catalog]);
  const modelsForProvider = useMemo(() => {
    if (!catalog || !preferredProvider) return [];
    const provider = catalog.find((p) => p.name === preferredProvider);
    return provider ? provider.models.map((m) => m.id) : [];
  }, [catalog, preferredProvider]);
  const selectedProvider = useMemo(() => {
    if (!catalog || !preferredProvider) return null;
    return catalog.find((p) => p.name === preferredProvider) ?? null;
  }, [catalog, preferredProvider]);

  const chosen = useMemo(() => {
    if (!selectedProvider || !preferredModel) return null;
    return selectedProvider.models.find((m) => m.id === preferredModel) ?? null;
  }, [selectedProvider, preferredModel]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      setError(null);
      setSuccess(null);

      if (!userEmail) {
        setPreferredProvider(null);
        setPreferredModel(null);
        setLoading(false);
        return;
      }

      const local = loadLocalPreferences(userEmail);
      if (local) {
        setPreferredProvider(local.preferred_provider);
        setPreferredModel(local.preferred_model);
      }

      try {
        const remote = await getModelPreferences();
        setPreferredProvider(remote.preferred_provider);
        setPreferredModel(remote.preferred_model);
        persistLocalPreferences(userEmail, remote);
      } catch {
        setError('Failed to load model preferences. Using local preferences.');
      } finally {
        setLoading(false);
      }
    };

    init();
  }, [userEmail]);

  useEffect(() => {
    if (!catalog || !preferredProvider) return;
    const providerExists = providers.includes(preferredProvider);
    if (!providerExists) {
      setPreferredProvider(null);
      setPreferredModel(null);
      return;
    }

    if (preferredModel) {
      const allowedModels = modelsForProvider;
      if (!allowedModels.includes(preferredModel)) {
        setPreferredModel(null);
      }
    }
  }, [catalog, preferredProvider, preferredModel, providers, modelsForProvider]);

  const canSave = Boolean(userEmail && preferredProvider && preferredModel && catalog);

  const handleSave = async () => {
    if (!userEmail) {
      setError(t('needsEmailSave'));
      return;
    }

    if (!preferredProvider || !preferredModel) {
      setError('Select both a provider and a model.');
      return;
    }

    if (!catalog) {
      setError('Model catalog is not available.');
      return;
    }

    const provider = catalog.find((p) => p.name === preferredProvider);
    if (!provider) {
      setError('Selected provider is not available.');
      return;
    }

    if (!provider.models.some((m) => m.id === preferredModel)) {
      setError(t('errorUnavailable'));
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);
    const next: ModelPreferences = {
      preferred_provider: preferredProvider,
      preferred_model: preferredModel,
    };
    persistLocalPreferences(userEmail, next);

    try {
      const saved = await updateModelPreferences(next);
      setPreferredProvider(saved.preferred_provider);
      setPreferredModel(saved.preferred_model);
      persistLocalPreferences(userEmail, saved);
      setSuccess(t('savedDefault'));
    } catch {
      setError(t('errorSave'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <SettingsPanel title={t('defaultModel')} description={t('defaultModelDescription')}>
      <SettingsRow
        label={t('providerLabel')}
        description={
          selectedProvider?.is_local &&
          selectedProvider.runtime_available !== undefined &&
          selectedProvider.runtime_available !== null ? (
            selectedProvider.runtime_available ? (
              <MonoAnnotation tone="success">
                {selectedProvider.available_models?.length
                  ? t('detectedModels', { models: selectedProvider.available_models.join(', ') })
                  : t('runtimeAvailable')}
              </MonoAnnotation>
            ) : (
              <div className="flex flex-col gap-0.5">
                <MonoAnnotation tone="warning">{t('runtimeUnavailable')}</MonoAnnotation>
                {selectedProvider.runtime_error ? (
                  <MonoAnnotation tone="destructive">{selectedProvider.runtime_error}</MonoAnnotation>
                ) : null}
              </div>
            )
          ) : null
        }
        action={
          <>
            {success ? <MonoAnnotation tone="success">{success}</MonoAnnotation> : null}
            {error ? <MonoAnnotation tone="destructive">{error}</MonoAnnotation> : null}
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !canSave}
              className="rounded-sm text-app font-medium text-foreground transition-colors hover:underline disabled:opacity-40"
            >
              {saving ? t('saving') : t('saveDefault')}
            </button>
          </>
        }
      >
        {loading ? (
          <span className="text-app text-muted-foreground">{t('loading')}</span>
        ) : !userEmail ? (
          <span className="text-app text-muted-foreground">{t('needsEmail')}</span>
        ) : !catalog ? (
          <span className="text-app text-muted-foreground">{t('noCatalog')}</span>
        ) : (
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <select
                id="preferred_provider"
                aria-label={t('providerLabel')}
                className="h-8 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
                value={preferredProvider || ''}
                onChange={(e) => {
                  const nextProvider = e.target.value || null;
                  setPreferredProvider(nextProvider);
                  if (!nextProvider) {
                    setPreferredModel(null);
                    return;
                  }
                  const provider = catalog.find((p) => p.name === nextProvider);
                  setPreferredModel(provider?.models[0]?.id || null);
                }}
              >
                <option value="">{t('selectProvider')}</option>
                {providers.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>

              <select
                id="preferred_model"
                aria-label={t('model')}
                className="h-8 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
                value={preferredModel || ''}
                onChange={(e) => setPreferredModel(e.target.value || null)}
                disabled={!preferredProvider}
              >
                <option value="">{t('selectModel')}</option>
                {modelsForProvider.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </div>

            {chosen ? (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <MonoAnnotation>
                  {td('context', { size: chosen.context_window.toLocaleString() })}
                </MonoAnnotation>
                <MonoAnnotation>
                  {chosen.pricing
                    ? td('price', {
                        input: chosen.pricing.input_price_per_1m.toFixed(2),
                        output: chosen.pricing.output_price_per_1m.toFixed(2),
                        currency: chosen.pricing.currency,
                      })
                    : td('priceUnknown')}
                </MonoAnnotation>
              </div>
            ) : null}
          </div>
        )}
      </SettingsRow>
    </SettingsPanel>
  );
}
