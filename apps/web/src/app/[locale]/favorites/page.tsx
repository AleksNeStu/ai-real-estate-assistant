'use client';

import { useEffect, useState } from 'react';
import { FolderPlus, Loader2, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';

import { useFavorites } from '@/contexts/FavoritesContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Modal } from '@/components/ui/modal';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import { formatPrice, resolveLocale } from '@/lib/format';
import { formatMonthlyPayment } from '@/lib/mortgage';
import type { FavoriteWithProperty } from '@/lib/types';

/**
 * The favourites as a shelf of saved properties.
 *
 * The route is the prototype's arrangement: the collections stand in a rail
 * on the left, and the listings of the chosen collection stand in a grid on
 * the right. A listing is an object, so it keeps a card - but the card is
 * the prototype's card: the price in mono, the monthly estimate beside it,
 * the note the owner wrote under it, and one quiet action.
 *
 * The note is part of the object, not decoration: "viewing Sat 14 Nov, 10:30"
 * is the reason the listing was saved, so it lives on the card and not in a
 * drawer behind a click.
 */

function FavoriteCard({
  favorite,
  onRemove,
}: {
  favorite: FavoriteWithProperty;
  onRemove: (propertyId: string) => void;
}) {
  const t = useTranslations('pages.favorites');
  const tCard = useTranslations('property.card');
  const tLanding = useTranslations('landing.hero');
  const locale = useLocale();

  const property = favorite.property;

  if (!property) {
    return (
      <article
        data-testid="favorite-card"
        className="flex flex-col justify-center gap-1 rounded-lg border border-border bg-card p-4"
      >
        <span className="text-[14px] font-medium text-foreground">
          {t('list.unavailable')}
        </span>
        <MonoAnnotation>ID: {favorite.property_id}</MonoAnnotation>
      </article>
    );
  }

  const currency = property.currency || 'USD';
  const price = property.price ? formatPrice(property.price, currency, locale) : null;

  // A rented flat is priced per month already; a sold one is priced once,
  // and the estimate says what that price costs per month.
  const isRent = property.listing_type === 'rent';
  const monthly =
    !isRent && property.price
      ? formatMonthlyPayment(property.price, {
          currency,
          locale: resolveLocale(locale),
          interestRate: 6.5,
          downPaymentPercent: 20,
          loanYears: 30,
        })
      : null;
  const monthlyLabel = monthly
    ? tLanding('instrumentPerMonth', {
        amount: formatPrice(Math.round(monthly.raw), currency, locale),
      })
    : null;

  const facts = [
    property.rooms ? tCard('beds', { count: property.rooms }) : null,
    property.area_sqm ? `${property.area_sqm} ${tCard('areaUnit')}` : null,
    property.district || property.neighborhood || property.city || null,
  ].filter(Boolean);

  const street =
    property.address ||
    [property.city, property.country].filter(Boolean).join(', ') ||
    tCard('locationUnavailable');

  return (
    <article
      data-testid="favorite-card"
      className="flex flex-col overflow-hidden rounded-lg border border-border bg-card"
    >
      <div className="relative aspect-video w-full bg-muted">
        {property.images?.[0] ? (
          <img
            src={property.images[0]}
            alt={property.title || tCard('untitled')}
            className="size-full object-cover"
            loading="lazy"
          />
        ) : (
          <span className="absolute bottom-2 left-2 font-mono text-[10px] leading-4 text-muted-foreground">
            {tCard('imagePlaceholder')}
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1 p-3.5">
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-mono text-[16px] font-semibold leading-5 text-foreground">
            {price || tCard('priceOnRequest')}
          </span>
          {monthlyLabel ? (
            <span className="font-mono text-[12px] leading-4 text-success">{monthlyLabel}</span>
          ) : null}
        </div>

        <span className="text-[14px] font-medium leading-5 text-foreground">
          {property.title || tCard('untitled')}
        </span>

        {facts.length ? (
          <span className="text-[12px] leading-4 text-muted-foreground">{facts.join(' · ')}</span>
        ) : null}

        <span className="text-[12px] leading-4 text-muted-foreground">{street}</span>

        {favorite.notes ? (
          <span className="mt-1.5 rounded-sm bg-muted px-2 py-1.5 text-[12px] leading-4 text-foreground">
            {favorite.notes}
          </span>
        ) : null}

        <div className="mt-1.5 flex items-center gap-3">
          <button
            type="button"
            onClick={() => onRemove(property.id as string)}
            aria-label={t('list.remove')}
            className="inline-flex items-center gap-1.5 border-0 bg-transparent p-0 text-[12px] text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          >
            <Trash2 className="size-3.5" aria-hidden="true" />
            {t('list.remove')}
          </button>
        </div>
      </div>
    </article>
  );
}

export default function FavoritesPage() {
  const locale = useLocale();
  const t = useTranslations('pages.favorites');
  const tCommon = useTranslations('common');
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const {
    favorites,
    collections,
    isLoading,
    error,
    loadFavoritesWithProperties,
    refreshCollections,
    addCollection,
    toggleFavorite,
  } = useFavorites();

  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [showNewCollectionModal, setShowNewCollectionModal] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');

  useEffect(() => {
    if (isAuthenticated) {
      loadFavoritesWithProperties(selectedCollection || undefined);
      refreshCollections();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, selectedCollection]);

  // Auth loading state
  if (authLoading) {
    return (
      <div
        className="flex min-h-[400px] items-center justify-center px-6 py-8"
        role="status"
        aria-live="polite"
      >
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
        <span className="sr-only">{tCommon('loading')}</span>
      </div>
    );
  }

  // Not authenticated state
  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-[1200px] px-6 py-8">
        <PageHeader title={t('title')} description={t('description')} />
        <p className="mt-6 max-w-[560px] text-[15px] leading-[23px] text-muted-foreground">
          {t('auth.description')}
        </p>
        <Link href={`/${locale}/auth/login`} className="mt-4 inline-block">
          <Button>{t('auth.signIn')}</Button>
        </Link>
      </div>
    );
  }

  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) return;

    try {
      await addCollection(newCollectionName.trim());
      setNewCollectionName('');
      setShowNewCollectionModal(false);
    } catch (err) {
      console.error('Failed to create collection:', err);
    }
  };

  const handleRemove = async (propertyId: string) => {
    try {
      await toggleFavorite(propertyId);
      await loadFavoritesWithProperties(selectedCollection || undefined);
      await refreshCollections();
    } catch (err) {
      console.error('Failed to remove the favourite:', err);
    }
  };

  const railButtonClass = (active: boolean) =>
    [
      'flex w-full items-baseline justify-between gap-3 rounded-md border-0 px-2.5 py-2 text-left text-[14px] leading-5 transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50',
      active ? 'bg-muted font-medium text-foreground' : 'bg-transparent text-foreground hover:bg-muted/60',
    ].join(' ');

  return (
    <div className="flex min-h-[calc(100vh-56px)] flex-col">
      <div className="border-b border-border px-6 pb-5 pt-6">
        <PageHeader
          title={t('title')}
          description={t('description')}
          actions={
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowNewCollectionModal(true)}
            >
              <FolderPlus className="mr-2 h-4 w-4" aria-hidden="true" />
              {t('newCollection')}
            </Button>
          }
        >
          <MonoAnnotation>{t('savedCount', { count: favorites.length })}</MonoAnnotation>
        </PageHeader>
      </div>

      {error ? (
        <div className="px-6 pt-6">
          <p
            className="m-0 border-t border-destructive py-4 text-[14px] text-destructive"
            role="alert"
          >
            {error}
          </p>
        </div>
      ) : null}

      <div className="grid flex-1 grid-cols-1 lg:grid-cols-[260px_minmax(0,1fr)]">
        {/* The rail of collections. */}
        <nav
          className="border-b border-border p-3 lg:border-b-0 lg:border-r"
          aria-label={t('collections.aria')}
        >
          <p className="px-2.5 pb-1.5 pt-1 text-[12px] leading-4 text-muted-foreground">
            {t('collections.title')}
          </p>
          <div role="listbox" aria-label={t('collections.aria')}>
            <button
              type="button"
              onClick={() => setSelectedCollection(null)}
              className={railButtonClass(selectedCollection === null)}
              role="option"
              aria-selected={selectedCollection === null}
              aria-label={t('collections.all', { count: favorites.length })}
            >
              <span className="truncate">{t('collections.allLabel')}</span>
            </button>

            {collections.map((collection) => (
              <button
                type="button"
                key={collection.id}
                onClick={() => setSelectedCollection(collection.id)}
                className={railButtonClass(selectedCollection === collection.id)}
                role="option"
                aria-selected={selectedCollection === collection.id}
              >
                <span className="truncate">{collection.name}</span>
                <span className="shrink-0 font-mono text-[12px] leading-4 text-muted-foreground">
                  {collection.favorite_count}
                </span>
              </button>
            ))}
          </div>
        </nav>

        {/* The listings of the chosen collection. */}
        <main className="px-6 py-5">
          {isLoading ? (
            <div
              className="flex min-h-[300px] items-center justify-center"
              role="status"
              aria-live="polite"
            >
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
              <span className="sr-only">{t('list.loading')}</span>
            </div>
          ) : favorites.length === 0 ? (
            <div className="border-t border-foreground py-8">
              <p className="m-0 text-[15px] font-semibold leading-6 text-foreground">
                {t('list.empty')}
              </p>
              <p className="mt-2 max-w-md text-[14px] leading-5 text-muted-foreground">
                {t('list.emptyHint')}
              </p>
              <Link href={`/${locale}/search`} className="mt-4 inline-block">
                <Button variant="outline">{t('list.browse')}</Button>
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {favorites.map((favorite) => (
                <FavoriteCard
                  key={favorite.id}
                  favorite={favorite}
                  onRemove={handleRemove}
                />
              ))}
            </div>
          )}
        </main>
      </div>

      {/* New Collection Modal */}
      <Modal
        open={showNewCollectionModal}
        onClose={() => setShowNewCollectionModal(false)}
        title={t('newCollection')}
        closeLabel={tCommon('close')}
        footer={
          <>
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowNewCollectionModal(false)}
            >
              {tCommon('cancel')}
            </Button>
            <Button type="button" onClick={handleCreateCollection}>
              {tCommon('create')}
            </Button>
          </>
        }
      >
        <Label htmlFor="collection-name-input" className="sr-only">
          {t('collectionName')}
        </Label>
        <Input
          id="collection-name-input"
          type="text"
          value={newCollectionName}
          onChange={(e) => setNewCollectionName(e.target.value)}
          placeholder={t('collectionName')}
          autoFocus
        />
      </Modal>
    </div>
  );
}
