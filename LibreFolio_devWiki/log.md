# devWiki Log

> Append-only chronological record of all wiki operations.
> Format: `## [YYYY-MM-DD] {operation} | {title}`
> Parse: `grep "^## \[" log.md | tail -10`

## [2026-07-01] ingest | Phase 09 — Portfolio Engine 3-Pool Refactor (commit 39106380)

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/` @ HEAD:`d27902b7`.
Major engine refactor: inline WAC single-pass (eliminates N×M `compute_wac_iterative` DB calls), 3-pool K/R/W event-driven state machine with SELL fix (read WAC before reducing pool → correct K/R split on full exit), LAST_BUY_PRICE(V(u)) as price fallback, pre-frame/frame separation (no market eval before t0), range-aware blob cache with fingerprint keys. Supporting analysis docs: architectural analysis, implementation status, P&L breakdown, asset contribution gap analysis.
Created: [[sources/phase09-portfolio-engine-3pool-refactor]], [[concepts/inline-wac-computation]], [[concepts/pre-frame-frame-separation]].
Updated: [[entities/portfolio-engine]] (inline WAC, fallback chain, blob cache, 3-pool, history), [[entities/portfolio-service]] (+612 lines noted, tech debt updated), [[concepts/3-pool-cash-model]] (full K/R/W event-driven semantics, SELL fix, reconciliation invariant).

## [2026-06-30] ingest | Group 1 — Phase 07 PlanD-D1D2: Split/Promote Full Stack

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/PlanD-D1D2/README.md` @ git:`8f363d79`.
Batch ingest of sub-plan bundle (D1 backend batch pipeline, D2 frontend PromoteMergeModal, Centralize payload layer, 4 bugfix rounds). Key insights: `_PromoteCandidate` duck-typing, endpoint elimination (no standalone /split or /promote), centralized txPayloadHelpers.ts + txCommitApi.ts (9 callsites), PMC override UX.
Created: [[sources/phase07-pland-split-promote]], [[decisions/batch-only-split-promote]], [[concepts/centralized-tx-payload]].

## [2026-06-30] ingest | Group 2 — Phase 07 Part 5: BRIM Import Wizard v5

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte5/plan-phase07Part5-v5-ImportWizard.prompt.md` @ git:`5592f299`.
Major paradigm shift v4→v5: single-file breadcrumb → multi-file 4-step stepper (z:70 wide modal). Schwab parser added. ImportTodo signals and WorkspaceIntent pattern documented. 4-level data pipeline captured.
Created: [[sources/phase07-part5-import-wizard-v5]], [[entities/import-wizard-modal]], [[concepts/workspace-intent-pattern]], [[concepts/import-todo-signals]], [[decisions/import-wizard-v5-paradigm]].

## [2026-06-30] ingest | Group 3 — Phase 07 Standalone: PWA Mobile Optimizations

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Standalone/plan-pwa-mobile-optimizations.prompt.md` @ git:`66f56432`.
Archive re-anchor for PWA plan (already ingested as r2-parallel-features-pwa-borsa-fx). Two additional bugfixes captured: Svelte 5 runes reactivity fix for HelpMenu, and beforeinstallprompt race condition fix with early-capture in app.html.
Created: [[sources/phase07-standalone-pwa]].
Updated: [[features/F-098]] (cross-reference only, status remains implemented).

## [2026-06-30] ingest | Group 4 — Phase 08: Market Data Scheduler Backend

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-08-subplan/plan-phase08Step1-2-backend.prompt.md` @ git:`5592f299`.
Embedded FastAPI scheduler daemon with leader election (psutil + file-lock), 2 job types (current-price + history-sync), 5 new settings, fetch_interval column removal, atomic state persistence, JSONL log. Test checkpoint covers Phase 07 Part 5 + Phase 08.
Created: [[sources/phase08-scheduler-backend]], [[entities/market-data-scheduler]].

## [2026-06-30] ingest | Group 5 — Phase 09: Portfolio Engine + Dashboard (Milestone 2)

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md` @ git:`39106380`.
Major: 4-layer portfolio architecture (Engine→Service→API→Store), 4-stage engine pipeline, 3-pool cash model, MWRR double-counting bug fix (initial_nav correction), unified /portfolio/report endpoint, L2 TTL cache, P&L breakdown analysis. 6 known issues documented.
Created: [[sources/phase09-portfolio-engine-dashboard]], [[entities/portfolio-engine]], [[entities/portfolio-service]], [[concepts/3-pool-cash-model]], [[concepts/portfolio-report-unified]], [[decisions/mwrr-boundary-fix]].

## [2026-06-30] ingest | Group 6 — Wiki Audit 2026-06-18

Sources: `wiki_audit_2026_06_18/audit_transactions.md`, `audit_backend_infra.md`, `audit_assets_brokers_brim.md` @ git:`010ec3ed`.
Two critical corrections: WorkspaceIntent is frontend-only Svelte 5 pattern (not backend multi-tenancy); test_runner is now a modular package at scripts/test_runner/ (18 modules, not monolithic .py file). New mkdocs: runner_architecture.md, scheduler.md, transaction-draft.md update. lf-screenshot-carousel component created.
Created: [[sources/wiki-audit-2026-06-18]], [[entities/test-runner]].
Updated: [[concepts/workspace-intent-pattern]] (new page with correct categorization).

