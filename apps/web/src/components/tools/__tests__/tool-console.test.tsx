import { fireEvent, render, screen } from '@testing-library/react';

import { jest } from '@jest/globals';

import { ToolOutput } from '../tool-output';
import { ToolRail } from '../tool-rail';

describe('ToolRail', () => {
  it('lists every tool with its mono name and its status', () => {
    render(
      <ToolRail
        tools={[
          { id: 'tool-mortgage', name: 'mortgage_calculator' },
          { id: 'tool-legal', name: 'legal_check', status: 'needsConfig' },
        ]}
        selected="tool-mortgage"
        onSelect={() => {}}
      />
    );

    expect(screen.getByText('mortgage_calculator')).toHaveClass('font-mono');
    expect(screen.getByText('ready')).toHaveClass('text-success');
    expect(screen.getByText('needs config')).toHaveClass('text-warning');
  });

  it('picks the tool it is asked for', () => {
    const onSelect = jest.fn();
    render(
      <ToolRail
        tools={[{ id: 'tool-mortgage', name: 'mortgage_calculator' }]}
        selected="tool-mortgage"
        onSelect={onSelect}
      />
    );

    const entry = screen.getByTestId('tool-mortgage_calculator');
    expect(entry).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(entry);
    expect(onSelect).toHaveBeenCalledWith('tool-mortgage');
  });
});

describe('ToolOutput', () => {
  it('shows the name of the call and the raw JSON behind it', () => {
    render(<ToolOutput name="mortgage_calculator" raw={{ monthly_payment: 2473 }} />);

    expect(screen.getByText('mortgage_calculator')).toHaveClass('font-mono');
    expect(screen.getByText('Raw JSON')).toBeInTheDocument();
    expect(screen.getByText(/"monthly_payment": 2473/)).toBeInTheDocument();
  });

  it('keeps the tool answer the tool rendered', () => {
    render(
      <ToolOutput name="mortgage_calculator" raw={{ monthly_payment: 2473 }}>
        <p>Monthly payment: 2 473 zł</p>
      </ToolOutput>
    );

    expect(screen.getByText('Monthly payment: 2 473 zł')).toBeInTheDocument();
  });
});
