'use client';

import { useState } from 'react';
import { X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import type { DataSource, DataSourceUpdate, DataSourceStatus } from '@/lib/types';

interface EditDataSourceDialogProps {
  source: DataSource | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (id: string, data: DataSourceUpdate) => void;
  isSaving?: boolean;
}

const STATUS_VALUES: DataSourceStatus[] = ['pending', 'active', 'disabled'];

const PROPERTY_TYPES = ['apartment', 'house', 'land', 'commercial', 'garage'] as const;
const LISTING_TYPES = ['sale', 'rent'] as const;

export function EditDataSourceDialog({
  source,
  isOpen,
  onClose,
  onSave,
  isSaving = false,
}: EditDataSourceDialogProps) {
  const t = useTranslations('pages.admin.dataSources');
  const tCommon = useTranslations('common');
  // key={editSource?.id} in parent ensures remount on source change
  const [name, setName] = useState(source?.name ?? '');
  const [status, setStatus] = useState<DataSourceStatus>(source?.status ?? 'pending');
  const [autoSync, setAutoSync] = useState(source?.auto_sync_enabled ?? false);
  const [syncSchedule, setSyncSchedule] = useState(source?.sync_schedule ?? '');
  const [config, setConfig] = useState<Record<string, unknown>>(
    source?.config ? { ...source.config } : {}
  );

  if (!isOpen || !source) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const update: DataSourceUpdate = {};
    if (name !== source.name) update.name = name;
    if (status !== source.status) update.status = status;
    if (autoSync !== source.auto_sync_enabled) update.auto_sync_enabled = autoSync;
    if (syncSchedule !== (source.sync_schedule ?? ''))
      update.sync_schedule = syncSchedule || undefined;
    if (JSON.stringify(config) !== JSON.stringify(source.config)) update.config = config;
    onSave(source.id, update);
  };

  const updateConfigField = (key: string, value: unknown) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const configKeys = Object.keys(config);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-dialog-title"
    >
      {/* The backdrop only closes the dialog for the mouse — the cancel button and Escape serve the keyboard. */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />

      <div className="relative bg-card rounded-lg shadow-lg w-full max-w-lg mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold" id="edit-dialog-title">
            {t('editDialog.title')}
          </h3>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Basic Info */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">
              {t('editDialog.sectionBasic')}
            </h4>

            <div>
              <label htmlFor="edit-name" className="block text-sm font-medium mb-1">
                {t('editDialog.name')}
              </label>
              <input
                id="edit-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                required
                minLength={1}
                maxLength={255}
              />
            </div>

            <div>
              <label htmlFor="edit-status" className="block text-sm font-medium mb-1">
                {t('editDialog.status')}
              </label>
              <select
                id="edit-status"
                value={status}
                onChange={(e) => setStatus(e.target.value as DataSourceStatus)}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              >
                {STATUS_VALUES.map((value) => (
                  <option key={value} value={value}>
                    {t(`editDialog.status${value.charAt(0).toUpperCase()}${value.slice(1)}`)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Config Filters */}
          {configKeys.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-muted-foreground">
                {t('editDialog.sectionFilters')}
              </h4>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(config).map(([key, value]) => (
                  <div
                    key={key}
                    className={key === 'portal' || key === 'source_name' ? 'col-span-2' : ''}
                  >
                    <label
                      htmlFor={`edit-cfg-${key}`}
                      className="block text-xs font-medium mb-1 capitalize"
                    >
                      {key.replace(/_/g, ' ')}
                    </label>
                    {renderConfigInput(key, value, updateConfigField, t)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Scheduling */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">
              {t('editDialog.sectionScheduling')}
            </h4>

            <div className="flex items-center gap-2">
              <input
                id="edit-auto-sync"
                type="checkbox"
                checked={autoSync}
                onChange={(e) => setAutoSync(e.target.checked)}
                className="rounded border"
              />
              <label htmlFor="edit-auto-sync" className="text-sm">
                {t('editDialog.autoSyncEnabled')}
              </label>
            </div>

            <div>
              <label htmlFor="edit-schedule" className="block text-sm font-medium mb-1">
                {t('editDialog.syncSchedule')}
              </label>
              <input
                id="edit-schedule"
                type="text"
                value={syncSchedule}
                onChange={(e) => setSyncSchedule(e.target.value)}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                placeholder={t('editDialog.syncSchedulePlaceholder')}
              />
              <p className="text-xs text-muted-foreground mt-1">{t('editDialog.cronHint')}</p>
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t">
          <Button variant="outline" onClick={onClose} disabled={isSaving}>
            {tCommon('cancel')}
          </Button>
          <Button
            onClick={handleSubmit as unknown as () => void}
            disabled={isSaving || !name.trim()}
          >
            {isSaving ? t('editDialog.saving') : t('editDialog.saveChanges')}
          </Button>
        </div>
      </div>
    </div>
  );
}

function renderConfigInput(
  key: string,
  value: unknown,
  onChange: (key: string, value: unknown) => void,
  t: (key: string) => string
) {
  if (key === 'property_type') {
    return (
      <select
        id={`edit-cfg-${key}`}
        value={String(value ?? '')}
        onChange={(e) => onChange(key, e.target.value)}
        className="w-full rounded-md border bg-background px-3 py-2 text-sm"
      >
        <option value="">—</option>
        {PROPERTY_TYPES.map((type) => (
          <option key={type} value={type}>
            {t(`editDialog.propertyType${type.charAt(0).toUpperCase()}${type.slice(1)}`)}
          </option>
        ))}
      </select>
    );
  }

  if (key === 'listing_type') {
    return (
      <select
        id={`edit-cfg-${key}`}
        value={String(value ?? '')}
        onChange={(e) => onChange(key, e.target.value)}
        className="w-full rounded-md border bg-background px-3 py-2 text-sm"
      >
        <option value="">—</option>
        {LISTING_TYPES.map((type) => (
          <option key={type} value={type}>
            {t(`editDialog.listingType${type.charAt(0).toUpperCase()}${type.slice(1)}`)}
          </option>
        ))}
      </select>
    );
  }

  if (
    key === 'min_price' ||
    key === 'max_price' ||
    key === 'min_rooms' ||
    key === 'max_rooms' ||
    key === 'limit'
  ) {
    return (
      <input
        id={`edit-cfg-${key}`}
        type="number"
        value={value != null ? String(value) : ''}
        onChange={(e) => onChange(key, e.target.value ? Number(e.target.value) : null)}
        className="w-full rounded-md border bg-background px-3 py-2 text-sm"
        min={0}
      />
    );
  }

  return (
    <input
      id={`edit-cfg-${key}`}
      type="text"
      value={String(value ?? '')}
      onChange={(e) => onChange(key, e.target.value)}
      className="w-full rounded-md border bg-background px-3 py-2 text-sm"
    />
  );
}