## [2026-06-30] ingest | Group 7 — Phase Final Bug Report 2026-06-25

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-final-subplan/bug_vari_report20260625.md` @ git:`1400451d`.
Static code analysis on Docker build: 5 bug categories. Critical: broker icon race condition (3 pages), import wizard oncreated path skips identifier prompt, BulkModal toolbar clipped by overflow-y:auto after import.
Created: [[sources/phase-final-bugs-2026-06-25]], [[problems/broker-icon-race-condition]], [[problems/import-wizard-identifier-prompt]], [[problems/bulk-modal-sticky-z-index]].

## [2026-06-30] ingest | Group 8 — CI/CD Release Pipeline

Source: `.github/workflows/release.yml` @ git:`a688bcb9` (commits a688bcb9..b79735e2).
GitHub Actions full automated pipeline: Node 24, Vite 7.3.5, package-lock.json, Docker :test tag, Playwright 8 workers + networkidle, screenshot cache, crypto.randomUUID polyfill.
Created: [[sources/ci-release-pipeline-2026-06]], [[concepts/ci-release-pipeline]].



**Created** (1 source page):
- [[sources/r3-sp-d-formmodal-wac-fx-chain]]

**Created** (3 decision pages):
- [[decisions/wac-target-currency-last-acquisition]] — WAC target = last acquisition's currency (deterministic)
- [[decisions/fxsyncmodal-parent-ownership]] — Parent owns FxSyncModal, child calls onOpenFxSync
- [[decisions/blur-detection-format-string-comparison]] — Compare formatDecimalForDisplay() strings for blur detection

**Updated** (2 feature pages):
- [[features/F-097]] — status: in-progress → **implemented** (all walktests pass, E2E added)
- [[features/F-048]] — title updated to reflect SP-D completion

**Key decisions extracted**:
- WAC target currency = most recent acquisition's currency (not majority)
- cost_basis_override is Currency object {code, amount}, sentinel {code, "0"} for auto hint
- FxSyncModal reuse pattern: parent owns modal, child calls onOpenFxSync prop
- Blur detection: compare formatDecimalForDisplay() strings (not numeric tolerance)
- useValidateScheduler: manual triggers bypass antiBounce 10s
- PromoteMergeModal WAC section was dead code → removed
- FX missing does NOT force manual mode (informative error only)

## [2026-06-01] ingest | Batch 4 — Five Independent Mini-Plans

Ingested 5 independent plans (BackendLogAudit, CandlestickChart, FxRangeHelper, LazyImageCache, RsiSignalBands) — all ✅ DONE 2026-06-01.

**Created** (1 source page):
- [[sources/independent-batch-2026-06-01]]

**Created** (3 concept pages):
- [[concepts/log-level-policy]] — 6-level hierarchy, TRACE registration, structlog patch
- [[concepts/image-preview-cache-pattern]] — objectUrl cache, size-based reuse, no ref counting
- [[concepts/fx-range-helper-pattern]] — ensureFxRangeLoaded centralization (DRY 6→1)

**Updated** (4 feature pages):
- [[features/F-076]] — status: planned → implemented (log policy + TRACE)
- [[features/F-080]] — status: planned → implemented (candlestick OHLCV chart)
- [[features/F-086]] — status: planned → implemented (image preview cache)
- [[features/F-039]] — added RSI zone-driven band style details

## [2026-06-02] ingest | Batch 2 — SP-C Bugfix Chain (11 plans: BulkModal + WAC Preview)

Ingested 11 completed plans from SP-C sub-plan (Frontend BulkModal + Suggest UX + WAC bugfixes) @ anchor `84f8bd07`.

**Created** (1 source page):
- [[sources/r2-sp-c-bugfix-chain]] — Combined source covering all 11 plans in the SP-C bugfix dependency chain

**Created** (2 problem pages):
- [[problems/wac-feedback-loop]] — WAC recalc → field update → infinite loop (resolved via cost_basis_mode)
- [[problems/clone-link-uuid-duplication]] — Clone paired rows from DB didn't generate link_uuid (resolved via type-rule check)

**Created** (2 concept pages):
- [[concepts/paired-partner-architecture]] — pairedWith, getPartnerOp, visibleOps, resolveFormItems pattern
- [[concepts/stateless-preview-pattern]] — Controlled components for computed values (WacPreviewSection)

**Created** (1 decision page):
- [[decisions/wac-inline-validate-commit]] — WAC computed in validate/commit, standalone endpoint eliminated from editing flow

**Updated**:
- [[features/F-097]] — Added bugfix chain status history, dead ends, implementation notes (feedback loop, stateless preview, link_uuid)
- [[features/F-048]] — Added SP-C bugfix chain references and related problems/concepts
- `raw/ingest-registry.md` — 11 entries added
- `index.md` — 1 source, 2 problems, 2 concepts, 1 decision added

Key patterns extracted:
1. **Feedback loop prevention**: Separate "what to compute" (mode) from "computed result" (value) — never let output be input trigger
2. **Paired partner architecture**: `pairedWith` for UI, `link_uuid` for backend — two separate linkage mechanisms
3. **Stateless preview**: Components displaying computed data should be controlled (no internal state)
4. **Fingerprint invalidation**: Hash material fields only — prevents unnecessary recalculation
5. **link_uuid promotion**: Decision based on target type needs, not source op type
6. **Post-flush WAC**: Compute on actual DB state in same transaction — eliminates adapter layer

## [2026-06-02] ingest | Batch 3 — Parallel Features (PWA, Port 60/40, Borsa Italiana, FX Fix)

Ingested 4 parallel-terminal features/fixes (no formal plan chains) @ anchor `84f8bd07`.

**Created** (1 source page):
- [[sources/r2-parallel-features-pwa-borsa-fx]] — Combined source covering PWA support (4 commits), Port 60/40 migration, Borsa Italiana provider, FX provider removal fix

**Created** (2 feature pages):
- [[features/F-098]] — NEW: Progressive Web App (PWA) — offline fallback, install button, iOS safe-area, theme-color sync
- [[features/F-099]] — NEW: Borsa Italiana Asset Provider — stocks, bonds, ETFs from borsaitaliana.it

**Created** (1 decision page):
- [[decisions/port-6040-scheme]] — All ports migrated from 8000/8001/8002 to 6040/6041/6042 ("60/40 rule" mnemonic)

**Updated**:
- [[features/registry]] — F-098 + F-099 added (Infrastructure / Assets domains)
- `raw/ingest-registry.md` — 5 entries added (PWA commits + plan, port commit, Borsa commit, FX fix commit)
- `index.md` — 2 feature pages, 1 source page, 1 decision added

Key observations:
1. **Provider pattern maturity**: Borsa Italiana is the 5th provider following `@register_provider` pattern — pattern now proven robust
2. **PWA = no-cache strategy**: financial apps prioritize data freshness over offline access — intentional design choice
3. **FX sentinel edge cases**: MANUAL auto-reinstate logic now handles all deletion scenarios including bulk-remove-all

## [2026-06-01] ingest | R2 Walktest Feedback Round — Batch 1 (WAC feature, 4 plans)

Ingested 4 source files from `PlanD_SplitPromoteFullStack/` R2 WAC sub-plans @ anchor `84f8bd07`.

**Created** (4 source pages):
- [[sources/r2-walktest-feedback-master]] — Master plan: 18 steps, 5 sub-plans (SP-A✅ SP-B✅ SP-C✅ SP-D⏳ SP-E🔲); cost_basis→Currency, WAC with FX, AssetEvent picker, store-first
- [[sources/r2-sp-a-cost-basis-wac]] — Backend: cost_basis_override→Currency, WACResult/WACConversionInfo schemas, compute_weighted_avg_cost with FX, recalc-wac endpoint (commit `92f4b1ba`)
- [[sources/r2-sp-b-backend-tests]] — Tests: 13 WAC API tests (WAC-1→WAC-13) + helpers; self-contained per-test isolation (commit `473d2611`)
- [[sources/r2-sp-c-bulkmodal-suggest-ux]] — Frontend: toolbar alignment, split preview fix, suggest overhaul (subtractive filter, human-readable, lightbulb), PromoteMergeModal simplified, ActionModal enhanced

**Created** (1 feature page):
- [[features/F-097]] — NEW: WAC — Weighted Average Cost (cross-currency, auto-calc on TRANSFER)

**Created** (1 decision page):
- [[decisions/cost-basis-currency-object]] — cost_basis_override from SafeDecimal to Currency {code, amount}; breaking change, no backward compat

**Updated**:
- [[features/F-048]] — 3 new status history entries (R2 SP-A/B/C), deferred items updated
- [[features/registry]] — F-097 added (fullstack, in-progress)
- `raw/ingest-registry.md` — 4 entries added
- `index.md` — F-097 in feature list, decision + 4 source pages added

Key architectural insights:
1. **Currency object over bare decimal**: unambiguous currency association enables multi-currency WAC
2. **Fail-safe WAC**: even one failed FX conversion → wac=None, never silently wrong
3. **Transient wac_info**: computed at commit time, not persisted — changes when FX rates update
4. **Target currency heuristic**: majority among TX → asset currency on tie → alphabetical

## [2026-05-31] ingest | Phase 07 Part 4 Round 6 — Plan D chain (7 files: split/promote full stack)

Ingested 8 source files: PlanB23 (registry backfill only, source page already existed), PlanD master @ `b0e223c0`, PlanD1 @ `666059b5`, PlanD2 @ `db7264ce`, D2-bugfix1 @ `fdf00d4b`, D2-bugfix2 @ `eb9b8ae2`, D2-bugfix3 @ `78f44497`, D2-bugfix4 @ `ce7344a1`.

**Created** (7 source pages):
- [[sources/phase07-part4-round6-pland-split-promote-master]] — Master plan: split/promote full stack integration into batch pipeline; D1✅ D2✅ bf1-4✅ D2-round2⏳; D3 absorbed into D2-bf3
- [[sources/phase07-part4-round6-pland1-backend-batch-suggest]] — Backend: TXMixedBatch + splits[]/promotes[], endpoint elimination (DD2), promote-suggest, consumed_link_uuids (DD4), _PromoteCandidate, 18 tests
- [[sources/phase07-part4-round6-pland2-frontend-split-promote]] — Frontend: PromoteMergeModal 3-column diff, BulkModal split/promote actions, Main Table promote migration to batch, suggest green banner
- [[sources/phase07-part4-round6-pland2-bugfix1]] — 21 bugs: BulkModal first-open race (getTypeRule FALLBACK_RULE), promote toolbar not appearing, findPromoteMatch constraint enrichment, collapse post-promote
- [[sources/phase07-part4-round6-pland2-bugfix2]] — Split preview editability (corrects DD-BF1), pipeline reorder (splits before updates), TXBatchResultItem.id→ids[], payload fixes
- [[sources/phase07-part4-round6-pland2-bugfix3]] — Biggest round: split schema {id_a,id_b}, suggest banner redesign, E2E (absorbed D3 scope), TransactionActionModal unification, cash sign fix
- [[sources/phase07-part4-round6-pland2-bugfix4]] — PMC auto-calc (compute_weighted_avg_cost), cost_basis_override only on receiver, promote-suggest constraint fix (None amount/qty), link_uuid sync, delta-days slider

**Updated** (1 decision):
- [[decisions/cash-transfer-split-promote]] — MAJOR: standalone `/split` and `/promote` endpoints eliminated (DD2); split/promote now exclusively via batch pipeline `splits[]+promotes[]`; added promote-suggest, consumed_link_uuids, PMC auto-calc

**Updated** (3 feature/connection pages):
- [[features/F-048]] — title updated (now "Form / Bulk / Delete / Promote / Split"), layer changed to fullstack, 8 new status history entries (D1→D2→bf1→bf2→bf3→bf4), PromoteMergeModal section, Split/Promote in BulkModal section, PMC Auto-Calc section, 10 new source files
- [[features/registry]] — F-048 title + layer updated
- [[connections/transactions-connections]] — header updated with Plan D completion status

**Registry**: 8 entries added to `raw/ingest-registry.md` (PlanB23 as `uncommitted` backfill, 7 PlanD files with commit hashes)
**Index**: 7 source pages + 1 decision summary updated in `index.md`

Key architectural insights documented:
1. **Endpoint elimination** (DD2): `/split` and `/promote` never used in production → removed entirely. All mutations go through unified `execute_batch` pipeline.
2. **consumed_link_uuids** (DD4): prevents Step 6 link resolution from re-processing link_uuids already consumed by promotes in Step 5c. Critical for atomic batch promote-and-create flows.
3. **Pipeline reorder** (DD-R2.2): `deletes(3) → splits(3b) → updates(4) → creates(5) → promotes(5c) → links(6) → balance(7)` — splits before updates enables "split + edit post-split" in same batch.
4. **PMC auto-calc**: `compute_weighted_avg_cost()` auto-fills `cost_basis_override` on TRANSFER receiver when null. Weighted average of BUY prices + incoming TRANSFER cost_basis at source broker.
5. **D3 absorbed**: E2E test scope originally planned as separate D3 sub-plan was absorbed into D2-bugfix3.

## [2026-05-30] ingest | Phase 07 Part 4 Round 6 Plans C2 + C2R2 — Bugfix, Pair Validation, MockFX, Contextual Validate

Ingested 2 new plan files (C2 @ `6aac0dce`, C2R2 @ `f9f3bec2`). Verified 8 already-ingested plans from the same batch — no re-ingest needed; existing pages accurate.

**Created** (2 source pages):
- [[sources/phase07-part4-round6-planc2-bugfix-pair-validation]] — 6 bugs fixed, pair desc/tags validation, clone paired, picker hideActions, bulk toast, UC 58%→92%, Docker non-root, font self-hosted, FX fallback, classification race
- [[sources/phase07-part4-round6-planc2r2-regressions-mockfx]] — MockFX providers, auto-populate removal, DistributionEditor fix, contextual validate, end-of-day balance confirmation, 8 balance walk tests, 3 FX fallback tests, 3 asset classification E2E

**Created** (4 decisions):
- [[decisions/pair-description-tags-validation]] — linked pairs must have identical desc+tags
- [[decisions/auto-populate-removal]] — metadata flow frontend-driven (probe→diff→PATCH)
- [[decisions/formmodal-contextual-validate]] — FormModal sends entire bulk context to /validate
- [[decisions/end-of-day-balance-check]] — intra-day order irrelevant, end-of-day aggregation

**Created** (1 problem):
- [[problems/fx-multi-route-no-fallback]] — FX sync used only primary route, no fallback to ECB/FED/SNB

**Updated**:
- [[features/F-048]] — Plan C2/C2R2 entries in status history, contextual validate, clone paired, picker hideActions, bulk toast, balance walk, 4 new related_decisions
- index.md, raw/ingest-registry.md

**Verification of already-ingested plans** (8 files): All source pages for Round 6 ContextMenu, Plan A, Plan B, Plan B1, Plan B23, Plan B23 Appendix, Plan C, Plan C3 confirmed accurate with no contradictions. Plan C3 page verified — no updates needed (correctly documents PendingOp as successor to C2R2 work).

Key architectural progression documented: C2 (bugfix + pair validation + infrastructure) → C2R2 (MockFX + auto-populate removal + contextual validate + balance confirmation) → C3 (PendingOp tagged union).

## [2026-05-30] ingest | Phase 07 Part 4 Round 6 Plan C3 — PendingOp Refactor
Ingested from `RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC3_PendingOpRefactor.prompt.md`.
**Created**: [[sources/phase07-part4-round6-planc3-pendingop-refactor]], [[decisions/pendingop-tagged-union]].
**Updated**: [[features/F-048]] (PendingOp tagged union, factory functions, 3 new E2E tests, data-action-id), [[concepts/txstore-pattern]] (PendingOp model updated to final implementation), [[concepts/e2e-data-testid-rule]] (data-action-id pattern).
Key insight: DraftRow→PendingOp completes 80%→100% of txStore architecture. Zero-copy originals + tagged discriminator + derived status make Plan D (Split/Promote) trivial (~10 LOC per action). `data-action-id` establishes i18n-resilient E2E selectors for DataTable row actions.

## [2026-05-29] ingest | Phase 07 Part 4 Round 6 Plan C — txStore Refactor
Ingested from `RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC_TxStoreRefactor.prompt.md`.
**Created**: [[sources/phase07-part4-round6-planc-txstore-refactor]], [[concepts/txstore-pattern]], [[decisions/txstore-single-source-of-truth]].
**Updated**: [[features/F-048]] (txStore as single source of truth, WorkspaceIntent pattern, PendingOp model, interface deduplication in types.ts, -30% LOC).
Key insight: 5 recurring bug categories (17+ instances) all rooted in 3-copy prop cascade; eliminated structurally by centralized store. Piano D (Split/Promote) now trivial.

## [2026-05-29] ingest | Phase 07 Part 4 Round 6 Plan B23 Appendix 1 — UI Polish
Ingested from `RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB23_Appendix1_UIPolish.prompt.md`.
**Created**: [[sources/phase07-part4-round6-planb23-appendix1-ui-polish]].
**Updated**: [[features/F-048]] (structured delete toast, responsive footer buttons, row background tints, viewer-only guard on bulk actions, conditional "Reset all", "Reset selected" toolbar button).
Note: Execution order in master plan updated — old Piano C (Split/Promote) renamed Piano D; txStore refactor inserted as Piano C prerequisite.

## [2026-05-27] ingest | Phase 07 Part 4 Round 6 Plan B23 — Bulk Delete via BulkModal + Mode Removal
Ingested Plan B23 + 3 source files (TransactionBulkModal.svelte, TransactionDeleteModal.svelte, +page.svelte transactions).
**Created**: [[sources/phase07-part4-round6-planb23-bulk-delete]], [[decisions/bulkmodal-mode-removal]].
**Updated**: [[features/F-048]] (mode-less architecture, delete flow, enriched DeleteModal, PickerModal guard),
[[features/F-047]] (BulkDeleteLinkedPairModal removed, bulkMode state removed),
[[connections/transactions-connections]] (Round 6 status), [[domains/transactions]],
[[features/registry]] (F-048 title), index.md.
Key changes: (1) BulkDeleteLinkedPairModal eliminated — bulk delete now via BulkModal with `initialStatus:'delete'`;
(2) `mode` prop removed from BulkModal — now mode-less, each row infers create/edit from `tx.id > 0`;
(3) TransactionDeleteModal enriched: 3 layouts, validate-now, error banners with resolveIssueMessage, success toast with icons;
(4) PickerModal guard for non-editable rows; (5) Confirm edit on deleted row.

## [2026-05-27] query | AssetMatchingWizard / asset search / Phase 6 Step 5 status
Synthesized answer from: F-028, F-049, F-012, domains/assets, workflows/brim-import-flow, workflows/asset-onboarding-flow, connections/assets-connections, sources/phase06-step3-rounds, phase-06-assets.md plan.
**Key finding**: AssetMatchingWizard.svelte was never built — Phase 6 Step 5 is still ⏳. The component exists only in plans and wiki references but has zero source files in the codebase. AssetSearchAutocomplete.svelte (F-028) exists and works for asset creation, but the 3-step matching wizard (DB search → provider search → manual create) for BRIM import was interrupted before Phase 07 Part 4 bugfix rounds.

## [2026-05-26] file | SafeDecimal — Preventing Scientific Notation in JSON Responses
Filed [[concepts/safe-decimal-pattern]]. `SafeDecimal` is an `Annotated[Decimal, PlainSerializer]`
type that forces `format(v, 'f')` during JSON serialization, preventing Python's `str(Decimal)`
from emitting scientific notation (`"1.29E+5"`) which breaks frontend Zod validators.
3-layer approach: type definition in `common.py`, `Currency.amount` adoption, per-schema migration.
Incrementally adopted in brokers.py + transactions.py; prices.py/fx.py/brim.py still pending.
Updated: index.md.

## [2026-05-26] file | Static export of constant metadata at compile-time (deferred)
Filed [[decisions/static-metadata-export]]. Deferred to Phase 8+: extracting constant
metadata (TX_TYPE_METADATA, asset types, currency codes) as static JSON at `dev.py api sync`
time instead of serving via runtime endpoints. Current cost is 1 req/session — not worth
the sync-pipeline + store refactor effort until more constant-data endpoints accumulate.
Related: [[decisions/server-driven-type-rules]].

## [2026-04-25] lint | wiki-lint pass #5 — post Phase 7 Parts 1+2+3 ingest reconciliation

**Scope**: full health-check after Phase 7 Part 3 closure (backend coverage 87.06%,
2 production bugs filed, Policy D destructive wipe in place, new backup router,
ErasableNumberCell typing fix). Workspace HEAD = `a61b0dfa` (matches latest re-anchor
in `raw/ingest-registry.md`).

### Drift detection — ✅ clean

All 17 unique git-hashes in `raw/ingest-registry.md` resolve in current history.
Phase 7 sources (Parts 1/2/3 + Closure + Closure_2) re-anchored at `a61b0dfa` =
HEAD; `git diff a61b0dfa HEAD -- {phase07 paths} = 0 lines`. No source drift.

### Prioritized repair list

| # | Sev | Page | Problem | Action |
|---|-----|------|---------|--------|
| L5-01 | P0 | `connections/transactions-connections.md` | Header "Phase 7 — in progress (Part 1✅, Part 2✅, Part 3–5 TODO)" + 7-row gap table all stale; Parts 1–3 now ✅ DONE | rewrote header + replaced gap table with closed-gap table |
| L5-02 | P0 | `features/F-051.md` | Source files & layer breakdown referenced `Transaction.related_asset_event_id`; **code has `Transaction.asset_event_id`** (models.py L580/L659) | renamed all references to `asset_event_id`; updated status to `implemented`; added Policy D link |
| L5-03 | P0 | `domains/transactions.md` | F-051 row "planned"; "Known problems" still listed Phase 7 gaps as open (access control, multi-broker atomic, plugin_version) — all closed in Part 2/3 | updated F-051 row→`implemented`, rewrote "Known problems" to reflect closed gaps + add Policy D context |
| L5-04 | P1 | `problems/assets-wipe-error-attr-mismatch.md` | Reported 2 fixed sites; **a third sibling `e.code` reference still lives at `assets.py:976` (bulk_upsert_events)** — code wins → annotate as residual | added "Residual occurrence" section; flagged for code-side follow-up |
| L5-05 | P1 | `decisions/policy-d-currency-wipe.md` | Missing cross-ref to `features/F-073` (Backup & Restore) — backup endpoints belong to F-073 | added `F-073` to `related` + body |
| L5-06 | P1 | `entities/backup-router.md` | Missing cross-ref to `features/F-073` | added F-073 in `related` + body |
| L5-07 | P1 | `features/F-073.md` | No `related_decisions`/`related_problems`; doesn't mention Policy D or `entities/backup-router` | added related_decisions + cross-refs |
| L5-08 | P1 | `decisions/price-currency-hard-reject.md` | I.3 (409 on currency change with prices) doesn't link to its destructive successor Policy D | added "When the user accepts the 409" pointer + `related: policy-d-currency-wipe` |
| L5-09 | P1 | `problems/asset-currency-mismatch.md` | Older "per-row currency column" page — silent on the fact that I.2 hard-reject + Policy D now formalise a stricter model on top of it | added "Superseded-in-spirit" header + cross-refs to I.2/I.3/Policy D |
| L5-10 | P1 | `domains/assets.md` | No mention of Policy D destructive wipe or backup-router despite being the asset domain owner | added "Asset currency change (Policy D)" subsection + cross-refs |
| L5-11 | P2 | `wiki/features/F-049.md`, `F-047.md`, `F-046.md` | mostly current; only minor stale gap-analysis bullets — covered transitively by L5-01 / L5-03 | none (P2, deferred) |

### Index drift

`index.md` Problems/Decisions/Entities tables reflect the on-disk state correctly
post Phase 7 Part 3 ingest. F-051 status row was the only case where index
implicitly inherited the page's stale `in-progress` — now reconciled via L5-02.

### Orphan detection — ✅ none

Every wiki/* page is reachable from `index.md` directly or transitively
(domains → features → connections → decisions/concepts/problems). The 4 new
Phase-7 pages (`problems/assets-wipe-error-attr-mismatch`, `problems/babel-currency-symbol-echo`,
`decisions/policy-d-currency-wipe`, `entities/backup-router`) are all listed in
`index.md` and now also linked from at least 2 sibling pages each (post-L5).

### Contradiction scan — beyond fixes above

- `e.code` vs `e.error_code`: only the wiki had stale claims; current code
  uses `e.error_code` in the 2 wipe handlers. Residual `e.code` at line 976
  (bulk_upsert_events) is a **code-side latent bug** — annotated, not silently
  preserved (L5-04).
- "Soft-skip currency mismatch" appears nowhere in the wiki as the *current*
  behaviour — only as historical context inside `price-currency-hard-reject.md`
  and Part 3 source page (correctly framed as "old behaviour").

### Knowledge condensation

- Pages **rewritten in place**: 5 (transactions-connections, F-051, domains/transactions, asset-currency-mismatch, price-currency-hard-reject)
- Cross-ref additions: 6 pages received new `related:` + body links
- Sections added: 4 ("Residual occurrence", "Asset currency change (Policy D)" in domains/assets, "Superseded-in-spirit" in asset-currency-mismatch, "Closed Phase 7 gaps" in transactions-connections)
- Sections deleted: 1 (the now-misleading "Phase 7 Gap Analysis (from plan)" 7-row TODO table in transactions-connections)
- Pages deleted: 0 (all stale content was condensed/annotated, not removed — historical signal preserved with "Superseded" framing)
- Concept debt scanned: `editbuffer-pattern` (concept) + `data-editor-unification` (decision) overlap is intentional (mechanism vs rationale). FX-related concepts (`daily-point-policy`, `prices-current-side-effect`) and BRIM-related decisions (`brim-broker-scoped`, `brim-fake-asset-id`, `brim-parser-only`) cover distinct angles; no merges performed.

**Total touched**: 11 wiki pages + log.md + this entry. **0 new pages created**, **0 pages deleted**.

---

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

## [2026-04-25] ingest | phase07 Parts 1/2/3 — re-anchor + G-batch6/G-batch7 closure

Re-ingested Phase 7 Parts 1, 2, 3 (incl. Closure + Closure_2 + Batch4d + BlockG)
after the plans were archived from `RoadmapV4_UI/plan-phase07-transaction-Part*.md`
into `RoadmapV4_UI/phases/phase-07-subplan/Parte{1,2,3}/`. All Phase 7 Parts 1–3
are now ✅ DONE.

**Re-anchored sources** (path + git_hash → `a61b0dfa`, status → ✅ DONE):
- [[sources/phase07-transactions]] — Parte1/Part1.md
- [[sources/phase07-part2-brim-revision]] — Parte2/Part2.prompt.md
- [[sources/phase07-part3-api-consolidation]] — Parte3/Part3.md
- [[sources/phase07-part3-closure]] — Parte3/Part3_1_Closure.md
- [[sources/phase07-part3-closure2]] — Parte3/Part3_1_Closure_2.prompt.md (+ 3 companions)

**Delta surfaced** (new content not in previous ingest):
- Backend coverage **76.05% → 85.34% → 87.06%** in 2 days (G-batch6 + G-batch7); from ~57% at start of Phase 7
- 2 production bugs discovered by the new tests:
  - [[problems/assets-wipe-error-attr-mismatch]] — `e.code` → `e.error_code` (HTTP 500 → 404)
  - [[problems/babel-currency-symbol-echo]] — `normalize_currency` echoed garbage; strict pycountry lookup
- Policy D destructive wipe semantics formalised (commit `8fc018ab`):
  - [[decisions/policy-d-currency-wipe]] — created
  - Distinguishes from `#R6-4` selective wipe (manual events preserved there)
