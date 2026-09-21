# Phase 0 - Onboarding Round 4: geometry e milestone contestuali

← Previous:
[Onboarding Round 3 — tour granulari per trigger](plan-phase00OnboardingRound3-TriggeredTours.prompt.md)

→ Follow-up:
[Onboarding Round 5 — progresso per-step e polish contestuale](plan-phase00OnboardingRound5-StepProgressPolish.prompt.md)

## Confine e autorizzazione

**Baseline worktree:** `8f7acd610127d1ba24dcddfef5b9acf4552d4f51`.

**Target isolato:** `4949b2f4c04050e46f643de848894b6706349f34`.

**Branch:** `e-alfy-onboarding-foundation`.

**Lane:** porta 6158, data dir assoluta
`/tmp/librefolio-r2-j-onboarding`.

**Coordinator session:** `c8328a01-f208-4ade-a352-0486d1f14de2`.

**Autorizzazione developer verbatim relayed dal coordinator, 2026-09-11:**
`Plan approved! Exited plan mode.`

Il server manuale Round 3 PID 22516 è stato arrestato prima di ogni edit; porta 6158
provata libera. Nessun target merge, staging, commit/history, `--force`, dato
production o porta 6040.

## Esito review Round 3

Accettati e da preservare:

- copy Welcome/Intro/Core e domini, salvo il riferimento Dashboard a Refresh;
- label dedicata `Disconnettiti`;
- intro logo, indicatori e pacing;
- flow pagina/Add/detail per Transactions/Broker/FX/Asset;
- source of truth backend, replay/versioning e migrazione draft `003`;
- topmost arbitration Form/Import/Bulk;
- Settings per dominio.

Respinti o da rifinire:

- linea SVG pointer;
- Core sempre centrato, con overlap soprattutto sugli step visibili 5 e 8;
- Dashboard puntata a Refresh e ordine Dashboard→Navigazione;
- freccia su overview o wrapper non azionabili;
- assenza del pulse rettangolare su Transazioni;
- Bulk lineare che descrive controlli non ancora presenti;
- Import CTA misurata durante il primo mount e corretta soltanto dopo scroll.

## Contratti invariati

- `user_onboarding_progress` è l'unica persistenza.
- Flow dovuto: `pending || version < current_version`.
- Nuova versione riapre completed e skipped.
- X automatico registra skip; X replay chiude solo il replay.
- Chiusura host senza Finish/X lascia il flow dovuto.
- Nessun click, route jump, apertura modal o write finanziario automatico.
- Session storage contiene solo cursor/replay transient.
- Modificare soltanto `003_user_onboarding_progress.py`; nessuna migration `004`.
- Tutti i flow restano unreleased/v1; nessun bump simulato.

## Decisione Bulk approvata

Il developer ha scelto **più guide Bulk persistite separate**.

Conservare `transaction_bulk_guide` come overview e aggiungere:

| Flow | Trigger reale | Target |
|---|---|---|
| `transaction_bulk_guide` | prima apertura Bulk topmost | workspace/header |
| `transaction_bulk_validation_guide` | primo validate concluso | risultato/status visibile |
| `transaction_bulk_selection_guide` | prima selezione non vuota | toolbar selezione montata |
| `transaction_bulk_save_guide` | primo draft commit-ready | pulsante Salva tutto |

La sequenza lineare
`workspace → add/import → validation → tools → save`
viene rimossa. Add Row e Import conservano le guide Form/Import dedicate.

Totale target: 18 flow. I tre nuovi flow sono pending/v1 nella sola `003`; `ensure`
crea solo le row mancanti.

## Matrice visuale per step

Sostituire il solo `presentation: spotlight | pointer` flow-wide con assi
step-specific:

| Campo | Valori |
|---|---|
| `pointer` | `none`, `cursor` |
| `highlight` | `none`, `pulse` |
| `backdrop` | boolean |
| `panelPlacement` | `auto`, `center`, `top`, `bottom`, `left`, `right` |
| `scrollPolicy` | `none`, `nearest-if-hidden` |

Regole:

- overview pagina: nessun cursor;
- Transactions overview: pulse evidente senza backdrop/inert;
- action/click step: cursor soltanto su button/link/input reale;
- header/chart/group informativi: message-only, oppure pulse se esplicitamente utile;
- nessun cursor su wrapper generico o al centro tra più controlli.

