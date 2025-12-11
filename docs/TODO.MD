# Global Roadmap: Poland, EU, CIS (incl. Russia), Turkey, Africa, USA

## Goals
- Unified platform for real‑estate search and analytics across regions
- Consumer mode (simple search, map, comparisons, calculators)
- Expert mode (indices, comparables, yield, risk, export)

## Data Architecture
- Extend `Property` and metadata:
  - `country`, `region`, `city`, `district`, `lat`, `lon`
  - `currency`, `price_original`, `price_converted`, `price_per_sqm`
  - `listing_type` (rent/sale), `transaction_type`, `property_type`
  - optional: `year_built`, `energy_cert`, `floor`, `amenities`
- FX normalization: PLN/EUR/USD/TRY/RUB/ZAR/…
  - Providers: ECB/NBP/Fed/…; daily cache
- Geocoding: batch via OpenStreetMap/Nominatim (rate‑limited), store lat/lon
- Storage: separate Chroma collections per region, naming `properties_<country>`

## Data Integrations
- Sources: CSV files, open datasets (HuggingFace, government stats), manual import
- Aggregation by city/district, validation/cleaning, deduplication
- Scheduler: incremental loads and reindexing on schedule

## Search & Retrieval
- Geospatial filters: bounding box, distance from point
- Facets: `country/city/type/rooms/price_per_sqm`, etc.
- Multilingual query normalization (synonyms, transliteration)
- Reranker: user priorities (family/investor), location/price/area signals

## Analytics & Indices
- City/country price indices (median, average, YoY/YoM)
- Rental yield (gross/net), ROI, payback period
- Comparables: similar properties + fair‑price adjustments
- Risk metrics: volatility, liquidity, vacancy (where available)
- Time series: smoothing, trends, anomalies

## Map & Visualization
- World map: center by selected country/city, data layers
- Heatmaps for price and yield, clustered points
- Map filters: price/m², rooms, type, year, energy

## UX/UI
- Quick presets (family/investor/office)
- Expert mode: index panels, comparables, export to PDF/CSV
- Locale/currency: choose language (EN/PL/RU/TR/AR/FR/DE/ES/IT/PT) and currency
- Accessibility: contrast, keyboard navigation, neutral states

## Notifications & Subscriptions
- Consumer digest: new listings, price drops, top‑5 picks
- Expert digest: indices, trends, top locations by yield
- Channels: Email (existing), extend templates and criteria

## DevOps & Quality
- Data validators: schemas/ranges/coordinate validity
- Tests: unit for analytics, integration for retriever, e2e UI
- Quality gates: ruff/mypy/bandit (enabled in CI)

## Sprints
- Sprint 1 (1–2 weeks)
  - [DONE] Schema extension (country/region/district/currency, lat/lon)
  - [DONE] Geospatial filters (radius) and base city price indices
  - [DONE] Monthly price index with YoY (Expert Panel)
  - [DONE] Moving average smoothing and anomaly detection (z-score)
  - [DONE] Map picker (click to set radius center) wired to retriever
  - [DONE] Multi-city YoY latest with UI table and leaders
  - [DONE] Deterministic lat/lon fill at ingestion for known cities
  - Map with filters, neutral UI states
  - Base digest (consumer/expert)
- Sprint 2 (2–3 weeks)
  - Indices and comparables for CIS/Russia/Turkey/USA/Africa
  - Yield/ROI, rate/expense scenarios
  - PRO filters (energy/year/elevator/parking), multilingual texts
- Sprint 3 (3–4 weeks)
  - Hedonic fair‑price model and strategic reranker
  - Historical map layers, points of interest, report export
  - Performance/cache/parallel ingestion
- Sprint 4 (2 weeks)
  - Notifications/scheduling/advanced templates
  - Full e2e tests, static checks, stabilization

## Success Metrics
- CTR for comparables, saved‑search conversions, digest opens
- Fair‑price accuracy (±%), map engagement, session duration
