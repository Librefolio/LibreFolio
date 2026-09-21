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

### Mandato successivo - integrazione condivisa

**Nuova baseline integrata verificata:** merge `4a9ae876e4599b5fdec5ade512b65b9c31a584a5`,
parent fondazione `8d9761db1` + target integrato `570beb386`.

**Autorizzazione coordinator su mandato developer, 2026-09-10:**
procedere con l'integrazione condivisa onboarding sulle superfici prima bloccate,
preservando D Tool/PAC e F DataImport/AssetModal. La review manuale developer resta
obbligatoria prima di archivio/chiusura.

Il mandato include:

- bootstrap auth/settings/onboarding condiviso e conditional welcome shell via route-id;
- gate redirect della root pubblica;
- pin guida Header e anchor semantici Sidebar/Tools;
- stato/replay per-flow in Settings;
- arbitraggio guide, DonationPopup e UpdateAvailable;
- guida ImportWizard sui veri step condizionali, sospensione nested modal e handoff
  Bulk/Save All senza click o scritture automatiche;
- test via `test-author`, documentazione inglese via `docs-writer`;
- richiesta al coordinator, non modifica J, per API sync, cataloghi i18n, MkDocs nav e
  changelog/master records.

### Follow-up UX Round 1

Il feedback operativo del primo tour apre
[plan-phase00OnboardingRound1-UXRefinement.prompt.md](plan-phase00OnboardingRound1-UXRefinement.prompt.md).
Il follow-up conserva questa fondazione e rifinisce insieme Welcome, tour introduttivo
e guida Import; la review manuale complessiva viene rinviata al prossimo sprint.

### Follow-up UX Round 2

La seconda review manuale apre
[plan-phase00OnboardingRound2-ModularGuides.prompt.md](plan-phase00OnboardingRound2-ModularGuides.prompt.md):
il tour monolitico viene separato in Core, Broker, FX, Asset e Import, con consegna
manual-first prima della nuova campagna test/docs.

### Follow-up UX Round 3

La review manuale del prototipo modulare apre
[plan-phase00OnboardingRound3-TriggeredTours.prompt.md](plan-phase00OnboardingRound3-TriggeredTours.prompt.md):
ogni pagina, Add/modal e dettaglio riceve un flow versionato per trigger; Round 3
inizierà in una nuova iterazione e riutilizzerà ancora la migrazione non pubblicata
`003`, senza crearne una nuova.

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

Il blocco storico seguente e stato superato dal mandato di integrazione condivisa
registrato sopra. I punti diventano gli step 7-13; non cancellare questo elenco, per
conservare il confine del checkpoint foundation:

- fetch parallelo settings/onboarding nel layout con generation guard;
- conditional shell via route-id strict;
- redirect welcome/deep-link;
- popup arbiter;
- Header/Sidebar tour pins;
- Settings replay controls;
- ImportWizard/Bulk semantic anchors;
- API sync, i18n, docs e review operativa integrata.

## Integrazione condivisa - passi autorizzati

### Step 7 - Riconciliazione post-merge D/F

**Stato:** completato il 2026-09-10.

Verificare il merge target, risolvere semanticamente il runner condiviso, rileggere
interamente le superfici shell/settings/import aggiornate e congelare il contratto di
integrazione senza perdere Tool/PAC, DataImport o AssetModal.

> **Note implementazione**: unico conflitto merge in
> `scripts/test_runner/_frontend_utility.py` risolto come union: registrazioni/path
> Tool/PAC D e cinque test onboarding J tutti preservati, component onboarding esclusi
> dal catalogo monolitico. Coordinator ha staged, developer ha creato merge
> `4a9ae876`; worktree pulito, `MERGE_HEAD` assente. Audit read-only post-merge ha
> verificato Sidebar `/tools`, PAC component/E2E, DataImport/AssetModal, step machine
> ImportWizard e profondita ModalBase. Nessuna modifica developer manual-review
> concorrente e stata segnalata sulle superfici condivise.

### Step 8 - Welcome atomico e bootstrap condiviso

**Stato:** completato il 2026-09-10.

