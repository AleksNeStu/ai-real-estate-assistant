/**
 * The markdown of the answer.
 *
 * The model writes markdown; the visitor must read a document, not the
 * characters of a document. This is a small parser for the subset the models
 * actually produce - headings, emphasis, code, lists, quotes, links, rules -
 * and it returns a tree of plain nodes.
 *
 * The safety property comes from the shape of the parser, not from a filter
 * that runs afterwards: nothing here builds markup. The tree is data, and the
 * renderer turns the data into elements. Raw HTML in the answer therefore
 * stays text, because there is no path from a string to a tag - a `<script>`
 * in the answer is a paragraph of text, never a script. A link is the one
 * place a string becomes an attribute, so the scheme is checked there.
 */

/** The inline runs of a paragraph: text, emphasis, code, links, breaks. */
export type MdInline =
  | { type: 'text'; value: string }
  | { type: 'strong'; children: MdInline[] }
  | { type: 'emphasis'; children: MdInline[] }
  | { type: 'code'; value: string }
  | { type: 'link'; href: string; children: MdInline[] }
  | { type: 'break' };

/** The blocks of an answer. */
export type MdBlock =
  | { type: 'heading'; level: number; children: MdInline[] }
  | { type: 'paragraph'; children: MdInline[] }
  | { type: 'code'; value: string }
  | { type: 'list'; ordered: boolean; start: number; items: MdBlock[][] }
  | { type: 'quote'; children: MdBlock[] }
  | { type: 'rule' };

/** The schemes a link may carry. Everything else is text. */
const SAFE_SCHEMES = new Set(['http', 'https', 'mailto']);

/** The characters a backslash may escape. */
const ESCAPABLE = new Set([
  '\\',
  '`',
  '*',
  '_',
  '{',
  '}',
  '[',
  ']',
  '(',
  ')',
  '#',
  '+',
  '-',
  '.',
  '!',
  '>',
  '|',
  '~',
]);

/** The named entities a link's destination may carry. */
const ENTITIES: Record<string, string> = {
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: "'",
  '#39': "'",
};

/**
 * Parse the answer into blocks.
 *
 * An unfinished fence is a code block that runs to the end of the text, which
 * is what streaming needs: the answer arrives in pieces and the code block is
 * still open while the rest of it is on its way.
 */
export function parseMarkdown(source: string): MdBlock[] {
  const lines = source.replace(/\r\n?/g, '\n').split('\n');
  return parseBlocks(lines);
}

/** What a link's destination is allowed to be. */
export interface HrefVerdict {
  /** The link may be rendered as an anchor. */
  safe: boolean;
  /** The link leaves the site, and says so. */
  external: boolean;
}

/**
 * Judge a link's destination.
 *
 * A scheme the browser would execute - `javascript:`, `data:` - never becomes
 * an anchor. Control characters are stripped before the scheme is read, so a
 * scheme split by a tab is read as the scheme it is and refused the same way.
 */
export function inspectHref(href: string): HrefVerdict {
  const cleaned = Array.from(href)
    .filter((character) => {
      const code = character.charCodeAt(0);
      return code > 0x20 && code !== 0x7f;
    })
    .join('');

  if (cleaned === '') return { safe: false, external: false };

  const scheme = /^([a-zA-Z][a-zA-Z0-9+.-]*):/.exec(cleaned);
  if (!scheme) {
    // No scheme: a path on this site, or a protocol-relative address.
    return { safe: true, external: cleaned.startsWith('//') };
  }

  const name = scheme[1].toLowerCase();
  if (!SAFE_SCHEMES.has(name)) return { safe: false, external: false };
  return { safe: true, external: name === 'http' || name === 'https' };
}

/* -------------------------------------------------------------------------- */
/* Blocks                                                                      */
/* -------------------------------------------------------------------------- */

function parseBlocks(lines: string[]): MdBlock[] {
  const blocks: MdBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (line.trim() === '') {
      index++;
      continue;
    }

    const fence = matchFence(line);
    if (fence) {
      const body: string[] = [];
      index++;
      while (index < lines.length && !isClosingFence(lines[index], fence.marker)) {
        body.push(lines[index]);
        index++;
      }
      if (index < lines.length) index++;
      blocks.push({ type: 'code', value: body.join('\n') });
      continue;
    }

    const heading = matchHeading(line);
    if (heading) {
      blocks.push({
        type: 'heading',
        level: heading.level,
        children: parseInline(heading.text),
      });
      index++;
      continue;
    }

    if (isRule(line)) {
      blocks.push({ type: 'rule' });
      index++;
      continue;
    }

    if (isQuote(line)) {
      const body: string[] = [];
      while (index < lines.length) {
        const current = lines[index];
        if (isQuote(current)) {
          body.push(current.replace(/^ {0,3}> ?/, ''));
          index++;
          continue;
        }
        if (current.trim() === '') break;
        body.push(current.trim());
        index++;
      }
      blocks.push({ type: 'quote', children: parseBlocks(body) });
      continue;
    }

    if (matchListMarker(line)) {
      const list = parseList(lines, index);
      blocks.push(list.node);
      index = list.next;
      continue;
    }

    const paragraph: string[] = [];
    while (index < lines.length) {
      const current = lines[index];
      if (current.trim() === '') break;
      if (isBlockStart(current)) break;
      paragraph.push(current);
      index++;
    }
    blocks.push({ type: 'paragraph', children: parseInline(paragraph.join('\n')) });
  }

  return blocks;
}