- New backup router `/api/v1/backup`:
  - [[entities/backup-router]] — created
  - Endpoints: `/backup/asset/{id}/{prices,events}` + `/backup/fx/{base}/{quote}/rates`
  - Replaces legacy `/assets/{id}/prices/export`
- I-bis #24 `changed_points` cap-500 + live-poll merge (commit `ddb1fcfb`) — refined in [[sources/phase07-part3-closure2]]
- ErasableNumberCell `$state<number | null>` fix (commit `83328b6b`) — captured in closure_2

**Files corrected** (previous ingest had wrong info):
- [[sources/phase07-part3-closure]] — old "R3-3 Policy D" line incorrectly claimed
  `/api/v1/system/{export,import}` as the backup. Replaced with the actual `backup.py`
  router + Policy D destructive wipe description.

**Cross-links added/strengthened**: F-012 (BRIM), F-046 (TX bulk), F-051 (TX↔AssetEvent),
F-056 (FIFO runtime — transaction preservation rationale), F-019/F-020 (FX),
[[entities/db-models]], [[entities/api-router]],
[[concepts/savewithretry-frontend-pattern]], [[decisions/price-currency-hard-reject]].

**Pages created**: 2 problems + 1 decision + 1 entity = 4 new wiki pages.
**Pages updated**: 5 source pages + index.md + ingest-registry.md.

