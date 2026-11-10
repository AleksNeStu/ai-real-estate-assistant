'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { SettingsPanel, SettingsRow } from '@/components/settings/settings-panel';
import {
  getTaskModelPreferences,
  createTaskModelPreference,
  updateTaskModelPreference,
  deleteTaskModelPreference,
  getSystemModelDefaults,
} from '@/lib/api';
import type {
  TaskType,
  TaskModelPreference,
  TaskModelPreferenceCreate,
  SystemDefaultsResponse,
  ModelProviderCatalog,
} from '@/lib/types';

/**
 * The per-task picker.
 *
 * Each task the assistant does - a chat, a search, a tool call, an analysis,
 * an embedding - can run on its own model. The list of tasks is a list, so it
 * is a ledger: one rule opens it and every row is a task, what it is for and
 * the model that handles it.
 *
 * The row says three things about the chosen model, and every one of them
 * comes from the catalogue the API carries: its context window and what a
 * million tokens cost on the way in and on the way out. A model the
 * catalogue does not price says so instead of carrying a made-up price.
 */

const TASK_TYPES: TaskType[] = ['chat', 'search', 'tools', 'analysis', 'embedding'];

interface TaskRowProps {
  taskType: TaskType;
  preference: TaskModelPreference | null;
  systemDefault: { provider: string; model_name: string; description?: string } | null;
  availableModels: Record<string, string[]>;
  providers: string[];
  catalog: ModelProviderCatalog[] | null;
  onSave: (taskType: TaskType, provider: string, modelName: string) => Promise<void>;
  onReset: (taskType: TaskType, preferenceId: string) => Promise<void>;
  loading: boolean;
}

