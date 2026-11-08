"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { getModelPreferences, updateModelPreferences } from "@/lib/api";
import type { ModelPreferences, ModelProviderCatalog } from "@/lib/types";

function storageKeyForEmail(userEmail: string): string {
  return `modelPrefs:${userEmail}`;
}

function loadLocalPreferences(userEmail: string): ModelPreferences | null {
  const raw = window.localStorage.getItem(storageKeyForEmail(userEmail));
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    const obj = parsed as { preferred_provider?: unknown; preferred_model?: unknown };
    return {
      preferred_provider: typeof obj.preferred_provider === "string" ? obj.preferred_provider : null,
      preferred_model: typeof obj.preferred_model === "string" ? obj.preferred_model : null,
    };
  } catch {
    return null;
  }
}

function persistLocalPreferences(userEmail: string, prefs: ModelPreferences) {
  window.localStorage.setItem(storageKeyForEmail(userEmail), JSON.stringify(prefs));
}

export function ModelSettings({ catalog, userEmail }: { catalog: ModelProviderCatalog[] | null; userEmail: string | null }) {
  const t = useTranslations("settings.models");
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
        setError("Failed to load model preferences. Using local preferences.");
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
      setError(t("needsEmailSave"));
      return;
    }

    if (!preferredProvider || !preferredModel) {
      setError("Select both a provider and a model.");
      return;
    }

    if (!catalog) {
      setError("Model catalog is not available.");
      return;
    }

    const provider = catalog.find((p) => p.name === preferredProvider);
    if (!provider) {
      setError("Selected provider is not available.");
      return;
    }

    if (!provider.models.some((m) => m.id === preferredModel)) {
      setError(t("errorUnavailable"));
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);
    const next: ModelPreferences = { preferred_provider: preferredProvider, preferred_model: preferredModel };
    persistLocalPreferences(userEmail, next);

    try {
      const saved = await updateModelPreferences(next);
      setPreferredProvider(saved.preferred_provider);
      setPreferredModel(saved.preferred_model);
      persistLocalPreferences(userEmail, saved);
      setSuccess(t("savedDefault"));
    } catch {
      setError(t("errorSave"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("defaultModel")}</CardTitle>
        <CardDescription>{t("defaultModelDescription")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <div className="p-2 text-sm text-muted-foreground">{t("loading")}</div>
        ) : !userEmail ? (
          <div className="rounded-md border p-3 text-sm text-muted-foreground">{t("needsEmail")}</div>
        ) : !catalog ? (
          <div className="rounded-md border p-3 text-sm text-muted-foreground">{t("noCatalog")}</div>
        ) : (
          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="preferred_provider">{t("providerLabel")}</Label>
              <select
                id="preferred_provider"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
                value={preferredProvider || ""}
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
                <option value="">{t("selectProvider")}</option>
                {providers.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>

            {selectedProvider?.is_local && selectedProvider.runtime_available !== undefined && selectedProvider.runtime_available !== null ? (
              <div className="rounded-md border p-3 text-sm text-muted-foreground">
                {selectedProvider.runtime_available ? (
                  <div>
                    <div>{t("runtimeAvailable")}</div>
                    {selectedProvider.available_models && selectedProvider.available_models.length ? (
                      <div>{t("detectedModels", { models: selectedProvider.available_models.join(", ") })}</div>
                    ) : (
                      <div>{t("noLocalModels")}</div>
                    )}
                  </div>
                ) : (
                  <div>
                    <div>{t("runtimeUnavailable")}</div>
                    {selectedProvider.runtime_error ? <div>{selectedProvider.runtime_error}</div> : null}
                  </div>
                )}
              </div>
            ) : null}

            <div className="grid gap-2">
              <Label htmlFor="preferred_model">{t("model")}</Label>
              <select
                id="preferred_model"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
                value={preferredModel || ""}
                onChange={(e) => setPreferredModel(e.target.value || null)}
                disabled={!preferredProvider}
              >
                <option value="">{t("selectModel")}</option>
                {modelsForProvider.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center justify-end gap-4">
              {success && <span className="text-success text-sm">{success}</span>}
              {error && <span className="text-destructive text-sm">{error}</span>}
              <Button onClick={handleSave} disabled={saving || !canSave}>
                {saving ? t("saving") : t("saveDefault")}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
