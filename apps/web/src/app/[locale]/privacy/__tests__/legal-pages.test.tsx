import React from 'react';

import { PRIVACY, TERMS } from '@/lib/legal';

import { generateMetadata as privacyMetadata } from '../../privacy/page';
import { generateMetadata as termsMetadata } from '../../terms/page';

// The metadata helper imports the catalogue reader from next-intl, whose
// server build is ESM and cannot be loaded by the test runtime. The catalogue
// is not what this test is about.
jest.mock('next-intl/server', () => ({
  getTranslations: jest.fn(async () => ({
    title: 'a title',
    description: 'a description',
  })),
}));

/**
 * The two legal pages.
 *
 * The Google consent screen asks for a privacy policy and a set of terms
 * before the app can be published to the public. These two pages are those
 * two documents - so the test says what they must not be: empty, or a
 * document without a section, or a page that claims a canonical of its own
 * without the hreflang map beside it.
 *
 * The pages are server components; the test renders the document data rather
 * than the markup, because the markup is the shared renderer and the text is
 * what a visitor reads.
 */

describe('the privacy policy', () => {
  it('says what is stored, where it is stored and who can read it', () => {
    const headings = PRIVACY.sections.map((section) => section.heading);

    expect(headings).toEqual(
      expect.arrayContaining([
        expect.stringMatching(/stored/i),
        expect.stringMatching(/where/i),
        expect.stringMatching(/who can read/i),
      ]),
    );
  });

  it('has a section for every paragraph it makes', () => {
    for (const section of PRIVACY.sections) {
      expect(section.paragraphs.length).toBeGreaterThan(0);
      for (const paragraph of section.paragraphs) {
        expect(paragraph.length).toBeGreaterThan(20);
      }
    }
  });

  it('declares its own title and description', () => {
    expect(PRIVACY.title.length).toBeGreaterThan(0);
    expect(PRIVACY.description.length).toBeGreaterThan(0);
  });

  it('names the buyer memory', () => {
    const headings = PRIVACY.sections.map((section) => section.heading);

    expect(headings).toEqual(
      expect.arrayContaining([expect.stringMatching(/buyer memory/i)]),
    );
  });

  it('says what the buyer memory is, where it belongs and how long it is kept', () => {
    const section = PRIVACY.sections.find(
      (candidate) => /buyer memory/i.test(candidate.heading),
    );

    expect(section).toBeDefined();
    const text = [...(section?.paragraphs ?? []), ...(section?.points ?? [])]
      .join(' ')
      .toLowerCase();
    expect(text).toContain('signed in');
    expect(text).toContain('read back');
    expect(text).toContain('delete');
    expect(text).toContain('kept');
  });

  it('says what the memory steers, and only what it steers', () => {
    // The memory is read back into the answers AND it steers what the buyer
    // is shown: the search applies it, a ruled-out area is not returned.
    // A policy must not promise what the product does not do - and it must
    // not hide what it does.
    const section = PRIVACY.sections.find(
      (candidate) => /buyer memory/i.test(candidate.heading),
    );
    const privacyText = [...(section?.paragraphs ?? []), ...(section?.points ?? [])]
      .join(' ')
      .toLowerCase();

    const termsSection = TERMS.sections.find((candidate) => /buyer memory/i.test(candidate.heading));
    const termsText = [...(termsSection?.paragraphs ?? []), ...(termsSection?.points ?? [])]
      .join(' ')
      .toLowerCase();

    for (const text of [privacyText, termsText]) {
      expect(text).toContain('steers what you are shown');
      expect(text).toContain('not returned at all');
    }
  });
});

describe('the terms of use', () => {
  it('says what the deployment is and is not', () => {
    const headings = TERMS.sections.map((section) => section.heading);

    expect(headings).toEqual(
      expect.arrayContaining([
        expect.stringMatching(/what this is/i),
        expect.stringMatching(/advice/i),
      ]),
    );
  });

  it('has a section for every paragraph it makes', () => {
    for (const section of TERMS.sections) {
      expect(section.paragraphs.length).toBeGreaterThan(0);
      for (const paragraph of section.paragraphs) {
        expect(paragraph.length).toBeGreaterThan(20);
      }
    }
  });
});

describe('the metadata of the legal pages', () => {
  it('declares a canonical and the whole hreflang map', async () => {
    const metadata = await privacyMetadata({ params: Promise.resolve({ locale: 'pl' }) });

    expect(metadata.title).toBe(PRIVACY.title);
    expect(metadata.description).toBe(PRIVACY.description);
    expect(metadata.alternates?.canonical).toContain('/pl/privacy');
    expect(Object.keys(metadata.alternates?.languages ?? {})).toContain('x-default');
  });

  it('gives the terms their own canonical', async () => {
    const metadata = await termsMetadata({ params: Promise.resolve({ locale: 'en' }) });

    expect(metadata.title).toBe(TERMS.title);
    expect(metadata.alternates?.canonical).toContain('/en/terms');
  });
});
