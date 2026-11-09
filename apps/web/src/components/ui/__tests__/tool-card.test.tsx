import { render, screen } from '@testing-library/react';

import { ToolCard } from '../tool-card';

describe('ToolCard', () => {
  it('shows the tool, its arguments, the result and the sources', () => {
    render(
      <ToolCard
        name="search_properties"
        label="Search"
        duration="0.21s"
        args='query="2-bedroom apartment"'
        result={<p>38 matches</p>}
        sources={[{ title: 'Kraków, 2 rooms', kind: 'demo catalogue', confidence: 'high' }]}
      />
    );

    expect(screen.getByText('search_properties')).toHaveClass('font-mono');
    expect(screen.getByText('Search · 0.21s')).toBeInTheDocument();
    expect(screen.getByText('args')).toBeInTheDocument();
    expect(screen.getByText('query="2-bedroom apartment"')).toBeInTheDocument();
    expect(screen.getByText('38 matches')).toBeInTheDocument();
    expect(screen.getByText('Sources (1)')).toBeInTheDocument();
    expect(screen.getByText('Kraków, 2 rooms')).toBeInTheDocument();
  });

  it('shows the conclusion and the intermediate steps', () => {
    render(
      <ToolCard
        name="rent_vs_buy"
        verdict="Buying overtakes renting in year 8."
        steps={['rent comparables: 7 rentals in Nowa Huta', 'net worth compared year by year']}
      />
    );

    expect(screen.getByText('Result')).toBeInTheDocument();
    expect(screen.getByText(/Buying overtakes renting in year 8\./)).toBeInTheDocument();
    expect(screen.getByText('Intermediate steps (2)')).toBeInTheDocument();
    expect(screen.getByText('rent comparables: 7 rentals in Nowa Huta')).toBeInTheDocument();
  });

  it('keeps the meaning of a confidence in its tone', () => {
    render(
      <ToolCard name="web_search" sources={[{ title: 'ztp.krakow.pl', confidence: 'medium' }]} />
    );

    expect(screen.getByText('medium')).toHaveClass('text-warning');
  });

  it('renders without the parts it was not given', () => {
    render(<ToolCard name="open_url" />);

    expect(screen.getByText('open_url')).toBeInTheDocument();
    expect(screen.queryByText('args')).not.toBeInTheDocument();
    expect(screen.queryByText('Result')).not.toBeInTheDocument();
    expect(screen.queryByText(/Sources/)).not.toBeInTheDocument();
  });
});
