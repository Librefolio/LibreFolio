# devWiki Index

> Master catalog of all wiki pages. Updated on every ingest and every page creation.
> LLM: read this first when answering queries to identify relevant pages.

## Domains

> Macro-level narratives — what each domain does, how its features cluster, and how it evolved.
> For individual feature details, use the Feature Registry below.

| Page | Domain | Features | Status |
|------|--------|----------|--------|
| [[domains/auth]] | AUTH | F-001–F-003 | stable |
| [[domains/layout-settings]] | LAYOUT & SETTINGS | F-004–F-008 | stable |
| [[domains/brokers]] | BROKERS | F-009–F-014 | stable |
| [[domains/fx]] | FX (Foreign Exchange) | F-015–F-023 | stable |
| [[domains/assets]] | ASSETS | F-024–F-036 | stable |
| [[domains/signals]] | TECHNICAL ANALYSIS (Signals) | F-037–F-045 | stable |
| [[domains/transactions]] | TRANSACTIONS | F-046–F-051 | in-progress |
| [[domains/scheduler]] | SCHEDULER | F-052–F-053 | planned |
| [[domains/dashboard]] | DASHBOARD | F-054–F-055 | planned |
| [[domains/calculations]] | CALCULATIONS | F-056–F-058 | stable |
| [[domains/infrastructure]] | INFRASTRUCTURE | F-059–F-074 | stable |

---

## Feature Registry

| Page | Description |
|------|-------------|
| [[features/registry]] | **Authoritative code→title→status→mkdocs table — READ THIS FIRST** (96 features across 12 domains) |

## Individual Feature Pages

| Page | Title | Domain | Status |
|------|-------|--------|--------|
| [[features/F-012]] | BRIM Framework | Brokers | implemented |
| [[features/F-019]] | MANUAL Sentinel FX Provider | FX | implemented |
| [[features/F-020]] | FX Currency Conversion Graph | FX | implemented |
| [[features/F-033]] | Asset Detail Page (chart, signals, editor) | Assets | implemented |
| [[features/F-034]] | Scheduled Investment Provider | Assets | implemented |
| [[features/F-037]] | Signal Library Framework | Signals | implemented |
| [[features/F-038]] | EMA Signal | Signals | implemented |
| [[features/F-039]] | RSI Signal | Signals | implemented |
| [[features/F-042]] | FX Pair Comparison Signal | Signals | implemented |
| [[features/F-056]] | FIFO at Runtime | Calculations | implemented |
| [[features/F-059]] | Provider Registry Pattern | Infrastructure | implemented |
| [[features/F-060]] | Thread Isolation for Providers | Infrastructure | implemented |
| [[features/F-061]] | 5-layer Provider Cache | Infrastructure | implemented |
| [[features/F-096]] | Scheduled Investment — Decoupled Frequencies + Anchor Day | Assets | idea |

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
| [[decisions/sveltekit-over-react]] | V4 rewrite switched from React+MUI to SvelteKit 2 + Svelte 5 | 2026-01-01 | frontend, svelte, architecture |
| [[decisions/zodios-api-client]] | Zodios chosen for type-safe, OpenAPI-generated API client | 2026-01-01 | frontend, api, typescript, zodios |
| [[decisions/single-docker-image]] | Single Docker image: FastAPI serves SvelteKit static build | 2026-01-01 | deployment, docker, ops |
| [[decisions/scheduled-investment-redesign]] | ScheduledInvestment redesigned as pure deterministic engine (no DB access) | 2026-04-01 | assets, providers, architecture |
| [[decisions/data-editor-unification]] | FX and Asset data editors unified into generic DataEditor component set | 2026-04-01 | frontend, components, ux |
| [[decisions/i18n-key-rationalization]] | Intentional duplicates OK when namespacing clarity > DRY (42 groups, ~30 accepted) | 2026-04-24 | frontend, i18n, translations, duplicates |
| [[decisions/three-phase-pipeline]] | Bulk operations use PREPARE→FETCH→PERSIST pattern with per-task sessions | 2026-03-31 | backend, async, database, architecture |
| [[decisions/signal-label-unification]] | `signalLabel.ts` utility + enriched `RenderedSignal` unify all signal label rendering | 2026-04-10 | frontend, signals, charts, ui, refactor |

## Concepts

| Page | Summary | Tags |
|------|---------|------|
| [[concepts/async-io-rule]] | **CRITICAL**: sync I/O in async handlers blocks uvicorn event loop | backend, async, performance |
| [[concepts/daily-point-policy]] | One record per day for prices and FX rates (upsert semantics) | backend, db, prices |
| [[concepts/single-migration-strategy]] | Modify 001_initial.py + recreate DB — no incremental migrations | backend, db, alembic |
| [[concepts/backend-only-calculations]] | All financial calculations in backend — frontend is pure display | architecture |
| [[concepts/dual-view-pattern]] | Card grid + DataTable toggle persisted in localStorage | frontend, ux |
| [[concepts/svelte5-runes]] | New components use $state/$derived/$effect — not $: reactive | frontend, svelte |
| [[concepts/timeseries-store-pattern]] | Generic client-side cache with gap detection for delta fetching | frontend, stores, timeseries |
| [[concepts/editbuffer-pattern]] | Per-row DataRow.status tracking for in-place edit, CSV import, bulk save | frontend, components, data-editor |
| [[concepts/mkdocs-suffix-i18n]] | MkDocs uses suffix strategy (index.en.md, index.it.md) for multilingual docs | mkdocs, i18n, documentation |
| [[concepts/backend-test-isolation]] | Each backend test creates its own user via unique_id() — zero cross-test state | testing, backend, isolation |
| [[concepts/e2e-data-testid-rule]] | ALWAYS use data-testid for Playwright selectors — NEVER CSS classes or text | testing, frontend, e2e, i18n |
| [[concepts/responsive-4mode-layout]] | Filter bar pages use 4 breakpoint modes (wide/tablet/tablet-s/mobile) for better intermediate-width UX | frontend, responsive, layout, ux |

