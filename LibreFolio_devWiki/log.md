# devWiki Log

> Append-only chronological record of all wiki operations.
> Format: `## [YYYY-MM-DD] {operation} | {title}`
> Parse: `grep "^## \[" log.md | tail -10`

## [2026-04-24] lint | Lint pass #4 — Phase 07 contradictions + API URL audit

**Issues found**: 7 (4 high, 3 medium)
**Issues repaired**: 7

### 🔴 High — Repaired

1. **Contradiction**: `wiki/domains/transactions.md` said `POST /brokers/:id/transactions/bulk` and "atomic per broker / per-broker scoped" on 4 different lines. Real code (`tx_router = APIRouter(prefix="/transactions")`) has `POST /transactions/bulk` (multi-broker atomic). Fixed all 4 occurrences: prose, Mermaid node, Mermaid node label ("per-broker scoped"), key-decisions bullet. Also removed the ⚠️ "under active development" warning banner (F-046 is now implemented) and updated F-046 row status to `implemented`.

2. **Wrong API URLs**: `wiki/workflows/brim-import-flow.md` upload, list-files, and parse endpoints still referenced the old `/files/` router prefix. Real code: `brim_router = APIRouter(prefix="/import")` mounted under `broker_router(prefix="/brokers")`. Fixed: `POST /api/v1/brokers/import/upload?broker_id={id}`, `GET /api/v1/brokers/import/files?broker_ids={id}`, `POST /api/v1/brokers/import/files/{id}/parse`. Also corrected source-files reference from non-existent `files.py` to `brokers.py (brim_router)`.

3. **Missing file**: `wiki/sources/phase07-transactions.md` was indexed in `index.md` and `raw/ingest-registry.md` (hash `f17d963`) but the file did not exist (zombie entry from previous session). Created the source page from `plan-phase07-transaction-Part1.md`.

4. **Wrong enables**: `wiki/features/F-046.md` incorrectly listed `F-037` (Signal Library Framework) in `enables`. Signal Library depends on the asset detail chart area (F-033), not on the TX Bulk API. Removed F-037 from F-046 enables.

### 🟡 Medium — Repaired

5. **Malformed YAML + wrong cross-ref**: `wiki/features/F-037.md` had `depends_on: [F-046-area: PriceChartFull]` — invalid YAML (colon in value) and wrong F-code (F-046 is TX API, not a chart). Fixed to `depends_on: [F-033]` (Asset Detail Page chart/signals/editor is the actual dependency).

6. **Missing cross-ref**: `wiki/decisions/brim-parser-only.md` had no link to `[[decisions/brim-fake-asset-id]]`. Added a "Related decisions" section explaining that fake IDs are the mechanism that makes parser-only viable.

**Deferred (no action needed)**:
- `problems/asset-currency-mismatch.md` — already status `resolved`, no further action.
- F-047/F-048/F-049/F-050/F-051 status in transactions domain — Phase 7 is still in-progress for these features; left as-is.

## [2026-04-24] ingest | Created 11 domain cluster pages

**Pages created** (`wiki/domains/`):
- `auth.md` — Domain: AUTH (F-001–F-003)
- `layout-settings.md` — Domain: LAYOUT & SETTINGS (F-004–F-008)
- `brokers.md` — Domain: BROKERS (F-009–F-014)
- `fx.md` — Domain: FX Foreign Exchange (F-015–F-023)
- `assets.md` — Domain: ASSETS (F-024–F-036)
- `signals.md` — Domain: TECHNICAL ANALYSIS Signals (F-037–F-045)
- `transactions.md` — Domain: TRANSACTIONS (F-046–F-051) — status: in-progress
- `scheduler.md` — Domain: SCHEDULER (F-052–F-053) — status: planned
- `dashboard.md` — Domain: DASHBOARD (F-054–F-055) — status: planned
- `calculations.md` — Domain: CALCULATIONS (F-056–F-058)
- `infrastructure.md` — Domain: INFRASTRUCTURE (F-059–F-074)