## Cursor compatto

- Eliminare la linea SVG.
- Ripristinare badge bianco `MousePointer2`, bounce, dark mode e
  `pointer-events:none`.
- Calcolare un hotspot dell'icona e posizionarlo dentro il bounding box del target.
- Pubblicare `data-pointer-hotspot-x/y` e mantenere
  `data-target-center-x/y`.
- Non montare pointer in stato waiting o con `pointer:none`.

## Placement collision-safe

- Misurare target e pannello reali.
- Generare candidate top/bottom/left/right/center con safe margin.
- Scartare candidate fuori viewport o che intersecano il target.
- Ordinare per preferenza step e spazio libero.
- Desktop Core sidebar: preferire area main a destra della sidebar.
- Mobile Core: scegliere sopra/sotto senza coprire la voce menu.
- Aggiungere override/regressioni esplicite per Core step visibile 5 (FX) e 8
  (Impostazioni).
- Pubblicare `data-panel-placement`.

## Core

Nuovo ordine:

1. `intro.navigation` — toggle desktop / burger mobile;
2. `intro.dashboard` — link `nav.dashboard`, sidebar aperta;
3. `intro.transactions_nav`;
4. `intro.brokers_nav`;
5. `intro.fx_nav`;
6. `intro.assets_nav`;
7. `intro.tools_nav`;
8. `intro.settings_nav`.

Rimuovere il contratto onboarding `dashboard.sync`; il copy Dashboard torna a
descrivere la pagina iniziale, senza riferimento al Refresh.

## Bulk runtime

Generalizzare la coda singola a FIFO deduplicata account-scoped.

Priorità quando più milestone Bulk diventano eleggibili:

```text
Import attiva
→ Bulk overview
→ Bulk validation
→ Bulk selection
→ Bulk save
```

Trigger:

- overview solo quando Bulk è topmost;
- validation dopo `validateRuns > 0` e scheduler settled;
- selection con `bulkTableSelectedRows.length > 0`;
- save con almeno un draft e `commitDisabled === false`.

Chiusura Bulk elimina queue host-local stale ma non completa/skippa i flow.
Replay separato attende sempre il proprio trigger.

## Import first-mount

Root cause confermata: la CTA footer viene misurata durante la transition `scale` di
`ModalBase`; il motion root corrente è il button e non vede l'animazione
dell'antenato. `scrollIntoView()` induce un secondo layout che maschera il difetto.

Fix:

- motion root = nearest `.modal-content`, `nav`, oppure anchor;
- attendere settle animation/transition + due frame identici;
- rimuovere `scrollIntoView()` incondizionato;
- CTA footer Import usa `scrollPolicy:none`;
- target offscreen usa solo `nearest-if-hidden` sullo scroll root dichiarato;
- `import-wizard-content` pubblica lo scroll root;
- activation non modifica `window.scrollY` né lo scrollTop del wizard;
- panel/cursor non coprono la CTA.

## Superfici

Backend:

- `backend/app/db/models.py`
- `backend/app/services/onboarding_service.py`
- `backend/alembic/versions/003_user_onboarding_progress.py`

Frontend:

- `frontend/src/lib/types/onboarding.ts`
- `frontend/src/lib/features/onboarding/onboardingApi.ts`
- `frontend/src/lib/features/onboarding/onboardingGuideCatalog.ts`
- `frontend/src/lib/features/onboarding/onboardingGuide.svelte.ts`
- `frontend/src/lib/components/onboarding/OnboardingCoachmark.svelte`
- `frontend/src/lib/components/onboarding/OnboardingOverlayHost.svelte`
- `frontend/src/lib/components/onboarding/OnboardingReplaySection.svelte`
- `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte`
- `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte`
- anchor reali nei componenti/route già toccati da J;
- `frontend/src/routes/(app)/dashboard/+page.svelte` per rimuovere l'anchor Sync.

Shared coordinator-owned:

- API sync;
- cataloghi EN/IT/FR/ES;
- runner registration;
- changelog/backlog/master records.

## Piano di esecuzione

### Step 1 - Piano durevole

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** server Round 3 fermato e porta 6158 provata libera.
> Creato questo piano, cross-linkato Round 3 e marcato respinto il checkpoint geometry
> precedente; copy e contratti accettati sono preservati.

