# Phase 0 - Onboarding foundation

## Stato e autorizzazione

**Baseline approvata:** `dev_release2` a
`f90d9801bd7a2d74aac6a27efe305314c6c004cc`.

**Workstream:** J, branch `e-alfy-onboarding-foundation`.

**Autorizzazione developer relayed verbatim dal coordinatore, 2026-09-10:**
`Approva J fondazione indipendente (Consigliato)`.

Questo piano prende in carico soltanto la fondazione indipendente di SP11/U8. Le
integrazioni shell, Tool/PAC e DataImport restano congelate fino ai checkpoint D/F e a
una nuova autorizzazione esplicita.

## Obiettivo

Consegnare:

- persistenza onboarding per-user e per-flow, indipendente da `login_count`;
- migrazione incrementale con grandfathering degli utenti esistenti;
- API dedicate per lettura, completamento e skip;
- primitive frontend account-scoped per bootstrap, replay, anchor e coachmark;
- pagina/componenti welcome isolati, non ancora collegati alla shell;
- test backend e frontend mirati, scritti tramite `test-author`.

## Contratti approvati

### Persistenza

Nuova tabella `user_onboarding_progress`, con una riga per `(user_id, flow)`:

- `flow`: `welcome | intro_tour | import_guide`;
- `status`: `pending | completed | skipped`;
- `version`: versione contenuto associata allo stato;
- timestamp di creazione, aggiornamento e transizione terminale;
- vincolo univoco `user_id + flow`;
- FK utente con cancellazione coerente al modello esistente.

La migrazione inserisce in modo idempotente tre righe
`completed / current-version` per ogni utente gia presente. Gli utenti creati dopo
l'upgrade e le righe mancanti nascono `pending / current-version`. Gli upsert runtime
inseriscono solo righe mancanti e non sovrascrivono mai stati terminali.

La sola condizione che richiede onboarding automatico e `status == pending`. Un
`version < current_version` espone soltanto `update_available`; non riapre
automaticamente flow `completed` o `skipped`.

`flow` viene persistito come stringa validata dal registry applicativo, non come enum
DB chiuso: un flow futuro non richiede `ALTER TABLE`.

### Estensibilita futura

Un nuovo step dentro un flow esistente aggiunge un ID semantico alla configurazione
frontend e incrementa la versione contenuto. Non richiede migrazione DB. Gli utenti
terminali non vengono riaperti; Settings puo proporre replay volontario. Un resume
token di una versione precedente viene invalidato o riportato al primo step ancora
valido, mai applicato per indice.

Un nuovo flow aggiunge una voce ai registry backend/frontend. La tabella resta
invariata; una migrazione solo-dati inserisce il flow per gli utenti esistenti con
policy esplicita, normalmente `completed` per non forzarli. Gli utenti nuovi ricevono
il flow `pending`.

### API

Login e `/auth/me` restano invariati. Nuova superficie dedicata sotto settings:

- GET stato dei flow;
- complete di un flow;
- skip di un flow;
- conflitto esplicito su versione client stale;
- operazioni terminali idempotenti.

Il completamento welcome con preferenze in una transazione atomica resta un contratto
per la fase di raccordo. Questa fondazione non altera login o layout.

### Replay

Replay manuale:

- e session-scoped e account-scoped;
- non riscrive preventivamente lo stato terminale backend;
- conserva lo stato precedente se viene abbandonato;
- aggiorna backend solo al completamento/skip esplicito;
- invalida risultati async appartenenti a una generazione account precedente.

### Frontend

La fondazione espone:

- tipi onboarding indipendenti dal client generato;
- store/controller con adapter API iniettabile;
- bootstrap generation-guarded;
- session storage namespaced per user/flow/version;
- registry di anchor semantici;
- coachmark accessibile, responsive e reduced-motion safe;
- welcome form/page isolati.

Nessun mount nella shell e nessun redirect automatico entra in questo checkpoint.

## Superfici autorizzate

Backend:

- `backend/app/db/models.py`;
- nuova revisione in `backend/alembic/versions/`;
- `backend/app/schemas/settings.py`;
- nuovo service onboarding dedicato;
- `backend/app/api/v1/settings.py`;
- test backend onboarding.

