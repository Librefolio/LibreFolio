# Phase 0 - Onboarding Round 2: guide modulari e progressive

← Previous: [Onboarding Round 1 — UX refinement](plan-phase00OnboardingRound1-UXRefinement.prompt.md)

## Stato e autorizzazione

**Baseline worktree:** `4a9ae876e4599b5fdec5ade512b65b9c31a584a5` più il delta
onboarding Foundation/Round 1 non committato.

**Autorizzazione developer relayed verbatim dal coordinator, 2026-09-11:**
`J Round 2 plan approved by developer through plan approval UI (interactive/manual-first).`

**Lane:** porta `6158`, data dir `/tmp/librefolio-r2-j-onboarding`, venv
`LibreFolio-SAUMUTtc`.

## Feedback developer

- Il Welcome deve cambiare lingua mentre si usa il selettore, non dopo Continue.
- L'uscita replay del Welcome va nel footer sinistro, accanto a Continue; rimuovere
  l'hint descrittivo rifiutato.
- La scena introduttiva richiede logo LibreFolio e frasi con fade in/out netto.
- Il primo Back deve essere visibile ma disabilitato.
- Nel Core tour il pulse deve emergere sopra la patina.
- Il Core tour deve spiegare soltanto Dashboard, burger/sidebar e destinazioni
  principali, senza saltare automaticamente tra pagine.
- Broker, FX e Asset diventano guide contestuali separate, attivate dal click reale
  su Add.
- Broker deve spiegare default import plugin e icona custom, non il solo saldo.
- FX deve spiegare coppia e provider.
- Asset deve spiegare ricerca/identità/configurazione e provider, non la sola valuta.
- Nei flow interattivi e Import: niente rettangolo/backdrop; solo message block e
  frecce verso le CTA utili.
- La guida Import deve rendere evidente che prosegue con gli step reali del wizard.
- Settings deve dare feedback forte quando una guida è armata.
- X non sospende: chiude definitivamente la versione corrente. In replay chiude solo
  il replay, senza mutare lo stato terminale.
- Una nuova versione del flow deve ripartire automaticamente anche dopo completed o
  skipped.
- Prototipo manuale prima di test-author, docs-writer e suite estese.

## Stato tecnico di partenza

- `user_onboarding_progress` persiste backend `flow`, `status`, `version` e timestamp.
- `sessionStorage` conserva soltanto cursore e replay temporanei.
- `OnboardingProgressItem` espone già `current_version` e `update_available`.
- Flow correnti: `welcome`, `intro_tour`, `import_guide`.
- Predicate automatico corrente: solo `status === pending`.
- Tour corrente: 13 step monolitici con preview automatiche Broker/FX/Asset.
- Import ancora il rettangolo all'intero contenuto dello step.
- `003_user_onboarding_progress.py` non è pubblicata; ultima release `1.1.0`.
- Graphify non è disponibile nel worktree e il devWiki non contiene user-onboarding.

## Decisioni architetturali

### Flow

Persistiti separatamente:

1. `welcome`;
2. `intro_tour` — nome API compatibile, UX “Core tour”;
3. `broker_guide`;
4. `fx_guide`;
5. `asset_guide`;
6. `import_guide`.

Trigger:

- Welcome: route obbligatoria se dovuto;
- Core: dopo Welcome/bootstrap;
- Broker/FX/Asset: solo click reale su Add;
- Import: solo apertura reale del wizard.

### Version policy

Un flow è dovuto quando `status === pending` **oppure**
`version < current_version`.

- La nuova versione riapre automaticamente completed e skipped.
- X su automatico chiama skip e registra la versione corrente.
- Finish su automatico chiama complete e registra la versione corrente.
- X/Finish in replay cancellano soltanto il token sessione.
- Chiusura della superficie ospite senza X/Finish interrompe la UI ma lascia il flow
  dovuto; il prossimo trigger riparte dal primo step utile.
- Nessun bump artificiale prima della prima release del sistema: contenuti correnti
  restano v1. In seguito si incrementa soltanto il flow modificato.

### Migrazione

Non creare `004`.

Modificare la non pubblicata `003_user_onboarding_progress.py`:

- aggiungere i tre flow contestuali;
- utenti esistenti 1.1:
  - Welcome `completed/v1`;
  - Core/Broker/FX/Asset/Import `pending/v1`;
