# Group B - Contracts and Runes (SP04-SP05)

**Approved plan:** revision 2, 2026-09-07.
**Execution baseline:** `4a73f5f63447e01b51993afb2e3c73e2c22a9a28`.
**Status:** B00-B09 delivered; manual review received, `changes_requested`.

Previous/master: [sprint plan, sections 4/10-12](../09_feedbackJobs/06_piano_sprint.md).
Scope source: [structural backlog](../09_feedbackJobs/00_backlog_strutturale_P4.md).
Only the coordinator writes forward links in those files.

This is the portable execution record of the approved session plan and its
AI/SignalResult, FX and Runes evidence annexes. The source observations below
refer to the pinned baseline, not the subsequent edited line numbers.

## 1. Goal and non-negotiable boundaries

| Family | Boundary | Deliverable |
|---|---|---|
| S6 6.11 | Internal AI Export contracts | Seventeen structural guards remain effective under Python -O. |
| S6 6.2 | Backend/API/generated client/frontend | Required response-only is_chain and deterministic providers_used membership, with lossless ordered traversal retained. |
| P4-6 = S6 6.7 | Internal SignalResult validation | Declarative ordered rules and named predicates, exactly equivalent behavior. |
| P4-5 | Frontend state/bindings | Three Svelte 5 migrations with unchanged UI and behavior. |

**No production database repairs.** B02 changes Python guards over in-memory
catalog definitions, not database rows. No persistent schema changes, backfill,
rate/source rewriting, direct SQL repair or production-data copy is planned.
Any newly required persistent correction requires separately approved scope
and a generic incremental Alembic migration, never instance-specific edits.
New FX response metadata is not persisted and needs no migration.

Out of scope: FIFO, BRIM, asset_source/refresh, execute_batch, cache lifecycle,
onboarding, privacy, Tool implementation and new signals. S6 6.3 remains closed
by removal; 6.12 remains resolved by one settings registry and two services.
TRY003 stays frozen. No staging/commit/push/rebase/reset. Wiki and TODO_FUTURI
remain untouched. No general cleanup of neighboring validators or UI.

G0 is complete: the developer manually aligned the initially wrong worktree
from d192ffa1 to 4a73f5f6. All planning evidence used the requested Git object;
no repeated investigation after alignment. The native gate approved revision2;
the developer explicitly requested implementation at 23:16 on 2026-09-07.
Shared runtime/generated/runner ownership still requires coordinator slots.

## 2. Incremental execution and immediate progress

| Step | Scope | Status |
|---|---|---|
| B00 | Approve contracts, align baseline, publish this portable plan | ✅ 2026-09-07 |
| B01 | Characterization by test-author, independent of new implementation | ✅ 2026-09-08 - all authoring handoffs and baseline requirements accepted |
| B02 | Seventeen AI Export guard replacements, no DB operation | ✅ 2026-09-08 - targeted structural/import/catalog acceptance |
| B03 | FX response schemas/API and ordered-provider naming | ✅ 2026-09-08 - schema/handler/ORM/sync and real HTTP cases |
| B04 | Central generation and typed FX consumers | ✅ 2026-09-08 - generated/type/build and 14 selected FX UI cases |
| B05 | Ordered SignalResult table after baseline oracle | ✅ 2026-09-08 - equivalent oracle, service and risk-consumer acceptance |
| B06 | PreferencesTab Runes | ✅ 2026-09-08 - component and owned-data E2E parity |
| B07 | GlobalSettingsTab Runes | ✅ 2026-09-08 - component and owned-data E2E parity |
| B08 | BrokerSharingPanel Runes | ✅ 2026-09-08 - component, F3 and modal/Info E2E parity |
| B09 | Shared registration, targeted runtime and FX documentation | ✅ 2026-09-08 - integrated automated acceptance and backend review |
| B10 | Real UI walkthrough, developer feedback and corrections | Partial acceptance 2026-09-09; corrective Round 1 open |

> **Note implementazione** (B00, 2026-09-07): approved contracts and evidence
> consolidated here; source baseline and production-data prohibition retained.
> AI code/test authors own separate files. Shared writer/runtime reservation
> requested from the coordinator; no server, DB, build or API sync started.

