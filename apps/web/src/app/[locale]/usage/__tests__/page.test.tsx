/**
 * Tests for Usage Dashboard page.
 *
 * Tests for the user activity analytics dashboard including:
 * - Summary metrics display
 * - Loading states
 * - Error handling
 * - Export functionality
 * - Tab navigation presence
 * - Period display
 * - Refresh interaction
 *
 * Note: jest.mock('@/lib/api') does not work in this project (Jest 30 + next/jest).
 * Instead, we mock the global `fetch` to return appropriate API responses.
 */

import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import UsagePage from '../page';
import type { UserActivitySummary, UserActivityTrendPoint } from '@/lib/types';

// Mock window.URL.createObjectURL and revokeObjectURL
global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
global.URL.revokeObjectURL = jest.fn();

// Get reference to the global mockFetch from jest.setup.ts
const mockFetch = globalThis.fetch as jest.Mock;

// Registry of URL patterns to mock responses
let fetchMockRegistry: Array<{
  pattern: string | RegExp;
  response: unknown;
  isError: boolean;
  isBlob?: boolean;
}> = [];

function createMockResponse(body: unknown, ok: boolean = true, status: number = 200) {
  return Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(typeof body === 'string' ? body : JSON.stringify(body)),
    headers: new Headers(),
  });
}

function applyFetchMock() {
  mockFetch.mockImplementation((url: string) => {
    for (const entry of fetchMockRegistry) {
      const matches =
        typeof entry.pattern === 'string' ? url.includes(entry.pattern) : entry.pattern.test(url);
      if (matches) {
        if (entry.isError) {
          return createMockResponse({ detail: entry.response }, false, 500);
        }
        if (entry.isBlob) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(entry.response),
            text: () => Promise.resolve('csv,data'),
            headers: new Headers({ 'content-type': 'text/csv' }),
            blob: () => Promise.resolve(new Blob(['csv,data'], { type: 'text/csv' })),
          });
        }
        return createMockResponse(entry.response, true, 200);
      }
    }
    return createMockResponse({ message: 'success' }, true, 200);
  });
}

function mockFetchResponse(urlPattern: string | RegExp, response: unknown) {
  fetchMockRegistry.push({ pattern: urlPattern, response, isError: false });
  applyFetchMock();
}

function mockFetchError(urlPattern: string | RegExp, errorMessage: string) {
  fetchMockRegistry.push({ pattern: urlPattern, response: errorMessage, isError: true });
  applyFetchMock();
}

function mockFetchBlob(urlPattern: string | RegExp) {
  fetchMockRegistry.push({ pattern: urlPattern, response: null, isError: false, isBlob: true });
  applyFetchMock();
}

describe('UsagePage', () => {
  const mockSummary: UserActivitySummary = {
    period_start: '2024-01-01T00:00:00Z',
    period_end: '2024-01-08T00:00:00Z',
    total_events: 150,
    total_searches: 75,
    total_property_views: 45,
    total_tool_uses: 20,
    total_property_clicks: 30,
    total_exports: 5,
    total_favorites: 10,
    unique_sessions: 12,
    avg_processing_time_ms: 1500,
    top_tools: [
      { tool_name: 'mortgage_calculator', count: 8 },
      { tool_name: 'investment_analyzer', count: 6 },
    ],
    top_search_cities: [
      { city: 'Warsaw', count: 30 },
      { city: 'Krakow', count: 25 },
    ],
    event_counts_by_day: [
      { date: '2024-01-01', count: 20 },
      { date: '2024-01-02', count: 25 },
    ],
  };

  const mockTrends: UserActivityTrendPoint[] = [
    { date: '2024-01-01', searches: 10, property_views: 6, tool_uses: 3, exports: 1 },
    { date: '2024-01-02', searches: 12, property_views: 8, tool_uses: 4, exports: 0 },
  ];

  // Mock document.createElement for download link
  const mockAnchorClick = jest.fn();
  const originalCreateElement = document.createElement.bind(document);

  beforeEach(() => {
    jest.clearAllMocks();
    fetchMockRegistry = [];

    // Default: return summary and trends
    mockFetchResponse('user-activity/summary', mockSummary);
    mockFetchResponse('user-activity/trends', { trends: mockTrends });

    document.createElement = jest.fn((tagName: string) => {
      const element = originalCreateElement(tagName);
      if (tagName === 'a') {
        (element as HTMLAnchorElement).click = mockAnchorClick;
      }
      return element;
    }) as jest.Mock;
  });

  afterEach(() => {
    document.createElement = originalCreateElement;
  });

  it('renders page title and description', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByText('Usage Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Track your activity and analytics')).toBeInTheDocument();
    });
  });

  it('shows loading skeleton while data is loading', () => {
    // Override fetch to never resolve
    mockFetch.mockImplementation(() => new Promise(() => {}));

    render(<UsagePage />);

    // Skeleton placeholders should be visible
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('displays summary metrics after loading', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByText('Total Searches')).toBeInTheDocument();
      expect(screen.getByText('75')).toBeInTheDocument();
      expect(screen.getByText('Property Views')).toBeInTheDocument();
      expect(screen.getByText('45')).toBeInTheDocument();
      expect(screen.getByText('Tools Used')).toBeInTheDocument();
      expect(screen.getByText('20')).toBeInTheDocument();
    });
  });

  it('displays additional metrics row', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByText('Property Clicks')).toBeInTheDocument();
      expect(screen.getByText('Exports')).toBeInTheDocument();
      expect(screen.getByText('Favorites')).toBeInTheDocument();
    });
  });

  it('displays error message when API fails', async () => {
    fetchMockRegistry = [];
    mockFetchError('user-activity', 'Failed to load usage data');

    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load usage data')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });
  });

  it('allows retry after error', async () => {
    // First call fails
    fetchMockRegistry = [];
    mockFetchError('user-activity', 'Failed to load');

    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load')).toBeInTheDocument();
    });

    // Set up success response for retry
    fetchMockRegistry = [];
    mockFetchResponse('user-activity/summary', mockSummary);
    mockFetchResponse('user-activity/trends', { trends: mockTrends });

    fireEvent.click(screen.getByRole('button', { name: /retry/i }));

    await waitFor(() => {
      expect(screen.getByText('Total Searches')).toBeInTheDocument();
    });
  });

  it('renders tab navigation with all tabs present', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /activity trends/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /top tools/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /top cities/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /daily activity/i })).toBeInTheDocument();
    });
  });

  it('displays formatted period date range', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      // The period badge shows formatted dates from the summary
      expect(screen.getByText(/Jan 1, 2024/)).toBeInTheDocument();
      expect(screen.getByText(/Jan 8, 2024/)).toBeInTheDocument();
    });
  });

  it('exports CSV when export button is clicked', async () => {
    // Set up blob response for export
    mockFetchBlob('user-activity/export');

    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /export csv/i }));

    await waitFor(() => {
      expect(mockAnchorClick).toHaveBeenCalled();
    });
  });

  it('displays avg response time metric', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByText('Avg Response Time')).toBeInTheDocument();
      // 1500ms = 1.5s
      expect(screen.getByText('1.5s')).toBeInTheDocument();
    });
  });

  it('shows unique sessions count', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByText(/12 unique sessions/)).toBeInTheDocument();
    });
  });

  it('renders refresh button', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });
  });
});
