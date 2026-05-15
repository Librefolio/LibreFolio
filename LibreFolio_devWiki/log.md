# devWiki Log

> Append-only chronological record of all wiki operations.
> Format: `## [YYYY-MM-DD] {operation} | {title}`
> Parse: `grep "^## \[" log.md | tail -10`

## [2026-05-31] ingest | Phase 07 Part 4 Round 6 — Plan B23 (registry backfill) + Plan D chain (7 files: split/promote full stack)

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
