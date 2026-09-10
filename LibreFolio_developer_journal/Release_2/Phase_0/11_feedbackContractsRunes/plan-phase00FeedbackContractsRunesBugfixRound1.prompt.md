# Group B - Manual review corrections, Round 1

**Date:** 2026-09-09. **Status:** checkpoint `74bfd9cf`; semantic merge with
`dev_release2`/`916f12bd` resolved and staged; combined automated acceptance
complete, developer visual review pending.
Previous: [B SP04-SP05 execution plan](plan-phase00FeedbackContractsRunes.prompt.md).
Source: current B worktree with checkpoint `74bfd9cf` merged against
`916f12bddf3eb9b8e834e4b9033eb52ce4bde25a`; the developer owns the pending
merge commit.

## 1. Accepted work and fixed scope

B10-01/03/04 and existing FX creation/edit/inversion were accepted by the
developer. Global Undo/Reset and normal-user read-only access also work.
The changelog records those delivered compatibility guarantees, not the
enhancements below before implementation.

"Other" is already implemented by visible unclaimed-key detection in
GlobalSettingsTab. All current standard keys are explicitly categorized or
managed by SchedulerConfigModal. The developer accepted its conditional
visibility: no empty-category UI, invented setting or backend change.

New scope:
- Standard amber confirmation instead of native browser confirm when locking
  global settings with a dirty draft.
- Verify last-owner deletion with both EDITOR and VIEWER remaining.
- Nonblocking creation-time FX sync for direct and multi-hop real providers.
- Existing formatting utilities, flagged FX labels and success-toast links.
- Asset-global creation success links only; contextual creation behavior stays.

No production DB correction, backfill, new migration, runtime/global cache
redesign, backend job platform, new provider, commit or integration of E's diff.
Only TEST fixtures may be created during an explicitly assigned runtime slot.

## 2. Findings and decisions

| Surface | Current evidence | Required change / boundary |
|---|---|---|
| GlobalSettingsTab, toggleLock | Native confirm in the current Runes file; Undo/Reset already correct. | Use existing ConfirmModal with warning=true/danger=false. Cancel/Escape keep draft and unlocked state; confirm discards and locks. |
| GlobalSettingsTab, isUnclaimedSetting/visibleCategories | Other appears only for visible unclaimed keys; scheduler-owned keys are excluded. | Keep behavior; retain current unknown-key coverage. |
| BrokerService.leave_broker:876+ | Counts OWNERs, not all members; last OWNER invokes delete_bulk(force=True). | No policy change. Add precise mixed-role cleanup evidence. |
| broker_user_access DDL | 001_initial.py:146-162 has ON DELETE CASCADE; db/session.py enables foreign_keys. ORM field declaration itself does not repeat ondelete. | Verify against a migrated TEST database; do not rewrite schema or data speculatively. |
| ACCESS-076 test | One OWNER + one VIEWER; checks HTTP absence, not physical grant-row absence. | Cover OWNER + EDITOR + VIEWER and read exact owned broker/access/user IDs after commit. |
| FxPairAddModal.handleSave | Awaits sync before oncreated/resetAndClose; reads result index0; builds unflagged ad-hoc text. | Snapshot request/identity, publish creation and close before awaiting sync; identify result by pair, not position. |
| FX creation hosts | FX list, dashboard and asset detail assume oncreated arrives after sync. Asset detail also emits a created-and-synced toast. | Separate creation and completion refresh; no premature "synced" message, no stale rates left on screen. |
| AssetModal.saveCreate | Existing immediate creation toast and nonblocking full-history request; contextual callers use the same component. | Opt-in link from asset-global only; retain default callbacks/toast count for dropdown/import/transaction callers. |
| assets/+page, handleSyncAsset/oncreated | Existing post-create sync success toast; there are already two potential sync triggers (modal + host). | Do not introduce a third request or silently redesign this pipeline. Link only the existing post-create success path; coordinate any independently owned duplicate-sync work with E. |
| buildFxSyncToast / fxPairHtml | Shared status formatter and emoji lookup already exist; current quote flag precedes the quote. | Reuse with a narrow opt-in outer-flag/link presentation for creation. Keep other callers' defaults. |
| ToastContainer.onPointerDown | Captures pointer except when target is a button; messages render HTML. | Anchors must retain native click/keyboard navigation; do not let swipe capture consume link clicks. |

