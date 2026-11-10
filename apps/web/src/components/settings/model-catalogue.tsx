'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { LedgerRow } from '@/components/ui/ledger';
import { MonoAnnotation, type MonoTone } from '@/components/ui/mono-annotation';
import { SettingsPanel, SettingsRow } from '@/components/settings/settings-panel';
import { testModelRuntime } from '@/lib/api';
import type { ModelProviderCatalog } from '@/lib/types';

/**
 * The model catalogue.
 *
 * A catalogue of models is a list, so it is a ledger: one ink rule opens it
 * and every row is a model with its provider, the size of its context, what a
 * million tokens cost on the way in and on the way out, and a button that
 * probes the provider behind it.
 *
 * Every number on the row is mono - the model id, the context, the prices.
 * A label states what a thing is.
 *
 * The probe is the runtime test. It answers two things the API carries: the
 * provider is reachable, and the key that provider needs is set. The
 * milliseconds are the round trip this browser measured - the API does not
 * carry a latency, so the number is ours, not the server's.
 */

export interface RuntimeProbe {
  state: 'idle' | 'running' | 'ok' | 'missing-key' | 'failed';
  /** The measured round trip of the probe, in milliseconds. */
  ms?: number;
  /** The message the API carried with the probe. */
  detail?: string;
}

/** The context window, in the shape a reader scans: 128k, 1M. */
export function formatContextWindow(tokens: number | undefined | null): string {
  if (!tokens || !Number.isFinite(tokens) || tokens <= 0) return '—';
  if (tokens >= 1_000_000) {
    const millions = tokens / 1_000_000;
    return `${Number.isInteger(millions) ? millions : millions.toFixed(1)}M`;
  }
  if (tokens >= 1000) {
    const thousands = tokens / 1000;
    return `${Number.isInteger(thousands) ? thousands : thousands.toFixed(1)}k`;
  }
  return String(tokens);
}

/** The price of a million tokens, in the currency the catalogue carries. */
export function formatPricePer1m(
  value: number | undefined | null,
  currency: string | undefined | null
): string {
  if (value === undefined || value === null || !Number.isFinite(value)) return '—';
  return `${currency || '—'} ${value.toFixed(2)}`;
}

/**
 * What the probe says.
 *
 * The API answers with a flag and a message. A provider that needs a key and
 * has none says so in the message; that is the "no key set" the reader sees.
 */
export function probeTone(probe: RuntimeProbe | undefined): MonoTone {
  if (!probe || probe.state === 'idle' || probe.state === 'running') return 'neutral';
  if (probe.state === 'ok') return 'success';
  if (probe.state === 'missing-key') return 'warning';
  return 'destructive';
}

/** Whether the probe failed because a key is missing, rather than a failure. */
export function isMissingKeyMessage(message: string | undefined | null): boolean {
  if (!message) return false;
  return /api key|key not|no key|not provided/i.test(message);
}

export interface ModelCatalogueProps {
  catalog: ModelProviderCatalog[];
  className?: string;
}