**Updated**:
- `index.md` — added `## Domains` section with links to all 11 pages
- `wiki/features/registry.md` — added navigation note pointing to `wiki/domains/` for macro-level context

---

## [2026-04-24] ingest | Project bootstrap — codebase analysis

Sources analyzed: `knowledge_base/00_project_overview.md` @ git:`f17d963`, `RoadmapV4_UI/phases/00-index.md` @ git:`f17d963`, `plan-phase07-transaction-Part1.md` @ git:`f17d963`, `phase-08-scheduler.md` @ git:`66ad026`, `RoadMapV1/01-Riassunto_generale.md` @ git:`f17d963`, `backend/app/db/models.py` @ git:`f17d963`, `backend/app/api/v1/router.py` @ git:`f1205b7`.

Full codebase survey: backend API routes, services, providers (FX/Asset/BRIM), frontend routes, stores, components, mkdocs coverage.

**Created**:
- [[features/registry]] — 74 features across 11 domains with codes, status, mkdocs links
- [[features/F-012]] BRIM Framework
- [[features/F-019]] MANUAL Sentinel FX Provider
- [[features/F-020]] FX Currency Conversion Graph
- [[features/F-034]] Scheduled Investment Provider
- [[features/F-037]] Signal Library Framework
- [[features/F-056]] FIFO at Runtime
- [[features/F-059]] Provider Registry Pattern
- [[connections/dependency-graph]] — full project dependency graph
- [[connections/fx-connections]] — FX domain dependency map
- [[connections/assets-connections]] — Asset domain dependency map
- [[connections/transactions-connections]] — Transaction domain (Phase 7 gap analysis)

**Current project state**: Phases 0–6 complete, Phase 7 (Transactions) in progress (Part 1+2 done, Part 3–5 TODO), Phases 8–10 planned.


## [2026-04-24] init | devWiki initialized

Wiki structure created. SCHEMA.md, index.md, log.md bootstrapped.
wiki/ subdirectories: decisions/, entities/, concepts/, problems/, sources/.
Skills created: wiki-ingest, wiki-query, wiki-lint (historian agent); wiki-search, wiki-file (main agent).

## [2026-04-24] ingest | Conventions, changelogs, decisions — Phase 4–6

Sources: `knowledge_base/05_project_conventions.md` @ git:`957a124`, `changelog_2026-04-10_live-ticker-and-provider-lifecycle.md` @ git:`2c448cd`, `plan-fxSyncApiRedesign.prompt.md` @ git:`f123d4d`, `analysis-brim-multiuser.md` @ git:`84516e3`, `plan-data-separation.md` @ git:`f17d963`.

Created:
- Concepts: [[concepts/async-io-rule]], [[concepts/daily-point-policy]], [[concepts/single-migration-strategy]], [[concepts/backend-only-calculations]], [[concepts/dual-view-pattern]], [[concepts/svelte5-runes]]
- Decisions: [[decisions/fx-sync-pair-based]], [[decisions/brim-broker-scoped]], [[decisions/provider-shutdown-generic]], [[decisions/prod-test-data-separation]]
- Problems: [[problems/event-loop-blocking]], [[problems/liveticker-header-crash]], [[problems/flag-emoji-windows]]

## [2026-04-24] lint | First full lint pass

Issues found: 75 (62 systemic enables omission, 7 missing decision pages, 4 broken links, 2 misplaced files).
Fixes applied: moved 2 misplaced files, fixed 3 broken wikilinks, created 4 missing decision pages, populated `enables` field on all 74 feature pages, updated index.md.

## [2026-04-24] ingest | mkdocs developer docs + source file links

Read all English mkdocs developer pages (`mkdocs_src/docs/developer/`) to map features to actual source files.
Added `## Source files` tables to all 98 wiki pages (74 features, 6 concepts, 8 decisions, 3 problems, 4 connections, 1 entity, 1 source, 1 registry).
Updated historian agent and wiki-search skill with "source file linking" as a core rule.

