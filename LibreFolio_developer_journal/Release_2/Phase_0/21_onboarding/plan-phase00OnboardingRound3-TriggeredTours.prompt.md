# Phase 0 - Onboarding Round 3: tour granulari per trigger

← Previous: [Onboarding Round 2 — guide modulari e progressive](plan-phase00OnboardingRound2-ModularGuides.prompt.md)

**Catena:** [piano padre](plan-phase00Onboarding.prompt.md) →
[Round 1](plan-phase00OnboardingRound1-UXRefinement.prompt.md) →
[Round 2](plan-phase00OnboardingRound2-ModularGuides.prompt.md) → Round 3.

## Confine e stato

**Baseline worktree:** `4a9ae876e4599b5fdec5ade512b65b9c31a584a5` più il delta
Foundation/Round 1/Round 2 non committato.

**Stato:** pianificato; implementazione rinviata alla prossima iterazione.

Questa iterazione chiude esclusivamente i record di coordinamento. Non modifica codice
Round 3, non invoca test-author/docs-writer e non lancia suite funzionali. La review
manuale ha intenzionalmente superseded il contratto UX Round 2; testarlo o documentarlo
ora cristallizzerebbe comportamento già destinato a cambiare.

## Feedback developer accettato

- Nel Welcome, la CTA superiore è Logout: usare una chiave dedicata con copy
  **Disconnettiti**, senza cambiare globalmente `auth.logout`.
- Intro scene approvata; aggiungere tre indicatori di fase e ridurre il vuoto tra
  fade-out e fade-in.
- Core tour approvato nel complesso.
- Pannello Core centrato nel viewport; freccia/pointer con punta su un vero pulsante.
- Il marker attuale, sopra/destra del target, sembra decorativo e non indica nulla.
- Copy Tool generale: programmi e calcolatori utili alle decisioni finanziarie.
- Prima entrata in Transazioni: introdurre inserimento manuale, Import e filtri/colonne.
- Guide separate per Add Transaction e Bulk Transaction.
- Import: rendere evidente la progressione reale del wizard e stabilizzare il pointer
  al primo mount, soprattutto su Analyze.
- Broker, FX e Asset: flow distinti per pagina, Add/modal e dettaglio.
- Granularità approvata: un flow persistito per ogni trigger.
- Bulk: il primo trigger che vi entra la arma; appare quando la Bulk è topmost.
- Nessuna nuova migrazione onboarding; `003` è ancora non pubblicata dopo 1.1.0.
- Nessuna implementazione Round 3 in questa iterazione.

## Contratti da preservare

- Source of truth backend: `user_onboarding_progress`.
- Row per user+flow con status, versione e timestamp.
- SessionStorage soltanto per cursore/replay temporaneo.
- Flow dovuto se pending oppure `version < current_version`.
- Nuova versione riapre completed e skipped.
- X automatico registra skipped/current; X replay chiude solo replay.
- Host chiuso senza Finish/X lascia il flow dovuto.
- Nessun click, route jump o write automatico.
- `broker_guide`, `fx_guide`, `asset_guide` restano gli ID delle guide Add/modal
  Round 2, evitando righe draft obsolete nei DB di sviluppo.

## Catalogo flow target

### Setup e Core

| Flow | Trigger |
|---|---|
| `welcome` | route Welcome dovuta |
| `intro_tour` | post-Welcome/bootstrap |

### Transazioni

| Flow | Trigger |
|---|---|
| `transactions_page_guide` | prima entrata `/transactions` |
| `transaction_create_guide` | click Add Transaction |
| `transaction_bulk_guide` | primo ingresso Bulk, quando topmost |
| `import_guide` | apertura Import Wizard |

### Broker

| Flow | Trigger |
|---|---|
| `broker_page_guide` | prima entrata `/brokers` |
| `broker_guide` | click Add Broker |
| `broker_detail_guide` | prima entrata `/brokers/[id]` |

### FX

| Flow | Trigger |
|---|---|
| `fx_page_guide` | prima entrata `/fx` |
| `fx_guide` | click Add Pair |
| `fx_detail_guide` | prima entrata `/fx/[pair]` |

### Asset

| Flow | Trigger |
|---|---|
| `asset_page_guide` | prima entrata `/assets` |
| `asset_guide` | click Add Asset |
| `asset_detail_guide` | prima entrata `/assets/[id]` |

Tutti i nuovi flow partono pending/v1. Non simulare bump prima della prima release.

## Migrazione/backend

Modificare ancora e soltanto
`backend/alembic/versions/003_user_onboarding_progress.py`:

- Welcome esistenti completed/v1;
- ogni guida pending/v1;
- insert idempotente e unique user+flow;
- ensure crea soltanto righe mancanti;
- registry versioni unico e ordinato;
- API GET/complete/skip generiche invariate.

Aggiornare enum backend/frontend, Zod runtime e seeder. Coordinator esegue API sync.

**Vincolo:** non creare `004` o altra migrazione onboarding. La `003` non è stata
pubblicata dopo 1.1.0.

## Trigger e arbitraggio topmost

Una guida:

- parte dal proprio trigger reale;
- non apre o naviga per conto dell'utente;
- non compete con una guida già attiva;
- aspetta che il proprio host sia topmost;
- termina solo con X/Finish espliciti.

Priorità:

```text
nested/errore critico
→ guida attiva
→ guida host topmost
→ guida pagina
→ Donation/Update
```

### Bulk

- Qualsiasi intent (create/edit/clone/delete/import) arma il flow al primo ingresso.
- Add Transaction:
  - Form guide prima;
  - Bulk guide queued;
  - Bulk guide parte quando Form chiude e Bulk diventa topmost.
- Import:
  - Import guide conserva priorità;
  - dopo Finish/X, se Bulk è aperta, parte Bulk guide.
- Altri intent: Bulk guide immediata.

Il controller aggiunge una coda account-scoped `pendingContextualFlow`; non è stato
backend e non sostituisce la progress row.

## Raffinamenti visivi

### Welcome

Nuova chiave `onboarding.welcome.logout`:

- IT `Disconnettiti`;
- EN/FR/ES equivalenti inequivoci.

### Intro

- Tre lineette progress:
  - inattive neutre;
  - attiva verde e più larga;
  - non cliccabili.
- Enter 250–300 ms; exit 250–300 ms; gap 100–150 ms massimo.
- Reduced motion senza animazione ma con phase indicator coerente.

### Geometry engine

Separare message panel, spotlight e pointer.

Core:

- pannello centrato salvo collisione grave;
- spotlight/pulse sopra la patina;
- tip della freccia sul centro del target;
- orientamento dal vettore panel→target;
- marker 6–10 px sopra la CTA, non sul bordo destro.

Contestuale/Import:

- safe placement che non copre target/footer;
- tip sul centro CTA;
- direzione up/down/left/right;
- pointer-events none;
- ResizeObserver + scroll/transition;
- dopo mount/cambio step attendere due frame con rect identico;
- pubblicare `data-placement`, `data-target-stable`,
  `data-target-center-x/y`.

Questa stability gate sostituisce il comportamento Analyze che si corregge solo dopo
Back/Next.

### Tool copy

> Strumenti raccoglie programmi e calcolatori utili per esplorare scenari e prendere
> decisioni finanziarie più consapevoli.

## Sequenze

### Core

Otto step Round 2 invariati; cambiano positioning e copy Tool.

### Transactions page

1. archivio/gestione operazioni;
2. Add Transaction e guida dedicata;
3. Import massivo e guida dedicata;
4. filtri, sort, column filter e visibilità colonne;
5. Finish.

### Add Transaction

1. tipo e broker;
2. quantità/cash/asset contestuali;
3. data, opzionali e relazioni;
4. Validate/Save;
5. Finish lascia Form aperto.

### Bulk

1. workspace e draft;
2. Add Row/Import toolbar;
3. validazione e issue navigation;
4. reset/selezione;
5. Save All vs Cancel.

### Import

- intro una tantum: la guida seguirà gli step reali;
- progress sempre visibile;
- pointer CTA stabile;
- niente rettangolo;
- Analyze attende target stable;
- wizard possiede Back/Continue/Parse/Import.

### Broker pagina

1. account e ruoli/accesso;
2. target currency/report summary;
3. card/table e azioni;
4. Add Broker.

### Broker Add

Round 2 invariato: overview → default plugin → icona.

### Broker dettaglio

1. header edit/share/sync;
2. overview/cash;
3. positions/lotti;
4. transactions/import;
5. info/condivisione.

### FX pagina

1. coppie e direzione;
2. filtri/data range/viste;
3. sync/refresh;
4. Add Pair.

### FX Add

Round 2 invariato: currencies → provider routes.

### FX dettaglio

1. coppia/direzione/swap;
2. provider/sync;
3. chart/signals/measure;
4. editor manuale.

### Asset pagina

1. catalogo e stati;
2. ricerca/filtri/view mode;
3. prezzi/sync;
4. Add Asset.

### Asset Add

Round 2 invariato: search → identity → provider.