/** The marker of a list item: its kind, its number and where its text starts. */
interface ListMarker {
  ordered: boolean;
  start: number;
  /** The indent of the item's marker. */
  indent: number;
  /** The indent of the item's own text, the marker included. */
  contentIndent: number;
  /** The text of the first line of the item. */
  text: string;
}

function matchListMarker(line: string): ListMarker | null {
  const match = /^( {0,3})(?:([-*+])|([0-9]{1,9})([.)]))([ \t]+)(.*)$/.exec(line);
  if (!match) return null;

  const ordered = match[3] !== undefined;
  const markerText = ordered ? match[3] + match[4] : match[2];
  const indent = match[1].length;
  const spaces = match[5].length;

  return {
    ordered,
    start: ordered ? Number.parseInt(match[3], 10) : 1,
    indent,
    contentIndent: indent + markerText.length + spaces,
    text: match[6],
  };
}

function parseList(lines: string[], start: number): { node: MdBlock; next: number } {
  const first = matchListMarker(lines[start]);
  if (!first) return { node: { type: 'paragraph', children: [] }, next: start };

  const items: MdBlock[][] = [];
  let index = start;

  while (index < lines.length) {
    const marker = matchListMarker(lines[index]);
    if (!marker) break;
    if (marker.indent !== first.indent || marker.ordered !== first.ordered) break;

    const content: string[] = [marker.text];
    index++;

    while (index < lines.length) {
      const current = lines[index];

      if (current.trim() === '') {
        const next = nextNonBlank(lines, index);
        if (next === -1) {
          index = lines.length;
          break;
        }
        // A blank line inside the item keeps the item open; a blank line
        // before a sibling item closes this one and opens the next.
        if (indentOf(lines[next]) > first.indent) {
          content.push('');
          index++;
          continue;
        }
        index = next;
        break;
      }

      const indent = indentOf(current);
      if (indent >= marker.contentIndent) {
        content.push(current.slice(marker.contentIndent));
        index++;
        continue;
      }

      const sibling = matchListMarker(current);
      if (sibling && sibling.indent === first.indent) break;
      if (indent > first.indent) {
        content.push(current.slice(first.indent));
        index++;
        continue;
      }
      if (isBlockStart(current)) break;

      // A lazy continuation of the item's paragraph.
      content.push(current.trim());
      index++;
    }

    items.push(parseBlocks(content));
  }

  return {
    node: { type: 'list', ordered: first.ordered, start: first.start, items },
    next: index,
  };
}

function matchFence(line: string): { marker: string } | null {
  const match = /^ {0,3}(`{3,}|~{3,})[ \t]*([^`]*)$/.exec(line);
  if (!match) return null;
  const info = match[2].trim();
  if (match[1].startsWith('`') && info.includes('`')) return null;
  return { marker: match[1] };
}

function isClosingFence(line: string, marker: string): boolean {
  const match = /^ {0,3}(`{3,}|~{3,})[ \t]*$/.exec(line);
  if (!match) return false;
  return match[1][0] === marker[0] && match[1].length >= marker.length;
}

function matchHeading(line: string): { level: number; text: string } | null {
  const match = /^ {0,3}(#{1,6})(?:[ \t]+(.*))?$/.exec(line);
  if (!match) return null;
  const text = (match[2] ?? '').replace(/[ \t]+#+[ \t]*$/, '').trim();
  return { level: match[1].length, text };
}

function isRule(line: string): boolean {
  return /^ {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$/.test(line);
}

function isQuote(line: string): boolean {
  return /^ {0,3}>/.test(line);
}

function isBlockStart(line: string): boolean {
  return (
    Boolean(matchFence(line) || matchHeading(line) || isRule(line) || isQuote(line)) ||
    matchListMarker(line) !== null
  );
}

function indentOf(line: string): number {
  let width = 0;
  for (const character of line) {
    if (character === ' ') width += 1;
    else if (character === '\t') width += 4;
    else break;
  }
  return width;
}

function nextNonBlank(lines: string[], from: number): number {
  for (let index = from; index < lines.length; index++) {
    if (lines[index].trim() !== '') return index;
  }
  return -1;
}

/* -------------------------------------------------------------------------- */
/* Inline runs                                                                 */
/* -------------------------------------------------------------------------- */

/** Parse the runs of a paragraph. */
export function parseInline(text: string): MdInline[] {
  const nodes: MdInline[] = [];
  let buffer = '';
  let index = 0;

  const flush = () => {
    if (buffer) {
      nodes.push({ type: 'text', value: buffer });
      buffer = '';
    }
  };

  while (index < text.length) {
    const character = text[index];

    if (character === '\\' && index + 1 < text.length && ESCAPABLE.has(text[index + 1])) {
      buffer += text[index + 1];
      index += 2;
      continue;
    }

    if (character === '`') {
      const run = countRun(text, index, '`');
      const close = findRun(text, index + run, '`', run);
      if (close !== -1) {
        flush();
        nodes.push({ type: 'code', value: trimCodeSpan(text.slice(index + run, close)) });
        index = close + run;
        continue;
      }
      buffer += character;
      index++;
      continue;
    }

    if (character === '[') {
      const link = parseLink(text, index);
      if (link) {
        flush();
        nodes.push(link.node);
        index = link.end;
        continue;
      }
      buffer += character;
      index++;
      continue;
    }

    if (character === '*' || character === '_') {
      const emphasis = parseEmphasis(text, index);
      if (emphasis) {
        flush();
        nodes.push(emphasis.node);
        index = emphasis.end;
        continue;
      }
      buffer += character;
      index++;
      continue;
    }

    if (character === '\n') {
      flush();
      nodes.push({ type: 'break' });
      index++;
      continue;
    }

    buffer += character;
    index++;
  }

  flush();
  return nodes;
}

