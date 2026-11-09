import { render, screen } from '@testing-library/react';

import { PassageLedger } from '../passage-ledger';
import type { EnhancedCitation } from '@/lib/types';

/**
 * The passages the answer was built from.
 *
 * Every field on a row comes from the citation the API returned - the
 * document, the place in it, the excerpt and the confidence. The ledger
 * must not read anything out of the answer text.
 */
function makeCitation(overrides: Partial<EnhancedCitation> = {}): EnhancedCitation {
  return {
    source: 'umowa-przedwstepna.pdf',
    chunk_index: 4,
    source_type: 'pdf',
    confidence: 'high',
    confidence_score: 0.86,
    content_snippet: 'Kupujący wpłaci zadatek w wysokości 48 900 zł.',
    citation_hash: 'abc',
    is_duplicate: false,
    validated: false,
    ...overrides,
  };
}

describe('PassageLedger', () => {
  it('numbers the passages and says how many were asked for', () => {
    render(<PassageLedger citations={[makeCitation()]} topK={3} />);

    expect(screen.getByText('Retrieved passages')).toBeInTheDocument();
    expect(screen.getByText('1 of 3 · confidence')).toBeInTheDocument();
    expect(screen.getByText('[1]')).toBeInTheDocument();
  });

  it('names the document and the place in it', () => {
    render(<PassageLedger citations={[makeCitation()]} topK={3} />);

    expect(screen.getByText('umowa-przedwstepna.pdf · chunk 4')).toBeInTheDocument();
  });

  it('prefers the page over the chunk', () => {
    render(
      <PassageLedger citations={[makeCitation({ page_number: 2, chunk_index: 4 })]} topK={3} />
    );

    expect(screen.getByText('umowa-przedwstepna.pdf · p. 2')).toBeInTheDocument();
  });

  it('quotes the passage and scores it', () => {
    render(<PassageLedger citations={[makeCitation()]} topK={3} />);

    expect(
      screen.getByText('“Kupujący wpłaci zadatek w wysokości 48 900 zł.”')
    ).toBeInTheDocument();
    expect(screen.getByText('0.86')).toBeInTheDocument();
  });

  it('says so when the citation carries no score', () => {
    render(
      <PassageLedger
        citations={[makeCitation({ confidence_score: 0 })]}
        topK={3}
      />
    );

    // Zero is a score, but a citation without one has nothing to state.
    expect(screen.getByText('0.00')).toBeInTheDocument();
  });

  it('falls back to an unknown source', () => {
    render(
      <PassageLedger
        citations={[makeCitation({ source: null, source_title: null, chunk_index: null })]}
        topK={3}
      />
    );

    expect(screen.getByText('Unknown source')).toBeInTheDocument();
  });
});
