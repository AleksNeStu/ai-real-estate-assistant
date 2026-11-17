import { pinLabel, pricePin } from '../map-pin';

const divIconMock = jest.fn((options: unknown) => ({ options }));

jest.mock('leaflet', () => ({
  divIcon: (...args: unknown[]) => divIconMock(...args),
}));

describe('the price pin', () => {
  beforeEach(() => {
    divIconMock.mockClear();
  });

  it('states the price of the listing', () => {
    const pin = pricePin(pinLabel(322000, 'PLN', 'en'));

    expect(String(pin.options.html)).toContain('322');
  });

  it('has a box, so the pin can be seen and clicked', () => {
    const pin = pricePin(pinLabel(322000, 'PLN', 'en'));

    const size = pin.options.iconSize as [number, number];
    const anchor = pin.options.iconAnchor as [number, number];

    // A zero-sized marker has no hit area: the price would be on the map
    // and the pin could not be opened.
    expect(size).not.toEqual([0, 0]);
    expect(size[0]).toBeGreaterThan(0);
    expect(size[1]).toBeGreaterThan(0);

    // The chip is centred in that box, so the pin sits on the listing.
    expect(anchor).toEqual([size[0] / 2, size[1] / 2]);
  });

  it('prints the price the row next to it prints', () => {
    // The exact price, not a rounded one: 322 000 zł must not read as "322k".
    expect(pinLabel(322000, 'PLN', 'en')).toContain('322');
    expect(pinLabel(322000, 'PLN', 'en')).not.toContain('K');
    expect(pinLabel(2100, 'PLN', 'en')).not.toContain('K');
  });

  it('says so when the listing has no price', () => {
    expect(pinLabel(undefined, 'PLN', 'en')).toBe('—');
  });
});
