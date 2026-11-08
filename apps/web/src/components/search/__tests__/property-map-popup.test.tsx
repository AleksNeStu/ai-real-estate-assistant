import React from 'react';
import { render, screen } from '@testing-library/react';

import { PropertyMapPopup, generatePopupHTML } from '../property-map-popup';
import type { PropertyMapPoint } from '../property-map-utils';

const point: PropertyMapPoint = {
  id: 'p-1',
  lat: 50.06,
  lon: 19.94,
  title: 'Mieszkanie w Śródmieściu',
  city: 'Krakow',
  country: 'Poland',
  price: 591030,
  currency: 'PLN',
  rooms: 3,
  area_sqm: 62,
};

describe('PropertyMapPopup', () => {
  it('shows the price in the currency of the listing', () => {
    render(<PropertyMapPopup point={point} />);

    // The popup used to print a dollar sign in front of every amount.
    expect(screen.getByText('PLN 591,030')).toBeInTheDocument();
    expect(screen.queryByText('$591,030')).not.toBeInTheDocument();
  });

  it('shows the price per square meter in the same currency', () => {
    render(<PropertyMapPopup point={{ ...point, price_per_sqm: 9532 }} />);

    expect(screen.getByText(/PLN 9,532/)).toBeInTheDocument();
  });
});

describe('generatePopupHTML', () => {
  it('builds the mapbox popup in the currency of the listing', () => {
    const html = generatePopupHTML(point, {
      priceOnRequest: 'Price on request',
      untitled: 'Untitled',
      locationUnavailable: 'Location unavailable',
      beds: 'beds',
      locale: 'en',
    });

    // The number format separates the currency code and the amount with a
    // narrow no-break space, so the whitespace is normalised first.
    const text = html.replace(/\s+/g, ' ');
    expect(text).toContain('PLN 591,030');
    expect(text).not.toContain('$591,030');
  });
});
