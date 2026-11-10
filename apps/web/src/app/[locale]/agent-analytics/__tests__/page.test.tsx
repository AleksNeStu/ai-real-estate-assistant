/**
 * Tests for the Agent analytics page.
 *
 * The page is the agent's numbers, the team beside them, the months of
 * deals and the coaching notes. The gate belongs to another lane and is
 * mocked here.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import AgentAnalyticsPage from '../page';
import * as api from '@/lib/api';
import type {
  AgentMetrics,
  CoachingInsight,
  GoalProgress,
  PerformanceTrendPoint,
  TeamComparison,
} from '@/lib/types';

jest.mock('@/components/shell/gate', () => ({
  AccountGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

jest.mock('@/lib/api', () => ({
  ApiError: class ApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
    }
  },
  getAgentMetrics: jest.fn(),
  getTeamComparison: jest.fn(),
  getPerformanceTrends: jest.fn(),
  getCoachingInsights: jest.fn(),
  getGoalProgress: jest.fn(),
  getTopPerformers: jest.fn(),
  getAgentsNeedingSupport: jest.fn(),
}));

const mockMetrics: AgentMetrics = {
  total_leads: 201,
  active_leads: 40,
  new_leads_week: 12,
  high_value_leads: 18,
  total_deals: 24,
  active_deals: 6,
  closed_deals: 18,
  fell_through_deals: 2,
  lead_to_qualified_rate: 26.4,
  qualified_to_deal_rate: 41.2,
  overall_conversion_rate: 31.0,
  avg_time_to_first_contact_hours: 1.2,
  avg_time_to_qualify_days: 3,
  avg_time_to_close_days: 21,
  total_deal_value: 8400000,
  avg_deal_value: 466667,
  total_commission: 120000,
  pending_commission: 18000,
  top_property_types: [{ type: 'apartment', count: 12, percentage: 60 }],
  top_locations: [{ location: 'Kraków', count: 9, percentage: 45 }],
  avg_lead_score: 62,
  deals_change_percent: 18,
  revenue_change_percent: 9,
};

const mockComparison: TeamComparison = {
  agent_id: 'a1',
  agent_name: 'Anna Kowalczyk',
  rank_by_deals: 1,
  rank_by_revenue: 2,
  rank_by_conversion: 1,
  total_agents: 4,
  deals_vs_avg_percent: 12,
  revenue_vs_avg_percent: 4,
  conversion_vs_avg_percent: 8,
  time_to_close_vs_avg_percent: -3,
  team_avg_deals: 4.5,
  team_avg_revenue: 2100000,
  team_avg_conversion: 24,
  team_avg_time_to_close_days: 22,
};

const mockTrends: PerformanceTrendPoint[] = [
  {
    period: '2026-01',
    period_start: '2026-01-01',
    period_end: '2026-01-31',
    leads: 12,
    deals_closed: 3,
    revenue: 900000,
    conversion_rate: 25,
    avg_deal_value: 300000,
  },
  {
    period: '2026-02',
    period_start: '2026-02-01',
    period_end: '2026-02-28',
    leads: 18,
    deals_closed: 9,
    revenue: 2700000,
    conversion_rate: 31,
    avg_deal_value: 300000,
  },
];

const mockInsights: CoachingInsight[] = [
  {
    category: 'improvement',
    title: 'Answer the new leads faster',
    description: 'Leads answered within an hour reach a viewing twice as often.',
    actionable_recommendation: 'Set a one-hour reply window.',
    priority: 1,
  },
];

const mockGoals: GoalProgress[] = [
  {
    id: 'g1',
    goal_type: 'deals',
    target_value: 24,
    current_value: 18,
    progress_percent: 75,
    period_type: 'quarterly',
    period_start: '2026-08-01',
    period_end: '2026-10-31',
    is_achieved: false,
    days_remaining: 0,
  },
];

describe('AgentAnalyticsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.getAgentMetrics as jest.Mock).mockResolvedValue(mockMetrics);
    (api.getTeamComparison as jest.Mock).mockResolvedValue(mockComparison);
    (api.getPerformanceTrends as jest.Mock).mockResolvedValue({ trends: mockTrends, interval: 'week' });
    (api.getCoachingInsights as jest.Mock).mockResolvedValue({ insights: mockInsights });
    (api.getGoalProgress as jest.Mock).mockResolvedValue({ goals: mockGoals });
    (api.getTopPerformers as jest.Mock).mockResolvedValue({
      performers: [{ agent_id: 'a1', agent_name: 'Anna Kowalczyk', metric_value: 7, rank: 1 }],
      metric: 'deals',
      period_days: 90,
    });
    (api.getAgentsNeedingSupport as jest.Mock).mockResolvedValue({
      agents: [
        {
          agent_id: 'a4',
          agent_name: 'Tomasz Wiśniewski',
          days_without_deal: 6,
          total_leads: 38,
          conversion_rate: 12,
          suggested_actions: [],
        },
      ],
      threshold_days: 30,
    });
  });

  it('states the page and the team it speaks about', async () => {
    render(<AgentAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Agent analytics' })).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText('4 agents · last 90 d')).toBeInTheDocument();
    });
  });

  it('opens with the KPI strip', async () => {
    render(<AgentAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByTestId('agent-kpi-strip')).toBeInTheDocument();
    });

    expect(screen.getAllByText('Leads').length).toBeGreaterThan(0);
    expect(screen.getAllByText('201').length).toBeGreaterThan(0);
    expect(screen.getByText('Deals closed')).toBeInTheDocument();
    expect(screen.getByText('18 of 24')).toBeInTheDocument();
  });

  it('holds the team in a ledger', async () => {
    render(<AgentAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('team-ledger-row').length).toBeGreaterThanOrEqual(2);
    });

    expect(screen.getAllByText('Anna Kowalczyk').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Tomasz Wiśniewski').length).toBeGreaterThan(0);
  });

  it('draws the months of deals', async () => {
    render(<AgentAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('agent-trend-bar')).toHaveLength(mockTrends.length);
    });

    expect(screen.getByText('Deals per month, team')).toBeInTheDocument();
  });

  it('states the coaching notes', async () => {
    render(<AgentAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText('Answer the new leads faster')).toBeInTheDocument();
    });
  });

  it('changes the period and asks the API about the new one', async () => {
    render(<AgentAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByTestId('agent-period-12mo')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('agent-period-12mo'));

    await waitFor(() => {
      expect(api.getPerformanceTrends).toHaveBeenCalledWith({ interval: 'month', periods: 12 });
    });
  });

  it('keeps the page when the team views are not available', async () => {
    (api.getTopPerformers as jest.Mock).mockRejectedValue(new Error('Forbidden'));
    (api.getAgentsNeedingSupport as jest.Mock).mockRejectedValue(new Error('Forbidden'));

    render(<AgentAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Leads').length).toBeGreaterThan(0);
    });

    expect(
      screen.getAllByText('This view is not available for your account.').length
    ).toBeGreaterThan(0);
  });

  it('handles an API error gracefully', async () => {
    (api.getAgentMetrics as jest.Mock).mockRejectedValue(new Error('API Error'));

    render(<AgentAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });
  });

  it('says the view belongs to an agent when the API refuses the account', async () => {
    (api.getAgentMetrics as jest.Mock).mockRejectedValue(
      new api.ApiError('Only agents and admins can access agent analytics', 403)
    );

    render(<AgentAnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText("An agent's view")).toBeInTheDocument();
    });

    // The wrong door is not a failure - there is nothing to retry.
    expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument();
  });
});