- nuovi utenti: ensure idempotente crea ogni flow `pending/current`;
- downgrade continua a rimuovere la tabella.

DB di sviluppo già migrati ricevono righe mancanti tramite ensure; la lane test viene
ricreata.

### Catalogo frontend

Estrarre un catalogo tipizzato per flow:

- versione backend;
- trigger `automatic | contextual`;
- presentation `spotlight | pointer`;
- step ordinati;
- anchor/copy/controlli;
- policy di completion.

Controller generico:

- `isDue`;
- `maybeStartFlow`;
- `armReplay`;
- `setStep(step, progress?)`;
- `next` / `previous`;
- `finish`;
- `exit`;
- `dismissHost`;
- reset account/generation.

## UX target

### Spotlight Core

- Quattro pannelli scuri attorno all'anchor, con foro trasparente.
- Anchor visibile, pulse verde evidente sopra la patina.
- Freccia verso il comando.
- Shell inert.
- Back/Next; primo Back disabilitato.

### Pointer contestuale

- Nessun backdrop, rettangolo o inert.
- Message block compatto.
- Freccia animata `pointer-events: none` vicino alla CTA.
- Superficie completamente interattiva.
- Nessun click sintetico.

### Welcome

- Preview locale immediata e reversibile:
  - aggiorna il catalogo i18n;
  - non scrive backend/localStorage;
  - Skip/Exit/Logout ripristinano la lingua persistita;
  - Continue la salva.
- Brand lockup `/logo.png` + LibreFolio.
- Footer:
  - sinistra `Salta configurazione` o `Esci dal tour`;
  - destra Continue.
- Rimuovere `exitReplayHint`.

### Intro scene

- Brand lockup con logo.
- Tre frasi `enter → hold → exit → blank`.
- Fade + lieve translate/blur; Start e auto-start one-shot a 10 s.
- Reduced motion statico.
- Solo X, con semantica mode-aware.

### Core tour

Tutto sulla Dashboard:

| # | Step | Anchor |
|---|---|---|
| 1 | Dashboard | `page.dashboard` |
| 2 | Burger/collapse | `nav.toggle.*` |
| 3 | Transazioni | `nav.transactions` |
| 4 | Broker | `nav.brokers` |
| 5 | FX | `nav.fx` |
| 6 | Asset | `nav.assets` |
| 7 | Tool | `nav.tools` |
| 8 | Settings/replay | `nav.settings` |

Su mobile il drawer si apre per gli step menu e resta aperto fino a Finish/X. Nessuna
navigazione automatica.

### Broker guide

Click reale Add Broker:

1. orientamento modale;
2. default Import Plugin;
3. icona personalizzata;
4. Finish, form ancora aperto.

### FX guide

Click reale Add Pair:

1. base/quote;
2. provider/route diretta, chain e manuale;
3. Finish, form ancora aperto.

### Asset guide

Click reale Add Asset:

1. ricerca online/auto-fill;
2. identità: nome, tipo, quote base, valuta;
3. provider/identificatore/parametri/no-provider;
4. Finish, form ancora aperto.

### Import guide

- Message-only, nessun backdrop/rettangolo/inert.
- Progress reale tra gli step visibili.
- Copy: `Continua usando il comando indicato`.
- Frecce verso:
  - `import-wizard-next`;
  - `import-wizard-parse`;
  - `import-wizard-continue`;
  - Continue Assets/Fix/Duplicates;
  - `import-wizard-import`;
  - `tx-bulk-commit`.
- Nested modal nasconde il message block e lo ripristina allo stesso step.
- Finish guida e Save All restano separati.
- Una sola nota di sicurezza per flow; eliminare ripetizioni “non salva”.

### Settings

Gruppi:

- Setup: Welcome;
- Core: navigazione;
- Contestuali: Broker, FX, Asset, Import.

Dopo arm replay:

- badge prominente con check;
- testo “Guida pronta…”;
- toast/evento `onboarding.replay.armed`;
- azione `Annulla attivazione`.

Replay All avvia Welcome/Core in sequenza e lascia i contestuali armati al trigger
reale. Mostrare `vista vN / corrente vM` e “Nuova versione da vedere”.

## Step di implementazione

### Step 1 - Piano e cross-link

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** creato questo piano e aggiunti link padre → Round 2 e
> Round 1 → Round 2. Decisioni developer su flow, X, version policy e riuso di `003`
> incorporate.

