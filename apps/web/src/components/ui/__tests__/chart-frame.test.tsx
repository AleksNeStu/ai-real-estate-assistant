import { render, screen } from '@testing-library/react';

import { ChartFrame } from '../chart-frame';

describe('ChartFrame', () => {
  it('renders the title and the mono caption beside it', () => {
    render(
      <ChartFrame title="Median asking price" caption="24 months">
        <svg aria-label="price chart" />
      </ChartFrame>
    );

    expect(screen.getByText('Median asking price')).toBeInTheDocument();
    expect(screen.getByText('24 months')).toHaveClass('font-mono');
  });

  it('reserves the height of the chart area, so nothing shifts when it arrives', () => {
    render(<ChartFrame title="Median asking price" />);

    expect(screen.getByTestId('chart-frame-area')).toHaveStyle({ minHeight: '240px' });
  });

  it('reserves the height the caller asks for', () => {
    render(<ChartFrame title="New listings per month" height={320} />);

    expect(screen.getByTestId('chart-frame-area')).toHaveStyle({ minHeight: '320px' });
  });

  it('draws the chart inside the reserved area', () => {
    render(
      <ChartFrame title="Area vs area">
        <svg aria-label="comparison chart" />
      </ChartFrame>
    );

    const area = screen.getByTestId('chart-frame-area');
    expect(area).toContainElement(screen.getByLabelText('comparison chart'));
  });
});