---

## [2026-04-28] ingest | Phase 07 Part 4 — /transactions UI + Round 1 + Round 2

Sources:
- `plan-phase07-transaction-Part4.prompt.md` @ git:`dcb91929`
- `plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md` @ git:`444b2d16`
- `plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md` @ git:`29898623`

Phase 7 Part 4 completes the `/transactions` frontend page (F-047 → **implemented**). Round 1 fixed 82+ issues across 14 sub-rounds, establishing 100% client-side filtering (W28 decision). Round 2 introduced `createEntityStore<T>()` factory, `brokerStore`, conditional pair-grouping, per-currency sliders, and `TxTypeIconCell`. F-048 Staging Modal moved from `planned` → **in-progress** (manual `create-many`/`edit-many` done; BRIM mode deferred to Part 5). Critical deviation: original plan had server-side filters on `GET /transactions` → replaced by full client-side filtering; `highlight_id` URL param removed in favour of DOM-direct pulse animation.

**Created**:
- [[sources/phase07-part4-transactions-ui]]
- [[sources/phase07-part4-round1]]
- [[sources/phase07-part4-round2]]
- [[concepts/entity-store-pattern]]
- [[concepts/always-pair-adjacent]]
- [[concepts/opportunistic-cache-merge]]
- [[decisions/transactions-client-side-filtering]]
- [[decisions/datatable-tooltip-custom-cell]]
- [[problems/svelte5-effect-read-write-loop]]
- [[problems/babel-currency-symbol-locale]]
- [[problems/datatable-filter-options-disappear]]

