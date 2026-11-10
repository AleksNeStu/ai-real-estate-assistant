import { fireEvent, render, screen } from '@testing-library/react';

import { DemoClip } from '@/components/landing/demo-clip';

/**
 * The six seconds of the demo on the landing.
 *
 * Three things have to be true: the landing shows the poster and one teal
 * action, the click plays the clip, and a visitor who asked for less motion
 * gets the poster alone - the file is never fetched for them.
 */

interface MockQuery extends MediaQueryList {
  listeners: Set<(event: MediaQueryListEvent) => void>;
}

function mockMatchMedia(matches: boolean): MockQuery {
  const query = {
    matches,
    media: '(prefers-reduced-motion: reduce)',
    onchange: null,
    listeners: new Set<(event: MediaQueryListEvent) => void>(),
    addEventListener: (_: string, listener: (event: MediaQueryListEvent) => void) => {
      query.listeners.add(listener);
    },
    removeEventListener: (_: string, listener: (event: MediaQueryListEvent) => void) => {
      query.listeners.delete(listener);
    },
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  } as unknown as MockQuery;

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: jest.fn(() => query),
  });

  return query;
}

const POSTER_ALT = 'The landing of the demo, with its search and its assistant';

describe('the demo clip on the landing', () => {
  beforeEach(() => {
    mockMatchMedia(false);
  });

  it('shows the poster and one play button, and asks for nothing', () => {
    const { container } = render(<DemoClip locale="en" />);

    expect(screen.getByAltText(POSTER_ALT)).toBeInTheDocument();
    expect(screen.getAllByRole('button')).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Play the demo' })).toBeInTheDocument();

    // The clip is not in the page until the click, so the browser never
    // fetches a megabyte for a visitor who never asks for it.
    expect(container.querySelector('video')).toBeNull();
  });

  it('names the routes in mono', () => {
    render(<DemoClip locale="en" />);

    const caption = screen.getByText('/en/search · /en/chat');
    expect(caption).toBeInTheDocument();
    expect(caption.className).toContain('font-mono');
  });

  it('plays the clip on the click, muted and looping', () => {
    const { container } = render(<DemoClip locale="en" />);

    fireEvent.click(screen.getByRole('button', { name: 'Play the demo' }));

    const video = container.querySelector('video');
    expect(video).not.toBeNull();
    expect(video).toHaveAttribute('src', '/clips/demo-6s.mp4');
    expect(video?.loop).toBe(true);
    expect(video?.muted).toBe(true);

    // The poster and the button give way to the clip.
    expect(screen.queryByAltText(POSTER_ALT)).not.toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('shows the poster alone where motion is reduced, and never loads the clip', () => {
    mockMatchMedia(true);

    const { container } = render(<DemoClip locale="en" />);

    expect(screen.getByAltText(POSTER_ALT)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(container.querySelector('video')).toBeNull();
  });
});
