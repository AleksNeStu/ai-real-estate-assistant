# GLOSSARY — one entity, one name

> The canonical name of every entity this product reasons about. The same thing
> is called the same thing in the code, the database, the interface and the
> e-mail. A change that introduces a second name for an existing value is a
> defect (Rule 349).
>
> Paths are relative to the repository root. Every row was read out of the tree
> — a row that names a file that does not exist is a defect in this document.

## The vocabulary of the domain

| Term | Means | Not to be confused with |
|---|---|---|
| **Property** | One flat, house or room the assistant can offer — the listing. It has a city, a price, an area, rooms, amenities, coordinates. | A **deed**. A property is what is *offered*; a deed is what was *transacted*. |
| **Catalogue** | The set of properties the deployment knows — the Chroma collection `properties` plus the JSON cache `.app_cache/properties.json`. | The **register**. The catalogue is what the app offers; the register is what people actually paid. |
| **Register** (Rejestr Cen Nieruchomości, RCN) | The official Polish register of transaction prices, published weekly by the state mapping office, free of charge since 13 February 2026. | A listing feed. The register carries **prices people paid**, not asking prices. |
| **Deed / PropertyTransaction** | One registered sale in the register: the address, the area, the rooms, the price, the date, the market segment. | A property. A deed becomes a **comparable**; a comparable becomes a **valuation**. |
| **Comparable** | A deed used as evidence for a valuation — matched on city, district, area, rooms and period. | A neighbour. |
| **Valuation** | What a flat is worth, answered from the register, with its comparables, its sample size, its period and its comparison area. | An asking price. A valuation is never an asking price. |
| **Place / City / District** | Where a thing is: a city with its districts, a district with its figures. | An **address**. The address names a door; the place names a market. |
| **Neighbourhood index** | A measured score for a district, computed from OpenStreetMap features — never from a hash. | A score the model made up. |
| **Visitor** | An anonymous person, identified by the `visitor_id` cookie (365 days). Their interactions become a lead. | A **user**. A visitor has no account. |
| **User** | A person with an account: JWT bearer, favourites, saved searches, buyer memory. | A visitor. |
| **Lead** | A scored contact — a captured waitlist signup or a tracked interaction — with its scoring breakdown and its funnel column. | An **agent**. |
| **Agent** | A broker or agency: their profile, listings, inquiries, assignments, goals, deals and commissions. | A **user**. An agent is a customer, not an account holder. |
| **Deal** | A transaction an agent closed, with its **commission**. | A deed. A deal is commercial; a deed is a register entry. |
| **SavedSearch** | A stored search that keeps running — it watches for new matches and for price drops. | A **FilterPreset** (a stored set of filters, run once). |
| **Collection** | A named shortlist of favourites, each with a note. | A **collection of documents** (the document vault). |
| **Buyer memory** | The durable facts about a buyer: the budget, the ruled-out areas, the liked listings. | The **preferences** profile (the model's ranking boosts for a session). |
| **Slot** | The named position of a link — `hero_search`, `exit_studio`, `studio_strip`, `footer`, … It travels with the click, so the funnel can say *which* CTA did it. | The **campaign** (`oss`, `studio`, `propvector`) and the **medium** (`landing`, `landing_mobile`, `app`). |
| **Data source** | A registered place properties come from — a file upload, a URL, a portal API, the register. It has a sync history and a health score. | A **bulk job** (one run of one import). |
| **Bulk job** | One import or export run: its kind, its status, its progress, its records processed. | A data source. |

## Where each entity lives

| Entity | SQLAlchemy model · table | Frontend | API |
|---|---|---|---|
| Property | **no table** — `data/schemas.py` `Property`; Chroma collection `properties`; `.app_cache/properties.json` | `Property` (`apps/web/src/lib/types.ts`) | `GET /api/v1/properties`, `POST /api/v1/search` |
| PropertyTransaction (deed) | `PropertyTransaction` · `property_transactions` | — (read through the valuation tool) | `POST /api/v1/tools/valuation` |
| User | `User` · `users` | `useAuth` context | `POST /api/v1/auth/*` |
| OAuth account | `OAuthAccount` · `oauth_accounts` | `OAuthButtons` | `POST /api/v1/auth/oauth/*` |
| Refresh / reset / verification token | `RefreshToken` · `refresh_tokens`, `PasswordResetToken` · `password_reset_tokens`, `EmailVerificationToken` · `email_verification_tokens` | — | `api/routers/auth_jwt.py` (`/api/v1/auth/*`) |
| Visitor | — (the `visitor_id` cookie + `lead_interactions`) | `visitor-tracking.ts` | `POST /api/v1/leads/track` |
| Lead | `Lead` · `leads` | `lead-board.tsx` | `/api/v1/leads` |
| Lead interaction | `LeadInteraction` · `lead_interactions` | — | `POST /api/v1/leads/track` |
| Lead score | `LeadScore` · `lead_scores` | `lead-format.ts` | `/api/v1/leads` |
| Agent | `AgentProfile` · `agent_profiles` | `agent-card.tsx` | `/api/v1/agents` |
| Agent listing | `AgentListing` · `agent_listings` | `agent-listings-ledger.tsx` | `/api/v1/agents` |
| Agent inquiry | `AgentInquiry` · `agent_inquiries` | `contact-agent-form.tsx` | `/api/v1/agents` |
| Viewing appointment | `ViewingAppointment` · `viewing_appointments` | `schedule-viewing-dialog.tsx` | `/api/v1/agents` |
| Agent assignment · goal | `AgentAssignment` · `agent_assignments`, `AgentGoal` · `agent_goals` | `agent-filters.tsx` | `/api/v1/agents` |
| Deal · commission | `Deal` · `deals`, `Commission` · `commissions` | — | `/api/v1/agents` |
| Saved search | `SavedSearchDB` · `saved_searches` | `save-search-button.tsx` | `/api/v1/saved-searches` |
| Collection | `CollectionDB` · `collections` | `favorites` page | `/api/v1/collections` |
| Favourite | `FavoriteDB` · `favorites` | `heart-button.tsx` | `/api/v1/favorites` |
| Filter preset | `FilterPresetDB` · `filter_presets` | `preset-selector.tsx` | `/api/v1/filter-presets` |
| Document | `DocumentDB` · `documents` | `document-list.tsx` | `/api/v1/documents` |
| Document template | `DocumentTemplateDB` · `document_templates` | — | `/api/v1/documents` |
| Signature request · signed document | `SignatureRequestDB` · `signature_requests`, `SignedDocumentDB` · `signed_documents` | — | `/api/v1/signatures` |
| Buyer memory fact | `BuyerMemoryFact` · `buyer_memory_facts` | `settings/buyer-memory` | `/api/v1/me/buyer-memory` |
| Preference profile | `UserPreferenceProfile` · `user_preference_profiles` | — | `/api/v1/profile` |
| Notification preference | `NotificationPreferenceDB` · `notification_preferences` | `settings/notification` | `/api/v1/settings/notifications` |
| Push subscription | `PushSubscription` · `push_subscriptions` | — | `/api/v1/push` |
| Data source | `DataSourceDB` · `data_sources` | `source-ledger.tsx` | `/api/v1/data-sources` |
| Data source sync history | `DataSourceSyncHistory` · `data_source_sync_history` | `connector-ledger.tsx` | `/api/v1/data-sources/{id}/history` |
| Bulk job | `BulkJob` · `bulk_jobs` | `job-ledger.tsx` | `/api/v1/bulk-jobs` |
| Price snapshot | `PriceSnapshot` · `price_snapshots` | `price-history-chart.tsx` | `/api/v1/properties/{id}/price-history` |
| Market anomaly | `MarketAnomaly` · `market_anomalies` | `anomaly-list.tsx` | `/api/v1/anomalies` |
| Ranking config | `RankingConfig` · `ranking_configs` | — | `/api/v1/ranking` |
| A/B experiment · assignment | `ABExperiment` · `ab_experiments`, `ABExperimentAssignment` · `ab_experiment_assignments` | — | `services/ab_testing_service.py` |
| Search event · interaction · feedback | `SearchEvent` · `search_events`, `SearchResultInteraction` · `search_result_interactions`, `SearchFeedback` · `search_feedback` | `search-feedback` | `POST /api/v1/feedback` |
| User activity event | `UserActivityEvent` · `user_activity_events` | `usage-activity-chart.tsx` | `/api/v1/user-activity` |
| CMA report | `CMAReportDB` · `cma_reports` | `cma-wizard.tsx` | `/api/v1/cma` |
| Task model preference | `TaskModelPreference` · `task_model_preferences` | `task-model` | `/api/v1/model-preferences`, `/api/v1/settings/model-preferences` |
| Audit log entry | `AuditLogEntry` · `audit_log_entries` | — | `GET /api/v1/audit` |

## The names that are not tables

| Name | Where it lives |
|---|---|
| **Provider** | one LLM vendor (`apps/api/models/providers/`) — 17 of them; the deployment picks one per request |
| **Route** | the API prefix under `/api/v1` (`apps/api/api/routers/`) — one module per domain |
| **Document (RAG)** | a LangChain `Document` in the knowledge store — a *different* thing from the document vault above |
| **Capability** | one key of `GET /api/v1/capabilities` — what the running deployment can actually do |
| **Deploy** | the platform-hosted staging (`deploy.yml`) or the self-hosted server (`deploy-selfhosted.yml`); the public address runs on the second |
| **Release** | a `vX.Y.Z` tag — it publishes the images and rolls the server; the tag is cut only after the CI on that commit is green |
