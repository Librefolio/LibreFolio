# Phase 0 - Onboarding Round 1: UX refinement

## Origine e baseline

**Piano padre:** [plan-phase00Onboarding.prompt.md](plan-phase00Onboarding.prompt.md).

**Baseline Git:** `4a9ae876e4599b5fdec5ade512b65b9c31a584a5`, più il delta
shared-onboarding già verificato e ancora non committato nello stesso worktree.

**Feedback developer:** review del primo tour, 2026-09-11.

## Obiettivo

Rifinire insieme Welcome, tour introduttivo e guida Import con una sola grammatica UX:

- lingua sempre reattiva;
- scena narrativa prima del tour;
- Dashboard come punto di partenza;
- insegnamento esplicito di burger/sidebar;
- tappe reali e non-writing su Transazioni, Broker, FX, Asset, Tool e Settings;
- controlli Skip/X/Back/Next coerenti;
- nessuna Pausa, demo data o scrittura automatica.

La review manuale complessiva è rinviata al prossimo sprint. Questo round termina con
gate automatici, server spento e checkpoint FROZEN.

## Decisioni approvate

- Rimuovere Pausa.
- X sospende e conserva replay; ripresa al prossimo refresh/login.
- Skip permanente in alto con icona uscita.
- Back in basso a sinistra con freccia; Next/Finish in basso a destra.
- Scena introduttiva con frasi automatiche + Start; auto-start one-shot dopo 10 s.
- Tool e Settings restano tappe finali.
- Modali Broker/FX/Asset possono aprirsi solo in modalità preview non-writing.
- Versioni backend restano v1 nel round pre-release; nessuna migrazione/API.

## Sequenza target

1. `intro.scene` — Dashboard coperta dalla scena narrativa.
2. `intro.dashboard` — panoramica pagina iniziale.
3. `intro.navigation` — sidebar collapse desktop / hamburger mobile.
4. `intro.transactions_nav` — voce Transazioni; navigazione soltanto con Next.
5. `intro.transactions_import` — pulsante Import.
6. `intro.brokers_add` — Add Broker.
7. `intro.brokers_currency` — preview BrokerModal, campo valuta.
8. `intro.fx_add` — Add FX pair.
9. `intro.fx_pair` — preview FxPairAddModal, base/quote.
10. `intro.assets_add` — Add Asset.
11. `intro.assets_config` — preview AssetModal, valuta/provider.
12. `intro.tools` — hub Tool/PAC.
13. `intro.settings` — replay onboarding e Finish.

## Step

### Step 1 - Contratto locale e scena introduttiva

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** i metadata conservano chiavi i18n e l'overlay risolve la
> copy con dipendenza esplicita dalla locale corrente. Il Welcome attende
> `waitLocale()` prima dell'avvio. Aggiunta `OnboardingIntroScene` con tre fasi,
> Start manuale, auto-start one-shot a 10 s, Escape/X/Skip, reduced motion e
> invalidazione dei timer concorrenti.
>
> **⚠️ Fuori pista:** la review degli error path ha rilevato che un fallimento API
> dello Skip durante `intro.scene` restava invisibile. La scena ora riceve e mostra
> lo stesso errore tradotto del coachmark in un alert accessibile.

- conservare chiavi i18n nei metadata, non stringhe risolte;
- dipendenza reattiva esplicita dalla locale;
- attendere locale selezionata dopo atomic Welcome;
- aggiungere `intro.scene` con clock iniettabile, tre frasi e auto-start 10 s;
- reduced motion, cleanup e one-shot race click/timer.

### Step 2 - Controller e sequenza tour

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** `INTRO_TOUR_STEP_IDS` ora descrive 13 tappe semantiche.
> `OnboardingOverlayHost` seleziona gli anchor desktop/mobile, cambia route solo
> dopo il Next esplicativo, supporta Back, sospende con X e chiude le superfici
> possedute dal tour su ogni transizione/uscita.
>
> **⚠️ Fuori pista:** durante la review del percorso completo, la direttiva
> `onboarding.settings` è risultata emessa come testo letterale anziché montata sul
> pannello replay. Corretto il markup e promosso il relativo check da seam manuale
> ad assert E2E.
>
> **⚠️ Fuori pista:** Finish/Skip ignoravano `active.mode` e un replay terminale
> poteva convertire `completed` in `skipped` o viceversa. Corretto il contratto:
> replay Finish/Exit elimina solo il token session-scoped; soltanto un flow pending
> automatico chiama complete/skip. Il replay Welcome salva le preferenze esplicite
> via endpoint settings esistente senza mutare il progresso onboarding.