export function ModelCatalogue({ catalog, className }: ModelCatalogueProps) {
  const t = useTranslations('pages.settings.models.catalogue');
  const [probes, setProbes] = useState<Record<string, RuntimeProbe>>({});

  const rows = useMemo(() => {
    return catalog.flatMap((provider) =>
      provider.models.map((model) => ({
        key: `${provider.name}/${model.id}`,
        provider,
        model,
      }))
    );
  }, [catalog]);

  const providers = catalog.length;

  const runProbe = async (providerName: string) => {
    setProbes((prev) => ({
      ...prev,
      [providerName]: { state: 'running' },
    }));
    const started = Date.now();
    try {
      const result = await testModelRuntime(providerName);
      const ms = Date.now() - started;
      const ok = result.runtime_available === true;
      setProbes((prev) => ({
        ...prev,
        [providerName]: {
          state: ok ? 'ok' : isMissingKeyMessage(result.runtime_error) ? 'missing-key' : 'failed',
          ms,
          detail: result.runtime_error ?? undefined,
        },
      }));
    } catch (err) {
      setProbes((prev) => ({
        ...prev,
        [providerName]: {
          state: 'failed',
          ms: Date.now() - started,
          detail: err instanceof Error ? err.message : undefined,
        },
      }));
    }
  };

  return (
    <SettingsPanel
      title={t('title')}
      description={t('description')}
      action={<MonoAnnotation>{t('providerCount', { count: providers })}</MonoAnnotation>}
      className={className}
    >
      <div className="hidden gap-4 pb-2 pt-2.5 text-annot text-muted-foreground lg:grid lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_90px_120px_120px_180px]">
        <span>{t('columns.model')}</span>
        <span>{t('columns.provider')}</span>
        <span>{t('columns.context')}</span>
        <span>{t('columns.input')}</span>
        <span>{t('columns.output')}</span>
        <span>{t('columns.probe')}</span>
      </div>

      {rows.length === 0 ? (
        <p className="py-4 text-app text-muted-foreground">{t('empty')}</p>
      ) : null}

      {rows.map(({ key, provider, model }, index) => {
        const probe = probes[provider.name];
        // The probe belongs to the provider, so it is stated once - on the
        // first row of that provider.
        const isFirstRowOfProvider = rows[index - 1]?.provider.name !== provider.name;
        return (
          <LedgerRow
            key={key}
            className="grid-cols-1 gap-x-4 gap-y-1.5 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_90px_120px_120px_180px] lg:items-center"
          >
            <div className="min-w-0">
              <MonoAnnotation className="font-medium text-foreground">{model.id}</MonoAnnotation>
              {model.display_name && model.display_name !== model.id ? (
                <span className="block text-annot text-muted-foreground">{model.display_name}</span>
              ) : null}
            </div>

            <div className="min-w-0">
              <span className="text-app text-foreground">{provider.display_name}</span>
              <MonoAnnotation className="block">
                {provider.is_local ? t('local') : t('hosted')}
              </MonoAnnotation>
            </div>

            <div>
              <MonoAnnotation>{formatContextWindow(model.context_window)}</MonoAnnotation>
            </div>

            <div>
              <MonoAnnotation>
                {formatPricePer1m(
                  model.pricing?.input_price_per_1m,
                  model.pricing?.currency
                )}
              </MonoAnnotation>
            </div>

            <div>
              <MonoAnnotation>
                {formatPricePer1m(
                  model.pricing?.output_price_per_1m,
                  model.pricing?.currency
                )}
              </MonoAnnotation>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => runProbe(provider.name)}
                disabled={probe?.state === 'running'}
                className="h-7 shrink-0 rounded-md border border-border bg-transparent px-2.5 text-annot font-medium text-foreground transition-colors hover:bg-muted disabled:opacity-60"
              >
                {probe?.state === 'running' ? t('testing') : t('test')}
              </button>
              {isFirstRowOfProvider ? (
                <MonoAnnotation tone={probeTone(probe)} className="min-w-0">
                  {probe?.state === 'ok' ? t('ok', { ms: probe.ms ?? 0 }) : null}
                  {probe?.state === 'missing-key' ? t('noKey') : null}
                  {probe?.state === 'failed'
                    ? probe.detail || t('failed')
                    : null}
                </MonoAnnotation>
              ) : null}
            </div>
          </LedgerRow>
        );
      })}
    </SettingsPanel>
  );
}

/**
 * The local runtime note.
 *
 * The prototype puts it under the catalogue: the two commands and the
 * variable a local model needs. It is a note, so it sits on a muted panel.
 */
export function LocalRuntimeNote({ className }: { className?: string }) {
  const t = useTranslations('pages.settings.models.local');
  return (
    <div className={className}>
      <SettingsRow label={t('label')} description={t('description')}>
        <div className="flex flex-col gap-2 text-annot text-muted-foreground">
          <span>{t('install')}</span>
          <MonoAnnotation className="text-foreground">ollama pull llama3.1:8b</MonoAnnotation>
          <span>{t('env')}</span>
          <MonoAnnotation className="text-foreground">OLLAMA_BASE_URL</MonoAnnotation>
        </div>
      </SettingsRow>
    </div>
  );
}
