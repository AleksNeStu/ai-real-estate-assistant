import { render, screen, fireEvent } from '@testing-library/react';

import { ShowcaseBody } from '../showcase-body';

describe('ShowcaseBody', () => {
  it('names the three sections of the catalogue', () => {
    render(<ShowcaseBody locale="en" />);

    expect(screen.getByText('Forks & Built With This')).toBeInTheDocument();
    expect(screen.getByText('Companies using this')).toBeInTheDocument();
    expect(screen.getByText('What people are saying')).toBeInTheDocument();
  });

  it('counts the entries of every section', () => {
    render(<ShowcaseBody locale="en" />);

    expect(screen.getAllByText('0 entries')).toHaveLength(3);
  });

  it('says what an entry looks like only when the reader asks for it', () => {
    render(<ShowcaseBody locale="en" />);

    expect(screen.queryByText('name and link')).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Show the entry format'));

    expect(screen.getByText('name and link')).toBeInTheDocument();
    expect(screen.getByText('verbatim, with permission')).toBeInTheDocument();
  });

  it('keeps the empty state honest - no entry is claimed', () => {
    render(<ShowcaseBody locale="en" />);

    expect(screen.getByText('No forks or built-with listings yet.')).toBeInTheDocument();
    expect(screen.getByText('No production deployments listed yet.')).toBeInTheDocument();
    expect(screen.getByText('No public quotes yet.')).toBeInTheDocument();
  });

  it('offers the demo and the repository', () => {
    render(<ShowcaseBody locale="en" />);

    expect(screen.getByRole('link', { name: 'Try the demo' })).toHaveAttribute(
      'href',
      '/en/search'
    );
    expect(screen.getByRole('link', { name: 'Star the repo' })).toHaveAttribute(
      'href',
      expect.stringContaining('github.com/AleksNeStu/ai-real-estate-assistant')
    );
  });
});
