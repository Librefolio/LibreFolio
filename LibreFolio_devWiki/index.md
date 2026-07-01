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
| [[features/F-047]] | Transaction List Page (DataTable, always-pair-adjacent, client-side filters) | Transactions | implemented |
| [[features/F-048]] | Transaction Modals (Form / Bulk / Delete / Promote / Split — mode-less, Round 6 Plan D done) | Transactions | in-progress |
| [[features/F-059]] | Provider Registry Pattern | Infrastructure | implemented |
| [[features/F-060]] | Thread Isolation for Providers | Infrastructure | implemented |
| [[features/F-061]] | 5-layer Provider Cache | Infrastructure | implemented |
| [[features/F-096]] | Scheduled Investment — Decoupled Frequencies + Anchor Day | Assets | idea |
| [[features/F-097]] | WAC — Weighted Average Cost (cross-currency, auto-calc on TRANSFER) | Transactions | in-progress |
| [[features/F-098]] | Progressive Web App (PWA) | Infrastructure | implemented |
| [[features/F-099]] | Borsa Italiana Asset Provider | Assets | implemented |

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
| [[decisions/brim-parser-only]] | BRIM Revision 2 — parser only, no commit endpoint, no asset events | 2026-04-20 | brim, brokers, architecture |
| [[decisions/multi-broker-atomic-tx]] | Bulk TX endpoints are not broker-scoped — accept items across multiple brokers | 2026-04-20 | transactions, api, atomicity |
| [[decisions/tx-link-uuid-semantics]] | link_uuid semantics: TRANSFER requires distinct brokers; DEPOSIT/WITHDRAWAL soft-linkable; promote endpoint | 2026-04-21 | transactions, transfer, linking |
| [[decisions/price-currency-hard-reject]] | Hard 400 on price currency mismatch; 409 on asset currency change with existing prices | 2026-04-21 | prices, currency, api, validation |
| [[decisions/policy-d-currency-wipe]] | Asset currency change → destructive symmetric wipe (prices + events); transactions preserved with `asset_event_id=NULL`; pre-confirm via new `/backup` router | 2026-04-23 | assets, currency, destructive, fifo, backup |
| [[decisions/transactions-client-side-filtering]] | All `/transactions` page filtering is client-side; `GET /transactions` loads all records; Refresh button for reload | 2026-04-28 | transactions, frontend, datatable, filtering |
| [[decisions/datatable-tooltip-custom-cell]] | Tooltips in DataTable cells use `<Tooltip.svelte>` via CustomCell only — `title=""` HTML attribute prohibited | 2026-04-28 | frontend, datatable, tooltip, svelte5 |
| [[decisions/dual-transaction-form-design]] | TransactionFormModal dual mode: single modal produces 2 linked payloads for FX/Transfer pairs | 2026-05-25 | frontend, transactions, modal, dual-form, pair |
| [[decisions/unified-batch-pipeline]] | 4 TX mutation endpoints → 2 (validate + commit) with TXMixedBatch + lenient per-row parse | 2026-04-29 | backend, transactions, api, architecture, pipeline |
| [[decisions/server-driven-type-rules]] | Replace 3 hardcoded frontend type-rule files with server-fetched `transactionTypeStore` | 2026-04-30 | backend, frontend, transactions, type-rules, auto-sign |
| [[decisions/test-runner-package-split]] | Monolithic test_runner.py (4841 lines) → 18-module package with distributed registry pattern | 2026-05-26 | testing, infrastructure, cli, refactoring, test_runner |
| [[decisions/static-metadata-export]] | Static JSON export of constant metadata at compile-time — deferred to Phase 8+ | 2026-05-26 | backend, frontend, architecture, api-sync, metadata, performance |
| [[decisions/txstore-single-source-of-truth]] | txStore replaces prop cascade — single Map<id,TXReadItem> eliminates 5 bug categories; -30% LOC | 2026-05-08 | frontend, transactions, stores, architecture, refactor |
| [[decisions/pendingop-tagged-union]] | PendingOp tagged union (create\|edit) replaces DraftRow — zero-copy originals, derived status, type-safe branching | 2026-05-11 | frontend, transactions, bulkModal, architecture, type-safety |
| [[decisions/bulkmodal-mode-removal]] | BulkModal mode-less: no mode prop, each row infers create/edit from tx.id > 0 | 2026-05-07 | frontend, transactions, bulkModal, architecture |
| [[decisions/cash-transfer-split-promote]] | CASH_TRANSFER first-class enum + split/promote via batch pipeline (standalone endpoints eliminated) | 2026-04-30 | frontend, backend, transactions, transfer, enum, batch-pipeline |
| [[decisions/context-menu-all-tables]] | ContextMenu default ON on all DataTables (right-click + mobile long-press) | 2026-05-05 | frontend, datatable, ux, context-menu |
| [[decisions/broker-access-min-paired]] | Paired access = min(role_A, role_B) + 3-layout delete + partner_broker_id | 2026-05-05 | frontend, transactions, broker-access, paired |
| [[decisions/pair-description-tags-validation]] | Linked transaction pairs must have identical description and tags — backend validates with pairDescriptionMismatch/pairTagsMismatch | 2026-05-10 | backend, transactions, validation, pair |
| [[decisions/auto-populate-removal]] | Remove implicit auto-populate from bulk_assign_providers — metadata flow now frontend-driven (probe→diff→PATCH) | 2026-05-11 | backend, assets, providers, metadata |
| [[decisions/formmodal-contextual-validate]] | FormModal sends entire bulk context to /validate for same-day dependency resolution | 2026-05-11 | frontend, transactions, validation, formModal |
| [[decisions/end-of-day-balance-check]] | Balance validation uses end-of-day aggregation — intra-day order irrelevant; consistent with daily-point policy | 2026-05-11 | backend, transactions, validation, balance |
| [[decisions/cost-basis-currency-object]] | cost_basis_override changed from bare SafeDecimal to Currency object {code, amount} — enables WAC cross-currency | 2026-05-24 | transactions, cost-basis, currency, schema, breaking-change |
| [[decisions/wac-inline-validate-commit]] | WAC computed in /validate response (preview) and applied in /commit post-flush — no standalone endpoint in editing flow | 2026-05-28 | backend, frontend, transactions, wac, architecture, api |
| [[decisions/port-6040-scheme]] | All ports migrated from 8000/8001/8002 to 6040/6041/6042 — "60/40 rule" mnemonic | 2026-05-27 | infrastructure, ports, developer-ergonomics |
| [[decisions/batch-only-split-promote]] | Standalone /split and /promote endpoints eliminated — batch-only via execute_batch | 2026-05-12 | backend, transactions, split, promote, batch-pipeline |
| [[decisions/import-wizard-v5-paradigm]] | Import Wizard v4→v5 paradigm: single-file modal → multi-file 4-step stepper | 2026-06-08 | frontend, brim, import-wizard, ux, stepper |
| [[decisions/mwrr-boundary-fix]] | MWRR XIRR double-counting deposits fix: initial_nav = nav_snapshots[0].nav | 2026-06-30 | backend, portfolio, mwrr, xirr, financial-math |

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
| [[concepts/prices-current-side-effect]] | `/assets/prices/current` is not read-only — it upserts today's OHLC; never chain with `/sync` | backend, frontend, assets, api-contract, side-effect |
| [[concepts/savewithretry-frontend-pattern]] | Unified modal save helper: error extraction, inline formError, optional toast, onError hook | frontend, ux, error-handling, modals |
| [[concepts/entity-store-pattern]] | `createEntityStore<T>()` factory for bounded entity caches with proper `invalidate()` semantics | frontend, stores, cache, svelte5 |
| [[concepts/always-pair-adjacent]] | TRANSFER/FX_CONVERSION pairs always rendered adjacent in TransactionsTable (giver above / receiver below) | frontend, transactions, datatable, rendering |
| [[concepts/opportunistic-cache-merge]] | Any code with fresh entity data calls `merge()` to deposit into shared store — universal ingress pattern | frontend, stores, cache, assets |
| [[concepts/validate-scheduler-pattern]] | Debounce 1s + idle 60s + manual validate with anti-bounce 10s; auto-disable above 50 rows | frontend, transactions, validation, scheduling |
| [[concepts/resolve-validation-message-pattern]] | Frontend i18n error resolution: code→i18n key, ID→name via stores, amount→formatted | frontend, transactions, i18n, error-handling |
| [[concepts/safe-decimal-pattern]] | SafeDecimal type prevents scientific notation in JSON responses; use instead of Decimal in response schemas | backend, serialization, pydantic, decimal, json |
| [[concepts/txstore-pattern]] | txStore.svelte.ts: page-scoped Map<id,TXReadItem> — single source of truth for transactions, WorkspaceIntent + PendingOp model | frontend, stores, transactions, svelte5, single-source-of-truth |
| [[concepts/paired-partner-architecture]] | pairedWith + getPartnerOp + visibleOps + resolveFormItems — frontend paired TX management | frontend, transactions, bulkModal, architecture, paired |
| [[concepts/stateless-preview-pattern]] | Controlled components for computed values — no internal state, cache on data model | frontend, svelte5, reactivity, controlled-component, wac |
| [[concepts/log-level-policy]] | 6-level hierarchy (CRITICAL→TRACE=5) with practical rules; structlog LEVEL_TO_NAME patched | backend, logging, structlog, trace, policy |
| [[concepts/image-preview-cache-pattern]] | objectUrl cache with size-based reuse; no ref counting, held for page lifetime | frontend, images, cache, performance, objecturl |
| [[concepts/fx-range-helper-pattern]] | ensureFxRangeLoaded centralizes gap-detect→bulk-fetch→merge for FX stores | frontend, fx, stores, dry, cache |
| [[concepts/centralized-tx-payload]] | txPayloadHelpers.ts + txCommitApi.ts — 9 callsites → single resolveOps()→buildBatchPayload()→commitBatch() | frontend, transactions, payload, api, dry |
| [[concepts/workspace-intent-pattern]] | Frontend-only Svelte 5 declarative API for bulk staging intents (create/edit/clone/delete/import) — NOT backend multi-tenancy | frontend, svelte5, transactions, bulkModal, staging |
| [[concepts/import-todo-signals]] | Plugin-emitted field blanks (severity: blocker/warning) — wizard-local, never touch PendingOp | frontend, brim, import, wizard, signals |
| [[concepts/3-pool-cash-model]] | Cash decomposed into deposited/invested/realized — powers GrowthChart 3-line visualization | backend, portfolio, cash, decomposition, dashboard |
| [[concepts/portfolio-report-unified]] | /portfolio/report runs engine once and returns all dashboard data — prevents race conditions + double runs | backend, api, portfolio, performance, cache |
| [[concepts/ci-release-pipeline]] | GitHub Actions full pipeline: build→test→docker→push→release. Node 24, Vite 7.3.5, package-lock, 8 workers | ci, github-actions, release, docker, playwright |
| [[concepts/inline-wac-computation]] | Single-pass inline WAC replacing N×M `compute_wac_iterative` DB calls — pool_qty/pool_cost accumulators in per-tx loop | backend, portfolio, wac, performance, engine |
| [[concepts/pre-frame-frame-separation]] | No market eval before t0; pre-frame builds accounting state (qty/WAC/cash/K/R/W pools) from historical transactions | backend, portfolio, engine, performance, pre-frame |

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
| [[problems/prices-current-sync-chain-empty-delta]] | Chaining `/prices/current` + `/sync` reports empty `changed_points` — `/current` already persisted today's row | resolved | backend, frontend, assets, prices, anti-pattern |
| [[problems/assets-wipe-error-attr-mismatch]] | `assets.py` wipe handlers used non-existent `e.code` (should be `e.error_code`) → HTTP 500 instead of 404 | resolved | backend, assets, exceptions, hidden-bug |
| [[problems/babel-currency-symbol-echo]] | `normalize_currency` echoed unknown garbage codes back as valid (babel quirk) — fixed via strict pycountry lookup | resolved | backend, currency, fx, hidden-bug |
| [[problems/svelte5-effect-read-write-loop]] | `$effect` reads and writes same `$state` → `effect_update_depth_exceeded` crash | resolved | frontend, svelte5, reactivity, infinite-loop |
| [[problems/babel-currency-symbol-locale]] | `get_currency_symbol('USD', locale='it')` returns `'USD'` not `'$'` — fix: always use `locale='en'` for symbol | resolved | backend, python, babel, currency, i18n |
| [[problems/datatable-filter-options-disappear]] | Enum filter options disappeared when count reached 0 due to `.filter(o => o.count > 0)` — removed that filter | resolved | frontend, datatable, filter, enum |
| [[problems/pydantic-422-preemption]] | Pydantic 422 pre-emption blocked service-layer validation; fixed by lenient per-row parse in unified pipeline | resolved | backend, pydantic, fastapi, transactions |
| [[problems/browser-autofill-numeric-fields]] | Chrome autofill on numeric text inputs — fixed with `autocomplete="off"` + randomised `name` | resolved | frontend, ux, forms, autofill |
| [[problems/dual-form-collect-duplication]] | FormModal/BulkModal had duplicated collect logic causing 3 cascading bugs — fixed via txPayloadHelpers.ts | resolved | frontend, transactions, dual-form, code-duplication |
| [[problems/wac-feedback-loop]] | WAC recalc → field update → WAC recalc infinite loop — fixed via explicit cost_basis_mode field | resolved | frontend, wac, reactivity, infinite-loop |
| [[problems/clone-link-uuid-duplication]] | Clone paired rows from DB didn't generate link_uuid — fixed via type-rule check | resolved | frontend, clone, link-uuid, paired |
| [[problems/fx-multi-route-no-fallback]] | FX sync_pairs_bulk used only primary route with no fallback — alternative routes (ECB/FED/SNB) ignored on failure | resolved | backend, fx, providers, sync, fallback |
| [[problems/broker-icon-race-condition]] | ensurePluginIconsLoaded race condition — broker icons show only dot in /files, tx filter, dashboard filter | open | frontend, broker-icon, race-condition, async |
| [[problems/import-wizard-identifier-prompt]] | oncreated path skips resolveAssetManual() → identifier prompt never opens for newly created assets | open | frontend, import-wizard, brim, identifier-prompt |
| [[problems/bulk-modal-sticky-z-index]] | After BRIM import row-selector toolbar clipped by overflow-y:auto container in BulkModal | open | frontend, bulk-modal, z-index, overflow, sticky |

