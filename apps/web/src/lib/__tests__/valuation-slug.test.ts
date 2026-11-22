import {
  decodeValuationSlug,
  encodeValuationSlug,
  foldToAscii,
  normalizeAddressPart,
} from '../valuation-slug';

describe('the slug of a valuation', () => {
  it('names the place', () => {
    const slug = encodeValuationSlug({
      city: 'Kraków',
      street: 'Myśliwska',
      area_sqm: 60,
      rooms: 3,
    });

    expect(slug).toBe('krakow~mysliwska~60~3');
  });

  it('is the same for the same place', () => {
    const first = encodeValuationSlug({
      city: 'Kraków',
      street: 'Myśliwska',
      area_sqm: 60,
      rooms: 3,
    });
    const second = encodeValuationSlug({
      city: '  kraków ',
      street: 'MYŚLIWSKA',
      area_sqm: 60,
      rooms: 3,
    });

    expect(first).toBe(second);
  });

  it('folds the letters that do not decompose', () => {
    // Without a transliteration table "Łódź" loses the L and the Z and
    // becomes "odz" - a link to a street that does not exist.
    expect(foldToAscii('Łódź')).toBe('lodz');
    expect(foldToAscii('Kraków')).toBe('krakow');
  });

  it('carries a number the reader did not give as absent', () => {
    const slug = encodeValuationSlug({ city: 'Kraków', street: 'Myśliwska' });

    expect(slug).toBe('krakow~mysliwska~x~x');
  });

  it('has no link for a place it cannot name', () => {
    expect(encodeValuationSlug({ city: '' })).toBe('');
  });

  it('normalises a name into a URL part', () => {
    expect(normalizeAddressPart('  al. 3 Maja  ')).toBe('al-3-maja');
    expect(normalizeAddressPart('---')).toBe('');
  });
});

describe('decoding a slug', () => {
  it('gives the place back', () => {
    const subject = decodeValuationSlug('krakow~mysliwska~60~3');

    expect(subject).toEqual({
      city: 'krakow',
      street: 'mysliwska',
      area_sqm: 60,
      rooms: 3,
    });
  });

  it('leaves out a number the reader did not give', () => {
    const subject = decodeValuationSlug('krakow~mysliwska~x~x');

    expect(subject?.area_sqm).toBeUndefined();
    expect(subject?.rooms).toBeUndefined();
  });

  it('refuses a slug that names no place', () => {
    expect(decodeValuationSlug('')).toBeNull();
    expect(decodeValuationSlug('krakow')).toBeNull();
    expect(decodeValuationSlug('krakow~mysliwska~60')).toBeNull();
    expect(decodeValuationSlug('~mysliwska~60~3')).toBeNull();
  });

  it('refuses a part that claims to be a number and is not', () => {
    expect(decodeValuationSlug('krakow~mysliwska~sixty~3')).toBeNull();
    expect(decodeValuationSlug('krakow~mysliwska~60~zero')).toBeNull();
  });

  it('round-trips a place', () => {
    const subject = { city: 'Łódź', street: 'Piotrkowska', area_sqm: 45, rooms: 2 };

    const decoded = decodeValuationSlug(encodeValuationSlug(subject));

    expect(decoded).not.toBeNull();
    expect(decoded?.city).toBe('lodz');
    expect(decoded?.street).toBe('piotrkowska');
    expect(decoded?.area_sqm).toBe(45);
    expect(decoded?.rooms).toBe(2);
  });
});