Frontend, preferendo nuovi file:

- `frontend/src/lib/types/onboarding.ts`;
- `frontend/src/lib/stores/app/onboarding.svelte.ts`;
- `frontend/src/lib/features/onboarding/**`;
- `frontend/src/lib/components/onboarding/**`;
- `frontend/src/routes/(app)/welcome/+page.svelte`;
- test unit/component onboarding.

## Superfici bloccate

Fino ai checkpoint D/F e a nuova autorizzazione:

- `frontend/src/routes/(app)/+layout.svelte`;
- `frontend/src/routes/+page.svelte`;
- `frontend/src/lib/components/layout/Sidebar.svelte`;
- `frontend/src/lib/components/layout/Header.svelte`;
- `frontend/src/lib/components/settings/tabs/PreferencesTab.svelte`;
- `frontend/src/routes/(app)/settings/+page.svelte`;
- `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte`;
- `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte`;
- `frontend/src/lib/components/assets/AssetModal.svelte`;
- mount/arbiter di DonationPopup e UpdateAvailable;
- `CsvEditor`, `DataImportModal` e wrapper DataImport posseduti da F.

Il coordinatore possiede:

- API sync e client generato;
- cataloghi i18n EN/IT/FR/ES;
- registrazioni test runner;
- MkDocs nav;
- `CHANGELOG.md` e record master Release 2.

## Lane runtime