### Step 2 - Flow Bulk persistiti

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** conservato `transaction_bulk_guide` come overview e
> aggiunti i flow persistiti validation/selection/save in enum backend/frontend,
> registry versioni, Zod runtime, catalogo guide, Settings e sola migration draft
> `003`. Totale source-of-truth: 18 flow v1. API sync resta nello Step 7
> coordinator-owned.

- enum/registry/tipi/Zod;
- tre nuove row nella sola migration 003;
- Settings grouping;
- API sync coordinator-owned.

### Step 3 - FIFO e trigger milestone

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** la queue contestuale è ora FIFO deduplicata e
> account-scoped. Bulk accoda overview/validation/selection/save in priorità stabile,
> osserva i trigger reali e sospende selection/save se il relativo controllo
> scompare. Import preempie qualunque flow Bulk e lo riaccoda allo stesso cursor;
> chiusura o destroy route dell'host puliscono tutte le entry Bulk senza terminal
> transition.

> **⚠️ Fuori pista:** la prima `clearQueued(flow)` FIFO assegnava un nuovo array
> anche quando il flow era assente, rischiando un effect loop nella Bulk. Ora muta lo
> state soltanto quando esiste davvero qualcosa da rimuovere.

- queue deduplicata;
- priorità Import/Bulk;
- trigger validation/selection/save;
- clear host/account.

### Step 4 - Presentation per-step

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** rimosso il presentation flow-wide e introdotti per step
> `pointer`, `highlight`, `backdrop`, `panelPlacement` e `scrollPolicy`. Gli overview
> non mostrano cursor; Transazioni overview usa pulse senza backdrop; i cursor
> restano solo su target azionabili. `guideAnchor` supporta alias multipli così
> Salva tutto è target reale sia per Import sia per Bulk Save.

- matrice pointer/highlight/backdrop/placement/scroll;
- audit anchor azionabili;
- pulse Transazioni.

### Step 5 - Geometry e Core

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** rimossa la linea SVG e ripristinato il badge
> `MousePointer2` Round 2 con hotspot pubblicato sul centro del target. Il pannello
> usa candidate collision-safe dentro viewport; Core ora segue Navigazione →
> Dashboard (`nav.dashboard`) e poi le sei destinazioni, con preferenze mobile
> bottom/top per FX e Impostazioni e destra su desktop. L'anchor Sync Dashboard è
> stato rimosso.

> **⚠️ Fuori pista:** il primo `front check` Round 4 ha rilevato due narrowing
> TypeScript sul rect nullable catturato nelle callback del placement. Introdotto un
> alias locale già validato prima delle callback; nessun cambio di comportamento.

- cursor badge/hotspot;
- placement collision-safe;
- Core Navigation→Dashboard;
- regressioni FX/Settings desktop/mobile.

### Step 6 - Import first-mount

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** il motion root include ora l'antenato `.modal-content`;
> le CTA Import usano `scrollPolicy:none`, mentre gli altri target scrollano soltanto
> se realmente fuori dallo scroll root dichiarato. Pointer/highlight attendono due
> frame identici dopo la transition; l'attivazione Import non induce scroll.

- ancestor motion root;
- scroll policy;
- scroll invariants;
- CTA stabile al primo mount.

### Step 7 - Shared handoff

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** coordinator API sync completo su 18 flow (OpenAPI,
> Zodios, discriminator fix e Tool generation, tutti exit 0; nessun generated
> tracked). Cataloghi aggiornati solo via `dev.py i18n`: 9 add, 2 update, 8 remove,
> parità EN/IT/FR/ES 2.989/2.989, 0 incomplete/backend missing. Check-orphans:
> backend 206, E2E 79, unit 205, tutti registrati e raggiungibili da `all`.

> **⚠️ Fuori pista coordinato:** applicato il handoff D su `ToolsHub.svelte`, file
> assegnato a J: card ready interamente cliccabile, prima riga Icon/Title/Docs,
> descrizione full-width, Docs z-20 indipendente, versione/stati preservati e freccia
> in basso a destra. Nessuna variante PAC e nessuna nuova chiave i18n.
>
> Il primo selector ToolsHub è risultato rosso perché lo snapshot iniziale del
> test-author, concluso dopo il patch production, aveva ripristinato il DOM
> pre-handoff. Il test ha quindi rilevato correttamente l'assenza del whole-card link;
> patch D riapplicato sul parent corrente prima del rerun. Il secondo selector ha
> precisato che la freccia deve essere figlia diretta assoluta della card, non dentro
> un footer wrapper; corretto senza cambiare il contratto generico.

