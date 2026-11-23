/**
 * Guards the tier copy — the README compare table, the README FAQ and the
 * landing tier cards — against what the repository actually ships.
 *
 * The table used to describe a split the code had already left behind: the
 * free column promised a "demo catalogue" while the free tier answered from
 * the official register of notarial transaction prices, and it gave the
 * enrichment pipeline, the alerts and the lead scoring to the hosted tier
 * although all three are in this tree. A table that lags the code is a lie
 * told twice — once in the README, once on the landing page.
 *
 * The decision the table has to agree with is on disk:
 * `docs/reasoning/2026-11-22-free-tier-and-hosted-tier.md`. The engine stays
 * MIT and ships the register; the hosted tier ships the live listing feeds,
 * the CRM around them and the enterprise controls.
 *
 * The seven frozen catalogues stay frozen: the tier copy is maintained in
 * English and Polish, and the frozen locales keep their own translation of
 * the wording they had. This file therefore checks English and Polish.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, it, expect } from '@jest/globals';

import enCatalog from '../../../messages/en.json';
import plCatalog from '../../../messages/pl.json';

const README = readFileSync(join(process.cwd(), '..', '..', 'README.md'), 'utf-8');

type Row = { capability: string; free: string; hosted: string };

/** The compare table, as the rows it is made of. */
function tierRows(): Row[] {
  const heading = README.indexOf('## The hosted version, and what comes next');
  expect(heading).toBeGreaterThan(-1);

  const table = README.slice(heading).split('\n').filter((line: string) => line.startsWith('|'));
  // The header row, the separator, then the capability rows.
  return table.slice(2).map((line: string) => {
    const cells = line
      .split('|')
      .slice(1, -1)
      .map((cell: string) => cell.trim());
    return { capability: cells[0], free: cells[1], hosted: cells[2] };
  });
}

/** The row whose capability matches a pattern. */
function rowMatching(pattern: RegExp): Row {
  const row = tierRows().find((candidate) => pattern.test(candidate.capability));
  expect(row).toBeDefined();
  return row!;
}

/**
 * What this repository ships today. Every one of these is in the tree, so
 * every one of them belongs in the free column of the compare table.
 */
const SHIPPED_BY_THIS_REPOSITORY: RegExp[] = [
  /official notarial transaction prices/i,
  /valuation with its evidence/i,
  /buyer memory/i,
  /accounts, favourites, saved searches/i,
  /alerts on saved searches/i,
  /neighbourhood index/i,
  /lead scoring/i,
  /enrichment pipeline/i,
  /hybrid vector \+ keyword search/i,
  /your own LLM keys/i,
];

describe('the tier copy states what each tier ships today', () => {
  describe('the README compare table', () => {
    it('gives the official notarial prices to the free column', () => {
      const row = rowMatching(/official notarial transaction prices/i);

      expect(row.capability).toMatch(/Rejestr Cen Nieruchomości/);
      expect(row.free).toBe('Free');
      expect(row.hosted).toBe('Included');
    });

    it.each(SHIPPED_BY_THIS_REPOSITORY)(
      'puts %s in the free column, because the repository ships it',
      (pattern: RegExp) => {
        const row = rowMatching(pattern);

        expect(row.free).toBe('Free');
      }
    );

    it('gives the live listing feeds, not the register, to the hosted tier', () => {
      const row = rowMatching(/live listing feeds/i);

      expect(row.free).toBe('—');
      expect(row.hosted).toBe('Pro');
    });

    it('names what the hosted tier adds on top', () => {
      const hosted = tierRows()
        .map((row) => row.hosted)
        .filter((cell) => cell !== 'Included')
        .join(' ');

      expect(hosted).toMatch(/Pro/);
      expect(hosted).toMatch(/Enterprise/);
      const capabilities = tierRows().map((row) => row.capability).join(' | ');
      expect(capabilities).toMatch(/more countries/i);
      expect(capabilities).toMatch(/alerts against the live feeds/i);
      expect(capabilities).toMatch(/AI CRM with bi-directional sync/i);
      expect(capabilities).toMatch(/connectors/i);
      expect(capabilities).toMatch(/SSO, MFA/i);
      expect(capabilities).toMatch(/white-label/i);
      expect(capabilities).toMatch(/SLAs/i);
    });

    it('keeps the pricing line the operator set', () => {
      expect(README).toMatch(/\*\*Free `\$0`\*\* · \*\*Pro `\$29\/mo`\*\* · \*\*Enterprise \(custom\)\*\*/);
    });

    it('does not give the free tier away in the FAQ answer', () => {
      const faq = README.slice(README.indexOf('**What is the difference to the hosted version?**'));

      expect(faq.slice(0, 400)).not.toMatch(/accounts, saved\s+searches, alerts/i);
      expect(faq.slice(0, 400)).toMatch(/live listing feeds/i);
    });
  });

  describe('the landing tier cards', () => {
    const exits = (locale: 'en' | 'pl') =>
      (locale === 'en' ? enCatalog : plCatalog).landing.exits as {
        run: { body: string };
        hosted: { body: string };
      };

    it('names the register in the free tier card, in English', () => {
      expect(exits('en').run.body).toMatch(/Rejestr Cen Nieruchomości/);
    });

    it('names the register in the free tier card, in Polish', () => {
      expect(exits('pl').run.body).toMatch(/Rejestru Cen Nieruchomości/);
    });

    it('names the hosted tier what the decision record gives it, in English', () => {
      const body = exits('en').hosted.body;

      expect(body).toMatch(/live listing feeds/i);
      expect(body).toMatch(/alerts/i);
      expect(body).toMatch(/AI CRM/i);
      expect(body).toMatch(/bi-directional sync/i);
      expect(body).toMatch(/connectors/i);
      expect(body).toMatch(/SSO\/MFA/);
      expect(body).toMatch(/white-label/i);
      expect(body).toMatch(/SLAs?/);
      // The enrichment pipeline is in this repository, so it is not the
      // hosted tier's exclusive claim.
      expect(body).not.toMatch(/enrichment pipeline/i);
    });

    it('names the hosted tier what the decision record gives it, in Polish', () => {
      const body = exits('pl').hosted.body;

      expect(body).toMatch(/żywe strumienie ofert/i);
      expect(body).toMatch(/alerty/i);
      expect(body).toMatch(/AI CRM/i);
      expect(body).toMatch(/synchronizacją dwukierunkową/i);
      expect(body).toMatch(/konektory/i);
      expect(body).toMatch(/SSO\/MFA/);
      expect(body).toMatch(/white-label/i);
      expect(body).toMatch(/SLA/);
      expect(body).not.toMatch(/potok wzbogacania/i);
    });

    it('says the same thing in both maintained catalogues', () => {
      const shared = ['AI CRM', 'SSO/MFA', 'white-label'];
      for (const capability of shared) {
        expect(exits('en').hosted.body).toContain(capability);
        expect(exits('pl').hosted.body).toContain(capability);
      }
    });
  });
});
