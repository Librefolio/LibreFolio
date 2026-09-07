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
| [[domains/dashboard]] | DASHBOARD | F-054–F-055 | implemented |
| [[domains/calculations]] | CALCULATIONS | F-056–F-058 | stable |
| [[domains/infrastructure]] | INFRASTRUCTURE | F-059–F-074 | stable |

---

## Feature Registry

| Page | Description |
|------|-------------|
| [[features/registry]] | **Authoritative code→title→status→mkdocs table — READ THIS FIRST** (96 features across 12 domains) |

## Individual Feature Pages

> **This is a selection, not the catalogue.** The authoritative list of all
> features — code, title, status, mkdocs link — is **[[features/registry]]**, and it
> is the only place that is kept complete. The table below highlights feature pages
> with substantial prose worth reading on their own; a feature's absence from it
> means nothing. Do not "fix" it by pasting in the remaining ~80 rows: that was
> tried (an auto-recovered dump of 60 bare `F-NNN` links with no title and no
> status), it duplicated the registry without its information, and it was removed
> on 2026-09-01.

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
| [[features/F-054]] | Dashboard KPI & Overview (unified `/portfolio/report`) | Dashboard | implemented |
| [[features/F-055]] | Portfolio Charts (Holdings/Performance panel, GrowthChart, Allocation) | Dashboard | implemented |
| [[features/F-058]] | ROI Calculations (TWRR + MWRR) | Calculations | implemented |
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
| [[decisions/drawdown-full-history-warmup]] | Drawdown has unlimited memory: `full_history` param (UI toggle) loads from `date.min`, AI Export always full; a SQL max-seed is FX-unsafe | 2026-09-02 | backend, signals, risk, drawdown, ai-export, warmup |
| [[decisions/settings-write-path-contract]] | Confirm before applying, report per field, never stop at the first refusal — C1-C9 answered as one contract | 2026-08-30 | settings, frontend, ux, api-contract |
| [[decisions/broker-last-owner-guard]] | Removal of the last owner is blocked while demotion to VIEWER is not; the obvious repair was rejected in favour of a dialogue | 2026-08-30 | brokers, sharing, permissions, ux |
| [[decisions/ai-export-news-driver-analysis]] | Portfolio news-driver Analysis combines deterministic movements with cited dated research while qualifying causality and preserving unexplained moves | 2026-08-03 | ai-export, portfolio, news, citations, causality |
| [[decisions/ai-export-technical-series-and-density-contract]] | Complete scope; indicator history 5/10/all non-empty rows and event windows 7d/min3, 21d/min10, 30d/min20, with warning rather than automatic cap | 2026-08-03 | ai-export, signals, timeseries, sampling, events, payload-size, risk |
| [[decisions/risk-g6-application-contracts]] | Stable/pending-approval G6 contracts: proxy audit trail, lazy-panel cache identity, present-buckets + Show all UX, and optional inert YAML tags | 2026-07-29 | risk, frontend, scenarios, cache, yaml |
| [[decisions/risk-quant-engine-process-boundary]] | QuantLib simulation and Riskfolio optimization run in separate lazy spawn pools with warm reuse, safe idle reap, and no in-process native math or silent fallback | 2026-07-28 | backend, risk, quantlib, riskfolio, multiprocessing |
| [[decisions/ai-export-contextual-ui-memory]] | AI Export drafts use user/context-scoped session storage with a sliding 10-minute TTL; logout or any new login resets defaults, while stale-operation guards remain | 2026-08-04 | frontend, ai-export, ui-memory, session-storage, ttl, auth, privacy |
| [[decisions/ai-export-versioned-snapshot-boundary]] | First public V1 uses one runtime over 67 components/40 datasets/11 analyses; functional tests avoid frozen prompt wording and semantic probes remain separate | 2026-08-05 | ai-export, backend, frontend, snapshot, components, testing, security, mcp |
| [[decisions/credit-agricole-securities-only-cash-neutral-brim]] | Crédit Agricole securities-only BRIM imports trades cash-neutral; succession legs become faithful BUY+DEPOSIT pairs | 2026-07-25 | backend, brim, broker, credit-agricole, cash |
| [[decisions/fifo-v4-income-eligibility-d1]] | FIFO v4 income eligibility uses D-1 open quantity, scoped to paying broker, transfer-aware | 2026-07-22 | backend, fifo, dividend, interest |
| [[decisions/fifo-v4-cost-allocation-ladder]] | Distinct deterministic FEE/TAX matching ladders route asset-linked costs to lots | 2026-07-22 | backend, fifo, fee, tax |
| [[decisions/fifo-v4-engine-architecture]] | One canonical FifoLotEngine path; native+target economic events; always-inline 3-level audit | 2026-07-22 | backend, fifo, architecture |
| [[decisions/fifo-v4-gross-net-status-model]] | Gross metrics untouched, net is additive; split analysis_status/LotNetMetricsStatus reliability model | 2026-07-22 | backend, frontend, fifo, net-metrics |
| [[decisions/fifo-v4-validation-and-scope]] | API-layer sign validation over DB CHECK; Portfolio Engine reconciliation deferred | 2026-07-22 | backend, validation, scope |
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
| [[decisions/mwrr-solver-newton-cap]] | Newton-Raphson-only XIRR solver + ±10000% result cap are deliberate design choices, not bugs (rejected Brent/hybrid) | 2026-07-07 | backend, portfolio, mwrr, xirr, financial-math, design-decision |
| [[decisions/portfolio-summary-direct-wiring]] | `get_summary()` wired directly to `PortfolioCalculationEngine` (no separate `DerivedViewsBuilder.build_summary()`); unified `/portfolio/report` replaces planned `/allocation-history`; `net_worth` field name kept | 2026-07-07 | backend, portfolio, architecture, api, design-decision |
| [[decisions/broker-list-visibility-non-members]] | Broker discovery opt-in (`include_inaccessible`) + read-only sharing visibility (icon everywhere) for EDITOR/VIEWER/non-members, no request-access flow | 2026-07-06 | backend, frontend, brokers, sharing, discovery, access-control |
| [[decisions/broker-card-aggregation-no-n-plus-one]] | Per-card quota%/NAV/Gain/cash-multivaluta on broker list via `GET /brokers` + one breakdown-enabled `/portfolio/report` call — never per-broker `/summary` | 2026-07-06 | backend, frontend, brokers, portfolio-engine, performance |
| [[decisions/ai-export-prompt-catalog]] | Historical frontend-only single-purpose prompt catalog; superseded by the Phase 0 versioned backend snapshot architecture | 2026-07-15 | frontend, ai-export, architecture, prompt-engineering |
| [[decisions/signal-backend-plugin-architecture]] | Technical indicators move to pure auto-discovered Python plugins consumed through one Asset/FX bulk request | 2026-07-23 | backend, frontend, signals, plugins, bulk-api |
| [[decisions/scheduler-converts-at-decision]] | An instant becomes a calendar day at the moment the scheduler decides, not at storage — one named conversion point, DST included | 2026-08-31 | backend, scheduler, timezone, dst, frontend |
| [[decisions/wac-target-currency-last-acquisition]] | WAC target currency is the last acquisition's currency, chosen because it is deterministic | 2026-06-03 | transactions, wac, currency, cost-basis, backend |
| [[decisions/blur-detection-format-string-comparison]] | Blur detection compares `formatDecimalForDisplay()` output, not numbers within a tolerance — the user's question is "did the displayed value change" | 2026-06-04 | frontend, transactions, wac, ux, precision |
| [[decisions/fxsyncmodal-parent-ownership]] | The parent owns `FxSyncModal`; the child asks via an `onOpenFxSync` prop instead of mounting its own | 2026-06-04 | frontend, transactions, fx, modal, architecture |

