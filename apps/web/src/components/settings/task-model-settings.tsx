'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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

const TASK_TYPE_LABELS: Record<TaskType, string> = {
  chat: 'chat',
  search: 'search',
  tools: 'tools',
  analysis: 'analysis',
  embedding: 'embedding',
};

const TASK_TYPE_DESCRIPTIONS: Record<TaskType, string> = {
  chat: 'chatDescription',
  search: 'searchDescription',
  tools: 'toolsDescription',
  analysis: 'analysisDescription',
  embedding: 'embeddingDescription',
};

const TASK_TYPES: TaskType[] = ['chat', 'search', 'tools', 'analysis', 'embedding'];

interface TaskRowProps {
  taskType: TaskType;
  preference: TaskModelPreference | null;
  systemDefault: { provider: string; model_name: string; description?: string } | null;
  availableModels: Record<string, string[]>;
  providers: string[];
  onSave: (taskType: TaskType, provider: string, modelName: string) => Promise<void>;
  onReset: (taskType: TaskType, preferenceId: string) => Promise<void>;
  loading: boolean;
  t: ReturnType<typeof useTranslations>;
}

function TaskRow({
  taskType,
  preference,
  systemDefault,
  availableModels,
  providers,
  onSave,
  onReset,
  loading,
  t,
}: TaskRowProps) {
  const [provider, setProvider] = useState(preference?.provider || systemDefault?.provider || '');
  const [modelName, setModelName] = useState(
    preference?.model_name || systemDefault?.model_name || ''
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const modelsForProvider = useMemo(() => {
    return availableModels[provider] || [];
  }, [availableModels, provider]);

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
      setError(t('taskModel.selectBoth'));
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await onSave(taskType, provider, modelName);
      setSuccess(t('taskModel.saved'));
      setTimeout(() => setSuccess(null), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('taskModel.failedToSave'));
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
      setSuccess(t('taskModel.resetToDefault'));
      setTimeout(() => setSuccess(null), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('taskModel.failedToReset'));
    } finally {
      setSaving(false);
    }
  };

  const hasChanges =
    (preference?.provider || systemDefault?.provider) !== provider ||
    (preference?.model_name || systemDefault?.model_name) !== modelName;
  const isUsingDefault = !preference;

  return (
    <div className="flex items-center gap-4 py-4 border-b last:border-b-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium">{t(`taskTypes.${TASK_TYPE_LABELS[taskType]}`)}</span>
          {isUsingDefault && (
            <span className="text-xs bg-muted px-2 py-0.5 rounded">
              {t('taskModel.systemDefault')}
            </span>
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          {t(`taskTypes.${TASK_TYPE_DESCRIPTIONS[taskType]}`)}
        </p>
      </div>

      <div className="flex items-center gap-2">
        <select
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={provider}
          onChange={(e) => handleProviderChange(e.target.value)}
          disabled={loading || saving}
          aria-label={`${t(`taskTypes.${TASK_TYPE_LABELS[taskType]}`)} provider`}
        >
          <option value="">{t('taskModel.provider')}</option>
          {providers.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>

        <select
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={modelName}
          onChange={(e) => setModelName(e.target.value)}
          disabled={loading || saving || !provider}
          aria-label={`${t(`taskTypes.${TASK_TYPE_LABELS[taskType]}`)} model`}
        >
          <option value="">{t('taskModel.model')}</option>
          {modelsForProvider.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>

        <Button size="sm" onClick={handleSave} disabled={loading || saving || !hasChanges}>
          {saving ? '...' : t('taskModel.save')}
        </Button>

        {preference && (
          <Button size="sm" variant="outline" onClick={handleReset} disabled={loading || saving}>
            {t('taskModel.reset')}
          </Button>
        )}
      </div>

      {error && <span className="text-xs text-destructive">{error}</span>}
      {success && <span className="text-xs text-success">{success}</span>}
    </div>
  );
}

interface TaskModelSettingsProps {
  catalog: ModelProviderCatalog[] | null;
  userEmail: string | null;
}

export function TaskModelSettings({ catalog, userEmail }: TaskModelSettingsProps) {
  const t = useTranslations('settings');
  const [loading, setLoading] = useState(true);
  const [preferences, setPreferences] = useState<TaskModelPreference[]>([]);
  const [systemDefaults, setSystemDefaults] = useState<SystemDefaultsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const providers = useMemo(() => {
    if (!catalog) return [];
    return catalog.map((p) => p.name);
  }, [catalog]);

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
        setError(err instanceof Error ? err.message : t('taskModel.loadFailed'));
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [userEmail]);

  const getPreferenceForTask = (taskType: TaskType): TaskModelPreference | null => {
    return preferences.find((p) => p.task_type === taskType) || null;
  };

  const getSystemDefaultForTask = (
    taskType: TaskType
  ): { provider: string; model_name: string; description?: string } | null => {
    // The defaults are optional and their shape comes from the backend: a
    // response without a list must not take the whole settings page down.
    return systemDefaults?.defaults?.find((d) => d.task_type === taskType) || null;
  };

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
      <Card>
        <CardHeader>
          <CardTitle>{t("taskModel.title")}</CardTitle>
          <CardDescription>{t("taskModel.needsEmail")}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("taskModel.title")}</CardTitle>
        <CardDescription>{t("taskModel.description")}</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="p-4 text-sm text-muted-foreground">{t("taskModel.loading")}</div>
        ) : error ? (
          <div className="p-4 text-sm text-destructive">{error}</div>
        ) : (
          <div>
            {TASK_TYPES.map((taskType) => (
              <TaskRow
                key={taskType}
                taskType={taskType}
                preference={getPreferenceForTask(taskType)}
                systemDefault={getSystemDefaultForTask(taskType)}
                availableModels={systemDefaults?.available_models || availableModels}
                providers={systemDefaults?.available_providers || providers}
                onSave={handleSave}
                onReset={handleReset}
                loading={loading}
                t={t}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
