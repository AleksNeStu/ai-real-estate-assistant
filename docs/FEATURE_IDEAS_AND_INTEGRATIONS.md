# Feature Ideas and External Integrations

This document captures future feature ideas for the AI Real Estate Assistant and groups them into categories. It also outlines how the app can integrate with external data sources (files, portals, APIs) for richer analytics.

---

## 1. Feature Categories

### 1.1. For Real Estate Agencies

- **Dynamic Pricing and Market Positioning**  
  - Estimate fair rent/sale price per property based on location, area, rooms, and recent comparables.  
  - Highlight if a listing is above/below market by percentage.  
  - Suggest price adjustment ranges to improve time-to-deal.

- **Lead Scoring and Prioritisation**  
  - Score incoming leads by likelihood to close, budget fit, and urgency.  
  - Prioritise leads across channels (website, portals, phone, email).  
  - Visualise funnels per agent and campaign.

- **Portfolio and Performance Analytics**  
  - Vacancy, average time on market, and absorption rates across cities/districts.  
  - Identify underperforming properties (long exposure, low interest).  
  - "White spots" on the map where demand is high and supply is low.

- **Listing Quality and Auto-Generated Descriptions**  
  - From structured data (area, layout, infrastructure) generate:  
    - full listing description;  
    - multiple headline variants;  
    - short summary for portals and social media.  
  - Adapt copy to different platforms while keeping core facts aligned.

- **Agent Productivity Analytics**  
  - Per-agent metrics: leads, deals, average time to close, conversion rates.  
  - Identify strengths (types of properties or locations where an agent performs best).

---

### 1.2. For Property Seekers

- **Neighbourhood Quality and Lifestyle Index**  
  - Composite index per neighbourhood (safety, green space, schools, services).  
  - Show pros/cons of each area in plain language.  
  - Combine internal data with external POI and open data.

- **Commute and Accessibility Analysis**  
  - Given work/school addresses, compute typical commute times by car/public transport/bike.  
  - Visualise isochrones ("30 minutes to work" zones) on a map.  
  - Rank properties by commute convenience.

- **Total Cost of Living / Ownership**  
  - Beyond rent/mortgage: utilities, parking, internet, taxes, insurance.  
  - Optionally, currency risk if rent is in a foreign currency.  
  - Scenario comparison: "central small flat" vs "larger flat in suburb".

- **Personalised Recommendations and Shortlists**  
  - User describes budget, lifestyle, family situation and preferences.  
  - System builds a persona and proposes suitable listings with explanation.  
  - Support a shared shortlist (family/friends can comment and vote).

- **Negotiation Helper**  
  - Analyse market data for a specific property.  
  - Suggest negotiation strategy and realistic price band.  
  - Generate emails/messages to landlord/agency based on user tone.

---

### 1.3. External Integrations (High-Level)

- **Listing Portals & Deal Registries**  
  - Periodic import of listings via API or CSV/Excel exports.  
  - Use historical data to build price indices and comparables.  
  - Optionally connect to public transaction registries where available.

- **Maps, Transport, and POI**  
  - Map providers (Google Maps, OpenStreetMap, Mapbox) for visualisation.  
  - Places/POI APIs to quantify availability of amenities (schools, parks, shops, medical).  
  - Public transport APIs or GTFS feeds for schedule and accessibility analysis.

- **Finance and Legal**  
  - Bank / mortgage APIs for interest rates and loan products.  
  - Integration with insurance quotation services.  
  - Document generation and e-signature for contracts (DocuSign, etc.).

- **Analytics / BI**  
  - Export pipelines to BI tools (Power BI, Tableau, Metabase).  
  - Scheduled exports (CSV/Parquet/SQL views) for data teams.

- **CRM and Calendars**  
  - CRM integration (HubSpot, Pipedrive, etc.) for leads and deals.  
  - Calendar integration for viewing appointments.

---

## 2. Focus: Integration with External Data Sources

The modern app (`app_modern.py`) already supports flexible CSV loading via `DataLoaderCsv` and `PropertyCollection` (data/csv_loader.py, data/schemas.py). The next step is to make integrations a first-class capability so users and agencies can plug in external data sources (files and portals) and immediately analyse them.

### 2.1. File-Based Integrations (CSV/Excel)

