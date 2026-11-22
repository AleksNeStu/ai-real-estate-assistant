# How a city is priced from notarial deeds

*What a commercial AVM cannot show you: the sales the estimate stands on.*

Every automated valuation estimate is a number without its evidence — a model
that learned from a market and will not say which flats it looked at. This
repository does the other thing: it reads the **Rejestr Cen Nieruchomości**
(RCN), the Polish register of notarial prices, and it prices a place by
comparing it with the flats that actually sold around it. The estimate always
carries the sales it stands on: how many, over which period, from which
comparison area.

The register is free. Since **13 February 2026** the data in the RCN has been
published without charge (the amendment to the Geodesy and Land Surveying Act,
Dz.U. 2025 poz. 1542, in force three months after it was announced), and the
Head Office of Geodesy and Cartography publishes what the starostas collect —
so the comparison below is not a proprietary input. It is a public record.

This is a write-up of how the pricing works, with the numbers taken from the
official export of the Małopolskie voivodeship (`teryt 12`) and computed by
the repository's own code on **2026-11-22**. The newest deed in that export
is dated **2026-10-30** — the register lags, and that lag is part of the
answer.

---

## 1. What the register holds

Every sale of a flat in Poland is recorded by a notary. The deed carries the
price, the surface area, the date, the address, the market (new-build or
secondary) and, when they were recorded, the number of rooms, the floor and
the condition of the building.

That is the whole raw material of a comparison-based valuation:

| Field | What it is |
|---|---|
| `lok_cena_brutto` | the price of the flat itself (the register also carries the whole transaction, which may include a garage — that is a fallback, not the default) |
| `lok_powierzchnia` | the surface area, in m² |
| `dok_data` | the date of the deed |
| `nier_rodzaj`, `lok_funkcja` | the kind of unit and its function — only residential flats are read |
| `rynek` | the market: `rynekWtorny` (secondary) or `rynekNowy` (new-build) |
| `pokoj` / `kondygnacja` | rooms and floor, when recorded |

Two decisions follow from the shape of this data, and they are the reason the
valuation is a comparison rather than a model:

- **Only the secondary market is valued.** A new-build flat is a different
  product with a different price; mixing the two produces a number that
  describes nothing. When a subject has no secondary-market sales at all, the
  service says so in its notes and uses every registered sale instead of
  pretending.
- **The area is a band, not a point.** A comparable's area may differ from the
  subject's by 15 % (`DEFAULT_AREA_TOLERANCE`); a flat twice the size is not
  a comparable for a small one.

## 2. The contract: N, the period, the area

A price per square metre on its own is a claim. The service therefore refuses
to answer without three things, and every result carries them:

- **N** — the number of comparable sales the estimate stands on.
- **the period** — the first and the last deed date of that set.
- **the comparison area** — the street, or the city, the sales came from.

`apps/api/services/rcn_valuation.py` is the implementation; the result object
(`ValuationResult`) has fields for exactly these three, plus a `confidence`
label derived from N.

### How the comparable set is chosen

The comparison starts as narrow as it can be and widens only as far as it has
to. **Size and place give way before time does**: a sale three years old on
the same street says more about that street than a sale last month across the
city says about the flat. The ladder is:

1. the street, flats of a similar size;
2. the street, every size;
3. the city, flats of a similar size;
4. the city, every size;

and only then, if the set is still too thin, the **window** widens — 18 months
by default, up to 60 — because time is the last thing to give up.

Every step the selection takes is recorded in the result's `notes`, so the
answer says how it got there:

```text
Secondary market only (rynekWtorny).
Flats of a similar size (51–69 m²).
Flats with 3 rooms.
Based on 1569 registered sale(s) between 2025-04-30 and 2026-10-30.
```

The confidence label follows the size of the set: below 8 comparable sales a
result is *low*, below 20 it is *medium*, above it *high*. Below the minimum
of 5 the service produces **no estimate at all** — a set that small is an
anecdote, not a valuation. The comparable sales are still returned, because
the evidence is worth having; only the number is withheld.

## 3. A worked example

Kraków, a 60 m² flat with 3 rooms on the secondary market, computed from the
official Małopolskie export on 2026-11-22:

| | |
|---|---|
| estimate | **889 047 PLN** |
| range | 769 663 – 1 036 212 PLN |
| median price per m² | 14 817 PLN/m² |
| comparison area | Kraków (city-wide) |
| N | 1 569 sales |
| period | 2025-04-30 → 2026-10-30 |
| confidence | high |

The same question asked about one street, Myśliwska:

| | |
|---|---|
| estimate | **959 182 PLN** |
| range | 846 539 – 1 082 016 PLN |
| median price per m² | 15 986 PLN/m² |
| comparison area | Myśliwska, Kraków |
| N | 26 sales |
| period | 2025-05-12 → 2026-10-12 |
| confidence | high |

Five of the sales the second estimate stands on:

