/**
 * Tests for Tools page.
 *
 * Tests for the multi-section tools page including:
 * - Page rendering with all tool sections
 * - Mortgage calculator form submission
 * - Compare properties form
 * - Error states
 * - Loading states
 *
 * Note: jest.mock('@/lib/api') does not work in this project (Jest 30 + next/jest).
 * Instead, we mock the global `fetch` to return appropriate API responses.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach } from '@jest/globals';

import ToolsPage from '../page';

// Mock window.URL.createObjectURL for export tests
global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
global.URL.revokeObjectURL = jest.fn();

// Get reference to the global mockFetch from jest.setup.ts
const mockFetch = globalThis.fetch as jest.Mock;

// Registry of URL patterns to mock responses
// Each entry: { pattern: string|RegExp, response: unknown, isError: boolean }
let fetchMockRegistry: Array<{
  pattern: string | RegExp;
  response: unknown;
  isError: boolean;
}> = [];

/**
 * Create a mock Response object.
 */
function createMockResponse(body: unknown, ok: boolean = true, status: number = 200) {
  return Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(typeof body === 'string' ? body : JSON.stringify(body)),
    headers: new Headers(),
  });
}

/**
 * Apply the fetch mock registry as the mock implementation.
 */
function applyFetchMock() {
  mockFetch.mockImplementation((url: string) => {
    for (const entry of fetchMockRegistry) {
      const matches =
        typeof entry.pattern === 'string' ? url.includes(entry.pattern) : entry.pattern.test(url);
      if (matches) {
        if (entry.isError) {
          const errorBody = { detail: entry.response };
          return createMockResponse(errorBody, false, 500);
        }
        return createMockResponse(entry.response, true, 200);
      }
    }
    // Default: return empty success response
    return createMockResponse({ message: 'success' }, true, 200);
  });
}

/**
 * Register a successful fetch mock response for a URL pattern.
 */
function mockFetchResponse(urlPattern: string | RegExp, response: unknown) {
  fetchMockRegistry.push({ pattern: urlPattern, response, isError: false });
  applyFetchMock();
}

/**
 * Register an error fetch mock for a URL pattern.
 */
function mockFetchError(urlPattern: string | RegExp, errorMessage: string) {
  fetchMockRegistry.push({ pattern: urlPattern, response: errorMessage, isError: true });
  applyFetchMock();
}

/**
 * Helper to render the ToolsPage and wait for async effects to settle.
 * The PromptTemplatesSection fires an async useEffect that loads templates.
 */
async function renderToolsPage(tool?: string) {
  let utils: ReturnType<typeof render>;
  await act(async () => {
    utils = render(<ToolsPage initialTool={tool ? `tool-${tool}` : undefined} />);
  });
  return utils!;
}