**Goal:** allow users to bring in data from arbitrary CSV/Excel exports, normalise it into the internal schema, and run the full analytics pipeline (vector store, insights, comparisons) on top.

**Current state:**
- `DataLoaderCsv` handles CSV URLs and local CSV files.  
- `format_df` performs robust schema inference and normalisation (city, rooms, area, currency, listing_type, geo, booleans).  
- `PropertyCollection.from_dataframe` converts formatted `DataFrame` rows into validated `Property` objects.

**Next steps:**
- Add an `ExcelDataLoader` (or extend `DataLoaderCsv`) to support:
  - `.xlsx`, `.xls`, `.ods` files;  
  - selecting a sheet and optional header row;  
  - reusing `format_df` logic for normalisation.
- Improve sidebar UI:
  - separate controls for "CSV/Excel file upload";  
  - optional per-file metadata (source name, portal name) stored in `PropertyCollection.source`.
- Persist and tag data:
  - track source type (`csv`, `excel`, `portal_X`) in metadata to allow filtering and deletion (`delete_by_source`).

### 2.2. Web-Based Integrations (Portals and APIs)

**Goal:** ingest data directly from listing portals or custom APIs using user-provided filters (city, budget, rooms, listing type), then run the same analytics as for local data.

**Patterns:**
- **Source adapters** under `tools/` (e.g. `tools/portal_adapter.py`):  
  - one adapter per portal/API;  
  - fetch listings via HTTP/GraphQL;  
  - normalise the payload into a common `DataFrame` format expected by `DataLoaderCsv.format_df`.
- **Filter configuration in the UI:**  
  - in the "Data Sources" expander, add a tab like "Portal";  
  - fields: portal name, city, price range, rooms, listing type;  
  - a button to trigger fetch + ingestion.

**Example flow:**
1. User selects "Portal: ExamplePortal" and sets filters (city, min/max price, rooms).  
2. App calls a portal adapter, which:  
   - builds a URL or API request with filters;  
   - fetches JSON or HTML;  
   - parses/normalises into `DataFrame` with columns expected by `format_df`.  
3. Normalised data is passed through the existing pipeline:  
   - `PropertyCollection.from_dataframe`;  
   - `ChromaPropertyStore.add_property_collection`;  
   - `MarketInsights` for analytics.  
4. UI updates analytics, comparisons, and recommendations based on the new dataset.

**Design considerations:**
- Adapters should avoid hard-coding any secrets; keys/tokens stored in env vars or `.env` (never committed).  
- Each adapter should be robust to partial failures (e.g. rate limiting, missing fields).  
- Respect terms of service for portals and use official APIs where available.

### 2.3. Unified Integration Interface

To keep integrations manageable:
- Define a simple **interface** for external sources, e.g.:

```python
class ExternalSourceAdapter(Protocol):
    def fetch(self, filters: dict) -> pd.DataFrame:
        ...  # returns a DataFrame with column names suitable for format_df
```

- Register adapters in a central registry (e.g. `tools/property_tools.py` or a new `tools/integrations.py`), so the UI can:
  - list available sources;  
  - show which require API keys and which work anonymously.

- Reuse the same ingestion pipeline for all sources (CSV, Excel, portals):
  - **normalise → PropertyCollection → vector store → analytics**.

### 2.4. Analytics on Integrated Data

Once data from files and portals is ingested into the unified schema, all existing analytics can be applied:
- **Market Insights** (`analytics/market_insights.py`):  
  - price trends, YoY changes, outliers, city/segment comparisons.
- **Comparison and recommendation tools** (`ui/comparison_viz.py`, agents):  
  - cross-portal comparison of listings;  
  - identifying best-value properties for a user profile.
- **Future extensions:**  
  - cohort analysis (properties from portal A vs portal B);  
  - performance per source (how many quality leads, time-to-deal by portal).

---

## 3. Roadmap Notes (Integrations)

Short-term possible tasks:
- Implement an Excel-capable loader reusing `format_df`.  
- Add a "Portal" tab in the sidebar UI that calls a dummy/test adapter.  
- Implement one real portal adapter (for a portal with a documented API) and wire it into the ingestion pipeline.

Medium-term:
- Add more adapters and a small registry of sources.  
- Extend analytics to segment results by `source` and `portal`.  
- Expose exports to third-party tools (BI, CRM) for integrated reporting.