**Updated**:
- [[features/F-047]] (in-progress → implemented, full component inventory)
- [[features/F-048]] (planned → in-progress, manual mode done)
- [[features/registry]] (F-047/F-048 status rows)
- [[domains/transactions]] (F-047/F-048 status, Part 4 context)
- [[connections/transactions-connections]] (header + gap table Part 4 closure)
- index.md, ingest-registry.md

**Pages created**: 3 sources + 3 concepts + 2 decisions + 3 problems = 11 new wiki pages.
**Pages updated**: 5 existing pages + index.md + ingest-registry.md.

---

## [2026-04-28] lint | Wiki lint pass #6 — post Phase 07 Part 4 ingest

**Scope**: health check after Phase 7 Part 4 ingest (11 new pages, 7 updated). Focus: stale endpoint references, F-047/F-048 status drift, orphan pages, index drift.

**Issues found**: 4 (1 high, 2 medium, 1 low)
**Issues repaired**: 3 (1 high, 2 medium)
**Deferred**: 1 (low)

### 🔴 High — Repaired

| # | Page | Problem | Fix |
|---|------|---------|-----|
| L6-01 | `domains/brokers.md` (Mermaid line 47) | `POST /brokers/:id/transactions/bulk` in Mermaid diagram — **stale broker-scoped endpoint**. Actual endpoint since Phase 7 Part 3 is `POST /transactions/bulk` (multi-broker atomic). This was fixed in `domains/transactions.md` in Lint #4 but the Brokers domain Mermaid was missed. | Replaced with `POST /transactions/bulk` |

### 🟡 Medium — Repaired

| # | Page | Problem | Fix |
|---|------|---------|-----|
| L6-02 | `domains/brokers.md` "What comes next" | Described F-048 Staging Modal as entirely future work — stale after Phase 7 Part 4 delivered manual `create-many`/`edit-many` modes | Updated to note manual modes done, BRIM `create-brim` coming in Part 5 |
| L6-03 | `raw/ingest-registry.md` Round1 entry | `plan-phase07-transaction-Part4_Round1` shows 14-line drift at git `444b2d16`. The diff is trivial: successor link updated from planned placeholder name to actual Round2 filename. Content is accurate; the drift is purely metadata. | Annotated in source page (`phase07-part4-round1.md`) — no re-ingest needed |

### 🟢 Low — Deferred

| # | Page | Problem | Recommendation |
|---|------|---------|---------------|
| L6-04 | `features/F-049.md` | F-049 describes "Review staging" in the flow; doesn't mention that F-048 manual mode is now available as an alternative entry to staging for non-BRIM use | P2 — update F-049 in Phase 7 Part 5 when BRIM→staging flow is finalized |

### Drift detection summary

| Source | Hash | Lines changed | Assessment |
|--------|------|---------------|------------|
| `plan-phase07-transaction-Part4.prompt.md` | `dcb91929` | 0 | ✅ clean |
| `plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md` | `444b2d16` | 14 | ⚠️ trivial — successor link metadata only |
| `plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md` | `29898623` | 0 | ✅ clean |

### Orphan check — ✅ none

All 11 new pages have inbound `[[links]]` from at least 2 other wiki files each (F-047, source pages, index.md, log.md, domain pages). No orphans.

### Index drift — ✅ none

No wiki pages missing from index.md (except individual F-00X feature pages, which are intentionally not individually listed — only notable ones appear under "Individual Feature Pages"). No dead index references found.

### Concept debt — ✅ satisfied by new pages

Terms that appeared 7–18× across wiki pages before this ingest now have concept pages:
- `entity-store-pattern` (18 occurrences) → [[concepts/entity-store-pattern]] ✅
- `always-pair-adjacent` (16 occurrences) → [[concepts/always-pair-adjacent]] ✅
- `opportunistic-cache-merge` (7 occurrences) → [[concepts/opportunistic-cache-merge]] ✅

`TxTypeIconCell` (6 occurrences) is a component name, not a pattern — documented in F-047. No concept page needed.

**Total touched**: `domains/brokers.md` (2 fixes) + log.md. **0 new pages created**, **0 pages deleted**.

## [2026-04-28] correction | Source-verified fixes — 4 factual errors corrected

Cross-checking all Phase 7 Part 4 wiki pages against actual source files (range: `fcdd89e8` → `2989862` HEAD). 4 factual errors corrected:

1. **`TxTypeIconCell.svelte` path** (F-047.md, sources/phase07-part4-round2.md): Missing `cells/` subdirectory. Fixed to `frontend/src/lib/components/transactions/cells/TxTypeIconCell.svelte`.

2. **TxTypeIconCell desktop interaction** (sources/phase07-part4-round2.md): Claimed "single click → open doc". Actual code: **double-click** (`ondblclick`) opens doc; single click shows tooltip only.

3. **assetStore loader endpoint** (concepts/entity-store-pattern.md, concepts/opportunistic-cache-merge.md): Examples used `apiClient.get('/assets/all')`. Actual: `zodiosApi.list_assets_api_v1_assets_query_get()` → `GET /assets/query`.