## [2026-05-10] ingest | Phases 0–6 source files — bulk wiki creation

Sources ingested: phase-00-setup.md, phase-01-foundation.md, phase-02-backend-auth.md, phase-03-layout-settings.md, phase-04-brokers.md, phase-05-fx.md, phase-06-assets.md, phase-06-subplan Round12 (AssetEvent + ScheduleRedesign + MaturationEngine), phase-06-subplan Step4 PlanB (DataEditorUnification), plan-fxConversionChain.prompt.md, scheduled_investment.py, justetf.py, DataEditorTypes.ts, TimeSeriesStore.ts, fxStoreRegistry.ts, models.py (updated hash), Dockerfile, 04_devpy_reference.md.

Created decisions:
- [[decisions/sveltekit-over-react]] — V4 frontend stack choice
- [[decisions/zodios-api-client]] — type-safe API client
- [[decisions/single-docker-image]] — deployment architecture
- [[decisions/scheduled-investment-redesign]] — pure deterministic engine, AssetEvent table
- [[decisions/data-editor-unification]] — generic DataEditor component set

Created concepts:
- [[concepts/timeseries-store-pattern]] — gap-aware client-side time series cache
- [[concepts/editbuffer-pattern]] — DataRow status tracking in DataEditor

Created problems:
- [[problems/justetf-websocket-disconnect]] — silent WebSocket freeze, backoff workaround
- [[problems/asset-currency-mismatch]] — per-row PriceHistory.currency design rationale

Created entities:
- [[entities/db-models]] — full model table, enums, design notes (replaces old stub)
- [[entities/devpy-cli]] — CLI architecture, command groups, workflow commands

Created workflows (new wiki/ subdirectory):
- [[workflows/asset-onboarding-flow]] — create → provider → sync → view
- [[workflows/brim-import-flow]] — upload → detect → parse → match → commit

Updated feature status histories:
- [[features/F-001]] — Phase 0/1/2 details
- [[features/F-009]] — Phase 4 (45-day Broker CRUD phase)
- [[features/F-012]] — Phase 4 BRIM framework
- [[features/F-019]] — Phase 5 MANUAL sentinel
- [[features/F-020]] — Phase 5 FX Conversion Chain
- [[features/F-034]] — Phase 6 Round 12 redesign (added redesign entry + link to decision)
- [[features/F-037]] — Phase 5 initial + Phase 6 expansion
- [[features/F-059]] — Phase 1/4/5/6 registry extension history

Updated index.md: new decisions, concepts, problems, entities, workflows sections.

---

## 2026-05-10 — TODO Files Ingest & Feature Registry Expansion (F-075–F-095)

**Source**: `TODO_Completati.md` and `TODO_FUTURI.md` (project root)

### Task 1: Verified F-073 and F-050
- [[features/F-073]] (Backup & Restore): Status confirmed as `implemented` (partial). Per-series exports implemented; full portfolio export/restore are HTTP 501 placeholders. Wiki was already accurate.
- [[features/F-050]] (File Preview): Confirmed not started. Image preview via PreviewCache works; text/CSV/markdown not implemented. Status history updated.

### Task 2: Enriched existing feature pages
- [[features/F-008]] (i18n): Added 2-pass cleanup details (Phase 5: 724→590, Phase 6: 875→825 keys, 50 duplicates consolidated to `common.*`)
- [[features/F-014]] (Image Upload & Crop): Added cropperjs v2 rationale, key new files (ImageCropper, ImageEditModal, FileEditModal)
- [[features/F-061]] (5-layer Cache): Added FX Rate Cache (TTL 5min in `fx.py`) and Upload Metadata Cache (TTL 1h in `static_uploads.py`)

### Task 3: Registry expanded to F-095
Added Domain: PLANNED / IDEA FEATURES section with F-075–F-095 (21 new entries).

