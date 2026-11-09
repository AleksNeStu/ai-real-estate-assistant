import { render, screen } from '@testing-library/react';

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
      />
    );

    expect(screen.getByText('mortgage_calculator')).toHaveClass('font-mono');
    expect(screen.getByText('ready')).toHaveClass('text-success');
    expect(screen.getByText('needs config')).toHaveClass('text-warning');
  });

  it('links every tool to its section on the page', () => {
    render(<ToolRail tools={[{ id: 'tool-mortgage', name: 'mortgage_calculator' }]} />);

    expect(screen.getByText('mortgage_calculator').closest('a')).toHaveAttribute(
      'href',
      '#tool-mortgage'
    );
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
