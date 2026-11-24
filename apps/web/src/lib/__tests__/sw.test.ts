import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';

// Mock logger
jest.mock('@/lib/logger', () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
}));

// Store for window event listeners
const eventListeners: Record<string, ((...args: unknown[]) => void)[]> = {};

// Setup mocks on global window (already exists in jsdom)
const mockRegister = jest.fn();
const mockGetRegistration = jest.fn();
const mockUnregister = jest.fn();
const mockServiceWorkerListeners: Record<string, ((...args: unknown[]) => void)[]> = {};

/** The state of the document when the worker registers. */
let mockReadyState = 'complete';

beforeEach(() => {
  jest.clearAllMocks();
  for (const key in eventListeners) delete eventListeners[key];
  for (const key in mockServiceWorkerListeners) delete mockServiceWorkerListeners[key];

  // Mock navigator.serviceWorker on existing global
  Object.defineProperty(globalThis, 'navigator', {
    value: {
      serviceWorker: {
        register: mockRegister,
        getRegistration: mockGetRegistration,
        controller: null,
        addEventListener: (event: string, fn: (...args: unknown[]) => void) => {
          if (!mockServiceWorkerListeners[event]) mockServiceWorkerListeners[event] = [];
          mockServiceWorkerListeners[event].push(fn);
        },
      },
    },
    writable: true,
    configurable: true,
  });

  // The document is loaded unless a test says otherwise.
  mockReadyState = 'complete';
  Object.defineProperty(document, 'readyState', {
    get: () => mockReadyState,
    configurable: true,
  });

  // Mock matchMedia on jsdom window
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockReturnValue({ matches: false }),
  });

  // Spy on window.addEventListener to capture listeners
  jest
    .spyOn(window, 'addEventListener')
    .mockImplementation(
      (event: string, fn: EventListenerOrEventListenerObject | ((...args: unknown[]) => void)) => {
        if (!eventListeners[event]) eventListeners[event] = [];
        if (typeof fn === 'function') eventListeners[event].push(fn);
      }
    );

  jest.spyOn(window, 'dispatchEvent').mockReturnValue(true);
});

afterEach(() => {
  // The captured install offer lives in module state, and the module outlives
  // the test: a test that leaves the offer behind hands the next test an
  // install that is already on offer, and the order of the suite then decides
  // what that test sees. Firing `appinstalled` is what clears it.
  const listeners = eventListeners['appinstalled'];
  if (listeners) {
    for (const listener of listeners) listener();
  }
});

import {
  registerServiceWorker,
  captureInstallPrompt,
  canInstallPWA,
  promptPWAInstall,
  isStandalonePWA,
  isServiceWorkerActive,
  getServiceWorkerRegistration,
  unregisterServiceWorker,
  applyUpdate,
} from '@/lib/sw';

describe('registerServiceWorker', () => {
  it('adds load, beforeinstallprompt, appinstalled listeners', () => {
    mockReadyState = 'loading';
    registerServiceWorker('production');

    const events = (window.addEventListener as jest.Mock).mock.calls.map((c) => c[0]);
    expect(events).toContain('load');
    expect(events).toContain('beforeinstallprompt');
    expect(events).toContain('appinstalled');
  });

  it('registers service worker on load', async () => {
    mockReadyState = 'loading';
    mockRegister.mockResolvedValue({
      scope: '/',
      addEventListener: jest.fn(),
      installing: null,
    });

    registerServiceWorker('production');

    const loadListeners = eventListeners['load'];
    expect(loadListeners).toBeDefined();
    expect(loadListeners!.length).toBeGreaterThan(0);

    await loadListeners![0]();
    expect(mockRegister).toHaveBeenCalledWith('/sw.js', { scope: '/' });
  });

  it('registers at once when the page is already loaded', async () => {
    mockRegister.mockResolvedValue({
      scope: '/',
      addEventListener: jest.fn(),
      installing: null,
    });

    registerServiceWorker('production');

    expect(mockRegister).toHaveBeenCalledWith('/sw.js', { scope: '/' });
  });

  it('does not register in development', () => {
    registerServiceWorker('development');

    expect(mockRegister).not.toHaveBeenCalled();
  });

  it('handles registration failure gracefully', async () => {
    mockRegister.mockRejectedValue(new Error('Failed'));

    registerServiceWorker('production');

    if (eventListeners['load']) {
      await eventListeners['load'][0](); // Should not throw
    }
  });

  it('handles beforeinstallprompt event', () => {
    registerServiceWorker('production');

    const listeners = eventListeners['beforeinstallprompt'];
    expect(listeners).toBeDefined();

    const fakeEvent = { preventDefault: jest.fn() };
    if (listeners) {
      listeners[0](fakeEvent);
      expect(fakeEvent.preventDefault).toHaveBeenCalled();
    }
  });

  it('handles appinstalled event', () => {
    registerServiceWorker('production');

    const listeners = eventListeners['appinstalled'];
    expect(listeners).toBeDefined();
    if (listeners) {
      listeners[0](); // Should not throw
    }
  });
});

