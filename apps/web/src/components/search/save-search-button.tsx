'use client';

import React, { useState } from 'react';
import { Bookmark, Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Modal } from '@/components/ui/modal';
import { createSavedSearch, ApiError } from '@/lib/api';
import type { AlertFrequency } from '@/lib/types';

interface SaveSearchButtonProps {
  filters: Record<string, unknown>;
  query?: string;
  onSaveSuccess?: () => void;
  className?: string;
}

export function SaveSearchButton({
  filters,
  query,
  onSaveSuccess,
  className,
}: SaveSearchButtonProps) {
  const t = useTranslations('savedSearches.dialog');
  const tCommon = useTranslations('common');
  const [isOpen, setIsOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState('');
  const [alertFrequency, setAlertFrequency] = useState<AlertFrequency>('daily');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleOpen = () => {
    setIsOpen(true);
    setError(null);
    setSuccess(false);
    // Pre-fill name from query if available
    if (query && !name) {
      setName(query.slice(0, 100));
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    setName('');
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
      await createSavedSearch({
        name: name.trim(),
        filters,
        alert_frequency: alertFrequency,
        notify_on_new: true,
        notify_on_price_drop: true,
      });
      setSuccess(true);
      setTimeout(() => {
        handleClose();
        onSaveSuccess?.();
      }, 1500);
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
    <>
      <Button type="button" variant="outline" onClick={handleOpen} className={className}>
        <Bookmark className="mr-2 h-4 w-4" aria-hidden="true" />
        {t('title')}
      </Button>

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
                    {tCommon('saving')}
                  </>
                ) : (
                  tCommon('save')
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
              <Label htmlFor="search-name">{t('name')}</Label>
              <Input
                id="search-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('namePlaceholder')}
                maxLength={255}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="alert-frequency">{t('alertFrequency')}</Label>
              <select
                id="alert-frequency"
                value={alertFrequency}
                onChange={(e) => setAlertFrequency(e.target.value as AlertFrequency)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              >
                <option value="instant">{t('frequencyInstant')}</option>
                <option value="daily">{t('frequencyDaily')}</option>
                <option value="weekly">{t('frequencyWeekly')}</option>
                <option value="none">{t('frequencyNone')}</option>
              </select>
            </div>

            <p className="text-sm text-muted-foreground">{t('hint')}</p>

            {error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
          </div>
        )}
      </Modal>
    </>
  );
}