- coordinator API sync;
- i18n add/update/remove esclusivamente via `dev.py`;
- nessun generated tracked inatteso.

### Step 8 - Test-author obbligatorio

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** test-author ha aggiornato esclusivamente test backend,
> component/controller ed E2E. Evidenza iniziale: component onboarding 301 pass;
> controller/anchor 53 pass; backend service 4 pass, migration 5 pass, API flow-list
> 1 pass; Playwright onboarding desktop/mobile 6 pass; Import 2 pass; Auth 2 pass;
> Settings 2 pass. Nessun dato disposable residuo e porta 6158 libera. Resta il
> follow-up ToolsHub richiesto dal handoff D, riaperto sullo stesso test-author dopo
> l'arrivo della modifica production.
>
> **ToolsHub follow-up:** runner coordinator-owned registrato; primo run rosso sul
> DOM pre-handoff ripristinato dallo snapshot agent, secondo run rosso perché la
> freccia era annidata nel footer invece che figlia diretta assoluta. Dopo il fix
> production, selector `ToolsHub generic catalogue cards` verde 2/2. Resta il rerun
> finale dei selector Round 4 sul parent corrente.
>
> **⚠️ Fuori pista infrastruttura:** nel rerun parent corrente, component 301,
> controller/anchor 53, servizi 4, migration 5 e API 1 sono passati. Il preflight del
> comando Playwright immediatamente successivo ha trovato per pochi secondi la porta
> 6158 ancora occupata dal backend API appena concluso e ha fermato correttamente lo
> script prima dell'avvio; nessun test Playwright è stato raccolto e `lsof` successivo
> ha confermato la porta libera. Ripresa dai selector rimanenti, senza force/kill.
>
> **⚠️ Fuori pista test:** onboarding desktop/mobile 6/6, Auth 2/2 e Settings 2/2
> sono passati; Import G2 è passato, mentre G1 ha letto `data-guide-state` e geometry
> in frame distinti dopo la chiusura di ParseDetail. Una invalidazione legittima tra
> i due read ha prodotto attributo hotspot vuoto, coercizzato erroneamente a zero.
> Verdict test-triage: **assumption**. Test-author sta sostituendo i read separati con
> un unico sample browser atomico e retrying, senza indebolire gli invarianti.
> Rerun G1/G2 verde 2/2; cleanup disposable/upload verificato e porta 6158 libera.
> Il selector ToolsHub finale è verde 2/2.

- component geometry;
- controller FIFO;
- Bulk milestone;
- Import no-scroll;
- Playwright desktop/mobile.

### Step 9 - Gate e review manuale

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** rerun finale parent corrente verde: onboarding component
> 301, controller/anchor 53, servizi 4, migration 5, API 1, onboarding Playwright
> desktop/mobile 6, Auth 2, Settings 2, Import G1/G2 2 e ToolsHub 2. Format-check,
> `front check` (0 errori/41 warning legacy), build production, Ruff, Black,
> i18n 3.043/3.043 e check-orphans 206 backend/79 E2E/206 unit sono verdi.
> Server test riaperto senza force su `http://localhost:6158`, PID 14112, root HTTP
> 200.

- statici mirati;
- suite selettive;
- server lane 6158;
- runbook developer.

## Runbook review manuale Round 4

Credenziali disposable lane:
`e2e_test_user` / `E2eTestPass123!`.

1. In `/settings` → Preferenze → Primo utilizzo e guide, scegliere **Ripeti tutto**.
2. Welcome: cambio lingua live, `Disconnettiti`, logo/indicatori/fade invariati.
3. Core su `/dashboard`:
   - step 1 burger/toggle;
   - step 2 link Dashboard nella sidebar;
   - poi Transazioni, Broker, FX, Asset, Strumenti, Impostazioni;
   - cursor badge compatto sul target reale, nessuna linea SVG;
   - pannello mai sopra il target, soprattutto FX e Impostazioni.
4. `/transactions`: overview con rettangolo pulse e senza cursor; Add/Import con
   cursor sul pulsante reale; colonne senza freccia decorativa.
5. Add Transaction: chiudere il Form senza salvare; Bulk overview parte solo quando
   Bulk è topmost.
