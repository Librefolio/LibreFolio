# 09_feedbackJobs — indice

Backlog del prossimo round di sviluppo. Ogni file è un'area; i task dentro hanno contesto,
dettagli implementativi e rimandi al codice/ai piani. Creato il 07/09/2026 dalla revisione
di TODO_FUTURI.md (classificazione con l'utente) + gli 8 P4 ereditati dall'audit 08.

| File | Area | Contenuto |
|------|------|-----------|
| [00_backlog_strutturale_P4.md](00_backlog_strutturale_P4.md) | Debito strutturale | Gli 8 task P4 dell'audit (scissione asset_source, execute_batch, BRIM helpers, Yahoo, Runes, status matrix, cache store, coda S6) |
| [01_ux_dashboard.md](01_ux_dashboard.md) | UX & dashboard | Provider probe, global privacy, YOC, uploader filter, currency help, support, onboarding, mobile header |
| [02_grafici_avanzati.md](02_grafici_avanzati.md) | Grafici | I10 calendar-return backend integrato; I60 Asset UI/follow-up attivi su I; P&L/candele/income ancora aperti |
| [03_asset_dati_classificazione.md](03_asset_dati_classificazione.md) | Asset & dati | ✅ Settori bond e import CSV distribuzioni integrati e revisionati |
| [04_brim_import.md](04_brim_import.md) | BRIM & import | ✅ eToro fee, refactor CA/helper maturity e delete-asset links integrati e revisionati |
| [05_pac_allocation_tool.md](05_pac_allocation_tool.md) | Tool platform | Tool platform e PAC P1 integrati; Round 2 PAC completo in corso su D; solver ancora aperto |
| [06_piano_sprint.md](06_piano_sprint.md) | Analysis and sprint plan | Current-code evidence, 16 sprints, parallel-work dependency map, shared-resource ownership and developer UI review gates |
| [07_feedback_import_critici.md](07_feedback_import_critici.md) | Urgent import/UX/update feedback | ✅ E1-E9 plus U1/U4/U5/U7/U9 integrati in `dev_release2` (`ef722b552`) |

## Stato esecutivo riconciliato — 2026-09-11

Questa tabella prevale sulle note cronologiche più sotto, che restano come storico dei
checkpoint intermedi.

| Sprint | Stato persistito |
|---|---|
| SP01–SP03 | ✅ Integrati e revisionati: E (`ef722b552`) + F (`e50d66408`, `cc57b6a38`). |
| SP04–SP05 | ✅ Contratti, matrice segnali e Runes integrati tramite B (`514582a47`). |
| SP06 | 🟡 YOC/U3 e I10 integrati; I60 implementato e validato sul branch I, follow-up UX attivo; G1c aperto. |
| SP07 | ⏸️ I20–I50 non iniziati; attendono rilascio delle superfici Portfolio/PAC condivise. |
| SP08 | 🟡 K autorizzato e in implementazione: P4-1, P4-4 e S6 6.4. |
| SP09 | ✅ G integrato, developer-accepted e archiviato (`ebba209c5`, docs `4949b2f4c`). |
| SP10 | ⏸️ Differito fino alla stabilizzazione chart/store. |
| SP11 | 🟡 J Round 2 revisionato; Round 3 in implementazione sul branch J, non integrato. |
| SP12 | ✅ Piattaforma Tool integrata (`570beb386`). |
| SP13–SP14 | 🟡 PAC P1 integrato; Round 2 completo attivo su D; solver SP14 ancora aperto. |
| SP15 | ⛔ Attende SP07 + SP11 + SP14. |
| SP16 | ✅ Refactor `execute_batch` integrato con L (`846aefb24`, combined `ed0f4ff30`); full backend e docs verdi. |

**Planning update (2026-09-07):** see [06](06_piano_sprint.md) for the current-code
assessment and decisions made during review. Global privacy, mobile auto-hide header,
synthetic P&L candles and the backend Tool plugin platform supersede the original narrower
scope. That update was planning-only; later execution authorizations are recorded below.

**Review follow-up (2026-09-07):** YOC now specifies a 365-day window, explained dash states,
an English theory page and a column-header tooltip. The shared CsvEditor is extended rather
than duplicated. Tool schemas live in the catalogue; data copying uses domain APIs.
Section 11 maps parallel work; section 12 requires ASCII mockup approval before substantial
UI changes and an operational developer walkthrough/feedback round afterward.

## Workstream H completion - 2026-09-11

U3 Yield on Cost is ✅ **IMPLEMENTED, VERIFIED, DEVELOPER-ACCEPTED AND INTEGRATED** in
checkpoint `74afcebce`, with the final renderer follow-up integrated at `f092a194b`; see the
[dedicated H implementation](../19_yieldOnCost/plan-phase00YieldOnCost.prompt.md).
The final contract uses non-negative gross asset-linked DIVIDEND/INTEREST
transactions, broker-scoped D-1 eligibility, split/FX provenance and residual
WAC. Recorded-zero income remains distinct from true `no_income`; negative
signed income is unsupported. Dashboard/Broker UI, four-language tooltips,
English docs and shared cache identities are included. I20+ must re-read the
post-H target before touching shared portfolio files.

## Selective resumption - 2026-09-08 11:30 CEST

The developer resumed unblocked work after the workstation change. **E** continues the
urgent import/asset/FX fixes, affected-row diagnostics E7, chronological ordering E8 and
U1/U5/U4/U7/U9 inherited from A. E9 was added the same day: investigate nightly
`1.0.1-114` reported up to date despite stable `1.1.0`, and display the actual detected
remote version in the banner, without accessing or updating production.
**C/D** resume contract, minimum real PAC `analyze` pilot,
numerical-policy and ASCII planning in their existing worktrees. This does not approve
outstanding numerical/UI gates or authorize their application implementation.

**Later direct approvals, 2026-09-08 15:48/15:51:** C may implement the complete Tool
platform in its owned files; D may implement the initial P1 mathematical core and backend
tests after N1/developer-C1/X1 approval. C diagnostics are now for every authenticated
user, with sanitized output; hub/About use locale-aware docs links, compute jobs are
separate per item, timings are observable and no `jsonschema` dependency is added.
These updates supersede the earlier C/D planning-only status, not E's manual-review
reservation. PAC UI, full solver, portfolio copies and Broker migration remain separate.

**A** does not restart transferred work. **B** has implementation ready in its own
worktree, pending developer operational review. E's live instance/build remains reserved
for the developer's manual review; production is off limits. Truly PURE checks and
worktree-local runner edits receive separate, serialized grants without DB/server setup.
This does not release E's backend, build/API-generation/i18n or frozen application files.
About/support integration follows E -> C. The manual PAC pilot does not depend on the
future Broker fractional-purchase migration or portfolio-copy feature.

See [06](06_piano_sprint.md) for current coordination. Execution records and application
diffs remain in their owners' worktrees until explicit integration. Only future topics
F-MC-1/2/3 were added to the main [TODO_FUTURI.md](../../../../TODO_FUTURI.md);
pre-existing deferred work is unchanged.

## Integration and closure policy - 2026-09-09

[Master plan, section 14](06_piano_sprint.md#14-integrazione-dei-worktree-chiusura-e-riallineamento)
defines delivery snapshots, integration into local `dev_release2`, semantic-conflict
review, mandatory plan/backlog/completed-task/changelog/knowledge updates, safe updates
of active worktrees via developer-performed merges, and archival after integration.
No Git-history operation is automated. Source readiness, developer acceptance and
integration are separate states.

## Group E completion - 2026-09-09

The final reviewed 109-file E package, including the Round 5 GHCR fix found by
independent review, was committed and integrated into `dev_release2` as `ef722b552`. Canonical
status lives in [07](07_feedback_import_critici.md); portable execution evidence
lives in [14_feedbackImportUrgent](../14_feedbackImportUrgent/manifest-integrazione-E.md).
U2 privacy,
U3 YOC, U8 onboarding and the deferred multicurrency proposals remain open.

## Group B checkpoint - 2026-09-10

[Contracts and Runes - SP04-SP05](../11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md)
and its [manual-review correction round](../11_feedbackContractsRunes/plan-phase00FeedbackContractsRunesBugfixRound1.prompt.md)
were integrated into `dev_release2` through `514582a47`. Scope remains P4-5,
P4-6/S6 6.7, S6 6.2 and S6 6.11 plus the approved review corrections. Combined
static, unit, API and targeted E2E gates were green on isolated lane `6151` +
`/tmp/librefolio-r2-b`; manual corrections are included. Runtime ownership follows the current section 14
integration policy, not the older execution lease.

## Performance charts plan-only checkpoint - 2026-09-10

[SP06 G3/G1c and SP07 G1a/G1b](../20_performanceCharts/plan-phase00PerformanceCharts.prompt.md)
have a durable final product contract, ASCII v2 storyboards, file ownership and
dependency-safe XL phase split. I10 signal-only calendar-return backend is integrated
(`d4b3deb2f`/`d54d74189`). H/YOC is integrated before I. I60 Asset UI is implemented
and automatically validated on branch I; its developer-approved UX follow-up is active.
I20–I50 and G1c remain unimplemented.

## Regole della cartella

- I task si pescano da qui all'inizio di un round; quando un task parte, il suo piano vive in
  `Phase_0/<NN_area>/` come di consueto, e qui viene marcato ✅ con link al piano.
- Le note "Status" citano la decisione utente del 07/09/2026.
- Ciò che è deliberatamente rinviato resta in `TODO_FUTURI.md` (non qui).
