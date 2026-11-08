/**
 * Guards the contract between the PDF/JSON-LD helpers and the message
 * catalogue.
 *
 * The helpers in `pdf-export.ts`, `investment-pdf-export.ts` and
 * `structured-data.ts` read their labels from the catalogue by key. A typo in
 * a key name is invisible at compile time — `useTranslations` would just hand
 * back the key path and the document would ship with "monthlyTco" printed on
 * it. These tests fail loudly instead.
 */

import { DEFAULT_TCO_PDF_COPY } from '../pdf-export';
import { DEFAULT_INVESTMENT_PDF_COPY } from '../investment-pdf-export';

import enCatalog from '../../../messages/en.json';
import plCatalog from '../../../messages/pl.json';
import ruCatalog from '../../../messages/ru.json';
import deCatalog from '../../../messages/de.json';
import esCatalog from '../../../messages/es.json';
import itCatalog from '../../../messages/it.json';
import ptCatalog from '../../../messages/pt.json';
import trCatalog from '../../../messages/tr.json';
import ukCatalog from '../../../messages/uk.json';

type Catalog = Record<string, unknown>;

const CATALOGS: Record<string, Catalog> = {
  en: enCatalog as Catalog,
  pl: plCatalog as Catalog,
  ru: ruCatalog as Catalog,
  de: deCatalog as Catalog,
  es: esCatalog as Catalog,
  it: itCatalog as Catalog,
  pt: ptCatalog as Catalog,
  tr: trCatalog as Catalog,
  uk: ukCatalog as Catalog,
};

const get = (catalog: Catalog, path: string): unknown =>
  path.split('.').reduce<unknown>((acc, part) => (acc == null ? null : (acc as Catalog)[part]), catalog);

describe('message catalogue covers the PDF and JSON-LD helpers', () => {
  describe.each(Object.entries(CATALOGS))('[%s]', (locale, catalog) => {
    it('has every label the TCO PDF asks for', () => {
      const missing = Object.keys(DEFAULT_TCO_PDF_COPY).filter(
        (key) => typeof get(catalog, `mortgage.pdf.${key}`) !== 'string'
      );
      expect(missing).toEqual([]);
    });

    it('has every label the investment PDF asks for', () => {
      const missing = Object.keys(DEFAULT_INVESTMENT_PDF_COPY).filter(
        (key) => typeof get(catalog, `investment.pdf.${key}`) !== 'string'
      );
      expect(missing).toEqual([]);
    });

    it('has a label for every score-breakdown key the API returns', () => {
      const scoreLabels = get(catalog, 'investment.pdf.scoreLabels') as Catalog;
      expect(scoreLabels).toBeDefined();
      const missing = ['location', 'type', 'size', 'rooms', 'recency', 'amenities'].filter(
        (key) => typeof scoreLabels[key] !== 'string'
      );
      expect(missing).toEqual([]);
    });

    it('has the JSON-LD description, keywords, language names and FAQ', () => {
      expect(typeof get(catalog, 'seo.structuredData.description')).toBe('string');
      expect(typeof get(catalog, 'seo.structuredData.keywords')).toBe('string');

      const languages = get(catalog, 'seo.structuredData.languages') as Catalog;
      expect(Object.keys(languages)).toHaveLength(9);

      const faq = get(catalog, 'seo.structuredData.faq') as Catalog;
      for (let i = 1; i <= 8; i++) {
        expect(typeof faq[`q${i}`]).toBe('string');
        expect(typeof faq[`a${i}`]).toBe('string');
      }
    });
  });

  it('keeps the same placeholder names in every locale', () => {
    const placeholders = (value: string) => (value.match(/\{(\w+)\}/g) ?? []).sort();

    for (const locale of Object.keys(CATALOGS)) {
      const catalog = CATALOGS[locale];

      expect(placeholders(get(catalog, 'mortgage.pdf.pageOf') as string)).toEqual(
        placeholders(get(CATALOGS.en, 'mortgage.pdf.pageOf') as string)
      );
      expect(placeholders(get(catalog, 'mortgage.pdf.generated') as string)).toEqual(
        placeholders(get(CATALOGS.en, 'mortgage.pdf.generated') as string)
      );
      expect(placeholders(get(catalog, 'mortgage.pdf.breakEvenPoint') as string)).toEqual(
        placeholders(get(CATALOGS.en, 'mortgage.pdf.breakEvenPoint') as string)
      );
      expect(placeholders(get(catalog, 'mortgage.pdf.advantages') as string)).toEqual(
        placeholders(get(CATALOGS.en, 'mortgage.pdf.advantages') as string)
      );
      expect(placeholders(get(catalog, 'investment.pdf.pageOf') as string)).toEqual(
        placeholders(get(CATALOGS.en, 'investment.pdf.pageOf') as string)
      );
      expect(placeholders(get(catalog, 'investment.pdf.generated') as string)).toEqual(
        placeholders(get(CATALOGS.en, 'investment.pdf.generated') as string)
      );
    }
  });
});
