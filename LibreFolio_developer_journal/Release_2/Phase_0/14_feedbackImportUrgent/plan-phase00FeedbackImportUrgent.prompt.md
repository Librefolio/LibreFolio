# Urgent import feedback - incremental bugfix plan

**Started:** 2026-09-08. **Owner:** Group E.
**Baseline:** `4a73f5f63447e01b51993afb2e3c73e2c22a9a28` (`refs/heads/dev_release2`).
**Worktree:** `e-alfy-laughing-tribble`; app-managed branch `e-alfy-import-e-ux-urgenti`.
**Follow-up:** [Round 1 - review operativa e UX approvata](plan-phase00FeedbackImportUrgentRound1-Review.prompt.md).
**Portable handoff:** [Integration manifest](manifest-integrazione-E.md) · [Review checklist](checklist-review-E.md).
**Mandate:** implement E1-E4 first, then E5-E6 and inherited U1/U5/U4/U7/U9.
The developer explicitly authorized P0/P1 investigation and fixes. U4/U7/U9 received
design approval on 2026-09-08 at 17:08, with the variants recorded in Round 1.
Le review operative successive sono registrate nei Round 1-4 e nel manifest.
**Stato aggiornato (2026-09-09):** ✅ esecuzione tecnica completata e pacchetto
applicato al checkout target `dev_release2`; il dev ha
approvato badge e sottotesti R4 alle 15:51. La richiesta finale di ingresso
diretto a Crea su Instagram e' valutata nel
[Round 4, sezione 4](plan-phase00FeedbackImportUrgentRound4-SocialBoundaries.prompt.md#4-ingresso-diretto-a-crea-su-instagram---verifica-conclusa-2026-09-09).
Commit/SHA e archiviazione restano in attesa del commit manuale. Le note datate dei
singoli passi descrivono la loro fase storica, non nuovi task rimasti da eseguire.

**Additional feedback (2026-09-08):** E7/E8 concern the bulk workspace's affected-row
references and chronological ordering. The developer observed them on production;
E reproduces with synthetic data on its test instance only. Private funding notes
remain in session messages and are not authorization to create production transactions.

## Scope and ownership

- E owns AssetModal, provider configuration, nested asset inspector and wizard integration
  together (E1/E2/U1/U5). Paired-form E3 and backend matching E4 may have separate writers.
- E alone runs project commands, suites, test backend/build, API generation and i18n.
  Test authors may write distinct regression files, but may not run suites or servers.
- A/B remain paused; later C/D source mandates apply only to their own worktrees.
  Do not touch BrokerSharingPanel or copy other worktrees' code.
- No staging, commits, pushes, history mutation, production data/services, schema redesign,
  automatic FX/cash creation, or relaxation of financial validation and permissions.
- The authorized source CSV is read locally, read-only and in memory. Do not persist its
  contents, private identifiers, dates, amounts, descriptions or holdings in artifacts,
  logs or fixtures. Regression data must be independently synthetic.

## Source plans

- [Feedback index](../09_feedbackJobs/README.md)
- [Sprint analysis / master 06](../09_feedbackJobs/06_piano_sprint.md)
- [UX backlog](../09_feedbackJobs/01_ux_dashboard.md)
- [BRIM backlog](../09_feedbackJobs/04_brim_import.md)
- [Urgent feedback report](../09_feedbackJobs/07_feedback_import_critici.md)
- The coordinator owns the urgent feedback report and master/backlog updates; E does not
  edit those documents.

## 0. Establish baseline and evidence - ✅ completed 2026-09-08

- [x] Verify exact HEAD and clean initial worktree.
- [x] Read the authorized CSV before application investigation.
- [x] Read master 06, README, UX and BRIM backlog, applicable repository instructions.
- [x] Query accumulated wiki knowledge; reconcile any stale claims against current code.
- [x] Restore only missing dependencies from existing locks and establish isolated runtime.

> **Note implementazione (2026-09-08):** HEAD matches the required baseline. The real CSV
> is valid UTF-8 without BOM, comma-delimited, with the expected seven columns, 34 rows,
> 22 non-empty asset references and four distinct ISIN-shaped identifiers. No outer
> whitespace, extra fields or broker column. These structural facts do not establish
> whether matching assets exist in the database.
>
> **Note implementazione (2026-09-08):** Executed the actual Generic CSV parser on the
> original read-only input with output captured in memory. It preserves all four ISIN
> hints, emits 24 valid transactions and ten `cashSignPositive` validation issues,
> and keeps the supplied per-file broker. No warnings; source unchanged. The ten schema
> failures are distinct from asset matching and must not be bypassed.
>
> **Note implementazione (2026-09-08):** No materialized `graph.json` in this worktree;
> used three targeted wiki pages instead, treating obsolete negative fake IDs and
> bulk routes as historical. Locked Python/frontend dependencies restored; baseline
> debug build succeeds with zero type diagnostics. Fresh DB path verified under this
> worktree, populated with repository synthetic data. E-owned backend PID 20306 on
> `127.0.0.1:6041` responds to health, runs from this worktree without reload/scheduler.
>
> **⚠️ Fuori pista (2026-09-08):** First `pipenv run python dev.py graph query` created
> the worktree-specific environment, then failed because `argcomplete` was absent.
> `pipenv sync --dev` restored the locked environment. First frontend build then failed
> on missing adapter/vite; `npm --prefix frontend ci` restored `package-lock.json`.
> No lock upgrades. The normal build's automatic API generation produced no tracked diff.

## 1. E1/E2 - reliable asset inspection and persisted metadata - ✅ core completed 2026-09-08

- Reproduce currency/manual-save failure in the final wizard step; inspect requests,
  validity/dirty state, callbacks, focus and all nested overlays before choosing a fix.
- Trace provider sector/geography values through save payload, DB readback, query DTO,
  stores and inspector rehydration; distinguish persistence loss from stale projection.
- Fix the owning lifecycle without re-syncing providers on every inspection.
- Verify change, save, close, reopen and fresh network read with owned synthetic assets.

> **Note implementazione (2026-09-08):** Source-level causes under reproduction:
> `/assets/query` is a summary without classification; the wizard passes it as complete
> edit data, while save always sends the classification field (including null). The list
> page has the same incomplete edit construction. Provider comparison uses fixed z-index
> 70 and currency confirmation fixed 50 below inspector 90. These are evidence from
> code, not yet proof that every reported freeze has this cause. Test-author is preparing
> real wizard/DB round-trip regressions with offline provider responses.

> **Note implementazione (2026-09-08, reproduction):** Confirmed in the actual baseline
> browser flow with a new synthetic account, broker, asset and two-row CSV. Full metadata
> GET initially returned description, sector and geography. The wizard inspector showed
> all three empty; a pointer-accessible name-only Save sent HTTP 200 with
> `classification_params: null`. A fresh GET confirmed real data loss, not just a blank
> projection. The unique primary ISIN matched before parsing in this same baseline.
>
> **Note implementazione (2026-09-08, reproduction):** A single owned manual price point
> made a currency edit return the correct HTTP 409. The confirmation existed at z50 below
> inspector z90; hit-testing its confirm button reached the inspector instead. No wipe
> was forced. Fresh GET/summary retained original currency and the owned price point.
> Plain name Save did work: this is a specific nested-dialog failure, not a universal
> validity failure.
>
> **⚠️ Fuori pista (2026-09-08):** Explicit `classification_params: {sector_area: null}`
> also cleared unrelated description/geography in the real API. Nested `exclude_none`
> collapsed it to `{}`, which the service treats as clear-all. The serializer now
> preserves only explicitly supplied nested fields, including nulls; other top-level
> null handling is unchanged. No migration. Schema prose was aligned to the actual
> atomic-per-field shallow-merge contract.
>
> **Note implementazione (2026-09-08, implementation):** Complete typed edit loading is
> shared by wizard/list. Form PATCH omits unchanged classification, sends only edited
> blocks, and preserves explicit partial/total clear. Nested dialogs inherit their
> parent layer; currency confirmation uses ModalBase for focus/scroll locking, retaining
> explicit confirmation and existing Escape/backdrop policy. Logical PATCH failures no
> longer masquerade as successful edits.
>
> **Note implementazione (2026-09-08, verification):** real wizard/API regressions
> verified edit, provider metadata save, fresh GET and reopen, including partial clear
> and currency confirmation with owned prices. Developer manual review confirmed the
> core behavior. Round 1 addresses its additional copy/name/interpolation requests;
> late test-only deltas remain explicitly queued for rerun.

## 2. E3 - paired FX completeness and validation - ✅ core completed 2026-09-08

- Reproduce broker-before-type, forced/hidden broker and initialization/reopen paths.
- Preserve the shared FX broker and explicit dates of each leg, nonzero opposite signs, currency distinction,
  scheduler correctness and backend balance/permission validation.
- Exercise the real bulk editor: Apply changes drafts; Save All commits separately.

> **Note implementazione (2026-09-08):** The hidden FX destination broker now derives
> from the source consistently in readiness, validation fingerprint and collected drafts.
> Paired cash magnitudes preserve decimal strings on edit and in the FX collector.
> Read-only historical signs remain unchanged. Browser/commit regression evidence pending.
>
> **⚠️ Fuori pista (2026-09-08):** The first delegated patch also forced a common date.
> Inspection of `buildDualCreatePayloads` proved that `to.date || from.date` is the
> existing FX contract: explicit different leg dates are permitted. Restricted the
> derivation to the broker; preserved independent date inputs and date swaps. Test-author
> received the corrected round-trip contract before consolidation.
>
> **Note implementazione (2026-09-08, verification):** real bulk staging, independent
> dates and exact decimals, funded commit/readback, and insufficient-funds rejection
> verified. Developer manual review passed. Original trigger is the broker selected
> before the FX layout: the displayed broker was valid while the hidden destination
> remained unset.

## 3. E4 - Generic CSV local mapping and cached parse refresh - ✅ core completed 2026-09-08

- Parse structural synthetic equivalents; preserve verbatim amounts and row currency.
- Separate extracted hints, local candidates and automatic selection.
- Cover primary ISIN, aliases, case/whitespace, inactive and ambiguous matches.
- Cover existing-before-parse, create-after-parse and reopen/last-parse cache paths.
- Respect parser/cache version policy if output changes. Never edit production sidecars.

> **Note implementazione (2026-09-08):** No backend/parser change justified. Current
> `search_asset_candidates` and its bulk counterpart merge primary ISIN (EXACT) and
> alternate ISIN (HIGH), deduplicate the same asset, and intentionally return no automatic
> choice for multiple distinct assets. Ticker/name fallback runs only without ISIN hits.
> Frontend previously overrode that ambiguity with its lone EXACT candidate, rejected a
> unique HIGH candidate on refresh, retained obsolete automatic choices and swallowed
> refresh errors. The new frontend helper mirrors backend cardinality, not a new policy.
>
> **Note implementazione (2026-09-08):** Live candidate refresh is being wired at forward
> navigation and handoff, with per-group identifier precedence, request/session guards,
> explicit error/retry state and preserved manual choices keyed by source identity.
> Cached parse facts are not rewritten; no parser-version bump or sidecar modification.
>
> **Note implementazione (2026-09-08, clarification and verification):** the dev
> clarified that the original complaint expected assets to be created automatically
> on first import. Manual creation/linking is intentional; this is not a reproduced
> backend matching failure. The independent safeguards above were verified for
> primary/inactive/alternate identifiers, ambiguity, creation after parse, and manual
> choices. Candidate refresh also reloads assetStore, fixing stale picker entries.

## 4. E5 - actionable duplicate broker error - ✅ completed 2026-09-09

- Preserve the existing text/status and per-owner conflict semantics.
- Localize the current frontend error channel via i18n CLI; no new resolver contract,
  DTO, error_code or migration.
- Required Italian recovery sentence:
  "Per risolvere rinomina il broker esistente o cambia il nome di quello che stai provando ad aggiungere".

## 4a. E7/E8 - bulk deficit references and chronological order - ✅ completed 2026-09-09

- E7: a same-day currency shortfall can affect several rows. Explain every relevant
  row and make the notification's action highlight all of them, not one arbitrary row.
  Derive affected rows from the actual validation scope; do not relax balance checks.
- E8: a newly added backdated FX conversion must appear in chronological ascending or
  descending order rather than remaining at the end by insertion order. Preserve pairing,
  stable row identity, filters, selection and payload indices independently of display.
- Reproduce with owned synthetic dates/amounts. Never import or repair the private ledger
  or add suggested funding transactions automatically.

> **Note implementazione (2026-09-08):** New feedback relayed to the coordinator and
> paired-form owner. Bulk/banner work is a distinct ownership boundary from E3.

## 4b. E9 - nightly/stable update checks and remote version - ✅ completed 2026-09-09

- Trace installed version normalization, GitHub source/channel, chosen release,
  cache/TTL/manual refresh, comparison and backend/UI status end to end.
- Use public release metadata and read-only historical Git/API evidence where the
  old installed build can be identified. Do not assume SemVer is the sole cause.
- The up-to-date toast must show the actual remote version selected for that check,
  never a copy of the installed version. Preserve channel policy and honest errors.
- No deployment, production request, automatic update or migration. API/codegen and
  four-language CLI work remain in E's integration queue.
- Test-author coverage: reported old-nightly/new-stable comparison, equality/newer local,
  malformed/prerelease policy, candidate selection/cache/refresh/failure, truthful banner.

> **Note implementazione (2026-09-08):** Bounded version-family owner assigned. About's
> version area is coordinated independently from gated U7 support. An old deployed
> client, if affected, still needs an explicit manual bootstrap update; local edits
> are not a fix applied to the developer's server.

## 5. E6 - one Generic CSV file per broker - ✅ completed 2026-09-08

- Use docs-writer for a highlighted English note in the existing
  `mkdocs_src/docs/developer/backend/brim/generic_csv.md`.
- State exactly one separate file per broker, never one flat multi-broker CSV.
  Several files/brokers in a wizard and several currencies in one broker remain valid.
- Use project-historian for a targeted existing BRIM/Generic CSV wiki note; verify source
  paths. No general wiki rewrite, graph rebuild or guide-path migration.

> **Note implementazione (2026-09-08):** English guide and targeted BRIM wiki decision
> updated by the respective specialists, with current source paths. Round 1 also
> repairs the interrupted column table without changing the guide's authoritative
> unsuffixed name. No automatic FX, currency conversion or asset creation added.

## 6. U1/U5 - provider lifecycle and currency help - ✅ completed 2026-09-09

- Same owner as step 1. Reset probe results by effective configuration/draft generation.
- Reject stale probe/metadata completion, including A-B-A, parameter edits and reopen.
- Keep the save-without-testing gate tied to the current configuration only.
- Add the existing-style currency tooltip through the i18n CLI, without new financial
  exposure fields or conflating asset currency with portfolio reporting currency.

> **Note implementazione (2026-09-08):** Added one draft-owned probe controller for
> automatic/manual requests and an independent metadata channel. Parent/child now share
> status and URL; configuration changes clear results, null clears parameter mirrors,
> and snapshot tickets reject stale session/draft/config completions. Per-field manual
> revision tracking protects edits made while metadata is pending, including edit/revert.
> Initial snapshot timers were removed; save confirmation is tied to its current context.
> Focused controller/component tests are under test-author ownership; not yet declared
> verified. Currency tooltip remains pending.

## 7. U4/U7/U9 - inherited UI approval and implementation - ✅ completed 2026-09-09

- Read A's authorized plan, ASCII proposals and operational runbook as references only.
- Obtain explicit developer approval before substantial UI code.
- U4: sortable uploader column with avatar/name multi-selection filter, not a separate
  toolbar; preserve list/grid filtering and unknown uploader identities.
  Preserve default UserSearchSelect `number | null` and permission boundaries.
- U7: reusable support actions only in DonationPopup/About; social opens another tab and
  leaves the original open. Manual fallback in a second modal; no cross-origin detection.
- U9: desktop and mobile hide-down/show-up with hysteresis and pin for focus/menu/modals,
  safe cleanup and navigation/resize.

> **Note implementazione (2026-09-08):** Read all three authorized A ASCII v1 proposals
> and the operational runbook without modifying them. Layout states remain
> `awaiting_dev_design_review`; the coordinator confirms approval will be collected
> separately. Existing U7 behavior decisions do not constitute layout approval.
>
> **Note implementazione (2026-09-08, 17:08):** approval received directly from the dev.
> U4 changed to the existing generalized column-filter pattern; U9 now includes desktop.
> Three distinct source-only owners are implementing the approved scope. Original A
> artifacts remain read-only; the review-folder summary records the approved variants.

## 8. Synthetic regressions and integration - ✅ completed 2026-09-09

- Test-author owns new/repaired tests and selector registration; E runs them serially.
- Use owned fixtures, identity-based assertions and cleanup; offline provider mocks.
- Require concrete evidence of network payload, DB persistence and reopening, not merely
  successful documentation output, mocked persistence or enabled buttons.
- Run focused existing lint/type/build/test commands; API sync after API changes.
- Record exact commands and evidence here without private CSV values.

## 9. Operational review and coordinator handoff - ✅ completed 2026-09-09

- Provide route, role, owned fixture, click sequence and expected results for each fix.
- Record developer operational feedback separately from automated regressions.
- Update this plan after every completed step with date, implementation note and detours.
- Report causes, fixes, remaining UI gates, conflicts and runtime lease handback to the
  coordinator. Do not describe unverified symptoms or gated UI as resolved.

> **Note implementazione (2026-09-08):** review manuale eseguita dal dev sulla build
> `3f50bf24...`; feedback/changes requested raccolti alle 16:34. Alle 17:08 U1
> confermato, U7 approvato, U4 approvato nella variante colonna/filtro multiutente e
> U9 esteso anche al desktop. Il seguito esecutivo e' nel Round 1 collegato sopra.
> E1/E2 hanno prove browser/API di persistenza; E3 ha staging/commit/reopen reali;
> E7/E8 hanno gruppo completo e ordinamento/payload verificati. Non si chiude la
> corsia prima delle correzioni richieste e della nuova verifica.

> **Note implementazione finali (2026-09-09):** R1 completed, followed by the directly
> requested [U7 Round 2](plan-phase00FeedbackImportUrgentRound2-Share.prompt.md).
> Current source and late test fixtures executed through targeted backend, component
> and real-browser flows; details and triage are recorded in both rounds. Original
> TEST database/uploads/sidecars restored at stopped temporary runtime, manual CSVs
> unchanged, private coherent backup retained. Final R2 build is served on 6041,
> PID 68600, index SHA256 `ab8b1458c1a49f1b835b3958d745e83e5a44f5d30e7c58d30ed4837941d0a4b6`.
> Operational checklist: `~/Documents/test-ui-urgenti/REVIEW-E-R2.md`.
> No commit/staging/push or production operation; no changes imported from A/B/C/D.