### Task 4: Created 21 feature pages
- [[features/F-075]] TanStack Table v9 Migration
- [[features/F-076]] Log Level Policy & TRACE Level
- [[features/F-077]] Mobile DataTable Touch Drag
- [[features/F-078]] User Filter in Files Page
- [[features/F-079]] GDPR Broker Access Compliance
- [[features/F-080]] Candlestick Chart / Volume Bars
- [[features/F-081]] Fiscal Sale Method (FIFO/LIFO/PMC/SelectID)
- [[features/F-082]] Cash Split Transactions
- [[features/F-083]] Multi-File Multi-Broker Import
- [[features/F-084]] Transaction Gain Chart
- [[features/F-085]] QuarkAI AI Assistant
- [[features/F-086]] Client-side Image Preview Cache (LazyImage)
- [[features/F-087]] Smooth Signal Line Style
- [[features/F-088]] Return-over-N Chart
- [[features/F-089]] FX Provider Per-Plugin Documentation
- [[features/F-090]] AssetEvent → Transaction Link (Enrichment)
- [[features/F-091]] Multi-Worker Cache Server
- [[features/F-092]] Default Language/Currency for New Users
- [[features/F-093]] Coupon Policy Field
- [[features/F-094]] Sync Date Range Dialog
- [[features/F-095]] Asset Delete Transaction Count Link

### Task 5: Created 2 problem pages
- [[problems/tanstack-svelte5-incompatibility]] — v8 adapter incompatible with Svelte 5 runes, custom adapter workaround
- [[problems/sync-functions-dead-code]] — sync wrappers removed as dead code; lesson: don't create unless immediate consumer

### Task 6: Created sources page
- [[sources/todos]] — documents both TODO files as continuous sources

### Task 7: Updated index.md, ingest-registry, log.md

---

## [2026-04-24] ingest | knowledge_base 03, 06, 07, 08

**Sources**: `knowledge_base/03_documentation.md`, `knowledge_base/06_testing_backend.md`, `knowledge_base/07_testing_frontend.md`, `knowledge_base/08_i18n_duplicates.md` — all @ git:`e8ab12a`.

### Created source pages
- [[sources/kb-03-documentation]] — MkDocs setup, Aphra v2 pipeline, gallery, documentation conventions
- [[sources/kb-06-testing-backend]] — Backend pytest architecture, _TestingServerManager, coverage, provider filtering
- [[sources/kb-07-testing-frontend]] — Playwright E2E patterns, fixtures, backend coverage SIGTERM architecture
- [[sources/kb-08-i18n-duplicates]] — i18n key rationalization principle, 42 duplicate groups

### Created concept pages
- [[concepts/mkdocs-suffix-i18n]] — Suffix strategy (`.en.md`, `.it.md`) for multilingual docs, ~36 source → 108 translated files
- [[concepts/backend-test-isolation]] — Each test creates own user via `unique_id()`, zero cross-test state
- [[concepts/e2e-data-testid-rule]] — ALWAYS use `data-testid`, NEVER CSS classes or text (i18n-safe, refactor-safe)

### Created decision page
- [[decisions/i18n-key-rationalization]] — Consolidate only when meaning+context+value match in all 4 languages; 42 groups (18 consolidated, ~30 accepted)

### Enriched feature pages
- [[features/F-067]] Playwright E2E Tests — added 2-project config, fixtures, backend coverage SIGTERM architecture, conventions, Linux deps
- [[features/F-068]] Backend API Tests — added _TestingServerManager details, mock data, coverage analysis, provider filtering, retry logic
- [[features/F-069]] MkDocs Multi-Language — added suffix i18n strategy, scope table, admonition blank line rule, gallery loader, style conventions, commands
- [[features/F-070]] Aphra LLM Translation Pipeline — added Aphra v2 architecture (shared analysis), 10-step cleaning, 13-dimension structural diff, cache, commands
- [[features/F-074]] E2E Test Gallery — added prerequisites (deterministic DB, Linux deps), output structure, viewport/theme/language loops, troubleshooting
- [[features/F-008]] i18n System — added two-pass cleanup stats, 42 duplicate groups, key namespaces table, CLI commands, reference docs

