import { render, screen } from '@testing-library/react';

import { ToolResult, ToolResultBars, ToolResultKv, ToolResultTable } from '../tool-result';

describe('ToolResultKv', () => {
  it('draws the field names in mono and the values beside them', () => {
    render(<ToolResultKv rows={[{ label: 'monthly_payment', value: '2 473 zł' }]} />);

    const label = screen.getByText('monthly_payment');
    const value = screen.getByText('2 473 zł');

    expect(label).toHaveClass('font-mono');
    expect(value).toHaveClass('font-mono');
  });
});

describe('ToolResultBars', () => {
  it('draws one bar per row, the longest one full', () => {
    render(
      <ToolResultBars
        rows={[
          { label: 'Safety', value: 5 },
          { label: 'Schools', value: 10 },
        ]}
      />
    );

    expect(screen.getByText('Safety')).toBeInTheDocument();
    expect(screen.getByText('Schools')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });
});

describe('ToolResultTable', () => {
  it('draws the head and the rows', () => {
    render(
      <ToolResultTable
        head={['Listing', 'Price']}
        rows={[['Nowa Huta', '489 000 zł']]}
      />
    );

    expect(screen.getByText('Listing')).toBeInTheDocument();
    expect(screen.getByText('Nowa Huta')).toBeInTheDocument();
    expect(screen.getByText('489 000 zł')).toBeInTheDocument();
  });
});

describe('ToolResult', () => {
  it('draws a payload of numbers as bars', () => {
    render(<ToolResult observation='{"safety": 7.1, "schools": 7.8}' />);

    expect(screen.getByText('safety')).toBeInTheDocument();
    expect(screen.getByText('7.1')).toBeInTheDocument();
  });

  it('draws a payload of mixed values as key-value rows', () => {
    render(<ToolResult observation='{"monthly_payment": "2 473 zł", "years": 30}' />);

    expect(screen.getByText('monthly_payment')).toHaveClass('font-mono');
    expect(screen.getByText('2 473 zł')).toBeInTheDocument();
  });

  it('draws a list of objects as a table', () => {
    render(
      <ToolResult
        observation='[{"district": "Nowa Huta", "price": "489 000 zł"}]'
      />
    );

    expect(screen.getByText('district')).toBeInTheDocument();
    expect(screen.getByText('Nowa Huta')).toBeInTheDocument();
  });

  it('draws an answer that is prose as prose', () => {
    render(<ToolResult observation="Buying overtakes renting in year 8." />);

    expect(screen.getByText('Buying overtakes renting in year 8.')).toBeInTheDocument();
  });

  it('draws nothing when the tool said nothing', () => {
    const { container } = render(<ToolResult observation={undefined} />);

    expect(container).toBeEmptyDOMElement();
  });
});
