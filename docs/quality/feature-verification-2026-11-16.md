# The claims of the open-source version, and the test behind each

**Date:** 2026-11-16 · **Task:** #87 · **Trigger:** the operator's report of the live demo
— broken buttons, no map.

This is the sweep the release of v5.3.7 asked for: every claim the README,
the landing and the legal pages make, the test that holds it, and the verdict
after this session. "Covered" means a test fails when the feature breaks —
not that a test file exists.

---

## 1. What the operator saw, and what it was

| Report | Cause | Verdict |
|---|---|---|
| "нету карт" — the landing hero shows no map | `hero-instrument.tsx` drew a hand-drawn SVG lattice with three price chips on it. The panel could never show a map, while the README promises "a parsed query, **a map** and three priced rows". | **Fixed** — the panel is now the product's own map (Leaflet, OpenStreetMap tiles, the house tile theme, no key). |
| The map's pins read as broken numbers ("322k", "4k") | the chip printed the price in thousands with no magnitude check, so 4 100 zł read as "4k" beside a row that said "4 100 zł" | **Fixed** — one price, one spelling (`formatMapPinPrice`), in the visitor's locale. |
| "поехавшие кнопки" — the exit-card buttons | "Suggest something" was a bare text link beside a 40 px button; the "Notify me" button had no flex centring and laid its label at the top of its box; the padding was `px-3.5` against `px-4`; card 1 sat on a different surface from cards 2 and 3; no focus ring on any of them | **Fixed** — one surface, one height, one padding, one focus ring, one structure. |

## 2. The claim → test matrix

| Claim | Where it is claimed | The test | Verdict |
|---|---|---|---|
| Natural-language search | README, landing | `test_query_analyzer.py` (60+), `test_api_search.py`, `test_search_router.py`; e2e mocks the endpoint | covered (the endpoint); the e2e is mocked |
| Matched listings, ranked | README | `test_recommendation_engine.py`, `test_strategic_reranker.py`, `test_ranking_explainer.py`, `test_hybrid_search_integration.py` | covered |
| A map on the landing | README §"Landing — the working tool" | `hero-instrument.test.tsx` (new), `e2e/landing/landing.spec.ts` (new) | covered |
| A map on the search page | README §"Interactive maps" | `property-map*.test.tsx`, `e2e/search/search.spec.ts` (markers) | covered (the tiles are fetched over the network, never asserted) |
| The listing page and its structured data | README §SEO | `server-page.test.tsx` (metadata, JSON-LD, canonical, hreflang) | covered (the builder **and** the page that carries it — the second half was missing) |
| The catalogue can be enumerated | README §"the catalogue can be enumerated" | `test_api_properties_enumeration_integration.py` (new) | covered — it had no test in any suite CI runs |
| The sitemap carries the listings | README §SEO | `sitemap.test.ts` (new) | covered — it had **no** test |
| The llms.txt names the routes and the catalogue | README §SEO | `llms.txt/__tests__/route.test.ts` (new) | covered — it had **no** test |
| robots.txt and the crawler policy | `public/robots.txt` | `src/__tests__/robots.test.ts` (new) | covered — it had **no** test |
| Google sign-in | README §"the demo signs in with Google" | `test_auth_jwt_router.py`, `OAuthButtons.test.tsx`, `test_capabilities.py` (new cases) | covered for the button and the endpoint; the browser round trip is still mocked |
| The sign-in button appears only when it can work | the capabilities contract | `test_capabilities.py` (new cases) | **Fixed** — the report ignored the redirect URI and JWT, so the button could show and the click 404/500 |
| The buyer memory | legal pages, landing | `test_buyer_memory_service.py`, `test_buyer_memory_erasure.py`, `test_memory_extractor.py` | covered on the backend; **no interface** (the legal text names the endpoint, so the promise as written is kept) |
| The CSRF double-submit | the security middleware | `test_csrf_double_submit.py` (new), `csrf.test.ts` (new) | **Fixed** — the cookie never existed, so a production deployment answered every POST with 403 |
| Nine interface languages | README | `i18n-key-parity.test.ts`, `i18n-catalogue-coverage.test.ts`, `e2e/i18n/locale.spec.ts` (new) | covered — six of the nine had never been rendered in a browser |
| Seventeen LLM providers | README | `test_provider_catalogue.py` (new) | covered — and it found that the Qwen key is `DASHSCOPE_API_KEY`, and that nine of the seventeen had no variable in the example file |
| The financial tools (mortgage, rent-vs-buy, ROI, TCO) | README | `test_tools.py`, `test_financial_metrics.py`, `mortgage.test.ts`, `investment-analyzer.test.tsx` | covered; the TCO calculator component has no test |
| Market insight and trends | README | `test_market_insights.py`, `test_market_api.py`, `e2e/market-trends/` | covered |
| The demo answers with a real model | landing | provider catalogue test, `test_multi_provider_fallback.py` | covered (the e2e mocks the model) |
| The coverage gate | README §Testing | `ci.yml` | **Fixed** — the check ended in `\|\| echo`, so the thresholds were printed and never applied |

## 3. What this session changed

- **The landing map** — `hero-map.tsx` (new), the hero instrument now renders the real map.
- **The exit controls** — one surface, one height, one padding, one focus ring.
- **The CSRF cookie** — set at sign-in, read by the browser, forwarded by the proxy.
- **The capabilities report** — it mirrors the OAuth endpoints again.
- **The example configuration** — the nine missing provider keys, the integrations that had none, and the two phantom variables (an auth library that is not installed, an analytics id nothing reads) removed.
- **The coverage gate** — it can fail; the floors are the coverage the code reaches (85.5 % unit, 52.0 % integration).
- **The tests** — 8 new suites over the claims that had none: the landing map, the sitemap, the llms.txt, the robots.txt, the catalogue enumeration, the provider catalogue, the CSRF double-submit, and the nine languages in a browser.

## 4. What is still open (and why)

| Gap | Why it is still open |
|---|---|
| The buyer memory has no interface | The legal text names the endpoint, so the promise as written is kept. An interface is a new surface, and this repository is frozen for demo purposes. |
| The e2e never touches a real backend | The suite mocks every API call; the Docker-stack spec that would not is skipped unless `E2E_STACK=true`. Wiring it into CI is a pipeline change of its own. |
| The Jest coverage gate measures the library layers only | `src/components/**` and `src/app/**` are outside `collectCoverageFrom`, so the 50 % gate says nothing about them. Widening it drops the global number to the real one — a ratchet, not a gate, until it is measured and set. |
| No mobile or tablet viewport | `playwright.config.ts` defines one project (desktop, 1440×900). |
| The neighbourhood adapters are untested against the network | Their unit tests skip for "requires network access". |
| `tests/performance`, `tests/resilience`, `tests/e2e_backend` do not run in CI | 132 test functions live in Makefile-only suites. |
