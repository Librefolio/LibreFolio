# Phase 0 - Onboarding Round 8: correzioni dalla review d'uso e prosecuzione concordata

← Previous:
[Onboarding Round 7 — anchor stall](plan-phase00OnboardingRound7-AnchorStall.prompt.md)

Piano gemello, stesso round di review:
[Privacy Round 2 — correzioni dalla review d'uso](../24_privacyGlobal/plan-phase00PrivacyGlobalRound2-PostReview.prompt.md)

Fonti:
[review d'uso 22/09](../09_feedbackJobs/08_review_visiva_20260922.md) (R3, R4, R19) ·
[dossier di review onboarding](onboarding-review-dossier.md) §6

## Confine e autorizzazione

**Baseline:** `f1047f766`, verificata 2026-09-23 10:33, albero pulito.

**Checkpoint:** C2 `64d78e244` (R3, R19) · C4 `5e7ae336e` (OB-8, OB-9, IWR-006, `settings.spec`), committato 2026-09-24.

**Branch:** `e-alfy-onboarding-foundation`.

**Lane copia prod:** porta `6168`, `/tmp/librefolio-r2-j-onboarding-prodcopy`, solo dalla snapshot
`/tmp/librefolio-r2-prod-snapshot`. **Lane suite:** porta `6158`, `/tmp/librefolio-r2-j-onboarding`,
solo `dev.py test …`.

**Coordinator:** `c8328a01-f208-4ade-a352-0486d1f14de2`.

**Autorizzazione developer verbatim, 2026-09-23:** `Plan approved! Exited plan mode.`

**Schema:** la migrazione `003_user_onboarding_progress` non esiste più; il suo contenuto vive in
`004_release_1_2_0_schema`. Questo round **non crea migrazioni**: se un'opzione ne richiedesse,
stop e domanda al coordinator, che aggiorna la 004.

## Premesse corrette prima di scrivere

- **«Il Round 4 resta valido e va cucito»** — il Round 4 è chiuso dal 2026-09-11, e il suo split
  Bulk in quattro flow persistiti è stato **rovesciato dal Round 5** (*«Import/Bulk tornano a un
  flow ciascuno»*, 2026-09-12). Cucirlo reintrodurrebbe una decisione annullata. Il coordinator
  ha registrato l'errore in 08 §10.
- **La prosecuzione concordata** è la sequenza R7 → R8 → R9 confermata dal developer il
  2026-09-21 nel Round 7. Qui si chiamano **OB-8** e **OB-9**, perché R8 e R9 della review sono
  le candele e la frase di I.
- **R3 «z-index»** — la lettura del codice dà un meccanismo diverso (sotto). Il coordinator l'ha
  registrata.

## Inventario

| # | difetto | causa | file |
|---|---|---|---|
| R3 | la modale «nuova versione» compare dopo, o sotto, il changelog | percorso **admin**: `ChangelogModal:242` → `updateAvailable.show()` → `DeferredAppPopups:41` la **rinvia** finché `modalDepth > 0`. Il percorso non-admin (`AskAdminModal` annidata, `:325`) risponde subito. Il rinvio è giusto per i popup non chiesti e sbagliato per un controllo che l'utente ha chiesto | `DeferredAppPopups.svelte` (mio, `8a8e686f0`), `ChangelogModal.svelte`, `updateCheckStore.svelte.ts`, `UpdateAvailableModal.svelte` |
| R4 | nessun «sei aggiornato» | con R2 attiva la versione era `v1.0.1-97-…` → esito `update-available` → nessun toast «aggiornato» era dovuto. E lo stato `'newer'` **non ha resa inline** | `ChangelogModal.svelte` |
| R19 | frase «Importa ha una guida» | `onboarding.tour.steps.transactionsNav.description`, usata da `OnboardingOverlayHost.svelte:74` | cataloghi i18n ×4 |
| OB-8 | il replay vive in `sessionStorage` e non sopravvive a scheda chiusa o cambio dispositivo | `onboarding.svelte.ts:22` | store onboarding, `OnboardingReplaySection.svelte` |
| OB-9 | uscire dalla route a metà guida riparte dallo step 1; 9 flow su 15 senza E2E | `OnboardingOverlayHost.svelte:641`, `ImportWizardModal:178` (`restartAtFirst`) | host, `onboardingRouteSettlement.ts` (co-autore `e38a521f0`) |

**R3/R4 — osservazione che separa rinvio da impilamento.** Con il changelog aperto, dopo il
check: `[data-testid=deferred-app-popups]` con `data-active-popup="none"` e `data-modal-depth="1"`
è il rinvio; `data-active-popup="update"` è una modale montata ma coperta (il changelog vive
**dentro** la `<nav class="fixed z-50 transform … overflow-hidden">` della Sidebar, senza portal).
R2 è riparata (`v1.1.0-228-gf1047f766`): R4 va ri-verificata in quello stato prima di ripararla.
Il caso `update-available` non è più riproducibile dal vivo: si prova con un test di componente.

## Decisioni — default approvati con il piano

| Q | decisione |
|---|---|
| Q2 | esito «nuova versione» di un check **manuale**: la modale compare **subito sopra** il changelog (richiesta marcata nello store, `DeferredAppPopups` salta il rinvio solo per quella, zIndex sopra 50) + riga di stato inline per **ogni** esito |
| Q5 | OB-8: `localStorage` per utente (la chiave `lf_{userId}_…` è già per utente), cancellato a logout e cambio account, con la nota «vale su questo dispositivo». Nessuno schema |
| Q6 | OB-9: uscire dalla route a metà guida riprende dallo step lasciato, non dallo step 1 |

## Passi

Ogni passo aggiorna questo file dopo il completamento: stato con data, `Note implementazione`,
`Fuori pista`, comando ed evidenza.

### Step 1 — Piano durevole — **Stato: ✅ completato il 2026-09-23.**

Questo file, il gemello privacy, cross-link `→ Follow-up` dal Round 7.

> **Note implementazione:** scritti questo piano e il gemello privacy Round 2; `→ Follow-up` in
> testa al Round 7 e nel §5 del Round 1 privacy. Ogni link relativo risolve, 0 rotti.

### Step 2 — R4, ri-verifica — **Stato: ✅ completato il 2026-09-24. R4 non si riproduce.**

Sulla copia prod, versione `v1.1.0-228-gf1047f766`: Sidebar → versione → «Verifica
aggiornamenti». Registrare: toast visibile o no, stato di `deferred-app-popups`. Solo dopo, il fix.

> **Note implementazione:** copia prod dalla snapshot (`004_release_1_2_0_schema`, senza
> marcatore), build frontend fresca, server `--test` su 6168: `app_version`
> **`v1.1.0-230-g176f19707`**, cioè il `HEAD` di questo ramo (R2 è davvero riparata). Sonda
> Playwright usa-e-getta, login `alfy`, Sidebar → `sidebar-version` → `changelog-check-update`,
> attesa **sull'evento** e non sull'orologio. Letto da `window.__lf.events`:
> `app.update.checked` con `status: up-to-date`, `remoteVersion: 1.1.0`, `currentVersion:
> v1.1.0-230-g176f19707`; un `toast-success` visibile. `compareVersions` confronta solo la versione
> base, e `1.1.0` contro `1.1.0` è `up-to-date`.
>
> **R4 era una conseguenza di R2**: con la versione sbagliata l'esito era `update-available`, che
> per costruzione non emette il toast «aggiornato». Nessuna correzione: la riga di stato inline che
> avevo proposto per Q2 serviva a R4, e **non la implemento** senza un difetto da riparare.
>
> **R3 confermato dal DOM**: col changelog aperto, `deferred-app-popups` ha
> `data-active-popup="none"` e `data-modal-depth="1"`. Un esito `update-available` sarebbe quindi
> rinviato alla chiusura del changelog — ciò che il developer ha visto. Non riproducibile dal vivo
> oggi (non c'è una release più nuova): si prova con i test di componente dello step 3.

### Step 3 — R3/R4, fix — **Stato: ✅ completato il 2026-09-24 (solo R3; R4 non si riproduce).** — *C2*

Per Q2: `updateCheckStore` distingue la richiesta manuale; `DeferredAppPopups` continua a
rinviare i popup non chiesti (contratto invariato) e mostra subito quella chiesta;
`UpdateAvailableModal` sopra il changelog; `ChangelogModal` con una riga di stato inline per
`up-to-date`, `no-release`, `image-pending`, `error`, `newer`. Toast e `notify` invariati: sono il
contratto su cui asseriscono i test.

> **Note implementazione:** solo R3; R4 non si riproduce (step 2), quindi niente riga di stato
> inline. `updateCheckStore`: `show(r, {requested})` e getter `requested`, azzerato da `close()` e
> `skipVersion()`. `DeferredAppPopups`: in testa all'effect, una richiesta manuale mostra subito la
> modale — anche con una modale aperta o una guida attiva, perché è la risposta a una domanda appena
> fatta; i popup non chiesti conservano esattamente le regole di prima. `UpdateAvailableModal`:
> `zIndex` 60 quando richiesta, perché il changelog vive nel contesto di impilamento della sidebar a
> 50. `ChangelogModal`: il percorso admin chiama `show(latest, {requested: true})`. Rossi attesi e
> misurati: **2**, in `ChangelogModal.test.ts`, entrambi sull'asserzione `show` chiamata con
> `(RELEASE)` e basta; gli altri 92 test delle superfici toccate restano verdi.
>
> Test via `test-author`, rieseguiti da me: `DeferredAppPopups.test.ts` nuovo, 5 test (popup
> automatico trattenuto con una modale aperta e con una guida attiva; richiesta manuale mostrata
> subito in entrambi i casi; `close()` torna a `none`, azzera `requested`, e un popup automatico
> successivo è di nuovo trattenuto). `UpdateAvailableModal.test.ts` +1 (`z-index` 60 richiesta, 50
> automatica). `ChangelogModal.test.ts`: le due asserzioni ora attendono `(RELEASE, {requested:
> true})`. Controllo negativo: tolto il ramo della richiesta → i 3 test della richiesta rossi, i 2
> automatici verdi; ripristino con sha identico. `onboarding-component-unit` dal runner: 13 file,
> 400 test, exit 0.
>
> Non riproducibile dal vivo finché non esiste una release più nuova della corrente: la prova di R3
> è la combinazione della misura del DOM allo step 2 e di questi test.

### Step 4 — R19 — **Stato: ✅ completato il 2026-09-24.**

`dev.py i18n update onboarding.tour.steps.transactionsNav.description` nelle quattro lingue:
cade solo la seconda frase. La chiave resta (nessuna chiave si dichiara morta prima della fine
del round).

> **Note implementazione:** eseguito, exit 0. Diff dei cataloghi: **una riga per lingua**, 4+/4−,
> nessun riordino né riformattazione. Nessun test o E2E cita la frase o la chiave: la usa solo
> `OnboardingOverlayHost.svelte:74`. Nessun test automatico nuovo, per la regola sul testo
> tradotto: la verifica è la review manuale.

### Step 5 — OB-8 — **Stato: ✅ completato il 2026-09-24** — *C4*

Replay in `localStorage` per Q5, cancellato da `registerClientSessionReset` a logout e cambio
account; il bump di versione continua a invalidarlo; nota in `OnboardingReplaySection`.

> **Note implementazione — codice.** In `stores/app/onboarding.svelte.ts`:
>
> - dipendenza rinominata `getSessionStorage` → `getReplayStorage`, default `window.localStorage`
>   (dentro `try`: un browser che nega lo storage dà `null`, non un'eccezione); il messaggio
>   d'errore diventa `Browser storage is unavailable`;
> - chiave invariata `lf_{userId}_onboarding_replay_{flow}_v{version}`, quindi per account e per
>   versione come prima; il bump di versione la invalida alla prima lettura o scrittura
>   (`removeReplayVersions`, invariato);
> - `clearAccountReplays(userId)` e il resetter di sessione `createOnboardingSessionResetter`: su
>   ogni transizione da un account (logout, sessione scaduta, cambio account) cancella le chiavi
>   dell'account precedente, poi azzera lo stato in memoria;
> - `handleExternalReplayChange` più il listener `storage` (`createReplayStorageListener`): se
>   un'altra scheda cancella la chiave della replay attiva, questa scheda lascia cadere la copia in
>   memoria e non può più riscriverla. Senza, la replay finita in una scheda poteva **tornare in
>   vita** al primo passo fatto nell'altra: è una conseguenza nuova di `localStorage`, che
>   `sessionStorage` non aveva.
>
> **⚠️ Fuori pista — trovato dal `test-author`, riprodotto su copia.** Lasciar cadere solo la copia
> in memoria bloccava la guida **automatica** nell'altra scheda: `ownsActivation`
> (`onboardingGuide.svelte.ts`) esige che `controller.replay` coincida con lo step attivo, quindi
> dopo la cancellazione `finish()` e `skip()` scrivevano sul server e poi **non chiudevano** lo
> step. Innesco realistico: due schede sulla stessa pagina con la stessa guida pendente, che ora
> condividono una chiave; oppure un logout in un'altra scheda. Peggio: premere *Esci* in quella
> scheda portava un flow già `completed` a `skipped`. **Decisione presa (da confermare dal
> developer):** quando un'altra scheda cancella la chiave, **questa scheda chiude il suo step**.
> Il listener vive ora nel modulo della guida (`onDropped` → `dismissHost()`), ed è **uno solo**:
> con due listener il primo lascerebbe cadere la replay e il secondo non chiuderebbe niente.
>
> **Note implementazione — test unitari** (via `test-author`, vitest locale, nessuna lane):
>
> | cosa | esito |
> |---|---|
> | `onboarding.test.ts` + `OnboardingReplaySection.test.ts`, prima del ritocco dei test | `Test Files 1 failed \| 1 passed (2)`, `56 failed \| 79 passed (135)`: tutti per l'iniezione `getSessionStorage`, ora ignorata. È il controllo positivo che il rinomino è effettivo |
> | dopo | **`Test Files 2 passed (2)`, `169 passed (169)`** (+34 test: persistenza fra runtime, bump di versione, `clearAccountReplays` col confine `lf_1_`/`lf_12_`, resetter su logout/cambio account/prima identità, rimozione da un'altra scheda con valore di ritorno, listener con `onDropped`, chiusura della guida automatica e di quella in replay, Finish in volo che si risolve o fallisce dopo la rimozione, e OB-9 al livello della guida: ripresa al 3° step dopo `dismissHost()`, ritorno al 1° con `restartAtFirst`) |
> | controlli negativi, solo su copie | `handleExternalReplayChange` no-op → 3 rossi; `onDropped` mai chiamato → 5; sempre chiamato → 5; filtro `storageArea` tolto → 2; esito sempre `false` → 7; host con `restartAtFirst` → solo il test di ripresa rosso. sha256 dei file di produzione identici prima e dopo |
> | `prettier --check`, `svelte-check` sulle due spec | puliti; nel progetto restano i 3 errori noti, in file non miei |
>
> **⚠️ Fuori pista — un mock che non vedeva la nuova esportazione.** `OnboardingReplaySection.test.ts`
> sostituisce il modulo `onboarding.svelte` e carica il modulo vero della guida, che ora chiama
> `createReplayStorageListener` all'import: il file moriva prima di eseguire i suoi 16 test, e il
> riepilogo mostrava `1 failed` accanto a `Tests 145 passed` — un rosso facile da leggere come
> verde. Una riga nel mock. `svelte-check` non poteva vederlo: fallisce solo a runtime.
>
> **i18n** (`dev.py i18n update`, 2 chiavi × 4 lingue, solo il valore): `armedAtNextTrigger` e
> `armedToast` dicevano «in questa scheda … chiudendo la scheda si annulla», promessa vera con
> `sessionStorage` e falsa ora. Diventano «in questo browser … uscendo dall'account si annulla».
>
> **⚠️ Fuori pista — scelta di parola, da confermare dal developer.** Q5 diceva «vale su questo
> dispositivo». Ho scritto **browser**: `localStorage` vale per il profilo del browser, e un secondo
> browser sullo stesso dispositivo non vede la replay. È lo stesso criterio del Round 7 (D7):
> dire all'utente il confine vero, che sa riconoscere. Se il developer preferisce «dispositivo», è
> un `dev.py i18n update` per chiave.
>
> **Conseguenze dichiarate.** (1) «Uscire» comprende anche la sessione scaduta: `checkAuth` fallito
> porta a `transitionClientSession(null)`, come il logout; coerente con il testo, ma una replay
> armata non sopravvive a una scadenza, mentre con `sessionStorage` sopravviveva nella stessa
> scheda. (2) Se il browser si chiude senza logout ed entra un altro account, la prima identità
> non viene vista come transizione: le chiavi del primo account restano, sotto il suo id, finché
> quell'account non rientra ed esce. Non sono visibili ad altri account.

### Step 5b — IWR-006, rosso preesistente di K — **Stato: ✅ completato il 2026-09-24**

Assegnato dal coordinator (12:16): `tx-import-resolution` IWR-006 fallisce sempre, il coachmark
`import.review` intercetta il click sull'opzione.

> **Note implementazione — la misura, prima del fix.** Ipotesi a confronto: H1 riga di versione
> vecchia nel DB di una lane; H3 guida armata per un utente terminale. Il runner rifà il populate
> a ogni lancio di questa categoria, quindi H1 cade per costruzione. Lettura del DB della mia lane
> dopo il run rosso (6158, populate fresco): `TEST_USER` aveva il flow `import_guide` **pending**,
> gli step Import 2 `completed`, 5 `pending`, 1 `skipped`, e gli step Bulk 4 `pending`; il populate
> aveva seminato 165 righe di flow e **0** di step.
>
> **Causa.** `_grandfather_onboarding_for_test_users` (mia, `8a8e686f0`) semina solo le righe dei
> flow: le righe di step sono arrivate col Round 5 e non l'ho estesa. Al primo
> `GET /settings/onboarding` il backend crea gli step mancanti come `pending`; le guide Import e
> Bulk sono guidate dagli step, non dal flow, e partono per un utente che il flow dà `completed`.
> Le spec che condividono `TEST_USER` completavano e saltavano i suoi step senza saperlo, e
> l'aggregato riportava il flow a `pending`: esito dipendente dall'ordine dei test. Il pattern
> di `tx-import-flow` (`installTerminalOnboardingProgress`, risposta terminale finta) aggirava
> proprio questo.
>
> **Fix alla radice** in `populate_mock_data.py` (+38/−4, solo quella funzione e un import):
> semina e ripara anche le righe di step, `completed` alla versione corrente. La spec non si tocca.
>
> | comando (lane 6158) | esito |
> |---|---|
> | `dev.py test … front-transaction tx-import-resolution`, prima | exit 1 · `1 failed`, `11 passed (2.1m)`; IWR-006 in timeout, `onboarding-coachmark-panel … data-step-id="import.review" … intercepts pointer events` |
> | idem, dopo | exit 0 · **`12 passed (42.0s)`**; populate: `165 row(s) inserted …; 132 step row(s) inserted` |
> | DB dopo il run | flow `import_guide` e `transaction_bulk_guide` `completed`; step 8 + 4 tutti `completed` |
> | `ruff check`, `black --check` sul file | puliti (black ha solo riunito la mia `print`) |
> | `dev.py test … db referential-integrity` (test via `test-author`, +132/−6) | **`17 passed`** (prima 15): step seminati `completed` alla versione corrente, idempotenza degli step, riparazione di uno step `pending` e di uno `skipped` in un passaggio, con ripristino in `finally`; utente nuovo con step `pending` dopo l'ensure |
> | controllo negativo (solo copia del file di test) | `4 failed, 13 passed`, tre asserzioni rovesciate più la chiamata di riparazione tolta; file ripristinato, sha256 identico |

### Step 6 — OB-9 — **Stato: ✅ completato il 2026-09-24** — *C4*

Ripresa dallo step lasciato per Q6. E2E dei 9 flow mai provati (modale e dettaglio Broker, FX,
Asset), desktop e mobile, lane 6158, via `test-author`.

> **Note implementazione — codice.** Una riga: `OnboardingOverlayHost.svelte`, sul disallineamento
> di rotta, `dismissHost()` invece di `dismissHost({restartAtFirst: true})`. La posizione salvata
> resta, e la pagina che al ritorno chiama `maybeStartContextual` riprende da lì (lo fa già via
> `resumeReplay`). La chiusura **delle modali** resta com'era: `restartAtFirst` a
> `TransactionFormModal`, `TransactionBulkModal`, e alle chiusure delle modali di Broker, FX,
> Asset; una modale riaperta ha un form nuovo, e la sua guida riparte dall'inizio.
> `ImportWizardModal:178` (file di K) **non si tocca**: `import_guide` è gestito per step, e lì
> `restartAtFirst` non ha effetto già oggi.
>
> **Note implementazione — E2E T11, OB-9 e OB-8** (via `test-author`, lane 6158). Spec nuova
> `frontend/e2e/onboarding-guides.spec.ts` (+584) con helper nuovi in
> `e2e/fixtures/onboarding-accounts.ts` (+155), registrata in `_frontend_utility.py` (+19,
> `front-utility onboarding-guides`, `project=""`: desktop **e** mobile). 12 test × 2 progetti:
> i 9 flow percorsi step per step su pagine vere (ordine del catalogo, `anchored`, `stable`,
> un solo target descritto e proprio quello dell'àncora, unica scrittura il `complete` del flow,
> nessun `/sync`); OB-9 pagina (3° step), dettaglio (2° step) e contrasto della modale (riparte);
> OB-8 replay in una scheda nuova aperta **dopo** aver chiuso quella che l'ha armata, logout che la
> cancella, chiusura nell'altra scheda senza toccarla. Un marcatore su `window` prova che la
> navigazione di OB-9 è restata lato client: un ricaricamento completo salterebbe il ramo sotto
> prova e passerebbe anche col vecchio codice. Ogni test ha il suo account usa-e-getta.
>
> | comando (lane 6158) | esito |
> |---|---|
> | `front-utility onboarding-guides`, due giri | `24 passed (1.5m)`, `24 passed (1.4m)` — 12 desktop + 12 mobile |
> | idem con `--workers 4` (mio) | exit 0 · `24 passed (46.7s)` |
> | `front-utility onboarding-tour` (regressione) | `10 passed (48.9s)` |
> | `check-orphans` del runner | 81 spec registrate, tutte raggiungibili |
>
> Letto dal `test-author`, non difetti di comportamento: le pagine asset interrogano
> `POST /assets/prices/current`, che chiama provider veri e scrive il prezzo del giorno su asset
> condivisi (la spec risponde con un risultato vuoto, come le altre spec asset); i pulsanti di
> chiusura di `FxPairAddModal` e l'X in testa ad `AssetModal` non hanno `data-testid`.

### Step 6c — `settings.spec` «Runes parity», rosso preesistente — **Stato: ✅ completato il 2026-09-24**

> **Trovato dalla mia regressione, non da C4.** `front-utility settings`: `1 failed | 44 passed`.
> Il test registra un account nuovo e va in `/settings`; un account nuovo ha `welcome` pendente e
> il bootstrap lo rimanda a `/welcome` (istantanea: «Welcome to LibreFolio»): timeout a 45 s. Il
> test è del 2026-09-10 (`74bfd9cf0`), il gating del benvenuto del 2026-09-11 (`8a8e686f0`, mio):
> rosso da allora, a ogni giro. **Fix nella spec** (via `test-author`, +16): dopo il login salta
> via API ogni flow ancora dovuto di quell'account (`skipDueFlowsExcept`, che **salta** il
> benvenuto invece di completarlo: completarlo scriverebbe lingua e valuta, cioè l'oggetto del
> test), poi entra da `/welcome?returnTo=/settings` e aspetta che l'app lo inoltri. Controlli
> negativi: senza il setup torna il timeout su `/welcome`; senza lo skip resta su `/welcome`;
> saltare **solo** il benvenuto non basta, perché l'intro rende inerte la shell.
>
> | comando | esito |
> |---|---|
> | `front-utility settings`, dopo | exit 0 · **`45 passed (1.1m)`** |
>
> **⚠️ Reperto, non corretto — possibile difetto di prodotto.** Con il benvenuto pendente, aprendo
> `/settings` direttamente la **shell completa** si vede per un attimo, poi l'app va a `/welcome`
> (controllo negativo B del `test-author`). Lettura statica: `(app)/+layout.svelte` è in modalità
> legacy (zero rune) e calcola `onboardingRouteReady` con istruzioni `$:` che leggono
> `appBootstrap.ready`, uno stato runes dentro un modulo: la stessa famiglia di R20. Quando
> `ready` diventa vero il template esce dal caricamento, ma `onboardingRouteReady` resta al valore
> vecchio, quindi il segnaposto `onboarding-redirecting` non compare e la pagina richiesta si
> disegna finché il redirect asincrono non arriva. Con una replay del benvenuto armata, la pagina
> lampeggiata è quella con i dati dell'utente. Da misurare dal vivo e da decidere: il file è il
> layout condiviso dell'app.

### Step 6d — Lampo della shell col benvenuto pendente — **Stato: ✅ completato il 2026-09-24**

Assegnato dal coordinator (14:25) dopo C4: misurarlo dal vivo sulla copia rinfrescata, e avvisare
prima di toccare `(app)/+layout.svelte`, che è condiviso.

> **Note implementazione — la misura.** Copia rinfrescata dalla snapshot (`004_release_1_2_0_schema`),
> server `--test` su 6168, sonda Playwright usa-e-getta (`requestAnimationFrame`: a ogni frame
> registra quali segnaposto e shell sono montati e visibili, il percorso, e **quanti** importi
> compaiono nel testo, mai quali). Credenziali solo da variabili d'ambiente; nessun importo scritto.
>
> | scenario (5 + 3 ripetizioni) | pagina richiesta → finale | frame `onboarding-redirecting` | **lampo**: frame con la shell della pagina richiesta | importi visibili nel lampo |
> |---|---|---|---|---|
> | A · account nuovo, benvenuto pendente | `/settings` → `/welcome` | **0** | 2–3 frame, 3–4 ms | 0 |
> | B · idem | `/dashboard` → `/welcome` | **0** | 3–5 frame, 18–36 ms | 0, **tranne 1 giro su 8: 9** (gli zeri di un portafoglio vuoto) |
> | C · proprietario, replay del benvenuto armata | `/dashboard` → `/welcome` | **0** | 2–3 frame, 11–16 ms | 0 (8 giri) |
> | D · idem | `/brokers` → `/welcome` | **0** | 1–2 frame, 0–1 ms | 0 (8 giri) |
> | E · controllo: proprietario senza replay | `/dashboard` → `/dashboard` | 0 | **0** | — (shell sulla pagina finale: 250–264 frame) |
>
> **Lettura.** Il segnaposto `onboarding-redirecting` non si monta **mai** (0 frame su 40 giri
> di A–D): il ramo del template è morto per un caricamento diretto, come diceva la lettura
> statica (istruzioni `$:` legacy su `appBootstrap.ready`, stato runes non tracciato). La pagina
> richiesta si disegna per 1–5 frame prima del redirect. Nessun importo del proprietario è
> comparso in 16 giri, ma il giro di B con 9 importi prova che **il contenuto della pagina può
> arrivare dentro la finestra**: con dati in cache o un redirect più lento, gli importi veri
> lampeggerebbero. Account usa-e-getta rimosso (`HTTP 200`); server fermato, 6168 libera.
>
> **Rimedio, approvato dal coordinator (15:1x) nel perimetro proposto; J unico scrittore del layout
> in questo round.** `routes/(app)/+layout.svelte` (+8/−3): `toStore(() => appBootstrap.ready)` e
> `$bootstrapReady` nelle due istruzioni `$:` di `onboardingDestination` e `onboardingRouteReady`.
> Il componente resta legacy.
>
> **Reperti residui, lasciati com'erano per decisione:** il blocco `$: if (… claimReactive …)`
> (rigira quando cambiano le due variabili, ma `claimReactive` è protetto da proprietario attivo e
> firma già gestita) e la lettura di `onboardingGuide.active?.flow` nella stessa `$:`, della stessa
> famiglia, senza difetto misurato.
>
> **Test di regressione, senza tempi** (via `test-author`, poi verificato da me): `src/routes/(app)/layout.gate.test.ts`
> + harness `__tests__/harness/AppLayoutGateHarness.svelte`, registrato in `onboarding-component-unit`
> (+1 riga nel runner). Monta il layout con un `appBootstrap` finto (getter enumerabili sopra `$state`),
> passa `ready` a vero e fa `tick()`: con un redirect dovuto deve comparire `onboarding-redirecting` e **non**
> `app-shell`; il controllo, con la stessa destinazione, mostra la pagina e prova che il gate ha rigirato.
>
> **⚠️ Fuori pista — serviva un file condiviso.** Vite risolve gli import mentre compila, prima di ogni
> `vi.mock`: senza alias nessun test poteva caricare un componente che importa `$app/stores` (13 sorgenti,
> fra cui Sidebar e le pagine). Ok del coordinator (15:26), J unico scrittore nel round: **+1 riga d'alias**
> in `frontend/vitest.config.ts` e il mock nuovo `src/__mocks__/$app/stores.ts`, con un docstring su cosa
> **non** simula (routing e navigazione). La fragilità del finto `appBootstrap` è scritta nel test, dove si
> costruisce. **Verificata compilando il layout:** la condizione di ogni `{#if}` sta dentro `$.untrack(…)`, e
> il template traccia `appBootstrap` **solo** con `$.deep_read_state(appBootstrap)`, un `for…in` sui getter
> enumerabili: se `appBootstrap` diventasse un'istanza di classe (getter sul prototipo, non enumerabili),
> non solo il finto, ma **il layout vero** resterebbe fermo sul caricamento. È un vincolo di produzione, non
> solo del test.
>
> | prova | esito |
> |---|---|
> | le tre categorie unit, prima e dopo l'alias, confronto per nome (multiinsieme, vitest diretto, nessuna lane) | `core-unit` 2513 = 2513; `component-unit` 2010 = 2010 (8 titoli ripetuti, identici prima e dopo); `onboarding-component-unit` 400 → **402**: gli unici nomi nuovi sono i 2 test del gate; 0 persi, 0 cambi di stato |
> | controllo negativo, rifatto da me sui file finali: copia del layout con le due `$:` pre-fix | `2 failed`: *«the requested page shell painted while a redirect is due»*, e il controllo non vede mai `resolveDestination('/dashboard')` |
> | test vero | `2 passed`; sha256 del layout di produzione identico prima e dopo; nessun residuo |
> | `prettier --check` sui file nuovi e toccati | pulito |
>
> **Misura «dopo»**, stessa sonda, copia rinfrescata di nuovo dalla snapshot, build del frontend
> che contiene il rimedio (sorgente modificato alle 15:01, `build/index.html` delle 15:31). Alla
> sonda ho aggiunto un `MutationObserver`: il campionamento per frame vede ciò che viene
> **disegnato**, e un nodo inserito e tolto nello stesso frame gli sfugge; l'osservatore vede ogni
> **montaggio**.
>
> | scenario (5 giri) | lampo: frame della shell sulla pagina richiesta | shell **montata** sulla pagina richiesta | `onboarding-redirecting` montato | … e disegnato |
> |---|---|---|---|---|
> | A · benvenuto pendente, `/settings` | **0** (prima 2–3) | **0/5** | **5/5** (prima 0) | 4/5 |
> | B · idem, `/dashboard` | **0** (prima 3–5) | **0/5** | **5/5** | 4/5 |
> | C · replay del benvenuto armata, `/dashboard` | **0** (prima 2–3) | **0/5** | **5/5** | 1/5 |
> | D · idem, `/brokers` | **0** (prima 1–2) | **0/5** | **5/5** | 3/5 |
> | E · controllo, senza replay | 0 | 0/5 | 0/5 | 0/5 — shell sulla pagina finale 258–265 frame, come prima |
>
> Il segnaposto si monta sempre; quando il redirect arriva nello stesso frame non fa in tempo a
> essere disegnato, ed è il comportamento giusto: nessun frame mostra la pagina richiesta. Account
> usa-e-getta rimosso; server fermato, 6168 libera.
>
> | E2E di regressione del layout (lane 6158) | esito |
> |---|---|
> | `front-utility onboarding-component-unit` (con il test nuovo) | `14 passed`, `402 passed` |
> | `front-utility auth` | `24 passed` |
> | `front-utility onboarding-tour` | `10 passed` |
> | `front-utility onboarding-guides` | `24 passed` |
> | `front-utility settings` | `45 passed` |
> | `front-utility header-scroll` | `4 passed` |
> | `dev.py front check` (client `a085da1c8dac`) | `3 errors and 41 warnings in 4 files`, il pavimento noto |

### Verifica di C4 — lane 6158, 2026-09-24

| comando | esito |
|---|---|
| `front-utility core-unit` | exit 0 · `Test Files 94 passed (94)`, `Tests 2513 passed (2513)` (C3: 2479; +34 di OB-8/OB-9) |
| `front-utility onboarding-component-unit` | exit 0 · `13 passed`, `400 passed` |
| `front-utility component-unit` | exit 0 · `76 passed`, `2010 passed` |
| `front-utility onboarding-guides --workers 4` | exit 0 · `24 passed` |
| `front-utility auth` | exit 0 · `24 passed` |
| `front-utility settings` | exit 0 dopo lo step 6c · `45 passed` |
| `front-utility header-scroll` | exit 0 · `4 passed` |
| `front-transaction tx-import-flow` | exit 0 · `10 passed` |
| `front-transaction tx-import-resolution` | exit 0 · `12 passed` (step 5b) |
| `db referential-integrity` | exit 0 · `17 passed` (step 5b) |
| `dev.py front check` (client `generated.ts` `a085da1c8dac`) | `3 errors and 41 warnings in 4 files` = il pavimento noto, nessuno nel delta |
| `prettier --check` sui file frontend di C4 | pulito (prettier ha solo spezzato la mia riga del listener) |
| `git diff --check` | pulito |

Non eseguiti: la suite unitaria intera per categoria diversa da quelle sopra; `chartCoreHelpers.test.ts`
dà `12 failed | 150 passed` sui test che rispecchiano il sorgente di `GrowthChart.svelte` (file di I;
questo ramo non tocca `charts/`).

### Step 6b — Documentazione OB-8/OB-9 — **Stato: ✅ completato il 2026-09-24** — *via `docs-writer`*

> **Note implementazione.** Utente (`.en.md`): `user/settings/preferences.en.md` (ambito della
> replay: questo browser e questo account, sopravvive a schede e riavvii, annullata da logout,
> anche per sessione scaduta mentre l'app è aperta, e da cambio account, chiusa nelle altre schede
> quando finisce; OB-9: uscire da una pagina riprende allo stesso step, chiudere un form Aggiungi
> lo fa ripartire) e `user/transactions/import/how-to.en.md` (una frase). Sviluppatore (`.md`, solo
> inglese): `developer/frontend/components/features/{settings,import-wizard,auth}.md`, +61/−42:
> `localStorage`, ciclo di vita della chiave, listener fra schede, OB-9 esatto.
>
> | comando | esito |
> |---|---|
> | `dev.py mkdocs build` (strict) | exit 0, nessun WARNING/ERROR |
> | `dev.py mkdocs check-links` | exit 0, `80 valid link(s)` |
> | `dev.py mkdocs translate-validate` sulle due pagine utente | exit 1, **stesso debito di prima** (15 errori, 9 avvisi): le versioni it/fr/es **non hanno affatto** le sezioni onboarding. Niente da correggere frase per frase: servono le sezioni intere, su richiesta del developer (pipeline Aphra). Nessun `translate-stamp` |
>
> **⚠️ Fuori pista — due correzioni oltre il mandato, entrambe legate.** (1) Il mio brief chiedeva
> solo `.en.md`, ma le pagine sviluppatore sono `.md` e dicevano ancora `sessionStorage`: corrette
> in un secondo giro. (2) Le stesse frasi descrivevano pulsanti che non esistono più
> dall'`8a8e686f0` («Skip permanently», «Exit replay», X che chiama `suspend()`): oggi c'è solo
> **X**, che chiama `exit()` = `skip()`. La frase su OB-9 non poteva essere vera senza correggerle,
> quindi il `docs-writer` le ha corrette **solo** nei paragrafi toccati.
>
> **Errori più vecchi, lasciati e passati al coordinator:** `settings.md` dice 3 flow (sono 15),
> descrive la replay solo per quei 3 e un avvio automatico dell'intro di 10 s (sono 8,
> `OnboardingIntroScene.svelte:18`); `auth.md` cita step dell'intro che non esistono in
> `CORE_TOUR_STEP_IDS`; `import-wizard.md` dice «uno dei tre flow», che `setStep` gira a ogni
> cambio di step, e che la guida chiama l'endpoint di flow (chiama quelli per step).

### Step 7 — Review manuale e FROZEN — **Stato: ⏳**

## Previsione conflitti

| file | owner | nota |
|---|---|---|
| `DeferredAppPopups.svelte` | J | nessun conflitto |
| `ChangelogModal`, `UpdateAvailableModal`, `updateCheckStore` | nessun owner attivo | ultimo tocco 2026-09-09 |
| cataloghi i18n | condivisi | un valore, via `dev.py`, elencato nell'handoff |
| `ImportWizardModal`, `TransactionBulkModal` | K | vincolo girato dal coordinator: 7 ancore `import.action.*` (`:4586–4770`), 5 del Bulk, step-sync `:164–178` e `:1279`. Secondo K, R18 si ripara in `AssetModal`; rieseguire l'E2E onboarding dopo il merge di K |
| `onboardingRouteSettlement.ts` | co-autore `e38a521f0` | toccato solo se OB-9 lo richiede — **non richiesto**: OB-9 è una riga dell'host |
| `backend/test_scripts/test_db/populate_mock_data.py` | condiviso | solo `_grandfather_onboarding_for_test_users` (mia) e un import: semina degli step (IWR-006). Effetto su **tutte** le lane dopo l'integrazione: `TEST_USER` davvero terminale, niente coachmark Import/Bulk nelle spec che non parlano di onboarding |
| `frontend/e2e/settings.spec.ts` | condiviso | solo il commento del blocco replay (`sessionStorage` → `localStorage`), via `test-author` |
| cataloghi i18n, OB-8 | condivisi | 2 valori (`onboarding.settings.armedAtNextTrigger`, `armedToast`) × 4 lingue, via `dev.py`, nessuna chiave nuova né rimossa |
| `features/tools/ToolsHub.svelte` | **D** (assegnato dal coordinator, 2026-09-24) | contiene l'àncora `use:guideAnchor={'tools.hub'}` a `:146`, fissata da `ToolsHub.test.ts:99`: D la preserva. Misurato: **nessuna guida la consuma** (controllo positivo: `nav.tools` consumata a `OnboardingOverlayHost.svelte:109`). Candidata naturale per una guida Strumenti quando esisterà la UI del PAC v2 |

## Test list — approvata con il piano

| # | livello | asserzione |
|---|---|---|
| T8 | componente | `DeferredAppPopups`: i popup automatici restano rinviati con `modalDepth > 0`; la richiesta manuale si mostra subito |
| T9 | componente | `ChangelogModal`: stato inline per ogni esito; percorso non-admin invariato |
| T10 | componente | OB-8: il replay sopravvive a una nuova scheda; cancellato a logout e cambio account; il bump di versione lo invalida |
| T11 | E2E | OB-9: 9 flow, desktop e mobile |

R19 non ha test automatico: niente asserzioni su testo tradotto. Review manuale.

## Runbook review manuale — copia prod `6168`

| dove | cosa | difetto se |
|---|---|---|
| Sidebar → versione → «Verifica aggiornamenti» | stato inline e toast | nessun riscontro visibile |
| tour intro, passo Transazioni | testo | cita ancora la guida di import |
| guida qualunque, cambio di pagina a metà e ritorno | step | riparte dallo step 1 |
| replay da Impostazioni, poi scheda nuova | guida | il replay è perso |
| replay armata, poi logout e nuovo login | Impostazioni | la replay è ancora armata |
| due schede sulla stessa pagina con la stessa guida; Fine in una | l'altra scheda | il coachmark resta aperto |
| Aggiungi Broker a metà guida, chiudi, riapri | guida della modale | riprende dallo step lasciato invece di ripartire |
| Impostazioni → replay: testo «in questo browser … uscendo dall'account si annulla» (4 lingue) | testo | dice ancora «scheda» |

## Definition of done

- Check manuale: riscontro visibile per ogni esito; «nuova versione» subito sopra il changelog;
  popup non chiesti ancora rinviati.
- R19: frase tolta in quattro lingue, chiave conservata.
- OB-8 e OB-9 per Q5 e Q6; E2E dei 9 flow verde desktop e mobile.
- Nessuna migrazione, nessuna chiave rimossa, porte 6158/6168 provate libere al FROZEN.

## CHANGELOG proposto — lo scrive il coordinator

- 🐛 Aggiornamenti: il controllo manuale mostra sempre l'esito, e la nuova versione compare subito.
- 🐛 Onboarding: rimosso dal tour un rimando superfluo alla guida di importazione.
- ✨ Onboarding: le guide ricordano a che punto sei in questo browser, anche chiudendo la scheda o
  riavviando; uscendo da una pagina a metà guida, al ritorno riprende dallo stesso passo. Una guida
  finita in una scheda si chiude anche nelle altre; uscire dall'account annulla le replay armate.
