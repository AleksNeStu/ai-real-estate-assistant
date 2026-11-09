import { render, screen } from '@testing-library/react';

import { ParsedChips } from '../parsed-chips';

/**
 * The row of the parsed sentence.
 *
 * The label, the chips and the count are the three pieces the landing's
 * instrument already renders; the row is the same shape everywhere.
 */
describe('ParsedChips', () => {
  it('renders the parsed label and every chip', () => {
    render(<ParsedChips chips={['city = Kraków', 'price ≤ 500 000 zł', 'rooms = 2']} />);

    expect(screen.getByText('parsed')).toBeInTheDocument();
    expect(screen.getByText('city = Kraków')).toBeInTheDocument();
    expect(screen.getByText('price ≤ 500 000 zł')).toBeInTheDocument();
    expect(screen.getByText('rooms = 2')).toBeInTheDocument();
  });

  it('renders the count of the listings', () => {
    render(<ParsedChips chips={['city = Kraków']} count={38} />);

    expect(screen.getByText('38 matches')).toBeInTheDocument();
  });

  it('leaves the count out when there is nothing to count', () => {
    render(<ParsedChips chips={['city = Kraków']} count={0} />);

    expect(screen.queryByText('0 matches')).not.toBeInTheDocument();
  });

  it('says so when the sentence produced no filter', () => {
    render(<ParsedChips chips={[]} />);

    expect(
      screen.getByText('The sentence decides — add filters of your own.')
    ).toBeInTheDocument();
    expect(screen.queryByText('parsed')).not.toBeNull();
  });

  it('renders the note beside the chips', () => {
    const note = 'Read from your sentence — change any of them in the filters.';
    render(<ParsedChips chips={['city = Kraków']} note={note} />);

    expect(screen.getByText(note)).toBeInTheDocument();
  });
});