## Concepts

| Page | Summary | Tags |
|------|---------|------|
| [[concepts/test-isolation-classes]] | PURE/READ/WRITE_SCOPED/WRITE_GLOBAL derived from the real data model; `exclusive_because` declares class and reason in one place | testing, test-runner, parallelism, isolation |
| [[concepts/derived-test-inventory]] | Everything the runner needs is computable from the registry without executing a test; actions are near-pure command producers | testing, test-runner, registry, tooling |
| [[concepts/run-cache-and-campaign-semantics]] | `--fresh-run` vs `--resume` vs neither — omitting both is *not* equivalent to `--fresh-run`, and it has already caused a misread coverage report | testing, test-runner, cache, metrics |
| [[concepts/playwright-run-consolidation]] | Consolidation trades process count for process duration; the 8-spec ceiling under JS coverage is a V8 heap limit, measured | testing, playwright, performance, coverage |
| [[concepts/transaction-hygiene-fixture]] | Cleanup between files, not between tests; the premise *new ⇒ mine* dies at >1 worker, so the fixture disables itself and says so | testing, playwright, e2e, isolation |
| [[concepts/load-only-red-is-a-product-defect]] | Parallelism does not create defects, it widens the window; the rule, its evidence, and where it must be falsified | testing, parallelism, triage, method |
| [[concepts/coverage-rate-vs-volume]] | A point costs ~321-362 lines; six competing metrics, of which Branches is the only honest one; the long tail explains the slowness | testing, coverage, metrics, method |
| [[concepts/characterisation-test-latch]] | Freeze a behaviour you have not decided about, so the decision cannot be made silently or forgotten | testing, method, product-decisions |
| [[concepts/discard-the-answer-not-the-question]] | Dropping a superseded response is right; dropping the request with it is data loss that fails nothing — four defects, one shape | frontend, async, svelte5, races, ux |
| [[concepts/ai-export-catalog-granularity-and-composition]] | V1 exposes 8 data exports + 11 analyses over 67 components/40 internal datasets; granular projections remain internal and fail closed when requested directly | ai-export, composition, datasets, analyses, ux, granularity |
| [[concepts/cancellation-safe-inflight-deduplication]] | Shield followers and explicitly resolve leader cancellation when collapsing identical expensive async jobs | backend, async, cache, cancellation, risk |
| [[concepts/d1-income-eligibility-window]] | Income eligibility = open quantity at end of D-1, never same-day state | backend, fifo, dividend |
| [[concepts/deterministic-cost-matching-ladder]] | Ordered FEE/TAX target search (same-day trades → prev-day trades → open holdings → orphan) | backend, fifo, fee, tax |
| [[concepts/asset-orphan-vs-portfolio-level-cost]] | Asset orphan (unmatched but asset-linked) vs assetless portfolio-level cost — different buckets | backend, fifo, data-quality |
| [[concepts/gross-net-dual-reporting]] | Gross accumulators untouched; net = gross minus allocated fees/taxes, always additive | backend, frontend, fifo |
| [[concepts/async-io-rule]] | **CRITICAL**: sync I/O in async handlers blocks uvicorn event loop | backend, async, performance |
| [[concepts/daily-point-policy]] | One record per day for prices and FX rates (upsert semantics) | backend, db, prices |
| [[concepts/single-migration-strategy]] | Modify 001_initial.py + recreate DB — no incremental migrations | backend, db, alembic |
| [[concepts/backend-only-calculations]] | All financial calculations in backend — frontend is pure display | architecture |
| [[concepts/dual-view-pattern]] | Card grid + DataTable toggle persisted in localStorage | frontend, ux |
| [[concepts/svelte5-runes]] | New components use $state/$derived/$effect — not $: reactive | frontend, svelte |
| [[concepts/timeseries-store-pattern]] | Generic client-side cache with gap detection for delta fetching | frontend, stores, timeseries |
| [[concepts/editbuffer-pattern]] | Per-row DataRow.status tracking for in-place edit, CSV import, bulk save | frontend, components, data-editor |
| [[concepts/mkdocs-suffix-i18n]] | MkDocs uses suffix strategy (index.en.md, index.it.md) for multilingual docs | mkdocs, i18n, documentation |
| [[concepts/backend-test-isolation]] | ⚠️ **RETIRED 2026-09-01** — claimed `unique_id()` combines timestamp + UUID4 and that this makes tests isolated. Neither is true. Kept for its history; go to the two pages below instead | testing, backend, retired |
| [[concepts/unique-test-identifiers]] | The naming convention that *does* hold: `PREFIX_<ms>_<counter>`, a process-global counter — unique inside a process, **not** across processes | testing, backend, naming |
| [[concepts/assert-on-identity-not-prose]] | Assert on a `data-*` attribute or an i18n key, never on rendered text — text is a translation, identity is a contract | testing, frontend, i18n, assertions |
| [[concepts/silent-no-op-option]] | An option that is accepted, does nothing, and says nothing. Paid for four times before it was named | cli, testing, infra, design |
| [[concepts/absence-sentinel-vs-nullable-type]] | When "no value" is a real state, model it with a sentinel you can name — not with `null`, which conflates "absent" with "not loaded" | modelling, backend, frontend, api-contract |
| [[concepts/twrr-mwrr-algorithms]] | Time-weighted vs money-weighted return: what each answers, and why the app shows both | finance, portfolio, twrr, mwrr, performance |
| [[concepts/fifo-lot-tracking]] | FIFO lot model: acquisitions form lots, disposals consume them oldest-first — the basis of cost, gain and tax reporting | finance, fifo, holdings, tax |
| [[concepts/interactive-pros-cons-slider]] | The mkdocs pros/cons slider used to present a trade-off without picking a side for the reader | ui, mkdocs, user-guidance |
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
| [[concepts/ci-release-pipeline]] | GitHub Actions full pipeline: build→test→docker→push→release. Node 24, Vite 7.3.5, package-lock, 8 workers. Incl. F14 release-tag convention (SemVer vX.Y.Z, stable only) | ci, github-actions, release, docker, playwright |
| [[concepts/inline-wac-computation]] | Single-pass inline WAC replacing N×M `compute_wac_iterative` DB calls — pool_qty/pool_cost accumulators in per-tx loop | backend, portfolio, wac, performance, engine |
| [[concepts/pre-frame-frame-separation]] | No market eval before t0; pre-frame builds accounting state (qty/WAC/cash/K/R/W pools) from historical transactions | backend, portfolio, engine, performance, pre-frame |
| [[concepts/holdings-performance-panel]] | Holdings/Performance tabs (renamed Exposure/Contribution), date-aware `get_summary()`, reconciliation invariant row, treemap zoom/pan fix | frontend, backend, dashboard, portfolio, treemap, echarts |
| [[concepts/chart-resolution-semantic-zoom]] | Daily→weekly→monthly bucketing driven by `dataZoom` range, with density/hysteresis + debounce — applies to price/growth/allocation charts and 9 signal overlays | frontend, charts, echarts, performance, semantic-zoom |

