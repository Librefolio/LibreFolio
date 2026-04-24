---
title: "Knowledge Base: Backend Reference"
category: source
source_type: knowledge_base
date_ingested: 2026-04-24
original_path: LibreFolio_developer_journal/knowledge_base/01_backend.md
tags: [backend, providers, database, testing, architecture]
related_features: [F-015, F-025, F-012, F-059, F-060, F-061, F-068]
---

# Source: Knowledge Base — Backend Reference

## Summary

Comprehensive overview of LibreFolio's backend architecture covering directory structure, database patterns (SQLite + Alembic), provider registry auto-discovery pattern for FX/Asset/BRIM providers, core cache architecture (5-layer system), thread isolation pattern, auth model (JWT cookie-based), and testing structure (850+ tests across 8 categories).

## Key Insights Extracted

### Provider Architecture
- **Provider Registry Pattern** ([[concepts/provider-registry-pattern]]): Auto-discovery via decorator across 3 domains (FX, Asset, BRIM)
- **Thread Isolation** ([[F-060]]): All provider calls run in dedicated threads with own event loops
- **5-Layer Cache** ([[F-061]]): TTL-based caching for asset history (15min), current (2min), metadata (30min), search queries (15min), search results (24h)
- **MANUAL Sentinel** ([[decisions/manual-fx-sentinel]]): Auto-insert/remove FX provider at priority 999

### Provider Specifics
- **FX Providers**: ECB, FED, BOE, SNB serve multi-currency in single batch calls
- **Asset Providers**: yfinance (search: ✅), JustETF (search: ✅), CSS Scraper (URL-based, no search), Scheduled Investment (synthetic yield calculator)
- **BRIM Providers**: 11 broker parsers (IBKR, Degiro, Directa, eToro, Coinbase, Revolut, Trading212, Bitpanda, Bitvavo, Schwab, Parqet)

### Database
- **Data Separation** ([[decisions/prod-test-data-separation]]): `backend/data/prod/` vs `backend/data/test/` — completely isolated SQLite databases
- **Single Migration** ([[concepts/single-migration-strategy]]): Embryonic schema edited in `001_initial.py`, recreate with `./dev.py db create-clean`

### Testing
- 850+ total tests across 8 categories: external (providers), db, services, utils, schemas, api (276 tests), e2e, front (Playwright 181+ tests)
- API tests: 70 asset endpoints, 28 FX, 22 brokers, 21 auth

### Auth
- JWT cookie-based (HttpOnly), stateless for multi-worker, first user = auto-admin
- Broker sharing: Owner/Editor/Viewer roles

## New Concepts Documented

None — all major concepts already in wiki. This source consolidates references.

## Enrichments Made

- Added backend-specific details to [[F-015]] (FX Provider Registry)
- Added cache layer specifics to [[F-061]] (5-layer Provider Cache)
- Added thread isolation notes to [[F-060]]
- Added BRIM plugin count to [[F-012]]

## Source Files

| Role | Path |
|------|------|
| Source KB file | `LibreFolio_developer_journal/knowledge_base/01_backend.md` |
| Models | `backend/app/db/models.py` |
| Services | `backend/app/services/` |
| API endpoints | `backend/app/api/v1/` |
| FX providers | `backend/app/services/fx_providers/` |
| Asset providers | `backend/app/services/asset_source_providers/` |
| BRIM providers | `backend/app/services/brim_providers/` |
| Test suite | `backend/test_scripts/` |
| Config | `backend/app/config.py` |