- sostituire ordine attuale;
- aggiungere responsive anchor selection;
- impedire goto anticipati;
- gestire Back/Next, X suspend e Skip terminale;
- chiudere sempre superfici tour-owned su uscita.

### Step 3 - Surface registry e preview non-writing

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** aggiunto registry richieste/superfici
> `onboardingTourSurfaces`; Dashboard, Sidebar/Header, Broker, FX, Asset, Tool e
> Settings espongono anchor stabili. BrokerModal, FxPairAddModal e AssetModal
> hanno preview esplicite senza submit/handler di scrittura e mantengono invariati
> create/edit normali.
>
> **⚠️ Fuori pista:** la sola assenza delle CTA write non impediva l'attivazione
> da tastiera dei controlli finanziari sottostanti durante le tappe esplicative.
> La shell applicativa è ora `inert` esclusivamente durante `intro_tour`; overlay e
> guida Import restano fuori dal blocco e pienamente interattivi.

- registry account/route scoped;
- Sidebar toggle anchor;
- Broker/FX/Asset page handler open/close;
- `tourPreview` sui tre modal host, nessuna CTA write;
- anchor valuta/base-quote/provider;
- preservare normali create/edit e D/F.

### Step 4 - Coachmark e Welcome

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** coachmark ridisegnato con Skip permanente e X in alto,
> Back/Next o Finish nel footer e nessun controllo Pause. Il Welcome possiede lo
> Skip nella testata e passa alla Dashboard/scena solo dopo il salvataggio atomico
> o lo skip e l'applicazione della locale.

- top Skip + icona uscita; top-right X;
- rimuovere Pause;
- footer Back sinistra / Next destra con icone;
- Welcome Skip spostato in alto;
- complete/skip Welcome → Dashboard + scena, dopo locale pronta;
- nessuna chiave letterale.

### Step 5 - Import guide

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** la guida Import usa la stessa chrome/copy reattiva.
> X chiama `suspend({resetImport: true})`, quindi il replay successivo riparte da
> Upload senza scrivere backend. Step condizionali, sospensione modali annidate,
> duplicate bounce, Bulk/Save All e Finish esplicito restano separati e invariati.

- stessa chrome/copy reattiva;
- X sospende e riallinea il prossimo import a upload;
- nessun Back/Next duplicato rispetto al wizard;
- conditional step, nested modal e duplicate bounce invariati;
- Bulk Finish separato da Save All e zero commit.

### Step 6 - Test e documentazione

**Stato:** ✅ completato (2026-09-11).

> **Note implementazione:** test-author ha aggiornato unit/component/E2E e aggiunto
> i test per intro scene, surface registry e tour desktop/mobile. `front check`
> passa con 0 errori/0 warning dopo formattazione. Docs-writer ha riallineato sei
> pagine EN: MkDocs strict build e 12/12 link passano; `translate-validate` conserva
> intenzionalmente il debito delle traduzioni sostanziali. Il coordinator ha aggiunto
> 27 chiavi Round 1 in EN/IT/FR/ES e registrato surface unit, intro component, tre
> preview modal e la nuova action E2E desktop/mobile. Audit i18n: 2.833/2.833 per
> locale, 0 incomplete e 0 backend key mancanti.
>
> **⚠️ Fuori pista:** il primo
> `... dev.py test --test-port 6158 --data-dir /tmp/librefolio-r2-j-onboarding front-utility onboarding-component-unit`
> ha raccolto 186 test: 185 pass, 1 fail. Il caso mobile osservava correttamente
> il nuovo anchor ma verificava la rimozione `aria-describedby` dal vecchio anchor
> prima del cleanup reattivo. Il primo verdetto **assumption** è stato invalidato dal
> retry mirato: anche attendendo la condizione, il cleanup leggeva il prop `anchor`
> già aggiornato e lasciava l'attributo sul nodo precedente. Verdetto finale:
> **defect**; l'effect ora cattura e ripulisce il nodo realmente posseduto.
>
> **⚠️ Fuori pista:** il primo `... front-transaction tx-import-flow` ha dato
> 8 pass / 2 fail. G1 pretendeva il coachmark dentro la terza modale, contraddicendo
> la sospensione nested approvata (Bulk + Wizard = profondità 2; ParseDetail = 3).
> G2 tentava di cliccare l'Import della pagina dietro il Bulk ancora correttamente
> aperto, invece del suo `tx-bulk-import`. Entrambi classificati **assumption** e
> rimandati a test-author; nessun prodotto modificato e nessun retry cieco.
>
> **⚠️ Fuori pista:** la prima action component completa (11 file) ha dato
> 260 pass / 1 fail: jsdom non rifletteva `inert={true}` come attributo HTML sul
> form Broker. Il test mantiene la prova sostanziale (submit sintetico, zero API e
> callback) e l'E2E Chromium verifica la property `inert`; rimossa solo l'assunzione
> di rappresentazione jsdom.