4. **Babel fix code** (problems/babel-currency-symbol-locale.md): Function signature was `list_currencies(locale: str)` (wrong). Actual: `list_currencies(language: str = "en")`. Code used `locale='en'` string; actual code uses `en_locale = get_babel_locale("en")` (a `babel.Locale` object), then `get_currency_symbol(code, locale=en_locale)`.

**Verified correct**: entityStore.ts API, brokerStore.ts API, isGrouped logic (TransactionsTable), DataTable fullData/onSortChange/getEnumOptionsWithCounts, capture-phase click (use:captureClick action).

**Files corrected**: F-047.md, sources/phase07-part4-round2.md, concepts/entity-store-pattern.md, concepts/opportunistic-cache-merge.md, problems/babel-currency-symbol-locale.md.

---

## [2026-05-25] file | Dual-Transaction Form — TransactionFormModal paired mode (R6-B.1–B.3)

Filed discovery: TransactionFormModal.svelte now supports paired transactions (FX_CONVERSION, TRANSFER_ASSET, TRANSFER_CASH) via a dual-form mode driven by `pairFormLayout` from `transactionTypeStore`.

**Created**:
- [[decisions/dual-transaction-form-design]] — design choices: single modal with From/To layout, Da/A sign-based detection on edit, swap normalisation, `collectDualCreates()` / `collectDualUpdates()`, client-side same-currency/same-broker validation

**Updated**:
- [[features/F-047]] — added TransactionFormModal to modal inventory + source files table; added `dual-transaction-form-design` to `related_decisions`
- `index.md` — added decision entry

Key implementation details captured: 3 layout modes (fx, transfer_asset, transfer_cash), `DualDraftTo` state type, partner auto-fetch in edit mode, 7 new i18n keys across 4 locales, type selector readonly in dual mode, advanced section hidden, tags/description shared across pair sides.

## [2026-05-25] ingest | Phase 7 Part 4 Rounds 3–5 (5 plan files)

Batch ingest of 5 Phase 7 Part 4 plan files covering the transaction modal system rewrite, i18n validation errors, unified batch pipeline, and server-driven type rules.

**Source files ingested** (git hash `133cb0d4`):
- `plan-phase07-transaction-Part4_Round3-stagingModalRewrite.prompt.md`
- `plan-phase07-transaction-Part4_Round3_Bugfix1-formModalRedesign.prompt.md`
- `plan-phase07-transaction-Part4_Round3_Bugfix2-i18nValidationErrors.prompt.md`
- `plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md`
- `plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md`

**Created**:
- [[sources/phase07-part4-round3-staging-rewrite]] — three-component split (FormModal/BulkModal/PromoteWizard)
- [[sources/phase07-part4-round4-unified-pipeline]] — 4 endpoints → 2 with lenient parse
- [[sources/phase07-part4-round5-server-type-rules]] — transactionTypeStore + auto-sign + dual-form
- [[problems/pydantic-422-preemption]] — Pydantic 422 blocks service-layer validation (resolved)

**Updated**:
- [[sources/phase07-part4-round3-bugfix1]] — 5 walkthrough rounds, A1→A3→A4 pivot, field reset, unsaved-changes
- [[sources/phase07-part4-round3-bugfix2]] — structured error codes, PydanticCustomError, resolveIssueMessage
- [[features/F-046]] → title updated (Unified Batch API), layer→fullstack
- [[features/F-047]] → confirmed implemented, dual-form modals
- [[features/F-048]] → confirmed in-progress (R6-B items pending)
- `features/registry.md` — TRANSACTIONS domain: 3 implemented, 1 in-progress, 2 planned
- `index.md` — 2 decisions, 2 concepts, 2 problems, 5 sources added
- `raw/ingest-registry.md` — 5 new entries at `133cb0d4`

**Key decisions surfaced**:
- [[decisions/unified-batch-pipeline]] — already existed
- [[decisions/server-driven-type-rules]] — already existed

**Key concepts surfaced**:
- [[concepts/validate-scheduler-pattern]] — already existed
- [[concepts/resolve-validation-message-pattern]] — already existed

**Key problems surfaced**:
- [[problems/pydantic-422-preemption]] — new (resolved by unified pipeline)
- [[problems/browser-autofill-numeric-fields]] — already existed

## [2026-05-28] ingest | Phase 07 Part 4 Rounds 5-6 (8 plan files — Bugfix 1-3 + Round 6 Plans A/B/B1)

Batch ingest of 8 Phase 7 Part 4 plan files covering Round 5 Bugfix 1-3 and Round 6 Plans A/B/B1. Git hash: `0351d65f`.

**Source files ingested**:
- `plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md` (re-anchored: R6-B expansion)
- `plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md`
- `plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md`
- `plan-phase07-transaction-Part4_Round5_Bugfix3_TestWalkFixes.prompt.md`
- `plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md`
- `plan-phase07-transaction-Part4_Round6_PlanA_ContextMenuBugfix.prompt.md`
- `plan-phase07-transaction-Part4_Round6_PlanB_DeletePickerAccess.prompt.md`
- `plan-phase07-transaction-Part4_Round6_PlanB1_BugfixRound1.prompt.md`

**Created** (6 source pages):
- [[sources/phase07-part4-round5-bugfix1-dual-form]] — CASH_TRANSFER, split/promote architecture, paired rendering
- [[sources/phase07-part4-round5-bugfix2-testwalk-overhaul]] — BulkModal readonly, "✓ Applica", dual dates
- [[sources/phase07-part4-round5-bugfix3-testwalk-fixes]] — PATCHABLE_FIELDS, type swap, TagInput, SafeDecimal
- [[sources/phase07-part4-round6-context-menu-delete]] — Round 6 master plan: ContextMenu, delete, picker
- [[sources/phase07-part4-round6-plana-context-menu-bugfix]] — ContextMenu + R7-C1/H1 fix + txPayloadHelpers.ts
- [[sources/phase07-part4-round6-planb-delete-picker-access]] — Broker access, DeleteModal 3 layouts, PickerModal, 48+ E2E tests

**Created** (3 decisions):
- [[decisions/cash-transfer-split-promote]] — CASH_TRANSFER first-class enum + split/promote immediate endpoints
- [[decisions/context-menu-all-tables]] — ContextMenu default ON on all DataTables
- [[decisions/broker-access-min-paired]] — Paired access = min(role_A, role_B) + 3-layout delete + partner_broker_id

**Created** (1 problem):
- [[problems/dual-form-collect-duplication]] — FormModal/BulkModal duplicated collect logic → txPayloadHelpers.ts

**Updated**:
- [[sources/phase07-part4-round5-server-type-rules]] — re-anchored at `0351d65f` (R6-B expansion)
- [[features/F-047]] — ContextMenu, asset clickable, description column, URL filter sync, broker access, soft reload, flat mode adjacency
- [[features/F-048]] — CASH_TRANSFER, split/promote architecture, PATCHABLE_FIELDS, type swap, TagInput, txPayloadHelpers, broker access gating, 3-layout DeleteModal, PickerModal, 48+ E2E tests, round 5-6 status history
- [[features/registry]] — F-048 title updated
- [[connections/transactions-connections]] — header updated with Round 5-6 achievements
- [[domains/transactions]] — F-048 feature cluster row updated
- `index.md` — 6 source pages, 3 decisions, 1 problem added
- `raw/ingest-registry.md` — 8 new entries at `0351d65f`

**Key architectural decisions surfaced**:
1. **CASH_TRANSFER** first-class enum (replaces VALID_MIXED_PAIRS hack); split/promote as immediate dedicated endpoints (schemas ready, backend endpoints in Plan C)
2. **ContextMenu** default ON on all DataTables (right-click + mobile long-press, zero consumer changes)
3. **Paired access = min(role_A, role_B)** — 3-layout TransactionDeleteModal (standalone/paired-full/paired-blocked); GET /brokers LEFT JOIN returning all brokers with user_role=null; partner_broker_id in TXReadItem
4. **txPayloadHelpers.ts** — shared utility eliminating 3 cascading bugs from FormModal/BulkModal logic duplication

**Pages created**: 6 sources + 3 decisions + 1 problem = 10 new wiki pages.
**Pages updated**: 7 existing pages + index.md + ingest-registry.md.