> **⚠️ Fuori pista** (baseline): worktree initially came from main despite the
> requested base. Planning used git show at the requested commit; the developer,
> not the agent, performed the later alignment.

> **Note implementazione** (runtime handoff, 2026-09-07): coordinator granted B
> the exclusive test/build/API-generation/shared-writer lease. C definitively
> uses About; GlobalSettings and the other two Runes remain B-owned. A's future
> DataTable/UserSearchSelect opt-ins do not change their current contracts.
> All specialist agents write only their assigned files; the B integrator is
> the sole command executor. Coordinator-owned forward links in backlog09 are
> intentional changes and are preserved.

> **⚠️ Fuori pista** (bootstrap, 2026-09-07): first test-mode API sync failed
> because the new isolated Python 3.13 worktree environment lacked argcomplete.
> Dependencies were restored from the lock, then through dev.py install;
> no lock or manifest changed. Port 6041 had no listener, test data resolves
> inside this worktree, and no production DB was accessed or created.

> **Note implementazione** (B04 handoff, 2026-09-07): test-mode api sync
> succeeded. OpenAPI input FXConversionRouteItem still has only base, quote,
> priority and chain_steps; read/result schemas require the two new fields.
> Frontend mappings now consume is_chain and preserve ordered steps; POST step
> projection retains only from/to/provider. Full frontend acceptance is pending.

> **Note implementazione** (B02 preliminary evidence, 2026-09-07): AST inspection
> finds exactly 34 remaining AI Export assertions and zero assertions in the
> seven structural target modules. Application initialization/OpenAPI export
> succeeded in normal and optimized Python, both in test mode. Negative
> per-guard subprocess acceptance still awaits the test-author handoff.

> **Note implementazione** (B02 complete, 2026-09-08): the stable test-author
> file covers 74 import-failure cases, four builder failures and four healthy
> controls across normal/-O. The services ai-export runner passed those classes
> together with the selected import-cycle/catalog/mapping/temporal regressions
> in 3m28s. Command and result: `.testLog/services__AI-Export-service-tests.log`.
> No contextual assertion, catalog ID/version or failure placement changed.

> **Note implementazione** (normal test setup, 2026-09-08): the standard services
> runner created the previously absent worktree TEST SQLite database using
> existing migrations. It did not use a backend server or production database;
> no migration file was added/changed. Its automatic archive is a TEST snapshot,
> not a copied production-data repair.

> **Note implementazione** (B09 backend integration, 2026-09-08): the complete
> services ai-export family passed 922 tests after the SignalResult table was
> wired. New test files are registered and reachable: check-orphans reports all
> 194 backend files, 178 frontend unit files and 67 E2E specs reachable.
> Backend lint passed after one safe C420 fixture-comprehension autofix.
> These results do not close the pending Runes triage or developer UI review.

> **Note implementazione** (B05 preparation, 2026-09-07): private immutable
> presence/predicate descriptors and ordered tables are prepared without
> replacing the active imperative validator. The independent reference suite
> must pass against that active baseline before wiring the new implementation.

> **Note implementazione** (B03 complete, 2026-09-08): 34 FX schema, 24 route
> handler, eight ORM-property and four sync tests passed; four existing real
> HTTP CRUD/MANUAL-sentinel cases then passed against the worktree test server.
> Tests preserve exact repeated-provider response and persisted source strings.
> Unknown-provider rollback diagnostics are covered by handler doubles; their
> metadata does not imply successful persistence.

> **Note implementazione** (B05 complete, 2026-09-08): all 471 schema tests
> passed first with the imperative validator active. After wiring the ordered
> private rule table, the same 471 passed, including the 3584/128 inner grids,
> raw boundaries, error order, schemas and dumps. All 45 SignalService tests and
> four selected risk-result consumer cases also passed. Existing series helpers,
> neighboring validators, enums and public fields remain unchanged.

