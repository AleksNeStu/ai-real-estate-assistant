/**
 * The text of the product must be legible on the surface it stands on.
 *
 * The design system keeps two kinds of colour next to each other: a SURFACE
 * (the colour of a panel - `muted`, `secondary`, `accent`, `card`, `popover`)
 * and its FOREGROUND (the colour of the text that stands on that panel).
 * They are not the same colour and they are not interchangeable: the surface
 * of the light theme is `240 4.8% 95.9%` (#f4f4f5) and of the dark theme
 * `240 3.7% 15.9%` (#27272a), which are panel colours, not text colours.
 *
 * Putting a surface colour in the text position is invisible. The onboarding
 * tour did it: its body text was painted `text-muted`, which measures 1.34:1
 * on the dark page and 1.10:1 on the light one - against a WCAG 2.1 AA floor
 * of 4.5:1 for body text. A first-time visitor could not read the tour on any
 * route of the demo.
 *
 * The mistake is cheap to make and cheap to repeat, so it is pinned here: no
 * component may put a surface token in the text position, and the rule is
 * anchored in the token table rather than in a list of class names - the
 * surface tokens are the ones whose `-foreground` partner really is another
 * lightness, and the table has to keep saying so.
 */

import fs from 'fs';
import path from 'path';

const SRC_DIR = path.join(__dirname, '..', '..');
const TOKENS_FILE = path.join(SRC_DIR, 'app', 'globals.css');

/** The tokens whose name says panel, not text. */
const SURFACE_TOKENS = ['muted', 'secondary', 'accent', 'card', 'popover'];

/**
 * A surface token in the text position.
 *
 * The variant prefix (`hover:`, `dark:`, `focus:`) belongs to the utility, so
 * it is part of what is matched. The lookahead keeps `text-muted-foreground`
 * out - that is the foreground of the muted surface, which is exactly the
 * colour text is allowed to carry. The boundary before the utility keeps the
 * scan off `bg-muted`, `border-muted` and the other positions where the
 * surface token is used as a surface.
 */
const TEXT_SURFACE = /(?:^|[\s"'`])(?:[a-z0-9-]+:)*text-(muted|secondary|accent|card|popover)(?![-\w])/g;

interface Hit {
  line: number;
  text: string;
}

/** The lines of a source that put a surface colour in the text position. */
function usesOfSurfaceText(source: string): Hit[] {
  const hits: Hit[] = [];
  source.split('\n').forEach((line, index) => {
    if (line.match(TEXT_SURFACE)) {
      hits.push({ line: index + 1, text: line.trim() });
    }
  });
  return hits;
}

/**
 * Every component of the tree, as a list of files.
 *
 * The test directories are left out: they hold the assertions, not the
 * product, and a fixture that names the defect on purpose is not a defect.
 */
function componentFiles(dir: string, found: string[] = []): string[] {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === '__tests__') continue;
      componentFiles(full, found);
    } else if (/\.tsx$/.test(entry.name) && !/\.(test|spec)\.tsx$/.test(entry.name)) {
      found.push(full);
    }
  }
  return found;
}

/** The body of a theme block of the token table. */
function blockBody(css: string, header: RegExp): string {
  const match = header.exec(css);
  if (!match) return '';
  const open = css.indexOf('{', match.index);
  const close = css.indexOf('\n}', open);
  return close < 0 ? css.slice(open + 1) : css.slice(open + 1, close);
}

/** Every token of a theme block, with the lightness it stands for. */
function lightnessesOf(block: string): Record<string, number> {
  const out: Record<string, number> = {};
  const token = /--([a-z0-9-]+):\s*[\d.]+\s+[\d.]+%\s+([\d.]+)%/g;
  let match = token.exec(block);
  while (match) {
    out[match[1]] = Number.parseFloat(match[2]);
    match = token.exec(block);
  }
  return out;
}

describe('the text of the product', () => {
  const css = fs.readFileSync(TOKENS_FILE, 'utf-8');
  const themes = {
    light: lightnessesOf(blockBody(css, /:root\s*\{/)),
    dark: lightnessesOf(blockBody(css, /(?:^|\n)\.dark\s*\{/)),
  };

  it('has a token table to read', () => {
    expect(fs.existsSync(TOKENS_FILE)).toBe(true);
    expect(Object.keys(themes.light).length).toBeGreaterThan(0);
    expect(Object.keys(themes.dark).length).toBeGreaterThan(0);
  });

  it('gives every surface token a foreground of another lightness', () => {
    // The rule the scan enforces is worth nothing if the table does not hold
    // it: a surface token and its foreground must really be two colours, in
    // both themes, or the pair means nothing.
    for (const [theme, tokens] of Object.entries(themes)) {
      for (const surface of SURFACE_TOKENS) {
        expect({ theme, token: tokens[surface] }).toEqual({
          theme,
          token: expect.any(Number),
        });
        expect({ theme, token: tokens[`${surface}-foreground`] }).toEqual({
          theme,
          token: expect.any(Number),
        });
        expect({
          theme,
          surface,
          same: tokens[surface] === tokens[`${surface}-foreground`],
        }).toEqual({ theme, surface, same: false });
      }
    }
  });

  it('finds a surface colour in the text position, and leaves the other positions alone', () => {
    // The scan has to be alive: a pattern that matches nothing would pass
    // every component forever. So it is proved on a source that holds one
    // defect in the text position and three correct uses of the same word.
    const source = [
      '      <p className="text-xs text-muted mt-1 leading-relaxed">{body}</p>',
      '      <div className="h-1.5 rounded-full bg-muted/40" />',
      '      <span className="text-muted-foreground">{annotation}</span>',
      '      <button className="hover:text-muted">hover</button>',
      '      <div className="border-muted" />',
    ].join('\n');
    const hits = usesOfSurfaceText(source);
    expect(hits.map((hit) => hit.line)).toEqual([1, 4]);
  });

  it('keeps every surface colour out of the text position', () => {
    const offenders: string[] = [];
    for (const file of componentFiles(SRC_DIR)) {
      const source = fs.readFileSync(file, 'utf-8');
      for (const hit of usesOfSurfaceText(source)) {
        offenders.push(`${path.relative(SRC_DIR, file)}:${hit.line}  ${hit.text}`);
      }
    }
    expect(offenders).toEqual([]);
  });
});
