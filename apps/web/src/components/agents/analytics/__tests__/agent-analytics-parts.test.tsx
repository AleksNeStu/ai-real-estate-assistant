import { render, screen } from '@testing-library/react';

import { AgentCoaching } from '../agent-coaching';
import { AgentKpiStrip } from '../agent-kpi-strip';
import { AgentTeamLedger } from '../agent-team-ledger';
import { AgentTrendChart } from '../agent-trend-chart';

/**
 * The agent analytics parts.
 *
 * The KPI strip states the numbers, the team ledger holds one row per agent
 * and a dash where the API says nothing, the chart draws the months, and
 * the coaching column says who is where.
 */

describe('AgentKpiStrip', () => {
  it('states every tile with its number and its note', () => {
    render(
      <AgentKpiStrip
        kpis={[
          { key: 'leads', value: 201, label: 'Leads', hint: '12 new this week' },
          { key: 'deals', value: 18, label: 'Deals closed', hint: '14 of 24' },
        ]}
      />
    );

    expect(screen.getByText('Leads')).toBeInTheDocument();
    expect(screen.getByText('201')).toBeInTheDocument();
    expect(screen.getByText('12 new this week')).toBeInTheDocument();
    expect(screen.getByText('14 of 24')).toBeInTheDocument();
  });
});

describe('AgentTeamLedger', () => {
  it('states the head of the table and every row', () => {
    render(
      <AgentTeamLedger
        rows={[
          { name: 'Anna Kowalczyk', leads: 64, conversion: 31, deals: 7, goal: { percent: 116, achieved: true } },
          { name: 'Marta Nowak', leads: null, conversion: null, deals: 5, goal: null },
        ]}
        goalLabel="Goal: 6 deals / quarter"
      />
    );

    expect(screen.getByText('Goal: 6 deals / quarter')).toBeInTheDocument();
    expect(screen.getByText('Anna Kowalczyk')).toBeInTheDocument();
    expect(screen.getByText('64')).toBeInTheDocument();
    expect(screen.getByText('31%')).toBeInTheDocument();
  });

  it('says so where the API does not carry a number', () => {
    render(
      <AgentTeamLedger
        rows={[{ name: 'Marta Nowak', leads: null, conversion: null, deals: 5, goal: null }]}
        goalLabel="Goal"
      />
    );

    // Two cells the API does not know, and the goal that does not exist.
    expect(screen.getAllByText('—')).toHaveLength(3);
  });

  it('says so when the team has no rows', () => {
    render(<AgentTeamLedger rows={[]} goalLabel="Goal" />);

    expect(screen.getByText('The team has no rows yet.')).toBeInTheDocument();
  });
});

describe('AgentTrendChart', () => {
  it('draws one bar per month', () => {
    render(
      <AgentTrendChart
        points={[
          { period: '2026-01', value: 3 },
          { period: '2026-02', value: 9 },
        ]}
        title="Deals per month, team"
        caption="12 months"
      />
    );

    expect(screen.getAllByTestId('agent-trend-bar')).toHaveLength(2);
    expect(screen.getByText('Deals per month, team')).toBeInTheDocument();
    expect(screen.getByText('12 months')).toBeInTheDocument();
  });
});

describe('AgentCoaching', () => {
  it('names the agent at the top and the one who needs support', () => {
    render(
      <AgentCoaching
        topPerformer={{ name: 'Anna Kowalczyk', metricValue: 7, rank: 1 }}
        needsSupport={{
          name: 'Tomasz Wiśniewski',
          daysWithoutDeal: 6,
          totalLeads: 38,
          conversionRate: 12,
        }}
        notes={[]}
      />
    );

    expect(screen.getByText('Anna Kowalczyk')).toBeInTheDocument();
    expect(screen.getByText('7 deals · rank 1')).toBeInTheDocument();
    expect(screen.getByText('Tomasz Wiśniewski')).toBeInTheDocument();
    expect(
      screen.getByText('6 days without a deal · 38 leads · 12% conversion')
    ).toBeInTheDocument();
  });

  it('states the coaching notes and says they need checking', () => {
    render(
      <AgentCoaching
        notes={[
          {
            category: 'improvement',
            title: 'Answer the new leads faster',
            description: 'Leads answered within an hour reach a viewing twice as often.',
            recommendation: 'Set a one-hour reply window.',
          },
        ]}
      />
    );

    expect(screen.getByText('Answer the new leads faster')).toBeInTheDocument();
    expect(
      screen.getByText("AI-generated from the team's numbers · verify before acting")
    ).toBeInTheDocument();
  });

  it('says so when a view is not available', () => {
    render(<AgentCoaching notes={[]} />);

    expect(
      screen.getAllByText('This view is not available for your account.').length
    ).toBeGreaterThan(0);
    expect(screen.getByText('No coaching notes yet.')).toBeInTheDocument();
  });
});