Developer decisions explicitly obtained:
- Background auto-sync applies to both direct and multi-hop real-provider
  routes; MANUAL remains without automatic sync; edit mode remains unchanged.
- If no automatic sync starts on creation, show an immediate green creation
  toast with a clickable flagged pair.
- Asset-global may enrich existing success toasts with navigation; contextual
  asset creation must not gain links or new success notifications.

## 3. UX contract and compact sketches

These reuse existing project components; no new screen or alternate modal
system. Preserve translated text, focus/Escape behavior, dark mode and current
toast duration/dismissal.

The developer explicitly approved these standard warning/link sketches with
"Si, procedi cosi" on 2026-09-09. No broader UI redesign is authorized.

```text
GLOBAL SETTINGS - dirty draft, lock requested
+------------------------------------------------+
| ! Discard changes?                         [x] |
| You have unsaved changes. Discard all changes? |
|                                                |
|                    [Cancel] [Discard] (amber)   |
+------------------------------------------------+
Cancel / Escape -> remain unlocked, draft intact
Discard         -> original values restored, locked
```

```text
FX - creation with auto-sync
[Create] -> configuration saved -> modal closes
                                   sync continues

completion success toast:
+------------------------------------------------+
| check  Synced:                             [x] |
|        JAPAN_FLAG [JPY / RON] ROMANIA_FLAG      |
|        fetched / changed + existing details    |
+------------------------------------------------+
                   clickable -> /fx/JPY-RON

FX - no automatic sync
[Create] -> modal closes -> green "Pair created"
                          with the same flagged link

ASSET GLOBAL - existing success toast
check [Asset name] created ... [x]
      clickable -> /assets/<id>

CONTEXTUAL ASSET CREATE
existing selector is filled; no added link/toast
```

JAPAN_FLAG and ROMANIA_FLAG mean the real emoji from the currency utilities,
not images or literal words. The primary entity label is clickable, not an
unrelated new action button. Green is reserved for the actual success outcome.
Partial/failure/skipped outcomes must use honest existing formatter variants;
never label a failed sync as successful creation-and-sync.

## 4. Implementation seams

### R1-01 - Global discard

Only GlobalSettingsTab production behavior changes: store confirmation-open
state, reuse ConfirmModal, preserve the existing discard text and generic
cancel/discard translations, and isolate confirm/cancel handlers.
No write request is sent by discard. Other remains conditional.

### R1-02 - Last-owner verification

test-author extends the existing broker-access API coverage with one OWNER,
one EDITOR and one VIEWER. Confirm all grants exist before leaving. After the
committed response, check the broker and its exact grant rows are absent,
both remaining user accounts still exist, and an unrelated owned broker/grant
remains intact. Preserve existing transaction/file cleanup semantics.

If this exposes an actual persistence defect, stop and report the discrepancy:
do not repair an instance's rows or edit released migration001. Any necessary
generic schema/data migration requires separate approval.

### R1-03 - FX creation lifecycle

Capture primary slug, all created pair slugs, date range and client-session
generation before the modal resets. Creation failure keeps the modal/draft.
Successful configuration calls oncreated once and closes immediately.

If automatic sync is applicable, launch one browser-side promise for the
same requested pairs/date range. This is not a durable backend job: no
guarantee is added for closing the browser tab. Its success handler uses the
captured pair identity, current locale and the shared formatter; no result[0].
Ignore obsolete account-generation notifications/refresh using the existing
clientSession helpers, without dropping a valid request when only the modal
unmounts. Do not let completion mutate a newly reopened draft.

Creation and sync-completion callbacks must be distinct. Wire FX list,
dashboard and asset-detail hosts so their data refreshes after completion
even though creation closed early. Keep page-lifetime guards where necessary;
do not reload a destroyed page or claim an asset-detail pair is synced before
the request finishes. Reuse existing store invalidation/refresh seams.

No auto-sync on edit or MANUAL; absent date range also yields creation-only
feedback. Creation-only success gets a flagged detail link immediately.