## Problems

| Page | Summary | Status | Tags |
|------|---------|--------|------|
| [[problems/compactcashcell-decimal-separator-feedback-loop]] | Sync-down `$effect` compared display strings, so the field's own echo erased `,` mid-typing; fix = numeric compare; plus the `isVisible({timeout})` probe trap with delayed tooltips | resolved | frontend, transactions, decimal, svelte5, ux, testing |
| [[problems/sitecustomize-shadows-homebrew-python]] | A project `sitecustomize.py` on PYTHONPATH shadows Homebrew Python's own (one per interpreter, first wins) → prefix fixup lost → `pipenv` unimportable → test backend bootstrap dead; fix = chain-exec the shadowed file + guarded coverage import | resolved | testing, coverage, macos, homebrew, python, environment |
| [[problems/svelte-template-branches-not-instrumented]] | Istanbul emits an empty `branchMap` for `{#if}` in Svelte markup; `.svelte` branch percentages are indicative only | accepted | frontend, coverage, svelte, measurement |
| [[problems/coverage-percent-mixed-lines-and-branches]] | 92,33 → 90,10 was a change of formula, not a regression; the flat branch figure was the signal nobody read | resolved | testing, coverage, metrics, false-alarm |
| [[problems/e2e-python-coverage-lost-above-two-workers]] | `.coveragerc` lacked `multiprocessing`; above 2 clients uvicorn forks and five coverage files are written empty, silently | resolved | testing, coverage, python, silent-failure |
| [[problems/registered-but-unreachable-test-actions]] | Six actions / ~273 tests reachable by name but by no `all` suite; `check-orphans` verified string presence, not reachability | resolved | testing, test-runner, orphans, silent-failure |
| [[problems/conftest-autouse-write-breaks-pure-class]] | An autouse session fixture wrote to `app.db`, defeating a static purity proof that never reads `conftest.py` | resolved | testing, pytest, isolation, sqlite |
| [[problems/brim-file-store-rename-race]] | The path is derived from sidecar content while the data file is being renamed; plus a non-atomic metadata read-modify-write | resolved | backend, brim, filesystem, races |
| [[problems/commit-reported-success-on-rolled-back-batch]] | `POST /transactions/commit` answered `success` with `committed: false`; the over-broad first fix then removed the ● indicator for a week | resolved | backend, transactions, api-contract |
| [[problems/utc-today-vs-user-calendar]] | `toISOString().slice(0,10)` in 18 sites — 3 product defects, 1 test defect, 14 correct; the classification is the artefact | resolved | frontend, dates, timezone, product-defect |
| [[problems/namedcache-clear-leaves-admission-filter]] | `clear()` emptied the map but left theine's W-TinyLFU sketch loaded; the cache then rejected every `set()` forever, silently | resolved | backend, cache, theine, silent-failure |
| [[problems/bulk-validate-index-map-off-by-one]] | `resolveOps` and `buildOpsIndexMap` walk one list at different speeds; the WAC preview lands on the wrong transaction | resolved | frontend, transactions, bulk, off-by-one |
| [[problems/env-var-injection-point-duplicated]] | Two Playwright launchers, one wired: `E2E_WORKERS` produced a default instead of an error — green, 3× slower | resolved | test-runner, env-vars, silent-failure |
| [[problems/i18n-key-assertion-false-green]] | A test asserting on `$_()` output looks like it checks a key but reads translated text; it is green only while the key is untranslated | resolved | frontend, testing, i18n, false-green |
| [[problems/playwright-route-stub-is-per-context]] | `page.route()` binds one browser context; on a table without `user_id` another worker writes the row anyway | resolved | frontend, testing, playwright, parallelism |
| [[problems/shared-component-option-changed-globally]] | `connectNulls: false` set on the shared LineChart to fix FX would have inverted every overlay in the app | resolved | frontend, charts, echarts, blast-radius |
| [[problems/transactions-without-asset-filter-nan-loop]] | `__null__` became `NaN`; `NaN !== NaN` defeated the no-op guard and caused an endless filter/URL navigation loop | resolved | frontend, transactions, datatable, filtering, nan |
| [[problems/quantlib-sobol-seed-skipto]] | QuantLib Sobol constructor seed did not implement a stream offset; MC now uses `random_seed` and QMC uses `skipTo(sobol_start_index)` | resolved | backend, risk, quantlib, sobol, qmc |
| [[problems/mwrr-pole-dataless-period-start]] | MWRR cumulativo a polo quando il periodo parte in un giorno senza dati (domenica) con deposito sul primo NAV reale; fix escludendo i flussi già dentro il primo snapshot | resolved | backend, roi, mwrr, xirr |
| [[problems/risk-spawn-worker-idle-residency]] | Lazy Risk workers stayed resident until app shutdown; generation-safe idle reap now releases all lanes and preserves lazy restart | resolved | backend, risk, multiprocessing, memory |
| [[problems/spawn-worker-response-queue-semaphore-leak]] | Forced worker crashes leaked response-queue semaphores; one-way response pipes removed the leak | resolved | backend, multiprocessing, spawn, ipc |
| [[problems/riskfolio-numpy-vectorbt-dependency-trap]] | Riskfolio 7.3.0 conflicts with NumPy 2.5.1 through vectorbt/Numba; exact 7.0.1 provides P13 without either dependency | resolved | backend, riskfolio, numpy, dependencies |
| [[problems/ai-export-drawdown-selected-history-fallback]] | Asset drawdown returned 409 when the technical window was empty despite valid selected-period history; market context now falls back to selected observations | resolved | backend, ai-export, asset, drawdown |
| [[problems/ai-export-clipboard-fallback-unreachable]] | Non-modern clipboard fallback was unreachable; V2 now prepares once and uses `writeText`/`execCommand` while preserving the immediate `ClipboardItem` path | resolved | frontend, ai-export, clipboard, compatibility |
| [[problems/ai-export-cash-fx-valuation-basis-mismatch]] | Invalid equality between transaction-date engine cash and snapshot-date native-cash exposure caused Portfolio AI Export 503; currency allocation now uses its declared own denominator | resolved | backend, ai-export, portfolio, cash, fx |
| [[problems/import-wizard-fake-id-collision]] | Multi-file import merged fake asset-ids from different files onto one asset — namespaced per-file + clone txs | resolved | frontend, brim, import, data-integrity |
| [[problems/datatable-net-columns-hidden-override-model]] | DataTable visibility snapshot couldn't react to dynamic hasNetCosts default — switched to override model | resolved | frontend, datatable, fifo |
| [[problems/transaction-update-bypassed-sign-validation]] | Transaction UPDATE could persist positive FEE/TAX — CREATE validated, PATCH didn't | resolved | backend, validation, transactions |
| [[problems/fifo-income-silently-dropped-after-full-close]] | Pre-v4 income allocator silently skipped income when no lot was open — now becomes asset_orphan_income | resolved | backend, fifo, dividend, data-quality |
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
| [[problems/openapi-zod-discriminator-type-erasure]] | openapi-zod-client erased ZodObject discriminator options under --export-types; fixed by singleton enums + targeted post-process | resolved | frontend, openapi, zodios, pydantic, codegen |
| [[problems/test-transaction-implied-constructor-mismatch]] | `test_transaction_implied.py` (6 tests) fails with TypeError — test's local `_builder()` helper uses pre-refactor `DailyStateBuilder.__init__` signature (stale `wac_series` kwarg, missing `asset_currencies`) | open | backend, testing, portfolio, pre-existing, unrelated |
| [[problems/datatable-column-resize-noop]] | DataTable.svelte column-resize handle icon shows but click has no effect in some tables — root cause not yet determined | open | frontend, datatable, ui, unresolved |
| [[problems/portfolio-asset-history-regression-restored]] | `GET /portfolio/asset-history` accidentally removed in a legacy-endpoint cleanup (commit `3184a969`), restored (commit `1a734008`) | resolved | backend, api, portfolio, regression |
| [[problems/ai-export-name-not-ticker]] | AI export used ticker/ISIN as the primary asset label instead of `name` in several renderer/builder call sites | resolved | frontend, ai-export, naming |
| [[problems/docker-system-info-missing-deps]] | System Info showed `App Version: unknown` + 0 deps in Docker — `.git/`/`Pipfile`/`package.json` never copied into image | resolved | docker, deployment, system-info, pipfile |
| [[problems/docker-entrypoint-gid20-collision]] | `entrypoint.sh` chown fails on macOS — host GID 20 collides with Debian's pre-existing `dialout` group | open | docker, macos, entrypoint, gid, permissions |
| [[problems/pytest-exit-swallows-failures]] | `conftest.py` called `os._exit()` in `pytest_sessionfinish`, killing the process before pytest printed FAILURES — every red run looked clean | resolved | backend, testing, pytest, infra |
| [[problems/resume-mode-stale-import]] | `--resume` never skipped an already-passed sub-suite: `_RESUME_MODE` was imported by value at module load, so the flag set later was never seen | resolved | testing, test-runner, python, infra |
| [[problems/coverage-mode-stale-import]] | The same bug on the same day for `--coverage`: it never reached the Playwright runs | resolved | testing, test-runner, coverage, python, infra |
| [[problems/coverage-report-category-dest-collision]] | `coverage-report --category` reused the parent subcommand's argparse `dest` and silently overwrote it | resolved | testing, coverage, cli, argparse, python, infra |
| [[problems/brlistresponse-contract-drift]] | `GET /brokers` changed shape from a bare list to `BRListResponse{items, inaccessible}` without the consumers moving with it | resolved | backend, frontend, api-contract, testing, brokers |

