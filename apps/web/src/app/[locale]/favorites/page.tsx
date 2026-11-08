'use client';

import { useEffect, useState } from 'react';
import { FolderPlus, Heart, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';

import { useFavorites } from '@/contexts/FavoritesContext';
import { useAuth } from '@/contexts/AuthContext';
import { PropertyCard } from '@/components/property';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Modal } from '@/components/ui/modal';
import { PageHeader } from '@/components/ui/page-header';

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
        className="container mx-auto px-4 py-8 flex items-center justify-center min-h-[400px]"
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
      <div className="container mx-auto px-4 py-8">
        <PageHeader title={t('title')} description={t('description')} />
        <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
          <Heart className="h-16 w-16 text-muted-foreground mb-4" aria-hidden="true" />
          <p className="text-lg font-medium mb-2">{t('auth.signInPrompt')}</p>
          <p className="text-muted-foreground mb-6">{t('auth.description')}</p>
          <Link href={`/${locale}/auth/login`}>
            <Button>{t('auth.signIn')}</Button>
          </Link>
        </div>
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

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col space-y-8">
        {/* Header */}
        <PageHeader
          title={t('title')}
          description={t('description')}
          actions={
            <Button variant="outline" onClick={() => setShowNewCollectionModal(true)}>
              <FolderPlus className="h-4 w-4 mr-2" />
              {t('newCollection')}
            </Button>
          }
        >
          <p className="text-muted-foreground">{t('savedCount', { count: favorites.length })}</p>
        </PageHeader>

        {/* Error state */}
        {error && (
          <div
            className="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive"
            role="alert"
          >
            <p>{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Collections Sidebar */}
          <div className="space-y-4">
            <div className="rounded-lg border bg-card p-4">
              <h2 className="font-semibold mb-4">{t('collections.title')}</h2>
              <div className="space-y-2" role="listbox" aria-label={t('collections.aria')}>
                <button
                  type="button"
                  onClick={() => setSelectedCollection(null)}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 ${
                    selectedCollection === null
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-muted'
                  }`}
                  role="option"
                  aria-selected={selectedCollection === null}
                >
                  {t('collections.all', { count: favorites.length })}
                </button>

                {collections.map((collection) => (
                  <button
                    type="button"
                    key={collection.id}
                    onClick={() => setSelectedCollection(collection.id)}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50 ${
                      selectedCollection === collection.id
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-muted'
                    }`}
                    role="option"
                    aria-selected={selectedCollection === collection.id}
                  >
                    {collection.name} ({collection.favorite_count})
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Favorites Grid */}
          <div className="md:col-span-3">
            {isLoading ? (
              <div
                className="flex items-center justify-center min-h-[300px]"
                role="status"
                aria-live="polite"
              >
                <Loader2
                  className="h-8 w-8 animate-spin text-muted-foreground"
                  aria-hidden="true"
                />
                <span className="sr-only">{t('list.loading')}</span>
              </div>
            ) : favorites.length === 0 ? (
              <div className="flex flex-col items-center justify-center min-h-[300px] text-center border rounded-lg border-dashed">
                <Heart className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold">{t('list.empty')}</h3>
                <p className="text-sm text-muted-foreground mt-2 max-w-sm">{t('list.emptyHint')}</p>
                <Link href={`/${locale}/search`}>
                  <Button variant="outline" className="mt-4">
                    {t('list.browse')}
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {favorites.map((favorite) => (
                  <div key={favorite.id} className="relative">
                    {favorite.property ? (
                      <PropertyCard property={favorite.property} />
                    ) : (
                      <div className="rounded-lg border bg-card p-6 text-center">
                        <p className="text-muted-foreground">{t('list.unavailable')}</p>
                        <p className="text-xs text-muted-foreground mt-2">
                          ID: {favorite.property_id}
                        </p>
                      </div>
                    )}
                    {favorite.notes && (
                      <div className="mt-2 p-2 bg-muted rounded text-sm">{favorite.notes}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
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