Implementare completamento welcome atomico preferenze+progress, bootstrap
auth/settings/onboarding generation-guarded, root redirect gate e conditional shell
strict route-id. Welcome non istanzia Sidebar/Header/Footer/Donation/Update. Errore
bootstrap sconosciuto/pending blocca con Retry/Logout; stato terminale cached dello
stesso account puo fail-open con banner retry.

> **Note implementazione**: `welcome_settings` opzionale sul comando complete attiva
> una singola transazione backend per preferenze + progress; stale version e commit
> failure lasciano entrambe le tabelle invariate. Nuovo `appBootstrap` iniettabile
> carica settings/onboarding/global in parallelo, applica generation guard,
> blocked/degraded policy e redirect safe. Root login/check usa lo stesso gate.
> `(app)/+layout` usa route-id strict, blocca ogni flash mentre redirige e sul welcome
> non istanzia shell, toast o popup. Gate: `services settings` 24/24, `api settings`
> 37/37, `front-utility core-unit` 82 file / 2.016 test,
> `onboarding-component-unit` 3 file / 50 test. Test shell/E2E integrati restano nello
> Step 12 insieme alle guide.

> **⚠️ Fuori pista 2026-09-10**: primo gate ufficiale Step 8
> `... dev.py test --test-port 6158 --data-dir
> /tmp/librefolio-r2-j-onboarding services settings` -> 18 pass / 6 fail. I nuovi test
> atomici erano verdi; i sei rossi esistenti esponevano `MissingGreenlet` dopo il
> refactor di `ensure_onboarding_progress`: le righe ORM erano state lette prima del
> commit e restituite expired. DB lane ricreato, nessun server usato. Fix prodotto:
> commit dell'insert idempotente, poi refetch async delle righe prima di restituirle.
>
> **⚠️ Fuori pista 2026-09-10**: primo `front-utility core-unit` Step 8 ->
> 2.012 pass / 1 fail. Il nuovo test generation/account ha mostrato che una
> `completeWelcome` stale ignorava correttamente il payload ma lasciava
> `transitioningFlow='welcome'` se il resetter account non era ancora intervenuto.
> Fix prodotto: il `finally` azzera busy soltanto quando il ticket resta l'ultima
> sequenza, indipendentemente dall'identita; una richiesta piu nuova conserva il proprio
> stato, una risposta stale non puo applicare dati.

### Step 9 - Tour introduttivo, shell e popup priority

**Stato:** completato il 2026-09-11.

Creare controller/host del tour, anchor route/nav reali, navigazione controllata senza
scritture, pin Header e apertura drawer mobile. Priorita:
auth/session critical > nested/user modal > guida > DonationPopup > UpdateAvailable.
Integrare route Tool realmente consegnata, senza alterarne contratti.

> **Note implementazione**: controller guida iniettabile con step intro namespaced,
> resume/pause/finish/skip, returnTo safe e precedenza intro su import. OverlayHost
> naviga sui route reali, apre il drawer per anchor nav, osserva profondita ModalBase e
> sospende sulle modali utente. Header espone pin `guideActive`; Sidebar registra anchor
> semantici mantenendo `/tools`/`nav-tools`; il bottone import Transazioni e ancorato.
> `DeferredAppPopups` arbitra guida > modali gia aperte > donation > update senza
> feedback loop sul lock del popup stesso. Gate combinato Step 9-11:
> `onboarding-component-unit` 7 file / 161 test verdi; core tour incluso nel gate
> `core-unit` 82 file / 2.039 test.

> **⚠️ Fuori pista 2026-09-10**: primo
> `... front-utility onboarding-component-unit` Step 9 -> 31 pass, suite coachmark non
> raccolta: Vitest non ha alias `$app/stores`, importato dal nuovo OverlayHost. Nessun
> prodotto/test eseguito oltre il mount. Fix architetturale: OverlayHost non legge
> routing globale; riceve `currentPath` dal layout owner, rendendo dipendenza e test
> espliciti. Repair test delegato a `test-author`.

### Step 10 - Replay per-flow in Settings

**Stato:** completato il 2026-09-11.

Mostrare status/version/update-available e azioni Replay per welcome, intro tour e
import guide, piu Replay all. Replay resta session-scoped, account-scoped e non
distruttivo: nessuna mutazione backend finche l'utente non completa o salta
esplicitamente.