### Updated registries
- `raw/ingest-registry.md`: added 4 KB files @ git:`e8ab12a`
- `index.md`: added 3 concept pages, 1 decision page, 4 source pages
- `log.md`: this entry

## [2026-04-24] ingest | KB 01/02 backend+frontend, Phase06 Bugfix Steps 1/2/6

Ingested 7 source documents from Phase 06 development:

**Knowledge Base References**:
- `knowledge_base/01_backend.md` → [[sources/kb-01-backend]] — backend architecture overview
- `knowledge_base/02_frontend.md` → [[sources/kb-02-frontend]] — frontend architecture overview

**Phase 06 Plans**:
- Phase 06 Bugfix Migration Steps 1-3 → [[sources/phase06-bugfix-migration]]
- Phase 06 Step 2 Providers → [[sources/phase06-step2-providers]]  
- Phase 06 Step 2c Sync Refactor → [[sources/phase06-step2c-sync-refactor]]
- Phase 06 Step 6 i18n Polish → [[sources/phase06-step6-i18n-polish]]

**New Decisions Created**:
- [[decisions/three-phase-pipeline]] — PREPARE→FETCH→PERSIST pattern for bulk operations (fixes concurrent session commits)

**New Concepts Created**:
- [[concepts/responsive-4mode-layout]] — 4-breakpoint system (wide/tablet/tablet-s/mobile) for filter bar pages

**New Problems Documented**:
- [[problems/asset-sync-transaction-closed]] — SQLAlchemy concurrent commit error, resolved by 3-phase pipeline

**Key Insights**:
- 3-phase pipeline pattern is a **documented convention**, not a base class abstraction (FX and Asset implementations differ significantly)
- `tablet-s` breakpoint (500-770px) provides better UX for intermediate screen widths where neither tablet nor mobile layouts work well
- i18n duplicate consolidation reduced 18 groups (conservative approach, ~30 intentional duplicates preserved per context-aware rationalization principle)
- CSS Scraper and Scheduled Investment providers use `params_schema` for dynamic form generation
- SyncModalBase pattern extracted common sync modal logic (FX + Asset wrappers)
- TypeScript fixes: `getUserStorage` return type, `EditableNumberCell` min/max, lucide-svelte icon type compatibility

**Files enriched**: No existing feature/decision pages needed updates (all major patterns already documented).

**Registry updates**: Added 1 decision, 1 concept, 1 problem, 7 source pages.

---

## [2026-05-24] ingest | Phase06 Step3-rounds, Step4-PlanA, Step4-PlanC

Sources ingested: 14 plan files from Bugfix-Step3 (Rounds 1-11), 6 plan files from Bugfix-Step4 PlanA+Plan0, 5 plan files from Bugfix-Step4 PlanC. Git hash: `e8ab12a`.

All facts verified against source code before writing.

**Source pages created**:
- [[sources/phase06-step3-rounds]] — Step3 bugfix rounds 1-11: AssetModal, AssetSearchAutocomplete, ProviderAssignmentSection, ScheduledInvestmentEditor F9
- [[sources/phase06-step4-plana]] — Step4 PlanA+Plan0: asset detail page A1-A10, chart panel redesign, event markers, signal label unification
- [[sources/phase06-step4-planc]] — Step4 PlanC: FX-aware price queries C1-C5, multi-FX comparison, provider cache architecture

**Features enriched**:
- [[features/F-033]] Asset Detail Page — AssetModal implementation details, provider assignment section, full A1-A10 detail page, event markers, panel redesign
- [[features/F-034]] Scheduled Investment Provider — F9 editor: layout β, CellDateRange, contiguity engine, CRUD (Add/Delete/Split/Merge), bulk delete multi-gap, JSON ↔ form serialization, ui_component in params_schema
- [[features/F-037]] Signal Library Framework — signalLabel.ts utility, RenderedSignal enrichment (iconUrl/assetType/currency/currencyFlag), loadComparisonData.ts, MeasurePanel refactor, signal line styles by category
- [[features/F-042]] FX Pair Comparison Signal — staircase fix via null-gap filtering, currency labels in RenderedSignal, requiredFxPairs derived, FxStatusBanner, PageSyncAllModal
- [[features/F-020]] FX Currency Conversion Graph — C1-C5 FX-aware price queries: target_currency, OHLC scaling, dual staleness tracking, live ticker conversion, comparison overlays

