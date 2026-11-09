/**
 * The message merge that lets a locale lag behind the English catalogue.
 *
 * The nine catalogues move together — a new key lands in all of them in the
 * same commit, and the key-parity test holds that. The merge is the safety
 * net under that rule: if a catalogue ever falls behind, the key it does not
 * carry falls back to the English wording instead of to the key path itself.
 *
 * The merge is what makes that fallback work on both sides of the render:
 * `getRequestConfig` hands the merged catalogue to the server components and
 * `getMessages` hands the same object to `NextIntlClientProvider`, so a
 * client component never sees a missing key.
 *
 * Two rules make the merge safe for a catalogue that stopped moving:
 *
 *   1. The English catalogue decides the SHAPE. The merged catalogue has
 *      exactly the English key set — a key the locale invented is dropped,
 *      a key the locale lacks is filled from English. Nothing renders a
 *      key path.
 *   2. The English catalogue also decides the PLACEHOLDERS. A locale whose
 *      copy names `{count}` where English names `{amount}` would fail to
 *      format at render time and fall back to the key path, so the English
 *      string wins whenever the two disagree.
 */

export type Messages = Record<string, unknown>;

function isPlainObject(value: unknown): value is Messages {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * The names of the ICU placeholders a message uses, sorted.
 *
 * Only the top-level names count: `{count}` and `{count, plural, one {x}
 * other {y}}` both name `count`, and the branch bodies of a plural are not
 * arguments of their own.
 */
export function placeholderNames(message: string): string[] {
  const names: string[] = [];
  let depth = 0;
  let start = -1;

  for (let i = 0; i < message.length; i++) {
    const char = message[i];
    if (char === '{') {
      if (depth === 0) start = i;
      depth++;
    } else if (char === '}') {
      depth--;
      if (depth === 0 && start !== -1) {
        const name = message.slice(start + 1, i).split(',')[0].trim();
        if (/^[A-Za-z0-9_]+$/.test(name)) names.push(name);
        start = -1;
      }
    }
  }

  return names.sort();
}

function samePlaceholders(english: string, other: string): boolean {
  const a = placeholderNames(english);
  const b = placeholderNames(other);
  return a.length === b.length && a.every((name, index) => name === b[index]);
}

/**
 * Merge one value of the English catalogue with the value the locale has.
 *
 * Objects merge key by key, arrays are taken whole from the locale, and a
 * string is taken from the locale only when it names the same placeholders
 * as the English string.
 *
 * Arrays are a unit: a row of the comparison table is a row, and merging two
 * tables position by position would mix one locale's capability name with
 * another locale's column. The arrays in this catalogue are read with
 * `t.raw()` and rendered as plain text, so they are never formatted and a
 * placeholder inside one is never substituted — which is why the placeholder
 * rule below does not reach into them.
 */
function mergeValue(english: unknown, other: unknown): unknown {
  if (other === undefined) return english;

  const englishIsObject = isPlainObject(english);
  const otherIsObject = isPlainObject(other);

  if (englishIsObject || otherIsObject) {
    // A shape mismatch is a stale catalogue, not a translation.
    if (!englishIsObject || !otherIsObject) return english;
    const merged: Messages = {};
    for (const [key, value] of Object.entries(english)) {
      merged[key] = mergeValue(value, (other as Messages)[key]);
    }
    return merged;
  }

  if (Array.isArray(english) || Array.isArray(other)) {
    if (!Array.isArray(english) || !Array.isArray(other)) return english;
    // An empty array is a catalogue that lost its content, not a translation.
    if (other.length === 0) return english;
    return other;
  }

  if (typeof english === 'string' && typeof other === 'string') {
    return samePlaceholders(english, other) ? other : english;
  }

  if (typeof english !== typeof other) return english;
  return other;
}

/**
 * The catalogue a locale actually renders.
 *
 * The result has the English key set exactly, with the locale's own words
 * wherever the locale carries them and English everywhere else.
 */
export function mergeMessages(english: Messages, locale: Messages): Messages {
  const merged: Messages = {};
  for (const [key, value] of Object.entries(english)) {
    merged[key] = mergeValue(value, locale[key]);
  }
  return merged;
}