> **Note implementazione**: nuova sezione Preferences con categoria Onboarding,
> status/version/current-version/update disponibile, replay per flow e Replay all.
> Welcome apre la route dedicata; intro avvia il controller; import arma la prossima
> apertura wizard. Replay all salva tre token e rollbacka quelli gia creati su errore.
> Nessuna chiamata complete/skip avviene all'avvio del replay. Spec dedicata e placement
> Preferences inclusi nell'action stretta coordinator-owned.

### Step 11 - Guida ImportWizard e handoff Bulk

**Stato:** completato il 2026-09-11.

Seguire gli step semantici reali
`upload|select|analyze|assets?|fix?|duplicates?|review`, sospendere sulle nested modal,
seguire il ritorno a duplicates e riallinearsi a upload/current step dopo close/refresh.
Alla consegna draft, evidenziare Save All senza clic; completare la guida solo con
Finish esplicito. Nessun ripristino draft, file demo o write finanziario automatico.

> **Note implementazione**: ImportWizard sincronizza la guida su
> `import.<currentStepId>`, quindi segue automaticamente step opzionali e ritorno a
> duplicates. Chiusura/discard pausa e riallinea a `import.upload`; handoff riuscito
> passa a `import.bulk` senza pausa. Bulk espone solo l'anchor sul bottone Save All e,
> se chiuso prima di Finish, pausa/resetta la guida. Overlay consente profondita 2 nel
> wizard, 1 nella Bulk e sospende le nested modal successive. Solo il bottone Finish
> del coachmark marca il flow completato; non invoca import, validate o commit.
> Unit/component verdi; handoff reale upload->parse->Bulk e prova rete no-auto-commit
> restano nello Step 12 E2E.
>
> **Note review 2026-09-11**: review indipendente del delta condiviso ha trovato due
> difetti, entrambi corretti prima dei gate finali: l'effect close-guide Bulk era
> annidato nell'effect promote-suggest e veniva distrutto proprio su `open=false`;
> e il redirect del layout poteva competere con il post-complete della welcome.
> L'effect Bulk e ora top-level; il layout non decide mai l'uscita dalla route welcome,
> che resta proprietaria dell'handoff intro/returnTo.

### Step 12 - Test, docs e handoff coordinator-owned

**Stato:** completato il 2026-09-11.

Usare `test-author` per ogni test nuovo/riparato e `docs-writer` per guide EN. Inviare
al coordinator delta esatti per:

- API sync/client generato;
- cataloghi i18n EN/IT/FR/ES;
- registrazioni runner eventualmente nuove;
- MkDocs nav;
- CHANGELOG e record Release 2.

> **Note implementazione**: test-author ha esteso spec registrate, senza nuova action
> E2E: auth nuovo/existing/atomic complete/skip/account switch; Settings status/replay;
> import reale upload->select->analyze->review->Bulk, nested modal suspension, anchor
> Save All e zero request commit prima/dopo Finish. Fixture canoniche E2E sono marcate
> completed/v1 dal seeder; utenti unici restano senza righe fino a ensure pending.
> Gate: auth 21/21, settings 45/45, tx-import-flow 9/9, header-scroll desktop+mobile
> 4/4, DB referential 15/15. Coordinator ha completato API sync canonico e 69 chiavi
> EN/IT/FR/ES; audit 2.806/2.806 per locale. Runner action stretta 7 spec / 161 test e
> check-orphans verdi.
>
> docs-writer ha aggiornato 7 pagine EN: Getting Started, Import how-to, Preferences,
> Profile, developer Import Wizard, Settings e Auth. MkDocs strict build e check-links
> verdi; nessun cambio nav necessario. Translation-validate registra debito reale sulle
> quattro pagine user, non stampato e non tradotto da J.
>
> Seam dichiarati: il CSV E2E race-free non produce `assets|fix|duplicates`, coperti da
> unit/component e inclusi nel runbook manuale; popup priority non e attivabile via
> debug nel build E2E production, coperta dal componente reale `DeferredAppPopups` e
> inclusa nel runbook.

