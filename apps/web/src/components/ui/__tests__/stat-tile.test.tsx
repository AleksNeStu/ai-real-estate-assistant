import { render, screen } from '@testing-library/react';

import { StatTile } from '../stat-tile';

describe('StatTile', () => {
  it('renders the value in mono and the label in the muted voice', () => {
    render(<StatTile value="1 200" label="listings in the catalogue" />);

    const value = screen.getByText('1 200');
    const label = screen.getByText('listings in the catalogue');

    expect(value).toBeInTheDocument();
    expect(value).toHaveClass('font-mono');

    expect(label).toBeInTheDocument();
    expect(label).toHaveClass('text-muted-foreground');
    expect(label).not.toHaveClass('font-mono');
  });

  it('keeps an optional hint in mono, because a hint is data', () => {
    render(<StatTile value="252" label="properties" hint="demo catalogue" />);

    expect(screen.getByText('demo catalogue')).toHaveClass('font-mono');
  });
});
