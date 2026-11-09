import { render, screen, fireEvent } from '@testing-library/react';

import { AgentFilters, EMPTY_AGENT_FILTERS } from '../agent-filters';

describe('AgentFilters', () => {
  it('offers the cities and the specialties the catalogue names', () => {
    render(
      <AgentFilters
        cities={['Kraków', 'Warsaw']}
        specialties={['Residential']}
        value={EMPTY_AGENT_FILTERS}
        onChange={jest.fn()}
        onClear={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: 'Kraków' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Warsaw' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Residential' })).toBeInTheDocument();
  });

  it('reports the city that was picked', () => {
    const onChange = jest.fn();
    render(
      <AgentFilters
        cities={['Kraków']}
        specialties={[]}
        value={EMPTY_AGENT_FILTERS}
        onChange={onChange}
        onClear={jest.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Kraków' }));

    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_AGENT_FILTERS, city: 'Kraków' });
  });

  it('reports the minimum rating that was picked', () => {
    const onChange = jest.fn();
    render(
      <AgentFilters
        cities={[]}
        specialties={[]}
        value={EMPTY_AGENT_FILTERS}
        onChange={onChange}
        onClear={jest.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '4.5+ Stars' }));

    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_AGENT_FILTERS, minRating: 4.5 });
  });

  it('reports the sort that was picked', () => {
    const onChange = jest.fn();
    render(
      <AgentFilters
        cities={[]}
        specialties={[]}
        value={EMPTY_AGENT_FILTERS}
        onChange={onChange}
        onClear={jest.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Most Reviews' }));

    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_AGENT_FILTERS, sort: 'reviews' });
  });

  it('clears the filters when the reader asks for it', () => {
    const onClear = jest.fn();
    render(
      <AgentFilters
        cities={[]}
        specialties={[]}
        value={EMPTY_AGENT_FILTERS}
        onChange={jest.fn()}
        onClear={onClear}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Clear Filters' }));

    expect(onClear).toHaveBeenCalled();
  });

  it('marks the picked city as pressed', () => {
    render(
      <AgentFilters
        cities={['Kraków']}
        specialties={[]}
        value={{ ...EMPTY_AGENT_FILTERS, city: 'Kraków' }}
        onChange={jest.fn()}
        onClear={jest.fn()}
      />
    );

    expect(screen.getByRole('button', { name: 'Kraków' })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
  });
});