**Approved corollary (coordinator, 2026-09-09):** also cover navigation to FX
detail before synchronization ends. The new helper exposes a typed,
creation-only completion subscription; the detail subscribes in synchronous
onMount before asynchronous initialization and cleans up on page/pair/account
changes. Completion matches canonical requested pairs and session generation.
Initial loading after an earlier completion uses the invalidated cache, not
the nonreactive notify ring or a forced reload.

The detail's rate loader guards **all** response-driven state and store writes
with a captured request epoch/pair/orientation/session, including the
no-signals path. It uses the existing gap detection, canonical conversion and
MAX/inversion primitives; the ungated ensureFxRangeLoaded call is not used for
this chart read because it merges before a caller can reject an obsolete
response. A delayed pre-sync success/404/error cannot overwrite the newer
chart, store, fetched intervals or loading state. The generic FX store and
other domains' cache lifecycle remain unchanged.

### R1-04 - Success links and formatting

Reuse buildFxSyncToast and fxPairHtml rather than copying currency/flag
lookups. Add only opt-in creation label/link options, keeping existing helper
callers compatible. Localize new/previously hardcoded creation wording with
existing keys where possible; any new keys go through the i18n CLI in EN/IT/FR/ES.

Use safe internal href construction and escape untrusted asset names/text;
do not interpolate raw names or arbitrary URLs into HTML. A small shared
internal-link helper is acceptable if existing prior art is absent.
ToastContainer must ignore anchor starts in its swipe-capture path, while
keeping dismissal gestures and the close button unchanged.

AssetModal receives a default-off creation-link option set only by the
asset-global host. The existing post-create host sync toast may use the same
link, gated at that caller, not for every manual sync everywhere. No new toast
or auto-navigation in TransactionFormModal/ImportWizardModal; selector
population remains the current callback contract. No E changes are copied.

## 5. Files, ownership and execution order

| Increment | Intended production files |
|---|---|
| R1-01 | frontend/src/lib/components/settings/tabs/GlobalSettingsTab.svelte |
| R1-02 | No production edit expected; backend/test_scripts/test_api/test_broker_access_api.py via test-author |
| R1-03 | FxPairAddModal.svelte; FX list, dashboard and asset-detail creation/completion handlers; fxCreationSync.ts; approved FX detail completion/initial-load corollary |
| R1-04 | utils/sync/syncToastHelpers.ts; utils/providerHelpers.ts; ToastContainer.svelte; narrow safe-link helper; AssetModal.svelte; assets/+page.svelte |
| Shared | Relevant tests and runner registrations; four locale JSON files via CLI; CHANGELOG and this journal chain |

Coordinator must reconcile AssetModal, assets/+page and assets/[id]/+page
ownership with E before those edits. A's DataTable/UserSearchSelect primitives
remain untouched. Main checkout, backlog09 and E's worktree are not edit targets.

E's read-only handoff (2026-09-09) confirms that its AssetModal changes affect
probe/draft guards, full edit data, classification patches and relative modal
stacking, but **not** the existing saveCreate success/callback/background-sync
lifecycle. Its asset-global oncreated callback still loads assets and invokes
handleSyncAsset. The duplicate sync opportunity is pre-existing and unfixed
in E; B adds no third request or unrelated pipeline repair. E did not modify
asset detail, dashboard, the two toast/format helpers or ToastContainer.
Future integration must retain E's full edit-loader/session guards, explicit
classification null semantics, probe state and relative zIndex. This handoff
does not authorize copying E's diff or granting a runtime lease.

Integration policy from master06 section14: one complete package at a time
returns to dev_release2, with Git history operations performed by the developer.
The developer checkpointed B at `74bfd9cf`, then started the merge from E/runtime
integration commit `916f12bd`. The five textual overlaps were reconciled
semantically without replacing whole files or applying global ours/theirs.
Combined evidence is recorded below; old `4a73f5f6+B` results remain historical.

## 5.1 Historical checkpoint before updating the base - 2026-09-10

The developer created B checkpoint
`74bfd9cf021af885abfb136c4e4f08b6a526f87a` from the package below, then
started the merge from
`916f12bddf3eb9b8e834e4b9033eb52ce4bde25a`. The inventory remains the
pre-merge handoff record; the agent did not create either commit.

Checkpoint inventory:

| Item | Count / state |
|---|---|
| Tracked modified files | 52 |
| New untracked files, all intended | 10 |
| Total package files | 62 |
| Tracked diff | 4,358 insertions / 633 deletions |
| New-file content | 3,327 lines |
| Whitespace check | Clean |
| Dependency manifests / lock files | Unchanged |
| Alembic files / production DB | Unchanged / absent |

The ten new files are the two portable B plans, two backend regression suites,
the FX creation service plus its two tests, FxPairAddModal and ToastContainer
tests, and the typed internal-link helper plus its test. None is disposable.

Generated/runtime material is deliberately excluded from the checkpoint:
OpenAPI/generated TypeScript, frontend build and `.svelte-kit`, node_modules,
Playwright reports/results, `.testLog`, pytest/Ruff caches, test SQLite,
test uploads/reports/logs, MkDocs site/vendor cache, runner cache/campaign and
platform `.DS_Store` files. Generated API artifacts must be regenerated from
the combined contracts after integration, never merged by hand.

### Six direct overlaps with `916f12bd`

| File | Reconciliation required after developer merge |
|---|---|
| `CHANGELOG.md` | Keep the target's single v1.1.1/Unreleased chapter and E entries; insert B's FX-route and Runes/creation-feedback entries into its existing sections. Never retain two Unreleased headings. |
| `09_feedbackJobs/06_piano_sprint.md` | Preserve target section 14, E integration/runtime-isolation history and current global coordination. Reapply only B's portable-plan link, delivered/checkpoint status and Round1 open state; update the baseline after integration. |
| `09_feedbackJobs/README.md` | Preserve target E completion/integration policy. Add B's plan link and status without restoring the older B runtime-ownership wording. |
| `AssetModal.svelte` | Start from E's providerProbeState, manual-edit protection, full edit payload/classification patch and zIndex lifecycle. Reapply only B's default-off `linkCreatedAsset` prop, safe-link imports and linked create-success label. Do not replace the file or revert E's loader/probe logic. |
| `assets/+page.svelte` | Start from E's async `loadAssetEditData`, session/request guards and busy state. Reapply only the link option/imports and `handleSyncAsset(..., true)` presentation for the existing asset-global success path. Preserve contextual defaults and acknowledge the pre-existing duplicate sync opportunity without adding another request. |
| `scripts/test_runner/_frontend_utility.py` | Keep target's new test-name filtering, isolation/runtime behavior and E registrations. Insert B's four paths (`entityLink`, `fxCreationSync`, `ToastContainer`, `FxPairAddModal`) into the current core/component lists rather than restoring the older runner file. |

Additional semantic dependencies without textual overlap:
- target changes to Broker API/service and the isolated test runner require the
  mixed-role ACCESS-076 test to be rerun on the combined revision;
- target ModalBase changes require the amber GlobalSettings confirmation tests
  to be rerun;
- all AssetModal tests must be evaluated against E's integrated component,
  not treated as certified by the old B build;
- previous B00-B09 green results remain valid evidence for `4a73f5f6+B`, not
  for `916f12bd+B`.