Ogni comando usa:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
```

Lane esclusiva J:

- porta `6158`;
- data dir assoluta `/tmp/librefolio-r2-j-onboarding`;
- nessun `server --force`;
- una sola operazione runtime alla volta.

## Passi

### Step 0 - Analisi, storyboard e contratto

**Stato:** completato il 2026-09-10.

> **Note implementazione**: verificata baseline esatta, adottato agent binding,
> analizzati auth/settings/session, UserSettings, layout/popup/Header, Preferences,
> ImportWizard/Bulk e dipendenze D/F. Storyboard desktop/mobile, addendum route/API ed
> estensibilita futura approvati per l'avvio della fondazione indipendente.

### Step 1 - Modello e migrazione

**Stato:** completato il 2026-09-10.

Creare modello, revisione Alembic incrementale, unique constraint e backfill
idempotente. Verificare upgrade/downgrade su DB popolato senza forzare utenti esistenti.

> **Note implementazione**: aggiunti `OnboardingFlow`, `OnboardingStatus` e
> `UserOnboardingProgress`; colonna `flow` stringa, unique `(user_id, flow)`, FK cascade,
> version/timestamp terminali. Migrazione incrementale
> `003_user_onboarding_progress.py`: existing users backfilled
> `completed/current-version`, nuovi utenti lasciati al bootstrap pending, downgrade
> limitato alla nuova tabella. Gate ufficiali:
> `... dev.py test --test-port 6158 --data-dir
> /tmp/librefolio-r2-j-onboarding db validate` -> 15/15;
> `... db referential-integrity` -> 13/13.

### Step 2 - Service, schema e API dedicate

**Stato:** completato il 2026-09-10.

Implementare ensure/read/complete/skip con:

- stato terminale mai sovrascritto dal bootstrap;
- versione stale esplicita;
- response con `current_version` e `update_available`;
- isolamento per current user;
- idempotenza documentata.

> **Note implementazione**: nuovo `onboarding_service.py` con registry versioni,
> ensure insert-only, snapshot ordinato, transizioni complete/skip idempotenti e
> `OnboardingVersionMismatchError`. Aggiunti DTO strict e endpoint dedicati
> `GET /settings/onboarding`,
> `POST /settings/onboarding/{flow}/complete|skip`; login e `/auth/me` invariati.
> Gate ufficiali:
> `... services settings` -> 19/19 dopo repair test-only UTC e regressione avatar
> null;
> `... api settings` -> 32/32.

### Step 3 - Store/controller frontend

**Stato:** completato il 2026-09-10.

Creare tipi, adapter API iniettabile, store/controller generation-guarded e replay
session-scoped. Nessun import del client generato nuovo e nessun mount shell.

> **Note implementazione**: aggiunti tipi frontend indipendenti, adapter Axios con
> validazione Zod, controller Svelte 5 con ticket user/generation/sequence, stato
> osservabile e transizioni idempotenti. Replay in `sessionStorage` usa chiavi
> user/flow/version, non chiama API all'avvio, invalida versioni/step obsoleti e
> rimuove payload corrotti. Registry anchor semantico separato e account-resettable.
> Gate `... front-utility core-unit` -> 81 file / 1.957 test verdi.

### Step 4 - Anchor, coachmark e welcome isolati

**Stato:** completato il 2026-09-10.

Creare registry anchor semantico, coachmark accessibile e welcome form/page isolati.
Usare `data-testid`, stato osservabile, focus/tastiera/mobile/reduced-motion. Non
toccare shell, popup, Header/Sidebar o wizard.

> **Note implementazione**: aggiunti action/registry anchor, coachmark non modale con
> waiting/error/anchored state, ARIA linkage ripristinata, Escape=pause, focus policy,
> layout mobile e reduced-motion. Welcome form staged riusa controlli settings, avatar
> opzionale e ImagePicker wrapper; pagina `/welcome` carica endpoint dedicato ma non
> impone redirect/mount shell. Review read-only ha rilevato landmark `main` annidati:
> sostituiti con root `div`. Gate action stretta
> `... front-utility onboarding-component-unit` -> 3 file / 43 test verdi.

### Step 5 - Test mirati

**Stato:** completato il 2026-09-10.

Invocare `test-author`. Coprire:

- migration/backfill/idempotenza;
- API current-user, terminal states e stale version;
- generation guard e account switching;
- replay senza mutazione terminale anticipata;
- anchor lifecycle;
- coachmark keyboard/mobile semantics;
- welcome staged state ed errori.

Nessuna modifica runner senza passaggio coordinatore.

> **Note implementazione**: `test-author` ha esteso test registrati backend per
> service/API/migrazione/FK e creato cinque spec frontend con harness locali. Aggiunta
> regressione avatar `null` (omesso preserva, esplicito azzera) e isolamento del wrapper
> immagini per evitare import graph estraneo. Il coordinator ha delegato la sola
> registrazione runner: due spec logic in `core-unit`, tre spec component nella nuova
> action `onboarding-component-unit`. `check-orphans` -> tutti i 196 backend, 77 E2E e
> 200 unit frontend registrati e raggiungibili. `front check` finale -> 0 errori,
> 41 warning legacy in 2 file non J.

> **⚠️ Fuori pista 2026-09-10**: il subagent backend, nonostante il divieto di
> runtime, ha eseguito `py_compile`, Ruff/Black mirati e uno script Alembic su
> `/tmp/lf_onboarding_migration_sanity`; ha poi rimosso la directory. Non ha avviato
> server/test suite ne usato porta 6158 o data lane J. Queste prove non vengono
> conteggiate come gate ufficiali; la validazione viene ripetuta dalla lane assegnata.
>
> **⚠️ Fuori pista 2026-09-10**: il gate ufficiale
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6158 --data-dir /tmp/librefolio-r2-j-onboarding services settings`
> ha creato il DB test nella lane, raccolto 18 test e chiuso con 17 pass / 1 fail.
> Il rosso e nella nuova assertion di test: timestamp ORM SQLite naive confrontato
> direttamente con lo stesso timestamp normalizzato UTC dallo schema response. Nessun
> server avviato; DB e archivio test lane toccati. Riparazione delegata a `test-author`,
> senza modificare il comportamento prodotto.

### Step 6 - Gate e checkpoint foundation

**Stato:** completato il 2026-09-10.

Eseguire soltanto gate mirati esistenti nella lane J, controllare diff e port shutdown,
aggiornare ogni step/evidenza, poi consegnare checkpoint:

- inventario file;
- evidenze pass/fail;
- generated/ignored esclusi;
- conflitti D/F;
- lista esatta integrazioni ancora bloccate;
- commit message proposto;
- stato finale `FROZEN`.