## Entities

| Page | Summary |
|------|---------|
| [[entities/api-router]] | FastAPI router structure — all v1 API routes and their modules |
| [[entities/backup-router]] | `/api/v1/backup` read-only export router (asset prices/events, FX rates) — Policy D pre-wipe snapshot |
| [[entities/db-models]] | All SQLModel ORM models — tables, enums, constraints, design notes |
| [[entities/devpy-cli]] | `dev.py` — single CLI entry point for all developer operations |
| [[entities/import-wizard-modal]] | 4-step BRIM Import Wizard (wide modal, z:70) — UploadedFileEntry→FileSelection→ParsedFileResult→MergedTransaction pipeline |
| [[entities/market-data-scheduler]] | Embedded FastAPI scheduler daemon — current-price + history-sync jobs, leader election, JSONL log |
| [[entities/portfolio-engine]] | 4-layer portfolio engine (1603 lines) — ScopeAwareClassifier→DailyStateBuilder→DerivedViewsBuilder→PortfolioCalculationEngine |
| [[entities/portfolio-service]] | PortfolioService (1946 lines) — orchestration, L2 TTL cache, get_report/summary/history/contribution |
| [[entities/test-runner]] | Modular test runner package at scripts/test_runner/ — 18 modules, distributed registry pattern |

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
| [[sources/phase07-transactions]] | `phases/phase-07-subplan/Parte1/plan-phase07-transaction-Part1.md` ✅ DONE | 2026-04-24 (upd. 2026-04-25) | phase07, transactions, api, brim, staging |
| [[sources/phase07-part2-brim-revision]] | `phases/phase-07-subplan/Parte2/plan-phase07-transaction-Part2.prompt.md` ✅ DONE | 2026-04-24 (upd. 2026-04-25) | phase07, brim, parser-only, plugin-version, revision |
| [[sources/phase07-part3-api-consolidation]] | `phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3.md` ✅ DONE | 2026-04-24 (upd. 2026-04-25) | phase07, transactions, api, multi-broker, transfer, currency |
| [[sources/phase07-part3-closure]] | `phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3_1_Closure.md` ✅ DONE | 2026-04-24 (upd. 2026-04-25) | phase07, i-bis, currency, policy-d, wipe, backup |
| [[sources/phase07-part3-closure2]] | `phases/phase-07-subplan/Parte3/plan-phase07-transaction-Part3_1_Closure_2.prompt.md` (+ Batch4d + BlockG G1..G7) ✅ DONE | 2026-04-24 (upd. 2026-04-25) | phase07, test-coverage, batch4, savewithretry, delta, 87% |
| [[sources/phase07-part4-transactions-ui]] | `plan-phase07-transaction-Part4.prompt.md` ✅ DONE | 2026-04-28 | phase07, transactions, frontend, datatable, staging, always-pair-adjacent |
| [[sources/phase07-part4-round1]] | `plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md` ✅ DONE | 2026-04-28 | phase07, transactions, frontend, bugfix, filters, currency-stack, client-side-filtering |
| [[sources/phase07-part4-round2]] | `plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md` ✅ DONE | 2026-04-28 | phase07, transactions, frontend, entityStore, brokerStore, slider, tooltip |
| [[sources/phase07-part4-round3-staging-rewrite]] | `plan-phase07-transaction-Part4_Round3-stagingModalRewrite.prompt.md` ✅ DONE | 2026-05-25 | phase07, transactions, formModal, bulkModal, promoteWizard, validate-scheduler |
| [[sources/phase07-part4-round3-bugfix1]] | `plan-phase07-transaction-Part4_Round3_Bugfix1-formModalRedesign.prompt.md` ✅ DONE | 2026-05-25 | phase07, transactions, bugfix, UX, unsaved-changes, tags-autocomplete |
| [[sources/phase07-part4-round3-bugfix2]] | `plan-phase07-transaction-Part4_Round3_Bugfix2-i18nValidationErrors.prompt.md` ✅ DONE | 2026-05-25 | phase07, transactions, i18n, validation, pydantic, structured-errors |
| [[sources/phase07-part4-round4-unified-pipeline]] | `plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md` ✅ DONE | 2026-05-25 | phase07, transactions, api, pipeline, lenient-parse, breaking-change |
| [[sources/phase07-part4-round5-server-type-rules]] | `plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md` ✅ DONE | 2026-05-25 | phase07, transactions, type-rules, auto-sign, dual-form, dark-mode |
| [[sources/phase07-part4-round6-planb23-bulk-delete]] | `plan-phase07-transaction-Part4_Round6_PlanB23_BulkDeleteViaBulkModal.prompt.md` ✅ DONE | 2026-05-27 | phase07, transactions, bulkModal, deleteModal, mode-removal, bulk-delete |
| [[sources/phase07-part4-round5-bugfix1-dual-form]] | `...Round5_Bugfix1_DualFormAndBulkFixes.prompt.md` ✅ DONE | 2026-05-28 | phase07, transactions, cash-transfer, split, promote, paired-row |
| [[sources/phase07-part4-round5-bugfix2-testwalk-overhaul]] | `...Round5_Bugfix2_PostTestWalkOverhaul.prompt.md` ✅ DONE | 2026-05-28 | phase07, transactions, bulkModal, readonly, dual-dates |
| [[sources/phase07-part4-round5-bugfix3-testwalk-fixes]] | `...Round5_Bugfix3_TestWalkFixes.prompt.md` ✅ DONE | 2026-05-28 | phase07, transactions, patchable-fields, type-swap, tagInput |
| [[sources/phase07-part4-round6-context-menu-delete]] | `...Round6_ContextMenuDeletePolish.prompt.md` ✅ DONE (Steps 1-6,8) | 2026-05-28 | phase07, transactions, context-menu, delete-modal, picker-modal |
| [[sources/phase07-part4-round6-plana-context-menu-bugfix]] | `...Round6_PlanA_ContextMenuBugfix.prompt.md` ✅ DONE | 2026-05-28 | phase07, transactions, context-menu, bugfix, txPayloadHelpers |
| [[sources/phase07-part4-round6-planb-delete-picker-access]] | `...Round6_PlanB_DeletePickerAccess.prompt.md` + `PlanB1` ✅ DONE (Fase 1+B1) | 2026-05-28 | phase07, transactions, delete-modal, picker-modal, broker-access |
| [[sources/phase07-part4-round6-planb23-appendix1-ui-polish]] | `...Round6_PlanB23_Appendix1_UIPolish.prompt.md` ✅ DONE | 2026-05-29 | phase07, transactions, ui-polish, responsive, toast, row-tints |
| [[sources/phase07-part4-round6-planc-txstore-refactor]] | `...Round6_PlanC_TxStoreRefactor.prompt.md` ✅ DONE | 2026-05-29 | phase07, transactions, txStore, refactor, single-source-of-truth |
| [[sources/phase07-part4-round6-planc3-pendingop-refactor]] | `...Round6_PlanC3_PendingOpRefactor.prompt.md` ✅ DONE | 2026-05-30 | phase07, transactions, bulkModal, pendingOp, tagged-union, e2e |
| [[sources/phase07-part4-round6-planc2-bugfix-pair-validation]] | `...Round6_PlanC2_BugfixAndPairValidation.prompt.md` ✅ DONE | 2026-05-30 | phase07, transactions, bugfix, pair-validation, clone, picker, toast, e2e |
| [[sources/phase07-part4-round6-planc2r2-regressions-mockfx]] | `...Round6_PlanC2Round2_FixRegressionsAndMockFX.prompt.md` ✅ DONE | 2026-05-30 | phase07, transactions, mockfx, auto-populate, contextual-validate, balance-walk |
| [[sources/phase07-part4-round6-pland-split-promote-master]] | `plan-phase07-tx-Part4_Round6_PlanD_SplitPromoteFullStack.prompt.md` ✅ DONE | 2026-05-31 | phase07, transactions, split, promote, batch-pipeline |
| [[sources/phase07-part4-round6-pland1-backend-batch-suggest]] | `plan-PlanD1_BackendBatchSuggest.prompt.md` ✅ DONE | 2026-05-31 | phase07, transactions, backend, batch, suggest, endpoint-elimination |
| [[sources/phase07-part4-round6-pland2-frontend-split-promote]] | `plan-PlanD2_FrontendSplitPromoteUI.prompt.md` ✅ DONE | 2026-05-31 | phase07, transactions, frontend, promoteMergeModal, suggest-banner |
| [[sources/phase07-part4-round6-pland2-bugfix1]] | `plan-bugfix1_SplitPromotePolish.prompt.md` ✅ DONE | 2026-05-31 | phase07, transactions, bugfix, getTypeRule, promote-toolbar |
| [[sources/phase07-part4-round6-pland2-bugfix2]] | `plan-bugfix2_PayloadSplitPreviewUX.prompt.md` ✅ DONE | 2026-05-31 | phase07, transactions, pipeline-reorder, split-preview |
| [[sources/phase07-part4-round6-pland2-bugfix3]] | `plan-bugfix3_UXModalPayloadSuggestE2E.prompt.md` ✅ DONE (absorbed D3) | 2026-05-31 | phase07, transactions, e2e, split-schema, suggest-banner |
| [[sources/phase07-part4-round6-pland2-bugfix4]] | `plan-bugfix4_SplitSuggestPmcOverrideUx.prompt.md` ✅ DONE | 2026-05-31 | phase07, transactions, pmc-auto-calc, cost-basis, delta-days |
| [[sources/r2-walktest-feedback-master]] | `PlanD_SplitPromoteFullStack/plan-R2-WalktestFeedbackRound.prompt.md` (SP-A✅B✅C✅ D✅ E🔲) | 2026-06-01 | phase07, transactions, wac, cost-basis, fx, walktest |
| [[sources/r2-sp-a-cost-basis-wac]] | `R2-WalktestFeedback/plan-R2-SP-A-CostBasisWAC.prompt.md` ✅ DONE | 2026-06-01 | phase07, transactions, wac, cost-basis, currency, backend |
| [[sources/r2-sp-b-backend-tests]] | `R2-WalktestFeedback/plan-R2-SP-B-BackendTests.prompt.md` ✅ DONE | 2026-06-01 | phase07, transactions, wac, testing, backend |
| [[sources/r2-sp-c-bulkmodal-suggest-ux]] | `R2-WalktestFeedback/plan-R2-SP-C-BulkModalSuggestUX.prompt.md` ✅ DONE | 2026-06-01 | phase07, transactions, frontend, bulkModal, suggest, ux |
| [[sources/r2-sp-c-bugfix-chain]] | SP-C Bugfix Chain (11 plans): BugfixRound1+2, FxSpread, UnifiedPartnerArch, ReactiveWac, FixCloneLinkUuid, FixFeedbackLoop, WacInlineValidateCommit, FixPartnerRows, StatelessPreview, BackendCleanup ✅ | 2026-06-02 | phase07, transactions, wac, bugfix, partner-architecture, stateless-preview |
| [[sources/r2-parallel-features-pwa-borsa-fx]] | Batch 3: PWA, Port 60/40, Borsa Italiana, FX fix (parallel commits) ✅ | 2026-06-02 | pwa, mobile, ports, assets, fx, borsa-italiana |
| [[sources/independent-batch-2026-06-01]] | Batch 4: 5 independent plans (LogAudit, Candlestick, FxRange, LazyImage, RsiBands) ✅ | 2026-06-01 | backend, frontend, logging, charts, fx, cache, signals |
| [[sources/r3-sp-d-formmodal-wac-fx-chain]] | SP-D chain (6 plans): FormModal props + EventPicker + WAC FX feedback + currency selector + bugfixes ✅ | 2026-06-04 | phase07, transactions, wac, fx, event-picker, formmodal |
| [[sources/phase07-pland-split-promote]] | PlanD-D1D2: batch-only split/promote, _PromoteCandidate duck-typing, centralized payload layer ✅ | 2026-06-30 | phase07, transactions, split, promote, batch-pipeline |
| [[sources/phase07-part5-import-wizard-v5]] | BRIM Import Wizard v5: 4-step stepper, multi-file, ImportTodo signals, WorkspaceIntent, Schwab ✅ | 2026-06-30 | phase07, brim, import-wizard, stepper, multi-file |
| [[sources/phase07-standalone-pwa]] | PWA archive plan: mobile CSS + manifest + install button + 2 bugfixes (Svelte 5 runes, beforeinstallprompt race) ✅ | 2026-06-30 | pwa, mobile, svelte5, race-condition |
| [[sources/phase08-scheduler-backend]] | Phase 08: embedded scheduler daemon, leader election, 5 new settings, fetch_interval cleanup, test checkpoint ✅ | 2026-06-30 | phase08, scheduler, backend, leader-election |
| [[sources/phase09-portfolio-engine-dashboard]] | Phase 09 M2: 4-layer portfolio engine, 3-pool cash, MWRR fix, unified /report endpoint, L2 cache ✅ | 2026-06-30 | phase09, portfolio, engine, kpi, mwrr, dashboard |
| [[sources/wiki-audit-2026-06-18]] | Wiki audit: WorkspaceIntent = frontend-only (not backend), test_runner now modular package, lf-screenshot-carousel ✅ | 2026-06-30 | audit, documentation, workspace-intent, test-runner |
| [[sources/phase-final-bugs-2026-06-25]] | Phase final QA: 5 bug categories (broker icon race, files refresh, import wizard identifier, bulk modal toolbar) | 2026-06-30 | bugs, qa, docker, race-condition |
| [[sources/ci-release-pipeline-2026-06]] | CI/CD: GitHub Actions release.yml — Node 24, Vite 7.3.5, package-lock, Docker :test tag, 8 Playwright workers ✅ | 2026-06-30 | ci, release, docker, playwright, nodejs |
| [[sources/phase09-portfolio-engine-3pool-refactor]] | Phase 09 Engine Refactor: inline WAC single-pass, 3-pool K/R/W event-driven, SELL fix, pre-frame/frame, blob cache ✅ | 2026-07-01 | phase09, portfolio, engine, wac, 3-pool, refactor |


