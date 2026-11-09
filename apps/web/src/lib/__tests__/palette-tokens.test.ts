import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { ACTION_HEX, DISTRICT_FILL, DISTRICT_LAYER, PALETTE, TOKEN_SOURCES } from '../palette';

/**
 * The palette holds literals because the map engines cannot read CSS. This
 * test is the leash: every literal must be the value of the token it claims,
 * in the light theme of `globals.css`. A token that moves without its
 * literal is a visual drift that no other test would catch.
 */
const globalsCss = readFileSync(
  join(process.cwd(), 'src/app/globals.css'),
  'utf-8',
);

function tokenHsl(name: string): [number, number, number] {
  const root = globalsCss.slice(globalsCss.indexOf(':root'), globalsCss.indexOf('.dark {'));
  const match = root.match(new RegExp(`${name}:\\s*([\\d.]+)\\s+([\\d.]+)%\\s+([\\d.]+)%`));
  if (!match) {
    throw new Error(`token ${name} is not defined in :root`);
  }
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

function parseColor(value: string): [number, number, number] {
  const match = value.match(/hsla?\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%/);
  if (!match) {
    throw new Error(`cannot parse colour ${value}`);
  }
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

function expectSameColor(actual: string, expected: [number, number, number]) {
  const [h, s, l] = parseColor(actual);
  expect(Math.abs(h - expected[0])).toBeLessThan(0.05);
  expect(Math.abs(s - expected[1])).toBeLessThan(0.05);
  expect(Math.abs(l - expected[2])).toBeLessThan(0.05);
}

/** The hex of an HSL triple, so a literal colour can be compared with a token. */
function hslToHex(h: number, s: number, l: number): string {
  const sRatio = s / 100;
  const lRatio = l / 100;
  const c = (1 - Math.abs(2 * lRatio - 1)) * sRatio;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = lRatio - c / 2;

  let rgb: [number, number, number];
  if (h < 60) rgb = [c, x, 0];
  else if (h < 120) rgb = [x, c, 0];
  else if (h < 180) rgb = [0, c, x];
  else if (h < 240) rgb = [0, x, c];
  else if (h < 300) rgb = [x, 0, c];
  else rgb = [c, 0, x];

  return (
    '#' +
    rgb
      .map((channel) =>
        Math.round((channel + m) * 255)
          .toString(16)
          .padStart(2, '0')
      )
      .join('')
  );
}

describe('the palette follows the tokens', () => {
  it.each(Object.entries(TOKEN_SOURCES))('%s is the value of %s', (literal, token) => {
    expectSameColor(literal, tokenHsl(token));
  });

  it('the district fills are the status tokens at their stated opacity', () => {
    expectSameColor(DISTRICT_FILL.low, tokenHsl('--success'));
    expectSameColor(DISTRICT_FILL.mediumLow, tokenHsl('--warning'));
    expectSameColor(DISTRICT_FILL.mediumHigh, tokenHsl('--caution'));
    expectSameColor(DISTRICT_FILL.high, tokenHsl('--destructive'));
    expectSameColor(DISTRICT_FILL.noData, tokenHsl('--muted-foreground'));
  });

  it('the accent is the teal of the design', () => {
    expectSameColor(PALETTE.action, tokenHsl('--action'));
  });

  it('the boundary layer colours are tokens too', () => {
    expectSameColor(DISTRICT_LAYER.line, tokenHsl('--district-line'));
    expectSameColor(DISTRICT_LAYER.label, tokenHsl('--district-label'));
    expectSameColor(DISTRICT_LAYER.halo, tokenHsl('--district-halo'));
  });

  it('the browser chrome colour is the same teal', () => {
    // `themeColor` takes a literal, so the hex is written out. It still has
    // to be the token's value - a teal that drifts from the action colour
    // would show in the browser chrome alone.
    const [h, s, l] = tokenHsl('--action');
    const hex = hslToHex(h, s, l);
    expect(hex.toLowerCase()).toBe(ACTION_HEX.toLowerCase());
  });
});
