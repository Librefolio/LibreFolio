# 09_feedbackJobs — indice

Backlog del prossimo round di sviluppo. Ogni file è un'area; i task dentro hanno contesto,
dettagli implementativi e rimandi al codice/ai piani. Creato il 07/09/2026 dalla revisione
di TODO_FUTURI.md (classificazione con l'utente) + gli 8 P4 ereditati dall'audit 08.

> **Cosa resta aperto** (verifica Q del 2026-10-09, base `3cceb4f90`). Tutte le altre voci di questa cartella sono fatte, con i riferimenti nella sezione «Stato verificato sul codice — 2026-10-09».
> - **P4-7, ciclo di vita delle cache dei prezzi nel frontend.** `frontend/src/lib/stores/assetPriceStoreRegistry.ts:30` è una `Map` senza limite né eviction. `removeAssetPriceStore` (`:64`) non viene mai chiamata fuori dal file, e niente la aggancia al reset di sessione. Peso medio. [00](00_backlog_strutturale_P4.md), [06](06_piano_sprint.md) SP10.
> - **P4-9, conversione dei test specchio** (DBT-D di I). `2e4c8589f` (28/09) ha chiuso i rossi e il file è verde, ma i 7 specchi ri-pinnati di `frontend/src/lib/components/charts/chartCoreHelpers.test.ts` leggono ancora il sorgente invece di eseguire le funzioni (35 `readFileSync` nel file). Peso basso. [00](00_backlog_strutturale_P4.md).
> - **P4-10, i sei siti di Risk fuori dal canale di mascheramento.** Vanno riverificati dopo il Round 2 della privacy: in `frontend/src/lib/utils/privacy/moneyRenderSites.test.ts` `riskAnalysisHelpers.ts` risulta `masked`. Peso basso. [00](00_backlog_strutturale_P4.md).
> - **R2, `VERSION` stantio**, difetto di design. `backend/app/utils/version.py:36-39` legge `VERSION` prima di `git describe`, e la build Docker lo lascia nella radice (`dev.py:1628-1637`): un server di sviluppo avviato dopo una build mostra una versione congelata. Manca la decisione: leggerlo solo senza `.git/`, o cancellarlo dopo la build. Peso medio. [08](08_review_visiva_20260922.md) R2.
> - **§2.4, guardiano del catalogo finto.** È un debito dichiarato, non verificato nel codice. Peso basso. [09](09_reperti_analisi_statica_20260922.md) §2.4.
> - **SP14, il Rebalancer** (`invest_only`, `invest_and_sell`, verifier SELL). Non è implementato (`backend/app/services/tool_plugins/pac_allocator.py:10-14`): è il prossimo lavoro di D, in `13_pacAllocator`.
> - **SP15, `SensitiveValue`.** È sospeso dal 21/09: [Round 1 di `24_privacyGlobal`](../../phases/24_privacyGlobal/plan-phase00PrivacyGlobalRound1-MaskingCore.prompt.md), passo 5.
>
> **Chiusa il 2026-10-09:** la §1.4 per AI Export non è un difetto, per decisione del developer: *«ma l'ai export non ha anteprima»*. Il prompt non si mostra a schermo: si copia, in chiaro per scelta. [09](09_reperti_analisi_statica_20260922.md) §1.4.

| File | Area | Contenuto |
|------|------|-----------|
| [00_backlog_strutturale_P4.md](00_backlog_strutturale_P4.md) | Debito strutturale | ✅ P4-1…P4-6 nel target; P4-8 non misurabile come task atomico; P4-11 chiuso (`804bc9903`). **Aperti P4-7** (registry senza eviction né reset di sessione), **P4-9** (conversione dei test specchio) e **P4-10** (da riverificare). Marker `TODO(P2-refactor)`: **21** (verifica del 09/10) |
| [01_ux_dashboard.md](01_ux_dashboard.md) | UX & dashboard | ✅ U1–U9 tutti nel target, U2 compreso (`b66e93003`, piano `24_privacyGlobal`) · verifica del 09/10 |
| [02_grafici_avanzati.md](02_grafici_avanzati.md) | Grafici | ✅ G1a, G1b, G1c e G3 (backend e UI Asset) nel target (merge I `2c382824d`, treno 23) · verifica del 09/10 |
| [03_asset_dati_classificazione.md](03_asset_dati_classificazione.md) | Asset & dati | ✅ Settori bond e import CSV distribuzioni integrati e revisionati |
| [04_brim_import.md](04_brim_import.md) | BRIM & import | ✅ eToro fee, refactor CA/helper maturity e delete-asset links integrati e revisionati |
| [05_pac_allocation_tool.md](05_pac_allocation_tool.md) | Tool platform | ✅ Tool platform e planner PAC 1.0.0 nel target (SCIP via PySCIPOpt `==6.2.1`); **Rebalancer non implementato** (`tool_plugins/pac_allocator.py:10-14`), prossimo lavoro di D in `13_pacAllocator` · verifica del 09/10 |
| [06_piano_sprint.md](06_piano_sprint.md) | Analysis and sprint plan | Current-code evidence, 16 sprints, parallel-work dependency map, shared-resource ownership and developer UI review gates |
| [07_feedback_import_critici.md](07_feedback_import_critici.md) | Urgent import/UX/update feedback | ✅ E1-E9 plus U1/U4/U5/U7/U9 integrati in `dev_release2` (`ef722b552`) |
| [08_review_visiva_20260922.md](08_review_visiva_20260922.md) | Review visiva end-to-end in produzione | 21 voci (R1–R21; il «20» era un errore di conteggio), verificate su `e4a46e9e0`, con cause, owner proposti e screenshot. Al 09/10 sono tutte chiuse o non-difetti, **tranne R2** (design di `VERSION`) |
| [09_reperti_analisi_statica_20260922.md](09_reperti_analisi_statica_20260922.md) | Reperti del round di analisi statica | Difetti, debito e 16 reperti di metodo; §9 registra le rettifiche che la review d'uso ha imposto all'analisi statica. Al 09/10 i difetti sono riparati o chiusi (la §1.4 per AI Export non è un difetto, per decisione del developer del 09/10); **§2.4** è un debito aperto |

## Glossario degli alias — leggilo prima della tabella

Lo stesso task compare in questa cartella sotto **due o tre nomi diversi**: il codice del
backlog (`G3`), il codice di fase del piano del workstream che lo implementa (`I60`), e la
lettera del workstream stesso (`I`). Le tabelle di stato usano indifferentemente l'uno o
l'altro.

> ⚠️ **Un alias non dichiarato è un falso negativo garantito per chi cerca il nome che non è
> stato usato.** Il 21/09 il coordinatore ha riportato `G3` come «non iniziato» leggendo una
> riga che diceva `I60 implementato e validato sul branch I`: la riga era corretta, esatta e
> aggiornata, e cercava un'etichetta che quella riga non contiene. Non è un problema di
> freschezza del dato — è un problema di vocabolario, e nessuna data lo avrebbe evitato.

| Backlog | Piano workstream | Workstream | Cos'è |
|---|---|---|---|
| G1a | I20 | I | Vista P&L assoluto su `GrowthChart` |
| G1b | I30/I40 | I | Candele sintetiche P&L |
| G1c | I50 | I | Istogrammi dividendi/interessi |
| G3 | **I10** (backend) + **I60** (UI Asset) | I | Rendimento a N giorni calendario |
| U3 | — | H | Yield on Cost |
| U8 | Round 1-6 | J | Onboarding |
| U2 | — | J (riassegnato) | Privacy globale |
| T1/T2 | Round 4-7 | D | Allocatore PAC / Rebalancer |
| P4-1, P4-4 | — | K | Scissione pricing asset |
| P4-2 | — | L | Scissione `execute_batch` |
| P4-3, B1 | — | G | BRIM Crédit Agricole ed eToro |
| A1, A2, B3 | — | F | Dati asset e CRUD |
| U1, U4, U5, U7, U9 | E1-E9 | E | Feedback import/UX urgenti |

## Stato verificato sul codice — 2026-10-09

Questa tabella prevale su quella del 21/09 qui sotto, che resta come storico. È stata rimisurata sul codice (verifica Q del 2026-10-09, base `3cceb4f90`). Gli SHA citati sono tutti antenati della base (`git merge-base --is-ancestor`); i rami I, J e D del 21/09 sono stati integrati.

| Sprint | Stato al 09/10 |
|---|---|
| SP01–SP05 | ✅ Nel target: E (`ef722b552`), F (`e50d66408`, `cc57b6a38`; piano archiviato in `Release_2/phases/17_assetDataOperations/`), B (`514582a47`). |
| SP06 | ✅ U3 (`74afcebce`) e G3 nel target: backend `d4b3deb2f`, UI Asset `51cb7b677` (`priceChartHelpers.ts` `ASSET_CALENDAR_ROLLING_RETURN`). G1c nel target (`2d22130bd`, `c4595922e`). |
| SP07 | ✅ G1a e G1b nel target (`8ed7a0f0d`, `eba37ba41`; merge I `2c382824d`, treno 23). |
| SP08 | ✅ Come il 21/09 (`3c85866dd`). |
| SP09 | ✅ Come il 21/09 (`ebba209c5`); `FEE_TYPES` è a `broker_etoro.py:71`. |
| SP10 | 🟡 **P4-7 aperto**: vedi «Cosa resta aperto». La riga del 21/09 diceva che `CachePanel.svelte` espone il registry, ma non è vero: il pannello mostra solo le cache del backend. |
| SP11 | ✅ Nel target, Round 7 compreso (`1982c254b`). In `21_onboarding` resta aperta la review manuale delle correzioni C7 (decisione del developer, 09/10). |
| SP12 | ✅ Come il 21/09 (`570beb386`). |
| SP13–SP14 | 🟡 Il planner PAC 1.0.0 è nel target: `b82e59ffa`, UI `0210f9848`, SCIP via PySCIPOpt `==6.2.1`. **Il Rebalancer non è implementato** (`tool_plugins/pac_allocator.py:10-14`): lavoro di D in `13_pacAllocator`. |
| SP15 | ✅ U2 nel target (`b66e93003`, `176f19707`, `64d78e244`; piano `24_privacyGlobal`), per dispositivo come deciso il 21/09. `SensitiveValue` è sospeso. |
| SP16 | ✅ Come il 21/09 (`846aefb24`). |

## Stato esecutivo riconciliato — 2026-09-21

Questa tabella prevale sulle note cronologiche più sotto, che restano come storico dei
checkpoint intermedi.

**Come è stata prodotta, perché la prossima sia falsificabile:** rimisurata contro il codice
il 21/09 (target `c75cf9150`), non copiata dalla revisione precedente. Ogni riga porta lo SHA
o il `file:riga` che la sostiene; gli otto SHA più caricati sono stati verificati uno per uno
contro `git log`. Dove la misura non è stata possibile la riga lo dice, invece di tacere.

| Sprint | Stato persistito |
|---|---|
| SP01–SP03 | ✅ Integrati e revisionati: E (`ef722b552`) + F (`e50d66408`, `cc57b6a38`). |
| SP04–SP05 | ✅ Contratti, matrice segnali e Runes integrati tramite B (`514582a47`). |
| SP06 | ✅ **Chiuso come lavoro, non come integrazione.** YOC/U3 nel target (`74afcebce`); G3 backend nel target (`d4b3deb2f`, `signal_plugins/calendar_rolling_return.py`); G3 UI Asset (`I60`) e G1c **fatti sul ramo I** (`51cb7b677`, `7df7ccbab`, `2d22130bd`, `d5e834de4`). Nulla di aperto: resta solo il rientro. |
| SP07 | 🟡 **Implementato sul ramo I, non nel target.** G1a/G1b in `8ed7a0f0d` più i fix `eba37ba41`, `ef7cce61c`, `69d0d27c6`, `70e87ac3a`. La dicitura «I20–I50 non iniziati» del 14/09 è **superata**. |
| SP08 | ✅ Asset pricing refactor integrato con K (`3c85866dd`, combined `b72475f0e`): P4-1, P4-4 e S6 6.4 chiusi. |
| SP09 | ✅ G integrato, developer-accepted e archiviato (`ebba209c5`, docs `4949b2f4c`). |
| SP10 | 🟡 **Parziale, non «differito».** `frontend/src/lib/stores/assetPriceStoreRegistry.ts` esiste nel target (`75783b1c6`) e `CachePanel.svelte` lo espone; **non è dimostrata** l'eviction né l'aggancio completo al reset di sessione. È l'unico task del round con lavoro reale residuo oltre a U2. |
| SP11 | ✅ **Nel target** dal merge `3913fe217` (19/09), più i fix `35f0bb484` e `38d44b717`. Resta fuori il solo `1982c254b` (stall dell'ancora a 3s) sul ramo J. |
| SP12 | ✅ Piattaforma Tool integrata (`570beb386`). |
| SP13–SP14 | 🟡 **Planner v2 funzionante sul ramo D** (`b82e59ffa`): `operation="plan"` produce un risultato reale end-to-end, prototipo P1 in corso di rimozione. Nel target c'è solo la piattaforma Tool. Fuori perimetro e non iniziati: SELL, policy del rebalancer, registrazione Tool, frontend operativo PAC (T2). Gate G-PAC aperto sul campionamento a scala. |
| SP15 | 🔵 **In analisi, non più «attende».** Il blocco dichiarato il 14/09 era su SP07+SP11+SP14: SP11 è nel target, SP07 esiste sul ramo I. L'analisi U2 (inventario, contratto di mascheramento, primitive) è autorizzata e in corso su J. **Decisione di prodotto presa il 21/09: preferenza privacy locale per dispositivo**, nessuna colonna server, nessuna migrazione Alembic — quindi U2 non tocca il backend e non ha superfici condivise con D. L'implementazione degli adapter resta dipendente dal rientro di I e D. |
| SP16 | ✅ Refactor `execute_batch` integrato con L (`846aefb24`, combined `ed0f4ff30`); full backend e docs verdi. |

### Il residuo vero — 2026-09-21

Dei ~40 task del backlog, **due soli** hanno lavoro di codice non ancora scritto:

| Task | Perché è residuo | Chi |
|---|---|---|
| **U2** privacy globale | Nessuna primitiva, nessuno store, nessun adapter esiste. L'analisi è in corso. | J |
| **P4-7** lifecycle cache | Il registry c'è; eviction e aggancio al reset di sessione non sono dimostrati. | nessuno |

Tutto il resto è **scritto**. La distinzione che conta non è più «fatto / da fare» ma
**«nel target / su un ramo»**:

| Ramo | Avanti di | Cosa porta |
|---|---|---|
| `e-alfy-performance-charts-plan` (I) | 17 commit | G1a, G1b, G1c, UI Asset di G3 |
| `e-alfy-allocatore-pac` (D) | 2 commit + lavoro in corso | T1 planner v2, rimozione prototipo P1 |
| `e-alfy-onboarding-foundation` (J) | 1 commit | fix stall onboarding; scope corrente = analisi U2 |

> ⚠️ **`B1` non è bloccato e non lo è dal 10/09.** La scheda in
> [04_brim_import.md](04_brim_import.md) descrive ancora `SKIP_TYPES` che scarta le fee: il
> codice attuale le mette in `FEE_TYPES` (`backend/app/services/brim_providers/broker_etoro.py:71`,
> commit `ebba209c5`). Il gate G-ETORO chiedeva un export reale **che è arrivato**. La scheda
> va letta come storia del problema, non come stato.


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
[dedicated H implementation](../../phases/19_yieldOnCost/plan-phase00YieldOnCost.prompt.md).
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
lives in [14_feedbackImportUrgent](../../phases/14_feedbackImportUrgent/manifest-integrazione-E.md).
U2 privacy,
U3 YOC, U8 onboarding and the deferred multicurrency proposals remain open.

## Group B checkpoint - 2026-09-10

[Contracts and Runes - SP04-SP05](../../phases/11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md)
and its [manual-review correction round](../../phases/11_feedbackContractsRunes/plan-phase00FeedbackContractsRunesBugfixRound1.prompt.md)
were integrated into `dev_release2` through `514582a47`. Scope remains P4-5,
P4-6/S6 6.7, S6 6.2 and S6 6.11 plus the approved review corrections. Combined
static, unit, API and targeted E2E gates were green on isolated lane `6151` +
`/tmp/librefolio-r2-b`; manual corrections are included. Runtime ownership follows the current section 14
integration policy, not the older execution lease.

## Performance charts plan-only checkpoint - 2026-09-10

[SP06 G3/G1c and SP07 G1a/G1b](../../phases/20_performanceCharts/plan-phase00PerformanceCharts.prompt.md)
have a durable final product contract, ASCII v2 storyboards, file ownership and
dependency-safe XL phase split. I10 signal-only calendar-return backend is integrated
(`d4b3deb2f`/`d54d74189`). H/YOC is integrated before I. I60 Asset UI is implemented
and automatically validated on branch I; its developer-approved UX follow-up is active.
I20–I50 and G1c remain unimplemented.

## Onboarding final checkpoint - 2026-09-14

[SP11 / U8](../21_onboarding/plan-phase00Onboarding.prompt.md) and its six review
rounds are implemented and automatically verified. The developer accepted the
final Welcome, Core, contextual and Import-guide UX in
[Round 6](../21_onboarding/plan-phase00OnboardingRound6-FinalUX.prompt.md).
Checkpoint J `580bd504f` is integrated into clean combined D baseline
`e38a521f0`; that baseline is not yet integrated into target `dev_release2`.

## PAC/Rebalancer prototype checkpoint - 2026-09-14

The separate PAC and Portfolio Rebalancer P1 Tools, shared multi-service plugin,
source-copy workflows and automated evidence are preserved in checkpoint D
`d66f8e58e`. Manual review rejected the analysis-only product contract: the next
iteration requires a newly approved high-level design for Broker routing, funding,
FX and executable discrete allocation. Collaborative redesign is active; no
replacement implementation plan or solver was approved at that 2026-09-14
checkpoint.

## PAC/Rebalancer operational planning checkpoint - 2026-09-15

Il developer ha approvato UX e nucleo matematico nei round successivi al
prototipo respinto. La loro autorità corrente è ora la suite con
[piano maestro target](../13_pacAllocator/plan-phase00PacRebalancerTargetDesign.prompt.md);
la [catena precedente](../13_pacAllocator/drafts/README.md) resta storica.
Nessun codice/test operativo è iniziato e il vecchio Round 7 non è più il piano
attivo: la review indipendente della suite è stata incorporata e il nuovo
piano implementativo verrà scritto dopo l'approvazione developer. Primario
globale fixed-L2, policy operative distinte, variante
margine BUY-only e proof/status conservativi restano congelati. SCIP è candidato
additivo; dependency/probe/capacità e risultato product-shaped restano gate.

## Regole della cartella

- I task si pescano da qui all'inizio di un round; quando un task parte, il suo piano vive in
  `Phase_0/<NN_area>/` come di consueto, e qui viene marcato ✅ con link al piano.
- Le note "Status" citano la decisione utente del 07/09/2026.
- Ciò che è deliberatamente rinviato resta in `TODO_FUTURI.md` (non qui).