> **⚠️ Fuori pista** (CLI, 2026-09-08): this dev.py version is verbose by
> default and rejects --verbose. The rejected invocation ran no test; commands
> were corrected using the current --help, without changing runner behavior.

> **⚠️ Fuori pista** (frontend acceptance, 2026-09-08): two initial TypeScript
> flow-narrowing errors were resolved by declaring the union through the
> $state generic. Type checking then passed with 41 legacy directive/component
> deprecation warnings intentionally retained. Component-unit yielded
> 1276 passed / two new-regression failures; test-author is triaging a dirty
> Reset observation and a same-ID rerender/refetch boundary before any verdict.

> **Note implementazione** (B06-B08 complete, 2026-09-08): all 1278 component
> tests now pass, followed by four owned-data real E2E workflows. The test-only
> fixes preserve exact payloads, one ACL read and false-at-close F3 assertions:
> bulk Reset, not the intentionally hidden dirty row Reset, proves late
> defaults were consumed; a compiled legacy host changes only readOnly instead
> of Testing Library replacing its raw props container. Verdict: assumption
> in both tests, not product defects or flakiness. No additional production
> behavior change was needed. The frontend build succeeds; final developer
> UI review remains a separate unclosed gate.

> **Note implementazione** (B06-B08 authoring, 2026-09-07): all three Runes
> files are stable and the diff preserves markup/styles/event handlers. Zero
> legacy reactive statements remain. Sharing retains the bindable dirty
> contract, only the two specified effects and await tick before close.
> These code handoffs are not runtime acceptance; test-author files remain
> separately owned until their own handoff.

> **Note implementazione** (B09 documentation substep, 2026-09-07): docs-writer
> updated only the English FX configuration page. Review corrected a false
> implication that extra metadata inputs are rejected (they remain ignored)
> and replaced adjacent JSON objects with a valid complete GET envelope.
> The example parses and distinguishes two ECB hops from one membership entry.
> No new links, translations, nav changes or broader FX-doc rewrite.

After every completed step, update this table immediately with date and
implementation note. Record detours and cross-link any corrective round.

## 3. AI Export: exact guard inventory and timing

Paths below are under `backend/app/services/ai_export/`.

| Baseline file:line | Exact invariant | Exception |
|---|---|---|
| components/catalog.py:219 | len(ALL_FOUNDATION_COMPONENTS) == 67 | ComponentRegistryError |
| components/catalog.py:220 | len(ALL_REAL_COMPONENTS) == 67 | ComponentRegistryError |
| components/catalog.py:221 | len(ALL_COMPONENTS) == 67 | ComponentRegistryError |
| components/asset_fx_registry.py:140 | Fragment count == Asset count + FX count (26) | AssetFxRegistryError |
| components/asset_fx_registry.py:141 | Asset IDs count == 14 | AssetFxRegistryError |
| components/asset_fx_registry.py:142 | FX IDs count == 12 | AssetFxRegistryError |
| components/asset_fx_registry.py:143 | Union ID cardinality == 26 | AssetFxRegistryError |
| components/portfolio_broker_registry.py:146 | Fragment count == Portfolio + Broker (41) | PortfolioBrokerRegistryError |
| components/portfolio_broker_registry.py:147 | Portfolio IDs count == 21 | PortfolioBrokerRegistryError |
| components/portfolio_broker_registry.py:148 | Broker IDs count == 20 | PortfolioBrokerRegistryError |
| datasets/catalog.py:867 | Public datasets count == EXPECTED_PUBLIC_DATASET_COUNT (8) | DatasetRegistryError |
| datasets/catalog.py:973 | Builder-local specs count == EXPECTED_DATASET_COUNT (40) | DatasetRegistryError |
| analyses/catalog.py:241 | Public analyses count == EXPECTED_ANALYSIS_COUNT (11) | AnalysisRegistryError |
| temporal/policy.py:80 | Policy outer key set == BucketDetailLevel | Local IndicatorPolicyError(ValueError) |
| temporal/policy.py:81 | Every row key set == SignalTemporalClass | Same |
| dependencies.py:112 | Mapping keys == DetailLevel | Local DetailLevelMappingError(ValueError) |
| dependencies.py:113 | Mapping values == BucketDetailLevel | Same |

