'use client';

/**
 * Service Worker Registration and Management Utilities
 * Handles PWA installation and service worker lifecycle
 */

import { info, warn } from '@/lib/logger';

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

let deferredInstallPrompt: BeforeInstallPromptEvent | null = null;

/**
 * Capture the browser's offer to install the app.
 *
 * The event is the only signal that the app can be installed at all: a
 * browser that does not fire it cannot install the app, so the button that
 * offers the install stays hidden where the install would not work.
 */
export function captureInstallPrompt(): void {
  if (typeof window === 'undefined') {
    return;
  }

  // Listen for the beforeinstallprompt event
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredInstallPrompt = e as BeforeInstallPromptEvent;
    window.dispatchEvent(new CustomEvent('pwa-install-available'));
  });

  // Listen for successful installation
  window.addEventListener('appinstalled', () => {
    info('PWA app installed');
    deferredInstallPrompt = null;
    window.dispatchEvent(new CustomEvent('pwa-installed'));
  });
}

/**
 * Announce a new version of the app.
 *
 * The worker that carries it waits until the visitor accepts the update -
 * an update that applied itself would replace the page under the reader.
 */
function announceUpdate(registration: ServiceWorkerRegistration): void {
  // A worker that finished installing before this page opened is already
  // waiting: the update is offered the moment the app opens.
  if (registration.waiting && navigator.serviceWorker.controller) {
    info('SW new content available');
    window.dispatchEvent(new CustomEvent('sw-update-available'));
    return;
  }

  registration.addEventListener('updatefound', () => {
    const newWorker = registration.installing;
    if (!newWorker) {
      return;
    }
    newWorker.addEventListener('statechange', () => {
      if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
        // New content is available, notify the user
        info('SW new content available');
        window.dispatchEvent(new CustomEvent('sw-update-available'));
      }
    });
  });
}

/**
 * Register the service worker
 * Should be called once when the app loads
 *
 * The environment is a parameter so the test can register the worker at all:
 * the build inlines the environment into the bundle, and a test bundle is
 * never a production one.
 */
export function registerServiceWorker(environment: string = process.env.NODE_ENV): void {
  captureInstallPrompt();

  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return;
  }

  // The worker caches what it serves, and what the development server serves
  // changes with every edit - a cached chunk is a stale chunk. The worker is
  // registered in the built application only.
  if (environment !== 'production') {
    return;
  }

  const register = async () => {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/',
      });

      info('SW registered', { scope: registration.scope });

      announceUpdate(registration);
    } catch (error) {
      console.error('[SW] Service Worker registration failed:', error);
    }
  };

  // The page may already be loaded when this runs - a slow first paint is
  // enough - and a `load` listener added after the event has fired never
  // fires at all.
  if (document.readyState === 'complete') {
    void register();
  } else {
    window.addEventListener('load', () => void register(), { once: true });
  }
}

/**
 * Apply the version that is waiting, and reload onto it.
 *
 * The worker is asked to take over first: the page reloads only once the new
 * worker controls it, so the reload lands on the new version instead of on
 * the old one it is trying to leave.
 *
 * The reload is the last thing it does: the promise settles only once the
 * new worker controls the page, so a caller that awaits it knows the page
 * it is about to show is the new one.
 */
export async function applyUpdate(): Promise<void> {
  const registration = await getServiceWorkerRegistration();
  const waiting = registration?.waiting;

  if (!waiting) {
    window.location.reload();
    return;
  }

  await new Promise<void>((resolve) => {
    navigator.serviceWorker.addEventListener('controllerchange', () => resolve(), { once: true });
    waiting.postMessage({ type: 'SKIP_WAITING' });
  });

  window.location.reload();
}

/**
 * Check if the app can be installed (PWA install prompt is available)
 */
export function canInstallPWA(): boolean {
  return deferredInstallPrompt !== null;
}

/**
 * Trigger the PWA install prompt
 * Returns true if the user accepted, false if dismissed
 */
export async function promptPWAInstall(): Promise<boolean> {
  if (!deferredInstallPrompt) {
    warn('PWA install prompt not available');
    return false;
  }

  try {
    await deferredInstallPrompt.prompt();
    const { outcome } = await deferredInstallPrompt.userChoice;

    if (outcome === 'accepted') {
      info('PWA user accepted install prompt');
      return true;
    } else {
      info('PWA user dismissed install prompt');
      return false;
    }
  } catch (error) {
    console.error('[PWA] Error showing install prompt:', error);
    return false;
  } finally {
    deferredInstallPrompt = null;
  }
}

/**
 * Check if the app is running as a standalone PWA
 */
export function isStandalonePWA(): boolean {
  if (typeof window === 'undefined') return false;

  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

/**
 * Check if the service worker is currently controlling the page
 */
export function isServiceWorkerActive(): boolean {
  if (typeof navigator === 'undefined') return false;
  return !!navigator.serviceWorker?.controller;
}

/**
 * Get the current service worker registration
 */
export async function getServiceWorkerRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
    return null;
  }

  const registration = await navigator.serviceWorker.getRegistration();
  return registration ?? null;
}

/**
 * Unregister the service worker (useful for debugging or cleanup)
 */
export async function unregisterServiceWorker(): Promise<boolean> {
  const registration = await getServiceWorkerRegistration();
  if (registration) {
    const success = await registration.unregister();
    if (success) {
      info('SW unregistered');
    }
    return success;
  }
  return false;
}