## Problems

| Page | Summary | Status | Tags |
|------|---------|--------|------|
| [[problems/event-loop-blocking]] | yfinance sync calls in async handlers freeze entire app | resolved | backend, async, performance |
| [[problems/liveticker-header-crash]] | LiveTicker in Header.svelte crashed on navigation | resolved | frontend, navigation |
| [[problems/flag-emoji-windows]] | Flag emoji blank on Windows — needs Noto Color Emoji font | resolved | frontend, emoji, windows |
| [[problems/justetf-websocket-disconnect]] | JustETF WebSocket silently freezes — reconnect backoff workaround | workaround | backend, providers, websocket |
| [[problems/asset-currency-mismatch]] | Asset price currency may differ from Asset.currency — per-row currency column | resolved | backend, db, currency, prices |
| [[problems/tanstack-svelte5-incompatibility]] | TanStack Table v8 official adapter is incompatible with Svelte 5 runes | workaround | frontend, svelte5, tanstack |
| [[problems/sync-functions-dead-code]] | Sync wrappers for async settings functions accumulated as dead code and were removed | resolved | backend, settings, dead-code |
| [[problems/asset-sync-transaction-closed]] | Bulk asset sync failed with "This transaction is closed" due to concurrent commits on shared session | resolved | backend, async, database, sqlalchemy |
| [[problems/asset-list-500-provider-input-type]] | list_assets returned 500 when asset had ProviderInputType.AUTO_GENERATED — wrong enum used in FAinfoResponse | resolved | backend, assets, providers, api, enum |

## Entities

| Page | Summary |
|------|---------|
| [[entities/api-router]] | FastAPI router structure — all v1 API routes and their modules |
| [[entities/db-models]] | All SQLModel ORM models — tables, enums, constraints, design notes |
| [[entities/devpy-cli]] | `dev.py` — single CLI entry point for all developer operations |

## Workflows

| Page | Summary | Tags |
|------|---------|------|
| [[workflows/asset-onboarding-flow]] | End-to-end steps to add an asset: create → provider → sync → view | assets, providers, ux |
| [[workflows/brim-import-flow]] | End-to-end broker report import: upload → detect → parse → match → commit | brim, brokers, transactions |

## Sources

| Page | Original | Date Ingested | Tags |
|------|----------|---------------|------|
| [[sources/roadmap-v1-summary]] | `RoadMapV1/01-Riassunto_generale.md` | 2026-04-24 | roadmap, architecture, history |
| [[sources/todos]] | `TODO_Completati.md` + `TODO_FUTURI.md` | 2026-05-10 | todo, planning, roadmap, features |
| [[sources/kb-03-documentation]] | `knowledge_base/03_documentation.md` | 2026-04-24 | mkdocs, documentation, i18n, aphra, gallery |
| [[sources/kb-06-testing-backend]] | `knowledge_base/06_testing_backend.md` | 2026-04-24 | testing, backend, pytest, api, coverage |
| [[sources/kb-07-testing-frontend]] | `knowledge_base/07_testing_frontend.md` | 2026-04-24 | testing, frontend, playwright, e2e, coverage |
| [[sources/kb-08-i18n-duplicates]] | `knowledge_base/08_i18n_duplicates.md` | 2026-04-24 | i18n, translations, duplicates, rationalization |
| [[sources/kb-01-backend]] | `knowledge_base/01_backend.md` | 2026-04-24 | backend, architecture, providers, cache, testing |
| [[sources/kb-02-frontend]] | `knowledge_base/02_frontend.md` | 2026-04-24 | frontend, architecture, sveltekit, stores, signals |
| [[sources/phase06-bugfix-migration]] | `phase-06-subplan/Bugfix-Step1/` | 2026-04-24 | phase06, responsive, typescript, i18n |
| [[sources/phase06-step2-providers]] | `phase-06-subplan/Bugfix-Step2/checklist` | 2026-04-24 | phase06, providers, css-scraper, scheduled |
| [[sources/phase06-step2c-sync-refactor]] | `phase-06-subplan/Bugfix-Step2/plan-Step2c` | 2026-04-24 | phase06, sync, delete, architecture |
| [[sources/phase06-step6-i18n-polish]] | `phase-06-subplan/Bugfix-Step6/` | 2026-04-24 | phase06, i18n, polish, coverage |
| [[sources/phase06-step3-rounds]] | `phase-06-subplan/Bugfix-Step3/` Rounds 1–11 | 2026-05-24 | phase06, assets, assetmodal, scheduledInvestment |
| [[sources/phase06-step4-plana]] | `phase-06-subplan/Bugfix-Step4/PlanA/` + `Plan0/` | 2026-05-24 | phase06, assets, detail, signals, charts |
| [[sources/phase06-step4-planc]] | `phase-06-subplan/Bugfix-Step4/PlanC/` | 2026-05-24 | phase06, fx, currency-conversion, cache |
| [[sources/roadmap-v4-index]] | `RoadMapV4/00-Index.md` | 2026-01-09 | roadmap, frontend, v4, phases, history |
