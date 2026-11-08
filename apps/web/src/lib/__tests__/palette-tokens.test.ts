import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { DISTRICT_FILL, PALETTE, TOKEN_SOURCES } from '../palette';

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
});