Replace in place, preserving predicates, messages where supplied and order.
Sixteen guards remain import-time, after their existing initialization; the
dataset specs guard stays inside build_dataset_registry before DatasetRegistry.
Integration checks at components/catalog.py:196-217 still fail earlier.
Leave all 34 contextual assertions unchanged. No catalog/ID/version/order,
sampling, renderer, successful payload or generic assertion-framework change.
Preserve eager package initialization and existing type-only/lazy import seams.

Test-author owns the new
`backend/test_scripts/test_services/test_ai_export_structural_invariants.py`.
Fresh normal and -O children use explicit condition/exit checks and healthy
67/40/11 controls. A test-only in-memory import loader injects malformed
collections immediately before the real guard, with a continuation marker
afterward; never replace the predicate/raise or use line numbers as anchors.
Validate unambiguous anchor, injection, exception type and correct phase.

Witnesses: missing/extra entries for 12 length checks; cross-domain and
within-domain duplicates with unchanged tuple lengths; missing/extra outer
policy keys and keys in every inner row; missing/extra mapping sources;
duplicate/missing or unexpected destinations with source coverage retained.
The builder fault must import successfully before invocation. No child pytest
assert rewriting, global optimization ban, DB fixture, network or prompt probe.

## 4. FX: response-only projection, not provenance repair

ORM properties in `backend/app/db/models.py:898-911` remain authoritative:
is_chain from step count; internal providers_used remains a set. The response
uses sorted(route.providers_used), a unique deterministic list of configured
codes including MANUAL and unknown submitted codes in failed configuration
results. It does not describe actual successful fetching.

| Path | is_chain | Membership | Traversal retained |
|---|---|---|---|
| MOCKFX | false | [MOCKFX] | One step |
| MOCKFX, MOCKFX | true | [MOCKFX] | Both steps and CHAIN:MOCKFX+MOCKFX |
| SNB, ECB | true | [ECB, SNB] | SNB then ECB |
| MANUAL | false | [MANUAL] | Manual-only sync remains skipped, singular provider_used=None |

Different fallback routes are not hops. Mixed MANUAL multi-step input remains
rejected by schemas/fx.py:314-366; repeated providers are legal, repeated
unordered currency edges are not. Preserve direction, aliases and rollback.

Files: schemas/fx.py:369-443 adds response-only FXConversionRouteReadItem and
uses it in FXConversionRoutesResponse; FXConversionRouteResult also requires
both fields. Keep input FXConversionRouteItem unchanged. No False/[] defaults
that hide an unmapped branch or retroactive extra-forbid input policy.

api/v1/fx.py:735-858 projects metadata in GET, created/updated POST results,
unknown-provider results and HTTP400 model_dump details. Error metadata derives
from an unattached ORM candidate; never filter unknown codes or write it to DB.
422 and delete/sync results do not acquire these fields.
services/fx.py:998-1001,1108-1109 only renames ordered provider lists; no sorting
or sets in CHAIN source assembly. ORM edit is only a membership docstring.

Consumers: FX list loadPairSources:291-321, detail:659-682 and
FxPairAddModal:107-115,226-267 use generated read types and is_chain. POSTs
allowlist base/quote/priority/chain_steps and from/to/provider within steps:
no GET spreads or type-only Omit. fxRoutesStore:62-78 projection/lifecycle is
unchanged; FxPairConfig:60-75 may need only its providerCode comment clarified.
FxTable.providerChainHtml:140-162 renders any populated steps, including direct
routes: do not replace that presentation check with is_chain. No new badges.

Tests: ORM set/repeats/MANUAL; dedicated new test_fx_route_schemas.py;
test_fx_api_unit GET/create/same-priority direct-chain-direct/error/rollback;
spoofed input cannot guide output; exact duplicate-provider sync AND DB source;
cache-hit and ordered fallback cases with mocks; synthetic GET fixtures and
intercepted POST allowlists. Preserve test_fx_conversion behavior.
Existing live tests accepting failed/skipped outcomes are not acceptance proof.