### Step 2 - Backend flow/version contract

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** `OnboardingFlow`, registry backend, schema runtime
> frontend e Zod validator includono `broker_guide`, `fx_guide`, `asset_guide`.
> Riutilizzata esclusivamente la migrazione non pubblicata `003`: Welcome viene
> backfillato completed/v1, tutti i guide flow pending/v1. Il seeder canonico itera
> già il registry e continua a rendere terminali gli account E2E senza modifica
> speciale. Endpoint e shape API restano generici; richiesto al coordinator il sync
> del client per l'enum esteso.
>
> **⚠️ Fuori pista:** la regola generale “nuova migrazione incrementale” non si
> applica qui perché il developer ha confermato che nessuna migrazione onboarding è
> stata pubblicata dopo 1.1.0. Creare `004` sarebbe stato rumore senza compatibilità
> reale da proteggere.

- enum/registry;
- predicate stale-version due;
- migrazione `003`;
- seeder;
- API generica invariata;
- handoff API sync coordinator.

### Step 3 - Controller e catalogo

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** aggiunto `onboardingGuideCatalog.ts` con cinque guide,
> step tipizzati, trigger e presentation mode. Il controller ora usa
> `pending || version < current_version`, avvia flow contestuali, arma replay
> generici, gestisce progress dinamico Import e separa `exit()` terminale/mode-aware
> da `dismissHost()` non terminale. Gli alias Round 1 restano temporaneamente per non
> rompere la compilazione dei test prima dell'OK developer.

- catalogo tipizzato;
- controller generico;
- mode-aware X/Finish;
- trigger automatic/contextual;
- account/refresh guards.

### Step 4 - Welcome e scena

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** il selettore Welcome applica una preview del catalogo
> senza persistere; Skip/Exit/Logout ripristinano la lingua salvata e Continue la
> rende definitiva. Azione secondaria spostata nel footer, hint rimosso, brand lockup
> con `/logo.png`. La scena usa stati enter/hold/exit con opacity/translate/blur,
> reduced motion e sola X mode-aware.

- locale preview reversibile;
- footer azioni;
- brand;
- animazione Apple-style;
- primo Back disabilitato.

### Step 5 - Core navigation

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** il Core conserva scena + otto step tutti su Dashboard:
> dashboard, toggle responsive e ciascuna destinazione Sidebar. Il primo Back è
> visibile/disabilitato. `OnboardingCoachmark` supporta spotlight a quattro pannelli
> con foro trasparente, pulse sopra la patina e pointer animato; nessuna route feature
> viene aperta.

- otto step Dashboard/Sidebar;
- no route hopping;
- spotlight cutout/pulse/freccia;
- responsive drawer.

### Step 6 - Guide Broker/FX/Asset

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** rimosse dal runtime le registrazioni che aprivano preview
> automatiche. I click Add reali avviano i flow contestuali sulle modali normali;
> chiudere l'host usa `dismissHost()` e lascia il flow dovuto. Anchor aggiunti:
> Broker title/plugin/icona, FX currencies/provider routes, Asset search/identity/
> provider. Il pointer message block non applica backdrop, rettangolo o inert.

- trigger click reali;
- anchor significativi;
- pointer mode interattivo;
- nessuna preview automatica runtime.

### Step 7 - Import e Settings

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** il wizard pubblica progress reale e ancora ogni step
> sulla CTA effettiva; Bulk resta ancorato a Save All. Il message block pointer mostra
> una freccia e istruzione contestuale senza velo. Settings raggruppa Setup/Core/
> Contestuali, arma ogni flow generico, mostra badge prominente, toast strutturato e
> permette `Annulla attivazione`. Replay All conserva i contestuali fino al click
> reale.

- CTA anchor/progress reale;
- message-only + frecce;
- feedback replay armato/cancel;
- copy ridotta.