**New decisions**:
- [[decisions/signal-label-unification]] — `signalLabel.ts` + enriched `RenderedSignal` as single source of truth for signal visual labels

**New problems**:
- [[problems/asset-list-500-provider-input-type]] — list_assets 500 on AUTO_GENERATED identifier type; fix: apply `map_input_type_to_identifier_type()` before building FAinfoResponse

**Skipped / not enriched**:
- F-035 (CSS Scraper): no new information in these plans
- F-036 (Provider Comparison Modal): no new information in these plans
- F-038/F-039/F-040/F-041 (individual signal pages): plan-partC_5 adds line style info to F-037 (framework), not individual signals
- F-060 (Thread Isolation): already well documented; plan-partC_7 confirms but adds no corrections
- F-061 (5-layer Provider Cache): already well documented with smart history range details

**Registry updates**: Added 3 source pages, 1 decision, 1 problem; enriched 5 feature pages; updated index.md and ingest-registry.md.

---

## [2026-04-24] ingest | TODO_FUTURI re-ingest + mkdocs developer pages mapping

**Task 1 — Re-ingest TODO_FUTURI.md**

Source: `TODO_FUTURI.md` @ git:`fcdd89e` (2026-04-17)

Comparison with existing registry F-075–F-095: all 21 features already documented from previous ingest (2026-05-10). Detected 1 NEW feature not yet in registry:

- **F-096** Scheduled Investment — Decoupled Frequencies (price vs coupon) + Anchor Day

**Created**:
- [[features/F-096]] — idea status, extends [[features/F-034]]

**Updated**:
- [[features/registry]] — added F-096 row, updated statistics (96 total features, 22 planned/idea)
- [[sources/todos]] — added F-096 to table

**Task 2 — Map mkdocs developer pages to features**

Systematically read all 68 mkdocs developer pages and mapped them to 36 features. Mapping hypothesis:

- **Architecture**: patterns (registry, async, alembic, config, plugin guides) → F-006, F-012, F-015, F-025, F-059, F-064
- **Database**: schema pages → F-001, F-002, F-009, F-016, F-030, F-046, F-064
- **Backend**: FX/Assets/BRIM architecture → F-012, F-013, F-015, F-016, F-017, F-018, F-019, F-024, F-025, F-026, F-027, F-031, F-034, F-035
- **API**: overview and testing → F-068
- **Frontend**: styling, i18n, state, components → F-001, F-004, F-005, F-008, F-009, F-011, F-020, F-071, F-072
- **Testing**: walkthrough pages → F-067, F-068
- **Docs/Tools**: translation pipeline, dev setup → F-063, F-070

**Updated 36 feature pages**:
- Frontmatter `mkdocs:` field — changed from `null` to primary mkdocs path (e.g., `"developer/backend/fx/architecture.md"`)
- `## Source files` table — prepended mkdocs rows (Primary mkdocs + secondary mkdocs pages for each feature)

**Coverage**:
- F-001, F-002, F-003, F-004, F-005, F-006, F-008, F-009, F-011, F-012, F-013
- F-015, F-016, F-017, F-018, F-019, F-020
- F-024, F-025, F-026, F-027, F-030, F-031, F-034, F-035, F-046
- F-059, F-060, F-063, F-064, F-067, F-068, F-070, F-071, F-072, F-096

**Pages with no feature mapping** (general infrastructure / UI library docs):
- `developer/api/overview.md`
- `developer/frontend/index.md`, `pages/index.md`, `components/index.md`, `components/data-table.md`, `components/live-ticker.md`, `components/select.md`
- `developer/frontend/components/ui-base/{atoms,datePickers,feedback,modals}.md`