## 5. SignalResult: ordered private matrix

Only production target: `backend/app/schemas/signals.py:1019-1134`.
Private immutable non-Pydantic descriptors combine grouped presence rules and
named predicates in the original order. No opaque lambdas or public fields.

| Status | Availability / warmup | Series / annotations | Warnings / error |
|---|---|---|---|
| OK | Both present, computable/complete, no partial availability | Series nonempty, no missing output; annotations optional | Warnings optional, error absent |
| PARTIAL | Both present, computable; incomplete warmup OR partial coverage OR PARTIAL_UNDEFINED_METRIC | Series nonempty, annotations optional | Warnings nonempty, error absent |
| UNAVAILABLE | Both present, noncomputable; complete warmup allowed | Both empty | Warnings optional, error absent |
| FAILED precompute | Both absent | Both empty | Warnings optional, error present |
| FAILED runtime | Both present, computable; partial/incomplete allowed | Both empty | Warnings optional, error present |

Precompute codes: UNKNOWN_SIGNAL/INVALID_PARAMS/PLANNING_ERROR. Runtime:
COMPUTE_ERROR/INVALID_OUTPUT/CONTRACT_VIOLATION. Classify by error.code, not
details.phase (PLANNING_ERROR may say orchestration).
Object presence means not None; collection emptiness is separate.

Precedence: series key -> semantic ID -> date/cardinality alignment FIRST for
every status. OK then checks metadata, series, computable/complete, full
availability, no missing values, error absent. PARTIAL: metadata, series,
computability, warning, justified partial state, error absent. UNAVAILABLE:
metadata, empty series/annotations, noncomputability, error absent. FAILED:
empty output, structured error, code-family metadata, runtime computability.
Finally required-point equality -> warmup flags -> risk_metadata/data_quality
presence parity. Guard before dereference; retain grouped messages.

Keep nested validators unchanged, including MISSING_SOURCE_CAPABILITY's
existing classification irregularity. Empty data_quality {} is present/valid;
empty risk_metadata is not. Valid risk pairing may accompany any status.
Zero is not missing; all-None/empty-point series fail earlier nested validation.
No new warning/reason, annotation-date or risk-cardinality coupling.

Test-author first extends test_signal_schemas.py with a pinned imperative
test-only reference model and public schema capture. Compare independent raw
payloads, fixed timestamps, acceptance, ordered loc/type/msg and dumps.
Planned grids: 3584 presence combinations (expected accepting cells 40) and
128 availability modes (31 nested-valid); confirm fixtures/counts before
replacement. Add co-fault precedence, both metadata/parity directions, every
series kind and None/zero/band boundaries. Never derive oracle expectations
from the new table or use model_construct for public-path coverage.
Existing service/risk-result tests remain regression selections, not edits.

## 6. Runes: same UI, binding and lifecycle

Only three migration targets: PreferencesTab (9), GlobalSettingsTab (10),
BrokerSharingPanel (24). Shared controls and legacy parents are not additional
migration targets.

Preferences: local state to $state; nine pure $derived values. Keep onMount
Promise.all reads and current loading/fallback behavior. Non-default compares
original with global defaults. Per-field PUTs, bulk order language/currency/
theme, continued attempts after refusal and partial outcome remain unchanged.
Apply language/theme/store only after success. Reset stages; Undo restores.

Global: canEdit via $props; local $state; ten derivations. Category labels keep
explicit currentLanguage dependency; non-default compares edited values.
Keep initial sequential settings/scheduler reads, explicit scheduler-save
reload, lock/discard, one bulk PATCH, Other/hidden keys/placeholder behavior,
DOM ref and listener cleanup. Scheduler/cache internals unchanged.

Sharing: typed $props, hasChanges=$bindable(false); local $state; pure derived
lists/percentages/candidates/chart; one derived role-options array. A small
effect publishes local dirty state; reload effect tracks only brokerId and
uses untrack for loadAccesses. Keep all explicit retry/self-demote reloads.
No new fetch on editing/auth/locale/readOnly changes or new race policy.
Keep independent original/current ACL copies and original JSON dirty projection.