## Recent Additions (Phase 09 + Final + CI)
- [[sources/phase09-portfolio-engine-dashboard]] — 2026-06-30
- [[entities/portfolio-engine]] — 2026-06-30 (updated 2026-07-01)
- [[entities/portfolio-service]] — 2026-06-30 (updated 2026-07-01)
- [[concepts/3-pool-cash-model]] — 2026-06-30 (updated 2026-07-01)
- [[concepts/portfolio-report-unified]] — 2026-06-30
- [[decisions/mwrr-boundary-fix]] — 2026-06-30
- [[sources/phase07-part5-import-wizard-v5]] — 2026-06-30
- [[entities/import-wizard-modal]] — 2026-06-30
- [[concepts/workspace-intent-pattern]] — 2026-06-30
- [[concepts/import-todo-signals]] — 2026-06-30
- [[decisions/import-wizard-v5-paradigm]] — 2026-06-30
- [[sources/phase07-pland-split-promote]] — 2026-06-30
- [[decisions/batch-only-split-promote]] — 2026-06-30
- [[concepts/centralized-tx-payload]] — 2026-06-30
- [[sources/phase08-scheduler-backend]] — 2026-06-30
- [[entities/market-data-scheduler]] — 2026-06-30
- [[sources/wiki-audit-2026-06-18]] — 2026-06-30
- [[entities/test-runner]] — 2026-06-30
- [[sources/phase-final-bugs-2026-06-25]] — 2026-06-30
- [[problems/broker-icon-race-condition]] — 2026-06-30
- [[problems/import-wizard-identifier-prompt]] — 2026-06-30
- [[sources/phase09-portfolio-engine-3pool-refactor]] — 2026-07-01
- [[concepts/inline-wac-computation]] — 2026-07-01
- [[concepts/pre-frame-frame-separation]] — 2026-07-01
- [[problems/bulk-modal-sticky-z-index]] — 2026-06-30
- [[sources/ci-release-pipeline-2026-06]] — 2026-06-30
- [[concepts/ci-release-pipeline]] — 2026-06-30
- [[sources/phase07-standalone-pwa]] — 2026-06-30
- [[sources/phase09-dashboard-batch]] — (previously listed)
- [[concepts/twrr-mwrr-algorithms]] — (previously listed)
- [[concepts/fifo-lot-tracking]] — (previously listed)
- [[sources/source-code-v0.9.0-batch]] — (previously listed)
- [[entities/video-promo-remotion]] — (previously listed)
- [[concepts/interactive-pros-cons-slider]] — (previously listed)


