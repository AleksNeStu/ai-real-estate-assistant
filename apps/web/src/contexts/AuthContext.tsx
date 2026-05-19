'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';

import { ApiError } from '@/lib/api';
import * as authApi from '@/lib/auth';
import type { User } from '@/lib/auth';
import { updateSentryUser } from '@/sentry.client';

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isDemoMode: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
  setIsDemoMode: (value: boolean) => void;
}

// Default context value for SSR/SSG when AuthProvider is not wrapping the component
const defaultAuthContext: AuthContextType = {
  user: null,
  isLoading: false,
  isAuthenticated: false,
  isDemoMode: false,
  error: null,
  login: async () => {
    throw new Error('AuthProvider not found');
  },
  register: async () => {
    throw new Error('AuthProvider not found');
  },
  logout: async () => {
    throw new Error('AuthProvider not found');
  },
  refreshUser: async () => {
    // Silent no-op during SSR
  },
  clearError: () => {},
  setIsDemoMode: () => {},
};

const AuthContext = createContext<AuthContextType>(defaultAuthContext);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch current user on mount
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const currentUser = await authApi.getCurrentUser();
        setUser(currentUser);
        setIsDemoMode(false);
      } catch (err) {
        if (err instanceof ApiError) {
          // 401 = JWT enabled, user not logged in
          // 404 = JWT completely disabled (auth endpoint doesn't exist)
          // Both mean: no authenticated user -> demo mode
          if (err.status === 401 || err.status === 404) {
            setIsDemoMode(true);
          } else {
            setError(err.message);
          }
        } else {
          setError('Failed to fetch user');
        }
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchUser();
  }, []);

  // Update Sentry user context when user state changes
  useEffect(() => {
    updateSentryUser();
  }, [user]);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    setIsLoading(true);

    try {
      const response = await authApi.login(email, password);
      setUser(response.user);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Login failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    setError(null);
    setIsLoading(true);

    try {
      const response = await authApi.register(email, password, fullName);
      setUser(response.user);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Registration failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setError(null);
    setIsLoading(true);

    try {
      await authApi.logout();
      setUser(null);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Logout failed';
      setError(message);
      // Still clear user on error
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await authApi.getCurrentUser();
      setUser(currentUser);
      setIsDemoMode(false);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 404)) {
        setUser(null);
        setIsDemoMode(true);
      }
      setError(err instanceof Error ? err.message : 'Failed to refresh user');
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    isDemoMode,
    error,
    login,
    register,
    logout,
    refreshUser,
    clearError,
    setIsDemoMode,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access the auth context.
 *
 * Returns default values when used outside of AuthProvider (e.g., during SSR).
 */
export function useAuth(): AuthContextType {
  return useContext(AuthContext);
}