Full ACL PUT, not changed grants only. Save success copies baseline, calls
onChanged/feedback, clears saving, then await tick before onCancel. Existing
BrokerSharingPanelHarness must first observe true and observe false AT close.
Embedded Info stays open. Preserve readOnly editing guards but member
self-service outside them, last-owner removal/demotion protections, EDITOR
self-demote, danger last-owner leave and goto -> onChanged -> onCancel order.
Failures retain draft and do not emit success callbacks. No reentrancy cleanup.

Test-author extends the three component tests for fetch cardinality/trigger,
live locale, listener cleanup, reset/refusal dirty binding and self-demote.
Focused real-UI cases in settings.spec.ts/broker-sharing.spec.ts use owned IDs,
real persisted values, existing setting-save/undo/reset and settings-save-all
handles. Existing persistence-named tests often prove only tab visibility and
sharing helpers use first records; do not inherit those assumptions.

## 7. Ownership, resource queue and future Fleet

Four independent families; no hard AI -> FX -> matrix -> Runes chain.
Default Runes order Preferences -> Global -> Sharing; optional per-file split
only after binding/lifecycle freeze. Astra owns invariants/schema/semantics/
review. Smaller models are allowed only for agreed typed FX mapping and pure
Preferences derivations; Sharing stays Astra. test-author owns test files;
docs-writer owns directly related English documentation.

One coordinator-owned writer for frontend/src/lib/api/openapi.json and
generated.ts, runner/indices/i18n and changelog. Preserve existing generation
postprocessor. front build and E2E auto-build ALSO call API sync and take that
lock. Register new AI file in AI_EXPORT_SERVICE_TEST_PATHS and new proposed
schemas fx-routes action centrally. No concurrent shared-file writes.

One runtime queue, including manual review. Mocked FX sync tests remain
exclusive as registered, not pure: they mutate shared test rates/routes.
Worktrees do not isolate databases, servers or ports. No new tool installs
without a missing-dependency failure and authorization. No production DB.

Preferences conflicts with later onboarding only by file; Tool C in About is
independent, but any GlobalSettings host integrates AFTER B migration.
FX page/store changes coordinate with future owners without adding cache or
new-signal scope. Each handoff names revision/files/contract/evidence/gaps.
No new worktree or development Fleet is launched implicitly.

## 8. Targeted acceptance and documentation

Commands are future queued actions from repo root, never concurrent:

| Scope | Runner |
|---|---|
| AI guard + catalogs/fragments/temporal | pipenv run python dev.py test services ai-export (with matching -k name arguments for targeted runs) |
| New FX schema file | pipenv run python dev.py test schemas fx-routes (register first) |
| FX ORM and handlers | test db model-validators; test api fx-unit via the same dev.py prefix |
| FX sync | pipenv run python dev.py test --workers 1 services fx-sync-service |
| SignalResult | test schemas signals; test services signal-service |
| Risk-result consumers | test services risk-all, only four existing risk-signal result tests selected |
| Generated client / type checking | pipenv run python dev.py api sync; pipenv run python dev.py front check |
| Three component files | pipenv run python dev.py test front-utility component-unit (no name/file filtering supported) |
| Settings / sharing parity | test front-utility settings "Runes parity"; test front-user broker-sharing "Runes parity" after focused cases exist |
| Embedding and FX routes | test front-broker detail; front-fx fx-api/fx-list/fx-detail/fx-add-pair with relevant selectors |
| Registration | pipenv run python dev.py test check-orphans |

Never substitute ai-export-pure for catalog/runtime tests. No automatic real
prompt probe. Format/lint/build only with existing scoped project tools.
Do not invent a dev.py --project mobile option for the desktop-default wrappers.

docs-writer updates only relevant English blocks in the existing monolingual
developer/backend/fx/configuration.md: output metadata, repeated provider hops,
membership versus traversal, error configuration and no new input fields.
No translation, filename migration or unrelated stale-doc cleanup.
Only the global writer may record the observable API addition in changelog.

## 9. UI acceptance belongs to the developer

