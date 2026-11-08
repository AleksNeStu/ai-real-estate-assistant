'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';

import {
  addFavorite,
  getFavoriteIds,
  getFavorites,
  getCollections,
  createCollection,
  updateCollection,
  deleteCollection,
  removeFavoriteByProperty,
  ApiError,
} from '@/lib/api';
import type { Collection, FavoriteWithProperty } from '@/lib/types';
import { useAuth } from './AuthContext';
import { useTranslations } from 'next-intl';

export interface FavoritesContextType {
  // State
  favoriteIds: Set<string>;
  favorites: FavoriteWithProperty[];
  collections: Collection[];
  isLoading: boolean;
  error: string | null;

  // Actions
  toggleFavorite: (propertyId: string) => Promise<boolean>;
  isFavorited: (propertyId: string) => boolean;
  refreshFavorites: () => Promise<void>;
  refreshCollections: () => Promise<void>;
  loadFavoritesWithProperties: (collectionId?: string) => Promise<void>;
  addCollection: (name: string, description?: string) => Promise<Collection>;
  updateCollection: (id: string, name?: string, description?: string) => Promise<void>;
  removeCollection: (id: string) => Promise<void>;
  clearError: () => void;
}

const defaultFavoritesContext: FavoritesContextType = {
  favoriteIds: new Set(),
  favorites: [],
  collections: [],
  isLoading: false,
  error: null,
  toggleFavorite: async () => false,
  isFavorited: () => false,
  refreshFavorites: async () => {},
  refreshCollections: async () => {},
  loadFavoritesWithProperties: async () => {},
  addCollection: async () => {
    throw new Error('FavoritesProvider not found');
  },
  updateCollection: async () => {
    throw new Error('FavoritesProvider not found');
  },
  removeCollection: async () => {
    throw new Error('FavoritesProvider not found');
  },
  clearError: () => {},
};

const FavoritesContext = createContext<FavoritesContextType>(defaultFavoritesContext);

interface FavoritesProviderProps {
  children: ReactNode;
}

export function FavoritesProvider({ children }: FavoritesProviderProps) {
  const { isAuthenticated, user } = useAuth();
  const t = useTranslations('favorites');
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());
  const [favorites, setFavorites] = useState<FavoriteWithProperty[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load favorite IDs when user authenticates
  useEffect(() => {
    if (isAuthenticated && user) {
      refreshFavorites();
      refreshCollections();
    } else {
      setFavoriteIds(new Set());
      setFavorites([]);
      setCollections([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user]);

  const refreshFavorites = useCallback(async () => {
    if (!isAuthenticated) return;

    setIsLoading(true);
    setError(null);

    try {
      const ids = await getFavoriteIds();
      setFavoriteIds(new Set(ids));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        // Not authenticated - clear state
        setFavoriteIds(new Set());
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load favorites');
      }
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  const refreshCollections = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      const response = await getCollections();
      setCollections(response.items);
    } catch (err) {
      // Silently fail - collections are optional
      console.error('Failed to load collections:', err);
    }
  }, [isAuthenticated]);

  const loadFavoritesWithProperties = useCallback(
    async (collectionId?: string) => {
      if (!isAuthenticated) return;

      setIsLoading(true);
      setError(null);

      try {
        const response = await getFavorites(collectionId);
        setFavorites(response.items);
        // Also update the IDs set
        setFavoriteIds(new Set(response.items.map((f) => f.property_id)));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load favorites');
      } finally {
        setIsLoading(false);
      }
    },
    [isAuthenticated]
  );

  const toggleFavorite = useCallback(
    async (propertyId: string): Promise<boolean> => {
      if (!isAuthenticated) {
        throw new Error(t('loginRequired'));
      }

      const wasFavorited = favoriteIds.has(propertyId);

      // Optimistic update
      setFavoriteIds((prev) => {
        const newSet = new Set(prev);
        if (wasFavorited) {
          newSet.delete(propertyId);
        } else {
          newSet.add(propertyId);
        }
        return newSet;
      });

      try {
        if (wasFavorited) {
          await removeFavoriteByProperty(propertyId);
          return false;
        } else {
          await addFavorite({ property_id: propertyId });
          return true;
        }
      } catch (err) {
        // Revert optimistic update
        setFavoriteIds((prev) => {
          const newSet = new Set(prev);
          if (wasFavorited) {
            newSet.add(propertyId);
          } else {
            newSet.delete(propertyId);
          }
          return newSet;
        });

        throw err;
      }
    },
    [isAuthenticated, favoriteIds, t]
  );

  const isFavorited = useCallback(
    (propertyId: string): boolean => {
      return favoriteIds.has(propertyId);
    },
    [favoriteIds]
  );

  const addCollectionFn = useCallback(
    async (name: string, description?: string): Promise<Collection> => {
      const collection = await createCollection({ name, description });
      setCollections((prev) => [...prev, collection]);
      return collection;
    },
    []
  );

  const updateCollectionFn = useCallback(
    async (id: string, name?: string, description?: string) => {
      const updated = await updateCollection(id, { name, description });
      setCollections((prev) => prev.map((c) => (c.id === id ? updated : c)));
    },
    []
  );

  const removeCollection = useCallback(async (id: string) => {
    await deleteCollection(id);
    setCollections((prev) => prev.filter((c) => c.id !== id));
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: FavoritesContextType = {
    favoriteIds,
    favorites,
    collections,
    isLoading,
    error,
    toggleFavorite,
    isFavorited,
    refreshFavorites,
    refreshCollections,
    loadFavoritesWithProperties,
    addCollection: addCollectionFn,
    updateCollection: updateCollectionFn,
    removeCollection,
    clearError,
  };

  return <FavoritesContext.Provider value={value}>{children}</FavoritesContext.Provider>;
}

export function useFavorites(): FavoritesContextType {
  return useContext(FavoritesContext);
}