> **⚠️ Fuori pista 2026-09-11**: primo `db referential-integrity` dopo il seed
> onboarding -> 14 pass / 1 fail, con `populate_mock_data` fermo prima del populate:
> `OnboardingFlow`/`OnboardingStatus`/`UserOnboardingProgress` erano esportati da
> `db.base` ma non dal barrel `backend.app.db` usato dal seeder. Nessun dato canonico
> e stato popolato; il test non ha raggiunto la nuova assertion. Fix additivo agli
> export del package, senza cambiare il modello.
>
> **⚠️ Fuori pista 2026-09-11**: core-unit finale Step 12 -> 2.036 pass / 4 fail.
> Tutti i rossi erano expectation test rimaste sui precedenti fallback inglesi dopo la
> conversione intenzionale del controller a chiavi i18n (`complete`, `skip`,
> `progressUnavailable`). Nessun errore di stato/API; test-author ha riallineato solo
> le quattro stringhe attese, preservando le assertion su active guide, replay e
> assenza di risultato success-shaped.
>
> **⚠️ Fuori pista 2026-09-11**: primo `front-utility header-scroll` integrato ->
> 0/4, tutti fermi prima della pagina Settings. La fixture synthetic strict rispondeva
> 501 al nuovo `GET /settings/onboarding`; `appBootstrap` ha correttamente mostrato lo
> stato blocked. Nessun difetto Header/layout. Test-author ha aggiunto risposta
> onboarding terminale sintetica per i tre flow, mantenendo il controllo
> `unexpectedRequests`.
>
> **⚠️ Fuori pista 2026-09-11**: autoreview controller ha trovato che Pause intro
> lasciava correttamente il token ma il reactive layout richiamava subito
> `maybeStartIntro`, che riprendeva quel token nello stesso runtime. La guard
> `introAttempted` ora precede il resume: Pause dura per la sessione; refresh o cambio
> account ricreano/resettono il controller e possono riprendere il token.

### Step 13 - Gate integrati e review manuale

**Stato:** completato il 2026-09-14 — gate automatici chiusi il 2026-09-11, review developer superata con OK verbatim del 2026-09-14: *«ok chat, ho visionato un pò tutto e non ho visto problemi! mi piace!»*. Riga chiusa a posteriori nel Round 7 Step 1: il lavoro era finito e integrato in `dev_release2`, ma nessuno era tornato a chiudere il marcatore.

Eseguire una suite alla volta nella lane J, static checks e review indipendente.
Preparare runbook desktop/mobile per:

- account nuovo vs existing/grandfathered;
- welcome complete/skip/error/refresh;
- tour complete/skip/pause/replay;
- popup priority;
- drawer/header/focus/reduced-motion;
- import con e senza step condizionali, nested modal e duplicate bounce;
- handoff Bulk e prova di nessun auto-commit;
- cambio account e deep-link.

Consegnare checkpoint FROZEN ma tenere sessione aperta: la chiusura richiede review
operativa developer e relativo giro di correzione.

> **Note implementazione**: matrice automatica finale sulla baseline integrata:
>
> - backend services settings 24/24;
> - API settings/onboarding 37/37;
> - DB referential/seeding 15/15;
> - frontend core-unit 82 file / 2.042 test;
> - onboarding-component-unit 7 file / 161 test;
> - auth onboarding desktop 22/22;
> - Settings replay desktop 45/45;
> - Import Wizard reale desktop 10/10, incluso nested modal, handoff Bulk, close-reset
>   e zero `/transactions/commit`;
> - Header scroll desktop/mobile 4/4;
> - frontend format check verde, svelte-check 0 errori / 41 warning legacy in due file;
> - i18n audit 2.806/2.806 per locale, 0 missing/backend keys;
> - check-orphans: 205 backend, 78 E2E, 203 unit frontend registrati e raggiungibili;
> - MkDocs strict build e check-links verdi via docs-writer;
> - review finale indipendente: nessun rilievo dopo due fix (effect Bulk top-level,
>   ownership redirect welcome).
>
> **⚠️ Fuori pista 2026-09-11**: primo import E2E integrato -> 8 pass / 1 timeout.
> Il G1 copiava due pressioni Escape dal corridoio senza guida; Escape e il gesto
> approvato Pause, quindi la guida spariva correttamente prima di analyze. Test-author
> ha rimosso solo gli Escape dal G1; rerun 9/9, poi regressione G2 aggiunta e suite
> finale 10/10.