> **Note implementazione**: gate finali completati. `front check` -> 0 errori,
> 41 warning legacy in 2 file non J; Prettier check dei 16 file frontend J -> verde;
> Ruff/Black backend -> verdi; Ruff mirato runner -> verde; `check-orphans` ->
> 196 backend, 77 E2E e 200 unit frontend registrati e raggiungibili; `git diff
> --check` -> verde. Review code indipendente: unico rilievo landmark `main` annidato
> corretto; follow-up reviewer senza rilievi. Delta: 10 file tracked modificati e
> 19 file nuovi. Nessuna superficie D/F bloccata modificata; eccezione autorizzata
> coordinator: `scripts/test_runner/_frontend_utility.py`, da integrare semanticamente
> con i cambi staged D. `lsof -nP -iTCP:6158 -sTCP:LISTEN` -> porta libera.
>
> Artefatti esclusi: `frontend/node_modules`, `.svelte-kit`, client API generato,
> `.testLog`, snapshot/archivi test e DB lane `/tmp/librefolio-r2-j-onboarding`.
> Nessun file privato o runtime destinato al checkpoint.
>
> Commit proposto: `feat(onboarding): add versioned foundation`.

> **⚠️ Fuori pista 2026-09-10**: il comando mirato
> `test -x frontend/node_modules/.bin/prettier && ... --write ...` e terminato con
> exit 1 prima di eseguire Prettier, perche il binario locale non esiste nel worktree.
> Nessun file, DB o server e stato toccato. Nessuna dipendenza e stata installata;
> bootstrap frontend richiesto al coordinatore come previsto dal binding.
>
> **⚠️ Fuori pista 2026-09-10**: dopo autorizzazione coordinator e stato eseguito una
> sola volta `npm --prefix frontend ci` (433 package dal lockfile; nessun audit fix).
> Il primo Prettier mirato lanciato dalla root ha fallito prima di scrivere perche il
> plugin Svelte veniva risolto da `noop.js`; lo stesso comando dalla cwd `frontend/`
> ha formattato correttamente i soli file J.
>
> **⚠️ Fuori pista 2026-09-10**: `... dev.py front check` non e utilizzabile come
> verdetto globale in questo worktree: il client coordinator-owned
> `frontend/src/lib/api/generated.ts` e assente, generando errori a cascata baseline.
> Le sole diagnostiche J isolate erano DOMRect proxied/a11y nel coachmark e typing mock
> Vitest; entrambe riparate. Nessun API sync e stato eseguito da J.
>
> **⚠️ Fuori pista 2026-09-10**: dopo delega coordinator sono stati registrati
> esattamente cinque path onboarding in `scripts/test_runner/_frontend_utility.py`.
> Questo file potra confliggere con i cambi runner staged di D: integrazione semantica,
> preservando entrambe le liste. Il primo `component-unit` completo ha mostrato 18
> failure test-only per collisione della prop `anchor` con le render options di Testing
> Library, poi riparate via `test-author`; nello stesso run un worker e uscito.
> Il rerun filtrato `... front-utility component-unit OnboardingCoachmark WelcomeForm
> WelcomePage` ha completato 39 test onboarding verdi su due file, poi il terzo worker
> ha raggiunto il limite heap V8 di 4 GB durante l'import dell'intero catalogo
> component-unit. Verdetto `test-triage`: **environment**, nessuna assertion prodotto
> rossa. Vietato alzare heap; richiesto al coordinator un gate runner che selezioni
> realmente i soli file onboarding.

## Definition of done del checkpoint

- utenti esistenti terminali dopo upgrade;
- utenti nuovi/missing pending senza usare `login_count`;
- tre flow separati e versionati;
- skip terminale idempotente;
- version mismatch passivo;
- API auth invariata;
- replay account/session-scoped;
- nessuna risposta async applicata dopo cambio account;
- primitive frontend testabili senza shell;
- welcome isolato senza redirect/mount condivisi;
- nessuna modifica alle superfici D/F o coordinator-owned;
- piano aggiornato immediatamente dopo ogni step;
- lane arrestata e porta libera al checkpoint.

## Scope futuro, non autorizzato

Raccordo successivo:

- fetch parallelo settings/onboarding nel layout con generation guard;
- conditional shell via route-id strict;
- redirect welcome/deep-link;
- popup arbiter;
- Header/Sidebar tour pins;
- Settings replay controls;
- ImportWizard/Bulk semantic anchors;
- API sync, i18n, docs e review operativa integrata.
