import { render, screen } from '@testing-library/react';

import { ContextPane } from '../context-pane';

describe('ContextPane', () => {
  it('indexes the calls the assistant made, with their mono names', () => {
    render(
      <ContextPane
        tools={[
          { id: 'tool-0-0', name: 'search_properties' },
          { id: 'tool-0-1', name: 'mortgage_calculator', label: 'Mortgage' },
        ]}
        sessionId="session-42"
      />
    );

    expect(screen.getByText('Tools used')).toBeInTheDocument();
    expect(screen.getByText('2 calls')).toBeInTheDocument();
    expect(screen.getByText('search_properties')).toHaveClass('font-mono');
    expect(screen.getByText('Mortgage')).toBeInTheDocument();
    expect(screen.getByText('session: session-42')).toBeInTheDocument();
  });

  it('says so when no call has been made yet', () => {
    render(<ContextPane tools={[]} />);

    expect(screen.getByText('No tool call yet.')).toBeInTheDocument();
    expect(screen.getByText('0 calls')).toBeInTheDocument();
  });

  it('links every call to its card in the conversation', () => {
    render(<ContextPane tools={[{ id: 'tool-0-0', name: 'search_properties' }]} />);

    expect(screen.getByText('search_properties').closest('a')).toHaveAttribute(
      'href',
      '#tool-0-0'
    );
  });
});