### Runbook review operativa desktop/mobile

Avvio, senza `--force`:

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py server --test \
  --port 6158 \
  --data-dir /tmp/librefolio-r2-j-onboarding
```

#### A. Welcome nuovo account

1. Da desktop, registrare un utente univoco e fare login.
2. Atteso: route `/welcome`; presenti `welcome-shell` e `welcome-page`; assenti Header,
   Sidebar, Donation e Update.
3. Verificare lingua/valuta iniziali contro i default admin reali. Il tema corrente non
   cambia.
4. Selezionare avatar oppure lasciarlo vuoto. Completare.
5. Atteso: una singola chiamata atomic welcome; nessun salvataggio finanziario; arrivo
   in Transazioni con tour introduttivo attivo.
6. Ripetere con un secondo account usando Skip permanente. Refresh e nuovo login non
   devono riproporre welcome.

#### B. Tour introduttivo

1. Verificare sequenza:
   Transazioni/Import -> Broker -> Asset -> Dashboard -> Tool -> Settings.
2. Desktop: Header resta visibile durante scroll down; Back/Next cambiano step e route.
3. Mobile: il drawer si apre per gli anchor nav, non copre il coachmark, safe-area
   rispettata.
4. Escape/Pause: il tour sparisce e non riparte nello stesso runtime.
5. Refresh: il token sessione riprende lo step semantico valido.
6. Skip permanente: logout/login non riapre il tour.
7. Finish: termina esplicitamente e applica il returnTo interno, se presente.

#### C. Replay Settings

1. Aprire Settings -> Preferences -> categoria Onboarding.
2. Verificare tre righe con status, versione vista/corrente e update badge quando
   applicabile.
3. Replay Welcome: apre welcome senza mutare prima lo stato backend.
4. Replay Tour: parte dalla prima tappa.
5. Replay Import: mostra "pronto per il prossimo import" e non naviga.
6. Replay all: apre welcome, poi tour; import resta armato per il prossimo wizard.
7. Abbandonare un replay: lo stato terminale precedente resta invariato.

#### D. Guida import

1. Aprire Transazioni -> Import -> wizard con un report reale.
2. Verificare `upload`, `select`, `analyze`, poi solo gli step condizionali realmente
   richiesti (`assets`, `fix`, `duplicates`) e infine `review`.
3. Aprire Parse Detail o AssetModal: coachmark sospeso; chiudere: riprende sullo stesso
   step.
4. Provocare una recheck duplicate che ritorna a `duplicates`: la guida deve seguirla,
   non avanzare per indice.
5. Premere Import to Editor: Bulk resta aperta, coachmark punta Save All.
6. Non premere Save All. Premere Finish guide: coachmark sparisce, draft Bulk restano,
   nessuna request `/transactions/commit`.
7. Ripetere chiudendo Bulk prima di Finish: guida pausa; riaprendo Import riparte da
   `upload`; nessun draft viene ricostruito dal tour.

#### E. Popup, errori e account boundary

1. Con guida attiva, armare Donation e Update tramite hook debug solo se disponibili
   nella build; altrimenti usare la cadenza reale senza modificarla.
2. Atteso: nessun popup sopra la guida; dopo fine/skip, Donation precede Update.
3. Con una modale utente/nested aperta, popup differiti e guida sospesa.
4. Bloccare temporaneamente `GET /settings/onboarding`: utente senza stato terminale
   cached vede Retry/Logout; utente terminale stesso account vede shell + banner retry.
5. Durante una request, fare logout/login con account differente. Nessun coachmark,
   replay, avatar, lingua o risultato async del primo account passa al secondo.

#### F. Chiusura lane

1. Registrare feedback desktop e mobile, incluse tastiera, focus e reduced motion.
2. Fermare il server avviato.
3. Verificare:

```bash
lsof -nP -iTCP:6158 -sTCP:LISTEN
```

Output atteso: nessun listener.