Combined validation uses only the B lane:
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
--test-port 6151 --data-dir /tmp/librefolio-r2-b ...`.
No agent command uses `--force`; the runner may internally recreate its own
isolated fixture database as designed.

## 5.2 Semantic merge and combined validation - 2026-09-10

The developer started `git merge dev_release2`; the agent resolved and staged
the five reported conflicts without creating the merge commit:

- `CHANGELOG.md`: retained one canonical undated `Unreleased` chapter and
  integrated B entries into E's sections.
- `06_piano_sprint.md` and `09_feedbackJobs/README.md`: retained E/runtime
  history and section 14, then re-added only B checkpoint/plan status.
- `AssetModal.svelte`: retained E's provider-probe, full payload,
  classification and stacking work; re-added only B's default-off asset link.
- `assets/+page.svelte`: retained E's async full edit loader/session/busy
  guards; re-added only B's asset-global link presentation, with no third sync.
- `_frontend_utility.py`: retained E/runtime registrations and filtering, and
  contains all four B registrations.

Static integration exposed three real seams and two stale test assumptions:
the ignored generated client needed regeneration from the combined backend;
the asset route list may omit `items`; and the generated FX conversion union is
wider than the validated scalar wire shape. These are handled by local API
regeneration, `items ?? []`, and an explicit scalar guard at the FX store
boundary. Test fixtures now copy readonly request steps into mutable response
steps. The bundled changelog test accepts exactly one undated `Unreleased`
chapter while still requiring dates on released chapters. ACCESS-076 cleanup
handles the exact test-owned bootstrap administrator on an otherwise empty
lane without weakening the production sole-admin guard.

Combined evidence so far:

| Check | Result |
|---|---|
| Runtime isolation | 133 passed |
| Test registration/reachability | 196 backend files, 77 E2E specs and 195 frontend unit files registered/reachable |
| Backend Ruff | Passed |
| Frontend Svelte check | 0 errors; 41 existing deprecation warnings in the two migrated Runes files |
| Frontend core units | 1,916 passed |
| Frontend component units | 1,722 passed |
| FX route schemas | 34 passed |
| Signal schemas | 471 passed |
| AI Export schemas | 16 passed |
| AI Export structural guards | 78 passed, including normal and optimized Python |
| SignalService | 45 passed |
| FX API unit / HTTP / sync / service | 29 / 21 / 10 / 5 passed |
| Last-owner physical cascade | 1 passed; OWNER, EDITOR, VIEWER, transaction and control rows verified |
| Settings Runes E2E | 2 passed |
| Broker-sharing Runes E2E | 2 passed |
| Explicit combined frontend build | Passed after API regeneration; 0 Svelte errors |
| FX creation/early-detail E2E | 11 passed |

The first combined FX creation E2E run passed all six new lifecycle,
navigation and stale-response cases plus four legacy cases. Its last legacy
route-section case exposed obsolete selector and seeded-route assumptions.
The repaired test now owns its route discovery responses, targets the exact
SearchSelect option test ID and waits for the options-close state. Its focused
rerun passed 1/1 and the complete action then passed 11/11.

Order: record acceptance -> agree scope/layout -> amber confirmation and
mixed-role characterization -> shared link/format seam -> FX async lifecycle
and all hosts -> asset-global opt-in -> integrated tests -> developer review.

Only the designated B integrator executes commands, with a fresh coordinator
lease before tests/build/server/i18n. During analysis the coordinator was told
it could release/reassign its current B review server; this agent did not stop
that parent-owned process. No runtime command has been executed for Round1.

## 6. Test and review acceptance

All test authoring/repair goes through test-author. Target existing registered
component-unit and sync-helper/core-unit actions, plus a narrowly registered
FxPairAddModal/ToastContainer test if absent. Extend only relevant settings,
broker-access and creation E2E cases, using owned TEST IDs.

Required witnesses:
- Native window.confirm is not called; amber ConfirmModal cancel/Escape and
  confirm preserve the specified draft/lock semantics.
- Other still appears for unclaimed visible keys and not for scheduler-only
  keys; no dummy setting is introduced.
- Physical last-owner cleanup with both remaining roles, intact users and
  unrelated grants; migrated TEST DB only.
- Deferred FX sync does not hold the creation modal open; creation failure
  still does. Result reorder, partial/failure/skipped, no-sync/MANUAL, reopened
  modal and account change do not produce wrong success or links.
- FX hosts refresh on actual sync completion, not just before data arrives.
- Flag order and emoji come from the shared utility; no duplicate formatting.
- Successful creation links target the correct detail, survive pointer and
  keyboard interaction, and escape hostile names safely.
- Asset-global links occur only in existing success toasts; contextual asset
  selectors still fill normally without additional links/notifications.

No real provider calls are needed: use deterministic mocks. No blanket suite
reruns, database resets or installs during planning. Final review reports
these new R1 behaviors separately from the accepted B10 cases.

## Progress

| Step | Status |
|---|---|
| R1-00 Feedback/changelog | Recorded 2026-09-09 |
| R1-01 Amber confirmation | Source/tests complete; unrun after Round1 |
| R1-02 Mixed-role cleanup proof | Regression complete; unrun after Round1 |
| R1-03 FX nonblocking creation/sync | Source/tests complete, including early-detail stale-response guard; unrun after Round1 |
| R1-04 Existing success links/flags | Source/tests/docs complete; unrun after Round1 |
| R1-05 Targeted acceptance | ✅ 2026-09-10 - combined static, unit, API and targeted E2E checks green on lane 6151 |
| R1-06 Developer review | Pending real combined UI/viewport review; automation does not replace this gate |

> **Note implementazione** (R1-01 authoring, 2026-09-09): GlobalSettingsTab now
> opens the existing amber ConfirmModal instead of calling browser confirm.
> Cancel/dismiss retains the draft; confirm undoes and locks. No new locale
> key or backend write is needed. Other remains conditional as accepted.
> Validation is pending a newly allocated runtime slot; shared creation/toast
> surfaces still require the coordinator's ownership handoff before editing.

> **Note implementazione** (coordination, 2026-09-09): B has no R1 test/build/
> generation/DB command running. The coordinator's review server 76024 is
> untouched and has reload disabled; prepared R1 source is not claimed as its
> served build. The coordinator was explicitly told that E may take its brief
> local-check lane. B awaits a new slot before any validation command.

> **Note implementazione** (source handoff, 2026-09-09): the coordinator
> explicitly granted source-only ownership of the Round1 shared surfaces.
> The typed internal-detail-link helper restricts destinations to asset IDs and
> FX slugs and escapes labels. Asset-global opts in to links in its existing
> creation/sync success messages; contextual callers remain default-off.
> FX formatter options reuse currency metadata and put flags outside the
> linked pair. Toast pointer handling now leaves native anchors alone.
> The coordinator stopped its own review server and assigned runtime to E;
> no B validation command has run in this round.

> **Note implementazione** (R1-02 test handoff, 2026-09-09): ACCESS-076 now
> prepares OWNER/EDITOR/VIEWER on the target and an unrelated control broker,
> then checks physical broker/grant/transaction rows after the API commit,
> retained accounts and untouched control grants. Inspection uses guarded
> SELECTs against the exact TEST database. Static review caught cleanup using
> the create-result key broker_id instead of the delete-result key id; the
> author is correcting that before execution. No persistence defect has been
> observed and no backend or migration change was made.

> **Note implementazione** (R1-03 source handoff/corollary, 2026-09-09): the
> creation helper and three hosts are integrated, with distinct callbacks,
> immutable input context, session guards and one aggregate status notification.
> Initial pre-sync reads keep their ordinary missing-data behavior rather than
> falsely turning a successful later sync yellow. The coordinator approved
> and the parent implemented the early-entered FX-detail corollary above; its
> focused tests are being added before the local readset is frozen.

> **⚠️ Fuori pista** (focused source review, 2026-09-09): two new lifecycle
> defects were caught before runtime. Modal teardown must not cancel a
> same-account configuration mutation that was already admitted: request
> continuation now uses the session guard, while draft updates/creation-close
> callbacks use the modal admission guard. This also prevents abandoning edit
> after DELETE but before its replacement POST; detached errors remain visible.
> The FX-detail completion reload now propagates transport/server failures to
> the aggregate refresh-warning path, while normal initial/pre-sync 404
> missing-data behavior and stale-response suppression stay unchanged.
> Test-author is adding regression witnesses; the local checkpoint is held
> until those files are stable.

> **Note implementazione** (review follow-up, 2026-09-09): the focused
> read-only reviewer found no significant issue after those two fixes.
> This is source-review evidence only, not a passing runtime result.

> **⚠️ Fuori pista** (combined validation, 2026-09-10): the first isolated
> ACCESS-076 run proved the full physical cascade but failed cleanup because a
> fresh database promotes its first account to sole administrator. The test now
> deletes ordinary owned accounts through the API and, only for the exact
> sole-admin rejection, verifies and deletes that exact test-owned row through
> `user_service`; the focused rerun is green and the production guard is intact.
> The first FX E2E run similarly passed all new behavior but exposed a legacy
> helper looking for nonexistent `role=option` elements and a fixed EUR/CAD pair
> already present in seeded routes. The repaired case uses stable test IDs and
> browser-local owned provider/route responses; focused and full reruns are green.

> **Note implementazione** (R1-05, 2026-09-10): the combined frontend was
> rebuilt explicitly after regenerating the ignored API client, so E2E evidence
> does not rely on the pre-integration bundle. All automated gates listed above
> are green. No merge commit was created by the agent; the developer still owns
> the merge commit and final real-UI/viewport verdict.
