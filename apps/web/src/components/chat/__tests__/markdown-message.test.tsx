import { render, screen } from '@testing-library/react';

import { MarkdownMessage, PlainMessage } from '../markdown-message';

/**
 * The answer of the model, in the markdown the model writes it in.
 */
const ANSWER = [
  '### Matching apartment in Kraków',
  '',
  '**Address:** ul. Kanonicka 21, Kazimierz',
  '',
  '- **Price:** 432,000 PLN',
  '- [Kraków on the map](https://www.openstreetmap.org/)',
].join('\n');

/** The window a hostile answer would try to write to. */
function pwned(): boolean | undefined {
  return (window as unknown as { __markdownPwned?: boolean }).__markdownPwned;
}

describe('MarkdownMessage', () => {
  it('draws the heading, the strong run, the list and the link', () => {
    render(<MarkdownMessage>{ANSWER}</MarkdownMessage>);

    expect(
      screen.getByRole('heading', { name: 'Matching apartment in Kraków' })
    ).toBeInTheDocument();
    expect(screen.getByText('Address:').tagName).toBe('STRONG');
    expect(screen.getByText('Price:').tagName).toBe('STRONG');
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByRole('link', { name: 'Kraków on the map' })).toHaveAttribute(
      'href',
      'https://www.openstreetmap.org/'
    );
  });

  it('shows the elements, not the markers', () => {
    const { container } = render(<MarkdownMessage>{ANSWER}</MarkdownMessage>);

    expect(container.textContent).not.toContain('###');
    expect(container.textContent).not.toContain('**');
    expect(container.textContent).not.toContain('](');
  });

  it('opens a link safely', () => {
    render(<MarkdownMessage>{ANSWER}</MarkdownMessage>);

    const link = screen.getByRole('link', { name: 'Kraków on the map' });
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('draws the first heading of the answer as a section of the page', () => {
    render(<MarkdownMessage>{ANSWER}</MarkdownMessage>);

    expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument();
  });

  it('renders a script in the answer as text, never as markup', () => {
    const hostile = [
      'Here is the flat.',
      '',
      '<script>window.__markdownPwned = true;</script>',
      '',
      '<img src="x" onerror="window.__markdownPwned = true">',
    ].join('\n');

    const { container } = render(<MarkdownMessage>{hostile}</MarkdownMessage>);

    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('img')).toBeNull();
    expect(pwned()).toBeUndefined();
    expect(screen.getByText(/<script>/)).toBeInTheDocument();
  });

  it('refuses a link the browser would execute', () => {
    const hostile = '[Open the door](javascript:window.__markdownPwned=true)';

    const { container } = render(<MarkdownMessage>{hostile}</MarkdownMessage>);

    expect(container.querySelector('a')).toBeNull();
    expect(pwned()).toBeUndefined();
    expect(screen.getByText('Open the door')).toBeInTheDocument();
  });

  it('keeps the answer readable while a code block is still open', () => {
    const streaming = 'Here is the snippet:\n\n```python\nprint("hello")';

    const { container } = render(<MarkdownMessage>{streaming}</MarkdownMessage>);

    expect(screen.getByText('Here is the snippet:')).toBeInTheDocument();
    expect(container.querySelector('pre')).not.toBeNull();
    expect(container.querySelector('code')?.textContent).toContain('print("hello")');
  });
});

describe('PlainMessage', () => {
  it('renders the error apology as plain text', () => {
    const apology =
      'I apologize, but I encountered an error: <b>boom</b>. Please try again.';

    const { container } = render(<PlainMessage>{apology}</PlainMessage>);

    expect(container.querySelector('b')).toBeNull();
    expect(container.textContent).toBe(apology);
  });
});
