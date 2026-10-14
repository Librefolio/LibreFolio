---
title: "services/assets — the asset pricing service, split by responsibility (formerly asset_sources behind the asset_source facade)"
category: entity
type: service
tags: [backend, assets, pricing, providers, refresh, prices, events, architecture]
related: [features/F-024, features/F-025, features/F-027, features/F-030, features/F-031, concepts/prices-current-side-effect, decisions/three-phase-pipeline, problems/asset-event-edit-delete-reinsert, problems/asset-classification-wiped-by-partial-save, sources/phase00-asset-pricing-refactor-2026-09]
---

# services/assets (package), formerly asset_sources and the `asset_source.py` facade

## Role
Everything the backend does with asset prices and their providers: CRUD and merge of assets, provider assignment and
probing, cross-provider search, metadata refresh, price queries, current quotes, the persistence of prices and
events, and the bulk refresh from providers. Until 2026-09-11 this was one module; Release 2 (SP08) split it by
responsibility with **no contract change**.

## Location
- `backend/app/services/assets/` since 1.3 (workstream X, lot CP2a, 2026-10-15). The package re-exports
  nothing: every name is imported from the module that defines it.
- The Release 2 facade `backend/app/services/asset_source.py` and the lazy barrel
  `backend/app/services/asset_sources/__init__.py` were removed in the same lot (plan 43, PL6). Until then they
  re-exported `AssetCRUDService`, `AssetSourceManager`, `AssetSearchService`, `AssetSourceProvider`,
  `AssetSourceError`, `AssetHistoryStartDate` and `ASSET_HISTORY_MIN_FALLBACK`.

| Module | Responsibility |
|---|---|
| `registry.py` | `AssetProviderRegistry`, which discovers the plugins in `services/asset_source_providers/` (1.3, CP1) |
| `core.py` | `AssetSourceProvider` (abstract provider base), shared errors and types, provider thread/cache plumbing |
| `crud.py` | `AssetCRUDService` — create, bulk patch (absent vs `null` semantics), bulk delete with per-item savepoints |
| `manager.py` | `AssetSourceManager` — a compatibility manager composed from the responsibility modules |
| `metadata.py` | provider metadata refresh |
| `price_query.py` | price queries (`get_prices_bulk`) and current quotes |
| `price_store.py` | persistence of prices and events (`_upsert_asset_events`: in-place edit by id) |
| `provider_management.py` | provider assignment and probe |
| `refresh.py` | `bulk_refresh_prices` as **PREPARE → FETCH → PERSIST** with typed hand-offs (`_PreparedRefreshItem`, `_FetchedRefreshData`) |
| `search.py` | `AssetSearchService` — cross-provider search orchestration |
| `web_link_finder.py` | the search's last-resort web lookup ([[decisions/web-link-finder-ddgs]]); in `services/` until 1.3 |
| `market_calendar.py` | market holidays and the carry-versus-quote rule; in `services/` until 1.3 |

## Design Notes
- **Contract preserved by design** (SP08): cache, thread and error identities, public imports, provider
  auto-discovery, chunked commits and the current-price write-back all behave as before; characterisation tests
  came first.
- **Leaf modules never import the manager** — the dependency points one way, which is what makes the split hold.
- The refresh follows the bulk-operation pattern of [[decisions/three-phase-pipeline]]: no session is held across the
  network phase.
- `/assets/prices/current` still persists today's candle ([[concepts/prices-current-side-effect]]); its write path is
  now `price_query.py` → `price_store.py`.
- Out of scope then, and still: cache-key normalisation, `source_plugin_key`, FX and BRIM refactors.
- Residual: `get_prices_bulk` keeps a `noqa: C901 — TODO(P2-refactor)` (multi-pass query/FX/signal pipeline).

## History
- 2026-09-11 (`3c85866dd`): SP08 split; `YahooFinanceProvider.get_history_value` split into fetch, DataFrame mapping
  and dividend/split parsing; the core logs through the project logger (the fix for an off-track incident in the
  plan). [[sources/phase00-asset-pricing-refactor-2026-09]]
- 2026-10-08: asset events edited in place by id ([[problems/asset-event-edit-delete-reinsert]]).
- 2026-10-15 (1.3, workstream X, CP1 and CP2a): `AssetProviderRegistry` moved to `services/assets/registry.py`;
  then the modules moved from `asset_sources/` to `services/assets/` with the same names, together with
  `market_calendar.py` and `web_link_finder.py`. The facade and the barrel were removed; no behaviour change.
  Plan: `LibreFolio_developer_journal/Release_2/Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md`.

## Source files

| Role | Path |
|------|------|
| Core | `backend/app/services/assets/core.py` |
| Registry | `backend/app/services/assets/registry.py` |
| CRUD | `backend/app/services/assets/crud.py` |
| Manager | `backend/app/services/assets/manager.py` |
| Price queries | `backend/app/services/assets/price_query.py` |
| Price/event store | `backend/app/services/assets/price_store.py` |
| Refresh pipeline | `backend/app/services/assets/refresh.py` |
| Search | `backend/app/services/assets/search.py` |
| Web link finder | `backend/app/services/assets/web_link_finder.py` |
| Market calendar | `backend/app/services/assets/market_calendar.py` |
| Yahoo provider | `backend/app/services/asset_source_providers/yahoo_finance/plugin.py` |
| Developer doc | `mkdocs_src/docs/developer/backend/assets/architecture.md` |
