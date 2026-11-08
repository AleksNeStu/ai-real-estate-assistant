'use client';

import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Modal } from '@/components/ui/modal';
import { createFilterPreset, ApiError } from '@/lib/api';
import type { FilterPreset } from '@/lib/types';

interface SavePresetDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  filters: Record<string, unknown>;
  onSuccess?: (preset: FilterPreset) => void;
}

export function SavePresetDialog({
  isOpen,
  onOpenChange,
  filters,
  onSuccess,
}: SavePresetDialogProps) {
  const t = useTranslations('search.preset');
  const tCommon = useTranslations('common');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleClose = () => {
    onOpenChange(false);
    setName('');
    setDescription('');
    setIsDefault(false);
    setError(null);
    setSuccess(false);
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError(t('nameRequired'));
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const preset = await createFilterPreset({
        name: name.trim(),
        description: description.trim() || undefined,
        filters,
        is_default: isDefault,
      });
      setSuccess(true);
      setTimeout(() => {
        handleClose();
        onSuccess?.(preset);
      }, 1000);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.category === 'auth') {
          setError(t('loginRequired'));
        } else {
          setError(err.message);
        }
      } else {
        setError(err instanceof Error ? err.message : t('saveFailed'));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={isOpen}
      onClose={handleClose}
      title={t('title')}
      closeLabel={tCommon('close')}
      footer={
        success ? null : (
          <>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={saving}
            >
              {tCommon('cancel')}
            </Button>
            <Button type="button" onClick={handleSave} disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                  {t('saving')}
                </>
              ) : (
                t('save')
              )}
            </Button>
          </>
        )
      }
    >
      {success ? (
        <div className="space-y-2 py-2 text-center">
          <p className="text-success font-medium">{t('saved')}</p>
          <p className="text-sm text-muted-foreground">{t('savedHint')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="preset-name">
              {t('name')} <span className="text-destructive">*</span>
            </Label>
            <Input
              id="preset-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('namePlaceholder')}
              maxLength={255}
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="preset-description">{t('description')}</Label>
            <textarea
              id="preset-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('descriptionPlaceholder')}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 resize-none"
              rows={2}
              maxLength={1000}
            />
          </div>

          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
              className="rounded border-input"
            />
            <span className="text-sm">{t('setDefault')}</span>
          </label>

          <p className="text-sm text-muted-foreground">{t('hint')}</p>

          {error ? (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      )}
    </Modal>
  );
}