No significant visual change is planned. Keep desktop/mobile/dark/focus/
keyboard/modal/chart behavior. If a new view or important visual change becomes
necessary: stop it, produce versioned desktop/mobile ASCII states, get explicit
developer approval before implementation.

At integration, publish exact build/revision/test URL and disposable roles/IDs:

| Walkthrough | Required observations |
|---|---|
| Settings -> Preferences | Per-field/bulk edit/save/undo/reset, success-only apply, partial failure and actual reload persistence. |
| Settings -> Admin | Admin unlock/lock discard, categories/defaults/Other, bulk save/reset; non-admin readonly; mobile dropdown/locale/listener behavior. Restore global test values under exclusive ownership. |
| Brokers list -> named share modal | Add/edit/reset, dirty-close reject/accept, successful save closes without extra discard; reopen persisted ACL. |
| Broker detail -> Info | Embedded save stays; viewer/editor/non-member permissions, EDITOR self-demote. |
| Sharing errors/leave | Failed read/retry, refused save, last-owner guards; leave/delete only a disposable broker, correct navigation/callback order. |
| FX list/table/detail/provider modal | Direct, repeated-provider chain, distinct providers, MANUAL; same ordered badges, inversion/edit/save and no membership UI added. |

Feedback records ID, revision/build, viewport/theme, view/state, action,
expected/observed, priority and decision/fix. Status remains awaiting_dev_review
until developer accepts; changes_requested opens a cross-linked correction
round. Automated tests or an agent walkthrough do not replace the developer.

Static, unproven FX concerns (provider-less leg_rates key and reverse-endpoint
chain normalization) were handed to the coordinator separately; no fixes,
backfills or new backlog tasks are authorized here. P4-6 and alias6.7 close
once; SP04/SP05 close only after their real acceptance and developer review.

## 10. Current developer-review handoff (2026-09-08)

> **Note implementazione** (B01/B04/B09 complete): all test-author handoffs are
> integrated. Acceptance: 922 complete AI Export service tests; 471 Signal
> schema tests before/after replacement plus 45 service and four selected risk
> consumers; 70 focused FX backend cases plus four real HTTP cases; 1278
> component tests; four owned-data Runes E2E cases; 14 selected FX E2E cases.
> The build succeeds, final backend lint and diff whitespace checks pass, and
> frontend checking has zero errors with 41 deliberately retained legacy
> directive/component deprecation warnings. Scoped Black/Prettier formatting
> touched only B-owned files. Dependency manifests, locks and Alembic files are
> unchanged. Read-only backend review reported no significant issue.

**Review URL after restart:** `http://127.0.0.1:6041/settings`.
Build/source identity: `v1.1.0-3-g4a73f5f6-dirty`, this worktree plus the B diff.
The browser canvas is titled **B - Contracts and Runes (TEST)**.
The server was started and verified by B, then stopped when the developer was
unavailable. Restart only after acquiring the coordinator's runtime slot with:
`LIBREFOLIO_TEST_MODE=1 pipenv run python dev.py server --test --no-scheduler --no-reload --host 127.0.0.1`.
Recorded readiness: HTTP 200; PID 82338 owned by B at initial handoff. Startup logs
confirm `test_mode=true` and this worktree's `backend/data/test/sqlite/app.db`.
Scheduler disabled; no market-data fetch should be triggered for this review.
The B-owned server is now stopped and port 6041 was confirmed free. Do not start
a second backend or reset/populate while the later review is active.

Only the seeded TEST credentials apply:

| Role | Username | Password |
|---|---|---|
| Admin | e2e_test_admin | E2eAdminPass123! |
| Normal user | e2e_test_user | E2eTestPass123! |

Suggested operational pass, desktop and a narrow/mobile viewport, light/dark:

1. Log in as the test admin. Settings -> Preferences: change a value, Undo;
   Reset stages only; Save, reload and observe persistence. Restore the value
   if desired. Locale/theme change only after successful save.