## [2026-06-17] ingest | Phase 09 Dashboard Batch
Source: `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/` @ git:`24cdc40`.
Extracted concepts regarding Dashboard KPI, TWRR, MWRR algorithms, and FIFO lot tracking implementations.
Created: [[sources/phase09-dashboard-batch]], [[concepts/twrr-mwrr-algorithms]], [[concepts/fifo-lot-tracking]].
Updated: [[features/F-054]].

## [2026-06-17] ingest | Source Code v0.9.0 Batch
Source: Source Code @ git:`6d89b44`.
Ingested new source code implementations including Remotion Video Promo, MkDocs Pros/Cons Slider, and Gallery Overhaul.
Created: [[sources/source-code-v0.9.0-batch]], [[entities/video-promo-remotion]], [[concepts/interactive-pros-cons-slider]].

## [2026-07-01] lint | Full wiki health check — post Phase 7-9 ingest

Graph: 6399 nodes, 17688 edges, 366 communities. 1080 corpus files.
God nodes: Currency (426 edges), TransactionType (199), Transaction (166), User (158), Asset (152).
Issues found: 4 (1 high, 2 medium, 1 low).

Repaired:
- [HIGH] Dead link in `index.md`: `problems/pydantic-422-pre-emption` → `problems/pydantic-422-preemption` (typo fix)

Deferred (medium):
- Index drift: 20 wiki/features/ files not listed in index.md (F-001–F-074 gaps) — acceptable: index uses domains as navigation hub, not exhaustive feature list
- Concept debt: "Phase 07 Part 4" node cluster [5x] and "Multi-Broker Atomic Transaction Batch" [4x] without new concept pages — already covered by decisions/multi-broker-atomic-tx.md and source pages

Low:
- graph.html not regenerated (6399 nodes > 5000 threshold)

Next recommended: ingest Phase 10 / next development cycle when available.

## [2026-07-01] graphify | Incremental update — portfolio engine 3-pool refactor

Graph updated: 6514 nodes (+115 vs pre-update 6399), 17914 edges (+226), 411 communities.
Changed files: portfolio_engine.py (AST) + 8 mkdocs risk-metrics/WAC docs (semantic) + 6 new wiki pages.
False-deleted manifest paths (corpus/corpus/ double-prefix) ignored — full rebuild not needed.

## [2026-07-07] ingest | Phase 09 M1/M2 archive closeout (Holdings/Performance panel, verification pass)

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/` (Milestone_1/, Milestone_2/ incl. `lowDashboard/`, `portfolio_engine/`, `Ai_consultant_engine/`, + 6 root cross-cutting docs) @ git:`1be3fc9c` (staged `git mv`, uncommitted at ingest time).
Milestone_3 (Broker UI v2) intentionally NOT archived — still in progress at old `phase-09-subplan/Milestone_3/` path.

This ingest is primarily a **closeout pass**: an exhaustive (non-sampled) verification against the current codebase found that ~20 items previously logged as "open" in `implementation_status_report.md` / `STATUS_REPORT_M2.md` / `ARCHITECTURE_CURRENT_STATE.md` (dated 2026-06-19/06-30) are now resolved by the Holdings/Performance refactor (commit `78aaa0a3`, 2026-07-06) and prior engine work (commit `39106380`, 2026-06-30): `get_summary()` wired to `PortfolioCalculationEngine`, `build_data_quality_report()` implemented, `first_position_date` present, GrowthChart stacked-area + rich tooltip, AllocationPanel Now/History toggle, DataQualityBanner unified field, TRANSACTION_IMPLIED fallback, tx double-click modal. ~7 items resolved *differently* than originally designed (architecture evolved) — recorded as [[decisions/portfolio-summary-direct-wiring]]. ~7 items remain genuinely open (low priority) — recorded in the source page and cross-linked from entity/domain pages. Per explicit user instruction, the MWRR "100x" result cap and Newton-only (non-Brent) solver choice are **deliberate design decisions, not bugs** — recorded as [[decisions/mwrr-solver-newton-cap]] with an explicit "do not record as a problem" note for future historians.

Also captured two genuinely open, unrelated pre-existing problems found during verification: a `test_transaction_implied.py` constructor-signature mismatch (6 failing tests, root cause confirmed via `pytest --junitxml`) and an unresolved `DataTable.svelte` column-resize click-no-effect bug (root cause not yet determined).

Created: [[sources/phase09-m1-m2-archive-2026-07]], [[concepts/holdings-performance-panel]], [[decisions/mwrr-solver-newton-cap]], [[decisions/portfolio-summary-direct-wiring]], [[problems/test-transaction-implied-constructor-mismatch]], [[problems/datatable-column-resize-noop]].

Updated: [[entities/portfolio-service]], [[entities/portfolio-engine]], [[concepts/twrr-mwrr-algorithms]], [[concepts/portfolio-report-unified]], [[sources/phase09-portfolio-engine-dashboard]], [[sources/phase09-portfolio-engine-3pool-refactor]], [[sources/phase09-dashboard-batch]], [[features/F-054]], [[features/F-055]], [[features/F-058]], [[features/registry]], [[domains/dashboard]], [[domains/calculations]].

Path corrections: fixed 8 files with stale `phase-09-subplan/Milestone_1|2` references (missing new `phases/` prefix introduced by the 2026-07-07 `git mv`) — [[decisions/mwrr-boundary-fix]], [[concepts/3-pool-cash-model]], [[concepts/pre-frame-frame-separation]], [[concepts/inline-wac-computation]], [[sources/phase09-portfolio-engine-3pool-refactor]], [[sources/phase09-portfolio-engine-dashboard]], [[entities/portfolio-engine]], [[sources/phase09-dashboard-batch]] (3 root-doc paths).

## [2026-07-07] graphify | Incremental update — Phase 09 M1/M2 archive closeout

Graph updated: 6527 nodes (+13 vs pre-update 6514), 18024 edges (+110), 381 communities (recomputed globally via Louvain — count not directly comparable to prior 411).
Scope: single semantic-extraction subagent chunk over the 23 wiki pages created/updated this ingest (6 new + 17 updated). 8 node IDs remapped to existing canonical IDs before merge to avoid duplicating already-modeled entities (`portfolio_engine_entity`, `portfolio_service_entity`, `decision_mwrr_boundary_fix`, `twrr_mwrr_algorithms_concept`, `portfolio_report_unified_concept`, `dashboard_document`, `f055_portfolio_charts`, `f058_roi_calculations_simple_dwr`).
Deferred (out of scope for this narrow update, left for a future full/incremental pass): semantic re-extraction of the 47 archived `phases/phase-09-subplan/` plan documents whose only change is the `git mv` path (content identical — these still show as "new" in manifest terms since their new path was never previously seen, but no new graph nodes are needed since content is unchanged); AST re-extraction of ~117 unrelated code files flagged as changed by `detect_incremental` (out of this session's scope). Manifest (`graphify-out/manifest.json`) stamped only for the 23 processed wiki files; as a side effect, `save_manifest`'s existing-entry reconciliation (root-relative re-anchoring) consolidated ~800 duplicate legacy absolute/relative key pairs and dropped 36 entries for genuinely-deleted/moved files — this is manifest hygiene, not a change to `graph.json`.
Community relabeling (Step 5, LLM-based) and `graph.html` regeneration (Step 6) skipped — graph exceeds the 5000-node HTML threshold and full community relabeling is out of proportion to a 23-file incremental update, consistent with the 2026-07-01 precedent.

## [2026-07-07] lint | Health check — post Phase 09 M1/M2 archive ingest

Graph: 6527 nodes, 18024 edges, 381 communities. 1125 corpus files.
God nodes unchanged from last lint (Currency 426, TransactionType 199, Transaction 166, User 158, BaseBulkResponse 155) — none are new-wiki-relevant.
New hyperedges from this ingest: "Dashboard Unified Report Flow", "Phase 09 Archive Closeout", "Portfolio Engine Refactor Core" — all EXTRACTED confidence 1.00, confirming the new pages integrated cleanly into existing clusters.
Issues found: 4 (0 high, 2 medium, 2 low) — all pre-existing, none introduced by this ingest.

Verified clean (explicit checks requested by user):
- No stale `phase-09-subplan/Milestone_1|2` (missing `phases/` prefix) references remain in any `wiki/` page or `index.md`. Only `raw/ingest-registry.md` and historical `log.md` entries still show the pre-move path — correct, since those are point-in-time git-hash snapshots from before the 2026-07-07 `git mv`.
- All 6 new pages have valid frontmatter, a `## Source files` table, and ≥4 inbound `[[links]]` — no new orphans.
- [[F-084]] (referenced from `domains/transactions.md`, `sources/todos.md`) not orphaned by the `domains/dashboard.md` rewrite — inbound links intact elsewhere.
- All `[[...]]` links in the 19 new/updated pages resolve to real files (bare `F-NNN` codes resolve to `features/F-NNN.md`).

