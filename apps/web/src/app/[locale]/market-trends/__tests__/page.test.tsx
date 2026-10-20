import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import MarketTrendsPage from '../page';
import * as api from '@/lib/api';

// Mock recharts components
jest.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => null,
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  TrendingUp: (props: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="trending-up-icon" {...props} />
  ),
  TrendingDown: (props: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="trending-down-icon" {...props} />
  ),
  Minus: (props: React.SVGProps<SVGSVGElement>) => <svg data-testid="minus-icon" {...props} />,
  Loader2: (props: React.SVGProps<SVGSVGElement>) => <svg data-testid="loader-icon" {...props} />,
  AlertCircle: (props: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="alert-icon" {...props} />
  ),
  Activity: (props: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="activity-icon" {...props} />
  ),
  DollarSign: (props: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="dollar-icon" {...props} />
  ),
  Building2: (props: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="building-icon" {...props} />
  ),
}));

// Mock UI components
jest.mock('@/components/ui/card', () => ({
  Card: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div data-testid="card" className={className}>
      {children}
    </div>
  ),
  CardContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardDescription: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardTitle: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
}));

jest.mock('@/components/ui/button', () => ({
  Button: ({
    children,
    onClick,
    disabled,
    ...props
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
  }) => (
    <button onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  ),
}));

jest.mock('@/components/ui/input', () => ({
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}));