## Entities

| Page | Summary |
|------|---------|
| [[entities/ai-export-snapshot-service]] | Sole AI Export runtime service with 67 components, 40 internal datasets, 8 public data exports, 11 analyses, exact stats, and a safe frontend prompt/clipboard boundary |
| [[entities/fifo-lot-engine]] | Canonical FIFO engine (backend/app/services/fifo_lot_engine.py) — quantitative replay + v4 economic allocation (income/fees/taxes, net metrics, 3-level audit) |
| [[entities/lots-analysis-service]] | Orchestration service between API and FifoLotEngine — FX prep, economic event building, DTO mapping; no longer the income allocator of record |
| [[entities/api-router]] | FastAPI router structure — all v1 API routes and their modules |
| [[entities/backup-router]] | `/api/v1/backup` read-only export router (asset prices/events, FX rates) — Policy D pre-wipe snapshot |
| [[entities/db-models]] | All SQLModel ORM models — tables, enums, constraints, design notes |
| [[entities/devpy-cli]] | `dev.py` — single CLI entry point for all developer operations |
| [[entities/import-wizard-modal]] | 4-step BRIM Import Wizard (wide modal, z:70) — UploadedFileEntry→FileSelection→ParsedFileResult→MergedTransaction pipeline |
| [[entities/market-data-scheduler]] | Embedded FastAPI scheduler daemon — current-price + history-sync jobs, leader election, JSONL log |
| [[entities/portfolio-engine]] | 4-layer portfolio engine (1603 lines) — ScopeAwareClassifier→DailyStateBuilder→DerivedViewsBuilder→PortfolioCalculationEngine |
| [[entities/portfolio-service]] | PortfolioService (1946 lines) — orchestration, L2 TTL cache, get_report/summary/history/contribution |
| [[entities/test-runner]] | `scripts/test_runner/` — **30 flat modules, 15 categories, 250 `add_test()` call sites**, registry built by 14 explicit `populate_registry()` calls (no auto-discovery). Rewritten from the code 2026-09-01 |
| [[entities/video-promo-remotion]] | Remotion-based promotional video pipeline (React, i18n-driven) |
| [[entities/time-series-aggregation]] | `timeSeriesAggregation.ts` — foundational bucketing/aggregation/hysteresis/debounce utility for resolution-aware charts |