Deferred (medium):
- **2 pre-existing orphan pages** (unrelated to this ingest): [[sources/phase07-part4-round3]] and [[sources/phase07-part4-round5]] — near-duplicate content of already-indexed, differently-slugged pages ([[sources/phase07-part4-round3-staging-rewrite]], [[sources/phase07-part4-round5-server-type-rules]]). Not linked from any other wiki page or from index.md. Recommend a future consolidation pass (merge or delete the duplicate slug).
- **Index drift**: 17 `wiki/features/*.md` files (F-001, F-003, F-004, F-008, F-009, F-014, F-015, F-023, F-024, F-036, F-045, F-046, F-051, F-052, F-053, F-056, F-074) not individually listed in `index.md` — same accepted pattern noted in the 2026-07-01 lint (index uses domains + Feature Registry as the navigation hub, not an exhaustive per-feature list).

Low:
- `graph.html` not regenerated (6527 nodes > 5000 threshold) — unchanged from prior lint.
- Concept debt (Interest, Dividend, Risk Metrics, TimeSeriesStore Pattern, Svelte 5 Runes Convention, "Phase 07 Part 4" cluster, "Multi-Broker Atomic Transaction Batch") — all pre-existing, already deferred in the 2026-07-01 lint as acceptable (covered by existing decision/source pages).

Not repaired this pass (deferred, low priority, unrelated to the requested ingest scope): the 2 orphan sources and the 17 unlisted feature pages.

Next recommended: a dedicated dedup pass on `sources/phase07-part4-round3.md` / `sources/phase07-part4-round5.md`; ingest Milestone 3 (Broker UI v2) once it completes.

## [2026-07-13] file | Full test suite green-up session
Ran `./dev.py test --fresh-run all` / `--resume all` to green the entire suite (14/14
categories). Filed three new problem pages for the cross-cutting infra/contract bugs found
along the way, and corrected the pre-existing [[problems/test-transaction-implied-constructor-mismatch]]
page (its proposed "signature-only" fix was verified empirically to not work — the WAC-as-price
fallback was actually removed, not renamed).
Filed: [[problems/pytest-exit-swallows-failures]], [[problems/resume-mode-stale-import]],
[[problems/brlistresponse-contract-drift]].

## [2026-07-15] ingest | Phase 09 M3 archive (Broker UI v2 redesign, chart-resolution/semantic-zoom)

Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/` (+ root
`implementation_plan.md` and 3 superseded pre-v2 designs) @ multiple git hashes (see `raw/ingest-registry.md`
— `git mv` archive, staged/uncommitted at ingest time, same pattern as the 2026-07-07 M1/M2 closeout). This
completes Phase 9 fully: all 3 Milestones now archived under `phases/phase-09-subplan/`.

Milestone 3 redesigns the Broker pages (global list + 3-tab detail) to reuse the unified `/portfolio/report`
widgets built in M1/M2, plus a cross-cutting chart-resolution/semantic-zoom workstream (7 impl plans + 1
study, written in parallel by a fleet of agents). All sub-plans verified ✅ design · ✅ implementation plan ·
✅ implemented (no open items). Key content: `GET /portfolio/asset-history` regression found-and-restored
(commit `3184a969` → `1a734008`); `GET /brokers?include_inaccessible=true` opt-in discovery; sharing icon
read-only for EDITOR/VIEWER/non-members (was OWNER-only); `BrokerBreakdown.cash_balances` added natively for
per-card NAV/Gain/quota% without N+1 calls; inline multi-broker FIFO lots panel (UI/display layer over the
existing `GET /portfolio/lots` engine output, no engine changes); daily→weekly→monthly semantic-zoom
bucketing (`timeSeriesAggregation.ts`) now shared across price/growth/allocation charts and 9 signal
overlays, plus a static compact-card variant with no interactive resolution switching.

**Explicit exclusion honored**: `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/` (== the symlinked
`LibreFolio_devWiki/corpus/roadmap/fifo-engine/`) was deliberately NOT read, summarized, or linked from any
page in this pass, per user instruction — it is a separate, still-open FIFO/WAC/transfer engine-internals
investigation ("Analisi tecnica completa... Domande aperte e raccomandazione", 2026-07-14), unrelated to this
UI redesign and not yet ready for ingest (no decision taken yet).

Created: [[sources/phase09-m3-broker-redesign-2026-07]], [[concepts/chart-resolution-semantic-zoom]],
[[entities/time-series-aggregation]], [[decisions/broker-list-visibility-non-members]],
[[decisions/broker-card-aggregation-no-n-plus-one]], [[problems/portfolio-asset-history-regression-restored]].

Updated: [[domains/brokers]] (UI v2 redesign summary + 2 new decisions linked), [[domains/dashboard]] ("M3 in
progress, not archived" note resolved; source-file paths corrected), [[entities/portfolio-engine]] (History
row for the M3 archiving milestone).

Also refreshed, as part of the archive move itself (not a separate wiki page): two stale "codice in working
tree non ancora committato" notes in `Milestone_3/README.md` (git status confirmed both already committed),
and flagged (not fixed, out of scope) a pre-existing broken link in the same file
(`GUIDA-TOOLBAR-RESPONSIVE.md` vs. the actual `GUIDA-TOOLBAR-RESPONSIVE-v2.md` on disk) plus two unrelated
pre-existing dangling links in `phases/phase-09-dashboard.md` pointing at documents later relocated by
earlier phase-07/phase-08 archiving passes (`plan-phase05-to-08-upgrade.md`,
`plan-WacInlineValidateCommit.prompt.md`) — none caused by this session's edits, left as noise per convention.

Per plan: the skill's own final `graphify --update` step was skipped here — superseded by a full
from-scratch graphify rebuild run immediately after the post-ingest lint pass (see following log entries).

## [2026-07-15] lint | Health check — post Phase 09 M3 ingest (pre-rebuild)

Graph (pre-rebuild, unchanged from 2026-07-07): 6527 nodes, 18024 edges, 381 communities, 1125 corpus files —
run intentionally BEFORE the full graphify rebuild per plan, so cheap file-based checks fix issues before the
costly rebuild processes the final state once. Graph-based checks (god nodes, high-degree gaps) therefore
still reflect the pre-ingest graph — the 6 new M3 pages aren't graphed yet; expected, not a defect. God nodes
unchanged from the 2026-07-07 lint (`Currency` 426, `TransactionType` 199, `Transaction` 166, `User` 158,
`BaseBulkResponse` 155) — all pre-existing code entities, none newly relevant to this ingest.

File-based checks on the 6 new + 3 updated pages from this ingest: **all clean**.
- Orphans: 0 — every new page has 3-5 inbound `[[links]]` (verified programmatically).
- Index drift: 0 — all `wiki/**/*.md` files are listed in `index.md`.
- Broken `[[wikilinks]]`: 0 introduced by this ingest (checked all 1537 wikilinks across 322 wiki files).

Issues found: 2, both pre-existing and unrelated to this ingest (deferred, not auto-repaired, following the
same scoping precedent set in the 2026-07-07 lint for the 2 unrelated orphan sources found then):
- `wiki/sources/kb-01-backend.md` → `[[concepts/provider-registry-pattern]]` — target page does not exist.
- `wiki/sources/phase06-step4-planc.md` → `[[problems/sync-pairs-bulk-none]]` (×2) — target page does not
  exist.

Carried over from the 2026-07-07 lint, still not repaired (unrelated to this ingest, same as before): the 2
near-duplicate orphan sources ([[sources/phase07-part4-round3]], [[sources/phase07-part4-round5]]) and the 17
`wiki/features/*.md` pages not individually listed in `index.md`.

Next recommended: full graphify rebuild (this session, immediately following); a dedicated pass on the 2
newly-found broken links + the carried-over dedup/index-drift items above, whenever a general wiki-cleanup
session is scheduled (not part of this ingest's scope).