describe('ToolsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset the fetch mock registry
    fetchMockRegistry = [];
    // Default: listPromptTemplates returns empty array so PromptTemplatesSection renders
    mockFetchResponse('prompt-templates', []);
  });

  // ---------- Page Structure ----------

  it('renders the page heading', async () => {
    await renderToolsPage();
    expect(screen.getByText('Tools')).toBeInTheDocument();
  });

  it('lists every tool in the tool list, and shows one at a time', async () => {
    await renderToolsPage();
    // The console shows one tool at a time; the list carries the rest.
    for (const name of [
      'mortgage_calculator',
      'compare_properties',
      'price_analysis',
      'location_analysis',
      'neighborhood_quality',
      'prompt_templates',
      'valuation',
      'legal_check',
      'enrich_address',
      'crm_sync_contact',
    ]) {
      expect(screen.getByTestId(`tool-${name}`)).toBeInTheDocument();
    }
    expect(screen.getByText('Mortgage Calculator')).toBeInTheDocument();
    expect(screen.queryByText('Compare Properties')).not.toBeInTheDocument();
  });

  // ---------- Mortgage Calculator ----------

  describe('MortgageSection', () => {
    it('renders mortgage input fields', async () => {
      await renderToolsPage();
      expect(screen.getByPlaceholderText('Property price')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Down payment %')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Interest rate %')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Loan years')).toBeInTheDocument();
    });

    it('renders the Calculate button', async () => {
      await renderToolsPage();
      expect(screen.getByRole('button', { name: /calculate/i })).toBeInTheDocument();
    });

    it('calculates mortgage and shows result', async () => {
      mockFetchResponse('mortgage-calculator', { monthly_payment: 2533.43 });

      await renderToolsPage();

      const priceInput = screen.getByPlaceholderText('Property price');
      await act(async () => {
        fireEvent.change(priceInput, { target: { value: '500000' } });
      });

      const calcButton = screen.getByRole('button', { name: /calculate/i });
      await act(async () => {
        fireEvent.click(calcButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/Monthly payment: 2533.43/)).toBeInTheDocument();
      });
    });

    it('shows error on API failure', async () => {
      mockFetchError('mortgage-calculator', 'Calculation failed');

      await renderToolsPage();

      const priceInput = screen.getByPlaceholderText('Property price');
      await act(async () => {
        fireEvent.change(priceInput, { target: { value: '100000' } });
      });

      const calcButton = screen.getByRole('button', { name: /calculate/i });
      await act(async () => {
        fireEvent.click(calcButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Calculation failed')).toBeInTheDocument();
      });
    });
  });

  // ---------- Compare Properties ----------

  describe('CompareSection', () => {
    it('renders the Compare section', async () => {
      await renderToolsPage('compare_properties');
      expect(screen.getByPlaceholderText('IDs comma-separated')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^compare$/i })).toBeInTheDocument();
    });

    it('compares properties and shows summary', async () => {
      mockFetchResponse('compare-properties', {
        summary: { count: 3, min_price: 100000, max_price: 500000, price_difference: 400000 },
      });

      await renderToolsPage('compare_properties');

      const idsInput = screen.getByPlaceholderText('IDs comma-separated');
      await act(async () => {
        fireEvent.change(idsInput, { target: { value: 'p1, p2, p3' } });
      });

      const compareButton = screen.getByRole('button', { name: /^compare$/i });
      await act(async () => {
        fireEvent.click(compareButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Count: 3')).toBeInTheDocument();
        expect(screen.getByText('Min price: 100000')).toBeInTheDocument();
      });
    });

    it('shows error when compare fails', async () => {
      mockFetchError('compare-properties', 'Compare failed');

      await renderToolsPage('compare_properties');

      const idsInput = screen.getByPlaceholderText('IDs comma-separated');
      await act(async () => {
        fireEvent.change(idsInput, { target: { value: 'p1' } });
      });

      const compareButton = screen.getByRole('button', { name: /^compare$/i });
      await act(async () => {
        fireEvent.click(compareButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Compare failed')).toBeInTheDocument();
      });
    });
  });

  // ---------- Price Analysis ----------

  describe('PriceAnalysisSection', () => {
    it('renders the Price Analysis section', async () => {
      await renderToolsPage('price_analysis');
      expect(screen.getByPlaceholderText('Query (e.g., city or type)')).toBeInTheDocument();
      expect(screen.getAllByRole('button', { name: /^analyze$/i }).length).toBeGreaterThan(0);
    });

    it('analyzes price and shows results', async () => {
      mockFetchResponse('tools/price-analysis', {
        count: 42,
        average_price: 350000,
        median_price: 320000,
      });

      await renderToolsPage('price_analysis');

      const queryInput = screen.getByPlaceholderText('Query (e.g., city or type)');
      await act(async () => {
        fireEvent.change(queryInput, { target: { value: 'Warsaw' } });
      });

      const analyzeButtons = screen.getAllByRole('button', { name: /^analyze$/i });
      await act(async () => {
        fireEvent.click(analyzeButtons[0]);
      });

      await waitFor(() => {
        expect(screen.getByText('Count: 42')).toBeInTheDocument();
        expect(screen.getByText('Average price: 350000')).toBeInTheDocument();
      });
    });
  });

  // ---------- Location Analysis ----------

  describe('LocationAnalysisSection', () => {
    it('renders the Location Analysis section', async () => {
      await renderToolsPage('location_analysis');
      const pidInputs = screen.getAllByPlaceholderText('Property ID');
      expect(pidInputs.length).toBeGreaterThanOrEqual(1);
    });

    it('analyzes location and shows results', async () => {
      mockFetchResponse('tools/location-analysis', {
        city: 'Berlin',
        neighborhood: 'Mitte',
        lat: 52.52,
        lon: 13.4,
      });

      await renderToolsPage('location_analysis');

      const locationHeading = screen.getByText('Location Analysis');
      const section = locationHeading.closest('section');

      const pidInput = section?.querySelector(
        'input[placeholder="Property ID"]'
      ) as HTMLInputElement;
      expect(pidInput).toBeTruthy();
      await act(async () => {
        fireEvent.change(pidInput, { target: { value: 'prop-123' } });
      });

      const analyzeBtn = section?.querySelector('button');
      expect(analyzeBtn).toBeTruthy();
      await act(async () => {
        fireEvent.click(analyzeBtn!);
      });

      await waitFor(() => {
        expect(section!.textContent).toContain('Berlin');
        expect(section!.textContent).toContain('Mitte');
      });
    });
  });

  // ---------- Error State ----------

  describe('Error Handling', () => {
    it('shows hint for data enrichment disabled errors', async () => {
      mockFetchError('mortgage-calculator', 'Data enrichment disabled for this endpoint');

      await renderToolsPage();

      const priceInput = screen.getByPlaceholderText('Property price');
      await act(async () => {
        fireEvent.change(priceInput, { target: { value: '100000' } });
      });

      const calcButton = screen.getByRole('button', { name: /calculate/i });
      await act(async () => {
        fireEvent.click(calcButton);
      });

      await waitFor(() => {
        expect(
          screen.getByText(/Enable on the backend: set DATA_ENRICHMENT_ENABLED=true/)
        ).toBeInTheDocument();
      });
    });

    it('shows hint for CRM connector errors', async () => {
      mockFetchError('crm-sync-contact', 'CRM connector not configured');

      await renderToolsPage('crm_sync_contact');

      const nameInput = screen.getByPlaceholderText('Name');
      await act(async () => {
        fireEvent.change(nameInput, { target: { value: 'John' } });
      });

      const syncButton = screen.getByRole('button', { name: /^sync$/i });
      await act(async () => {
        fireEvent.click(syncButton);
      });

      await waitFor(() => {
        expect(
          screen.getByText(/Configure on the backend: set CRM_WEBHOOK_URL/)
        ).toBeInTheDocument();
      });
    });
  });
});