## Workflows

| Page | Summary | Tags |
|------|---------|------|
| [[workflows/asset-onboarding-flow]] | End-to-end steps to add an asset: create → provider → sync → view | assets, providers, ux |
| [[workflows/brim-import-flow]] | End-to-end broker report import: upload → detect → parse → match → commit | brim, brokers, transactions |

## Sources

| Page | Original | Date Ingested | Tags |
|------|----------|---------------|------|
| [[sources/p7-js-coverage-instrumentation]] | P7 — JS/Svelte coverage via monocart; the feared obstacle (a different build artefact) did not exist | 2026-08-31 | testing, coverage, frontend, instrumentation |
| [[sources/p8-runner-parallel-architecture]] | P8 — runner migration: isolation classes, derived inventory, resource broker, three-level contract | 2026-08-31 | testing, test-runner, parallelism, architecture |
| [[sources/p9-test-semantics]] | P9 — what the suite's numbers mean; OOM is instrumentation, and a green is not evidence | 2026-08-31 | testing, semantics, method |
| [[sources/frontend-parallelism-tappe-7-11]] | Stages 7-11: consolidation, de-sleeping, and 216 tests in 5,6 min (3,0×) | 2026-08-31 | testing, parallelism, playwright, performance |
| [[sources/coverage-campaign-2026-08]] | The multi-lane coverage campaign; 15/15, 78,02 % lines, 59,45 % branch arms, 90,18 % backend | 2026-08-31 | testing, coverage, campaign, metrics |
| [[sources/coverage-fase012-and-branch-lanes]] | Phases 0-1-2 plus the sync and pure-logic lanes; the night run, the five metrics, `sortFn` never read | 2026-08-31 | testing, coverage, frontend, sync |
| [[sources/settings-lane-and-sixteen-defects]] | The sixteen tracked defects and the user's answers — the densest source of product decisions in the campaign | 2026-08-31 | settings, brokers, scheduler, fx, product-decisions |
| [[sources/coda-beta-parametric-forkserver]] | The beta coda: four discarded questions, forkserver orphans, the BRIM race, and how a slow endpoint is ruled out | 2026-08-31 | testing, parallelism, backend, method |
| [[sources/beta-testing-2026-08-05]] | First external beta: 34 findings adjudicated 30/2/2/3; `COMPRAVENDITA TITOLI` unhandled cost a ~50k hole | 2026-08-31 | beta-testing, brim, credit-agricole, reconciliation |
| [[sources/mkdocs-audit-2026-08-05]] | Read-only 182-page published EN MkDocs audit; 64 evidence-backed discrepancies, developer guide explicitly deferred | 2026-08-05 | audit, mkdocs, documentation, backend, frontend, ai-export, fx, admin |
| [[sources/phase00-risk-analysis-backend]] | Completed and audited `Release_2/Phase_0/02_riskfolioIntegration/` backend G0-G5 chain; G6 reconciled but not executed | 2026-07-28 | phase0, backend, risk, quantlib, riskfolio |
| [[sources/phase00-ai-export-backend-snapshot]] | Completed AI Export chain through first public V1, single runtime, separated semantic probes, 114/114 closure evidence, and zero orphan tests | 2026-08-05 | phase0, ai-export, snapshot, composition, runtime, testing, mcp |
| [[sources/fifo-v4-fee-tax-integration]] | `RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/` | 2026-07-22 | backend, fifo, fee, tax, dividend, cost-basis |
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
| [[sources/phase09-dashboard-batch]] | Phase 09 dashboard batch — KPI, TWRR/MWRR, FIFO, portfolio | 2026-06-30 | phase-09, dashboard, kpi, twrr, mwrr, fifo, portfolio |
| [[sources/source-code-v0.9.0-batch]] | Source-code sweep at v0.9.0 — Remotion, UI, gallery | 2026-06-30 | source-code, v0.9.0, remotion, ui, gallery |
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
| [[sources/phase09-m1-m2-archive-2026-07]] | Phase 09 M1+M2 archived to `phases/`: Holdings/Performance panel refactor, ~20 open items resolved, ~7 resolved differently, ~7 still open ✅ | 2026-07-07 | phase09, portfolio, dashboard, archive, holdings-performance, mwrr, twrr |
| [[sources/phase09-m3-broker-redesign-2026-07]] | Phase 09 M3 archived to `phases/phase-09-subplan/Milestone_3/`: Broker List/Detail v2 (discovery, sharing, per-card aggregation), FIFO lots UI panel, chart-resolution/semantic-zoom ✅ | 2026-07-15 | phase09, broker, dashboard, archive, chart-resolution, semantic-zoom, discovery, sharing |