- test-author: unit/component/E2E desktop+mobile;
- nuovo `onboarding-tour.spec.ts`, registrazione coordinator;
- docs-writer: pagine EN esistenti;
- coordinator: i18n EN/IT/FR/ES, runner, CHANGELOG/master.

### Step 7 - Gate e checkpoint

**Stato:** ✅ gate automatici completati (2026-09-11); review manuale aperta.

> **Note implementazione:** gate verdi già acquisiti nella lane J:
> `services settings` 24/24, `api settings` 37/37, `db populate --force`,
> `db referential-integrity` 15/15, `front-utility core-unit` 83 file / 2.054 test,
> `front-utility onboarding-component-unit` 11 file / 261 test,
> `front-utility settings` 45/45, `front-utility header-scroll` desktop/mobile 4/4
> e `front-transaction tx-import-flow` 10/10 dopo il triage. MkDocs strict build e
> link-check sono verdi; `front check` è 0 errori/41 warning legacy in due file;
> audit i18n 2.833/2.833 per locale.
>
> **Note review read-only:** la review finale ha trovato cinque problemi
> significativi, tutti corretti: race fra terminalizzazione Welcome e locale/returnTo;
> perdita della preview dopo remount del surface owner; highlight mobile non aggiornato
> durante la transizione Sidebar; Escape attivo durante complete/skip pending; flash del
> login durante retry bootstrap autenticato. Surface remount, motion refresh, busy
> Escape e retry bootstrap hanno test-author coverage; la race Welcome resta un seam
> manuale perché non esiste ancora un segnale deterministico tra risposta terminale e
> `waitLocale()`.
>
> **Ripresa post-freeze:** `front-utility auth` 23/23,
> `front-utility onboarding-tour` desktop/mobile 6/6, format-check globale verde e
> `check-orphans` verde (79 E2E frontend, 205 unit frontend, 205 backend registrati e
> raggiungibili). `front check` finale: 0 errori e 41 warning legacy in due file.
>
> **⚠️ Fuori pista:** il primo tour E2E ha dato 2 pass / 4 fail. Il desktop resume
> ha provato un difetto reale: dopo reload il layout dipendeva soltanto da una reactive
> legacy per riattivare il token; ora invoca idempotentemente `maybeStartIntro()` dopo
> bootstrap riuscito. I tre timeout mobile condividevano un'unica causa test: click
> pointer sull'opzione di un dropdown fixed fuori viewport. Il test-author usa ora il
> contratto tastiera pubblico con traversal bounded e nessun sleep. Rerun completo:
> 6/6 in 51,5 s.
>
> **Review runtime:** server test avviato senza `--force` con
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py server --test
> --port 6158 --data-dir /tmp/librefolio-r2-j-onboarding`; PID 95503 in ascolto su
> `*:6158`, `GET /api/v1/system/health` risponde `{"status":"ok"}`. Mantenerlo attivo
> fino al feedback developer e arrestarlo prima dell'handoff finale.

- lane 6158, una suite alla volta;
- core/component/onboarding E2E/auth/settings/import/header;
- front format/check, i18n audit, check-orphans;
- MkDocs build/check-links;
- review read-only e diff-check;
- review manuale attiva sulla lane 6158; shutdown rinviato alla chiusura finale.

## Runbook manuale combinato - prossimo sprint

### A. Account nuovo, Welcome e locale

1. Registrare un account usa-e-getta unico; atteso: `/welcome`, shell slim senza
   Sidebar, Header, Footer, Donation o Update.
2. Cambiare lingua e valuta, opzionalmente avatar, poi Continue. Atteso: una sola
   request atomica Welcome, Dashboard e scena già nella lingua scelta; nessuna chiave
   `onboarding.*`/`common.next` visibile.
3. Ripetere con Skip permanente. Atteso: nessuna preference write, Welcome terminale,
   scena intro ancora pending e disponibile.
4. Simulare errore complete/skip. Atteso: alert leggibile, controlli riabilitati,
   nessun falso successo né uscita dalla route.

### B. Scena e tour desktop

1. Lasciare la scena inattiva: tre frasi compaiono/scompaiono e il tour parte una sola
   volta a 10 s. In una seconda sessione premere Start prima del termine: nessun doppio
   avanzamento. Con reduced motion: testo statico completo, stesso deadline.
2. Dashboard: verificare titolo/copy, Skip e X in alto, nessuna Pausa, Next in basso a
   destra; la shell sottostante è `inert`.
3. Navigation: l'anchor indica il toggle collapse/expand; Back torna a Dashboard.
4. Transactions: prima evidenzia la voce Sidebar senza navigare; solo Next apre
   `/transactions`, chiude l'eventuale drawer ed evidenzia Import.
5. Broker: Add Broker, poi preview valuta. FX: Add Pair, poi base/quote. Asset: Add
   Asset, poi valuta/provider. Ogni preview è leggibile ma senza Save/Create e nessuna
   request finanziaria.
6. Tool/PAC resta raggiungibile dalla route reale. Settings apre Preferences,
   `onboarding-replay-section` è ancorato; Finish completa solo il pending automatico e
   rimuove `inert`.

### C. Tour mobile/focus

1. Ripetere B a viewport mobile. Navigation ancora il burger Header; lo step
   Transactions apre il drawer e ne evidenzia la voce; il Next successivo lo chiude.
2. Verificare coachmark bottom-sheet, safe-area, Back/Next opposti, Skip/X raggiungibili,
   focus sul pannello e Header pinned senza salto durante scroll.
3. X sospende mantenendo lo step semantico; refresh e nuovo login dello stesso account
   lo riprendono. Cambio account non trasferisce step, lingua, replay o risultato async.

### D. Replay terminale non distruttivo

1. Da Settings armare separatamente Welcome, Tour e Import su flow completed/skipped.
2. Atteso: label **Exit replay**, non **Skip permanently**.
3. Finish/Exit di Tour e Import eliminano solo il token sessione; nessuna request
   onboarding complete/skip e status/version/timestamp backend invariati.
4. Welcome Continue salva solo lingua/valuta/avatar esplicitamente scelti via settings
   PUT; Exit replay non salva nulla. In entrambi i casi lo status onboarding resta
   invariato.
5. Version mismatch terminale resta passivo e non riapre alcun flow.

### E. Guida Import reale

1. Armare Import da Settings, aprire Bulk -> Import. Atteso: guida su Upload e shell
   interattiva; X la sospende e riallinea la prossima apertura a Upload.
2. Percorrere file proprio: Upload -> Select -> Analyze -> eventuali
   Assets/Fix/Duplicates -> Review. Il coachmark segue lo step reale senza Back/Next
   duplicati.
3. Aprire ParseDetail/FilePreview/Broker/Asset nested. Atteso: guida sospesa oltre la
   profondità consentita e ripristinata allo stesso step dopo close.
4. Handoff Bulk: Save All evidenziato ma mai auto-cliccato; Finish della guida non
   salva draft. Solo un click utente separato su Save All crea transazioni.
5. Chiudere Bulk prima di Finish: nessuna complete/skip, replay conservato e prossima
   apertura su Upload.

### F. Popup, refresh e stato terminale

1. Con guida attiva, armare Donation/Update tramite hook debug quando disponibile:
   nessun popup sopra guida/modali; dopo l'uscita rispettare Donation -> Update.
2. Refresh su ogni route/preview: nessun modal finanziario o draft ricreato/cliccato
   automaticamente; solo lo step semantico sessione può riprendere.
3. Dopo Skip permanente automatico o Finish automatico, refresh/login non riaprono il
   flow. Replay manuale resta sempre disponibile da Settings.

## Definition of Done

- lingua scelta nel Welcome attiva nella scena e in ogni coachmark;
- nessuna chiave visibile;
- scena narrativa + Start + auto-start 10 s;
- Dashboard e navigazione spiegate prima di qualsiasi goto;
- sequenza completa fino a Settings;
- modali preview non scrivono;
- Pausa rimossa, X/Skip/Back/Next conformi;
- Import resta zero-auto-write;
- account/version/skip/replay invariati;
- gate automatici verdi;
- server 6158 disponibile durante la review manuale e spento alla chiusura finale;
- review complessiva aperta con il runbook seguente.

→ Follow-up: [Onboarding Round 2 — guide modulari e progressive](plan-phase00OnboardingRound2-ModularGuides.prompt.md)

→ Iterazione successiva: [Onboarding Round 3 — tour granulari per trigger](plan-phase00OnboardingRound3-TriggeredTours.prompt.md)
