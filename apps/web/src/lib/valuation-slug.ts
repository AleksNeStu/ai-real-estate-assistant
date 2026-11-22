/**
 * The link to one valuation.
 *
 * WHY A VALUATION NEEDS A LINK
 *
 * The interactive valuation page answers in the browser: the reader types an
 * address, the register answers, and the answer dies with the tab. It cannot
 * be shared, it cannot be indexed, and it carries no structured data - so the
 * one surface the site earns impressions on cannot send a visitor anywhere.
 *
 * A link fixes that: the same address produces the same link, so the answer
 * can be sent to somebody, bookmarked, and read by a crawler that never runs
 * the JavaScript.
 *
 * WHY THE SLUG IS ASCII
 *
 * The slug is folded to ASCII on purpose. A URL with diacritics in it has two
 * spellings - the encoded one and the decoded one - and a canonical that names
 * one of them while a crawler arrives with the other is a page that competes
 * with itself. The register matches on folded text anyway (it folds the case
 * and the diacritics of every street before it compares), so folding the slug
 * costs nothing: the folded street finds the same sales the spelled street
 * would have found.
 *
 * The display name comes back from the register - `comparison_area` carries
 * the street as it is written there - so the page shows "Myśliwska" even
 * though the link says "mysliwska".
 *
 * WHY THE PERIOD IS NOT IN THE LINK
 *
 * The register moves: the same address is compared with a different set of
 * sales next month. A link that carried the period would freeze the answer -
 * and it would do it by pointing at a page whose content no longer matches
 * the URL, because the register behind it has moved on. So the link names the
 * PLACE, and the page states the period it used. One place, one link, always.
 */

/** The place a valuation is about. */
export interface ValuationSubject {
  city: string;
  street?: string | null;
  area_sqm?: number | null;
  rooms?: number | null;
}

/**
 * The separator between the parts of a slug.
 *
 * `~` is an unreserved character in a URI (RFC 3986), so it needs no percent
 * encoding and survives in an address bar as it is. Every other candidate -
 * `-`, `_`, `.` - occurs inside a street name, and a separator that occurs
 * inside its own data cannot be decoded unambiguously.
 */
const SEPARATOR = '~';

/** The part that stands for a number the reader did not give. */
const ABSENT = 'x';

/**
 * The letters that do not decompose into a base letter and a combining mark.
 *
 * `ó` decomposes (`o` + acute) and is handled by the general rule below, but
 * `ł` is a letter of its own: NFD leaves it alone, and without this table it
 * would be dropped as a non-ASCII character - "Łódź" would become "odz".
 */
const TRANSLITERATIONS: Record<string, string> = {
  ł: 'l',
  Ł: 'l',
  đ: 'd',
  Đ: 'd',
  ð: 'd',
  Ð: 'd',
  ø: 'o',
  Ø: 'o',
  æ: 'ae',
  Æ: 'ae',
  œ: 'oe',
  Œ: 'oe',
  ß: 'ss',
  ẞ: 'ss',
  þ: 'th',
  Þ: 'th',
};

/** Fold a name to its ASCII form: no case, no diacritics, no punctuation. */
export function foldToAscii(value: string): string {
  const transliterated = value.replace(
    /[łŁđĐðÐøØæÆœŒßẞþÞ]/g,
    (character) => TRANSLITERATIONS[character] ?? character,
  );
  return transliterated
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase();
}

/**
 * One part of a slug: the folded text with everything that is not a letter or
 * a digit replaced by a dash.
 */
export function normalizeAddressPart(value: string): string {
  return foldToAscii(value)
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/** A number as it goes into a slug: the rounded value, or the absent mark. */
function numericPart(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return ABSENT;
  const rounded = Math.round(value);
  return rounded > 0 ? String(rounded) : ABSENT;
}

/**
 * The link of one valuation.
 *
 * The same subject always produces the same slug, and a slug always decodes
 * back to the subject it was made from.
 */
export function encodeValuationSlug(subject: ValuationSubject): string {
  const city = normalizeAddressPart(subject.city ?? '');
  if (!city) return '';
  const street = normalizeAddressPart(subject.street ?? '');
  return [city, street, numericPart(subject.area_sqm), numericPart(subject.rooms)].join(
    SEPARATOR,
  );
}

/**
 * The subject a slug names.
 *
 * Returns `null` for a slug that is not one: a slug with the wrong number of
 * parts, an empty city, or a part that claims to be a number and is not.
 * A page that cannot name its place is a 404, not a guess.
 */
export function decodeValuationSlug(slug: string): ValuationSubject | null {
  if (!slug) return null;
  const parts = slug.split(SEPARATOR);
  if (parts.length !== 4) return null;

  const [city, street, area, rooms] = parts;
  if (!city) return null;

  const subject: ValuationSubject = { city, street: street || null };

  if (area !== ABSENT) {
    const parsed = Number(area);
    if (!Number.isFinite(parsed) || parsed <= 0) return null;
    subject.area_sqm = parsed;
  }

  if (rooms !== ABSENT) {
    const parsed = Number(rooms);
    if (!Number.isFinite(parsed) || parsed <= 0) return null;
    subject.rooms = parsed;
  }

  return subject;
}

/** The path of the page that answers for a slug. */
export function valuationPath(locale: string, slug: string): string {
  return `/${locale}/valuation/${slug}`;
}
