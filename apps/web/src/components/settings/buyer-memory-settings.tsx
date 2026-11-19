'use client';

import { useCallback, useEffect, useState } from 'react';
import { Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { Modal } from '@/components/ui/modal';
import { SettingsPanel, SettingsRow } from '@/components/settings/settings-panel';
import { EmptyState, ErrorState } from '@/components/ui/states';
import { ApiError, deleteBuyerMemory, getBuyerMemory } from '@/lib/api';
import type { BuyerMemoryFact } from '@/lib/api';

/**
 * The buyer memory, as the buyer sees it.
 *
 * The legal pages promise two things: that the memory can be seen and that it
 * can be deleted, "through your account". This panel is where both promises
 * are kept - it lists what is remembered, fact by fact, and it wipes the whole
 * memory behind a confirmation.
 *
 * The wording is the legal wording. The memory holds "a budget, areas you
 * ruled out, a feature you need, a listing you liked"; it steers the answers
 * and the listings that are shown; a fact is kept for a year and then expires.
 * The panel says the same things, so the two documents cannot drift apart.
 *
 * The list is a ledger - one rule opens it, one row per fact - and the delete
 * asks first, because a memory cannot be brought back.
 */

/**
 * The kinds the backend records, and the key each one is named by.
 *
 * The backend closes the set. A kind it does not know is shown as it arrived:
 * inventing a name for it would be a guess.
 */
const KIND_KEYS: Record<string, string> = {
  budget: 'budget',
  ruled_out_area: 'ruledOutArea',
  liked: 'liked',
  disliked: 'disliked',
  requirement: 'requirement',
  note: 'note',
};

function formatDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString();
}

export function BuyerMemorySettings({ className }: { className?: string }) {
  const t = useTranslations('pages.settings.memory');
  const tCommon = useTranslations('common');

  const [facts, setFacts] = useState<BuyerMemoryFact[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [signedOut, setSignedOut] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deletedCount, setDeletedCount] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await getBuyerMemory();
      setFacts(data.facts ?? []);
      setSignedOut(false);
    } catch (err) {
      // The endpoint asks for a real token, so an anonymous visitor is a 401.
      // That is not a failure: the memory belongs to a signed-in account.
      if (err instanceof ApiError && err.category === 'auth') {
        setFacts(null);
        setSignedOut(true);
      } else {
        setFacts(null);
        setLoadError(err instanceof Error ? err.message : t('loadFailed'));
      }
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleDelete = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      const result = await deleteBuyerMemory();
      setFacts([]);
      setDeletedCount(result.deleted);
      setConfirmOpen(false);
    } catch (err) {
      // The facts stay on the screen: nothing was erased, and the visitor is
      // told that.
      setDeleteError(err instanceof Error ? err.message : t('deleteFailed'));
      setConfirmOpen(false);
    } finally {
      setDeleting(false);
    }
  };

  const kindLabel = (fact: BuyerMemoryFact): string => {
    const key = KIND_KEYS[fact.kind];
    return key ? t(`kinds.${key}`) : fact.kind;
  };

  const list = facts ?? [];

  return (
    <SettingsPanel
      title={t('title')}
      description={t('description')}
      className={className}
      action={
        list.length > 0 ? <MonoAnnotation>{t('count', { count: list.length })}</MonoAnnotation> : null
      }
    >
      {loading ? (
        <p className="py-4 text-app text-muted-foreground">{tCommon('loading')}</p>
      ) : signedOut ? (
        <EmptyState title={t('signedOutTitle')} description={t('signedOutDescription')} />
      ) : loadError ? (
        <ErrorState
          title={t('loadFailed')}
          description={loadError}
          onRetry={() => void load()}
          retryLabel={tCommon('retry')}
        />
      ) : list.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        list.map((fact) => {
          const recorded = formatDate(fact.created_at);
          const expires = formatDate(fact.expires_at);
          return (
            <SettingsRow
              key={fact.id}
              label={kindLabel(fact)}
              action={
                <MonoAnnotation>
                  {expires ? t('expires', { date: expires }) : null}
                  {recorded ? `${expires ? ' · ' : ''}${t('recorded', { date: recorded })}` : null}
                </MonoAnnotation>
              }
            >
              <span className="text-app text-foreground">{fact.content}</span>
            </SettingsRow>
          );
        })
      )}

      {deleteError ? (
        <div className="py-4">
          <MonoAnnotation tone="destructive">{deleteError}</MonoAnnotation>
        </div>
      ) : null}

      {deletedCount !== null ? (
        <div className="py-4">
          <MonoAnnotation tone="success">{t('deleted', { count: deletedCount })}</MonoAnnotation>
        </div>
      ) : null}

      {list.length > 0 ? (
        <SettingsRow
          label={t('deleteLabel')}
          description={t('deleteDescription')}
          action={
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={() => setConfirmOpen(true)}
              disabled={deleting}
            >
              <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('deleteButton')}
            </Button>
          }
        />
      ) : null}

      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title={t('confirmTitle')}
        description={t('confirmDescription')}
        closeLabel={tCommon('close')}
        footer={
          <>
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmOpen(false)}
              disabled={deleting}
            >
              {tCommon('cancel')}
            </Button>
            <Button type="button" variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? t('deleting') : t('deleteConfirm')}
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted-foreground">{t('confirmNote')}</p>
      </Modal>
    </SettingsPanel>
  );
}
