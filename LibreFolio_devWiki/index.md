# devWiki Index

> Master catalog of all wiki pages. Updated on every ingest and every page creation.
> LLM: read this first when answering queries to identify relevant pages.

## Feature Registry

| Page | Description |
|------|-------------|
| [[features/registry]] | **Authoritative code→title→status→mkdocs table — READ THIS FIRST** (74 features across 11 domains) |

## Individual Feature Pages

| Page | Title | Domain | Status |
|------|-------|--------|--------|
| [[features/F-012]] | BRIM Framework | Brokers | implemented |
| [[features/F-019]] | MANUAL Sentinel FX Provider | FX | implemented |
| [[features/F-020]] | FX Currency Conversion Graph | FX | implemented |
| [[features/F-034]] | Scheduled Investment Provider | Assets | implemented |
| [[features/F-037]] | Signal Library Framework | Signals | implemented |
| [[features/F-056]] | FIFO at Runtime | Calculations | implemented |
| [[features/F-059]] | Provider Registry Pattern | Infrastructure | implemented |

## Connections (Cross-Feature Dependency Maps)

| Page | Domain | Summary |
|------|--------|---------|
| [[connections/dependency-graph]] | ALL | Full project dependency graph + critical chains |
| [[connections/fx-connections]] | FX | FX provider → pair → sync → conversion → display chain |
| [[connections/assets-connections]] | Assets | Asset CRUD → provider → sync → chart chain |
| [[connections/transactions-connections]] | Transactions | TX model → list → staging → BRIM import chain (Phase 7) |

## Decisions

| Page | Summary | Date | Tags |
|------|---------|------|------|
| [[decisions/fx-sync-pair-based]] | FX sync redesigned from currency-list to pair-list (GET→POST) | 2026-03-06 | fx, api, breaking-change |
| [[decisions/brim-broker-scoped]] | BRIM upload moved to broker scope for proper access control | 2026-01-22 | brim, brokers, multiuser |
| [[decisions/provider-shutdown-generic]] | Generic shutdown() in ABCs replaces hardcoded JustETF cleanup | 2026-04-10 | backend, providers, lifecycle |
| [[decisions/prod-test-data-separation]] | Complete prod/test directory isolation for all data | 2026-01-26 | backend, testing, isolation |
| [[decisions/brim-fake-asset-id]] | BRIM plugins emit negative integers as fake asset IDs during parse | 2026 | brim, brokers, transactions |
| [[decisions/manual-fx-sentinel]] | MANUAL is a sentinel FX provider that auto-inserts when no real provider covers a pair | 2026 | fx, providers, sentinel |
| [[decisions/fifo-runtime-decision]] | FIFO cost basis computed at query time, never persisted to DB | 2026 | backend, calculations, fifo |
| [[decisions/provider-registry-decision]] | `@register_provider` decorator for auto-discovery of all provider families | 2026 | backend, providers, architecture |

## Concepts

| Page | Summary | Tags |
|------|---------|------|
| [[concepts/async-io-rule]] | **CRITICAL**: sync I/O in async handlers blocks uvicorn event loop | backend, async, performance |
| [[concepts/daily-point-policy]] | One record per day for prices and FX rates (upsert semantics) | backend, db, prices |
| [[concepts/single-migration-strategy]] | Modify 001_initial.py + recreate DB — no incremental migrations | backend, db, alembic |
| [[concepts/backend-only-calculations]] | All financial calculations in backend — frontend is pure display | architecture |
| [[concepts/dual-view-pattern]] | Card grid + DataTable toggle persisted in localStorage | frontend, ux |
| [[concepts/svelte5-runes]] | New components use $state/$derived/$effect — not $: reactive | frontend, svelte |

## Problems

| Page | Summary | Status | Tags |
|------|---------|--------|------|
| [[problems/event-loop-blocking]] | yfinance sync calls in async handlers freeze entire app | resolved | backend, async, performance |
| [[problems/liveticker-header-crash]] | LiveTicker in Header.svelte crashed on navigation | resolved | frontend, navigation |
| [[problems/flag-emoji-windows]] | Flag emoji blank on Windows — needs Noto Color Emoji font | resolved | frontend, emoji, windows |

## Entities

| Page | Summary |
|------|---------|
| [[entities/api-router]] | FastAPI router structure — all v1 API routes and their modules |

## Sources

| Page | Original | Date Ingested | Tags |
|------|----------|---------------|------|
| [[sources/roadmap-v1-summary]] | `RoadMapV1/01-Riassunto_generale.md` | 2026-04-24 | roadmap, architecture, history |
