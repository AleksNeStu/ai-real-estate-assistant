/**
 * Tests for the Usage page.
 *
 * The page is the dashboard: the event-kind tiles, the daily chart, the
 * activity ledger and the CSV export. The gate belongs to another lane and
 * is mocked here.
 *
 * Note: jest.mock('@/lib/api') does not work in this project (Jest 30 +
 * next/jest). Instead, we mock the global `fetch` to return appropriate API
 * responses.
 */

import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import UsagePage from '../page';
import type { UserActivitySummary, UserActivityTrendPoint } from '@/lib/types';

jest.mock('@/components/shell/gate', () => ({
  AccountGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

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

  it('renders the page title and its description', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Usage' })).toBeInTheDocument();
      expect(
        screen.getByText('Your activity on this deployment · last 30 days')
      ).toBeInTheDocument();
    });
  });

  it('states every event kind and its total', async () => {
    render(<UsagePage />);

    // The tile is the handle: the same word also names the ledger's rows and
    // the chart's title, so the assertion is scoped to the tile.
    const tile = await screen.findByTestId('usage-kind-search');
    const kinds: Array<[string, string, string]> = [
      ['usage-kind-search', 'Searches', '75'],
      ['usage-kind-view', 'Views', '45'],
      ['usage-kind-click', 'Clicks', '30'],
      ['usage-kind-tool_call', 'Tool calls', '20'],
      ['usage-kind-download', 'Downloads', '5'],
    ];

    for (const [testId, label, value] of kinds) {
      const tile = screen.getByTestId(testId);
      expect(tile).toHaveTextContent(label);
      expect(tile).toHaveTextContent(value);
    }
    expect(tile).toBeInTheDocument();
  });

  it('draws the daily chart', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByText('Searches per day')).toBeInTheDocument();
    });

    // The bars arrive with the series, so the assertion waits for them
    // rather than for the chart's title - the title is there before it.
    await waitFor(() => {
      expect(screen.getAllByTestId('usage-bar')).toHaveLength(mockTrends.length);
    });
  });

  it('opens the ledger with the searches of the period', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByText('Activity log')).toBeInTheDocument();
    });

    // The rows arrive with the series, so the assertion waits for the ledger
    // itself - the heading is there before it.
    const ledger = await screen.findByTestId('usage-log');
    // The day names the axis too, so the assertion is scoped to the ledger.
    expect(within(ledger).getByText('Jan 1')).toBeInTheDocument();
    expect(within(ledger).getByText('10 events')).toBeInTheDocument();
  });

  it('speaks about the tool calls when the tool kind is chosen', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByTestId('usage-kind-tool_call')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('usage-kind-tool_call'));

    await waitFor(() => {
      expect(screen.getByText('mortgage_calculator')).toBeInTheDocument();
    });

    expect(screen.getByText('8 calls')).toBeInTheDocument();
  });

  it('says where the full log lives', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(
        screen.getByText('The full log — every event with its session and its data — is in the CSV.')
      ).toBeInTheDocument();
    });
  });

  it('states the period and the sessions', async () => {
    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByText('Jan 1 – Jan 8')).toBeInTheDocument();
      expect(screen.getByText(/12 unique sessions/)).toBeInTheDocument();
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
    fetchMockRegistry = [];
    mockFetchError('user-activity', 'Failed to load');

    render(<UsagePage />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load')).toBeInTheDocument();
    });

    fetchMockRegistry = [];
    mockFetchResponse('user-activity/summary', mockSummary);
    mockFetchResponse('user-activity/trends', { trends: mockTrends });

    fireEvent.click(screen.getByRole('button', { name: /retry/i }));

    await waitFor(() => {
      expect(screen.getByText('Searches')).toBeInTheDocument();
    });
  });

  it('exports CSV when export button is clicked', async () => {
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
});
