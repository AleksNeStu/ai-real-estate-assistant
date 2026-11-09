import { render, screen } from '@testing-library/react';

import { UsageActivityChart } from '../usage-activity-chart';
import { UsageKindTiles } from '../usage-kind-tiles';
import { formatDay, formatPeriod, totalEvents } from '../usage-format';

/**
 * The usage tiles and the daily chart.
 *
 * The tiles are the filter, so choosing one is worth a test; the chart
 * states the days the API carried, so an empty period is worth a test too.
 */

describe('UsageKindTiles', () => {
  const tiles = [
    { kind: 'search' as const, value: 46, label: 'Searches' },
    { kind: 'view' as const, value: 112, label: 'Views' },
    { kind: 'click' as const, value: 38, label: 'Clicks' },
    { kind: 'tool_call' as const, value: 29, label: 'Tool calls' },
    { kind: 'download' as const, value: 4, label: 'Downloads' },
  ];

  it('states every kind and its count', () => {
    render(<UsageKindTiles tiles={tiles} selected={null} />);

    expect(screen.getByText('Searches')).toBeInTheDocument();
    expect(screen.getByText('46')).toBeInTheDocument();
    expect(screen.getByText('112')).toBeInTheDocument();
  });

  it('marks the chosen kind', () => {
    render(<UsageKindTiles tiles={tiles} selected="view" />);

    expect(screen.getByTestId('usage-kind-view')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('usage-kind-search')).toHaveAttribute('aria-pressed', 'false');
  });

  it('clears the kind when the chosen one is chosen again', () => {
    const onSelect = jest.fn();
    render(<UsageKindTiles tiles={tiles} selected="view" onSelect={onSelect} />);

    screen.getByTestId('usage-kind-view').click();

    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it('chooses a kind that was not chosen', () => {
    const onSelect = jest.fn();
    render(<UsageKindTiles tiles={tiles} selected="view" onSelect={onSelect} />);

    screen.getByTestId('usage-kind-click').click();

    expect(onSelect).toHaveBeenCalledWith('click');
  });
});

describe('UsageActivityChart', () => {
  it('draws one bar per day', () => {
    render(
      <UsageActivityChart
        points={[
          { date: '2026-10-10', value: 3 },
          { date: '2026-10-11', value: 9 },
        ]}
        title="Searches per day"
      />
    );

    expect(screen.getAllByTestId('usage-bar')).toHaveLength(2);
    expect(screen.getByText('Searches per day')).toBeInTheDocument();
  });

  it('reserves the area so the chart does not move when it lands', () => {
    render(<UsageActivityChart points={[]} title="Searches per day" />);

    expect(screen.getByTestId('chart-frame-area')).toBeInTheDocument();
  });

  it('states the first and the last day', () => {
    render(
      <UsageActivityChart
        points={[{ date: '2026-10-10', value: 1 }]}
        title="Searches per day"
        axisLabels={{ first: '10 Oct', last: '8 Nov' }}
      />
    );

    expect(screen.getByText('10 Oct')).toBeInTheDocument();
    expect(screen.getByText('8 Nov')).toBeInTheDocument();
  });
});

describe('the usage formatters', () => {
  it('states a day without the year', () => {
    expect(formatDay('2026-11-08', 'en')).toBe('Nov 8');
  });

  it('states a period at both ends', () => {
    expect(formatPeriod('2026-10-10', '2026-11-08', 'en')).toBe('Oct 10 – Nov 8');
  });

  it('adds up the events of every kind', () => {
    expect(
      totalEvents({ search: 1, view: 2, click: 3, tool_call: 4, download: 5 })
    ).toBe(15);
  });
});