jest.mock('@/components/ui/label', () => ({
  Label: ({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) => (
    <label htmlFor={htmlFor}>{children}</label>
  ),
}));

jest.mock('@/components/ui/select', () => ({
  Select: ({
    children,
    value,
    onValueChange,
  }: {
    children: React.ReactNode;
    value: string;
    onValueChange: (v: string) => void;
  }) => (
    <div data-testid="select" data-value={value}>
      {children}
    </div>
  ),
  SelectContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SelectItem: ({ children, value }: { children: React.ReactNode; value: string }) => (
    <div data-testid={`select-item-${value}`}>{children}</div>
  ),
  SelectTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SelectValue: () => <span />,
}));

// Mock AreaComparisonComponent
jest.mock('@/components/analytics/area-comparison', () => ({
  AreaComparisonComponent: () => <div data-testid="area-comparison">Area Comparison</div>,
}));

// Mock the API module
jest.mock('@/lib/api', () => {
  class MockApiError extends Error {
    constructor(
      message: string,
      public status: number,
      public request_id?: string
    ) {
      super(message);
      this.name = 'ApiError';
    }
  }
  return {
    getMarketTrends: jest.fn(),
    getMarketIndicators: jest.fn(),
    ApiError: MockApiError,
  };
});

const mockTrends = {
  city: 'Berlin',
  district: undefined,
  interval: 'month' as const,
  data_points: [
    {
      period: '2024-01',
      start_date: '2024-01-01',
      end_date: '2024-01-31',
      average_price: 450000,
      median_price: 420000,
      volume: 120,
    },
    {
      period: '2024-02',
      start_date: '2024-02-01',
      end_date: '2024-02-29',
      average_price: 460000,
      median_price: 430000,
      volume: 135,
    },
  ],
  trend_direction: 'increasing' as const,
  change_percent: 2.2,
  confidence: 'high' as const,
};

const mockIndicators = {
  city: 'Berlin',
  overall_trend: 'rising' as const,
  total_listings: 1500,
  new_listings_7d: 42,
  price_drops_7d: 18,
  hottest_districts: [{ name: 'Mitte', avg_price: 650000, count: 200 }],
  coldest_districts: [{ name: 'Marzahn', avg_price: 280000, count: 150 }],
};

describe('MarketTrendsPage', () => {
  const mockGetMarketTrends = api.getMarketTrends as jest.Mock;
  const mockGetMarketIndicators = api.getMarketIndicators as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    mockGetMarketTrends.mockResolvedValue(mockTrends);
    mockGetMarketIndicators.mockResolvedValue(mockIndicators);
  });

  it('renders page title and description', async () => {
    render(<MarketTrendsPage />);

    expect(screen.getByText('Market Trends')).toBeInTheDocument();
    expect(screen.getByText(/Analyze price trends and market indicators/)).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    mockGetMarketTrends.mockImplementation(() => new Promise(() => {}));
    mockGetMarketIndicators.mockImplementation(() => new Promise(() => {}));

    render(<MarketTrendsPage />);

    // The page shows a spinner when loading and no trends - multiple loaders exist (button + main)
    const loaders = screen.getAllByTestId('loader-icon');
    expect(loaders.length).toBeGreaterThan(0);
  });

  it('renders market indicators after data loads', async () => {
    await act(async () => {
      render(<MarketTrendsPage />);
    });

    await waitFor(() => {
      expect(screen.getByText('Overall Trend')).toBeInTheDocument();
    });

    expect(screen.getByText('Total Listings')).toBeInTheDocument();
    expect(screen.getByText('New (7 days)')).toBeInTheDocument();
    expect(screen.getByText('Price Drops (7d)')).toBeInTheDocument();

    // Verify indicator values
    expect(screen.getByText('1,500')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('18')).toBeInTheDocument();
  });

  it('renders price trends chart when data points exist', async () => {
    await act(async () => {
      render(<MarketTrendsPage />);
    });

    // Card title is "Average and Median Prices" since `06aff9f2` extracted
    // the charts into `@/components/market-trends/MarketTrendsCharts` (it was
    // "Price Trends" inline in this page before the recharts dynamic-import).
    await waitFor(() => {
      expect(screen.getByText('Average and Median Prices')).toBeInTheDocument();
    });

    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('renders listing volume chart when data points exist', async () => {
    await act(async () => {
      render(<MarketTrendsPage />);
    });

    await waitFor(() => {
      expect(screen.getByText('Listing Volume')).toBeInTheDocument();
    });

    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });

  it('renders filter controls', async () => {
    await act(async () => {
      render(<MarketTrendsPage />);
    });

    await waitFor(() => {
      expect(screen.getByText('Filters')).toBeInTheDocument();
    });

    // Verify filter labels and inputs exist
    expect(screen.getByLabelText('City')).toBeInTheDocument();
    // Interval uses a Select component (mocked), verify label exists
    expect(screen.getByText('Interval', { selector: 'label' })).toBeInTheDocument();
    expect(screen.getByLabelText('Months Back')).toBeInTheDocument();
    expect(screen.getByText('Apply Filters')).toBeInTheDocument();
  });

  it('renders hottest and coldest districts', async () => {
    await act(async () => {
      render(<MarketTrendsPage />);
    });

    await waitFor(() => {
      expect(screen.getByText('Hottest Areas')).toBeInTheDocument();
      expect(screen.getByText('Most Affordable')).toBeInTheDocument();
    });

    expect(screen.getByText('Mitte')).toBeInTheDocument();
    expect(screen.getByText('Marzahn')).toBeInTheDocument();
    expect(screen.getByText('$650,000')).toBeInTheDocument();
    expect(screen.getByText('$280,000')).toBeInTheDocument();
  });

  it('shows error state when API fails', async () => {
    mockGetMarketTrends.mockRejectedValue(new Error('Failed to load market data'));
    mockGetMarketIndicators.mockRejectedValue(new Error('Failed to load market data'));

    await act(async () => {
      render(<MarketTrendsPage />);
    });

    await waitFor(() => {
      expect(screen.getByText('Failed to load market data')).toBeInTheDocument();
    });

    // Error alert icon should be visible
    expect(screen.getByTestId('alert-icon')).toBeInTheDocument();
  });

  it('renders AreaComparisonComponent', async () => {
    await act(async () => {
      render(<MarketTrendsPage />);
    });

    await waitFor(() => {
      expect(screen.getByTestId('area-comparison')).toBeInTheDocument();
    });
  });

  it('calls fetchData when Apply Filters is clicked', async () => {
    await act(async () => {
      render(<MarketTrendsPage />);
    });

    await waitFor(() => {
      expect(screen.getByText('Apply Filters')).toBeInTheDocument();
    });

    // Initial call from useEffect
    expect(mockGetMarketTrends).toHaveBeenCalledTimes(1);

    // Click Apply Filters to trigger another fetch
    const applyButton = screen.getByText('Apply Filters');
    await act(async () => {
      fireEvent.click(applyButton);
    });

    await waitFor(() => {
      expect(mockGetMarketTrends).toHaveBeenCalledTimes(2);
    });
  });
});