### Step 8 - Checkpoint manual-first

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** coordinator API sync completato senza delta tracked
> (endpoint generici invariati) e cataloghi EN/IT/FR/ES aggiornati. Gate volutamente
> limitati al prototipo: frontend format-check verde, `front check` 0 errori / 41
> warning legacy in due file, audit i18n 2.878/2.878 per locale, Ruff + Black verdi
> sui tre file backend, `git diff --check` verde. Nessuna suite funzionale, nessun
> test-author e nessun docs-writer avviati in questo round.
>
> **Review runtime:** server test avviato senza `--force` con
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py server --test
> --port 6158 --data-dir /tmp/librefolio-r2-j-onboarding`; PID 25282 in ascolto su
> `*:6158`, health `{"status":"ok"}`.

- coordinator API sync/i18n;
- format + build/type-check necessari;
- reset/upgrade lane J;
- server 6158;
- runbook developer.

Nessun test-author/docs-writer/suite estesa prima del feedback.

### Step 9 - Iterazioni developer

**Stato:** ✅ review manuale completata (2026-09-11).

> **Note review developer:** approvati Welcome, intro scene e Core tour nel loro
> impianto generale. Richiesti per Round 3: copy Logout non ambigua; indicatori fase
> intro e gap fade ridotto; pannello Core centrato e pointer realmente agganciato alla
> CTA; copy Tool generalizzata; guide separate pagina/Add/dettaglio; guide dedicate
> Transactions page, Add Transaction e Bulk; stabilità pointer Import; introduzioni
> pagina/dettaglio Broker, FX e Asset.
>
> **Decisioni confermate:** granularità “un flow per trigger” anche per Broker; Bulk
> si arma al primo trigger che vi entra e parte quando diventa topmost. Nessuna
> implementazione Round 3 in questa iterazione.

- mantenere server aperto;
- correggere feedback;
- ottenere OK UX esplicito.

### Step 10 - Test/docs/gate dopo OK

**Stato:** superseded dal Round 3; debito intenzionale.

> **Note coordinamento:** non invocare test-author/docs-writer e non completare le
> suite funzionali sul contratto Round 2, ormai destinato a cambiare. Test, docs,
> runner, record finali e review read-only verranno aggiornati una sola volta dopo
> l'OK UX Round 3. Restano valide le evidenze statiche del checkpoint manual-first:
> format frontend verde; `front check` 0 errori/41 warning legacy; i18n
> 2.878/2.878 per locale; Ruff/Black backend verdi; diff-check verde.

- test-author;
- docs-writer;
- runner/i18n finali/CHANGELOG/master coordinator;
- backend/frontend/E2E/MkDocs/review;
- shutdown lane e checkpoint.

## Superfici previste

Backend:

- `backend/app/db/models.py`
- `backend/app/services/onboarding_service.py`
- `backend/alembic/versions/003_user_onboarding_progress.py`
- seeder e test onboarding esistenti.

Frontend:

- tipi/store/controller/catalogo onboarding;
- OverlayHost, Coachmark/message block, IntroScene, ReplaySection;
- Welcome route/page/form;
- app layout e Sidebar;
- pagine/modali Broker, FX, Asset;
- ImportWizardModal e TransactionBulkModal;
- cataloghi i18n coordinator-owned.

Dopo OK:

- test store/controller/component/modal;
- auth/settings/onboarding-tour/import E2E;
- docs EN esistenti;
- runner, changelog e record condivisi.

## Rischi

- Esplosione flow → catalogo unico e controller generico.
- Vecchi utenti bloccati → Welcome terminale; guide contestuali solo al trigger.
- Versione invasiva → bump per-flow, X chiude la sola versione corrente.
- Overlay che impedisce uso → pointer mode senza backdrop/rettangolo.
- Anchor mancante → waiting esplicito, nessun click sintetico.
- Copy rumorosa → nota sicurezza una volta per flow.
- Test che cristallizzano gusto prematuro → test/docs soltanto dopo OK.
- Migrazione inutile → riuso `003`, esplicitamente autorizzato perché non pubblicato.

## Definition of Done

- lingua Welcome live e persistita solo con Continue;
- footer Welcome corretto, hint rimosso;
- logo + fade enter/hold/exit;
- Core soltanto Dashboard/nav, primo Back disabilitato;
- pulse visibile sopra spotlight;
- Broker/FX/Asset contestuali e interattivi;
- Import message-only con progress/frecce CTA;
- replay armato evidente in Settings;
- X terminale per automatico e non distruttiva in replay;
- nuova versione riapre completed e skipped;
- solo migrazione `003`;
- prototipo provato prima dei test estesi;
- dopo OK: test/docs/gate verdi e server spento.

→ Follow-up: [Onboarding Round 3 — tour granulari per trigger](plan-phase00OnboardingRound3-TriggeredTours.prompt.md)
