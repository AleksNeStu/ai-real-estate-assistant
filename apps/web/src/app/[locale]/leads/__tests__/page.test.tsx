/**
 * Tests for Leads Page.
 *
 * Task #58: Comprehensive Test Suite Update
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import LeadsPage from '../page';
import * as api from '@/lib/api';
import type { LeadWithScore, LeadListResponse, ScoringStatistics } from '@/lib/types';

// Mock the API module
jest.mock('@/lib/api', () => ({
  getLeads: jest.fn(),
  getHighValueLeads: jest.fn(),
  getScoringStatistics: jest.fn(),
  updateLeadStatus: jest.fn(),
  recalculateScores: jest.fn(),
  exportLeads: jest.fn(),
}));

// Mock date-fns
jest.mock('date-fns', () => ({
  formatDistanceToNow: jest.fn(() => '2 hours ago'),
  formatTimeAgo: jest.fn(() => '2 hours ago'),
}));

const mockLeads: LeadWithScore[] = [
  {
    id: 'lead-1',
    visitor_id: 'visitor-1',
    email: 'john@example.com',
    name: 'John Doe',
    status: 'new',
    total_score: 85,
    search_activity_score: 30,
    engagement_score: 25,
    intent_score: 30,
    interaction_count: 12,
    last_activity_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    source: 'organic',
    phone: null,
    user_id: null,
    current_score: 85,
    updated_at: new Date().toISOString(),
    first_seen_at: new Date().toISOString(),
    consent_given: true,
  },
  {
    id: 'lead-2',
    visitor_id: 'visitor-2',
    email: 'jane@example.com',
    name: 'Jane Smith',
    status: 'contacted',
    total_score: 65,
    search_activity_score: 20,
    engagement_score: 25,
    intent_score: 20,
    interaction_count: 8,
    last_activity_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    source: 'referral',
    phone: '+1234567890',
    user_id: 'user-1',
    current_score: 65,
    updated_at: new Date().toISOString(),
    first_seen_at: new Date().toISOString(),
    consent_given: true,
  },
  {
    id: 'lead-3',
    visitor_id: 'visitor-3',
    email: 'bob@example.com',
    name: 'Bob Wilson',
    status: 'qualified',
    total_score: 92,
    search_activity_score: 35,
    engagement_score: 30,
    intent_score: 27,
    interaction_count: 20,
    last_activity_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    source: 'paid',
    phone: null,
    user_id: null,
    current_score: 92,
    updated_at: new Date().toISOString(),
    first_seen_at: new Date().toISOString(),
    consent_given: true,
  },
];

const mockStatistics: ScoringStatistics = {
  total_leads: 100,
  avg_score: 55.5,
  high_value_leads: 15,
  conversion_rate: 0.25,
  converted_leads: 25,
  new_leads_24h: 10,
  score_distribution: {
    high_80_100: 15,
    medium_50_79: 25,
    low_0_49: 60,
  },
  scores_calculated_today: 20,
  model_version: '1.0.0',
  weights: {
    search_activity: 0.3,
    property_views: 0.25,
    engagement: 0.25,
    recency: 0.2,
  },
};

const mockLeadResponse: LeadListResponse = {
  items: mockLeads,
  total: 3,
  page: 1,
  page_size: 50,
  total_pages: 1,
};

describe('LeadsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.getLeads as jest.Mock).mockResolvedValue(mockLeadResponse);
    (api.getHighValueLeads as jest.Mock).mockResolvedValue([mockLeads[2]]);
    (api.getScoringStatistics as jest.Mock).mockResolvedValue(mockStatistics);
  });

  it('renders loading state with skeletons initially', () => {
    render(<LeadsPage />);
    // The page shows Skeleton components while loading
    // Skeleton component renders with animate-pulse class
    const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders leads page title after loading', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Lead Dashboard')).toBeInTheDocument();
    });
  });

  it('renders high value leads section', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('High Value Leads')).toBeInTheDocument();
    });
  });

  it('renders statistics cards after loading', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Total Leads')).toBeInTheDocument();
      expect(screen.getByText('Average Score')).toBeInTheDocument();
    });
  });

  it('displays leads in the list', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    expect(screen.getByText('jane@example.com')).toBeInTheDocument();
  });

  it('shows correct status badges', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('New')).toBeInTheDocument();
    });
  });

  it('shows score badges', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('85')).toBeInTheDocument();
    });
  });

  it('handles API error gracefully', async () => {
    (api.getLeads as jest.Mock).mockRejectedValue(new Error('API Error'));

    render(<LeadsPage />);

    await waitFor(() => {
      // The error component shows the retry button on error
      expect(screen.getByText('Try again')).toBeInTheDocument();
    });
  });

  it('renders recalculate scores button', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Recalculate Scores')).toBeInTheDocument();
    });
  });

  it('renders export button', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Export')).toBeInTheDocument();
    });
  });

  it('renders search input', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Search leads...')).toBeInTheDocument();
    });
  });

  it('renders tab navigation', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('All Leads')).toBeInTheDocument();
      expect(screen.getByText('High Value')).toBeInTheDocument();
      expect(screen.getByText('New')).toBeInTheDocument();
    });
  });

  // ---- Additional coverage tests ----

  it('displays statistics values correctly', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      // Total leads count (100 appears in stats card)
      const totalLeadsElements = screen.getAllByText('100');
      expect(totalLeadsElements.length).toBeGreaterThanOrEqual(1);
      // High value leads count
      expect(screen.getByText('15')).toBeInTheDocument();
      // Average score
      expect(screen.getByText('55.5')).toBeInTheDocument();
      // Conversion rate - 0.25.toFixed(1) => "0.3", displayed as "0.3%"
      expect(screen.getByText('0.3%')).toBeInTheDocument();
    });
  });

  it('displays new leads in last 24h', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText(/\+10 in last 24h/)).toBeInTheDocument();
    });
  });

  it('shows converted leads count', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('25 converted')).toBeInTheDocument();
    });
  });

  it('displays lead email and phone', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('john@example.com')).toBeInTheDocument();
    });

    // Jane has a phone number
    expect(screen.getByText('+1234567890')).toBeInTheDocument();
  });

  it('shows score breakdown for leads (Search/Engage/Intent)', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      // The page renders score breakdown labels
      expect(screen.getAllByText('Search').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Engage').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Intent').length).toBeGreaterThan(0);
    });
  });

  it('calls recalculateScores when Recalculate Scores button is clicked', async () => {
    (api.recalculateScores as jest.Mock).mockResolvedValue({});

    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Recalculate Scores')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Recalculate Scores'));

    await waitFor(() => {
      expect(api.recalculateScores).toHaveBeenCalled();
    });
  });

  it('calls exportLeads when Export button is clicked', async () => {
    const mockBlob = new Blob(['csv data'], { type: 'text/csv' });
    (api.exportLeads as jest.Mock).mockResolvedValue(mockBlob);

    // Mock URL.createObjectURL and related
    const mockUrl = 'blob:http://localhost/test';
    const originalCreateObjectURL = window.URL.createObjectURL;
    const originalRevokeObjectURL = window.URL.revokeObjectURL;
    window.URL.createObjectURL = jest.fn(() => mockUrl);
    window.URL.revokeObjectURL = jest.fn();

    // Mock createElement to track the anchor element
    const mockAnchor = { click: jest.fn(), href: '', download: '' };
    const originalCreateElement = document.createElement.bind(document);
    jest.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      if (tag === 'a') return mockAnchor as unknown as HTMLAnchorElement;
      return originalCreateElement(tag);
    });

    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Export')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Export'));

    await waitFor(() => {
      expect(api.exportLeads).toHaveBeenCalled();
    });

    // Restore mocks
    window.URL.createObjectURL = originalCreateObjectURL;
    window.URL.revokeObjectURL = originalRevokeObjectURL;
    (document.createElement as jest.Mock).mockRestore();
  });

  it('renders lead score bar text', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      // Score bar displays total_score/100
      expect(screen.getByText('85/100')).toBeInTheDocument();
      expect(screen.getByText('65/100')).toBeInTheDocument();
      expect(screen.getByText('92/100')).toBeInTheDocument();
    });
  });

  it('renders "Lead Score" label', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      const labels = screen.getAllByText('Lead Score');
      expect(labels.length).toBeGreaterThan(0);
    });
  });

  it('shows time ago for lead activity', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      // The activity time is rendered with Intl.RelativeTimeFormat, so the exact
      // wording depends on how long ago the fixture was created.
      // Intl.RelativeTimeFormat renders 'this minute' / 'N minutes ago' / 'now'
      const timeAgoElements = screen.getAllByText(/this minute|minute ago|last minute|now/i);
      expect(timeAgoElements.length).toBeGreaterThan(0);
    });
  });

  it('retries loading when Try Again is clicked after error', async () => {
    (api.getLeads as jest.Mock)
      .mockRejectedValueOnce(new Error('API Error'))
      .mockResolvedValueOnce(mockLeadResponse);

    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Try again')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Try again'));

    await waitFor(() => {
      expect(screen.getByText('Lead Dashboard')).toBeInTheDocument();
    });
  });

  it('renders high value leads from separate API', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      // getHighValueLeads is called with (70, 10)
      expect(api.getHighValueLeads).toHaveBeenCalledWith(70, 10);
    });
  });

  it('calls getScoringStatistics on load', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(api.getScoringStatistics).toHaveBeenCalled();
    });
  });

  it('renders Contacted status badge for jane', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Contacted')).toBeInTheDocument();
    });
  });

  it('renders Qualified status badge', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Qualified')).toBeInTheDocument();
    });
  });

  it('renders "No leads found" when lead list is empty', async () => {
    (api.getLeads as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 50,
      total_pages: 0,
    });

    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('No leads found')).toBeInTheDocument();
    });

    expect(
      screen.getByText('Try adjusting your filters or wait for new leads to come in')
    ).toBeInTheDocument();
  });
});