| Address | Area | Price | PLN/m² | Date |
|---|---|---|---|---|
| Myśliwska 68C | 60.49 m² | 1 200 000 PLN | 19 838 | 2026-10-12 |
| Myśliwska 55 | 53.09 m² | 960 000 PLN | 18 083 | 2026-10-02 |
| Myśliwska 66 | 57.75 m² | 919 000 PLN | 15 913 | 2026-09-01 |
| Myśliwska 66E | 57.52 m² | 1 028 856 PLN | 17 887 | 2026-08-24 |
| Myśliwska 68 | 64.48 m² | 1 225 000 PLN | 18 998 | 2026-08-24 |

The street estimate is 8 % above the city estimate, and the reason is in the
evidence: Myśliwska's registered prices per m² run higher than the city's, and
its own 26 sales are the ones being compared.

For scale: in the twelve months to 2026-10-30, 13 668 flats were registered
in Kraków, at a median of 14 949 PLN/m² (the middle half of them between
13 079 and 17 228 PLN/m²).

### When there is not enough

Ask about a street with four registered sales in the window and the answer
changes shape instead of shrinking quietly:

```text
Only 4 sale(s) on RÓGATKA — the comparison fell back to the whole city.
```

The estimate becomes the city's estimate, and the note says that is what
happened. A number that cannot be supported locally is not returned as if it
were.

## 4. The trend, measured rather than assumed

A forecast needs a rate, and a rate nobody measured is a constant wearing a
forecast's clothes. The service measures the trend the same way it measures
everything else — from the sales.

The comparable set is split in two by date. The median price per m² of the
older half is compared with the median of the newer half, and the difference
is annualised over the time between them. From the same export:

- **Kraków: +3.9 % a year** (40 947 sales between 2023-11-23 and 2026-10-30).
- **Myśliwska: −0.4 % a year** (26 sales between 2025-05-12 and 2026-10-12).

The measurement is **refused** — no trend is returned — when either half has
fewer than 4 sales, when the two halves are less than 180 days apart, or when
the annualised rate falls outside −15 % … +25 %, because a rate outside that
range is a handful of sales rather than a market.

## 5. Where the register stops

The honest limits, because a write-up that only lists strengths is an
advertisement:

- **It is a record of the past.** The newest deed in the export used here is
  2026-10-30, and the register runs months behind the market. It prices what
  people paid, not what today's asking price is.
- **Coverage is uneven.** Not every powiat publishes the same layers; some
  carry no condition, floor or room count. The service uses what a deed
  carries and never fills the gap with a guess.
- **The deed is not the listing.** There are no photographs, no descriptions,
  no floor plans, no views, no renovation state. Two flats on the same street
  with the same area and the same price per m² can be in very different
  condition. That is the difference between this and a commercial AVM, and it
  is a difference in kind, not in degree.
- **There is no rent, no yield and no forecast.** The measured trend is a
  description of registered prices, not a prediction. It is the only
  forward-looking statement this repository makes about prices, and it is
  labelled as a measurement.
- **Outliers exist.** The register contains the occasional deed with an
  implausible price per m² (a whole building sold as one flat, a garage sold
  as a flat). The comparison filters on the secondary market, the size band
  and the room count, but it does not pretend to clean the register.

## 6. Running it yourself

The endpoint takes an address and answers from the register:

```bash
curl -X POST http://localhost:8000/api/v1/tools/valuation \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_ACCESS_KEY" \
  -d '{"city": "Kraków", "street": "Myśliwska", "area_sqm": 60, "rooms": 3}'
```

A request that names a city or a street is always answered from the register.
A request that names only a catalogue property follows `VALUATION_MODE`: the
register when it says `rcn`, the seeded catalogue's own price per m²
otherwise — which is all a seeded listing can offer.

The code path, from the endpoint down:

| Layer | File |
|---|---|
| HTTP endpoint | `apps/api/api/routers/tools.py` → `POST /tools/valuation` |
| The comparison | `apps/api/services/rcn_valuation.py` |
| The register | `apps/api/data/rcn/rcn_client.py` (export download + cache), `apps/api/data/rcn/rcn_ingest.py` |
| The tool the assistant calls | `apps/api/tools/rcn_valuation_tool.py` |
| The provider | `apps/api/agents/services/valuation.py` |

The export itself is published per voivodeship by GUGiK as a GeoParquet
bundle and is cached on disk, so a re-run does not re-download 34 MB per
voivodeship.

## 7. Why it matters for this project

This repository is MIT and self-hostable, and it runs on the public register
rather than on a paid feed. That is the point of the write-up: the open-source
audience asks what this does that a commercial AVM does not, and the honest
answer is not "better". It is that **the evidence is shown**. The sales, the
period, the comparison area and the notes are in the answer, and every number
can be traced back to a deed. A commercial AVM gives you a number and keeps
the reasoning to itself.

Where the register stops, this repository says so instead of widening the
blur. That is the whole difference between a valuation and a forecast wearing
a valuation's clothes.