### Asset dettaglio

1. header/stato/azioni;
2. chart/signals/measure;
3. editor prezzi/eventi;
4. metadata;
5. risk.

## Settings

Gruppi:

- Setup;
- Core;
- Transazioni;
- Broker;
- FX;
- Asset.

Per dominio:

- summary `N/M guide completate`;
- disclosure per Page/Add/Detail;
- status/version;
- replay;
- armed/cancel.

Replay All arma tutti i token ma non apre route/modal/dettagli.

## Step futura implementazione

### Step 1 - Espansione flow

- enum/registry/tipi;
- modifica esclusiva `003`;
- seeder/ensure;
- API sync.

### Step 2 - Trigger/coda

- page-entry;
- detail-entry;
- Add/modal;
- Bulk topmost queue;
- arbitration/reset account.

### Step 3 - Welcome/intro polish

- Disconnettiti;
- phase indicators;
- gap fade.

### Step 4 - Geometry engine

- panel center;
- pointer tip;
- placement;
- stable rect gate;
- observer/transition.

### Step 5 - Transactions

- page/Create/Bulk;
- Import stabilization.

### Step 6 - Broker/FX/Asset

- page e detail;
- conservare Add guide;
- Tool copy.

### Step 7 - Settings

- domain summaries/disclosures;
- replay/armed.

### Step 8 - Manual-first checkpoint

- coordinator i18n/API;
- format/type-check/lint mirati;
- lane 6158;
- developer review.

Nessun test-agent/docs prima dell'OK UX.

### Step 9 - Dopo OK

- test-author;
- docs-writer;
- runner/i18n finali/CHANGELOG/master;
- gate completi/review/shutdown.

## Debito intenzionale ereditato

Round 2 non riceve test/docs finali perché superseded:

- nessun test-author Round 2;
- nessun docs-writer Round 2;
- nessuna suite funzionale completa Round 2;
- nessuna review read-only finale Round 2.

Evidenze statiche valide:

- frontend format-check verde;
- `front check` 0 errori/41 warning legacy;
- i18n 2.878/2.878 per locale;
- Ruff/Black backend verdi;
- diff-check verde.

## Checkpoint persistente pre-Round 3

**HEAD:** `4a9ae876e4599b5fdec5ade512b65b9c31a584a5`

**Branch:** `e-alfy-onboarding-foundation`

**Manifest:** 69 file tracked modificati + 18 untracked = 87 path; 0 staged,
0 unmerged.

**Delta tracked:** 6.040 inserimenti / 354 rimozioni su 69 file. I nuovi file non
sono inclusi nello stat tracked.

**Lane:** server 6158 arrestato; `lsof -nP -iTCP:6158 -sTCP:LISTEN` non restituisce
listener.

**Evidenza preservata:**

- frontend format-check verde;
- `front check` 0 errori / 41 warning legacy in due file;
- i18n 2.878/2.878 per EN/IT/FR/ES, 0 incomplete/backend missing;
- Ruff + Black verdi sui file backend Round 2;
- coordinator API sync riuscito senza delta generated tracked;
- `git diff --check` verde.

**Esclusioni:** database e upload lane sotto `/tmp/librefolio-r2-j-onboarding`,
`.testLog`, Playwright results/report, frontend build e `.svelte-kit`, cache, log,
OpenAPI/Zodios/Tool artifacts rigenerati senza delta tracked.

**Conflitti target previsti:**

- `CHANGELOG.md`;
- cataloghi `frontend/src/lib/i18n/{en,it,fr,es}.json`;
- `scripts/test_runner/_frontend_utility.py`;
- master record `09_feedbackJobs/{01_ux_dashboard,06_piano_sprint,README}.md`;
- `frontend/src/routes/(app)/dashboard/+page.svelte`, semantic overlap probabile con
  H integrato;
- possibili overlap additivi in app layout/Header/Sidebar e file API shared.

Prima di integrare l'ultimo target, preservare questo WIP con checkpoint developer/
coordinator. Nessun merge/staging/commit è stato eseguito da J.

**Commit WIP proposto:**

`feat(onboarding): add modular guide foundation`

## Definition of Done

- Welcome usa Disconnettiti;
- Intro dots + gap breve;
- Core panel centrato e pointer reale;
- Tool copy generale;
- Page/Add/Detail separati per Transactions/Broker/FX/Asset;
- Add Transaction/Bulk/Import distinti;
- Bulk first-trigger/topmost;
- Import stable al primo mount;
- Settings leggibile con molti flow;
- solo migrazione `003`;
- manual review prima dei test/docs.