function TaskRow({
  taskType,
  preference,
  systemDefault,
  availableModels,
  providers,
  catalog,
  onSave,
  onReset,
  loading,
}: TaskRowProps) {
  const t = useTranslations('pages.settings.models.perTask');
  const tTypes = useTranslations('taskTypes');
  const [provider, setProvider] = useState(preference?.provider || systemDefault?.provider || '');
  const [modelName, setModelName] = useState(
    preference?.model_name || systemDefault?.model_name || ''
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const modelsForProvider = useMemo(() => availableModels[provider] || [], [availableModels, provider]);

  // The catalogue entry of the chosen model: the context window and the
  // price of a million tokens. Both are the API's numbers or nothing.
  const chosen = useMemo(() => {
    if (!catalog || !provider || !modelName) return null;
    const providerEntry = catalog.find((p) => p.name === provider);
    return providerEntry?.models.find((m) => m.id === modelName) ?? null;
  }, [catalog, provider, modelName]);

  useEffect(() => {
    if (preference) {
      setProvider(preference.provider);
      setModelName(preference.model_name);
    } else if (systemDefault) {
      setProvider(systemDefault.provider);
      setModelName(systemDefault.model_name);
    }
  }, [preference, systemDefault]);

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider);
    const models = availableModels[newProvider] || [];
    setModelName(models[0] || '');
  };

  const handleSave = async () => {
    if (!provider || !modelName) {
      setError(t('selectBoth'));
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await onSave(taskType, provider, modelName);
      setSuccess(t('saved'));
      setTimeout(() => setSuccess(null), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('failedToSave'));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!preference?.id) return;
    setSaving(true);
    setError(null);
    try {
      await onReset(taskType, preference.id);
      if (systemDefault) {
        setProvider(systemDefault.provider);
        setModelName(systemDefault.model_name);
      }
      setSuccess(t('resetToDefault'));
      setTimeout(() => setSuccess(null), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('failedToReset'));
    } finally {
      setSaving(false);
    }
  };

  const hasChanges =
    (preference?.provider || systemDefault?.provider) !== provider ||
    (preference?.model_name || systemDefault?.model_name) !== modelName;
  const isUsingDefault = !preference;

  return (
    <SettingsRow
      label={tTypes(taskType)}
      description={tTypes(`${taskType}Description`)}
      action={
        <>
          <button
            type="button"
            onClick={handleSave}
            disabled={loading || saving || !hasChanges}
            className="rounded-sm text-app font-medium text-foreground transition-colors hover:underline disabled:opacity-40"
          >
            {saving ? t('saving') : t('save')}
          </button>
          {preference ? (
            <button
              type="button"
              onClick={handleReset}
              disabled={loading || saving}
              className="rounded-sm text-app font-medium text-muted-foreground transition-colors hover:text-foreground hover:underline disabled:opacity-40"
            >
              {t('reset')}
            </button>
          ) : null}
          {isUsingDefault ? <MonoAnnotation>{t('systemDefault')}</MonoAnnotation> : null}
        </>
      }
    >
      <div className="flex flex-col gap-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="h-8 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
            value={provider}
            onChange={(e) => handleProviderChange(e.target.value)}
            disabled={loading || saving}
            aria-label={`${tTypes(taskType)} provider`}
          >
            <option value="">{t('provider')}</option>
            {providers.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>

          <select
            className="h-8 rounded-md border border-input bg-background px-2 font-mono text-[13px]"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            disabled={loading || saving || !provider}
            aria-label={`${tTypes(taskType)} model`}
          >
            <option value="">{t('model')}</option>
            {modelsForProvider.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <MonoAnnotation>
            {chosen
              ? t('context', { size: chosen.context_window.toLocaleString() })
              : t('contextUnknown')}
          </MonoAnnotation>
          <MonoAnnotation>
            {chosen?.pricing
              ? t('price', {
                  input: chosen.pricing.input_price_per_1m.toFixed(2),
                  output: chosen.pricing.output_price_per_1m.toFixed(2),
                  currency: chosen.pricing.currency,
                })
              : t('priceUnknown')}
          </MonoAnnotation>
        </div>

        {error ? (
          <MonoAnnotation tone="destructive" className="block">
            {error}
          </MonoAnnotation>
        ) : null}
        {success ? (
          <MonoAnnotation tone="success" className="block">
            {success}
          </MonoAnnotation>
        ) : null}
      </div>
    </SettingsRow>
  );
}

interface TaskModelSettingsProps {
  catalog: ModelProviderCatalog[] | null;
  userEmail: string | null;
}

export function TaskModelSettings({ catalog, userEmail }: TaskModelSettingsProps) {
  const t = useTranslations('pages.settings.models.perTask');
  const [loading, setLoading] = useState(true);
  const [preferences, setPreferences] = useState<TaskModelPreference[]>([]);
  const [systemDefaults, setSystemDefaults] = useState<SystemDefaultsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const providers = useMemo(() => (catalog ? catalog.map((p) => p.name) : []), [catalog]);

  const availableModels = useMemo(() => {
    if (!catalog) return {};
    const result: Record<string, string[]> = {};
    for (const provider of catalog) {
      result[provider.name] = provider.models.map((m) => m.id);
    }
    return result;
  }, [catalog]);

  useEffect(() => {
    const load = async () => {
      if (!userEmail) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const [prefsResponse, defaultsResponse] = await Promise.all([
          getTaskModelPreferences(),
          getSystemModelDefaults(),
        ]);
        setPreferences(prefsResponse.items);
        setSystemDefaults(defaultsResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : t('loadFailed'));
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [userEmail, t]);

  const getPreferenceForTask = (taskType: TaskType): TaskModelPreference | null =>
    preferences.find((p) => p.task_type === taskType) || null;

  const getSystemDefaultForTask = (
    taskType: TaskType
  ): { provider: string; model_name: string; description?: string } | null =>
    // The defaults are optional and their shape comes from the backend: a
    // response without a list must not take the whole settings page down.
    systemDefaults?.defaults?.find((d) => d.task_type === taskType) || null;

  const handleSave = async (taskType: TaskType, provider: string, modelName: string) => {
    const existing = getPreferenceForTask(taskType);

    if (existing) {
      const updated = await updateTaskModelPreference(existing.id, {
        provider,
        model_name: modelName,
      });
      setPreferences((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    } else {
      const data: TaskModelPreferenceCreate = {
        task_type: taskType,
        provider,
        model_name: modelName,
      };
      const created = await createTaskModelPreference(data);
      setPreferences((prev) => [...prev, created]);
    }
  };

  const handleReset = async (_taskType: TaskType, preferenceId: string) => {
    await deleteTaskModelPreference(preferenceId);
    setPreferences((prev) => prev.filter((p) => p.id !== preferenceId));
  };

  if (!userEmail) {
    return (
      <SettingsPanel title={t('title')} description={t('needsEmail')}>
        <div />
      </SettingsPanel>
    );
  }

  return (
    <SettingsPanel title={t('title')} description={t('description')}>
      {loading ? (
        <p className="py-4 text-app text-muted-foreground">{t('loading')}</p>
      ) : error ? (
        <MonoAnnotation tone="destructive" className="block py-4">
          {error}
        </MonoAnnotation>
      ) : (
        TASK_TYPES.map((taskType) => (
          <TaskRow
            key={taskType}
            taskType={taskType}
            preference={getPreferenceForTask(taskType)}
            systemDefault={getSystemDefaultForTask(taskType)}
            availableModels={systemDefaults?.available_models || availableModels}
            providers={systemDefaults?.available_providers || providers}
            catalog={catalog}
            onSave={handleSave}
            onReset={handleReset}
            loading={loading}
          />
        ))
      )}
    </SettingsPanel>
  );
}
