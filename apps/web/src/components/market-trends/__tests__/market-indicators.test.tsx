import { render, screen } from '@testing-library/react';

import { DistrictsLedger } from '../districts-ledger';
import { MarketIndicatorsPanel } from '../market-indicators';
import type { MarketIndicators } from '@/lib/types';

/**
 * The indicators and the districts.
 *
 * Both panels are ledgers of numbers the API returned, so the cases worth a
 * test are the ones where the API says less than usual: no change over the
 * last twelve months, and a district list that is empty.
 */
const indicators: MarketIndicators = {
  city: 'Krakow',
  overall_trend: 'rising',
  avg_price_change_1y: 6.3,
  total_listings: 1500,
  new_listings_7d: 42,
  price_drops_7d: 18,
  hottest_districts: [{ name: 'Mitte', avg_price: 650000, count: 200 }],
  coldest_districts: [{ name: 'Marzahn', avg_price: 280000, count: 150 }],
};

describe('MarketIndicatorsPanel', () => {
  it('names the market it is about', () => {
    render(<MarketIndicatorsPanel indicators={indicators} city="Krakow" />);

    expect(screen.getByText('Market indicators · Krakow')).toBeInTheDocument();
  });

  it('says all cities when the view is not narrowed to one', () => {
    render(<MarketIndicatorsPanel indicators={indicators} city={null} />);

    expect(screen.getByText('Market indicators · all cities')).toBeInTheDocument();
  });

  it('writes every indicator the API returned', () => {
    render(<MarketIndicatorsPanel indicators={indicators} city="Krakow" />);

    expect(screen.getByText('Overall Trend')).toBeInTheDocument();
    expect(screen.getByText('rising')).toBeInTheDocument();
    expect(screen.getByText('Total Listings')).toBeInTheDocument();
    expect(screen.getByText('1,500')).toBeInTheDocument();
    expect(screen.getByText('New (7 days)')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('Price Drops (7d)')).toBeInTheDocument();
    expect(screen.getByText('18')).toBeInTheDocument();
  });

  it('writes the twelve-month change with its sign', () => {
    render(<MarketIndicatorsPanel indicators={indicators} city="Krakow" />);

    expect(screen.getByText('Change, 12 months')).toBeInTheDocument();
    expect(screen.getByText('+6.3%')).toBeInTheDocument();
  });

  it('has no change when the API carries none', () => {
    render(
      <MarketIndicatorsPanel
        indicators={{ ...indicators, avg_price_change_1y: undefined }}
        city="Krakow"
      />
    );

    expect(screen.getByText('Change, 12 months')).toBeInTheDocument();
    // The change and the price per m² are the two the API does not carry.
    expect(screen.getAllByText('—')).toHaveLength(2);
  });

  it('has no change when the API sends null', () => {
    render(
      <MarketIndicatorsPanel
        indicators={{ ...indicators, avg_price_change_1y: null }}
        city="Krakow"
      />
    );

    expect(screen.getByText('Change, 12 months')).toBeInTheDocument();
    // A null is the API's way of saying it cannot compute the change.
    expect(screen.getAllByText('—')).toHaveLength(2);
  });

  it('has no price per m² when the trends carry none', () => {
    render(<MarketIndicatorsPanel indicators={indicators} city="Krakow" />);

    expect(screen.getByText('Price per m²')).toBeInTheDocument();
    // The change is there; the price per m² is the one the API does not carry.
    expect(screen.getAllByText('—')).toHaveLength(1);
  });

  it('writes the price per m² when the trends carry one', () => {
    render(
      <MarketIndicatorsPanel indicators={indicators} city="Krakow" pricePerSqm={15260} />
    );

    expect(screen.getByText('15,260')).toBeInTheDocument();
  });
});

describe('DistrictsLedger', () => {
  it('names both lists', () => {
    render(<DistrictsLedger indicators={indicators} />);

    expect(screen.getByText('Hottest Areas')).toBeInTheDocument();
    expect(screen.getByText('Most Affordable')).toBeInTheDocument();
  });

  it('writes the districts and how many listings stand behind them', () => {
    render(<DistrictsLedger indicators={indicators} />);

    expect(screen.getByText('Mitte')).toBeInTheDocument();
    expect(screen.getByText('200 listings')).toBeInTheDocument();
    expect(screen.getByText('Marzahn')).toBeInTheDocument();
    expect(screen.getByText('150 listings')).toBeInTheDocument();
  });

  it('writes the price in the currency of the listings when it is known', () => {
    render(<DistrictsLedger indicators={indicators} currency="PLN" />);

    expect(screen.getByText('PLN 650,000')).toBeInTheDocument();
  });

  it('writes a bare number when the currency is unknown', () => {
    render(<DistrictsLedger indicators={indicators} />);

    // A dollar sign in front of a Polish listing would be a guess.
    expect(screen.getByText('650,000')).toBeInTheDocument();
    expect(screen.queryByText('$650,000')).not.toBeInTheDocument();
  });

  it('draws nothing when the catalogue names no district', () => {
    const { container } = render(
      <DistrictsLedger
        indicators={{ ...indicators, hottest_districts: [], coldest_districts: [] }}
      />
    );

    expect(container).toBeEmptyDOMElement();
  });
});