## Chronological register

> **What changed when.** The full narrative lives in [`log.md`](log.md) — this is a
> map into it, not a second copy of it.
>
> Two rules keep it cheap, both applied 2026-09-01: a page is listed **once, on the
> date it was created**, never again when it is updated; and a bulk ingest is named
> and counted rather than expanded. Before that this section re-listed pages that
> the tables above already carry, which cost every reader of this index the same
> information two and three times over.

| Date | What happened | New pages |
|------|---------------|-----------|
| 2026-09-01 | **Lint repair.** 233 source-file paths remapped across 109 pages after the June 2026 refactors; three invented paths removed; [[entities/test-runner]] rewritten from the code; [[concepts/backend-test-isolation]] retired; the two bare-slug source twins deleted into [[sources/phase07-part4-round3-staging-rewrite]] and [[sources/phase07-part4-round5-server-type-rules]] | [[concepts/unique-test-identifiers]], [[concepts/silent-no-op-option]], [[concepts/assert-on-identity-not-prose]] |
| 2026-08-31 | **Consolidation ingest** — 14 session plans + the 2026-08-05 beta report. 9 source pages, 10 concepts, 3 decisions, 14 problems. All listed in the tables above; the sources are grouped under [[sources/coverage-campaign-2026-08]] and its siblings | *(38 pages — see log)* |
| 2026-07-15 | Phase 09 M3 broker redesign archived | [[sources/phase09-m3-broker-redesign-2026-07]], [[concepts/chart-resolution-semantic-zoom]], [[entities/time-series-aggregation]], [[decisions/broker-list-visibility-non-members]], [[decisions/broker-card-aggregation-no-n-plus-one]], [[problems/portfolio-asset-history-regression-restored]] |
| 2026-07-07 | Phase 09 M1/M2 archived; F-054 / F-055 / F-058 planned → implemented | [[sources/phase09-m1-m2-archive-2026-07]], [[concepts/holdings-performance-panel]], [[decisions/mwrr-solver-newton-cap]], [[decisions/portfolio-summary-direct-wiring]], [[problems/test-transaction-implied-constructor-mismatch]], [[problems/datatable-column-resize-noop]] |
| 2026-07-01 | Portfolio engine 3-pool refactor | [[sources/phase09-portfolio-engine-3pool-refactor]], [[concepts/inline-wac-computation]], [[concepts/pre-frame-frame-separation]] |
| 2026-06-30 | Phase 09 dashboard, Phase 07 Part 5 import wizard, Phase 08 scheduler, CI pipeline, final bug sweep — the wiki's first bulk population | *(23 pages — see log; all carried in the tables above)* |

> `[[decisions/mwrr-solver-newton-cap]]` is a **deliberate design decision, not a
> bug** — it has been mistaken for one before.