## Uncategorized / Auto-Recovered

The following pages were automatically recovered by the lint pass:

### Features
- [[features/F-002]]
- [[features/F-005]]
- [[features/F-006]]
- [[features/F-007]]
- [[features/F-010]]
- [[features/F-011]]
- [[features/F-013]]
- [[features/F-016]]
- [[features/F-017]]
- [[features/F-018]]
- [[features/F-021]]
- [[features/F-022]]
- [[features/F-025]]
- [[features/F-026]]
- [[features/F-027]]
- [[features/F-028]]
- [[features/F-029]]
- [[features/F-030]]
- [[features/F-031]]
- [[features/F-032]]
- [[features/F-035]]
- [[features/F-040]]
- [[features/F-041]]
- [[features/F-043]]
- [[features/F-044]]
- [[features/F-049]]
- [[features/F-050]]
- [[features/F-057]]
- [[features/F-062]]
- [[features/F-063]]
- [[features/F-064]]
- [[features/F-065]]
- [[features/F-066]]
- [[features/F-067]]
- [[features/F-068]]
- [[features/F-069]]
- [[features/F-070]]
- [[features/F-071]]
- [[features/F-072]]
- [[features/F-073]]
- [[features/F-075]]
- [[features/F-076]]
- [[features/F-077]]
- [[features/F-078]]
- [[features/F-079]]
- [[features/F-080]]
- [[features/F-081]]
- [[features/F-082]]
- [[features/F-083]]
- [[features/F-084]]
- [[features/F-085]]
- [[features/F-086]]
- [[features/F-087]]
- [[features/F-088]]
- [[features/F-089]]
- [[features/F-090]]
- [[features/F-091]]
- [[features/F-092]]
- [[features/F-093]]
- [[features/F-094]]
- [[features/F-095]]

### Problems
- [[problems/pydantic-422-preemption]]

### Decisions
- [[decisions/blur-detection-format-string-comparison]]
- [[decisions/fxsyncmodal-parent-ownership]]
- [[decisions/wac-target-currency-last-acquisition]]

