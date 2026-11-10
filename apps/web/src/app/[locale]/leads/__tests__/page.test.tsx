/**
 * Tests for the Leads page.
 *
 * The page is the board: the funnel, the five columns, the high-value rail
 * and the CSV export. The gate belongs to another lane and is mocked here -
 * the page test is about the board, not about the wall in front of it.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import LeadsPage from '../page';
import * as api from '@/lib/api';
import type { LeadWithScore, LeadListResponse, ScoringStatistics } from '@/lib/types';

jest.mock('@/components/shell/gate', () => ({
  AccountGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock the API module
jest.mock('@/lib/api', () => ({
  getLeads: jest.fn(),
  getHighValueLeads: jest.fn(),
  getScoringStatistics: jest.fn(),
  updateLeadStatus: jest.fn(),
  recalculateScores: jest.fn(),
  exportLeads: jest.fn(),
}));

function makeLead(
  id: string,
  name: string,
  status: LeadWithScore['status'],
  total_score: number
): LeadWithScore {
  const now = new Date().toISOString();
  return {
    id,
    visitor_id: `visitor-${id}`,
    email: `${id}@example.com`,
    name,
    status,
    total_score,
    search_activity_score: 30,
    engagement_score: 25,
    intent_score: 30,
    interaction_count: 12,
    last_activity_at: now,
    created_at: now,
    source: 'organic',
    current_score: total_score,
    updated_at: now,
    first_seen_at: now,
    consent_given: true,
  };
}

const mockLeads: LeadWithScore[] = [
  makeLead('lead-1', 'John Doe', 'new', 85),
  makeLead('lead-2', 'Jane Smith', 'contacted', 65),
  makeLead('lead-3', 'Bob Wilson', 'qualified', 92),
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
    engagement: 0.25,
    intent: 0.25,
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

  it('states the board once the leads are in', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Leads' })).toBeInTheDocument();
    });
  });

  it('opens with the funnel, counted from the leads', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Three leads reached the first stage; two of them were contacted.
    // The funnel is the handle: the word "Leads" also names the page's
    // heading, so the assertion is scoped to the strip.
    const funnel = screen.getByTestId('lead-funnel');
    expect(within(funnel).getByText('Leads')).toBeInTheDocument();
    expect(within(funnel).getByText('67% of previous')).toBeInTheDocument();
  });

  it('holds every lead in a column', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    expect(screen.getByRole('region', { name: 'New' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Contacted' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Qualified' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Converted' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Lost' })).toBeInTheDocument();
  });

  it('shows the score of a lead', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('85')).toBeInTheDocument();
    });
  });

  it('keeps the high-value leads in the rail', async () => {
    render(<LeadsPage />);

    // The rail's heading is there before its rows are, so the assertion
    // waits for the lead itself. The lead is also on the board, so the
    // assertion is scoped to the rail.
    const rail = screen.getByRole('complementary');
    await waitFor(() => {
      expect(within(rail).getByText('Bob Wilson')).toBeInTheDocument();
    });

    expect(screen.getByText('High-value leads')).toBeInTheDocument();
  });

  it('asks the API for the high-value leads at the threshold of the board', async () => {
    render(<LeadsPage />);

    await waitFor(() => {
      expect(api.getHighValueLeads).toHaveBeenCalledWith(80, 10);
    });
  });

  it('moves a lead one stage along when it is advanced', async () => {
    (api.updateLeadStatus as jest.Mock).mockResolvedValue({});
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByRole('button', { name: 'Advance →' })[0]);

    await waitFor(() => {
      expect(api.updateLeadStatus).toHaveBeenCalledWith('lead-1', 'contacted');
    });
  });

  it('exports the leads as a CSV', async () => {
    const mockBlob = new Blob(['csv data'], { type: 'text/csv' });
    (api.exportLeads as jest.Mock).mockResolvedValue(mockBlob);

    const originalCreateObjectURL = window.URL.createObjectURL;
    const originalRevokeObjectURL = window.URL.revokeObjectURL;
    window.URL.createObjectURL = jest.fn(() => 'blob:http://localhost/test');
    window.URL.revokeObjectURL = jest.fn();

    // The anchor is a real element with a spied click: a fake object breaks
    // React's own rendering of the anchor, because React sets attributes on
    // what it gets back.
    const originalCreateElement = document.createElement.bind(document);
    const anchorClick = jest.fn();
    jest.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const element = originalCreateElement(tag);
      if (tag === 'a') (element as HTMLAnchorElement).click = anchorClick;
      return element;
    });

    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Export CSV')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Export CSV'));

    await waitFor(() => {
      expect(api.exportLeads).toHaveBeenCalled();
    });
    expect(anchorClick).toHaveBeenCalled();

    window.URL.createObjectURL = originalCreateObjectURL;
    window.URL.revokeObjectURL = originalRevokeObjectURL;
    (document.createElement as jest.Mock).mockRestore();
  });

  it('recalculates the scores when it is asked to', async () => {
    (api.recalculateScores as jest.Mock).mockResolvedValue({});
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Recalculate scores')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Recalculate scores'));

    await waitFor(() => {
      expect(api.recalculateScores).toHaveBeenCalled();
    });
  });

  it('keeps the board when the statistics are not available to this account', async () => {
    (api.getScoringStatistics as jest.Mock).mockRejectedValue(new Error('Forbidden'));
    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    expect(screen.queryByText('Try again')).not.toBeInTheDocument();
  });

  it('handles an API error gracefully', async () => {
    (api.getLeads as jest.Mock).mockRejectedValue(new Error('API Error'));

    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getByText('Try again')).toBeInTheDocument();
    });
  });

  it('says so when the board is empty', async () => {
    (api.getLeads as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 50,
      total_pages: 0,
    });

    render(<LeadsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('No leads here')).toHaveLength(5);
    });
  });
});
