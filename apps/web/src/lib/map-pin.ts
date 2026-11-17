import { divIcon } from 'leaflet';
import { formatMapPinPrice } from '@/lib/format';

/**
 * The box the chip is drawn in.
 *
 * It is the marker element Leaflet measures, positions and makes clickable.
 * The chip itself is centred in it, so the box only has to be big enough to
 * hold the price and to be a real hit area - the price text is not wrapped,
 * so a longer price simply reaches past the box.
 */
const CHIP_BOX_WIDTH = 96;
const CHIP_BOX_HEIGHT = 22;

/**
 * The price pin - one pin for every map in the product.
 *
 * The landing's hero map prints the price on the pin, because a pin that
 * says what the listing costs is the whole point of a map of listings: a
 * dot tells the visitor where, the price tells them whether it is worth
 * the click. The search map had a bare dot, so the same map answered a
 * weaker question in the place where the visitor actually searches.
 *
 * The pin is the price, and the price is the price the row next to it
 * shows - one price, one spelling. The chip used to print the number in
 * thousands with no magnitude check, so 322 000 zł read as "322k" and
 * 4 100 zł read as "4k" next to a row that said "4 100 zł". Carrying the
 * currency into the chip was not enough either: a 2 100 zł listing still
 * read as "2.1K", which is a different price. The chip prints the price
 * the row prints, and only shortens it when the number is genuinely too
 * long for a chip.
 */
export function pricePin(
  label: string,
  highlighted = false
): ReturnType<typeof divIcon> {
  const background = highlighted ? 'hsl(var(--foreground))' : 'hsl(var(--background))';
  const color = highlighted ? 'hsl(var(--background))' : 'hsl(var(--foreground))';
  const border = highlighted ? 'hsl(var(--foreground))' : 'hsl(var(--border))';

  return divIcon({
    className: '',
    // The chip is centred in a box that Leaflet can measure, and the box is
    // what the visitor clicks. A zero-sized marker (the chip alone, drawn
    // with a transform) has no hit area at all: the price is on the map,
    // but the pin cannot be opened - and an assistive technology sees an
    // element with no size at all.
    html: `<div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);display:inline-flex;align-items:center;height:22px;padding:0 9px;border-radius:9999px;border:1px solid ${border};background:${background};color:${color};font-family:var(--font-mono),ui-monospace,monospace;font-size:11px;line-height:1;white-space:nowrap;box-shadow:0 2px 8px hsl(var(--foreground) / 0.28)">${label}</div>`,
    iconSize: [CHIP_BOX_WIDTH, CHIP_BOX_HEIGHT],
    iconAnchor: [CHIP_BOX_WIDTH / 2, CHIP_BOX_HEIGHT / 2],
  });
}

/**
 * The label of a price pin: the price, in the market's own spelling.
 *
 * The rows format the price with the Polish locale (the market's own
 * spelling), so the chip does the same - a pin that reads "2 100 zł" next
 * to a row that reads "2 100 zł" is one price, one spelling.
 */
export function pinLabel(price?: number, currency = 'PLN', locale = 'pl-PL'): string {
  return formatMapPinPrice(price, currency, locale);
}