2. Settings -> Admin: unlock, modify an instance value, refuse then accept
   lock/discard. Inspect categories and mobile selector. If testing a global
   Save, record and restore that TEST value through the UI. Do not clear
   unrelated caches or trigger scheduler work.
3. Create a new empty broker named for this B review; do not use a broker with
   seeded transactions for destructive actions. Open sharing from the list:
   add/edit a test-user grant, Reset, edit again, exercise dirty close/discard,
   then Save. It must close without a second discard prompt. Reopen and verify
   the ACL; repeat from Info, where normal Save stays embedded.
4. Check normal-user read-only/admin visibility and available member
   self-service. Last-owner refusal can be inspected without deletion; use
   only a separately created empty broker for leave-and-delete confirmation.
5. Open FX list/table/detail and Provider configuration. Inspect direct and
   available chain routes, inversion and editing. Repeated providers remain
   repeated in the route; no membership badge or redesigned control was added.
   Do not sync a real bank merely for visual acceptance.

Record developer feedback with revision/view/viewport/action/expected/observed,
priority and decision. This section is a runbook and automated handoff,
**not a claim that the developer has completed the review**. B10 remains open.

### Review status and feedback

| ID | Date | Scope | Observation | Disposition |
|---|---|---|---|---|
| B-UI-001 | 2026-09-08 | Final FX/Runes operational and visual review | The explicit review request reported that the developer was unavailable and would review later. No UI acceptance or defect feedback was supplied. | Keep B10 / final group closure open. Use this runbook when the developer is available; automated evidence does not replace approval. |

> **Note implementazione** (handoff, 2026-09-08): technical work is complete;
> no code/runtime action is being invented to bypass the human review gate.
> The attached B review server was stopped via its owned process handle, port
> 6041 is free, and the coordinator is notified that the runtime lease can be
> returned. Coordinator-owned backlog09 changes are preserved. No commits,
> staging, lock/manifest changes, Alembic changes or production-data writes.

## 11. Developer feedback - 2026-09-09

This supersedes the deferred-review state above, not its historical record.
The developer reported actual manual results; no automatic suite was rerun to
record this feedback.

| ID | Review item | Developer result / requested follow-up |
|---|---|---|
| B-UI-002 | B10-01 Preferences | Accepted. |
| B-UI-003 | B10-02 Global settings | Undo/reset and normal-user read-only access accepted. Replace browser confirm with the standard amber warning ConfirmModal. |
| B-UI-004 | B10-02 Other category | Explained: shown only for visible unclaimed keys. Developer explicitly accepted keeping that behavior; no empty category or dummy setting is requested. |
| B-UI-005 | B10-03 / B10-04 sharing modal and Info | Accepted. |
| B-UI-006 | B10-05 last owner | Appears correct, including OWNER leaving with one EDITOR and one VIEWER remaining. Verify physical access-row cleanup and code; UI disappearance alone is not proof. |
| B-UI-007 | B10-06 FX configuration | Existing creation/edit/inversion accepted, including new pairs. Enhancement: close after configuration succeeds and sync in background for both direct and multi-hop real-provider routes. |
| B-UI-008 | Creation feedback | Successful FX sync toast links the flagged pair to its detail; when no sync starts, show immediate creation success with the same link. Existing asset-global creation-success toasts should link the asset; contextual dropdown/import/transaction creation must not gain links or new notifications. |
| B-UI-009 | FX toast formatting | Use existing formatting utilities; Japanese flag before JPY and Romanian flag after RON, as emoji, not ad-hoc unflagged text. |
| B-UI-010 | B10-07 viewport/visual sweep | No explicit verdict supplied; do not infer acceptance. |

> **Note implementazione** (feedback intake, 2026-09-09): accepted preference
> and sharing behavior recorded in CHANGELOG as compatibility, without claiming
> the requested corrections are already implemented. "Other" is not removed:
> its conditional behavior was confirmed by the developer. The runtime is not
> needed during analysis, so the coordinator was told it may reassign its
> review server/queue. No coordinator-owned process was stopped by this agent.

Follow-up:
[Round 1 - manual review corrections](plan-phase00FeedbackContractsRunesBugfixRound1.prompt.md).
