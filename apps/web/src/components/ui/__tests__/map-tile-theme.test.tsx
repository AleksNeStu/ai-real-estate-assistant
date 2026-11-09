import { render } from '@testing-library/react';

import { DARK_TILE_FILTER, LIGHT_TILE_FILTER, MapTileTheme } from '../map-tile-theme';

/**
 * The map hands out its tile pane; the theme filter is written on that pane.
 * The double keeps one pane for the whole file, so a test can read back the
 * filter that was written.
 */
jest.mock('react-leaflet', () => {
  const pane = { style: {} as { filter?: string } };
  const map = { getPane: () => pane };
  return { useMap: () => map, __pane: pane };
});

const pane = (
  jest.requireMock('react-leaflet') as { __pane: { style: { filter?: string } } }
).__pane;

/** The observer delivers on a microtask; a macrotask boundary waits it out. */
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

describe('MapTileTheme', () => {
  beforeEach(() => {
    document.documentElement.className = '';
    pane.style.filter = undefined;
  });

  it('greys the tiles in the light theme', () => {
    render(<MapTileTheme />);

    expect(pane.style.filter).toBe(LIGHT_TILE_FILTER);
  });

  it('inverts the tiles in the dark theme', () => {
    document.documentElement.classList.add('dark');

    render(<MapTileTheme />);

    expect(pane.style.filter).toBe(DARK_TILE_FILTER);
  });

  it('follows the theme toggle without a re-mount', async () => {
    render(<MapTileTheme />);
    expect(pane.style.filter).toBe(LIGHT_TILE_FILTER);

    document.documentElement.classList.add('dark');
    await settle();

    expect(pane.style.filter).toBe(DARK_TILE_FILTER);

    document.documentElement.classList.remove('dark');
    await settle();

    expect(pane.style.filter).toBe(LIGHT_TILE_FILTER);
  });
});
