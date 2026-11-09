import { render, screen } from '@testing-library/react';

import { MonoAnnotation } from '../mono-annotation';

describe('MonoAnnotation', () => {
  it('renders its data in mono', () => {
    render(<MonoAnnotation>/search</MonoAnnotation>);

    const annotation = screen.getByText('/search');

    expect(annotation).toBeInTheDocument();
    expect(annotation).toHaveClass('font-mono');
    expect(annotation).toHaveClass('text-muted-foreground');
  });

  it('gives a status its meaning, and keeps the muted voice for the rest', () => {
    render(<MonoAnnotation tone="success">live</MonoAnnotation>);

    const annotation = screen.getByText('live');

    expect(annotation).toHaveClass('text-success');
    expect(annotation).not.toHaveClass('text-muted-foreground');
  });

  it('lets the caller add its own classes', () => {
    render(
      <MonoAnnotation tone="warning" className="text-right">
        planned
      </MonoAnnotation>
    );

    const annotation = screen.getByText('planned');

    expect(annotation).toHaveClass('text-warning');
    expect(annotation).toHaveClass('text-right');
  });
});