function parseEmphasis(
  text: string,
  start: number
): { node: MdInline; end: number } | null {
  const marker = text[start];
  const run = countRun(text, start, marker);
  const strong = run >= 2;
  const delimiter = strong ? marker.repeat(2) : marker;
  const open = start + delimiter.length;

  if (open >= text.length || /\s/.test(text[open])) return null;
  // `_` does not open inside a word: `snake_case_name` stays a word.
  if (marker === '_' && start > 0 && /[0-9A-Za-z]/.test(text[start - 1])) return null;

  const close = findClosingDelimiter(text, open, delimiter, marker);
  if (close === -1) return null;

  const inner = text.slice(open, close);
  if (inner.length === 0) return null;

  return {
    node: { type: strong ? 'strong' : 'emphasis', children: parseInline(inner) },
    end: close + delimiter.length,
  };
}

function findClosingDelimiter(
  text: string,
  from: number,
  delimiter: string,
  marker: string
): number {
  for (let index = from; index < text.length; index++) {
    if (text[index] !== marker) continue;
    const run = countRun(text, index, marker);
    if (run < delimiter.length) continue;
    if (index > 0 && /\s/.test(text[index - 1])) continue;
    // `_` does not close inside a word either.
    if (
      marker === '_' &&
      index + run < text.length &&
      /[0-9A-Za-z]/.test(text[index + run])
    ) {
      continue;
    }
    return index;
  }
  return -1;
}

function parseLink(text: string, start: number): { node: MdInline; end: number } | null {
  let depth = 0;
  let labelEnd = -1;

  for (let index = start + 1; index < text.length; index++) {
    const character = text[index];
    if (character === '\\') {
      index++;
      continue;
    }
    if (character === '[') depth++;
    else if (character === ']') {
      if (depth === 0) {
        labelEnd = index;
        break;
      }
      depth--;
    }
  }
  if (labelEnd === -1) return null;

  let index = labelEnd + 1;
  if (text[index] !== '(') return null;
  index++;
  while (index < text.length && /[ \t]/.test(text[index])) index++;

  let href = '';
  if (text[index] === '<') {
    const close = text.indexOf('>', index);
    if (close === -1) return null;
    href = text.slice(index + 1, close);
    index = close + 1;
  } else {
    let parentheses = 0;
    let destination = '';
    while (index < text.length) {
      const character = text[index];
      if (character === '\\' && index + 1 < text.length) {
        destination += text[index + 1];
        index += 2;
        continue;
      }
      if (character === '(') parentheses++;
      else if (character === ')') {
        if (parentheses === 0) break;
        parentheses--;
      } else if (/\s/.test(character)) break;
      destination += character;
      index++;
    }
    href = destination;
  }

  while (index < text.length && /[ \t]/.test(text[index])) index++;
  if (text[index] === '"' || text[index] === "'") {
    const quote = text[index];
    const close = text.indexOf(quote, index + 1);
    if (close === -1) return null;
    index = close + 1;
  }
  while (index < text.length && /[ \t]/.test(text[index])) index++;
  if (text[index] !== ')') return null;
  index++;

  const label = text.slice(start + 1, labelEnd);
  return {
    node: { type: 'link', href: decodeEntities(href), children: parseInline(label) },
    end: index,
  };
}

function decodeEntities(value: string): string {
  return value.replace(/&(#?[0-9a-zA-Z]+);/g, (match, name: string) => {
    const decoded = ENTITIES[name] ?? ENTITIES[name.toLowerCase()];
    return decoded ?? match;
  });
}

function countRun(text: string, from: number, character: string): number {
  let count = 0;
  while (from + count < text.length && text[from + count] === character) count++;
  return count;
}

function findRun(text: string, from: number, character: string, length: number): number {
  for (let index = from; index < text.length; index++) {
    if (text[index] !== character) continue;
    if (countRun(text, index, character) >= length) return index;
  }
  return -1;
}

function trimCodeSpan(value: string): string {
  if (value.length >= 2 && value.startsWith(' ') && value.endsWith(' ') && value.trim() !== '') {
    return value.slice(1, -1);
  }
  return value;
}