**Registry summary after update**:
- 96 total features
- 62 implemented/documented
- 3 in-progress
- 31 planned/idea
- **36 features now linked to mkdocs developer pages** (up from 0 before this session)

## [2026-04-24] lint | Full reasoned lint pass #3

**Checks run**: thin pages, missing source sections, broken wikilinks, F-096 symmetry, registry vs files, mkdocs path validity, index orphans, log format, conceptual quality, connections currency.

**Issues found and fixed**:
- ✅ F-075–F-096: added full "Domain: PLANNED/IDEA" section to `registry.md` (22 features were counted in stats but had no individual rows)
- ✅ F-034 `enables:` updated to include F-096
- ✅ `## Source files` added to `problems/sync-functions-dead-code.md`, `problems/tanstack-svelte5-incompatibility.md`, `sources/todos.md`

**No issues found**:
- No broken wikilinks
- No orphan pages (all reachable from index.md)
- All mkdocs: paths point to real files
- Log format: all entries well-formed
- Thin pages: all under-25-line pages are planned/idea features (appropriate)
- Concept pages (daily-point-policy, backend-only-calculations, fifo-runtime-decision): substantive and accurate
## [2026-04-24] file | I-bis #24 v4 — `/prices/current` has a persistence side-effect
Filed lesson learned from final iteration of I-bis #24 (Auto-refresh mirato post-sync).
Root cause: `AssetSourceManager.get_current_prices_bulk` upserts today's OHLC to
PriceHistory (F.2 + F.3), so chaining `/current` + `/sync` for the same asset always
yields empty `changed_points` — the changes already happened on `/current`.
Created: [[concepts/prices-current-side-effect]] (cross-cutting API contract),
[[problems/prices-current-sync-chain-empty-delta]] (specific anti-pattern bug).
Updated: index.md (Concepts + Problems tables).

---

## 2026-04-24 — Phase 07 Part 2–3 Ingest (Transactions system final)

Ingested all remaining Phase 07 plan files (Part 2, Part 3, Closure, Closure_2 + BlockG).
This completes the documentation of the core transaction system architecture.

**Sources ingested (4 new source pages):**
- [[sources/phase07-part2-brim-revision]] — BRIM Revision 2 (parser-only)
- [[sources/phase07-part3-api-consolidation]] — multi-broker atomic TX, transfer semantics, currency simplification
- [[sources/phase07-part3-closure]] — Blocco I decisions, I-bis queue, #R6-4 scheduled investment wipe
- [[sources/phase07-part3-closure2]] — Batch 4 (saveWithRetry adoption), BlockG test coverage (76.05%)

**Decisions created (4):**
- [[decisions/brim-parser-only]] — BRIM is a parser; no commit endpoint, no asset events
- [[decisions/multi-broker-atomic-tx]] — bulk endpoints not broker-scoped, multi-broker atomic
- [[decisions/tx-link-uuid-semantics]] — TRANSFER/DEPOSIT/WITHDRAWAL link_uuid rules + promote endpoint
- [[decisions/price-currency-hard-reject]] — hard 400 on mismatch, 409 on currency change with prices

**Concepts created (1):**
- [[concepts/savewithretry-frontend-pattern]] — unified modal save helper adopted in 8+ modals

**Features updated:**
- [[features/F-012]] — BRIM Revision 2: parser-only, plugin_version, parse_is_stale, bulk_upsert_events rename
- [[features/F-046]] — status→implemented, multi-broker bulk endpoints, validate/suggest/promote
- [[features/F-049]] — commit via /transactions/bulk (not BRIM-specific), parse_is_stale UI
- [[features/F-051]] — status→in-progress, events/suggest endpoint documented

**Registry updated:**
- F-046: `in-progress` → `implemented`
- F-051: `planned` → `in-progress`

**Wiki page count**: ~176 pages (170 + 4 sources + 4 decisions + 1 concept - 3 from prev pass)