6. Bulk:
   - overview alla prima apertura;
   - validation soltanto dopo il primo validate concluso;
   - selection soltanto dopo aver selezionato una riga;
   - save soltanto quando Salva tutto è abilitato;
   - ogni voce è indipendente e ripetibile dalle Impostazioni.
7. Import:
   - aprire il wizard e controllare subito il cursor sulla CTA senza scroll;
   - ripetere su Analyze;
   - aprire/chiudere Parse Detail: al ritorno geometry torna stabile;
   - Import mantiene priorità, poi riprende le milestone Bulk.
8. Broker/FX/Asset: overview pagina senza cursor; freccia soltanto su Add, Sync,
   provider/editor/tab realmente cliccabili.
9. Desktop e mobile circa 390×844: pannello dentro viewport, target scoperto,
   hotspot dentro il controllo; sidebar transition completata prima del cursor.
10. `/tools`: card ready cliccabile interamente, Docs resta azione indipendente,
    descrizione full-width e freccia in basso a destra; card unavailable disabilitata.

### Step 10 - Post-OK UX

**Stato:** ✅ completato il 2026-09-14 — sbloccato dall'OK verbatim del developer del 2026-09-14 e superato dall'integrazione in `dev_release2`. Riga chiusa a posteriori nel Round 7 Step 1.

- docs-writer;
- suite completa;
- review read-only;
- shared finali e handoff integrazione.

## Test obbligatori

Tutti i test nuovi/riparati passano da `test-author`.

Component:

- pointer assente/presente per mode;
- hotspot dentro target;
- pulse indipendente dal backdrop;
- pannello nel viewport e senza intersezione target;
- ancestor transition mantiene waiting fino a settle;
- `scrollPolicy:none` non invoca scroll;
- FIFO/dedupe/reset.

Playwright desktop/mobile:

- bbox pannello entro viewport;
- area intersezione panel/target zero;
- hotspot cursor dentro target ±2 px;
- overview cursor count 0;
- Transazioni pulse contiene target e pagina resta interattiva;
- Core ordine 1–8 e target Dashboard nav;
- FX/Settings non sovrapposti;
- sidebar transition stabile prima del cursor;
- Import primo mount/Analyze corretto senza scroll manuale;
- `window.scrollY` e wizard scrollTop invariati;
- Bulk subflow assente prima del trigger, presente una volta al primo evento;
- Import preemption conserva ordine Bulk.

`frontend/e2e/onboarding-tour.spec.ts` è ancora basato sul vecchio route-hopping
Round 1 e deve essere riscritto sul contratto corrente, non semplicemente rattoppato.

## Gate/runtime

- Il server 6158 resta spento durante implementazione/test.
- Test solo nella lane assegnata con:
  `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py ...`
- Nessun comando concorrente su porta/data dir.
- Statici: format/check/build, Ruff/Black, i18n audit, API sync.
- Mirati: component/controller/Bulk/Import + Playwright desktop/mobile.
- Server 6158 riaperto soltanto per review manuale finale, senza `--force`.
- Docs e full campaign restano post-OK UX.

## Rischi

- Queue race → FIFO deduplicata e priorità host esplicita.
- Transform ancestor → osservare l'antenato animato.
- Target non-action → audit DOM e matrice per-step.
- Mobile collision → candidate scoring + regressioni FX/Settings.
- Flow explosion → soltanto tre nuove row, disclosure Settings.
- DB draft → ID esistente preservato, nuove row create da ensure/003.
- Test obsoleti → riscrittura specialistica del contratto reale.

## Definition of Done

- Cursor Round 2 ripristinato e realmente ancorato.
- Nessuna linea SVG.
- Core 1/2 invertiti; Dashboard punta al menu.
- Core FX/Settings senza overlap desktop/mobile.
- Overview senza cursor; Transazioni con pulse non bloccante.
- Quattro flow Bulk persistiti e trigger-event driven.
- Import corretto al primo mount senza scroll indotto.
- Geometry coperta da Playwright desktop/mobile.
- Nessuna migration 004 o write/navigation automatico.
- Review lane 6158 consegnata dopo gate mirati.

La review developer ha accettato ordine Core, cursor compatto e placement. Sono
superseded da Round 5: flow Bulk separati, assenza pulse sulle aree informative,
flicker `waiting`, rigidità Import opzionale e compatibilità tab stale.