describe('captureInstallPrompt', () => {
  it('offers the install once the browser fires the event', () => {
    captureInstallPrompt();

    expect(canInstallPWA()).toBe(false);

    const listeners = eventListeners['beforeinstallprompt'];
    listeners![0]({ preventDefault: jest.fn() });

    expect(canInstallPWA()).toBe(true);
  });

  it('forgets the offer once the app is installed', () => {
    captureInstallPrompt();

    eventListeners['beforeinstallprompt']![0]({ preventDefault: jest.fn() });
    expect(canInstallPWA()).toBe(true);

    eventListeners['appinstalled']![0]();

    expect(canInstallPWA()).toBe(false);
  });
});

describe('canInstallPWA', () => {
  it('returns false when no deferred prompt', () => {
    expect(canInstallPWA()).toBe(false);
  });
});

describe('promptPWAInstall', () => {
  it('returns false when no deferred prompt', async () => {
    const result = await promptPWAInstall();
    expect(result).toBe(false);
  });
});

describe('isStandalonePWA', () => {
  it('returns false when matchMedia returns false', () => {
    (window.matchMedia as jest.Mock).mockReturnValue({ matches: false });
    expect(isStandalonePWA()).toBe(false);
  });

  it('returns true when matchMedia matches standalone', () => {
    (window.matchMedia as jest.Mock).mockReturnValue({ matches: true });
    expect(isStandalonePWA()).toBe(true);
  });
});

describe('isServiceWorkerActive', () => {
  it('returns false when no controller', () => {
    expect(isServiceWorkerActive()).toBe(false);
  });

  it('returns true when controller exists', () => {
    Object.defineProperty(globalThis, 'navigator', {
      value: {
        serviceWorker: {
          controller: { state: 'activated' },
        },
      },
      writable: true,
      configurable: true,
    });

    expect(isServiceWorkerActive()).toBe(true);
  });
});

describe('getServiceWorkerRegistration', () => {
  it('returns null when no registration', async () => {
    mockGetRegistration.mockResolvedValue(undefined);
    const result = await getServiceWorkerRegistration();
    expect(result).toBeNull();
  });

  it('returns registration when found', async () => {
    const mockReg = { scope: '/' };
    mockGetRegistration.mockResolvedValue(mockReg);
    const result = await getServiceWorkerRegistration();
    expect(result).toBe(mockReg);
  });
});

describe('unregisterServiceWorker', () => {
  it('returns false when no registration', async () => {
    mockGetRegistration.mockResolvedValue(undefined);
    const result = await unregisterServiceWorker('production');
    expect(result).toBe(false);
  });

  it('returns true when unregistration succeeds', async () => {
    mockGetRegistration.mockResolvedValue({ unregister: mockUnregister });
    mockUnregister.mockResolvedValue(true);
    const result = await unregisterServiceWorker('production');
    expect(result).toBe(true);
  });

  it('returns false when unregistration fails', async () => {
    mockGetRegistration.mockResolvedValue({ unregister: mockUnregister });
    mockUnregister.mockResolvedValue(false);
    const result = await unregisterServiceWorker('production');
    expect(result).toBe(false);
  });
});

describe('applyUpdate', () => {
  /** Every pending microtask has run. */
  const flushMicrotasks = () => new Promise((resolve) => setTimeout(resolve, 0));

  /** The navigation jsdom refuses to make, silenced for the test. */
  let consoleError: jest.SpiedFunction<typeof console.error>;

  beforeEach(() => {
    consoleError = jest.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  afterEach(() => {
    consoleError.mockRestore();
  });

  it('asks the waiting worker to take over', async () => {
    const postMessage = jest.fn();
    mockGetRegistration.mockResolvedValue({
      waiting: { postMessage, state: 'installed' },
    });

    const applied = applyUpdate();
    await flushMicrotasks();

    expect(postMessage).toHaveBeenCalledWith({ type: 'SKIP_WAITING' });

    // The new worker has to control the page before the page reloads.
    mockServiceWorkerListeners['controllerchange']![0]();
    await applied;
  });

  it('reloads once the new worker controls the page', async () => {
    const postMessage = jest.fn();
    mockGetRegistration.mockResolvedValue({
      waiting: { postMessage, state: 'installed' },
    });

    let settled = false;
    const applied = applyUpdate().then(() => {
      settled = true;
    });

    await flushMicrotasks();
    expect(settled).toBe(false);

    mockServiceWorkerListeners['controllerchange']![0]();
    await applied;
    expect(settled).toBe(true);
  });

  it('reloads at once when no version is waiting', async () => {
    mockGetRegistration.mockResolvedValue({ waiting: null });

    await applyUpdate();
  });
});
