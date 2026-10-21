# Backlog dopo la 1.2 — indice unico

> **Aperto il 2026-10-11** dal coordinatore della Release 2, su proposta del developer (testuale): «materializzare in
> LibreFolio_developer_journal/Release_2/Phase_0 un file mardown con il baklog post 1.2 e farlo popolare oltre che a te
> anche ai vari sotto agenti [...] così che con i vari treni e riallineamenti di baseline anche gli altri agenti possono
> aggiungerci roba e ne viene fuori un indice completo, utile per quando si riparte con gli sviluppi della 1.3 o 1.2.1
> da una chat pulita».
>
> È il **punto d'ingresso** di tutto il lavoro lasciato dopo la 1.2. Non sostituisce i vademecum delle cartelle né il
> backlog 38: li indicizza, con una riga per voce e il rimando ai dettagli.

## Come si usa

- **Una riga per voce**: `- **ID · titolo** — peso; origine (chi, data). Dettagli: [dove](percorso), sezione «…».`
  I dettagli (file e righe, prove, decisioni) restano dove sono già: il backlog 38, il README o il piano della cartella.
- **Ognuno scrive solo nella propria sezione.** Così i merge dei treni non si scontrano. Una voce che riguarda un'altra
  area si segnala al coordinatore, che la sposta.
- **Quando**: nello stesso checkpoint in cui la voce nasce, insieme al proprio piano. Chi chiude una voce la marca
  ✅ con data e commit: una voce non si cancella.
- **Il coordinatore riconcilia a ogni treno**: doppioni, voci chiuse, spostamenti fra sezioni, conteggi dell'indice.
- **Non va qui** il futuro deliberato, che resta in [`TODO_FUTURI.md`](../../../TODO_FUTURI.md). Non va qui nemmeno
  il lavoro già pianificato per la 1.2 e ancora in corso: quello sta nei piani delle cartelle.
- Pesi: minimo, basso, medio-basso, medio, alto. «Da verificare» vuol dire che serve prima un test rosso.

## 🧭 Ripartire da qui

> **La 1.2.0 è uscita il 14/10/2026**: tag `v1.2.0`, commit `cf00fac7d` su `main`, con lo stesso albero di `a3fe2eb04`
> in `dev_release2`. La run finale con coverage sull'albero del codice (`10e646f79`) era verde, 0 rossi; la galleria
> finale anche. Le sessioni figlie della release (R, V, U, T, I, M, W) sono archiviate: il loro lavoro aperto è in
> questo file, sezione per sezione. Da qui si pianifica la 1.3.0.
>
> **Dopo il rilascio, sempre il 14/10**: la pipeline di rilascio è verde (run 38540086298) e la pagina wiki della
> release è `released`. Il repo è stato ripulito: il progetto video è passato al repo business; `POC_UX`, `dev.sh` e
> il pacchetto `engineering-skills` sono usciti, la storia no. I branch locali `e-alfy-*` delle sessioni archiviate
> sono cancellati, tutti già contenuti in `dev_release2`. Il CHANGELOG ha un capitolo `[Unreleased]` con la sola
> sezione «🧹 Repository cleanup»: le voci della 1.3.0 vanno lì. Due decisioni aperte del developer: **C-92** qui
> sotto e il grafo della devWiki («Devwiki e grafo», sezione C).
>
> **La 1.3.0 è partita il 14/10** (coordinatore della 1.3): piano e stato vivo in
> [`Release_2/Phase_1/`](../Phase_1/README.md). Ogni sessione della 1.3 ha la sua sezione in fondo a questo file
> (H, A, X, W, J, Z, B, E, Y); le voci di queste sezioni chiuse dalla 1.3 le marca ✅ il coordinatore a ogni treno.

1. Questo file, per sapere cosa resta e dove sono i dettagli.
2. Le regole del progetto: [`.github/copilot-instructions.md`](../../../.github/copilot-instructions.md). La
   decisione 10 dice che la matematica finanziaria ha una casa sola, `backend/app/services/financial_math/`.
3. Lo stato del rilascio e delle cartelle: [`phases/00-index.md`](../phases/00-index.md).
4. Per una famiglia di lavoro, la sua guida per una chat nuova:
    - Rischio: [README della 02](02_riskfolioIntegration/README.md), sezione «🧭 Ripartire da qui»;
    - PAC: [README della 13](13_pacAllocator/implementation/README.md), blocco «🧭 Ripartire da qui» in testa.
5. Le cartelle restano in `Phase_0` anche da chiuse (developer, 10/10): si archiviano solo le chat.

## Indice per fonte

| Fonte | Cosa contiene | Stato all'apertura |
| --- | --- | --- |
| [Backlog 38](38_postReleaseBacklog/README.md) | I residui delle cartelle archiviate il 09/10 (gruppi N, O, L, K, P, I) e il backlog del coordinatore (C-1…C-55) | 138 voci |
| [README della 02](02_riskfolioIntegration/README.md) | Rischio: lavoro aperto, buchi, difetti, domande aperte | A1–A6, B1–B3, B6–B8 aperti |
| [README della 13](13_pacAllocator/implementation/README.md) | PAC: il backlog delle righe e la nota di ripartenza | riga 14, E2E del PAC, difetti 1, 2, 5, opzione (e) |
| [Piano della 16](16_toolPlatform/plan-phase00ToolPlatform.prompt.md) | Piattaforma dei Tool: la definizione di fatto residua (§5) | riverificata da W il 12/10 (B6a): D-T1…D-T3 nella sezione D |
| [Cartella 21](21_onboarding/plan-phase00Onboarding.prompt.md) | Onboarding: «Cosa resta aperto», voci 2–7 | 6 voci; la 1, la review manuale C7, chiusa l'11/10 |
| [Piani della 27](27_releaseImages/) | Immagini di rilascio, galleria, pipeline delle traduzioni | vedi la sezione M |
| [Piano della 32](32_docsEnglish12/plan-phase00DocsEnglish12.prompt.md) | Documentazione inglese della 1.2 | chiusa (S24); C-43 nel 38, 32-1…32-5 nella sezione Q |
| [Piano della 37](37_brimScalable/plan-phase00BrimScalable.prompt.md) e [recap dell'esportatore](37_brimScalable/recap-phase00ScalableExporter.md) | Scalable: «Ancora aperti, con chi li ha» (passo 13) e «Todo aperti» | chiusa; aperti con responsabile |
| [Piano della 41](41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md) | P&L per broker: §14 Backlog (B1–B19) | chiuso: F nel treno 42; le voci aperte nella sezione I |
| [Piano della 42](42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md) | Controlli delle coppie promosse | chiuso; C-46…C-48 nel treno 37, C-45 nel 38; le voci P nella sezione P |
| [Piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md) | Casa unica della matematica finanziaria e riordino del codice: U1–U10, B4, i lotti della parte 2 | B1, B2, B3a nel treno 37, B3b nel 38, PL3 e FE1 nel 39; T-1 nel 45; C-53 nel 47; BU1 nel 50 e BU2 nel 53 (D-P7); C-55 nel 56 |
| [Piano della 44](44_importWizardBrokerGate/plan-phase00ImportWizardBrokerGate.prompt.md) | Il wizard di import: «Avanti» aspetta la lista dei broker (M-16) | chiuso nel treno 48 |
| [Piano della 45](45_pluginModules/plan-phase00PluginModules.prompt.md) | Plugin in cartelle e traduzioni modulari, passi U-0…U-5 | aperto: U-1 (una cartella per plugin) nel treno 61; le voci aperte nella sezione U |
| [Piano della 46](46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md) | Le voci 21–23 della checklist del server: E2E su dati reali e righe legacy, il pannello lotti dopo il sync | chiuso nel treno 56; le voci aperte nella sezione V |
| [Piano della 47](47_chartAxisDayLabels/plan-phase00ChartAxisDayLabels.prompt.md) | Gli assi x dei grafici: il giorno nelle etichette, le linee dei broker del P&L che restavano | chiuso nel treno 59; 47-1 nella sezione I |
| [Piano della 48](48_uiPolish/plan-phase00UiPolish.prompt.md) | La rifinitura UI: BrokerIcon, la modale del broker sbagliato, il pannello della sicurezza, M-20, V-19 | chiuso nella 1.2 |
| [Piano della 49](49_requestCountRace/plan-phase00RequestCountRace.prompt.md) | La corsa dei contatori di richieste in `asset-detail.spec.ts` | chiuso nella 1.2 |
| [Piano della 50](50_brokerDetailBudget/plan-phase00BrokerDetailBudget.prompt.md) | Il dettaglio broker sotto carico (C-58) | chiuso nella 1.2 |
| [Piano della 51](51_narrowFitFixes/plan-phase00NarrowFitFixes.prompt.md) | Quello che non entra sui telefoni (R-1, R-2, R-4) e i marcatori persi nel periodo in corso (R-5) | chiuso nel treno 91 |
| [Piano della 52](52_timeAxisLastLabel/plan-phase00TimeAxisLastLabel.prompt.md) | L'ultima etichetta degli assi del tempo sui telefoni, le date dei tooltip, il periodo in corso di Growth, Alloc e lotti | chiuso nel treno 97 |
| [Piano della 53](53_pacTests/plan-phase00PacTests.prompt.md) | I test del PAC (T-PAC): mappa, coperture, test che mentono, difetti D1–D4, lotti A–C | aperto: tutto dopo la 1.2 (C-69, C-73…C-78) |
| [Piano della 54](54_galleryFixtureShares/plan-phase00GalleryFixtureShares.prompt.md) | La fixture della galleria: quote, YoC e variazione di un giorno non più scalate (I-M30) | chiuso nel treno 99; la privacy resta una domanda del developer |
| [Programma colori](../Phase_1/10_colorSystem/README.md) | Analisi colori v1.2 (P1–P11), piano generale (token, Designer Lab), workstream L, R, G, T, DV e, dal 16/10, IW, TR, AF, BK, IM (D-T28); materiale della designer | aperto il 14/10; spostato in `Phase_1/10_colorSystem` il 14/10 sera (era la 55); giro 1 della designer ricevuto; 16/10 sera: il 93,9 % delle classi sui ruoli (m1 697 nel target), il resto aspetta la designer; 17/10 notte: m1 674, token di componente letterali 583 → 6, i neutri dei grafici sui ruoli (B4), `drawnColors` sui ruoli; 18/10 notte: giro 3 della designer applicato (grafici, toast e banner, badge dei tipi sui ruoli `--lf-cat-*`), m1 590, galleria prima/dopo e zip per la designer |
| [Gallery deterministica](../Phase_1/10_colorSystem/G-galleryDeterminism/README.md) | Gallery deterministica: 27 schermate instabili su 177, fallimenti sotto carico; workstream G | aperto il 14/10; ora in `10_colorSystem/G-galleryDeterminism` (era la 56) |
| [Rapporto della run finale](38_postReleaseBacklog/report-R-final-run-coverage-20261013.md) | La run completa con coverage sull'albero candidato al tag (`10e646f79`): 0 rossi | C-79 |
| [README della 09](09_feedbackJobs/README.md) | Backlog strutturale P4 e feedback, «Cosa resta aperto» in cima (09/10) | 7 voci: 6 nella sezione 09, SP14 nella D |
| [`TODO_FUTURI.md`](../../../TODO_FUTURI.md) | Il futuro deliberato, non backlog | 53 temi |
| [Indice di luglio](38_postReleaseBacklog/TODO_ProssimeAttivita.md) | `TODO_ProssimeAttivita.md`, già nella radice: l'indice di priorità del 18/07, superato da questo file e dalla 09 | archiviato il 14/10 |
| [Fase 01, la 1.3.0](../Phase_1/README.md) e il suo [piano generale](../Phase_1/plan-phase01Release13.prompt.md) | Le funzioni per il cloud a ondate, il riordino del piano 43, le sessioni H, A, X, W, J, Z, B, E, Y | aperta il 14/10: sezioni H…Y in fondo |

---

## C · Coordinatore

Dettagli: [backlog 38](38_postReleaseBacklog/README.md). Qui le voci più pesanti o trasversali:

- **C-41 · Gli scatti dell'AI Export** — medio; developer, 10/10. Dettagli: 38, C-41.
- **C-42 · I vincoli delle coppie anche per contante e cambio** — medio. Dettagli: 38, C-42.
- **C-43 · Gli 8 scatti dei portali dei broker** — basso; servono schermate vere. Dettagli: 38, C-43.
- **C-44 · Gli helper della galleria in un posto solo** — basso. Dettagli: 38, C-44.
- **C-45 · Il picker del 💡 vede solo le righe caricate** — basso, da verificare. Dettagli: 38, C-45.
- **I-07 · Il controllo dei tipi sugli E2E** — basso: 2 errori e nessun gate. Dettagli: 38, I-07.
- ✅ **C-49 · Il backend non si ferma al SIGTERM entro 5 s dopo alcuni E2E** — basso, da verificare; anche per
  `docker stop`. Dettagli: 38, C-49.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): Z6b, un tempo massimo di spegnimento per tutti
  (`LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`), con l'attesa delle richieste in volo e un watchdog che chiude il processo
  allo scadere, commit `f0b9bcad2` (parte 1, entrato in `dev_release2` con `000090aaf`) e `fb3f98a0c` (parte 2,
  entrato in `dev_release2` con `967094d81`). Dettagli: sezione Z, voce C-49.
- ✅ **C-50 · L'AI Export di un Asset espone il nome interno `portfolio_weight_ratio`** — chiusa da T nel treno 39
  (`dd0a8d497`). Dettagli: 38, C-50.
- **C-51 · I dati sintetici scrivono la vecchia forma di `classification_params`** — basso. Dettagli: 38, C-51.
- **C-52 · La CLI della sonda dell'AI Export non sa scegliere l'Asset né l'utente sintetico** — minimo. Dettagli: 38, C-52.
- ✅ **C-53 · L'AI Export dice «non riconciliato» per un residuo di rumore** — chiusa nella 1.2 da T, treno 47
  (`876d2b430`). Dettagli: 38, C-53.
- ✅ **C-54 · «Novità dalla tua ultima versione» al login** — medio; **dopo la 1.2**, per decisione del developer (12/10).
  Al login, una versione più nuova dell'ultima vista apre il modale del changelog sui capitoli non visti, nella
  lingua dell'utente. Dettagli: 38, C-54.
  ✅ **Fatto da A il 17/10 (A11)** (`737268864`, dev `630c478cd`): `AuthUserResponse.whats_new` e `POST /auth/whats-new/seen`, modale `WhatsNewModal` fra i popup differiti; account `NULL` vedono il capitolo corrente, i nuovi mai.
- ✅ **C-55 · L'AI Export di un broker senza posizioni non passa i controlli pubblici «invalid HHI points»** — chiusa
  nella 1.2 da T, nel treno 56 (developer, 12/10). Il payload era corretto; sbagliava la sonda, che contava ogni HHI
  nullo come violazione. Dettagli: 38, C-55.
- **C-56 · BrokerIcon: con le props vuote l'icona non legge lo store (H3)** — basso, latente; I, 12/10. La catena
  delle icone nasce solo dalle props (`frontend/src/lib/components/brokers/BrokerIcon.svelte`). Oggi le superfici
  passano le props piene, quindi non si vede; si vedrebbe con una superficie che passa solo l'id. `BrokerBadge` legge
  già lo store. Va tenuto `settledIconFieldIds`, che impedisce il giro infinito. Dettagli: l'analisi di I del 12/10,
  nel piano della 48 (rifinitura UI), §1.
- **C-57 · La lista dei plugin per le icone non si ritenta dopo un errore (H2)** — basso, da verificare; I, 12/10. Se la
  prima richiesta fallisce (`frontend/src/lib/utils/broker/brokerHelpers.ts`, `ensurePluginIconsLoaded`), le icone dei
  plugin mancano fino al ricaricamento della pagina. Dettagli: come C-56.
- ✅ **C-58 · Dettaglio broker: un test sfora i 30 s sotto carico** — chiusa nella 1.2 da I, lotto 50 (13/10): era
  un'assunzione di tempo, non un difetto. Ogni test del blocco esterno ricaricava la lista dei broker che il
  `beforeEach` aveva appena lasciato pronta. Ora gli helper aprono il broker dalla lista sullo schermo e ne asseriscono
  l'indirizzo, e il blocco FIFO ha un budget esplicito di 60 s, come i blocchi axisBuilder e P&L; nessuna asserzione
  tolta o allentata. La prova, sul test (ora `:429`): con ogni risposta dell'API ritardata di 2,5 s la base scade a
  30,0 s e la cura passa in 23,1 s; con 3,8 s la cura passa in 34,6 s, grazie ai 60 s. La spec intera è verde a 1
  worker (carico 16 → 44) e a 4 worker (carico 46 → 34). Era: basso; coordinatore, 12/10. Nel gate del treno 59,
  con carico ~56, «the lot detail modal renders its three sections and the net breakdown»
  (`frontend/e2e/brokers/brokers-detail.spec.ts:410`) è scaduto durante la navigazione, prima del pannello (40,1 s);
  rilanciato con carico 30, è passato in 2,9 s. Nei 30 s stanno login, `ensureBrokerExists`, due navigazioni e il
  pannello. Da valutare con `test-triage`: un budget esplicito o una navigazione in meno. Dettagli:
  [piano della 50](50_brokerDetailBudget/plan-phase00BrokerDetailBudget.prompt.md).
- ✅ **C-59 · L'immagine Docker installa `uvicorn[standard]` fuori dal lock** — chiusa il 13/10, prima del tag (decisione
  del developer, D5): il developer ha eseguito `pipenv upgrade "uvicorn[standard]==0.52.4"` e `pipenv sync --dev`, a
  corsie ferme. Il lock ora contiene uvloop 0.23.0, httptools 0.9.0 e watchfiles 1.3.0. Il resolver ha alzato due extra
  già presenti, websockets 17.1 → 17.2 e python-dotenv 1.2.3 → 1.2.4; i pacchetti di sviluppo non sono cambiati. Il
  `Dockerfile` installa solo `requirements.txt`, generato dal lock. Era: medio-basso; coordinatore, 12/10, dalla
  ricerca su Python. `Dockerfile:70` esegue `pip install uvicorn[standard]` senza versione dopo `requirements.txt`:
  `uvloop`, `httptools` e gli altri extra arrivano in produzione all'ultima versione del giorno della build, mentre il
  lock non li contiene, e sviluppo e test girano senza `uvloop`. È uno scarto fra sviluppo e produzione, e una build
  non riproducibile. Cura: gli extra nel `Pipfile` (`uvicorn = {extras = ["standard"], …}`), il lock e
  `requirements.txt` rigenerati dal developer, poi via la riga 70. Dettagli: [rapporto di ricerca del 12/10](38_postReleaseBacklog/research-python-3.15-20261012.md),
  §5.
- **C-60 · Python dopo la 3.13** — medio; developer, 12/10 (richiesta di ricerca). Python 3.15.0 è uscito il 09/10.
  - Gli import lazy (PEP 810) sono una parola chiave esplicita, `lazy import`: utili per avviare più in fretta i worker
    con QuantLib, cvxpy, matplotlib e TA-Lib.
  - Il free-threading (senza GIL) resta una build separata, `python3.15t`, non il default. Non alza il throughput di
    questo server: l'event loop resta uno e SQLite ha un solo scrittore. Aiuterebbe solo il lavoro CPU nei thread.
  - Al 12/10 cvxpy, riskfolio-lib, osqp, arch, ta-lib e PyYAML non hanno wheel per la 3.15.
  - Consiglio del 12/10: la 1.2 resta su 3.13 (sicurezza fino a ottobre 2029); dopo la 1.2 la **3.14 con la build
    normale**; la 3.15 verso il primo trimestre 2027, dopo una nuova verifica delle wheel; il free-threading più avanti.
  - **Decisione del developer (13/10)**: si resta sulla 3.13 finché un salto non porta vantaggi significativi. Il
    passaggio alla 3.14 dopo la 1.2 non è in calendario. Il rapporto del 12/10 è **il punto di partenza dei prossimi
    confronti**: si rifanno le stesse verifiche (la tabella delle wheel pacchetto per pacchetto, lo stato del
    free-threading, le immagini Docker) e si confrontano con le sue tabelle.
  - Dettagli, con la tabella di compatibilità pacchetto per pacchetto: [rapporto di ricerca del 12/10](38_postReleaseBacklog/research-python-3.15-20261012.md).
- **C-61 · BulkModal: la barra di selezione dopo un import, mai provata** — basso, da verificare; W (lint della
  devWiki), 12/10. La pagina della wiki è aperta dal 25/06: dopo un import BRIM la barra di selezione del BulkModal
  mancava o era tagliata (il contenitore `overflow-y: auto`, oppure `onSelectionChange` non propagato). Nessuna delle
  due cure proposte è nel codice, e nessun E2E seleziona una riga nel BulkModal dopo il passaggio dall'import
  (`tx-bulk-import-handoff.spec.ts` non guarda la barra). Prima un test rosso; se non si riproduce, la pagina si
  chiude. Dettagli: [`bulk-modal-sticky-z-index`](../../../LibreFolio_devWiki/wiki/problems/bulk-modal-sticky-z-index.md).
- ✅ **C-62 · DataTable: il ridimensionamento delle colonne è provato su una tabella sola** — basso, da verificare; W (lint
  della devWiki), 12/10. La pagina della wiki, aperta dal 07/07, dice che in alcune tabelle la maniglia non allarga la
  colonna, senza una causa trovata (`onColumnResize` non letto dal genitore, o una `width` fissa che la rimette com'era).
  Un E2E lo prova solo sulla tabella L1° del Laboratorio di rischio (`risk-lab.spec.ts`, «value columns carry their
  help»): le altre DataTable vanno ritestate. Dettagli: [`datatable-column-resize-noop`](../../../LibreFolio_devWiki/wiki/problems/datatable-column-resize-noop.md).
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): Y7 con la decisione D-Y18, prima un rosso E2E su una
  tabella `layout-auto` (`layout/datatable-resize`), poi le maniglie sui Pointer Events e la larghezza trascinata tenuta
  anche come `min-width`, commit `ca681b4f9`, entrato in `dev_release2` con `a613a217c`.
- ✅ **C-63 · File: due pulsanti «copia» con un ripiego scritto a mano** — chiusa nella 1.2 da I, treno 72
  (`65d20910e`): FileGrid e FilesTable copiano dall'helper. Era: minimo; coordinatore, 12/10, dal lint della
  devWiki. `components/files/FileGrid.svelte:110` e `components/files/FilesTable.svelte:544` hanno un loro ripiego
  `execCommand` per l'HTTP, che funziona, invece dell'helper comune `utils/clipboard.ts` (`writeTextToClipboard`);
  FileGrid ignora l'esito di `execCommand` e segna «copiato» anche quando non ha copiato. Cura: passare entrambi
  dall'helper, dopo M-20 (lotto 48 di I). Dettagli: la voce M-20 nella sezione M.
- ✅ **C-64 · Devwiki: il secondo giro di lint** — chiusa da W il 13/10 (devWiki soltanto): date e hash in conflitto
  e feature `planned` contro il codice (C-64a–e, la mappa degli hash riscritti `8ba2db509`); le pagine feature
  contro il capitolo [1.2.0] verificato, con la pagina nuova F-114 (`fa93b1777`); i piani di
  `phases/06_betaTestingReportAndFixing`, con 3 pagine corrette perché contraddicevano il codice e 5 nuove
  (`2b1734e76`). I rilievi minori non verificati sono elencati nella pagina fonte
  `sources/beta-testing-2026-08-05`. Ne sono nate C-65 e C-66, qui sotto.
- **C-65 · Evento → transazione: il resto del collegamento (F-090)** — medio-basso; W (C-64), 12/10. Sono già nel
  codice, sotto F-051: la FK `RESTRICT` (`backend/app/db/models.py:830`), la cancellazione degli eventi che risponde
  con un esito per id e rispetta il `RESTRICT` (`api/v1/assets.py`, `delete_events_bulk`), il selettore degli eventi
  nel form. Mancano il modale al cambio di provider (vecchio evento → nuovo, con la proposta di ricollegare) e la
  ricerca inversa `GET /transactions?asset_event_id=`. Vicina ma diversa: «🔗 Suggerimento eventi collegabili nella
  bulk modal» in [`TODO_FUTURI.md`](../../../TODO_FUTURI.md). Dettagli: [F-090](../../../LibreFolio_devWiki/wiki/features/F-090.md).
  - ✅ **Ricerca inversa chiusa il 15/10** da W (lotto I1 della 1.3, `5e96df752`; in `dev_release2` con `dc7e4e48e`):
    `GET /transactions?asset_event_id=`, nei broker che l'utente vede (C-65b nel piano 04). Resta aperta la modale al
    cambio di provider (C-65a, X e W).
  - Stato (19/10): fatta la parte b, la ricerca inversa (`5e96df752`, entrato in `dev_release2` con `dc7e4e48e`);
    resta C-65a, la modale al cambio di provider, non fatta: è fuori dal lotto K3 di W, parcheggiato il 19/10 (N91),
    e si fa con X dopo (piano 04, §7).
- ✅ **C-66 · Sync: l'avviso prima di sovrascrivere i dati (F-094)** (chiusa 16/10 dal coordinatore: X `32c64bbd9`, entrata `4b2e0df80`; il developer: il fornitore vince, basta l'avviso; X-R29/X-R30) — basso; W (C-64), 12/10. Il dialogo c'è già ed è
  comune a cambi e asset: `SyncModalBase`, con `FxSyncModal`, `AssetSyncModal` (lista degli asset) e `PageSyncModal`
  (pagine di dettaglio), che sincronizzano l'intervallo della pagina. Manca solo l'avviso quando l'intervallo scelto
  copre dati che esistono già, per i cambi come per gli asset. Dettagli: [F-094](../../../LibreFolio_devWiki/wiki/features/F-094.md).
- **C-67 · Coverage JS: ogni invocazione ricostruisce il frontend due volte** — basso; R, 13/10, run completa §3.6.
  `dev.py server --test` forza il modo debug (`dev.py:197`, `:228`), quindi una build di produzione strumentata è
  «del modo sbagliato» e viene ricostruita in debug; poi `_ensure_frontend_build` (`_frontend_common.py:71-74`) rifà
  la strumentata. Nella run completa non costa nulla, nei rilanci di una singola azione 5–7 minuti. Dettagli:
  [rapporto di R del 12/10](38_postReleaseBacklog/report-R-full-run-coverage-20261012.md), §3.6.
- **C-68 · Gli artefatti di Playwright spariscono alla categoria successiva** — basso; R, 13/10. `test-results/` si
  svuota a ogni invocazione: `error-context.md` e gli screenshot dei rossi di una categoria si perdono quando parte la
  successiva. In una run completa vanno copiati via mano a mano. Dettagli: come C-67.
- **C-69 · Il planner del PAC non ha coverage JS** — medio-basso; R, 13/10; aggiornata da T il 13/10 con l'analisi
  T-PAC. Il developer: «Tutto dopo la 1.2».
  - **Le misure** (corsia di T, base `6a12f9a06`): unit al 17,40 % (788 statement su 4 528, istanbul in Vitest).
    La logica TS è al 34 %, i componenti al 4 %; 61 file su 84 sono allo 0 %. La run del 12/10 dava il 14 % su
    7 008 statement della build strumentata.
  - **I1, la misura E2E è falsata.** La lacuna 3 di V (`pac-allocator-real`) è verde ma raccoglie zero coverage JS.
    La fixture `jsCoverage` (`frontend/e2e/fixtures/playwright.ts:311-360`) legge `window.__coverage__` solo al
    teardown, e lo spec ha già portato la pagina su `about:blank` (`frontend/e2e/pac-allocator-real.spec.ts:283`).
    I contatori si perdono a ogni navigazione, e 47 punti degli E2E finiscono su `about:blank`: le cifre E2E del JS
    sono limiti inferiori, e una nuova misura non vedrà lo spec di V. La fixture è di V.
  - **Da fare, dopo la 1.2**:
    - lotto A, ~3,5 g: percentuali, riequilibrio dei target, badge della prova, `localProblems`, rinforzo dello spec
      di V con la coverage raccolta prima dello smontaggio, perimetro dal vivo;
    - lotto B, ~5 g: i componenti;
    - lotto C, ~4 g: un E2E «FX e commissioni» e il backend fine.

  Dettagli: [piano della 53](53_pacTests/plan-phase00PacTests.prompt.md), §1, §6 e §9; rapporto di R come C-67, §4.2.
- **C-70 · I rifiuti di lettura dei plugin di import sono solo in inglese** — basso; T, 13/10, controllo del
  CHANGELOG (D13). Il messaggio che il Generic CSV dà per un file che non sa leggere, e quelli della lettura di L108,
  arrivano in inglese in ogni lingua, e il rifiuto del Generic CSV nomina il codice `broker_generic_csv` invece del
  nome del plugin. Da fare: codici d'errore con parametri, tradotti nel frammento i18n del plugin. Dettagli:
  `/tmp/libreFolio_changelog_audit_T.md` §3 D13 (copia nella sessione del coordinatore).
  - ✅ **Parte a chiusa il 15/10** da W (lotto K2a della 1.3, `0eac8e1b6`; in `dev_release2` con `62c964242`):
    DEGIRO e il Generic CSV rifiutano un file con un `BRIMRefusal` a codice, tradotto in `importWizard.parseRefusal.*`
    (le chiavi stanno nella sorgente `importWizard`, non nel frammento del plugin, per la regola R1 di
    `gate-plugin-i18n-ownership`), e il rifiuto nomina il plugin col suo nome. Resta la parte b, il 400 del parse
    tradotto nel wizard e il codice dell'anteprima illeggibile (K2b, dopo un commit del coordinatore su `brokers.py`
    e `uploads.py`).
  - Stato (19/10): fatta la parte a (K2a, `0eac8e1b6`, entrato in `dev_release2` con `62c964242`); resta la parte b,
    K2b (il 400 strutturato del parse e `preview_unreadable_workbook`), con K2c: non fatte, perché aspettavano un
    commit del coordinatore su `brokers.py` e `uploads.py` che non è venuto (piano 04, §7).
- ✅ **C-71 · Due «Rolling Return» con lo stesso nome** (chiusa 16/10 dal coordinatore: CP-10a di J, decisione 29, treno 100 — resta un solo Rolling Return in giorni di calendario, l'indicatore della 1.1 è ritirato) — minimo; I, 13/10, controllo del CHANGELOG (D-I1). L'indicatore
  della 1.1 (`rolling_return`, finestra in osservazioni) resta nel catalogo dei segnali e usa la stessa chiave di nome,
  `signals.riskRollingReturn.name`, del modo nuovo del grafico dell'asset (`calendar_rolling_return`, giorni di
  calendario, nascosto dal catalogo). Chi viene dalla 1.1 può leggerli come un doppione. Da fare: un nome che dica la
  finestra («… (observations)» contro «… (calendar days)»), oppure ritirare l'indicatore vecchio.
- **C-72 · Commenti e pagine del runner e della coverage rimasti indietro** — minimo; V e M, 13/10, trovati
  lavorando a V-28 e M-29. Il codice è giusto, i testi no:
  - help e commenti del runner: `scripts/test_runner/_cli.py:437`, `:482`, `:866`; `_coverage.py:151-165`;
    `_consolidate.py:204`, `:259`; la docstring di `_common.py:120` nomina `_consolidate._run_playwright_batch`, che oggi
    è `run_playwright_group`;
  - `frontend/vitest.config.ts:47` cita uno script che non esiste; `frontend/scripts/js-coverage-report.js:14`, `:35`;
  - `mkdocs_src/docs/developer/test-walkthrough/runner_architecture.md:433-453`, `:716`, `:732`;
  - la pagina devWiki `problems/svelte-template-branches-not-instrumented.md`, contraddetta da `2e104b919`.
  Da fare: un giro solo sui testi, senza toccare il comportamento.
- ✅ **C-73 · Le percentuali del planner del PAC arrotondano male i pareggi (D1)** — basso; T, 13/10 (T-PAC); dopo la
  1.2. `planner/` sta per `frontend/src/lib/features/tools/pac-allocator/planner/`.
  - **Il difetto**: `formatPlannerPercent` e `formatPlannerPercentUnits` (`planner/format.ts:223-235`) passano da
    `formatPercent(Number(…))` (`frontend/src/lib/utils/core/formatPercent.ts:82-90`: `value * scale`, poi
    `toFixed`). Il planner invece dichiara «half away from zero, exactly» (`planner/decimal.ts:106`, R14).
  - **Le prove**: una quota esatta di 0,30595 appare «30,59 %» invece di «30,60 %»; fra 0,1 e 0,9 sbaglia 3 864
    pareggi su 8 000. Tocca pesi, quote, esposizioni, spread e margini.
  - **Non è l'arrotondamento prudente del piano**: quello sta nel calcolo (`constraints.py:417-418` e il margine
    d'esecuzione), non nella visualizzazione.
  - **Da fare**: il rosso in `format.test.ts` (TP-2), poi `roundDecimal` prima di formattare.

  Dettagli: [piano della 53](53_pacTests/plan-phase00PacTests.prompt.md), §5 D1.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): CP-2 di J, le percentuali arrotondano i pareggi una volta
  sola, sul testo decimale (0,30595 → «30,60 %»), con i rossi in `format.test.ts`, commit `5810e03d2`, entrato in
  `dev_release2` con `2faa88a34`.
- ✅ **C-74 · L'aiuto di «Value after the plan» è sbagliato per il PAC (D2)** — basso; T, 13/10 (T-PAC); dopo la 1.2.
  - **Il difetto**: l'aiuto dice «the units you had plus the ones bought» (`planner/result/AssetTable.svelte:79-83`,
    chiave `…finalValueHelp`). Nel PAC invece `final_value = buy_mid_value` e `current_invested = 0`: lo impone lo
    schema (`backend/app/schemas/pac_allocator.py:1976-1981`, `:2026-2027`), e la stessa tabella lo dice in
    `buyMidHelp`.
  - **Anche «Ideal value»** nomina «already invested», che nel PAC vale sempre 0.
  - **Da fare**: i due testi nei 4 cataloghi con `dev.py i18n update`, senza chiavi nuove.

  Dettagli: piano della 53, §5 D2.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): CP-2 di J, i testi di aiuto del valore finale e di quello
  ideale descrivono un PAC, che parte da zero, nei 4 cataloghi e senza chiavi nuove, commit `5810e03d2`, entrato in
  `dev_release2` con `2faa88a34`.
- ✅ **C-75 · Un limite di SCIP a -0.0 farebbe fallire la validazione del risultato (D3)** — basso; T, 13/10 (T-PAC);
  dopo la 1.2.
  - **Il difetto**: `_float_text` (`backend/app/services/pac_allocator/planner_report.py:1044-1059`) scrive -0.0
    come «-0» (`_decimal_text`, `:1086-1091`). `PlannerFixedDecimal` (`backend/app/schemas/pac_allocator.py:47`)
    rifiuta «-0» in `primal` e `dual`.
  - **L'effetto**: non è mai stato visto, ma un piano valido diventerebbe un risultato che non passa la validazione.
  - **Da fare**: il rosso con un limite -0.0 (TP-11), poi lo zero negativo scritto come «0».

  Dettagli: piano della 53, §5 D3.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): CP-2 di J, le prove del solutore scrivono «0» per uno zero
  di qualunque segno, col rosso di un limite -0.0 in `test_pac_planner_report.py`, commit `5810e03d2`, entrato in
  `dev_release2` con `2faa88a34`.
- ✅ **C-76 · Il cancello locale del planner non controlla segno e zero (D4)** — basso; T, 13/10 (T-PAC); dopo la 1.2.
  - **Il difetto**: `localProblems` (`planner/request.ts:154-175`) controlla solo «vuoto» e «non è un numero» per
    l'importo da usare, il contributo e il passo dell'ordine. Un negativo o uno zero arriva al codec o al backend.
    L'utente legge l'errore generico «A field does not match the planner contract: {path}», non un messaggio sul
    passo.
  - **In più**: il backend riporta un importo selezionato negativo sul percorso di `available`
    (`backend/app/services/pac_allocator/normalize.py:449-450`).
  - **Da fare**: `localProblems` a tabella (TP-12) e i controlli, con chiavi nuove per i messaggi.

  Dettagli: piano della 53, §5 D4.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): CP-2 di J, `localProblems` segnala sul suo campo un
  importo o un contributo negativo e un passo ≤ 0, e il backend riporta un importo selezionato negativo sul suo
  percorso, commit `5810e03d2`, entrato in `dev_release2` con `2faa88a34`.
- **C-77 · Test del PAC che dichiarano più di quanto verificano** — medio-basso; T, 13/10 (T-PAC); dopo la 1.2.
  - **Backend**:
    - **B1**: «requires owner» (`backend/test_scripts/test_services/test_portfolio_allocation_source.py:398-444`).
      Con EDITOR e VIEWER la sessione finta non restituisce righe, a prescindere dal codice; della produzione si
      controlla solo che `OWNER` sia fra i parametri (`:404`). Un filtro `role IN (OWNER, EDITOR)` passerebbe.
      L'unico test dal vivo usa VIEWER.
    - **B2**: «superuser has no implicit bypass» (`backend/test_scripts/test_api/test_portfolio_api.py:1565-1596`)
      mocka il builder perché sollevi sempre.
    - **Altri tre**: i filtri `broker_id IN` di posizioni e cassa (`portfolio_allocation_source.py:61-66`,
      `:127-131`) non girano in nessun test; la mappa congelata dei codici d'errore non chiama la produzione; 42
      rifiuti dello schema non controllano la ragione.
  - **Frontend**:
    - l'E2E `pac-allocator-real` («printed as the engine answered») non confronta istruzioni (quantità), pesi né
      «Verified in Decimal»;
    - `printed()` scarta «≈» e separatori (`frontend/e2e/pac-allocator-real.spec.ts:150-155`), il filo passa da
      `Number()` (`:528-537`), e i dati in euro interi non arrotondano mai;
    - `request.test.ts:30` promette i problemi locali per id ma controlla solo la lista vuota;
    - `ResultCell.test.ts` monta 3 varianti su 11.
  - **Da fare**: TP-17 (perimetro dal vivo con EDITOR, selezione mista, SQL vero) e TP-18 (rinforzo dello spec); il
    resto nei lotti B e C.

  Dettagli: piano della 53, §4.
- **C-78 · Minori del PAC** — minimo; T, 13/10 (T-PAC); tutti dopo la 1.2.
  - **D5**: denaro e prezzi del planner passano da un double (`planner/format.ts:109`,
    `frontend/src/lib/utils/currency/currencyFormat.ts:46`). Oltre circa 15 cifre significative le ultime cifre sono
    inventate, senza «≈».
  - **D6**: `AssetEditor` riscrive i pesi delle esposizioni dalle frazioni float del `DistributionEditor` condiviso
    (`planner/steps/AssetEditor.svelte:82-104`, `toFixed(6)`), quindi tiene 4 decimali di percentuale.
  - **Backend, dall'audit, da riverificare**:
    - i limiti del plugin (256/512 KiB) abbassati in silenzio ai default della piattaforma (128/256 KiB);
    - `rounding_delta` pubblicato da `rounding_adjustment`, col segno degli accrediti invertito rispetto al testo
      del contratto (`schemas/pac_allocator.py:1553`, `planner_report.py:703-722`);
    - `request_fingerprint = snapshot_id` nei risultati di fallimento (`planner.py:167`);
    - «-0» negli importi economici della copia (`portfolio_allocation_source.py:598`).
  - **Testi vecchi**: i commenti di `test_pac_planner_normalize.py:544-552`, `test_pac_planner_wire_numbers.py:10-15`,
    `modeText.test.ts:11-16`, `pluralCountSites.test.ts:13-19` e `pac-allocator-real.spec.ts:19`.

  Dettagli: piano della 53, §4 e §5.
- ✅ **C-79 · Cancellare un broker lascia il suo lock e la sua cartella vuota in `broker_reports`** — minimo; R, 14/10, run
  finale. Alla cancellazione di un broker restano `.locks/broker_N.lock` e la cartella vuota `uploaded/broker_N/`: nella
  run finale, 89 lock e circa 107 cartelle dei broker temporanei delle spec di import. Nessun file di report resta
  orfano. Cura: la pulizia del file system nella cancellazione del broker (BRIM/import), dopo la 1.2. Dettagli:
  [rapporto della run finale](38_postReleaseBacklog/report-R-final-run-coverage-20261013.md), §3.
  - ✅ **Chiusa il 15/10** da W (lotto I1 della 1.3, `5e96df752`; in `dev_release2` con `dc7e4e48e`): la cancellazione
    del broker toglie anche le sue cartelle di stato vuote e il suo lock. Con lei C-3 del backlog 38.
- **C-80 · Backend: i moduli sotto l'80 %** — basso; R, run finale del 13/10 (§4.1). In 1.2 la copertura
  complessiva è 91,55 %, ma alcuni moduli restano indietro:
  - `services/scheduler/scheduler.py` 60,18 %;
  - `brim_providers/broker_cryptocom` 69,86 % e `broker_cointracking` 74,45 %;
  - `api/v1/assets.py` 75,00 %, fermo dal 03/09 (73,9 % nel report 17);
  - `fx_providers/fed` 75,18 %, che dipende dalla rete;
  - `services/tools/resources.py` 75,50 % (run del 12/10).

  Per pacchetto, `brim_providers` ha la quota più grossa di righe mancanti (906, rami al 79,7 %); `fx_providers` ha i
  rami al 75,4 %. Cura: test mirati, a partire dallo scheduler e da `api/v1/assets.py`. Dettagli: [rapporto della run finale](38_postReleaseBacklog/report-R-final-run-coverage-20261013.md).
- **C-81 · Frontend: i file mai eseguiti e i grandi scoperti** — basso; R, run del 12/10 e finale (§4.2). Da
  rimisurare **dopo I1** (C-69): finché la fixture `jsCoverage` perde i contatori, le cifre E2E sono limiti inferiori.
  - Allo 0 %, fuori dal planner del PAC: `features/tools/ToolDiagnosticsPanel.svelte`,
    `features/tools/components/ToolExecutionMetrics.svelte`, `routes/+error.svelte`,
    `components/risk/levels/SimulationProvenance.svelte`, `components/files/FileSetBadges.svelte`,
    `components/assets/assetEditData.ts`, `hooks.server.ts`.
  - I più scoperti: `ImportWizardModal.svelte` (1 374 statement, 50,1 %, sceso dal 54,9 %: non attribuibile finché c'è
    I1), la pagina dell'asset (553), `TransactionBulkModal.svelte` (423), `TransactionFormModal.svelte` (338), la
    lista degli asset (300), `RiskAnalysisPanel.svelte` (279, rami al 40,1 %), `LotComparisonChart.svelte` (46,8 % il
    12/10).

  Dettagli: [rapporto della run finale](38_postReleaseBacklog/report-R-final-run-coverage-20261013.md).
- **C-82 · Le cure da carico sono provate solo a carico normale** — medio-basso; R, run finale. La run finale ha avuto
  un carico medio di 8,9, contro 37,9 il 12/10: dimostra che le cure di V-27, V-28, V-33 e V-36 reggono a carico
  normale, non a carico alto. Cura: una run a 4 worker con un'altra corsia attiva, o con un carico sintetico, prima
  del prossimo rilascio. Dettagli: [rapporto della run finale](38_postReleaseBacklog/report-R-final-run-coverage-20261013.md), §1.2.
- **C-83 · Le pagine scrivono la barra del giorno in `price_history`** — minimo; R, run finale (§3). Quando una pagina
  chiede il prezzo corrente, il backend lo salva come barra del giorno (nella run finale +7 righe, poi +3 dopo
  mezzanotte). Uno spec che contasse le barre di un asset vedrebbe +1 secondo il giorno e l'ordine dei test: un
  conteggio va scritto relativo, mai assoluto. Dettagli: [rapporto della run finale](38_postReleaseBacklog/report-R-final-run-coverage-20261013.md).
- ✅ **C-84 · Le versioni scritte a mano nei file del progetto** — minimo; coordinatore, 14/10. `pyproject.toml` e
  `frontend/package.json` dicono ancora 1.1.0, fissate il 05/08; nessuno le legge, perché la versione dell'app viene da
  `git describe`. Da allineare a ogni rilascio, o da togliere. **Metà chiusa da H il 15/10** (decisione 14):
  `pyproject.toml` a `0.0.0`, con un commento (`6e78b8c96`, in `dev_release2` con `9deb0ea08`); `frontend/package.json`
  e le due righe radice del lock con il CP5b di H, dopo la finestra della galleria.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): anche la seconda metà, `frontend/package.json` e le due
  righe radice di `package-lock.json` a `0.0.0` (CP5b di H, decisione 14), commit `87be1e2d8`, entrato in
  `dev_release2` con `83eaa5a28`; la prima metà è `6e78b8c96`, entrato con `9deb0ea08`.
- ✅ **C-85 · Mostrare che si sta aspettando il server, nelle richieste importanti** — medio; developer, 14/10, dalla
  verifica sul server della build `v1.1.0-1674-g797a7e432` (voce 7). Le sue parole: «quando un pacchetto è in volo non si
  ha chiaro che si sta attendendo la risposta, dobbiamo aggiungere nel backlog un task che si occupa di rendere palese
  in qualche modo che si sta aspettando una risposta dal server per le domande importanti».
  - Il caso visto: nel grafico P&L della Dashboard, cambiando i broker del filtro, le linee si aggiornano solo quando
    arriva la risposta, e nel frattempo niente dice che il calcolo è in corso.
  - Da fare: l'elenco delle richieste lente o importanti (il report della Dashboard e dei broker, il Rischio, i lotti,
    l'AI Export, il PAC, i sync), e per ciascuna un segnale uniforme di attesa sul contenuto che cambierà: uno stato
    «in aggiornamento» sul grafico o sul pannello, e i dati vecchi attenuati invece che lasciati come se fossero
    attuali. Da progettare insieme, con un componente comune, e dopo la 1.2.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): Y11, con la decisione 48 del developer (niente badge né
  dati attenuati): finché la pagina aspetta una richiesta importante, il pulsante «Aggiorna» della barra in cima si
  spegne e la sua icona gira (`pageBusy`), e il pulsante «Aggiorna» del pannello del rischio esce. Commit `ec018afdf` e
  `e843be00c` (entrati in `dev_release2` con `0c79932a7`) e `37bfeebb9`, le pagine degli asset (entrato con
  `d32d0f3d9`). Dettagli: piano di Y, «Y11».
- ↪ **C-86 · Un provider di prezzi con le API di Interactive Brokers** — basso; utente C (uno dei primi utenti), chat del
  04/09, ritrovata dal developer il 14/10. Prezzo corrente e storico letti con la chiave dell'utente. Dipende da un
  posto dove salvare le chiavi dei plugin (consegnato nella 1.3: impostazioni dei plugin con segreti) e da un account per le
  prove. Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 4.
  ↪ **Spostata il 18/10 in `TODO_FUTURI.md`, «🧬 Profilo dei dati dell'asset»** (developer), insieme a F16 e F-MC-3.
- ↪ **C-87 · Rendimento a scadenza (YTM) e duration delle obbligazioni** — basso; utente C, chat del 04/09. Salvarli con
  la loro data, perché cambiano nel tempo, e mostrarli nella pagina dell'asset. Da decidere se leggerli da un provider
  o calcolarli in `backend/app/services/financial_math/`. Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 5.
  ↪ **Spostata il 18/10 in `TODO_FUTURI.md`, «🧬 Profilo dei dati dell'asset»** (developer), insieme a F16 e F-MC-3.
- ↪ **C-88 · Un pacchetto di dati di qualità in abbonamento** — minimo, un'idea da valutare per `TODO_FUTURI.md`; utente
  C, chat del 04/09. Prezzi storici e composizioni dei fondi a pagamento, per chi li vuole, anche come sostegno al
  progetto. Da valutare: licenze dei dati, costi, convivenza con l'installazione self-hosted. Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 14.
  ↪ **Spostata il 18/10 in `TODO_FUTURI.md`, «🧬 Profilo dei dati dell'asset»** (developer), insieme a F16 e F-MC-3.
- ✅ **C-89 · Spiegare le due date del cambio valuta** — minimo; utente C, chat del 04/09. Nel modulo, accanto alle date
  «Da» e «A» (`TransactionFormModal.svelte:1645`, `:1693`), un suggerimento: di solito coincidono, e si separano quando
  il broker accredita la nuova valuta in un altro giorno. La stessa frase nella guida (`user/transactions/form.*.md`).
  Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 31.
  - ✅ **Chiusa il 15/10** da W (lotto K1 della 1.3, `532a1fd9c`; in `dev_release2` con `d915c869f`):
    il suggerimento nel form (`tx-form-fx-dates-hint`) e la stessa frase nella guida, nelle 4 lingue.
- ✅ **C-90 · «Testa configurazione» dice che è solo una prova** — minimo; utente C, chat del 04/09. Accanto al risultato
  dello storico, una riga: la prova legge gli ultimi giorni, e alla creazione dell'asset LibreFolio scarica tutto lo
  storico disponibile. Oggi lo dice solo la guida (`user/assets/create-edit.en.md:67`). Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 11.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): X, nel lotto F21 + C-90 del CP13, la nota
  `assets.probe.scopeNote` in 4 lingue accanto all'esito di una prova manuale con lo storico riuscito, commit
  `656667b86`, entrato in `dev_release2` con `cd617824e`.
- **C-91 · Collaudare gli import di Interactive Brokers e Fineco su report veri** — minimo; utente C, chat del 04/09.
  Sono ancora Beta, scritti su esempi trovati online: chiedere all'utente un report vero con i numeri cambiati,
  ricavarne fixture sintetiche e, se regge, togliere il Beta. Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 32.
- **C-92 · Il capitolo 1.2.0 del CHANGELOG non cita due idee dell'utente C che sono nel codice** — minimo, decisione
  del developer; coordinatore, 14/10. I settori «Obbligazioni societarie» e «Titoli di Stato», assegnati da Borsa
  Italiana, e l'import CSV delle distribuzioni per settore e paese sono nella 1.2.0, ma il capitolo non li nomina. Due
  strade: aggiungerle come correzione dopo il rilascio, in 4 lingue con lo stamp del pezzo (il capitolo è rilasciato,
  quindi `translate-validate` è severo), oppure lasciare il capitolo com'è. Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voci 8 e 17.
- ✅ **C-93 · Un test dell'AI Export lascia un thread di aiosqlite dopo la chiusura del loop, sotto carico** — minimo, da
  verificare; W, 15/10 (`all-backend` della revisione combinata di I1). Due `PytestUnhandledThreadExceptionWarning`
  («Event loop is closed») nel gruppo parallelo, worker 1, in
  `test_ai_export_components_portfolio_broker_financial.py::TestPerformanceBuckets::test_performance_path_uses_detail_owned_uniform_density[broker-broker.performance-components1-full-30]`.
  Non è un rosso; da solo il test passa senza avvisi. Dominio dell'AI Export: a J dopo il CP-1, con la skill
  `test-triage`. Dettagli: [piano 04](../Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md),
  «Revisione combinata `123c21efc`», passo 6.
  - 15/10: non riprodotto nella `all-backend` di J sulla revisione `b17f8fb85` (13 810 passed, nessun avviso).
  - ✅ **Chiusa il 15/10** da J (`12bcf7e99`; in `dev_release2` con `c412f8dad`). Causa trovata, verdetto «stato
    condiviso»: 7 test dell'AI Export lasciavano aperte connessioni aiosqlite. Erano 3 in `broker_adequacy`, senza
    `engine.dispose()`, e 4 test di composizione in `portfolio_broker_integration`, che eseguivano SQL vero sulla
    sessione senza tabelle e passavano per una via d'errore casuale. Riprodotto in modo deterministico: un GC in un
    thread con un loop corrente chiuso dà i 2 avvisi identici. Curato con una fixture che chiude il motore, scenari
    ermetici e una guardia sulla sessione senza tabelle. Verificato con `all-backend --workers 2`: 0 connessioni
    lasciate aperte, nessun avviso. Dettagli: piano J, §10 «C-93».
- ✅ **C-94 · Il server di test costruisce frontend e documentazione dentro i 300 s d'avvio** — basso, infrastruttura;
  J, 14/10 (era J-2), con una nota del coordinatore. In un worktree nuovo il primo `all-backend` cade anche dopo
  `npm ci`: prima di uvicorn `dev.py server --test` fa la build di debug del frontend (~4 min) e quella del sito, se
  mancano, dentro `STARTUP_TIMEOUT` (`scripts/test_runner/_server.py:48`), con lo stdout in `DEVNULL` (`:274-275`).
  Lo stesso succede dopo un merge che cambia il frontend o la doc. Rimedio di oggi, scritto in
  `.github/copilot-instructions.md`: `front build --debug` e `mkdocs build` prima della run, oppure
  `LIBREFOLIO_TEST_STARTUP_TIMEOUT=600`. Cura proposta: le build prima che parta il tempo massimo, con un messaggio
  che dica cosa sta costruendo. Nota: senza `node_modules` il runner arriva a `npx` attraverso `generate-api`, e
  dovrebbe fermarsi subito. Il runner è condiviso: va assegnato a una sessione. Dettagli: piano J, §10
  «`all-backend` — la base».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): J, `dev.py server --build-only` fa le build prima che
  parta il tempo massimo, e il runner e la galleria lo lanciano in primo piano, con l'output; `front build` e
  `api client` si fermano subito senza `node_modules`. Commit `1c67dd5d9`, entrato in `dev_release2` con `2faa88a34`.
  I `npx` diretti rimasti nel runner sono J-8.
- **C-95 · L'albero dei moduli in `backend-schemas.instructions.md` è indietro** — minimo, doc per gli agenti; W, 15/10
  (K2a). L'albero di `.github/instructions/backend-schemas.instructions.md` non elenca `ai_export_runtime`,
  `pac_allocator/`, `portfolio`, `risk`, `risk_scenarios`, `signals`, `system`, `tools`, `wac`; le righe di
  `assets/` e `transactions/` le hanno già aggiornate X (CP4) e W (K2a). Da fare in una passata sola a fine
  riordino. Dettagli: piano 04, §12, K2a.
- ✅ **C-96 · Le corsie dei test prendono la configurazione dell'istanza dal `.env` del developer** (chiusa 16/10 dal coordinatore: H `901fa33f6`, «test lanes ignore the instance's configuration») — medio, sicurezza dei
  test; E, 15/10 (analisi). `scripts/cli_base.py:configure_test_runtime()` carica il `.env` e toglie solo
  `INSTANCE_TRUST_SECRETS` (S2 di H): ogni altra `LIBREFOLIO_*` arriva alle corsie. Con la configurazione SMTP di E i
  test spedirebbero email vere; con `LIBREFOLIO_BLOCKED` o il profilo gestito tutte le corsie cambierebbero
  comportamento. Cura: la corsia tiene solo le variabili del runner e scarta il resto della configurazione d'istanza
  venuta dal `.env`; un test usa `.env.example` come elenco. Assegnata a H dal coordinatore, prima del primo lotto di E;
  comprende A-9 (le quattro variabili di account di A5a). Dettagli: analisi di E; piano H.
- ✅ **C-97 · Più cifre decimali per quantità e prezzi (crypto, issue #43)** — medio, **nella 1.3**; coordinatore,
  16/10, dalla issue [#43](https://github.com/Librefolio/LibreFolio/issues/43) di un utente che segna BTC, ETH e PEPE.
  Assegnata a W (transazioni), dopo W-B30 e W-B36b.
  - **Oggi**: il form delle transazioni accetta 6 decimali (`maxFractionDigits={6}`, `TxFormSingleSection.svelte:176`
    e `:224`, `TxFormPairSection.svelte:192`, da `75309672e` del 18/09). La 1.1 ne accettava di più.
  - **Il modello**: `Numeric(18, 6)` per quantità, importi e costo manuale (`transactions`), per i prezzi
    (`price_history`) e per i valori degli eventi (`asset_events`). Su SQLite la scala dichiarata non limita ciò che
    si salva (la colonna tiene un `REAL`), ma SQLAlchemy **arrotonda a 6 decimali in lettura**: misurato il 16/10,
    `0.12345678` salvato torna `0.123457`, e il valore intero resta nel file.
  - **Le cifre che servono**:
    - **quantità: 10 decimali**. BTC ne usa 8 (il satoshi). I broker dell'utente ne mostrano 6–8 secondo il token, e
      qualche exchange arriva a 10. I 18 di ETH (wei) servono solo ai wallet on-chain, fuori dai broker;
    - **prezzi: 12 decimali**. PEPE vale `0,0000034573 €` (10 decimali), e i token sotto `1e-8` ne vogliono 12 per
      tenere almeno 4 cifre significative. I cambi hanno già `Numeric(24, 10)`;
    - **importi in valuta: restano 6**.
    - **Il limite vero è il `REAL` di SQLite**, circa 15 cifre significative. Con 10 decimali una quantità è esatta fino
      a 99 999 unità; oltre, i token che si contano a milioni usano pochi decimali. Un salvataggio decimale esatto
      (testo) è un lavoro più grande, da valutare dopo, insieme al lotto G della matematica (niente `SUM` in SQL).
  - **Superfici**: il modello; la migrazione, da decidere nell'analisi (precedenti: le note di 002 e 004 sulle
    dichiarazioni che SQLite ignora); il form singolo, quello della coppia e il Bulk; la visualizzazione delle quantità
    (`txDisplayHelpers.ts:21` taglia a 6, più le tabelle di posizioni e lotti); i prezzi piccoli mostrati con abbastanza
    cifre significative; l'import CSV e il BRIM non devono troncare.
  - **Oltre il limite**: un valore con più cifre si rifiuta con un messaggio che dice il massimo, mai arrotondato in
    silenzio.
  - **Effetto per chi ha già i dati**: i valori salvati con più cifre (dalla 1.1, da un import o via API) tornano
    visibili, perché sparisce solo l'arrotondamento in lettura. Quelli già risalvati a 6 restano a 6.
  - **I `.svelte` del form sono nell'area TR dei colori**: cambia solo un attributo, ma serve il loro OK.
  - Test: test-author, dal rosso della quantità a 8 e 10 decimali e del prezzo `0.0000034573`. Doc utente delle
    transazioni. Una riga 🐛 nel CHANGELOG.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): W, in tre lotti, più uno di X.
  - C-97a, modello e backend (quantità a 10 decimali, prezzi e costo unitario a 12, rifiuto oltre il massimo): commit
    `bab52635d` (cherry-pick in `dev_release2`, treno 123) e `de901f228`, il costo Auto (entrato con `c91bd41b2`).
  - C-97b, l'input: commit `24aa1d69b`, entrato in `dev_release2` con `b2462042d`.
  - C-97c, la visualizzazione: commit `a1e8a3631`, `a8ec9d309` e `6f11057fb` (entrati con `f1bfa1e31`, `016fe7af9` e
    `e19f7c7e6`); C-97c-4 di X, i cambi delle valute deboli, `7ac14656a` (entrato con `e414edf0b`).
  - I seguiti sono voci a sé nella sezione W: W-B51, W-B64, W-B65, W-B78.
- **C-98 · Fornitore di prezzi CoinGecko** — basso, da decidere; coordinatore, 16/10, suggerimento dell'utente della
  issue #43 («CoinGecko lists 3× more crypto than Yahoo Finance»). CoinGecko ha un'API gratuita con chiave e limiti al
  minuto: con le impostazioni dei plugin di CP11 (chiave per utente o per istanza) si integra come plugin di X. Non è
  nella 1.3 finché il developer non lo chiede.
- **C-99 · Manuale admin: nuova struttura, variabili d'ambiente divise per categoria** — medio, **nella 1.3**;
  developer, 16/10. Un solo lotto di documentazione del coordinatore, quando i lotti cloud di H, A, B, E e Z sono entrati.
  Struttura, regola provvisoria per i figli e requisiti (link vecchi funzionanti, controllo delle variabili,
  `.env.example` diviso): piano generale della 1.3, §6, «Manuale admin: la struttura finale».
  Stato (19/10): fatta la regola provvisoria per i figli, per esempio le sette righe dell'email in
  `configuration.en.md`, una riga ciascuna col link a `email.md` (E6.1 di E, `3480cbc53`, entrato in `dev_release2` con
  `56759b2c8`); resta il lotto della struttura, del coordinatore: le pagine per categoria, la tabella di tutte le
  variabili, `.env.example` diviso e i link vecchi funzionanti.
- **C-100 · Regola di review: un campo di sicurezza nuovo dichiara il suo valore managed** — minimo, regola; E e
  coordinatore, 17/10 (revisione di H-37, R13-SEC7). Un campo `Settings` di sicurezza nuovo dichiara il suo valore in
  `PROFILE_DEFAULTS["managed"]` nello stesso lotto, e chi rivede lo controlla; il test (a) di `MANAGED_DEFAULTS` non lo
  vede se lista e test cambiano insieme. La riga gemella sta in `backend.instructions.md` (H-39), che aggiunge anche
  l'avviso quando la protezione dei frame è spenta in managed.
- **Devwiki e grafo** — medio: il passo 3 dell'historian e la ricostruzione del grafo dopo la 1.2 (P-6). **14/10, prima
  va sistemato lo strumento**: graphify 0.9.54 (quello nel lock) non indicizza più i link simbolici che puntano fuori
  dalla radice, e il corpus (`LibreFolio_devWiki/corpus/`) è fatto solo di quelli. Il rilevamento vede 0 file e, con un
  `graph.json` già presente, `./dev.py graph update` non si ferma: per questo non l'ho lanciato. Il grafo è fermo al
  10/09 (cache AST `v0.8.46`). Strade: fissare graphify alla 0.8.x, oppure un corpus senza link esterni. Nello stesso
  giro, `check_source_paths.py`: segnala come mancanti le cartelle di output della coverage (`frontend/coverage-js/`,
  `htmlcov-backend/`, `htmlcov-backend-e2e/`, `htmlcov-frontend/`), ignorate da git, quando non sono sul disco (in ogni
  worktree nuovo, e nel checkout principale dopo la pulizia del 14/10). Dovrebbe saltare i percorsi ignorati da git.

## Risk · Rischio (02)

Dettagli: [README della 02](02_riskfolioIntegration/README.md), sezioni «cosa resta aperto» e «🧭 Ripartire da qui».

- **A1–A6** — la fase 3 degli asset nei segnali, la scheda Rischio dell'asset, la guardia della simulazione, i percorsi
  adattivi, il rendimento totale, l'ottimizzazione oltre 100 titoli (A6, riaperta l'11/10).
- **B1–B3, B6–B8** — l'icona della doc sui pannelli, le colonne di rischio di Asset Global, la fetta del portafoglio per
  asset, V1/V2, gli ordinamenti della heatmap di L2, la paginazione di L3.

## D · PAC e Tool (13, 16)

Dettagli: [README della 13](13_pacAllocator/implementation/README.md), «🧭 Ripartire da qui» e «Backlog».

- **Riga 14 · L'analisi del Rebalancer**, poi gli E2E del PAC insieme a quelli del Rebalancer.
- **Difetti 1, 2, 5 e l'opzione (e)** del backlog della 13; **C-38**, l'intestazione Actions su mobile.
  Stato (19/10): chiusi C-38 e i difetti 2 e 5 da Y7, con la decisione D-Y17 (sotto i 768 px le colonne di selezione e
  delle azioni scorrono con la tabella, intestazione e celle insieme), commit `ca681b4f9`, entrato in `dev_release2` con
  `a613a217c`; restano il difetto 1 e l'opzione (e).
- **D-T1 · La modalità di memoria dei Tool non si vede in nessuna schermata** — basso; W, 12/10, ricontrollato sul
  codice (B6a). `capabilities.memory.mode` nella diagnostica e `resources.memory` per job stanno nell'API, ma
  `ToolDiagnosticsPanel.svelte` e `ToolExecutionMetrics.svelte` non li mostrano. Il dossier dell'11/09 la chiamava «la
  riga più importante». Dettagli: [F-106 nella devWiki](../../../LibreFolio_devWiki/wiki/features/F-106.md), «Still
  open»; [piano della 16](16_toolPlatform/plan-phase00ToolPlatform.prompt.md), §5.
- **D-T2 · Il client dei Tool aspetta il timeout della piattaforma, non quello dell'operazione** — minimo oggi; W, 12/10.
  `frontend/src/lib/features/tools/contracts.ts:343` usa `client_timeout_ms` della politica (65 s). Il PAC dichiara lo
  stesso valore, quindi oggi non cambia niente; conta col secondo Tool. Dettagli: come D-T1.
- **D-T3 · La misura della memoria in modalità osservata** — da verificare; W, 12/10. La memoria residente sommata di un
  albero di processi può contare due volte le pagine condivise, e un picco fra due campioni può passare inosservato. Il
  percorso cgroup non è mai stato provato su un host delegato vero, e nessun benchmark è stato fatto. Dettagli: come
  D-T1.

## I · P&L per broker (41)

Dettagli: [piano della 41](41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md), §14; dove va ogni voce, §17.6. Il
lotto è chiuso: il motore nel treno 32, la card (H) nel treno 35, F nel treno 42. Su F-AI il developer ha deciso il
12/10: nella 1.2 la (a), cioè niente; la (b), il nome «FX on cash» nell'export del portafoglio, è la voce qui sotto.
Righe scritte da I il 12/10, coi numeri di riga di `5d62658bb`; la voce F-AI (b) con quelli di `378338fed`; la 47-1,
dal piano 47, con quelli del suo commit C3; la 49-1, dal piano 49, con quelli di `0071b9703`.

Altrove: B9 (T-U3), C1 (T-U4), L1/L2 (T-U6) e KpiSection (T-U8) sono nella sezione T. P1, R4, W1 e X5 sui prezzi F
non li ha toccati e restano a T: P1 in U4, R4 in U5 con B8, W1 in U7, X5 dei prezzi in U1 (§17.6). Il gruppo I del
[backlog 38](38_postReleaseBacklog/README.md) resta lì: aggregazioni e grafici (I-01…I-05, col gate della privacy in
I-05), `npx` nel runner (I-06), il `tsc` degli E2E (I-07, già nella sezione C), il debito di traduzione MkDocs (I-08),
gli eventi degli asset (I-09…I-12). Fuori da questa sezione: B16 (latente, nessuna azione), C-53 (del coordinatore), il
debito di traduzione di F-5 (di M).

- ✅ **F (B4, B13, B14) · La cassa in valuta estera rivalutata ogni giorno** — nella 1.2, chiusa il 12/10 nel treno 42
  (merge `15cbff6fb`): il modulo `36b181836` e i suoi risultati di cambio `a5f41f60c`, il motore `aa6b6077a`, il
  servizio con la riga «FX on cash» `c04e44ff5`, il frontend `9a0d9280c`, la doc `a4332b25b`. Chiude anche la metà di
  B11 sulla cassa, B12 per le storie e i flussi dei contributi, X5 e O2 sui giri del portafoglio e sulla card.
  Dettagli: [piano della 41](41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md),
  §15, da «F-0» a «F-5».
- **F-AI (b) · «FX on cash» per nome nell'export del portafoglio** — basso; I, 12/10. Decisione del developer: dopo la
  1.2, «con un codice tipizzato». Oggi la riga compare per nome negli `effects` di `broker.flows_income_costs`;
  nell'export del portafoglio resta dentro `period_other_result`, perché `portfolio.flows_income` tiene solo Income e
  Cost (`portfolio_financial.py:401,438`).
  - Il codice: un campo tipizzato su `OtherPeriodEffect` (`schemas/portfolio.py:433-440`), scritto da chi produce la
    riga (`portfolio_service.py:1978`). Chi la legge confronta il codice, non più la descrizione inglese: l'export e i
    due confronti del frontend (`OtherPeriodEffectsTable.svelte:75`, `PerformanceChart.svelte:291`). Il campo è
    additivo, ma cambia l'API: serve `api sync`.
  - L'export: un campo con le righe «FX on cash» per broker, filtrate per codice. `portfolio.flows_income` passa a v2
    (`components/catalog.py:109`), con `COMPACT_COMPONENT_VERSIONS` `{1,2}` (`snapshotDataRenderer.ts:1443`) e i test.
  - Sonda mirata sulla corsia, sui dati sintetici (metodo del piano 43, B3b passo 5).
  - Facoltativo: una frase sulla cassa rivalutata nella `valuation_semantics` delle due provenance, col loro bump a v3.
  - Stima ¾ g più la sonda: il codice aggiunge circa 2 h alla ½ g del piano. Rischio basso sulle cifre, che non
    cambiano; medio sul contratto. Dettagli: idem, §15 «F-AI».
- **B1 · L'avviso sulle quote diverse non arriva all'utente** — basso; I, 10/10 (D6). Si scrive solo per le coppie di
  più giorni (`portfolio_engine.py:347-350`, nel blocco di `:332`) e finisce in `classifier_warnings` (`:2107`, letto
  a `:2335`), che nessun chiamante passa. Dettagli: idem, §14.
- **B2 · Coppie invertite** — basso; I, 10/10. Se l'arrivo ha una data precedente alla partenza, il flusso cade sulla
  data più tarda e resta il residuo transitorio di prima. Dettagli: idem, §10 e §15 «T2a–T2e», «Data del flusso».
- **B3 · K/R delle gambe esterne e normali** — basso; I, 10/10. Solo le gambe `linked_internal` di CASH_TRANSFER e
  FX_CONVERSION muovono i pool (`portfolio_engine.py:860-872` nel pre-frame, `:1122-1133` nel frame): la partenza
  prende prima da R poi da K, l'arrivo mette tutto in K («Approximate»). Le metà `linked_external_*` e le gambe normali
  non toccano K/R. Cambia solo la ripartizione dei BUY fra nuovo e reinvestito (`acquisition_funding`). Dettagli:
  idem, §14.
- **B5 · Nel waterfall, una voce per i trasferimenti al valore di mercato** — basso; I, 10/10. Nelle viste filtrate
  (D2, D5) i titoli che entrano o escono dalla selezione sono capitale al valore di mercato, mentre i contributi
  spostano l'unrealized al costo (B8): la differenza, ∓(valore di mercato − costo), è il guadagno maturato presso
  l'altro broker e finisce nel residuo «Other». Da decidere con B8: se i contributi valutano il trasferimento al
  mercato, la voce può non servire. Dettagli: idem, §14.
- **B6 · Coppie ADJUSTMENT coi flussi al valore di mercato** — basso; I, 10/10. Escluse da D4: restano capitale al
  costo, e una coppia di più giorni è un intervallo «cash» a valore 0. Dettagli: idem, §14.
- **B7 · Uno split durante il viaggio** — basso, da verificare; I, 10/10. Dettagli: idem, §14.
- **B8 · Il prezzo proprio dei contributi** — medio; I, 10/10. `get_positions_contribution`
  (`portfolio_service.py:1642`) prende l'ultima chiusura con `_get_price_at_date` (`:525`, senza ripiego né split) a
  `:1789` e `:1806`, converte i prezzi uno a uno (`:1795`, `:1813`) e su un TRANSFER sposta l'unrealized al costo. Va
  in T-U5 con V2/P2 e R4 di T e con le quantità di B12: insieme 1½–2 g. Dettagli: idem, §14 e §17.6.
- ✅ **B10 · `periodBasePnl` dichiarato e mai usato** — minimo; I, 10/10. `GrowthChart.svelte:594-600`.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): Y1, tolto nel taglio di `GrowthChart` (FE6a), commit
  `495fe0eae`, entrato in `dev_release2` con `badec1465`.
- ✅ **B11 · I giorni «dirty» non contano i cambi dei titoli** — medio, ½ g; test-author di I, 10/10. I giorni di cambio
  si contano solo per le valute tenute in cassa (`native_cash.py:271-279`; motore `:808` e `:922-923`). La cura cambia
  NAV e linee anche con la sola cassa in valuta base, quindi il golden della guardia andrebbe rigenerato: serve una
  decisione. Va in T-U1 o T-U5. Dettagli: idem, §14 e §17.6.
  - **Chiusa** (16/10, 03:55) da J CP-6 (decisione 28, `58c10197c`), entrato col treno 87 (`628e3e49e`); golden W1 rigenerato.
- **B12 · Le quantità dei contributi leggono le date future** — minimo, latente; I, 11/10. Senza `date_to`,
  `_get_transactions` (`portfolio_service.py:1721`) legge anche le righe future; l'unico chiamante, `get_report`
  (`:2234`), passa sempre la data di fine, quindi nessun effetto in produzione. Va in T-U5 con B8. Validare le date
  future è una scelta di prodotto. Dettagli: idem, §14.
- **B15 · Il PAC e la pagina del broker rifanno la custodia** — medio-basso, ½ g; I (T7), 11/10. Il PAC somma
  `Transaction.amount` per broker e valuta senza quota (`portfolio_allocation_source.py:109-137`; le quantità a `:45`);
  la pagina del broker passa da `transaction_service.get_cash_balances` (`broker_service.py:392`). Entrambi potrebbero
  leggere `NativeCash.balances()` (`native_cash.py:281`), ciascuno con la sua regola di quota. Va in T-U5 o T-U7.
  Dettagli: idem, §14 e §16 punto 9.
- **B17 · Il risultato di cambio sulla cassa in viaggio resta nel residuo «Other»** — basso; I, 12/10. Test S6:
  residuo −175, nessuna riga FX. Dettagli: idem, §15 «F-W», «Fuori pista».
- **B18 · Lo spread di un FX_CONVERSION sullo stesso broker resta nel residuo** — basso; I, 12/10. Test S5: −10 nel
  residuo. Dettagli: idem, §15 «F-W», «Fuori pista».
- **B19 · L'ordine delle righe degli unallocati nei contributi** — minimo, preesistente; I, 12/10.
  `portfolio_service.py:1938` scorre `set(unalloc_income.keys()) | set(unalloc_fees.keys())` e perde l'ordine
  d'accesso fissato a `:1705-1706`: in pratica è l'ordine dell'hash degli interi di CPython. La cura cambia l'ordine
  delle righe, non le cifre. Dettagli: idem, §15 «F-W», «Fuori pista».
- ✅ **47-1 · Sotto zoom gli assi a categoria perdono le etichette** — basso, preesistente; I, 12/10 (piano 47, punto 3
  dell'analisi). In compatto l'`interval` si calcola su tutti i punti (`responsiveXAxis.ts:149`, da `2d22130bd`), e i
  gestori del `dataZoom` di `CandlestickChart.svelte:249`, `LineChart.svelte:358` e `PriceChartFull.svelte:579` non lo
  ricalcolano sulla finestra visibile. Prova SSR, un anno giornaliero a 800 px con spazio per 12 etichette: 12 senza
  zoom, 7 con metà periodo, 4 con un quinto, solo i due bordi su una finestra di 33 punti. Gli assi time non ne
  soffrono. Dettagli: [piano della 47](47_chartAxisDayLabels/plan-phase00ChartAxisDayLabels.prompt.md), §4 «Fuori» e
  §9, passo 7.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): Y8, l'`interval` delle categorie si ricalcola sulla
  finestra visibile dello zoom in `LineChart`, `CandlestickChart` e `PriceChartFull`, commit `a25d09a69`, entrato in
  `dev_release2` con `160562b56`.
- ✅ **48-1 · Il pulsante dell'AI Export più largo dei vicini nella barra** — minimo, cosmetico; I, 12/10 (piano 48,
  V-19). Il trigger di `AiExportMenu.svelte:298` ha `px-3 gap-2`, i pulsanti vicini `px-2.5 gap-1.5`
  (`assets/[id]/+page.svelte:2826-2861`). Allinearlo stringe la colonna di «Exportación IA» di circa 12 px. Da solo
  non avrebbe curato V-19, che sforava fino a 18,8 px: lo ha curato C5 con le soglie `denseRow`. Resta un ritocco di
  coerenza. Dettagli: [piano della 48](48_uiPolish/plan-phase00UiPolish.prompt.md), §1.5 e passo 5.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): Y8 con l'ok di J, il pulsante dell'AI Export e il
  `sync-button` della Dashboard a `gap-1.5 px-2.5` come i vicini, commit `a25d09a69`, entrato in `dev_release2` con
  `160562b56`.
- **49-1 · Il debito di lint di `_frontend_broker.py`** — minimo, preesistente; I, 12/10 (piano 49, §6). `ruff check`
  dà E701 a `:44`, `:45`, `:52`, `:53` e PLC0415 a `:96`; `black --check` lo riformatterebbe in due pezzi. Viene da
  `1a29e0523`, `547c06cf0` e `7d3463e2f`, ed è fuori dal gate: ruff e black del gate passano solo `backend/`
  (`dev.py:1841`, `:1848`). Nel runner intero sono 149 errori ruff in 17 file, e black riformatterebbe 15 file su 30:
  se pulirlo in una volta sola lo decide il coordinatore. Dettagli:
  [piano della 49](49_requestCountRace/plan-phase00RequestCountRace.prompt.md), §6.
- ✅ **54-1 · Con la liquidità negativa la storia dell'allocazione sfora il 100 % e il grafico la taglia** — basso,
  preesistente; I, 13/10 (piano 54, passo 8). La liquidità entra in Tipo e Settore col suo segno, non in Geografia
  (`daily_state.py:715-717`, `cumulative_cash + it_cash`), e ogni lista divide per il totale con segno
  (`derived_views.py:231-243`): un saldo negativo porta le quote positive sopra 100. ECharts impila i negativi sotto lo
  zero (`stackStrategy` di default `samesign`, `echarts/lib/processor/dataStack.js:103`, `:132`) e `max: 100` taglia
  la cima (`AllocationHistoryChart.svelte:703`, `:802`). Tooltip e famiglie scartano le voci fino a 0,01 (`:623`,
  `:626`, `:775`), la torta quelle fino a 0 (`AllocationPanel.svelte:60-67`): la liquidità negativa non compare da
  nessuna parte. Nessun caso nella corsia né nella fixture. Da decidere se mostrare la leva o togliere la liquidità
  negativa dal totale. Dettagli: [piano della 54](54_galleryFixtureShares/plan-phase00GalleryFixtureShares.prompt.md),
  passo 8.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): Y10, con la decisione 49 del developer: l'asse della storia
  segue la pila, le serie si impilano `samesign`, i tooltip mostrano la liquidità negativa come riga a sé, fuori da
  «Remaining», e il pannello dice lo scoperto sotto la torta, commit `1bb8dc990`, entrato in `dev_release2` con
  `4447814ed`.

## P · Transazioni e Bulk (42)

Dettagli: [piano della 42](42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md) e 38, sezione «P · Costo medio e
impostazioni». C-46…C-48 sono nel treno 37. Righe mandate da P l'11/10 e trascritte dal coordinatore; P-5 è passata nella
sezione T, e P-7 (chiudere le issue #32 e #35) è un compito del rilascio, non di dopo.

- **P-2 · Anteprima WAC: etichetta sbagliata per le righe di split e ramo `add_at_wac` morto** — basso; P, archivio
  della 30 (09/10). Dettagli: [38](38_postReleaseBacklog/README.md), sezione «P · Costo medio e impostazioni», P-2.
- ✅ **P-3 · Contributo per posizione: dividendi e costi senza cambio esclusi senza segnale** — chiusa da F nel treno 42
  (B14 di I, `c04e44ff5`). Era: basso; P, archivio della 30 (09/10). Dettagli: idem, P-3.
- ✅ **P-4 · Fuso orario: verificare il database IANA nell'immagine Docker** — basso; P, archivio della 30 (09/10).
  Dettagli: idem, P-4.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): CP7a di H, verificato in un container sulla stessa base
  (`python:3.13-slim` non ha `tzdata-legacy`: `Asia/Calcutta` e `US/Eastern` non si risolvono), poi `tzdata` e
  `tzdata-legacy` via apt nell'immagine finale, commit `2e2d7ee70`, entrato in `dev_release2` con `744f5a0ee`. La prova
  a runtime dell'immagine intera resta aperta in CP7a (piano H, §14 «CP7a»).
- **P-8 · `tx-clone.spec.ts`: commento di testa superato** — minimo; P, archivio della 30 (09/10). Dettagli: idem, P-8.
- **P-9 · Black: riformattare `test_portfolio_api.py` e `test_portfolio_wac.py`** — minimo; P, archivio della 30
  (09/10). Dettagli: idem, P-9.
- ✅ **P-10 · `MISSING_COST_BASIS` raggiungibile dall'app riclassificando uno SPLIT** — basso, serve una decisione; P,
  analisi della 39 (09/10). Dettagli: idem, P-10.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): decisione D-J2 del developer (A, punto 27): il cambio di
  tipo di uno SPLIT con rettifiche legate senza costo è rifiutato con un messaggio tradotto; con un costo, anche 0,
  passa. CP-14a di J, commit `475bb9270` (entrato in `dev_release2` con `03101ddad`); il messaggio tradotto, F5,
  `8452e5e5d` (entrato con `b6b615c3d`); il rifiuto che fallisce chiuso, X-R47b, `1b6d65da7` (entrato con
  `952c68cd5`); la doc, `469e9f6b8` (entrato con `647efcc28`).
- **P-12 · Griglia del Bulk: le quantità oltre 15 cifre significative appaiono arrotondate** — basso; test-author di
  P, C-46 (11/10). Dettagli: [piano della 42](42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md), sezione
  «7. Seguito: C-46, C-47, C-48».
- **P-13 · Percentuali non localizzate nei componenti condivisi della Dashboard** — basso; P, mini-lotto dell'audit di
  M (11/10). `KpiSection`: 7 siti con `formatPercent` senza `locale`, visibili anche nella pagina del broker. Dettagli:
  [piano della 42](42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md), sezione «8. Mini-lotto dai reperti
  dell'audit di M», 8.1.
- **P-14 · es: «broker» senza accento in altre 46 chiavi** — basso; P (11/10); i nomi propri come Interactive Brokers
  restano. Dettagli: idem, 8.2.
- **P-15 · Altre etichette inglesi scritte nel codice** — basso; test-author di P (11/10). `DataEditor`: «Date», i
  contatori «modified/deleted/new», un `aria-label`, «Reset layout»; `BrokerSharingPanel:832`: «max». Dettagli: idem,
  8.1 e 8.
  - ✅ **Parte di W chiusa il 15/10** (lotto K1 della 1.3, `532a1fd9c`; in `dev_release2` con `d915c869f`):
    i contatori e l'`aria-label` della levetta delle righe vecchie in `DataEditor`, «Help» e «Close» di
    `DataImportModal` (W-B8). «Date» era già `common.date`. Restano «Reset layout»
    (`components/table/ColumnVisibilityToggle.svelte:177`) e «max» (`BrokerSharingPanel:832`), a Y (decisione Q6 del
    piano 04).
  - Stato (19/10): fatta la parte di W (sopra); «Reset layout» (`components/table/ColumnVisibilityToggle.svelte:167`) e
    «max» (`features/brokers/BrokerSharingPanel.svelte:827`) sono ancora scritti in inglese in `dev_release2`, e
    restano a Y.

## T · Matematica finanziaria e riordino (43)

Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md). Prima della 1.2: B1–B3 (B1, B2 e B3a nel treno 37, B3b nel checkpoint successivo), PL3, BU1, T-1
(dopo F) e FE1, perché l'onboarding è libero dall'11/10. Righe scritte da T dal riallineamento al treno 37; le voci B9 e
P-5 le ha trascritte il coordinatore. Dopo la 1.2:

**Difetti e motore**

- ✅ **T-B4 · La data del lotto più vecchio dopo uno split** — medio; T, 11/10. Va con U6. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione
  «7.1 Lotti, passi, peso, quando».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): MF-H, con la decisione D-MF2 (l'arrivo al broker): la
  finestra di detenzione nella casa (`financial_math/holding_window.py`), dove uno split riscala i lotti aperti e ne
  tiene le date, commit `e5d287287`, entrato in `dev_release2` con `bcc644491`.
- ✅ **T-B5 · Il P&L di una chiusura FIFO mescola le valute** (chiusa 16/10 dal coordinatore: CP-7a di J, decisione 26, treno 107) — peso da stimare, serve una decisione; T, 11/10. Se un lotto
  è aperto e chiuso in valute diverse, `_close_position_piece` (`fifo_lot_engine.py:905-940`) sottrae il prezzo del
  lotto da quello di vendita senza convertirli. Limite già documentato nella pagina dev del servizio dei lotti.
  Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3a — Lotti, niente ripiego sull'importo non convertito».
- ✅ **T-B6 · Lotti: la fonte del prezzo di riferimento dice «exact» anche quando il prezzo convertito manca** (chiusa 16/10 dal coordinatore: CP-7a di J, treno 107) — minimo;
  T, 11/10, dalla sonda di B3b. Senza cambio `reference_unit_price` è `None`, ma `reference_price_source` resta
  `exact`, e l'AI Export lo copia. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3b», «Sonda».
- ✅ **T-B7 · AI Export: segnalare le colonne tolte perché nulle in ogni riga, in tutti i componenti** — medio-basso;
  coordinatore, 11/10. Il renderer compatto toglie una colonna nulla in ogni riga; solo i lotti ne hanno la traccia
  (`unavailable_amount_lot_count`, B3b). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3b», «Scoperte sul renderer dell'AI Export».
  ✅ **Fatto da J il 17/10** (`7184cb123`, dev `36d24e7d2`): le colonne con un `null` esplicito in ogni riga sono nominate dopo la tabella (`omitted_null_columns=…`), le etichette passano a `_v2`. Seguito: J-54 (i campi in cui `null` vuol dire «nessuno»).

- ✅ **T-B8 · Sintesi FIFO dell'AI Export: valore aperto e P&L non realizzato sommano insiemi di lotti diversi** — basso;
  T, 11/10, dal docs-writer di B3b. Ognuna delle due somme prende i lotti aperti in cui quel campo è noto, mentre i
  conteggi della copertura contano i lotti in cui sono noti entrambi; con il costo di un lotto ignoto (B3b) le due
  somme non coprono più gli stessi lotti. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3b», «Passo 6».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): MF-E1 (la parte E1b), le due somme sugli stessi lotti, quelli
  in cui sono noti entrambi, con `portfolio/broker.fifo_summary` a v3, commit `570af3d09`, entrato in `dev_release2`
  con `e43dfae68`. E2 di MF, i corti nella storia di performance, è un'altra cosa e aspetta il developer.
- ✅ **T-B9 · AI Export: un residuo reale sotto l'unità minima della valuta si stampa `0` accanto a `reconciled` falso** —
  minimo; T, 12/10, dal docs-writer di C-53. Il renderer stampa `0` un residuo monetario più piccolo dell'unità minima
  (`monetary_residuals_zeroed`); dopo C-53 `reconciled` tollera solo `CONVERSION_DUST` (1e-9), quindi un residuo fra le
  due soglie si contraddirebbe. Improbabile: il riepilogo chiude la scomposizione per costruzione. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «C-53 — implementazione».
  ✅ **Chiusa come verificata, senza codice** (J, 17/10; piano 05, «T-B9»): il residuo è solo arrotondamento del contesto `Decimal` a 28 cifre (~1e-27 × gli importi), `other_result` viene dagli stessi `Decimal` del riepilogo; il caso `1E-24` è già fissato da `test_engine_closing_term_reconciles_despite_decimal_rounding`.

**Unificazioni della matematica comune (parte 1)**

- **T-U1 · Un piano dei cambi unico: mancanti e provenienza** — medio; T, 11/10. Esclude i giri del portafoglio, che
  ha chiuso F (O2; X5 sui movimenti): le 4 conversioni dei prezzi di X5 restano qui e in U5. Comprende il servizio
  dei lotti, che con FEE/TAX presenti converte ogni BUY/SELL come peso possibile e può segnalare il cambio di un trade
  che nessun pool legge (docs-writer di B3b). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.3» e «7.1».
- ✅ **T-U2 · Frazionamenti: caricamento, validazione, rapporto cumulato** — medio-basso; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezioni «2.7» e «7.1».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): MF-I, un caricatore solo in `financial_math/splits.py`
  (`load_split_links`, `is_valid_split_ratio`, `split_linked_ids`) per motore, lotti, Yield on Cost, repliche del WAC,
  sommario del broker e costo Auto: I1 nel commit `30b464272` (entrato in `dev_release2` con `8d244d1c6`), I2 nel
  commit `291423296` (entrato con `3741b95b0`). Il rapporto cumulato resta `_cumulative_split_ratio`, una funzione sola,
  in `financial_math/portfolio/daily_state.py`, già nella casa.
- **T-U3 · Le quote di proprietà in un solo modulo** — basso nel servizio, medio nell'AI Export; T, 11/10. Esclude i
  giri del portafoglio di F; comprende B9 di I, qui sotto. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.6» e «7.1».
- **B9 (di I) · L'AI Export dalla pagina di un broker, per Viewer ed Editor** — medio-basso, in U3; developer, 11/10.
  Nel patrimonio lo 0 di Viewer ed Editor è giusto (la Dashboard passa solo i broker propri con quota > 0); dalla
  pagina di un broker solo visto le cifre del report sono piene e il turnover è moltiplicato per la quota grezza 0
  (`broker_cost_efficiency.py:150-157`); in più l'`abs` sul reddito (`portfolio_income.py:379`). La cura: una regola
  sola per export, quella della pagina da cui parte. Dettagli: [piano della 41](41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md),
  §14 B9 e §17.6.
- **T-U4 · Rendimenti e annualizzazione** — medio; T, 11/10. Comprende R1 (il ribasamento scritto due volte) e la
  riprova R2, il rendimento netto, il 365 osservato, la parità fra rischio e segnali, P1 (il P&L di periodo del servizio) e C1 di I
  (`_wac_qualifying_txs`, il costo unitario dell'anteprima). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.1» e «7.1».
  Stato (19/10): fatta da J la parte di CP-4, cioè R1/R2, R3, R5, P1 e C1 (`58f8e3967`, entrato in `dev_release2` con
  `322d55042`; `70bc2d290`, con `a180ea0b7`; `4ea6cc61e`, con `40f44f364`), e da MF la parte R6–R10 (MF-D, entrato
  con `8d244d1c6`, `aca75c7ca`, `482343eb3` e `c2feaf3e4`); resta R11, a J: il test di parità fra le versioni pandas di
  volatilità e Sharpe mobili (`signals/risk_adapters.py`) e `risk/metrics.py`.
- **T-U5 · Prezzo del giorno e valorizzazione** — medio-alto; T, 11/10. Comprende R4 (il P&L di periodo della posizione),
  con B8 di I. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.2» e «7.1».
- ✅ **T-U6 · Finestre di detenzione dal FIFO** — medio; T, 11/10. Comprende L1 e L2 di I e T-B4. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezioni «2.5» e «7.1».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): MF-H, L1 e L2 nella casa,
  `financial_math/holding_window.py` (`oldest_open_lot_date`, `closed_position_window`), con T-B4, commit `e5d287287`,
  entrato in `dev_release2` con `bcc644491`.
- **T-U7 · Pesi e concentrazione** — medio; T, 11/10. Comprende W1 (l'allocazione senza il valore in viaggio). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.8» e «7.1».
- ✅ **T-U8 · Il frontend solo di presentazione: Δ, KPI, lotti** — medio-alto; T, 11/10. **Chiusa il 17/10 (coordinatore)**: V11 e P5 di Y entrati (dev `d4ecfb692`); il modale della custodia legge `original_cost`; `MeasureSignal.ts`, `CompoundSignal.ts`, `LinearSignal.ts` e `SineSignal.ts` portano `@financial-math-exception` e il gate li elenca. Resta la Δ dell'intervallo, che è X-R59 (MF). **Stato precedente, 17/10 (coordinatore)**: con Y12a, MF-P e il lotto R17/W8/P4 di Y (dev `1565b6bbb`) restano solo V11 e P5, legati a MF-E e a CP-7b di J; la dichiarazione delle misure è coperta per `MeasureSignal.ts` da CP-14b. Comprende il valore d'apertura
  che il modale della custodia ricalcola come quantità × prezzo d'apertura (`LotCustodyModal.svelte`) invece di
  leggere `original_cost`, trovato in B3b, e la dichiarazione nel codice delle misure interattive che la regola
  ammette (`MeasureSignal.ts`, `CompoundSignal.ts`, `LinearSignal.ts`, `SineSignal.ts`; docs-writer di T-1). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «7.1».
- **T-U9 · L'AI Export dalle case comuni** — medio; T, 11/10. Comprende il `reason_code` di `broker.concentration_comparison`,
  trovato con C-55 (12/10): `broker_summary_unavailable` (`broker_concentration_context.py:390`) esce anche quando il
  riepilogo del broker c'è ma non ha posizioni, mai avute o tutte chiuse. Il messaggio è esatto, il codice no; cambiarlo
  cambia il contratto, quindi la v2. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «7.1» e «C-55 — analisi».
- ✅ **T-U10 · Interessi e convenzioni di calendario (`interest.py`)** — basso-medio; T, 11/10, decisione D-8. Dettagli:
  [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.10» e «7.1».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): CP-14a di J, convenzioni di calendario e interesse
  semplice in `financial_math/interest.py`, una sola camminata dei giorni nel provider Scheduled Investment e una rete
  dorata sui valori di prima, commit `ec8a0b31e`, entrato in `dev_release2` con `03101ddad`.
- ✅ **T-D9 · MeasureSignal: la soglia dei 30 giorni sull'annualizzato** — **chiusa il 17/10 da CP-14b di J** (dev `4111239a7`): `MIN_ANNUALIZATION_DAYS = 30` in `MeasureSignal.ts`, `—` sotto i 30 giorni e su un inizio a 0 (N65). Era: minimo; T, 11/10, decisione D-9. Dettagli:
  [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «2.1», riga R18.
- **P-5 (di P) · Migrare `roi_utils` e `valuation_utils` in `financial_math`** — basso, refactor; decisione D1 del
  developer, registrata da P (09/10). Coperta da T-1 e BU1 se entrano nella 1.2. Dettagli:
  [38](38_postReleaseBacklog/README.md), sezione «P · Costo medio e impostazioni», P-5.

**Code reordering (parte 2)**

- ✅ **T-PL1 · Il runtime dei segnali in `services/signals/`, fine del ciclo rischio↔segnali** — medio; T, 11/10.
  Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): CP-10b e CP-10c di J. Il runtime è in `services/signals/`,
  con `base.py` fuori dai plugin e `risk_adapters.py` al posto di `risk/signal_helpers.py`, poi `signals/service.py`
  tagliato per tema; il rischio non importa più i segnali, e i segnali leggono solo `risk.metrics`. Commit `3aa2e412e`
  (entrato in `dev_release2` con `b36e3873f`) e `539351fd9` (entrato con `69e1c58e9`).
- ✅ **T-PL2 · Un registro per famiglia di plugin** — medio; T, 11/10, decisione D-P1. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): CP1 di X, i registri nei pacchetti di famiglia
  (`services/{assets,fx,brim,signals,risk}/registry.py`), commit `9426c1bae`, entrato in `dev_release2` con
  `64a5a3fe7`.
- ✅ **T-PL4 · `fx.py` diventa `services/fx/`** — medio; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): X, `services/fx.py` spostato in `services/fx/` nel CP1
  (`9426c1bae`, entrato in `dev_release2` con `64a5a3fe7`), poi tagliato per tema, col router dei cambi, nel CP3
  (`b991d5e26`, entrato con `8000aba5a`).
- **T-PL5 · `brim_provider.py` diventa `services/brim/`** — medio-alto; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
  Stato (19/10): fatta la rinomina in `services/brim/` (W4 CP6, commit `548a0688d`, entrato in `dev_release2` con
  `155d9b050`); resta il taglio di `brim_provider.py` per tema (CP7 di W), non fatto: aspettava lo stesso commit del
  coordinatore di W3 (piano 04, §7).
- ✅ **T-PL6 · Asset: `base.py`, via lo shim `asset_source.py`** — medio-basso; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): X, via lo shim e il barile di `asset_sources/` nel CP2a
  (`4284c50f3`, entrato in `dev_release2` con `64a5a3fe7`), poi `services/assets/base.py` tagliato da `core.py` nel
  CP2b (`870c9956f`, entrato con `92b42d796`).
- **T-PL7 · Un router proprio per i segnali, con gli URL invariati** — medio-basso; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «P2.1».
- **T-P2.2 · I file grandi del backend, divisi per cuciture** — medio; T, 11/10. L'evaluator del PAC,
  `portfolio_service`, le transazioni, `broker_service`, `price_store`, i router, gli schemi. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «P2.2».
  Stato (19/10): fatti i tagli di sorgente, evaluator e schemi del PAC (CP-1 di J, `9a58157a4`, entrato in
  `dev_release2` con `e1fbc801f`), di transazioni e `broker_service` (W2, `97aa874a6`, con `998fd2701`), degli schemi
  delle transazioni (W7, `e28aad42f`, con `1cd7300f3`), di `price_store`, del router e degli schemi degli asset (CP2b di
  X, `870c9956f`, con `92b42d796`), del servizio e del router dei cambi (CP3 di X, `b991d5e26`, con `8000aba5a`), del
  servizio del rischio (CP-9a di J, `b6d45f026`, con `c4eeaef14`) e di quello dei segnali (CP-10c, `539351fd9`, con
  `69e1c58e9`); restano `portfolio_service` (CP-8 di J), `api/v1/brokers.py` (W3 di W, non fatto) e gli schemi di
  rischio, segnali e portafoglio (CP-9b/9c e CP-8 di J).
- **T-SG · I file sciolti in cima a `backend/app/services/`, raggruppati per dominio** — medio; T, 11/10; **dopo la
  1.2**, riconfermato dal developer il 12/10. Oggi sono 33 moduli.
  - Nascono dai lotti di sopra: `signals/` (T-PL1), `fx/` (T-PL4), `brim/` (T-PL5), `assets/` (T-PL6), `transactions/`,
    `portfolio/` e `brokers/` (T-P2.2).
  - Restano da spostare a parte i servizi piccoli:
    - `accounts/`: auth, utenti, impostazioni, impostazioni globali, onboarding, popup delle donazioni;
    - `platform/`: registri dei provider e dei container, sentinella delle date, soglie della qualità dei dati, backup;
    - `files/`: upload statici, anteprima dei file.
  - Prima la rinomina, poi il taglio (§4.2 del piano).
  - Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.2»,
    paragrafo «`services/` in cima ha 40 voci».
- **T-DI · I campi data nativi restano nella lingua del browser** — minimo, limite noto; T, 12/10 (analisi di M-18). Con
  M-18 numeri e date seguono la lingua della UI, ma un `<input type="date">` lo disegna il browser
  (`frontend/src/lib/components/risk/RiskAnalysisPanel.svelte:902,906`). Serve un selettore di date dell'app. Dettagli:
  [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «10», M-18.
- ✅ **T-BU1+BU2 · `utils/` del backend: sottocartelle per tipo di utility** — chiusa nella 1.2 da T: BU1 nel treno 50
  (`346b7e292`), BU2 nel treno 53 (`8dae5cc6e`). `utils/` resta la casa delle funzioni foglia (D-P7), con le
  sottocartelle `asset/`, `fx/` e `runtime/`; la precisione del DB è in `db/precision.py`. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezioni «P2.3», «D-P7» e «BU1/BU2».
- **T-FE2…FE11 · Il frontend a cartelle per funzionalità** — da basso ad alto; T, 11/10. FE8 dopo P; FE6 e FE7 dopo F.
  Comprende due cose trovate con FE1 e con le durate: la copia di `DELTA_PERIODS` nella pagina FX
  (`routes/(app)/fx/+page.svelte:159`) e l'albero di `developer/frontend/index.md`, che non ha `lib/features/`.
  Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.4».
- **T-TS1 · I test del backend specchiati sul codice** — alto, solo se lo si vuole (D-P5); T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «P2.5».
- **T-TP · `pyproject.toml`: `testpaths` punta a una cartella che non esiste** — minimo; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «P2.5».
- **T-W1 · devWiki: i percorsi vecchi nella prosa, dopo T-1** — basso; T, con l'historian, 12/10. T-1 ha aggiornato solo
  le 58 righe «Source files»; restano 50 menzioni in 28 file, fra cui le sezioni «Location» di
  `entities/portfolio-engine.md` e `entities/fifo-lot-engine.md`, `F-100`, `F-058`, `F-056`, `fifo-runtime-decision`,
  `financial-math-single-average-cost.md:200`, e `domains/calculations.md:70`, che chiama «FIFO engine»
  `transaction_service.py`. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B4 — devWiki».
- ✅ **T-R1 · Nomi privati attraverso il confine dello strato** — minimo; T, 12/10. `risk/service.py:439` chiama
  `PortfolioService._get_configured_fx_pair_sets()`, che avvolge `load_configured_fx_pair_sets`
  (`financial_math/portfolio/data_quality.py`); `portfolio_service` importa `_compute_tx_fingerprint` dal motore. Il
  PAC l'ha già fatto in T-1 (`QUANTITY_DUST_THRESHOLD` pubblico). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «B2 — motore del portafoglio in sei moduli».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore), in due metà: il rischio legge le coppie configurate dalla
  casa (`load_configured_fx_pair_sets`) nel CP-9a di J, commit `b6d45f026` (entrato in `dev_release2` con
  `c4eeaef14`); `compute_tx_fingerprint` del motore è pubblico dal lotto MF-A, commit `9a1d57bfa` (entrato con
  `536501541`).
- **T-ST · I giorni «stale»: un plurale vero e l'abbreviazione tradotta** — minimo; T, 12/10 (M-18 CP2, scelta (A) del
  coordinatore). `chart.tooltip.stale` ha lo stesso `{days}` nelle 4 lingue ma nessun plurale ICU: «day(s)»,
  «giorno/i», «jour(s)», «día(s)». La leggono i tooltip di `CandlestickChart.svelte:520` e `LineChart.svelte:777` e,
  dal CP2, il titolo del badge di `DataEditor.svelte:180`. Il badge visibile `⚠️ {N}d` ha una «d» inglese (it «g», fr
  «j»); l'unica chiave con l'abbreviazione è `transactions.fxInfo.stale` («non agg. {days}g»), che aggiunge una parola.
  Da fare: il plurale ICU nei 4 cataloghi, con testi diversi per lingua (la cache dei formatter di svelte-i18n), e
  un'abbreviazione tradotta per il badge. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «10», M-18 CP2.
- **T-ICU · I numeri dentro i messaggi del catalogo seguono la lingua senza regione** — minimo, limite noto; T, 12/10
  (M-18 CP2). Con M-18 ogni cifra passa da `uiLocale()`, ma le cifre che svelte-i18n formatta dentro un messaggio ICU
  usano il suo `$locale`, cioè la lingua senza regione: l'unico `{covered, number, percent}`
  (`risk.warnings.historical_replay_mostly_excluded`) e il `#` dei 74 plurali. Si vede solo con un browser che porta
  una regione diversa da quella di default: per esempio con un browser es-MX il `#` di un plurale scrive `1234` dove il
  resto della pagina scrive `1,234`, e l'unico percento `13 %` invece di `13%`. Nei cataloghi
  non ci sono date ICU. Due strade: passare a svelte-i18n la locale completa (`it-CH` ricade sul catalogo `it`) senza
  cambiare chi legge `$locale` per i link e i testi, oppure formattare le cifre prima di passarle al messaggio, come fa
  già `problemCount`. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione
  «10», M-18 CP2.
- ✅ **T-EN1 · Testo inglese scritto a mano nei tooltip del grafico dei prezzi** — chiusa nella 1.2 da T, checkpoint
  T-EN del 13/10, con le chiavi `chart.tooltip.{originalValue,fxRateDate,fxDaysBack}` e `assets.probe.points` (il
  plurale: «1 point»). Il commit lo scrive il coordinatore all'integrazione. Era: minimo; T, 12/10 (trovato con M-18).
  `PriceChartFull.svelte:785-788` scrive «orig.», «(Nd back)» e «fx @» in ogni lingua; `ProviderAssignmentSection.svelte:354`
  scrive «points» nel dettaglio della sonda dello storico (la cifra accanto segue la lingua dal CP3b). Servono chiavi
  nuove: dopo la
  divisione dei cataloghi di U. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «10», M-18 CP3.
- ✅ **T-EN2 · Le etichette dei segnali what-if sono in inglese, con cifre grezze** — chiusa nella 1.2 da T,
  checkpoint T-EN del 13/10: le chiavi `chartSettings.signals.{linear,compound,sine}Label`, le cifre da
  `formatPercent` e `formatFixed`. Per decisione del coordinatore include anche le unità dell'editor dei parametri
  («%/yr», «days»), con `signals.units.percentPerYear`. Il commit lo scrive il coordinatore all'integrazione. Era:
  minimo; T, 12/10 (trovato con M-18).
  `LinearSignal.ts:74-75`, `CompoundSignal.ts:96-97` e `SineSignal.ts:87` scrivono «Linear 5%/yr +2%», «Compound …» e
  «Sine ±…% / …d»: parole inglesi e numeri stampati grezzi (`${rate}%`) in ogni lingua. Servono chiavi, e le cifre da
  `formatPercent`/`formatFixed`. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «10», M-18 CP3.
- **T-COL · L'ordine dei nomi segue la collazione del browser** — minimo; T, 12/10 (trovato con M-18). Nessun chiamante
  passa una locale a `nameComparator` (`risk/correlationHelpers.ts:252`): `assetSetTable.ts:49`,
  `CorrelationHeatmap.svelte:140`, `LabAssetPicker.svelte:46`. Così i nomi si ordinano con le regole del browser, non
  con quelle della lingua dell'interfaccia. Non è una cifra: è testo, quindi conta la lingua (`$currentLanguage`), non
  `uiLocale()`. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «10»,
  M-18 CP3.
- **T-DEAD · Codice morto trovato con M-18** — minimo; T, 12/10. Il ramo `relative` di `formatCellDate`
  (`components/table/dataTableLogic.ts:335-342`) scrive «Nd ago» in inglese, ma nessuna colonna usa
  `format: 'relative'` (il tipo è in `types.ts:46`). `formatDate` in `routes/(app)/files/+page.svelte:685` non viene
  mai chiamata. Da togliere, oppure, se una colonna adotta `relative`, da scrivere con `Intl.RelativeTimeFormat` nella
  lingua dell'interfaccia. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «10», M-18 CP3.
- ✅ **T-ISO · Le date d'osservazione restano ISO nei tooltip del grafico dei prezzi e nella sonda** — chiusa nella
  1.2 da T, checkpoint T-ISO + T-FB del 13/10: il coordinatore l'ha anticipata, perché la riga 🔄 «Numbers and dates
  follow the interface language everywhere» promette anche i tooltip. Le date passano da `formatDay`
  (`utils/core/formatAxisDate.ts`), nella lingua dell'interfaccia. Il lotto copre anche le intestazioni dei tooltip di
  `PriceChartFull`, `CandlestickChart` e `LineChart`, e la tabella che compare al passaggio sulla sonda
  (`providerProbe.ts`). Il `date_range` si legge senza cambiare l'API, perché il backend lo scrive sempre
  `inizio → fine`. Il commit lo scrive il coordinatore all'integrazione. Era: basso; T, 13/10 (trovato con T-EN1).
  Con M-18 le date seguono la lingua dell'interfaccia, ma alcune date d'osservazione si leggevano ancora `2024-03-01`.
  - In `components/charts/PriceChartFull.svelte`: il segnaposto `{date}` di `chart.tooltip.valueAt` (`:1017`, `:1020`,
    `:1029`), le righe `↩` (`:1018`) e `💱` (`:1023`) del riferimento, la data dell'evento nei periodi aggregati
    (`:778`) e quella del cambio (`chart.tooltip.fxRateDate`, `:789`).
  - In `components/assets/ProviderAssignmentSection.svelte`: la data del prezzo corrente (`:335`) e l'intervallo dello
    storico, `date_range`, che arriva dal backend come una stringa sola (`:355`).

  Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «T-EN — analisi» e
  «T-ISO + T-FB».

  **Riparazione dopo il treno 88**: il test del ciclo di vita dell'AssetModal riconosceva la riga dello storico dal
  `date_range` grezzo nel testo, e ha dato 8 rossi in `component-unit`. Le righe della sonda pubblicano ora
  `data-operation` (`current_price`, `history`, `probe`). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «T-ISO, la riparazione di `component-unit`».
- ✅ **T-FB · I ripieghi inglesi dei segnali di confronto** — chiusa nella 1.2 da T, checkpoint T-ISO + T-FB del 13/10,
  per decisione del coordinatore. «Asset #N» ha ora una chiave sola, `chartSettings.signals.assetFallback`. Prima
  era `fxDetail.assetFallback`, che è stata tolta. I segnali la leggono con `ChartSignal.text`, le due pagine con `$t`.
  «Asset» e «FX Pair» vengono dal catalogo (`common.asset`, `chartSettings.signals.fxPair`). Nello stesso lotto sono
  entrati i tre errori della pagina dell'asset («Asset #N not found», «Failed to load asset info», «Failed to load
  prices»), ora chiavi `assetDetail.*`, e «Other» nelle regole dello stress in it, fr ed es. Il commit lo scrive il
  coordinatore all'integrazione. Era: minimo; T, 13/10 (trovato con T-EN2).
  Se l'asset di confronto non c'era più, l'etichetta diceva `Asset #N` o `Asset`
  (`charts/signals/AssetComparisonSignal.ts:173-174`, e `routes/(app)/assets/[id]/+page.svelte:690`, `:871`, `:895`,
  `:1004`, `:1274`). Una coppia vuota diceva `FX Pair` (`charts/signals/FxPairSignal.ts:94`). Si vedeva solo con una
  configurazione salvata che punta a un asset cancellato. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezioni «T-EN — analisi» e «T-ISO + T-FB».
- **T-CAT · Due rese delle categorie: tipi, settori e paesi** — minimo; T, 13/10 (trovato con T-SHK). Lo shock del
  rischio scrive i bucket con `components/risk/stressBucketLabel.ts`, il PAC le categorie di esposizione con
  `exposureCategoryLabel` (`features/tools/pac-allocator/planner/categoryLabels.svelte.ts`). Le regole sono le stesse:
  tipo tradotto, settore con emoji, paese con bandiera, codice sconosciuto scritto com'è. Da fare: una funzione sola, in
  un modulo condiviso fuori dalle due feature. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «T-SHK — analisi».
- **T-GRP · I gruppi geografici dell'host restano id grezzi nella tabella dello shock** — minimo; T, 13/10 (trovato con
  T-SHK). `stressBucketLabel` dà un nome solo a `european_union`. Un gruppo definito dall'host nel catalogo degli scenari
  porta già i suoi nomi per lingua (`geography_groups`), ma la tabella non li legge. Inoltre, se un impatto avesse i pesi
  senza `bucket_audit`, ogni bucket avrebbe peso 0 e la tabella sparirebbe; oggi il backend lo manda sempre. Dettagli:
  [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «T-SHK + T-CL».
- ✅ **T-EVW · Il grafico dei prezzi forse perde gli eventi alla risoluzione settimanale o mensile** — chiusa nella 1.2:
  è la R-5 del lotto 51 di I, confermata a runtime da V e curata da I in `1acd1bf10`, treno 91. Il tooltip dello stesso
  punto, che diceva ancora «value at» la fine teorica del periodo, lo allinea T nel checkpoint «Il tooltip del periodo
  in corso». Dettagli: [piano della 51](51_narrowFitFixes/plan-phase00NarrowFitFixes.prompt.md), sezione «R-5», e
  [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «Il tooltip del periodo in
  corso». Era: da verificare; T, 13/10 (letto nel codice da test-author durante T-ISO).
  Il marcatore stava sulla fine teorica del periodo, il punto aggregato sull'ultimo dato: nell'ultimo periodo, ancora
  aperto, l'evento non trovava il suo punto e non si disegnava.

La voce di `TODO_FUTURI.md` sul riordino del codice si cancella a mano a mano.

## M · Traduzioni, galleria e pipeline (27)

Dettagli: [piani della 27](27_releaseImages/); per M-2…M-7 il [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
sezioni «5.9d» e «After 1.2». Righe M-4…M-7 mandate da M l'11/10, trascritte dal coordinatore.

- **M-1 · Immagini solo amd64** — [piano ReleaseGallery](27_releaseImages/plan-phase00ReleaseGallery.prompt.md), riga 209.
- **M-2 · Un passo deterministico della pipeline per i percorsi `../` delle traduzioni** — basso: solo se il caso si
  ripete (decisione del coordinatore, 11/10). I prompt (`step3_user.txt:16`, `step4`/`step5:28`) chiedono di copiare
  `src`/`href` alla lettera: ritradurre le 4 pagine con immagini locali in HTML grezzo rimette la copia, che
  `html-asset-depth` segnala.
- **M-3 · L'audit degli stamp come opzione di `translate-validate`** — basso; insieme alla scansione delle coppie
  mascherate (i tre script stanno fuori dal repo).
- ✅ **M-4 · Lo spazio insecabile della tipografia francese** — nella 1.2, decisione del developer dell'11/10: un hook
  di build, `mkdocs_src/hooks/fr_typography.py`, nel lotto 15 di M (checkpoint B). Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «6.1».
- **M-5 · La virgola decimale nelle formule** — basso; M, 11/10. Per la 1.2 restano col punto (decisione del developer
  dell'11/10).
- **M-6 · Il `../` di `srcset` e `poster` in `html-attr-mismatch`** — minimo; docs-writer di M, 11/10.
- **M-7 · La guida dei plugin BRIM e le favicon locali** — minimo; docs-writer di M, 11/10. Pagina EN: la prende chi
  riscrive la guida dei plugin BRIM.
- **M-8 · Le etichette della UI nelle pagine di teoria** — basso; M, 11/10: il 5.4 ha lasciato fuori 248 righe nelle
  pagine di teoria (scansione finale), dove il grassetto segna concetti e non citazioni. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «6.3».
- **M-9 · Il confronto etichette–catalogo come controllo di `translate-validate`** — basso; M, 11/10: oggi è uno script
  fuori dal repo (`b15_ui_label_scan.py`) che appaia per posizione grassetti e corsivi con il catalogo EN. Non vede i
  link, il testo semplice, le didascalie e gli alt: «Rendimento rolling» / «Rentabilidad móvil» (43 occorrenze, lotto 16)
  sono emersi a mano. Un controllo vero dovrebbe cercare anche i nomi delle modalità e dei pulsanti nel testo. Dettagli:
  [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezioni «6.3» e «7.2».
- **M-10 · I nomi dei provider nelle traduzioni** — minimo; M, 11/10: «Scheduled Investment» è tradotto nel nav e nei
  titoli delle pagine («Investimento Programmato», «Investissement Programmé», «Inversión Programada») e resta in inglese
  nelle tabelle (12/11/11 occorrenze); l'app mostra il nome del backend, in inglese. Scegliere una forma sola. Dettagli:
  [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «7.3».
- **M-11 · Il registro nei prompt della pipeline** — basso; M, 11/10: i prompt (`prompts/short_article/`) non dicono
  a chi si rivolge la guida (es «tú», it «tu», fr «vous»): il lotto 16 ha tolto 112 forme di «usted» dalle pagine
  spagnole, e una run nuova potrebbe rimetterle. Una regola nei prompt e un controllo che confronti «you/your»
  dell'inglese con le forme della traduzione. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «7.4».
- **M-12 · La riga «FX on cash» negli scatti della galleria** — basso; M, 12/10: la vista Performance della galleria
  riproduce `frontend/e2e/dashboard-report.json`, una cattura reale normalizzata senza liquidità in valuta estera, quindi la
  riga di F non compare. Serve una cattura nuova dai dati del developer (regola 12: `dev.py mkdocs
  normalize-dashboard-fixture`), con un broker che tenga liquidità in un'altra valuta. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «9.3».
- ✅ **M-13 · Le sonde della galleria che ignorano il timeout** — nella 1.2, lotto 19 di M (12/10, decisione del
  coordinatore). Delle 76 sonde `isVisible({timeout})` di `gallery.spec.ts`, 48 diventano `appears()`: 19 stanno davanti a
  uno scatto, 29 lo preparano. Le 3 `isEnabled({timeout})` del pulsante di analisi diventano `becomesEnabled()`, nuova in
  `e2e/fixtures/probe.ts`. Il preludio del wizard di import aspetta i `data-busy` dei passi 1, 2 e 4. Le 28 sonde rimaste
  falliscono in modo visibile, oppure puliscono dopo lo scatto. Gli 8 scatti mancati escono, e gli scenari toccati sono
  16/16. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «10».
- ✅ **M-14 · I numeri degli scatti nella lingua del browser** — nella 1.2, lotto 20 di M (12/10, decisione del
  developer). Gli scatti di ogni lingua li fa un browser di quella lingua: en-US, it-IT, fr-FR, es-ES. La locale si imposta
  con `Emulation.setLocaleOverride` dalla sessione CDP del test (`e2e/fixtures/galleryLocale.ts`), in testa a ogni ciclo di
  lingua e prima che la pagina venga disegnata. I 13 test che fotografano una pagina preparata una volta sola la
  ridisegnano per lingua. Una guardia fa fallire lo scatto se la pagina è nata con un'altra locale. Galleria completa: 250
  passati, 1 saltato per scelta, 1 rosso. Il rosso era un cambio di rete della macchina (Tailscale), e lo stesso test,
  ripetuto 3 volte da solo, è verde. Restano col punto i numeri scritti con `toFixed` (M-18). Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «11».
- **M-15 · Le sonde della galleria che dovrebbero essere `expect`** — basso; M (test-author), 12/10. Il lotto 19 ha messo
  `appears()`, che è opzionale, anche dove il componente rende sempre l'elemento sul percorso del test. Sono, con le righe
  di `7b3c2b5ab`: `selectTransactionType` (2603, 2608), le viste tabella (4192, 4675), la riga del file nel wizard (3281,
  3352, 5612), lo sblocco della cache (1969), la modifica del broker (4108), la ricerca asset (4702) e i preset di data
  (909, 911, 921). Lì un `expect(...).toBeVisible()` trasformerebbe uno scatto mancato in un rosso (regola 6). Restano
  anche l'attesa a tempo dello scatto del passo 2 del wizard (3236), che il `data-busy` del passo potrebbe sostituire; le 7
  sonde della classe C, che oggi falliscono in modo visibile ma sotto carico possono diventare instabili; e lo stesso
  difetto fuori dalla galleria, in `transactions/tx-picker-pagination.spec.ts:161` (`isEnabled({timeout})`). Dettagli:
  [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezioni «10.0» e «10.1».
  - Stato (coordinatore, 14/10): la parte della galleria passa al workstream G (56), per decisione del developer (D4
    di G); se ne segue lo stato nella sezione «G · Gallery deterministica». Qui resta solo
    `transactions/tx-picker-pagination.spec.ts:161`.
- ✅ **M-16 · Il pulsante di avanzamento del wizard di import prima che arrivino i broker** — chiusa nella 1.2 da I,
  treno 48 (`3cd25af4f`): Avanti disabilitato finché la lista dei broker non arriva. Origine: test-author di M,
  12/10, fuori dal perimetro di M. Al passo 1 «Avanti: Seleziona File» resta abilitato mentre la lista dei broker si
  carica (`ImportWizardModal.svelte:5378`). `loadBrokerFiles()` legge la lista una volta sola, all'avvio (`:3512`). Se l'utente
  è più veloce della lista, il passo 2 apre tutti i pannelli dei broker chiusi (`:3530`), e i file ci sono ma non si
  vedono. Va disabilitato il pulsante finché i broker non arrivano, oppure il passo 2 deve ricalcolare i pannelli quando la
  lista arriva. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «10.2».
- **M-17 · Due testi della UI fissi in inglese** — basso; M, 12/10, fuori dal perimetro di M: li corregge I nella 1.2,
  dopo M-16 (decisione del coordinatore). `components/ui/date/DateRangePicker.svelte:1109` formatta il periodo scelto con
  la locale `'en'` fissa, quindi il selettore mostra i mesi in inglese in ogni lingua. `components/settings/tabs/GlobalSettingsTab.svelte:726`
  scrive «Last updated:» in inglese. Si chiude quando la correzione è nel target. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «11.0».
- **M-18 · I numeri scritti con `toFixed`** — medio; M, 12/10, fuori dal perimetro di M. Un numero composto con
  `toFixed(n)` non passa per nessuna locale e tiene il punto in ogni lingua: con M-14 gli importi degli scatti it/fr/es
  sono localizzati, questi numeri accanto no («+4788,01 €» ma «14.07%»). Sono le percentuali, circa 50 righe in una
  trentina di file (i rendimenti della dashboard, `components/dashboard/KpiSection.svelte:252-255,268`; i livelli di
  rischio, il PAC, i grafici, le card FX); le dimensioni dei file (`utils/files/upload.ts:56-59`, `formatBytes`: «9.2 KB»);
  le durate (`components/settings/SchedulerLogModal.svelte:235`, `utils/sync/syncHelpers.ts:110`: «18.7s»). Per le
  percentuali c'è già un formattatore (`utils/core/formatPercent.ts`). Il quando lo decide il coordinatore. Dettagli:
  [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezioni «11.2» e «11.3».
  Stato (19/10): T l'ha chiusa già nella 1.2, nei CP1–CP3b del 12/10 (fra gli altri `5b2aad5c4`, `ff7c96fd0`,
  `c17d39d5a` e `33cc145b5`, tutti in `dev_release2`): ogni cifra passa da `uiLocale()`. I 27 `toFixed` rimasti nel
  codice di produzione del frontend (controllati il 19/10) sono calcoli, valori d'input, larghezze CSS, chiavi di
  confronto o strumenti di sviluppo, nessuno è testo mostrato. Le voci nate da M-18 sono T-DI, T-ST, T-ICU, T-COL e
  T-DEAD, nella sezione T. Resta solo la spunta, da decidere.
- ✅ **M-19 · MathJax cercato nel posto sbagliato sulle pagine annidate** — nella 1.2, lotto 24 di M (12/10, decisione del
  coordinatore); c'era già nella 1.0 e nella 1.1. `mkdocs_src/docs/javascripts/lib-loader.js` cercava la copia locale di
  MathJax nella cartella della pagina: su ogni pagina annidata dava 404 e passava a jsdelivr, quindi senza internet le
  formule non si vedevano. Ora la base è l'indirizzo dello script stesso (`document.currentScript`), che MkDocs collega
  sempre alla radice del sito. Provato senza internet: 34 pagine su 34 (16 pagine con formule, 4 lingue, profondità da 2
  a 6, servite sotto `/mkdocs/` e sotto `/LibreFolio/`) caricano la copia locale e disegnano ogni formula. Il test e2e
  `front-utility docs-offline-math` è registrato nel lotto 28. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «15». **Seguito nel lotto 25** (12/10, decisione del coordinatore): la copia locale non aveva i font di MathJax,
  che il bundle cerca accanto a sé (`output/chtml/fonts/woff-v2/`). Con la correzione ogni pagina annidata prendeva lo
  script locale e disegnava le formule col font della pagina: lettere diritte, frazioni tagliate. Prima, online, quelle
  pagine passavano dalla CDN e i font c'erano. Anche il sito pubblico (1.1.0) serve lo script senza i font.
  `scripts/update_js_cache.py` ora scarica anche i 22 font che il bundle nomina (321 KB), con la stessa severità dello
  script; `mathjax.js` non chiama più `MathJax.typesetPromise()` prima che MathJax esista (un `TypeError` su ogni
  pagina). Dettagli: [piano del lotto 25](27_releaseImages/plan-phase00ChangelogTranslation.prompt.md), passo «8».
- ✅ **M-20 · Cinque pulsanti «copia» senza il ripiego per l'HTTP** — chiusa nella 1.2 da I, treno 72 (`65d20910e`).
  Era: basso; M (trovato da docs-writer), 12/10, fuori dal
  perimetro di M: assegnata a I nel lotto di rifinitura UI (decisione del coordinatore). Il browser non dà l'API degli appunti a una pagina in `http://` fuori da `localhost` (per esempio
  Tailscale in HTTP, o l'indirizzo di rete locale). `frontend/src/lib/utils/clipboard.ts:14` (`writeTextToClipboard`)
  ha il ripiego, ma cinque pulsanti chiamano `navigator.clipboard.writeText` direttamente e lì non copiano niente:
  `components/settings/tabs/AboutTab.svelte:242`, `components/brokers/lots/UnifiedLotsTable.svelte:391`,
  `components/auth/AskAdminModal.svelte:30` (un toast d'errore), `components/files/FilePreviewModal.svelte:377`,
  `components/assets/ProviderAssignmentSection.svelte:595`. La guida della sicurezza non dice più che l'app installabile
  è «l'unico motivo» per preferire HTTPS. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «14.7».
- **M-21 · La doc non si ricompila quando cambiano solo i suoi JavaScript o CSS** — basso; M, 12/10, fuori dal perimetro
  di M (`dev.py` è condiviso). `auto_build_mkdocs()` (`dev.py:2151-2171`, per `dev.py server`) e
  `_docker_ensure_assets_built()` (per `dev.py docker build`) ricompilano `mkdocs_src/site` solo se un `.md` è più nuovo
  di `site/index.html`. Una modifica al solo `lib-loader.js` o a `extra.css` lascia com'è un sito già compilato: un server
  o un'immagine costruiti in locale non la prendono senza `dev.py mkdocs build`. In CI il sito si compila da zero, quindi
  le immagini pubblicate non ne soffrono. Basterebbe guardare tutti i file sotto `mkdocs_src/docs/`. Lo stesso vale per
  i file che `dev.py cache js` scarica in `javascripts/vendor/` (dal lotto 25 anche i font di MathJax). Dettagli:
  [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «15.3».
- **M-22 · Mermaid si disegna solo con internet** — medio; M (trovato da test-author scrivendo lo spec di M-19), 12/10,
  dopo la 1.2 (decisione del coordinatore). `mkdocs_src/docs/javascripts/mermaid.mjs` importa Mermaid e il layout ELK
  solo da jsDelivr (`mermaid@11`, `@mermaid-js/layout-elk@0`), senza copia locale né ripiego. Senza internet, come
  nell'immagine completa, i diagrammi restano codice: 74 pagine (20 tradotte nelle 4 lingue e 54 della guida per
  sviluppatori, 134 file). Online ogni pagina chiama un server terzo, come MathJax prima di M-19. La strada è quella di
  MathJax: una copia in `vendor/` scaricata da `scripts/update_js_cache.py` e un caricatore con ripiego; resta da
  scegliere il formato da copiare, perché il modulo ESM di Mermaid ne carica altri. Dettagli:
  [piano del lotto 25](27_releaseImages/plan-phase00ChangelogTranslation.prompt.md), passo «8».
- ✅ **M-23 · Il changelog dell'app in francese senza spazi non separabili** — nella 1.2, M (lotto 27; assegnata a M
  dal coordinatore il 12/10, con `changelog.ts` e i suoi test). Le traduzioni tengono spazi normali, e per le pagine
  della documentazione li cambia in spazi non separabili `mkdocs_src/hooks/fr_typography.py`, al momento della build.
  Il modale del changelog legge `CHANGELOG.fr.md` senza MkDocs, quindi lì una riga poteva andare a capo prima di `;`
  `:` `?` `!` `%` o dentro « ». Ora `frontend/src/lib/features/changelog/changelog.ts` applica le stesse regole ai
  capitoli francesi (`typesetFrench`, `typesetFrenchMarkdown`), sul testo Markdown prima di tagliarlo in capitoli, fuori
  dal codice (inline e blocchi), dalle destinazioni dei link, dalle immagini, dall'HTML e dagli URL; i sorgenti restano
  come sono. L'HTML del modale coincide byte per byte con quello dell'hook sui 4 capitoli francesi; 136 test Vitest nuovi
  (`front-utility core-unit`). Dettagli: [piano del lotto 25](27_releaseImages/plan-phase00ChangelogTranslation.prompt.md),
  passo «11».
- **M-24 · La galleria non fissa `navigator.language`** — basso; M (sonda della preparazione di I5), 12/10, riga di
  backlog per decisione del coordinatore. Dal M-18 l'app scrive le cifre con `uiLocale()`, che legge
  `navigator.language`.
  - **Cosa fissa la galleria:** il locale del browser, con `Emulation.setLocaleOverride`
    (`frontend/e2e/fixtures/galleryLocale.ts`). Quell'override sposta solo il locale di ripiego di `Intl` e
    l'Accept-Language.
  - **Oggi:** nel Chromium headless della galleria `navigator.language` resta `en-US` (misurato su macOS con LANG C,
    it_IT ed en_GB), quindi gli scatti inglesi escono americani, come previsto.
  - **Il rischio:** con `dev.py mkdocs gallery --headed` o `--ui`, o dove Chromium risponde altrimenti (non misurato),
    gli scatti inglesi uscirebbero britannici, e nessun test diventerebbe rosso.
  - **La guardia:** il timbro di `stampDocumentLocale` registra anche `navigator.language`, ed `expectDrawnUnder`
    controlla che ne venga il locale atteso per ogni lingua.

  Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezioni «21.2» e «23».
- ✅ **M-25 · Un `dev.py docker build` locale può riusare un frontend con un'altra versione** — basso; M (lotto 34), 13/10.
  - **Perché:** `_docker_ensure_assets_built()` ricostruisce il frontend solo se `check_frontend_needs_build()` lo
    trova vecchio, e quel controllo guarda le date dei sorgenti, non la versione.
  - **L'effetto:** dopo un commit che non tocca il frontend, l'immagine locale riusa un bundle con la versione di un
    build precedente, anche `-dirty`, mentre `VERSION`, scritto alla fine, è nuovo.
  - **Fuori portata:** le immagini pubblicate non ne soffrono, perché la CI ricostruisce sempre il frontend con
    `LF_APP_VERSION`.
  - **La cura:** congelare la versione una volta all'inizio di `_docker_ensure_assets_built()`, passarla come
    `LF_APP_VERSION` al build del frontend, segnarla in `frontend/build/` accanto a `.build-debug`, e ricostruire
    quando è diversa.

  Dettagli: [piano ReleaseGallery](27_releaseImages/plan-phase00ReleaseGallery.prompt.md), passo «30».
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): CP7a di H, la cura proposta qui: la versione si congela una
  volta all'inizio di `_docker_ensure_assets_built()`, un frontend di un'altra versione, vecchio o di debug si
  ricostruisce, e il tag viene da `VERSION`; provata dal lato dell'host (piano H, §14 «CP7a»), commit `2e2d7ee70`,
  entrato in `dev_release2` con `744f5a0ee`.
- ✅ **M-26 · Due pagine della doc dicono ancora cose vecchie sui test e sulla CLI** — chiusa nella 1.2, M (lotto 36,
  13/10). Era: basso; M (docs-writer, lotto 35), 13/10, fuori dal perimetro del punto 2. `runner_architecture` ora usa
  `trackTransactionWrites()` e dice le due condizioni della pulizia; `cli_tools` dice in 4 lingue che anche `deactivate`
  rifiuta l'ultimo amministratore attivo. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «27.3».
  - `developer/test-walkthrough/runner_architecture.md:205-227` importa `deleteTransactionsCreatedSince`, che non
    esiste più, e consiglia la pulizia per differenza di id che `db-cleanup.ts` chiama non sicura; `:573` non dice che
    serve anche `E2E_WORKERS` ≤ 1.
  - `admin/cli_tools.*.md:70-77` non dice che anche `deactivate` rifiuta l'ultimo amministratore attivo.

  Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «26.2».
- ✅ **M-27 · La scheda Posizioni si chiama ancora «Performance» in alcune pagine** — chiusa nella 1.2, M (lotto 36,
  13/10), con la regola del coordinatore: per i controlli il nome del catalogo, «Holdings» resta dove indica il
  contenuto. Didascalie, frasi della galleria, `positions` e le due pagine developer, in 4 lingue dove tradotte.
  Restano due commenti nel codice (`PositionsPanel.svelte:142`, `dashboard/+page.svelte:623`). Dettagli:
  [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «27.2». Era: basso; M (docs-writer, lotto 35),
  13/10. Il selettore dice «Portafoglio / Periodo»; il lotto 35 ha corretto solo le 5 «Performance view» chieste.
  Restano la sezione e i titoli degli scatti di `user/dashboard/positions.*.md` e `user/brokers/index.*.md`, le pagine
  della galleria («Holdings and Performance») e due pagine developer. Dettagli: [journal del giro
  12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «26.2».
- ✅ **M-28 · Lo spagnolo chiama i tassi di cambio sia «tasas» sia «tipos de cambio»** — chiusa nella 1.2, M (lotto 37,
  13/10): 56 valori ora dicono *tipo(s) de cambio*, gli 8 che non sono un cambio tengono *tasa*; larghezze verificate
  (`toolbar-width-sweep` 15/15, sonda a 360 px). Dettagli: [journal del giro
  12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «28.2». Era: basso; M (lotto 36), 13/10.
  Il glossario dice *tipo de cambio*, e così il nuovo pulsante dei dati mancanti (`dataQuality.cta.sync_fx_pair`,
  «Sincronizar tipos de cambio») e `common.syncFxRates`. Nel catalogo spagnolo, però, 29 valori dicono *tasas*:
  per esempio «Sincronizar tasas» sul pulsante della pagina FX (`fxDetail.syncRates`) e altri valori di `fx.*`,
  `csvImport.*` e `transactions.wac.*`. Sono sorgenti di altre aree (`i18n/fx/`, …), da allineare al glossario
  con `dev.py i18n update`. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «27.1».
  - **Lotto 37, 13/10:** elenco pronto, 56 valori da cambiare e 8 da tenere (tasso privo di rischio, d'interesse, di
    crescita); si applica dopo il lotto di T. Dettagli: stesso journal, sezione «28.2».
- ✅ **M-29 · `runner_architecture.md` sbaglia ancora i worker** — chiusa nella 1.2, M (lotto 37, 13/10): la sezione
  «`--workers` reaches Playwright too» ora dice il tetto dei worker del browser e il backend condiviso dimensionato da
  `--workers`. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione
  «28.1». Era: basso; M (docs-writer, lotto 36), 13/10.
  - `:264` dice che si inietta `E2E_WORKERS=4`; oggi è al più metà dei core logici, ed è esportato solo sopra 1 e se
    non è già impostato (`scripts/test_runner/_common.py:90-131`).
  - `:267` e `:270` danno ⌊n/2⌋ worker del server; la configurazione usa `Math.ceil(E2E_WORKERS / 2)`,
    sovrascrivibile (`frontend/playwright.config.ts:54`): con 3 worker del browser sono 2, non 1.

  Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «27.3».
- ✅ **M-30 · Lo storico dell'allocazione non arriva al 100 %** — chiusa nella 1.2 da I (I-M30, piano 54:
  `a26051686`, `a08e208b4`, treno 99), verificata da M (lotto 45, 14/10). La causa era la fixture della galleria
  (`frontend/e2e/dashboard-report.json`): la normalizzazione di privacy scalava anche le quote dell'allocazione e lo
  YoC. Ora lo stack arriva al 100 % in tipo, settore e geografia, e la torta stampa le quote corrette. Dettagli: [piano
  della 54](54_galleryFixtureShares/plan-phase00GalleryFixtureShares.prompt.md); la verifica: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «36». Era:
  da verificare; M (lotto 42), 13/10: lo stack non arrivava al 100 % nelle tre viste, in ogni lingua e tema.
- ✅ **M-31 · Lo scatto `brokers/detail` mostra un broker vuoto** — chiusa nella 1.2, M (lotto 43, 13/10): il test
  apre Interactive Brokers per nome (`openBrokerCardByName`, come gli altri scatti della pagina del broker), che ha
  liquidità e titoli in tutta la finestra di 3 mesi; 16 scatti con Crescita e Allocazione piene. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «34». Era: basso; M (lotto 42), 13/10: il test prendeva la prima card della lista
  (`frontend/e2e/gallery.spec.ts:3104`), Charles Schwab, tutto a 0,00 sul periodo predefinito 3M, con «Nessun dato
  disponibile» in Crescita e Allocazione.
- ✅ **M-32 · L'alt dello scatto del dettaglio nella pagina dei broker** — chiusa nella 1.2, M (lotto 44, 13/10): lo
  scatto è passato dal passo 3 di «Create a broker» all'inizio di «🗂️ Inside a broker», con l'alt «Broker Detail»
  (Dettaglio broker, Détail du courtier, Detalle del bróker) e una frase che lo introduce e fa da didascalia; nelle
  quattro lingue, con lo stamp. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «35». Era: minimo; M (lotto 43), 13/10:
  `mkdocs_src/docs/user/brokers/index.{en,it,fr,es}.md:29` mostrava lo scatto `brokers/detail` sotto «Click
  **Create**», con l'alt del modulo di modifica copiato dall'immagine sopra («Broker Edit Form», …).
- **M-33 · Nessuno scatto mostra la colonna YOC** — basso; M (lotto 45), 14/10: nella tabella delle posizioni lo YoC è
  la settima colonna (`frontend/src/lib/components/dashboard/ExposureTable.svelte:5`). Lo scatto desktop finisce a
  P&L %, con Annualizzato tagliato; quello mobile alla prima colonna; la vista Periodo non la ha. Le pagine che la
  descrivono (`user/dashboard/positions.*.md:40` e `:59`, `user/brokers/index.*.md:102`) non hanno un'immagine che la
  mostri. Una via: nello scatto della tabella, scorrere fino alla colonna, o nasconderne qualcuna col selettore (👁).
  Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «36.1».

## Q · Documentazione e onboarding (21, 32)

Dettagli: [cartella 21](21_onboarding/) e [piano della 32](32_docsEnglish12/plan-phase00DocsEnglish12.prompt.md).

- ✅ **La review manuale C7 dell'onboarding** — chiusa l'11/10 dal developer: «tutte queste ricordo di averle
  testate, è tutto verde». Il punto 7, la guida della modale Aggiungi Broker che riparte dal primo passo, è coperto
  dall'E2E «OB-9 contrast» (`frontend/e2e/onboarding-guides.spec.ts`), verde l'11/10 sul target su desktop e mobile.
  FE1 è libero.
- **21-2 · Il contratto fra il catalogo TS e il registry Python dei flussi** — medio; nessun test confronta i due
  lati. Dettagli: [cartella 21](21_onboarding/plan-phase00Onboarding.prompt.md), «Cosa resta aperto», punto 2.
- **21-3 · Il re-trigger al cambio di versione di un flusso** — medio; mai provato end-to-end. Dettagli: idem, punto 3.
- **21-4 · La fascia 641–1023 px** — basso; Playwright prova solo 1280 e 430. Dettagli: idem, punto 4.
- **21-5 · Il reset admin o CLI dell'onboarding di un utente** — basso; oggi serve SQL. Dettagli: idem, punto 5.
- **21-6 · La telemetria su completamento e salto** — basso, facoltativa. Dettagli: idem, punto 6.
- **21-7 · L'ancora `tools.hub` senza guida** — basso; candidata per una guida Tools. Dettagli: idem, punto 7.

Le voci 32-1…32-5 vengono dai reperti dei docs-writer di S22 e S23, mai girati prima: i dettagli stanno solo qui
(trascritte dal coordinatore dalla ricognizione finale di Q, 11/10, verificate a `251067435`). Q è archiviata: le
voci le prende chi riparte sulla documentazione.

- **32-1 · Tre dettagli della pagina del banner di qualità dei dati** — minimo; Q (S23, docs-writer), 09/10. Il
  titolo `:93` attribuisce tutti i codici di portafoglio a `build_data_quality_report`, ma `MWRR_SERIES_UNRELIABLE`
  lo aggiunge `PortfolioService.get_report()` (titolo tenuto per l'ancora); la mappa dei file `:22` non cita
  quell'aggiunta per `portfolio_service.py`; la tabella dei trigger della Dashboard non ha una riga
  `MISSING_FX_RATES`. Dettagli: [data-quality-banner.md](../../../mkdocs_src/docs/developer/frontend/data-quality-banner.md),
  sezioni «🏷️ Active IssueCodes» e «🧪 How to Trigger Issues».
- **32-2 · La frase d'apertura del banner nella Dashboard** — basso; Q (S23, docs-writer), 09/10. `:88` dice che il
  banner compare se alla data finale mancano prezzi o cambi, ma il banner segnala anche prezzi vecchi, costi
  d'acquisto mancanti, cambi delle transazioni passate e asset valutati al prezzo di transazione; il `<div>` dello
  screenshot (`:89-91`) sta dentro il paragrafo, senza righe vuote. La pagina è tradotta: correggerla rimette il
  paragrafo nel giro di traduzione. Dettagli: [Dashboard](../../../mkdocs_src/docs/user/dashboard/index.en.md),
  sezione «🌡️ Data Quality Banner».
- **32-3 · `docker exec` gira come root** — basso; Q (S23, docs-writer), 09/10. `./dev.py docker exec` lancia
  `docker compose exec librefolio python dev.py …` senza `--user` (`dev.py:1796`), e l'immagine non ha `USER`: i
  comandi girano come root, e i file che creano in `LibreFolio-data/` restano di root fino al prossimo avvio, quando
  l'entrypoint ridà la cartella a `LIBREFOLIO_UID`/`GID` (`entrypoint.sh:21-29`). La pagina admin non lo dice, e il
  commento del compose d'esempio (`:287`, e lo stesso in `docker-compose.yml:42`) dice «drops to 'librefolio' user»,
  mentre gosu riceve gli id numerici (`Dockerfile:129-137`). Da decidere: documentarlo o passare `--user`.
  Dettagli: [docker_advanced.en.md](../../../mkdocs_src/docs/admin/docker_advanced.en.md), sezione «📡 `docker exec`».
  Stato (19/10): scelta la seconda strada (D8 di H): `./dev.py docker exec` passa per gosu con gli id numerici, e
  commento del compose e pagina admin sono corretti (CP7a di H, commit `2e2d7ee70`, entrato in `dev_release2` con
  `744f5a0ee`); la provano solo i controlli statici di `utils dev-cli-docker`, resta la prova a runtime nell'immagine
  (piano H, §14 «CP7a»).
- **32-4 · Le righe «Status: Implemented (Feb 2026)» delle pagine di stato del frontend** — minimo; Q (S23,
  docs-writer), 09/10. `developer/frontend/state/{index,app-state,domain-state,reference-state}.md` hanno ancora
  quella data, che git non conferma; `core-infrastructure.md` e `registries.md` sono già corrette con le date di git.
  Dettagli: [state/index.md](../../../mkdocs_src/docs/developer/frontend/state/index.md).
- **32-5 · La docstring di `daily_risk_free_rate`** — minimo; Q (S22, docs-writer), 09/10.
  `backend/app/services/risk/metrics.py:211-215` dice che un tasso per giorni di calendario «flatters every ratio
  computed with a non-zero rate»: succede solo con un tasso positivo, con uno negativo il rapporto scende (le pagine
  Sharpe e Sortino lo dicono già). Da fare insieme a C-32 del 38. Dettagli:
  [metrics.py](../../../backend/app/services/risk/metrics.py), `daily_risk_free_rate`.

## S · BRIM Scalable (37)

Dettagli: [piano della 37](37_brimScalable/plan-phase00BrimScalable.prompt.md), «Ancora aperti, con chi li ha», e
[recap dell'esportatore](37_brimScalable/recap-phase00ScalableExporter.md), «Todo aperti». S è archiviata: le voci
le prende chi riparte sui BRIM.

## V · E2E qualità dati (46)

Dettagli: [piano della 46](46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md), §9 «Avanzamento». Righe scritte da
V il 12/10, nel checkpoint dei test E2E delle voci 21-23 della checklist.

- ✅ **V-1 · «Sincronizza prezzi» (STALE_PRICE) non aggiorna i pannelli già aperti** — basso; V, 12/10. È il gemello
  della D2: `handleBannerAction` (`dashboard/+page.svelte`) ricarica il report, ma non incrementa `refreshVersion`. Il
  pannello lotti e il rischio già aperti restano quindi vecchi fino a una ricarica. Dettagli: piano della 46, §9
  «Passo 4». **Chiusa il 12/10** nel lotto 2 di V: prima il rosso, poi `refreshVersion += 1` dopo `invalidate()` nel
  ramo `sync_asset_prices` (`dashboard/+page.svelte:457-458`). Test in `stale-price-banner.spec.ts`. Commit: lotto 2
  di V, indicato dal coordinatore. Dettagli: idem, §11.3.
- **V-2 · Il pannello lotti non pubblica `data-busy`** — basso; V, 12/10. Parte con `loading` falso
  (`LotsAnalysisPanel.svelte:91`), quindi un'assenza si legge solo dopo un testimone, cioè le righe dei lotti, o sulla
  risposta. Gli spec della 46 fanno così. Dettagli: idem, §9 «Passo 3».
- ✅ **V-3 · TRANSFER orfano: i lotti falliscono, la Dashboard lo conta come capitale in natura** — basso, dopo la 1.2
  (decisione del developer, 13/10); test-author di V (B1), 12/10. L'analisi dei lotti risponde `FAILED` con
  `TRANSFER_PAIR_MISSING`. Nessun test lo fissa. Dettagli: idem, §9 «Passo 1».
  - **Come nasce**: cancellando un broker, `delete_by_broker` (`transaction_service.py:334-352`) toglie solo il
    collegamento `related_transaction_id` alla metà rimasta sull'altro broker, che resta un TRANSFER spaiato. C'era già
    nella `v1.1.0`.
  - **Il comportamento giusto, deciso dal developer il 13/10**: il TRANSFER rimasto senza la sua metà torna a essere un
    semplice **ADJUSTMENT**, con la stessa quantità e lo stesso `cost_basis_override`. Così i lotti FIFO lo leggono come
    un ADJUSTMENT (`fifo/engine.py`, i rami `ADJUSTMENT_IN`/`ADJUSTMENT_OUT`) e non falliscono più.
  - Da progettare: la Dashboard (oggi `classifier.py:104`, capitale in natura), gli orfani già presenti nei DB (una
    migrazione o una conversione alla lettura), e i test della cancellazione del broker.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): W-B6 di W, con la divisione D-J4 (W scrive, J rivede i
  numeri). La cancellazione di un broker converte la metà rimasta (N1b-1, commit `6be11ecf3`); gli orfani già nei DB
  li converte la correzione post-migrazione `orphan_pair_halves` (N1b-2/N1b-3, `5e19c6018` e `0e4bd9790`), tutti
  entrati in `dev_release2` con `14d58cc61`. Con la decisione 47 anche la gamba in uscita diventa un ADJUSTMENT-out al
  costo Auto (`a66bbc1a4`, entrato con `ea72346b7`), che i lotti consegnano al costo (CP-16 di J, `335fb89cf`, entrato
  con `240675ad1`).
- ✅ **V-4 · Se si chiude P-10, E2 di `data-quality-real.spec.ts` va ricostruito** — minimo; V, 12/10. E2 ottiene
  `MISSING_COST_BASIS` dall'app riclassificando uno SPLIT in PRICE_ADJUSTMENT. E4 (righe legacy) e B1 restano validi.
  Dettagli: idem, §4.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): J, con CP-14a. Dopo P-10 nessuna strada legittima porta a
  `MISSING_COST_BASIS` su dati nuovi, quindi E2 ora fissa il rifiuto (409 con i `params` esatti, nessun costo ignoto
  su Dashboard, lotti e broker, e il passaggio con un costo di 0); le due prove che c'erano solo in E2 sono passate a
  `data-quality-legacy.spec.ts`. Commit `475bb9270` (entrato in `dev_release2` con `03101ddad`) e `c21ea4b10`, i
  `params` col conteggio nascosto (entrato con `ba612882a`).
- ✅ **V-5 · Un commento superato in `data-quality-banners.spec.ts:434`** — minimo; V, 12/10. Parla di «the seed's
  MISSING_COST_BASIS», ma il populate fallisce se manca un costo (`populate_mock_data.py:3944-3959`): il seed non può
  produrlo. Dettagli: idem, §1.1. **Chiusa il 12/10** nel lotto 2 di V: il commento ora nomina il `TRANSACTION_IMPLIED`
  che il test inietta. Commit: lotto 2 di V, indicato dal coordinatore.
- ✅ **V-6 · La doc dev elenca solo una parte dei test di `data-quality-banners.spec.ts`** — minimo; docs-writer di V,
  12/10. Mancano i tre test di «Sincronizza tassi» e quello dei link di `MISSING_PRICE`. Dettagli:
  [data-quality-banner.md](../../../mkdocs_src/docs/developer/frontend/data-quality-banner.md), sezione «Frontend E2E
  Tests (`e2e/portfolio/data-quality-banners.spec.ts`)». **Chiusa il 12/10** nel lotto 2 di V: la sezione elenca tutti
  i 18 test, per contesto, e spiega perché lo spec inietta le issue. Aggiornate anche la riga `sync_asset_prices`
  della tabella delle CTA (V-1) e la sezione di `stale-price-banner`. Commit: lotto 2 di V, indicato dal coordinatore.
- ✅ **V-7 · `dashboard-cache.spec.ts:338` rosso accanto a `dashboard-broker-filter-label`** — basso; V, 12/10.
  Preesistente, fuori scope, i due spec non sono di V. Nel giro consolidato `--workers 4 front-portfolio all`:
  - `dashboard-broker-filter-label` crea e cancella un broker di `TEST_USER` (11:52:46 → :51/:52 UTC);
  - nel frattempo `dashboard-cache` aveva letto i broker posseduti dello stesso utente;
  - la sua `risk/query` riceve 403 «subset not fully accessible» (`risk.py:73,89`) e il pannello mostra «Risk data
    could not be loaded».
  Da solo, a 4 worker, `dashboard-cache` passa 6/6. La cura probabile: `broker-filter-label` su un account
  usa-e-getta. Da decidere se il pannello debba rileggere i broker posseduti dopo un 403. Dettagli: piano della 46,
  §9 «Passo 7». **Chiusa il 12/10** nel lotto 2 di V: `broker-filter-label` gira su un account usa-e-getta con due
  broker suoi, e `TEST_USER` non viene più toccato. Nel giro consolidato a 4 worker passano 157/157, con
  `dashboard-cache:338` accanto ai test di `broker-filter-label`. La domanda sul 403 continua in V-8. Commit: lotto 2
  di V, indicato dal coordinatore.
- **V-8 · Il pannello Rischio con un broker sparito: 403 e nessuna rilettura** — basso, dopo la 1.2 (decisione del
  developer, 13/10); V, 12/10. Se un broker posseduto sparisce dopo che la Dashboard ha letto i broker, per esempio
  cancellato in un'altra scheda, la `risk/query` riceve 403 «Requested portfolio broker subset is not fully accessible»
  (`risk.py:73,89`). Il tab Rischio mostra «Risk data could not be loaded» finché la pagina non rilegge i broker.
  Nessun dato è sbagliato o perso. Cura proposta: al 403 il pannello rilegge i broker posseduti e riprova una volta,
  con un E2E. Dettagli: piano della 46, §9 «Passo 7» e §11.
- ✅ **V-9 · Due frasi superate nella doc del banner** — minimo; docs-writer di V, 12/10. In
  [data-quality-banner.md](../../../mkdocs_src/docs/developer/frontend/data-quality-banner.md):
  - la sezione «Component Modes → grouped» dice che le prime 3 issue sono visibili e che un pulsante appare quando
    sono di più. In realtà il banner parte chiuso (`expanded = false`) e l'intestazione `data-quality-toggle` apre e
    chiude tutto l'elenco;
  - la regola di `TRANSACTION_IMPLIED` cita il testo inglese «still valued at cost», mentre `en.json` dice «valued at
    their last transaction price…».

  **Chiusa il 12/10**, lavoro 3 di V, passo 1. La sezione «grouped» descrive il banner chiuso, il toggle e
  l'intestazione che conta solo errori e avvisi diversi da zero. La regola cita il testo attuale. Commit: lavoro 3 di
  V, passo 1, indicato dal coordinatore. Dettagli: piano della 46, §12.2.
- ✅ **V-10 · Due difetti latenti in `data-quality-banners.spec.ts`** — minimo; docs-writer di V, 12/10:
  - i commenti citano `hasFailedConversion` (`assets/[id]/+page.svelte:501`), che non esiste più; ora c'è
    `getComparisonEventFxDependency`;
  - nel test «header does not show "0 errors, 0 warnings"», la regex `/0 error/i` colpisce anche «10 error(s)»: con
    10 errori o più fallirebbe senza ragione.
  Dettagli: piano della 46, §11.3.

  **Chiusa il 12/10**, lavoro 3 di V, passo 1.
  - Prima il rosso: dieci errori serviti, e la vecchia regex respinge «10 error(s)».
  - Poi tre test deterministici, che servono l'elenco intero e leggono i numeri di `data-quality-toggle`: solo info,
    dieci errori, l'ordine per severità.
  - Il commento ora descrive `getComparisonEventFxDependency`.
  - Verdi 20/20 a 1 e a 4 worker.

  Commit: lavoro 3 di V, passo 1, indicato dal coordinatore. Dettagli: piano della 46, §12.2.
- ✅ **V-11 · `TRANSACTION_IMPLIED` può dire «nessun prezzo di mercato da oltre 2 settimane» per un asset quotato ieri**
  — basso, da confermare con un test; docs-writer di V, 12/10. Per lettura del codice:
  - `AssetPriceSeries.resolve` (`financial_math/price_marks.py:197-223`) prende l'osservazione più recente, quote o
    trade che sia. Un BUY registrato oggi, prima del sync della quotazione di oggi, batte quindi la quotazione di ieri:
    `LAST_TRADE_PRICE`, l'asset è «implied»;
  - superato il periodo di grazia, contato dal primo BUY/SELL e non dall'ultima quotazione
    (`portfolio_service.py:1083-1088`), compare l'avviso, e il testo di `en.json:1719` parla di oltre 2 settimane
    senza prezzo di mercato.
  La valutazione al prezzo del trade è sensata; sbagliato è solo il messaggio. Dettagli: piano della 46, §12.2.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): CP-4b di J, con la decisione D-J15 del developer: il
  periodo di grazia parte dall'ultima quotazione di mercato, e dal primo BUY/SELL solo per un asset senza quotazioni,
  con i rossi sui tre scenari, commit `58f8e3967`, entrato in `dev_release2` con `322d55042`.
- **V-12 · La doc del banner attribuisce il modo `grouped` alla sola Dashboard** — minimo; docs-writer di V, 12/10. In
  [data-quality-banner.md](../../../mkdocs_src/docs/developer/frontend/data-quality-banner.md), sezione «Component
  Modes», il titolo dice «`grouped` — Dashboard». Lo usano anche `RiskAnalysisPanel.svelte:619`,
  `AssetSetRiskPanel.svelte:848` e `risk/levels/RiskPanelHeader.svelte:116`.
- **V-13 · Commenti del backend che dicono ancora «valued at cost»** — minimo; docs-writer di V, 12/10.
  `TRANSACTION_IMPLIED` valuta all'ultimo prezzo di transazione (`en.json:1719`). Dicono ancora «at cost»:
  - `financial_math/portfolio/data_quality.py:66` e `:115`;
  - `portfolio_service.py:1069`, che cita il messaggio come se fosse ancora quello vecchio.
- **V-14 · Sonde legate al seed rimaste in `data-quality-banners.spec.ts`** — basso; test-author di V, 12/10. Sono
  le stesse classi del test riscritto in V-10, ma non sono state toccate:
  - `expandDataQualityBanner` (`:74`) decide se agire con `isVisible({timeout: 3000}).catch(() => false)`, e
    `isVisible` ignora il timeout;
  - il test «when data quality banner is present it is grouped with issue rows» (`:401`, sonda a `:404`) e il test
    «range-before-data issue appears when URL date precedes first data» (`:697`, sonda a `:704`) annotano invece di
    fallire quando manca la condizione;
  - `goToFirstAssetDetail` (`:44`) apre il primo `asset-card-*` senza filtro; lo usano tre test della pagina asset;
  - il commento del test «FX pair missing issue has add-fx-pair CTA in flat mode» cita righe superate (`:483` → oggi
    `:669`; `:1052` → oggi `:2631`).
  Cura: servire le issue con `serveDashboardIssues`, come in V-10, e un asset scelto per id. Dettagli: piano della
  46, §12.2.
- **V-15 · Spec che creano e cancellano broker di `TEST_USER` (la classe di V-7)** — basso; V, 12/10 (audit del
  lavoro 3, passo 2). Creano broker dell'utente condiviso e li cancellano per id: il danno è transitorio e resta nella
  propria categoria, perché il parallelo esiste solo lì. Nessun rosso dimostrato. I lettori sensibili, cioè lo scope
  del rischio, che risponde 403 come in V-7, stanno in portfolio e ai-export, dove oggi nessuno scrive. L'elenco:
  - asset: `assets/asset-merge.spec.ts`;
  - broker: `brokers/broker-create-feedback.spec.ts`, `brokers/broker-recovery.spec.ts`,
    `brokers/brokers-detail.spec.ts`;
  - fx: `fx/fx-flag-font.spec.ts`;
  - utility: `files.spec.ts`, `files-destructive.spec.ts` (seriale; i broker vivono fino ad `afterAll`). Correzione del
    12/10: in `files.spec.ts` il test di `:886` «opens table preview for BRIM files» è di classe A, perché lascia il suo
    broker e il file BRIM; la cura è nel checkpoint delle lacune 2 e 1;
  - transaction: `tx-broker-icon-hydration`, `tx-bulk-diagnostics`, `tx-bulk-import-handoff`,
    `tx-bulk-promote-cost-basis`, `tx-bulk-row-order`, `tx-clone` (tranne il test di `:549`, che va nella cura A7),
    `tx-fx-completeness`, `tx-import-asset-inspector`, `tx-import-ca-contract`, `tx-import-degiro`,
    `tx-import-duplicate-precedence`, `tx-import-file-selection`, `tx-import-matching`, `tx-import-report-set`,
    `tx-import-upload`, `tx-selection-after-bulk`, `tx-wac-bulk`.

  Cura, a poco a poco: un account usa-e-getta (`registerDisposableUser`, `createOwnedBroker` di
  `fixtures/onboarding-accounts.ts`), come in `dashboard-broker-filter-label`. Dettagli: piano della 46, §12.3.
  Nella 2b (12/10) è stato sistemato anche `tx-wac-bulk`: WB5 dipendeva dagli avanzi degli altri spec, e ora costruisce
  la sua coppia; WB4 cancella ciò che committa. Dettagli: piano della 46, §12.8.
- ✅ **V-16 · Login, registrazione e cambio password fanno bcrypt dentro l'event loop** — medio, serve una decisione;
  test-author di V, 12/10, verificato da me. Le chiamate sincrone stanno direttamente nei gestori `async def`:
  - `login` (`api/v1/auth.py:105`) chiama `verify_password_or_dummy`, cioè `bcrypt.checkpw`
    (`services/auth_service.py:62`);
  - `register` (`:205`) arriva a `hash_password` (`auth_service.py:44`) attraverso `user_service.create_user`
    (`user_service.py:168`);
  - il cambio password chiama `verify_password` e `hash_password` (`auth.py:253`, `:262`).

  Con costo 12 ogni controllo prende circa 0,24 s, misurati, e per quel tempo il worker uvicorn non serve nessun'altra
  richiesta. È contro la regola «Async I/O» delle istruzioni del progetto. A 4 worker E2E erano circa 51 login in
  67 s. Non è dimostrato che abbia causato un rosso. Cura probabile: `await asyncio.to_thread(...)`. Dettagli: piano
  della 46, §12.5.

  **Chiusa il 12/10**, checkpoint V-16 di V, deciso dal coordinatore.
  - Prima il rosso: `TestPasswordWorkLeavesTheEventLoopFree` in `test_auth_api.py`, con un heartbeat nel loop e un
    sostituto bloccante di 0,4 s. Buchi misurati di 0,40 s su login, register e cambio password.
  - Poi la cura: `asyncio.to_thread` in `auth.py`, per login e cambio password, e in `user_service.create_user`.
  - Verdi: `api auth` 60/60, `api profile` 12/12, `api account-deletion` 6/6, e un E2E di login a 1 e a 4 worker.
  - `user_service.reset_password`, usata solo dal CLI, resta com'è.

  Commit: checkpoint V-16 di V, indicato dal coordinatore. Dettagli: piano della 46, §12.7.
- **V-17 · Il runner: la chiave `settings` prende anche `fx-chart-settings`, e il setup di Playwright ripopola** —
  basso; test-author di V, 12/10:
  - `_frontend_utility.py:373` passa `settings.spec.ts` a Playwright come pattern, e il pattern prende anche
    `fx/fx-chart-settings.spec.ts`: 45 test invece di 42. Nel giro consolidato quei 3 test girano due volte, in fx e in
    utility;
  - in ogni invocazione il setup di Playwright ripopola il DB e ricrea gli utenti («Ensuring test DB is populated…»),
    anche se il runner l'ha appena fatto: su questa strada `LF_SETUP_DONE` non sembra impostato. Sono circa 20 s a
    giro, con il backend condiviso già avviato;
  - il catalogo delle eccezioni seriali in `playwright.config.ts` non elenca il blocco seriale nuovo di
    `settings/scheduler.spec.ts` («Saving»), e mancava già di `fx-destructive` e `files-destructive`.
    **Questo punto è chiuso il 12/10**, nella 2b di V: il catalogo elenca i cinque blocchi seriali veri, e
    `asset-event-delete` è uscito dall'elenco.
  Dettagli: piano della 46, §12.5.
- **V-18 · Selettori CSS e in inglese rimasti nei test delle impostazioni** — basso; test-author di V, 12/10:
  - in `SchedulerConfigModal.svelte` i chip degli orari non hanno testid: FSCH-008/009 usano `span.rounded-full`. Il
    pulsante di rimozione ha `aria-label="Remove {slot}"` in inglese fisso, che è anche un difetto i18n del prodotto.
    Attributi proposti: `data-testid="scheduler-config-time-slot"` più `data-slot`, e
    `data-testid="scheduler-config-time-remove"`;
  - in `settings.spec.ts`, «Global Settings — Toggle & Number Interaction» usa titoli in inglese, `.setting-row` e il
    testo ON/OFF. I testid per migrarlo esistono già: `settings-lock-toggle`, `setting-save`, `setting-undo`;
  - «preferences persist after navigating away and back» controlla solo la visibilità.
  Dettagli: piano della 46, §12.5.
- ✅ **V-19 · In spagnolo la barra della Dashboard e dell'asset sfora in modo denseRow** — chiusa nella 1.2 da I,
  treno 72 (`7f8febd9d`): soglie denseRow 990 e 890. Era: basso, difetto di layout;
  gate di V, 12/10. `layout/toolbar-width-sweep.spec.ts:873`, casi `es` di dashboard e assetDetail. Il gruppo
  «Exportación IA …» esce dalla barra (`dashboard-filter-bar`, `asset-detail-filter-bar`):
  - asset: +1,8 px a vw 1220, +11,8 px a vw 1210, +9,8 px a vw 940 (soglia denseRow 850);
  - dashboard: +1,0 px a vw 1320, +11,0 px a vw 1310 (soglia denseRow 950).

  È deterministico: rosso anche a 1 worker. Lo spec suggerisce di alzare la soglia sopra la barra più larga, oppure di
  accorciare le etichette. La 2a di V non tocca né le barre né i cataloghi. Dettagli: piano della 46, §12.5.
- ✅ **V-20 · Attese di 3 s sulla prima navigazione, rosse sotto carico** — basso; gate di V, 12/10. Sono verdi da
  sole o a 1 worker, rosse con la concorrenza:
  - `auth.spec.ts:379` e `:615` (Integrated onboarding 1 e 4): dopo `login()`, `toHaveURL(/dashboard/)` usa i 3 s di
    default; il test accanto (`:370`) ne usa 15;
  - `layout/app-start-auth.spec.ts:184`: poll di 3 s su `/auth/me` dopo `goto('/assets')`. Con tre test concorrenti i
    due fratelli passano da 2,7 e 5 s a 15 e 18 s;
  - `files.spec.ts:835` ha esaurito i 30 s solo nel giro pieno.

  Cura: aspettare la condizione con un limite di stato adeguato, non i 3 s di default. Il rallentamento stesso merita
  una voce sua; V-16 è una concausa possibile. Dettagli: piano della 46, §12.5.

  **Chiusa il 12/10**, nella 2b di V, con attese su stati pubblicati e limiti espliciti:
  - `openLoginPage`, `expectLandedOnDashboard` (path, poi `dashboard-page`) ed `expectLandedOnWelcome` in
    `auth.spec.ts`, che copre anche il resto del flusso;
  - lo stato del layout prima del gate in `app-start-auth:190`;
  - `files-page` `data-busy` e la pulizia in `afterEach` in `files:854`.

  Verdi `auth` 29/29, `app-start-auth` 3/3 e `files` 28/28, a 1 e a 4 worker, sotto carico alto. Commit: checkpoint 2b
  di V, indicato dal coordinatore. Dettagli: piano della 46, §12.8.
- **V-21 · Sonde e selettori vietati rimasti negli spec curati dalla 2b** — basso; test-author di V, 12/10. La 2b ha
  curato i test che scrivevano sullo stato condiviso, non tutto il resto degli stessi file:
  - `transactions-modals`:
    - **T10 non prova niente**: il delete della toolbar ora apre il workspace bulk, quindi la sua sonda su
      `confirm-modal-confirm` risponde sempre falso. In più legge un contatore globale;
    - **T1 non mostra mai un commit riuscito**: sceglie Charles Schwab, senza cassa, e va in rollback. È una
      decisione, perché cambiare broker cambia ciò che il test asserisce;
    - `.first()` senza filtro in T3/T9/T11, e sonde `isVisible().catch`;
  - `tx-wac-unit-toggle`: classi CSS (`bg-gray-200`, `bg-libre-green`) e sonde;
  - `tx-wac-formmodal`: FM10 usa `.nth(count-1)` e la classe `font-medium`; FM7 ha una sonda;
  - `tx-commit-all-types`:
    - `.checkbox-btn` e `tr.row-deleted`;
    - il test FX_CONVERSION accetta ancora «nessun commit»;
    - `expectTransactionGone` dice che gli id vengono riusati, ma `AUTOINCREMENT` c'è dal piano 34;
  - `tx-split-promote` e `tx-paired-edit`:
    - sonde e classi CSS in Bug 6, Bug 14, NR-1 e Guard;
    - gli helper della coppia sono copiati nei due spec;
    - il commento di `selectRow` («a paired row selects both halves») è sbagliato;
  - `tx-event-picker`: `pickAssetByName`, se la sonda manca, clicca il primo asset della lista;
  - `tx-import-resolution`:
    - `openImportWizard` usa un `.first()` senza filtro;
    - IWR-007 e IWR-010 hanno `return` condizionali;
    - IWR-006b ripiega su un controllo più debole;
  - `tx-clone`: righe scelte per posizione, classi CSS, `text=new`; il test «view-only» esce presto;
  - `files.spec.ts`:
    - ✅ gli altri test di File Preview: i PDF puliscono in `finally` con 30 s, mentre markdown, immagine, dettaglio, zoom
      e commenti non cancellano mai il loro upload (la lista `ownedStaticFiles` ora c'è). **Chiuso il 12/10** da
      `eb269ecde` («files spec cleans uploads and broker»), ora nel target (treno 76): ogni upload si iscrive in
      `ownedStaticFiles`, e il broker BRIM si cancella in un `afterEach`;
    - il modo griglia/lista si legge dalla classe `active`: servirebbe `aria-pressed` su `view-mode-grid` e
      `view-mode-list` in `files/+page.svelte` (~`:704/707`);
  - la fixture `logout()` (`auth-helpers.ts`) usa ancora i 3 s di default.

  Dettagli: piano della 46, §12.8.

  ✅ **Chiusa in gran parte il 13/10**, nel checkpoint V-25/V-21 di V, via test-author. Verde a 1 e a 4 worker, col
  DB al seed. Dettagli: piano della 46, §12.10.
  - `transactions-modals`:
    - T10 lavora su un DEPOSIT proprio, cancellato dal flusso vero e verificato per id;
    - T3, T9 e T11 usano righe proprie;
    - le sonde sono tolte, e T6 e T7b ora provano davvero.
  - `tx-wac-unit-toggle` e `tx-wac-formmodal`: `aria-pressed` al posto delle classi; FM10 trova la riga per una
    descrizione unica; FM7 è un'asserzione.
  - `tx-commit-all-types`:
    - checkbox per id, e lo stato della riga da `tx-bulk-row-status`;
    - FX_CONVERSION esige il commit;
    - il commento su AUTOINCREMENT è corretto.
  - `tx-split-promote`, `tx-paired-edit` e `tx-clone` usano account propri; gli helper della coppia stanno in
    `fixtures/owned-pair.ts`.
  - `tx-event-picker`: niente più ripiego sul primo asset.
  - `tx-import-resolution`:
    - niente `return` condizionali;
    - IWR-007 asserisce il contratto vero, quello della doc utente: una collisione col DB arriva alla revisione non
      spuntata, con `data-duplicate-status="likely"`, e senza il passo «Duplicates»;
    - IWR-006b apre la `TransactionCompareModal`.
  - `files.spec.ts` legge `aria-pressed`, e `logout()` aspetta `/` e `login-page`.
  - Gli attributi nuovi:
    - `tx-bulk-row-status` con `data-status`;
    - `tx-bulk-delete-selected`;
    - la prop `testId` di `Tooltip`, usata come `tx-form-cost-basis-help`;
    - `data-duplicate-status`;
    - `aria-pressed` su `view-mode-*`.

  **Resta aperto:**
  - ✅ **T1, chiusa il 13/10** in un checkpoint di V, via test-author. La decisione del developer (domanda 8): «C:
    entrambi, due test». Il vecchio T1 sparisce. T1a, T1b e T6 stanno in un blocco proprio, ciascuno su un account suo,
    con un broker suo.
    - **T1a**: un BUY dal form, sul broker del test finanziato, arriva nel bulk editor e si salva (`committed`). Lo si
      ritrova via API, per id e con i valori mandati, e nella tabella.
    - **T1b**: lo stesso BUY su un broker senza cassa viene rifiutato con `balanceCashNegative`, coi parametri della
      richiesta.
      - Il messaggio nomina il broker, la data ISO e la valuta, e il suo link porta alla riga.
      - Il modale resta aperto con la riga, e il broker non ha righe.
    - **Le prove**: T1a rosso senza deposito, T1b rosso col broker finanziato; entrambi poi verdi.
    - `fillBuyTransaction` sceglie broker e asset per nome. T2 e T6 sono verdi.
      - **T6** era verde per la ragione sbagliata: il form corregge il segno di `-1`, e l'avviso nasceva dalla cassa
        vuota di Charles Schwab. Ora sta anche lui su un account suo, con un broker senza cassa: prima verifica che
        l'avviso nomini il broker, poi lo chiude. È rosso col broker finanziato.
    - `transactions-modals` 21/21 a 1 e a 4 worker, col DB al seed. Ne sono nate V-37 e V-38.

    Dettagli: piano della 46, §12.14.
  - ✅ **T4, chiusa il 13/10** in un checkpoint di V, via test-author.
    - **La decisione del developer** (domanda 12): nel bulk editor «Costo di carico» (`cost_basis_override`) prima di
      «Evento» (`asset_event_id`) è voluto, non è una regressione. La nota del passo 10 del piano Bugfix-3 («spostato
      dopo») è superata.
    - **Il test**: T4 ora legge l'ordine delle intestazioni del workspace (`dt-header-*` in `tx-bulk-body`), dopo aver
      verificato che le due colonne si vedono di default.
    - **Le prove**:
      - col solo ordine atteso invertito è rosso, e mostra l'ordine vero;
      - ripristinato, è verde;
      - `transactions-modals` 20/20 a 1 e a 4 worker, col DB al seed.

    Dettagli: piano della 46, §12.13.
  - **T5 e T8** asseriscono il testo tradotto dell'etichetta dell'asset. Servirebbe uno stato pubblicato, per esempio
    `data-asset-field` su `tx-form-asset-wrap` (`TransactionFormModal.svelte`, ~`:1900`); per T8, però, il soggetto è
    la traduzione.
  - **T13** comincia ad aspettare la risposta di validazione solo dopo il click su Apply.
  - **`transactions-modals`, residui minori** visti da test-author di V il 13/10, fuori lista:
    - `goToTransactions` ingoia la sua `Promise.race` con `.catch`;
    - `optionListReady` usa `.first()` su `[role="listbox"]` senza filtro;
    - l'intestazione dello spec dice ancora «port 6041»;
    - il commento «T4: no confirm dialog» nel test «Delete» usa un'altra numerazione;
    - l'opzione `skipCash` di `fillBuyTransaction` non ha più chiamanti.

    I `bulkRows.first()` e la `Promise.race(...).catch` del vecchio T1 sono spariti con T1a e T1b (13/10).
  - ✅ **`tx-wac-fx` e `tx-wac-mode`: le sonde intorno a «⚡ Validate now», chiuse il 13/10** nel checkpoint V-37 di V,
    via test-author.
    - Le cinque sonde `isVisible().catch(() => false)`: `tx-wac-fx.spec.ts` `setupMissingFxScenario` (`:105`), W6, W7
      e W8 (`:287`, `:320`, `:359`), più `tx-wac-mode.spec.ts:247`. Ora asseriscono il pulsante visibile e attivo, e
      poi cliccano.
    - Il test ⚡ di `tx-wac-mode` aspetta il giro del clic (`data-validate-runs`) dopo un form fermo, quindi prova che
      il clic arriva al server.
  - **`tx-wac-fx` e `tx-wac-mode`, residui**, fuori lista, visti da test-author di V il 13/10:
    - in W1-W5 di `tx-wac-fx` restano altre sonde `isVisible().catch` e dei `return` anticipati quando non compare
      niente;
    - `selectAsset` clicca un `.first()` senza filtro (`tx-wac-fx.spec.ts:71`);
    - W7 usa `.tooltip` e un `.first()` senza filtro;
    - W9-W11 di `tx-wac-mode` asseriscono classi CSS.
  - **`tx-delete`**, fuori lista: `.checkbox-btn` in A6 e B3-guard (`:652`, `:774`, `:815`), `.disabled-select-icon`
    (`:811`) e una sonda (`:793`).
- **V-22 · «+ New event» può modificare un evento esistente dicendo di averlo creato** — dopo la 1.2, deciso dal developer il 13/10; letto da
  test-author di V e verificato nel codice da me, 12/10. Nessun test lo dimostra ancora:
  - `EventCreateMiniModal.svelte:133-145` manda un upsert senza id (`upsert_events_bulk`);
  - il backend applica un upsert senza id all'evento con la stessa data e lo stesso tipo, e lo aggiorna sul posto, anche
    se è collegato (`test_upsert_without_id_keeps_the_event_id`,
    `test_upsert_without_id_updates_a_linked_event_in_place`);
  - il modale rilegge quell'evento, mostra un toast di successo e lo passa al form come appena creato.

  Un dividendo «nuovo» nello stesso giorno di uno esistente, magari del provider, ne sovrascrive importo e note. Da
  decidere se è voluto. Se non lo è, il rosso va scritto prima della cura. Dettagli: piano della 46, §12.8.
- ✅ **V-23 · Il bulk editor nasconde il broker di sola lettura e attacca l'errore d'accesso alla riga sbagliata** — basso,
  UX; test-author di V (triage di WB5), 12/10:
  - un TRANSFER verso un broker di sola lettura mostra il ricevente come «To: —». `renderBrokerHtml`
    (`TransactionBulkModal.svelte` ~`:1608`) cerca il broker solo nella lista dei broker modificabili
    (`getEditableBrokers()`, ~`:593`). L'utente non vede quale broker causa l'errore, e il banner lo chiama solo
    «Broker #2»;
  - `_append_access_issues` (`transaction_batch_stages.py` ~`:158-178`) riporta ogni errore d'accesso come
    `operation="create", index=0`. La griglia lo mette sulla riga 1a (IB, modificabile) e non sulla 1b (DEGIRO).

  Dettagli: piano della 46, §12.8.

  ✅ **Chiusa il 15/10** da W (lotto I1 della 1.3, `5e96df752`; in `dev_release2` con `dc7e4e48e`): un rifiuto per
  riga e per broker negato, sulla riga che lo causa; il bulk editor nomina anche i broker di sola lettura.

- **V-24 · Nel bulk editor la cella del costo in Auto può mostrare per un attimo «💡 0.00» come `ready`** — basso, UX;
  test-author di V (lacuna 5), 12/10, letto nel codice e non visto a schermo. Appena un TRANSFER in Auto passa dal form
  all'editor, il form invia un importo 0 come segnaposto, che porta solo la valuta, e la cella tratta qualsiasi importo
  come proposta pronta. Il valore si corregge appena torna la validazione dell'editor (150 nel test). Per un istante
  l'utente vede il sintomo corretto nella 1.2 (costo 0), e `data-state="ready"` non vuol dire «calcolato». Dettagli:
  piano della 46, §12.9.

- **V-25 · `tx-delete` consuma righe del seed e lascia un broker di `TEST_USER`** — basso; gate di V, 12/10. Nel giro
  consolidato `front-transaction all`:
  - «A1-confirm» (`tx-delete.spec.ts:181`) cancella la FEE `[delete-safe] Platform fee for delete test`;
  - «A2-confirm» cancella la coppia `delete-consume`;
  - «A1-error» lascia di proposito il broker `T4-delref-<suffix>` (OWNER `e2e_test_user`) e il suo asset
    (`:390-393`).

  Il DB, quindi, a fine categoria non torna al seed. Le righe consumate sono monouso per costruzione, e ogni invocazione
  ripopola. Il broker permanente, però, è della classe A7. Cura possibile: righe e broker creati dal test, come in A5
  e A7. Dettagli: piano della 46, §12.9.

  ✅ **Chiusa il 13/10**, nel checkpoint V-25/V-21 di V, via test-author.
  - **La prova del danno**, sullo spec non modificato: dopo il giro il DB aveva 73 transazioni, 9 broker e 18 asset,
    contro 76, 8 e 17 del seed.
  - **La cura**:
    - A1-confirm e A2-confirm lavorano su account usa-e-getta, con una FEE propria e una coppia ETH propria, finanziate
      da righe proprie, e cancellate in `afterEach` con l'account;
    - A1-error registra gli id appena esistono e cancella righe, broker (`force`) e asset per id;
    - lo stato «delete» si legge da `tx-bulk-row-status`.
  - **La verifica**: 15/15 a 1 e a 4 worker, col DB al seed. L'impronta delle righe 1–76 è identica nei due giri.
  - **Resta**: la riga 28 del seed (FEE «Platform fee for delete test») e la coppia 45/46 (`delete-consume`) non le
    legge più nessuno spec. Restano nel seed, perché toglierle sposterebbe i lettori posizionali, come FE-SP-C4 di
    `tx-bulk-suggest-ux`, `tx-picker-pagination`, A6 e B3-guard di `tx-delete`. Un consolidato a 1 worker non dovrebbe
    più ripopolare dopo `tx-delete`.
  - **I commenti** che lo davano ancora per distruttivo sono corretti nello stesso checkpoint: fixture `playwright.ts`,
    skill `testing-frontend`, `populate_mock_data.py` 9c e `tx-paired-edit`. La doc dev `runner_architecture.md`
    (`:232`, `:561`, `:577`, `:588`) è di M ed è segnalata al coordinatore.

- ✅ **V-26 · Due rossi da carico della classe di V-20, nella verifica di V-21c** — basso; V, 13/10. Visti con la
  coverage della 6176 in corso; test-triage dà «assunzione», col prodotto corretto in tutti e due.
  - **`layout/app-start-auth.spec.ts`**, «a 401 in the middle of a session» (era `:263`, ora `:266`): rosso 2 volte su
    2 a 1 worker, con loadavg 17–25.
    - Appena `data-busy` diventa falso, `/assets` lancia senza `await` `loadFxPairSlugs()`: la GET delle route e 24
      `POST /fx/currencies/convert`.
    - Le `convert` partono a cavallo di `clearCookies`, quindi il primo 401 può nascere su `/assets`. L'interceptor
      porta giustamente a `/?redirect=%2Fassets`.
  - **`ai-export/ai-export-memory.spec.ts:66`**: rosso a 4 worker nel setup.
    - `setupAiExportPage` faceva `login()` e poi `setLanguage('en')`, con 5 s per tutta la catena del bootstrap
      (V-27).
  - **Chiusa il 13/10** nel checkpoint V-25/V-21, via test-author, decisione del coordinatore:
    - in quel test, `GET /fx/providers/routes` è servita localmente con zero coppie, mentre il 401 resta vero e del
      backend;
    - `setupAiExportPage` aspetta l'arrivo: l'URL fuori da `/` e `app-shell` visibile.

    Verdi `front-utility auth` 29/29 e `front-ai-export all` (18 E2E e 426 Vitest), a 1 e a 4 worker, col DB pulito.
    Dettagli: piano della 46, §12.10.

- ✅ **V-27 · `login()` ritorna appena sparisce il form, prima dell'arrivo** — basso; V (triage di V-26), 13/10.
  - `auth-helpers.ts` `login()` ritorna quando il form sparisce, mentre `/` carica ancora il bootstrap: impostazioni
    utente, onboarding, impostazioni globali. Solo dopo porta a `/dashboard`.
  - Ogni chiamante che ha bisogno dell'arrivo deve compensare da sé: `signIn()` di `app-start-auth`,
    `expectLandedOnDashboard` di `auth.spec` e, da V-26, `setupAiExportPage`.
  - Non compensa ancora `switchUser` di `ai-export-memory`, che fa `login()` e subito `setLanguage` per `TEST_USER_2`
    e `TEST_ADMIN`.
  - Cura strutturale: `login()` finisce all'arrivo, cioè URL fuori da `/` e `app-shell` (o `welcome-shell`) visibile.
    I chiamanti sono più di 100, quindi serve una validazione dell'intera suite. Dettagli: piano della 46, §12.10.
  - **Portata nella 1.2** dal coordinatore il 13/10: nella run completa di R è la causa di 9 rossi (auth ×5, AI Export
    ×4). Quei 9 erano su `a5653f9ef`, prima di V-20 e V-26, che li curano già sul posto. La cura strutturale resta per
    tutti i chiamanti, che sono 257 chiamate in 102 file.
  - `login()` deve chiudere anche su `onboarding-bootstrap-blocked`, che un test di `auth.spec` provoca apposta.
    Dettagli: piano della 46, §12.11.

  ✅ **Chiusa il 13/10**, nel lotto «rossi da carico» di V, via test-author.
  - `login()` (`frontend/e2e/fixtures/auth-helpers.ts`) ritorna solo quando è visibile uno dei tre stati d'arrivo:
    `app-shell`, `welcome-shell` o `onboarding-bootstrap-blocked`. Ha 30 s, e se l'arrivo non viene il messaggio nomina
    la schermata a vista e il suo path.
  - Lo scan delle 273 chiamate non ha trovato test che trattengano il bootstrap attorno a `login()`.
  - I commenti diventati falsi sono aggiornati, e le attese sul posto restano.
  - I budget dei test sono alzati dove l'header dichiara «a red must end on its own assertion»: `auth.spec` 120 s,
    `app-start-auth` 150 s, `ai-export-contract` 240 s.
  - Verde: 6 giri a 1 worker (102/102), poi le 8 categorie front a 4 worker.
- ✅ **V-28 · Il teardown di `jsCoverage` consuma i 30 s del test** — medio, perché blocca il gate di rilascio con coverage;
  run completa di R, 12/10, assegnata a V dal coordinatore il 13/10.
  - Il fixture (`frontend/e2e/fixtures/playwright.ts`, `jsCoverage`) è `{scope: 'test', auto: true}` senza un
    `timeout` suo. Raccoglie `window.__coverage__` e scrive circa 17 MB di JSON per test dentro il budget del test,
    che è di 30 s.
  - Sotto carico (load 45–112) questo è costato 15 rossi, «Tearing down "jsCoverage" exceeded the test timeout», con
    durate di 40–49 s. Da soli sono tutti verdi, in 11–19 s.
  - Esiste solo con `--coverage js`.
  - Cura: un `timeout` dedicato al fixture. In Playwright 1.61 setup e teardown hanno allora uno slot loro.
  - Fonti: rapporto di R, §3.2; devWiki `problems/jscoverage-teardown-spends-the-test-budget`. Dettagli: piano della
    46, §12.11.

  ✅ **Chiusa il 13/10**, nel lotto «rossi da carico» di V, via test-author.
  - La cura: `JS_COVERAGE_TIMEOUT_MS = 120_000` sul fixture. Precisazione, verificata nel sorgente di Playwright: senza
    `timeout` il teardown pesava sullo slot degli after-hooks, 30 s condivisi.
  - La prova del meccanismo: un ritardo temporaneo di 35 s nel teardown. Senza la cura è rosso, «Tearing down
    "jsCoverage" exceeded the test timeout»; con la cura è verde. Il ritardo è stato tolto.
  - La prova con coverage: `--coverage js --workers 4 front-fx all` ha 103 E2E verdi, nessun teardown in timeout, test
    più lungo 9,6 s, 97 file raw da circa 18 MB.
  - Doc allineate: la skill `testing-frontend`, `frontend-testing.instructions.md`, e in MkDocs
    `test-walkthrough/coverage-model.md` e `index.md`. Descrivono la pipeline istanbul vera; V8 e monocart non ci
    sono più.
  - La pagina devWiki la riallinea W, su indicazione del coordinatore.
- ✅ **V-29 · Togliere una coppia nuova dal bulk editor lasciava la metà nascosta: «Discard changes?» su un workspace
  vuoto** — basso, UX; evidenza E0 di V-21a, 13/10.
  - Il caso: si aggiunge una coppia nuova (TRANSFER o FX_CONVERSION dal form), poi la si toglie con «Mark for
    deletion» o «Delete selected». La griglia resta vuota, ma alla chiusura il workspace chiede di scartare.
  - Il controllo: una riga singola nuova, tolta allo stesso modo, si chiude senza chiedere.
  - La causa: `removeRow` filtrava solo `tempId`, quindi la partner nascosta (`pairedWith`) restava in `ops`.
    `resolveOps` la saltava, perciò non arrivava mai al server; `serializeOps` invece la contava. I dati non si
    toccavano.
  - Il difetto c'è dalla **1.1.0**.
  - **Chiusa il 13/10** in un commit a parte, `fix(transactions): …`, deciso dal coordinatore: `removeRow` toglie
    anche l'op con `pairedWith === tempId`.
    - Il rosso prima della cura: T7b e la variante «Delete selected» di `transactions-modals`, `Received: "asks to
      discard"`.
    - Dopo la cura: `transactions-modals` 20/20 a 1 e a 4 worker, e i vicini `tx-paired-edit` e `tx-split-promote`
      verdi a 1 e a 4 worker.
  - Se merita una riga 🐛 nel CHANGELOG lo decide il coordinatore. Dettagli: piano della 46, §12.10.
- **V-30 · Il fixture `jsCoverage` fonde le pagine di un test con `Object.assign`: può sottocontare** — basso, misura;
  visto dal docs-writer di V (lotto V-28), 13/10, letto nel codice e non misurato.
  - Il teardown (`frontend/e2e/fixtures/playwright.ts`, `jsCoverage`) scrive
    `JSON.stringify(Object.assign({}, ...entries))`: un oggetto per test, con le coverage delle sue pagine fuse per
    chiave di file.
  - Se due pagine dello stesso test caricano lo stesso file, i contatori dell'ultima sostituiscono quelli della prima,
    invece di sommarsi. Il report sottostima allora le righe raggiunte solo dalla prima pagina.
  - Cura possibile: un file per pagina, perché `js-coverage-report.js` fonde già per file con `istanbul-lib-coverage`;
    oppure la fusione con `createCoverageMap().merge()` nel fixture.
  - Fuori dal mandato di V-28, che riguarda solo il budget del teardown: dopo la 1.2. Dettagli: piano della 46, §12.11.
- **V-31 · `fx-sync-mock` lascia i tassi MOCKFX che il suo sync scrive** — basso; gate `front-fx all` a 4 worker di V,
  13/10. Dopo la 1.2, decisione del coordinatore.
  - `frontend/e2e/fx/fx-sync-mock.spec.ts` sincronizza le coppie MOCKFX del seed. Le route sono del seed, ma i tassi
    li scrive il test: dopo la categoria restano 372 righe (EUR/ILS, MYR, PHP e TWD, 93 ciascuna).
  - Il suo header diceva «this file writes nothing». In questo lotto si corregge solo l'header.
  - Oggi è tollerato: nessuno spec legge i tassi di quelle coppie, e il populate seguente li riscrive.
  - Cura possibile: togliere i tassi scritti, per coppia e finestra di date, in `afterAll`; oppure route proprie. Il
    motivo dell'header per non usarle, la rete di ripopolamento che le cancellava a metà giro, non regge più: la rete
    è spenta sopra 1 worker, e dopo V-25 nessuno spec distrugge più righe del seed.
  - Nello stesso gate, `fx-destructive` cancellava EUR/PLN ed EUR/SEK del seed: è curato in questo lotto. Dettagli:
    piano della 46, §12.11.
- **V-32 · Gli spec degli asset: scelte per posizione, pulizie che non verificano l'esito, un rischio latente** —
  basso; `v32-asset` di V, 13/10. Dopo la 1.2, per il confine del lotto deciso dal coordinatore.
  - In questo lotto sono curati i 4 asset mai cancellati (`asset-classification` ×3, `asset-modal` Test 4) e il
    `.first()` del Test 5 di `asset-modal`.
  - **Restano, per posizione**:
    - il Test 9 di `asset-modal` (`:247`), lo stesso difetto del Test 5: gli helper per curarlo sono già nel file;
    - `navigateToAssetByName` (`frontend/e2e/assets/assets-helpers.ts:52/57`) ripiega sulla prima card o riga dopo
      una ricerca sondata. La usa anche la galleria;
    - `asset-detail:292` sceglie la prima opzione di confronto;
    - lo Scenario 3 di `asset-event-delete` (`:291/:295`) prende la prima card, e il resto dipende da sonde.
  - **Restano, pulizie che non verificano l'esito**: `asset-modal` Bug K (`await createResponse` fuori dal `try`),
    Param, Benchmark e Type Tree; `asset-list` `:604`, `:846` e `:1007`; `dropFixture` di `asset-merge` (`:100`,
    anche lui con id per posizione); le pulizie degli eventi di `asset-event-delete` e `asset-data-editor`.
  - **Il rischio latente**: lo Scenario 2 di `asset-event-delete` (~`:220-270`) segna da cancellare ogni evento di Apple
    nella finestra di 3 mesi e salva. Oggi non cancella niente solo perché gli eventi del seed in quella finestra sono
    collegati a transazioni. Un evento scollegato, di un vicino a 4 worker o di un seed futuro, verrebbe cancellato
    davvero.
  - Nel Test 3 di `asset-classification`, la cancellazione della voce dipende da una sonda su `row-actions-*`.
    Dettagli: piano della 46, §12.11.
- ✅ **V-33 · Budget stretti dopo una navigazione: il dettaglio FX e la tabella delle transazioni** — basso; run
  completa di R, §3.4–3.5, 12/10; esteso dal coordinatore il 13/10.
  - **I rossi di R**:
    - `fx/fx-add-pair.spec.ts:219` aspettava `fx-detail-page` coi 3 s di default dopo il click sulla card;
    - CAC-001, `tx-import-ca-contract.spec.ts:131`, aspettava `tx-table` con 10 s, e la tabella è arrivata appena dopo.
  - Il verdetto di test-triage: assunzione d'orologio.
  - **Chiusa il 13/10**, via test-author.
    - `fx-add-pair`: 15 s di navigazione, e `data-chart-pair` prima della visibilità.
    - **Le attese di `tx-table`** dopo una navigazione: 38 siti in 36 spec delle transazioni, a 10 s o a 8 s. Ora
      aspettano prima `waitForSettled(transactions-page, 20 s)`, poi `tx-table` a 20 s.
    - **I budget di test** che non contenevano il gate: `transactions-table`, `tx-wac`, `tx-wac-mode`,
      `tx-broker-access`, `tx-tooltips`, `tx-paired-edit`, `tx-clone`, `tx-delete` e `tx-picker-pagination` passano a
      45 s; `tx-wac-fx` a 60 s. Il blame non dava nessuna ragione contraria.
    - Le 13 attese della galleria le gira il coordinatore a M.
  - Verde: `front-transaction all` a 4 worker, 365 E2E, al seed, e `front-fx all` a 4 worker.
  - Sotto osservazione nella run finale: il gruppo a 30 s, che lascia circa 10 s a login e test. Dettagli: piano della
    46, §12.11.
- **V-34 · La pulizia di `trackTransactionWrites` controlla solo lo stato HTTP** — basso; segnalato da M tramite il
  coordinatore, 13/10. Dopo la 1.2.
  - `cleanup()` in `frontend/e2e/fixtures/db-cleanup.ts` (~`:130-141`) cancella le righe create dalla pagina con un
    `POST /transactions/commit` e verifica solo `res.ok()`.
  - Non legge `committed` né gli esiti per id. Una delete rifiutata dentro una risposta 200 passerebbe quindi in
    silenzio, e la pulizia fallita non si vedrebbe: un esito negativo per id, per esempio un `RESTRICT`, o un commit
    respinto dalla validazione (saldo, accesso).
  - Lo usano 6 spec: `transactions-modals`, `tx-bulk-promote-exec`, `tx-clone`, `tx-commit-all-types`,
    `tx-wac-formmodal`, `tx-wac-unit-toggle`.
  - **Nel lotto V-27/V-28/V-33 non ha nascosto niente**: dopo ogni giro di quegli spec, e dopo `front-transaction all` a
    4 worker, il DB era al seed (76 transazioni, id massimo 76).
  - Cura possibile: richiedere `committed === true` e il successo di ogni esito di delete, nominando gli id rimasti,
    come fanno già le pulizie di V-25 e degli asset.
- **V-35 · `fx-detail:923`: il pannello «aesthetics» resta aperto dopo il secondo click, una volta, sotto carico** —
  medio, perché il meccanismo è sconosciuto; gate del treno 88 (6150, 1 worker, carico 100–158), triage di V, 13/10.
  **Sotto osservazione.**
  - **Il rosso**: dopo il secondo click, `not.toBeVisible()` scade coi 3 s. Il call log dice «10 × locator resolved to
    <div data-testid="fx-detail-aesthetics-panel" …> unexpected value "visible"»: il processo era vivo, e il pannello è
    rimasto davvero aperto. Da solo è verde 17/17.
  - **Nel codice** (`frontend/src/routes/(app)/fx/[pair]/+page.svelte`) il toggle fa solo
    `showAesthetics = !showAesthetics`. Il pannello è un `{#if}` semplice, senza `{#key}`, transizioni o async.
    `showAesthetics` torna `true` solo dal toggle, o dai ripristini dell'editor dei dati, che si apre solo dai suoi
    bottoni. Nessun meccanismo trovato.
  - **50 giri di sonda, tutti verdi**, coi passi esatti del test, sotto CPU ×1–20, API ritardate, pause e richieste
    tardive (`/tmp/libreFolio_v_fxaes_*`).
  - **Quello che c'è ora**, decisione del coordinatore:
    - `aria-expanded` sul toggle dell'estetica; quello dei segnali l'aveva già;
    - i due test di `fx-detail` (e `fx-destructive`) verificano `aria-expanded` dopo ogni click e poi il pannello;
    - su un rosso allegano e stampano il registro in pagina, `[fx-panel-log]`: click, `aria-expanded`, pannelli,
      `data-busy`, errori.

    Il prossimo rosso dirà da solo se il click non è arrivato o se lo stato si è ribaltato.
  - Se succede: leggere il registro; se lo stato torna `true` senza un click, è un difetto di prodotto. Dettagli: piano
    della 46, §12.12.
- ✅ **V-36 · `setLanguage` scommetteva 3 s sul caricamento del dizionario** — basso; rosso di M nella
  `toolbar-width-sweep` (`assetsList › fr`, carico 60), 13/10.
  - `setLanguage` (`frontend/e2e/fixtures/auth-helpers.ts`) aspetta lo stato giusto: `<html lang>` e
    `data-i18n-ready`, pubblicati da `routes/+layout.svelte` quando svelte-i18n ha caricato il chunk del dizionario,
    circa 290 KB. Lo faceva però coi 3 s di default, e il bottone del selettore con 5 s.
  - **Chiusa il 13/10** in un checkpoint di V.
    - Il rosso deterministico: il chunk del dizionario trattenuto 5 s dà «Expected "it", Received "en", Timeout 3000ms».
    - La cura: `LANGUAGE_SWITCH_MS = 15_000` sulle tre attese. Col ritardo ancora attivo è verde.
    - `toolbar-width-sweep` 15/15 e `front-ai-export all` sono verdi a 4 worker.

    Dettagli: piano della 46, §12.12.
- **V-37 · Nel form, «valid» accanto a un errore che blocca Apply** — UX. Il minimo e 1b sono chiusi il 13/10 (✅,
  sotto); il pre-step completo, V-37b, resta per dopo la 1.2. Visto da test-author di V nello snapshot di T6, 13/10, e
  verificato nel codice da me.
  - Un BUY con quantità `-1`: il campo Qty è rosso con «must be > 0» e Apply è disabilitato.
  - «⚡ Validate now», però, risponde «valid»: il form manda al server la quantità col segno già corretto,
    `applySign('-1', 'positive')` → `'1'` (`frontend/src/lib/utils/transactions/txPayloadHelpers.ts:142-150`,
    `:243-249`).
  - L'utente legge insieme «valid» e un errore che gli impedisce di salvare.
  - Prove: `/tmp/libreFolio_v_t1/4-t2-t6.t6-results/error-context.md`, righe 1510-1535.
  - **La risposta del developer** (13/10, testuale): «diciamo che è un caso limite in effetti, la soluzione migliore
    sarebbe nel form di disattivare il validate finchè tutti i campi obbligatori non ci sono e non sono validi con le
    regole di scrittura. Però non una disabilitazione completa, più un pre-step, se lo clicco prima verifichiamo che gli
    obbligatori ci siano, poi che tutti siano nel formato corretto e se si si manda il pacchetto al server, se no, le
    celle con i problemi si evidenziano di rosso, mi hai capito? se è facile lo farei subito, altrimenti dopo la 1.2».
  - **L'analisi di V** (13/10, solo lettura del codice). Dettagli: piano della 46, §12.15.
    - **Il minimo**, circa mezza giornata, rischio basso:
      - «valid» non compare mai con errori del form: `isFreshlyValid` (`TransactionFormModal.svelte:942`) tiene conto
        di `hasSignViolation` (`:1304`) e di `dualValidationError` (`:831`);
      - niente pacchetto finché quegli errori ci sono: né dall'auto-validazione (`scheduler.enabled`, `:855`), né dal
        clic, che oggi scavalca `enabled` (`useValidateScheduler.svelte.ts:71`);
      - il clic porta al primo campo in errore.

      Tocca solo `TransactionFormModal.svelte`. Nessuna chiave i18n e nessuna asserzione esistente cambia; servono test
      nuovi (Vitest, più uno o due E2E).
    - **1b, la data**, da verificare a schermo, circa un'ora in più:
      - `SingleDatePicker` (`components/ui/date/SingleDatePicker.svelte:75`, `:150-165`) tiene a schermo un testo che
        non legge come data, anche una data futura, ma non lo dice al form;
      - per lettura del codice, validate **e Apply** usano quindi in silenzio la data di prima;
      - se si conferma: una callback additiva, e la data entra negli errori del form e nel cancello di Apply.
    - **Il pre-step completo**, 1,5-2 giorni, rischio medio:
      - il pulsante resta sempre cliccabile (oggi `disabled={!isFormComplete}`, `:2074`);
      - al clic controlla prima gli obbligatori, poi il formato; il rosso va su tutte le celle in errore e il fuoco sulla
        prima;
      - vale per singola, coppia e FX.

      Tocca il form, un helper puro nuovo e da 2 a 4 chiavi i18n nelle 4 lingue (file di U), più doc e galleria (di
      M). Cambiano `tx-fx-completeness:262`, `:363` e `:389`.
    - **Il bulk editor non serve**, in nessuna delle due parti: non ha campi suoi, le righe arrivano già normalizzate,
      e il suo «valid» (`TransactionBulkModal.svelte:3604`) riflette solo il server.
    - **La proposta**: il minimo, più 1b se confermato, nella 1.2; il pre-step completo dopo, come V-37b.
  - **La decisione del developer** (13/10, testuale): «Il minimo ora, più la data se la sonda la conferma; il pre-step
    completo dopo la 1.2 (Consigliato)». La sonda ha confermato la data: un BUY si salvava in silenzio con la data di
    prima, dalla v1.1.0 (`52b48fd83`).
  - ✅ **Il minimo e 1b, chiusi il 13/10** nel checkpoint V-37 di V. La cura è mia, i test sono di test-author, visti
    rossi prima della cura.
    - `SingleDatePicker` ha una prop facoltativa `onvaliditychange`.
    - In `TransactionFormModal` gli errori del form (quantità o segno della cassa rifiutati, due lati uguali, data
      rifiutata) bloccano «valid», l'auto-validazione, «⚡ Validate now» e Apply. Il clic porta al primo campo
      sbagliato.
    - **I test**:
      - due E2E di 1b (data futura e testo che non è una data) e uno del minimo (`-1`, nessuna richiesta, il fuoco,
        poi un solo giro), in `transactions-modals`;
      - due Vitest, del form e del picker.
    - `front-transaction all` a 4 worker: 369 E2E e 887 Vitest verdi, col DB al seed.
    - La doc è in `user/transactions/form.en.md`, solo EN: M la porta nelle altre lingue.
    - Dettagli: piano della 46, §12.16.
  - **Resta aperto, dopo la 1.2: V-37b, il pre-step completo** (§2 dell'analisi): ⚡ sempre cliccabile, prima gli
    obbligatori e poi il formato, il rosso su tutte le celle in errore, in singola, coppia e FX. Circa 1,5-2 giorni.
- ✅ **V-38 · Il form elenca un problema di saldo tra i problemi dei campi** — basso, UX; letto nel codice da test-author
  di V, 13/10, e verificato da me; **non visto a schermo**.
  - Il form divide i problemi per indice: `index >= 0` sono dei campi, `< 0` di saldo
    (`TransactionFormModal.svelte:944-945`).
  - Il server attacca `balanceCashNegative` alla riga che lo causa (`index: 0`). Nel form finisce quindi sotto il titolo
    dei problemi dei campi, non sotto «This configuration causes data inconsistencies».
  - Il bulk editor divide invece per codice (`isBulkBalanceIssue`, `utils/transactions/bulkDisplay.ts:145`), e mette lo
    stesso problema sotto il titolo del saldo.
  - Da verificare a schermo prima di decidere. Dettagli: piano della 46, §12.14.
  - ✅ **Chiusa il 15/10** da W (lotto K1 della 1.3, `532a1fd9c`; in `dev_release2` con `d915c869f`):
    visto a schermo, poi il form divide i problemi per codice come il bulk editor (`isBulkBalanceIssue`).

## 09 · Feedback e backlog strutturale

Dettagli: [README della 09](09_feedbackJobs/README.md), «Cosa resta aperto» in cima (verifica Q del 09/10). Prevale
sulle tabelle del 21/09, «Il residuo vero» compreso. Correzione della ricognizione finale di Q, 11/10.

- **P4-7 · Il ciclo di vita delle cache dei prezzi nel frontend** — medio; il registry è una `Map` senza limite né
  eviction, e niente lo azzera a fine sessione. Dettagli: README della 09, «Cosa resta aperto», e
  [`00_backlog_strutturale_P4.md`](09_feedbackJobs/00_backlog_strutturale_P4.md).
- **P4-9 · La conversione dei test specchio** — basso; gli specchi di `chartCoreHelpers.test.ts` leggono ancora il
  sorgente invece di eseguire le funzioni. Dettagli: idem.
- **P4-10 · I sei siti di Risk fuori dal canale di mascheramento** — basso, da riverificare dopo il Round 2 della
  privacy. Dettagli: idem.
- ✅ **R2 · `VERSION` stantio** — medio; manca la decisione: leggerlo solo senza `.git/`, o cancellarlo dopo la build.
  Dettagli: idem, e [08](09_feedbackJobs/08_review_visiva_20260922.md) R2. **Chiusa da H il 15/10** (piano 1.3, §10
  n. 12): con `.git` vince `git describe`; `VERSION` vale solo senza `.git` o quando git fallisce; prima di tutto
  `LF_APP_VERSION`, che la pipeline di rilascio esporta già per la build del frontend (`6e78b8c96`, in `dev_release2`
  con `9deb0ea08`).
- **§2.4 · Il guardiano del catalogo finto** — basso; debito dichiarato, non verificato nel codice. Dettagli: idem, e
  [09](09_feedbackJobs/09_reperti_analisi_statica_20260922.md) §2.4.
- **SP15 · `SensitiveValue`** — peso da stimare; sospeso dal 21/09 perché non c'era nessun consumatore misurato, e non
  sta in nessun altro backlog. Dettagli:
  [Round 1 della 24](../phases/24_privacyGlobal/plan-phase00PrivacyGlobalRound1-MaskingCore.prompt.md), passo 5.
- SP14, il Rebalancer, sta nella sezione D (riga 14 della 13).

## U · Plugin modulari e traduzioni (45)

Dettagli: [piano della 45](45_pluginModules/plan-phase00PluginModules.prompt.md), sezioni «7», «9» e «10». Ogni plugin è
una cartella `<famiglia>/<nome>/` con `plugin.py`; le traduzioni vengono da `base/`, dai sottosistemi e dai frammenti dei
plugin.

- **U-B1 · Le traduzioni dei plugin montati a runtime** — medio; U, 12/10. È il limite che la decisione D-1 chiede di
  registrare, delegata al coordinatore dal developer: un plugin montato con un volume di docker-compose ha il codice
  caricato ma non le traduzioni, che si uniscono al build, quindi mostra il nome del backend. Servirà un'unione a
  runtime: il backend serve i frammenti, il frontend li aggiunge con `addMessages`. Dettagli: piano della 45, sezioni
  «0» e «9».
- **U-B2 · Le sorgenti dei sottosistemi accanto al codice** — basso; U, 12/10, decisione D-B del developer: per la 1.2
  le 17 sorgenti restano in `frontend/src/lib/i18n/<sottosistema>/`. Quando T-FE2…FE11 crea le cartelle per
  funzionalità (`lib/features/<x>/`), ogni sottosistema si può spostare con la sua funzionalità: è un `git mv` della
  cartella, che porta con sé il suo `prefixes.txt`, più un glob in più in `discover()` di `scripts/i18n_catalog.py`. Le
  chiavi e i prefissi non cambiano, e `dev.py i18n check --against <rev>` prova l'equivalenza. Dettagli: piano della 45,
  sezioni «2.5» e «9».
- **U-B3 · Le icone dentro la cartella del plugin** — basso; U, 12/10, decisione D-7, che le lascia dove sono nella 1.2.
  Servono `static/` nella cartella, la rotta di `uploads.py` e `generate_static_url` nelle 3 basi. Dettagli: piano della
  45, sezione «9».
  - **Schwab resta dopo la 1.2** (U-6b, 13/10). U-6 aveva messo nel pacchetto il logo di Schwab, e il developer l'ha
    annullato: «ci blocca solo perchè abbiamo fatto tante richieste tutte assieme. comunque mostrare la valigetta è
    accettabile».
    - L'ipotesi del developer: il controllo anti-bot di www.schwab.com risponde alle nostre raffiche di richieste, cioè
      galleria ed E2E, e gli utenti non ne sono toccati.
    - L'`icon_url` resta `https://www.schwab.com/favicon.ico`.
    - La strada provata in U-6 è nella storia, nel commit `a6d1754ed`: il logo, la mappa `SINGLE_PLUGIN` di
      `compose_broker_icons.py` e `generate_static_url`. Si riprende se il blocco tocca gli utenti.

    Dettagli: piano della 45, sezione «10», U-6 e U-6b.
- **U-B4 · `sample_reports/` per plugin** — basso-medio; U, 12/10, decisione D-7. Ci sono 25 percorsi fra E2E e test
  backend. Dettagli: piano della 45, sezione «9».
- ✅ **U-B5 · I vecchi percorsi `<famiglia>/<nome>.py` fuori da U** — basso; U, 12/10. Chiusa: le due parti erano già
  fatte.
  - Il devWiki: W, passo D del 12/10 (`a74a5bfb6`, treno 63). Ha spostato 112 citazioni in 54 pagine e ne ha lasciate 8
    come storia.
  - `financial-theory/fundamentals/day-count.{en,it,fr,es}.md:10`: già corretto nelle 4 lingue (`18e872872`).

  Verifica di U, 13/10:
  - `check_source_paths` non trova percorsi di plugin; i suoi 5 percorsi mancanti sono artefatti ignorati, fuori da U;
  - i percorsi piatti di plugin restano solo nella cronaca, `log.md` e `raw/ingest-registry.md`.

  Dettagli: piano della 45, sezioni «3» e «10», U-5.
- **U-B6 · Il server di sviluppo non segue le sorgenti del catalogo** — basso; U, 12/10.
  - Oggi: `npm run dev` genera il catalogo all'avvio (`predev`), e i comandi `dev.py i18n` lo rigenerano da soli.
  - Il limite: una modifica a mano di una sorgente (`base/`, un sottosistema, un frammento di plugin) arriva al server di
    sviluppo solo dopo `dev.py i18n build` o `npm run i18n:build`.
  - La soluzione: un plugin Vite che osserva le sorgenti e rilancia la build.

  Dettagli: piano della 45, sezione «10», U-2.
- **U-B7 · `dev.py i18n add` non conosce gli spazi dei plugin** — basso; U con docs-writer, 12/10.
  - Oggi: senza `--into`, la prima chiave di un segnale o di un tool nuovo (`signals.<nuovo>.name`, `tools.<nuovo>.name`)
    va nel sottosistema col prefisso dichiarato (`charts`, `tools`), senza avviso, e la segnala solo
    `utils gate-plugin-i18n-ownership`. Le guide dicono di passare sempre `--into` per le chiavi di un plugin.
  - La soluzione: un avviso in `route()` quando la chiave apre un ramo nuovo sotto un prefisso di sottosistema che
    contiene già frammenti di plugin («se è un plugin nuovo, `--into <famiglia>/<plugin>`»). Non servono i registri,
    bastano i proprietari.

  Dettagli: piano della 45, sezione «10», U-4.
- ✅ **U-B8 · Un passo superato nella guida dei plugin BRIM** — basso; docs-writer in U-6, 13/10.
  - Il passo 3 di «Register the user-facing docs» in `brim_plugin_guide.md` (la «Capacity table», l.~1598) chiede
    una riga nella tabella `??? info "📊 Importer Capabilities"` delle pagine `user/transactions/import/index.*.md`.
    Quella tabella non c'è più.
  - Fuori dal perimetro di U-6, quindi non l'ho toccato: si toglie il passo, oppure lo si riscrive per le schede
    dell'indice.

  Dettagli: piano della 45, sezione «10», U-6.
  ✅ Chiusa nella 1.3 (19/10, contabilità del coordinatore): W4 CP6 di W, il passo «Capacity table» tolto dalla guida
  insieme allo spostamento in `services/brim/`, commit `548a0688d`, entrato in `dev_release2` con `155d9b050`.
- **U-B9 · I broker dei dati mock non hanno un plugin d'importazione predefinito** — basso; U, 13/10, nel controllo a
  occhio di U-6.
  - `populate_mock_data.py:300-369` scrive `brim_plugin_key` nei dizionari dei broker, ma `Broker(**broker_data)` lo
    scarta senza dirlo, e il campo viene solo stampato. Il campo vero è `default_import_plugin`.
  - Così nel DB di test e nella galleria nessun broker mock usa l'icona del suo plugin: ognuno resta sul favicon del
    portale. Per «Charles Schwab» questo vuol dire la valigetta, quando il sito blocca le nostre raffiche.
  - **Dopo la 1.2.** Il developer, 13/10: «mostrare la valigetta è accettabile», anche in galleria.
  - La correzione è di M (galleria) o dei dati di test: rinominare la chiave cambia le icone di tutti i broker mock.

  Dettagli: piano della 45, sezione «10», U-6 (passo 8) e U-6b.

## L · Designer Lab (55)

- **L-1 · Designer Lab v1** — medio; coordinatore, 14/10, approvato dal developer lo stesso giorno.
  - Pagina nascosta `/designer-lab`, solo nelle build di debug; il server di test la serve già, perché usa sempre la
    build di debug.
  - Catalogo dei colori generato al build.
  - Modifica dal vivo di variabili CSS, colori dei fogli di stile e colori dei grafici.
  - Export JSON + Markdown con file e riga, per l'agente.

  Dettagli: [progetto](../Phase_1/10_colorSystem/design-designerLab.md); piano del figlio in `../Phase_1/10_colorSystem/L-designerLab/`.
- **L-2 · L'inventario Python legge il catalogo JS** — basso; L, 14/10 (decisione 4: una fonte sola, passaggio separato).
  Oggi le due implementazioni danno conteggi identici (verifica riga per riga) e devono restare allineate a mano.
  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «Passo 1».
- **L-3 · Campionario dei componenti negli stati principali** — medio; L, 14/10 (decisione 6: dopo la v1).
  Dettagli: [progetto](../Phase_1/10_colorSystem/design-designerLab.md), §11.6.
- **L-4 · Salvataggio dell'export sul server di test** — basso; L, 14/10 (decisione 3: solo download nella v1).
  Serve un endpoint solo in modalità test. Dettagli: [progetto](../Phase_1/10_colorSystem/design-designerLab.md), §11.3.
- **L-5 · Contratto `themeRevision` con R** — basso; L, 14/10.
  - Se R-1 sostituisce gli osservatori dei grafici con uno store, il Lab può incrementarlo invece di riapplicare le opzioni.
  - Oggi la ri-applicazione dal vivo copre tutti i grafici.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «Correzioni al progetto» 1.
- **L-6 · Indice «visto dal vivo» per valore** — basso; L, 14/10.
  - Le schede dell'app non riferiscono al Lab quali valori del catalogo hanno davvero visto, nel CSSOM o in `setOption`.
  - La portata reale di L3 (colori derivati, palette predefinita di ECharts) resta dichiarata ma non misurata.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «Correzioni al progetto» 2.
- **L-7 · Accettazione dal vivo con la designer** — medio; L, 14/10: è la DoD esterna del passo 4, su
  `scripts/visual_review/designer_live.sh`. Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «Passo 4».
- **L-8 · File del componente dalla classe di scope** — basso; L, 14/10 (passo 5b).
  - Il selettore conosce la classe di scope Svelte dell'elemento puntato (`svelte-xxxx`), ma non il file `.svelte` a cui appartiene.
  - Oggi i candidati vengono da test id, regole e usi delle classi. Una mappa classe → file costruita al build, solo in debug, aggiungerebbe il file del componente come candidato.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «Passo 5b».
- **L-9 · Limiti noti del selettore di elementi** — basso; L, 14/10 (passo 5b).
  - Non si possono puntare gli elementi con `pointer-events: none`.
  - I colori dei grafici calcolati da funzioni (tooltip) restano al piano globale anche dentro una specializzazione.
  - Uno sfondo visto attraverso, che viene da fuori del componente, non si specializza.
  - Il percorso strutturale del selettore di anteprima si rompe se il DOM cambia.

  Dettagli: pagina developer `designer-lab.md`, «Known Limits».
- **L-10 · Ruoli di T nel catalogo** — basso-medio; L, 14/10 (avviso del coordinatore sul workstream T). **Dipende da T-1 nella base di L.** ✅ **Chiusa il 15/10**: commit `a6f29298e` (base `9d57aa4c0`), fuso con `dev_release2` in `fb2526cc4` e validato lì.
  - Classi `*-lf-<nome>`: il conteggio va esteso nello scanner **e** in `color_inventory.py` con una riga ciascuno, per tenere la parità. La riga Python di `tw_custom_re` è **assegnata a L** come estensione di ④ (coordinatore, 14/10 alle 21:59). Si fanno entrambe nello stesso cambio; la parità si verifica dopo, sullo stesso albero; i numeri prima e dopo vanno nell'handoff.
  - Catena `@theme inline`: `--color-lf-card: var(--lf-surface-card)` è un alias che a runtime non esiste. La palette e le «Variabili dell'app» devono mandare la modifica a `--lf-surface-card`, non all'alias.
  - L1: oggi gli override stanno su `html`, quindi un sotto-albero `.dark`/`.light` che ridefinisce i ruoli tiene i suoi valori. Da scriverli anche sui selettori del token (`html.dark, .dark`). Oggi nessun sotto-albero lo fa.
  - Il selettore di elementi non ha bisogno di nulla: con `inline` la regola vincitrice legge già `var(--lf-…)`.
  - **Fatto (15/10):**
    - `lf-` è nelle due regex, nello stesso cambio. La parità è identica prima e dopo, con `custom` da 764 a 912.
    - Le definizioni di `@theme inline` portano `inline` e `alias_of`; la voce di palette porta `role`.
    - Chip, editor, impatto, export e candidati `class-use` passano dal ruolo. Nell'export le occorrenze di un alias hanno `raw` uguale alla classe.
    - L1 scrive anche su `.light` e `.dark` (`VAR_SELECTOR`).
    - Il selettore di elementi ha avuto bisogno di due ritocchi: i candidati via ruolo e il filtro con gli alias.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «Passo 6»; chiusura in «L-10 — Ruoli di T nel Lab».
- **L-11 · Interruttore «mostra i rimasti indietro»** — basso; proposta di T, 14/10.
  - Un contorno di debug, nel layer `lf-designer-lab` e sincronizzato tra le schede, sugli elementi con classi legacy (`-gray-`, `-slate-`, `bg-white`, `libre-`).
  - La lista va presa dal piano di migrazione di T.
  - Va fatto dopo il checkpoint dei passi 5b–6, quando T-1 avrà fissato i ruoli.
- **L-12 · Il runner può ricostruire in release a metà giro** — medio; L, 14/10, dal rapporto di `test-author` E2E. **Proprietario: chi mantiene il runner** (`scripts/test_runner/_frontend_common.py`).
  - Il server condiviso (`dev.py server --test`) costruisce il frontend in debug. Poi l'azione chiama `_ensure_frontend_build()` con `debug=False`, che ricostruisce **in release** se un file sotto `frontend/src` è più nuovo della build.
  - Se un sorgente cambia in quel momento, il server serve una build senza Lab e gli E2E del Lab cadono a metà giro. Il problema riguarda anche chiunque modifichi `src` mentre gira una suite.
  - Il 14/10 non è successo: ogni giro ha stampato «Frontend build is up to date».
  - Correzione possibile: allineare `_ensure_frontend_build()` alla modalità del server di test, cioè debug, o farlo saltare quando il server di test è già partito.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «Passo 6».
- **L-13 · Soggetti degli E2E del Lab che seguono la migrazione di T** — basso; L, 15/10, dal rapporto di `test-author` dopo il fuso con R.
  - Gli E2E del Lab ricavano a runtime come un componente scrive il colore (fuso con R). Restano però legati ad alcuni elementi dell'app, che le ondate di T cambieranno:
    - **W4**, transazioni: il sottotitolo della pagina passa a un'utility di ruolo (`text-lf-*`). `textPaletteClassOf` cerca una classe di palette e fallisce in modo esplicito. Con L-10 l'helper deve accettare anche le utility di ruolo, con la catena alias → ruolo. Il test L1, la sospensione e la scorciatoia vanno riportati su quel percorso. ✅ **Pronto con L-10 (15/10):** `colourSourceOf()` di `lab-helpers.ts` legge la classe, che sia di palette o di ruolo; per un'utility di ruolo ricava il ruolo dal CSSOM della pagina. Il test L1, la sospensione, l'export e la scorciatoia lo usano già, con chip = alias e bersaglio = ruolo; quando W4 entra non serve toccarli. `textPaletteClassOf` è stato tolto.
    - **B6**, pulizia: sparisce l'override P1 di `app.css` su `text-gray-500`. Il test del selettore in scuro va ritirato o riportato su un nuovo soggetto P1, se ne resta uno. Decisione di L in quel momento. → Con **L-20** (16/10) il test cerca da solo un override P1 rimasto e, se non ne trova, si salta con un messaggio.
    - **W6**, DataTable: l'intestazione con un'utility di ruolo chiede a `pickView` i candidati `class-use` via ruolo, cioè L-10 (2). Senza L-10 il controllo «candidato in `DataTable.svelte`» diventa rosso, e a ragione. ✅ **Coperto da L-10 (15/10):** i candidati `class-use` passano dal ruolo, verificati dal test unitario in `pickView.test.ts` e dall'E2E del selettore sul `login-modal`.
    - **W5**, ponte sRGB per ECharts: se i colori dei grafici smettono di essere letterali, il test L3 e forse il motore L3 vanno rivisti.
  - Ogni rottura è esplicita: il test cade con un messaggio che nomina il presupposto mancante.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «Gallery candidata di L e validazione del fuso con R».
- **L-14 · Le classi scritte nei commenti contano come usi** — basso; L, 15/10 (L-10). **Proprietari: L per lo scanner, il coordinatore per `color_inventory.py`.** Il cambio va fatto in tutti e due insieme, per non perdere la parità.
  - Scanner e inventario Python contano le classi colore anche dentro i commenti, per tutte le famiglie. Dopo T-1, 5 dei 148 usi delle classi `lf` sono commenti di intestazione di `app.css` e `tokens.css`.
  - Nel Lab quei commenti compaiono fra gli usi, nell'impatto e fra le occorrenze dell'export: l'agente trova una riga di commento.
  - Correzione possibile: saltare i commenti CSS, JS e HTML nelle due implementazioni, nello stesso cambio, e rimisurare la parità.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «L-10 — Ruoli di T nel Lab», passo 1.
- **L-15 · Coppie di contrasto sui ruoli `--lf-*`** — basso; L, 15/10 (L-10).
  - Il pannello del contrasto del Lab confronta solo `--theme-text-*` con `--theme-bg-*`, più i bordi sulla card. I componenti migrati da T leggono i ruoli `--lf-*`, che il pannello non considera.
  - T ha già un gate di contrasto sui ruoli. Al Lab servirebbe per vedere dal vivo l'effetto di una modifica.
  - Le coppie vanno prese dalla tabella di T, non indovinate.
  - **Decisione D3 (coordinatore, 15/10):** T sposta `CONTRAST_PAIRS` da `themeTokens.gate.test.ts` a un modulo condiviso dopo T-8; il pannello lo legge da lì, senza copie.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «L-10 — Ruoli di T nel Lab».
- **L-16 · Giro 3 della designer nel Lab: ruoli di T-8 e colori di categoria** — medio; coordinatore, 15/10 (decisioni D1–D4). Il cursore dell'opacità (D2) è fatto e validato il 15/10. ✅ 16/10: validato su `e44383f13`, con i commit `4cc601e57` e `88ef51358`; la correzione di svelte-check è nel commit del checkpoint finale.
  - **Dopo l'ingresso di T-8:** verifica del catalogo sui ruoli nuovi (barra verde, stati espliciti, terminale, interruttore, ombre, viola AI, hover dei campi) e una prova L1 a mano. Niente isole `.dark`/`.light`: T usa ruoli dedicati (D2).
  - **Dopo l'ingresso del modulo di DV** (`lib/theme/chartCategories.ts`, contratto C1–C4): livello `category` (scheda «Categorie», aggancio C3 con `categoryColor` su `LabHook`, segnale C4 `notifyChartColorsChange()`, export e `verify-export`, una riga nella skill, test unit ed E2E). «Per valore» non basta: tipi e settori condividono 7 esadecimali in chiaro e 11 in scuro.

  - **In corso (15/10, notte; T e DV entrati in `a0915bef9`):**
    - i ruoli di T-8/T-8b sono tutti modificabili: 92 ruoli root e 88 alias, tutti col loro ruolo;
    - prefissi delle classi allineati a `PREFIXES` (D-a), con 2 chip delle ombre;
    - C4 emesso dall'engine, anche per le definizioni dei ruoli riscritte da L2;
    - livello `category` per chiave, scritto; `verify-export` trova le righe di categoria per chiave e tema;
    - `CHART_PATH_RE` accetta già `features/{dashboard,risk,brokers/lots}` (Y3, Y4b, Y5).

    Checkpoint intermedio il 16/10 alle 02:0x (`4cc601e57`). Copia sostituita da `lookupKey` di TD-1 dopo il merge di base `0b229ef95` (02:15).
    Validazione pesante su `e44383f13`, 16/10 03:26–03:50:
    - unitari 712, gate 186, svelte-check 0 errori dopo una correzione di una riga mia;
    - parità identica, MkDocs strict 0/0, `check-links` 96;
    - E2E `live` 12, `all` 17 più 624 unitari, `e2e` a 4 worker 17, `check-orphans` verde;
    - build di release con 0 tracce del Lab.
  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «Giro 3 della designer nel Lab» e «Cursore dell'opacità nell'editor».

- **L-17 · Il selettore di elementi nomina la categoria di una fetta** — basso; L, 15/10 (L-16, punto 5, nel backlog su decisione del coordinatore).
  - Oggi il selettore riporta i colori di un grafico, ma non la categoria (`type:ETF`) di una fetta: un colore può appartenere a due categorie, per esempio ETF e Tecnologia.
  - Servirebbe che il grafico dichiarasse la chiave della fetta puntata, nell'opzione o con un attributo dati; da concordare con DV.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «L-16 — Giro 3 nel Lab».

- **L-18 · Togliere i vecchi percorsi `components/` dei grafici dopo Y3 e Y5** — minimo; L, 16/10 (L-16). ✅ 16/10, nel checkpoint L-18 (il commit è del coordinatore).
  - `CHART_PATH_RE` (`scan-colors.mjs`) accetta i due percorsi finché gli spostamenti della 1.3 non sono finiti. Y4b è già entrato e `components/risk` non esiste più.
  - Dopo Y3 (`features/dashboard/`) e Y5 (`features/brokers/lots/`):
    - togliere i rami `components/(dashboard|risk|brokers/lots)` della regex, le righe sintetiche corrispondenti di `scanColors.test.ts` e la parentesi sui due percorsi in `designer-lab.md`;
    - aggiornare la costante `GROWTH` di `pickView.test.ts` e l'esempio JSON con `components/brokers/BrokerImportFilesModal.svelte`.
  - **Fatto (16/10, dopo l'ingresso di Y in `d5c3c3ae3`):**
    - `CHART_PATH_RE` senza `components/(dashboard|risk|brokers/lots)`;
    - test e doc aggiornati;
    - l'esempio JSON è su `LoadingSpinner.svelte:60`, perché il modale dei broker non ha più `#374151`;
    - il catalogo ha l'hash identico.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «L-16 — Giro 3 nel Lab», passo 7, e «L-18».

- **L-19 · Due esempi della pagina developer del Lab non corrispondono più al codice** — basso; L, 16/10 (`docs-writer` in L-18).
  - **Esempio di export, la modifica `--color-emerald-600@light`:** cita `src/lib/components/assets/AssetCard.svelte:133`, che oggi è `case 'up':`. L'unico `emerald-600` del file è alla riga 134, ed è `dark:border-emerald-600`, una variante scura, mentre la modifica è `@light`. Anche le cifre di `impact` (46/3/27) sembrano vecchie.
  - **Esempi del selettore e del suo export:** citano `src/lib/components/table/DataTable.svelte:1607` con `#64748b` come «rule-literal». Oggi la riga 1607 è `}`, e `#64748b` non c'è più nel file: la regola `th` legge `var(--lf-cmp-datatable-header-text)`, e il valore sta in `src/lib/theme/components/table.css`.
  - **Cosa serve:** una cattura nuova dal Lab, con export e selettore, non solo un numero di riga. La storia dell'esempio («una regola con un colore scritto») va scelta su un caso che esiste ancora. `TransactionsTable.svelte:993` (`tx-table`) è ancora giusto.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «L-18», fuori pista dell'esempio JSON.

- **L-20 · Il test del selettore in tema scuro non dipende più dal sottotitolo di `/transactions`** — basso; coordinatore, 16/10, per la migrazione di TR.
  - Il test «dark-theme pick» usava il sottotitolo di `/transactions` (`text-gray-500`, sovrascritto in scuro da `app.css`), che TR migra ai ruoli.
  - Ora inietta un `<p>` proprio sulla pagina `/` del visitatore, con la classe di un override `html.dark .<classe> { color: var(--…) !important }` che cerca nel CSSOM, e controlla che compaia esattamente la variabile letta dalla regola.
  - Senza nessun override di quel tipo, cioè dopo B6, il test si salta con un messaggio esplicito.
  - ✅ 16/10: `picker` 4/4 ed e2e del Lab 17/17 a 4 worker, alle 13:18. Il test nuovo passa senza saltare; nel checkpoint L-20 (il commit è del coordinatore).

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «L-20».

- **L-21 · Censimento a runtime dei colori predefiniti di ECharts e delle librerie** — medio; L, 16/10 (audit dei colori fuori metrica).
  - **Il problema:** `CHART_INIT_THEME` fissa solo il font, quindi ogni colore che un'opzione non scrive resta quello di ECharts. Il controllo statico ne ha confermati 5: i tooltip di `CorrelationHeatmap` e `ScatterChart`, tre `axisPointer`. Gli altri, cioè palette delle serie, stati `emphasis`/`blur`, etichette di `markLine`, non si possono vedere senza il browser.
  - **Proposta:** un giro con il Lab nella corsia 6152, su ogni pagina con un grafico:
    - leggere `getOption()` di ogni istanza;
    - togliere i colori scritti nel sorgente (catalogo, ruoli risolti, categorie);
    - ciò che resta sono i predefiniti.
  - Lo stesso giro può fotografare embedpdf e cheetah-grid. Serve uno slot con il server.

  Dettagli: [audit](../Phase_1/10_colorSystem/L-designerLab/audit-colori-fuori-metrica.md), §2 riga 8 e §5.

- **L-22 · Il catalogo del Lab elenca i colori scritti nei commenti** — basso; L, 16/10 (audit dei colori fuori metrica).
  - Sono ≈ 170 voci su 1450, per esempio `/* rgba(147, 51, 234, 0.25) */` accanto ai token di componente, le note della designer in `tokens.css` e i JSDoc di `colorAlpha.ts`. Non sono fonti: il cricchetto di T toglie i commenti.
  - Nelle schede compaiono come occorrenze in più di un valore, e nell'export finiscono tra le righe da cambiare, ma sono righe di commento.
  - **Correzione possibile:** l'annotazione salta i commenti, mentre il conteggio resta allineato a `color_inventory.py` per la parità, come per L-14.

  Dettagli: [audit](../Phase_1/10_colorSystem/L-designerLab/audit-colori-fuori-metrica.md), §3.

## R · Fattorizzazione colori a parità di aspetto (55)

Ogni ondata va dimostrata con una gallery dello stesso giorno `identical` (a parte le schermate instabili della 56).
Ciò che cambia l'aspetto non è di R: aspetta il report della designer (piano generale, «Decisioni del developer»).

> **Stato (R, 15/10): ✅ R chiuso.** Lotti A–D in `dev_release2` da `8fd8e494b`; cancello gallery unico A+B+C+D
> superato. Restano aperte R-5…R-8. Piano: [R-colorRefactor](../Phase_1/10_colorSystem/R-colorRefactor/plan-phase00ColorRefactor.prompt.md).

- ✅ **R-1 · Colori dei grafici in un modulo unico** — alto; coordinatore, 14/10.
  - Oggi: 4 set per assi, griglie e tooltip; 3 palette di allocazione; coppie chiaro/scuro scritte in 17 grafici.
  - Stessi valori, divergenze con un nome.

  Dettagli: [report 04](../Phase_1/10_colorSystem/analysis/04_charts_dataviz.md), §1–§3.
  - Stato (R, 14/10): codice nel checkpoint del lotto B (W3–W5). `lib/theme/themePair.ts` (`themed()`),
    `chartTheme.ts`, `chartPalettes.ts`, `chartColorScales.ts`: 229 siti in 33 file; neutri, palette, serie, formule e
    lotti; ogni divergenza ha un nome (`CHART_GAIN_LOSS.price` `#ef4444` / `.portfolio` `#dc2626`, box del tooltip
    comune e della candela, interesse di Growth e dei lotti…). Il dividendo di Growth e dei lotti è ora una voce sola. Si
    chiude con il commit e il cancello B.
  - Stato (R, 14/10), lotto D (W8, D4): il tema si legge da un solo punto, `lib/theme/themeMode.ts`
    (`isDarkTheme()`, `onThemeClassChange()`).
    - Interessa 16 osservatori e 23 letture di `classList.contains('dark')` in 19 file.
    - Il ridisegno a ogni cambio di classe di `<html>` resta.
    - Gate `themeModeReads`: niente letture o osservatori della classe fuori da `themeMode.ts`.
    - Piano: [R-colorRefactor](../Phase_1/10_colorSystem/R-colorRefactor/plan-phase00ColorRefactor.prompt.md), «W8».
  - ✅ Chiusa il 15/10 (R): lotti B (`75c45d923`) e D (`98731240d`), in `dev_release2` da `8fd8e494b`; cancello
    gallery unico A+B+C+D superato.
- ✅ **R-2 · Funzioni condivise per segno, stati e badge** — medio; coordinatore, 14/10.
  - Oggi: ternario guadagno/perdita in almeno 20 punti e 7 mappe di stato indipendenti.
  - Output identici.

  Dettagli: [report 03](../Phase_1/10_colorSystem/analysis/03_semantic_dynamic_logic.md), §1–§3.
  - Stato (R, 14/10): codice nel checkpoint del lotto A (W1–W2): `lib/theme/toneClasses.ts` (`SIGN_TEXT`, `SIGN_BAR`,
    `POLARITY_TONES`, `STATUS_TONES`, `KIND_TONES`), 42 siti di segno in 20 file e 11 mappe di stato in 9 file; CSS
    compilato identico alla baseline. Si chiude con il commit del checkpoint e il cancello A.
  - ✅ Chiusa il 15/10 (R): lotto A (`d80b9e0cd`), in `dev_release2` da `8fd8e494b`; cancello gallery unico
    A+B+C+D superato.
- ✅ **R-3 · Hex nei `<style>` in variabili CSS con lo stesso valore** (P8: `DataTable*`, modali file e immagini,
  `ConfirmModal`) — medio; coordinatore, 14/10. Dettagli: [report 02](../Phase_1/10_colorSystem/analysis/02_ui_components.md), §4.
  - Stato (R, 14/10): codice nel checkpoint del lotto C (W6–W7).
    - 16 componenti, 908 dichiarazioni, 604 token `--lf-cmp-<componente>-<ruolo>` con gemelle `-dark`, su `:root` in
      `lib/theme/components/{table,media,files,dialogs}.css`, importati dai componenti; le regole `.dark` restano
      dove sono.
    - I valori sono quelli che la build emetteva: esbuild quantizza i colori delle dichiarazioni, ma non quelli delle
      custom property.
    - Fuori dal CSS, cioè cheetah-grid e SVG in data URL, i colori vanno in `lib/theme/drawnColors.ts`.
    - Prove: CSS compilato identico regola per regola; definizioni presenti con ogni pagina che le usa; gate
      `themeComponentTokens` in `core-unit` (definizione unica, import, nessun token orfano).
    - Si chiude con il commit e il cancello C.
  - Stato (R, 14/10), lotto D (W9, D5): i quattro file P8 fuori elenco (pagina dei file, `BrokerImportFilesModal`,
    `ImportBrokerMismatchModal`, `CompactCashCell`).
    - 172 letterali diventano 124 token: 728 in tutto.
    - Letterali fuori da `lib/theme/**` e da `app.css`, dalla base al lotto D: hex da 1.554 a 88, funzioni colore da
      198 a 50.
    - Piano: [R-colorRefactor](../Phase_1/10_colorSystem/R-colorRefactor/plan-phase00ColorRefactor.prompt.md), «W9».
  - ✅ Chiusa il 15/10 (R): lotti C (`0b660632f`) e D (`98731240d`), in `dev_release2` da `8fd8e494b`; cancello
    gallery unico A+B+C+D superato.
- ✅ **R-4 · Funzioni fragili e refusi senza effetto visibile** — basso; coordinatore, 14/10.
  - `hexToRgba` e la concatenazione `+ '88'` accettano solo `#rrggbb`.
  - La meta `theme-color` scura è `#156534` invece di `#166534`.

  Dettagli: [report 01](../Phase_1/10_colorSystem/analysis/01_theme_foundation.md), §6.5; [report 04](../Phase_1/10_colorSystem/analysis/04_charts_dataviz.md), §5.
  - Stato (R, 14/10): codice e test nel checkpoint del lotto A (W0); `lib/theme/colorAlpha.ts`, meta corretta nei tre
    punti con gate di concordanza. Si chiude con il commit del checkpoint e il cancello A. Piano:
    [R-colorRefactor](../Phase_1/10_colorSystem/R-colorRefactor/plan-phase00ColorRefactor.prompt.md), «W0».
  - ✅ Chiusa il 15/10 (R): lotto A (`d80b9e0cd`), in `dev_release2` da `8fd8e494b`; cancello gallery unico
    A+B+C+D superato. Il timbro di `static/sw.js`, che andava rifatto con la correzione di `offline.html`, l'ha
    aggiunto il coordinatore all'ingresso (`23f6578f3`).
- **R-5 · `withAlpha` su `hsl()` con spazi produce un colore non valido** — minimo; R, 14/10.
  - `hsla(210 68% 44%, a)` mescola le due sintassi; oggi nessun chiamante ci passa (`lotColor` non arriva a `withAlpha`).
  - Da correggere quando un colore con spazi ci arriverà (fase B), con la gallery.

  Dettagli: piano R, «W0», nota «Fuori pista».
- **R-6 · Viola della linea di anteprima negli editor dei dati** — minimo; coordinatore, 14/10.
  - `color: '#a855f7'` scritto a mano in `assets/AssetDataEditorSection.svelte:248` e in
    `fx/FxDataEditorSection.svelte:129`.
  - Fuori dal perimetro di R: sono cartelle della 1.3. Passa alla fase B.
  - Fino ad allora è un'eccezione del cricchetto dei colori letterali, che dal 14/10 è il gate M2 di T: R gli ha
    consegnato l'elenco delle eccezioni.

  Dettagli: piano R, «W7», nota sulle eccezioni del cricchetto.
- **R-7 · Due viste non seguono il cambio di tema dal vivo** — basso; R, 14/10 (osservazione del `test-author` in W8).
  - `charts/SemiDonutChart.svelte` e l'anteprima a tabella di `files/FilePreviewModal.svelte` (cheetah-grid)
    leggono il tema quando disegnano, ma non hanno osservatore. Dopo un cambio di tema mostrano i colori vecchi fino
    al ridisegno successivo o alla riapertura.
  - Precede R. Correggerlo cambia il comportamento, quindi non è di R.
  - Riguarda T (B4) e il Designer Lab, che riapplica i colori dal vivo. La correzione è un `onThemeClassChange()`
    con ridisegno.

  Dettagli: [piano R](../Phase_1/10_colorSystem/R-colorRefactor/plan-phase00ColorRefactor.prompt.md), «W8», «Fuori pista».
- **R-8 · `--resolve` della baseline colori toglie un `--accept`** — basso; R, 15/10; per T.
  - `theme-roles.mjs --resolve` (`mergeBaselines`) dà a una riga presente sui due lati il m1 minore e **solo i
    colori che entrambi hanno**, senza guardare la base né le righe `~accept`.
  - Se un lato ha accettato uno scambio di colore e l'altro ha ancora la riga della base, il colore accettato
    sparisce e `--check` torna rosso. È successo il 15/10, nel merge della base di R con T-2, sulla correzione D3 di
    `themeStore.ts`: rimediato rilanciando lo stesso `--accept`, con l'OK del coordinatore.
  - Correzione proposta: un vero merge a tre vie (se un lato è uguale alla base, vince l'altro), oppure vince il
    lato che ha un `~accept` per quel file.

  Dettagli: [piano R](../Phase_1/10_colorSystem/R-colorRefactor/plan-phase00ColorRefactor.prompt.md), «Merge della base con T-2»; wiki
  `problems/colour-ratchet-resolve-drops-an-accept`.

## G · Gallery deterministica (56)

- ✅ **G-1 · 27 schermate instabili su 177** — medio; coordinatore, 14/10, misura di due esecuzioni identiche.
  - Sfondo animato del login non congelato.
  - Scorrimento di pochi pixel nel pannello lotti.
  - Altre instabili da analizzare.

  Dettagli: [README della 56](../Phase_1/10_colorSystem/G-galleryDeterminism/README.md) e [stabilità](../Phase_1/10_colorSystem/G-galleryDeterminism/evidence/stability-2026-10-14.md).
  - *Stato al 14/10 (G):* assestamento comune dello scatto e correzioni dei percorsi nel checkpoint di G. Nelle run
    filtrate dello stesso giorno 10 delle 27 instabili sono diventate stabili e 10 «rumore minimo». La prima misura
    completa è stata invalidata dalla fuga del prezzo live (G-6). Misura finale il 15/10 su `dev_release2` con G dentro.
    Dettagli: [piano della 56](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md), passi 3 e 6.
  - *Stato al 15/10 (G):* misura finale `g-final3` (X = `2338aaf79`, 6 worker, `live_price_check` pulito): **6 instabili
    su 177**.
    - 2 di solo contenuto, accettate: ordine delle immagini del seed, ordine dei file del set.
    - 4 di inquadratura (`detail-measures*` e `about-plugin-diagnostics` su mobile, la pagina dietro `scheduler-config`):
      corrette nel checkpoint 2 di G, verifica nella corsia 6153.
    - Le 19 medie sono contenuto o residui di resa spiegati.
    - ✅ *Verifica del checkpoint 2:* 2 run da sole, 8/8 + 8/8 verdi, `live_price_check` 0. Diagnostica e
      `scheduler-log` stabili, `scheduler-config` e `detail-measures-active` `low`. Su `detail-measures` resta 1
      variante su 16 (G-11).

    Dettagli: [analisi del 15/10](../Phase_1/10_colorSystem/G-galleryDeterminism/evidence/analysis-final-2026-10-15.md).
  - ✅ **15/10, chiusa** con il piano della 56, su decisione del coordinatore delle 16:05.
    - La DoD è raggiunta con `g-final3`.
    - Dopo sono arrivati il checkpoint 2, G-9 e G-10, corretta da H.
    - **Resta aperta G-11.**
    - La conferma su due run complete viene dalla nuova coppia di riferimento (G-13).
- **G-2 · 4–5 test desktop falliti in ogni esecuzione completa a 10 worker, ogni volta diversi** — medio; coordinatore,
  14/10.
  - Login fermo su «auth-loading» nel primo blocco; modali delle transazioni.
  - Passano in un secondo tentativo isolato.
  - Da analizzare con `test-triage`: non sono classificati.

  Dettagli: README della 56.
  - *Stato al 14/10 (G):* nelle 2 gallery complete a 10 worker del 14/10 (carico 17–35) nessun rosso di auth-loading né
    dei modali delle transazioni. Rossi rimasti: promote-merge (assunzione del test, corretta da G) e un solo rosso che
    compare solo sotto carico, G-8. Da riconfermare con la misura finale del 15/10.
  - *Residuo (G, 14/10):* con carico esterno estremo (87–94 su 10 core, 5 corsie 1.3 con le suite backend) due attese
    di inquadratura sono scadute perché la pagina non rispondeva («waiting on the predicate»):
    - `frameTarget` (10 s) in `Asset detail classification`;
    - `headerOutOfShot` (scadenza predefinita di `expect`, 3 s) in `risk lab historical replay (injected)`.

    Da soli passano 2/2. Proposta non fatta: dare a `headerOutOfShot` la stessa scadenza di `frameTarget`. Dettagli:
    piano della 56, verifica del checkpoint.
  - ✅ **15/10, verdetto:** saturazione della macchina.
    - A 10 worker la prima r1 della misura finale ha avuto 8 rossi desktop nei primi 10 minuti, a carico 65, con
      richieste in volo da 10–20 s. Da soli passano.
    - A 6 worker: 0 rossi in 2 run complete.
    - `dev.py mkdocs gallery` avvia di default un worker browser per CPU più 3 worker server.
    - Il README del toolkit dice `-- --workers 6`; il default in `dev.py` passa a J (C-94), decisione del coordinatore.

    Dettagli: piano della 56, passo 5.
- **G-3 · `Dashboard Risk › what-if crisis replay` su desktop** — medio-basso; coordinatore, 14/10.
  - Fallisce in 2 esecuzioni su 3.
  - Il menu contiene «Global Financial Crisis», ma `chooseReplayPreset`
    (`frontend/e2e/fixtures/galleryRiskDashboard.ts:146`) non si ferma mai sulla voce.
  - Il messaggio d'errore non descrive ciò che succede.

  Dettagli: README della 56.
  - *Stato al 14/10 (G):* `chooseReplayPreset` riscritto (puntatore parcheggiato, cammino nei due versi, messaggio con
    gli ultimi stati), nel checkpoint di G. Verde in 4 run desktop sotto carico su 5: smoke a 6 worker, 2 complete a 10
    e `g-verify2` a 5 con carico fino a 94. La quinta arriva con la misura finale del 15/10.
  - ✅ **15/10:** verde in 6 run desktop sotto carico su 6, con le due della misura finale (`g-final3`). Dettagli: piano
    della 56, passo 2.
- **G-4 · Difetto del prodotto trovato col rumore: il chip del provider resta sul codice** — basso; G, 14/10,
  correzione autorizzata dal coordinatore. Causa: nell'intestazione del dettaglio asset il nome è
  `getAssetProviderName(code)`, che legge una `Map` non reattiva; se `assetInfo` arriva prima del catalogo dei provider
  (le due letture sono in parallelo), il chip resta su «yfinance» invece di «Yahoo Finance». Effetto: su mobile
  l'intestazione va a capo in modo diverso e lo scatto si sposta; un utente con rete lenta vede il codice. Dettagli:
  [piano della 56](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md), §2.1.
  ✅ 14/10: due `$derived` che leggono `$assetProvidersVersion` in `assets/[id]/+page.svelte`, test rosso→verde in
  `asset-detail.spec.ts`; nel checkpoint di G.
- **G-5 · Parte gallery di M-15 assorbita da G** — basso; developer, 14/10 (D4): le sonde `appears()` della gallery
  dove il componente rende sempre l'elemento diventano `expect`, insieme alle 7 sonde di classe C e all'attesa a tempo
  del passo 2 del wizard. Resta fuori `transactions/tx-picker-pagination.spec.ts:161`. Dettagli: piano della 56, §3,
  passo 3.
  ✅ 14/10: compito B del passo 3; nel checkpoint di G.
- **G-6 · La gallery perde la guardia offline a fine test e un poll del prezzo live scrive nel DB condiviso** — medio;
  G, 14/10, trovato nella prima misura finale.
  - Causa: l'`afterEach` della gallery toglie le rotte (`unrouteAll`) con la pagina ancora viva, poi la interroga.
    `cleanupGalleryAccount` fa lo stesso prima di `about:blank`.
  - Il dettaglio asset interroga `POST /assets/prices/current` ogni 30 s e ogni 60 s. Un tick nel varco arriva a Yahoo e
    riscrive la candela di oggi.
  - Effetto: il 14/10 alle 22:02:33 ha cambiato Apple a metà run e reso non valida la misura del rumore.
  - Correzione nel checkpoint di G: lasciare la pagina, poi togliere le rotte. Verifica:
    `scripts/visual_review/live_price_check.py` sugli snapshot, che dà 0 righe di prezzo live nel log della corsia
    (`g-alone4`, `g-verify2`, `g-alone5` del 14/10).
  - ✅ **15/10:** la correzione è in `dev_release2` dal checkpoint 1 di G (`0076f4269`). `live_price_check` dà 0 su
    entrambe le run della misura finale (`g-final3-r1`, `g-final3-r2`).

  Dettagli: piano della 56, passo 6.
- **G-7 · Lo stesso varco di G-6 negli E2E fuori dalla gallery** — basso; G, 14/10, su richiesta del coordinatore.
  Senza correzione, decisione del coordinatore.
  - Rotte tolte, poi `about:blank`: `assets/asset-browse.spec.ts:149`, `assets/asset-mobile-layout.spec.ts:113`,
    `layout/toolbar-width-sweep.spec.ts:320`.
  - Rotte tolte nell'`afterEach` e nessun `about:blank`: `layout/app-start-auth.spec.ts:193`.
  - Rotte tolte nel `finally`, sulla dashboard dopo un asset: `portfolio/dashboard-cache.spec.ts:334–563`.
  - Tutte proteggono `POST /assets/prices/current`. Correzione: lasciare la pagina prima di togliere le rotte.

  Dettagli: piano della 56, passo 6.
- ✅ **G-8 · Il catalogo dei Tools risponde 503 sotto carico** — medio-basso; G, 14/10, rosso della gallery
  `about plugin diagnostics`.
  - Causa: `ToolRoute` (`backend/app/api/v1/tools.py:92`) limita ogni richiesta `/tools` a
    `ingress_timeout_ms = 2000` (`backend/app/schemas/tools.py:83`). `GET /api/v1/tools/catalog` ha impiegato 2.649 ms
    con carico 35 su 10 core.
  - Effetto: il pannello di diagnostica in Impostazioni › About va in errore. Da solo il test passa 2/2, con scatti
    identici.
  - Per la regola [«un rosso solo sotto carico è un difetto del prodotto»](../../../LibreFolio_devWiki/wiki/concepts/load-only-red-is-a-product-defect.md)
    è un candidato difetto del prodotto: un host lento vedrebbe lo stesso errore.
  - ✅ **Chiusa il 15/10** da J (`6ce5ea180`; in `dev_release2` con `c75f08101`): l'autenticazione girava dentro la
    finestra d'ingresso di 2 s, prima che l'endpoint spostasse la scadenza. Le rotte senza corpo (catalogo,
    diagnostica) partono con il loro budget di 20 s; il compute tiene la finestra. Dettagli: piano J, §10 «G-8».
  - **Instradata a J (1.3, «Numeri e analisi»)** dal coordinatore, il 14/10, a priorità bassa, dopo il primo
    checkpoint di J. La voce nella sezione di J la scrive J.

  Dettagli: piano della 56, passo 6.
- ✅ **G-9 · La gallery può fotografare un indicatore non applicato** — basso-medio; coordinatore, 15/10 (candidata di L,
  `assets/detail-signals-macd`, mobile it chiaro: menu degli indicatori ancora aperto, MACD non applicato, 1 variante su
  16).
  - Causa (G, verificata nel codice): `selectIndicatorFromTree` (`frontend/e2e/gallery.spec.ts:165`) clicca l'opzione e
    non verifica l'esito: né il menu chiuso né la card dell'indicatore. `waitForSignalCardsSettled` (`:182`) aspetta che
    non resti nessun `signal-loading`, e passa a vuoto se la card non c'è ancora.
  - Correzione proposta (perimetro G, test-author):
    - dopo il clic, il menu chiuso (`aria-expanded` false sul trigger di `TreeSelect`) e una card `signal-card-*` con
      `data-signal-type` uguale all'opzione;
    - `waitForSignalCardsSettled` che richiede almeno una card.

    Un clic perso diventa un rosso con un messaggio chiaro, invece di uno scatto sbagliato. Vale per tutti i chiamanti:
    EMA, RSI, MACD, Bollinger.
  - *15/10, diagnosi completata (G, sola lettura):*
    - l'impronta dello scatto sbagliato ha il focus su `signal-tree-option-macd` e la pagina 342 px più corta: il
      mousedown è arrivato, il clic no;
    - `TreeSelect.open()` rimanda con due `setTimeout(0)` focus della ricerca e `scrollIntoView`; sotto carico l'input
      passa prima dei timer, e il mouseup cade su un'altra voce;
    - la correzione sceglie da tastiera tramite `aria-activedescendant`, dopo `settledToOpen`, e verifica l'esito;
    - chiamanti: 5, con il drawdown.

    Via del coordinatore alle 13:01: correzione e run filtrata nella corsia 6153.
  - *15/10, correzione fatta (test-author, `gallery.spec.ts`):* scelta da tastiera dopo `settledToOpen` e il puntatore
    parcheggiato, con l'esito verificato (menu chiuso, card del tipo). Nella run filtrata (`g-g9-w5`, 5 worker, carico
    86–150) l'helper è riuscito in tutti i 63 scatti presi: `focus` "-" in tutti, frame identici a `g-final3-r1`, MACD
    verde sui due progetti. 5 rossi fuori dall'helper (lista asset, clic sul tema, `textStill`, cattura), tutti di
    carico.
  - ✅ **15/10, chiusa (DoD 10/10):** codice in `5da3c9eba`, che entra in `dev_release2` con l'ingresso di G-9. Sulla
    revisione fusa `6f0198a08`, i 5 test con rossi di carico rifatti da soli a 1 worker sono verdi: EMA, RSI e Bollinger
    desktop, drawdown desktop e mobile. Su 40 scatti: nessuna opzione con il focus, frame identici a `g-final3-r1`,
    `live_price_check` 0.

  Dettagli: piano della 56, passo 8.
- ✅ **G-10 · Ordine casuale delle immagini del seed nelle liste di file** — medio-basso; G, 15/10, su segnalazione del
  coordinatore (`files/static-grid`: miniatura `men_04` in una corsia, `woman_07` in un'altra).
  - Causa (prodotto, verificata nel codice):
    - `seed_default_avatars()` (`backend/app/services/files/static_uploads.py:480`) scrive tutti gli avatar con lo
      stesso `uploaded_at` (un solo `now`) e con un UUID casuale come nome;
    - `list_uploads()` (`:335`) legge i metadati con `glob("*.json")`, cioè nell'ordine della directory, e ordina solo
      per `uploaded_at`. L'ordinamento è stabile, quindi a parità di data resta l'ordine dei nomi casuali, diverso a ogni
      populate.
  - Non dipende da file rimasti nella cartella dati: `--clean` svuota `custom-uploads`, marker compreso, e il populate
    ricrea gli avatar.
  - Effetto: `media/asset-picker-modal`, la prima instabile rimasta (16/16, 24 %), perché `AssetPickerModal` legge lo
    stesso `GET /api/v1/uploads`. Inoltre l'ordine in `files/static-grid` e `static-tab`, e la miniatura che cambia da
    una corsia all'altra. Oggi è contenuto accettato.
  - Correzione proposta (fuori dal perimetro di G): una chiave secondaria deterministica nell'ordinamento di
    `list_uploads`, per esempio il nome originale a parità di `uploaded_at`. Non cambia lo stile. Per un utente conta
    solo fra file caricati nello stesso istante. **Instradata alla 1.3 dal coordinatore il 15/10** (difetto del
    prodotto, probabilmente H, che ha `services/files`): la voce nella sezione di chi la prende la scrive lui.
  - ✅ **15/10, chiusa da H** con `b4533a949` (`fix(uploads): list same-instant uploads in a stable order`), entrata in
    `dev_release2` con `744f5a0ee`.
    - `list_uploads()` ordina sempre per `uploaded_at`, dal più recente. A parità di data ora decide il nome originale,
      senza distinguere le maiuscole, e poi l'id: gli avatar del seed, che hanno tutti la stessa data, escono sempre
      nello stesso ordine.
    - Test di H in `backend/test_scripts/test_services/test_static_uploads.py`.
    - Nella gallery si aspetta un ordine fisso in `media/asset-picker-modal`, `files/static-tab` e `files/static-grid`, e
      la stessa miniatura in ogni corsia. Da confermare alla prossima coppia di run dello stesso giorno sul target.
    - Voce collegata nella sezione di H: H-10, sulla cartella degli upload svuotata dal test dei servizi.

  Dettagli: [analisi del 15/10](../Phase_1/10_colorSystem/G-galleryDeterminism/evidence/analysis-final-2026-10-15.md).
- **G-11 · Su mobile, a scroll fermo in fondo alla pagina, l'header resta a volte visibile, solo in spagnolo** — basso;
  G, 15/10, verifica del checkpoint 2.
  - Sintomo: in `assets/detail-measures`, dove la pagina finisce prima del grafico (scroll fermo a 552 px), l'header
    dovrebbe essere nascosto come dopo ogni scroll verso il basso. È rimasto visibile 3 volte, sempre in es: 2 con il
    percorso vecchio (`g-final3-r1`, chiaro e scuro) e 1 con `frameTarget` (`g-c2-w1-a`, chiaro, ↕️ «header visible»);
    nelle altre lingue mai. Una variante su 16, circa 5,8 % dei pixel: la fascia dell'header.
  - Ipotesi: `Header.svelte` rimette `visible` senza scroll a ogni `syncScrollContext()`. Lo chiamano il focus che esce
    dall'header, il suo ResizeObserver, un `resize`, un cambio di `routeKey` (`pathname + search`), menu e blocco dei
    modali. Quale scatti in spagnolo non si vede dal codice.
  - Proposta (perimetro G, test-author):
    - una run filtrata con un osservatore, lato test, delle transizioni di `data-scroll-state` e degli eventi vicini,
      per trovare la causa;
    - nella gallery, a scroll fermo, un breve su-e-giù che porti l'header nello stato di uno scroll in basso, prima
      dello scatto.

    Se la causa è nel prodotto, va segnalata e non corretta qui.
  - *16/10, coppia di G-13 (r1↔r2):* ancora una variante su 16, sempre su mobile in `es/light`, e ora anche in
    `assets/detail-editor`: l'header è visibile in una run e nascosto nell'altra, 7,7 % dei pixel. Dettagli:
    [analisi G-13](../Phase_1/10_colorSystem/G-galleryDeterminism/evidence/analysis-g13-2026-10-16.md).

  Dettagli: [analisi del 15/10](../Phase_1/10_colorSystem/G-galleryDeterminism/evidence/analysis-final-2026-10-15.md), «Verifica delle correzioni».
- **G-12 · Due commenti nel codice descrivono ancora il vecchio helper della gallery** — minimo; G, 15/10, handoff di
  G-9; voce aperta su richiesta del coordinatore. **Instradata alla 1.3 dal coordinatore il 15/10**, perché
  `SignalTreeSelect.test.ts` è del perimetro dei grafici: la voce nella sezione di chi la prende la scrive lui.
  - Da G-9 (`5da3c9eba`), `selectIndicatorFromTree` (`frontend/e2e/gallery.spec.ts`) non tocca più il menu con il
    puntatore. Apre con ↓, aspetta il focus sulla ricerca, sposta l'evidenziazione con ↓/↑ leggendo
    `aria-activedescendant`, apre la famiglia chiusa con → e sceglie con Invio.
  - `frontend/src/lib/components/charts/SignalTreeSelect.test.ts`, la rete di caratterizzazione D-K1 (workstream K):
    - righe 16–17, l'elenco «Who leans on the contract»: attribuisce all'helper la prima famiglia aperta da sola, che
      oggi serve allo scatto `assets/detail-signals-tree`, e la famiglia chiusa aperta con un clic, che oggi si apre
      con →;
    - righe 306–310: il titolo «the way the gallery helper drives it» e il commento «expand the family only when it is
      collapsed, then click the option» descrivono il percorso vecchio.

    La riga 213 resta vera. Le asserzioni restano giuste: la scelta con il clic è un percorso degli utenti. Il percorso
    nuovo della gallery è già fissato dal blocco `keyboard` dello stesso file: ↓ sul trigger chiuso apre con il focus
    sulla ricerca, poi ↓/↑, → sulla famiglia chiusa, Invio sceglie. Va aggiornato solo il testo, nessuna asserzione.
  - `frontend/src/lib/components/ui/select/TreeSelect.svelte`, commento alle righe 17–19: resta vero, perché lo scatto
    `assets/detail-signals-tree` conta sulla prima famiglia aperta da sola (`defaultExpanded`). Da rileggere insieme
    all'elenco del test: ora la gallery si appoggia anche al contratto da tastiera.
  - L'intestazione del test vieta di cambiarlo «to accommodate the refactor». Qui il refactor non c'entra: cambia chi
    usa il contratto, non il contratto. Decide comunque il proprietario.

  Dettagli: [piano della 56](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md), passo 8.
- ✅ **G-13 · Nuova coppia di riferimento della gallery sul target, dopo l'ingresso di T** — medio; coordinatore, 15/10,
  assegnata a G.
  - Quando: T entra in `dev_release2` (D-T20, dopo la revisione di T-8 da parte del developer). Via e slot li dà il
    coordinatore; fino ad allora nessuna run.
  - Cosa:
    - due gallery complete dello stesso giorno sul target, con `-- --workers 6` e un populate nuovo per ogni run;
    - `live_price_check` dopo ogni run;
    - il diff con le maschere e l'analisi di stabilità.
  - Perché: diventano il riferimento delle ondate e della 1.3. Contengono le inquadrature del checkpoint 2, G-9 e G-10,
    che `g-final3` non ha.
  - Conferma attesa:
    - 0 instabili di inquadratura, salvo l'eventuale variante di G-11;
    - `media/asset-picker-modal` stabile;
    - fra quelle di contenuto, solo `brokers/import-nway-compare`, accettata.
  - ✅ **16/10, fatto.** Tre gallery complete di `a2c1c39f4`, a 6 worker, con un populate nuovo per run e
    `live_price_check` 0:
    - `g-ref13-r1`, 00:02: 6 rossi di carico (build di altre corsie);
    - `g-ref13-r2`, 00:52: verde;
    - `g-ref13-r3`, 05:28: verde.
  - **La coppia del rumore è r1↔r2**: 22 `stable`, 137 `low`, 18 `medium`, 4 `unstable` (il 15/10: 40/112/19/6).
    - Inquadrature uguali salvo G-11.
    - `media/asset-picker-modal` è `low`: G-10 funziona.
    - Restano `unstable` di contenuto `files/brim-report-sets` (G-17) e `brokers/import-nway-compare`.
  - **r2↔r3 non è una coppia del rumore: attraversa la data UTC.** Il planner del PAC data lo scenario con la minore
    fra la data locale e quella UTC (N26), quindi gli scatti PAC di r1 e r2, presi fra le 00:02 e le 01:31, mostrano il
    15/10. Regola nel README del toolkit: niente catture fra mezzanotte locale e mezzanotte UTC.
  - **Riferimento delle candidate del 16/10: `g-ref13-r3`**, con le maschere e la stabilità di `g-ref13__r1__vs__r2`.
  - **Candidata della notte `g-cand16a`** (`72e66d1a6`): verde, 2904 PNG.
    - Diff contro r3: 2720 immagini cambiate, quasi tutte per la migrazione ai ruoli di colore.
    - Foglio per il developer, ordinato per cambio visibile: `diffs/g-ref13-r3__vs__g-cand16a/contact_sheet.it.html`.
      Dal 16/10 il comando è nel toolkit, su richiesta del coordinatore: `gallery_tool sheet <diff> --lang it`.

  Dettagli: [analisi G-13](../Phase_1/10_colorSystem/G-galleryDeterminism/evidence/analysis-g13-2026-10-16.md) e
  [stabilità](../Phase_1/10_colorSystem/G-galleryDeterminism/evidence/stability-2026-10-16.md).
- **G-14 · Gli orari della gallery dipendono dal fuso della macchina** — basso; G, 15/10, su domanda del coordinatore
  (revisione di `settings/backup-ready`, B). **Proposta: valore e momento li decide il developer.**
  - Ogni istante si disegna nel fuso del browser, e la gallery lo lascia alla macchina: non c'è `timezoneId`.
    - Qui il fuso è Europe/Rome. La gallery pubblicata nasce invece in CI (`release.yml`, `mkdocs gallery --workers 4`),
      su un runner GitHub in UTC.
    - Quindi la documentazione mostra ore diverse da quelle delle run locali: pagina File, scheduler, `updated_at` delle
      impostazioni globali, Users, Backup.
    - I 5 grafici con un asse `time` di ECharts (Growth, AllocationHistory e i tre dei lotti) mettono le tacche alla
      mezzanotte locale.
    - Il backend non aggiunge differenze: `server_tz` e il default di `scheduler_timezone` sono sempre UTC.
  - Non riguarda il cancello di R né la coppia di G-13: sulla stessa macchina il fuso è lo stesso. Un istante fisso si
    disegna con l'offset di quell'istante, quindi nemmeno il cambio d'ora del 25/10 lo sposta.
  - Correzione proposta (perimetro G, test-author): una riga a livello di file in `gallery.spec.ts`,
    `test.use({timezoneId: …})`, accanto a quella di `launchOptions`. `playwright.config.ts` resta com'è.
  - Il valore:
    - `Europe/Rome`, consigliato: è il fuso di questa macchina, quindi non cambia nessuno scatto locale. Riferimenti e
      candidate restano validi in qualunque ordine d'ingresso; cambiano una volta sola le ore delle immagini generate
      in CI.
    - `UTC`: neutro e uguale alle immagini pubblicate oggi, ma cambia ogni scatto locale con un'ora o un asse del tempo.
      Dovrebbe entrare prima di G-13, e ogni candidata dovrebbe averlo nella base prima del suo cancello.
  - Verifica: una run filtrata di `settings/backup-ready`, che con `Europe/Rome` deve mostrare la stessa ora di prima.
- ✅ **G-15 · Su desktop, in spagnolo, la scheda Email esce dalla barra delle schede di Settings** — basso-medio; G,
  15/10, doppio lancio degli scatti nuovi (`g-new3-a/b`). **Difetto del prodotto, proprietario da instradare.**
  - Con le 3 schede nuove (Utenti, Backup, Email) l'admin ha 7 schede. In uno scatto desktop di 1280 px:
    - in inglese ci stanno, e resta lo spazio prima di «Admin»;
    - in italiano e francese ci stanno di misura;
    - in spagnolo «Copia de seguridad» le spinge oltre il bordo, e di «Correo» resta visibile solo la «C».
  - Anche nello scatto `settings/email`, dove «Correo» è la scheda attiva, si vede solo la sua «C».
  - Causa: in `routes/(app)/settings/+page.svelte` la card della barra ha `overflow-hidden`, e `TabBar` non scorre in
    orizzontale. Con la barra laterale e in spagnolo, la scheda si raggiunge solo con `?tab=email` o con la tastiera.
  - *Inferenza, non misurata:* nelle finestre fra 640 px (`sm:`, dove compaiono le etichette) e circa 1200 px, la barra
    può uscire anche nelle altre lingue.
  - Correzioni possibili, a scelta del prodotto:
    - `shrinkLabelsToFit`, che `TabBar` ha già e che Settings non usa;
    - uno scorrimento orizzontale che tenga in vista la scheda attiva;
    - un'etichetta spagnola più corta.
  - Per la gallery è deterministico: a e b sono identici. La correzione però cambierà gli scatti desktop di Settings in
    spagnolo, quindi conviene farla prima di G-13, o accettare un riferimento nuovo.
  - **Chiusa il 16/10.** La correzione è `affae6ffe` (15/10), la seconda proposta: la barra scorre in orizzontale e tiene
    in vista la scheda attiva. Verificata negli scatti `g-email-a/b` (`102fa9ec1`): «Correo» ed «E-mail» sono in vista.
    - Resta, in francese e spagnolo, una domanda di design: la prima scheda è fuori vista e la seconda è tagliata al
      bordo, senza segno di scorrimento nello scatto. L'ho girata al coordinatore.

  Dettagli: snapshot `g-new3-a/b` e `g-email-a/b` in `LibreFolio_visual_review`,
  `desktop/<lingua>/light/settings/email.png`.
- ✅ **G-16 · Scatto delle esposizioni del PAC (`tools/pac-result-exposures`)** — medio; coordinatore, 15/10 (TD-1: il
  developer approva dagli scatti le barre «ideale vs reale» sui colori delle categorie, D-T21).
  - Fatto da test-author, nel perimetro di G. Lo scatto è nel test `PAC allocator result`, fra il piano e la prova: 8
    scatti per progetto.
    - `framePacExposures` apre la sezione, che è chiusa di default, e ne verifica l'esito. Aspetta mappe e barre sugli
      stati pubblicati (`data-state`, `data-chart-ready`) e controlla le righe attese.
    - Inquadratura su desktop: dal titolo, e lo schermo alto tiene la sezione intera.
    - Inquadratura su mobile: il corpo finisce in fondo allo schermo, con le barre intere e sopra quanto ci sta delle
      mappe.
    - `closePacExposures` la richiude, così gli scatti esistenti restano com'erano.
  - Contenuto: le due mappe (USA, e la quota non classificata elencata sotto) e le barre per tipo (ETF, STOCK).
  - **I settori restano piegati in una riga**: «nessuna classificazione dichiarata · 100% non classificato».
    - Il seed divide Apple in Technology e Services e Microsoft in Technology e Cloud. Ma Services e Cloud non sono
      settori di `FinancialSector`, quindi la sorgente del planner rifiuta le due suddivisioni intere
      (`allocation.classification_invalid`).
    - Per avere le barre dei settori serve un seed con settori validi. È fuori dal perimetro di G e cambia anche altri
      scatti, per esempio `assets/detail-classification`.
  - La pagina utente del PAC non lo mostra: non ha un segnaposto (`data-name`), da aggiungere con la documentazione se
    serve.
  - Verifica: statica pulita (`tsc` con i soli 2 errori di base, prettier). La run filtrata a 1 worker parte dopo il
    merge della punta; poi la coppia di G-13 lo include.
  - ✅ **15/10–16/10, verificata.** Codice `73f7d32c6`, in `dev_release2` con `a8991e20b`.
    - Run filtrata a 1 worker su `a2c1c39f4` (`g-g16-w1b`): verde, 16 PNG per scatto. Le impronte dei tre scatti PAC
      esistenti sono uguali a `g-final3`: richiudere la sezione funziona.
    - Nella coppia di G-13 lo scatto è `stable`, 0/16.
    - La prima run (`g-g16-w1`, 23:05, carico 80–96) era rossa per un `worker_crashed` dello strumento PAC, non per lo
      scatto. Il coordinatore l'ha instradato a J (1.3).
    - Resta per dopo: le barre dei settori, con un seed dai settori validi.
- **G-17 · Il nome casuale dell'account usa e getta è rumore di contenuto** — basso; G, 16/10, coppia di G-13.
  - `files/brim-report-sets` è `unstable` (16/16, fino al 3,2 %): il nome `demo_xxxxxx` dell'account del test compare
    nella tabella e nel filtro «Caricato da» aperto, che si allarga con lui. Lo stesso nome è fra le cause di diversi
    `medium`.
  - Proposta (perimetro G, test-author): in `registerGalleryAccount` (`galleryReportSets.ts`), un nome deterministico
    per test e progetto, con il ripiego casuale se la registrazione risponde che esiste già. Così lo scatto diventa
    uguale fra due run.
  - Da valutare con la pulizia degli account (`cleanupGalleryAccount`): un nome fisso non deve scontrarsi con quello di
    una run interrotta che non l'ha cancellato.

  Dettagli: [analisi G-13](../Phase_1/10_colorSystem/G-galleryDeterminism/evidence/analysis-g13-2026-10-16.md), «La coppia del rumore».
- **G-18 · Guardia G3 a runtime nella galleria** ✅ 16/10, `07fe58276` — medio; coordinatore, 16/10 (il developer: «vedi tu»).
  - Il gate G3 vede gli elementi misti, con classi di ruolo e legacy insieme, solo se sono scritti così nel sorgente.
    Non vede le classi composte a runtime: le prop di classe fra aree, le costanti, le concatenazioni.
  - Ogni snapshot ora scandisce ogni scatto con le regex del gate (`galleryMixed.ts`, dopo la cattura, solo
    segnalazione) e scrive `mixed_elements.json`.
  - `gallery_tool mixed` li stampa per cartella del file candidato, o per sezione. Il testid è un indizio, non una
    prova.
  - Verificata nella run filtrata `g-mixed-probe` (Settings, 192 scatti): un record per PNG, 0 errori di scansione,
    4 ms di mediana per scatto. **Misti oggi in Settings: 0.** Il conto su tutta la galleria arriverà da solo con il
    prossimo snapshot completo.
  - I 13 rossi della run sono di ambiente (carico 110–145 su 10 CPU) e cadono tutti prima della scansione.

  Dettagli: [piano di G](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md),
  «G-18 · Guardia G3 a runtime nella galleria (16/10)».
- **G-19 · «Asset detail rolling return» legge il selettore prima che la pagina si assesti** — basso; G, 16/10, verifica
  FE5c.
  - `gallery.spec.ts` 5361–5363 legge il pulsante «Rolling Return» subito dopo l'apertura e il clic su 1W, senza
    aspettare `data-busy="false"` o `data-series-state`.
  - Un ricaricamento in corso svuota `chartData` e smonta il selettore finché i prezzi non rispondono: il clic stesso,
    o il ricaricamento completo del poll live su un grafico convertito.
  - Sotto carico (richieste ferme 25 s) il test va in timeout a 20 s.
  - Proposta (test-author, perimetro G): aspettare la pagina assestata prima di leggere il selettore.

  Dettagli: [piano di G](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md),
  «Dopo G-18», verifica di FE5c.
- **G-20 · Gli scatti del ripristino B5b** — medio; 1.3 tramite il coordinatore, 16/10 sera. Non è per subito.
  - Gli stati da fotografare, nella scheda Backup dell'admin:
    1. il report del controllo della copia, la finestra `restore-report` (`RestoreReportModal.svelte`): i totali
       (`restore-report-totals`, con `data-status="changed"` per l'avviso di differenza) e gli avvisi
       (`restore-report-warnings`); poi `-ready`, `-migrations`, `-admins`, `-blocker`;
    2. la conferma con la parola da digitare (`restore-confirm-word`, `restore-confirm-input`, `restore-confirm`);
    3. l'overlay del riavvio (`restart-overlay`, `restart-detail`);
    4. l'esito. Il fallimento ha la sua schermata: l'overlay con `data-outcome="rolled_back"` e il motivo (es.
       `first_start_failed`), poi l'avviso `restore-last-result` sulla card. Il successo (`committed`) no, per scelta
       (P8): la pagina passa all'accesso e la card non dice niente (FBKP-107; confermato da B il 17/10).
  - **Il successo resta muto, per scelta: decisione P8 del developer** (16/10), «successo senza messaggio, se ha
    funzionato lo vedi».
    - Nella notte del 17/10 la 1.3 aveva deciso B-27, un avviso «applied on …» sulla card, con la N67. Li ha ritirati
      alle 04:53 (coordinatore), perché contraddicevano P8.
    - Per G-20 si fotografano solo l'overlay di fallimento (`rolled_back`) e l'avviso `restore-last-result`. Per il
      successo nessuno scatto.
  - B ha già simulato il flusso in `frontend/e2e/settings/backup.spec.ts` (`0cd910a7e`). La fixture `restoreTest`,
    con la sua `lane`, risponde sempre nella pagina al riavvio (`POST /api/v1/backup/restore/restart`). Quando il caso
    lo chiede, risponde anche a upload, controllo, esito, stato e `GET /api/v1/system/ready`.
    - FBKP-102 finge upload e controllo: al server non arriva niente.
    - FBKP-103…105 partono da un ripristino in attesa finto; FBKP-103 è il rollback (`first_start_failed`).
    - FBKP-106 e 107 usano il server vero della corsia, tranne il riavvio.
    - Le fixture le passa B.
  - Proposta (test-author, perimetro G): gli scatti nel test di Settings, gli aiuti in
    `frontend/e2e/fixtures/galleryBackup.ts`, che già finge la card del backup. Solo intercept finti, come in
    FBKP-102…105: nessun archivio caricato, nessun ripristino in attesa sul server della corsia, nessun riavvio.
  - L'inquadratura mobile di `settings/backup-ready`. Con B la card del ripristino sta sotto quella del backup, e su
    mobile resta tutta sotto il bordo dello schermo (`dh` en 1167 su 740): non si vede. Su desktop lo schermo si
    allunga e mostra le due card intere.
    - Decisione della 1.3 (coordinatore, 16/10 sera): uno scatto mobile a parte, scorso fino alla card del ripristino.
    - Con B4 dei backup (`df1f0d52c`, 17/10) la card del backup si allunga ancora: c'è la scelta «Kind of backup».
  - Poi: un doppio lancio a/b filtrato, come per `settings/plugins` ed `email`, e le righe di
    `mkdocs_src/docs/gallery/*.en.md` scritte da docs-writer.

  Dettagli: [piano di G](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md),
  «Dopo G-18», `settings/backup-ready` per la 1.3.
- **G-21 · Uno scatto delle sezioni premium della ricerca degli asset** — basso; 1.3 tramite il coordinatore, 16/10
  notte. Non è per subito.
  - La definizione di fatto del piano di X chiede uno scatto della ricerca con le sezioni premium (X-R32).
  - Serve un provider premium instradato, come fa l'E2E `asset-modal.spec.ts` («Asset search — premium first…»).
  - Si programma con G; lo scatto lo scrive test-author. Nel frattempo gli scatti degli import mostrano già la riga
    «Can't find it? Let us know».

  Dettagli: X-R32, nella sezione «X · Plugin, asset e ricerca (fase 01)» di questo file.
- **G-22 · La scheda Security nella galleria, e il badge di «Amministrazione» da una fixture** — medio; coordinatore,
  17/10 09:23, dopo A8b (`6e2b2c8b7`). Si programma dopo la run del punto 33.
  - Con A8b la pagina Settings, appena si apre, legge `GET /api/v1/security/checks` (il `prefetch` della scheda
    Security nel registro, `settingsTabs.ts`). Il gruppo «Amministrazione» porta un badge (`tab-badge`): il conto delle
    voci in errore o in avviso (`attentionCount`, `securityFindings.ts`). Alle voci del server si aggiunge quella del
    browser sulla registrazione aperta, quando l'istanza è raggiunta da un host fuori dalla rete locale.
  - Oggi quel conto è della corsia, cioè della sua configurazione di test, non di una demo. Compare in ogni scatto
    admin della pagina Settings, anche su Profilo, dove «Amministrazione» non è selezionata.
  - **Decisione del coordinatore (17/10 09:23): sì alla fixture**, come per la Dashboard (`dashboard-report.json`) e per
    la card del backup (`galleryBackup.ts`).
    - Una risposta di `GET /api/v1/security/checks` con lo schema vero (`SecurityChecksResponse`: `items` di
      `SecurityCheckRead`, cioè `check_id`, `severity`, `i18n_key`, `detail`) e valori realistici.
    - Serve sia allo scatto nuovo della scheda Security sia al badge in tutti gli scatti admin: la galleria non dipende
      più dalla configurazione della corsia.
    - Da verificare scrivendola: la voce del browser dipende dalla modalità di registrazione della corsia e dall'host
      della pagina; la fixture deve renderla fissa anche lei, o dire perché non compare.
    - A rivede la fixture: è il proprietario di Security.
  - Lo scatto: la scheda Security (`settings-tab-security`, `SecurityTab.svelte`) con le voci da guardare
    (`security-finding`, con il collegamento `security-finding-action` dove c'è) e quelle superate (`security-passed`).
  - Il test lo scrive test-author, nel perimetro di G: `gallery.spec.ts` e una fixture in
    `frontend/e2e/fixtures/gallerySecurity.ts`. Poi un doppio a/b filtrato, e le righe di
    `mkdocs_src/docs/gallery/*.en.md` scritte da docs-writer.
  - **Da G-28 (20/10):** il file `gallerySecurity.ts` e la risposta di base per ogni scena, tutti i controlli «ok»,
    vengono da G-28. La domanda sulla voce del browser ha la sua risposta: gli host della galleria, `localhost` e
    `lf-e2e.lan`, sono locali, quindi la voce non compare. A G-22 restano gli scatti con dei controlli da guardare,
    ognuno col suo instradamento registrato nel test, dopo quello di base:
    - la scheda Security, come sopra;
    - la riga della connessione col pallino e il link dei controlli, per la sezione «Security Warnings for
      Administrators» di `user/connection-security` (N69b), che oggi non ha un'immagine.

  Dettagli: [piano di G](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md),
  «Dopo G-18», «Punto 33 della designer».
- **G-23 · `settings/cache-panel` dipende dai test vicini** — basso; G, 17/10, dalla run del punto 33.
  - Il pannello mostra le cache in memoria del server di test (`GET /api/v1/settings/cache/status`). Quante voci ha
    ogni cache dipende da cosa hanno fatto prima, sullo stesso server, gli altri test della run.
  - Nella run filtrata del 17/10 le due catture dello stesso commit, a e b, hanno dato una riga in meno in b. La pagina
    era più corta di 31 px e l'inquadratura, presa dal fondo, è scesa: fino all'8,9 % dei pixel cambiati, in 16
    varianti su 16. In G-13, su gallerie complete, lo scatto era `low`.
  - Proposta: servire lo stato delle cache da una fixture con lo schema vero (`CacheStatusResponse`), come G-22 per i
    controlli di sicurezza. Il test lo scrive test-author; la fixture la rivede il proprietario del pannello.

  Dettagli: [piano di G](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md),
  «Dopo G-18», «Punto 33 della designer».
- **G-24 · Lo scatto della modale «What's new» (C-54)** — basso; coordinatore, 18/10 01:24, dalla coda della 1.3
  (17/10 17:48, dopo `331cee121`). Non nella galleria del giro 3.
  - La modale «What's new since your last version» (`frontend/src/lib/features/changelog/WhatsNewModal.svelte`) non ha
    uno scatto. La apre `DeferredAppPopups`, prima fra i popup automatici, quando `user.whats_new` (login e
    `GET /api/v1/auth/me`) nomina capitoli rilasciati di `CHANGELOG.md` che l'utente non ha visto.
  - Per gli utenti di test `whats_new` è `null`: nessuno scatto di oggi la incontra per caso.
  - Il metodo è quello di `frontend/e2e/layout/whats-new.spec.ts`: la risposta vera di `GET /api/v1/auth/me`, con
    `user.whats_new` sostituito (`route.fetch()`, poi `fulfill`). Lo stub vale per il contesto che lo installa.
  - Da decidere scrivendolo:
    - `since` e `release` fra i capitoli già rilasciati (oggi 1.1.0, 1.2.0, 1.2.1), così lo scatto non cambia a ogni
      nuova versione;
    - la chiusura scrive `POST /api/v1/auth/whats-new/seen` sul DB condiviso: lo scatto non la chiude, o la intercetta;
    - nelle quattro lingue: il capitolo tradotto dove il bundle lo traduce, altrimenti in inglese con la pillola
      (`whats-new-not-translated`).
  - Il test lo scrive test-author, nel perimetro di G (`gallery.spec.ts`, una fixture in `frontend/e2e/fixtures/`). Poi
    un doppio a/b filtrato, e la riga di `mkdocs_src/docs/gallery/*.en.md` scritta da docs-writer.

  Dettagli: [piano di G](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md),
  «Galleria del giro 3».
- **G-25 · `onboarding/welcome-setup` su mobile: in francese e spagnolo la pagina non sta più nell'inquadratura** —
  basso; G, 18/10, dalla galleria del giro 3. Il coordinatore l'ha accettata alle 02:36.
  - Dal 17/10 la pagina di benvenuto ha la nota legale sotto la card (A9, `b1b647edc`, `LegalNotice`).
  - Lo scatto la guarda dal fondo: `frameWelcome` (`frontend/e2e/fixtures/galleryOnboarding.ts`) scorre in fondo e
    vuole interi nell'inquadratura i cinque controlli, cioè l'avatar, la lingua, la valuta, «salta» e «continua».
  - Su mobile, in francese e spagnolo, coi testi più lunghi, la pagina non ci sta più e l'avatar esce in alto: è
    visibile al 78,75 %. Il test fallisce nelle 4 varianti, chiaro e scuro, e quelle immagini mancano. In inglese e
    italiano passa; su desktop tutte e 8 le varianti passano.
  - Non è carico né tempo: lo stesso rapporto in nove esecuzioni del 18/10, cioè le tre gallerie complete e i loro fill
    a 2 e a 1 worker. Verdetto `test-triage`: assunzione del test. Il prodotto è corretto. `designer-16b` (16/10, prima
    di A9) aveva tutte e 16 le varianti.
  - Proposta: per quello scatto, uno schermo alto quanto la pagina (`extendScreenToBlock` di `galleryTallShots.ts`),
    così nell'immagine entra anche la nota legale. In alternativa l'inquadratura sulla sola card, con la nota fuori. La
    scelta la conferma A, il proprietario di A9.
  - Il test lo ripara test-author, nel perimetro di G. Poi un doppio a/b filtrato, in francese e spagnolo su mobile.

  Dettagli: [piano di G](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md),
  «Galleria del giro 3».
- **G-26 · `settings/password-modal` su mobile: la pagina sotto la modale si ferma a scorrimenti diversi** — basso; G,
  18/10, dal rumore della galleria del giro 3.
  - Nelle due catture identiche del dopo (`cd686f445`, 18/10), su mobile in spagnolo scuro, la modale è uguale ma la
    pagina dietro no: in una si vedono il nome utente ed «Eliminar Cuenta», nell'altra l'avatar e «Seguridad». È il
    15,4 % dei pixel, in una variante su 16.
  - Nel rumore del 16/10 (`g-ref13`) lo scatto era «basso»; oggi è «instabile». Nei confronti dello stesso giorno le
    sue zone di rumore lo coprono, ma il riferimento resta meno pulito.
  - Da fare con `test-triage`, partendo dall'ipotesi del tempo: la pagina che scorre mentre la modale si apre, o
    l'avatar che si carica e la sposta. Poi fermare lo scorrimento prima di aprire la modale, come negli altri scatti a
    pagina ferma.
  - Il test lo ripara test-author, nel perimetro di G. Poi un doppio a/b filtrato su mobile.

  Dettagli: [piano di G](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md),
  «Galleria del giro 3».
- **G-27 · `build_designer_round.py`: l'etichetta del «prima» e la coppia dello stesso giorno** — basso; G, 18/10,
  dallo zip del giro 3. Il coordinatore l'ha approvata il 18/10 alle 04:05, per un lotto successivo.
  - Lo strumento chiama v1.2 il «prima» (le tabelle «prima (v1.2)», la guida, l'indice) e scrive che i dati cambiano
    col giorno della cattura. Era vero per il pacchetto del 16/10, non per la coppia dello stesso giorno del 18/10.
  - Quella notte il testo l'ho corretto dopo il build, solo nelle pagine generate: 726 tabelle, 4 note, la guida e
    l'indice. Il README di `scripts/visual_review/` lo dice al passo 3b.
  - Proposta: un'opzione per l'etichetta del «prima» (per esempio `--before-label`) e il riconoscimento della coppia
    dello stesso giorno dalle date delle due catture, che cambia la frase sui dati. In `scripts/visual_review/`, poi
    una prova a secco sulla coppia del giro 3, che resta su disco.

  Dettagli: [piano di G](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md),
  «Galleria del giro 3» e «README di `scripts/visual_review/` al riferimento del 18/10».
- ✅ **G-28 · N69b nella galleria: i controlli di sicurezza «ok» in ogni scena** — medio, con una scadenza; coordinatore,
  20/10 13:35. Deve entrare prima che la 1.3 rigeneri la galleria, alla fine di Y-39.
  - Da N69b (`1e711253a`) ogni pagina che un admin apre legge `GET /api/v1/security/checks`. Con un errore o un avviso
    compaiono:
    - un pallino sullo scudo della riga della connessione, nella barra laterale;
    - un link «N security warnings» nei suoi dettagli;
    - sul telefono, un pallino sul pulsante del menu (`mobile-menu-security-dot`).
  - La corsia ha il limite dei login spento (`accounts.login_limit`, avviso `auth.checks.loginLimit.off`). Senza cura:
    - il pallino è in ogni scena da admin, cioè quasi tutta la galleria, ed è l'avviso di una corsia di test, non di
      un'installazione;
    - in `security/connection-indicator` il link in più allunga i dettagli, e sul telefono rischia il controllo «tutta
      la riga sullo schermo»;
    - il pallino arriva dopo una lettura asincrona: rischio di a≠b.
  - La voce del browser non conta: i due host della galleria, `localhost` e `lf-e2e.lan`, sono locali (`isLocalHost`),
    quindi la registrazione aperta non aggiunge niente.
  - **La cura, decisa da G il 20/10:** i controlli simulati «ok» per ogni test. Lo scatto da utente normale curerebbe
    una sola scena.
    - `frontend/e2e/fixtures/gallerySecurity.ts`, come `galleryEmail.ts`. Contiene i 17 controlli della lista della
      piattaforma (`config_audit.CONFIG_CHECKS` e `platform.plugin_secrets`), nel suo ordine, ognuno `ok` con la
      chiave del suo ramo `ok` nel backend.
      - È tipata col client generato e controllata con `schemas.SecurityChecksResponse` alla registrazione.
      - Risponde solo a `GET` su quel percorso, il resto ricade alle regole di prima, e conta le letture.
    - È installata nel `beforeEach` esterno di `gallery.spec.ts`, dopo `guardGalleryOffline`: vale per ogni pagina di
      ogni test, anche sotto `lf-e2e.lan`. Un test che vuole altri controlli registra il suo instradamento dopo (G-22).
    - Nella scena `security/connection-indicator`, prima dello scatto:
      - la prova che la fixture ha risposto su quel caricamento;
      - `data-security-attention="0"` e `data-security-severity="none"`;
      - nessun `connection-security-attention-link`;
      - sul telefono, nessun `mobile-menu-security-dot`.
    - Testo alternativo: nessuna modifica. Quello di `user/connection-security` e delle 8 pagine della galleria
      descrive la riga aperta su «rete locale», con la ragione e il link «How to connect securely», ed è quello che lo
      scatto mostra.
  - **Cambi attesi con la cura:** il badge «1» su «Amministrazione» e su «Security» sparisce dagli scatti admin di
    Settings. Nient'altro di N69b.
  - Il codice lo scrive test-author, nel perimetro di G; A rivede i valori della fixture, perché è il proprietario di
    Security.
  - Verifica:
    - `prettier --check` e `tsc -p tsconfig.e2e.json`;
    - poi un doppio a/b filtrato nella corsia 6153: la scena, `main dashboard`, `mobile menu open`, Settings admin,
      `plugins` e `users`.

  - **✅ Fatto il 20/10, entra col checkpoint di G** (via del coordinatore alle 13:48):
    - test-author ha scritto la fixture e le asserzioni della scena; `prettier --check` e `tsc -p tsconfig.e2e.json`
      puliti;
    - due catture filtrate degli stessi 7 test, a e b, nella corsia 6153: tutte verdi, 136 PNG ciascuna;
      `security/connection-indicator` identica in ogni immagine, il resto nel rumore noto;
    - a occhio contro il 18/10: nessun pallino, e il badge sparito;
    - foglio: `LibreFolio_visual_review/sheets/g28-2026-10-20/`. Il valore della fixture lo guarda A, tramite la 1.3.

  Dettagli: [piano di G](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md),
  «Nota per la prossima galleria completa», N69b, e «N69 nella galleria».

## T (colori) · Token e tema (Phase_1/10_colorSystem)

> Workstream T del programma colori, aperto il 14/10 (D-T1). Da non confondere con la sezione «T · Matematica
> finanziaria e riordino (43)». Piano: [T-tokensTheme](../Phase_1/10_colorSystem/T-tokensTheme/plan-phase01TokensTheme.prompt.md).

- **TC-1 · I requisiti della password detti anche a chi usa un lettore di schermo** — basso; T, 14/10.
  - Oggi ✓ e ✗ distinguono un requisito soddisfatto senza affidarsi al colore, ma non hanno testo per i lettori di
    schermo.
  - Servono due chiavi i18n («soddisfatto», «non soddisfatto») in testo nascosto: lo fa A, che possiede la card di
    registrazione dopo il giro di T.

  Dettagli: piano di T, passo T-2.
- ✅ **TC-2 · Ruoli in attesa del giro 2 della designer** — medio; T, 14/10. **Chiusa il 15/10 con T-8**
  (checkpoint 7): il giro 2 (D-T17) risponde a N1–N6 e Q2–Q13, e i ruoli sono in `tokens.css`; gli stati sulla barra
  verde sono di nuovo nella barra (D-T17 supera D-T15). Ciò che resta da confermare passa a TC-8.
  - Sono derivati provvisori, calcolati solo dai suoi valori: hover e premuto in chiaro, fondale delle modali, inverso
    dei tooltip, tinte di avviso, errore e informazione.
  - ✅ **Stati sulla barra verde** (T-3, 15/10): chiusa da D-T15 (15/10). La barra laterale è neutra, e le icone di
    `ConnectionSecurityIndicator` sono sui ruoli di stato (T-6).
  - Da decidere con lei:
    - guadagno e perdita distinti da successo ed errore;
    - l'info `#155EEF`, molto saturo;
    - le opacità delle colline del login in scuro;
    - palette categoriale e colori dei grafici.
  - Le otto correzioni minime di contrasto (D-T6) vanno confermate.
  - **Domande di W1 e W2** (15/10, notte): Q1–Q13 nel piano di T, sezione W1–W6, «Ruoli che mancano». Q1 è chiusa da
    D-T16 (15/10): un controllo selezionato è `bg-lf-checked` (focus) col segno `text-lf-on-checked` (card).
  - **Giro 2, «Pietra e Salvia»** (15/10, T-6): la palette è applicata. I ruoli che la sua tabella non copre, i valori
    provvisori e le correzioni minime di contrasto sono nel piano di T, passo T-6.
  - **Decisioni del developer, 15/10:**
    - D-T15, che supera D-T2: barra laterale neutra (`#EDF0EE`/`#111615`); il verde `#1B4334` resta per l'header del
      login e i pulsanti;
    - D-T16, che chiude Q1: un controllo selezionato è riempito di verde focus (`#236B4D`/`#429E79`) col segno nel
      colore della card;
    - D-T3 confermata: niente ponte, chi non è migrato resta visibilmente vecchio.
  - **Domande aperte del giro 2 (N1–N6):**
    - N1: voce attiva e hover della barra neutra, e il suo bordo;
    - N2: la barra del titolo della PWA segue la barra neutra o resta verde (serve a T-4);
    - N3: il bordo della card di accesso in scuro;
    - N4: il sottotitolo «Crea un account» del render;
    - N5: le sei correzioni di contrasto, soprattutto il bordo dei campi;
    - N6: colline e linee scure, e i pallini sulle linee.
  - **Domande aperte di W1/W2 (Q2–Q13):**
    - controlli: interruttore spento (Q2), hover dei pulsanti pieni (Q3), stato «modificato» (Q4), pallino neutro (Q5);
    - superfici e testi: codice e terminale (Q6), `mark` (Q7), ombre (Q8), coachmark (Q9), avviso nel tooltip (Q10);
    - colori categoriali: viola dell'AI Export (Q11), icone decorative (Q12);
    - fondale delle modali (Q13).

  Dettagli: piano di T, «Autorizzazione e decisioni»; `frontend/src/lib/theme/tokens.css`.
- **TC-3 · Uno scanner dei colori solo, con L** — basso; T, 14/10.
  - Il cricchetto (`frontend/scripts/theme/theme-roles.mjs`) copia la regex delle classi di palette dallo scanner del
    Designer Lab (`scan-colors.mjs`).
  - Quando L entra in `dev_release2`, un modulo comune evita che i due conteggi divergano.

  Dettagli: piano di T, passo T-1.
- **TC-4 · Le cinque regole della password scritte due volte** — basso; T (trovato da `test-author`), 14/10.
  - Le stesse regole stanno in `ui/input/PasswordStrength.svelte` (la lista mostrata) e in
    `auth/RegisterCard.svelte` (la validazione del modulo). Oggi coincidono; se divergessero, la lista direbbe
    «soddisfatta» mentre il modulo rifiuta la password.
  - Una fonte sola per le regole: è di A, che possiede la registrazione (F13).

  Dettagli: piano di T, passo T-2.
- **TC-5 · Il tema scelto dall'header non sopravvive a un nuovo accesso** — basso; T (trovato da `test-author`), 15/10.
  - `ThemeToggle` scrive solo `localStorage`; all'accesso `auth.ts` riapplica il tema salvato nell'account
    (`applyTheme`), quindi una scelta fatta dall'header si perde se diverge da quella salvata. Comportamento di prima di
    T, non di colore.
  - **Accessibilità della shell, anche questa di prima:** la chiusura mobile della barra laterale non ha nome
    accessibile; il `title` del pulsante di compressione e l'`aria-label` del fondale sono in inglese fisso; le
    schermate d'attesa della shell scrivono «Loading...» e «Checking authentication...» in inglese.

  Dettagli: piano di T, passo T-3.
- **TC-6 · Alla prima visita il selettore della lingua mostra l'inglese mentre l'interfaccia è nella lingua del
  browser** — basso; T, 15/10. Da instradare: non è di colore.
  - Visto sugli scatti di T-5: browser `it-IT`, nessuna preferenza salvata, pagina di accesso in italiano con la
    bandiera 🇬🇧, e nel menu è selezionato l'inglese.
  - Causa probabile, letta e non provata: `currentLanguage` (`lib/stores/app/language.ts`) nasce col valore salvato o
    con `en`; il suo `init()`, chiamato al montaggio del layout radice, legge una volta sola il `locale` di svelte-i18n,
    che passa a `it` solo dopo aver caricato il dizionario. Il negozio resta `en`.

  Dettagli: piano di T, passo T-5.
- **TC-7 · `--resolve` non fa un vero merge a tre vie** — medio; R-8 della sezione R, spostata qui dal coordinatore il
  15/10.
  - **Il difetto:** `mergeBaselines` (`frontend/scripts/theme/theme-roles.mjs`) non guarda la base per una riga presente
    su entrambi i lati: prende il minimo di m1 e i soli valori di m2 comuni ai due lati.
  - **Cosa succede:** se un lato ha accettato uno scambio (`--accept`), per esempio D3 in `themeStore.ts`
    (`#156534` → `#166534`), e l'altro ha ancora la riga della base, il valore accettato sparisce dal fuso. Il gate
    dà rosso sull'albero fuso, e bisogna rifare `--accept` a mano. Successo due volte il 15/10, nei merge di R e di X.
  - **La correzione:**
    - un merge a tre vie vero: se un lato è uguale alla base, vince l'altro; se sono cambiati entrambi, il più
      stretto;
    - la riga di un file con `~accept` su un lato vince per quel file;
    - test sintetici in `themeRoles.gate.test.ts`, scritti da `test-author`.
  - 🔄 **Implementata in T-8** (15/10, checkpoint 7): una riga lasciata com'era da un lato prende quella dell'altro;
    cambiata dai due lati vince il lato con un `~accept` nuovo (due: errore), altrimenti il più stretto. Si chiude con
    la validazione della revisione fusa, quando i test passano.

  Dettagli: piano di T, passo T-6, «Validazione del fuso», e T-8, punto 10.
- **TC-8 · Giro 3 della designer: quello che resta da confermare** — medio; T, 15/10. Per D-T21 la designer rivede
  tutto insieme nel giro 3.
  - Le sette correzioni minime di contrasto di T-8 sui valori del giro 2 (D-T6), ciascuna col valore chiesto accanto in
    `tokens.css`. L'ottava, sul caffè dell'header verde, è decaduta col suo ruolo in T-8b (D-T23: header neutro).
  - I derivati provvisori: hover dell'azione in chiaro, testo su un pieno AI (`--lf-on-ai`), commenti del terminale,
    ombra delle card in scuro (40 %).
  - Le scelte di T: indicatore della voce attiva a sinistra; la fascia del logo fusa nella barra. (Il pallino di
    sicurezza `#F87171` della barra verde è tornato `--lf-danger` con l'header neutro di D-T23.)
  - Interruttore spento: in chiaro si riconosce solo dal bordo del pallino, e il gate dei contrasti non lo misura.
  - Da TC-2: guadagno e perdita distinti da successo ed errore.
  - Il rosso e il verde del tema scuro scelti dal developer dopo l'anteprima (D-T25 `#FF7A86`, D-T26 `#5ED69A`), estesi
    agli stati della barra verde: per D-T21 la designer li rivede nel giro 3.

  Dettagli: piano di T, passo T-8 nell'avanzamento.
- **TC-9 · Il `background_color` del manifest resta il beige delle icone** — basso; T, 15/10. Da decidere.
  - D-T7 vuole splash, pagina offline e `background_color` del manifest sullo sfondo pagina, che col giro 2 è
    `#F3F5F3`. Splash e pagina offline lo seguono (T-8).
  - Il manifest no: `test_pwa_assets.py` (K) lo fissa a `#F5F4EF`, il colore in cui sono dipinte fino al bordo le icone
    maskable (`icon-maskable-{192,512}.png`), così il ritaglio del launcher incontra lo splash di sistema senza cucitura.
  - Per seguire D-T7 servono le icone ridipinte e la costante del test aggiornata, nello stesso commit. La differenza
    fra i due colori è minima.

  Dettagli: piano di T, passo T-8, punto 15.
- **TC-10 · Revisione del mattino delle ondate notturne (D-T27)** — medio; T, 15/10 notte. Per D-T27 i lotti entrano
  validati senza l'OK del developer; dove i ruoli e la skill `theme-roles` non coprono un caso, T sceglie il ruolo più
  vicino e lo annota nel piano come **«da rivedere»**.
  - W3-a: le barre della dashboard prendono il ruolo del testo (più scure in chiaro, niente fluo in scuro); le barre
    categoriali «Costo d'acquisto» e «Liquidità» restano blu e smeraldo, in attesa di un ruolo categoriale.
  - TD-3: i pulsanti attivi della card «Allocazione Patrimoniale» seguono la designer (`--lf-action`), non D-T16
    (`--lf-checked`); solo in quel pannello.
  - W3-c: i toast in scuro diventano pieni chiari col testo scuro, anche l'errore (`danger` + `on-status`, non
    `danger-solid`); il banner della qualità dei dati tiene l'errore nel tono d'avviso, e per l'hover dei suoi pulsanti
    manca un ruolo; la barra PAC «bilanciata» passa da `libre-green` a `success`, la «sconosciuta» va su `neutral` con
    la traccia ancora di palette; i chip neutri su `bg-lf-neutral`.
  - Rimandato: le due funzioni di segno di `brokers/lots/LotCustodyModal.svelte` (righe 103–114), dopo l'ingresso di J,
    che ha il file aperto; `ui/input/DistributionEditor.svelte` (copie di `pacTargetBar`/`pacTargetTotal`) con W1-d,
    dopo che G avrà cambiato l'asserzione `text-green-600` di `gallery.spec.ts:6067`. ✅ `LotCustodyModal` fatto il 16/10
    dopo J CP-16 (I1).
  - I1: le righe evidenziate delle liste su `bg-lf-selected`, più quiete in scuro della vecchia piena verde; il bordo
    quasi nero del selettore dei segnali su `border-lf-input` (manca un bordo di campo forte); il filtro attivo di
    `CheckMenu` sui ruoli `info`; l'avviso dentro il tooltip di `FxProviderSelect` resta `#fbbf24` finché
    `ui/feedback/Tooltip.svelte` non passa a `bg-lf-inverse` (Q10 li lega: da proporre come lotto a parte). ✅ Q10 fatto
    il 16/10.
  - Q10: in scuro tutti i tooltip diventano chiari col testo scuro; tre ruoli `-on-inverse` nuovi (pericolo, info,
    attenuato) col valore del tema opposto, la regola di Q10 estesa; info e attenuato a 4,54:1 in chiaro; l'ombra dei
    tooltip è quella dei menu.
  - W1-d: il suggerimento evidenziato di `TagInput` passa dal blu a `bg-lf-selected`.
  - Rimandati da W1-d, consegnati col lotto input (`37972b529`, 16/10): `ExactDecimalInput` ed `ExactQuantityInput` con i
    chiamanti (`INPUT` del PAC, i form delle transazioni, i 6 campi dei grafici di DV). Da rivedere: un campo non valido
    resta rosso anche col fuoco (`aria-invalid:border-lf-danger` vince su `focus:`).
  - W1-c, W1-e, W2-a (bozze dello slot, in ingresso col secondo slot): preset inattivi che si scuriscono al passaggio come
    oggi; badge della durata personalizzata ancora ambra; tooltip, modali e onboarding sui ruoli (fondale delle modali e
    del coachmark al 60 %, tessere del logo bianche anche in scuro, contorno di «Riprova» tenue sul banner).
  - W1-e, dalla galleria candidata di G: il bordo N3 di `ModalBase` (1 px sopra e sotto) rende ogni modale 2 px più alta;
    le scene adattate al dialogo crescono di 2–3 px (`transactions/form-modal-transfer` 884 → 886). Voluto; senza
    ingombro sarebbe un'ombra interna.
  - W1-f1, W1-g, W2-b (16/10): la barra della sync su `bg-lf-warning` (l'ambra era un accento, non un avviso); i banner in
    scuro più accesi (prima il testo era al 60 % di proposito, commit `7b4090d74`); le tinte `-soft`/`-line` in scuro
    opache; nel changelog il filo del `mark` come ombra interna e la testata dei capitoli al passaggio su `bg-lf-neutral`.
  - Da sapere per W5/W6: quando `AssetCurrencyChangeModal` porterà il suo bordo rosso sui ruoli (per esempio
    `border-lf-danger-line`), quel nome viene prima di `border-lf-raised` di `ModalBase` e perderebbe: servirà una variante
    della modale, non un `contentClass`. **Approvata** (coordinatore, 16/10): `ModalBase` prende un prop di tono,
    `tone="danger"` → `border-2 border-lf-danger-line` al posto di `border-lf-raised`, in un ternario solo (regola 8), nel
    lotto «component tokens» di T; fino ad allora AF lascia legacy il file (segnalato da AF, catena C1). **Fatta** (T,
    16/10, lotto «component tokens», parte 1): `tone` con `data-tone`; AF passa a `tone="danger"` dopo l'ingresso.

  Dettagli: piano di T, voci «da rivedere» di ogni lotto nell'avanzamento (da W3-a in poi).
- **TC-11 · Una select disabilitata a lista aperta accetta ancora un clic su un'opzione** — basso; trovata da
  `test-author` il 16/10 in I1, fuori dai colori. `SimpleSelect`: la lista resta aperta quando `disabled` o `loading` si
  accendono, e il gestore del clic rifiuta solo le opzioni disabilitate e le intestazioni; la tastiera invece controlla
  `disabled || loading`. Se il prodotto chiuderà la lista, lo stato «aperto, poi disabilitato» di `SimpleSelect.test.ts`
  va tolto. Dettagli: piano di T, I1, passo 4.
- ✅ **TC-12 · La voce orfana del coachmark nel gate** — minimo; T, 16/10; chiusa il 16/10, commit `d3b04a867`. Con W2-a il
  bagliore del coachmark è su `var(--lf-tour-glow)` e non chiede più l'eccezione
  `ARBITRARY_ALLOWED` di `frontend/scripts/theme/theme-roles.mjs` (riga 84). Non si poteva aspettare Y5: il gate
  (`themeRoles.gate.test.ts`, «keeps … ARBITRARY_ALLOWED current») vuole che una voce che non lascia passare niente si
  tolga, e nel secondo slot è caduto. Tolta la riga 84 con l'OK del coordinatore (Y5 cambia la riga 70: il merge a tre vie
  è pulito); riscritti i due commenti di `src/themeRoles.gate.test.ts` (~218, ~547). Dettagli: piano di T, «Secondo
  slot».
- **TC-13 · Tre controlli deboli negli E2E dell'editor dei dati (spec di W)** — minimo; T, 16/10, lotto W1-f2. Fuori
  dalle righe approvate, già presenti: in `asset-data-editor.spec.ts` il test 21 sta dentro un `if (await
  staleToggle.isVisible(...))` che non aspetta, quindi il suo verde non prova il contatore; nessun controllo positivo
  tocca il ✗ di `CsvEditor`; `fx-csv-import.spec.ts:56` dipende dalla parola inglese «error». Lotto W1-g, stesso file: il
  test 14 («info banner reflects current direction», riga 289 e seguenti) tiene la guardia `if (count() > 0)`, che ora
  non serve più (il banner c'è sempre) e può nascondere un'assenza, e non verifica l'ordine dei codici dopo lo scambio
  (`toContainText(/EUR.*USD/)`, poi `/USD.*EUR/`, varrebbe in tutte e quattro le lingue). Da proporre a W. Dettagli:
  piano di T, «W1-f1, W2-b, W2-d e W1-f2», passi 7 e 9.
- **TC-14 · I test «in scuro» di `image-crop.spec.ts` non sanno se il tema è scuro** — minimo; T, 16/10, lotto W1-g. Il
  `beforeEach` (riga 616) e F1 (riga 643) riconoscono lo scuro da `[class*="dark"]`, che prende qualsiasi elemento con
  un'utility `dark:`: in chiaro il `beforeEach` può non cliccare il selettore del tema, e F1 passa comunque. La migrazione
  ai ruoli toglie le classi `dark:` e rende il controllo via via giusto, ma la cura è leggere solo `html` con
  `toHaveClass(/\bdark\b/)`. Da proporre al proprietario degli spec dei file. Dettagli: piano di T, «W1-f1, W2-b, W2-d e
  W1-f2», passo 10.
- ✅ **TC-15 · Testo muted su una riga selezionata (`bg-lf-selected`)** — basso; T, 16/10, lotto del gate; chiusa il
  16/10 nel lotto TC-15 di T: una regola centrale nello `<style>` delle 4 select di `ui/select` (`SearchSelect`,
  `SimpleSelect`, `TreeSelect` col passaggio, `AssetPickerPanel`), che copre anche gli snippet dei chiamanti; più
  `FileGrid` (scheda selezionata) e `UnifiedLotsTable` (riga evidenziata) nei component tokens. Misurato col
  risolutore del gate: sul ruolo traslucido `selected` reggono 4,5:1 solo `primary`, `secondary` e `link` (mai su un
  `panel`, 4,09:1 in scuro). Il muted, i quattro stati e i segni scendono a 3,84–4,48:1 quasi ovunque, e schiarire la
  tinta non basta (al 6 % il peggiore resta 4,17). Caso reale: le righe evidenziate di `ui/select/AssetPickerPanel`
  (tipo e valuta in muted); da ripassare le altre opzioni evidenziate di `ui/select`. Cura, decisa col coordinatore: nei
  componenti, muted → secondary mentre la riga è selezionata o evidenziata; la regola è nello skill `design-system`,
  regola 5. Da fare in un lotto di T. Dettagli: piano di T, «Il lotto del gate», passo 4.
- **TC-16 · `FilePreviewModal.test.ts` aspetta il visore col budget di 1 s di `waitFor`** — minimo; T, 16/10, lotto
  «component tokens». `listening()` (riga ~597) aspetta `viewer.opened`, `failed` e `tiles` con il timeout predefinito di
  `waitFor` (1 s) su una catena asincrona (il finto EmbedPDF). Sotto carico (41–52) due test sono caduti una volta alla
  riga 598 (`viewer.opened` vuoto); con lo stesso codice verdi da soli (37/37, due volte) e nell'insieme dei 30 file
  (978/979). Verdetto della triage: l'orologio (un'assunzione del test), nessun difetto del prodotto né dei miei file. Cura
  per il proprietario dell'area dei file: un budget esplicito su quel `waitFor`. Dettagli: piano di T, «I component
  tokens, parte 1», passo 5.
- **TC-17 · `tx-picker-pagination.spec.ts` apre il picker con un budget esplicito di 5 s** — minimo; T, 16/10, lotto «le
  tabelle». `openPicker` (riga ~67) aspetta `tx-picker-modal` visibile con `timeout: 5_000`, e la spec ha altri budget
  espliciti di 2–3 s. Nel sesto slot, a carico 90–140, P1 è caduto lì una volta: il modale non era visibile entro 5 s.
  Da sola a carico ~45 la spec è passata 5/5, P1 in 7,0 s. Verdetto della triage: l'orologio, un'assunzione del test;
  nessun difetto del prodotto né del lotto, che cambia solo gli stili. Cura per il proprietario della spec delle
  transazioni: togliere i budget brevi espliciti e lasciare il timeout di `expect` della configurazione. Dettagli: piano
  di T, «Sesto slot» e «La spec del rischio sui ruoli», passo 3.
- ✅ **TC-18 · Il commit rifiuta il costo del ricevente di un TRANSFER con più di 12 decimali (FM6 di
  `tx-wac-formmodal`)** — alto; T, 17/10, mini-lotto `CompactCashCell`; **chiusa il 17/10 come duplicato di W-B56**:
  corretta da W in `de901f228` (sul target con `c91bd41b2`), FM6 verde sulla punta `b58108665` (`tx-wac-formmodal`
  10/10). La segnalazione com'era: nel bulk, un BUY di 10 Apple su Interactive Brokers a 1000 e un TRANSFER di 5 verso
  Directa: il commit risponde 200 con `committed: false`, «Row 2b: Cost basis override: At most 12 decimal places». Il
  WAC proposto al ricevente si vede arrotondato («💡 170.36 $ USD per unit») ma parte intero, e lo stadio di precisione
  del batch lo rifiuta (`transaction_batch_stages.py:117`, `decimal_limit_issue` di `backend/app/db/precision.py`).
  Riproducibile: lo stesso rosso tre volte, due col lotto e una con i due file del lotto riportati a HEAD (`9016f47c3`,
  build rifatta); il lotto cambia solo lo `<style>` e l'import, quindi non c'entra. Il modulo di precisione è cambiato
  il 16/10 sera (`bab52635d`, `0c3275057`); la spec è ferma dal 13/10. Verdetto della triage: difetto del prodotto. Cura
  per il proprietario del WAC: arrotondare il costo proposto alla scala della colonna prima del commit, o quantizzarlo
  nel backend; il test resta com'è. Dettagli: piano di T, «`CompactCashCell`», passo 4.
- **TC-19 · La pagina per sviluppatori del banner della qualità dei dati dice ancora «amber/sky»** — minimo, docs; T,
  17/10, R3-a (giro 3). `mkdocs_src/docs/developer/frontend/data-quality-banner.md`, riga ~46, descrive il modo
  raggruppato come «Single amber/sky container»: da R3-a il contenitore prende il tono del problema più grave (`danger`,
  `warning` o `info`, via `DATA_QUALITY_TONE`), ogni riga il suo, e i chip stanno sulla card col bordo nel colore dello
  stato (proposta a, T3-b). Va scritta anche la regola del developer per i banner (rosso per gli errori veri, ambra per
  i dati mancanti, blu per le note, verde per i successi) e il `MISSING_PRICE` del rischio diventato un avviso. Per la
  passata della documentazione a fine programma (docs-writer). Dettagli: piano di T, «Giro 3 della designer». **Dal
  19/10 (T2) anche la disposizione:** nel modo raggruppato il pulsante che ripara tutta la categoria sta in testa, col
  messaggio e le voci sotto (le coppie, o i nomi degli asset di STALE_PRICE, al più 3 e «+N»); aggiungere o aprire una
  coppia è un chip per coppia, come gli asset; il modo piatto è invariato (piano di T, «T2»).
- ✅ **TC-20 · Il caso «export JSON, reset all, import back» del Lab dava per diverse due sorgenti di colore diventate
  una** — basso, test; T, 18/10, verifica per l'ingresso di DV; **chiusa il 18/10 nel checkpoint di R3-c** (commit
  `6b218d4a4`, entrato in `cd686f445`): per il passo L2 il caso usa la radice della pagina delle transazioni
  (`transactionsPageRoot`, `text-lf-primary`), con le precondizioni che le due sorgenti siano diverse e che dopo L1 la
  radice tenga il suo colore; `front-designer-lab live` 12/12 sulla punta `b238d5b6e` più l'albero (01:11–01:14). La
  segnalazione com'era: `frontend/e2e/designer-lab/designer-lab-live.spec.ts:673` cambia nella stessa run la variabile
  del sottotitolo delle transazioni (L1, rosa) e il letterale dell'intestazione della data di `DataTable` (L2, blu); dal
  16/10 leggono entrambi `--lf-text-muted` (`546204732`, e il lotto delle tabelle di T `77bfa6a39`), così l'override di
  L1 vince e l'intestazione resta rosa: rosso deterministico, anche sul target senza DV (`7845fc3d3`: 11 verdi e 1
  rosso). Verdetto della triage: un'assunzione del test. La spec era di L (archiviato): la prende T. Dettagli: piano di
  T, «Una verifica per l'ingresso di DV» e «R3-c e TC-20».
- **TC-21 · Una riga cancellata lascia vedere sotto le colonne fisse di `DataTable`** — minimo; T, 19/10, cura delle
  colonne fisse. `tr.row-deleted td` (bulk delle transazioni, `DataEditor`) sbiadisce ogni cella con `opacity: 0.55`,
  le fisse comprese (la selezione, e le azioni in `DataEditor`), che lasciano vedere al 45 % il contenuto che scorre
  sotto. C'era già prima del lotto delle tabelle; non è una tinta di riga e la riga opaca non la cura: va sbiadito il
  contenuto, non lo sfondo, senza cambiare l'aspetto delle celle normali. Dettagli: piano di T, «Le colonne fisse
  trasparenti», Fuori pista.
- **TC-22 · La pagina per sviluppatori di `DataTable` non dice come si tinge una riga** — minimo, docs; T, 19/10, cura
  delle colonne fisse. `mkdocs_src/docs/developer/frontend/components/core-ui/data-table.md`, «Sticky columns»: una riga
  dipinge la card e la tinta del suo stato, `--dt-row-tint` (registrata con `@property`), e le celle fisse ereditano i
  due strati; chi tinge le righe con `getRowClass` imposta `--dt-row-tint`, mai lo sfondo della riga (`AssetTable`).
  Per la passata della documentazione a fine programma (docs-writer). Dettagli: piano di T, «Le colonne fisse
  trasparenti».
- **TC-23 · Nei pannelli del rischio i chip «Aggiungi coppia FX» portano tutti a `/fx`** — minimo; T, 19/10, T2 (il
  pulsante sopra ciò che ripara). Il banner raggruppato dà ora un chip per coppia ad `add_fx_pair` e `navigate_fx`, e
  ogni chip passa la sua coppia come `target`. La dashboard apre l'aggiunta su quella coppia; nei pannelli del rischio
  (`RiskPanelHeader`, `RiskAnalysisPanel`, `labQualityAction` di `features/risk/syncTargets.ts`, usato da
  `AssetSetRiskPanel`) `add_fx_pair` porta a `/fx` qualunque sia il `target`, come faceva il pulsante unico. Per il
  proprietario del rischio (la 1.3): aprire l'aggiunta sulla coppia del chip, se serve; `syncTargets.test.ts` fissa
  oggi il comportamento attuale. Dettagli: piano di T, «T2».

---

## DV · Colori dei grafici (Phase_1/10_colorSystem)

> Workstream DV del programma colori, aperto il 15/10 per le scelte GR1–GR5 del giro 2 della designer (D-T17): colore
> fisso per tipo e per settore, uguale in torta e storico; tavolozze per tema; emoji dei settori unificate. Codice a due
> lettere: «D» e «V» erano già usate (developer, 15/10).
>
> Valori e controlli: [giro 2 della designer](../Phase_1/10_colorSystem/designer-feedback/2026-10-15-round2-palette/README.md)
> e la sua [analisi](../Phase_1/10_colorSystem/designer-feedback/2026-10-15-round2-palette/analisi.md), §4–§6. Il piano:
> [`plan-phase00ChartColors.prompt.md`](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md).
> Gli ID di questa sezione sono `DV-n`.

- ✅ **DV-1 · La rigenerazione documentata del golden di `native_cash_guard` non arriva al test** — minimo; DV, 15/10
  (S1). **Chiusa il 15/10 da J con CP-4**, entrato in `dev_release2` col merge `322d55042`: la variabile ora è
  `LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD`, e il docstring spiega perché porta il prefisso `LIBREFOLIO_TEST_`.
  - Il comando del docstring, `LIBREFOLIO_REGEN_NATIVE_CASH_GUARD=1 ./dev.py test services roi-fifo-utils
    native_cash_guard`, non funziona: la corsia di test scarta ogni `LIBREFOLIO_*` che non sia `LIBREFOLIO_TEST_*`
    (`scripts/cli_base.py`, `_test_lane_drops`). Il test confronta, invece di riscrivere.
  - In S1 il golden è stato aggiornato sulle 4 righe del diff del test (💵 → 💰), poi verificato verde byte per byte.
  - Rimedio: rinominare la variabile in `LIBREFOLIO_TEST_…`, oppure aggiungerla a `TEST_LANE_KEEPS`. Fuori dal perimetro
    di DV: il coordinatore la gira alla 1.3 (15/10).
  - **La chiude J nel lotto CP-4** (coordinatore, 15/10): la variabile diventa
    `LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD=1`, che passa il filtro della corsia. Si chiude qui, citando CP-4, quando
    entra.
  - **Conflitto atteso sul golden:**
    - J lo rigenera con un campo nuovo (+116 righe), DV ha cambiato 4 righe a mano;
    - chi entra per secondo lo rigenera con la variabile nuova sulla revisione fusa, senza unire a mano.
    - J è entrato per primo, quindi rigenera DV, al merge di base fatto dal coordinatore prima della sua validazione.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezione «S1».
- ✅ **DV-2 · Un settore senza emoji: l'endpoint ripiega su 📊, la vista dell'allocazione su `None`** — minimo; DV, 15/10
  (`test-author`, S1). **Chiusa il 15/10** (in attesa del commit del coordinatore).
  - Un solo ripiego, accanto alla mappa in `sector.py`: `SECTOR_EMOJI_FALLBACK`, cioè ❓, l'emoji di «Non
    classificato». Lo usano l'endpoint e il motore (`sector_emoji`), ed è fissato nei test.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezione «DV-2 e
    decisione 8».
- **DV-3 · La torta non legge più l'`emoji` che le passano dashboard e pagina dell'asset** — minimo; DV, 15/10 (S3).
  - Con la decisione 8 la torta per settore prende le emoji dallo store dei settori. Il campo `emoji` di
    `AllocationEntry` è rimosso, ma è ancora calcolato e passato:
    - `components/dashboard/AllocationPanel.svelte:65` (zona di Y10);
    - `routes/(app)/assets/[id]/+page.svelte:3496` (`getSectorEmoji(name)`, zona di X).
  - Per `front check` non è un errore: l'oggetto nasce dentro un `.map`, e TypeScript fa il controllo delle proprietà
    in eccesso solo su un letterale assegnato direttamente (verificato con `tsc` 5.9 su una prova isolata, 15/10).
  - È un dato morto e innocuo. Si toglie quando quei file si toccano.
  - **Girata dalla 1.3** a Y-6/Y10 e a X (FE5c) (coordinatore, 15/10).
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezione «S3».
- **DV-4 · `hexToHsl` resta usato solo dai test** — minimo; DV, 15/10 (S3).
  - Il suo unico consumatore di produzione era `shadeForDepth`, tolto con GR4 (miscela in OKLab).
  - Da decidere se rimuoverlo con i suoi test o tenerlo come inverso documentato di `hslToHex` (`utils/colors.ts`).
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezione «S3».
- **DV-5 · Due pagine developer descrivono ancora le sfumature HSL** — minimo; DV, 15/10 (S3).
  - Pagine:
    - `mkdocs_src/docs/developer/frontend/components/charts.md`, «Pie Charts»: parla di `shadeForDepth`, della
      passeggiata in luminosità e della diffusione sui due lati;
    - `mkdocs_src/docs/developer/frontend/designer-lab.md:920` lo cita come esempio di colore derivato (pagina di L).
  - Il sito si aggiorna solo alla chiusura del programma colori (developer, 14/10).
  - Da scrivere allora:
    - `categoryColor` come unico punto di lettura;
    - GR4 a miscela in OKLab;
    - il ponte `roleColors`;
    - il segnale C4.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezione «S2».
- ✅ **DV-6 · Un'etichetta di settore comincia con uno spazio finché l'elenco dei settori non arriva** — minimo; DV,
  15/10 (`test-author`, S10). **Chiusa il 15/10** (in attesa del commit del coordinatore).
  - Causa: la decisione 8. Senza il ripiego scritto a mano, `getSectorEmoji` restituisce `''` fino al caricamento, e
    due composizioni scrivono `` `${emoji} ${nome}` `` senza controllarlo:
    - `components/risk/stressBucketLabel.ts:37`, usato da `L4Shock` e `RiskAnalysisPanel` (zona di Y):
      `title=" Finanziari"` e `aria-label=" Finanziari"`;
    - `features/tools/pac-allocator/planner/categoryLabels.svelte.ts:22` (PAC).
  - Dura una richiesta: entrambi caricano l'elenco e si ridisegnano quando arriva.
  - Rimedio di una riga, come fanno già torta e `SectorSearchSelect`: ``emoji ? `${emoji} ${nome}` : nome``.
  - **OK della 1.3** (coordinatore, 15/10): le due righe le fa DV, dopo il merge di base e la prova 0 e prima dello
    slot pesante; il test lo scrive `test-author`. I file sono di Y (`stressBucketLabel.ts`, che Y4b sposterà dopo
    l'ingresso di DV) e del PAC, di J.
  - **Fatto** sulla revisione `0182d890d`:
    - in entrambi i file, il ramo del settore mette l'emoji solo se c'è;
    - test nuovi `stressBucketLabel.test.ts` e `categoryLabels.test.ts`, 9 e 9, registrati in `core-unit`;
    - il mirror di `L4Shock.test.ts` è allineato, 22.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezione «S10».
- **DV-7 · W5-PAC e W5-charts: colori rimasti in palette, in attesa di una scelta o di un lotto di T** — minimo; DV,
  16/10 (W5-PAC, W5-charts).
  - ✅ (16/10, W6-e) **La traccia delle barre** di `TargetsStep`:63 e `DistributionDialog`:102 (`bg-gray-100
    dark:bg-slate-700`): tutte e due su `bg-lf-neutral`, il ruolo delle tracce.
    - Il riempimento «sconosciuto» di `STATUS_TONES.pacTargetBar` passa da `bg-lf-neutral` (ΔE00 0 dalla traccia) a
      `bg-lf-secondary`: il colore che l'obiettivo ha già nel risultato, 5,77/5,84:1 sulla traccia (coordinatore,
      16/10).
    - È una scelta provvisoria: il coordinatore la porta alla designer, nella raccolta al punto 27.
  - **Le barre «quota dopo il piano»**, `bg-libre-green`, in `AssetTable`:149 e `ResultCell`:79.
    - Sono un colore di dato accanto al neutro dell'obiettivo (`bg-lf-secondary`), non il marchio: `bg-lf-action` in
      scuro è spento sulla traccia.
    - Aspetta il punto 2.7 della designer o i colori di tipo di GR1.
  - **La barra della distribuzione attuale** di `DistributionDialog` (la costante `FILL`, `bg-libre-green`): il peso
    attuale di ogni asset posseduto, cioè un colore di dato, resta legacy (W6-e).
    - In scuro è il verde fluo `#00d681`, quello che il developer ha rifiutato nel PAC (TD-1).
    - Per TD-1 il «reale» prende il colore della categoria della riga, accanto al neutro «ideale»: qui la riga è un
      asset, quindi sarebbe il colore del suo tipo (GR1). È un cambio di disegno: aspetta la stessa scelta delle barre
      «dopo il piano».
  - **Le fasi di `BackendTimingBar`**: punti 2.1 e 2.5 (anche nell'inventario). Restano 14 classi, cioè le 6 fasi e
    l'attesa in coda. Il separatore dei segmenti è sui ruoli dal 16/10 (`divide-lf-card` sul contenitore, G-18).
  - **La legenda di `RiskReturnLevel`** (W6-a), 4 classi: il punto «portafoglio» cielo e il rombo «benchmark» ambra
    (riga 170), con le tinte delle righe della tabella (`--lf-cmp-risk-return-row-*` in `theme/components/table.css`).
    Sono le categorie della serie ECharts del grafico rischio/rendimento: aspettano il punto 2.5 della designer.
  - **I 4 interruttori di `ChartAestheticsSection`** (W5-charts), 16 classi: traccia e manopola alle righe 111/119,
    133/141, 155/162 e 176/184.
    - Il coordinatore (02:50) li vuole nel lotto di T sugli interruttori, tutti insieme con quelli dell'app (riga Q2
      della skill), così in scuro non ce n'è uno diverso dagli altri.
  - ✅ **Le barre «valore contabile» e «liquidità» dei KPI** (`features/dashboard/KpiSection.svelte` @405 e @417, 4
    classi: `bg-blue-500` e `bg-emerald-500` con le loro metà scure). Sono colori d'identità di due misure, non segni né
    stati: restano categorie (coordinatore, 16/10 12:07, regola 11 dello skill `design-system`).
    - **Per la designer:** quando decide il punto 2.2, la barra della liquidità potrebbe leggere il colore della
      categoria Liquidità dei grafici: lo stesso salvia, e la stessa misura in tutta l'app.
    - Il valore contabile resta da decidere insieme alle altre categorie.
    - **Decise dal giro 3** (designer e developer, 17/10, `decisioni.md` §1.7): il valore contabile nel blu dell'ETF
      (K1-a), la liquidità nel colore della Liquidità, ora blu ardesia. Le fa DV in **R3-5**, dopo i ruoli
      `--lf-cat-etf` e `--lf-cat-liquidity` di T (§1.9, decisione (A)).
    - **Fatto il 18/10** (R3-5, sulla base merge `3dba7f894`, in attesa del commit del coordinatore): `bg-lf-cat-etf` e
      `bg-lf-cat-liquidity`; le 4 classi escono dal baseline del ratchet (m1 594 → 590).
  - **Non di DV**, annotati per non perderli:
    - ✅ `INPUT` e `TITLE_INPUT` di `planner/ui.ts`: migrati dal lotto di T sull'input, `37972b529` (16/10);
    - ✅ i 6 campi di testo e numerici di `components/charts/` (W5-charts, 42 classi): stesso lotto di T, `37972b529`;
    - ✅ `ExposureMaps` (4): migrato da DV in W6-c, `5d2c1ce62` (16/10), dopo Y9;
    - ✅ `KpiSection` (W6-b), le catene verso `KpiMetricBar`: `ui/display` è passato da T a DV (coordinatore, 16/10
      11:48) e il lotto `ui/display` di DV le ha chiuse (`valueColor`@354 → `text-lf-primary`). Restano solo le due
      barre di categoria, alla riga sopra.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezioni
    «W5-PAC», «W5-charts» e «W6».
- ✅ **DV-8 · Le linee dei broker ripetono i colori dal nono broker** — minimo; DV, 16/10 (W6-c, rilettura dello skill
  `design-system`). **Chiusa il 16/10** (lotto DV-8 sulla base `bf2afbba3`, in attesa del commit del coordinatore):
  `growthBrokerColor(index, dark, poles?)` passa da `sequenceColor` dalla nona linea, con i poli della card della
  pagina per default; `GrowthChart.svelte` e `growthChartSeries.ts` non cambiano. Test: il blocco `growthBrokerColor`
  di `lib/theme/chartCategories.test.ts` (test-author), 10 casi.
  - Era: `growthBrokerColor(index, dark)` (`frontend/src/lib/theme/chartPalettes.ts`) prendeva
    `CATEGORY_SEQUENCE[index % 8]`: il nono broker aveva il colore del primo.
  - GR5 vuole, oltre la fine di una sequenza, gli stessi colori una sfumatura più in là, come già fanno la
    semi-ciambella e lo storico geografico con `sequenceColor(…, shadePoles(dark, card))`.
  - Rimedio: `growthBrokerColor` passa da `sequenceColor` con i poli della card letti da `chartRoles`. Tocca
    `chartPalettes.ts`, `features/dashboard/growthChartSeries.ts` e i loro test; è logica, non classi, quindi dopo W6.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezione
    «W6», passo W6-c.
- ✅ **DV-9 · Adottare `SIGN_TEXT.riskTable` e `SIGN_BAR.histogram` quando T li aggiunge** — minimo; DV, 16/10 (W6-a,
  regola 7 dello skill `design-system`). **Chiusa il 16/10**, commit `bf2afbba3` (lotto DV-9 sulla
  base `63e3a22d8`).
  - Era: `LOSS_CLASS` di `features/risk/AssetSetLossComparisonSection.svelte` scriveva `text-lf-loss`, e le barre sotto
    il taglio di `features/risk/levels/l1/ReturnHistogram.svelte` scrivevano `bg-lf-loss/80`: i ruoli giusti, ma non
    presi dalle tabelle per significato, come vuole la regola 7.
  - T ha aggiunto le voci nel suo lotto dei ruoli (`f043c1b58`), con `SIGN_BADGE`.
  - **Fatto:**
    - `LOSS_CLASS` → `SIGN_TEXT.riskTable.loss`;
    - le barre → `SIGN_BAR.histogram.loss`;
    - i badge «Income» e «Cost» di `features/dashboard/OtherPeriodEffectsTable.svelte` → `SIGN_BADGE.gain` e
      `SIGN_BADGE.loss`, che escono dal baseline.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezione
    «W6», passi W6-a e DV-9.
- **DV-10 · B4: quel che i neutri dei grafici sui ruoli lasciano alla designer** — minimo; DV, 16/10 notte (B4,
  D-T27).
  - **Da rivedere con lei:** la mappa voce → ruolo è il ruolo più vicino. In scuro assi e griglie passano da 1,93 a
    1,21:1 sulla card (`border-subtle`, come i divisori); i riquadri dei tooltip sono popover (`card`, `raised`).
    - I tooltip di correlazione e rischio/rendimento prendono il riquadro comune: il loro bordo non riprende più il
      colore del punto o della cella sotto il puntatore (ECharts lo faceva quando il bordo non era indicato), ed è il
      bordo neutro di tutti gli altri tooltip.
  - **Restano in `chartTheme.ts` coi valori legacy:** le serie, gli stati, i segni (guadagno e perdita aspettano un
    lotto con lei: fondono il rosso dei prezzi e quello del portafoglio), i punti del rischio/rendimento.
  - ✅ **`GEO_MAP_COLORS.land`** non va su un ruolo: su `neutral` starebbe a ΔE00 4,1/3,7 dal primo gradino della scala
    (GR5.1). È lo zero della scala, da decidere con lei. **Decisa dal giro 3** (17/10, `decisioni.md` §1.6): il «senza
    dati» `#D5D9E0`/`#343B46`, con la scala nuova dei sei blu; lotto R3-2 di DV, in attesa del commit del coordinatore.
  - **Il testo dei bottoni di stato del Gantt** (`on-status`) resta sotto 4,5:1 sui pieni legacy ambra e cielo di
    `LOT_STATE_COLORS` (3,07 e 3,95:1 in chiaro), come prima: si cura coi pieni di stato.
  - **Quattro helper puri leggono i ruoli su `<html>`,** non sull'elemento del grafico (`buildSecondaryYAxes`,
    `buildSignalReferencePrimitives`, `buildScatterOption`, `buildGrowthFullSeries`): oggi nessun effetto, da
    sistemare se un grafico entra in un sottoalbero a tema forzato.
  - **Il ponte riporta in sRGB `oklab()`, `oklch()` e `color(srgb …)`** (B4b); `lab()`, `lch()`, `color(display-p3 …)`
    e `color(srgb-linear …)` vanno allo stand-in senza segnale. Oggi nessun effetto (`tokens.css` mescola solo `in
    oklab`); da estendere se una miscela o una modifica del Lab usa un altro spazio.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezione
    «B4».
- **DV-11 · I colori dei tipi in due copie, finché il Lab non passa ai ruoli** — medio; DV, 17/10 (giro 3, §1.9).
  - Decisione (A) del coordinatore, in due passi. Il primo è del giro 3: i valori in `lib/theme/chartCategories.ts`,
    i ruoli `--lf-cat-*` di T in `tokens.css` coi valori uguali, e il test di parità di `chartCategories.test.ts` che
    blocca le due copie (flag di consegna alla `PENDING_READERS`).
    - Fatto il 18/10: T è entrato per primo (R3-b, `7845fc3d3`), DV ha girato il flag `CATEGORY_ROLES_IN_TOKENS` al
      merge del target (`3dba7f894`); da allora i 12 ruoli sono tenuti uguali ai colori dei grafici, nei due temi.
  - **Resta il secondo:** il layer `category` del Designer Lab diventa una vista dei ruoli, e `chartCategories.ts`
    legge i tipi dai ruoli col ponte di `roleColors`; allora la copia nel file sparisce. Lotto da programmare con L
    (archiviato), coordinatore, 17/10.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezione
    «Giro 3».
- **DV-12 · L'E2E del pannello posizioni trattiene la «prima» richiesta del report, non quella della pagina sotto
  prova** — minimo, test; DV, 18/10 (slot del giro 3, fuori area: `e2e/portfolio/dashboard.spec.ts`, «Positions panel
  publishes its loading state through data-busy»).
  - Rosso nella run intera su `08512c952`, verde da solo; verde nello slot di B4 (`f35fd9026`), con lo stesso ordine.
  - `login()` atterra su `/dashboard` e aspetta solo che l'app arrivi: una POST `/portfolio/report` della pagina
    d'atterraggio partita dopo la rotta è «la prima», il `goto` la abbandona, e il pannello non è mai occupato.
  - Rimedio nel test (`test-author`, proprietario dello spec): `page.goto('about:blank')` prima della rotta, oppure
    trattenere la richiesta della pagina sotto prova.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), passo G3-9.
- **DV-13 · L'E2E «export JSON, reset all, import back» del Lab vuole due fonti di colore che dal 16/10 sono una** —
  minimo, test; DV, 18/10 (slot del giro 3, fuori area: `e2e/designer-lab/designer-lab-live.spec.ts`).
  - Deterministico: il sottotitolo delle transazioni e l'intestazione di `DataTable` leggono tutti e due
    `--lf-text-muted` (`546204732` e `77bfa6a39`, 16/10). La modifica della variabile vince su quella del letterale, e
    l'intestazione esce rosa invece che blu.
  - Rimedio nel test (`test-author`; il Lab, L, è archiviato): due elementi con fonti diverse, con la precondizione
    scritta.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), passo G3-9.
- ✅ **DV-14 · `PriceChartFull` e `CandlestickChart` nascono ancora alla densità del caricamento** — minimo; DV, 19/10
  (DPR, grafici sfocati dopo un cambio di schermo). **Chiusa il 19/10** sulla punta `56666d2ce` (Y-N65 entrato in
  `5cb47395f`), in attesa del commit del coordinatore: le due chiamate su `chartInitOptions`, la deroga
  `PIXEL_RATIO_PENDING` vuota (il meccanismo resta per un grafico che non possa migrare subito).
  - I due file sono di Y-N65 (1.3) per circa un giorno: restano fuori dal lotto DPR, nella deroga `PIXEL_RATIO_PENDING`
    del gate K-13 (`frontend/src/lib/components/charts/chartFlagFont.test.ts`). Finché ci restano, i loro grafici
    (dettaglio dell'asset e dei cambi) nascono alla densità di quando la scheda si è aperta e non seguono un cambio.
  - Rimedio, un lotto piccolo di DV quando la 1.3 li dà liberi (coordinatore, 19/10): la riga
    `echarts.init(chartContainer, CHART_INIT_THEME, chartInitOptions(chartContainer))` e l'import in ciascuno, e le
    due voci tolte dalla deroga, che il gate rende rosse appena i file passano `chartInitOptions`.
  - Dettagli: [piano di DV](../Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md), sezione «DPR».

---

## IW · Colori dell'import (Phase_1/10_colorSystem)

> Workstream IW del programma colori, aperto il 16/10 (D-T28): migrazione 1:1 ai ruoli di colore della propria area,
> senza decisioni di design, con la skill `theme-roles` e lo skill comune del design system (D-T29). Area: `components/transactions/import/**`, `wizard/**`, `modals/ImportWizardModal`, `ParseDetailModal`, `ImportBrokerMismatchModal`.
> Il piano: `../Phase_1/10_colorSystem/IW-importColors/`. Gli ID di questa sezione sono `IW-n`.

- ✅ **IW-1 · Quattro pulsanti pieni verdi e blu in attesa dei ruoli hover** — basso; IW, 16/10 (D2). Restano legacy
  `asset-group-confirm-all`, `asset-group-confirm-{id}` (`AssetGroupStep`), `import-wizard-warning-confirm` (il ramo
  info) e `create-primary-confirm` (`ImportWizardModal`). T ha aggiunto `hover:bg-lf-success-hover` e
  `hover:bg-lf-info-hover` (`f043c1b58`): si convertono dopo la base merge. Dettagli: [piano IW](../Phase_1/10_colorSystem/IW-importColors/plan-phase00ImportColors.prompt.md), sezione «Restano legacy».
  ✅ 16/10, `9c79d5b35` (checkpoint 2 di IW, passo 5 del piano): i quattro su `success`/`info` con i
  loro hover; `create-primary-confirm` resta nei «da rivedere» (IW-7).
- **IW-2 · Le stelle «primario» degli identificativi senza ruolo** — basso; IW, 16/10 (D6). `AssetGroupStep`,
  `fill-amber-400 text-amber-500` su legenda e badge (6 classi): serve un ruolo «marcatore», o i categoriali.
  Dettagli: piano IW, sezione «Restano legacy».
- **IW-3 · Badge degli identificativi categoriali, con l'anello ambra del primario** — basso; IW, 16/10.
  `AssetGroupStep`: classi da `KIND_TONES.identifier` più `ring-amber-400 dark:ring-offset-gray-900` sull'elemento
  (2 classi nel file): coi categoriali di B4. Dettagli: piano IW, sezione «Catene di classi».
- **IW-4 · Lo `<style>` di `ImportBrokerMismatchModal` sui token `--lf-cmp-broker-mismatch-*`** — basso; IW, 16/10
  (D3). 12 token con override `.dark` in `lib/theme/components/dialogs.css`: con W6/B5 di T, che toglie i token non
  più letti. Dettagli: piano IW, decisione D3.
- **IW-5 · Il chip viola del tasso implicito delle coppie** — basso; IW, 16/10. `lib/utils/transactions/pairCellHtml.ts`,
  `text-violet-600 dark:text-violet-400`: categoriale, e rispecchia `renderDualHtml` di `TransactionBulkModal` (TR); si
  muovono insieme. Dettagli: piano IW, sezione «Restano legacy».
- **IW-6 · Colori passati per prop di classe ad `AssetSelect`** — basso, design; IW, 16/10. `confidenceBadgeClass`
  (`ImportWizardModal` → `ReviewStep` → `badgeClass` di `ui/select/AssetSelect`) porta colori, ora sui ruoli; la regola 3
  della skill comune vuole una variante (`variant="…"`). Con T. Dettagli: piano IW, sezione «Catene di classi».
- **IW-7 · Scelte «da rivedere» della migrazione dell'import** — basso, aspetto; IW, 16/10. Stato dei duplicati tutto
  `warning` (D1), timeline del set, stepper e barre su `checked`, fuoco blu diventato verde, pulsanti contornati al 3:1,
  bordi tratteggiati dei gruppi di asset sul `-line`, testi `-800` su card a `text-lf-X`, maniglia su `bg-lf-input`,
  testo attenuato su `neutral` (~4:1), `create-primary-confirm` su `info` (è l'azione primaria del suo dialogo: forse
  `action`). Dettagli: piano IW, «Da rivedere per il developer» e note dei lotti.
- **IW-8 · Note di test-author su `tx-brim-import.spec.ts` e `tx-import-resolution.spec.ts`** — basso, test; IW, 16/10
  (area W: da spostare). In T4 la guardia `if` salta l'asserzione solo quando qualcosa si rompe, e la guardia esterna usa
  il testo tradotto `text=Resolve Assets` (c'è `import-wizard-resolve-section`); T1 non importa mai con questo campione;
  i commenti «amber badge» di `tx-import-resolution.spec.ts` (riga 43 e IWR-001) diventano falsi dopo IW-5. Dettagli:
  piano IW, passo 1, «Spec T4».

---

## TR · Colori delle transazioni (Phase_1/10_colorSystem)

> Workstream TR del programma colori, aperto il 16/10 (D-T28): migrazione 1:1 ai ruoli di colore della propria area,
> senza decisioni di design, con la skill `theme-roles` e lo skill comune del design system (D-T29). Area: il resto di `components/transactions/**` e `routes/(app)/transactions/**`.
> Il piano: `../Phase_1/10_colorSystem/TR-transactionColors/`. Gli ID di questa sezione sono `TR-n`.

- ✅ **TR-1 · Il sottotitolo di `/transactions` è ancora legacy** — minimo; TR, 16/10. `routes/(app)/transactions/+page.svelte:738`
  (`text-gray-500 dark:text-gray-400`) resta com'è, perché il test «dark-theme pick of a text-gray-500 element» di
  `e2e/designer-lab/designer-lab-picker.spec.ts` lo usa come elemento rimappato da `app.css`. Migra a `text-lf-muted`
  quando L sposta il soggetto del test: si sblocca con l'ingresso di L-20 (coordinatore, 16/10 12:12). Dettagli: [piano di TR](../Phase_1/10_colorSystem/TR-transactionColors/plan-phase00TransactionColors.prompt.md),
  sezione «Cosa resta, e perché».
  ✅ 16/10, `546204732` (lotto 6 di TR): L-20 (`d2e4ae947`, in `dev_release2` con `460529690`) toglie il sottotitolo
  dal test; il `<p>` passa a `text-lf-muted`.
- ✅ **TR-2 · Due conferme verdi piene senza ruolo per l'hover** — basso; TR, 16/10. `PromoteMergeModal.svelte:262`
  (`bg-green-600 hover:bg-green-700`) e `TransactionActionModal.svelte:387` (lo stesso verde, col ramo ambra dello split
  nello stesso ternario) restano legacy e interi: manca un `success-hover`. Serve un ruolo di T, oppure una decisione:
  `bg-lf-action`, o il ramo ambra su `bg-lf-warning hover:bg-lf-warning-hover text-lf-on-status`. Dettagli: piano di
  TR, sezione «Cosa resta, e perché».
  ✅ 16/10, `70bae91b4` (lotto 5 di TR, secondo checkpoint): con i ruoli nuovi di T (`f043c1b58`), le due conferme passano a
  `bg-lf-success hover:bg-lf-success-hover text-lf-on-status`, e il ramo dello split a `bg-lf-warning
  hover:bg-lf-warning-hover`, nello stesso ternario (OK del coordinatore, 12:12).
- **TR-3 · Lo `<style>` di `TransactionsTable` tiene 13 letterali** — basso; TR, 16/10. Sono:
  - la base della tinta del broker, `white`/`#0f0f18`: la stessa ricetta di `UnifiedLotsTable` di BK. **Passa a T**, nel
    lotto dei component tokens (coordinatore, 16/10 12:12);
  - l'hover traslucido dell'icona del tipo, `rgb(0 0 0/.05)`/`rgb(255 255 255/.08)`: nessun ruolo traslucido;
  - il pallino evento viola: categoria;
  - l'impulso indaco di riga: nessun ruolo d'evidenza.

  Dettagli: piano di TR, sezione «Cosa resta, e perché».
- **TR-4 · Le categorie lasciate nelle transazioni** — basso; TR, 16/10. 120 classi aspettano i ruoli categoriali:
  - i tipi d'evento di `AssetEventPicker`;
  - la codifica A/B/«unisci» di `PromoteMergeModal`;
  - il chip FX viola;
  - la promozione indaco;
  - lo split viola;
  - la riga «in attesa» e i badge d'effetto del WAC.

  Con loro va portato a un `data-*` il selettore `span.text-indigo-500` di `e2e/transactions/tx-wac-bulk.spec.ts:676`.
  Dettagli: piano di TR, sezione «Cosa resta, e perché».
- **TR-5 · `scrollbar-thumb-gray-300 dark:scrollbar-thumb-slate-600` sulla tabella WAC** — minimo; TR, 16/10.
  `WacPreviewSection.svelte`, tabella delle transazioni qualificanti: colori di palette che il gate non conta (il
  prefisso `scrollbar-thumb` non è nella lista) e che non hanno un ruolo. Funzionano, col loro `dark:` esplicito.
  Probabile anche altrove: da aggiungere ai prefissi del gate quando esisterà un ruolo. Dettagli: piano di TR, passo 2.

---

## AF · Colori di asset e cambi (Phase_1/10_colorSystem)

> Workstream AF del programma colori, aperto il 16/10 (D-T28): migrazione 1:1 ai ruoli di colore della propria area,
> senza decisioni di design, con la skill `theme-roles` e lo skill comune del design system (D-T29). Area: `components/assets/**`, `routes/(app)/assets/**`, `components/fx/**`, `routes/(app)/fx/**`.
> Il dettaglio asset (`routes/(app)/assets/[id]`, `components/assets/detail/`) è entrato dopo X FE5c, con il lotto 9.
> **Stato al 16/10, 18:30:** area migrata, tutto nel target (`c179a5144`): m1 da 1.946 a 170, m2 da 6 a 0. Restano
> solo classi annotate: AF-1 (aspetta la designer), AF-2, AF-3, AF-5, AF-7 (lotto degli interruttori di T); da
> chiudere AF-8 (conferma) e AF-10 (ruolo di T). La sera del 16/10 il lotto dei component tokens di file, media e menu
> contestuale (piano AF, passo 16) lascia AF-11; il suo slot pesante segnala AF-12 e AF-13. Nella notte del 17/10
> `lib/theme/drawnColors.ts` passa ai ruoli (piano AF, passo 17) e lascia AF-14.
> Il piano: `../Phase_1/10_colorSystem/AF-assetFxColors/`. Gli ID di questa sezione sono `AF-n`.

- **AF-1 · Accenti degli strumenti della barra del grafico** — basso; AF, 16/10. Restano legacy, perché sono tinte che
  distinguono strumenti:
  - gli interruttori misura (viola), editor (ambra) ed estetica (smeraldo), col loro ramo a riposo;
  - l'accento viola della sezione misure;
  - le icone di sezione: segnali blu, metadati azzurro.

  Li trovi in `routes/(app)/fx/[pair]` (54 classi) e, dopo FE5c, in `routes/(app)/assets/[id]` (42: i tre interruttori)
  e in `components/assets/detail/` (13: `AssetDetailMetadataPanel` 1, `AssetDetailMeasuresSection` 11,
  `AssetDetailSignalsPanel` 1). La Q12 della designer («niente arcobaleno») va verso un colore unico: lo decidono la
  designer o T. Dettagli: [piano AF](../Phase_1/10_colorSystem/AF-assetFxColors/plan-phase00AssetFxColors.prompt.md),
  sezione «7. Restano legacy».
- **AF-2 · Tipi distinti dalla tinta** — basso; AF, 16/10. Il badge `txScope` di `AssetTable` (proprio smeraldo, altri
  blu, analisi grigio; 12 classi) e l'origine dell'identificativo di `IdentifierPrimaryChooser` (fornitore blu, salvato
  verde; 7 classi) restano categoriali, come `KIND_TONES`. I test `AssetTable.test.ts:190–192, 209` e
  `asset-list.spec.ts:782–795` li leggono ancora per classe. Dettagli: piano AF, sezione «7».
- **AF-3 · Riquadri decorativi degli stati vuoti** — minimo; AF, 16/10. Le monete ambra di `routes/(app)/fx/+page` e il
  grafico verde di `routes/(app)/assets/+page` sono una tinta per pagina, non uno stato: restano legacy (4 + 4 classi).
  Dettagli: piano AF, sezione «7».
- **AF-4 · Bordo rosso di `AssetCurrencyChangeModal` attraverso `ModalBase.contentClass`** — medio-basso; AF, 16/10.
  Va portato con TC-10 e con la regola 9 dello skill `design-system`. Con un ruolo (`border-lf-danger-line`)
  perderebbe contro `border-lf-raised`: serve una variante di `ModalBase` (T). Intanto la catena resta legacy (2
  classi). Dettagli: piano AF, sezione «2. Catene», C1. ✅ 16/10: T ha aggiunto `ModalBase tone="danger"`
  (`4d8ae68c4`); `AssetCurrencyChangeModal` lo usa e non passa più colori in `contentClass` (checkpoint D, piano AF passo
  13).
- **AF-5 · Chip `<code>` sulle tinte dei banner** — minimo; AF, 16/10. In `PriceDataImportModal` (6 classi) ed
  `EventDataImportModal` (12) i chip sono `bg-white/30 dark:bg-slate-700/50` dentro `InfoBanner`. Nessun ruolo dà un
  chip su una tinta in tutti e due i temi, e `htmlSink.gate.test.ts:73` ne fissa uno alla lettera. Restano legacy fino a
  un ruolo di T. Dettagli: piano AF, sezione «2», C5.
- **AF-6 · Velo e icona bianca sull'immagine dell'asset** — minimo; AF, 16/10. In `AssetModalDetails:104–107`
  (`bg-black/40`, `text-white`) mancava un ruolo «testo sul velo». ✅ 16/10: T ha creato `text-lf-on-overlay`
  (`f043c1b58`); il velo va su `bg-lf-overlay` e l'icona su `text-lf-on-overlay` (checkpoint AF dopo `bfd33a0f5`).
  Da rivedere: il velo è più scuro (60 % invece del 40 %). Dettagli: piano AF, passo 12.
- **AF-7 · Tre interruttori dell'area** — basso; AF, 16/10. `AssetModalFooter` attivo/benchmark e l'interesse di mora
  di `ScheduledInvestmentEditor` (12 classi) restano per il lotto unico degli interruttori di T, già nel suo
  inventario. Dettagli: piano di T, «Il lotto degli interruttori (Q2)».
- **AF-8 · `hover:bg-libre-green-dark` è una classe morta** — minimo, da decidere; AF, 16/10. `--color-libre-green-dark`
  non esiste, quindi oggi i pulsanti di `BoundaryDateModal` e `ScheduledInvestmentEditor` non cambiano al passaggio. La
  migrazione propone `hover:bg-lf-action-hover`, che aggiunge l'hover di tutti i primari: va confermato. Dettagli:
  piano AF, sezione «6».
- **AF-9 · Dettaglio asset in attesa di X FE5c** — medio; AF, 16/10. In `routes/(app)/assets/[id]/+page.svelte` (155
  classi dopo FE5c) e nei 6 componenti di `components/assets/detail/` (145) la migrazione parte dopo l'ingresso di FE5c
  (lotto 9). Dettagli: piano AF, sezione «5. Lotti». ✅ 16/10: FE5c è entrato (`a44951cf5`) e il lotto 9 è migrato sui file
  reali, da 300 a 55 classi (tutte AF-1; checkpoint D, piano AF passo 13).
- **AF-10 · Un bottone secondario su una superficie `panel` non ha un ruolo** — minimo; AF, 16/10. Il piede `panel` di
  `AssetCurrencyChangeModal` ha un «Annulla» grigio che prima era due passi sopra il piede (slate-200 su slate-50). Con
  `bg-lf-panel` sparirebbe: ha preso `bg-lf-neutral hover:bg-lf-input/30`, il ruolo più vicino. È la domanda aperta 3
  dello skill `design-system` (`panel` = `hover`): serve un neutro «sopra panel» con il suo hover (T). Dettagli: piano
  AF, passo 6, lotto 6.
- **AF-11 · L'icona immagine di `FileUploader` resta sui component tokens** — minimo; AF, 16/10. Nel lotto dei
  component tokens di file, media e menu contestuale (8 componenti sui ruoli, `dialogs.css` e `files.css` cancellati)
  il blu dell'icona delle immagini resta legacy: è una categoria (un colore per tipo di file), non uno stato. Restano i
  suoi 2 token in `media.css`, con la regola `.dark` e l'import di `FileUploader`; vanno via con i ruoli categoriali.
  Dettagli: piano AF, passo 16.
- **AF-12 · `image-crop.spec.ts` F1 cerca il tema scuro nelle classi** — basso; AF, 16/10 (slot E). Il `beforeEach` di
  «Dark Mode - Image Crop Components» decide se cliccare il toggle con `isVisible()` istantanei e col primo elemento
  `[class*="dark"]` della pagina, e F1 accetta lo stesso ripiego come prova del tema scuro. La migrazione toglie le classi
  `dark:`: F1 rosso alle 22:30, con la pagina in chiaro (verdetto del triage: assunzione). La correzione: aspettare il
  toggle e asserire `html.dark`; la scrive test-author, con l'OK del coordinatore (la spec non è di AF). Dettagli: piano
  AF, passo 16.4. 16/10, 23:00: correzione scritta (piano AF, passo 16.5). ✅ per F1, 16/10: commit `f2f13184b`, verde
  nello slot di recupero (`image-crop` 42/42, piano AF passo 16.6). Resta aperto il seguito su F2 e F3, che decidono
  con `isVisible()` istantanei se aprire le modali e non verificano il tema.
- **AF-13 · Il runner rifà la build del frontend per un `.DS_Store`** — basso; AF, 16/10 (slot E).
  `check_frontend_needs_build` (`scripts/cli_base.py`) confronta l'mtime di ogni file sotto `frontend/src`, file nascosti
  compresi: un `.DS_Store` toccato da macOS ha fatto rifare la build a metà di uno slot (circa 7 minuti col carico a
  160). Va escluso, insieme agli altri file nascosti; tocca al proprietario del runner. Dettagli: piano AF, passo 16.4.
  Si è ripetuto nello slot di recupero (23:52, una build in più all'avvio di `asset-list`; piano AF, passo 16.6).
- **AF-14 · Il foglio di calcolo in chiaro resta sul tema della libreria** — minimo; AF, 17/10. Con `drawnColors.ts` sui
  ruoli, l'anteprima dei fogli (`FilePreviewModal`, cheetah-grid) disegna il tema scuro tutto dai ruoli, mentre in chiaro
  tiene `MATERIAL_DESIGN` della libreria (fondo, testo, selezione blu) con i soli due bordi sui ruoli: una scelta
  provvisoria, nel punto 35 della raccolta per la designer, insieme alla riga indicata su `mark` e all'iniziale degli
  avatar con `readableText`. Un tema unico dai ruoli per i due temi è la sua decisione (riga 10 del rapporto di L).
  Dettagli: piano AF, passo 17.

---

## BK · Colori dei broker (Phase_1/10_colorSystem)

> Workstream BK del programma colori, aperto il 16/10 (D-T28): migrazione 1:1 ai ruoli di colore della propria area,
> senza decisioni di design, con la skill `theme-roles` e lo skill comune del design system (D-T29). Area: `features/brokers/**`, lotti compresi, e `routes/(app)/brokers/**`.
> Il piano: `../Phase_1/10_colorSystem/BK-brokerColors/`. Gli ID di questa sezione sono `BK-n`.

- **BK-1 · Ruoli del broker OWNER/EDITOR/VIEWER ancora in palette** — medio; BK, 16/10. 69 classi: il badge di
  `BrokerCard`, il badge della quota di `routes/(app)/brokers/[id]/+page.svelte`, le tre sezioni di `BrokerSharingPanel`
  (icone, chip e avatar; il grigio VIEWER resta col set), più `utils/broker/brokerRoleHelpers.ts` (T). Categoria: aspetta
  i ruoli categoriali. Details: [piano BK](../Phase_1/10_colorSystem/BK-brokerColors/plan-phase00BrokerColors.prompt.md),
  sezione «Restano legacy».
- **BK-2 · Badge dei lotti ancora in palette** — medio; BK, 16/10. 84 classi: direzione, stato (CLOSED compreso), in
  transito e custodia di `UnifiedLotsTable` (60), la chip «in transito» di `LotGanttChart` (4), i marcatori degli eventi e
  le icone «in transito» di `LotCustodyModal` (20). Aspettano il giro dei badge (DV-7), da allineare a
  `LOT_STATE_COLORS`. `SIGN_BADGE` (T, 16/10) non fa per loro: nessuno dice un guadagno o una perdita; LONG/SHORT è la
  direzione della posizione, non un segno (regola 7 della skill `design-system`), e ha un bordo che `SIGN_BADGE` non ha.
  Details: [piano BK](../Phase_1/10_colorSystem/BK-brokerColors/plan-phase00BrokerColors.prompt.md),
  sezione «Restano legacy» e passo S5b.
- **BK-3 · Interruttore «Attivo» di `BrokerForm`** — minimo; BK, 16/10. 4 classi (`features/brokers/BrokerForm.svelte`,
  il `role="switch"` e la sua manopola) → lotto degli interruttori di T, che nel suo inventario ha ancora il percorso
  `components/brokers/BrokerForm.svelte (298)`. Details: [piano di T](../Phase_1/10_colorSystem/T-tokensTheme/plan-phase01TokensTheme.prompt.md),
  «Il lotto degli interruttori (Q2)».
- ✅ **BK-4 · Testo sullo scrim** — minimo; BK, 16/10. L'icona `text-white` sullo scrim del selettore d'icona di
  `BrokerForm` non aveva un ruolo. Chiusa il 16/10 con `text-lf-on-overlay`, il ruolo provvisorio di T (`f043c1b58`),
  nel mini-checkpoint di BK dopo la base merge `2eef01e59`. Details: [piano BK](../Phase_1/10_colorSystem/BK-brokerColors/plan-phase00BrokerColors.prompt.md),
  passo S5b.
- **BK-5 · Campione della legenda «stimato al costo»** — minimo; BK, 16/10. In `LotComparisonChart` il trattino
  `border-slate-500 dark:border-slate-400` (2 classi) ricopia `LOT_COMPARISON_COLORS.estimatedValue` di DV: migra quando
  DV porta quella coppia su un ruolo, così legenda e linea restano uguali. Details: [piano BK](../Phase_1/10_colorSystem/BK-brokerColors/plan-phase00BrokerColors.prompt.md),
  sezione «Restano legacy».
- **BK-6 · `<style>` con `--lf-cmp-*` nell'area** — basso; BK, 16/10. `BrokerImportFilesModal` (28 letture da
  `files.css`) e `UnifiedLotsTable` (8 da `table.css`, più le variabili dei broker di DV): portarli ai ruoli lascerebbe
  senza lettori le definizioni di T (gate (c) di `themeComponentTokens`) → B5/W6 di T. Details: [piano BK](../Phase_1/10_colorSystem/BK-brokerColors/plan-phase00BrokerColors.prompt.md),
  sezione «Stato attuale».
- **BK-7 · `toHaveClass(/selected/)` sulle righe di DataTable** — minimo; BK, 16/10. `e2e/brokers/brokers-detail.spec.ts`
  righe 392–419 (spec della 1.3): la regex prenderebbe anche un ruolo `bg-lf-selected` quando `DataTable` (T, W6) migra;
  meglio leggere `aria-selected`. Details: [piano BK](../Phase_1/10_colorSystem/BK-brokerColors/plan-phase00BrokerColors.prompt.md),
  sezione «Stato attuale».
- ✅ **BK-8 · Lotto L4, `LotCustodyModal`** — medio; BK, 16/10. 205 classi riservate a Y fino al suo ingresso (coordinatore,
  16/10); poi migrazione dalla versione di Y, 205 → 20. Chiusa il 16/10 sera nel checkpoint L4 di BK, con il misto di
  G-18 (`contentClass` tolto); restano i 20 di BK-2. Details: [piano BK](../Phase_1/10_colorSystem/BK-brokerColors/plan-phase00BrokerColors.prompt.md),
  passo S7.

---

## IM · Colori delle impostazioni (Phase_1/10_colorSystem)

> Workstream IM del programma colori, aperto il 16/10 (D-T28): migrazione 1:1 ai ruoli di colore della propria area,
> senza decisioni di design, con la skill `theme-roles` e lo skill comune del design system (D-T29). Area: `features/settings/**`, `routes/(app)/settings/**`, `features/support/**`, `features/update-check/**`.
> Il piano: `../Phase_1/10_colorSystem/IM-settingsColors/`. Gli ID di questa sezione sono `IM-n`.

- ✅ **IM-1 · `DonationPopupModal` sui ruoli** — basso (28 classi, `#ffffff`); origine IM, 16/10. Chiusa il 16/10 con
  l'OK di A, nel checkpoint IM 2: 28 → 0, e via da `app.css` le regole morte `html.dark .bg-libre-beige` e
  `html.dark .text-libre-dark` (C4). Commit `8636a368f`.
  Dettagli: [piano IM](../Phase_1/10_colorSystem/IM-settingsColors/plan-phase00SettingsColors.prompt.md), «A7».
- ✅ **IM-2 · Icona della fotocamera sul fondale dell'avatar** — minimo (`ProfileTab`, `text-white`); origine IM, 16/10.
  Chiusa il 16/10, commit `8636a368f`: `text-lf-on-overlay`, ruolo di T da `f043c1b58`. Dettagli: piano IM, «A7».
- **IM-3 · Famiglie di plugin di «Informazioni»** — basso (`AboutTab`: 4 card e 4 badge, 20 classi); origine IM, 16/10.
  Accenti categoriali (asset verde, cambi blu, import ambra, segnali viola) e i neutri delle loro card restano legacy
  (G3) finché non ci sono i ruoli categoriali; in scuro le card restano blu notte. Dettagli: piano IM, §5 «IM-5».
- **IM-4 · Cuore di «Fatto con ❤»** — minimo (`AboutTab`, `text-red-500` decorativo); origine IM, 16/10. Nessun ruolo:
  `text-lf-danger` sarebbe un uso improprio. Da chiedere a T o alla designer. Dettagli: piano IM, §5 «IM-5».
- **IM-5 · Marchi dei social** — basso (`supportLinks.ts`, 14 classi; anello scuro del bottone «copia» di
  `SocialShareModal`); origine IM, 16/10. X e TikTok usano neutri Tailwind come nero del marchio, gli altri `text-white`
  su colori di terzi: manca un ruolo, o un'eccezione dichiarata. Dettagli: piano IM, §5 «IM-6».
- **IM-6 · Badge del provider nel log dello scheduler** — minimo; origine IM, 16/10. Le classi vengono da
  `PROVIDER_COLORS` di `lib/utils/providerHelpers.ts` (categoriali, fuori area): lo span segue la tabella quando migra.
  Dettagli: piano IM, §2.

---

## Sessioni della 1.3.0 (fase 01)

> Aperte il 14/10 dal coordinatore della 1.3. Piano: [fase 01](../Phase_1/README.md). Ogni sessione scrive solo la
> propria sezione, qui sotto, nello stesso checkpoint in cui la voce nasce; le voci di altre sezioni chiuse da una
> sessione della 1.3 le marca ✅ il coordinatore.

## H · Piattaforma (fase 01)

> 16/10, treno 110 (`0ecc5ed27`): chiuse dal coordinatore H-1, H-4, H-6, H-9, H-14, H-15, H-16 (lotti di H entrati). Restano aperte H-3 (opzione A, P24), H-5, H-17 (le due righe di B), H-18 (→ sezione C), H-19 (→ A).

Piano: [`01_platform`](../Phase_1/01_platform/plan-phase01Platform.prompt.md).

- ✅ **H-1 · Nella prosa della devWiki restano menzioni dei percorsi spostati da CP1, CP2a e CP4** — minimo; H, 14-15/10.
  - **CP1**: 9 menzioni in 8 pagine, fuori dalle tabelle «Source files»: `domains/scheduler.md:13`,
    `features/F-011.md:20`, `F-014.md:20`, `F-052.md:22`, `F-073.md:25`, `entities/market-data-scheduler.md:22-23`.
    - Due sono storiche: `features/F-078.md:34` e `sources/phase00-brim-danske-bank-2026-10.md:37`.
    - Nella tabella di `domains/scheduler.md:82` la riga dice ancora «(planned) … (not yet created)».
  - **CP2a**: 9 menzioni di `backend/app/config.py` (oggi `backend/app/config/__init__.py`) in 8 pagine:
    `concepts/runtime-lanes.md:29`, `decisions/prod-test-data-separation.md:28`, `utils-leaf-functions-only.md:83`,
    `port-6040-scheme.md:34`, `problems/db-path-argument-ignored-by-alembic.md:22`, `features/F-011.md:20`,
    `F-064.md:20`, `sources/r2-parallel-features-pwa-borsa-fx.md:82` e `:91`. L'ultima è una tabella sotto un
    titolo che il controllo dei percorsi non legge.
  - **CP4**: 2 menzioni di `backend/app/api/v1/system.py`, oggi il pacchetto `backend/app/api/v1/system/`, in prosa:
    `features/F-102.md:24` e `problems/docker-system-info-missing-deps.md:24`. Le 6 righe «Source files» sono già
    aggiornate.
  - È lo stesso caso di T-W1.

  Dettagli: [piano H](../Phase_1/01_platform/plan-phase01Platform.prompt.md), §14 «CP1 passo 1».
- ✅ **H-2 · I test del backend costruiscono frontend e MkDocs dentro i 300 s d'avvio del server condiviso** (chiusa 16/10 dal coordinatore: `1c67dd5d9`, il `--build-only` del runner) — basso; H,
  14/10.
  - `dev.py server --test` ricostruisce il frontend se un file di `frontend/src` è più recente della build: basta un
    `.test.ts`.
  - In un worktree senza `node_modules`, `api sync` chiama `npx openapi-zod-client` e la build chiama
    `npx svelte-check` (`dev.py:638`).
  - Oggi la regola è nelle istruzioni. La cura starebbe nel runner: costruire prima di far partire il conto alla
    rovescia, oppure fermarsi subito con un messaggio se mancano `node_modules`.
  - È vicina a I-06 del backlog 38.

  Dettagli: piano H, §14 «CP1 passo 0» e «Fuori pista 3».
- **H-3 · Una chiave d'istanza persa dopo il primo uso sembra un primo uso** — medio-basso; H, revisione di sicurezza di
  CP3 (15/10).
  - Se `secrets/instance.key` sparisce, per esempio con un ripristino senza `secrets/`, `derive_key` ne genera una
    nuova senza avvisi.
  - Ciò che la vecchia chiave cifrava resta illeggibile, e i dati nuovi si cifrano con una chiave che non sta in nessun
    backup.
  - Cura proposta: al primo uso, un valore di controllo della chiave nel DB (per esempio un HMAC con la chiave derivata
    `instance.key-check.v1`). Se il valore c'è, `derive_key` non genera mai una chiave e rifiuta una chiave diversa.
  - Serve il DB: si fa con X e B al loro primo uso di `derive_key`. Oggi la doc admin chiede di ripristinare
    `secrets/` insieme ai dati.
  - Note di progetto per X e B:
    - una chiave per istanza, mai la stessa su più istanze;
    - un backup cifrato con una chiave derivata non deve contenere anche `secrets/`;
    - una chiave configurata è casuale, non una passphrase.

  Dettagli: piano H, §14 «CP3 passo 2».
  - 17/10: l'opzione A resta **P24**, una decisione del developer ancora aperta: voleva più contesto. Il contesto è nel
    piano H, §14, «H-3, opzione A: il contesto per la decisione P24»: dove sta la chiave, che cosa protegge, che cosa
    succede se il file sparisce, perché nel cloud è più sicuro, e l'opzione A con il suo peso. Il consiglio è
    rimandarla dopo la 1.3: l'opzione B, già entrata, basta, e la A migliora solo il self-hosted.
- ✅ **H-4 · `validate_test_data_dir` solleva un `PermissionError` grezzo per una cartella gestita non attraversabile** —
  minimo; H, 15/10.
  - In modalità test, `_same_filesystem_location` chiama `Path.exists()`, che su Python 3.13 solleva con `EACCES`.
  - Vale per `sqlite/`, e da CP3 anche per `secrets/`.
  - È fail-closed, ma senza un messaggio chiaro: andrebbe trasformato in `ValueError` col percorso.

  Dettagli: piano H, §14 «CP3 passo 2», «Fuori pista».
- **H-5 · Debito di traduzione delle pagine admin toccate da H** — basso; H, 15/10.
  - `translate-validate --hide-localized` conta 102 errori nel repository. 33 vengono da CP5a: un riquadro su
    `/api/v1/system/ready` in `docker_advanced` e in `service_exposure`, in IT, FR ed ES.
  - Gli altri 69 c'erano già, in `configuration`, `filesystem` e `index`; ci sono anche le righe di CP3 e CP4.
  - CP6 aggiunge la pagina nuova `admin/hosting_providers` (solo inglese, titolo di navigazione compreso), le righe delle
    variabili del blocco e dei controlli d'avvio in `configuration`, e un punto in `admin/index`.
  - Si chiude con la traduzione, che parte solo su richiesta esplicita del developer.
  - 16/10, lotto «b-doc-notes» (B-4, B-5): righe nuove in `filesystem`, `docker_advanced` e `index`.
    `translate-validate --file` dà 27, 42 e 15 errori, compreso il debito che c'era già. **Ordine**: il testo nuovo
    di `filesystem` e `docker_advanced` rimanda a `cli_tools.md#backup` e `#backup-docker`, ancore che
    `cli_tools.{it,fr,es}.md` non hanno finché non si chiude B-7. Va tradotto insieme a B-7 o dopo, altrimenti la build
    rigorosa IT/FR/ES non trova le ancore. L'ancora `#what-to-back-up` c'è già nelle 4 lingue.
  - 16/10, P17: la sottosezione nuova «🧭 The Visitor's Address» (`#client-address`) e l'ultimo paragrafo riscritto dei
    «Limits» in `connection_checks`, e una riga in `configuration` che punta a `connection_checks.md#client-address`.
    **Ordine**: `configuration` va tradotta insieme a `connection_checks` o dopo, che deve tenere
    `{: #client-address }`; altrimenti la build rigorosa di quella lingua non trova l'ancora.
  - 17/10, H-36: un blocco nuovo in fondo a `#client-address` di `connection_checks` (un paragrafo, quattro punti, un
    paragrafo) e due frasi nel §2 di `docker_advanced`, che rimandano a `connection_checks.md#client-address`.
    **Ordine**: `docker_advanced` va tradotta insieme a `connection_checks` o dopo, per la stessa ancora.
  - 17/10, H-39 e H-40:
    - in `configuration`, «Startup Checks», due righe nuove (la protezione dai frame e la CSP report-only spente nel
      profilo managed);
    - in `connection_checks`, «Limits», il paragrafo «It cannot always see where visitors are» riscritto in parte
      (IPv4 e IPv6 su Docker Engine), e una clausola nel punto «To fix it» di «The Visitor's Address».
    - `hosting_providers` e le pagine per sviluppatori sono solo in inglese.

  Dettagli: piano H, §14 «CP5a passo 2», «CP6 passo 4» e «Lotto b-doc-notes».
- ✅ **H-6 · Due controlli d'assenza in `AboutTab.test.ts` non possono fallire** — minimo; H (test-author, CP5b), 15/10.
  - «omits a provider section entirely when nothing is installed» e «shows each section only when its own list has
    something in it» cercano `settings.assetProviders` con un confronto esatto.
  - L'intestazione è però «etichetta (n)», quindi la ricerca non trova niente anche quando la sezione c'è.
  - Cura: confrontare con `/settings\.assetProviders/`, come fa il test nuovo di CP5b.

  Dettagli: piano H, §14 «CP5b».
- **H-7 · Senza `tzdata` di PyPI, su un sistema senza database dei fusi lo scheduler va in UTC** — basso; H (CP7a,
  docs-writer), 15/10.
  - `zoneinfo` legge il database del sistema, poi il pacchetto `tzdata` di PyPI, che non è nel lock.
  - Nell'immagine Docker lo copre `tzdata-legacy` (CP7a). Su un host senza database (Windows), ogni fuso salvato
    ricadrebbe in UTC (`scheduler.py:20-24`).
  - Cura: `tzdata` nel Pipfile, nella finestra delle dipendenze.

  Dettagli: piano H, §14 «CP7a passo 2».
- **H-8 · La scheda «password dimenticata» mostra un `docker exec` che gira come root** — minimo; H (CP7a,
  docs-writer), 15/10; il file è di A.
  - `ForgotPasswordCard.svelte:43` mostra `docker compose exec … user reset`.
  - Da CP7a, `./dev.py docker exec` passa per gosu con gli id numerici; il comando nudo gira come root, e i file che
    crea restano di root fino al riavvio.
  - Cura: mostrare il comando con gosu, come `admin/docker_advanced` (sezione «docker exec»), oppure
    `./dev.py docker exec`.

  Dettagli: piano H, §14 «CP7a passo 2».
- ✅ **H-9 · Una seconda chiamata di `configure_logging()` lascia aperti i gestori che toglie** — minimo; H (test-author,
  lotto del log di accesso), 15/10.
  - `logging_config.py` toglie i gestori della radice con `removeHandler` senza `close()`; poi `basicConfig(force=True)`
    non trova più niente da chiudere.
  - Conta solo per il file di log, e in produzione la chiamata è una per processo.
  - Cura: `close()` su ogni gestore tolto, oppure lasciare la pulizia a `basicConfig(force=True)`.

  Dettagli: piano H, §14 «Lotto "credenziali nei log di accesso"».
- **H-10 · `services static-uploads` è dichiarata `write-scoped`, ma svuota la cartella degli upload della corsia** —
  basso; H (test-author, G-10), 15/10. ✅ 15/10 (lotto 36, CP-U1): la fixture `_private_data_dir` punta la cartella dei
  dati su `tmp_path` e non tocca più quella della corsia.
  - Il fixture autouse di `test_static_uploads.py` cancella e ricrea `custom-uploads` della corsia, dove stanno anche gli
    avatar del seed. Un'altra unità che li legge, in parallelo, li perde.
  - Nessun rosso visto finora; c'era già prima di G-10.
  - Cura: una cartella di upload temporanea per ogni test, sostituendo `get_uploads_dir`, oppure dichiarare l'unità
    esclusiva.

  Dettagli: piano H, §14 «Lotto piccolo: G-10 e due note di E».
- **H-11 · Un build locale dell'immagine, dietro un proxy che ri-firma il TLS, si ferma a `pip install`** — basso; H
  (prova Docker di CP7a), 15/10.
  - Il container di build non conosce la CA del proxy: PyPI risponde «self-signed certificate in certificate chain».
  - Le immagini di rilascio si costruiscono in CI: tocca solo chi costruisce in locale, in una rete aziendale o dietro un
    proxy.
  - Cura possibile: un secret di build facoltativo con una CA in più per pip
    (`RUN --mount=type=secret,id=extra_ca,required=false`), documentato in `admin/docker_advanced`.

  Dettagli: piano H, §14 «Validazione unica dei quattro lotti e prova Docker».
- ✅ **H-12 · Un avvio fallito del server condiviso dei test non dice perché** — basso; H (verifica di A5), 15/10. Metà ✅
  15/10 (lotto «billing_url e rotte dei link»): `check_port_in_use` conta solo i listener, come il runner. Resta
  l'output scartato del server condiviso.
  - `scripts/test_runner/_server.py` avvia `dev.py server --test` con stdout e stderr su `DEVNULL`: il runner stampa
    solo «Shared backend exited during startup (code 1)».
  - Le due verifiche della porta sono diverse: il runner guarda solo i listener; `cmd_server` usa `lsof -i :PORT -t`,
    che conta ogni socket sulla porta, anche quelli del server precedente ancora in chiusura.
  - Visto una volta, subito dopo un'altra invocazione sulla stessa corsia; non si è ripetuto. La causa resta
    un'ipotesi.
  - Cura: le ultime righe dell'output del server nel messaggio d'errore, e in `cmd_server` solo i listener
    (`-sTCP:LISTEN`), come fa il runner.

  Dettagli: piano H, §14 «Due aggiornamenti di base … e la verifica di C-96».
  Chiusa il 16/10 (riconciliazione del 17/10): la prima metà il 15/10 (`87f9ed6b5`, solo i listener), il resto nel lotto «H-12, il resto» (`cca1c8b0a`, l'output del server condiviso nel messaggio d'errore).
- **H-13 · `LIBREFOLIO_REGEN_NATIVE_CASH_GUARD` non arriva al test: la corsia la toglie (C-96)** — basso; DV dei colori
  (DV-1), 15/10. ✅ 15/10: chiusa da J in CP-4, con la variabile rinominata `LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD`.
  - Il comando documentato per rigenerare `backend/test_scripts/fixtures/native_cash_guard/eur_only_golden.json`
    (`test_native_cash_guard.py`, la docstring e `_REGEN_COMMAND`) esporta la variabile nella shell.
    `configure_test_runtime()` toglie ogni `LIBREFOLIO_*` che la corsia non tiene (`_test_lane_drops`), quindi pytest non la
    vede e il golden non si rigenera.
  - È l'unica variabile di rigenerazione del repo. Le password del probe AI Export non passano da una corsia: il probe si
    lancia con `pipenv run python`.
  - Cura proposta: rinominarla `LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD`, il prefisso che la corsia già tiene, senza un
    elenco nuovo; aggiornare la docstring e `_REGEN_COMMAND`; un caso di `utils runtime-isolation` che fissi il passaggio di
    `LIBREFOLIO_TEST_REGEN_*`. In alternativa, un elenco esplicito `LIBREFOLIO_REGEN_*` in `TEST_LANE_KEEPS`.

  Dettagli: piano H, §14 «Ingresso dopo A6a».
- ✅ **H-14 · `derive_key_from`: derivare da una chiave d'istanza data, non solo da quella corrente** — medio; X (CP10,
  impostazioni dei plugin), 15/10.
  - Serve al ripristino di B: i segreti dei plugin di un backup sono cifrati con la chiave dell'istanza d'origine, e
    vanno cifrati di nuovo con quella dell'istanza che ripristina.
  - Oggi `instance_key.derive_key(purpose)` deriva solo dalla chiave corrente.
  - Cura: `derive_key_from(key, purpose, length=32)` nello stesso modulo, con lo stesso HKDF; `derive_key` la chiama
    con la chiave corrente. Da accordare con X e B (nome, firma).

  Dettagli: piano H, §14 «Voci di backlog da X CP10».
- ✅ **H-15 · Un controllo d'avvio per una chiave dei segreti dei plugin inutilizzabile** — medio; X (CP10), 15/10.
  - `plugin_secrets_key_status` (X) dice se i segreti salvati si possono ancora decifrare con la chiave corrente, con i
    totali quando non si può, e gira in `to_thread`.
  - Cura: un controllo in `config_audit.py` che lo usa, con un avviso nei log e nella UI dell'admin, nello stile degli
    altri controlli (codice, gravità, chiave i18n).

  Dettagli: piano H, §14 «Voci di backlog da X CP10».
- ✅ **H-16 · `developer/architecture/security.md`: due frasi superate dai segreti dei plugin** — basso; X (CP10), 15/10.
  - L'elenco dei segreti letti con `env_secret()` non ha le variabili dei plugin (`LIBREFOLIO_PLUGIN_*`).
  - La «known limitation» chiama ancora «planned» un controllo della chiave che il `key_id` di X ora rende possibile.

  Dettagli: piano H, §14 «Voci di backlog da X CP10».
- ✅ **H-17 · I default del profilo gestito passano da due meccanismi** — basso; H (CP7b-2), 16/10.
  - `PROFILE_DEFAULTS` (`config/__init__.py`) copre solo i campi di `Settings`, con un test di guardia sulla tabella.
  - Il limite di upload del ripristino di B decide il suo default da sé: `MANAGED_MAX_UPLOAD_MB` (500) in
    `config/backup.py`, perché `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` si legge da `os.environ`.
  - Cura proposta: una sola tabella, o un accessore `profile_default(name, fallback)` che anche i moduli di sezione
    usano, così la guardia copre ogni default del profilo. Da concordare con B.

  Dettagli: piano H, §14 «CP7b-2», passo 2.
  Chiusa il 16/10 (riconciliazione del 17/10): `fb4ecc18c` (`ENVIRONMENT_PROFILE_DEFAULTS` e `profile_default()` per i moduli di sezione, sotto la stessa guardia) e `8f7e086e9` di B (il limite di upload dalla tabella).
- **H-18 · I toast non arrivano ai lettori di schermo** — basso; H (revisione del test-author sulla card della pagina di
  blocco), 16/10.
  - `ToastContainer` (`components/ui/feedback/`) non ha né `aria-live` né `role="status"`: nessun toast dell'app viene
    annunciato. Gli errori che contano hanno di solito anche un `role="alert"` nel punto in cui avvengono, come nella
    card del backup.
  - Cura proposta: una regione `aria-live="polite"` sul contenitore, `assertive` per gli errori, con un caso Vitest. Il
    componente è condiviso: va al proprietario dell'interfaccia comune, con la regola dei colori per i file condivisi.

  Dettagli: piano H, §14 «La card del backup nella pagina di blocco».
- ✅ **H-19 · `POST /users/address-probe` risponde 500 se la chiave d'istanza non si può usare** — basso; H (analisi di H-3),
  16/10.
  - `issue_probe_nonce()` (`services/accounts/address_probe.py`, di A) chiama `derive_key()` senza gestire
    `InstanceKeyError`. Con un file della chiave generato e poi rovinato, il server parte con un errore nel log, e la
    rotta dell'admin dà 500. `verify_probe_nonce()` invece lo tollera e risponde `False`.
  - Cura proposta: 503 con un codice, per esempio `instance_key_unavailable`, e un caso di test. Il codice è di A: da
    girare ad A.

  Dettagli: piano H, §14 «H-3, il resto».
  - Cura fatta il 17/10 da H, con l'OK di scrittura del coordinatore; A rivede (lotto «H-19», piano H §14).
    `issue_address_probe` risponde 503 `INSTANCE_KEY_UNAVAILABLE` per un `InstanceKeyError`, e scrive un warning con
    `admin_id`. Prima era un 500 con il traceback. Due test in processo in `test_address_probe_api.py`.
  Chiusa il 17/10 (riconciliazione del 17/10): `48aa7a3ed` (503 `INSTANCE_KEY_UNAVAILABLE`), doc `139ca6129`.
- **H-20 · L'output del runner rediretto su un file arriva solo alla fine** — molto basso; H (`all-backend` di H-12),
  16/10.
  - Con `> file`, ma anche con `--log-file`, lo stdout del runner è bufferizzato a blocchi, come ogni processo Python
    che scrive su un file. In un `all-backend -q` il file resta fermo per mezz'ora alle righe della build: quelle
    escono da un sottoprocesso. Le righe del runner, come «Starting shared test backend» e «Shared backend ready»,
    arrivano solo all'uscita. Chi segue un run lungo non ne vede l'avanzamento, salvo leggere i log per unità di
    `.testLog`.
  - Cura possibile: `sys.stdout.reconfigure(line_buffering=True)` all'avvio del runner, oppure `PYTHONUNBUFFERED=1`
    nei comandi documentati. Nessuna fretta: il run non ne soffre.

  Dettagli: piano H, §14 «Lotto «H-12, il resto»», passo 13.
- ✅ **H-21 · Un'azione `api` lanciata da sola non rifà gli utenti di fixture** (W-B54) — basso, runner; W (C-97a, slot
  API), 16/10. Assegnata ad H dal coordinatore alle 18:39.
  - Il setup della categoria `api` (`_api_setup` in `scripts/test_runner/_backend_api.py`, `db_populate(force=True)`)
    parte da `run_category_setup("api")` solo con la categoria intera (`api_test`) o nel passaggio consolidato. Per
    un'azione singola, `dispatch_to_category` lo salta e usa il DB della corsia così com'è.
  - Dopo un run che ricrea il DB vuoto (`services`, `db create`), i test che entrano come `e2e_test_admin` o
    `e2e_test_user` cadono con 401: 6 rossi su 118 per W il 16/10, verdetto «ambiente». Oggi si evita a mano,
    lanciando prima `db populate --force`.
  - Cura proposta: prima di un'azione `api` singola, una lettura del DB della corsia controlla che ci siano gli utenti
    di fixture. Se mancano, il runner chiama `run_category_setup("api")`, oppure lo dice prima di partire con il
    comando da lanciare. Un caso di test puro per ciascun ramo: «mancano → seed» e «ci sono → niente».
  - Registro del runner: superficie condivisa, lo scrittore lo assegna il coordinatore.

  Dettagli: piano 04 di W, sezione C-97a; piano H, §14 «Lotto «H-12, il resto»», passo 14.
  Chiusa il 16/10 (riconciliazione del 17/10): `74b420db8`.
- ✅ **H-22 · Due funzioni di `client_address.py` servono solo ai test** — molto basso; H (nota di E dal rapporto
  dead-code, girata dal coordinatore), 16/10.
  - `mask_client_address()` (P17) non ha consumatori, né oggi né in programma: nessun log del codice scrive
    l'indirizzo di un client (verificato su `dev_release2` il 16/10). Cura proposta: toglierla, insieme al blocco (g)
    di `test_client_address.py`, alla sua riga nella docstring del modulo e alle due frasi di
    `developer/architecture/security.md` (la riga della tabella, e «a log holds only the `mask_client_address()`
    form», da sostituire con «a log never holds a client address»). Se un log ne avrà bisogno, torna con il suo
    primo chiamante.
  - `reset_client_address_cache()` è un aggancio per i test dentro il codice di produzione. Cura proposta: i test
    azzerano da soli `_configured_header.cache_clear()` e `_warned`, come fanno già i test di E con
    `delivery._report_invalid.cache_clear()`, e la funzione va via, con la sua frase in `security.md`. L'alternativa
    è `ignore_names` in `pyproject.toml`, con il motivo. La scelta vale anche per `reset_provider_cooldowns` e
    `reset_shutdown_budget_state` di Z, quindi la convenzione la decide il coordinatore.
  - Solo i miei test usano le due funzioni, su dev e sui rami di E e di B: toglierle non rompe nessun merge. In
    `security.md` le due frasi sono mie, scritte in P17.
  - **Non sono codice morto**, e restano:
    - `client_rate_key`: lo adotta E con `2ef892b3f`, non ancora in dev;
    - `profile_default`: H-17, aspetta che B lo usi in `backup_max_upload_mb()`;
    - `derive_key_from`: H-14, aspetta il rekey di X (P24).
  - `dev.py lint --dead-code --scope backend` conta oggi 5 simboli senza riferimenti e 50 usati solo dai test, in
    molte aree: non è un cancello attivo. Quattro sono in `services/files/` e nello scheduler, che H ha spostato nel
    riordino: `get_upload_mime_type` e `get_upload_by_user` (gennaio 2026), `read_supported_preview_type` (giugno),
    `_local_times_to_utc` (giugno). Sono nati prima della 1.3: debito vecchio, fuori da questa voce.

  - **Decisione N58** (coordinatore, 20:35, convenzione da rivedere col developer): via `mask_client_address`;
    nessuna funzione di produzione solo per i test, perché i test azzerano da soli lo stato (`cache_clear()`, o il
    fixture del modulo); `ignore_names` con il motivo solo quando non si può. Cura nel lotto «H-22» (piano H, §14),
    provata il 16/10. Resta il testo del selettore in `_backend_services.py` (MF e A): patch pronta, dal coordinatore.

  Dettagli: piano H, §14 «Revisioni della sera», punto 4, e lotto «H-22».
  Chiusa il 16/10 (riconciliazione del 17/10): `420cc6d13`.
- ✅ **H-23 · Un'azione `services` da sola ricrea il DB della corsia anche per un test `pure`** — basso, runner; H
  (mini-lotto della docstring), 16/10.
  - `_run_exclusive_setups()` (`scripts/test_runner/_cli.py`) gira per ogni invocazione. `_categories_in_scope()`
    restituisce la categoria qualunque sia l'azione, quindi `dev.py test … services client-address`, un test `pure`
    che non apre nessun DB, esegue il setup esclusivo di `services`: «Removing existing test database», poi
    `db create`. Lo hanno fatto tutte e tre le mie corse di H-22 il 16/10, e così la corsia perde gli utenti di
    fixture. Era anche la causa iniziale delle corse perse da W e da J: H-21 ripara il lato `api` (rifà il seed),
    non il lato `services`.
  - Cura proposta: per una singola azione, il setup esclusivo gira solo se l'azione non è `pure` (la classe
    d'isolamento è nel catalogo, `add_test(…, isolation=…)` / `default_isolation`). Oppure con un `setup_needed` di
    `services`, come H-21. Un caso di test puro per ciascun ramo.
  - Registro del runner: superficie condivisa, lo scrittore lo assegna il coordinatore.

  Dettagli: piano H, §14, mini-lotto «La docstring di `instance_block.py`».
  - Cura fatta il 16/10 (lotto «H-23», piano H §14): `_inventory.declared_isolation()` e, in `_run_exclusive_setups()`,
    il salto per un'azione da sola dichiarata `pure`, con una riga. Provata: `services client-address` lascia il DB
    invariato (inode, mtime, dimensione), `services asset-sync-counts` lo ricrea come prima.
  Chiusa il 16/10 (riconciliazione del 17/10): `9541c0667`.
- ✅ **H-24 · Un `.DS_Store` o un test cambiato in `frontend/src` fanno ricostruire il frontend** — basso, runner; E,
  via coordinatore, 16/10.
  - `check_frontend_needs_build()` (`scripts/cli_base.py` ~609) confronta con la build ogni file sotto `frontend/src`
    (`rglob("*")`): un `.DS_Store` del Finder fa sembrare la build più vecchia dei sorgenti, e parte una ricostruzione
    di minuti. E ha dovuto riportare indietro a mano la mtime del file. Lo stesso vale per i 504 file
    `*.test.*`/`*.spec.*` di Vitest, che Vite non impacchetta e nessun codice dell'app importa.
  - Cura proposta: la scansione salta i percorsi con una parte nascosta (il nome inizia con `.`) e i file di test; tiene
    tutto il resto, `prefixes.txt` del catalogo i18n compresi, perché una build creduta fresca a torto costa più di
    una ricostruzione in più. Con un test.
  - Residuo da dire: `_tool_contract_sources()` conta anche le mtime delle cartelle (`backend/app/schemas`,
    `services/tools`, `tool_plugins`) per accorgersi di un file tolto. Un `.DS_Store` creato lì cambia la mtime della
    cartella, e non si può escludere senza perdere quel rilevamento.

  Dettagli: piano H, §14, lotto «H-23», passo 4.
  - Cura fatta il 16/10 (lotto «H-24», piano H §14): `_counts_for_the_build()` in `scripts/cli_base.py` salta i
    percorsi nascosti, i file `.test.`/`.spec.` e le cartelle `__tests__`/`__mocks__` (33 file di supporto ai test, che
    nessun codice dell'app importa). Prova reale: con il solo `.DS_Store` più recente della build, la risposta passa
    da True a False.
  - Residuo chiuso il 17/10 (lotto «Residuo di H-24 e H-28», piano H §14). `cmd_fe_build` registra in
    `frontend/build/.tool-contract-inputs` l'impronta dell'elenco degli ingressi, solo se la build riesce. Il
    controllo la confronta: un file aggiunto, tolto o rinominato fa ricostruire; un `.DS_Store`, un file nascosto o
    `__pycache__/` no. Senza la registrazione vale la regola vecchia, con le mtime delle cartelle.
    - Prova reale sul vero albero dopo una build vera: con un `.DS_Store` in `backend/app/schemas` la build resta
      fresca, dove la regola vecchia l'avrebbe data stale.
  Chiusa il 16/10 (riconciliazione del 17/10): `c53012fcb`.
- ✅ **H-25 · Con `--workers` sopra 1, un'azione da sola fa girare il pre-passaggio parallelo di tutta la categoria** —
  basso, runner; H (analisi di H-23), 16/10.
  - `_run_parallel_prepass()` → `_parallel_for_scope()` → `plan(scope)` pianifica tutta la categoria, non l'azione
    indicata, a differenza dei pre-passaggi consolidati, che girano solo con `action in (None, "all")`. Con le classi
    server (READ, WRITE_SCOPED) chiama anche `run_category_setup(scope)`: `--workers 2 services client-address` gira
    i test parallelizzabili di `services` e ricrea il DB della corsia.
  - Cura proposta: il pre-passaggio parallelo solo per la categoria intera, come i consolidati. Con un test.

  Dettagli: piano H, §14, lotto «H-23», passo 1.
  - Cura fatta il 16-17/10 (lotto «H-25», piano H §14): `_parallel_prepass_applies()` in `_cli.py`, la regola dei
    pre-passaggi consolidati. Niente pre-passaggio parallelo con un'azione singola o con dei nomi di test.
  Chiusa il 17/10 (riconciliazione del 17/10): `4f70eed78`.
- ✅ **H-26 · I nomi di test dopo `all` vengono scartati in silenzio** — basso, runner; H (dal test-author di H-25),
  17/10.
  - Il parser accetta `test_names` dopo qualsiasi azione (`_cli.py` ~331, `nargs="*"`), ma le 16 azioni `all` sono
    tutte registrate con `test_names=False`. `run_test_from_registry()` chiama allora la funzione senza nomi
    (`accepts_test_names`, ~95): `./dev.py test services all foo` fa girare tutta la categoria, senza dirlo.
  - Cura proposta: rifiutare i nomi su un'azione che non li prende, con exit 2 e un messaggio che dice di nominare
    l'azione, oppure applicarli a tutta la categoria (`-k` su ogni unità). La seconda è più utile ma più larga: va
    decisa col coordinatore. Con un test.

  Dettagli: piano H, §14, lotto «H-25», passo 2.
  - Cura fatta il 17/10 (lotto «H-26», piano H §14), con la regola unica scelta dal coordinatore.
    - `_refused_test_names()` in `_cli.py`: i nomi dati a una qualunque delle 36 azioni registrate senza nomi (le 16
      `all`, `db create`/`populate`, 18 unità Vitest) danno exit 2 e un messaggio: «name the action» dopo `all`, «takes
      no test names» dopo le altre.
    - Il controllo avviene prima di ogni effetto collaterale, in `_dispatch_test_command` e in `main()`, `--list`
      compreso.
    - Prova reale: 6 comandi rifiutati, nulla cambiato.
  Chiusa il 17/10 (riconciliazione del 17/10): `b34f5e990`, doc `30c5afa02`.
- ✅ **H-27 · `profile_default` non controlla il tipo del valore del profilo** — basso, configurazione; E (R13-SEC3), via
  coordinatore, 17/10.
  - `profile_default(name, fallback)` (`backend/app/config/__init__.py` ~579) restituisce con un `cast` il valore di
    `ENVIRONMENT_PROFILE_DEFAULTS[<profilo>]`, senza controllarne il tipo. Oggi l'unica voce è `managed`:
    `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` = 500, letta da `backup_max_upload_mb()` (`config/backup.py` ~78) con ripiego `0`,
    che vuol dire «nessun limite».
  - Se la voce sparisce, il profilo gestito si comporta come il self-hosted e non mette limiti alla dimensione di un
    restore, senza avviso. Se vale `None`, quel valore passa e viene trattato anche lui come «nessun limite».
  - Cura proposta: il tipo del valore deve essere quello del ripiego (`bool` a parte), altrimenti un errore chiaro
    all'avvio; più un test che fissa le voci di `managed` insieme ai loro lettori. Dopo il lotto H-26 / residuo di H-24
    / H-28.

  Dettagli: piano H, §14, «Residuo di H-24».
  - Cura fatta il 17/10 (lotto «H-27», piano H §14).
    - `profile_default()` accetta solo un valore del tipo esatto del ripiego; un altro tipo alza
      `ProfileDefaultError` (un `TypeError`) e il lettore si ferma: un `None` non diventa più «nessun limite».
    - Una guardia statica in `services profile-defaults` confronta il ripiego letterale di ogni chiamata con le voci
      dei profili.
    - Nessun controllo all'avvio: il tipo atteso lo conosce solo il lettore.
    - Resta a B, se lo vuole: con una tabella sbagliata le due rotte di `restore.py` rispondono 500, perché catturano
      solo `BackupConfigError`; per il suo 503 basta catturare anche `ProfileDefaultError`.
  Chiusa il 17/10 (riconciliazione del 17/10): `51dd43926`.
- ✅ **H-28 · Il catch-all della SPA serve i file nascosti di `frontend/build/`** — basso, sicurezza (informazione); H
  (analisi del residuo di H-24), 17/10.
  - `frontend_catchall()` (`backend/app/services/platform/static_site.py` ~130) serve qualunque file che
    `confined_path` trova dentro la build, dotfile compresi. Rispondono `GET /.build-debug` (dice se la build è di
    debug) e `GET /.build-version` (la versione, già pubblica), anche dall'immagine. Risponde anche
    `/fonts/noto-color-emoji/.cache_manifest.json`, che l'app non chiede mai: lo legge solo `update_js_cache.py`, dal
    disco.
  - Cura, nel lotto H-26 / residuo di H-24: un file con una parte nascosta nel percorso risolto dentro la build va al
    fallback della SPA, come un percorso fuori dalla build. `/assets/../favicon.png` resta servito. Con un test.

  Dettagli: piano H, §14, «Residuo di H-24».
  - Cura fatta il 17/10: `_hidden_in_build()` in `static_site.py`.
    - Prova reale su un server della corsia: i quattro percorsi nascosti danno `200.html`; `robots.txt` e
      `manifest.json` restano serviti.
  Chiusa il 17/10 (riconciliazione del 17/10): `36dbc5174`, riga del CHANGELOG `5beecac3d`.
- ✅ **H-29 · Il mount di `/_app` e `/mkdocs` servono ancora i file nascosti** — basso, sicurezza (informazione); H
  (residuo di H-28), 17/10.
  - H-28 ha chiuso il catch-all della SPA. `ImmutableStaticFiles` (`/_app`) e `mkdocs_static` (`/mkdocs`) non filtrano
    i nomi che iniziano con `.`.
  - Oggi non ce ne sono: SvelteKit e MkDocs non ne producono, e l'immagine non ne contiene. Su un Mac di sviluppo, però,
    un `.DS_Store` del Finder dentro `frontend/build/_app/` o `mkdocs_src/site/` sarebbe servito.
  - Cura proposta: la stessa regola di `_hidden_in_build()` nei due percorsi, con un test ciascuno.

  Dettagli: piano H, §14, «Residuo di H-24 e H-28».
  - Cura fatta il 17/10 (lotto «H-29 e H-30», piano H §14).
    - `ImmutableStaticFiles.get_response()` dà a un nome nascosto il 404 di un file mancante;
    - `mkdocs_static()` gli dà il 404 della documentazione, attraverso `_hidden_below()`, che usa anche il catch-all.
  Chiusa il 17/10 (riconciliazione del 17/10): `44acd2317`.
- ✅ **H-30 · `python -m scripts.test_runner --log-file` non fotografa il DB se il corpo alza un'eccezione** — basso,
  runner; H (test-author di H-26), 17/10.
  - Nel ramo `--log-file` di `main()` (`scripts/test_runner/_cli.py`), `_snapshot_log_dir_db()` segue
    `_timed_run(...)` senza `try/finally`, a differenza di `_dispatch_test_command` (il percorso di `dev.py test`).
  - Effetto: un crash del corpo lascia i log senza la copia del DB. Riguarda solo l'ingresso `python -m`.
  - Cura proposta: lo stesso `try/finally`, con un test.

  Dettagli: piano H, §14, «Residuo di H-24 e H-28».
  - Cura fatta il 17/10 (lotto «H-29 e H-30»): il `try/finally` dentro il `with` di `tee_output`, come in
    `_dispatch_test_command`.
  Chiusa il 17/10 (riconciliazione del 17/10): `97b746696`.
- **H-31 · `blocked` nel pubblico `/system/instance`** — basso, facoltativo; E (E-11) e coordinatore, 17/10.
  - Le pagine anonime dei link (A7b) deducono il blocco dal 401 di una rotta pubblica fuori lista. Un booleano
    `blocked` in `GET /system/instance`, che è permesso a istanza bloccata, lo direbbe senza deduzioni e senza
    dettagli: la data di cancellazione resta dietro login in `/system/block`.
  - Non serve per E-11: E lo risolve nei suoi file, con il 401 `INVALID_CREDENTIALS` della sola `resend`.
  - Scelto (a) invece di (b), un codice nel 401 anonimo del blocco: con (b) una rotta protetta non risponderebbe più
    allo stesso modo con o senza blocco.

  Dettagli: piano H, §14, lotto «H-29 e H-30».
- ✅ **H-32 · Un `float` nel corpo di una richiesta accetta `1E+400`** — basso, API; A (A-35), via coordinatore, 17/10.
  - Pydantic accetta `inf` e `nan` di default (`allow_inf_nan=True`): la richiesta riceve 200. Se una rotta
    restituisce il valore così com'è, il renderer di Starlette (`allow_nan=False`) fallisce con un 500.
  - Direzione: un inventario dei campi `float` degli schemi dei corpi; poi forse `allow_inf_nan=False` nel modello
    base, o `Decimal` dove sono soldi.

  Dettagli: piano H, §14, lotto «H-29 e H-30».
  - Cura fatta il 17/10 (lotto «H-32», piano H §14).
    - Inventario sull'app vera: 6 `float` raggiungibili da una richiesta. 5 erano già finiti (i segnali,
      `FiniteFloat`); il sesto, `PluginSettingPlainValue` di X, ora ha `AllowInfNan(False)`.
    - Niente nella base `StrictModel`, che regge anche le risposte e i modelli interni.
    - Guardia `services request-float-inputs`: percorre tutte le rotte con barriere.
    - Il 500 di A vale solo per le rotte senza `response_model`: con FastAPI 0.141 quelle con `response_model`
      rispondono `null`.
    - Trovato strada facendo: con il gestore standard dei 422, un valore non finito su un campo già finito dà un 500,
      perché l'errore ripete l'`input`. Lo cura il gestore globale di A7b-2, che toglie l'`input`.
  Chiusa il 17/10 (riconciliazione del 17/10): `80676ed09`.
- ✅ **H-33 · Senza un gestore di `ResponseValidationError`, il log del server contiene la risposta** — basso,
  sicurezza (log); E (R13-SEC4), via coordinatore, 17/10.
  - Quando una risposta non passa il suo `response_model`, FastAPI alza `ResponseValidationError`. Nessuno la gestisce,
    quindi il traceback che uvicorn scrive nel log porta l'`input`: la risposta stessa, con i dati che conteneva.
  - Cura proposta: un gestore, accanto a quello globale dei 422 di A (A-35, lotto A7b-2), che registra la rotta e gli
    errori senza il valore e risponde 500.

  Dettagli: piano H, §14, lotto «H-29 e H-30».
  - Cura fatta il 17/10 (lotto «H-33», piano H §14).
    - `backend/app/api/response_validation.py`, installato da `main.py` subito dopo il gestore dei 422 di A.
    - Un solo evento di log: metodo, percorso modello completo (`exc.endpoint_path`), endpoint, e per ogni errore
      `type` e `loc`. Mai l'`input`, il `msg` o il traceback.
    - La risposta è lo stesso 500 in testo semplice.
    - Resto latente: un endpoint generatore tipizzato (streaming di FastAPI) fallirebbe la convalida a risposta già
      iniziata, e Starlette scriverebbe ancora `str(exc)` nel traceback. Oggi LibreFolio non ne ha.
  Chiusa il 17/10 (riconciliazione del 17/10): `5a0060816`.
- ✅ **H-34 · Il JSON libero di una richiesta accetta `Infinity` e `NaN` al suo interno** — basso, API; H (residuo di
  H-32, dal test-author e dal docs-writer), 17/10.
  - La regola di H-32 riguarda i campi `float`. I campi `Any` o `JsonValue` raggiungibili da una richiesta accettano
    numeri non finiti al loro interno:
    - `FAProviderAssignmentItem.provider_params` e `FAProviderProbeRequest.provider_params` (`dict[str, Any]`, X:
      `POST /assets/provider` e `/assets/provider/probe`);
    - `RiskAnalyticRequest.parameters` (`JsonValue`, J: `POST /risk/query`), senza validatore.
    - `ToolComputeItem.parameters` sta in un modello con `allow_inf_nan=False`: da verificare che valga anche dentro
      `JsonValue`.
    - `SignalRequest.params` è già protetto (`ensure_json_safe`).
  - Cura proposta, a ciascun proprietario: un validatore come `ensure_json_safe` sui campi liberi; la guardia di H-32
    potrebbe poi elencarli.

  Dettagli: piano H, §14, lotto «H-32».
  - Cura fatta il 17/10 (lotto «H-34», piano H §14), con l'OK di scrittura del coordinatore.
    - `FAProviderConfigBase.provider_params` (X) e `RiskAnalyticRequest.parameters` (J) hanno un
      `field_validator(mode="before")` con `ensure_json_safe`. X e J rivedono.
    - `ToolComputeItem.parameters` era già protetto: `JsonValue` rispetta l'`allow_inf_nan=False` del suo modello.
    - La guardia di H-32 elenca ora le 5 posizioni libere, ognuna con la sua sonda. Il paragrafo di
      `security.md#request-numbers` arriva con i documenti di H-39.
  Chiusa il 17/10 (riconciliazione del 17/10): `d5d080a84`, entrato in dev `75bfac237`.
- ✅ **H-35 · Dopo A8a: la docstring di `log_configuration_audit()` e la pulizia di `test_config_audit.py`** — minimo; H
  (review di A8a), via coordinatore, 17/10.
  - La docstring non nomina il `ValueError` di `LIBREFOLIO_LOGIN_LIMIT` né l'`AdminBootstrapConfigError` di F02.
  - `test_config_audit.py`: togliere i 9 segni «updated in A8a (accounts check, H reviews)» e l'impalcatura «red until
    A8a» (`_accounts_checks()` con `importlib`). `ACCOUNTS_CONFIG_CHECKS` e `check_login_limit` vanno importati in cima,
    e l'id di A va in `CHECK_IDS`.
  - In più, dal test-author di H-36: `_configure` deve svuotare le note di `client_address._untrusted_forwarding`. Così
    una nota lasciata da un altro file nello stesso processo non rompe i test che vogliono ogni controllo `ok`.
  - Si fa dopo l'ingresso di A8a e l'avanzamento del ramo di H.
  - Cura fatta il 17/10, dopo A8a e B-9 (lotto «H-35», piano H §14):
    - le due docstring di `config_audit.py`;
    - in `test_config_audit.py`, via l'impalcatura di A8a e di B-9, e `CHECK_IDS` nell'ordine di `CONFIG_CHECKS`;
    - `_configure` svuota le note di H-36, con un test che prima era rosso.

  Dettagli: piano H, §14, «Review di A8a» e lotti «H-36» e «H-35».
  Chiusa il 17/10 (riconciliazione del 17/10): `0836e834b`, entrato in dev `d28a6d7df`.
- ✅ **H-36 · Dietro un proxy che uvicorn non considera fidato, i limiti per indirizzo contano tutti i visitatori
  insieme** — medio, sicurezza; E (R13-SEC6), via coordinatore, 17/10. Decisione notturna N70.
  - L'immagine Docker avvia uvicorn con i suoi default, che seguono `X-Forwarded-For` solo da `127.0.0.1`. Un proxy
    davanti al container si collega dalla rete Docker (per esempio `172.18.0.2`), e ogni visitatore prende il suo
    indirizzo. Il limite per indirizzo di A8a (50 tentativi) bloccherebbe allora l'accesso di tutti.
  - Cura fatta il 17/10 (lotto «H-36», piano H §14):
    - in `client_address.py`, `forwarded_by_untrusted_proxy(request)`: vero per un header di inoltro (`X-Forwarded-For`,
      `Forwarded`, `X-Real-IP`) da un peer locale secondo `classify_ip`, quando né `LIBREFOLIO_CLIENT_IP_HEADER` né
      uvicorn hanno sostituito l'indirizzo;
    - `rate_limit_address(request)`: `None` in quel caso, cioè nessun conteggio per indirizzo, altrimenti
      `client_address`;
    - le note tengono solo i nomi degli header (N58); la prima di ogni classe va nel log, una volta per processo;
    - il controllo `platform.client_address`, con le tre chiavi `instance.checks.clientAddress.*`.
  - Restano ad A e a E: passare i punti di chiamata a `rate_limit_address` (A in A8a, E in E-13) e aggiornare le loro
    frasi nei documenti, in «Callers.» di `security.md`, `connection_checks`, `configuration` ed `email`.

  Dettagli: piano H, §14, lotto «H-36».
  Chiusa il 17/10 (riconciliazione del 17/10): `36cc0119d`, doc `b3e9f9c8a`.
- ✅ **H-37 · Se manca una voce del profilo `managed`, `profile_default` dà il fallback del codice, cioè nessun limite** —
  basso, sicurezza; E (R13-SEC7), via coordinatore, 17/10.
  - `profile_default` (`config/__init__.py`, ~584) usa il fallback del codice quando il profilo `managed` non elenca la
    variabile, e per un limite il fallback 0 vuol dire «nessun limite».
  - Deve fallire chiuso: rifiutare l'avvio, oppure un default sicuro dichiarato per ogni campo. Oggi il profilo
    `managed` ha una sola voce, `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`: 500.
  - Prima i rossi; E rivede. Si fa dopo H-36.
  - Cura fatta il 17/10 (lotto «H-37», piano H §14). La scelta è il fallimento chiuso alla chiamata, senza rifiuto
    all'avvio, come per H-27.
    - Sotto ogni profilo tranne `selfhosted`, una variabile che il profilo non elenca solleva `ProfileDefaultError`.
    - Le rotte di B danno 503 e `upload_limit_mb` null.
    - La guardia (h) controlla anche la direzione nuova, con il suo autotest.
  - Resta a E da decidere: `PROFILE_DEFAULTS` (i campi di `Settings`) ha la stessa forma. Senza la voce managed di
    `LIBREFOLIO_FRAME_PROTECTION` si torna in silenzio a spento, e oggi lo ferma solo il test (a).

  Dettagli: piano H, §14, lotto «H-37».
  Chiusa il 17/10 (riconciliazione del 17/10): `373cb53e6`, entrato in dev `b37e926af`.
- **H-38 · Tailscale Serve davanti al container, e Docker Desktop: cosa mettere in `FORWARDED_ALLOW_IPS`** — basso,
  documentazione; H (dal docs-writer di H-36), 17/10.
  - Tailscale Serve sull'host inoltra a `127.0.0.1:6040`. Con Docker su Linux il container vede probabilmente il gateway
    della rete Docker (il proxy di Docker), quindi H-36 avvisa se Serve manda un header di inoltro; se non ne manda,
    nessuno può accorgersene.
  - Elencare il gateway sembra sicuro su Linux, dove gli altri visitatori arrivano col loro indirizzo. Non lo è con
    Docker Desktop, dove tutti arrivano dal gateway.
  - Da provare su un Docker vero (il demone oggi è spento, come per CP7a), poi una frase in `service_exposure` e in
    `docker_advanced`.

  Dettagli: piano H, §14, lotto «H-36».
- ✅ **H-39 · Il profilo managed senza protezione dai frame non si vede** — basso, sicurezza; E (review di H-37, decisione
  su `PROFILE_DEFAULTS`), via coordinatore, 17/10.
  - Una voce managed persa in `PROFILE_DEFAULTS`, o un pannello che spegne `LIBREFOLIO_FRAME_PROTECTION`, riporta
    in silenzio al default del codice. E non vuole una chiusura a runtime, ma un controllo che si veda.
  - Cosa serve:
    - un controllo `platform.frame_protection`: spento in managed è un warning, all'avvio e nella scheda Sicurezza;
    - `platform.csp_report_only`: spento in managed è un info;
    - il self-hosted è sempre ok.
    - Le aspettative di managed stanno scritte nel controllo, non lette dalla tabella.
  - In più, una regola di review: un campo `Settings` di sicurezza nuovo dichiara il suo valore managed nello stesso
    lotto.
  - Stato al 17/10: la regola è scritta in `.github/instructions/backend.instructions.md`, e la riga accanto a C-99 la
    scrive il coordinatore. I due controlli, i test e le chiavi i18n aspettano l'ingresso di B-9, che scrive negli
    stessi file (`config_audit.py`, `test_config_audit.py`). La cura in prova è pronta in `files/h39/` della sessione H.
  - Cura fatta il 17/10, dopo B-9 (lotto «H-39», piano H §14).
    - `check_frame_protection` (warning) e `check_csp_report_only` (info) in `config_audit.py`, dopo
      `check_client_address`.
    - Sei chiavi `instance.checks.*` in 4 lingue, e i documenti: `security.md`, `settings.md`, `configuration`,
      `hosting_providers`.
    - Resta: un controllo a richiesta letto dopo una modifica di `.env` senza riavvio può mostrare il valore nuovo,
      mentre il middleware porta ancora quello vecchio. I documenti dicono già di riavviare.

  Dettagli: piano H, §14, lotti «Z-24» (la nota di H-39) e «H-39».
  Chiusa il 17/10 (riconciliazione del 17/10): `52adadc05`, entrato in dev `0403b5eb7`.
- **H-40 · IPv6 su Docker Engine: il visitatore arriva dal gateway della rete** — basso, documentazione; E, via
  coordinatore, 17/10.
  - `connection_checks.en.md:328-329` dice che Docker Engine su Linux tiene l'indirizzo del visitatore. Vale per IPv4
    (DNAT). Un visitatore IPv6 verso un container senza IPv6 passa da `docker-proxy` e arriva dal gateway della rete,
    senza header di inoltro. N70 non può vederlo, e tutti i visitatori IPv6 condividono un solo conteggio per
    indirizzo (istanza esposta direttamente).
  - Una frase nei documenti, da verificare su un host Linux, come H-38. Va con i documenti di H-39.
  - Frase scritta il 17/10 (lotto «H-39», piano H §14), come cautela, in `connection_checks#limits`; più due clausole,
    in `connection_checks#client-address` e in «Why only a local peer» di `security.md`. Un visitatore IPv6 che passa
    da `docker-proxy` può anche aggiungere un header di inoltro e lasciare i limiti per indirizzo, come con Docker
    Desktop. Resta da verificare su un host Linux con Docker, insieme a H-38.
- ✅ **H-41 · I `resolved_fields` di una promozione non sono validati** — medio, robustezza; W (trovato nel lotto H-34),
  17/10.
  - `TXPromoteBatchItem.resolved_fields: Dict[str, Any]` (`POST /transactions/validate` e `/commit`) è applicato così
    com'è da `_apply_promote_resolved_fields` (`services/transactions/batch_creates.py`).
  - `description` è assegnata senza controllare il tipo né la lunghezza (il create la limita a 500). Un numero,
    `Infinity` compreso, finirebbe nella colonna `Text` e ogni lettura di quella transazione darebbe 500, perché il
    modello di lettura vuole una stringa.
  - `cost_basis_override` passa da `Currency.model_validate`, il cui errore probabilmente esce come 500. `date` passa
    da `parse_ISO_date`.
  - Cura possibile, a W: un modello tipato (`description: str` con la stessa lunghezza, `tags`, `date`,
    `cost_basis_override: Currency`, `extra="forbid"`). È da W anche decidere se le liste di `dict` di
    `TXMixedBatch` (righe validate dopo, una per una) entrano nella guardia delle posizioni libere.

  Dettagli: piano H, §14, lotto «H-34».
  Chiusa il 17/10 (riconciliazione del 17/10): `c0b67f4c8` (lotto R13-SEC7-3, «type promote fields»), con i rossi `61acbc16b`.
- ✅ **H-42 · Tre direttive della CSP imposte sulle pagine accanto a `frame-ancestors`** — basso, sicurezza; E (dopo
  H-39), via coordinatore, 17/10.
  - Con la protezione dai frame accesa (il default di managed), le risposte HTML hanno `frame-ancestors 'self';
    object-src 'none'; base-uri 'self'; form-action 'self'`. Le altre tengono solo `frame-ancestors 'self'`: Chromium
    tratta il visore PDF integrato come un plugin, e `object-src 'none'` sulla risposta di un PDF lo fermerebbe.
  - E2E con `page.route` come guardia permanente, perché una corsia non può accendere la protezione (vedi H-43).
  - Cura fatta il 17/10 da H (lotto «H-42», piano H §14); E rivede. A protezione accesa, le risposte `text/html` hanno
    `PAGE_POLICY`, le altre solo `frame-ancestors 'self'`. Test backend `services managed-headers` (256). Guardia nel
    browser: `front-utility page-policy`, verde a 1 e a 4 worker, con i tre controlli positivi e documenti, PDF e
    Dashboard senza violazioni.
  - Nota per E: in Chromium 149, un `<object>` di un'immagine inserito nello stesso task di un `form.submit()` verso
    un'altra origine parte come immagine, senza il controllo `object-src`. Plugin e documenti restano bloccati. Per
    questo il controllo dello spec è un `<object>` `application/pdf`.

  Dettagli: piano H, §14, lotto «H-42».
  Chiusa il 17/10 (riconciliazione del 17/10): `7903bbe72`, `84c71a0c7`, `fb8661dd2`, entrati in dev `3b0af4094`.
- ✅ **H-43 · Una corsia di test con il profilo managed, per gli E2E del cloud** — basso, runner; H (analisi di H-42),
  17/10.
  - `configure_test_runtime` toglie a ogni corsia ogni `LIBREFOLIO_*` dello sviluppatore, e un run ha un solo backend
    condiviso: oggi nessun E2E può girare con il profilo managed, o con la protezione dai frame accesa, e un header
    vero.
  - Strada possibile: un'opzione del runner, per esempio `--lane-setting NOME=VALORE` con una lista di nomi ammessi,
    applicata dopo le rimozioni, con i suoi test e documenti. Così gli E2E esistenti girerebbero sul profilo del cloud.

  ✅ **Fase 1 fatta il 17/10** (checkpoint delle 19:20; decisioni del coordinatore D1–D4).
  - `--lane-setting NOME=VALORE`, su `dev.py test` e `dev.py server --test`, per i tre nomi di `TEST_LANE_SETTABLE`
    (`LIBREFOLIO_PROFILE`, `LIBREFOLIO_FRAME_PROTECTION`, `LIBREFOLIO_CSP_REPORT_ONLY`). Arriva a ogni processo della
    corsia con `LIBREFOLIO_TEST_LANE_SETTINGS`, e viene rifiutata quando sta in `.env`, anche sotto `pipenv run`.
  - Il raccoglitore delle violazioni della CSP, sempre acceso nella fixture condivisa, con l'interruttore
    `E2E_CSP_COLLECTOR=0` e la baseline `e2e/csp-baseline.json` (quattro voci con proprietario; una risorsa si nomina
    per `blockedURI` o per `blockedPath`).
  - Le azioni `front-utility csp-collector` (in `all`) e `front-utility cloud-smoke`: 13 spec su una corsia managed,
    `named_only`, quindi fuori da ogni `all` anche nel passo consolidato.
  - Prove: il cloud smoke è verde (225 + 1 skipped); il campione self-hosted è verde col raccoglitore acceso
    (`front-broker all` 57 E2E, `front-ai-export all` 18 E2E).
  - **Fase 2**: una volta sola, nel cancello della release candidate, nella corsia del coordinatore
    (`all-frontend --lane-setting LIBREFOLIO_PROFILE=managed`). Prima va fatta la riga di A su LGM-E-01 e LGM-E-03 di
    `legal-and-managed.spec.ts`: provano la risposta della corsia con una corsia self-hosted come precondizione, quindi
    su una managed falliscono per costruzione.
  - Residui: H-52 (gli hash, D4, con la restrizione della voce `eval`), H-53 (la sonda dell'indirizzo con una
    `connect-src` applicata). `named_only` lo legge solo il passo consolidato del frontend: un'azione del backend che ne
    avesse bisogno vorrebbe lo stesso filtro in `_consolidate_backend.py` e nel passo parallelo.

  Dettagli: piano H, §14, lotto «H-42», analisi punto 4.
  Chiusa il 17/10 (riconciliazione del 19/10): `cd04b17b0`, `11d0bce48`, entrati in dev `d3212e9f2`; `3b01fff93`, in dev
  `a6adb0066`. La fase 2 (una volta, nel cancello della release candidate) resta al coordinatore.
- **H-44 · Il ripiego dell'anteprima PDF probabilmente scarica il file invece di mostrarlo** — basso, file; trovato nel
  lotto H-42 (dal docs-writer), via coordinatore, 17/10. Il proprietario lo assegna il coordinatore al prossimo treno.
  - Quando il visore EmbedPDF fallisce, `FilePreviewModal.svelte` mostra il PDF in un `<iframe>` su
    `/api/v1/uploads/file/{id}`, il `source_url` di `api/v1/uploads.py`.
  - `serve_file` passa sempre `filename` a `FileResponse`, quindi la risposta è `Content-Disposition: attachment`, e un
    iframe con un allegato fa partire uno scaricamento.
  - È precedente a H-19 e H-42, e non è verificato in un browser.
  - Solo la pagina File. Lo stesso componente, nei dialoghi d'import dei broker, riceve come `source_url`
    `/api/v1/brokers/import/files/{id}/download?download=false` (`api/v1/brokers.py:750`), servito inline: lì il
    ripiego mostra il PDF. Il confronto fra le due rotte indica la cura.
  - Legame con H-42: la CSP più stretta va solo sulle risposte `text/html` anche per questo caso. Un PDF mostrato inline
    non deve ricevere `object-src 'none'`, che può fermare il visore integrato di Chromium.

  Dettagli: piano H, §14, lotto «H-42».
- ✅ **H-45 · `image/svg+xml` e `application/xhtml+xml` fuori dalla politica delle pagine** — basso, sicurezza; seguito di
  H-42 per E, via coordinatore, 17/10. E lo giudica nella revisione di H-42.
  - Con la protezione dai frame accesa, `PAGE_POLICY` va solo sulle risposte `text/html`. Un SVG o un XHTML, documenti
    anche loro quando si aprono direttamente, tengono il solo `frame-ancestors 'self'`.
  - Oggi la build, i documenti e i plugin non hanno SVG (verificato il 17/10: lo dicevo a torto). Un SVG dell'utente
    arriva come `attachment`, dagli upload e dai broker (`INLINE_SAFE_MEDIA_TYPES` di `api/v1/brokers.py` non ha
    `image/svg+xml`).
  - Cura fatta il 17/10 da H (lotto «H-45», piano H §14), con la specifica di E; E rivede.
    - Con la protezione dai frame accesa, `PAGE_POLICY` va su ogni documento: `text/html`, `application/xhtml+xml`,
      `image/svg+xml`, `application/xml`, `text/xml` e i tipi `+xml`. I PDF restano fuori, e il report-only resta su
      `text/html` esatto.
    - Un 304 non riceve nessuna CSP. Una sonda in Chromium 149 mostra che la CSP di un 304 sostituisce quella della
      pagina in cache; oggi è latente, perché solo `StaticFiles` (`/_app`) risponde 304 e non ha documenti.
    - Test: `services managed-headers`, 355.

  Dettagli: piano H, §14, lotti «H-42», passo 7, e «H-45».
  Chiusa il 17/10 (riconciliazione del 17/10): `3553c7870`, `77e9611e0`, entrati in dev `5ee3f6fef`.
- ✅ **H-46 · `LIBREFOLIO_TEST_MODE` acceso fuori da una corsia di test non si vede** — basso, sicurezza; E (review di
  X-R44), via coordinatore, 17/10.
  - `dev.py server` lo spegne sempre. Un server avviato in altro modo (`uvicorn` a mano, un'unità di servizio) lo
    prende dal suo ambiente, e nessun controllo lo dice. Effetti:
    - `mockprov` e `mockfx` (X-R44) tornano visibili;
    - i dati vanno nella cartella di test;
    - `.env` non si legge più.
  - Nell'immagine così com'è il server invece si ferma all'import su un `PermissionError`: l'utente del server non può
    creare la cartella di test. È dedotto dai file e riprodotto fuori da un container; la prova in un container va con
    CP7a.
  - Cura fatta il 17/10 da H (lotto «H-46», piano H §14); E rivede. Il controllo `platform.test_mode` è `error` quando
    test mode è acceso senza `LIBREFOLIO_TEST_LANE_ID` (che ogni corsia ha e che `dev.py server` toglie), nel log
    d'avvio e nella scheda Sicurezza. Nel profilo managed **ferma l'avvio**, come un `JWT_SECRET` corto (decisione del
    coordinatore, 17/10). Test: `services config-audit`, 204.
  - Residuo per CP7a: provare in un container che l'immagine si fermi all'import, e valutare un messaggio chiaro al
    posto del traceback di `PermissionError`.

  Dettagli: piano H, §14, lotto «H-46».
  Chiusa il 17/10 (riconciliazione del 17/10): `3cce3a2b8`, `9292ef57b`, entrati in dev `b7dcd3a25`.
- **H-47 · `read_secret_file`: un'opzione per leggere un segreto da root, solo da un file regolare e senza link sotto una
  radice data** — basso, sicurezza; B-38 della review BZ di B, via coordinatore, 17/10. Il disegno è rivisto il 17/10,
  dopo aver riletto B-38 entrato. Dopo la 1.3.
  - La CLI del backup gira da root e legge la password e la chiave d'istanza vecchia (`--password-file`,
    `--instance-key-file`, B-18) con `read_secret_file` (`config/__init__.py`). Quella apre per percorso, segue i link e
    aprirebbe una FIFO. Il file può stare in una cartella che l'utente del server controlla: `backups/`, come
    suggeriva la guida di B-18.
  - **Cosa ha fatto B-38** (entrato, `1ed071c2f`; `_secret_path()` in `scripts/backup_cli.py`; `security.md`, «Secret
    files read as root»), da root:
    - rifiuta un percorso che passa per un link in un componente qualunque dalla cartella dei dati in giù
      (`_link_inside()`, un `os.lstat` per componente);
    - poi apre con `O_RDONLY|O_NONBLOCK` **seguendo i link** e chiede a `fstat` un file regolare: una FIFO, una
      cartella o un dispositivo sono rifiutati subito, mai attesi;
    - chiude, e lascia leggere a `read_secret_file`.
    Fuori dalla cartella dei dati i link si seguono di proposito: i segreti di Kubernetes sono link
    (`/etc/secret/pw` → `..data/pw`).
  - **Il residuo**: tre passi separati, cioè il giro di `lstat`, l'apertura del controllo e quella di
    `read_secret_file`. Fra un passo e l'altro il percorso può cambiare (lo dicono la docstring di `_secret_path()` e
    `security.md`).
  - **Il disegno**: `read_secret_file(path, label, *, regular_only=False, no_links_under=None)`. Mai un `O_NOFOLLOW`
    secco, che romperebbe Kubernetes.
    - `regular_only`: una sola apertura `O_RDONLY|O_NONBLOCK`, `fstat` sul descrittore (file regolare, altrimenti
      `SecretFileError` «is not a regular file», con il nome e il percorso come oggi) e la lettura **dallo stesso
      descrittore**. Un file scambiato dopo il controllo non si legge.
    - `no_links_under=<radice>`: il tratto del percorso sotto la radice si apre un componente alla volta, con
      `os.open(nome, O_NOFOLLOW…, dir_fd=…)` sul descrittore del componente precedente. Un link lì dà `SecretFileError`,
      e la sua destinazione non si legge. I link fuori dalla radice restano seguiti.
    - Così controllo e lettura passano per una sola catena di descrittori, e le corse spariscono. La CLI passa
      all'opzione e toglie la sua copia: `_link_inside()` e la prima apertura.
  - **Default invariati**: i lettori dell'avvio (`env_secret`, la chiave generata) restano come sono. I segreti di
    Docker sono file regolari montati.
  - **Costo**: piccolo-medio, perché c'è la discesa con `dir_fd` su macOS e Linux. Più i test:
    - un link dentro e uno fuori dalla radice;
    - una FIFO, che non deve bloccare;
    - una cartella, un dispositivo, un file regolare;
    - uno scambio fra controllo e lettura;
    - l'opzione spenta, che si comporta come oggi.

  Dettagli: questa riga; la guardia di B in B-38.
  ✅ **Il disegno è entrato** il 17/10 (riconciliazione del 19/10): `cd0e21548`, in dev `13b6cfde1`. Il codice
  (`regular_only`, `no_links_under`) resta aperto, dopo la 1.3.
- **H-48 · `env_url` toglie la barra finale anche ai link di una pagina** — basso; H (review di A9), via coordinatore,
  17/10. Da fare con H-47 (stesso file, `config/__init__.py`), altrimenti dopo la 1.3.
  - `env_url` toglie una barra finale perché a `LIBREFOLIO_PUBLIC_URL` si attacca un percorso. Gli altri suoi
    lettori sono link a una pagina, dove `…/terms/` diventa `…/terms`:
    - `LIBREFOLIO_SUPPORT_URL` (H, `config/platform.py`);
    - `LIBREFOLIO_TOS_URL` e `LIBREFOLIO_PRIVACY_URL` (A9, stesso file);
    - `LIBREFOLIO_BILLING_URL` (A, `config/accounts.py`).
    Quasi ovunque il server risponde con un redirect, quindi il danno è raro.
  - Cura: i link tengono il percorso com'è scritto, per esempio con un parametro di `env_url` o con una funzione
    sorella; `PUBLIC_URL` tiene il taglio. Gli stessi controlli (`http(s)`, nome dell'host, niente credenziali).
  - **Rimandata a dopo la 1.3** (coordinatore, 17/10). I rossi erano scritti, ma la cura toccava più di quanto stimato.
    Il lavoro in corso (i test, la doc, `apply_h48.py`) è conservato fuori dal repo, nella cartella della sessione H
    (`files/h48-wip/`); i file del repo sono tornati come prima.
  - I test da cambiare (13), con l'OK di A sui suoi:
    - miei:
      - `test_config_package.py`: i sei test di `env_url` estesi a `env_link`; due test nuovi su `env_link`; la riga
        `stripped-without-its-trailing-slash` di `support_url`; `test_support_link_is_the_support_address_and_logs_nothing[valid-is-the-address]`;
      - `test_instance_block.py`: `BILLING_LINK`, la riga `https-one-trailing-slash-removed` e
        `test_the_block_page_gives_a_regular_user_no_billing_link`;
      - `test_system_api.py`: `test_the_configured_support_address_is_answered[set-without-its-trailing-slash]`;
    - di A:
      - `test_legal_links.py`: le righe `stripped-without-its-trailing-slash` e `ipv4-with-a-port`, il confronto con
        `env_url` e `test_the_link_is_the_address_and_logs_nothing[terms|privacy-valid-is-the-address]`;
      - `test_instance_config_legal_api.py`: `test_a_valid_address_is_published_as_env_url_gives_it[selfhosted|managed-both-stripped-…]`;
      - `test_registration_service.py`: `test_a_url_variable_is_stripped_of_spaces_and_of_its_trailing_slash[trailing-slash|stripped-http-with-port|path-and-case-kept-billing_url]`
        e `test_a_missing_url_or_a_valid_billing_url_is_no_problem_to_report`.
  - Selettori: `services config-package`, `legal-links`, `registration`; e, con uno slot di ~8 min,
    `api instance-block`, `api system`, `api instance-legal`.

  Dettagli: piano H, §14, «Review di A9» e lotto «H-49 e H-48».
- ✅ **H-49 · `platform.test_mode`: un lane id nei limiti della sonda di prontezza** — basso; E (review di H-46), via
  coordinatore, 17/10. Da fare con H-48.
  - H-46 conta come corsia ogni `LIBREFOLIO_TEST_LANE_ID` non bianco. Il runner ne crea uno di 32 caratteri, e la sonda
    `test-lane-health` accetta da 16 a 128 caratteri: un lane id fuori da quei limiti non è una corsia che funziona.
  - Cura: i due limiti in costanti accanto a `owning_test_lane_id()`, usate dalla sonda e dal controllo.
  - Cura fatta il 17/10 da H (lotto «H-49 e H-48», piano H §14); E rivede.
    - `TEST_LANE_ID_MIN_LENGTH` (16) e `TEST_LANE_ID_MAX_LENGTH` (128) in `config/platform.py`, usati dalla sonda e da
      `platform.test_mode`: è una corsia solo un id, senza spazi, fra quei limiti.
    - Il messaggio dello stop managed dice «(no LIBREFOLIO_TEST_LANE_ID of 16 to 128 characters)».
    - Test: `services config-audit`, 220.

  Dettagli: piano H, §14, lotto «H-49 e H-48».
  Chiusa il 17/10 (riconciliazione del 17/10): `d97d83b57`, `988f22860`, entrati in dev `96da36422`. H-48 resta aperta.
- **H-50 · Le impostazioni di scope SYSTEM si leggono una volta per voce di `/prices/current`** — basso, prestazioni;
  E (R13-SEC9), via coordinatore, 17/10. Dopo la 1.3.
  - `configure_instance()` (`services/plugin_settings/runtime.py`) apre un `AsyncSession` sul motore asincrono per ogni
    istanza di un plugin che ha campi SYSTEM o USER. `POST /api/v1/assets/prices/current` configura un'istanza per
    voce: una connessione SQLite e una lettura per ogni asset della richiesta.
  - Oggi solo `mockprov` (test-only) dichiara campi così, quindi in esercizio non costa nulla; costerà al primo plugin
    vero con impostazioni.
  - Cura: leggere le righe una volta per richiesta (per famiglia e plugin) e passarle alle istanze, oppure una cache
    breve, invalidata da ogni scrittura delle impostazioni. Il codice è di X (impostazioni dei plugin): serve il suo
    OK, o lo fa X.

  Dettagli: questa riga.
- ✅ **H-51 · Il motore del server vivo tiene `trusted_schema` acceso, con il `regexp` e il `floor` Python di SQLAlchemy**
  — basso, sicurezza; H (review di B-36/B-37), deciso dal coordinatore il 17/10. Da fare dopo W-B75, nella 1.3.
  - SQLAlchemy 2.0.52 (dialetto pysqlite, ereditato da aiosqlite) registra `regexp` e `floor` in Python su ogni
    connessione. `trusted_schema` vale 1 di default.
  - Il listener globale `set_sqlite_pragma()` (`db/session.py`) imposta solo `foreign_keys`, WAL e `busy_timeout`.
  - B-28 controlla i tipi degli oggetti, non le espressioni.
  - Sonda (`files/b36review/` della sessione H): un archivio con una colonna `DEFAULT (regexp(…))` passa il controllo
    del ripristino, perché l'`integrity_check` della connessione semplice risponde `ok` (un CHECK invece lì fallisce,
    «unknown function»). Poi, nel server, ogni insert che omette quella colonna fa girare il `regexp` Python con il
    pattern e il valore dell'archivio; lo fa anche il motore async.
  - Cura: `PRAGMA trusted_schema=OFF` per primo nel listener globale. Lo schema di LibreFolio (head 009) chiama solo
    il built-in `lower()`, quindi per l'app non cambia niente.
  - Nello stesso lotto: la frase di `security.md` sulla chiave d'istanza durante il ripristino, superata da B-18
    (r. ~706). Va riscritta col percorso vero:
    - `dev.py backup restore --instance-key-file`, solo da CLI;
    - il file è letto da root prima del cambio di utente (B-38);
    - `instance_key_invalid` scatta prima di creare qualsiasi cosa;
    - la chiave dell'archivio vince (D1).
  - Sempre nello stesso lotto, la frase sul motore di Alembic: il listener di `env.py` è una cura vera.
  - Verifica nello slot: i miei test, le suite delle migrazioni e `api backup-restore`.

  ✅ **Fatto il 17/10** (checkpoint delle 15:50).
  - `set_sqlite_pragma()` spegne `trusted_schema` per primo e rilegge lo schema per ultimo
    (`writable_schema=RESET`). Il listener gira prima che il dialetto registri le funzioni e legge lo schema
    presto: senza il reset un CHECK o un indice le chiamava ancora, anche nel processo dell'upgrade (sonda
    `files/h51/`).
  - La frase di B-18 in `security.md` è riscritta, insieme alla doc dei motori.
  - Test: `db session-pragmas` (15).
  Dettagli: piano H, §14, «Review di B-36/B-37» e il lotto H-51.
  Chiusa il 17/10 (riconciliazione del 19/10): `bb2ba3e26`, `df34b9f4b`, `2def8f7db`, entrati in dev `70ab2fcc6`
  (CHANGELOG `6aa42af1a`).
- ✅ **H-52 · Gli script inline di `index.html` nella CSP per hash (D4 di H-43)** — basso, sicurezza; H, deciso dal
  coordinatore il 17/10 (D4): un lotto H dopo la fase 1 di H-43, nella 1.3 se c'è tempo.
  - Oggi `CSP_REPORT_ONLY_POLICY` (`security_headers.py`) ha `script-src 'self' 'wasm-unsafe-eval'`. I due script
    inline dell'`index.html` costruito (l'anti-FOUC di `app.html`, 1459 caratteri, e il bootstrap di SvelteKit, 373)
    sono segnalati su ogni pagina, e la baseline del raccoglitore li conosce (`index-inline-script-0/1`).
  - Cura: gli `sha256-…` dei due script nella policy, calcolati dall'HTML servito (`index.html` e `200.html`, che oggi
    hanno gli stessi script). Poi via le due voci dalla baseline, e il test 5 della spec del raccoglitore si aggiorna
    (la sua copia della policy).
  - Nello stesso lotto, `'report-sample'` nella `script-src` report-only, e la voce `cheetah-grid-global-probe` si
    restringe al campione «return this». Oggi conosce ogni `eval`.
  - Nota: le voci con `indexInlineScript` si cercano nell'`index.html` servito su `/`, mentre un link profondo riceve
    `200.html`. Gli script stanno alle stesse righe perché vengono dallo stesso `app.html`; con gli hash la dipendenza
    sparisce.

  ✅ **Fatto il 17/10** (checkpoint delle 21:15; decisioni del coordinatore D-H52-1…4).
  - `spa_inline_script_hashes()` (`static_site.py`) dà gli hash degli script inline di ogni pagina della build
    (`index.html`, `200.html`, che ha un bootstrap diverso, e `offline.html`). Li legge una volta, alla costruzione del
    middleware; `report_only_policy()` li aggiunge a `script-src`, accanto a `'report-sample'`.
  - Il gestore inline di `offline.html` è diventato un listener, e `sw.js` è ritimbrato.
  - La baseline E2E ha due voci: F1 con il campione esatto, F3. Il meccanismo delle righe è tolto.
  - Lungo la strada, due difetti preesistenti curati con l'OK del coordinatore:
    - `check_frontend_needs_build()` non guardava `frontend/static/`: una modifica lì lasciava la build «fresca»;
    - `stamp_service_worker()` riscriveva `sw.js` a ogni build della doc. Ora scrive solo se cambia, e `front build`
      timbra prima di costruire.
  - Prove: `services managed-headers` 411, `utils pwa-assets` 26, `runtime-isolation` 387; `front-utility
    csp-collector` 12 + 1 skipped su entrambe le corsie; cloud smoke nello slot.

  Dettagli: piano H, §14, lotto «H-43, fase 1», decisioni D4 e passo 4 (F1); lotto «H-52».
  Chiusa il 17/10 (riconciliazione del 19/10): `aaea0824b`, `cfb59de97`, `70da097fb`, entrati in dev `ca7ba117c`
  (CHANGELOG `1ec74c8e5`).
- **H-53 · La sonda dell'indirizzo di un link, con una `connect-src` applicata (F3 di H-43, metà sicurezza)** — basso,
  sicurezza; trovato dal primo cloud smoke, deciso dal coordinatore il 17/10. La metà dell'esperienza è di A.
  - Il controllo dell'indirizzo di un link (Impostazioni › Utenti) prende `<indirizzo scritto dall'admin>/api/v1/auth/
    address-probe?nonce=…` dal browser, di qualunque origine. Con la policy report-only di managed sono segnalazioni
    `connect-src` (AUSR-E-07 scrive apposta altre origini); la baseline le conosce con la voce
    `address-probe-other-origin` (confronto sul percorso, proprietari A e H).
  - Con una `connect-src 'self'` applicata la sonda di un'origine diversa dalla pagina verrebbe bloccata: un admin che
    naviga da un indirizzo interno vedrebbe «non verificabile».
  - Cura, quando la CSP si applica: l'origine pubblica configurata in `connect-src`, oppure la sonda dal server.

  Dettagli: piano H, §14, lotto «H-43, fase 1», passo 4 (F3).
- ✅ **H-54 · Il controllo della build vecchia non vede un file tolto da `frontend/src/` o da `frontend/static/`** —
  minimo, strumenti; trovato da test-author nel lotto H-52, 17/10.
  - `check_frontend_needs_build()` confronta le date dei file che esistono. Le date delle cartelle non contano (un
    `.DS_Store` le muoverebbe), quindi un file cancellato dopo la build resta nella build, che sembra fresca. Solo gli
    input dei contratti dei Tool hanno l'impronta del loro elenco (H-24).
  - Cura possibile: la stessa impronta dell'elenco (nomi, non date) per `src/` e `static/`, registrata a ogni build
    riuscita.

  Dettagli: piano H, §14, lotto «H-52», passo 3.

  ✅ **Fatto il 17/10** (checkpoint delle 21:41).
  - L'impronta dell'elenco registrata dopo ogni build riuscita (`tool_contract_fingerprint()`) contiene ora anche i file
    contati di `frontend/src/` e `frontend/static/`, tolti i cataloghi generati; il formato è `/2`.
  - Un file cancellato, rinominato o arrivato con una data vecchia fa ricostruire. Dopo l'aggiornamento c'è una
    ricostruzione, una volta sola.
  - Provato dal vivo: dopo la build, l'impronta registrata e quella attuale sono uguali e non si ricostruisce più.
  - Test: `utils runtime-isolation` 454 (+67).
  Chiusa il 17/10 (riconciliazione del 19/10): `14a723dc6`, `cb037b0e0`, entrati in dev `d6c252ec4`.
- **H-55 · La CSP applicata: `LIBREFOLIO_CSP_ENFORCE`** — medio-basso, sicurezza; H, dopo H-52, con le decisioni
  E1–E6 del coordinatore del 17/10. **Sospesa il 19/10**: è tra gli ampliamenti della 1.3 che il developer sta
  leggendo, con l'interruttore e il suo default.
  - Oggi la CSP del profilo managed solo segnala (H-52). Con l'interruttore acceso, le pagine della web app avrebbero
    in più una policy applicata: quella report-only con gli hash, senza `frame-ancestors`, perché i frame restano a
    `LIBREFOLIO_FRAME_PROTECTION`. È spento ovunque per default. La proposta per il managed: acceso dopo un cloud
    smoke verde con la policy applicata.
  - Le decisioni del coordinatore:
    - F1 (cheetah-grid) resta un'eccezione documentata; la trasformazione in Vite viene dopo la 1.3;
    - l'origine di `LIBREFOLIO_PUBLIC_URL` va in `connect-src` (con A per AUSR-E-07, dopo A-57);
    - gli hash si leggono solo all'avvio;
    - nessun endpoint di segnalazione;
    - `api.github.com` resta ammesso finché il controllo degli aggiornamenti è acceso.
  - Fatti l'analisi e i rossi, mai eseguiti. I rossi sono parcheggiati come patch nella cartella della sessione H
    (`files/parked/h55-csp-enforce-reds-on-d6c252ec4.patch`), e il worktree è tornato al commit.
  - Alla ripresa, prima della cura:
    - il rifiuto di `--coverage` sulla corsia che applica (scelta 4) poggia su una premessa sbagliata: istanbul legge
      `globalThis` e non fa `new Function`. Va riproposto;
    - un `LIBREFOLIO_PUBLIC_URL` non valido va gestito. Proposta: scriverlo nel log e non aggiungere nessuna origine.

  Dettagli: piano H, §14, lotto «H-55», note «Sospeso» e «Fuori pista».
- **H-56 · Allo spegnimento nessun passo aspetta o ferma i compiti in background dell'avvio** — basso; E (nota su
  E-19a), via coordinatore, 17/10. Dopo la 1.3, insieme allo spegnimento di Z.
  - `app_lifespan.py` tiene in `_background_tasks` questi compiti, e nessun passo dello spegnimento li cancella o li
    aspetta:
    - il prewarm dei provider;
    - quello delle festività di mercato;
    - l'audit delle valute salvate (E-19a, in un thread);
    - il prewarm del pool BRIM, se acceso (in un thread).
  - Alla chiusura del ciclo di eventi Python 3.13 cancella i compiti rimasti, poi aspetta i thread dell'executor di
    default fino a 300 s (`shutdown_default_executor`). Uno stop subito dopo l'avvio aspetta quindi i thread ancora al
    lavoro. L'audit legge e basta (circa 1,6 s a 3 milioni di prezzi), quindi interromperlo non fa danni.
  Dettagli: questa riga.
- **H-57 · Le migrazioni della 1.3 in una sola, `005_release_1_3_0_schema`, e 13 indici inutili tolti** — medio,
  schema; il developer, via coordinatore, 19/10 (variante V4: la 010 fuori, gli indici tolti nella 005). Fatto il
  19/10. `all-backend`: 28 771 passati; i 10 falliti sono rossi della base, non di H-57 (H-59 e altri, riprodotti su
  `HEAD` pulito). In attesa del treno con Z-33r e Z-32cr (produzione del developer ferma prima).
  - Una sola revisione al posto di 005–010, uguale allo schema che lasciava la catena (istantanea congelata, test);
    i 13 indici via con `DROP INDEX IF EXISTS`, modelli allineati, guardia `test_no_redundant_indexes` in
    `db validate`; la regola nelle istruzioni del DB, nello skill `devpy-server` e in `patterns/alembic.md`.
  - Un DB a una revisione ritirata (011 o 010) si porta avanti a mano, con la procedura V4 del piano H (provata
    sulla 005 definitiva). Il server non parte su quelle revisioni e il ripristino le rifiuta, per scelta.

  Dettagli: piano H, §14, lotto «H-57».
- **H-58 · Due lacune vecchie della doc del DB, viste in H-57** — basso, doc; docs-writer di H-57, 19/10.
  - `patterns/alembic.md`, «SQLite and Alembic Limitations»: presenta il batch mode senza l'avvertenza su
    `PRAGMA foreign_keys=ON` (ricostruire una tabella fa scattare gli `ON DELETE` delle tabelle figlie), che la
    docstring della 005 spiega; l'esempio del `CHECK` usa `op.batch_alter_table`.
  - `database/assets_pricing.md:63`: «(`identifier_isin`, `identifier_ticker`, …) are indexed», ma solo quelle due
    colonne hanno un indice.

  Dettagli: questa riga.
- **H-59 · I sostituti di `configure_test_runtime` nei test non accettano `lane_settings` (rossi della base da H-43)**
  — medio, test rossi in `dev_release2`; trovato da `all-backend` di H-57, 19/10. Proposta mandata al coordinatore.
  - H-43 (`cd04b17b0`) fa passare sempre `lane_settings=` da `cmd_server` a `configure_test_runtime`. Le funzioni che
    nei test ne fanno le veci accettano solo `port` e `data_dir`, quindi `TypeError` in 5 test:
    `test_probe_rate_limit.py::test_lane_server_starts_with_the_probe_limit_off`, `test_dev_server_interrupt.py` (3)
    e `test_dev_designer_lab_banner.py` (1, `[test-server]`).
  - Cura: i sostituti accettano `lane_settings=None`, come la funzione vera (test-author). I 3 file non sono di H:
    serve il via del coordinatore.
  - Il via è arrivato il 19/10 e allarga il lotto: anche `LIBREFOLIO_DISABLE_WHATS_NEW` in `UNDOCUMENTED_ON_PURPOSE`
    (D-A7) e `worker_exit_code` nelle attese di `test_tools_schemas.py` (J-19). EMF-009 è di E. **Fatto il 19/10**:
    8 rossi → verdi, checkpoint inviato; il ✅ col commit va alla prossima riconciliazione.

  Dettagli: piano H, §14, lotto «H-57», nota delle 14:20.
- ✅ **H-60 · Errori leggibili: le informazioni utili stampate in caso di errore, anche in console** — alto, regola del
  developer (19/10), via coordinatore. Analisi e via il 19/10 (D1 no, D2–D5 sì; D4 (a)). **Fatto il 19/10**: rossi,
  cura, regola, doc; `all-backend` 29 456 passati e 0 falliti. Checkpoint inviato; il ✅ col commit alla prossima
  riconciliazione. Restano agli altri D3 (A, J), D5 (J) e i P2 qui sotto.
  - **I P2 ai proprietari** (li distribuisce il coordinatore; dal piano H, §14, H-60 punto 2): X `assets/refresh.py`
    (363, 575, 594, 614, 629: anche testi di errori del DB nella risposta), `assets/metadata.py:132`,
    `assets/core.py:93`; W `brokers/broker_service.py:202,418,461` (`str(e)` per riga), `transactions/batch_*.py` e
    `lone_transfer_legs.py:98`, `brim/registry.py:45,89`, `brim/brim_provider.py:239`; MF
    `financial_math/portfolio/engine.py:473`; Y/J `signals/planning.py:197`; J `tools/executor.py:273`,
    `tools/worker.py:178`, `tools/registry.py:115,170`, `ai_export/dependencies.py:459` (diagnostics mai letti) e
    `:609` (catene senza `from`), D5 (`reason_code` di `snapshot_source_failure`), D3 per l'AI Export; A D3 per i
    messaggi generici; J/X `api/v1/fx/currencies.py:95` (`{e!s}` nel 502); H
    `platform/scheduler/settings.py:44`.
  - Il log dell'app è JSON; la forma raddoppiata dell'estratto viene dallo strumento che l'ha letto. Difetto vero:
    `logger.exception()` scrive la traceback due volte e il livello `EXCEPTION` (84 punti).
  - 90 `except` larghi senza traccia nel log; P1 l'AI Export (`dependencies.py:478`, i `diagnostics` mai letti) e
    `tools/executor.py:273` (J).
  - Proposta: `request_id` e gestore unico dei 5xx (H), console del frontend da `zodios-client.ts` (H, ok di A), la
    regola nelle istruzioni, i P2 per area (W, X, MF, Y/J).

  Dettagli: piano H, §14, lotto «H-60».
  - ✅ 21/10 (riconciliazione): in `dev_release2` col treno 2 (`e8c970379`; commit `bf16865ed`, cura `b6a5d8544`) e, per la mappa delle guide e il fix W-B37, col treno 3 (`6ba039f01`).

## A · Account e accessi (fase 01)

Piano: [`02_accounts`](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md).

Contabilità del 19/10 (base `6578f1d75`): ogni riga confrontata con il codice e con i commit. Chiuse ora A-2, A-5 (la
parte di A), A-6, A-7 (i punti di A), A-8, A-9, A-12, A-15, A-21 (con A-21a; il resto è la nuova A-21b) e A-39 (in
inglese). Restano aperte, e ancora vere nel codice, A-17, A-18, A-19, A-28, A-29, A-30, A-36, A-37, A-38 e A-48; A-1,
A-21b, A-31, A-41, A-49 e A-58 aspettano una decisione; A-4 e A-10 sono lavoro di documentazione; A-57 è sospesa.

- **A-1 · Un utente loggato vede più di «nomi broker e nomi utenti»** — medio, decisione (privacy; multi-utente e
  cloud); A (14/10).
  - Le email degli admin con `GET /users/search?admins=true`.
  - Nome e icona di tutti i broker con `GET /brokers?include_inaccessible=true`.
  - Elenco, anteprima e download di tutti i file caricati: `GET /uploads` e `/uploads/file/{id}`; solo la cancellazione
    controlla il proprietario.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), sezione «A1.8».
- ✅ **A-2 · `GET /settings/global` si legge senza login** — basso; chiusa il 16/10 con A6d (`683b4ff5b`, ingresso
  `19dd8a96d`): le impostazioni globali si leggono solo con il login, 401 senza sessione (GSET-001…003); A (14/10).
  Esponeva tutte le impostazioni globali:
  scheduler, durata della sessione, registrazione. Dettagli: idem, §2 «Da sapere».
- ✅ **A-3 · `reset_password` calcola bcrypt sul loop degli eventi** — basso; A (14/10); chiusa il 15/10 con A4
  (`3ac4114d5`: `await asyncio.to_thread(hash_password, new_password)`), registrata il 17/10 (X-R66).
  `services/accounts/user_service.py:205` chiama `hash_password` senza `asyncio.to_thread` (regola Async I/O). Si
  chiude con A4, che tocca il reset per la versione della sessione. Dettagli: idem, §1 «Reset della password».
- **A-4 · devWiki: prosa con i vecchi percorsi dei servizi account, e due pagine di dominio non allineate** — minimo;
  A (14/10), per lo storico.
  - 15 menzioni in prosa, in 14 file. Le tabelle «Source files» sono già aggiornate (C6).
  - `domains/auth.md` descrive una gestione utenti dalla UI che non esiste (F-002 l'ha già corretta).
  - `domains/layout-settings.md` descrive un footer con il ticker che non esiste.
  - Dopo A2 (15/10), 4 righe di prosa citano ancora le cartelle frontend spostate: `features/F-104.md:26`,
    `features/F-002.md:35`, `problems/copy-buttons-without-http-fallback.md:31`, `:33`. Le ultime due sono una tabella
    del corpo, non «Source files».
  - 19/10 a `6578f1d75`: ancora 14 righe con i vecchi percorsi dei servizi, in 13 pagine (`features/F-001`, `F-002`,
    `F-003`, `F-005`, `F-006`, `F-065`, `F-092`, `F-105`, quattro pagine di `problems/`,
    `decisions/automatic-popups-wait-for-guides`), e le 4 righe delle cartelle frontend qui sopra. Lavoro dello
    storico, con la tabella vecchio → nuovo di A10.
  - Dettagli: idem, §2 «Deriva della devWiki», «A1.4» e «A2.3».
- ✅ **A-5 · Formato preesistente in file toccati da A1** — minimo; chiusa per la parte di A il 15/10 con A3
  (`user_cli.py`); A (14/10).
  - black riformatterebbe 4 file, già così alla base: `scripts/user_cli.py`, `scripts/coverage_analysis.py`,
    `test_portfolio_api.py`, `test_portfolio_wac.py`.
  - ruff segnala W293 a `user_cli.py:208` e PLC0415 a `:271`.
  - ✅ **`user_cli.py` chiuso il 15/10** con A3, che ne tocca i comandi (L12): black, W293 e PLC0415, più il C901
    portato dal comando nuovo (ora una tabella). Restano gli altri tre file, fuori dal dominio di A.
  - 19/10 a `6578f1d75`: `test_portfolio_wac.py` ora passa black; `scripts/coverage_analysis.py` e
    `test_portfolio_api.py` no. Fuori dal dominio di A: segnalati al coordinatore.
  - Dettagli: idem, «A1.6» e «A3.3».
- ✅ **A-6 · Una fonte sola per le regole della password** (richiama T-B4 della sezione «T (colori)») — basso; chiusa
  il 16/10 con A6c (`4bbc6fbf6`, ingresso `3b3f6a1f0`): le regole stanno in `services/accounts/password_policy.py`,
  l'API e la CLI le applicano, il frontend le legge (`features/auth/passwordRules.ts`); A (15/10).
  - Quattro copie delle stesse cinque regole: `ui/input/PasswordStrength.svelte`, `settings/PasswordChangeModal.svelte`,
    `auth/RegisterCard.svelte` e `validate_password` di `scripts/user_cli.py`.
  - L'API chiede solo 8 caratteri (`schemas/auth.py:31`, `:38`). Da decidere se applicare le stesse regole anche lì.
  - Si fa nel lotto A5, che aggiunge i moduli d'invito e di reset con le stesse regole.
  - 15/10: **aspetta la decisione 37 del developer** (coordinatore, via di A5). Intanto A5a lascia all'API il minimo di
    8 caratteri anche nei corpi nuovi (`AuthRegisterRequest` con l'invito, `PasswordResetRequest`).
  - 15/10 pomeriggio: **la decisione 37 è presa**. Le regole stanno nel backend, che le applica anche all'API; un
    endpoint le espone al frontend; la CLI usa la stessa funzione; l'indicatore di robustezza resta; le password già
    salvate restano valide. **Si fa nel lotto A6c**, dopo A6b e prima di A8: dettagli nel piano, «Decisione 37».
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A1.9».
- ✅ **A-7 · Doc per sviluppatori non allineate al codice, trovate in A3** — minimo; chiusa per i punti di A (15/10,
  con A4b e A6b; la frase «via CLI or API» di `users_and_brokers.md` non c'è più); A (15/10, `docs-writer`).
  - `architecture/access_control.md:116-123`:
    - dice che `set_user_admin()` non controlla l'ultimo admin, ma da `2fb8b8502` l'ultimo admin attivo non si
      declassa né si disattiva;
    - dice che un account disattivato riceve un 401, ma riceve un 403 `ACCOUNT_DISABLED`, e solo con la password
      giusta.
    - ✅ **Chiuse il 15/10** con A4b: `docs-writer` le ha corrette insieme alle righe sulle sessioni.
  - `frontend/components/features/settings.md`: il titolo «GlobalSettingsTab (Admin only)», ma la scheda la vedono
    tutti. Si sistema in A6, con le schede Utenti e Sicurezza (attenzione all'ancora). ✅ **Chiusa il 15/10** con A6b:
    titolo «🌍 GlobalSettingsTab (read by everyone, edited by administrators)», ancora esplicita
    `#globalsettingstab-admin-only` per i link vecchi.
  - `frontend/state/app-state.md:11`: dice che lo store dell'autenticazione gestisce token JWT, ma usa il cookie
    HttpOnly. ✅ **Chiusa il 15/10** con A4b.
  - La prop `icon` di `PasswordInput`, aggiunta da T, manca in `core-ui/atoms.md` e `features/auth.md`. È di T:
    segnalata al coordinatore.
  - Trovata in A4 (15/10): `architecture/patterns/alembic.md` presenta il batch come modo normale di cambiare una
    tabella in SQLite, e il suo esempio di CHECK usa `op.batch_alter_table('transaction')`. Non avverte che, con
    `foreign_keys=ON`, il batch ricostruisce la tabella e cancella a cascata le righe delle tabelle figlie: è il
    motivo per cui la 004 e la 005 lo evitano. Il nome della tabella è anche sbagliato: è `transactions`. La pagina è
    di tutti: segnalata al coordinatore.
  - Trovata in A4b (15/10): `architecture/users_and_brokers.md`, «👤 User Roles», dice che un admin gestisce gli
    utenti «via CLI or API». L'API non esiste ancora: la porta A5. Si verifica allora.
  - 19/10 a `6578f1d75`, non di A e ancora veri: la prop `icon` di `PasswordInput` manca in `core-ui/atoms.md` (T);
    `patterns/alembic.md` usa ancora `op.batch_alter_table('transaction')` senza l'avvertenza su
    `foreign_keys=ON`. Di nuovo al coordinatore.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A3.5», «A4.5» e «A4b.4».
- ✅ **A-8 · Richiama TC-6** della sezione «T (colori)» (chiusa il 15/10 con A5b, `2b0715532`): alla prima visita con
  il browser in `it-IT`, il selettore della
  lingua mostra l'inglese — basso; programma colori (15/10).
  - Probabile causa: `lib/stores/app/language.ts`, `init()`.
  - Si corregge in un lotto di A che tocca la pagina d'accesso o le preferenze, con il rosso visto prima (E2E con il
    locale del browser `it-IT`).
  - ✅ **Corretta in A5b** (15/10; commit all'ingresso di A5). Il negozio della lingua segue `locale` di
    svelte-i18n finché non c'è una preferenza salvata e nessuno ne sceglie una. Il selettore pubblica
    `data-language`. Rosso visto prima: `language.test.ts` (6 rossi su 7, poi 7 ✅). L'E2E `it-IT`/`fr-FR` in
    `auth.spec.ts` gira dopo la finestra.
  - Dettagli: idem, «A3.0».
- ✅ **A-9 · Il runner non toglie le variabili degli account dall'ambiente della corsia** — basso; chiusa da H con
  C-96 (`901fa33f6`, 15/10; registrata dal coordinatore il 16/10); A (15/10, trovata da
  `test-author` in A5).
  - `LIBREFOLIO_REGISTRATION`, `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_PUBLIC_URL` e `LIBREFOLIO_BILLING_URL`: se la shell
    che lancia il runner ne imposta una, il server della corsia la legge, e cambiano la registrazione o i link per
    tutti i test che girano lì.
  - I casi che cambiano queste variabili girano già nel processo del test, con `monkeypatch`: il rischio è solo
    l'ambiente di chi lancia.
  - È infrastruttura condivisa dei test (`configure_test_runtime`): decide il coordinatore.
  - ➡️ **Passa a H come C-96** (coordinatore, 15/10). E ha trovato che il problema è più largo: ogni `LIBREFOLIO_*`
    del `.env` arriva alle corsie dei test, comprese le future variabili SMTP. La cura generale di H copre anche
    queste quattro. A non ha scritto né codice né test per A-9.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A5.2».
- **A-10 · Debito di traduzione delle pagine toccate da A5** — basso; A, 15/10.
  - 17/10, lotto A-11/A-16/A-40: in EN cambiano ancora `admin/cli_tools` (i punti 📏 e 🏁 su `user activate`) e
    `admin/configuration` («When the Instance Is Full»: `user activate` senza avviso per chi tiene già il posto).
  - 17/10, lotti A8a–C-54, nessun timbro: `admin/configuration` («Failed Sign-ins» `#login-limit`, i controlli
    d'avvio, la frase dell'avviso dell'admin iniziale, la riga di `LIBREFOLIO_PROBE_RATE_LIMIT`),
    `admin/connection_checks` (`#client-address`), `admin/cli_tools` (la regola 3–50), `admin/index`,
    `user/getting-started` (la nota del login, `#verify-email`), `user/settings/profile`, `user/settings/about` (la
    sezione nuova di «What's new», ancora `#changelog-modal`), `user/installation` (un punto),
    `community/contribute`. Ancore da tenere uguali in ogni lingua: `#login-limit`, `#client-address`,
    `#changelog-modal`.
  - Le pagine EN di A5a e A5b sono nel lotto; IT, FR ed ES sono indietro su 6 pagine: `admin/configuration`,
    `admin/cli_tools`, `admin/settings`, `admin/service_exposure`, `community/faq`, `user/getting-started`.
  - Vanno tradotte insieme: si linkano con ancore esplicite nuove (`#accounts`, `#user-limit`, `#registration`,
    `#invite`, `#reset-link`, `#reset-onboarding`, `#invitation-link`, `#password-reset-link`), da tenere uguali
    in ogni lingua.
  - Finché non sono tradotte il build stretto resta verde: le pagine vecchie non puntano alle ancore nuove.
  - Si fa dopo A6–A9, che toccano di nuovo le stesse pagine. La prepara il lotto A10, solo su richiesta
    esplicita del developer (coordinatore, 15/10).
  - Da A6b (15/10) in più: la pagina nuova `admin/users` (senza traduzioni: IT, FR ed ES mostrano l'inglese) e le
    sezioni cambiate di `user/settings/profile` («Delete Account»), `admin/cli_tools` («Manage Users», «Invite
    Someone»), `admin/settings` («Who Can Sign Up», Related), `admin/configuration` (righe `LIBREFOLIO_PUBLIC_URL` e
    `LIBREFOLIO_BILLING_URL`), `admin/index` e `user/settings/index`. La pagina nuova non usa ancore che esistono solo
    in inglese; quando le traduzioni avranno `#accounts`, `#user-limit`, `#registration`, `#invite`, `#reset-link` e
    `#reset-onboarding`, si potranno aggiungere i link precisi.
  - In `admin/configuration` IT, FR ed ES manca tutta la sezione «Accounts and Sign-ups» (`#accounts`): nessuna
    delle tre variabili `LIBREFOLIO_REGISTRATION`, `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_PUBLIC_URL`. Il coordinatore
    (15/10, 16:56) conferma che è debito di A.
  - Da A6d, A6e e A6c (16/10), nessun timbro: `admin/settings` (introduzione, «Who Can Sign Up», che in IT/FR/ES manca
    del tutto), `admin/configuration`, `admin/service_exposure`, `admin/hosting_providers`, `admin/cli_tools` (anche
    «➕ Create and List Users», le regole della password), `user/installation`, `user/settings/profile` («Changing
    Your Email», «🔑 Change Password»), `admin/email`.
  - Da A7a (16/10), nessun timbro: sezioni nuove in `admin/configuration` («The Initial Administrator») e
    `admin/cli_tools` (`user setup-link`), con le ancore `#initial-admin` e `#setup-link` da tenere uguali in ogni lingua;
    `admin/hosting_providers` (`#initial-admin`); una o due frasi in `admin/settings`, `admin/users`, `admin/index`,
    `admin/host_installation`, `admin/docker_advanced`, `user/installation`, `user/getting-started`.
  - Da P18 (16/10), nessun timbro: in `admin/cli_tools` due sezioni nuove, «Change the Email Address of an Account»
    (`#set-email`) e «Two Accounts with the Same Email Address» (`#email-case-conflict`), con le ancore da tenere uguali
    in ogni lingua (oggi le pagine inglesi linkano `cli_tools.md` per nome di sezione, senza ancora); una frase in
    `admin/docker_advanced` (un riavvio non aiuta finché gli account non sono separati); in `user/settings/profile`
    «Changing Your Email» (un punto cambiato, uno nuovo: le maiuscole).
  - Da N69a (20/10), nessun timbro; le traduzioni ora dicono cose false:
    - `user/settings/index` dice ancora che «Administration» è visibile a tutti; da N69-2 è solo degli admin;
    - `admin/settings`, in tre passaggi: l'introduzione («everyone can read them»), «everyone else gets a read-only
      view» ed «Everyone can see the panel»;
    - `user/settings/profile`: l'avatar si vede anche nella scheda Utenti, con un link nuovo `admin/users.md#accounts`
      che manca alle traduzioni;
    - `community/faq`: «Scheduler Enabled» lo controlla un amministratore, nelle due voci di prezzi e cambi.

  Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A5b.5».
- ✅ **A-11 · Un tema non valido in `user_settings` blocca l'accesso** — basso; chiusa il 17/10 (commit del
  coordinatore): un tema salvato che l'app non conosce si mostra come il `default_theme` noto, altrimenti `auto`, con un
  avviso nel log; la riga non si riscrive (SET-A11-01…07); trovata dal `test-author` di E (15/10),
  letta nel codice e non ancora provata; segnalata dal coordinatore.
  - Una riga di `user_settings` con un `theme` diverso da `light`, `dark` e `auto` farebbe rispondere 500 a
    `/auth/login` e a `/settings/user`.
  - Prima della correzione serve un rosso. È piccola: va in un lotto dopo A5.
- ✅ **A-12 · `e2e/settings.spec.ts`: selettori ancora fragili nei test non toccati da A5b** — minimo; chiusa il 15/10
  con A6b (`1577663c1`, ingresso `09ca36b9d`); A (15/10,
  `test-author` della riparazione).
  - I test dei numeri usano `.first()` su `.setting-row input[type="number"]`, i `title` tradotti «Save» e
    «Undo» e un XPath su una classe CSS.
  - Lo sblocco usa il `title` tradotto, mentre esiste `settings-lock-toggle`.
  - I due `beforeEach` aspettano la classe `.setting-row` invece di `data-busy` della scheda.
  - Il segnaposto «Coming soon» (disabilitato sempre) non ha più un test: lo copriva per caso il vecchio
    `.first()`. Basta un test di componente (`SettingToggle`, `disabled` e `badge`).
  - I test «non admin» non provano la sola lettura: manca l'asserzione che `settings-lock-toggle` non c'è.
  - Si fa con la scheda Utenti (A6), che tocca la stessa pagina.
  - ✅ **Chiusa il 15/10** con A6b (`test-author` E2): `data-busy`, `settings-lock-toggle`, righe per chiave,
    `setting-save`/`setting-undo`, prova della sola lettura (nuovo `settings-readonly-indicator`), il segnaposto in
    `SettingControls.test.ts`; `front-utility settings` 46 ✅. Commit al checkpoint A6b; dettagli in «A6b.2».
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A5b.9».
- ✅ **A-13 · Su un'istanza bloccata, `/invite` mostra il modulo e la registrazione finisce al login** — minimo; chiusa
  il 16/10 in A7b (commit del coordinatore); A (15/10, dal merge di H CP6; accettato dal coordinatore).
  - Cura (decisione del coordinatore, A7b): l'intercettore del client non porta più al login su un 401 dalle pagine
    anonime dei link (`/setup`, `/invite`, `/reset-password`, `/verify-email`, `isLinkPage`; revisione di H), e
    `describeRegistrationError` legge il 401, o il 423 `instance_blocked`, come `auth.instanceBlocked`. Per
    `/verify-email` il 401 di `confirm` resta da riconoscere nella pagina: H lo passa a E.
  - Contesto: per non perdere l'accesso, `auth.inspect_link_token` e `auth.reset_password_with_link` entrano in
    `ALLOWED_WHEN_BLOCKED` (lotto piccolo di H dopo A5); `auth.register` resta fuori.
  - Effetto: `tokens/inspect` risponde anche per gli inviti, quindi `/invite` mostra il modulo. La registrazione
    riceve poi un 401 (anonimo su una rotta bloccata), e l'interceptor del client porta al login senza spiegare.
  - Possibile cura: la pagina d'invito che riconosce il blocco (per esempio un campo pubblico e innocuo in
    `/system/instance`, da concordare con H e con la decisione 15), oppure `tokens/inspect` che sul blocco
    risponde come per un link non valido quando lo scopo è `invite`.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A5b.10».
- ✅ **A-14 · `access_control.md`: «The last OWNER cannot remove themselves» contraddice «Self-Management»** — minimo;
  trovata dal `docs-writer` di A6a (15/10), fuori dal perimetro di A, segnalata al coordinatore.
  - In «Key Rules & Constraints» l'ultimo OWNER non può togliersi; in «Self-Management», e nel codice
    (`BrokerService.leave_broker`), l'ultimo OWNER che se ne va elimina il broker.
  - La pagina è del controllo d'accesso ai broker: la correzione è di chi la tiene (W, o chi decide il coordinatore).
  - **Assegnata a W** dal coordinatore (15/10, 16:56), con la doc di `leave_broker`.
  - **Chiusa** (16/10, 01:38) dal lotto di doc di W (`bf66d4fe7`), entrato col treno 72 (`6fa3f8936`).
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A6.5».
- ✅ **A-15 · La docstring di `instance_block.py` non cita la sonda dell'indirizzo** — minimo; chiusa il 17/10 da H
  (`ef3f29f52`: la docstring cita `GET /auth/address-probe`); trovata dal
  `docs-writer` di A6a (15/10). Il file è di H.
  - La docstring elenca come esempi le rotte pubbliche fuori da `ALLOWED_WHEN_BLOCKED`. Da A6a ce n'è un'altra,
    `GET /auth/address-probe`, che con l'istanza bloccata risponde 401 come le altre.
  - Una riga, da mettere nel lotto piccolo di H su `ALLOWED_WHEN_BLOCKED`, o da A al prossimo aggiornamento di base.
  - **Girata ad H** dal coordinatore (15/10, 16:56).
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A6.5».
- ✅ **A-16 · L'unico admin che elimina il proprio account riceve 400 senza `error_code`** — minimo; chiusa il 17/10
  (commit del coordinatore): 400 `{error_code: LAST_ADMIN, message}`, nel dialogo la chiave nuova
  `settings.usersTab.errors.LAST_ADMIN_DELETION` (ACCDEL-002/003, AERR-15…19, ADEL-28/29); A (15/10, dal
  `test-author` V4 di A6b).
  - `DELETE /auth/users/me` risponde `400 "Cannot delete account: you are the only administrator"`: una frase
    inglese e nessun codice.
  - Dal frontend di A6b, `accountErrors.ts` mostra la frase del server per un 400/409 senza codice, come faceva il
    dialogo di prima. Funziona, ma non è tradotta.
  - **Cura**: un `detail` con `error_code` (per esempio `LAST_ADMIN`) e un messaggio tradotto nel dialogo. Cambia la
    forma della risposta, quindi servono un rosso e l'aggiornamento dei casi ACCDEL sull'unico amministratore.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A6b.2».
- **A-17 · KeePassXC mette la sua icona sul campo Email della registrazione** — basso; segnalata dal coordinatore
  colori (15/10).
  - KeePassXC prende come nome utente il campo subito prima della password, e in `RegisterCard` quel campo è Email.
  - Possibile cura: Email prima di Username, nella registrazione e nella pagina d'invito che usa la stessa scheda.
    Attenzione a T-8b dei colori, che tocca le stesse schede di accesso: si fa dopo il suo ingresso.
- **A-18 · Il registro delle schede importa i corpi: ogni scheda nuova costringe a un `vi.mock` in più** — basso;
  E-6, segnalato da E tramite il coordinatore (15/10).
  - `settingsTabs.ts` importa il componente di ogni scheda. I test che usano il registro vero (`settingsTabs.test.ts`,
    `routes/(app)/settings/page.tabs.test.ts`) devono rendere inerte ogni corpo con un `vi.mock`. Tocca B, E, X e A.
  - **Opzione 1, caricamento pigro**: `load: () => import('…')` al posto di `component`; la pagina rende
    `{#await tab.load()}`. In più ogni scheda da amministratore diventa un pezzo di JS separato. I test che leggono
    solo id e ordini non importano più nessun corpo.
  - **Opzione 2, registro senza corpi**: `settingsTabsMeta.ts` (id, etichetta, icona, ordine, `visible`, `props`,
    `alignEnd`) più una mappa id → componente usata solo dalla pagina.
  - **Non entra in A6b**: cambia il rendering della pagina e le asserzioni dei test di B ed E, e A6b è già validato.
    Proposta: un lotto breve e coordinato, quando le schede di B, E e X sono tutte dentro, con
    `settings`/`admin-users` E2E e lo scatto della galleria da ricontrollare (il corpo arriva dopo un `await`).
  - Nello stesso giro, nota di G (15/10): i corpi e le rotte dello scatto `settings/users` in `fixtures/galleryUsers.ts`,
    come `galleryEmail.ts`.
- **A-19 · Su un'istanza su invito «Register here» lampeggia al caricamento del login** — basso; deciso dal
  coordinatore in A6d (15/10).
  - Finché `GET /system/instance` non risponde, `LoginCard` usa `DEFAULT_INSTANCE_CONFIG` (`open`) e offre il link;
    poi lo ritira. Il default resta `open` per non mettere in corsa gli scatti del login (G, theme-roles) e per lasciare
    alle E2E negative di `auth.spec.ts` il loro controllo «prima».
  - Possibile cura: nascondere il link finché l'istanza non risponde, con uno stato `data-*` sulla scheda che le prove
    e la galleria possano aspettare. Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md),
    «A6d.1».
- ✅ **A-20 · `black` fallisce su `scripts/test_runner/_backend_services.py`** — minimo; chiusa in A6d (15/10); da E tramite il coordinatore
  (15/10). Il `print_info` di `services_account_deletion_preview` (A6a, `5928176cf`) ha 305 caratteri: si spezza in A6d.
- ✅ **A-21 · Lo username accetta qualsiasi testo, e finisce nel saluto delle email** — basso; chiusa il 17/10 con
  A-21a (`5da71d037`, ingresso `6e2b2c8b7`): niente `@` nei nomi nuovi, nessuna email uguale a un nome, la ricerca
  per indirizzo prima; il resto è A-21b, qui sotto. Dal coordinatore (15/10,
  dalla revisione di sicurezza di E3).
  - Oggi `username` ha solo una lunghezza (3–50): passano anche frasi intere, link e testo che imita un messaggio
    del sistema, e le email di E lo mettono nel saluto.
  - Possibile cura: un insieme di caratteri ammessi (lettere, cifre, `._-`), uguale in registrazione, profilo, CLI e
    inviti; gli username già salvati restano validi (la regola vale solo quando se ne sceglie uno nuovo), come per le
    password (decisione 37).
  - In più (dal `test-author` di A-22, 16/10): uno username può contenere `@` e somigliare a un indirizzo, quindi un
    evento di log che porta lo username («User logged in» e altri) può scrivere qualcosa che sembra un'email; e il login
    cerca «username o email» con un solo campo, quindi uno username uguale all'indirizzo di un altro account è ambiguo.
    Il carattere `@` va escluso con la stessa regola.
  - **Allargata dal coordinatore** (16/10, con P18): gli username diventano unici senza distinzione di maiuscole, come gli
    indirizzi (P18); username nuovi senza `@`, e un identificativo con `@` cerca solo l'email (oggi
    `get_user_by_username_or_email` prende il primo dei due, senza ordine: il login e la «password dimenticata» per email
    possono finire sull'account sbagliato, nota di E). Per gli username già salvati con `@` o con varianti di maiuscole,
    prima un'analisi, nessun cambio silenzioso. Lotto dopo P18.
- **A-21b · Username unici senza distinzione di maiuscole, e un insieme di caratteri** — basso, decisione del
  developer; da A-21 (coordinatore, 17/10, 07:01). L'unicità a prescindere dalle maiuscole (come gli indirizzi,
  P18), i caratteri ammessi nei nomi nuovi, e una migrazione nuova (la 010 ora è di Z-32 (c)). La ricerca non va resa
  indifferente alle maiuscole prima dell'unicità (punto b di E: ricreerebbe il DoS fra «Bob» e «bob»). Facoltativo,
  per H: il conteggio delle collisioni storiche nei controlli di Sicurezza. Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md),
  «A-21 — Analisi».
- ✅ **A-22 · I login falliti scrivono nel log l'identificativo digitato, anche un indirizzo email** — basso; chiusa in A-22
  (16/10); dal `test-author` di A7c (16/10).
  - `api/v1/auth.py` ~160–167: «Login failed: user not found», «…wrong password», «…user inactive» con
    `username=request.username`; il login accetta anche l'email in quel campo, quindi un tentativo fallito con l'email
    la scrive nel log, contro la regola di E (nessun indirizzo nei log).
  - Cura proposta: `user_id` quando l'account esiste (password sbagliata, account disattivo), niente dell'identificativo
    quando non esiste; un rosso in-process come PROF-017. Da fare subito dopo A7c o in A8, che riscrive quel percorso.
    Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A7c».
  - Fatta così (16/10): LOGIN-027…033 in `test_auth_api.py`; dettagli nel piano, «A-22».
- ✅ **A-23 · L'avvio della verifica dell'indirizzo risponde 500 quando la chiave d'istanza non si può usare** — basso; da
  H (H-19, tramite il coordinatore, 16/10). **Chiusa** (17/10): fatta da H come H-19 (dev `9b23bdbfe`: `48aa7a3ed` +
  `139ca6129`; revisione di A: OK). Il seguito sulle parole dei due dialoghi è **A-49**.
  - `POST /api/v1/users/address-probe` (`address_probe.issue_probe_nonce()`, firma il nonce con una chiave derivata dalla
    chiave d'istanza) risponde 500 se la chiave non si può usare, mentre `GET /auth/address-probe`
    (`verify_probe_nonce()`) lo tollera.
  - Cura: 503 con un codice d'errore, e il dialogo della scheda Utenti lo dice come «non verificabile». Lotto piccolo dopo
    A7a/A7b; diventa urgente solo se il developer sceglie l'opzione A di H-3 (P24).
- ✅ **A-24 · Tre test di E diventano impossibili con P18** — basso; chiusa il 16/10 (delta A-24 dopo il merge di base
  `12cd3c2e0`, commit del coordinatore); A (16/10, dai verdi di P18).
  - `test_email_flows.py` (`ONE_MAILBOX`, la riga 1356), `test_email_verification.py` EMV-043 (`MAILBOX_VARIANTS`, la
    riga 166) e `test_email_verification_api.py` EVA-016 (`MAILBOX_VARIANTS`, la riga 122) creano quattro account sulla
    stessa casella scritta in quattro forme ASCII: con l'indice `ux_users_email_lower` la seconda riga è rifiutata.
  - Cura (decisa dal coordinatore, approvata da E, 16/10): varianti con lettere non ASCII in letterali NFC (`\u00e4`
    precomposta), una casella per le chiavi `casefold` di E, quattro righe per l'indice A–Z. La scrive A con un
    `test-author` **dopo il mini-lotto di E** che fa accettare `SMTPUTF8` al suo SMTP finto (oggi un destinatario non
    ASCII dà `SEND_FAILED`).
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «P18.4» e «P18.5».
- ✅ **A-25 · La scheda Profilo chiede la password per un cambio di sole maiuscole** — basso; chiusa il 16/10 (lotto A-25,
  commit del coordinatore); dal `docs-writer` di P18
  (16/10).
  - `features/settings/tabs/ProfileTab.svelte` righe 89–92 confronta l'indirizzo esatto: con un cambio di sole maiuscole
    la scheda chiede la password attuale, avvisa della disconnessione e tiene «Salva» spento, mentre il server (C5 di
    P18) non chiede nulla e non chiude sessioni.
  - Cura approvata dal coordinatore (16/10): solo logica, nessuna classe; un helper `sameEmail` (A–Z come il backend),
    `emailNeedsPassword` e il blocco della password solo per un indirizzo diverso; rossi prima in `ProfileTab.test.ts`.
    Lotto subito dopo l'aggiornamento di base che porta IM, come commit a sé; poi una frase in `user/settings/profile`.
- ✅ **A-26 · Il confronto «modelli = migrazione» di 005 non vede un indice su espressione non unico** — minimo;
  chiusa il 17/10 (commit del coordinatore): la chiave degli indici di `_shape` viene da `_index_list` (MIG005-A26-01…03,
  anche un indice unico con due nomi); dal
  `test-author` di P18 (16/10).
  - In `test_migration_005_accounts.py`, la chiave `indexes` di `_shape` viene dall'inspector di SQLAlchemy, che salta gli
    indici su espressione da entrambe le parti (con un avviso). Gli insiemi unici li vede (riparazione di P18), ma un
    indice su espressione **non** unico presente da una parte sola, o lo stesso con due nomi, passerebbe.
  - Cura: costruire quella chiave da `_index_list` (origine `'c'`). Oggi nessun indice del genere esiste; per
    `ux_users_email_lower` nome e SQL li fissa MIG009-003.
- ✅ **A-27 · Un cambio dell'indirizzo o della password non revoca i link di reset vivi** — medio (sicurezza); chiusa il
  16/10 (lotto A-27, commit del coordinatore); dalla revisione di E (E6.9), tramite il coordinatore (16/10).
  - `user_service.update_profile` (cambio vero dell'indirizzo: anche `PUT /auth/profile` e `user set-email`) e la rotta
    `POST /auth/change-password` chiudono le sessioni ma lasciano vivi i link `PASSWORD_RESET`: con la «password
    dimenticata» aperta, chi controlla la vecchia casella chiede un link prima del cambio e lo usa dopo, entro 30 minuti.
    Stesso buco in `user_service.reset_password` (CLI `user reset`), trovato da A.
  - Cura: `token_service.revoke_tokens(…, purpose=PASSWORD_RESET)` nella stessa transazione del cambio, come già fanno
    `create_password_reset` e `complete_password_reset`; rossi prima. Lotto a sé dopo l'ingresso di P18.
  - Fatta così (16/10): i tre punti; rossi nel contratto 7 di `test_session_version.py` e REVOKE-003…007 di
    `test_session_revocation_api.py`. Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md),
    «A-27».
- **A-28 · La riga dell'email della scheda Profilo non si assesta dopo certi salvataggi** — minimo; dal `test-author` di
  A-25 (16/10).
  - Il server mette il dominio in minuscolo (`EmailStr`): dopo aver salvato `Alice@Example.COM`, `/auth/me` risponde
    `Alice@example.com`, l'input tiene quanto scritto e la riga resta «modificata» (con un cambio vero scritto con il
    dominio in maiuscolo, prima di A-25 chiedeva perfino di nuovo la password per lo stesso indirizzo).
  - Un indirizzo cambiato altrove mentre la scheda è aperta: una variante di sole maiuscole della forma vecchia è un
    cambio vero per il server, che risponde 400 `CURRENT_PASSWORD_REQUIRED`; la scheda tiene l'indirizzo e svuota la
    password, ma non mostra il campo per scriverla.
  - Cura possibile: dopo un salvataggio riuscito l'input prende la forma che il server ha conservato; sul 400
    `CURRENT_PASSWORD_REQUIRED` la scheda rilegge l'indirizzo salvato. Da decidere con A7b/A8, che toccano la stessa
    scheda.
- ✅ **Nota per A8** (limite dei tentativi): anche `PUT /auth/profile` (con A6e) e `POST /auth/change-password`
  verificano la password attuale: vanno sotto lo stesso limite del login, o diventano un modo per indovinarla.
  Fatta il 17/10 con A8 (`66873b0c9`: i due endpoint rispondono 429 oltre il limite, prima di controllare la password, e
  contano errori e successi in `login_throttle` sotto lo username dell'account), registrata il 17/10 (X-R66).
- **A-29 · Sotto `vite dev` le pagine dei link portano al login** — minimo; da H, revisione di A7b (16/10).
  `frontend/src/hooks.server.ts` ha `PUBLIC_ROUTES` = `/` e `/api`: con il server di sviluppo (5173) chi apre un link
  senza sessione viene mandato a `/?redirect=…` e il token nel frammento si perde. In produzione e nelle corsie di test
  il frontend è statico e non passa di lì. Cura possibile: le quattro pagine dei link (`isLinkPage`) fra le pubbliche.
  Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A7b.5».
- **A-30 · Un nuovo link di setup dall'API e dalla scheda Utenti** — basso; deciso dal coordinatore (A7b, 16/10).
  Oggi l'admin iniziale in attesa riceve un link nuovo solo da `dev.py user setup-link` (o dal pannello di chi ospita):
  la scheda Utenti mostra il suggerimento, nessun pulsante. Dettagli: [piano
  02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A7b — Analisi e contratto».
- **A-31 · Il ripristino revoca il link di setup che l'avvio ha appena riarmato** — basso, non è un difetto della 1.3;
  da B tramite il coordinatore (16/10); A e B insieme.
  - Il caso: un archivio con l'admin iniziale ancora in attesa **e** un altro admin attivo, ripristinato su
    un'istanza con `LIBREFOLIO_ADMIN_EMAIL` e un token mai visto. Con l'ordine d'avvio della decisione N57
    (`global-settings` → `admin-bootstrap` → `restore-commit` → `plugin-secrets-check`) il bootstrap riarma il link di
    setup e il commit del ripristino, che revoca ogni link vivo di qualunque scopo, lo revoca subito: serve
    `./dev.py user setup-link`, e il log dell'avvio successivo lo dice.
  - Cura possibile (B): nel commit, risparmiare i link emessi dall'avvio in corso.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «Dopo A7b — A-31».
- ✅ **A-32 · Un admin iniziale disattivato si riattiva con il suo vecchio link di setup** — medio (sicurezza, confidenza
  5/10); chiusa il 17/10 in A7b-2 (commit del coordinatore); dalla revisione di sicurezza di E («R13-SEC»), tramite il
  coordinatore (16/10).
  - Cura (N60): `token_service.retire_tokens` (revocato e consumato insieme) a ogni attivazione e a ogni password data,
    e nel rifiuto di `complete_admin_setup`; per ogni account con un link di setup.
  - `complete_admin_setup` rifiuta solo un account attivo; le altre attivazioni (PATCH dell'admin, `user activate`) e
    gli altri modi di dare una password (`user reset`, link di reset, cambio password) non toccano i link
    `ADMIN_SETUP`: attivato per altra via e poi disattivato entro le 72 h, l'account torna «in attesa» e chi ha il link
    (anche dal log) lo riattiva con una password sua.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A7b-2 — Analisi e
    contratto».
- ✅ **A-33 · Cambiare l'indirizzo dell'admin in attesa non revoca il link già mandato al vecchio** — basso (sicurezza,
  confidenza 5/10); chiusa il 17/10 in A7b-2 (commit del coordinatore); dalla revisione di E («R13-SEC»), tramite il
  coordinatore (16/10). Cura: un cambio vero dell'indirizzo revoca i link di setup (`_follow_variables`,
  `update_profile`); l'account resta in attesa.
  - `_follow_variables` cambia l'email dell'account in attesa quando cambia `LIBREFOLIO_ADMIN_EMAIL`, ma il link di
    setup già consegnato al vecchio indirizzo resta buono; lo stesso per `user set-email` sull'account in attesa.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A7b-2 — Analisi e
    contratto».
- ✅ **A-34 · `end_sessions` incrementa la copia in memoria: due incrementi concorrenti ne contano uno** — basso;
  chiusa il 17/10 in A8a (commit del coordinatore): `await end_sessions(session, user)`, un `UPDATE … RETURNING` Core
  sulla connessione della sessione più `set_committed_value`; due richieste → +2 (`services session-version`).
  dalla revisione di E («R13-SEC»), tramite il coordinatore (16/10). Valutata in A7b-2 e lasciata: non costa poco
  (`test_session_version.py` ne fissa la forma sincrona, contratto 5; 9 chiamate da rendere asincrone). Con A8.
  - `user_service.end_sessions` fa `user.session_version += 1` sull'oggetto: due richieste quasi simultanee
    scrivono lo stesso valore, e un cookie riemesso fra le due (cambio password) sopravvive alla seconda. Finestra
    sotto il secondo. Cura: l'incremento in SQL (`session_version = session_version + 1`), 9 chiamate.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A7b-2 — Analisi e
    contratto».
- ✅ **A-35 · Una risposta 422 rimanda indietro la password** — medio (sicurezza); chiusa il 17/10 in A7b-2 (commit del
  coordinatore); dal coordinatore (16/10). Cura (D2): `api/validation_errors.py`, `install_validation_error_handler`
  in `main.py`, toglie `input` da ogni errore del 422 di tutta l'app.
  - Il gestore predefinito di FastAPI mette `input` in ogni errore di validazione: un campo troppo corto rimanda il suo
    valore, e un campo **mancante** rimanda tutto il corpo, password e token compresi (provato in processo con
    FastAPI 0.141.1). Vale per login, registrazione, cambio password, reset, setup, profilo, eliminazione dell'account,
    e per le rotte degli altri con segreti nel corpo. Le impostazioni dei plugin lo evitano già con una `route_class`
    propria (`_NoInputEchoRoute` in `api/v1/plugin_settings.py`).
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A7b-2 — Analisi e
    contratto».
- **A-36 · Il Profilo nasconde la password attuale che il server chiede** — basso (UX, nessun aggiramento); dalla
  revisione di E di A-25 («R13-SEC3»), tramite il coordinatore (17/10, 04:54). Dopo A7b-2.
  - `ProfileTab` decide se l'indirizzo cambia sul testo grezzo (`sameEmail` di `features/auth/emailCase.ts`: solo
    A–Z ripiegate); il server confronta il valore già normalizzato da `EmailStr` (spazi, NFC, IDNA) con quello salvato
    (`user_service.same_email`). Dove divergono — spazi, una forma NFD, un dominio internazionale, un indirizzo salvato
    prima della normalizzazione — il server risponde 400 `CURRENT_PASSWORD_REQUIRED` mentre il campo resta nascosto:
    un vicolo cieco. Direzione: il client chiede la password anche quando il 400 arriva (mostrare il campo su quel
    codice), oppure confronta come il server.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A-25».
- **A-37 · Togliere `NoInputEchoRoute` dopo l'ingresso di B4 e di A7b-2** — minimo; dal coordinatore (17/10).
  B4 sposta la `route_class` delle impostazioni dei plugin in `backend/app/api/no_echo.py` (`NoInputEchoRoute`, con
  `test_no_echo_route.py`); il gestore globale di A-35 (`api/validation_errors.py`) la rende un doppione. Quando sono
  dentro entrambi: togliere la classe e il suo uso in `api/v1/plugin_settings.py`, adattare `test_no_echo_route.py`,
  aggiornare `developer/architecture/patterns/plugin_settings.md` (riga sulla classe). Il test di
  `test_plugin_settings_api.py` resta: passa dal server vero. Dettagli: [piano
  02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A7b-2 — Decisioni del coordinatore». 19/10 a
  `6578f1d75`: la usa anche `api/v1/backup/instance.py` (B), quindi toglierla tocca anche B.
- ✅ **A-39 · `admin/configuration`: l'avviso del link scaduto e quello del cambio d'indirizzo** — minimo (doc, con
  traduzioni); chiusa in inglese il 17/10 con A-50 (`6700a04b4`: «expired» quando il link è scaduto, «withdrawn
  (cancelled, or its address changed)» quando è stato annullato o l'indirizzo è cambiato); le traduzioni non hanno
  ancora la sezione dell'admin iniziale (A-10). Dal `docs-writer` di A7b-2, tramite il coordinatore (17/10). La pagina dice che ogni avvio senza un link
  vivo scrive l'avviso di scadenza; dopo A-33 l'avvio che applica un indirizzo nuovo scrive invece «The initial
  administrator's address changed: the setup link handed over before no longer works; …», e quelli dopo l'avviso di
  scadenza. Una frase, e la stessa nelle tre traduzioni. Dettagli: [piano
  02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A7b-2.2».
- ✅ **A-40 · `user activate` sull'admin in attesa avvisa del limite di utenti anche se il suo posto è già contato** —
  chiusa il 17/10 (commit del coordinatore): nessun avviso anche con `is_pending_admin` (IMG-030f);
  minimo; dal `docs-writer` di A7b-2, tramite il coordinatore (17/10); preesistente. A istanza piena il CLI scrive
  l'avviso del limite (che supera), ma l'admin in attesa era già contato fra i posti (D-A10): l'attivazione non ne
  occupa uno nuovo. Cura possibile: nel CLI, nessun avviso quando l'account era in attesa. Dettagli: [piano
  02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A7b-2.2».
- **A-41 · Un limite per indirizzo sui token sbagliati (inspect, setup, reset, invito)** — basso; proposto in A8 (C2) e
  tenuto fuori dal coordinatore (17/10): i token sono lunghi (256 bit) e casuali, la forza bruta non è praticabile, e un
  limite per indirizzo rischia di bloccare utenti dietro lo stesso NAT. Da riprendere solo se compare un motivo nuovo
  (per esempio token più corti). Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md),
  «A8 — Analisi e contratto».
- **A-38 · Il 422 toglie solo `input`: `msg` e `ctx` portano parti del valore dove un validatore lo formatta** — basso;
  dalla revisione di E di A7b-2 («R13-SEC4»), tramite il coordinatore (17/10).
  - Esempi: `schemas/common.py:98` (valuta), `schemas/settings.py:434-459` (orari, giorni, fuso, valuta), `uuid_parsing`.
    Nessuno tocca una credenziale oggi (verificato in A7b-2: `ctx.error` esce vuoto, il valore passa da `msg`).
  - In parte già coperto: `test_validation_errors_api.py` vuole il segnale assente da **tutta** la risposta sulle otto
    rotte con credenziali, ma solo per le forme d'errore che esercita. Cura: una regola in `security.md#validation-errors`
    («un validatore non mette il valore nel messaggio») e, se serve, un test che la imponga per ogni campo segreto.
  - 19/10: `security.md#validation-errors` ora descrive il limite («What it does not remove (backlog A-38)»); mancano
    la regola e il test.
- ✅ **A-42 · Una gara fra un setup e un nuovo link di setup** — basso; chiusa il 17/10 in A-42/A-43 (commit del
  coordinatore); dalla revisione di E di A7b-2 («R13-SEC4»). Cura: `issue_setup_link` e il riarmo revocano prima (un solo
  UPDATE, che prende il lock) e rileggono «in attesa» sotto il lock; `complete_admin_setup` rifiuta (`TOKEN_INVALID`)
  quando un altro link di setup dell'account è consumato, e ritira i suoi link.
  `issue_setup_link` e il riarmo all'avvio decidono «in attesa» da una lettura fatta prima del BEGIN differito: un
  `POST /auth/setup` chiuso in quella finestra lascia un link vivo all'account appena attivato. Cura proposta da E: rifiutare
  il consumo (e il rilascio) quando un altro link di setup dell'account è già consumato.
- ✅ **A-43 · La disattivazione non tocca i link di setup (con A-44: annullare l'admin iniziale)** — basso; chiusa il
  17/10 in A-42/A-43 (commit del coordinatore); dalla revisione di E di A7b-2 («R13-SEC4»); A-44 unita qui dal
  coordinatore (17/10, 03:09). Cura: come sotto; in più la retrocessione dell'admin in attesa è rifiutata (409
  `PENDING_SETUP`, `user demote`), la sua cancellazione diretta è permessa, la scheda Utenti ha «Annulla il link di
  setup», e un account protetto rifiuta anche l'annullamento (la CLI no). Dettagli: [piano
  02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A-42 + A-43 — Implementazione».
  - Disattivare l'admin **in attesa** è l'annullamento: i suoi link si **revocano** (non si ritirano: resta in attesa,
    così `user setup-link`, la via dell'operatore, gli dà ancora un link nuovo; un ritiro lo toglierebbe dall'attesa e
    `setup-link` non lo troverebbe più).
  - Disattivare un account **non** in attesa **ritira** i link di setup che avesse (i database delle build precedenti
    della 1.3, con link vivi su account già attivati).
  - Cambiano per costruzione: UADM-062 e UADM-067 (`{is_active: false}` sull'admin in attesa: resta in attesa, ma il
    link non vale più), le varianti di UADM-069 e SETUP-016 che lo disattivano.
- ✅ **A-44 · L'admin iniziale che non ha mai fatto il setup non si può annullare** — unita ad **A-43** dal coordinatore
  (17/10, 03:09): disattivarlo è l'annullamento. Dettagli delle voci di E: [piano
  02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A7b-2 — Revisione di E».
- ✅ **A-45 · `developer/api/index.md`: `/auth` «token refresh» non esiste** — minimo (doc, solo inglese); chiusa il 17/10
  (commit del coordinatore): la riga elenca le rotte vere; dal
  `docs-writer` di A8a (17/10). La riga del router dice «Authentication (login, token refresh)»: non c'è nessun
  refresh, il cookie dura `session_ttl_hours` (`security.md` «Token Expiration»). Lasciata fuori da A8a perché
  estranea. Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A8a.6».
- ✅ **A-46 · `./dev.py user create` non controlla la lunghezza del nome (3–50)** — minimo; chiusa il 17/10 (commit del
  coordinatore): `user_service._new_username_refusal()` (la `@`, poi 3–50) in `create_user` e `update_profile`
  (UNAME-020…023); dal `docs-writer` di A-21a (17/10). La riga di comando rifiuta la `@` (A-21a) ma non un nome di 2 caratteri o di 60, che la registrazione e il
  profilo rifiutano. Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A-21a.5».
- ✅ **A-47 · `USERNAME_INVALID` riconosciuto dal testo del messaggio** — minimo; chiusa il 17/10 (commit del
  coordinatore): `AccountError` (un `str` con `.code`), i chiamanti guardano il codice (UNAME-030/031, UNAME-API-12);
  dalla revisione di E di A-21a (17/10, LOW). `auth.py` (registrazione via `registration_service`, profilo) sceglie il codice confrontando
  `error == USERNAME_RESERVED_MESSAGE`: un cambio di parole lo romperebbe in silenzio. Meglio un codice restituito da
  `user_service.create_user`/`update_profile`. Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md),
  «A-21a — Revisione di E».
- **A-48 · La pagina offline mostra il caffè anche su un'istanza gestita** — basso; dal `docs-writer` di A9 (17/10).
  `frontend/static/offline.html` (statica, senza l'app) disegna sempre il link «Buy Me a Coffee»: non può sapere il
  profilo. Rimedio possibile: l'app salva il profilo confermato dal server (per esempio in `localStorage`) e la pagina
  offline nasconde il link se è `managed`; il file è della squadra dei colori (copie statiche dei ruoli). Dettagli:
  [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A9.5».
- **A-49 · Un messaggio suo per il 503 `INSTANCE_KEY_UNAVAILABLE` della verifica dell'indirizzo (con E)** — basso,
  dopo la 1.3 salvo che venga facile; dalla revisione di H-19 (A, 17/10; coordinatore). Il dialogo d'invito della scheda
  Utenti (`LinkShare` → `checkAddress()`) lo dice «non verificabile» e il controllo dei link della scheda Email
  (`emailLinks.ts`, di E) «irraggiungibile»: col codice nuovo i due posti possono dire «questa istanza non può
  verificare gli indirizzi: vedi i controlli di configurazione». Condivisa con E. Dettagli:
  [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «Revisione di H-19».
- ✅ **A-50 · Dopo un annullamento, l'avvio dice «scaduto»** — minimo; chiusa il 17/10 (commit del coordinatore), con il
  lotto del helper del profilo; da A-43 (A, 17/10). Cura: `_latest_setup_withdrawn()`; se l'ultimo link di setup è
  revocato e mai consumato, il WARNING dice «…was withdrawn (cancelled, or its address changed)…» (A50-001…004).
  Annullato il link dell'admin in
  attesa, un riavvio con lo **stesso** `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` giustamente non lo riarma (il valore è noto),
  ma `_keep_pending_admin` avvisa «The initial administrator's setup link has expired»: il rimedio è giusto, la causa
  no. Cura: leggere l'ultimo link di setup e dire «cancelled» quando è revocato. Dettagli:
  [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A-43.5».
- ✅ **A-51 · Annullamento e cancellazione dell'admin in attesa decisi da letture prima del lock** — basso (classe A-42);
  chiusa il 17/10 (commit del coordinatore): il PATCH con `cancel_setup` (409 `SETUP_COMPLETED`), `update_user_status`,
  `set_user_active` e `set_user_admin` decidono sotto il lock, la DELETE rilegge sotto il lock (`DEMOTE_FIRST`);
  dalla revisione di E di A-42/A-43 (17/10), tramite il coordinatore; prima della 1.3 (coordinatore, 14:44). Se il setup
  si completa in quel millisecondo l'annullamento è un no-op con un 200 vecchio e la cancellazione toglie l'admin appena
  attivato senza `DEMOTE_FIRST`; in più la scheda annulla con lo stesso corpo di una disattivazione (una riga vecchia
  disattiva il proprietario nuovo), e `user deactivate` può disattivare l'unico admin. Dettagli:
  [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A-51».
- ✅ **A-52 · L'eliminazione di sé conta gli admin attivi prima del lock di scrittura** — basso (classe A-51); chiusa il
  17/10 (commit del coordinatore): `refreshed_under_lock`, poi il conteggio (ACCDEL-LOCK-01…03); A (17/10,
  analisi del lotto A-11/A-16/A-40/A-26). `DELETE /auth/users/me` legge `count_active_superusers()` senza
  `begin_writes`: gli ultimi due admin attivi che si eliminano nello stesso istante passerebbero entrambi, e l'istanza
  resterebbe senza admin. `DELETE /users/{id}` e il PATCH decidono già sotto il lock. Cura: `begin_writes(session,
  User)` e il conteggio ripetuto, rosso prima. Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «Lotto A-11/A-16/A-40/A-26».
- ✅ **A-53 · `developer/api/curl-testing.md`: l'esempio «Update preferences» usa una rotta che non esiste** — minimo;
  chiusa il 17/10 (commit del coordinatore): l'esempio usa `GET` e `PUT /api/v1/settings/user`. Doc; dal `docs-writer` del lotto A-11/A-16/A-40 (17/10). `PATCH /api/v1/auth/users/me/preferences` con
  `{language, currency}`: le preferenze sono `PUT /api/v1/settings/user` (`language`, `base_currency`, `theme`,
  `avatar_url`). Pagina solo EN.
- ✅ **A-54 · Un account cancellato da un altro admin nella stessa finestra risponde 500, non 404** — basso (classe A-51);
  chiusa il 17/10 (commit del coordinatore): `user_service.refreshed_under_lock` nei quattro punti e, approvate dal
  coordinatore, in tre rotte con lo stesso difetto (link di reset, revoca delle sessioni, reset dell'onboarding): il 404
  di `_user_or_404` (la stringa nuda: decisione del coordinatore), «User 'x' not found» nella CLI (UADM-LOCK-01/02/10–12, LOCK-CLI-01, ACCDEL-LOCK-03);
  dalla revisione di E di A-51 (17/10), tramite il coordinatore. Dopo `begin_writes`, `session.refresh(user)` solleva
  `InvalidRequestError` su una riga appena cancellata (prima era `StaleDataError`, sempre un 500), in quattro punti:
  `update_user_status` (PATCH), `set_user_active` e `set_user_admin` (CLI), il ramo «in attesa» di `DELETE /users/{id}`.
  Cura: un aiuto che la intercetta, fa rollback e risponde il 404 di `_user_or_404` (con `USER_NOT_FOUND`: da decidere),
  nella CLI «User 'x' not found». Proposta nel lotto «decidere sotto il lock» (A-52, A-54, A-55, A-56).
- ✅ **A-55 · `DELETE /users/{id}` rilegge sotto il lock solo l'admin in attesa** — basso; chiusa il 17/10 (commit del
  coordinatore): ogni cancellazione decide sotto il lock (UADM-LOCK-03); da E (17/10), come A-54. Un
  account promosso da un altro admin nella finestra viene cancellato senza `DEMOTE_FIRST` (non può togliere l'ultimo
  admin attivo: chi cancella lo è). Cura: rileggere sotto il lock per ogni cancellazione.
- ✅ **A-56 · Il limite di utenti si conta prima del lock** — basso (conta per i limiti dei piani); chiusa il 17/10
  (commit del coordinatore): la riattivazione del PATCH e `create_invite` contano dopo `begin_writes` (UADM-LOCK-04/05);
  da E (17/10, la
  riattivazione, preesistente), e da A la creazione degli inviti. Il PATCH guarda `usage.full` prima di
  `update_user_status`, `create_invite` conta prima di ogni scrittura: due operazioni concorrenti a limite − 1 lo
  superano di uno. La registrazione è già sicura: riconta dopo la sua scrittura, sotto il lock. Cura: contare dopo
  `begin_writes`.
- ✅ **A-57 · `legal-and-managed.spec.ts`: LGM-E-01 e LGM-E-03 devono leggere il profilo della corsia** — basso, solo test;
  chiusa il 19/10 (commit del coordinatore): i due test leggono prima la risposta della corsia e verificano la sua
  variante; verde su una corsia self-hosted e su una gestita (5/5 e 5/5). Il ritorno in `CLOUD_SMOKE_SPECS` è di H;
  in 1.3, prima della fase 2 di H-43 (il cancello RC di H); dal coordinatore (17/10, da H-43, dev `a6adb0066`, la corsia
  di prova gestita). I due casi danno per scontata la variante self-hosted: su una corsia gestita falliscono per
  costruzione. Cura: leggere `GET /api/v1/system/instance` della corsia e verificare la variante corrispondente; poi H
  rimette la spec in `CLOUD_SMOKE_SPECS`. Dopo il lotto in corso.
  - Sospesa dal developer il 19/10 mattina, poi il suo «ok» (11:42). Analisi e prova 1 il 17/10 (su una corsia
    gestita LGM-E-01/03 rossi, gli altri verdi); spec riscritta e verde il 19/10, insieme alla frase sulle pre-release
    in `developer/frontend/onboarding.md` (nota 2 di E su C-54). Dettagli: [piano
    02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A-57» e «A57.1»–«A57.4».
- **A-58 · Con `connect-src 'self'` imposto, la verifica dell'indirizzo di un link verso un'altra origine è bloccata** —
  basso, UX; dopo la 1.3, la metà UX di H-53; dal coordinatore (17/10). Il dialogo d'invito della scheda Utenti
  (`LinkShare` → `checkAddress()`) oggi dice «non verificabile»: decidere cosa vede l'admin. Decisione aperta.
  - Dal coordinatore (17/10, 21:35): H prepara `LIBREFOLIO_CSP_ENFORCE` (spento di default; `connect-src` solo
    `'self'` e l'origine di `LIBREFOLIO_PUBLIC_URL`). Quando H manda la politica esatta, A rivede anche le attese di
    AUSR-E-07 (`e2e/settings/admin-users.spec.ts`), che prova apposta altre origini http, su una corsia che la
    applica.
- ✅ **A-CL1 · Il changelog aperto da Impostazioni › Informazioni resta «in caricamento»** — basso, UX; chiusa il 19/10
  (commit del coordinatore): una finestra sola per tutta l'app, quella della Sidebar, aperta dalle due versioni tramite
  `changelogModalStore.svelte.ts`; la cache delle traduzioni è una `SvelteMap`. Visto dal developer sulla nightly
  (`v1.2.1-2591-g5e1a7c3af`), tramite il coordinatore (19/10). La finestra chiusa mentre la traduzione caricava
  scartava il risultato, e alla riapertura leggeva una cache non reattiva. Verde con Vitest (M1, M2, About, Sidebar
  1–4) e con l'E2E E1/E2 di `changelog-locale.spec.ts`, rosso prima della cura. Dettagli: [piano
  02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A-CL1» e «CL1.1»–«CL1.7».
- **A-59 · Il ramo in sola lettura di `GlobalSettingsTab` non si raggiunge più** — minimo, pulizia; A, 20/10 (N69a).
  Da N69-2 la scheda è solo degli admin, quindi `canEdit` è sempre vero sullo schermo. Il ramo in sola lettura
  (`settings-readonly-indicator`, i controlli disattivati, le `props` `{canEdit}` del registro) e i suoi test restano
  per ora. Cura: toglierli insieme, con la doc per sviluppatori di `GlobalSettingsTab`. Dettagli: [piano
  02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «N69 — L'amministrazione: via al lotto».
- **A-60 · Due altri cerchi d'avatar non usano `UserAvatar`** — minimo, fattorizzazione; A, 20/10 (N69a).
  - Hanno ognuno la sua copia di `getAvatarInitial`: `components/ui/select/UserSearchSelect.svelte` (i selettori
    di utenti) e `features/brokers/BrokerSharingPanel.svelte` (iniziali ambra su classi di palette, del programma
    colori).
  - `UserAvatar` (N69-4) ha lo schema dei selettori: `bg-lf-neutral` con `text-lf-muted`, per condizione del
    programma colori (19/10).
  - Quella coppia non è fra quelle che il cancello del contrasto misura (regola 5 della skill `design-system`: un
    testo su `neutral` non è promesso). La decide il programma colori.
  - Cura: i due cerchi passano a `UserAvatar`, con i loro proprietari. Dettagli: [piano
    02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «N69a.3».
- **A-61 · Lo store dei controlli di sicurezza non si azzera al cambio d'account** — basso; A, 20/10 (N69b).
  - `securityChecks` (`features/settings/security/securityChecks.svelte.ts`, da A8b) non registra un
    `registerClientSessionReset`: dopo un'uscita e un altro accesso nella stessa scheda tiene la risposta di prima.
  - Cosa si vede: niente di sbagliato. I componenti filtrano per ruolo, quindi un membro non vede né il puntino né
    il conto; un altro admin vede i controlli dell'istanza, che sono gli stessi, ma letti prima, fino a «Controlla
    di nuovo» o a un ricaricamento.
  - Da N69b lo store si riempie su ogni pagina di un admin, non più solo in Impostazioni.
  - Cura: un reset alla transizione della sessione (`checks`, `answered`, `status`), con il suo test. Dettagli: [piano
    02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «N69b.1».
- **A-62 · Il nome accessibile del pulsante del menu è in inglese in ogni lingua** — basso, a11y; A, 20/10 (N69b;
  visto in F2.2).
  - `Header.svelte`: «Toggle menu» è scritto a mano dal piano 36. Da N69b il nome aggiunge, dopo «—», il livello della
    connessione e il conto degli avvisi nella lingua dell'utente, quindi in italiano diventa per esempio «Toggle menu
    — 2 avvisi di sicurezza».
  - Nel catalogo non c'è una chiave per il menu.
  - Cura (chiesta al coordinatore nel checkpoint di N69b): una chiave nuova nelle 4 lingue e l'asserzione di
    `Header.test.ts`. Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «F2.2».

## X · Plugin, asset e ricerca (fase 01)

Piano: [`03_pluginsAssets`](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md).

- ✅ **Voce 5 di `TODO_ProssimeAttivita` · Link alle transazioni nella modale di cancellazione dell'asset** — chiusa da X il
  14/10 senza codice: già fatta il 10/09 in `e50d66408` (conteggio e link nella cancellazione singola e in quella multipla,
  `FAAssetDeleteResult.transaction_count`, E2E in `e2e/assets/asset-list.spec.ts`); nella devWiki F-095 era già
  `documented`, e `domains/assets.md` non la elenca più fra le cose da fare. Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «2.5».
- ✅ **X-R1 · Il percorso di `normalize_rate_for_storage` nella descrizione di un endpoint dei cambi** — minimo; X, 14/10 (CP1,
  CP3). La docstring di `create_routes_bulk` (oggi `api/v1/fx/providers.py:183`) cita ancora «``services/fx.py``»; la
  funzione sta in `services/fx/storage.py` dal CP3. Il testo è nella descrizione dell'endpoint in `openapi.json`, e il PL4 è
  un riordino a `openapi.json` invariato: come X-R2, si corregge in un lotto che cambia comunque l'API (il CP6, F05, o
  prima). **Chiusa il 15/10**, con X-R2, in un commit sopra X-R11a che entra con FE5b; `openapi.json` cambia solo nelle tre
  descrizioni. Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «15», CP1, CP3
  e X-R1 + X-R2.
- ✅ **X-R2 · I vecchi percorsi degli asset in due descrizioni di schemi dell'API** — minimo; X, 15/10 (CP2a, CP2b). Le
  docstring di `BackwardFillInfo` (`schemas/common.py:369`) e di `IdentifierType` (`db/models.py:117` e `:123`) citano ancora
  `schemas/assets.py` (diventato `schemas/assets/assets.py` nel CP2b) e `asset_source.py` (tolto nel CP2a). Il testo finisce
  in `openapi.json`: resta fino a un lotto che cambia comunque l'API (il CP6, F05, o prima). Nella stessa docstring di
  `db/models.py`, la riga `:127` cita `services/brim_provider.py`, spostato da W (W4 CP6) in `services/brim/`: per la stessa
  ragione resta, e si corregge insieme alle altre (aggiunta il 15/10, validazione di `d1ef3ddeb`). **Chiusa il 15/10** con
  X-R1; nella stessa docstring anche il passo 1, che mandava la colonna nuova in `001_initial.py` contro la regola delle
  migrazioni incrementali. Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione
  «15», CP2a, CP2b e X-R1 + X-R2.
- ✅ **X-R3 · Tre commenti del frontend citano il modulo degli asset tolto** — minimo; X, 15/10 (CP2b, validazione di
  `eb245b624`). `AssetModal.svelte:1507` e `:1636` attribuiscono ad `asset_source.py` le cancellazioni di prezzi ed eventi
  generati (oggi in `services/assets/provider_management.py`, `bulk_assign_providers`), e `assetPayload.test.ts:58` la fusione
  per campo della classificazione (oggi in `services/assets/crud.py`, `patch_assets_bulk`). Fuori dal perimetro dei lotti
  del backend: si corregge nel FE5, con il taglio di `AssetModal`. **Chiusa nel FE5b-1 il 15/10**: i due commenti di
  `AssetModal` puntano a `services/assets/provider_management.py`, quello di `assetPayload.test.ts:58` a
  `services/assets/crud.py`. Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md),
  sezione «15», CP2b e FE5b.
- **X-R4 · Il diagramma della guida dei plugin FX attribuisce al servizio la divisione per le valute multi-unità** —
  minimo, doc; segnalato da docs-writer il 15/10 (CP3). In `mkdocs_src/docs/developer/architecture/patterns/fx_plugin_guide.md`
  un riquadro Mermaid dice «Service normalizes … Multi-unit ÷100»; la stessa pagina dice che la divisione la fa il plugin, e
  nessun codice di `services/fx/` la fa (`base.py` dichiara solo la proprietà `multi_unit_currencies`). Preesistente al
  riordino. Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «15», CP3.
- ✅ **X-R5 · Commenti e docstring con i percorsi tolti da CP2a, CP2b e CP3** — minimo; X, 15/10 (validazione di
  `d1ef3ddeb`). Un grep più largo di quelli dei lotti (nomi di file nudi, nomi puntati dentro le docstring, il frontend e
  `TODO_FUTURI.md`) trova 16 righe che citano un percorso che non c'è più; erano tutte già nel mio ramo prima del merge
  (nessuna arriva dalle altre sessioni). Solo testo: nessuna è in `openapi.json` né cambia comportamento.
  - Backend: `asset_source_providers/scheduled_investment/plugin.py:33-34` (`schemas.assets.FA…` → `schemas.assets.assets`,
    CP2b); `services/assets/core.py:15` («fx.py» → `services/fx/`, CP3); `test_api/test_fx_compress_errors.py:1` (→
    `api/v1/fx/currencies.py`, CP3); `test_services/test_fx_core.py:5` (→ `services/fx/storage.py` e `sync.py`, CP3).
  - Frontend: `e2e/assets/asset-modal.spec.ts:526` («asset_source.py» → `services/assets/provider_management.py`, CP2a);
    `e2e/fixtures/galleryOfflineData.ts:62` (→ `api/v1/fx/providers.py`, CP3); `e2e/fixtures/galleryProviderCompare.ts:40`
    e `galleryReportSets.ts:398` («asset_sources/search.py» → `services/assets/search.py`, CP2a);
    `components/assets/ScheduledInvestmentEditor.svelte:75`, `:81`, `:89` (→ `schemas/assets/assets.py`, CP2b);
    `stores/app/auth.test.ts:574` (→ `api/v1/assets/crud.py`, CP2b); `stores/reference/fxRoutesStore.test.ts:8` («fx.py» →
    `services/fx/sync.py`, `sync_pairs_bulk`, CP3).
  - `TODO_FUTURI.md:1121` (→ `schemas/assets/assets.py`) e `:2067` (→ `services/assets/price_query.py:149`).
  Decisione del coordinatore (15/10): nel lotto CP3b, compresi `auth.test.ts:574` (lo avvisa lui ad A) e le 2 righe di
  `TODO_FUTURI.md`; restano fuori i due commenti di `AssetModal` (X-R3, FE5) e le 3 fixture della galleria, che sono di G e
  il coordinatore gira al coordinatore colori. **Chiusa nel CP3b il 15/10** per le 13 righe del perimetro deciso; i due
  commenti di `AssetModal` restano in X-R3, le 3 fixture sono passate a G. Dettagli:
  [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «15», quinto aggiornamento di base e CP3b.
- ✅ **X-R6 · `web_link_finder`: timeout e numero massimo di URL non validati** — piccolo; segnalato da H il 15/10 (lotto
  `web_link_finder`), girato a X dal coordinatore. Preesistente e invariato dagli spostamenti. `config/plugins.py:46-52`
  accetta `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` a `nan` o `inf` (`float()`), e `services/assets/web_link_finder.py:108`
  (`DDGS(timeout=int(timeout) or None)`) allora solleva: la ricerca rende `[]` scrivendo solo un debug (`:244-245`); un
  timeout sotto 1 diventa `int(…) == 0`, cioè nessun timeout; con `LIBREFOLIO_WEB_LINK_FINDER_MAX=0` il controllo di
  `:259` arriva dopo il primo `append`, e torna comunque un URL. Cura: valori finiti e ≥ 1 negli accessori di
  `config/plugins.py` (file di H: d'accordo con H) e un timeout non intero rispettato; con il CP6 (F05) o il CP10, che
  toccano la configurazione dei plugin. **Chiusa nel CP10 il 15/10** (commit al checkpoint del CP10): i due accessori di
  `config/plugins.py` danno il default per un valore non finito o sotto 1, `DDGS(timeout=math.ceil(timeout))` rispetta un
  timeout non intero, `.env.example` e la docstring dicono «at least 1»; i sei casi di `test_config_package.py` che
  fissavano il vecchio comportamento aggiornati. Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md),
  sezione «15», quinto aggiornamento di base, e sezione «CP10», passo 8.
- ✅ **X-R7 · La pagina di Borsa Italiana elenca le variabili del `web_link_finder` senza `_FILE`** — minimo, doc; segnalato
  da H il 15/10. `mkdocs_src/docs/developer/backend/assets/provider_borsa_italiana.md:123` cita `_API_KEY` ma non
  `_API_KEY_FILE` (segreti Docker, `env_secret()`); la fonte di verità è `search_link_finder.md`: la riga va ridotta a un
  rimando. **Chiusa nel CP3b il 15/10** (docs-writer): la riga rimanda a `search_link_finder.md#configuration-env-vars-all-optional`.
  Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «15», CP3b.
- ✅ **X-R8 · `GET /fx/providers` chiede alla BCE l'elenco delle valute a ogni richiesta** — piccolo, prodotto; X, 15/10
  (preparazione del CP3b). `list_providers` (`api/v1/fx/providers.py:97-101`) chiama `get_supported_currencies` di ogni
  fornitore pubblico; quello della BCE (`fx_providers/ecb/plugin.py:95`) fa una richiesta HTTP senza cache, con 30 s di
  timeout: ogni apertura dell'elenco aspetta la BCE, e senza rete la BCE compare con zero valute (l'errore resta nel log).
  Lo stesso vale per la SNB finché non riesce una volta nel processo (`fx_providers/snb/plugin.py:139-149`,
  `_ensure_currency_map`, data.snb.ch, 15 s): trovato nel CP3b.
  Il CP3b toglie la rete dai test che controllano le valute; le chiamate senza filtro (elenco completo, `MANUAL` nascosto)
  restano, e sul server vanno comunque alla BCE. Proposta del coordinatore (15/10; il developer può cambiarla): una cache
  dell'elenco delle valute dei fornitori, valida 24 ore; se la BCE non risponde si usa l'ultimo elenco noto, con un timeout
  breve. In un lotto di X dopo il CP3b. **Chiusa da X il 15/10**: `services/fx/catalog.py`,
  `get_supported_currencies_cached`, usato da `list_providers`: cache con nome `fx_provider_currencies` (24 h, nel pannello
  delle cache), timeout di 5 s, l'ultimo elenco noto quando il fornitore fallisce, riprovato dopo 5 minuti; una sola
  richiesta per fornitore con chiamate simultanee. API e `openapi.json` invariati; 8 test senza rete
  (`services fx-catalog`). In `dev_release2` con `173ba19e2` (X-R8 `1dfd4e657`). Dettagli:
  [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «15», quinto aggiornamento di base e X-R8.
- **X-R10 · Commenti e pagine dei cambi un po' più ottimisti del codice** — minimo, doc; X, 15/10 (X-R8, segnalate da
  docs-writer). Preesistenti, nessuna cambia comportamento:
  - `frontend/src/lib/stores/currencyGraphStore.ts`: il commento dice che le risposte sono «stable» e che la cache
    «can never go stale»; con la cache di 24 h l'elenco di un fornitore può cambiare durante la sessione (e prima poteva
    arrivare vuoto e poi pieno);
  - `mkdocs_src/docs/developer/frontend/fx-chain-algorithm.md`: l'esempio sopra il paragrafo «Why this works» usa
    `getOrBuildGraph()`, `fetchProviders()`, `fetchCurrencies()`; lo store vero ha `getCurrencyGraph()`, una
    `buildPromise` condivisa ed `ensureCurrenciesLoaded()`;
  - `fx_plugin_guide.md`: «Phase 1 happens when a user adds a new currency pair» è più stretto del vero (il frontend chiama
    `/fx/providers` una volta per sessione, alla prima vista che usa il grafo, e a ogni apertura della scheda About);
  - `settings_cache.md`: le cache «register lazily at import time», ma `yfinance_currency` si registra alla creazione
    del plugin.
  - la docstring di `create_routes_bulk` (`api/v1/fx/providers.py:180`) cita ancora `services/fx.py`, che dopo il CP3 è
    `services/fx/` (la normalizzazione sta in `storage.py`): segnalata dal coordinatore il 15/10, è la stessa riga di
    **X-R1**, aperta dal CP1; resta lì, perché il testo finisce nella descrizione dell'endpoint in `openapi.json`.
    ✅ Chiusa il 15/10 con X-R1.
  Proposta: con il FE4 (frontend dei cambi). Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md),
  sezione «15», X-R8.
- ✅ **W-B9 · Un test dei cambi chiama dal vivo la BCE** — piccolo; trovato da W, assegnato a X dal coordinatore il 15/10.
  `test_api/test_fx_api.py::test_providers_include_target_currencies` passa da `GET /fx/providers`, che chiama dal vivo
  `get_supported_currencies` di `fx_providers/ecb/plugin.py`; su un errore di rete il gestore in `api/v1/fx/providers.py`
  (`list_providers`, righe ~97-101 dal CP3) rende una lista vuota. Va contro la regola dei test senza rete. Non nel CP3,
  che è un riordino puro (`openapi.json` e test invariati): lotto di solo test CP3b, approvato dal coordinatore il 15/10,
  dopo l'ingresso del CP3 e prima del CP4. **Chiusa nel CP3b il 15/10**: contratto e filtri su FED e BOE, le chiamate senza
  filtro controllano solo i codici; `api fx` senza rete 21/21 (prima 19/21). La SNB è rimasta fuori perché scarica anche
  lei il suo elenco (scostamento dalla decisione, confermato dal coordinatore il 15/10). Dettagli:
  [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «15», CP2a, CP3 e CP3b.
- ✅ **W-B13 · `fx-csv-import.spec.ts` prende la ✕ della modale d'importazione per testo** — minimo, test; trovato da W
  il 15/10 (K1), assegnato a X dal coordinatore. `frontend/e2e/fx/fx-csv-import.spec.ts:247` e `:276` usano
  `button[aria-label="Close"]`; con P-15 l'etichetta viene da `common.close`, quindi il selettore regge solo in
  inglese. Cura: il `data-testid` `data-import-modal-close`, aggiunto in K1; nel lotto CP3b, con W-B9. **Chiusa nel CP3b il
  15/10** (`front-fx fx-csv-import` 21/21). Dettagli: piano 04, §12, K1 passo 4; piano 03, sezione «15», CP3b.
- **X-R9 · `fx-csv-import.spec.ts`: altri quattro selettori validi solo in inglese** — minimo, test; X, 15/10 (CP3b,
  segnalato da test-author). Oltre alla ✕ di W-B13: `:233` controlla il testo tradotto dell'errore
  (`toHaveText("Header currencies don't match")` su `fx-import-header-mismatch-error`: basta la visibilità), `:234` prende il
  pulsante con `hasText: 'Import (1)'` (c'è già `data-import-confirm`), `:250` cerca `text=Discard import` e `:261` il
  pulsante `hasText: 'Cancel'`. Per questi ultimi due `DataImportModal.svelte` non ha test-id: il `ConfirmModal` di `:305`
  accetta `testId` ma non lo riceve, e il pulsante Annulla di `:287` non ne ha. Cura: due test-id nel componente (condiviso,
  toccato da W in K1) e le quattro righe della spec. Deciso dal coordinatore il 15/10: con il FE4; i due test-id li chiede
  lui a W, proprietario di `DataImportModal.svelte`. **15/10, i due test-id ci sono** (W E0, `d226bc69e`):
  `data-import-cancel` e `data-import-discard-confirm`. Restano a X le quattro righe della spec, con il FE4.
  Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «15», CP3b.
- **X-R11 · `AssetModal`: stranezze preesistenti viste dai test di FE5b-2** — minimo; X, 15/10 (FE5b-2, segnalate da
  test-author). Copiate fedelmente nei moduli puri, nessuna cambiata:
  - ✅ la riga della descrizione nel dialogo di confronto ha l'etichetta fissa `'Description'`
    (`assetMetadataComparison.ts`), e `ProviderComparisonModal` la mostra com'è: in IT ed ES resta in inglese. Cura di
    poche righe: `common.description` c'è già nei quattro cataloghi, basta un'etichetta in più in `ComparisonLabels`.
    **Chiusa il 15/10** (X-R11a): in un commit a parte sopra FE5b-2, deciso dal coordinatore; entra con FE5b; test
    rosso prima (3 su 61);
  - `searchResultIdentifier` controlla che l'identificativo non sia vuoto prima di togliere gli spazi: uno di soli spazi
    diventa una riga vuota, o un conflitto con un codice vuoto;
  - `withElectedPrimary` chiama `.trim()` sui valori OTHER senza convertirli in stringa (`mergeOtherIdentifierValues` li
    converte);
  - `mergeOtherIdentifierValues` scarta solo `null` e `undefined`: `false` o un oggetto diventano righe `'false'` o
    `'[object Object]'`;
  - un `{currency: null}` nei parametri del fornitore blocca la valuta del risultato di ricerca (conta solo la chiave).
  Proposta: le quattro rimaste con il FE5a. Dettagli:
  [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «15», FE5b-2 e X-R11a.

- ✅ **J-5 · Un thread dell'executor resta con un loop chiuso come loop corrente** — basso, robustezza; trovata da J il
  15/10 (C-93), assegnata a X dal coordinatore. `services/assets/core.py:114-119` (`_sync_runner`, dentro
  `asyncio.to_thread`) imposta un loop nuovo, lo chiude e non lo toglie: chi poi, nello stesso thread, chiama
  `asyncio.get_event_loop()` riceve un loop chiuso. È il contesto in cui una connessione aiosqlite raccolta dal GC
  muore con «Event loop is closed». Cura di una riga: `asyncio.set_event_loop(None)` nel `finally`, oppure
  `asyncio.Runner`; un lotto piccolo con un test, dopo il CP4. Dettagli: piano J, §10 «C-93», «Triage». **Chiusa da X il
  15/10**: `asyncio.set_event_loop(None)` nel `finally` di `_sync_runner`, prima di `loop.close()`, come
  `asyncio.Runner.close()`; test `test_provider_core_cache.py::TestRunProviderInThread::test_worker_thread_does_not_keep_closed_event_loop`,
  rosso prima della riga e verde dopo (`7794e2fb0`, in `dev_release2` con `743fca514`). Dettagli:
  [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «15», J-5.

- **X-R12 · Un evento del fornitore datato oggi arriva solo il giorno dopo** — piccolo, prodotto; trovata da W in E1b,
  girata a X dal coordinatore il 15/10, valutata da X lo stesso giorno, fuori dal CP10. Il refresh chiede la storia fino
  a ieri (`services/assets/refresh.py:227`, `history_end = today - 1` quando `end >= today`), e gli eventi arrivano
  solo con la storia: un dividendo o uno split con la data di oggi entra il giorno dopo.
  - **Perché c'è il taglio**: protegge i prezzi. La chiusura di oggi non c'è ancora, e il valore di oggi arriva da
    `get_current_value`.
  - **Gli eventi non hanno questa ragione**: una data di stacco annunciata è un fatto. Restano legati al taglio solo
    perché viaggiano nella stessa chiamata.
  - **Effetto**: nessun errore di valore. Uno split sposta le posizioni solo con la transazione ADJUSTMENT legata
    all'evento (`portfolio/engine.py:213-223`). Ritarda di un giorno la comparsa dell'evento, il suo collegamento da una
    transazione e i dati di AI Export.
  - **Cura proposta**: chiedere la storia fino a oggi e scartare il prezzo di oggi prima della cache e della scrittura,
    tenendo gli eventi fino a oggi. Va rivisto il calcolo della copertura della cache (`dates`), che non deve contare
    oggi. Va verificato per ogni plugin che `end_date` sia inclusivo, e con `scheduled_investment`, che i punti futuri
    li genera da sé.
  - Un lotto con un test di regressione su `mockprov`, dopo X1–X8, che toccano lo stesso percorso.
  Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «CP10», nota su X-R12.
  ✅ **Chiusa da X il 16/10**:
  - la chiamata della storia finisce oggi;
  - i prezzi della storia dopo ieri restano fuori dalla cache e dai prezzi, così il prezzo di oggi resta il valore
    corrente;
  - gli eventi fino a oggi restano;
  - con un buco nella cache, la chiamata va fino a oggi.

  Sei test di regressione in `test_asset_source_refresh.py`, tre dei quali rossi sul codice di prima. Non su `mockprov`
  ma su un fornitore finto in processo, che restituisce gli eventi solo dentro l'intervallo chiesto. Commit del
  coordinatore, lotto X-R12. Decisione notturna N17 sul costo di justETF. Dettagli: piano 03, sezione «X-R12».
- ✅ **X-R13 · La pagina dell'asset calcola ancora `emoji` per il grafico dei settori** (chiusa il 16/10 con il FE5c-1:
  `9b58867eb`, entrata in dev `92a0d4daf`) — minimo, frontend; dal programma
  colori (DV-3, innocua), girata a X dal coordinatore il 15/10. Con DV il campo `emoji` di `AllocationEntry` sparisce,
  ma `routes/(app)/assets/[id]/+page.svelte:3496` (su `dev_release2`, il `map` dei dati di `AllocationPieChart` per i
  settori) lo calcola ancora: un dato morto, che `front check` non vede. Da togliere nel FE5c, col taglio della pagina.
  Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «CP10», note della sera.
  ✅ **Chiusa da X il 16/10**, primo pezzo del FE5c: tolti il campo e l'import, e `front check` passa a 0 errori.
  Commit del coordinatore, lotto FE5c-1. Dettagli: piano 03, sezione «FE5c-1».
- **X-R14 · La pagina di dettaglio dei cambi tiene copie degli helper dei segnali** — minimo, frontend; X, 16/10 (FE5c-2).
  `fx/[pair]/+page.svelte` ha copie identiche di `parseBackendSignalResults`, `signalDataContextFingerprint` e
  `comparisonAssetIds`, che il FE5c ha portato in `lib/charts/chartPageSignals.ts` (N18). E `toSlug` di
  `assetDetailFxRequirements.ts` è una copia di `createPairSlug` (`fxStoreRegistry.ts`), che però rende maiuscolo.
  Da adottare e unificare nel FE4 (CP7). Dettagli: piano 03, sezione «FE5c-2» e «FE5c-6».
- ✅ **X-R15 · Due testi inglesi fissi nella pagina dell'asset** (chiusa il 17/10, `e890e6772`, entrata in dev `16e837153`: «Provider» riusa `common.provider`, «Manual» è `assetDetail.manualChip`) — minimo, i18n; X, 16/10 (FE5c-3, FE5c-5). «Provider»
  (il titolo della fonte nel pannello dei metadati) e «✏️ Manual» (il chip dell'intestazione) non passano dal
  catalogo. Il FE5c li sposta così come sono, in `AssetDetailMetadataPanel` e in `AssetDetailHeader`: due chiavi in
  `assets` dopo il taglio, come O-8. Dettagli: piano 03, sezione «FE5c-3/4/5».
- ✅ **X-R16 · Un segnale non valido salta la cache dei prezzi della pagina dell'asset** (chiusa il 19/10, in attesa del
  commit del coordinatore: un segnale non valido fa fallire solo i segnali, sulle due pagine; su quella di una coppia la
  conversione si legge con l'isolamento dei segnali, e i tassi restano; si lega a N64; piano 03, «X-R16 ripresa») —
  basso, frontend; X, 16/10
  (test-author del FE5c-2). In `loadChartData`, `parseBackendSignalResults` rifiuta tutta la risposta se un solo
  segnale non è valido. Questa parte è voluta: nessun segnale del backend viene mostrato, e `signalRequestFailed` lo
  dice.
  - **Il difetto**: il `throw` salta anche la scrittura dei prezzi nella cache e `resolveMaxStartFromChartData()`.
    Con «Tutto», l'inizio dell'intervallo non si risolve, e i prezzi già arrivati non entrano nella cache.
  - **Cura**: leggere i segnali dopo la cache e la risoluzione, o catturare l'errore solo attorno ai segnali. Con un
    test di componente o E2E che instrada un segnale non valido.
  - Fuori dal FE5c, che sposta il codice senza cambiarlo. Dettagli: piano 03, sezione «FE5c-2».
- ✅ **X-R17 · La conferma di cancellazione di un asset non nomina i suoi eventi** (chiusa il 17/10, `e890e6772`, entrata in dev `16e837153`: `confirmWarning` e `bulkConfirmMessage` nominano gli eventi, con il plurale e due refusi corretti) — basso, UX; dal test-author di
  W-B42 (lettura), girata a X dal coordinatore il 16/10. La descrizione della conferma singola
  (`routes/(app)/assets/+page.svelte:1808`, `assets.delete.confirmWarning`) dice «Provider assignments and price history
  will be removed», ma anche gli eventi (dividendi, split) se ne vanno in cascata. Cura: una frase nella chiave in 4
  lingue, e lo stesso nella conferma multipla. Dopo il FE5c.
- ✅ **X-R18 · Una transazione blocca la cancellazione solo dopo la conferma** (chiusa il 17/10, `e890e6772`, entrata in dev `16e837153`: la conferma singola si apre già bloccata, con il link, quando il `tx_count` della riga è sopra 0) — basso, UX; stessa origine.
  `confirmDeleteAsset` (`:925`) chiama il DELETE e solo allora riceve `HAS_TRANSACTIONS`, con il conteggio e il link
  alle transazioni; la multipla fa lo stesso (`:995`). L'utente conferma una cosa che non può succedere. Cura: usare il
  `tx_count` della riga della lista (`:554`) per aprire la conferma già bloccata, con il link. È solo un'indicazione,
  perché può contare solo le transazioni visibili all'utente, e il controllo del backend resta quello che decide. Dopo
  il FE5c.
- ✅ **X-R19 · «N assets» in inglese fisso nella conferma multipla** (chiusa il 17/10, `e890e6772`, entrata in dev `16e837153`: `assets.delete.itemsLabel`, un plurale) — minimo, i18n; stessa origine.
  `itemsLabel={\`${deletingAssets.length} assets\`}` (`:1826`). Cura: una chiave con il plurale in `assets.delete`, 4
  lingue. Dopo il FE5c.
- ✅ **X-R20 · Il cestino della card e la conferma singola senza `data-testid`** (chiusa il 17/10, `e890e6772`, entrata in dev `16e837153`: `asset-card-delete-btn`, `asset-delete-confirm`, `asset-bulk-delete-confirm`; le E2E li usano) — minimo, test; stessa origine.
  Il bottone del cestino di `AssetCard.svelte:318` non ha `data-testid`, e la `ConfirmModal` singola (`:1805`) non
  passa `testId` (la multipla nemmeno). Cura: `asset-card-delete-btn` e `testId` sulle due conferme, poi le E2E che
  oggi passano dal testo o dalla posizione. Dopo il FE5c.
- **X-R21 · `fxRoutesStore.test.ts` va in timeout sotto carico, e il secondo caso eredita il primo** — basso, test; X,
  16/10 (triage durante la verifica della base `fa97791f6`).
  - **Il caso**: in `core-unit`, con la macchina a carico ~100, il file ha impiegato 7,5 s. Il primo caso è andato in
    timeout ai 5 s di default di Vitest; il secondo ha fallito con «`listRoutes` chiamata 2 volte». Da solo il file
    passa in 2,1 s, e il primo caso impiega 437 ms.
  - **Verdetto del triage: assunzione (il tempo)**. Ogni caso fa `vi.resetModules()` e poi un `import()` a freddo di
    `fxRoutesStore`, che si porta dietro tutto il grafo di `fxStoreRegistry`, dentro i 5 s di default.
  - **La cascata**: il caricamento rimasto in sospeso chiama il mock condiviso (`vi.hoisted`) durante il caso
    successivo.
  - **Cura, solo nel test**:
    - scaldare il grafo una volta sola, in un `beforeAll` con un timeout ampio, prima dei `resetModules`;
    - dare a ogni caso il suo mock, così un timeout non si propaga.
  - Mio, perché è nell'area del FE4. Dettagli: piano 03, sezione «CP13».
  ✅ **Chiusa da X il 16/10**:
  - un mock nuovo per caso, installato con `vi.doMock`, così una lettura in sospeso non viene contata nel caso dopo;
  - il grafo dello store si scalda una volta in `beforeAll`;
  - `afterEach` aspetta `vi.dynamicImportSettled()`, alla sua prima volta nel repo.
  - Il file da solo dà 5/5, e il primo caso passa da 437 a 57 ms; `core-unit` è verde.
  - Commit del coordinatore, lotto X-R21. Dettagli: piano 03, sezione «X-R21».
- ✅ **X-R22 · L'invito a reinserire un segreto illeggibile non dice di ripristinare prima la vecchia chiave** (chiusa il
  17/10: `375d09db3`, entrata in dev `618563949`) — basso,
  testi; da H (H-3, opzione B), girata a X dal coordinatore il 16/10.
  - **Il problema**: salvare un segreto riscrive la sua riga con la chiave attuale. Se l'amministratore ripristina poi
    la vecchia chiave d'istanza, il segreto appena reinserito diventa illeggibile a sua volta.
  - La doc di H (`481a93f1c`, su `admin/configuration.md#plugin-secrets`, non ancora in `dev_release2` il 16/10 alle
    10:35) ora dice: «If you still have the old key, put it back before anyone enters them again».
  - **I miei due testi** dicono solo «enter it again», senza l'ordine:
    - il suggerimento dell'interfaccia, `frontend/src/lib/i18n/pluginSettings/en.json:31` (4 lingue);
    - la riga della tabella in `mkdocs_src/docs/user/settings/plugins.en.md:117`.
  - **Attenzione**: la pagina di H **cita alla lettera** il testo dell'interfaccia («The tab says so under each one:
    *Saved, but this instance's key cannot read it: enter it again.*»). Cambiando la chiave i18n va cambiata nello
    stesso commit anche la citazione nella sua pagina, con l'ok di H.
  - **Cura**: dopo che `481a93f1c` è nella mia base, un lotto piccolo dopo FE5c e CP13, che allinea:
    - la chiave in 4 lingue;
    - la riga della mia pagina utente, con il link alla sezione di H;
    - la citazione nella pagina di H.
- **X-R23 · Il caricamento dei dati della pagina dell'asset resta nella pagina** — medio, refactor; X, 16/10 (FE5c,
  pezzo 9, decisione del coordinatore). Il FE5c ha tolto alla pagina `routes/(app)/assets/[id]/+page.svelte` gli
  helper, i pannelli, la barra e il polling; restano `loadChartData` (~310 righe) e il caricamento dei confronti.
  - **Perché non nel FE5c**: leggono e scrivono una trentina dei ~80 `$state` della pagina. Spostarli vuol dire
    ridisegnare lo stato della pagina (una classe o uno store `.svelte.ts` con le richieste e le loro generazioni), con
    rischio alto e conflitti con J, Y e Z.
  - **Cura**: un lotto dopo la 1.3, con le E2E della pagina come rete. Dettagli: piano 03, sezione «FE5c», pezzo 9.
- ✅ **X-R24 · La ricerca senza `providers` interroga anche il provider dei test** (chiusa il 17/10: `e22251856`, entrata in dev `fd6886bb0`) — basso, API; X, 16/10 (test-author di
  F21, in lettura). `AssetSearchService.search` e `search_stream` (`services/assets/search.py`), quando la richiesta non
  dice quali provider, prendono tutto `AssetProviderRegistry.list_providers()`, compreso `mockprov`, che è `test_only` e
  sa cercare.
  - **Effetto**: una chiamata diretta a `/assets/provider/search?q=…` senza `providers` restituisce anche i risultati
    «Mock Asset» in produzione. L'interfaccia passa sempre `providers`, quindi l'utente non li vede.
  - **Cura**: escludere i provider `test_only` dalla lista di default, come fa già `GET /assets/provider`. Prima va
    controllato che nessun test, API o E2E, cerchi senza `providers` aspettandosi i risultati del mock.
  - **Collegato, minimo**: la docstring di `services/assets/__init__.py` dice che `AssetSourceProvider` e
    `AssetSourceError` stanno in `core.py`, ma sono in `base.py`.
  - Dettagli: piano 03, sezione «CP13», F21.
- ✅ **X-R25 · `test_complete_e2e_flow_justetf` va in timeout alla ricerca quando un fornitore esterno è lento** (chiusa il 17/10: `e22251856`, entrata in dev `fd6886bb0`) — basso,
  test; trovato da J in `all-backend`, girato a X dal coordinatore il 16/10.
  - **Il caso**: `backend/test_scripts/test_e2e/test_search_to_prices.py`, step 1, chiede
    `/assets/provider/search?q=iShares Core MSCI World` **senza `providers`**, con `TIMEOUT = 30.0`. Da solo passa 3/3
    in 18 s.
  - **Perché**: senza `providers` la ricerca interroga tutti i fornitori in parallelo. Ognuno ha 30 s sul server
    (`services/assets/search.py`, `timeout=30.0`), più il ripiego del link finder quando non trova niente. L'attesa
    del test, 30 s, è uguale al budget di un solo fornitore, non a quello della richiesta. **Verdetto: assunzione
    (il tempo)**; il prodotto è corretto.
  - **Cura**, nel test:
    - `providers=justetf` allo step 1, perché il test è su justETF, così non dipende dagli altri fornitori, `mockprov`
      compreso (X-R24);
    - un tempo di attesa per la ricerca sopra quello del server, almeno 60 s con la risoluzione degli URL.
  - Un lotto piccolo, quando c'è tempo.
- **X-R26 · `AssetDetailLive`: un cambio d'asset diretto confronta il primo prezzo con l'ultimo dell'asset di prima**
  — minimo, latente; trovato dal test-author scrivendo i rossi delle correzioni dal vivo, X, 16/10.
  - **Il caso**: l'effetto riparte quando cambia l'asset, ma tiene `#previousNative`. Il primo tick del nuovo asset
    si confronterebbe col prezzo del vecchio, e il lampeggio sarebbe falso.
  - **Oggi la pagina non ci arriva**: al cambio d'asset `reloadPage()` mette prima `assetInfo = null`
    (`routes/(app)/assets/[id]/+page.svelte` ~1058). L'effetto passa così dal ramo fermo, che azzera il riferimento.
  - **Cura, se mai servisse**: azzerare il riferimento solo quando cambia l'id dell'asset. Azzerarlo a ogni nuova
    esecuzione romperebbe il caso «keeps no trace of a dropped answer».
  - Dettagli: piano 03, «Correzioni dal vivo 1 e 2».
- ✅ **X-R27 · Il cambio di valuta di un asset non invalida mai le sue cache** (risolta il 16/10, lotto X-R27/28: un
  rosso per ogni difetto, poi la chiave unica `core.asset_cache_key()`; `8f3632d45`, entrata in dev `ccfabfd6d`) — basso,
  backend; colori (slot TR,
  corsia 6154, 16/10 13:43), girato a X dal coordinatore il 16/10.
  - **Il sintomo nel log**: `wipe_market_data: cache invalidation skipped — 'Asset' object has no attribute
    'provider_code'`.
  - **Perché**: il passo 4 di `services/assets/currency_change.py` (~149–161) legge `provider_code`,
    `provider_params`, `identifier` e `identifier_type` da `Asset`. Quei campi stanno sull'assegnazione del fornitore
    (`AssetProviderAssignment`). L'eccezione è presa e solo registrata: dopo un cambio di valuta le cache della storia
    e del prezzo corrente restano fino alla loro scadenza (15 min e 2 min).
  - **Cura**, con un rosso prima: leggere l'assegnazione e costruire la chiave da lì.
- ✅ **X-R28 · La cache del prezzo corrente ha una chiave senza i parametri del fornitore** (risolta il 16/10, stesso
  lotto: `8f3632d45`, entrata in dev `ccfabfd6d`, con la riga 🐛 nel CHANGELOG; nessuna riparazione, per decisione del developer) — **medio** (rivisto il
  16/10 alle 17:35: tocca tutti gli investimenti programmati e scrive dati), backend; X, 16/10, trovato misurando
  X-R27.
  - **Il caso**: `services/assets/price_query.py:764` mette in `_asset_current_cache` la chiave `(codice,
    identificativo, tipo, impostazioni)`. `refresh.py:229` e le invalidazioni (`provider_management.py` ~236,
    `currency_change.py`) usano invece la chiave a cinque elementi, con l'hash dei parametri (#R3-4).
  - **Effetti**: due assegnazioni con stesso codice, identificativo e tipo ma parametri diversi si scambierebbero il
    prezzo corrente per 2 minuti. Nessuna invalidazione raggiunge quelle voci.
  - **Il caso grave** (17:35): ogni investimento programmato ha l'identificativo `NULL` (`AUTO_GENERATED`,
    `provider_management.py:119`). Quindi tutti condividono la stessa voce. In più `/assets/prices/current` salva
    anche i risultati presi dalla cache come prezzo di oggi (`price_query.py:845`): la riga di oggi degli altri
    riceve il valore del primo.
    - Un giorno passato tiene il valore sbagliato **solo fino alla sincronizzazione notturna**, che lo corregge.
      - La «resume» che avevo trovato è quella delle sincronizzazioni del frontend (`dashboard/+page.svelte:438`,
        `AssetModal.svelte:1241`), non quella dello scheduler.
      - La sincronizzazione notturna della storia (`run_history_sync`, `scheduler/jobs.py:163`) riscrive gli ultimi
        14 giorni (`horizon_days`) dalla storia del fornitore, e gli investimenti programmati la espongono.
      - Restano solo il massimo e il minimo allargati, nei giorni colpiti. Correzione del coordinatore, 17:33.
    - **Decisione del developer (17:33)**: correzione del codice più una riga 🐛 nel CHANGELOG, senza riparazione.
      La riga dice chi è colpito, che cosa ha visto, e che le chiusure si correggono da sole entro 2 settimane.
    - **Risposte al coordinatore** (17:45, sola lettura):
      1. Un aggiornamento completo rimette giusta la chiusura (upsert `bulk_upsert_prices`). Non sistema invece
         `open`/`high`/`low` di una riga creata o allargata da un poll (F.2, F.3), perché il plugin manda solo la
         chiusura.
      2. Le righe sbagliate si riconoscono.
         - Il poll scrive `source_plugin_key = 'provider:scheduled_investment'`, il refresh `'scheduled_investment'`.
         - Fra le righe col prefisso, sono sbagliate quelle la cui chiusura è diversa dal valore del piano, che si
           può ricalcolare.
      3. Chi è esposto:
         - anche lo scheduler, senza pagine aperte: `run_current_price_refresh`, `scheduler/jobs.py:81`, ogni 10
           minuti di default;
         - con stesso identificativo e parametri diversi: `css_scraper`, `borsa_italiana`, `justetf`.
         - Non lo è `yahoo_finance`, che ignora i parametri.
    - Decisione: vedi sopra (developer, 17:33).
- **X-R29 · Sync: l'avviso di C-66 con il conteggio preciso, e quanti dati manuali** — basso; X, 16/10 (opzione B di
  C-66, decisione del coordinatore).
  - C-66 è stato fatto con l'opzione A: il conteggio viene dai dati che la pagina mostra.
  - La B è un endpoint che conta le righe salvate nell'intervallo e quante sono manuali (`source_plugin_key`), per
    asset e cambi. Così l'avviso può nominare i prezzi manuali.
- ✅ **X-R30 · La sincronizzazione degli asset deve tenere i prezzi manuali?** — chiusa il 16/10 (giornale `24242bdd2`)
  con la risposta del developer: **vince il fornitore**, i prezzi manuali non si tengono. Basta l'avviso di C-66 (opzione A), che lo dice
  («modifiche manuali comprese»). Domanda posta dal coordinatore il 16/10 (opzione C di C-66).
  - Oggi la sync scrive ogni data che il fornitore restituisce, e sovrascrive anche un prezzo `MANUAL`
    (`bulk_upsert_prices`). I cambi invece saltano le coppie solo `MANUAL`.
  - Il rischio vero di C-66 è questo.
  - **Cura proposta**: una sola funzione in `services/assets/core.py` che costruisce la chiave, usata nei quattro
    punti, con un rosso per ciascun difetto. È naturale farla nello stesso lotto di X-R27.
- ✅ **X-R31 · Ricerca degli asset: il messaggio d'errore non è tradotto** (chiusa il 17/10, `e890e6772`, entrata in dev `16e837153`: `assets.search.failed`) — basso; X, 16/10 (trovato dal test-author di
  F21/P20, fuori perimetro).
  - Quando falliscono sia lo streaming sia il ripiego REST, la tendina mostra `e.message` così com'è, oppure
    `'Search failed'` in inglese (`AssetSearchAutocomplete.svelte`, ramo `catch` del REST).
  - Cura: una chiave `assets.search.failed` in 4 lingue. L'errore tecnico resta nel log (`console.error`).
  - Il timeout ha già la sua chiave (`assets.search.timeout`).
- **X-R32 · Galleria: uno scatto della ricerca con le sezioni premium** — basso; X, 17/10 (DoD del piano 03, §10).
  - Serve un provider premium instradato, come fa l'E2E `asset-modal.spec.ts` («Asset search — premium first…»).
  - Si concorda con G; nel frattempo gli scatti degli import mostrano già la riga «Can't find it? Let us know».
- **X-R33 · E2E `asset-modal.spec.ts`: la rotta «Bug G» su `/settings/user` è fragile** — basso; X, 17/10 (trovato
  dal test-author di F21/P20).
  - Fa `route.fulfill({response, json})` e così tiene `content-encoding: gzip` della risposta vera. Se quella risposta
    arrivasse a 1 KB, il browser proverebbe a decomprimere un JSON in chiaro.
  - Cura: togliere `content-encoding` e `content-length`, come fanno `fixtures/instance-config.ts` e il blocco F21/P20.
- ✅ **X-R34 · Doc: `asset_plugin_guide.md` «How It Works» dice che il frontend chiama `GET …/search`** (chiusa il 17/10 con X-R24: `e22251856`, entrata in dev `fd6886bb0`) — basso; X, 17/10
  (trovato dal docs-writer).
  - In realtà il frontend usa prima lo streaming (`…/search/stream`), e il REST solo come ripiego.
- ✅ **X-R35 · `env_url` accetta `user:pass@` e lo pubblica** (chiusa il 17/10: `4e06d78ff`, entrata in dev
  `67668f5ce`) — piccolo, **prima del rilascio**; da E (piano 08,
  revisione di sicurezza «R13-SEC2»), assegnata a X dal coordinatore il 17/10.
  - Un indirizzo con utente e password passa il validatore e finisce sull'anonimo `GET /system/instance`.
  - Cura: il validatore della configurazione rifiuta utente e password. Copre anche `LIBREFOLIO_PUBLIC_URL` e
    `LIBREFOLIO_BILLING_URL`, che passano dallo stesso helper.
- **X-R36 · Chiave di cache: l'impronta dei parametri è un MD5 tagliato a 32 bit** — nota; da E («R13-SEC3»), 17/10.
  - `services/assets/core.py:81`. Oggi è innocuo: i prezzi sono condivisi e una collisione mescola solo due asset con
    parametri diversi.
  - Diventa **MEDIO** il giorno in cui gli asset avranno un proprietario: allora serve un'impronta piena.
- ✅ **X-R37 · P20 nell'interfaccia: le 4 note di E** (chiusa il 17/10: `c7434f00c`, entrata in dev `908fe6c90`) —
  piccolo, **prima di O-8**; da E («R13-SEC2/SEC3»), 17/10.
  1. `assetSearchReport.ts:70-74`: il controllo legge il valore senza base, così `https:host` passa e, come `href`, si
     risolve sull'istanza. Usare `url.href`.
  2. **N61** (decisione notturna del coordinatore): su `managed`, senza un `support_url` valido, o con
     `/system/instance` fallito, niente ripiego sulla issue pubblica di GitHub: pubblicherebbe `managed`, i codici dei
     provider e gli identificativi. La riga si nasconde, oppure resta senza azione: la soluzione più pulita.
  3. Un `support_url` con `user:pass@` (`url.username` o `url.password`) conta come mancante.
  4. `create-edit.en.md`: in modifica il rapporto porta anche gli identificativi dell'asset (ISIN, ticker…). Dirlo.
  - Se il punto 2 cambia quello che vede un utente `managed`, va ritoccata la riga del CHANGELOG.
- ✅ **X-R38 · Cambi: un tasso enorme si salva come infinito, e il suo inverso come zero** (chiusa il 17/10: `80f5c65ff`, entrata in dev `fd6886bb0`) — medio, **dopo X-R35**; il lato
  FX dello stesso buco di W-B58 (W lo chiude per transazioni e prezzi). W l'ha annotato come **W-B61**; girato a X dal
  coordinatore il 17/10.
  - Un tasso manuale `1E+400` si salva come `inf`, e il suo inverso come `0`; `truncate_fx_rate` solleva un'eccezione
    già da `1E+50`.
  - **Direzione** (la stessa di W-B58): un limite alle cifre intere in ogni scrittura dei cambi (manuale, provider,
    inverso), una lettura che non solleva mai, un 4xx e mai un 500.
  - Riusare l'helper di W `max_integer_digits(model, column)` in `db/precision.py`, che entra con W-B58.
- **X-R39 · Editor dei dati dell'asset: le stranezze trovate con O-8** — basso; X, 17/10 (dal test-author di O-8; già
  presenti prima di O-8).
  - I conteggi non sono simmetrici: gli eventi eliminati vengono dal server, quelli salvati dal client. Le righe di
    evento non valide si scartano in silenzio, mentre per i prezzi c'è il conteggio delle righe scartate.
  - Un salvataggio sono tre richieste separate (prezzi aggiornati, prezzi cancellati, eventi): un errore può arrivare
    dopo una scrittura parziale, e il messaggio non lo dice.
  - Le righe di prezzo vuote, scartate, allargano lo stesso l'intervallo del grafico dopo un salvataggio riuscito
    (`expandedRange` legge tutte le righe `appended`).
  - `onsave` non è atteso: un errore nel ricaricamento della pagina dopo il salvataggio non viene mai mostrato.
  - Il banner d'errore dell'editor dei cambi non ha un `data-testid` (quello degli asset l'ha avuto con O-8).
- ✅ **X-R40 · Prezzo corrente: la quotazione rifiutata torna lo stesso come prezzo dal vivo** (chiusa il 17/10 insieme a W-B62: `a7b572ce2`, entrata in dev `fd6886bb0`; resta il seguito X-R51) — basso, **dopo X-R38**; X,
  17/10 (le mie due note alla revisione di W-B58, accettate dal coordinatore).
  - `services/assets/price_query.py` ~862–866: una quotazione che `storable_price` non può tenere non si salva, ma la
    risposta la restituisce (`FACurrentPriceItem.value`, sorgente `provider:…`): un 1E+60 compare nella UI come prezzo
    dal vivo, anche se il DB l'ha rifiutato. Cura: rispondere con un errore per la voce, come «No price data available».
  - ~865: l'avviso si ripete a ogni interrogazione della stessa quotazione (lo scheduler ogni 10 minuti, più ogni pagina
    aperta). Cura: una volta per (asset, valore) per processo (`functools.cache`, come `_report_invalid`), oppure
    `info`.
- ✅ **X-R41 · `POST /fx/currencies/convert` con importo 0 dà un 500** (chiusa il 17/10, `e890e6772`, entrata in dev `16e837153`: un importo 0 si converte come una unità: risposta 0 al tasso del giorno) — basso; X, 17/10 (trovato dal test-author di
  X-R38, girato nel backlog dal coordinatore).
  - L'endpoint divide per l'importo di partenza: convertire 0 fra due valute solleva un'eccezione invece di rispondere 0.
- **X-R42 · Due fixture dei test FX lasciano righe committate** — basso, test; X, 17/10 (dal test-author di X-R38).
  - `test_upsert_multiple_pairs` e la fixture di modulo di `test_fx_conversion` committano tassi che non tolgono mai.
  - Inoltre le ragioni `exclusive_because` di `fx-core` e `fx-sync-service` nel runner descrivono ancora il troncamento
    di tutta la tabella, mentre le due fixture ora sono limitate alle loro righe.
- ✅ **X-R43 · Impostazioni dei plugin: un intero di 401 cifre in `value` dà un 500** (chiusa il 17/10: entrata in dev `3e7948446`, fix e journal; E rivede a posteriori) — basso, solo admin o proprietario; X,
  17/10 (trovato con H-32, girato nel backlog dal coordinatore; lo stesso difetto nella R13-SEC7-2 di E).
  - `fields.py:324` passa il valore a `math.isfinite()`, che con un `int` più grande di un double solleva
    `OverflowError`. `service.py:255` cattura solo `SettingValueError`, quindi `PATCH /settings/plugins/bulk` risponde 500
    invece dell'esito per voce `INVALID_VALUE`.
  - Cura: in `validate_value`, un intero fuori dall'intervallo di un double (o qualunque `OverflowError`) diventa
    `SettingValueError`; un rosso con un intero di 401 cifre.
  - Fatto: il limite è `MAX_SAFE_INTEGER` (2^53 − 1), quello che la pagina delle impostazioni tiene esatto; copre anche
    la variabile d'ambiente, la riga salvata e le dichiarazioni, che fallivano allo stesso modo. Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md),
    sezione «X-R43».
- ✅ **X-R44 · `mockprov` si può nominare e assegnare a un asset anche in produzione** (chiusa il 17/10: `59f5bcfdc`, entrata in dev `5a8c64c5c`, riga del CHANGELOG estesa dal coordinatore in `1c8eba6f5`; chiude anche `MOCKFX`) — piccolo, **prima del rilascio,
  dopo X-R38**; X, 17/10 (revisione R13-SEC5 di E su X-R24/25, girata dal coordinatore).
  - `mockprov` è nell'immagine di produzione e sempre registrato. Con X-R24 la ricerca senza `providers` lo salta, ma
    chiunque può nominarlo in una ricerca e **assegnarlo a un asset** con `POST /assets/provider`, che non controlla né
    il registro né `test_only`: una serie finta a 100 USD al giorno su un asset globale, condiviso fra gli utenti.
  - Direzione: fuori dalla modalità di test, rifiutare i codici `test_only` in `configured_provider` e nell'assegnazione.
  - Per F05, quando arriva: l'elenco dei fornitori permessi deve chiudere anche il percorso di un fornitore *nominato*
    (`configured_provider`/`get_plugin`), non solo l'elenco e il default.
- **X-R44b · Un controllo di qualità dei dati per i codici di fornitore che nessun registro serve** — basso, dopo la
  1.3 se non costa poco; X, 17/10 (E, revisione di X-R44, girata dal coordinatore).
  - Elencare le assegnazioni degli asset, le rotte dei cambi e le righe il cui codice di fornitore nessun registro
    serve: copre le righe che i doppi di test hanno già scritto nelle istanze rilasciate, e i plugin rimossi.
  - Nota informativa di E: `shutdown_all_providers` istanzia ancora i doppi; innocuo, nessuna azione.
- ↩️ **X-R45 · Cambi: chi legge `fx_rates` direttamente non salta i tassi vecchi inutilizzabili** (**annullata il 19/10**
  per decisione del developer; il rovescio è in attesa del commit. Dettagli nel piano 03, «Rovescio di X-R45».
  - Tolti: la condizione nei tre lettori nuovi, la guardia strutturale, la doc, il runner e la riga del CHANGELOG.
  - Restano, com'erano, i filtri di `convert_bulk` (X-R38) e dei period changes (X-R59).
  - Prima: chiusa il 17/10, `629304ab3` + `21164d0a7`, entrata in dev `b690c0785`: la strada (b) del backlog, `usable_fx_rate_clause()` in ogni lettore che calcola, più una guardia strutturale; revisori MF per il PAC, Z per lo scheduler) — basso; X, 17/10 (da
  X-R38).
  - Con X-R38 nessuna scrittura salva più un tasso fuori dai limiti, e `convert_bulk` e `compute_chain_rate` saltano quelli
    vecchi (`inf`, 0, 20 cifre intere: una 1.2 poteva salvarli, per esempio un manuale `1E-11`, che si rilegge 0).
  - Diversi moduli però leggono la tabella per conto loro: `financial_math/portfolio/engine.py:99`, `financial_math/lots/*`,
    `financial_math/price_marks.py`, `pac_allocator/source/{wac,fx_quotes}.py`, i componenti FX dell'AI Export,
    `api/v1/backup/exports.py`. Con uno 0 vecchio, chi divide solleva un'eccezione; con un `inf`, gli importi diventano
    assurdi.
  - Due strade, da decidere:
    - (a) una migrazione di dati che toglie, o mette da parte, le righe con `rate < 1E-10` o `rate >= 1E+14`: richiede
      il via del developer, perché tocca dati dell'utente;
    - (b) lo stesso filtro, `usable_fx_rate_bounds()`, in ogni lettore: molti file di J e dell'AI Export.
- ✅ **X-R46 · Editor dei cambi (e degli asset): i rifiuti del server non si vedono** (chiusa il 17/10, `88d0fb840`, entrata in dev `2c43ac451`: le due scritture manuali nominano ogni data lasciata fuori in `rejected`, data e motivo; il 400 dei
  cambi tutto rifiutato ha `detail` `{code: fx_rates_refused, message, rejected}`; `writeRefusal.ts` dà una frase tradotta
  per ogni rifiuto codificato e un avviso che nomina le date; Axios non arriva più all'utente. Dettagli nel piano 03,
  «X-R46») — basso-medio, **subito dopo X-R38**; X, 17/10
  (trovato dal docs-writer di X-R38).
  - Gemello trovato da B (17/10): `AssetDataEditorSection.svelte` (~316) conta come salvata ogni riga inviata e non legge
    `results[].message`, così una data scartata dal controllo OHLC è annunciata come salvata.
  - Allargata il 17/10 (revisione di X-R65 e nota di Z): anche `AssetDataEditorSection.svelte`, e il nuovo 422
    `date_out_of_range` (`items`, `count`, `params.min`/`max`): oggi entrambi gli editor mostrano solo «Request failed with
    status code 422» (`e.message`), senza la data né i limiti. Un refuso come 2062 per 2026 basta a farlo comparire.
  - `FxDataEditorSection.svelte`, `handleSave()`, quando tutti i tassi sono rifiutati (400): il toast e il banner mostrano
    «Request failed with status code 400» di Axios, non il `detail` del backend (coppia, data, limiti). L'editor resta
    aperto con le modifiche.
  - Quando un tasso è rifiutato fra altri validi (200 con `errors`): l'editor ignora `errors`, conta il rifiutato in «FX
    rates: N saved» e ricarica. Il tasso manca, in silenzio.
  - Con X-R38 l'editor raggiunge questi rifiuti (più di 14 cifre intere, o sotto `1E-10` una volta salvato). Prima il
    tasso si salvava sbagliato; ora si scarta, ma la UI dice che è salvato.
  - Cura: mostrare il `detail` del 400 e gli `errors` del 200 (per data), contarli a parte. Prove: Vitest e
    `front-fx fx-editor`. Poi la frase della pagina utente (`user/fx/detail/data-editor.en.md`) può dire «con un messaggio
    che nomina la data».
- ✅ **X-R75 · La modale delle rotte di un cambio cancella prima di salvare** (chiusa il 17/10 da B: `5cbc60844` frontend +
  `970081b45` backend, entrata in dev `6ee4d2ed4`; revisione di X dopo l'ingresso: OK, il residuo delle gambe delle
  catene è X-R79) — piccolo-medio, perdita di dati a ogni
  salvataggio fallito, **nella 1.3, fatta da B** (decisione del coordinatore, 17/10 17:05: B ha già l'analisi, con lo
  stesso gemello, e fa l'opzione A, un `replace=true` atomico su `POST /fx/providers/routes`; X rivede; la modale delle
  rotte resta a B); X, 17/10 (E, E-19, girata dal coordinatore).
  - `FxPairAddModal.svelte` (~321-339), `handleSave()` in modifica: prima `DELETE /fx/providers/routes` con
    `[{base, quote}]` (tutte le priorità della coppia), poi `POST /fx/providers/routes` con le rotte nuove. Due richieste,
    due transazioni.
  - Se il POST fallisce, le rotte vecchie sono già cancellate e la coppia resta senza rotte. Può fallire per un 422
    (un lato non ISO), un 400 (un provider sconosciuto, con il rollback del solo POST), un 409 (una scrittura
    concorrente) o la rete.
  - **Gemello, da provare con un rosso**: togliendo tutti i provider in modifica, la modale salta il POST, convinta
    che il backend rimetta la sentinella MANUAL. Ma `delete_routes_bulk` la rimette solo dopo una cancellazione con
    priorità: `fully_deleted_pairs` esclude quelle senza. La coppia resta senza nessuna rotta, nemmeno MANUAL, mentre
    la creazione nello stesso caso salva MANUAL (priorità 999).
  - **Cura proposta, nel backend**: le rotte di una coppia si sostituiscono in una sola transazione.
    - Tutto convalidato prima di scrivere; cancellazione e inserimento insieme; la sentinella MANUAL quando non resta
      un provider vero.
    - La modale in modifica fa una sola chiamata.
    - Forma da decidere nell'analisi: un `PUT /fx/providers/routes` o un parametro `replace` del POST.
    - Le coppie intermedie (le gambe delle catene) restano un'aggiunta, mai una sostituzione.
  - **Alternativa solo frontend**, più piccola ma non atomica: prima il POST (un upsert per priorità), poi la
    cancellazione mirata delle sole priorità in più. Un secondo passo fallito lascia rotte in più, non ne perde.
  - **Prove**:
    - rossi API: un rifiuto lascia intatte le rotte; un insieme vuoto dà MANUAL; il riordino delle priorità;
    - Vitest della modale: in modifica una sola chiamata, nessun DELETE prima;
    - E2E `front-fx fx-add-pair`: una modifica che fallisce lascia le rotte com'erano.
    Doc: le rotte nella pagina dev dei cambi; `api sync`.
  - **Peso**: come X-R58: una rotta del backend, la modale, tre livelli di test, una finestra E2E (`fx-add-pair`).
    L'alternativa solo frontend è piccola.
- ✅ **X-R79 · Il `replace` di X-R75 sostituisce anche le gambe delle catene** (chiusa il 17/10 da B: `b4a66be9a` +
  `13db415b8`, entrata in dev `6f11a6790`; opzione A, solo frontend) — basso, **nella 1.3, fatta da B**, dopo
  W-B64/65 (decisione del coordinatore, 17/10 19:05); X, 17/10 (revisione di X-R75).
  - `POST /fx/providers/routes?replace=true` vale per ogni coppia della richiesta, anche per le gambe che la modale
    aggiunge con «crea le coppie intermedie». La voce X-R75 le voleva solo aggiunte, mai sostituite.
  - La modale manda solo le gambe che crede non configurate, secondo la sua cache al salvataggio. Se un'altra scheda o
    un altro utente configura quella gamba nel frattempo, la modifica ne sostituisce le rotte con quella di priorità 1
    e cancella le altre. È una corsa stretta, e la docstring di B la dice.
  - Cura (frontend): in modifica, prima le gambe con un upsert semplice (solo aggiunta), poi la sola coppia principale
    con `replace=true`; un Vitest fissa l'ordine delle due richieste. Se fallisce la seconda, restano solo gambe nuove.
  - Residui noti (accettati dal coordinatore, 17/10 20:2x):
    - l'upsert semplice non è solo aggiunta: una gamba configurata nel frattempo ha ancora la sua priorità 1 riscritta
      (le altre restano). L'opzione B, una bandiera `create_only` del backend, va a X dopo la 1.3;
    - un 409 sulla richiesta della coppia, dopo le gambe scritte, mostra `fx.addPair.createConflict` («Nothing was
      saved»), che per le gambe non è vero. È raro: serve un inserimento concorrente della stessa priorità;
    - dopo le gambe scritte e la coppia rifiutata, lo store delle rotte non le conosce: un nuovo tentativo le riscrive
      uguali.
- **X-R80 · Le gambe delle catene non sono mai davvero «solo aggiunte»** — basso, **dopo la 1.3**; X, 17/10 (dall'analisi
  di B per X-R79, girata dal coordinatore).
  - `create_routes_bulk` fa un upsert per (base, quote, priorità): a una priorità esistente sovrascrive `chain_steps`
    (`api/v1/fx/providers.py` ~249-262), e un provider vero toglie la rotta MANUAL.
  - Così anche il POST delle gambe di X-R79 (opzione A, solo frontend) può sovrascrivere la priorità 1 di una gamba
    configurata nel frattempo. È la stessa esposizione che il percorso di creazione ha sempre avuto.
  - Per avere davvero «solo aggiunta» serve un flag del backend, per esempio `create_only`: salta una coppia che ha
    già rotte, nella stessa transazione. Più `api sync`.
- ✅ **X-R47 · Il rapporto di uno SPLIT non è mai validato** (chiusa il 17/10: `5f68a8db0`, la regola (d) con `1b6d65da7`; entrata in dev `952c68cd5`; gli SPLIT già salvati sono MF-D4) — **prima del rilascio**, dopo X-R40/W-B62; X, 17/10 (J, analisi
  V-4 di CP-14a, F4, girato dal coordinatore).
  - Si salva uno SPLIT con rapporto 0 o negativo. Appena una transazione lo collega, il motore solleva un `ValueError` e
    il report della Dashboard risponde 500.
  - Cura: validare il rapporto alla scrittura dell'evento. Al via, verificare col coordinatore chi possiede i file degli
    eventi (consegnati a W dopo CP2b).
  - Rosso della regola (d) dei confini dello strato (J, 17/10 06:20): `event_store.py` nominava `AssetEventType.SPLIT`.
    Cura: il predicato `financial_math.splits.is_split_event_type` (file di J, J rivede).
- ✅ **X-R47b · Senza chiamante il rifiuto di P-10 mostrava tutti gli id** (chiusa il 17/10: `1b6d65da7`, entrata in dev `952c68cd5`) — piccolo, sicurezza (LOW); X, 17/10 (E,
  revisione di `5f68a8db0`, girato dal coordinatore). Nello stesso lotto della cura della regola (d).
  - Cura: la rotta passa `_current_user.id`; senza chiamante nessun id, solo `hidden_transactions_count`. I test P-10 di
    J (file di W) rispondono a un utente che vede le transazioni: J e W rivedono. Nello stesso lotto, la nota LOW di W:
    il rapporto nel messaggio d'errore scritto nella lingua dell'interfaccia (`formatExactDecimal`). Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md),
    sezione «X-R47b».
- ✅ **X-R48 · `market-data/wipe` cancella gli SPLIT collegati a rettifiche senza costo** (chiusa il 17/10: entrata in dev `2ea54ff76`; J ed E rivedono a posteriori) — **prima del rilascio, dopo
  l'ingresso di CP-14a di J**; X, 17/10 (J, F1, girato dal coordinatore).
  - `POST /assets/{id}/market-data/wipe` (il flusso del cambio di valuta, ma si può chiamare anche da solo) scollega ogni
    transazione dagli eventi dell'asset e li cancella tutti, SPLIT compresi (`currency_change.py:131-137`). Una
    rettifica +q collegata a uno SPLIT, senza costo, diventa `MISSING_COST_BASIS`.
  - **Deciso**: una guardia come quella di P-10, cioè un rifiuto 409 con i dettagli (evento, data, transazioni), tramite
    `financial_math.splits.costless_incoming_split_adjustments`, che arriva con CP-14a.
- ⏸️ **X-R48b · La modale del cambio di valuta non avvisa prima della conferma** (sospesa il 19/10 con i rossi scritti,
  messi da parte in patch: N68 può cambiare la modale; piano 03, «X-R16 + X-R48b») — basso, UX, non urgente; X, 17/10 (J,
  revisione di X-R48, girata dal coordinatore).
  - Il riepilogo (dry run) non rifiuta mai, quindi il pannello di conferma non può avvisare: l'utente incontra il 409
    solo dopo aver confermato.
  - Cura facoltativa: il riepilogo porta il numero degli SPLIT che bloccano, e la modale avvisa prima della conferma.
- ✅ **X-R49 · Lo stesso buco di X-R48 dal cambio dei parametri di un Scheduled Investment** (chiusa il 17/10, `589f15607`, entrata in dev `e710cf552`: rifiuto 409 `PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST` prima di ogni scrittura, frase tradotta nella modale dell'asset; dettagli nel piano 03, «X-R49») — basso; X, 17/10 (J, F2,
  girato dal coordinatore).
  - `provider_management.py:212-221`: vale solo se un utente ha scritto uno SPLIT fra gli eventi del piano.
  - Ordine deciso dal coordinatore dopo X-R40/W-B62: X-R47 → X-R48 → X-R44 → X-R49.
- ✅ **X-R50 · Seguito di X-R38: tre note della revisione R13-SEC5 di E** (chiusa il 17/10: `243ab6150`, entrata in dev `fd6886bb0`; ECB a parte, X-R52) — piccolo, **nel lotto di X-R40/W-B62**; X, 17/10
  (E, girato dal coordinatore).
  1. Limite del double: un tasso a meno di 0,008 da `1E+14` ha 14 cifre intere e passa, risposto «inserted», ma SQLite lo
     salva come `1e14`, e ogni conversione lo salta. `storable_fx_rate` deve chiedere anche `float(v) < 1E+14`.
  2. Underflow: `normalize_storable_rate` può restituire zero quando l'inverso va in underflow, contro la sua docstring.
     Dopo l'inversione, chiedere `> 0`.
  3. BOE e SNB: `Decimal(str)` solleva `InvalidOperation`, che il loro `except` non cattura; un valore ostile fa fallire
     tutto il fetch di quel provider (solo disponibilità). FED ha lo stesso buco
     (`except (ValueError, IndexError, ZeroDivisionError)`): lo chiudo insieme.
  - Inoltre E ha classato MEDIUM 8/10 le scritture dei cambi da parte di qualunque utente (profilo gestito): va al
    developer insieme a D-SEC2-1, non a X.
- ✅ **X-R51 · Il refresh non dice più perché ha scartato il valore corrente** (chiusa il 17/10: `ce798e36a`, entrata in dev `b3cae6e0e`) — piccolo, **subito dopo l'ingresso di
  X-R40/W-B62**; X, 17/10 (trovato dal docs-writer di X-R40).
  - Con X-R40/W-B62 una quotazione corrente che nessuna colonna tiene si scarta prima dell'upsert. Il risultato del
    refresh perde così il motivo («rejected … no price column can keep»): con lo storico è OK senza messaggio, senza
    storico è FAILED con «No price data available from provider». Il motivo resta solo nel log, una volta.
  - Cura pronta (`files/checks/xr51_code.py` della sessione X): una nota in `_FetchedRefreshData` che finisce negli
    `errors`, quindi PARTIAL col motivo, oppure FAILED col motivo. Rossi pronti in `files/drafts/`. Docs da ritoccare:
    il paragrafo del refresh in `backend/assets/architecture.md`.
  - Nello stesso lotto, due ritocchi trovati dal docs-writer di X-R50:
    - `fx_rate_limits_text()` non nomina la regola del double: un `99999999999999.995` manuale si sente dire «al
      massimo 14 cifre prima della virgola», ma ne ha 14. Aggiungere «sotto 100000000000000». I test cercano solo i
      numeri 14 e 10, e la frase va aggiornata anche in `backend/fx/configuration.md`;
    - la docstring di `_collect_leg_rates()` (`sync.py`) nomina solo l'overflow, non l'underflow.
- ✅ **X-R52 · ECB: un valore che non è un numero fa perdere tutta la valuta** (consegnata il 17/10, 05:35; SHA all'ingresso) — piccolo, disponibilità; X, 17/10 (trovato dal
  docs-writer di X-R50).
  - `ecb/plugin.py` non ha un `try` per osservazione, e il suo `except (KeyError, IndexError, ValueError)` non cattura
    `InvalidOperation`: un valore ostile fa uscire l'eccezione grezza invece di `FXServiceError`, e si perde la valuta,
    forse tutto il fetch di ECB. ECB è il fornitore principale dei cambi.
  - Cura: saltare l'osservazione (`ArithmeticError`), come BOE, SNB e FED con X-R50. Un rosso in `test_fx_parse_errors.py`.
- ✅ **X-R53 · Usare il campo dei periodi fissi (1D, 1W…) che MF porta nel backend** (chiusa il 17/10: entrata in dev `78708660f`; MF e Y rivedono a posteriori) — medio, **quando MF manda il
  contratto**; X, 17/10 (coordinatore).
  - Fatto: `lib/utils/periodChanges.ts` legge le due rotte di MF; le pagine degli asset e dei cambi non calcolano più le
    Δ (via `DELTA_PERIODS`, `computePeriodDelta` e la seconda copia); `/period-changes` non è una scrittura; riga 🐛
    dell'ora legale nel CHANGELOG. Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «X-R53».
  - Oggi la tabella dei periodi fissi di asset e cambi si calcola nel frontend (`lib/utils/assetPriceDerived.ts:193`,
    `AssetTable.svelte:239`, `routes/(app)/fx/+page.svelte:236`). MF, nel lotto MF-P, crea il campo nel backend.
  - Da fare: leggerlo da lì nei miei file, quando MF scrive col contratto. Non ora.
  - Accordo con MF (17/10, 05:25), detto al coordinatore:
    - endpoint dedicati: `POST /assets/prices/period-changes` e `POST /fx/currencies/period-changes`;
    - `as_of` = la fine dell'intervallo, come oggi: le serie sono giornaliere e riempite all'indietro, quindi i numeri
      non cambiano, compreso un 1D a 0 % nel fine settimana;
    - resta la regola di oggi, che mostra le colonne fino all'intervallo scelto, quindi niente cambia a vista. Mostrare
      tutti i periodi che hanno un valore va proposto al developer;
    - `target_currency` col cambio di ogni giorno;
    - MF scrive il backend (moduli nuovi, rotte e schemi aggiunti nei miei file) e io lo rivedo; il frontend è mio, dopo
      l'ingresso di MF.
  - Contratto di MF (05:50, backend al checkpoint):
    - `POST /api/v1/assets/prices/period-changes` prende `[{asset_id, as_of, target_currency?}]` e restituisce per
      voce `{asset_id, as_of, currency, periods[{key, days, change_ratio}], errors[]}`;
    - `POST /api/v1/fx/currencies/period-changes` prende `[{base, quote, as_of}]` (422 se base = quote) e restituisce
      `periods[{…, inverse_change_ratio}]`;
    - i periodi arrivano in ordine (1D … 5Y); i valori sono frazioni, da moltiplicare per 100; null = non disponibile.
  - Da fare nel lotto frontend:
    - `isPortfolioAffectingMutation()` (`lib/stores/portfolio/portfolioMutation.ts:102-107`) deve escludere
      `/period-changes`, altrimenti ogni chiamata segna come vecchie le viste del portafoglio. Aggiornare anche la riga
      di `developer/frontend/state/domain-state.md`. Di chi è il file, da verificare all'avvio;
    - via le due copie di `computePeriodDelta`. Calcolavano il giorno di riferimento in ora locale del browser e, a cavallo
      dell'ora legale, sbagliavano di un giorno. Il backend conta giorni di calendario esatti: alcuni riferimenti
      cambiano, e va una riga 🐛 nel CHANGELOG;
    - altre differenze: 1D c'è anche con un intervallo di un giorno; una serie nativa con valute miste, o una
      conversione fallita, dà null più un errore; un prezzo ≤ 0 dà null.
- **X-R56 · Uno SPLIT di un provider con un rapporto non valido, salvato prima di X-R47, non si può correggere** — basso,
  **dopo X-R53**, prima l'analisi; X, 17/10 (MF-D4, girato dal coordinatore).
  - Non si modifica per id (`EVENT_NOT_EDITABLE`, è di un provider) e non si cancella finché ha transazioni collegate
    (`EVENT_IN_USE`): la CTA `navigate_asset` del nuovo avviso `INVALID_SPLIT_RATIO` porta a un vicolo cieco.
  - Direzione: un refresh del provider riscrive o scarta quell'evento (con la regola dei collegamenti), oppure una via
    di recupero.
- ✅ **X-R58 · Le liste di asset e cambi tacciono quando la richiesta bulk supera i limiti di Z-25** (chiusa il 17/10, `2b48340b6`, entrata in dev `1bef78be1`: un toast tradotto da `bulkRefusalMessage`; il caricatore FX continua a rilanciare, per scelta) — piccolo, **subito
  dopo X-R53, quando Z-25 entra**; X, 17/10 (coordinatore, N77).
  - Z-25 aggiunge due 422 con codice a `POST /assets/prices/query` e `POST /fx/currencies/convert`:
    `bulk_too_many_items` (più di 1000 voci) e `bulk_too_many_days` (più di 5 milioni di giorni-voce, contati dopo la
    lettura). Oggi il `catch` di `fetchAllPriceData` (asset) e quello dei cambi tacciono: card senza prezzi.
  - Cura: un messaggio esplicito col limite, una chiave i18n in 4 lingue, su quei codici. Serve il contratto di Z (la
    forma del `detail` e i parametri del limite) quando Z-25 entra.
- ✅ **X-R59 · La Δ sull'intervallo si calcola ancora nel browser** (fatta il 17/10: il backend da MF, `a8de6b584`,
  entrato in dev `482343eb3`; il frontend da Y, lotti A/B, `53fea97f7`, entrato in dev `f317e3a9f`) — basso, regola 10 (una casa sola per la matematica
  finanziaria); X, 17/10 (trovata dal docs-writer di X-R53). **Passata a MF** (coordinatore, 17/10 08:40).
  - Il cambio sull'intervallo scelto (le card delle due liste; le colonne Δ Abs e Δ % della tabella dei cambi) è
    `computeDerivedPriceState()` (`lib/utils/assetPriceDerived.ts`) e `FxTable.getDelta()` → `displayFxDelta()`
    (`lib/stores/fxStoreRegistry.ts`, anche nella card e nella pagina della coppia): ultimo / primo − 1, in float.
  - X-R53 ha portato nel backend solo le colonne dei periodi fissi (1D…5Y).
- ✅ **X-R60 · Le colonne Δ: tre note della revisione di Y su X-R53** (chiusa il 17/10, `6d74ab3a1`, entrata in dev `cb05410a5`: un registro delle richieste in `periodChanges.ts`, 24 casi di unità e 8 E2E) — piccolo, **dopo X-R48**; X, 17/10 (Y, girata dal
  coordinatore). Prima il punto 1.
  1. Cambi, una coppia sola (`loadPairPeriodChanges`): nessun indicatore, quindi `data-busy` può dirsi finito mentre la
     Δ di quella coppia è in volo; e non avanza la versione, quindi una risposta completa più vecchia che arriva dopo
     riscrive la coppia.
  2. Il nuovo tentativo dei segnali e il cambio delle impostazioni richiedono anche i periodi, che non ne dipendono.
  3. Un errore cancella le Δ ancora valide per lo stesso `dateEnd`.
- **X-R61 · Il Sync di una sola card o riga sovrascrive i prezzi salvati senza l'avviso di C-66** — basso, domanda di
  prodotto per il developer (nel file delle domande del coordinatore, 17/10); X, 17/10 (il test-author di Y-28).
  - `handleSyncAsset` (la card o la riga della lista) parte subito, senza la finestra: nessun avviso prima di
    sostituire i prezzi salvati del periodo, modifiche manuali comprese. L'avviso c'è solo nella finestra (Sync all, il
    Sync della selezione, la pagina dell'asset).
  - Da decidere: aprire la finestra anche lì, o un avviso leggero, o lasciare com'è.
- ✅ **X-R62 · «Nessun provider» fallisce quando un evento del provider è collegato a una transazione** (chiusa il 17/10 da H: `9fcbbe523` + `1e660d104`, entrata in dev `907fb3b97`; revisione di X dopo l'ingresso: OK, il residuo dei 500 in X-R74) — basso (fallisce
  chiuso, nessun costo corrotto), **dopo la 1.3** salvo che costi poco; X, 17/10 (trovato leggendo X-R49, non
  riprodotto).
  - `bulk_remove_providers` cancella l'assegnazione; `AssetEvent.provider_assignment_id` è `ON DELETE CASCADE`,
    `Transaction.asset_event_id` è `ON DELETE RESTRICT` e SQLite applica le chiavi (`PRAGMA foreign_keys=ON`): con un
    dividendo Yahoo o uno SPLIT del piano collegato a una transazione, la rimozione fallisce con un errore d'integrità,
    che la modale mostra come errore generico.
  - Da decidere: scollegare prima, come il wipe di X-R48 (con la regola degli SPLIT senza costo), o rifiutare con un
    codice e i collegamenti. Prima un rosso che lo riproduca.
- ✅ **X-R66 · Il limite delle sonde dei provider detto nella lingua dell'utente** — basso, **dopo X-R58** (il
  coordinatore, 17/10); X, 17/10 (dalla revisione di MF-SI2).
  - `POST /assets/provider/probe` risponde 429 `{error_code: PROBE_RATE_LIMITED, retry_after, message}` oltre 30
    sonde al minuto per utente. «Test Configuration» mostra il `message` inglese del backend (`extractErrorMessage`),
    «Ask Provider» un generico «si è verificato un errore».
  - Cura: una frase tradotta con l'ora locale di fine attesa, come per il `RATE_LIMITED` dei provider.
  ✅ **Fatto da A il 17/10** (`ed5ad328a`, dev `e50c23919`): `probeRateLimitMessage()` in `resolveProviderError.ts`, chiavi `providerErrors.PROBE_RATE_LIMITED*` ×4; Test Configuration e Ask Provider dicono quando riprovare.
- **X-R49b · I controlli degli SPLIT senza costo leggono prima del BEGIN differito** — basso, dopo la 1.3 salvo che costi
  poco; X, 17/10 (E, revisione di X-R49, via coordinatore). Vale anche per X-R48.
  - Il controllo legge prima della prima scrittura, fuori dal lock di scrittura di SQLite: una rettifica senza costo
    collegata da un altro utente nei millisecondi fra controllo e cancellazione sfugge.
  - Cura, se la si vuole: rifare il controllo dopo la prima scrittura, sotto il lock, come fa A-42.
- **X-R67 · Liste `IN (...)` di id di evento oltre i 32.766 parametri di SQLite** — basso, dopo la 1.3; X, 17/10 (revisione
  di X-R62).
  - `costless_incoming_split_adjustments` (X-R48, X-R49) e `event_links.events_with_linked_transactions` (X-R62) mettono
    tutti gli id in un solo `IN`. Un asset con più eventi generati (un piano con cedole giornaliere su circa 90 anni)
    farebbe un 500.
  - Cura: una sottoquery sull'assegnazione o sull'asset al posto della lista.
- **X-R68 · Due funzioni senza chiamanti in produzione** — minimo; X, 17/10 (Z, dopo Z-27).
  - `ensureFxRangeLoadedBulk` (`stores/fxStoreRegistry.ts`) e `ensureAssetPriceRangeLoaded`
    (`stores/assetPriceStoreRegistry.ts`): candidate al codice morto, con i loro test.
- **X-R69 · Togliere il provider rifiuta, cambiare il piano scollega** — basso, decisione di prodotto; X, 17/10 (H, nota di
  X-R62).
  - «Nessun provider» rifiuta finché un evento generato ha transazioni collegate (X-R62); nuovi parametri del piano o un
    altro provider scollegano quegli eventi e rifiutano solo per gli SPLIT con rettifiche senza costo (X-R49).
  - Da decidere se allineare: per esempio, scollegare anche alla rimozione con la sola regola degli SPLIT.
- **X-R70 · Il refresh conta le date rifiutate dal controllo OHLC** — basso; X, 17/10 (Z, nota di X-R65).
  - `_persist_refresh_item` toglie dal conteggio le date che nessuna colonna tiene e quelle fuori intervallo, ma non
    quelle che `bulk_upsert_prices` rifiuta per OHLC impossibile (chiusura fuori da [minimo, massimo]).
- ✅ **X-R71 · Il caricamento manuale dei prezzi non è tutto o niente sulla valuta** (fatta da B: `d5963fa60`, entrata in
  dev `1c7937984` il 17/10; rivista da X: OK) — basso-medio, **nella 1.3, fatta da B**
  (il coordinatore, 17/10; X rivede); X, 17/10 (Z, nota di X-R65).
  - Una valuta diversa da quella dell'asset è rifiutata asset per asset, dopo che gli asset precedenti sono stati
    scritti. Il controllo va prima della prima scrittura, come X-R65 fa ora per le date.
  - Il disegno di B: il caricamento manuale controlla la valuta di ogni asset prima della prima scrittura, 422
    `price_currency_mismatch` con `items`; B tocca una riga di descrizione in `schemas/prices.py`.
- ✅ **X-R72 · Le date degli eventi degli asset senza pavimento al 1900** (chiusa il 19/10: superata da N83, che toglie il
  pavimento anche alle scritture di prezzi e cambi; gli eventi vanno già in quella direzione) — basso, prima da verificare; X, 17/10 (Z, nota di
  X-R65).
  - I periodi di un piano Scheduled Investment sono già limitati a 1900-2200 (`SCHEDULE_MIN_DATE`). La data aperta è
    probabilmente quella degli `asset_events` del piano, e degli eventi degli asset in generale (manuali o dei
    provider), che X-R65 non limita.
- **X-R73 · `_range_start_in_bounds` ripete `stored_date_bounds()`** — minimo; X, 17/10 (Z, nota di X-R65).
  - `api/v1/assets/prices.py` (di MF, R13-SEC9-4) confronta a mano [`EARLIEST_RANGE_START`, `latest_range_end()`]:
    deve chiamare l'aiuto unico di `utils/date_range_limits.py`.
- ✅ **X-R74 · Le rotte di asset e cambi rispondono 500 con il testo dell'errore** (chiusa il 17/10, `8224a0cec`, entrata in dev `1c1456713`: 26 siti in 6 file rispondono «Internal error while …» e registrano l'errore; in più il 400
  `MERGE_FAILED` della fusione, «Merge failed: internal error»; `services routes-generic-500` 34 passed, 8 suite API e DB 165 passed) — basso, sicurezza (fuga di testo SQL),
  **nella 1.3, primo lotto dopo X-R58**; X, 17/10 (revisione di X-R62, punto 1 di J; decisione del coordinatore).
  - X-R62 ha tolto l'`IntegrityError` dal 500 (ora `PROVIDER_REMOVAL_CONFLICT`, senza SQL). Il `except Exception` di
    `remove_providers_bulk`, e il ripiego per gli altri `AssetSourceError`, rispondono ancora `detail=str(e)`: un altro
    errore del database (per esempio `OperationalError`) mostra il suo SQL. Lo stesso in tutto
    `api/v1/assets/providers.py`: 7 punti, e la sonda non registra nemmeno l'errore.
  - La stessa fuga in altri 5 file di X: `assets/crud.py` 7, `assets/events.py` 5, `assets/market_data.py` 2 (uno è
    il wipe di X-R48), `fx/providers.py` 4 (`f"Failed to …: {e!s}"`), `fx/currencies.py` 1. **Tutti e 6 i file in un
    solo lotto** (sì del coordinatore, 17/10 15:50), con un rosso parametrizzato su ogni rotta, la sonda che registra il
    suo errore e una riga 🔒 nel CHANGELOG.
  - Cura: il messaggio generico di R13-SEC9-3 (come `api/v1/assets/prices.py`), l'errore nel log con la sua eccezione;
    i 400/404/409 scritti apposta restano. Prima un rosso parametrizzato su ogni rotta, come
    `test_sec9_3_a_failure_answers_500_without_echoing_it`.
  - Registrata prima, per errore, come «H-51» nella sezione di H: l'ID era già di H (`trusted_schema`).
- ✅ **X-R65 · Il pavimento delle date sulle scritture manuali di prezzi e cambi** (rivista il 19/10 dalla revisione di N83:
  il pavimento del 1900 è tolto da tutte le scritture di prezzi e cambi, anche dei fornitori; resta «non oltre domani»; X,
  in attesa del commit del coordinatore) — decisione notturna N83; **fatta da Z** (`30e19b9d9`, entrata in dev `c726b9d89`, rivista da X il 17/10: OK); X, 17/10
  (il coordinatore; numerata X-R65 per lo scontro con X-R64).
  - Le letture si fermano al 1900-01-01 (`EARLIEST_RANGE_START`), le scritture manuali di prezzi e di tassi di cambio
    no: un prezzo prima del 1900 si può salvare, e «Tutto» risolve allora l'inizio dell'intervallo prima del 1900
    (visto nella revisione di X-R59: un `range_start` così fa fallire tutta la richiesta di period-changes).
  - Direzione (N83): lo stesso pavimento sulle scritture manuali, come per le transazioni (N74).
  - Dettagli del coordinatore: un prezzo piantato al 0001-01-01 faceva percorrere a un replay del rischio o a una query
    circa 740.000 giorni per asset (J, SEC8-1b); intervallo [`EARLIEST_RANGE_START`, `latest_range_end()`], 422 con
    codice (`date_out_of_range`); i punti dei provider fuori intervallo scartati e non contati.
- ✅ **X-R44c · Solo asset e cambi possono dichiarare `test_only`** (chiusa il 17/10, `4bda99953`, entrata in dev `e41427916`: due guardie in `services test-only-providers`, provate con una mutazione) — piccolo, **subito** (il coordinatore, 17/10); X, 17/10.
  - Il filtro di X-R44 sta nella base dei registri (`_withheld()`), ma segnali e rischio (`list_definitions`), BRIM
    (rilevamento ed elenco) e tools (la sua istantanea) leggono il proprio archivio senza chiederlo: un `test_only` lì
    sarebbe servito in produzione. Un test di guardia lo vieta fuori da asset e cambi.
- ✅ **X-R64 · La richiesta di period-changes divisa in lotti da 1.000** (chiusa il 17/10, `aedf5d8c3`, entrata in dev `15132b448`; con il sondaggio dal vivo di `/prices/current`, tetto di R13-SEC9-1: sì del coordinatore, 17/10) — piccolo, **dopo l'ingresso di Z-27**, con il suo
  aiuto e la sua costante; X, 17/10 (dalla revisione di X-R59: il limite scende da 10.000 a 1.000).
  - Dentro `fetchAssetPeriodChanges`/`fetchFxPeriodChanges` (il registro di X-R60 vede una sola risposta unita); poi
    aggiornare i due passi della documentazione di MF (`assets/architecture.md` ~374, `fx/architecture.md` ~238), che
    oggi la assegnano a Z-27, aggiungendo il flusso di X-R60 (quale risposta resta, l'indicatore, un errore che tiene le
    Δ dello stesso giorno, inversione e impostazioni che non chiedono nulla). Insieme a X-R58.
- **X-R63 · Due vuoti vecchi nella documentazione degli asset** — minimo, al prossimo tocco di quelle pagine; X, 17/10
  (il docs-writer di X-R49).
  - `developer/backend/assets/architecture.md`: la tabella dei moduli non elenca `provider_policy.py`.
  - `user/assets/providers/scheduled-investment.en.md`, tabella degli eventi del piano: manca **Maturity Settlement**,
    che l'editor offre (la pagina ha traduzioni: debito da tradurre).
- ✅ **X-R57 · Il commento C-66 di `asset-detail.spec.ts` dà una ragione superata** (chiusa il 17/10 con Y-28: `c18517e31`, entrata in dev `8aafffad8`) — minimo; X, 17/10 (Z, dopo Z-3).
  - Verso la riga 8672 di `e2e/assets/asset-detail.spec.ts` il commento dice «by its UTC reckoning…»; dopo Z-3 (dev
    `0f55265a1`) le pagine degli asset leggono il giorno dell'utente (`todayIso()`). Lo stub resta giusto: cambia solo
    la ragione scritta. Da fare al prossimo tocco di quel file.
- ✅ **X-R55 · Intervalli senza tetto: una data estrema blocca l'istanza** (fatta da Z: `a71d23e7e` + `0ca0c0d59`,
  entrata in dev `ab7711f04` il 17/10; il portafoglio con J-43, `a46f85bda`, in dev `09cb9231a`) — sicurezza, disponibilità; **passata a Z** (il
  coordinatore, 17/10 06:38: Z è libera; X rivede al checkpoint di Z, perché i file sono di X); X, 17/10 (J, lo stesso
  vettore di R13-SEC7-1; girato dal coordinatore). E rivede.
  - `services/assets/price_query.py` `_build_backward_filled_series`: un punto per giorno su qualunque intervallo chiesto
    (API dei prezzi degli asset, ambiti degli asset del rischio, segnali).
  - `api/v1/fx/currencies.py` (~427 e ~471): il ciclo di `convert` sull'intervallo della richiesta.
  - Una richiesta con `end` 9999-12-30 o `start` 0001-01-01 blocca l'istanza.
  - Direzione, come J: la fine limitata a oggi + 1 (margine per i fusi orari); l'inizio limitato al primo dato o a un
    arco di 100 anni. Prima i rossi con date moderate, poi le date estreme come guardie con un limite di tempo.
- **X-R76 · I valori degli eventi di un piano d'investimento programmato oltre i 6 decimali si troncano in silenzio** —
  basso, numeri, **dopo la 1.3** (non costa poco, sotto); X, 17/10 (W, residuo di W-B68, girato dal coordinatore).
  - Gli eventi pianificati di uno Scheduled Investment (`asset_events` di `FAScheduledInvestmentSchedule`, parametri
    dell'utente) passano dal percorso degli eventi dei provider (`_storable_events`, `services/assets/event_store.py`).
  - Da W-B68 un valore con più di 6 decimali vi si tronca alla colonna (`RealDecimal(18, 6)`), in silenzio; prima si
    rileggeva arrotondato, in silenzio anche allora.
  - Cura: rifiutarlo all'ingresso del piano, nel provider, con un messaggio che nomina l'evento. Non su
    `FAAssetEventPoint`: è condiviso con l'uscita dei provider, dove il troncamento è giusto.
  - Perché non costa poco: `validate_params` dello Scheduled Investment gira anche a ogni lettura (valore corrente e
    storico, `plugin.py` ~543 e ~616) e al refresh (`refresh.py` ~149). Un controllo nello schema farebbe smettere di
    sincronizzarsi i piani già salvati con 7 decimali. Serve una regola per quelli (rifiuto solo in scrittura, o
    arrotondamento esplicito con avviso), più il messaggio nel modulo del piano.
- **X-R77 · Il test di X-R47 accetta qualunque numero come «nome dell'asset»** — minimo, test, al prossimo tocco di
  `test_event_split_ratio.py`; X, 17/10 (W, nota dopo W-B68, girata dal coordinatore).
  - `_names_the_asset` cerca l'id come numero intero ovunque nel testo dell'evento di log. Con l'asset 1 basta il
    `count=1` dell'avviso «Splits skipped» a soddisfarlo.
  - Cura: confrontare la chiave `asset_id` dell'evento di structlog (`event_store.py` la scrive) invece del testo.
- **X-R78 · Prezzi manuali: con un solo limite vero dalla parte sbagliata della chiusura, la riga si salva incoerente** —
  basso, decisione di politica, **dopo la 1.3**; X, 17/10 (test-author di X-R46, dopo la cura del −1).
  - Da X-R46 un limite cancellato (−1) non è un limite: il controllo stretto di `bulk_upsert_prices` vale solo con due
    limiti veri in arrivo.
  - Con un solo limite vero la riga si scrive com'è. Così l'editor può salvare un Low sopra la chiusura con High
    cancellato, o un High sotto la chiusura con Low cancellato; il test
    `test_a_manual_edit_erasing_low_with_high_below_the_close_is_saved_as_is` fissa questa politica com'è oggi.
  - Vicino: un Low mandato da solo, col High salvato, è allargato in silenzio fino alla chiusura (il ramo «widen»,
    pensato per i provider che mandano solo la chiusura).
  - Da decidere: rifiutare un limite vero dalla parte sbagliata (`ohlc_inconsistent`), allargarlo, o scriverlo. Poi
    cambia il test.
- ✅ **C-97c-4 · I cambi delle valute deboli letti come zeri** (chiusa il 17/10, `7ac14656a`, entrata in dev `e414edf0b`) —
  piccolo, **nella 1.3**; X, 17/10 (revisione di C-97c-3, decisione del coordinatore).
  - La lista, la card e il riepilogo dei cambi, il Δ della lista e il tooltip del cambio di una transazione usano
    `formatPrice(x, {minDecimals: 4})`. Prima scrivevano `formatFixed(x, 4)`, e VND→USD si leggeva `0.0000`.
  - Dettagli nel piano 03, «C-97c-4».
- **X-R81 · La conferma di cancellazione aperta già bloccata non vede le transazioni cancellate nel frattempo** — basso,
  **dopo la 1.3**; X, 19/10 (coordinatore colori, revisione di X-R18, girata dal coordinatore il 17/10).
  - La conferma singola si apre bloccata dal `tx_count` della riga com'era al caricamento della lista. Se le transazioni
    dell'asset si cancellano intanto (un'altra scheda), resta bloccata finché la lista non si ricarica, anche se il
    DELETE ora passerebbe.
  - Cure possibili, nello stato bloccato: un'azione «Controlla di nuovo» che rilegge il conteggio della riga, oppure una
    che manda il DELETE e lascia decidere il backend (`HAS_TRANSACTIONS` rifiuta comunque).
  - Costo: una chiave in 4 lingue e una E2E. La revisione: colori puliti, logica giusta.
- **X-R82 · PAC, cambi salvati: un ramo e un codice che nessun dato raggiunge più** — minimo, **dopo la 1.3**, non tocca i
  numeri; X, 19/10 (MF, revisione di X-R45, voce 1, girata dal coordinatore il 17/10).
  - **Il ramo e il codice: decaduti il 19/10** con il rovescio di X-R45. Lo 0 dell'ultima riga salvata torna
    `allocation.saved_fx_invalid`; lo fissa `test_xr45_reverted_the_planner_fx_quote_is_built_from_the_latest_stored_row`.
  - **Resta aperta** solo la docstring di `_validate_canonical_fx_pair` (voce «Accanto», sotto).
  - In `build_planner_fx_quotes` (`pac_allocator/source/fx_quotes.py` ~103–116), `rate if rate > 0 else None` e il
    problema `allocation.saved_fx_invalid` non si raggiungono più. L'unica fonte è `_load_latest_planner_fx_rows`, la
    condizione di X-R45 sta nella sottoquery della data e `(date, base, quote)` è unico (`uq_fx_rates_date_base_quote`):
    la riga unita è quella che l'ha passata, quindi almeno 1E-10.
  - Toglierlo del tutto non è gratis: il codice sta nei due enum (`schemas/portfolio.py:1630`,
    `schemas/pac_allocator/base.py:178`), quindi in OpenAPI e nel contratto versionato del tool `pac_allocator`
    (`tool-contracts.openapi.json`), più 4 chiavi i18n in `pacAllocator`.
  - Strade: (a) tenerlo, con un commento «irraggiungibile dopo X-R45: la guardia è nella lettura» (consigliata: nessun
    contratto cambia); (b) togliere solo il ramo, lasciando codice e chiavi; (c) togliere tutto, con OpenAPI, contratto del
    tool e chiavi.
  - Accanto: la docstring di `_validate_canonical_fx_pair` (`schemas/portfolio.py:1255`) promette «'usd/eur' ->
    'EUR/USD'», ma il codice rifiuta l'ordine discendente con un 422. Da correggere la docstring.
- **X-R83 · Pagina dell'asset: il ramo che fonde il Sync dell'asset della pagina non si raggiunge** — minimo, **dopo la
  1.3**; X, 19/10 (lettura del codice per N64). L'ipotesi registrata qui come difetto visibile è smentita dalla lettura,
  prima di scrivere il rosso.
  - Il Sync della barra passa da `handlePageSyncComplete` → `handleRefresh()`, che invalida la cache dei prezzi e ricarica
    forzando: il grafico finisce sulla risposta del server.
  - Il ramo `canMergeOnly` sta in `runSyncAsset` (`routes/(app)/assets/[id]/+page.svelte` ~2001), con la condizione
    `assetId === pageAssetId`. Lo raggiunge solo il Sync di una card di confronto, e la pagina esclude il proprio asset
    dai confronti (`availableAssets`, ~2341): è un ramo morto.
  - Se tornasse vivo, avrebbe il difetto: fonde il delta solo in `chartData`, poi la ricarica legge la cache, che non lo
    ha, e il grafico torna ai valori di prima.
  - Cura: togliere il ramo, come X-R68.

- **X-R84 · Un chunk che non si carica dopo il login dà «500 Internal Error» e SvelteKit non riprova** — basso, **fuori
  dal perimetro di X** (shell del frontend), da girare a chi la possiede; X, 19/10 (triage di un rosso E2E di N92).
  Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md), sezione «N92 (i) con "clear"
  — rossi, cura, verdi», parte «E2E».
  - Osservato in `fx-data-editor.spec.ts`: dopo il login, la navigazione a `/dashboard` ha chiesto 47 dei 63 chunk.
  - SvelteKit ha controllato `version.json` due volte, l'ha trovato uguale e ha mostrato la pagina d'errore, dove
    l'utente resta finché non ricarica.
  - Nessun errore del backend; rifatta da sola, la spec passa. Il guasto è del trasporto, ma la reazione dell'app è un
    errore 500, non un nuovo tentativo.
  - Strade possibili, da decidere: ricaricare una volta su un import dinamico fallito, oppure una pagina d'errore che
    lo dice e offre di riprovare.

## W · Import e transazioni (fase 01)

Piano: [`04_importTransactions`](../Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md).

- ✅ **W-B1 · L'icona dei plugin servita con un controllo `startswith`** — basso, sicurezza; W, 14/10 (analisi).
  `serve_plugin_static` (`backend/app/api/v1/uploads.py:541`) confronta i percorsi come stringhe: una cartella sorella
  che comincia con lo stesso nome passerebbe il controllo. Oggi non ce n'è nessuna, e la rotta chiede il login. Cura:
  `Path.is_relative_to`, con U-B3 (lotto W5), d'accordo con H. Dettagli: piano 04, §1.1 e §7.
  ✅ 16/10 (triage): chiusa da `6e8251014` (14/10, in v1.2.1, «fix(server): keep served file paths inside their folder»):
  `serve_plugin_static` usa `confined_path` (`backend/app/utils/runtime/paths.py`: `resolve()` e `is_relative_to`);
  CHANGELOG 1.2.1 «The server keeps every file it serves inside the folder it belongs to». Dettagli: piano 04, sezione «Triage».
- **W-B2 · Il cambio di provider scollega in silenzio le transazioni dagli eventi automatici** — medio-basso, dati; W,
  14/10 (analisi). `asset_sources/provider_management.py:186-195` (di X): cambiando i parametri o il provider di un
  asset, gli eventi del provider si cancellano e le transazioni collegate perdono il collegamento senza avviso. È il
  caso che la modale di C-65 deve mostrare (C-65a, X e W). Dettagli: piano 04, §2 (C-65).
- ✅ **W-B3 · Un file BRIM senza `target_broker_id` è aperto a ogni utente** — da verificare, sicurezza; coordinatore,
  14/10. `_get_brim_file_with_access` (`backend/app/api/v1/brokers.py:119`) salta il controllo dei ruoli quando il file
  non ha un broker (i file vecchi, alla radice delle cartelle). Prima un rosso: se quei file possono ancora esistere, e
  chi li vede. Dettagli: piano 04.
  ✅ 15/10 (F36, decisione 36): confermata (lista, lettura, parse e cancellazione aperti a chiunque con il login) e chiusa:
  un file senza broker lo raggiungono solo chi l'ha caricato e l'admin (senza caricatore registrato, come i file di prima
  del 24/01/2026, solo l'admin); 403 per gli altri, assente dalle loro liste. Dettagli: piano 04, sezione F36.
  Riferimenti (triage 16/10): `3907eed36`; CHANGELOG [Unreleased] «Broker reports uploaded by older versions are no
  longer open to every user» (non in 1.2.1).
- ✅ **W-B4 · Gli id dei file BRIM accettati senza controllo del formato** — basso, sicurezza; coordinatore, 14/10. Le rotte
  `/brokers/import/files/{file_id}` accettano una stringa qualsiasi: un controllo del formato UUID all'ingresso è una
  difesa in più sui percorsi. Dettagli: piano 04.
  ✅ 15/10 (F36): un `file_id` che non è un UUID nella forma canonica minuscola risponde 404 prima di ogni ricerca (prima
  un id di 300 caratteri dava 500, un file `<uuid>-1` veniva servito, e su macOS anche l'id in maiuscolo).
  Riferimenti (triage 16/10): `3907eed36`; CHANGELOG [Unreleased] «Report file ids are checked first» (non in 1.2.1).
- ✅ **W-B5 · La cassa del broker conta le transazioni future** — da verificare, numeri; coordinatore, 14/10 (D-J16
  dell'analisi di J, con B15 lato broker). `TransactionService.get_cash_balances`
  (`backend/app/services/transactions/transaction_service.py:476-480`) somma tutte le transazioni del broker, anche
  quelle con una data futura. Dettagli: piano 04; analisi di J.
  ✅ 15/10, `6be11ecf3` (N1a): il riepilogo del broker prende `as_of`, il giorno dell'utente, per cassa, quantità e costo
  medio; la cassa dalla casa unica (`native_balances`). Il resto della copia per la convalida del batch è W-B19.
- ✅ **W-B6 · V-3, TRANSFER orfano: la scrittura e la migrazione dei dati** — basso; coordinatore, 14/10 (D-J4). A W la
  conversione in ADJUSTMENT della metà rimasta quando si cancella un broker, e la correzione degli orfani già presenti
  nei DB; a J i rossi su lotti e Dashboard. Dettagli: voce V-3 nella sezione V.
  ✅ 15/10, `6be11ecf3` (N1b-1, la cancellazione) e `5e19c6018` + `0e4bd9790` (N1b-2/N1b-3, la correzione
  post-migrazione `orphan_pair_halves`, entrata col punto 46 del developer): la gamba in arrivo di un TRANSFER diventa un
  ADJUSTMENT col suo costo (Auto se mancava, finché c'è il mittente; senza, «costo mancante» con l'avviso), quelle di
  cassa un DEPOSIT o un WITHDRAWAL. **Resta aperto il punto 47** del developer: la gamba in uscita di un TRANSFER perde
  solo il link, come prima; se si decide di convertirla, è un lotto nuovo.
  ◐ 16/10 (decisione 47, lotto di W pronto, **ingresso dopo J-17**): la gamba in uscita diventa un ADJUSTMENT-out al costo
  Auto del suo broker (`_handover_cost`; i lotti la consegnano a quel costo con CP-16 di J), senza un cambio resta un
  TRANSFER senza link; lo split di una coppia TRANSFER fa lo stesso nel batch (rifiutato con `WAC_FX_UNAVAILABLE` se manca
  il cambio), il promote toglie il costo dal lato che cede; le gambe sole già nei DB le converte il passo d'avvio
  `lone-transfer-legs` dopo le correzioni post-migrazione (dry run nella riga di comando). Dettagli: piano 04, sezione
  «Decisione 47».
- **W-B7 · `TODO_FUTURI`, eventi collegabili: percorso e conteggi superati** — minimo; W, 14/10 (analisi). L'endpoint è
  `POST /transactions/events/suggest`, i test API sono 10 e non 8, `suggest_events_bulk` sta in
  `services/transactions/transaction_service.py:492`. Si aggiorna quando la voce entra nel lotto K3. Dettagli: piano 04,
  §2.
- ✅ **W-B8 · `DataImportModal`: «Help» e «Close» in inglese** — minimo; W, 14/10 (analisi). Gli `aria-label` di
  `components/ui/data-editor/DataImportModal.svelte:211` e `:220` sono scritti nel codice; vanno con P-15 (lotto K1).
  Dettagli: piano 04, §2 (P-15). ✅ Chiusa il 15/10 (lotto K1 della 1.3, `532a1fd9c`; in `dev_release2` con `d915c869f`).
- ↪ **W-B9 · `test_fx_api.py` raggiunge ECB via rete** — spostata nella sezione X dal coordinatore il 15/10
  (dominio dei cambi), dove X l'ha già ripresa con i dettagli.
- ✅ **W-B10 · `access_control.md`: l'elenco degli endpoint d'accesso non è quello dell'API** — minimo, doc; W, 15/10 (W2).
  `mkdocs_src/docs/developer/architecture/access_control.md`, «API Endpoints», elenca `POST /brokers/{id}/access` e
  `PATCH`/`DELETE /brokers/{id}/access/{user_id}`; l'API ha `GET` e `PUT /brokers/{broker_id}/access` (tutta la
  configurazione in un colpo), `PATCH` e `DELETE /brokers/{broker_id}/access/me` (`backend/app/api/v1/brokers.py:408`,
  `:440`, `:493`, `:519`). L'elenco dei metodi sopra è stato corretto in W2. Dettagli: piano 04, §12, W2 passo 5.
  ✅ 15/10 (lotto di doc A-14): «🌐 API Endpoints» elenca le quattro rotte vere (`GET`/`PUT …/access`, `PATCH`/`DELETE
  …/access/me`), con chi le chiama e le risposte d'errore. Dettagli: piano 04, sezione «Lotto di doc A-14».
  Commit (riconciliato il 19/10): `bf66d4fe7` (lotto di doc A-14), dev `6fa3f8936`.
- ✅ **W-B11 · `TransactionBulkModal.svelte`: `brokerName()` non ha chiamanti** — minimo, codice morto; W, 15/10 (I1). La
  funzione (`frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte:1597`) non è usata da nessuna
  parte del file né altrove; i nomi dei broker passano da `renderBrokerHtml`. Si toglie col taglio della modale (FE8a).
  Dettagli: piano 04, §12, I1. ✅ Chiusa il 15/10 (lotto FE8a-2: la funzione è tolta col taglio del Bulk).
  Commit (riconciliato il 19/10): `464350cc7` (FE8a-2, il taglio del Bulk).
- ✅ **W-B12 · `test_cross_broker_access_failure_is_atomic` lascia i suoi broker nel DB condiviso** — minimo, test; W
  (test-author di I1), 15/10. Il test (`backend/test_scripts/test_api/test_broker_multiuser_api.py`, MULTI-008d) crea
  due broker e non li cancella; i test V-23 della stessa classe nuova (`TestAccessRefusalPlacement`) puliscono anche dopo
  un rosso, e possono fargli da modello. Dettagli: piano 04, §12, I1.
  ✅ 16/10: MULTI-008d crea i broker con gli aiuti V-23 e li cancella in un `finally`; nessun `M008d%` resta dopo il run.
  Dettagli: piano 04, sezione W-B12.
- ↪ **W-B13 · `fx-csv-import.spec.ts` prende la ✕ della modale d'importazione per testo** — spostata nella sezione X
  dal coordinatore il 15/10 (spec di X).
  Commit (riconciliato il 19/10): `8129f8176` (MULTI-008d pulisce i suoi broker).
- ✅ **W-B14 · La docstring di `IdentifierType` cita percorsi vecchi, ed è nell'OpenAPI** — minimo, doc; W, 15/10 (W4,
  CP6). `backend/app/db/models.py:127` dice ancora `backend/app/services/brim_provider.py` (ora `services/brim/`), accanto
  a `services/asset_source.py` e `schemas/assets.py` di X. La docstring diventa la descrizione dell'enum nell'OpenAPI,
  quindi un lotto di riordino, che vuole lo schema identico, non la tocca. Cura: un lotto che accetta la differenza
  nella descrizione, insieme a X per le sue due righe. Dettagli: piano 04, §12, W4.
  ✅ 15/10 (riconciliato il 19/10): `f8d87ed9c` «docs(api): fix stale paths in API descriptions» porta la docstring di `IdentifierType` a `services/brim/brim_provider.py`.
- **W-B16 · Un evento del fornitore reimportato da un backup torna come evento manuale, e poi raddoppia** — basso,
  dati; W, 15/10 (analisi di E1, I-11b). L'export degli eventi (`backend/app/api/v1/backup.py:277-330`) porta la colonna
  `source` (`MANUAL`/`PROVIDER`), che l'import ignora. Se la riga del fornitore trova ancora il suo evento, l'editor la
  salta (`frontend/src/lib/components/ui/data-editor/DataEditor.svelte:545-548`); se non lo trova più, per esempio dopo
  un cambio di valuta che cancella gli eventi, rientra come evento manuale, e il fornitore la ricrea al sync successivo:
  due eventi. Oggi la guida chiede di togliere a mano quelle righe (`user/assets/detail/data-editor.en.md:71`). Proposta:
  l'import degli eventi salta le righe `PROVIDER` quando l'asset ha un fornitore assegnato e le conta nel riepilogo;
  un'opzione le importa comunque come manuali, per un asset rimasto senza fornitore. Dettagli: piano 04, §12, E0.
- ✅ **W-B15 · `tx-bulk-operations.spec.ts` prende il pulsante di chiusura per testo** — minimo, test; trovato da X il 15/10
  (CP3b), assegnato a W dal coordinatore. `frontend/e2e/transactions/tx-bulk-operations.spec.ts:428` usa
  `button:has-text("Cancel"), button:has-text("Close"), [aria-label="Close"]`, che regge solo in inglese. Nella
  stessa famiglia, X-R9 (sezione X) chiede due `data-testid` in `DataImportModal.svelte` di W: il `ConfirmModal` di
  `:305` e il pulsante Annulla di `:287`. Dettagli: piano 03, §15, CP3b. **Chiusa da W il 15/10** (E0, `d226bc69e`): la
  spec chiude il picker con `tx-picker-cancel`, che c'era già; nessun difetto del prodotto.
- ✅ **W-B17 · L'API accetta una FX_CONVERSION fra due broker** — basso, dati; W, 15/10 (N1). I metadati vogliono le due
  metà sullo stesso broker (`backend/app/schemas/transactions/type_metadata.py:313-315`, `broker_id: equal`), e il form, la
  promozione e gli import le scrivono così; ma `_validate_linked_pair` (`backend/app/services/transactions/validation.py:64-89`)
  rifiuta TRANSFER e CASH_TRANSFER sullo stesso broker e non rifiuta una FX_CONVERSION su due broker, quindi
  `POST /transactions/commit` con un `link_uuid` su due broker la crea, e cancellando uno dei due broker ne resta una metà
  (N1b-1 la converte per segno, come lo split). Cura: `pairBrokerMismatch` per una FX_CONVERSION su due broker, con il
  rosso. Dettagli: piano 04, §12, N1.
  ✅ 16/10: `_validate_linked_pair` rifiuta una FX_CONVERSION su due broker (`pairBrokerMismatch`, `brokerA`/`brokerB`;
  chiave i18n nelle 4 lingue); rosso visto, `services transaction` 67/67. Update e promozione non possono crearla. Dettagli:
  piano 04, sezione W-B17. Residuo → W-B46.
  Commit (riconciliato il 19/10): `926a5c422`, treno 106 (`b82e7765f`).
- **W-B18 · `test_account_deletion_api.py`: docstring ferme al piano 34** — minimo, test; W, 15/10 (N1, segnalato da
  test-author). ACCDEL-003 dice ancora «NEW, red today» e che la guardia conta ogni superutente con `count_superusers`
  (l'endpoint usa `count_active_superusers`); ACCDEL-002/004/005 dicono «green today and after the fix» (la cura del
  piano 34); `_service_delete_brokers` parla di «today's code». Le asserzioni sono giuste: cambia solo il testo. Cura:
  un passaggio di sola prosa, nel primo lotto che tocca il file. Dettagli: piano 04, §12, N1.
- **W-B19 · La convalida dei saldi del batch somma la cassa da sé (copia della casa unica)** — basso, numeri; W, 15/10
  (N1, trovato da docs-writer). `backend/app/services/transactions/balances.py`: `_validate_broker_balances` (`:41-47`),
  `_get_balances_before_date` (`:93-100`) e `get_balances_at_end_of` (`:107`, usato dal gap-fix dell'import) sommano la
  cassa per broker e valuta senza `financial_math/native_cash.py` (regola 4, `backend.instructions.md`). Oggi le regole
  coincidono (righe con importo e valuta), quindi nessun numero è sbagliato. **J conferma** (15/10): copia per la metà
  di cassa. Cura: le due somme su `native_balances` (le esclusioni come filtro sui movimenti); il cammino di
  `_validate_broker_balances` (`:68-82`) su una funzione pura della casa per il percorso (per broker e valuta, il primo
  giorno sotto zero), con la sola attribuzione alla riga del batch e l'errore nella convalida; in una passata sola
  (saldo iniziale più percorso), perché gira a ogni batch: misurare sui set dei report BRIM. Di passaggio, la somma
  `Decimal` della casa toglie il dubbio del `SUM` di SQLite in virgola mobile (`Numeric(18, 6)`; mai visto sbagliare).
  La metà delle quantità resta fuori: la casa non ha la quantità per posizione a una data (J-1 di J). Dettagli: piano
  04, §12, N1.
- ✅ **W-B20 · `delete_bulk` non è atomico per broker** — basso, dati; W, 15/10 (N1, trovato da docs-writer; riscritta il
  15/10 con i reperti di X). `BrokerService.delete_bulk` (`backend/app/services/brokers/broker_service.py:424`) cattura gli
  errori per broker e non riempie mai `errors`, e `DELETE /brokers` fa commit quando `errors` è vuoto
  (`backend/app/api/v1/brokers.py:389`): ciò che un broker fallito ha già scritto nella sessione entra nel commit. N1b-1
  calcola tutti i costi Auto prima di ogni modifica (BR-U-080), quindi la cancellazione stessa non lascia mezze scritture;
  resta il caso generale. Un SAVEPOINT per broker da solo non basta: pysqlite non apre la transazione prima del primo
  DML, e il RELEASE del savepoint più esterno fa commit (provato su un SQLite di prova: SELECT, savepoint, rollback
  esterno → la riga resta). Reperti di X: `delete_assets_bulk` è **già atomico**, perché un `UPDATE` vuoto prima del
  primo savepoint fa emettere `BEGIN` (`backend/app/services/assets/crud.py:349-351`, da `e50d66408`), e lo fissa
  `backend/test_scripts/test_services/test_asset_source.py::test_delete_assets_bulk_commit_failure_propagates_and_rolls_back_tentative_deletes`
  (rosso senza l'`UPDATE`); il listener `begin` generale è **scartato**, perché una sessione che legge, vede un altro
  scrittore fare commit e poi scrive fallisce subito con `SQLITE_BUSY_SNAPSHOT`, che `busy_timeout` non aspetta.
  **Cura decisa** (coordinatore, 15/10): un aiuto in `backend/app/db/session.py` che apre la transazione prima del primo
  savepoint di un percorso di scrittura (lo stesso `UPDATE` vuoto, o `BEGIN IMMEDIATE` se nessuna transazione è aperta);
  `delete_bulk` lo usa per broker, con un rosso prima; X potrà poi sostituirci il trucco locale di `crud.py`. Lotto
  piccolo di W, dopo l'ingresso di N1. Dettagli: piano 04, §12, N1.
  ✅ 15/10 (W-B20): `begin_writes(session, table)` in `backend/app/db/session.py` (in aggiunta: l'`UPDATE` vuoto) e
  `delete_bulk` con un savepoint per broker (`_delete_one`, il `flush` dentro): un broker che fallisce a metà non lascia
  niente, gli altri della richiesta si cancellano, la cancellazione dell'account resta tutto o niente. Rossi BR-U-081…085;
  la mutazione senza l'aiuto fa tornare rossi BR-U-082 e i due test dell'account. Il trucco di `crud.py` resta a X.
  Dettagli: piano 04, sezione W-B20.
- **W-B21 · `admin/cli_tools`: la correzione `orphan_pair_halves` solo in inglese** — minimo, doc; W, 15/10 (N1b-2).
  La sezione «Post-Migration Fixes» di `mkdocs_src/docs/admin/cli_tools.en.md` dice la seconda correzione solo in EN
  (coordinatore: niente IT/FR/ES né stamp, perché il file lo toccano anche A e H). Va nel debito di traduzione di A-10
  (sezione A), che nel mio ramo non c'è ancora: da riunire alla riconciliazione. N1b-3 aggiunge un punto (il warning
  delle violazioni di FK già presenti) e cambia una frase del riquadro (lo script stampa il log); E1c aggiunge il
  paragrafo della correzione `event_types` (due punti). Dettagli: piano 04, §12, N1 ed E1.
- ✅ **W-B22 · Correzioni post-migrazione: una violazione di FK già nel DB blocca ogni correzione, a ogni avvio** — basso,
  dati; W, 15/10 (N1b-2, provato da docs-writer su un DB di prova). Il controllo comune
  (`backend/app/db/post_migration/__init__.py`, `_common_problems`) vuole `PRAGMA foreign_key_check` **vuoto** sull'intero
  DB dopo ogni correzione: su un DB che chiede ancora `autoincrement` e ha un link pendente, `autoincrement` fallisce, il
  giro si ferma prima di `orphan_pair_halves` (che quel link l'avrebbe tolto), e si ripete a ogni avvio con una copia
  `.bak` in più ogni volta. Vale per ogni violazione di FK preesistente, in qualunque tabella (già prima di N1b-2). Il
  caso reale è raro: le cancellazioni dell'app scollegavano sempre prima, con le FK accese. Proposta: il controllo
  confronta le violazioni prima e dopo, come già fa con i conteggi delle righe (una correzione non ne aggiunge), più un
  rosso; file del quadro del piano 34, da assegnare. Dettagli: piano 04, §12, N1. **Chiusa** (N1b-3, 15/10, `0e4bd9790`, assegnata a W
  dal coordinatore): conta solo una violazione nuova; quelle già presenti restano, con un warning per giro.
- ✅ **W-B23 · `python -m backend.app.db.post_migration` non registra le righe INFO** — minimo, log; W, 15/10 (N1b-2,
  trovato da docs-writer). Lo script (`backend/app/db/post_migration/__main__.py`) non chiama `configure_logging()`: si
  vede il warning su stderr (con gli id per conversione, anche nel dry run), ma una riparazione fatta a mano non lascia
  la riga per transazione né «applied and verified», che all'avvio del server vanno nel log. Proposta: configurare il
  log nello script (console e `logs/` della data-dir configurata), con un test che non sporchi la sandbox dei test del
  piano 34. File del quadro, da assegnare. Dettagli: piano 04, §12, N1. **Chiusa** (N1b-3, 15/10, `0e4bd9790`): il log sulla console
  soltanto (JSON su stdout, nessun file nella data-dir), configurato solo quando lo script gira con `python -m`.
- **W-B24 · Chi può modificare i dati condivisi degli asset: un modello per il futuro** — basso, decisione; W, 15/10
  (decisione 25 del developer). Asset, prezzi manuali, eventi (dividendi, split) e classificazioni sono condivisi fra
  tutti gli utenti di un'istanza: chiunque abbia fatto il login li crea, modifica, unisce e cancella, anche chi vede un
  broker solo in lettura, e una correzione cambia i calcoli di tutti. Il developer (15/10): «l'istanza è condivisa
  apposta, è un rischio necessario che uno sbagli, è noto e accettato» — nella 1.3 resta così. Per il futuro (istanze
  cloud con più famiglie?): un modello fra solo gli admin, solo chi ha creato l'asset, solo chi ne ha posizioni, o un
  registro delle modifiche con l'autore. Dettagli: file delle decisioni, punto 25.
- **W-B26 · Una tendina aperta verso l'alto in una tabella finisce sotto l'intestazione fissa** — basso, UI (componenti
  condivisi); W, 15/10 (E1b, trovato dal test-author). La lista di `SimpleSelect` è `fixed z-[9999]` ma non è portata nel
  `body` (`frontend/src/lib/components/ui/select/SimpleSelect.svelte:328`): dentro una tabella resta nel contesto di
  sovrapposizione di un antenato, sotto la `th` fissa (`z-index: 15`, `components/table/DataTable.svelte:1621`). Quando
  si apre verso l'alto vicino all'intestazione (poco spazio sotto) le opzioni sono coperte e non si cliccano: visto
  nell'editor degli eventi, sul tipo di una riga. Cura possibile: portare la lista nel `body`, come gli altri menu
  fissi. File condivisi (UI e tabella): da assegnare. Dettagli: piano 04, sezione E1, passo 3.
- **W-B27 · L'editor dei dati dell'asset: il prefisso «Save failed:» in inglese e le date ISO nel messaggio** — minimo,
  chiarezza; W, 15/10 (E1b, docs-writer). Dopo E1b il motivo di un rifiuto degli eventi è tradotto, ma il `catch` del
  salvataggio in `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` lo antepone a «Failed to save: » /
  «Save failed: » scritti a mano in inglese, e la frase porta le date in ISO. In più le chiavi `events.deleteBlocked` e
  `events.deleteNotFound` (sorgente i18n `assets`) non le usa più nessuno: da togliere. Righe di X: da assegnare.
  Dettagli: piano 04, sezione E1, passo 3.
  ◐ 15/10 (lotto di doc A-14): **le due chiavi sono tolte** (`dev.py i18n remove`, in EN/IT/FR/ES; nessun lettore nel
  prodotto, nei test, nelle E2E, nel backend né nella doc). Resta aperto il prefisso «Save failed:» con le date ISO in
  `AssetDataEditorSection.svelte`: righe di X, da assegnare.
- **W-B28 · Debito di traduzione delle pagine utente di E1b** — minimo, doc; W, 15/10 (E1b). Cambiate solo in inglese,
  senza stamp: `user/assets/detail/data-editor.en.md` (§ 📅 Events tab: il salvataggio tutto o niente e l'elenco dei
  rifiuti; § 📥 Import from CSV: il `type` e la colonna `currency`), `user/assets/detail/events.en.md` («From you» e il
  nuovo H3 `#new-event`, da tenere con quell'àncora in ogni lingua: `form` la cita), `user/transactions/form.en.md`
  («Missing event?»). IT, FR ed ES con la pipeline, su richiesta del developer. Dettagli: piano 04, sezione E1, passo 5.
- ✅ **W-B29 · `asset-event-delete.spec.ts`: lo scenario 1 scrive su Apple condivisa a una data fissa** — minimo, test; W,
  15/10 (E1b, segnalato dal test-author). Lo scenario 1 salva un DIVIDEND sull'asset Apple condiviso a una data fissa,
  con un marcatore `Date.now()`: se i progetti desktop e mobile lo eseguono insieme, il secondo upsert sovrascrive la riga
  del primo. Lo scenario 2 marca le righe con una sonda `isVisible().catch`. Cura: un asset proprio per test, come in
  `asset-event-editor-save.spec.ts`. Dettagli: piano 04, sezione E1, passo 3.
  ✅ 16/10: gli scenari 1 e 2 su un asset proprio (il 2 anche con broker e transazione propri), righe segnate per id, pulizia
  in `afterEach`; aiuti comuni in `frontend/e2e/assets/asset-events-owned.ts`. E2E `asset-event-delete` 4/4 e
  `asset-event-editor-save` 4/4. Dettagli: piano 04, sezione W-B29. Residuo negli scenari 3 e 4 → W-B42.
  Commit (riconciliato il 19/10): `f9969056e`.
- ✅ **W-B30 · Svuotare un costo manuale non lo toglie: la modifica lo tiene in silenzio** — basso, numeri; W, 15/10 (N2,
  test-author). In un aggiornamento `cost_basis_override: null` vale «invariato», come un campo assente
  (`_apply_update_values`, `backend/app/services/transactions/batch_edits.py`): il modulo, quando l'utente svuota un costo
  manuale, manda `null` e il backend tiene il costo di prima senza dirlo. Da decidere: un modo esplicito di togliere il
  costo (con la regola del costo obbligatorio che poi lo rifiuta dove serve) o un messaggio. Dettagli: piano 04, sezione
  N2.
  ✅ 16/10 (decisione P5 del developer, lettura (B) del coordinatore delle 11:42, da rivedere dal developer): in un update un
  `cost_basis_override: null` esplicito (la chiave in `model_fields_set`) toglie il costo manuale, importo e valuta, dove il
  tipo e il lato finali della riga lo prendono (`cost_basis_allowed`), e lì N2 rifiuta con `costBasisRequired` (con la
  tabella di oggi sempre: i lati che prendono un costo lo vogliono); altrove, e con Auto, il `null` si ignora (i costi di
  consegna della 47 restano); la chiave assente lascia il costo com'è. Rosso visto, `services transaction-cost-basis-rule`
  80/80. Dettagli: piano 04, sezione W-B30. Residuo → W-B49.
  Commit (riconciliato il 19/10): `54880598b`, treno 111.
- ✅ **W-B31 · La regola 12 del costo è una seconda copia scritta a mano** — minimo, codice; W, 15/10 (N2, test-author).
  `validate_transaction_business_rules` (`backend/app/schemas/transactions/transactions.py`, regola 12,
  `costBasisModeIncompatible`) ammette `cost_basis_mode` solo per TRANSFER e ADJUSTMENT con quantità > 0, a mano, mentre
  N2 legge dai metadati il costo obbligatorio (`cost_basis_required`). Leggerla da `TX_TYPE_METADATA` porterebbe un
  import circolare (`type_metadata.py` importa `transactions.py`): serve spostare la funzione o un import tardivo.
  Dettagli: piano 04, sezione N2.
  ✅ 16/10 (W-B31): la regola 12 chiede `cost_basis_allowed()` (`type_metadata.py`, legge `TX_TYPE_METADATA` al momento
  della chiamata, lo stesso `cbAllowed` del frontend); il ciclo sciolto spostando i gruppi di scambio (`SWAP_GROUPS`,
  `get_swap_group`) in `type_metadata.py` (decisione notturna, da rivedere). Rossi TX-S-092/093. Dettagli: piano 04,
  sezione W-B31.
  Commit (riconciliato il 19/10): `b29f41e51`, dev `4e69b5271` (treno 78).
- ✅ **W-B36 · Le regole 5–11 del batch sono copie scritte a mano dei metadati dei tipi** — minimo, codice; W, 16/10
  (W-B31). `validate_transaction_business_rules` (`backend/app/schemas/transactions/transactions.py`) scrive a mano
  quali tipi vogliono l'asset (regola 5) e la cassa (7), la cassa vietata all'ADJUSTMENT (8), i tipi collegabili a un
  evento (9, con `EVENT_COMPATIBLE_TYPES`), i segni di quantità (10) e di cassa (11); `TX_TYPE_METADATA` ha già
  `asset_mode`, `cash_mode`, `quantity_sign`, `cash_sign`, `event_compatible`, che il frontend legge. Dopo W-B31 il ciclo
  d'import non c'è più: si possono leggere dalla tabella, con un test di parità per tipo e segno come TX-S-090. Da
  verificare prima che le semantiche coincidano (per esempio «free», l'asset facoltativo di INTEREST, FEE e TAX).
  Dettagli: piano 04, sezione W-B31.
  ◐ 16/10 (W-B36): la parte che coincide letta dalla tabella (regole 5, 7, 8, 9, 10, 11; `EVENT_COMPATIBLE_TYPES` tolto),
  rossi TX-S-095…109; i quattro casi in cui la tabella è più severa restano com'è oggi, eccezioni esplicite che
  rimandano alla decisione **P6** del developer (lista del 16/10); il caso 4 si raggiunge anche con un promote (un
  WITHDRAWAL e un DEPOSIT a importo zero promossi). Restano due copie scritte a mano nei testi dell'API (OpenAPI, quindi
  `api sync`): la descrizione di `TXCreateItem.asset_event_id` «(DIVIDEND/INTEREST/ADJUSTMENT only)» e quella di
  `cost_basis_pair` (`type_metadata.py`: «qty<0» per l'indice 0, che vale ≤ 0, ed etichette italiane «Da»/«A»).
  Dettagli: piano 04, sezione W-B36.
  ✅ 16/10 (W-B36b, decisione **P6** del developer: «solo quando cambia il campo interessato»): i quattro punti valgono
  negli update quando cambia il campo (la cassa per i casi 1 e 4, la quantità per il 2 e il 3), confrontato per valore con
  la riga salvata prima del batch (`changed_rule_fields`); un promote cambia il tipo e li controlla tutti; CREATE com'era.
  Codice nuovo `cashNonzero` (4 lingue). Le righe salvate fuori dalla tabella restano modificabili (note, tag, data, valori
  rimandati com'erano); sulla copia dei dati del developer nessuna riga fuori regola (i 4 conteggi a 0). Rossi visti (7 e
  TX-S-110), `services transaction` 96/96. Di W-B36 restano aperte solo le due copie nei testi dell'API qui sopra.
  Dettagli: piano 04, sezione W-B36b.
  Commit (riconciliato il 19/10): `dcb33859f`, dev `4e69b5271` (treno 78).
- ✅ **W-B37 · Il modale dei report del broker cancella in blocco anche i file non cancellabili** — minimo, chiarezza; W,
  16/10 (H, CP-U2, docs-writer). Dopo CP-U2 `FilesTable` nasconde «elimina» sulle righe con `can_delete: false` in
  tutte e due le schede, quindi anche nel modale; ma `handleDeleteMultiple`
  (`frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte:168`) manda tutti i selezionati e riporta i 403,
  mentre la pagina File li salta con l'avviso `uploads.deleteSkipped` (evento `file.delete.skipped`). Cura: filtrare
  `can_delete !== false` prima del ciclo, con la stessa chiave e lo stesso evento. Dopo l'ingresso di CP-U2 di H (la
  chiave e l'evento arrivano con quello). Dettagli: messaggio di H, 16/10 00:31.
  ✅ 16/10: `handleDeleteMultiple` salta i file con `can_delete: false` con l'avviso e l'evento della pagina File; Vitest
  `BrokerImportFilesModal.test.ts` (4 test, 2 rossi prima). Dettagli: piano 04, sezione W-B37.
  Commit (riconciliato il 19/10): `c8da45fc4`.
- ✅ **W-B38 · Gli errori multipli della creazione portano i testi con `{type}` non risolto** — minimo, chiarezza; W, 16/10
  (W-B36, test-author). Con due o più violazioni `TXCreateItem.validate_transaction_rules`
  (`backend/app/schemas/transactions/transactions.py`, `multipleBusinessRuleErrors`) impacchetta per ciascuna
  `e.message_template`, non `e.message()`: il testo arriva in `TXValidationIssue.error` (batch) e in
  `BRIMValidationIssue.message` (import) come «{type} requires asset_id». Cura: `e.message()` (i parametri restano in
  `ctx`); cambia testi visibili nelle risposte (in meglio). W-B36 tiene apposta i testi di prima (letterali per tipo dove
  lo erano). Dettagli: piano 04, sezione W-B36.
  ✅ 16/10: il pacchetto porta `e.message()`, i parametri restano in `ctx`; rossi visti (TX-S-109 rovesciato, G.3.13 nuovo,
  l'import di BRIM), poi `schemas transactions` 105/105, `services brim-create-transaction` 14/14, `api
  transactions-validate` 12/12. Dettagli: piano 04, sezione W-B38.
  Commit (riconciliato il 19/10): `52387e2c0`.
- ✅ **W-B39 · Uno split rifiutato non dice niente all'utente** — basso, chiarezza; W, 16/10 (decisione 47, docs-writer).
  `confirmSplit()` (`frontend/src/routes/(app)/transactions/+page.svelte`) scrive i problemi del batch solo in console.
  Con la 47 uno split si rifiuta anche per un cambio mancante (`WAC_FX_UNAVAILABLE` sull'operazione `split`), e prima già
  per altri codici: l'utente non vede il perché. Proposta: mostrare il problema (toast o pannello, con il codice tradotto).
  Frontend delle transazioni (FE8, dopo il lotto A dei colori). Dettagli: piano 04, sezione «Decisione 47».
  ✅ 16/10: un rifiuto di split o di promozione dalla pagina Transazioni dà un toast d'errore col titolo e i motivi tradotti
  (`utils/transactions/commitRefusal.ts`); un cambio mancante su uno split ha il suo testo (`wacFxUnavailableSplit`, 4
  lingue); la conferma resta aperta. Vitest 63/63, E2E `tx-split-refusal` 2/2 (rosso prima). Toast invece di un riquadro:
  decisione notturna. Dettagli: piano 04, sezione W-B39.
  Commit (riconciliato il 19/10): `df898b445`, treno 98 (`f7ab73409`).
- **W-B40 · Lo split di una coppia non ancora salvata nel Bulk non applica la 47** — basso, numeri; W, 16/10 (decisione
  47, docs-writer). `TransactionBulkModal.svelte` (~933) cambia solo i tipi di una coppia TRANSFER non salvata: l'ADJUSTMENT
  in uscita si crea senza costo e i lotti leggono le unità come distrutte. Da decidere: il backend dà il costo Auto a un
  ADJUSTMENT −q creato che lo chiede (oggi `cost_basis_mode` non è ammesso su un ADJUSTMENT negativo: cambia i metadati),
  oppure il Bulk non scioglie in ADJUSTMENT una coppia non salvata. Dettagli: piano 04, sezione «Decisione 47».
- ✅ **W-B41 · Altri test di `test_broker_multiuser_api.py` lasciano broker e transazioni nel DB condiviso** — minimo, test;
  W, 16/10 (W-B12, test-author). Tutti i test di `TestMultiUserRoles` e `TestEditorRestrictions` tranne
  `test_owner_can_delete_broker` lasciano il loro broker (`create_broker`); MULTI-007, 008b e 008c anche transazioni. Il
  modello è quello di W-B12 (`_Owned`, `_new_broker`, cancellazione in un `finally`). Dettagli: piano 04, sezione W-B12.
  ✅ 16/10: un context manager `_owning` negli 11 test (broker `MULTI00x_<hex>`); `api broker-multiuser` 20/20 senza broker
  né transazioni rimaste (prima +11 e +3). Dettagli: piano 04, sezione W-B41.
  Commit (riconciliato il 19/10): `f2b6c0983`.
- ✅ **W-B42 · `asset-event-delete.spec.ts`: gli scenari 3 e 4 sondano e prendono «il primo»** — minimo, test; W, 16/10
  (W-B29, test-author). Lo scenario 3 (`delete asset with events shows appropriate warning`) usa sonde `isVisible().catch`,
  un `.first()` senza filtro e un filtro per testo `/delete|elimina/i`, e può passare senza asserire nulla; lo scenario 4
  (`event badge reflects current link state`) prende il primo pallino degli eventi e dipende dai collegamenti del mock.
  Solo letture: nessun dato condiviso a rischio. Cura: asset e collegamenti propri, come gli scenari 1 e 2
  (`frontend/e2e/assets/asset-events-owned.ts`), e asserzioni esplicite. Dettagli: piano 04, sezione W-B29.
  ✅ 16/10: scenario 3 su un asset proprio (card per id, conferma col nome, annulla, asset ed evento restano); scenario 4 su un
  DIVIDEND proprio collegato (pallino visibile, scollegato con `asset_event_id: 0`, pallino sparito). E2E 4/4. Dettagli:
  piano 04, sezione W-B42.
  Commit (riconciliato il 19/10): `3564129b5`, treno 98 (`f7ab73409`).
- ✅ **W-B43 · Tre debolezze in `asset-data-editor.spec.ts` e `fx-csv-import.spec.ts`** — minimo, test; W, 16/10 (TC-13,
  trovate dal test-author di T, lotto dei colori). In `frontend/e2e/assets/asset-data-editor.spec.ts` il test 21 sta dentro
  un `if (isVisible)` che non aspetta (può passare senza asserire nulla), e nessun controllo positivo verifica la ✗; in
  `frontend/e2e/fx/fx-csv-import.spec.ts:56` l'asserzione dipende dalla parola «error» (testo tradotto). Cura: dopo il
  lotto W1-g di T (~07:30, che tocca quei file: `asset-data-editor.spec.ts:287`, `fx-csv-import.spec.ts:53,56,289`), coi
  `data-testid`/`data-state` che introduce. Dettagli: messaggio del coordinatore, 16/10 06:07.
  ✅ 16/10 (riconciliato il 17/10): i due spec asseriscono invece di sondare, dev `d6a260c89` (`a59593570`). Restano W-B47 e
  W-B48. Dettagli: piano 04, sezione W-B43.
- ✅ **W-B44 · `PromoteMergeModal` senza `data-testid` univoci** — minimo, test; W, 16/10 (W-B39, test-author). Con la modale
  aperta `promote-merge-modal` trova due elementi, e il suo «Annulla» non ha `data-testid`: un test della promozione con campi
  diversi non li può prendere in modo stabile (oggi nessuno lo fa). Cura: un `data-testid` per elemento, in
  `frontend/src/lib/components/transactions/modals/PromoteMergeModal.svelte`. Dettagli: piano 04, sezione W-B39.
  ✅ 16/10: `promote-merge-modal` solo sul dialogo, `promote-merge-modal-content` sul contenuto, `promote-merge-cancel` su
  Annulla; Vitest `PromoteMergeModal.test.ts` 4/4 (3 rossi prima). Dettagli: piano 04, sezione W-B44.
  Commit (riconciliato il 19/10): `911252a85`, treno 99 (`504f80d9f`).
- ✅ **W-B45 · `transactions-modals.spec.ts`: T13 col tempo di serie di 30 s fra vicini a 60 s** — minimo, test; W, 16/10 (T,
  colori, 08:01). In `frontend/e2e/transactions/transactions-modals.spec.ts:1211` T13 tiene il tempo di serie (30 s), mentre i
  vicini sullo stesso percorso hanno `test.setTimeout(60_000)`: col carico a 43–49 è scaduto prima di ogni controllo; da solo,
  col carico a 30, passa in 3,5 s. Cura: allinearlo ai vicini, in un lotto piccolo dopo l'ingresso del lotto di T (che tocca
  quello spec e i due `TxForm*`) e l'aggiornamento della mia base. Dettagli: messaggio del coordinatore, 16/10 08:01.
  ✅ 16/10: `test.setTimeout(60_000)` in testa a T13. Dettagli: piano 04, sezione W-B45.
  Commit (riconciliato il 19/10): `7ab9add9e`, treno 102 (`70d312a35`).
- **W-B46 · Le regole delle coppie scritte a mano, non lette dalla tabella** — minimo, dati; W, 16/10 (W-B17).
  `_validate_linked_pair` (`backend/app/services/transactions/validation.py`) codifica a mano broker, asset e quantità di
  TRANSFER, CASH_TRANSFER e (da W-B17) FX_CONVERSION, mentre `TX_TYPE_METADATA` dichiara le `pair_field_constraints` e la
  promozione le legge già (`_check_promote_constraints`, `backend/app/services/transactions/promotion.py`). La tabella vuole
  anche `cash_currency: different` per FX_CONVERSION, che nessuna regola di creazione controlla: una FX_CONVERSION nella
  stessa valuta passa dall'API. Leggerla cambia ciò che l'API accetta → da decidere. Cura: le regole delle coppie lette dalla
  tabella, come W-B31/W-B36 per le regole 5–12, con le eccezioni nominate. Dettagli: piano 04, sezione W-B17.
- **W-B47 · La barra di stato dell'editor CSV solo in inglese** — minimo, chiarezza; W, 16/10 (W-B43). In
  `frontend/src/lib/components/ui/data-editor/CsvEditor.svelte` (~507-513) «N valid row(s)», «• N error(s)» e «• duplicate
  …s» sono scritti a mano in inglese, in ogni import CSV (prezzi, eventi, cambi): un utente in IT, FR o ES li legge in inglese.
  Cura: chiavi i18n con plurale ICU (base `csvImport.*`), nelle 4 lingue. File dell'area T dei colori: prima di scriverci,
  avvisare il coordinatore. Anche il piede di `frontend/src/lib/components/ui/data-editor/DataImportModal.svelte` scrive a
  mano «• N error(s)» e «• duplicates», senza `data-state`. Dettagli: piano 04, sezione W-B43.
- ✅ **W-B48 · Altri selettori per testo e un altro `if` vuoto in `asset-data-editor.spec.ts` e `fx-csv-import.spec.ts`** —
  minimo, test; W, 16/10 (W-B43, test-author). In `frontend/e2e/assets/asset-data-editor.spec.ts`: `/Import \(N\)/` (righe
  293, 307, 330, 344, 370, 399, 463, 477; c'è già `data-import-confirm` con `data-valid-rows` e `data-error-count`),
  `button:has-text("Save")` (216, 245, 264, 353, 408) e `toHaveText(/Save \(\d+\)/)` (357; c'è `asset-editor-save-btn`),
  `button:has-text("Cancel")` (220, 277; c'è `asset-editor-cancel-btn`), la classe `span.rounded-full` (259), il glifo ✕
  di un pulsante senza `data-testid` (232). In `frontend/e2e/fx/fx-csv-import.spec.ts`: `'Import (2)'` e `'Import (1)'`
  (178, 196, 223, 264, 397, 479, 490), `text=Discard import` (280; c'è `data-import-discard-confirm`), `hasText: 'Cancel'`
  (291; c'è `data-import-cancel`), e il test 14 («info banner reflects current direction», 319–336) dentro due `if (count()
  > 0)` che lo fanno passare senza asserire nulla (lo stesso difetto del test 21). Cura: i `data-testid` e gli attributi che
  esistono già, nessun codice di prodotto; tranne il ✕, che chiede un `data-testid` (file dell'area dei colori). Dettagli:
  piano 04, sezione W-B43.
  ✅ 17/10: i due spec senza selettori per testo né classi (`data-import-confirm` con `data-valid-rows`, `asset-editor-save-btn`/
  `-cancel-btn`, `tab-badge` con `data-badge`, `data-import-discard-confirm`, `data-import-cancel`), il test 14 asserisce, e i due glifi
  su `data-testid` nuovi (`asset-detail-editor-close`, `fx-import-swap`, OK del coordinatore). Dettagli: piano 04, «W-B48».
  Commit (riconciliato il 19/10): `080f7ee7f`, dev `4bc6b2ab1`.
- **W-B49 · Svuotare il costo nel modulo: il rifiuto arriva solo a «Salva tutto», e tre testi dicono ancora «vuoto = Auto»**
  — minimo, chiarezza; W, 16/10 (W-B30, docs-writer). (1) Ogni modifica passa dalla Bulk, che apre il modulo; il controllo
  dal vivo del modulo su una coppia (`collectDualUpdates` → `diffDualItem`,
  `frontend/src/lib/utils/transactions/txPayloadHelpers.ts`) lascia fuori un costo manuale svuotato: la gamba ricevente
  costruita da `buildDualCreatePayloads` non ha la chiave `cost_basis_override` quando il campo è vuoto. Il costo non resta
  in silenzio (il «Salva tutto» della Bulk passa da `buildUpdateDiff`, che manda il `null`, e W-B30 lo rifiuta), ma l'utente
  vede il rifiuto solo lì. (2) Il tooltip `transactions.costBasisOverride.tooltip` («If empty, auto-calculated from
  purchases at save», 4 lingue, `WacPreviewSection.svelte:352`) e la riga «Normal transfer» della tabella di
  `mkdocs_src/docs/financial-theory/instruments/transaction-types/adjustment.en.md:95` («Leave empty — auto-calculated»; IT
  e FR alla 76–77) dicono ancora che vuoto vuol dire Auto: da N2, vuoto in **Manuale** è rifiutato e l'Auto si sceglie.
  Cura: `diffDualItem` manda `null` quando la bozza non ha costo e la riga salvata sì, come `buildUpdateDiff`, con un rosso
  Vitest; i testi riscritti nelle 4 lingue (file `.ts`, `.json` e `.md`, nessun `.svelte`). Dettagli: piano 04, sezione
  W-B30.
- **W-B50 · Quattro debolezze nei due spec del wizard di import** — minimo, test; W, 16/10 (IW-8: note del lotto dei
  colori dell'import, passate dal coordinatore). In `frontend/e2e/transactions/tx-brim-import.spec.ts`: (1) T4 (221–243)
  asserisce dentro due `if (… isVisible …)` che saltano il controllo proprio quando qualcosa si rompe; (2) la guardia
  esterna di T3 e T4 cerca il testo tradotto `text=Resolve Assets` (200, 232), mentre la sezione ha
  `data-testid="import-wizard-resolve-section"` (`frontend/src/lib/components/transactions/wizard/ReviewStep.svelte:116`);
  (3) T1 non importa mai col suo campione: il ramo `if (isEnabled)` (160) non gira. In
  `frontend/e2e/transactions/tx-import-resolution.spec.ts`: (4) i commenti del «badge ambra» (riga 43 e IWR-001, 478)
  diventano falsi coi lotti dei colori dell'import. Cura: solo i due spec, coi `data-testid` che esistono; dopo l'ingresso
  del lotto di IW (`48ecea1e2`, che tocca T4 alle righe 234–235) e l'aggiornamento della mia base. Dettagli: piano di IW,
  `LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/IW-importColors/plan-phase00ImportColors.prompt.md`
  (sul ramo di IW), passo 1, «Spec T4».
- ✅ **W-B51 · La tolleranza dei duplicati BRIM è grossa per le quantità crypto** — minimo, dati; W, 16/10 (C-97, analisi).
  `detect_tx_duplicates` (`backend/app/services/brim/brim_provider.py`, ~2156) confronta le quantità con
  `QUANTITY_TOLERANCE = Decimal("0.0001")`: con le quantità a 10 decimali di C-97, due acquisti di bitcoin diversi lo stesso
  giorno (0,00015 e 0,00008 BTC) coincidono sulla quantità, e un import che li ritrova li segna come doppioni probabili
  (deselezionati per default) se anche l'importo coincide a 0,01. Cura: una tolleranza relativa alla scala (o l'uguaglianza,
  ora che le quantità tornano esatte), con un rosso; dopo C-97a. Dettagli: piano 04, sezione C-97.
  ✅ 17/10 (D-W51-1, coordinatore): uguali arrotondate half-up alla scala della meno precisa (`normalize()`) e mai oltre 0,0001
  (`_same_quantity`); una quantità salvata illeggibile non è più un `TypeError`. 4 rossi, 7 guardie. Resta il gemello del wizard:
  W-B81. Dettagli: piano 04, «W-B51».
  Commit (riconciliato il 19/10): `52573b4aa`, dev `4bc6b2ab1`, CHANGELOG `c97001b80`.
- ✅ **W-B52 · Svuotare il massimo di un prezzo rifiuta la data** — minimo, dati; W, 16/10 (C-97a, test-author). In
  `bulk_upsert_prices` (`backend/app/services/assets/price_store.py`, ~194–197) il controllo OHLC confronta i valori
  ricevuti, sentinella compresa: con `high = -1` (svuota il massimo), da solo o con `low = -1`, vale `low <= close <= -1`,
  falso, e la data è scartata come «impossible OHLC (close outside [low, high])» invece di svuotare il campo. Cura: il
  controllo sui valori dopo la fusione delle sentinelle (`merged_low`, `merged_high`), con un rosso. Dettagli: piano 04,
  sezione C-97a.
  ✅ 17/10 (riconciliato il 19/10), da X (X-R46): un limite cancellato (la sentinella −1) non è più un limite, la chiusura si confronta solo con due limiti veri; `88d0fb840`, dev `2c43ac451`.
- ✅ **W-B53 · La prima analisi BRIM dopo l'avvio supera i 30 s del test** — minimo, test e prestazioni; W, 16/10 (J-30 di J,
  passato dal coordinatore; visto da H, J e forse MF). Il primo `POST /brokers/import/files/{id}/parse` dopo l'avvio del
  server crea il pool di processi BRIM (`_get_pool`, `backend/app/services/brim/brim_parse_pool.py`, `forkserver`): sotto carico
  ci mette 31–49 s, contro i 30 s fissi di `backend/test_scripts/test_api/test_brim_api.py` (`TIMEOUT`, `TestParseEndpoint`);
  poi circa 1 s. Anche un utente aspetta il primo import. Cura (proposta di J): **scaldare il pool all'avvio**, in background,
  come fa già il calendario dei mercati (`start_market_holiday_prewarm`, `backend/app/services/platform/app_lifespan.py`),
  oppure una fixture che lo scaldi prima dei test a tempo; **non** un tempo più lungo. Un lotto piccolo dopo C-97a. Dettagli:
  messaggio del coordinatore, 16/10 17:45. **Chiusa da W il 16/10** (commit al checkpoint di W-B53): il forkserver precarica
  il modulo BRIM e i plugin (`backend/app/services/brim/brim_parse_preload.py`), e il passo d'avvio `brim-parse-pool` lo
  scalda in background, **opzionale** (decisione N56: `LIBREFOLIO_BRIM_PREWARM`, `backend/app/config/brim.py`, spento in
  produzione, acceso in modalità test); `api brim` 118/118 col server di test scaldato. Dettagli: piano 04, sezione W-B53.
  Commit (riconciliato il 19/10): `193412cdf`.
- ✅ **W-B54 · Un'azione `api` lanciata da sola non rifà gli utenti di fixture** — minimo, test; W, 16/10 (C-97a, slot API). Il
  setup della categoria `api` (`_api_setup`, `scripts/test_runner/_backend_api.py`: `db_populate(force=True)`) gira solo con
  la categoria intera; `dev.py test … api brim` da solo usa il DB com'è, e dopo una prova `services` (che lo ricrea vuoto) i
  test che entrano come `e2e_test_admin` cadono sulla loro premessa (401, «the api setup, db populate, seeds it»): 6 rossi su
  118 il 16/10, verdetto ambiente. Cura: il runner rifà il seed quando un'azione `api` singola trova il DB senza gli utenti
  di fixture, o lo dice prima di partire. Registro del runner: superficie condivisa, decide il coordinatore. Dettagli: piano 04,
  sezione C-97a.
  ✅ 16/10 (riconciliato il 19/10): `74b420db8` «fix(test-runner): one api action reseeds fixtures».
- ✅ **W-B55 · La 47 in un'altra valuta non ha una prova da capo a fondo** — minimo, test; W, 16/10 (decisione 47 con J-24).
  La gamba che cede prende il costo Auto del suo broker nella valuta dell'ultimo acquisto (`_handover_cost`,
  `compute_wac_iterative`), e con J-24 la Dashboard ne realizza la differenza di cambio nel giorno della consegna. Oggi è
  coperto in due metà: i test di W scrivono la riga in EUR (più i casi di cambio mancante), il «foreign book» di J
  (`test_adjustment_out_with_cost_numbers.py`) la legge in USD. Cura: un caso in `test_orphan_transfer_after_broker_delete.py`
  con un titolo comprato in USD e il rapporto in EUR, dalla cancellazione del broker che riceve ai numeri di lotti e
  Dashboard. Dettagli: piano 04, sezione «Decisione 47 in dev: la prova con J-24».
  ✅ **Fatto da J il 17/10**: `TestOrphanOutgoingTransferInAnotherCurrency` (controllo a mano e orfana vera, in USD con report in EUR); riga, Dashboard, lotti e parità tornano ai valori derivati a mano. Nessun difetto.
- **W-B56 · Il costo medio dell'anteprima esce senza arrotondamento** — minimo, numeri; W, 16/10 (C-97a, E2E di FE8b).
  `compute_wac_iterative` (`backend/app/services/portfolio_service.py`, casa di MF) rende la media con tutte le cifre del
  quoziente (100 / 3 = 33.333…): l'anteprima la mostra, il commit in Auto la scrive, e se un utente la «congela» in un
  costo manuale la conferma la rifiuta (oltre 12 decimali, D2). Proposta del coordinatore: `round_computed_value` alla
  fonte, come D6 per i valori calcolati. Da decidere con MF (avvisato dal coordinatore). La parte urgente, il controllo
  dei decimali che rifiutava l'importo di un costo Auto, è nel checkpoint «C-97a, il costo Auto». Dettagli: piano 04.
- **W-B57 · Il picker del Bulk ha 5 s per aprirsi, pochi sotto carico** — minimo, test; colori (TC-17), 17/10. In
  `frontend/e2e/transactions/tx-picker-pagination.spec.ts`, `openPicker` (:59-70) aspetta il pulsante 3 s (:63) e la modale 5 s
  (:67), poi le righe 10 s: al carico 90–140 la modale arriva oltre i 5 s. Cura: un budget unico e legato a uno stato osservabile
  (il frame e la prima riga `data-row-id` con lo stesso tempo, o uno `data-state` della modale), mai un'attesa nuda; dopo C-97b o in
  un lotto di spec. Dettagli: TC-17 del team colori, via il coordinatore.
- ✅ **W-B58 · Un valore enorme blocca gli asset di tutti (C-97a)** — medio, sicurezza e dati; E, 17/10 (R13-SEC2,
  reperto 1, MEDIUM 8/10; note 1, 2, 4, 5). `RealDecimal` solleva leggendo un REAL ±inf o da 1e54 in su, e nessuno limita la
  grandezza (`1E+60` passa `decimal_limit_issue`): un BUY da `1E+60` su un broker con scoperto e short dà 500 a ogni utente su
  `/assets/all`, e un provider che risponde `1e400` rende illeggibile la riga di oggi del prezzo. Cura: una lettura che non
  solleva mai, il limite delle cifre intere a ogni scrittore (codice `integerDigitsExceeded`), il prezzo corrente troncato, la
  promozione controllata, i blocchi dei provider senza eccezioni a metà. Da chiudere prima del rilascio. Cifre intere: 15 per
  quantità e importo (decisione notturna N63 del coordinatore, da rivedere col developer), le altre colonne come dichiarate (12
  prezzi, costo per unità e valore dell'evento; 24 il volume). Dettagli: piano 04, sezione «W-B58 e W-B59».
  ✅ 17/10 (riconciliato): entrato con W-B59, dev `4e9d1815f` (`94fbd54fd`). Dettagli: piano 04, «W-B58 e W-B59».
- ✅ **W-B59 · Il precaricamento del pool BRIM ferma il server al primo import (W-B53)** — medio, disponibilità; E, 17/10
  (R13-SEC2, nota 12, 9/10, provata). `_get_pool()` imposta il precaricamento anche col prewarm spento: su 3.13 il primo parse
  dopo un avvio blocca il loop per tutto l'import di BRIM (~4 s a riposo, 30–50 s sotto carico), contro N56. Cura: il
  precaricamento solo col prewarm acceso. Dettagli: piano 04, sezione «W-B58 e W-B59».
  ✅ 17/10 (riconciliato): il pool si precarica solo col prewarm acceso, dev `4e9d1815f` (`e69544f79`). Dettagli: piano 04,
  «W-B58 e W-B59».
- ✅ **W-B64 · Il Form accetta 12 cifre intere per la quantità, il backend 15 (N63)** — minimo, chiarezza; W, 17/10 (C-97b). Le tre
  quantità del Form (`features/transactions/form/TxFormSingleSection.svelte` ×2, `TxFormPairSection.svelte`) hanno
  `maxIntegerDigits={12}`: una quantità da mille miliardi in su è segnata invalida nel Form, mentre il backend la accetta (N63:
  15). Gli importi non hanno un limite intero nel Form. E `ExactDecimalInput` conta gli zeri finali (`0.10000000000`, 11
  decimali, è rifiutato a 10), mentre il backend e la mini-modale degli eventi non li contano. Cura: `maxIntegerDigits={15}` e la
  guardia `1000000000000.1` di `TransactionFormModal.test.ts` spostata a 16 cifre intere, dopo che il developer ha confermato N63;
  gli zeri finali non contati nel budget dei decimali (anche il PAC usa il componente). Dettagli: piano 04, sezione «C-97b — i
  decimali in input: la cura».
  ✅ 17/10 (riconciliato il 19/10), fatta da B per il bilanciamento del carico: `2b3c9e8d7`, dev `cde76dc54`. B ha aperto B-47 e B-48 nella sua sezione (in K3a, parcheggiato).
- ✅ **W-B65 · «Applica» senza modifiche su una SELL nel Bulk mostra il segno e chiede di scartare** — minimo, chiarezza; W, 17/10
  (test-author, guardia E2E di C-97b). Aprendo una SELL esistente nel Bulk e premendo «Applica» nel Form senza toccare nulla, la riga
  riprende i campi dal payload del Form, che porta il segno: la cella mostra `-0.00000001` invece della grandezza, e chiudendo il
  Bulk si chiede di scartare modifiche che non ci sono. Precedente a C-97b (la guardia chiude con «Annulla»). Da verificare con un
  rosso, poi l'«Applica» riporta il segno della convenzione del Bulk (grandezza). Dettagli: piano 04, sezione «C-97b — i decimali in
  input: la cura».
  ✅ 17/10 (riconciliato il 19/10), fatta da B, con W-B64: `2b3c9e8d7`, dev `cde76dc54`.
- ✅ **W-B66 · Il campo decimale: un esponente incollato cambia il numero, un incolla enorme blocca la scheda** — basso, numeri e
  disponibilità; E, 17/10 (R13-SEC5, revisione di C-97b, sotto la soglia). Tre note: (1) `filterDecimalInput`
  (`frontend/src/lib/utils/core/parseDecimalInput.ts`) toglie ciò che non è cifra, punto, virgola o il meno iniziale, quindi un
  `1e-8` incollato diventa `18`, visibile ma senza un avviso (precedente al lotto); (2) un incolla enorme blocca la scheda di chi
  incolla: `ExactDecimalInput` confronta coi limiti `min`/`max` con `10n ** places` (le cifre decimali incollate), e la cella del Bulk
  passa il testo da `formatDecimalForDisplay`, la cui regex `^-?\d*\.?\d*$` torna indietro in modo quadratico su un testo lungo che
  non combacia (solo il proprio browser); (3) il toast di «+ New event» mostra 2 decimali (`parseFloat`, `formatFixed`): va con
  C-97c. Cura: (1) un esponente incollato letto esatto o rifiutato col messaggio; (2) un tetto alla lunghezza del testo prima del
  confronto e una regex lineare; (3) in C-97c. Dettagli: piano 08 di E, «R13-SEC5».
  ✅ 17/10 (D-W66-1 = (a), coordinatore). Un testo incollato interamente in notazione scientifica si legge esatto entro ±100 (il
  limite del backend), in `filterDecimalInput` e in `normalizeDecimalInput` per ogni campo che legge da lì: `1e-8` →
  `0.00000001`. Un testo con un esponente che non si legge (fuori portata, o non interamente un numero: `1e5x`) resta com'è,
  rosso, con `common.decimalExponentOutOfRange` (4 lingue). Le frecce non lo spostano. Le tre regex quadratiche sono lineari
  (circa 3 s a 40 000 caratteri), e `compareExact` gira solo nel budget delle cifre. Prove: 88 rossi verdi (Vitest 231),
  `core-unit` 8 589, `component-unit` 4 821, `front check` 0/0. Il punto (3) resta in C-97c. Dettagli: piano 04, «W-B66 — cura».
  Commit (riconciliato il 19/10): `b8e180ff8`, dev `e820279e1`, CHANGELOG `731140500`.
- ✅ **W-B67 · Il costo Auto può finire sulla riga sbagliata** — medio, numeri; J, 17/10 (analisi di V-4, via il coordinatore). Prima
  del rilascio. `_find_created_tx_for_wac` (`backend/app/services/transactions/auto_cost.py:158-183`) trova la riga creata di un
  elemento senza `link_uuid` cercando l'ultima con lo stesso broker, asset, data e tipo (`order_by(id.desc()).limit(1)`): con due
  ADJUSTMENT Auto non collegati nello stesso giorno in un batch, il primo non riceve mai il costo e si salva senza (come Auto salta il
  controllo del costo), il secondo lo riceve due volte; e un Auto seguito da un Manuale con la stessa chiave sovrascrive il costo
  Manuale con la media. Cura: la riga di ogni elemento dalla mappa che la creazione già conosce (indice → riga), senza la ricerca per
  campi; rossi prima. Dopo W-B60. Dettagli: piano 04, sezione «W-B67» (quando parte).
  Analisi (17/10, W): c'è un secondo difetto. Le righe Auto dello stesso batch non ancora costate entrano a zero nelle medie delle
  altre, e il risultato segue l'ordine degli indici (BUY 10 a 100, due Auto +5 lo stesso giorno: con la sola mappa 66,67 e 88,89).
  **Decisione N84** (D-W67-1 → P1, coordinatore 17/10): ogni create sulla propria riga; le righe Auto in ordine di data del loro
  gruppo, poi per indice; quelle non ancora costate (salvo le legate a uno split) fuori dai gruppi delle altre. Lo stesso costo che
  avrebbero salvate una alla volta in ordine di data. Dettagli: piano 04, «W-B67 — … analisi» e «W-B67 — cura».
  ✅ 17/10: `context.created_by_index` (la riga di ogni create, da `apply_creates`) al posto della ricerca per campi
  (`_find_created_tx_for_wac` tolta); le righe Auto in ordine di data del gruppo, poi le create per indice e gli update per indice;
  quelle non ancora costate (salvo le legate a uno split) fuori dai gruppi delle altre. 4 rossi verdi (`transaction-cost-basis-rule`
  171); `transaction` 125, `transaction-decimal-places` 201, `auto-cost-unreadable-pool` 17, `lone-transfer-legs` 20,
  `orphan-transfer-numbers` 21, `roi-fifo-utils` 1 312, `broker` 81. Slot prima dell'ingresso: `api transactions-wac` 20,
  `portfolio-wac` 12, `batch-split-promote` 38; E2E `tx-wac-bulk` 11, `tx-wac-formmodal` 10, `tx-transfer-auto-cost` 2. Dettagli:
  piano 04, sezione «W-B67 — cura».
  Commit (riconciliato il 19/10): `279b3d5bd`, dev `ac92e6fae`, CHANGELOG `f078b766c`.
- ✅ **W-B68 · I valori degli eventi dei provider non sono troncati alla colonna** — basso, numeri; W, 17/10 (W-B60, docs-writer). I
  prezzi dei provider si salvano troncati a ciò che la colonna tiene (`storable_value`, `truncate_priceHistory`), i valori degli eventi
  dei provider no: `_storable_events` (`backend/app/services/assets/event_store.py`) ne controlla solo la grandezza. Con la lettura di
  `RealDecimal(18, 6)` (W-B60) un valore con più di 6 decimali si rilegge arrotondato, e un pareggio arrotonda in modo diverso da prima
  (`784.0774475`: prima `…447`, ora `…448`, 0,000001); un valore di 10 o più cifre intere può superare le 15 significative. Cura:
  `storable_value(value, AssetEvent, "value")` anche per gli eventi dei provider, come i prezzi (letto = scritto). Dettagli: piano 04,
  sezione «W-B60».
  ✅ 17/10: `_storable_events` (`event_store.py`) tronca col `storable_value` di `AssetEvent.value`, solo quando il numero cambia
  (la forma resta), e giudica il rapporto dello split sul valore troncato (`1E-7` si scarta, prima si rileggeva 0). 12 rossi verdi
  (`asset-digit-limits` 99), `event-split-ratio` 78, `asset-event-store` 71, `asset-source-guards` 29, `asset-source-refresh` 18,
  `asset-source` 61. Residuo di X: i valori degli eventi di un piano d'investimento programmato (parametri dell'utente) oltre i 6
  decimali si troncano in silenzio; rifiutarli all'ingresso è del provider. Dettagli: piano 04, sezione «W-B68».
  Commit (riconciliato il 19/10): `b1981a17b`, dev `06e9d2c20`, CHANGELOG `cc2e9307c`.
- ✅ **W-B60 · Gli importi tornano col rumore del double (C-97)** — minimo, numeri; W, 17/10 (W-B58, N63). `Transaction.amount` e
  `AssetEvent.value` sono `Numeric(18, 6)`, che SQLAlchemy rilegge col formato `'%.6f'`: da 11 cifre intere il rumore del double
  compare nei decimali (`123456789012.345` torna `123456789012.345001`; con le 15 cifre intere di N63 `99999999999999.9` torna
  `99999999999999.906250`). Gli importi interi (VND, IDR) tornano esatti. Cura: `RealDecimal(18, 6)` (stesso DDL, nessuna
  migrazione), dopo aver controllato le `SUM` in SQL su quelle colonne; rossi prima. Chiude anche metà di W-B63. Dettagli: piano 04,
  sezione «W-B58 e W-B59».
  ✅ 17/10 (riconciliato): importi e valori degli eventi letti esatti, dev `484c71afb`. Dettagli: piano 04, «W-B60».
- ✅ **W-B61 · I cambi senza limite di grandezza (classe di W-B58)** — medio, dati; W per X, 17/10 (W-B58). Il cambio manuale
  (`api/v1/fx/currencies.py:92` → `services/fx/storage.py:60`) non ha limite: `1E+400` si salva come REAL inf, e il suo inverso
  `1E-400` come 0; dei provider, `truncate_fx_rate` (`db/precision.py`) solleva `InvalidOperation` da `1E+50`. Codice di X (il
  coordinatore lo avvisa). Cura: `decimal_limit_issue` e `storable_value` di W-B58 sulla colonna `FxRate.rate`. Dettagli: piano 04,
  sezione «W-B58 e W-B59».
  ✅ 17/10 (riconciliato), da X: i cambi che non si salvano rifiutati o saltati, `80f5c65ff`.
- ✅ **W-B62 · `/prices/current` risponde per intero un prezzo enorme del provider** — basso, disponibilità; W, 17/10 (R13-SEC2, nota
  6). Il serializzatore `format(v, "f")` (`backend/app/schemas/common.py:47`) scrive per intero un `1E+50000000`: ~50 MB per
  risposta, che la cache di 2 minuti riserve. Dopo W-B58 il valore non si salva più, ma la risposta lo porta ancora. Cura: la
  quotazione non memorizzabile risponde come non disponibile, o il serializzatore rifiuta un esponente oltre una soglia. Analisi
  (17/10): anche la cache di 2 minuti e il delta del refresh la portano; proposta al confine del provider, mai nel serializzatore.
  **Passata a X** (coordinatore, 17/10 03:4x), con la sua X-R40; i rossi scritti da W gli vanno consegnati. Dettagli: piano 04,
  sezioni «W-B58 e W-B59» e «W-B62 e W-B63».
  ✅ 17/10 (riconciliato), da X (X-R40): dev `fd6886bb0`. Resta W-B63 (D-W63-1).
- **W-B63 · Un inf già salvato in una colonna `Numeric` rompe le risposte** — basso, dati; W, 17/10 (W-B58). Importo, valore di
  evento, volume e cambio si rileggono `Decimal('Infinity')` (formato `'%.Nf'`), che il JSON scrive `Infinity`. Solo dati scritti
  prima di W-B58 o a mano. Importo e valore dell'evento li chiude W-B60 (letti `None`, mai più scritti); volume e cambio restano.
  E dopo W-B60 la query degli eventi (`query_events_bulk`) fallisce ancora su un valore `None` (`Currency(amount=None)`): una riga
  così va saltata, con un avviso. Analisi (17/10): una correzione post-migrazione che annulla o cancella gli inf ricavabili e
  riporta quelli dell'utente, più due guardie puntuali; decisione D-W63-1. Dettagli: piano 04, sezioni «W-B58 e W-B59», «W-B60» e
  «W-B62 e W-B63».
- ✅ **W-B69 · Il costo Auto si calcola saltando una riga illeggibile (regressione di W-B58)** — medio, numeri; W, 17/10 (all-backend di
  W-B60, approvata dal coordinatore: **blocca il rilascio**). Da W-B58 una quantità o un importo illeggibile si legge `None` invece di
  sollevare: `compute_wac_iterative` carica la riga e `cost_movement_from_transaction` (`financial_math/average_cost.py`) la salta, e
  un importo `None` diventa un acquisto gratuito. Così la media di un costo Auto (batch, divisione di una coppia TRANSFER, gambe sole,
  cancellazione di un broker) esce senza quella riga, per sempre; i 2 rossi di `test_lone_transfer_legs.py` sono rossi anche in dev.
  Cura: `UnreadablePoolError` in `_auto_cost` (`backend/app/services/transactions/auto_cost.py`), la ragione per gamba, la
  cancellazione che fallisce intera, nel batch l'issue `autoCostUnreadable` `{count}` (4 lingue) e lo stop; rossi prima. Dopo
  SEC7-3. Dettagli: piano 04, sezione «W-B69».
  ◐ 17/10: il cuore è di **MF** (coordinatore, 08:1x): `UnreadablePoolError` in `_auto_cost`, le gambe sole, `delete_by_broker`, il
  cucito per riga `_compute_wac_for_auto_items(..., unreadable=lista)`; dentro in dev `c61a2db4d` (`1b4e4a27d`), rivisto da W: ok.
  **Resta a W la metà del batch** (`autoCostUnreadable` sulla riga Auto e sulla divisione, i18n, il paragrafo di `wac.md`), dopo
  l'entrata di SEC7-3; i rossi sono parcheggiati in `files/wb69_mine/` della sessione di W. Nel frattempo un batch che incontra un insieme
  illeggibile risponde 500, non più un costo sbagliato. Dettagli: piano 04, «Revisione del lotto di MF».
  ✅ 17/10: la metà del batch di W — `autoCostUnreadable` `{count}` sulla riga Auto e sulla divisione di una coppia TRANSFER (4
  lingue), niente più 500; più il pavimento di N74 condiviso (`EARLIEST_RANGE_START` di MF-SEC8-2 al posto di `TRANSACTION_DATE_MIN`).
  33 rossi verdi, `services transaction-cost-basis-rule` 137. Dettagli: piano 04, «W-B69 — la metà del batch».
- ✅ **W-B70 · L'unione di una promozione propone una descrizione che il backend rifiuta, in inglese** — minimo, chiarezza; W, 17/10
  (H-41). La descrizione unita (`mergeStrings`, `frontend/src/lib/features/transactions/bulk/promoteHelpers.ts`: `a\nb`) di due
  descrizioni lunghe supera i 500 caratteri che create, update e (da H-41) i campi uniti accettano: il salvataggio la rifiuta con
  `string_too_long`, che `PYDANTIC_BUILTIN_KEYS` (`resolveValidationMessage.ts`) non traduce («Descrizione: String should have at most
  500 characters»; lo stesso per una create o un update troppo lunghi). Cura: la modale d'unione mostra il conteggio e avvisa oltre 500;
  `string_too_long` tradotto (con `max_length` dai `ctx` dell'errore, che il parse del batch oggi scarta). Dettagli: piano 04, sezione
  «H-41 dentro SEC7-3».
  Allargata il 17/10 (nota di H nella revisione di W-B75): lo stesso vale per ogni errore di campo con un contesto di dati semplici,
  che il batch (`_lone_error_params`, W-B72) e il parse BRIM (W-B75) passano con `params` nulli. Un `greater_than` su `id_a`/`id_b`
  (split e promozione) o su `from_tx_id` (la vecchia promozione), solo da API, arriva senza `{gt}`, e
  `transactions.pydantic.greaterThan` («Value must be greater than {gt}») resta senza il valore. Cura con questa voce: il contesto di
  dati semplici anche per gli errori di campo, nelle due copie della regola, rossi prima (i rifiuti di H-41 e del batch che oggi
  fissano `params` nulli cambiano contratto).
  ✅ 17/10 (D-W70-1…5, coordinatore): ogni errore porta come `params` il suo contesto di dati semplici, anche di campo
  (`{max_length: 500}`, `{gt: 0}`, `{ge: 0}`), e i sotto-errori impacchettati passano dallo stesso filtro, in un solo modulo
  (`backend/app/utils/pydantic_errors.py`, W-B77); `string_too_long` tradotto (`transactions.pydantic.stringTooLong`, 4 lingue) e
  l'etichetta del ramo dei built-in escapata; la modale d'unione conta in punti di codice e blocca Conferma oltre 500; «Unisci tutto»
  lascia la coppia troppo lunga, con un avviso. Rossi: backend 66, frontend 34, l'E2E PC7. Dettagli: piano 04, «W-B70 (+ W-B77) — cura».
  Commit (riconciliato il 19/10): `c95eb0cf0`, dev `41335f1e1`, CHANGELOG `c9ebc1102`.
- ✅ **W-B71 · Il suggerimento di promozione (ed eventi) va in 500 con una data ai bordi del calendario** — basso, disponibilità; W, 17/10
  (SEC7-3). `promote_suggest_bulk` (`backend/app/services/transactions/promotion.py`) calcola `inp.date ± timedelta(days=tolerance_days)`
  (0–30, 7 di default): con `0001-01-01` o `9999-12-31` un `OverflowError`, un 500 per quella richiesta sola (niente memoria né CPU); da
  verificare lo stesso giro nel suggerimento degli eventi (`schemas/transactions/event_suggest.py`, 0–7). Cura: le date di input nei
  limiti di N74 (un 422 al confine) o la finestra tagliata ai bordi. Dettagli: piano 04, sezione «R13-SEC7-3 — cura».
  Analisi (17/10): **tre** punti, non due — anche `get_balances_at_end_of` (`balances.py`), con l'`as_of` del gap-fix BRIM dalla
  richiesta; cura scelta: un aiuto `shift_date` che satura a `date.min`/`date.max` (non un 422: le richieste di suggerimento sono a
  lotti). Ordine approvato: dopo W-B74. Dettagli: piano 04, «W-B71, W-B72, W-B74 — analisi».
  ✅ 17/10 (prima di W-B74, ordine cambiato col coordinatore): `shift_date` (`utils/datetime_utils.py`) nei due suggerimenti e nei
  cinque `± 1 giorno` di `brim_report_sets.py` (date del file caricato: perimetro allargato, approvato), `get_balances_at_end_of` con una
  query inclusiva (una riga del `9999-12-31` conta); rossi in 5 file, verdi nello slot (`utils datetime` 39, `brim-gap-fix` 106,
  `brim-report-sets` 274, `api batch-split-promote` 38, `api events-suggest` 11). Dettagli: piano 04, sezione «W-B71 — cura».
  Commit (riconciliato il 19/10): `b801dc687`, dev `1431e20df`, CHANGELOG `2dddaa95d`.
- ✅ **W-B72 · Il costo unito di una promozione finisce su entrambe le righe di una coppia di cassa** — basso, numeri; W, 17/10 (H-41,
  docs-writer). `_apply_promote_cost_basis` (`backend/app/services/transactions/batch_creates.py`) scrive il costo sulla gamba di
  quantità positiva, ma su **entrambe** quando nessuna ne ha una (una coppia di cassa: FX_CONVERSION, CASH_TRANSFER), e dopo la pulizia
  di `cost_basis_allowed`: un client dell'API può lasciare un costo per unità su righe che non ne prendono. L'interfaccia non manda il
  costo (solo descrizione e tag). Da verificare se `validate_cost_basis` lo rifiuta dopo; cura probabile: lo stesso
  `cost_basis_allowed` sul costo unito, rosso prima. Dettagli: piano 04, sezione «H-41 dentro SEC7-3».
  Analisi (17/10): nessun numero sbagliato (la matematica salta una riga a quantità 0), ma il buco è più largo: nemmeno create e update
  rifiutano un `cost_basis_override` su un tipo che non ne prende (la regola 12 guarda solo `cost_basis_mode`). **Decisione notturna
  N78** (D-W72-1 → b, coordinatore 08:39, da rivedere col developer): la regola 12 estesa a `cost_basis_override` su ogni scrittura,
  codice `costBasisNotAllowed {type, qty}`, le righe già salvate restano; più la chiave mancante di `costBasisModeIncompatible` (oggi
  in inglese grezzo) e un cancello sui codici delle regole. Ordine: dopo W-B71. Dettagli: piano 04, «W-B71, W-B72, W-B74 — analisi».
  **N78 raffinata** (coordinatore, 17/10, dai rossi): **tranne un ADJUSTMENT a quantità < 0**, il costo di consegna della decisione 47,
  che la decisione 4 lascia mettere a un update dello stesso batch dello split. Con la cura: un errore di regola da solo tiene i suoi
  `params` (oggi solo quelli impacchettati), e il vecchio `promote_transfer` rifiuta un costo su un FX_CONVERSION invece di lasciarlo
  cadere. Dettagli: piano 04, sezione «W-B72 — … (N78): cura».
  ✅ 17/10: regola 12b (`cost_basis_set`, `costBasisNotAllowed {type, qty}`, tranne un ADJUSTMENT −q) su create e update;
  `_resolved_cost_issues` per il costo unito di una coppia di cassa; `_lone_error_params` in `_parse_lenient`; `promote_transfer`
  rifiuta un costo su FX_CONVERSION; `costBasisNotAllowed` e `costBasisModeIncompatible` in 4 lingue, cancello su tutti i codici delle
  regole (22). 21 rossi verdi: `transaction-cost-basis-rule` 164, `transaction` 125, `transaction-decimal-places` 201; BRIM
  (`brim-create-transaction` 14, `brim-gap-fix` 115, `external brim-providers` 736) e gate i18n verdi. Dettagli: piano 04, sezione
  «W-B72 — … (N78): cura». Dopo l'ingresso, un rosso di dev (X): il cancello dell'HTML
  (`frontend/src/htmlInterpolation.gate.test.ts`) non ammetteva il `<b>` delle due chiavi nuove. Ora sono testo semplice; il
  cancello dà 26 verdi e `core-unit` 8 378 verdi.
  Commit (riconciliato il 19/10): `e71b68d50`, dev `7bc66c7ca`; il cancello HTML `21b8aa975`, dev `5603a23a7`.
- ✅ **W-B75 · Un errore di campo di un plugin BRIM può rendere la risposta del parse non serializzabile** — minimo, disponibilità; W,
  17/10 (W-B72). `BRIMProvider._create_transaction` (`backend/app/services/brim/brim_provider.py`) copia in `params` il contesto di ogni
  errore solo così com'è; quello di un `value_error` porta l'oggetto eccezione, e `BRIMValidationIssue.model_dump(mode="json")` alza
  `PydanticSerializationError` (verificato). **Correzione di H**: non un 500 ma un 400 «Unable to serialize…», perché il dump di
  `brokers.py:1047` sta dentro il `try`, e il file resta `PARSED` senza risultato salvato (`move_to_failed` sposta solo da
  `UPLOADED`). Oggi non è raggiungibile: i plugin passano istanze di `Currency` (non
  rivalidate) e liste di stringhe. È latente per un plugin nuovo. Cura: lo stesso filtro dei dati semplici di `_lone_error_params`
  (W-B72), con un rosso su un plugin finto. Dettagli: piano 04, sezione «W-B72 — … (N78): cura».
  ➡️ 17/10: passata a **H** (bilanciamento del coordinatore); io la rivedo al checkpoint di H.
  ✅ 17/10 (H): `BRIMProvider._lone_error_params`, la regola di W-B72, più 18 test; commit `118bd39bf` + `21a2610c8` → dev
  `9ba7ef9d3`. Rivista da W dopo l'ingresso: OK. Le note di H archiviate in W-B70 (il `{gt}` latente) e W-B77 (le due copie).
- ✅ **W-B77 · La regola dei `params` e `_loc_to_field` esistono in due copie (batch e BRIM)** — minimo, pulizia; W con H, 17/10
  (revisione di W-B75). `_lone_error_params`, `_PLAIN_PARAM_TYPES` e `_loc_to_field` stanno sia in
  `backend/app/services/transactions/transaction_batch_stages.py` sia in `backend/app/services/brim/brim_provider.py`, e una
  modifica a una sola delle due fa divergere i `params` di una riga rifiutata dal parse e dal batch. Cura: un modulo condiviso (per
  esempio in `schemas/` o `utils/`), con i test delle due parti; con l'occasione, la docstring di BRIM che dice «made the parse answer
  500» (era un 400, la correzione stessa di H). Dopo W-B70, che cambia la regola. Dettagli: questa voce.
  ✅ 17/10, dentro W-B70 (D-W70-5): una sola copia, `backend/app/utils/pydantic_errors.py` (`PLAIN_PARAM_TYPES`, `loc_to_field`,
  `error_params`); le due copie tolte senza alias, `TestOneCopy` lo tiene. La docstring «500» è sparita con la copia di BRIM. Rivede H.
  Commit (riconciliato il 19/10): `c95eb0cf0` (dentro W-B70), dev `41335f1e1`.
- **W-B78 · Le 10 cifre decimali di una quantità sono scritte a mano in 9 file del frontend** — minimo, pulizia; W, 17/10 (C-97c-3).
  I decimali che una quantità tiene (C-97a) sono un `10` letterale in dieci punti: `TxFormSingleSection.svelte` (2), `TxFormPairSection.svelte`,
  `txDisplayHelpers.ts`, `resolveValidationMessage.ts`, `WacPreviewSection.svelte`, `import/GapFixStep.svelte`,
  `brokers/lots/LotAnalysisFailedNotice.svelte`, `dashboard/ExposureTable.svelte`, e la costante dei lotti
  `LOT_QUANTITY_FRACTION_DIGITS` (`lotChartShared.ts`, C-97c-2). Se la colonna cambia scala, ognuno va trovato a mano. Cura: una costante
  in `frontend/src/lib/utils/core/` accanto a `formatPrice`, letta da tutti (i lotti la importano). Dopo la 1.3: tocca le aree TR, IW, BK
  e DV. Dettagli: piano 04, sezione «C-97c-3».
  - **Nello stesso giro** (Y, 17/10, revisione DV di C-97c-3, via il coordinatore): la coppia `priceFractionDigits` + formattatore di
    valuta è ripetuta in 5 componenti: `components/assets/AssetTable.svelte:220`, `features/dashboard/ExposureTable.svelte:160`
    (`formatUnitPrice`), `features/brokers/lots/LotCustodyModal.svelte:97`, `features/brokers/lots/LotWacPriceChart.svelte:528`,
    `features/transactions/wac/WacPreviewSection.svelte:315`. Cura: un aiuto solo in `currencyFormat.ts`, proposta di Y
    `formatCurrencyPrice(value, currency, {minDecimals, floorDecimals, sensitivity})`, coi rossi Vitest dei cinque formati di oggi
    (aree AF, DV, BK, TR).
- **W-B79 · «Promuovi coppia» apre la modale d'unione anche quando differiscono solo data o costo** — minimo, chiarezza; W, 17/10
  (docs-writer di W-B70). `onPromotePair` (`frontend/src/routes/(app)/transactions/+page.svelte:392-402`) conta come divergenza anche
  data e costo base, che `PromoteMergeModal` non offre più dal maggio 2026 (SP-C Step 5): la modale si apre senza campi e il corpo dice
  solo «Confirm promotion». Cura: la divergenza su descrizione e tag soltanto (come «Unisci» nel Bulk), altrimenti la conferma semplice;
  un rosso di componente o E2E prima. Dopo la 1.3. Dettagli: piano 04, «W-B70 (+ W-B77) — cura».
- **W-B80 · I rifiuti `ledger_unreadable` del gap-fix arrivano in inglese in ogni lingua** — minimo, chiarezza; W, 17/10 (revisione
  di E-19a). Il 409 del gap-fix (`backend/app/services/brim/brim_gap_fix.py`: le righe illeggibili di W-B74 e, da E-19a, i codici di
  valuta non ISO, con i codici citati) è una frase inglese che il passo del wizard mostra com'è (`extractErrorMessage` →
  `GapFixStep.svelte:337`, testo semplice, sicuro): l'utente italiano, francese o spagnolo la legge in inglese, mentre lo stesso caso nel
  batch è tradotto (`transactions.errors.ledgerUnreadable`). Cura: il 409 con un codice e i parametri (`count`, i codici e il loro ISO),
  tradotto nel wizard, come C-70 per i rifiuti dei plugin. Dopo la 1.3, salvo spazio. Dettagli: questa voce.
- ✅ **W-B81 · I doppioni del wizard tra file usano la stessa tolleranza fissa di W-B51** — minimo, dati; W, 17/10 (W-B51). Il wizard
  raggruppa le righe di file diversi e del pool in attesa con `dedupKeysMatch`
  (`frontend/src/lib/features/transactions/import/importDedup.ts:145-157`): la quantità e il costo per unità a 0,0001
  (`QUANTITY_TOLERANCE`, `importTypes.ts:105`) su `Number(...)`, e l'identità del gruppo con `toFixed(4)` (`describeDedupKey`). Due
  acquisti ricorrenti di crypto in due file dello stesso import (o un file e il pool) finiscono nello stesso gruppo, «sicuro» se la
  descrizione coincide. Cura: la regola di D-W51-1 sui testi decimali esatti (la scala del meno preciso, half-up, mai oltre 0,0001),
  l'identità senza `toFixed(4)`; rossi Vitest in `importDedup.test.ts`; la pagina `import-wizard.md` («The dedup signature»). Subito dopo
  W-B51, proposta. Dettagli: piano 04, «W-B51».
  ✅ 17/10 (via del coordinatore): `sameDedupQuantity`, la regola di D-W51-1 letta esatta dai testi decimali (mai un float, mai un
  esponente in un testo), per la quantità e il costo per unità; l'importo entro 0,01 calcolato esatto; `DedupKey` e l'identità del
  gruppo con i testi esatti. In più: una quantità illeggibile (`'n/a'`) non combacia più con tutto. 67 rossi Vitest, la tabella dei casi
  condivisa coi nomi del backend. Dettagli: piano 04, «W-B81».
  Commit (riconciliato il 19/10): `f5536f856`, dev `5890d512c`, CHANGELOG `05b6b834e`.
- **W-B82 · Un costo che il plugin o il gap-fix dà senza modalità si perde nel Bulk** — minimo, dati (latente); W, 19/10 (revisione di
  J-57 sul percorso dell'import). `txCreateItemToPendingOp` (`frontend/src/lib/features/transactions/bulk/TransactionBulkModal.svelte`)
  lascia `cost_basis_mode` a `null` quando il plugin non lo dà, e `buildCreatePayload` (`features/transactions/txPayloadHelpers.ts:277-283`)
  manda un costo solo in Auto o in Manuale: la proposta del gap-fix con il costo per unità della banca (`brim_gap_fix.py:213`,
  `unit_cost`) arriverebbe senza costo, rifiutata con `costBasisRequired`. Crédit Agricole e Intesa mettono `manual` da sé. Nello stesso
  giro: una riga importata con un costo 0 e senza modalità si apre nel form in Auto e lo 0 diventa il segnaposto della valuta
  (`TransactionFormModal.svelte:400-402`). Latente: oggi nessun plugin riempie `unit_cost` (solo Danske Bank costruisce posizioni, senza
  costo). Cura proposta: all'ingresso dell'import un costo senza modalità diventa Manuale, e il gap-fix scrive `cost_basis_mode="manual"`;
  un rosso Vitest e uno pytest. Dopo il via del coordinatore. Dettagli: piano 04, «Revisione dopo l'ingresso — J-57».
- **W-B83 · Fineco: una compravendita col controvalore vuoto entra a 0 €, senza avviso** — basso, dati (latente); W, 19/10
  (verifica di Q-N74-1; corretta il 19/10 nell'analisi del lotto). `broker_fineco/plugin.py:310-311` legge una quantità o un
  controvalore vuoti come 0, una divisa vuota come EUR (`:308`) e una data valuta vuota come la data dell'operazione (`:285`).
  Una **quantità vuota** non entra: la regola 10 rifiuta la riga già in lettura (`qtyPositive`, `qtyNegative`) e il wizard la
  mostra come riga in errore. Un **controvalore vuoto** entra invece in silenzio a 0 €: la regola 7 chiede solo che la cassa ci
  sia, e la 11 salta il segno sullo zero (`schemas/transactions/transactions.py:132-133`, `:169-173`); così un BUY a 0 €, o un
  rimborso (SELL) a 0 €, cioè la perdita di tutto il costo. Una riga provvisoria così, se Fineco ne scrive (non verificato: nessun
  export vero), entrerebbe. Cura decisa (Q-N74-1, developer 19/10): la riga resta fuori, con una nota o niente, nessun avviso.
  Superata dal developer il 19/10 alle 14:05: «siccome fineco per ora è in beta, io importerei tutto ma metterei un banner nota».
  Dettagli: piano 04, «N74 · Fineco opzione (a), W-B83 e le righe sicure».
  ✅ 19/10 (lotto N74, via del coordinatore con le decisioni del developer): la riga entra come prima. Una nota info,
  `fineco_incomplete_rows`, nomina le righe a cui manca un numero necessario, di ogni tipo: la quantità di BUY, SELL e ADJUSTMENT, il
  controvalore di BUY, SELL, DIVIDEND e INTEREST, mai la divisa o il prezzo. Dice che il plugin è in beta e porta il link «apri una
  issue su GitHub» (`context.report_issue`, `BrimNoticeList.svelte`). Nello stesso lotto: le righe Fineco con la data valuta dopo
  oggi del server restano fuori intere, con la nota `fineco_not_yet_settled`; `excluded_not_yet_settled` di Danske Bank diventa
  nota; il limite delle date del batch è domani del server. Commit: il checkpoint N74 del coordinatore. Dettagli: piano 04, «N74 ·
  Fineco opzione (a), W-B83 e le righe sicure».
- **W-B84 · Il link «apri una issue su GitHub» del wizard d'import anche sulle istanze gestite** — basso, chiarezza (cloud); W,
  19/10 (lotto N74). Il wizard porta su GitHub da due punti: il passo delle righe da sistemare (`FixFlaggedStep.svelte:521`, già
  prima) e la nota di un plugin in beta (`BrimNoticeList.svelte`, N74), su ogni istanza. La ricerca degli asset invece (P20, N61,
  `assetSearchReport.ts`, `supportChannel()`) usa l'indirizzo di supporto dell'istanza (`support_url`). GitHub vale solo
  sull'istanza in proprio: su un'istanza gestita senza indirizzo, nessun link. Un utente del cloud verrebbe mandato sul GitHub
  pubblico. Proposta: i due link del wizard seguono `supportChannel()`. Sull'istanza gestita senza canale, il testo della nota non
  finisce più con «:». Domanda al developer, via il coordinatore. Dettagli: piano 04, «N74 · Fineco opzione (a), W-B83 e le
  righe sicure», «Checkpoint».
  ✅ 19/10, chiusa con la decisione del developer (D1), testuale: «essendo una cosa generica che tocca sia le istanze self-hosted
  che quelle hostate, facciamo aprire il link sempre su github». I due link restano come sono, nessun codice. Dettagli: piano 04,
  «N74 — il merge di `dev_release2` e le risposte del developer».
- ✅ **W-B85 · Danske Bank: `excluded_status` mescola le righe annullate e quelle in attesa** — minimo, chiarezza; W, 19/10 (lotto
  N74). `_classify_custody()` e `_classify_cash()` (`broker_danske_bank/plugin.py`) mettono sotto `status` ogni riga non contabilizzata:
  un ordine di custodia con un `Tila` diverso da «Toteutettu», una riga di cassa con un `Tila` diverso da «Toteutunut», o una
  prenotazione «Varaus». Un ordine annullato non arriverà mai: un avviso va bene. Una riga in attesa o una prenotazione arriverà
  invece regolata col prossimo import: è il caso di `excluded_not_yet_settled`, che con N74 è una nota. Il codice non le distingue:
  confronta soltanto con lo stato «contabilizzato». Proposta, se il developer la vuole: due ragioni, `pending` (nota) e `status`
  (avviso), col vocabolario degli stati di Danske preso da un export vero. Domanda al developer, via il coordinatore. Dettagli: piano
  04, «N74 · Fineco opzione (a), W-B83 e le righe sicure», «Checkpoint».
  19/10, la risposta del developer (D2), testuale: «per danske abbiamo gli export veri, se siamo in grado di scartarli con certezza
  non serve neanche il banner, possiamo scartarle in silenzio, metterlo al massimo nel log del backend». L'analisi, in sola lettura:
  gli export veri della issue #26 hanno `Tila` costante, «Toteutunut» nella cassa e «Toteutettu» nella custodia. L'autore non ha mai
  visto un annullato e non conosce gli altri valori. I campioni del repo sono sintetici. Il significato di `Varaus` invece è certo:
  è una prenotazione, e un convertitore open source la scarta. Proposta (b): `Varaus` scartata in silenzio, con una riga nel log;
  ogni altro stato resta avviso, perché è ignoto. Le alternative sono (a) tutto come oggi e (c) tutto in silenzio. In attesa della
  scelta. Dettagli: piano 04, «N74 — il merge di `dev_release2` e le risposte del developer», «D2».
  19/10, decisione del developer: un principio per tutti i plugin BRIM, testuale: «quello che sappiamo va ignorato, venga
  scartato, presente al più nei log, quello che non sappiamo se sia corretto scartarlo, lo scartiamo, ma facciamo comparire un
  avviso in cui si evidenzia il fatto all'utente e gli si dice di aprire la issue per far gestire il caso, con link a github». Per
  Danske: «Varaus» in silenzio con il log; ogni altro stato non contabilizzato con un avviso e `report_issue`; versione 1.0.2. Il
  lotto è in analisi. Dettagli: piano 04, «W-B85 · «Noto in silenzio, ignoto con avviso»: analisi».
  ✅ 19/10, la parte decisa (via del coordinatore 16:23):
  - Danske: «Varaus» → `reservation`, in silenzio con il log e nel conto del set; `excluded_status` → avviso con `report_issue`;
    versione 1.0.2;
  - la regola 10 della skill `brim-plugin`, e la guida dei plugin.
  Restano aperte D-W85-1…4: gli altri motivi di Danske, le note delle righe non regolate, gli altri plugin (W-B86), i salti con
  effetto economico (W-B87). Commit: il checkpoint W-B85 del coordinatore. Dettagli: piano 04, «W-B85 · Danske Bank, «noto in
  silenzio, ignoto con avviso»: cura».
  - ✅ 21/10 (riconciliazione): in `dev_release2` (commit `323c120eb`, 19/10).
- **W-B86 · Gli altri plugin BRIM col principio «noto in silenzio, ignoto con avviso»** — medio, chiarezza (cloud); W, 19/10
  (inventario di W-B85). Oggi 25 plugin saltano le righe ignote o illeggibili con un avviso a stringa per riga, che diventa
  `generic` e non può portare il link «apri una issue». DEGIRO, Scalable e Crédit Agricole hanno già note a codice: basta
  aggiungere `report_issue`. Alcune righe note e sicure avvisano invece di tacere. Proposta: un aiuto unico in `_brim_io.py`, con due
  codici condivisi (`rows_not_recognized`, `rows_unreadable`), evidenza e `report_issue`, e un test di contratto su tutti i plugin.
  Circa 1,5 giorni. La decisione (1.3 o dopo) spetta al coordinatore. Dettagli: piano 04, «W-B85 · «Noto in silenzio, ignoto con
  avviso»: analisi», punto 3.
- **W-B87 · Plugin che saltano in silenzio righe con un effetto economico** — alto, numeri; W, 19/10 (inventario di W-B85).
  - Revolut: lo stock split, `SKIP_TYPES` (`broker_revolut/plugin.py:90-93`).
  - Trading 212: stock split, distribuzione di azioni e conversione di valuta (`broker_trading212/plugin.py:87-92`).
  - eToro: le commissioni overnight, i loro rimborsi e la tassa SDRT (`broker_etoro/plugin.py:75-79`).
  - Con un avviso per riga: Trade Republic (le gambe Kosten/Belasting), Swissquote (le gambe forex), IBKR (FX senza ISIN).
  Quantità dopo uno split, costi e tasse escono sbagliati senza che l'utente lo sappia. Proposta: per la 1.3 almeno l'avviso con
  `report_issue`; l'import vero, per plugin, dopo. Dettagli: piano 04, «W-B85 · «Noto in silenzio, ignoto con avviso»: analisi»,
  punto 4.
- **W-B88 · Quale data registra ogni plugin BRIM, contro il principio di B-52** — medio, numeri; W, 19/10 (analisi di B-52). Il
  principio del developer: registrare la data dell'operazione; usare la data valuta, o lo stato, solo per decidere se la riga è
  regolata. Nel lotto B-52 ci sono Fineco, Danske e il CSV generico. Altri 10 plugin nominano una data valuta o di regolamento:
  Avanza, Crédit Agricole, DEGIRO, Directa, Disnat, Intesa, InvestEngine, Rabobank, Saxo, Schwab. Va fatto l'inventario di quale data
  registra ciascuno; si correggono quelli che datano con la valuta. Proposta: dopo lo sprint, come W-B86. Dettagli: piano 04,
  «B-52 · La data dell'operazione: analisi», punto 9.
- **W-B89 · La data di una transazione è ancora descritta come «settlement date»** — minimo, chiarezza; W, 20/10 (docs-writer di
  B-52). Col principio di B-52 il campo è la data dell'operazione, ma lo descrivono ancora come data di regolamento:
  `backend/app/db/models.py:300, 857, 884`, `schemas/transactions/transactions.py:233, 522`, `schemas/transactions/batch.py:202` e la
  pagina `developer/backend/database/brokers_transactions.md:99`. Le descrizioni degli schemi finiscono nell'OpenAPI e nel client
  generato. Sono file condivisi: decide il coordinatore (proposta: «the operation date, the day the operation was made»). Dettagli:
  piano 04, «B-52 · La data dell'operazione: cura», passo 4.
  ✅ 20/10 (via del coordinatore): «Trade date: the day the operation was made» in `models.py`, negli schemi e nella doc del DB;
  `api sync` senza differenze tracciate. Commit: il checkpoint W-B89 del coordinatore. Dettagli: piano 04, «W-B89».
- **W-B90 · Una `DataTable` senza colonne non si assesta mai** — minimo, test; W, 20/10 (test-author di B-51). Con `columns: []` il
  ripiego per un ordine di colonne vuoto (`frontend/src/lib/components/table/DataTable.svelte:855-861`) riscrive a ogni giro un `[]` e
  un `{}` nuovi, e l'effetto si richiama da sé: Svelte si ferma su `effect_update_depth_exceeded`. Nessun utente lo vede (ogni tabella
  dell'app ha colonne), ma un test di componente che monta una tabella vuota cade (`AnalyzeStep.test.ts` passa una colonna inerte, col
  perché). Cura, piccola: il ripiego scrive solo se l'ordine di default ha colonne (`defaultColumnOrder.length > 0`), e lo stesso
  per le larghezze. È un file condiviso: decide il coordinatore, con il suo proprietario. Dettagli: piano 04, «B-51», passo 1.
- **W-B91 · La guida dell'import, passo 3: «un file è fallito» manda a un bottone che può mancare** — minimo, chiarezza; W, 20/10
  (docs-writer di B-51). In `user/transactions/import/how-to.*.md` il punto «A file failed: … Fix its plugin in Select Files, then click
  Re-parse all»: **Re-parse all** sta nella fila dei riquadri, che compare solo se almeno un file è stato letto, quindi se falliscono
  tutti non c'è; e cambiare plugin e premere **Parse (N)** rianalizza già da sé. Con questa, due tabelle per sviluppatori
  (`brim_plugin_guide.md:910`, `developer/backend/brim/architecture.md:392`) dicono dove compaiono le note senza i conti nuovi di B-51.
  Cura: due frasi in EN, IT, FR, ES più il timbro; in un lotto di doc. Dettagli: piano 04, «B-51», passo 4.
- **W-B76 · La riga aperta con `?highlight=<id>` non resta segnata** — minimo, test e chiarezza; Y-31 (Y), 17/10, via il
  coordinatore. `pulseElement` (`frontend/src/routes/(app)/transactions/+page.svelte:491-501`) dà alla riga la classe
  `tx-row-highlight` per 1,6 s e poi la toglie: finita l'animazione, né l'utente né un test sa quale riga si è aperta, e l'E2E di
  J-12 può solo controllare che la modale si apra. Cura, economica: un segno che resta, `data-highlighted="true"` sulla riga fino
  alla prossima evidenziazione o al cambio di pagina, con un ruolo visibile del design system (un ruolo `-lf-`, niente palette);
  l'E2E di J-12 lo legge. Dopo la 1.3, salvo spazio. Dettagli: questa voce.
- ✅ **W-B73 · La pagina utente delle transazioni dice che l'unione sceglie anche data e costo** — minimo, doc; W, 17/10 (docs-writer).
  `mkdocs_src/docs/user/transactions/index.en.md` descrive il dialogo «Promote pair» con la scelta di data e costo; `PromoteMergeModal`
  offre solo descrizione e tag dal maggio 2026 (SP-C Step 5). La pagina ha già un debito di traduzione non timbrato (la cache di Aphra
  non corrisponde all'EN di HEAD): correggere l'EN e lasciare la traduzione alla pipeline. Dettagli: piano 04, sezione «R13-SEC7-3 —
  cura».
  ✅ 17/10, con la doc di W-B70 (stessa riga della pagina): «If the rows have a different description or different tags, you choose
  what to keep; each row keeps its own date», più il limite di 500 caratteri della modale. Solo l'EN: il debito di traduzione resta
  alla pipeline (nessun timbro).
  Commit (riconciliato il 19/10): `c95eb0cf0` (con W-B70), dev `41335f1e1`.
- ✅ **W-B74 · Una riga illeggibile fa fallire il giro dei saldi senza codice** — basso, chiarezza; W, 17/10 (test-author di W-B69). Una
  quantità o un importo che si legge `None` (testo, o un inf: W-B58) fa sommare `None` a `_validate_broker_balances`
  (`backend/app/services/transactions/balances.py`): un `TypeError`, che il batch rende come «Balance validation error» senza codice né
  riga. Ogni batch che rigioca quel broker da prima della riga si ferma così, e l'utente non sa perché. Cura: la riga illeggibile come
  issue con un codice proprio (o la pulizia di W-B63). Dettagli: piano 04, sezione «W-B69».
  Analisi (17/10): **peggio del titolo** — prima della finestra del giro (`_get_balances_before_date`, via `native_cash.py` e
  `ledger_totals.py`) una riga illeggibile **sparisce in silenzio**, e il saldo d'inizio è sbagliato: un batch da rifiutare può
  passare. Cura: il conteggio delle righe illeggibili del broker all'inizio del giro e in `get_balances_at_end_of`, rifiuto
  `ledgerUnreadable {brokerId, count}` (4 lingue, il messaggio manda all'amministratore: la lista non le mostra). Primo dei tre, dopo la
  metà del batch di W-B69, con l'aiuto di query condiviso con quello di MF. Dettagli: piano 04, «W-B71, W-B72, W-B74 — analisi».
  ✅ 17/10: `count_unreadable_rows()` (nuovo `unreadable_rows.py`, condiviso col conteggio dell'insieme di W-B69); il giro di un broker
  con righe illeggibili rifiutato con `ledgerUnreadable {brokerId, count}` (indice −1, 4 lingue), il gap-fix con 409
  `ledger_unreadable`; 17 rossi verdi, i 24 contratti di W-B69 aggiornati (due issue). Resta la via d'uscita dei dati: W-B63. Dettagli:
  piano 04, sezione «W-B74».
  Commit (riconciliato il 19/10): `bd5deeb36`, dev `80cee9c2d`, CHANGELOG `e908f0d4f`.
- ✅ **W-B32 · I report senza broker compaiono nella lista di ogni broker** — minimo, chiarezza; W, 15/10 (F36,
  docs-writer). `brim_provider.list_files` tiene i file senza broker anche quando filtra per `broker_ids`
  (`backend/app/services/brim/brim_provider.py`, «files without broker_id (legacy)»): dopo F36 li vedono solo il
  caricatore e l'admin, ma nella lista «Uploaded Reports» di **ogni** broker (tutti per l'admin, i propri per gli altri).
  Da decidere: con un filtro di broker esplicito, escluderli (restano nella vista senza filtro della pagina File).
  Dettagli: piano 04, sezione F36.
  ✅ 16/10 (decisione notturna dentro la decisione 36, da rivedere): con `broker_ids` esplicito la rotta lascia fuori i file
  senza broker, senza filtro invariata (`list_files` intatta); F36-16 rosso 2/2 prima, `api brim` 118/118 dopo; doc in EN,
  IT, FR, ES. Dettagli: piano 04, sezione W-B32.
  Commit (riconciliato il 19/10): `84d24ed03`, treno 101 (`c94254695`).
- ✅ **W-B33 · `transactions/service.md`, «Broker Deletion»: tre imprecisioni di testo** — minimo, doc; W, 15/10 (W-B20,
  docs-writer). In `mkdocs_src/docs/developer/backend/transactions/service.md`:
  - «One is required since (`costBasisRequired`)» resta senza data né versione e si legge troncata;
  - «both helpers come from `_compute_wac_for_auto_items()`» nomina tre aiuti, e quella funzione li usa tutti e tre;
  - la tabella dei chiamanti dice che `delete_bulk()` chiede `OWNER` e tace il superuser: `as_user_id="all"` salta il
    controllo, `as_user_id=<id>` controlla quell'utente.
  Da fare nel lotto di doc A-14 / W-B10. Dettagli: piano 04, sezione W-B20.
  ✅ 15/10 (lotto di doc A-14): le tre frasi corrette (il codice `costBasisRequired` quando un batch crea quella metà
  senza costo, con il rimando alla regola; «all three helpers»; l'admin con `as_user_id` nella riga di `delete_bulk()`).
  Commit (riconciliato il 19/10): `f062418e4` (lotto di doc A-14), dev `6fa3f8936`.
- ✅ **W-B34 · L'elenco degli accessi di un broker lo legge chiunque abbia un login, e-mail comprese** — da decidere
  (developer), sicurezza; W, 15/10 (lotto di doc A-14, docs-writer). `GET /brokers/{broker_id}/access`
  (`backend/app/api/v1/brokers.py:446`) chiama `get_by_id(…, as_user_id="all")` e `list_accesses()` non controlla: ogni
  utente autenticato legge username, e-mail, ruoli e quote dei membri di qualsiasi broker (id sequenziali). Accettato
  per decisione del developer (C-8 della 38) per l'istanza di famiglia; nel cloud gli utenti sono estranei. Proposta di
  W: solo chi ha un ruolo sul broker e l'admin, 404 agli altri (come i file di F36); unico chiamante del frontend
  `BrokerSharingPanel`; da cambiare ACCESS-002/003 e `test_account_deletion_api.py:351-352`. Inviata al coordinatore il
  15/10 (regola della notte). Dettagli: piano 04, sezione «Lotto di doc A-14».
  ⊘ 16/10, **decisione del developer (P4): non si restringe**, nessun lotto. Il motivo, suo: gli utenti devono sapere che
  esistono altri broker, per capire perché un nome non si può riusare e a chi chiedere. L'elenco resta leggibile da ogni
  utente autenticato, come descrivono le docstring (W-B35) e `access_control.md` (lotto A-14). Dettagli: messaggio del
  coordinatore, 16/10 11:11.
  ✅ Chiusa senza codice (riconciliato il 19/10): decisione P4 del developer (16/10, la riga ⊘ qui sopra); le docstring dicono l'elenco aperto per decisione, `02f08057f`.
- ✅ **W-B35 · Docstring e commenti superati dell'accesso ai broker** — minimo, chiarezza; W, 15/10 (lotto di doc A-14,
  docs-writer). `backend/app/services/brokers/access.py:98` («skip access check»: `list_accesses()` non ne fa, e i suoi
  argomenti `user_id`/`is_superuser` non servono); `access.py:141` e `backend/app/api/v1/brokers.py:496` (un controllo
  «calling user cannot remove themselves as last OWNER» che non esiste: lo copre «almeno un OWNER»); la docstring di
  `list_broker_access` (`brokers.py:455`, già in C-8 della 38); `backend/app/services/transactions/transaction_service.py:84`
  («one is required since», troncata come la doc di W-B33). Il `PUT …/access` su un broker che non esiste risponde 403
  all'utente e 400 all'admin, non 404. Le docstring delle rotte finiscono nell'OpenAPI: `api sync` dopo. Da fare con
  W-B34 o in un lotto di codice. Dettagli: piano 04, sezione «Lotto di doc A-14».
  ✅ 16/10: docstring di `list_accesses`, `bulk_update_access`, `list_broker_access` e del `PUT …/access` allineate al codice
  (`api sync`: il client è ignorato da git); `transaction_service.py:84` con la 47. Resta il 403/400 del `PUT` su un broker
  che non esiste (comportamento). Dettagli: piano 04, sezione W-B35.
  Commit (riconciliato il 19/10): `d35e3c8f3`.

## J · Numeri e analisi (fase 01)

Piano: [`05_numbersAnalysis`](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md). Righe scritte da J
il 14/10, nel checkpoint J-0; i numeri di riga sono di `c9bb8f257`. G-8 e J-4 scritte il 15/10, nel checkpoint CP-1.

**16/10, ripartizione con MF** (piano di MF approvato dal developer, via il coordinatore alle 13:26). Passano a MF:
- CP-3 (U5a: B8, V2/P2, R4, B19 e il TRANSFER di P22);
- CP-5 (U2, U6, T-B4);
- U3 e U7 di CP-11, con O4;
- la matematica di CP-12 (U9, T-B8);
- CP-13 meno CP-13a (U8 lato backend);
- i residui R6–R10 di T-U4.

Le loro righe nelle altre sezioni le riconcilia il coordinatore. Restano a J: J-17, CP-13a (P19), J-24, CP-7b, J-26,
J-10…J-12, CP-8, CP-9, CP-10 (con R11), U1, U10, CP-14, T-B7, T-B9 e B15. Dettagli: piano di MF, §2; piano J, §10.

- **J-1 · Copie della matematica comune fuori dall'inventario del 43** — basso; J, 14/10 (analisi). Ognuna va nel
  lotto che unifica la sua famiglia:
  - `risk/metrics.py:741` (giorni di calendario → osservazioni, con 365) → U4a, CP-10;
  - `portfolio_service.py:824` (G/L % della posizione) → U4b, CP-4;
  - `series_preparation.py:184` (fattore di cambio ricavato dal close) → U1, CP-11;
  - `fx.py:717` (inversione del tasso nella catena delle rotte) → U1, nei file di X dopo il suo PL4 (D-J17);
  - `ai_export/components/fx_timing_context.py:361-362` (rendimenti dal minimo e dal massimo) → U9, CP-12; **→ MF**
    (MF-D, 16/10);
  - frontend, per Y con U8: `lib/charts/signals/CompoundSignal.ts:69` (curva what-if, eccezione interattiva da
    dichiarare, R19) e `lib/components/risk/levels/levelHelpers.ts:359` (rendimento che recupera una perdita): il
    secondo diventa un campo del backend con P19 (CP-13a di J, 16/10), poi Y lo legge.
  - **15/10, nella revisione di V-3 per W**: la quantità per posizione a una data non ha una funzione nella casa, e oggi
    si conta in più posti: in `transactions/balances.py` (`get_asset_holdings` e la metà delle quantità di
    `_get_balances_before_date` e del replay della validazione) e nel `cumulative_qty` del motore. Da decidere se il
    registro delle quantità appartiene alla casa. La metà della cassa la rifà W come W-B19, su `native_balances`.
    **→ MF** (MF-G, su `ledger_totals.position_quantities`, 16/10).
  - **15/10, nel piano di CP-6**: un buco nei cambi si legge in due modi. Il motore valuta i titoli e la cassa in
    transito a giorno esatto (`fx_rate_map.get`: niente cambio → valore mancante, `daily_state.py:1031`,
    `_convert`); la cassa nativa porta avanti l'ultimo cambio noto senza limite (`native_cash._rate_at`). Con un buco
    oltre la finestra di riempimento di `convert_bulk`, la cassa resta valutata e i titoli no. Una sola regola per i
    buchi → U1, CP-11. CP-6 usa una sola funzione dei giorni di cambio, che riceve la lettura del chiamante.

  - **17/10**: il punto di `risk/metrics.py:741`, con la sua inversa a `risk/quant/resampling.py:235`, passa a MF
    (J-1 punto 1), con le 6 condizioni di J riferite dal coordinatore. Dettagli: piano 05, §10 «J-19 entrata…».

  Dettagli: [piano J](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), §1.2 «Copie nuove».
- ↪ **J-2 · Il server di test costruisce frontend e documentazione dentro i 300 s d'avvio** — spostata nella sezione C
  dal coordinatore il 15/10 (runner condiviso), come C-94.
- ✅ **J-3 · Monte Carlo e ricampionamento a 365 giorni fissi** — da verificare; T, 11/10 (piano 43, §5, «da segnalare a
  parte»), ripresa da J, che ora possiede il rischio. `risk/quant/quantlib_worker.py:116,195` e
  `risk/quant/resampling.py:235` contano 365 giorni all'anno, mentre il resto del rischio usa il fattore osservato. Può
  essere una convenzione di calendario coerente: prima un test che lo provi, poi l'eventuale cura in CP-10. Dettagli:
  [piano 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), §5.
  - ✅ 17/10: **verificata da J, non è un difetto** (chiusa col checkpoint J-49). Il GBM cammina `horizon_days/365` anni
    a passi di un giorno di calendario, con deriva e covarianza annue stimate col fattore osservato
    (`quant/estimation.py:52-53`): dopo 365 giorni la varianza è quella di un anno, qualunque sia la frequenza della
    storia. Il bootstrap (algoritmo 4.0.0) converte i giorni nei passi osservati (`calendar_days_to_observations`), e
    `resampling.py:235` è solo la conversione inversa per dichiarare la lunghezza del blocco. Dettagli:
    [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «J-49».
    Prova: la verifica nel diario `0767fba38`, senza codice.
- ✅ **G-8 · Il catalogo dei Tool sotto carico supera i 2 s d'ingresso** — basso; G (galleria del programma colori),
  assegnata a J dal coordinatore il 14/10, dopo CP-1. Sotto carico la lettura del catalogo supera
  `ToolRoute.ingress_timeout_ms` (2 000 ms, `schemas/tools.py:83`, applicato in `api/v1/tools.py:92`) e la pagina
  «about plugin diagnostics» è andata in rosso nella galleria. Proposte di G: un limite proprio per il catalogo, oppure
  un catalogo in cache. Prima un rosso che lo riproduca. Dettagli: piano J, §10 «Checkpoint J-0».
  - 15/10, J: chiusa al checkpoint G-8. Il tempo si perdeva prima del catalogo: l'autenticazione girava dentro la
    finestra d'ingresso di 2 s. Le rotte senza corpo (catalogo, diagnostica) aprono ora sotto il loro budget di 20 s;
    il compute tiene la finestra d'ingresso. Rosso prima, verde dopo (`api tools` 12). Dettagli: piano J, §10 «G-8».
- **J-4 · Prosa della devWiki con i percorsi del PAC di prima del riordino** — basso, documentazione; J, 15/10 (CP-1).
  C6 riguarda le tabelle «Source files», aggiornate in CP-1; restano tre passi di prosa al presente che citano i file
  com'erano prima del riordino: `features/F-107.md:49-50`, `features/F-108.md:31`,
  `problems/i18n-audit-false-dead-and-false-used.md:48`. Da rinfrescare in un passaggio di `wiki-lint`. Dettagli: piano
  J, §10 «A — rinomina», «Restano di proposito».
- ↪ **J-5 · Un thread dell'executor resta con un loop chiuso come loop corrente** — spostata nella sezione X dal
  coordinatore il 15/10 (file di X), come lotto piccolo con un test dopo il CP4. ✅ Chiusa da X il 15/10
  (`743fca514`).
- ✅ **J-6 · Nessuna guardia di suite per le connessioni aiosqlite lasciate aperte** — basso, facoltativa; J, 15/10
  (C-93). Oggi le connessioni aperte dopo un test sono 0 in tutta la suite, ma lo garantisce solo la guardia del file
  d'integrazione dell'AI Export. Una fixture autouse nel `conftest.py` condiviso potrebbe far fallire ogni test che
  lascia aperta una `aiosqlite.Connection` creata durante il test (registrando le connessioni create e controllando
  al teardown, come la sonda usata per C-93). Il conftest è condiviso: decide il coordinatore. Dettagli: piano J, §10
  «C-93».
  - 15/10, J: chiusa al checkpoint J-6. Fixture autouse `_aiosqlite_leak_guard` nel `conftest.py` condiviso: un
    test che lascia aperta una connessione aiosqlite creata nel thread principale ha un ERROR al proprio teardown, con
    lo stack di creazione; elenco esplicito `AIOSQLITE_LEAK_EXCEPTIONS`, vuoto. Self-test in `utils
    gate-aiosqlite-leak` (9). `all-backend --workers 2` verde senza rapporti. Dettagli: piano J, §10 «J-6».
  - In `dev_release2` con `e2cb55054` (J-6 `b49a54645`); la regola è la n. 7 di
    `.github/instructions/backend-testing.instructions.md`.
- **J-7 · Il frontend dei test si costruisce in produzione e in debug** — basso, tempo dei test; J, 15/10 (C-94),
  da smistare a un treno dal coordinatore. Le due parti chiedono build diverse:
  - il server di test vuole il debug: `dev.py:204` (`debug_mode = True` in modalità test) e `auto_build_frontend`
    (`dev.py:2110`), che ricostruisce quando il marcatore `frontend/build/.build-debug` non corrisponde (`:2124`);
  - il runner frontend chiede la produzione: `_frontend_common.py:93` (`debug=False`), attraverso il controllo
    generico `cli_base.auto_build_frontend` (`:620`), che il marcatore non lo legge.

  Effetti, letti nel codice:
  - **server condiviso** (il percorso normale): il server costruisce in debug prima dei test, poi il runner trova la
    build aggiornata. Quindi i test frontend girano sul bundle di debug, anche se il runner chiede la produzione;
  - **copertura JS**: ogni run costruisce due volte. Il server ricostruisce in debug, perché il marcatore della run
    precedente dice produzione; quella build cancella `.coverage-instrumented`, perché adapter-static svuota
    `build/`; allora `_ensure_frontend_build` (`:71-74`) forza la build strumentata di produzione;
  - **server avviato da Playwright** (galleria, `--no-shared-server`, `playwright test` diretto): prima la build di
    produzione, del runner o della CI (`release.yml:172`), poi il `webServer` ricostruisce in debug.

  Da decidere: un solo tipo di build per i test, su cui le due parti concordano (debug, strumentata sotto la
  copertura JS), oppure un server di test che accetta la build che trova. Collegato, da C-94: con `--no-shared-server`
  e `playwright test` diretto le build restano dentro il tempo massimo del `webServer`. Il suo env
  (`playwright.config.ts:31-39`) porta la strumentazione della copertura JS, e un passo `--build-only` senza
  quell'env costruirebbe un'altra cosa. Deciso il tipo di build, anche quei percorsi possono avere il passo prima di
  Playwright. Dettagli: piano J, §10 «C-94».
- **J-8 · Il runner frontend chiama ancora `npx` senza controllare `node_modules`** — basso, robustezza; J, 15/10
  (C-94), runner condiviso: da spostare nella sezione C se il coordinatore preferisce. C-94 ferma con un messaggio
  chiaro il percorso delle build (`dev.py front build`, `api client|sync`, quindi il server di test e
  `_ensure_frontend_build`); restano fuori le chiamate dirette del runner, che senza `frontend/node_modules` vanno al
  registro: `npx vitest run` in `_frontend_ai_export.py:45`, `_frontend_asset.py:14,66`, `_frontend_broker.py:17`,
  `_frontend_fx.py:14`, `_frontend_portfolio.py:143-295`, `_frontend_transaction.py:13`, `_frontend_user.py:14`,
  `_frontend_utility.py:20,190,343`, `_consolidate.py:265`; `npx playwright test` in `_consolidate.py:179`. Le azioni
  Playwright passano prima da `_ensure_frontend_build`, che ora si ferma, e lanciano `npm run test:e2e`, non `npx`;
  quelle solo Vitest no. Cura possibile: lo stesso controllo di `dev.require_frontend_dependencies` in un punto comune
  del runner, oppure i binari di `frontend/node_modules/.bin` al posto di `npx`. Dettagli: piano J, §10 «C-94».
- ✅ **J-9 · Il lotto da ADJUSTMENT-in prende la valuta della riga, non quella del costo** — medio, numeri; trovata dal
  test-author di W (V-3), verificata da J il 15/10. `fifo/engine.py:353` apre il lotto con la `currency` della riga,
  mentre il prezzo è `cost_basis_override`, che sta in `cost_basis_currency`. Con `currency` nulla, ammessa perché
  l'importo è 0 (`db/models.py`, docstring di `Transaction`), `FxRateResolver.convert` (`financial_math/lots/conversions.py:59-60`)
  tratta il costo come già nella valuta del report: niente conversione, niente segnalazione. Il costo medio legge
  invece `cost_basis_currency` (`average_cost.py:280-289`), quindi i due motori leggono lo stesso costo in due valute.
  Tocca ogni ADJUSTMENT-in con il costo in un'altra valuta, e anche le righe convertite da V-3. Cura: la valuta del
  lotto è `cost_basis_currency` quando il prezzo viene dall'override. Prima il rosso: un ADJUSTMENT-in in USD e un
  report in EUR, con `currency` diversa e con `currency` nulla. Dettagli: piano J, §10 «Domande di W N1».
  ✅ Chiusa da J il 15/10 in CP-16 (decisione del coordinatore, 23:00): il lotto prende `cost_basis_currency` quando il
  prezzo viene dall'override; la riga d'apertura della cronologia converte con la valuta del lotto e la cronologia
  registra quel cambio. Rossi in `test_fifo_adjustment_out_with_cost.py` e `test_lots_analysis_pure.py`. Commit: il
  checkpoint di CP-16, `335fb89cf` → dev `240675ad1`. Dettagli: piano J, §10 «CP-16».
- ✅ **J-10 · I lotti falliscono quando il broker mittente di un TRANSFER è fuori dallo scope** — medio, numeri e
  chiarezza; trovata dal test-author di W, allargata da J il 15/10. Letta nel codice, non provata.
  `_load_transactions` (`lots_analysis_service.py:518-520`) carica solo i broker dello scope, e la pagina del broker
  apre i lotti con `broker_ids=[broker.id]` (`brokers/[id]/+page.svelte:676`). Quindi anche il proprietario, sulla
  pagina di B, vede `FAILED` con `TRANSFER_PAIR_MISSING` per un titolo arrivato da A con la coppia intera; un
  co-proprietario che non vede A lo vede ovunque. Solo `PERFORMANCE_HISTORY` rifà il giro su tutti i broker
  accessibili (`:213-216`). L4 (`test_portfolio_cost_currency.py:1053`) copre solo il caso con entrambi i broker nello
  scope. Da decidere:
  - per il proprietario, girare sui broker accessibili e filtrare l'uscita sullo scope, come la performance;
  - per chi non vede il mittente, leggere la gamba come l'orfano dopo V-3: un ADJUSTMENT al suo costo congelato.

  Dettagli: piano J, §10 «Domande di W N1».
  - ✅ 17/10: fatta da J (checkpoint J-10): entrata con `ba612882a`, CHANGELOG `4529ce9ad`. Dettagli: piano 05,
    sezione «J-10».
- **J-11 · Un ADJUSTMENT in uscita senza costo si legge come unità distrutte** — da decidere (developer), numeri; J,
  15/10, nella revisione di V-3. Letta nel codice, non provata.
  - **Il caso**: si cancella il broker che riceve un TRANSFER. Sopravvive la gamba in uscita, che non può avere costo
    (`cost_basis_pair: ["forbidden", …]`). Alla lettera della decisione del 13/10 diventa un ADJUSTMENT −q senza
    override.
  - **Dashboard**: senza override `_is_capital_adjustment` (`daily_state.py:1119-1133`) è falso, quindi il capitale
    non scende. P&L di A da +80, uscita al mercato con `_transfer_leg_capital`, a −20.
  - **Lotti**: l'`ADJUSTMENT_OUT` chiude a prezzo 0 (`fifo/engine.py:374-382`, `:613`): realizzato −80 e lotto a −20
    (`lots_analysis_service.py:745-769`).
  - **Con un override**: la Dashboard dà già 60, cioè il guadagno della posizione. I lotti restano a −20 finché FIFO
    non legge un `ADJUSTMENT_OUT` con costo come una distribuzione al suo costo.
  - **Lo split di una coppia** (`batch_edits.py:126-139`) produce oggi la stessa uscita senza costo: nella vista
    combinata il P&L scende del costo delle unità spostate.
  - **Opzioni mandate al coordinatore il 15/10**:
    1. raccomandata: override sulla gamba in uscita dalla funzione dell'Auto, più la regola FIFO, lotto di J con il
       suo rosso;
    2. intanto, solo le gambe in entrata;
    3. alla lettera.

  - **Decisione del coordinatore, 15/10 10:04: la 2 per ora.** Si convertono solo le gambe di titoli in arrivo; quelle
    in uscita restano TRANSFER orfani come oggi. Le gambe di cassa diventano DEPOSIT o WITHDRAWAL come previsto: capitale
    e P&L invariati, ma cambiano due serie della Dashboard (finanziamento degli acquisti dai pool K/R/W, punti dei
    depositi), da dichiarare (detto a W).
  - **La scelta definitiva va al developer come punto 47**, con la raccomandazione di J (la 1) e la stessa domanda sullo
    split di una coppia: che cosa vuol dire per le unità in uscita. Se sceglie la 1: lotto di J con il rosso prima, poi
    la correzione degli orfani in uscita.
  - **Decisione 47 del developer (15/10, 19:09)**, alla lettera: «sono daccordo, si va mantenuto lo stesso principio nel
    senso opposto». La gamba in uscita rimasta senza coppia diventa una rettifica in uscita **con il costo** medio con
    cui le unità partono, dalla funzione del costo «Auto»; nell'esempio guadagno 60 sia in Dashboard sia nei lotti.
    - **Dove vale**: la cancellazione del broker che riceve, le gambe in uscita già spaiate nei database, «dividi la
      coppia».
    - **Lotti**: J, **CP-16**, la regola in FIFO con il rosso prima, dopo CP-4c e CP-4d e prima di CP-15 (ordine
      confermato dal coordinatore il 15/10: CP-4d resta prima perché corregge un numero visibile; W non aspetta ancora
      la regola, prima fa N2 e i file dei broker). Conversione delle cancellazioni e dei dati: W, sopra la regola di J,
      con la firma da accordare.
    - **Punto aperto per CP-16**: con più lotti a prezzi diversi le unità possono uscire al loro costo FIFO (realizzato
      0, come in un trasferimento) oppure al costo medio della riga (realizzato = medio − costo FIFO). Nell'esempio le
      due letture coincidono. Da proporre all'avvio di CP-16, con un rosso per ciascuna lettura.
    - **La regola nei lotti (J, CP-16, 15/10)**: lettura (b), il costo medio della riga, decisa dal coordinatore la notte
      del 15/10, «da rivedere» col developer. Ogni lotto consumato chiude al costo della riga e il valore ceduto conta
      come proventi; un lotto comprato a un altro prezzo realizza la differenza (10 a 10 e 10 a 20, uscita −10 al costo
      15: il primo lotto realizza +50; lotti 150 = Dashboard 150). In un'altra valuta il lotto esce al suo costo FIFO
      fino a CP-7. Anche la performance dei lotti conta l'uscita al costo come flusso esterno. Resta di W la conversione
      delle gambe in uscita, con la firma che il coordinatore gli gira.

  Dettagli: piano J, §10 «Domande di W N1» e «CP-16».
- ✅ **J-12 · Con l'analisi dei lotti `FAILED` il pannello disegna lo stesso lotti e cifre** — medio, chiarezza (utenti
  non esperti); trovata dal test-author di W (V-3, caso speculare), confermata da J nel codice il 15/10.
  - **Il caso**: un TRANSFER in uscita orfano. FIFO salta la coppia irrisolta (`_resolve_transfer_pair`, `FAILED` con
    `TRANSFER_PAIR_MISSING`), quindi il lotto di A resta con 10 X aperti, valore 300 e P&L 100, mentre la posizione e
    le righe WAC dicono 6.
  - **Il pannello** (`LotsAnalysisPanel.svelte:478-482`) mostra l'avviso rosso, poi disegna lo stesso grafici e lotti.
  - **Da decidere col coordinatore**:
    - il backend non dà le cifre dei lotti quando lo stato è `FAILED` (`_QUANTITATIVE_FAILURE_CODES` dice già «whole
      FIFO reconstruction unreliable»): un solo punto per ogni consumatore, AI Export compreso;
    - oppure il pannello le nasconde.

  Prima un rosso sul caso speculare di W. Dettagli: piano J, §10 «Domande di W N1».
  - ✅ 17/10, metà backend e AI Export: fatta da J (checkpoint J-12; N81, opzione A). La metà del pannello è di Y.
    - Con `FAILED` il servizio non dà nessuna cifra dei lotti: tiene le righe WAC, le issue che fanno fallire il
      rigioco (con `transaction_date`, `fails_analysis` e, per un trasferimento, la gamba che dà) e le lacune delle
      righe WAC.
    - AI Export: l'asset è dichiarato in `failed_lot_reconstructions` (solo identità e codici), i totali del perimetro
      sono nulli; `*.fifo_lots` v3, `asset.lot_detail` v4 con lo stato. Dettagli: piano 05, sezione «J-12 — backend e
      AI Export».
  - ✅ 17/10: fatta. Il backend e l'AI Export da J (`4195fa857`, `fc8ab50ca` → dev `2fa8ec1a8`), il pannello da Y
    (`46b5fbc0e`). Dettagli: piano 05, sezione «J-12».
- ✅ **J-13 · Volatilità, Sharpe e Beta mobili mostrano «giorni» ma contano osservazioni** — basso, chiarezza (utenti
  non esperti); J, 15/10, nella nota sul punto 29 per il coordinatore.
  - `rolling_volatility`, `rolling_sharpe` e `rolling_beta` dichiarano `"x-suffix": "days"` sulla finestra (come oggi
    `rolling_return`), mentre il tooltip condiviso `signals.tooltips.riskWindow` dice «Number of prepared daily return
    observations».
  - Per questi stimatori le osservazioni sono la misura giusta (annualizzazione per periodi): si cambia **solo
    l'etichetta**, in «osservazioni», nei 4 cataloghi. Deciso dal coordinatore il 15/10: nessun cambio di calcolo.
  -   Va con CP-10a, insieme al punto 29 (un solo Rolling Return a giorni di calendario, approvato dal developer il 15/10).
  ✅ Chiusa da J il 16/10 in CP-10a: le tre finestre dichiarano `"x-suffix": "observations"`, con la chiave nuova
  `signals.units.observations` nei 4 cataloghi; il tooltip `signals.tooltips.riskWindow` resta. Nessun calcolo cambia.
  La matrice dei plugin lo fissa (`test_period_params_declare_their_unit_and_tooltip`). Commit: il checkpoint di CP-10a,
  `af919560c` → dev `82e9c5305`.

  Dettagli: piano J, §10 «Decisioni 26–30 (15/10) e piano dei lotti sbloccati».
- ✅ **J-14 · Copie del realizzato e della G/L % da portare alla regola del punto 26** — medio, numeri; J, 15/10. Il
  developer (punto 26): «se ci sono altre aree di codice che fanno una cosa simile, magari duplicando, segna che bisogna
  fattorizzare e ottenere il meglio dalle 2 con la policy corretta». Regola: costo al cambio dell'acquisto, proventi al
  cambio della vendita; il motore della Dashboard la applica già.
  - nei lotti di J (CP-7, con un rosso per ogni comportamento che cambia): `lots/histories.py:160-182`,
    `lots_analysis_service.py:728-770` e `:1042-1045`, e di riflesso l'AI Export (`payloads/portfolio_broker.py:604-606`,
    `:775-776`);
  - duplicati senza cambio di valore: l'identità del periodo nell'AI Export (`portfolio_financial.py:489`,
    `broker_financial.py:434`, CP-12; **→ MF**, la matematica di CP-12, 16/10); la G/L % in `portfolio_service.py:824`,
    `:939` (CP-4);
  - **in un file di W**: `brokers/summary.py:119-135`, terza copia della G/L %, nella valuta dell'asset: da smistare
    dal coordinatore. ✅ Fatta da CP-7a (`gain_loss_ratio`, treno 107, `4f9e94420`).

  Dettagli: piano J, §10 «Decisioni 26–30 (15/10) e piano dei lotti sbloccati», «Inventario del punto 26».
  ✅ **Chiusa il 17/10** (coordinatore, mappatura di MF): i punti 2, 3 e 7 da CP-7a, il 6 da CP-4 (`gain_loss_ratio`), il 4 ereditato (somma valori già convertiti); il 5 (residuo d'identità dell'AI Export) e il 5b (`period_other_result` in `get_positions_contribution`) dal lotto J-14 di MF: `period_identity_residual` e `is_reconciled` in `financial_math/portfolio/period.py`, nessun valore cambia (`8cc5661bc`, dev `f44340118`).
- **J-15 · La galleria ristampa l'output di Playwright senza flush** — basso, strumenti (programma colori); J, 15/10,
  nella prova di C-94. `dev.py`, `cmd_mkdocs_gallery`, `print(line, end='')` nel ciclo su `proc.stdout`: su una pipe
  (il `tee` di `gallery_snapshot.sh`, i log) Python bufferizza a blocchi, e l'avanzamento di Playwright arriva a pezzi da
  8 KB o tutto alla fine, nell'ordine giusto ma senza l'ora vera; sul terminale va bene. Com'era prima di C-94. Cura
  proposta: `flush=True` su quella riga, col via del coordinatore colori.

  Dettagli: piano J, §10, C-94, passo 6 (3), «Fuori pista».
- ✅ **J-16 · Il test del gemello compatto del PAC non dice quale risultato fallisce** — basso, test; segnalata da X tramite
  il coordinatore, 15/10. `test_pac_compute_plans_the_compact_twin_like_the_explicit_request` (`api pac-planner-tool`)
  è caduto una volta sotto un carico fra 75 e 121, con `(1, 1)` invece di `(2, 0)`; da solo passa. I Tools non scrivono
  nel log l'elemento fallito, e il test controlla i conteggi prima di stampare i risultati, quindi la causa non si
  vede. Proposta: mettere `results` nel messaggio d'errore dell'asserzione, poi, alla prossima caduta, il triage con la
  skill `test-triage`. Lotto piccolo, quando capita, con `test-author`.
  - ✅ 17/10: fatta da J (test-author), solo il messaggio; nessuna condizione cambia (albero sintattico confrontato
    con HEAD). Se i conteggi non tornano, il messaggio dà `(status, error)` di ogni elemento, l'`execution_id` e
    le metriche di quello che non è riuscito (servono anche per J-19), e `server_processing_ms`. Il piano resta
    fuori. `api pac-planner-tool` 12/12. Rivede X. Il triage, alla prossima caduta. Dettagli: piano 05, §10 «J-16».
    Commit `59233f44b` → dev `78e2171ee`.
- ✅ **J-17 · Una rettifica col costo segna il prezzo dell'asset a quel costo** — medio, numeri (titoli quotati di rado);
  J, 15/10, in CP-16. Letta nel codice, non provata. `build_asset_price_series` (`financial_math/price_marks.py:307-309`)
  prende ogni ADJUSTMENT con `cost_basis_override` diverso da zero come un'osservazione TRADE, in entrata e in uscita.
  In un giorno senza quotazione di mercato il prezzo dell'asset, per tutti i broker, diventa quel costo, e resta fino
  alla quotazione successiva: Dashboard e lotti valutano le posizioni al costo, non all'ultimo prezzo di mercato. Oggi
  succede ai seed (Intesa, Crédit Agricole, di solito prima di ogni quotazione) e alle gambe in entrata convertite da
  V-3; con la decisione 47 succederà anche alle gambe in uscita convertite da W e allo split di una coppia, dove prima
  il TRANSFER non segnava nulla. Proposta: una rettifica in uscita non segna mai il prezzo (consegnare unità al costo
  non è un prezzo osservato); per quelle in entrata, segnare solo se l'asset non ha ancora una quotazione di mercato.
  Prima il rosso; serve la decisione del developer, perché cambia il comportamento dei seed. Dettagli: piano J, §10
  «CP-16».
  **Decisione del developer** (P2, 16/10): «le rettifiche sono transazioni; portano un WAC, che può voler dire molte cose
  e non è il prezzo dell'asset in quel momento; i prezzi si deducono solo da un acquisto»: una rettifica non è mai
  un'osservazione di prezzo, in entrata e in uscita (per la SELL decide il developer). Caso senza prezzo, **opzione A**:
  una posizione senza alcuna osservazione vale il suo costo storico, come stima dichiarata («valutato al costo, nessun
  prezzo»). Lotto J-17 dopo CP-7a, disegno approvato il 16/10: piano J, §10 «J-17».
  - ✅ 16/10: fatta da J con la decisione (a): `638213507`, entrata con `94321d7db`. Dettagli: piano 05, §10 «J-17».
- ✅ **J-18 · Su SQLite `Numeric(18, 6)` si salva come numero in virgola mobile** — basso, dati; trovata dal test-author di
  J il 16/10 (CP-15), con una prova su file. SQLAlchemy su SQLite non passa i Decimal al driver: li converte in `float`
  e li rilegge con 6 decimali, quindi un importo o una quantità oltre ~15 cifre significative si salva arrotondato
  (`123456789012.123456` torna `123456789012.123459`). Fino a ~1e10 il 6° decimale regge: nessun portafoglio personale
  ci arriva. Ma `backend-db.instructions.md` («`Numeric(18, 6)` for precision») fa credere a 18 cifre esatte. Proposta:
  scriverlo in quelle istruzioni e nella pagina dev del DB; nessun cambio di schema. Dettagli: piano J, §10 «CP-15».
  - ✅ 17/10: verificata, già coperta; nessuna modifica (J, sola lettura). Le istruzioni non dicono più
    «`Numeric(18, 6)` for precision»: da C-97 e W-B60 importi, quantità e prezzi sono `RealDecimal`
    (`db/real_decimal.py`), che rilegge il decimale scritto con al più 15 cifre significative, e un valore oltre i
    limiti della colonna è rifiutato (`backend-db.instructions.md`, «Conventions»). La pagina dev del DB
    (`architecture/database/index.md`, «Decimal Columns») dice che SQLite tiene un `NUMERIC` come double e ignora
    la precisione dichiarata, con gli esempi di lettura. Dettagli: piano 05, §10 «Documentazione».
    Prova: la verifica nel diario `e0996ab26` → dev `78e2171ee`, senza cambi.
- **J-19 · Il PAC finisce in `worker_crashed` sotto carico** — da capire: OOM o timeout del worker; basso, robustezza;
  segnalata da G tramite il coordinatore, 16/10. Il 15/10 alle 23:05, nella galleria G-13 dei colori, il 4° e il 5°
  calcolo del PAC sono finiti in `tool_error` con `worker_crashed`: il processo isolato dello strumento è uscito prima
  del risultato. Carico fra 80 e 96, macchina molto in swap. Rifatto con il carico a 40–61: 8 su 8 verdi. Il runtime dei
  Tools non è cambiato da `g-final3`. Dettagli: checkpoint di G-13 dei colori.
  - **Dal codice** (J, sola lettura): un superamento misurato della memoria dà `memory_limit`
    (`tools/process_tree.py`, `observe_memory_limit`), un tempo scaduto dà `execution_timeout`
    (`tools/executor.py`, `_read_exact`, `_wait_result`). `worker_crashed` vuol dire che il figlio è uscito o ha chiuso il
    tubo senza nessuno dei due: ucciso da fuori, un limite colpito dentro il figlio, o un errore all'avvio sotto swap.
  - **Proposta**: registrare nel log, e nelle metriche dell'elemento, il codice d'uscita del figlio (negativo = il
    segnale) e il picco di memoria osservato. Alla prossima caduta, il triage con la skill `test-triage`. Il file è dei
    Tools: lotto piccolo, d'accordo col proprietario del runtime.
  - ✅ 17/10, **strumentazione fatta** (J; via del coordinatore, `schemas/tools.py` ed `executor.py` a J per il lotto):
    `a8299354f` → dev `635b50537`.
    - `ToolItemMetrics.worker_exit_code`: lo stato d'uscita del worker caduto, letto prima della pulizia che lo
      segnalerebbe (attesa di raccolta 0,5 s): il codice, o il segnale in negativo (−9 = SIGKILL, come l'OOM killer
      del kernel). È null per ogni altro esito, e per una caduta vista col figlio ancora vivo.
    - Il padre scarta un valore mandato dal worker.
    - Una riga `Tool worker crashed` (identificativi, stato d'uscita, memoria, tempo; mai input né risultato).
    - Il picco di memoria era già nelle metriche (`resources.memory`).
    - 7 test in `tools-lifecycle`: 23, −9, figlio vivo → null, la riga di log, più i controlli.
    - **Resta aperta la causa**: alla prossima caduta, il triage con questi dati (skill `test-triage`). Dettagli:
      piano 05, §10 «J-42 e J-19».
- ✅ **J-20 · `AllocationItem.value` si dice «0-100» ma con la liquidità negativa esce da quei limiti** — minimo,
  chiarezza (contratto dell'API); segnalata da Y (Y10, decisione 49) tramite il coordinatore, 16/10.
  `backend/app/schemas/portfolio.py:79` descrive `value` come «Percentage share (0-100)»: con la liquidità negativa le
  quote positive superano 100 e la riga della liquidità va sotto zero. Cura: descrivere la quota sul totale netto, che
  può superare 100 o scendere sotto zero quando la liquidità è negativa; poi `api sync`. Nessun valore cambia. Lotto: J,
  dentro CP-6.
  ✅ Chiusa da J il 16/10 in CP-6: la descrizione dice la formula (`amount / sum of all slices × 100`, arrotondata a
  0,01) e che con la liquidità negativa la fetta della cassa va sotto zero e le altre possono superare 100. `api sync`
  senza file tracciati cambiati. Commit: il checkpoint di CP-6, `58c10197c` → dev `628e3e49e`.
- ✅ **J-21 · La linea di un segnale del backend scavalca i punti che non hanno un valore** — basso, chiarezza; trovata dal
  test-author di J (CP-10a), 16/10. Il renderer toglie i punti senza numero (`charts/signals/backendRenderer.ts:215`),
  giustamente: mai uno zero finto. Ma `components/charts/chartCoreHelpers.ts:334` mette `connectNulls` a `true` quando
  il segnale non lo dice, e il renderer non lo dice mai: la linea unisce i due lati del buco come se ci fossero valori.
  Vale per ogni segnale del backend; il Rolling Return a calendario, ora nel pannello, ne ha quando manca il prezzo di
  riferimento a metà serie. Proposta: per i segnali del backend la linea si interrompe dove il punto non ha valore
  (`connectNulls: false` nel renderer), con un Vitest. File dei grafici: Y (FE2), o J d'accordo con Y. Dettagli: piano J,
  §10 «CP-10a».
  - ✅ 17/10: fatta da J con l'alternativa precisa approvata dal coordinatore. `connectNulls: false` avrebbe
    interrotto ogni indicatore delle sessioni a ogni fine settimana. Il renderer divide una linea o un'area in tratti
    ai punti senza valore, e i giorni assenti restano uniti. Con la ricaduta (a), il badge «📈N» conta le date
    distinte (`renderedSignalPointCount`), giusto ora anche per RSI, CCI, MFI e StochRSI. Rivedono Y (renderer) e
    X (le due pagine). Dettagli: piano 05, §10 «J-21».
  - ✅ 17/10, **J-21 bis** (nota di Y): con una finestra piccola su un asset poco scambiato, un'uscita arrivava a centinaia
    di tratti, cioè di serie. Tetto `MAX_LINE_RUNS = 30`: oltre il tetto, un'uscita senza stile (o un'area) è una linea
    unita, chiamata «(gaps joined)», più un avviso nel risultato, in 4 lingue. Nessun tratto di un punto con una
    finestra di 3 o più. La cura vera è J-59. Dettagli: piano 05, §10 «J-21 bis».
  - Commit: J-21 `85a1c6f89` → dev `78e2171ee`; J-21 bis `def1d5259` → dev `539371064`. Revisione a posteriori di Y
    (19/10): OK, con tre seguiti in J-61 (l'avviso del tetto non arriva all'utente).
- **J-22 · Debito di traduzione di CP-10a (un solo Rolling Return, J-13)** — basso, documentazione; J, 16/10. Pagine EN
  cambiate di senso, senza stamp: `financial-theory/fundamentals/returns` (tutta la sezione Rolling Return; esce l'ancora
  `#rolling-return-sessions`), `financial-theory/technical-analysis/indicators/index` (introduzione, righe Rolling Return e
  Rolling Beta), `financial-theory/technical-analysis/risk-metrics/volatility` (prima frase della volatilità mobile),
  `user/assets/detail/signals` (la voce Rolling Return e il paragrafo sulle finestre). ⚠️ `returns` e `signals` vanno
  tradotte **nello stesso giro**: le pagine IT/FR/ES dei segnali puntano a `#rolling-return-sessions`, che oggi esiste
  solo nelle `returns` IT/FR/ES; tradotta `returns` da sola, quei tre link si rompono. Dettagli: piano J, §10 «CP-10a».
- ✅ **J-23 · Due incoerenze nelle pagine dell'analisi tecnica** — minimo, documentazione; trovate dal docs-writer di J
  (CP-10a), 16/10, già prima del lotto. `financial-theory/technical-analysis/index.en.md:17` dice i concetti del gruppo
  Rischio «sotto Risk Metrics», ma quello del Rolling Return sta sotto Returns; la riga Underwater Drawdown di
  `indicators/index.en.md` porta a `max-drawdown`, mentre il `docs_path` del plugin e la pagina dei segnali portano a
  `current-drawdown`. Da allineare in un lotto di documentazione, con il loro debito di traduzione.
  - ✅ 17/10: fatta da J nelle 4 lingue, due link. Il Rolling Return rimanda a Returns; la riga Underwater Drawdown
    a `current-drawdown`. `technical-analysis/index` timbrata. `indicators/index` ha già un debito di traduzione
    da `af919560c` (CP-10a, solo EN), lasciato alla pipeline. Dettagli: piano 05, §10 «Documentazione».
    Commit `bb8dca7d3` → dev `78e2171ee`.
- ✅ **J-24 · Consegna al costo d'un titolo estero: i lotti e la Dashboard danno totali diversi** — basso, numeri (caso
  raro); trovata dal docs-writer di J (CP-7a), 16/10, già da CP-16. Una rettifica in uscita col costo, su un titolo in
  un'altra valuta: i lotti valutano la consegna al cambio del giorno (da CP-7a la differenza di cambio dal giorno
  d'acquisto è realizzata; prima stava nel «di mercato»), la Dashboard toglie il costo dal capitale al valore storico e
  la lascia cadere. Scarto dei totali: `q × costo × (cambio alla consegna − cambio all'acquisto)`. Decisione del
  developer: (A, proposta) «al costo» anche nella valuta del report: i lotti valutano la consegna al costo medio storico
  del pool nella valuta del report, come la Dashboard; (B) tenerla così e scriverlo nella pagina. Dettagli: piano J, §10
  «CP-7».
  **Decisione del developer** (P21, 16/10): «convertire nella valuta di destinazione al cambio del giorno della
  transazione, e fare ogni calcolo nella valuta di destinazione, come nel fix appena prima della 1.2». I lotti la
  seguono già (CP-7a); la Dashboard no: si allinea la Dashboard (la distribuzione al cambio del giorno della rettifica,
  la differenza col costo storico nel realizzato), lotto proprio dopo J-17. La proposta (A) cade. Dettagli: piano J,
  §10 «J-24».
  - ✅ 16/10: fatta da J con la regola P21 (`9d702ae8d`): la Dashboard realizza D − C nel giorno della consegna, come i
    lotti. Da capo a fondo in USD con W-B55 (`2a35c1b73`). Dettagli: piano 05, §10 «J-24».
- **J-25 · Debito di traduzione di CP-7a (lotti in un'altra valuta)** — basso, documentazione; J, 16/10. Pagine EN
  cambiate di senso, senza stamp: `financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis`
  (sezione nuova `#lots-in-another-currency` con l'esempio D-J1), `…/fifo-engine/index` (una frase rovesciata, un
  paragrafo nuovo, due link) e `financial-theory/instruments/transaction-types/adjustment` (la nota sulla valuta della
  consegna rovesciata). `index` punta all'ancora nuova: tradurla con `fifo-lot-analysis` nello stesso giro. Dettagli:
  piano J, §10 «CP-7a».
- ✅ **J-26 · Sonda reale dell'AI Export per CP-7a** — basso, prova; J, 16/10. **Chiusa il 16/10** (commit al checkpoint):
  sonda reale sulla copia dei dati del developer (P26), base `4f0a5d323` contro la mia HEAD, 9 casi. Equivalenza
  UI/sonda esatta; solo le versioni attese (J-17, MF), tutte compatte; il testo cambia solo nella provenienza (J-17,
  J-24); nessun reperto. Il ponte della sonda era rotto su dev dal 16/10 11:18 (Z-20): corretto nello stesso lotto.
  Testo originale: Il realizzato e il «di mercato» dei lotti
  esteri cambiano (decisione 26) attraverso builder invariati, quindi nessuna versione; i test dei componenti passano
  (302). La sonda mirata (`ai_export_real_prompt_probe.py`) gira sugli utenti reali del developer e con le loro
  credenziali, che una corsia coordinata non ha: da fare col developer, un Asset con un lotto USD chiuso e il suo Broker
  (atteso: realizzato coi cambi delle due date, non realizzato 0). Dettagli: piano J, §10 «CP-7a».
- ✅ **J-27 · `ControlTotals.from_json` espande per intero un importo con un esponente enorme** — basso, robustezza;
  **chiusa il 16/10** (commit al checkpoint): `_as_amount` legge solo testo decimale semplice, al più 60 cifre per parte;
  doc e docstring dicono la prova del ripristino prima della conferma. Testo originale: trovata
  dal test-author di B con una sonda, via il coordinatore, 16/10. `_as_amount` (`financial_math/ledger_totals.py:190`)
  accetta ogni testo decimale finito e lo passa a `_canonical`, che lo scrive per esteso: `"1E+50000000"` costa 121 MB e
  0,4 s, quindi un manifest scritto a mano può esaurire la memoria nella prova a secco del ripristino. B si protegge da
  sé in B-13 (solo testo decimale semplice prima di `from_json`). Proposta: `_as_amount` rifiuta esponenti e lunghezze
  oltre la precisione del suo contesto (`_EXACT`, 60 cifre), così ogni chiamante è protetto; rosso prima (test-author).
  Dopo CP-10a e CP-7a. Dettagli: piano J, §10 «CP-15».
  ✅ 16/10: fatta da J (checkpoint J-27), `7336722ad` → dev `e221a0544`.
- ✅ **J-28 · L'avviso dei lotti «nessun prezzo di mercato, valore al costo» scatta anche quando gli scambi prezzano
  l'asset** — basso, chiarezza; J, 16/10 (letto durante J-17). **Chiusa da CP-7b il 16/10** (commit al checkpoint):
  l'avviso e il valore al costo seguono la regola per giorno della Dashboard (nessuna osservazione ≤ il giorno, né
  quotazione né BUY o SELL), e l'avviso nomina esattamente quei giorni; descrizione di `value_source` corretta. Testo
  originale: `lots_analysis_service.py:141` mette `estimated_mode` quando
  l'asset non ha quotazioni (`PriceHistory`) fino alla fine della finestra, e `:283` aggiunge
  `CURRENT_PRICE_ASSUMED_AT_COST` («No market price … open value estimated at cost, market P&L excluded»). Ma il valore
  dei lotti viene dal risolutore unico, che usa anche i prezzi di BUY e SELL: un asset senza quotazioni ma con scambi è
  valutato allo scambio (`:760`, ramo `MARKET_PRICE`), e l'avviso dice il falso. C'era già prima di J-17. Proposta:
  l'avviso solo quando i lotti sono davvero al costo, cioè senza alcuna osservazione (né quotazione né BUY o SELL), la
  condizione del ramo `ESTIMATED_AT_COST`; rosso prima. Nello stesso lotto la descrizione di `LotSummarySchema.value_source`
  (`schemas/portfolio.py:829`: «MARKET_PRICE quando c'è un prezzo reale, se no ESTIMATED_AT_COST»), che è anche
  `MARKET_PRICE` per un prezzo di scambio e `None` senza segno con l'asset quotato; `api sync`. Dopo CP-7b (V1 tocca la
  stessa sintesi). Dettagli: piano J, §10 «J-17», rapporto degli specialisti.
  Commit (CP-7b): `0bd9ecd82` → dev `48da9bf3c`.
- **J-29 · Debito di traduzione di J-17 (una rettifica non è un prezzo; valore al costo)** — basso, documentazione; J,
  16/10. Pagine EN cambiate di senso, senza stamp, tutte sotto `financial-theory/technical-analysis/`:
  - in `performance-metrics/portfolio-engine/`: `price-resolution`, `index` (§2, §3), `nav`, `deposited-capital`,
    `period-pnl`;
  - `performance-metrics/fifo-engine/fifo-lot-analysis` (sezione `#estimated-at-cost` riscritta);
  - `performance-metrics/weighted-average-cost` e `risk-metrics/data-quality`.

  Pagine utente: `user/dashboard/index`, `positions`, `charts`, `kpi-cards`, e `user/tools/pac-allocator/index`.
  `translate-validate` (16/10) dà 18 errori strutturali nuovi da J-17, su 747 del sito:
  - 12 per il link nuovo a `index.md#3-position-state` (`price-resolution`, `nav`, `period-pnl`, `deposited-capital`);
  - 3 per un blocco di formula nuovo in `price-resolution`;
  - 3 per un link nuovo a `#estimated-at-cost` in `fifo-lot-analysis`.

  Tradurre `index` con le quattro pagine che vi puntano, nello stesso giro. Dettagli: piano J, §10 «J-17».
- **J-30 · Il primo parse del BRIM dopo l'avvio supera i 30 s del test sotto carico** — basso, tempo dei test e prima
  importazione; J, 16/10 (slot 2 di J-17), da smistare dal coordinatore (area del BRIM). Il primo
  `POST /brokers/import/files/{id}/parse` fa partire il pool dei processi (`brim_parse_pool.py`, forkserver): **48,8 s**
  nello slot e **31,2 s** al rilancio, con carico 100–158; i parse seguenti 0,2–1 s. `test_brim_api.py::TestParseEndpoint`
  aspetta 30 s fissi (`TIMEOUT`), quindi il primo test della classe scade. Verdetto `test-triage`: lentezza.
  Strade possibili: scaldare il pool all'avvio del server, oppure una fixture che lo scaldi prima dei test temporizzati.
  Allungare il tempo no. Dettagli: piano J, §10 «J-17», slot 2.
- **J-31 · Debito di traduzione di CP-13a (il guadagno che recupera un drawdown)** — basso, documentazione; J, 16/10.
  Pagine EN cambiate di senso, senza stamp: `financial-theory/technical-analysis/risk-metrics/max-drawdown` (dopo
  l'avviso dell'asimmetria, in `#recovery-time`: il risultato porta il guadagno dal minimo al picco; prima diceva che il
  sistema calcola solo la lettura corrente, e IT/FR/ES lo dicono ancora) e `…/risk-metrics/current-drawdown` (il
  paragrafo dopo la formula, quello nuovo sulla perdita totale con l'avviso, la prima frase dell'avviso, in
  `#what-it-takes-to-get-back`). `translate-validate` (16/10): 3 errori strutturali nuovi, il link da `max-drawdown`
  a `current-drawdown.md#what-it-takes-to-get-back`. Tradurle nello stesso giro. Dettagli: piano J, §10 «CP-13a».
- **J-32 · Debito di traduzione di J-24 (la rettifica in uscita consegna al cambio del suo giorno)** — basso,
  documentazione; J, 16/10. Pagine EN cambiate di senso, senza stamp, sotto
  `financial-theory/technical-analysis/performance-metrics/`:
  - `portfolio-engine/deposited-capital`: sezione nuova `#outgoing-adjustments` con esempio, più punti riscritti;
    36 errori strutturali.
  - `portfolio-engine/index`: §8, con l'ancora nuova `#8-realized-gain-loss`, che i titoli tradotti devono portare.
  - `portfolio-engine/period-pnl`, `twrr`, `mwrr`, `weighted-average-cost`.
  - `fifo-engine/index`, `fifo-engine/fifo-lot-analysis`.

  Fuori da quella cartella: `financial-theory/instruments/transaction-types/adjustment` e
  `user/dashboard/kpi-cards`. `translate-validate` (16/10): 63 errori strutturali nuovi da J-24. `adjustment`, `fifo-engine/index` e
  `fifo-lot-analysis` avevano già debito (J-25). Tradurle nello stesso giro, con `index` (l'ancora del §8). Dettagli: piano
  J, §10 «J-24».
- ✅ **J-33 · Lo storico della performance dei lotti salta i giorni senza prezzo, la Dashboard li valuta al costo** —
  medio-basso, numeri; J, 16/10, trovata in CP-7b.
  - Dove: `lots/histories.py::build_performance_history` (ROI e TWRR dei lotti, `PERFORMANCE_HISTORY`). Fa la NAV solo
    nei giorni con un prezzo; i flussi di prima li porta al primo giorno con la NAV.
  - Il caso: un asset il cui primo possesso è una rettifica prima della sua prima osservazione. Da CP-7b gli storici del
    valore e del rendimento valutano al costo i giorni senza osservazione ≤ sé, come la Dashboard (J-17, decisione (a)
    del coordinatore). La performance invece ha un buco in quei giorni, e il salto dal costo al primo prezzo può cadere
    fuori dalla catena del TWRR.
  - C'era già prima di CP-7b, per ogni asset.
  - Stesso caso, effetto più forte (docs-writer di CP-7b): un trasferimento che attraversa il perimetro dei broker in un
    giorno al costo non ha prezzo, quindi `invalid_external_flow_from` svuota ROI e TWRR da quel giorno in poi. La
    Dashboard valuta quella gamba al costo.
  - Proposta: la NAV di quei giorni, e la gamba di un trasferimento che attraversa il perimetro, al costo dei lotti LONG
    aperti (costo noto, cambio all'apertura; un giorno con un lotto SHORT aperto o un costo ignoto resta senza punto), con
    le stesse `at_cost_until`; rosso prima. Dichiarare prima i valori che cambiano.
  - Dettagli: piano J, §10 «CP-7b — codice».
  - ✅ 17/10: fatta da J (checkpoint J-33). Nei giorni senza osservazione la NAV è al costo dei lotti LONG aperti (cambio
    d'apertura) e un trasferimento sposta il costo delle sue unità; il TWRR comprende il salto dal costo al primo
    prezzo, come il ROI. Una rettifica senza costo conta 0 come nella storia del valore (J-35 resta al developer).
    Dettagli: piano 05, sezione «J-33».
    Commit `2434588ca` → dev `104333567`.
- **J-34 · Debito di traduzione di CP-7b (il riferimento dei lotti e i giorni al costo)** — basso, documentazione; J,
  16/10. Pagine EN cambiate di senso, senza stamp:
  - `financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis`:
    - Open Return per Lot: le tre provenienze del riferimento, `exact`/`fallback`, il cambio della data d'apertura,
      l'esempio nuovo «A lot received by succession», il consiglio ritolto;
    - Estimated-at-Cost riscritta per giorno, con la rettifica senza costo;
    - un paragrafo di From Lots to Aggregate Metrics.
  - `…/portfolio-engine/price-resolution` (§ Missing Marks, la frase dei lotti) e `user/dashboard/positions` (due punti).

  `translate-validate` (16/10): da 882 a 891 errori strutturali, tutti in `fifo-lot-analysis`: 24 righe nuove e 15
  sparite. Sono l'ammonimento nuovo, che sposta il tipo dei seguenti, e il link nuovo ad `adjustment`. La pagina aveva
  già debito (J-25, J-29, J-32): tradurla in un giro solo. Dettagli: piano J, §10 «CP-7b — codice».
- ✅ **J-37 · Il testo del catalogo di `lots-analysis-pure` non dice più cosa prova l'unità** — minimo, test; J, 16/10
  ✅ 17/10, dentro il checkpoint di CP-14a (commit a parte): `print_info`, `desc` e commento d'isolamento di
  `lots-analysis-pure`, più la stringa di `risk-oracle` (`signal_helpers.py` → `signals/risk_adapters.py`).
  (test-author di CP-7b).
  - Dove: `scripts/test_runner/_backend_services.py`, unità `lots-analysis-pure`. Tre testi descrivono ancora i test di
    prima: `print_info` (~:893), `desc` (~:1894) e il commento di `isolation="pure"` (~:1897-1898), che parla solo dei
    due casi asincroni con `convert_bulk` finto.
  - Da CP-7b l'unità prova anche i giorni al costo e il riferimento, con casi che guidano `get_lots_analysis` su loader
    finti e una sessione finta; resta pura.
  - Testo proposto nel passaggio di CP-7b.
  - Quando: il file è condiviso e A ce l'ha aperto (A7b). Lo scrive J dopo l'ingresso di A, su indicazione del
    coordinatore (16/10 22:22).
  - ✅ 17/10: fatta in CP-14a, `ec8a0b31e` → dev `03101ddad`.
- **J-35 · Un lotto aperto da una rettifica senza costo vale 0 nei giorni al costo, la Dashboard lo lascia senza
  valore** — basso, numeri; J, 16/10 (docs-writer di CP-7b).
  - Il motore FIFO apre il lotto a costo zero («a zero-cost quantity correction»). Il costo medio della Dashboard invece
    conta quel costo come ignoto (`ADD_UNKNOWN_COST`, `report_complete=False`), quindi `_value_held_position` lascia la
    posizione MISSING. È la differenza documentata in `financial-theory/instruments/transaction-types/adjustment`
    («the FIFO lot opens at zero cost, but the average cost (WAC) treats the cost as unknown»).
  - Effetto: nei giorni senza osservazione (CP-7b, regola per giorno) i lotti mostrano quel lotto a 0, la Dashboard
    nulla. Prima di CP-7b succedeva solo per un asset senza alcuna osservazione; ora anche prima della prima
    osservazione di un asset prezzato dopo.
  - Raro: una rettifica positiva si salva senza costo solo se legata a uno split, che non apre lotti. Restano le righe
    salvate prima dell'obbligo, e quelle il cui evento di split è poi diventato un aggiustamento di prezzo (il percorso
    di P-10: `transactions/auto_cost.py:76-82`, fissato da `test_portfolio_wac.py:521`), che aprono un lotto a costo
    zero.
  - Proposta: decidere insieme a J-11 (la rettifica in uscita senza costo) se una rettifica senza costo ha un costo
    zero o ignoto. Se ignoto: un segno `cost_known` sul lotto, messo dal motore, e niente valore al costo senza di
    esso (sintesi e storici); rosso prima.
  - Dettagli: piano J, §10 «CP-7b — codice».
- ✅ **J-36 · I due messaggi del prezzo di riferimento dei lotti dicono cose inesatte** — basso, chiarezza; J, 16/10
  (docs-writer di CP-7b). Chiavi `dataQuality.referencePriceFallback` / `referencePriceUnavailable`, quattro cataloghi.
  - `referencePriceUnavailable` («relative return cannot be computed»): falso per un lotto col suo costo, che ripiega
    sul proprio prezzo (`opening_reference_price`, sorgente `exact`). Vero solo per un lotto a costo zero.
  - `referencePriceFallback` («Lot opening price unavailable on the exact date — using last known price
    {reference_price}»): da CP-7b esce anche per la media degli scambi del giorno stesso (decisione 1: `exact` solo per
    una quotazione), quando un prezzo quel giorno c'è. Inoltre `{reference_price}` è nativo, senza valuta né conversione.
  - Proposta: testi che dicono cosa fa il calcolo («no market quote on the opening day — the reference is the last
    known price, a carried quote or a trade price»; «no price on or before the opening day — the relative return uses
    the lot's own price, when it has one»), e il prezzo convertito con la sua valuta; quattro lingue.
  - Dettagli: piano J, §10 «CP-7b — codice».
  - ✅ 17/10: fatta da J (checkpoint J-36). I due testi dicono cosa fa il calcolo, nei 4 cataloghi, senza il prezzo: il
    banner dei lotti raggruppa le issue per codice in un messaggio solo (i parametri della prima) con un chip per lotto,
    quindi un prezzo non può valere per tutti. Il parametro `reference_price` resta nei `message_params`, non letto.
    Dettagli: piano 05, sezione «J-36».
    Commit `ff84d674f` → dev `e5a975c8b`.
- ✅ **J-38 · La guida dei plugin dei segnali descrive male l'ordine del taglio e il piano** — minimo, documentazione; J,
  17/10 (docs-writer di CP-10c). Pagina `developer/architecture/patterns/signal_plugin_guide.md`, solo inglese.
  - Il diagramma di sequenza del grafico disegna «Slice to visible range and assign status» dopo le annotazioni. Nel
    codice, prima e dopo CP-10c, taglio e stato avvengono per ogni calcolo dentro `execute_planned_signal`; le
    annotazioni si attaccano dopo, sulle serie intere tenute da parte. Il testo «3. Annotations» («before output is
    sliced») è impreciso allo stesso modo.
  - La sezione del piano non dice che un lotto incoerente solleva `SignalRequestValidationError` e ferma tutto il lotto,
    a differenza dei fallimenti preliminari, che restano per istanza.
  - Preesistenti, non legati al taglio. Dettagli: piano J, §10 «CP-10c».
  - ✅ 17/10: fatta da J (docs-writer). Il diagramma taglia e assegna lo stato dentro il ciclo; le annotazioni
    girano dopo, sulle serie estese. «3. Annotations» è riscritta. Il Piano dice che un lotto incoerente solleva
    `SignalRequestValidationError`, ferma tutto il lotto e diventa un 422. Dettagli: piano 05, §10 «Documentazione».
    Commit `bb8dca7d3` → dev `78e2171ee`.
- **J-39 · Investimento programmato: l'ultima cedola contata due volte, e la mora che parte dal valore prima della
  cedola** — medio, numeri; J, 17/10 (docs-writer di CP-14a, verificata da J in memoria). Preesistente: viene da
  I-bis #26, che emette alle date di maturazione il valore prima dell'azzeramento della cedola, giusto per il grafico.
  Lo stesso valore finisce però in due consumatori che vogliono quello dopo:
  - **Liquidazione**: `_generate_schedule_values` mette in `MATURITY_SETTLEMENT` `values[last_end]`, il valore prima
    della cedola. Un titolo da 10 000 al 5 % con cedola annuale a scadenza e senza mora dà INTEREST 498,63 **e**
    MATURITY_SETTLEMENT 10 498,63: 10 997,26 incassati, e l'ultima cedola è contata due volte. La liquidazione giusta
    è il valore dopo la cedola, qui 10 000.
  - **Mora**: `_compute_late_interest_value` riceve `cached[maturity]`, ancora il valore prima della cedola. Con mora
    SIMPLE al 10 %, il giorno dopo la scadenza dà 10 501,37 invece di 10 002,74: la cedola è pagata e insieme ancora
    dovuta.
  - Da decidere (developer, perché è modellazione): se c'è mora, la cedola di scadenza è pagata (base = capitale) o
    no (niente evento INTEREST a scadenza, base con la cedola)? Oggi il codice fa tutte e due le cose.
  - **Dopo la scadenza, con la mora** (verificato da J nel codice il 17/10, ~04:05):
    - la liquidazione della mora nasce solo in `get_history_value`, all'ultima data di maturazione della mora ≤ la
      `end_date` della richiesta: si sposta con la finestra. `get_current_value` intanto continua a maturare senza
      fine;
    - le cedole della mora (`li.generate_interest`) valgono ciascuna `value − principal`, senza azzeramento dopo:
      ogni pagamento riconta tutti quelli prima.
    - Senza mora le due strade concordano (tutte e due leggono la liquidazione): la cura di CP-14b le corregge
      insieme.
  - La rete dorata di CP-14a (`accrual_golden.json`, casi s2 e s4) fissa i valori di oggi: la cura li cambia,
    dichiarati, col rosso prima.
  - **Decisione del coordinatore (17/10, notte)**:
    - la liquidazione senza mora va in **CP-14b**, coi valori dichiarati, il rosso prima e una riga 🐛;
    - la parte della mora aspetta il developer (la domanda è nella lista del mattino);
    - `get_current_value` contro `get_history_value` dopo la scadenza si verifica nell'analisi di CP-14b.
  - **Liquidazione senza mora: curata in CP-14b (17/10, `69cc2faac` → dev `4111239a7`)** — è il capitale quando l'ultima cedola cade alla scadenza,
    altrimenti il valore del giorno; `get_current_value` e `get_history_value` dopo la scadenza la seguono. Rosso prima,
    8 punti della rete dichiarati (le liquidazioni di `s4_annual_settlement` al capitale). **Resta aperta la parte
    della mora**: base, liquidazione che si sposta con `end_date`, cedole della mora senza azzeramento (developer).
  - Dettagli: piano J, §10 «CP-14a» e «CP-14b».
- ✅ **J-40 · Lo svuotamento dei dati di mercato toglie gli SPLIT e lascia rettifiche senza costo (il buco di P-10 dal
  lato asset)** — medio, numeri, da decidere; test-author di J (CP-14a, V-4), 17/10, letto nel codice. Area di X.
  - `POST /assets/{id}/market-data/wipe` (`market_data.py:46-71`) è il flusso del cambio di valuta
    (`AssetCurrencyChangeModal.svelte:103-109`), ma si può chiamare anche da solo.
  - Stacca ogni transazione dagli eventi dell'asset e li cancella tutti, SPLIT compresi (`currency_change.py:131-137`).
  - Una rettifica +q legata a uno SPLIT e salvata senza costo (Auto) diventa un'acquisizione di costo sconosciuto,
    cioè `MISSING_COST_BASIS`: lo stesso esito che P-10 rifiuta.
  - Il pannello di conferma mostra solo il numero delle transazioni legate.
  - **Deciso dal coordinatore (17/10, notte): un rifiuto come P-10** (lo svuotamento risponde 409 coi dettagli),
    coerente con la decisione 27 A. **→ X** (anche il parente minore).
  - Parente minore: il cambio dei parametri di un investimento programmato stacca e cancella gli eventi del provider
    (`provider_management.py:212-221`). Conta solo se l'utente ha scritto uno SPLIT negli eventi del calendario.
  - ✅ 17/10: fatta da X come **X-R48** (dev `2ea54ff76`): il rifiuto `MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST` (409)
    usa `costless_incoming_split_adjustments` di J; J ha rivisto dopo (OK). Il parente minore resta aperto come
    **X-R49** (di X).
- ✅ **J-41 · Il costo Auto può finire sulla riga sbagliata** — medio, numeri; test-author di J, 17/10, letto nel codice,
  **da provare con un rosso**. Area di W.
  - Senza legame, `_find_created_tx_for_wac` (`auto_cost.py:158-183`) prende la riga più recente con stesso broker,
    asset, data e tipo.
  - Due rettifiche Auto dello stesso asset, nello stesso giorno, sullo stesso broker e nello stesso lotto: la prima non
    riceve mai un costo. Essendo Auto salta il controllo del costo (`batch_costs.py:154-155`), e resta senza.
  - Varianti: una riga Auto seguita da una Manuale con la stessa chiave sovrascrive il costo Manuale; dal modale bulk
    (`{amount: "0"}`, `TransactionBulkModal.svelte:1099`) la riga mancata resta a 0 in silenzio.
  - **→ W** (coordinatore, 17/10).
  - ✅ 17/10: già fatta, è **W-B67** (W, `279b3d5bd`, entrata con `ac92e6fae` alle 14:00): ogni create si costa sulla
    propria riga (`context.created_by_index`, `_find_created_tx_for_wac` tolta) e le righe Auto in ordine di data
    (N84). I due casi sono test di W-B67 per nome, rossi fino alla cura: `test_two_auto_rows_on_one_key_each_hold_the_
    average_before_the_other` e `test_auto_then_manual_on_one_key_each_row_keeps_its_own_cost`
    (`services transaction-cost-basis-rule`). La variante del modale bulk non può più accadere: nessuna riga resta
    senza costo. Nessun codice da J. Vicina ma diversa: **J-57**. Dettagli: piano 05, §10 «J-41».
- ✅ **J-42 · Il rapporto di uno SPLIT non è mai validato** — basso, numeri; test-author di J, 17/10, letto nel codice.
  Area di X. Un rapporto 0 o negativo si salva (P-10 lascia passare la modifica, il tipo non cambia). Quando una
  transazione lo lega, il motore solleva `ValueError` (`engine.py:226-227`) e il rapporto della Dashboard risponde
  500. `is_valid_split_ratio` della casa (`splits.py`) esiste già. **→ X** (coordinatore, 17/10).
  - ✅ 17/10: già fatta, nessun codice da J (tornata da X a J il 17/10, verificata).
    - La scrittura è **X-R47** (`5f68a8db0`): `bulk_upsert_events` → `_reject_invalid_split_ratios` con
      `is_valid_split_ratio`. Copre ogni modo di scrivere uno SPLIT a mano, anche una modifica che tiene il tipo e
      che P-10 lascia passare, con un 400 `EVENT_INVALID_SPLIT_RATIO` tradotto in 4 lingue; un aggiornamento del
      provider lo scarta.
    - La lettura è **MF-D4**: un rapporto salvato non valido conta come mancante e non fa più rispondere 500, con
      l'avviso `INVALID_SPLIT_RATIO`.
    - Verdi su HEAD: `services event-split-ratio` 78, `roi-fifo-utils -k invalid_split` 69. Dettagli: piano 05, §10
      «J-42 e J-19».
- ✅ **J-43 · L'avviso delle quote diverse fra le due gambe di un trasferimento tace se cadono lo stesso giorno** —
  minimo, qualità dei dati; MF (MF-J4), assegnata a J dal coordinatore il 17/10, dopo CP-14b.
  - In `financial_math/portfolio/classifier.py:131-149` l'avviso `share mismatch` sta dentro il ramo
    `if pair_key not in processed_pairs and tx.date != paired.date:`, quello che costruisce l'intervallo in transito.
  - Due gambe collegate dello stesso giorno, fra broker con quote di proprietà diverse, non producono nessun avviso
    (`share_mismatch_warnings`, `schemas/portfolio.py:239`).
  - Cura: l'avviso esce dal ramo delle date diverse e resta una volta per coppia. Prima il rosso.
  - **Analisi di J (17/10, 05:55): l'avviso non esce mai dal classificatore, in nessuna data.** `engine.py:246` non
    legge `classification.warnings`; `build_data_quality_report(classifier_warnings=…)` non ha chiamanti che lo
    passino; `DataQualityReport.share_mismatch_warnings` (e `in_transit_cost_basis_warnings`) non li riempie nessuno,
    da `77b976ebc` (giugno). Il modello è voluto (D-MF4 = a: lo scarto fra quote diverse è P&L), quindi l'avviso è
    l'unica spiegazione per l'utente. **J-43a** (come scritta) subito; **J-43b** (portarlo nel rapporto, issue INFO
    `TRANSFER_SHARE_MISMATCH` in 4 lingue, o togliere i campi morti) aspetta il via del coordinatore. Dettagli:
    [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «J-43».
- ✅ **J-44 · Il Δ% del tooltip del grafico dà 0 % quando il primo valore è 0** — minimo, numeri; J, 17/10, letto nel
  codice durante CP-14b. `components/charts/priceChartHelpers.ts::buildDeltaHtml` calcola il Δ% dal primo valore del
  grafico e, per scelta scritta nel suo JSDoc, dà 0 % su un primo valore 0. È lo stesso numero sbagliato che la
  decisione N65 toglie al righello (CP-14b: `—`), in una seconda copia del Δ% nel frontend (regola 10: va segnalata).
  Da instradare: il file ha storia dei colori (lotto B) e di X (helper della pagina asset). Dettagli:
  [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «CP-14b».
  - 17/10, coordinatore: **a J**, dopo F5, riusando `changePct` di `MeasureSignal.ts` (stessa regola di N65); X rivede in sola lettura, nessuna classe di colore toccata.
  - ✅ 17/10: fatta da J nel checkpoint di F5 (`changePct` esportato da `MeasureSignal.ts`, `buildDeltaHtml` con «—» su un
    primo valore 0); il coordinatore l'aveva passata a Y mentre era già fatta: resta nel checkpoint di J, **Y rivede**.
    Commit `824b27437` → dev `b6b615c3d`.
- ✅ **J-45 (SEC7-1b) · Il rigioco del motore del portafoglio gira sul ciclo degli eventi** — medio, sicurezza
  (disponibilità); J, 17/10, nell'analisi di R13-SEC7-1. `PortfolioCalculationEngine.calculate` chiama
  `builder.build()` (`engine.py:424`), lavoro di CPU sincrono, dentro una funzione `async`: un rapporto lungo ferma
  tutte le richieste dell'istanza per la sua durata. SEC7-1 toglie le date senza limite, non questo. Portarlo in
  `asyncio.to_thread` non è gratis: il costruttore legge oggetti ORM (`Transaction`) i cui attributi pigri potrebbero
  toccare la sessione asincrona da un altro thread; serve prima staccare i dati (valori semplici) dalla sessione.
  Decisione del coordinatore (17/10): nell'indice, non in SEC7-1. **→ MF** (coordinatore, 17/10 07:00: `run_in_executor` con un
  pool dedicato, `max_workers=2`, insieme a MF-D4 dopo l'ingresso di J-43/SEC7-1; J rivede). Dettagli:
  [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «R13-SEC7-1».
  ✅ 17/10: fatta da MF, `43a7f0156` → dev `15d414a69`; J ha rivisto (OK).
- ✅ **J-47 · Un trasferimento ancora in viaggio alla fine dell'intervallo manda i lotti in `FAILED`** — medio, numeri;
  J, 17/10, letto nel codice durante l'analisi di J-10, non ancora riprodotto. Con partenza ≤ `date_to` < arrivo,
  `LotsAnalysisService._load_transactions` taglia a `date_to` e la gamba d'arrivo manca: `TRANSFER_PAIR_MISSING`
  anche col perimetro intero (periodi dell'AI Export, intervalli della Dashboard che finiscono durante il viaggio).
  Coordinatore (17/10 08:05): subito dopo J-10, prima di J-12. Prima il rosso, poi la lettura al confine del tempo,
  coerente col transito della Dashboard (`in_transit_intervals`). Dettagli:
  [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «J-10».
  - ✅ 17/10: fatta da J (checkpoint J-47). La compagna in arrivo nel perimetro va solo al motore, che si ferma a
    `date_to` (`replay_until`): le unità restano in viaggio, come nella Dashboard. Nessun arrivo nella cronologia.
    Dettagli: piano 05, sezione «J-47».
    Commit `f40c598ba` → dev `647efcc28`.
- ✅ **J-48 · Le gambe di un trasferimento lette al confine del perimetro si vedono come «rettifiche» nei lotti** —
  basso, chiarezza; J, 17/10, da J-10 (N76). Nella modale della custodia, nel Gantt e nel grafico WAC una gamba che
  attraversa il perimetro compare come «Adjustment In/Out». La sistemazione: etichette esplicite di trasferimento,
  cioè un campo del backend sulle righe della cronologia, le 3 viste e l'i18n. In J-10 solo l'etichetta neutra della
  modale (scelta (a') del coordinatore, 17/10 08:05). Dettagli:
  [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «J-10».
  - 17/10: via del coordinatore al campo additivo `scope_boundary` (solo etichette, l'economia resta su `kind`, mai
    il broker compagno), con il codice dopo l'ingresso di Y-30. Lo stop del developer è arrivato prima di ogni file
    di prodotto.
  - ⏸️ **19/10, sospesa**: è fra gli ampliamenti che il developer sta leggendo. Il lavoro a metà è parcheggiato
    nella cartella di sessione di J, `files/parked/`: `j48-backend-scope-boundary.patch` (schema e servizio, mai
    applicata) e `j48-test-probe.patch` (solo la sonda del test-author, nessun test di J-48). `git apply --check` OK
    su `635b50537`. Dettagli: piano 05, §10 «J-19 entrata; MF-A12, J-1 di MF, analisi di J-48».
  - ✅ **19/10, fatta da J** (via del coordinatore delle 11:42, col developer: «se lo riesci a risolvere ok»).
    - Il backend dà `LotTimelineEventSchema.scope_boundary` (`IN`/`OUT`) sulle righe di una gamba letta al confine.
    - Le tre viste la mostrano come trasferimento: «TRANSFER+»/«TRANSFER-» nello Storico, il ◆ su Lot Life, «Transfer
      In»/«Out» sui segni del costo medio. Solo etichette: ogni cifra legge `kind`, e il broker compagno non compare.
    - Rossi prima: 5 backend, 30 Vitest, 2 della modale.
    - Verdi: `roi-fifo-utils` 1512, `api portfolio` 56, `core-unit` 9331, E2E `front-broker detail` 40.
    - Dettagli: piano 05, §10 «J-48 — le etichette esplicite di trasferimento». I commit li scrive il coordinatore
      all'ingresso.
- ✅ **SEC8-1b (da R13-SEC8 di E) · Il rigioco storico del rischio cammina un intervallo senza limiti** — alto,
  sicurezza (disponibilità); assegnata a J dal coordinatore (17/10 08:22), dopo J-10 e J-47. `replay_range` di
  `/risk/query` non ha limiti (`DateRangeModel` controlla solo `end >= start`) e arriva al caricamento dei prezzi e
  alla preparazione delle serie (`risk/replay.py`). Lo stesso clamp di SEC7-1, cioè `latest_range_end()` e un
  pavimento per l'inizio; l'ambito degli asset lo chiude X-R55 di Z. Prima i rossi, E rivede. Dettagli:
  [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «J-10».
  - ✅ 17/10: fatta da J (checkpoint SEC8-1b). `bounded_range()` in `risk/scope.py`: la fine al più domani, l'inizio al
    più presto 100 anni prima della fine (`range_span_floor`). Vale per l'intervallo principale di ogni richiesta e per
    la finestra del rigioco, proposta compresa: prima un prezzo piantato all'anno 1 faceva proporre una finestra
    dall'anno 1 (~739 000 giorni). La cura alla fonte, un pavimento sulle date dei prezzi scritti a mano, è **N83** di X.
    Dettagli: piano 05, sezione «SEC8-1b».
    Commit `949825b8b` → dev `a565e06d0`.
- ✅ **J-49 · Un controllo statico per i lettori di `latest_range_end`** — basso, test; proposta del test-author di Z
  con X-R55, girata dal coordinatore (17/10 08:30), non ora. La cucitura di SEC7-1
  (`test_scripts/test_services/_range_bounds.py`, `RANGE_BOUND_CONSUMERS`) toglie il limite solo nei moduli della
  sua lista. Z ci ha aggiunto `price_query` e `currencies` a mano, e SEC8-1b porterà un altro lettore. Un modulo di
  `backend/app` che legge `latest_range_end` e manca dalla lista fa fallire gli scenari 2032–2091 dei file che
  tolgono il limite. Il test: una lettura `ast` di `backend/app`, per cui l'insieme dei moduli che legano il nome
  (`from …datetime_utils import latest_range_end`) è uguale alla lista. Prima un rilevatore che vede un modulo finto,
  come le regole di `test_layer_boundaries.py`. Dettagli:
  [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «R13-SEC7-1».
  - ✅ 17/10: fatta da J (checkpoint J-49). `TestRangeBoundSeamCoversEveryReader` in `test_date_range_bounds.py`, con la
    prova del rilevatore su 10 sorgenti finte. Il rosso ha trovato due lettori arrivati oggi e mancanti dalla lista:
    `utils/date_range_limits.py` (X-R65) e `api/v1/assets/prices.py` (R13-SEC9-4). Erano una lacuna latente, nessuna
    suite ci passava. Aggiunti alla lista. Dettagli: piano 05, sezione «J-49».
    Commit `42185231b` → dev `e2e883136`.
- ✅ **J-50 · Il rifiuto dei troppi giorni di `get_prices_bulk` diventa un 500 nel rischio e nell'AI Export** — basso,
  chiarezza (è già un rifiuto, non un DoS); dal coordinatore (17/10 08:34), dopo SEC8-1b. Con Z-25 (N77)
  `get_prices_bulk` alza `BulkTooManyDaysError` (il nome lo darà Z all'ingresso di Z-25) oltre 5 M giorni-asset per
  richiesta. Il rischio (l'ambito degli asset) e l'AI Export lo chiamano dall'interno: senza traduzione l'utente vede
  un 500. Va tradotto in un rifiuto con codice, dalla parte del rischio (`RiskUnavailableError` con un `RiskErrorCode`)
  e dell'AI Export. Prima i rossi. Dettagli:
  [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «J-10».
  - ✅ 17/10: fatta da J (checkpoint J-50).
    - Rischio: ogni analitica risulta `unavailable` · `resource_limit` col rimedio `period_or_assets`, la
      convenzione D379 (200), al posto del 500.
    - AI Export: 422 `selection_not_applicable`, `reason_code` `too_many_price_days`, al posto del 503.
    - Una frase propria in 4 lingue per tutti e due. Dettagli: piano 05, sezione «J-50».
    - 17/10 13:45: dev rosso sulla guardia dei rimedi (il rimedio era un letterale fuori dalla tabella): curato in
      J-50b, una tabella e un costruttore in `risk/base.py` e una scansione che vieta un rimedio scritto altrove.
      Dettagli: piano 05, sezione «J-50b».
    - Commit: J-50 `11ef9ab6f` → dev `5bfdbe0af`; J-50b `d9da0ff54` → dev `ef74ff9fc`.
- ✅ **J-51 · Lo YoC di un co-proprietario manca sulle unità ricevute da un broker che non vede** — medio, numeri;
  J, 17/10, letto nel codice durante J-10, non riprodotto. `yield_on_cost._include_external_transfer_legs` aggiunge
  al rigioco la sola gamba della compagna. Se quel broker non è visibile, il componente {A, B} parte da un A senza
  storia: `FIFO_SOURCE_QUANTITY_MISSING` → `FAILED`, YoC «non disponibile» per la posizione in B. Il lato del
  mittente funziona; il filtro dei broker del proprietario non c'entra (lo YoC carica tutti i broker visibili).
  La cura naturale è la lettura al confine di J-10 (`financial_math/lots/scope_boundary.py`), applicata ai broker
  visibili al posto della gamba aggiunta. Prima un rosso. Dettagli:
  [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «J-10».
  - ✅ 17/10: fatta da J (checkpoint J-51). Lo YoC legge al confine dei broker visibili le sole gambe in arrivo
    (`read_arrivals_at_scope_boundary`); una partenza tiene la compagna (le unità in viaggio contano per l'origine). Il
    costo resta il WAC della posizione della Dashboard: con la base della gamba un valore, senza `MISSING_WAC`.
    Dettagli: piano 05, sezione «J-51».
    Commit `45c4c098e` → dev `1becf502f`.
- ✅ **J-53 · Il banner dei lotti mostra un solo fondo orfano per codice** — medio, numeri e chiarezza; J, 17/10 (analisi
  di J-36). **Titolare: Y** (frontend, decisione del coordinatore 17/10), dopo i lotti A/B di X-R59, nella 1.3.
  `lotDataQualityHelpers.buildIssueGroups` raggruppa le issue per codice e mostra il messaggio coi parametri della
  prima; `ASSET_INCOME_NO_ELIGIBLE_LOTS` e `ASSET_COST_NO_ELIGIBLE_LOTS` arrivano una per fondo orfano («…of
  {target_amount} {target_currency} on {as_of_date} — income left unallocated»), senza lotto, quindi senza chip: con più
  fondi il banner mostra l'importo e la data di uno solo e nasconde gli altri. La cura: una riga per issue per i codici
  senza lotto (non un totale del backend, che sommerebbe valute diverse e perderebbe le date). Dettagli:
  [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «J-36».
  ✅ **Fatto da Y il 17/10** (`c37c2bb1e`, dev `fb6d58d17`): un blocco per codice, una riga per ogni issue senza lotto con i suoi parametri; si vedono anche le due `MISSING_FX_RATES` (provider e manuali).
- ✅ **J-52 · Due convenzioni d'eco per la finestra del rigioco fuori dai limiti** — minimo, chiarezza; nota cosmetica di E
  alla revisione di SEC8-1b (17/10), facoltativa. Per una richiesta fuori dai limiti la finestra preparata
  (`requested_range`, che fa da ripiego di `metadata.analyzed_range`) è quella limitata, mentre `output.replay_range` e
  `metadata.params` ripetono la richiesta. Visibile solo fuori dai limiti. Da scegliere una convenzione sola, o da dire
  nella pagina. Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione
  «SEC8-1b».
  - ✅ 17/10: fatta da J (checkpoint J-52). `metadata.params` ripete la richiesta; l'output (`replay_range`) e
    `metadata.analyzed_range` dicono la finestra rigiocata, quella limitata. Lo stress passa a `algorithm_version` 3.0.1,
    un salto solo per SEC8-1b e J-52. Dettagli: piano 05, sezione «J-52».
    Commit `2684dc6c1` → dev `df1194de4`.
- ✅ **J-54 · Nell'AI Export `null` vuol dire anche «nessuno», e T-B7 lo nomina come «non disponibile»** — minimo,
  chiarezza; J, 17/10 (rossi di T-B7, letto nel codice).
  - Il backend scrive ogni `None` come `null` (`model_dump(mode="json")`, senza `exclude_none`), anche dove vuol dire
    «nessuno» invece che «ignoto»:
    - il `closing_date` di un lotto aperto;
    - il `reason_code` di una riga senza problemi;
    - il `component` di un'uscita scalare;
    - `minimum`/`maximum` di un'uscita senza limiti (`IndicatorOutputColumn`).
  - Il preambolo dice `null=explicitly unavailable`. Era già così in una tabella mista; da T-B7 una colonna così, nulla
    in ogni riga, si nomina anche su `omitted_null_columns=`. Per esempio ogni OUTPUT DEFINITIONS di un segnale senza
    limiti nomina `component,minimum,maximum`.
  - Cure possibili (da decidere):
    - (a) il preambolo allarga `null` a «non disponibile, o nessuno per quella riga»;
    - (b) il renderer tratta come «non si applica» i metadati delle definizioni;
    - (c) il backend omette quei campi, con un salto di versione dei componenti.
  - Da guardare nella sonda mirata di T-B7. Dettagli:
    [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «T-B7».
  - **Deciso dal coordinatore (17/10, ~16:15): opzione (b), prima del rilascio.** Una costante sola,
    `NULL_MEANS_NONE_COLUMNS`, con 11 voci (erano 8; poi i rossi hanno corretto l'insieme):
    - ovunque: `closing_date`, `reason_code`, `conversion_reason`;
    - solo in OUTPUT DEFINITIONS: `component`, `minimum`, `maximum`;
    - in ogni tabella del calendario dei redditi: `asset_ref`;
    - nel PERIOD SUMMARY di `asset.indicators` e `fx.indicators`: `portfolio_weight_percent` e
      `technical_normalized_weight_percent`.

    `partial_reason_code` è uscito: in ENTITY STATUS un null vuol dire «motivo ignoto». Nulla in ogni riga, una colonna
    dell'insieme si toglie in silenzio. Le celle delle tabelle miste restano `null` (J-55). Dettagli: piano 05, sezione
    «J-54».
  - ✅ 17/10: fatta da J (checkpoint J-54): `96889bbfc`, entrata con `f9aef5d99`; riga 🔄 di T-B7 estesa
    (`a3d4d60a7`). Dettagli: piano 05, sezione «J-54».
- **J-55 · Le celle «nessuno» delle tabelle miste dell'AI Export si stampano `null` («explicitly unavailable»)** —
  minimo, chiarezza; J, 17/10 (J-54). **Dopo la 1.3** (coordinatore, 17/10).
  - Esempio: in una tabella di lotti con lotti aperti e chiusi, la cella `closing_date` di un lotto aperto dice
    `null`, che il preambolo definisce «explicitly unavailable». È così dalla 1.1; J-54 toglie solo il nome di una
    colonna nulla in ogni riga.
  - Per stampare quelle celle vuote serve, nel preambolo, una definizione della cella vuota («non si applica a quella
    riga»). Quella definizione coprirebbe anche le altre celle vuote, e non tutte vogliono dire «nessuno»: per esempio
    un `bucket_count` `undefined` delle INSTANCES.
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «J-54».
- **J-56 · Settimanale e mensile: una linea divisa in più serie fa un gradino nel secchio del taglio** — minimo,
  chiarezza; J, 17/10 (J-21). Proposta: dopo la 1.3; file dei grafici, Y (FE2).
  - `downsampleRenderedSignal` (`components/charts/timeSeriesAggregation.ts`) raggruppa ogni `RenderedSignal` nei
    secchi per conto suo. Due serie della stessa uscita con punti nello stesso secchio hanno ciascuna un
    rappresentante a quella data. La linea fa un gradino verticale; il tooltip, che salta i nomi già visti
    (`PriceChartFull.svelte`), mostra il valore della prima serie e non quello del secchio intero.
  - Vale da prima per le fette di stile, a ogni attraversamento di soglia di RSI, CCI, MFI e StochRSI. Da J-21 vale
    anche per i tratti di una linea con un punto senza valore: un buco dentro un secchio non si vede, e al suo posto
    c'è il gradino. A risoluzione giornaliera nulla cambia.
  - Cura possibile: aggregare l'uscita intera una volta sola, e dividerla in fette e tratti dopo l'aggregazione.
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «J-21».
- **J-59 · Una serie sola per uscita, con i vuoti dichiarati e i giorni assenti uniti** — basso, prestazioni e
  chiarezza; J, 17/10 (nota di Y su J-21). **Dopo la 1.3**, file dei grafici, Y (FE2).
  - Da J-21 una linea si divide in tratti ai punti senza valore, e ogni tratto è una serie ECharts lunga quanto
    l'asse. Misurato sulle metriche mobili vere: con la finestra di default (90) c'è un tratto solo; con una finestra
    piccola su un asset giornaliero poco scambiato (30–60 % di chiusure invariate) i tratti sono da 46 a 371.
    Nessun tratto di un punto solo con una finestra di 3 o più. Per ora un tetto nel renderer (J-21 bis): oltre il
    tetto l'uscita torna una linea unita, con un avviso.
  - La cura vera: una serie per uscita, con dati a coppie (`[date, value]`, `[gapDate, null]`, `connectNulls:
    false`). I giorni assenti non hanno elemento e restano uniti; un array allineato all'asse non lo permette, e
    anche `'-'` vale null. I tratti del renderer restano, e i due costruttori dei grafici li fondono.
  - File: `charts/signals/backendRenderer.ts` (una chiave di gruppo e la data del vuoto), `ChartSignal.ts` (il
    tipo), `components/charts/chartCoreHelpers.ts` (`buildOverlaySignalSeries`), `LineChart.svelte` (la sua copia
    del costruttore, `:505`) e i tooltip di `PriceChartFull.svelte:983-984` e `LineChart.svelte:810-811`, che
    leggono `p.value` come numero o `{value}` e con le coppie stamperebbero l'array.
  - Rossi: molti vuoti danno una serie sola; fine settimana uniti; vuoti spezzati; indicatori agli estremi;
    valori del tooltip giusti. Stima ~3 h. Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md),
    sezione «J-21».
- ✅ **J-57 · Una rettifica in Auto senza nulla da mediare si salva a costo 0** — medio, numeri (utenti non esperti);
  J, 17/10 (analisi di J-41), letta nel codice. Area di W; da decidere insieme a J-11/J-35 (costo zero o ignoto).
  - Un pool vuoto dà un costo medio di **0** nella valuta dell'asset, non None (`compute_wac_iterative`,
    `portfolio_service.py:199-204`; documentato in `wac.md`, «with no rows left it returns a zero WAC»). Il risultato
    è un `Currency` e quindi vero: `_write_auto_cost` (`transactions/auto_cost.py`) lo scrive. Il controllo del costo
    salta le righe Auto (`batch_costs.py`).
  - Il modulo parte in Auto (`TransactionFormModal.svelte:307`) e non avvisa di un suggerimento a 0. Una rettifica
    in entrata su un broker che non ha mai avuto l'asset, salvata senza toccare il costo, è quindi un acquisto
    gratuito (`ADD_ZERO_COST`): Dashboard e lotti mostrano tutto il valore come guadagno. Salvata senza costo, la
    stessa riga avrebbe costo ignoto (`ADD_UNKNOWN_COST`).
  - Un TRANSFER ricevuto da un pool vuoto dà 0 anch'esso (`test_wacp27_empty_pool_wac_zero` lo fissa nella
    validazione), ma il controllo dei saldi lo rifiuta al salvataggio: il mittente andrebbe sotto zero.
  - Cure possibili: (a) rifiutare con un messaggio tradotto («niente da mediare: inserisci il costo»); (b) costo
    ignoto, come una rettifica senza costo, e il risultato lo dice; (c) tenere lo 0 e avvisare nell'anteprima. Prima
    un rosso. Dettagli: piano 05, §10 «J-41».
  - Decisione del coordinatore, notturna **N88** (17/10, da rivedere dal developer): (a), rifiutare. Due codici,
    `autoCostEmptyPool` (nessuna unità nel pool alla data: mai avute o vendute tutte) e `autoCostUnknownPool` (unità
    tenute, nessuna a costo noto). Un pool di unità gratuite tiene il suo 0; uno 0 scritto a mano resta accettato.
    Solo le righe Auto del lotto: passaggi di decisione 47, `delete_by_broker`, `POST /portfolio/wac` e PAC invariati.
    Il costo in parte ignoto è **J-58**.
  - ✅ 17/10: fatta da J (W rivede).
    - Il motore ne dà lo stato tramite una facciata sorella, `wac_pool_holding()` in `portfolio_service.py`, senza
      cache e chiamata solo quando la media è 0.
    - La cache di `compute_wac_iterative` resta com'era.
    - 11 rossi più P27 (`test_wacp27_empty_pool_is_refused`).
    - Verdi: `transaction-cost-basis-rule` 189, `api transactions-wac` 20, `roi-fifo-utils` 1 439, e i 6 E2E del costo
      Auto.
    - Dettagli: piano 05, §10 «J-57».
    - Commit `b7e2bb3bd` → dev `539371064`; CHANGELOG `c80031659`.
  - **19/10, il developer**: J-57 resta e si completa. Lo 0 scritto a mano resta permesso, per il regalo, sia nel
    form sia nell'import col wizard, e il messaggio suggerisce «Manuale e 0». Analisi in sola lettura: piano 05,
    §10 «Ripartenza del 19/10». Le domande al developer passano dal coordinatore.
- **J-58 · Il costo Auto di un pool in parte a costo ignoto è sottostimato, in silenzio** — medio, numeri; J, 17/10
  (analisi di J-57). **Da decidere (developer)**; proposta: rifiutare, come N88.
  - Un'acquisizione senza costo entra nel motore come `ADD_UNKNOWN_COST`: la quantità sale, il costo no, e il pool
    resta «incompleto» (`report_complete=False`) finché non si svuota. `compute_wac_iterative` non guarda la
    completezza: la media è il costo noto diviso per tutte le unità. BUY 10 per 1 000 € più 10 ricevute senza costo:
    una rettifica Auto si salva a 50 € invece di «ignoto».
  - N88 rifiuta solo lo 0 (nessuna unità, o nessuna a costo noto). Il caso in parte noto cambia un flusso che oggi
    funziona per chi importa (righe senza costo da broker esterni), quindi la scelta è del developer.
  - Cura proposta: lo stesso rifiuto quando il pool è incompleto, con un codice proprio. In alternativa, un avviso
    nell'anteprima. Un controllo che fissa il valore di oggi c'è già (J-57, C4).
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), sezione «J-57».
- ✅ **J-60 · Un costo di carico scritto a mano può essere negativo** — basso, numeri e dati; J, 19/10 (analisi di J-57
  completa, letto nel codice). **Deciso: (a)**, rifiutarlo e tenere lo 0 (coordinatore, 19/10). I testi li ha
  approvati il developer con J-57. N92 (i) ha poi deciso che un prezzo negativo non si accetta.
  - Il backend non guarda il segno: `Currency.amount` può essere negativo (`schemas/common.py:188`) e
    `IsoCurrencyAmount` controlla solo il codice (`:498-504`). Il batch controlla solo le cifre
    (`transaction_batch_stages.py:96-102`). Nel form la cella del costo diventa rossa sotto lo 0
    (`signHint="positive"`), ma non blocca.
  - Quindi una rettifica in entrata, o la gamba che riceve un trasferimento, si salva con un costo per unità
    negativo, e il WAC e i lotti lo usano.
  - La sfumatura: per N92 un prezzo negativo esiste (alcuni strumenti), quindi rifiutarlo sempre è una scelta.
  - Opzioni: (a) rifiutare un costo < 0 con un codice tradotto; (b) accettarlo con un avviso; (c) com'è oggi.
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), §10 «Ripartenza del
    19/10».
  - **Chiusa il 20/10 da J** (checkpoint J-60). Lo stadio `check_cost_basis_sign` del batch
    (`transaction_batch_stages.py`) legge il costo dove lo legge il controllo delle cifre: il costo manuale di una
    creazione, o di un aggiornamento che lo manda (l'Auto è escluso), e quello che una promozione risolve. Sotto lo 0:
    `costBasisNegative` su `cost_basis_override`, e il batch non si salva.
  - **Residui** (coordinatore, 20/10 14:28):
    - le righe già salvate con un costo negativo, e la media Auto negativa che ne può nascere: **J-70**;
    - note senza voce:
      - preesistente, per ogni codice: `promote_transfer` appiattisce le issue in `errors: [str]`, quindi lì il
        rifiuto arriva come testo inglese;
      - un'issue che non è di saldo salta il calcolo Auto di tutto il batch.
- **J-61 · Tre seguiti della revisione di Y a J-21 bis** — minimo, chiarezza e documentazione; Y, 19/10 (revisione a
  posteriori di `def1d5259`: OK). Niente codice adesso (coordinatore, 19/10). Dettagli: piano 09 di Y, «19/10 ·
  Revisione a posteriori di J-21 bis».
  - **L'avviso non arriva all'utente.** `outcome.warnings` di `renderBackendSignalResult` (`backendRenderer.ts:370`)
    non lo legge nessuna pagina: le pagine leggono gli avvisi del backend (`item.result.warnings`). Di «gaps
    joined» resta solo il nome nella legenda e nel tooltip. Y consiglia (i): togliere l'avviso, con la chiave
    `signals.gapsJoined.warning` nei 4 cataloghi, e correggere il commento e J-59; nulla di visibile cambia.
    Mostrarlo nel pannello cambierebbe l'interfaccia: è una domanda per il developer.
  - **La guida dei plugin dei segnali** (`signal_plugin_guide.md:255-260`) dice ancora che il renderer spezza
    sempre una linea o un'area dove manca il valore: manca la frase sul tetto dei 30 tratti.
  - **CHANGELOG, riga 308**: «more than 30 gaps» → «30 gaps or more». La linea si unisce oltre 30 tratti
    (`runs.length > MAX_LINE_RUNS`), cioè da 30 vuoti in su.
- **J-62 · R11: i gemelli pandas di volatilità e Sharpe mobili, senza parità e con due copie del validatore** — basso,
  numeri (regola 10); J, 19/10 (revisione della voce 1 di J-1 di MF, `068d5dd51`). Coordinatore, 19/10: in R11, nella
  sezione J.
  - `signals/risk_adapters.py` calcola volatilità e Sharpe mobili con pandas, gemelli di `risk/metrics.py`
    (`annualized_volatility`, `annualized_sharpe`). Nessun test fissa la loro parità: è R11 del piano 43 (resto di
    CP-10, a J).
  - Le stesse due funzioni ripetono la regola del fattore d'annualizzazione (`:191-193`, `:222-224`: finito e
    positivo, altrimenti `ValueError`). Dopo `068d5dd51` quella regola ha una casa sola,
    `financial_math.returns.positive_annualization_factor`, e le due copie la devono leggere.
  - Da fare: il test di parità (test-author), poi le due copie sostituite dalla funzione della casa. Nessun valore
    cambia. Dopo J-48.
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), §10 «Revisione della
    voce 1 di J-1 di MF».
- **J-63 · L1 delle «formule veloci» di MF: i lotti calcolati sui giorni di cambiamento** — medio, prestazioni (numeri
  identici); coordinatore, 19/10 (il piano «formule veloci» di MF entra nella 1.3).
  - ✅ **L1a** 19/10 (checkpoint L1a; commit del coordinatore). I sette costruttori giornalieri dei lotti girano solo
    sui giorni in cui un ingresso cambia, e `expand_to_days` riempie la finestra
    (`financial_math/lots/change_days.py`). Uscita identica al byte: 0 differenze su quattro copie di DB, dati veri
    compresi. Col 1900 il tempo si dimezza.
  - **L1b**, dopo P3 di MF: i giorni del mercato presi dai gradini di P3 invece che dalla scansione di ogni giorno.
    Restano giornalieri la conversione del segno, i cambi chiesti giorno per giorno e la scansione stessa: è il resto
    del tempo col 1900. Da coordinare con Y per i grafici.
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), §10 «L1a — i lotti
    calcolati solo nei giorni in cui cambia qualcosa».
- **J-64 · Il CSV generico chiede il costo dove c'è già o dove non si può dare** — basso, dati e chiarezza; docs-writer
  di J, 19/10 (durante J-57 completo). Il plugin `broker_generic_csv` mette il todo bloccante `corporate_action` su ogni
  `ADJUSTMENT` senza costo (`plugin.py:455-470`, `has_cbo`), con due difetti:
  - un costo **0 scritto nel file** conta come mancante (`float(...) == 0`). Un regalo registrato a 0 arriva col todo,
    e l'utente deve riscrivere 0: va contro «lo 0 è un costo vero» (decisione Q-J57-3);
  - il controllo non guarda il segno. Una rettifica in uscita non prende un costo (`required_qty_pos`), quindi il suo
    todo non si chiude mai e **Save All** resta bloccato. Questo l'ha visto il docs-writer leggendo il codice: è da
    provare.
  - Esisteva già prima di J-57; tocca il plugin, non il mio perimetro. Da assegnare: il proprietario dei plugin BRIM.
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), §10 «J-57 completo —
    esecuzione», passo 3.
- ✅ **J-65 · Due definizioni di «coperto» per i prezzi dell'AI Export** — basso, numeri (chiarezza del prompt); E, 19/10
  (analisi di E-AI503, «per J»), confermata da J nella revisione del 20/10.
  - **Chiusa il 20/10 come doppione di E-23** (coordinatore): stesso caso, l'asset con prezzi solo prima del periodo.
    Il developer l'ha deciso in E-23, assegnato a E.
  - Una serie stantia (prezzi salvati solo prima del periodo), o fatta solo di righe senza `close`, resta in `assets`
    di `portfolio/broker.technical_prices` con la sua valuta e tutti i secchi vuoti, ed è contata in
    `covered_asset_count`. `technical_coverage`, nello stesso dataset, la dà invece con 0 osservazioni.
  - Preesistente: E-AI503 non la tocca. Da decidere se chiamarla «non coperta» (un terzo `reason_code`, per esempio
    «nessun prezzo nel periodo») o dichiararla nel testo.
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), §10 «Ripresa del 20/10
    e revisione di E-AI503», nota 2.
- ✅ **J-66 · Il banner di promozione del bulk mostra coppia FX e tasso implicito al contrario** — medio, numeri (un tasso
  mostrato invertito); J, 20/10 (slot di J-57, `front-transaction all`).
  - Il bulk tiene come valore assoluto il contante dei tipi con regola `cashSign: 'negative'`, per esempio il prelievo:
    le righe salvate (`fieldsFromTx`) e quelle importate (`txCreateItemToPendingOp`) da prima, quelle del form da
    W-B65 (`2b3c9e8d7`, 17/10). Il banner, il tasso implicito, la richiesta del cambio di mercato e il «left» di
    «Merge all» sceglievano il lato «da» dal segno del valore.
  - Con un prelievo di 1000 EUR e un deposito di 1100 USD, a seconda dell'ordine il banner scriveva
    «USD → EUR @ 0.9091» invece di «EUR → USD @ 1.1000», oppure metteva il deposito per primo.
  - Si vede in `tx-fx-implied-rate.spec.ts`, Scenario A e A2: rossi e deterministici sulla base `2534c71fd`, anche in
    una corsa da sola. J-57 non c'entra.
  - **Chiusa il 20/10 da J** (via del coordinatore, checkpoint J-66). Un aiutante solo, `promotePairOrder`
    (`promoteHelpers.ts`), legge il lato dal contante col segno del tipo, come `cashAmountsCancel`. Lo leggono tutti e
    cinque i punti: i quattro di prima più il dialogo del «Merge» singolo (Q-J66-1 (a), decisione del coordinatore).
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), §10 «J-57 v3 e slot
    pesante, parte 2» e «J-66 — il banner di promozione legge il segno dal tipo».
- ✅ **J-67 · Dopo un merge di righe salvate, la griglia può mostrare la coppia al contrario fino al salvataggio** — basso,
  chiarezza (nessun dato salvato sbagliato); J, 20/10 (docs-writer durante J-66, verificato da J).
  - `collapseIntoPaired` (`TransactionBulkModal.svelte` ~`:739-754`) sceglie la riga visibile, il «From:» della
    griglia, da `Number(cash)`, dopo che `executePromote` ha già cambiato il tipo. Per due righe salvate, o una salvata
    e una nuova, il prelievo è ancora un valore assoluto: se il deposito è `opA`, resta visibile lui e la coppia si
    legge al contrario fino al salvataggio. Le due righe nuove hanno già il segno, e lì è corretto.
  - Preesistente; J-66 non lo peggiora.
  - Rimedio proposto: `promotePairOrder` sui tipi di partenza, prima del cambio di tipo, e `from`/`to` passati a
    `collapseIntoPaired`. Un rosso E2E: due righe salvate col deposito come `opA`, la riga visibile dev'essere il
    prelievo. Peso: 1–2 ore.
  - Da assegnare: il proprietario del promote (W), oppure J.
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), §10 «J-66 — il banner
    di promozione legge il segno dal tipo», passo 5.
  - **20/10, coordinatore**: assegnata a J, dopo il §29 punto 2. Riporta la griglia al dato salvato: non serve una
    domanda.
  - **Chiusa il 20/10 da J** (checkpoint J-67). Le facce erano tre, con una causa sola: i rami dei salvati e dei misti di
    `executePromote` cambiavano il tipo senza spostare il segno nell'importo.
    - La riga visibile era sbagliata, e il contante si leggeva «+X / +X».
    - Uno split prima del salvataggio scambiava i tipi delle due righe e lasciava la promozione in coda: il
      salvataggio veniva rifiutato (`promoteRefNotFound`). L'E2E l'ha provato: rifiutato, nulla scritto.
    - Con la riga salvata in vista, lo split non faceva nulla.
  - Cura: il segno passa nell'importo in tutti i rami. «Split pair» su un merge non salvato lo annulla
    (`undoPendingPromote`). Spec nuovo `tx-bulk-promote-split` (F1–F3, guardia G).
- **J-68 · Un trasferimento in un giorno solo non nomina l'origine nelle viste dei lotti** — basso, chiarezza; J, 20/10
  (test-author durante il §29 punto 2, verificato da J nel codice).
  - Per un trasferimento che parte e arriva lo stesso giorno, `_build_transfer_rows` (`lots_analysis_service.py`)
    scrive solo TRANSFER_ARRIVE, dal frammento di destinazione, con `broker_id` B ma senza `source_broker_id` né
    `destination_broker_id`; non c'è TRANSFER_DEPART. Un trasferimento di più giorni ha invece le due righe, con
    origine e destinazione.
  - Effetto: lo Storico della modale scrive «In transit → B» senza dire da dove; il tooltip del grafico WAC scrive «—»
    sia in «Da» sia in «A». Nessun numero.
  - Da guardare insieme al §29 punto 1 (il tooltip dei marcatori vuole «Da A / A B»): l'origine sta nel frammento di
    partenza, oppure nel motore, che può scriverla sul frammento di destinazione.
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), §10 «Gantt §29, punto
    2», passo 1.
- **J-70 · Costi di carico negativi già salvati, e la media Auto che ne nasce** — basso, numeri e dati; J, 20/10
  (residui di J-60, raccolti in una voce dal coordinatore).
  - J-60 rifiuta un costo negativo nuovo o mandato di nuovo. Le righe salvate prima con un costo manuale negativo
    restano, e il WAC e i lotti le usano. Quante sono si conta su una copia dei dati reali (skill `real-data-copy`),
    quando servirà.
  - Una riga Auto su un insieme che contiene quelle righe può ancora prendere una media negativa: N88 reagisce solo
    allo 0 esatto. Un costo salvato a −300 per unità porta la media a −100. La guardia
    `test_an_auto_row_over_a_pool_averaging_below_zero_gets_no_cost_basis_negative` fissa soltanto che quella riga
    non riceve `costBasisNegative`, non il valore.
  - Rimedi possibili, da decidere dopo il conteggio:
    - (a) far correggere le righe all'utente: un avviso di qualità dei dati che le elenca;
    - (b) rifiutare una media Auto sotto lo 0 con un codice proprio, come N88 fa per l'insieme vuoto;
    - (c) nessuno, se il conteggio è zero.
  - Dettagli: [piano 05](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), §10 «J-60 — un costo di
    carico negativo si rifiuta nel batch», passo 1.

## Z · Sospensione e risveglio (fase 01)

Piano: [`06_sleepWake`](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md).

- ✅ **C-49 (sezione C) · presa in carico da Z** — prove senza codice in Z6a (autorizzate il 15/10), cura in Z6b con il
  punto 35 delle decisioni. Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione
  «Z6a — prove su C-49, senza codice di prodotto».
  - 15/10, Z: 9 cicli di vita puliti su spec singole; il coordinatore cerca l'avviso nelle sue run di categoria. Dalla
    lettura di uvicorn 0.52.4, con SIGTERM l'ipotesi dei thread è esclusa; restano le richieste in volo (la più
    probabile), i passi del lifespan e i processi figli. Disegno della cura: piano 06, sezione «Z6b — disegno».
  - ✅ 15/10, Z: **chiusa da Z6b** (commit `f0b9bcad2` e `fb3f98a0c`, entrati in `967094d81`): un tempo massimo di
    spegnimento per tutti, `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` (8 s), con l'attesa delle richieste in volo a 3/8 e un
    watchdog che chiude il processo allo scadere. Prove: piano 06, sezione «Z6b — codice». Le run di categoria del
    coordinatore all'ingresso fanno da conferma; la riga di C-49 nella sezione C la riconcilia lui.
- ✅ **Z-1 · Il ciclo del grafico del dettaglio asset gira anche su un intervallo passato** — chiusa da Z1 il 15/10
  (commit `74d028ec6`): il ciclo unico del dettaglio ha la guardia `isHeadToday`; il test E2E `front-asset live-pause`
  (f) prova che un intervallo passato non chiede nulla (rosso prima: richieste a +2,1 e +57,1 s). Era: basso, da
  verificare; Z, 14/10. Il poll di 60 s (`routes/(app)/assets/[id]/+page.svelte:1977-2083`) non aveva la guardia
  `isHeadToday`, e `mergeChartPointsIncremental` non taglia sull'intervallo. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Passi di Z1».
- ✅ **Z-2 · Due cicli sullo stesso endpoint nel dettaglio asset** — chiusa da Z1 il 15/10 (commit `74d028ec6`), per la
  decisione 31: un ciclo solo ogni 30 s, una richiesta per giro che alimenta il riepilogo e la testa del grafico; la
  fusione è coordinata con X (FE5c) dal coordinatore. Era: basso; Z, 14/10, tre scritture di `POST
  /assets/prices/current` al minuto. Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md),
  sezione «Passi di Z1».
- ✅ **Z-3 · `isHeadToday` confronta con la data UTC** — basso; Z, 14/10. **Chiusa il 16/10 col lotto A** (il commit è
  del coordinatore): le due pagine degli asset confrontano `dateEnd` con `todayIso()`, il giorno del calendario
  dell'utente, come `dateEnd` stesso. Lo fissano (i)–(l) di `asset-live-pause.spec.ts`: rossi senza la correzione,
  verdi con. Era: con la data UTC, la sera a ovest di Greenwich un periodo che finisce oggi sembrava passato (niente
  prezzo dal vivo), e subito dopo mezzanotte a est un periodo finito ieri sembrava vivo e interrogava il fornitore.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Lotto A».
  - Prova (19/10): `a43502298` (lotto A), entrato in `0f55265a1`; CHANGELOG `ac9671fd3`.
- **Z-4 · Risvegli orari per singolo titolo** — medio; Z, 14/10, dalla decisione D-19 del business plan. Serve un campo
  per asset; nella 1.3 c'è solo l'intraday globale, spento di default (D8). Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «4. Decisioni».
- ✅ **Z-5 · Recupero dall'ultima data salvata invece dei 14 giorni fissi** — basso; Z, 14/10 (F07, priorità bassa).
  **Chiusa il 16/10 col lotto Z-5** (il commit è del coordinatore): la sync storica copre almeno l'orizzonte e, per un
  asset o una coppia il cui ultimo dato salvato è più vecchio, riparte dal giorno dopo, al massimo un anno indietro
  (`_history_sync_start` in `scheduler/jobs.py`); senza dati salvati resta l'orizzonte. Era: la finestra era sempre e
  solo l'orizzonte («Lookback horizon», 14 giorni di default), e chi restava indietro di più teneva il buco. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-5».
  - Prova (19/10): `b36542f81`, entrato in `ebe9eb346`; CHANGELOG `7344dda47`.
- ✅ **Z-6 · Il docstring dello scheduler dice che l'elezione del leader gira in un thread** — chiusa da Z3 il 15/10:
  `run_due_jobs` chiama `am_i_leader()`, `load_state` e `save_state` con `asyncio.to_thread`, e la docstring nuova lo
  dice. Era: `services/platform/scheduler/scheduler.py:108` chiamava `am_i_leader()` (psutil) sul loop. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z3 — scheduler».
  - Prova (19/10): `a4da204b4` (con Z3).
- **Z-7 · Calendario dei risvegli: prossima esecuzione per job, `next_wake_at` e jitter** — medio; developer, 15/10
  (decisione 33: «il next_wakeup per ora non serve [...] è una cosa per il futuro quando servirà»). Quando il pannello
  del cloud terrà un calendario: la prossima esecuzione di ogni job (con l'ora legale), `next_wake_at` nella risposta di
  `wake-sync` e in un GET con lo stesso token, il jitter per istanza. La risposta di `wake-sync` nasce estendibile per
  questo. Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «4. Decisioni».
- ✅ **Z-8 · Il dettaglio di un asset senza fornitore chiede il prezzo dal vivo ogni 30 s** — basso; Z, 15/10 (Z1).
  **Chiusa il 16/10 col lotto A** (il commit è del coordinatore; X ha dato a Z il file): l'effetto di
  `assetDetailLive.svelte.ts` avvia il poller solo con un codice di fornitore, letto da un `$derived` booleano, così
  una ricarica dell'assegnazione con lo stesso codice (o con un altro) non lo riavvia; la testa del grafico non
  controlla più il fornitore. Era: un asset manuale chiedeva `POST /assets/prices/current` ogni 30 s, e ogni risposta
  (solo il prezzo salvato) contava come scrittura del portafoglio.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Lotto A».
  - Prova (19/10): `a43502298` (lotto A), entrato in `0f55265a1`; CHANGELOG `ac9671fd3`.
- ✅ **Z-9 · Doc delle pause dei fornitori** — basso; Z, 15/10 (Z7a). **Chiusa il 16/10 col lotto Z-9** (sola doc,
  dopo Z7c-1): la sezione `#provider-pauses` di `admin/sleep_wake.en.md` (durata, chi aspetta e cosa si vede, memoria
  e sospensione, log) e le due righe in `admin/configuration.en.md`; la parte di sviluppo l'aveva già scritta X
  (`developer/backend/assets/architecture.md#provider-pauses`), che ora rimanda alla pagina admin. Era: due pagine,
  - la pagina admin `admin/configuration.en.md`, con le due variabili, il default acceso e l'eccezione della decisione
    34;
  - la pagina d'architettura degli asset: il confine e le pause.

  Le variabili esistono da Z7a ma non hanno effetto finché X non aggancia il confine (X1–X4): la doc va scritta con
  l'aggancio. Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-9».
  - Prova (19/10): `467fbac05`, entrato in `dd4a97e01` (treno 105).
- ✅ **Z-10 · Ctrl+C su `./dev.py server` uccide il server dopo 0,25 s** — basso; docs-writer di Z, 15/10 (Z6b).
  **Chiusa il 17/10 col lotto Z-10** (il commit è del coordinatore; via da scrittore su `cli_base.py`, `dev.py:448` e
  tre test di H e L). `dev.py server` lancia il server con `run_server_live` (`scripts/cli_base.py`):
  - al Ctrl+C non inoltra nulla (il server ha già il SIGINT del terminale) e aspetta il suo spegnimento fino al
    budget più 2 s;
  - un SIGTERM a `dev.py` lo inoltra al server, con la stessa attesa;
  - un secondo segnale, o la grazia finita, lo uccide; codici 130 e 143.
  I gestori registrano i segnali senza sollevare eccezioni, e `run_command_live` resta com'è per gli altri comandi.
  Era: con `subprocess.run` il server moriva di SIGKILL 0,25 s dopo il Ctrl+C, a metà del suo spegnimento (provato
  il 17/10 con un finto server: uscita a 0,29 s, server ucciso), e un SIGTERM a `dev.py` lasciava il server orfano.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-10».
  - Prova (19/10): `1bd8dc332`, entrato in `a38d6bdfe`; CHANGELOG `75a1107a7`.
- ✅ **Z-11 · Lock dei job tra processi (flock) per più worker** — basso; coordinatore, 15/10 (D-Z3-3). **Chiusa il
  17/10 col lotto Z-11** (il commit è del coordinatore; decisione notturna N71, da rivedere col developer).
  - Dove c'è `fcntl`, ogni giro prende `<data_dir>/.scheduler.lock` (`scheduler/run_lock.py`) prima di leggere lo
    stato, e qualunque worker esegue i job, uno alla volta. Chi aspetta rilegge lo stato e trova i job `not_due`.
  - `wake-sync` funziona su ogni worker, e il ritorno parte subito nel worker che l'ha visto.
  - Senza `fcntl` (Windows) resta il leader, con `not_leader`.
  Era: con `--workers` i job giravano solo nel worker leader; un altro worker che riceveva `wake-sync` rispondeva
  `not_leader`, e la spinta del ritorno aspettava il giro del leader, entro 60 s. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-11 — lock dei job tra processi:
  analisi».
  - Prova (19/10): `2db7edd68`, entrato in `c5e3c199d`; CHANGELOG `47405701f`.
- ✅ **Z-12 · `admin/filesystem`: il commento di `scheduler_state.json`** — minimo, doc; docs-writer di Z, 16/10
  (Z7c-2). **Chiusa il 16/10 col lotto Z-12** (il commit è del coordinatore): nelle quattro lingue, a mano e senza
  stamp, il commento dice l'ultima esecuzione e il nuovo tentativo previsto («Scheduled syncs: last run, pending
  retry»); in `filesystem.es.md` ora è in spagnolo. Era: diceva solo «Last run of the scheduled syncs», mentre da Z7b il
  file tiene anche i rimandati, il nuovo tentativo e l'attesa dopo i fallimenti. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezioni «Z7c-2», passo 4, e «Z-12».
  - Prova (19/10): `f561aec07`, entrato in `ebe9eb346`.
- ✅ **Z-13 · Dopo un recupero dei prezzi la pagina aperta non si ricarica da sola** — basso; docs-writer di Z, 16/10
  (Z5). **Chiusa il 16/10 col lotto Z-13** (commit `9d19c2093`; Z-13b, per il vincolo di Y11, nel checkpoint
  successivo): a fine recupero il frontend manda `{kind: 'prices'}` sul bus del portafoglio, e il Dashboard e la pagina
  di un broker sullo schermo chiedono di nuovo il loro report in background, senza force e senza passare
  dall'«Aggiorna» dell'utente. I pannelli di rischio e dei lotti restano a Z-15. Era: a fine recupero il frontend
  chiamava `requestPortfolioRefresh()`, che segna come stale le cache del portafoglio (`portfolioStore.invalidate()`
  alza solo un contatore non reattivo): la pagina già sullo schermo mostrava le cifre nuove al prossimo caricamento o
  con «Aggiorna». Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezioni «Z5 —
  codice» e «Z-13».
  - Prova (19/10): entrato in `12cd3c2e0` con Z5; Z-13b `f83ab0c5b`, entrato in `26dda1a26`.
- ✅ **Z-14 · Le pagine di un asset e di un cambio non vedono un recupero dei prezzi** — basso; docs-writer di Z, 16/10
  (Z-13). **Chiusa il 17/10 col lotto Z-14** (il commit è del coordinatore): `TimeSeriesStore.markStale()` tiene i
  punti e fa chiedere di nuovo la lettura successiva, anche dove ci sono dati (le risposte riempiono all'indietro i
  giorni); i due registri ascoltano il bus e segnano stale tutti i negozi solo su `{kind: 'prices'}`; `lookupFxRate`
  tratta un giorno stale come mancante. Dopo un recupero la visita successiva di una pagina dei prezzi o dei cambi, o
  un cambio d'intervallo, chiede di nuovo, una volta. Una pagina già aperta resta com'è: Z-14b. Era: un intervallo
  già caricato nella sessione tornava dalla cache finché non si premeva «Aggiorna» su quella pagina. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-14 — analisi».
  - Prova (19/10): `1f4986c70`, entrato in `2765773f5`; CHANGELOG `6e02e56ec`.
- **Z-14b · Una pagina dei prezzi o dei cambi aperta durante un recupero non si ricarica da sola** — basso, UX;
  Z, 17/10 (Z-14). Con Z-14 i negozi dei prezzi e dei cambi diventano stale su `{kind: 'prices'}` e la lettura
  successiva chiede di nuovo; ma una pagina già aperta (lista e dettaglio degli asset, lista e dettaglio dei cambi)
  tiene il suo grafico finché non cambia intervallo, non si naviga o non si preme «Aggiorna», mentre Dashboard e
  broker si ricaricano in background (Z-13). Cura possibile: un ascoltatore di `{kind: 'prices'}` nelle quattro
  pagine e una ricarica silenziosa (niente `aria-busy` né spinner, la lezione di Z-18). Nello stesso spirito: al
  ritorno dopo un recupero la pagina mostra il caricamento, come una prima visita, invece dei punti vecchi che il
  negozio tiene. Decisione di UX del developer, fra le domande del mattino del coordinatore; il dettaglio asset è
  ora di Y. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-14 — analisi», punto B.
  - Stato (19/10): piano pronto (piano 06, «Z-14b + Z-15 — piano per il mattino»), non partito: aspetta il sì del
    developer.
- **Z-15 · Dopo un recupero dei prezzi i pannelli di rischio e dei lotti restano indietro** — basso; coordinatore e Y,
  16/10 (Z-13b, vincolo Y11). La ricarica in background di Z-13 chiede di nuovo solo il report della pagina: non tocca
  `refreshVersion` né `requestPortfolioRefresh()`, che sono l'«Aggiorna» dell'utente e con Y11 farebbero girare
  l'icona (`pageBusy`). I pannelli di rischio e dei lotti già sullo schermo tengono le cifre vecchie, segnate stale,
  finché non si ricaricano. Da decidere con Y dopo Y11: per esempio i pannelli si ricaricano da soli su
  `{kind: 'prices'}`, fuori da `pageBusy`. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-13», passo 6.
  - Stato (19/10): con Z-14b, piano pronto e non partito: aspetta il sì del developer.
- ✅ **Z-16 · `admin/filesystem`: l'albero tradotto è indietro** — minimo, traduzione; Z, 16/10 (Z-12). **Chiusa il
  17/10 a mano** (il commit è del coordinatore; via del 17/10 ~05:32, senza stamp): gli alberi IT, FR ed ES hanno le
  tre righe (`backups/`, `secrets/`, `instance.key`), con la colonna dei commenti allineata all'inglese, e i nove
  commenti dello spagnolo sono tradotti. La pagina resta con il suo debito di traduzione fuori dall'albero (la cache
  di Aphra è del 10/10): il prossimo giro lo chiude. Era: in `filesystem.es.md` nove commenti in inglese, e i tre
  alberi senza le tre righe aggiunte in inglese. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-16».
  - Prova (19/10): `3d9b30433`, entrato in `737972ef5`.
- ✅ **Z-17 · `developer/backend/scheduler.md`: «The backend does not validate these values»** — minimo, doc;
  docs-writer di Z, 16/10 (Z-5). **Chiusa il 16/10 col mini-lotto Z-17** (il commit è del coordinatore): la frase dice
  ora che `PATCH /api/v1/settings/global/bulk` controlla ogni valore con `validate_global_setting_value()` contro
  `GLOBAL_SETTINGS_CONSTRAINTS` e risponde 422 senza scrivere nulla, e che i ripieghi del caricamento restano per i
  valori salvati prima del controllo o scritti a mano. Era: diceva che il backend non valida e che i limiti li fa
  rispettare solo il dialogo, falso da `84d9e3360` (9/10). Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-17».
  - Prova (19/10): `e6f152622`, entrato in `4f0a5d323`.
- ✅ **Z-18 · Il Dashboard si dichiara «occupato» durante la ricarica dopo un recupero dei prezzi** — basso,
  accessibilità; Y tramite il coordinatore, 16/10 (Z-13, P3 di Y11). **Chiusa il 16/10 col lotto B** (il commit è del
  coordinatore): dopo un recupero il Dashboard ricarica con `loadAll(false, false, {background: true})`, che non accende
  né `reportLoading` né `contributionRefreshing` (al suo posto `contributionInBackground`, che la radice non legge):
  `aria-busy` e `data-busy` della radice restano spenti; un caricamento chiesto dall'utente li accende ancora. I
  pulsanti «Aggiorna» seguono `pageBusy.busy` da Y11 e non girano: lo fissano (d), (e) e (f) dello spec di Z-13, e
  i due casi «reload in background» di `page-busy.spec.ts` attendono ora la radice a `false`. Era: la radice passava
  a `aria-busy="true"` e un lettore di schermo annunciava «occupato» per un semplice aggiornamento dei prezzi.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Lotto B».
  - Prova (19/10): `1b46178bd` (lotto B), entrato in `30483ec38`; CHANGELOG `4e233fe5b`.
- ✅ **Z-19 · N58: due funzioni di produzione che servono solo ai test** — basso; coordinatore (da H-22), 16/10.
  **Chiusa il 16/10 col lotto A** (il commit è del coordinatore): tolte `reset_provider_cooldowns()`,
  `reset_shutdown_budget_state()` e `Cooldowns.clear()`; i test mettono un `Cooldowns` nuovo al posto di
  `PROVIDER_COOLDOWNS` e rimettono `_watchdog` a `None` con `monkeypatch` (PCD-018 riscritto sul comportamento,
  SDB-032 tolto). `Cooldowns.reset(key)` resta, eccezione di N58 scritta nel docstring: nessun metodo pubblico dà a
  PCD-011 lo stesso stato pulito. `lint --dead-code` non segnala più le due funzioni.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Lotto A», decisione N-ZA-6.
  - Prova (19/10): `a43502298` (lotto A), entrato in `0f55265a1`.
- ✅ **Z-20 · Disaccoppiare `zodios-client` dai moduli con le rune** — basso; coordinatore, 16/10 (riga J-26, assegnata
  a Z). **Chiusa il 17/10 col lotto Z-20** (il commit è del coordinatore; H e J hanno scelto): il client delle API e
  l'ingresso della sonda non importano più moduli con le rune. `instanceBlock` è diviso in `instanceBlockState.ts`
  (semplice: le costanti, `isInstanceBlockedError`, il segnale, il reset di sessione), che il client segna, e
  `instanceBlock.svelte.ts`, la faccia reattiva del layout, allineata in modo sincrono (opzione A di H, con le sue
  quattro condizioni); il pozzo degli avvisi di `priceRefresh` carica `instanceNotices.svelte` al primo uso. Il ponte
  della sonda non ha più il plugin di Svelte (sì di J) e il cancello `apiClientRuneFree.gate.test.ts` (`core-unit`) lo
  tiene vero, da `$lib/api` e dall'ingresso della sonda. Era: dal 16/10 11:18 (Z5) il ponte moriva con
  `rune_outside_svelte`, e J l'aveva riparato compilando le rune (`985b10cbd`). Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-20 — analisi».
  - Prova (19/10): `3235837ad`, entrato in `3f654c4da`.
- ✅ **Z-21 · N58: altre quattro funzioni di Z usate solo dai test** — basso; Z, 16/10 (lotto A, `lint --dead-code`).
  **Chiusa il 17/10 col lotto Z-21** (il commit è del coordinatore): tolte `cooldown_snapshot()`, la proprietà
  `ShutdownWatchdog.armed_at`, `current_shutdown_watchdog()` e `Activity.is_busy()`, con le due menzioni del runner. I
  test leggono l'istanza in uso, il `deadline`, `shutdown_budget._watchdog` e `busy_reasons()`; nessun caso tolto.
  `lint --dead-code` non le segnala più. Nata come Z-20, rinominata il 16/10 (il numero era già di J-26). Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-21».
  - Prova (19/10): `e05b231ff`, entrato in `ffd58ffbd`.
- ✅ **Z-22 · `instanceBlock.svelte.ts`: un ascoltatore in più a ogni aggiornamento a caldo** — basso, solo sviluppo;
  H, 17/10 (revisione di Z-20). **Chiusa il 17/10 col lotto Z-22** (il commit è del coordinatore): ogni copia della
  faccia ferma la precedente passandosi la funzione per `import.meta.hot.data`; la build toglie il blocco. La riga
  proposta, `import.meta.hot?.dispose(stop)`, qui non scatta: Vite chiama `dispose()` solo sul modulo attraverso cui
  l'aggiornamento è accettato, cioè il layout (provato col Vite del repo: 1→4 ascoltatori in tre modifiche, col
  passaggio sempre 1). Era: la faccia si iscriveva a `instanceBlockState` all'import, e a ogni aggiornamento a caldo
  del file la copia vecchia restava iscritta. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-22».
  - Prova (19/10): `d49263b0e`, entrato in `22d46da6e`.
- **Z-23 · Un aiuto comune per i lock su file (`flock`)** — basso, dopo la 1.3; Z, 17/10 (Z-11, N-Z11-4). Il modello
  «`LOCK_EX|LOCK_NB`, `O_NOFOLLOW`, `0o600`, ripiego per processo senza `fcntl`» è ora in cinque posti:
  `instance_backup/jobs.py` (`_RunLock`), `instance_backup/apply.py`, `db/post_migration`, `brim_provider.py` e
  `scheduler/run_lock.py`. Un modulo comune li unirebbe; tocca file di più sessioni (fra cui B per il backup).
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-11 — lock dei job tra
  processi: analisi».
- ✅ **Z-24 · `.scheduler.lock` fra i percorsi protetti della cartella dati di test** — **chiusa il 17/10 da H**
  (dev `36a487e84`): `managed_paths` di `validate_test_data_dir()` + test di symlink e hardlink. Era: minimo,
  facoltativo; Z, 17/10
  (Z-11, segnalato da test-author). `validate_test_data_dir` (`backend/app/config/__init__.py`, file di H) elenca i
  percorsi gestiti che una cartella di test non può condividere con la produzione: c'è `scheduler_state.json`, non
  il nuovo `.scheduler.lock`. Rischio basso: un symlink al suo posto è già rifiutato (`O_NOFOLLOW`), e un hardlink al
  lock di produzione farebbe solo aspettare a turno i giri dei due server, senza toccare dati. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-11 — lock dei job tra processi:
  analisi».
- ✅ **Z-25 · Un tetto alla lunghezza delle liste di `POST /assets/prices/query` e `POST /fx/currencies/convert`** —
  basso, sicurezza; Z, 17/10 (X-R55, N75, punto 4; via coordinatore). **Chiusa il 17/10 col lotto Z-25** (il commit
  è del coordinatore; decisione notturna N77, opzione C, da rivedere col developer).
  - Al più 1 000 voci per richiesta (422 `bulk_too_many_items`, prima di ogni lettura) e 5 milioni di voci-giorno
    (422 `bulk_too_many_days`). Costanti, errore e `detail` in `utils/date_range_limits.py`.
  - Prezzi: `get_prices_bulk()` conta, dopo la lettura di prezzi e semi e prima dei riempimenti, i punti che ogni
    riempimento emetterà (`_fill_span()`), serie di confronto comprese. Cambi: il gestore pianifica e conta ogni
    blocco di giorni prima di costruirne uno; un rifiuto costa millisecondi (BL-API-03: 0,01 s).
  - Restano: il web app (Z-27, sotto); rischio e AI Export ricevono `BulkTooManyDaysError` senza 422 (un 500): riga
    a J dal coordinatore, che dovrà aggiornare anche la frase in `developer/backend/assets/architecture.md`
    (`#bulk-request-limits`).
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-25 — un tetto alle
  richieste di massa di prezzi e cambi: analisi».
  - Prova (19/10): `4b711e803`, entrato in `d0bc7a547`; CHANGELOG `282c583b5`.
- ✅ **Z-26 · L'attesa del lock fra processi dello scheduler non ha un tempo massimo** — basso; E (R13-SEC8), via
  coordinatore, 17/10. **Chiusa il 17/10 col lotto Z-26** (il commit è del coordinatore; decisione notturna N79, da
  rivedere col developer).
  - Un giro aspetta al più `LOCK_WAIT_SECONDS` (600 s, `scheduler/run_lock.py`): una sola scadenza, fissata dopo
    l'assestamento dell'orologio, per le due attese, il lock del processo e quello fra processi; mai per i job.
  - A scadenza: nessun job, stato non letto, un avviso nel log, e `not_leader`; il giro dopo riprova. Il
    `wake-sync` dietro un giro fermo risponde così, e la sveglia seguente è accettata.
  Era: `scheduler_run_lock()` (`run_lock.py:83-91`, Z-11) aspettava senza limite; un job bloccato in un worker
  fermava i giri degli altri, e `wake-sync` rispondeva 409 a chi arrivava dopo. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-26 — l'attesa del lock fra
  processi senza tempo massimo: analisi».
  - Prova (19/10): `e9999a11a`, entrato in `8c362c1f3`; CHANGELOG `8850fe814`.
- ✅ **Z-27 · Il web app manda una pagina intera in una richiesta di massa (per Y e X)** — basso, dopo Z-25; Z, 17/10
  (Z-25, N77; via coordinatore).
  - La lista asset (`fetchAllPriceData` in `routes/(app)/assets/+page.svelte`) manda una voce per asset in un solo
    `POST /assets/prices/query`; la lista e il registro dei cambi fanno lo stesso con le coppie.
  - Con Z-25 un'istanza oltre 1 000 asset, o oltre 5 milioni di voci-giorno, riceve un 422. Oggi la pagina mostra
    allora le carte senza prezzi: l'errore arriva solo alla console (il `catch` di `fetchAllPriceData`).
  - Seguito: dividere la richiesta in lotti (Y, X). Il messaggio esplicito lo fa X (con X-R53), per non avere due
    scrittori sulle stesse pagine.
  - **Anche i cambi a periodo fisso** (MF, 17/10, X-R59; decisione del coordinatore): `POST /assets/prices/period-changes`
    e `POST /fx/currencies/period-changes` hanno lo stesso tetto (`MAX_BULK_ITEMS`, 422 `bulk_too_many_items`), più
    ≤ 5 giorni `as_of`/`range_start` distinti (422 `period_changes_too_many_days`): la stessa regola di divisione in
    lotti da 1 000 vale per loro, con un `as_of` per richiesta.
  - **Chiusa il 17/10 per la parte di Z** (il commit è del coordinatore; decisioni D1–D4): l'aiuto
    `lib/api/bulkBatches.ts` e i chiamanti A (lista asset) e C (lista cambi), con R13-SEC9-2 (il budget a 1 000 000,
    800 000 nel web app). Le colonne Δ (D/B) le passa X all'aiuto, con X-R59 e X-R60; il messaggio di X-R58 viene
    dopo, negli stessi `catch`.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezioni «Z-25 — un tetto alle
  richieste di massa di prezzi e cambi: analisi», «Z-27 — il web app e i tetti delle richieste di massa: analisi» e
  «Z-27 — le richieste di massa divise in lotti: lavoro».
  - Prova (19/10): `8d236fa11`, entrato in `726d90d72`; CHANGELOG `f1786a883`.
- **Z-29 · Una scheda della lista asset carica lo storico giornaliero intero** — **alto** (coordinatore, 17/10, da
  R13-SEC9-2 di E: «it's the real cure, post-1.3»), progetto, **nella 1.3** (N90, 17/10; ordine del 20/10: Y-39 → Z-29b → Z-29s → Y-40); Z, 17/10 (dall'analisi di Z-27).
  - Su «All» la lista chiede per ogni asset tutti i giorni dal 2000 (~9 800 punti): 300 asset sono ~2,9 milioni di
    punti, centinaia di MB di JSON, elaborati dal pool di worker. I lotti di Z-27 ne limitano il picco per risposta,
    non il totale.
  - Una scheda ne mostra un riassunto (ultimo prezzo, mini grafico): servirebbe una serie ridotta dal backend
    (campionata) o un'altra fonte per le schede. Da progettare dopo la 1.3; tocca la lista (X) e la query dei prezzi.
  - Analisi del 17/10 (sola lettura, chiesta dal coordinatore per la 1.3): consigliata (A), `max_points` facoltativo
    nella query dei prezzi (il backend sceglie il passo per asset, ~30× meno punti su «All»), in due lotti: Z-29a
    backend, Z-29b lista (X). In attesa della decisione.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezioni «Z-27 — il web app e i tetti
  delle richieste di massa: analisi» e «Z-29 — una scheda della lista asset e lo storico intero: analisi».
  - Stato (21/10): Z-29a (backend: `max_points`, `resolution`, `sample_like`) in `dev_release2` col treno 1 (`746920b83`),
    Z-29d-0 col treno 2, Z-29a-f col treno 4 (`bbc668d02`). Restano: Z-29s-a (rossi scritti nel worktree di Z, nessun codice),
    Z-29b (dopo l'ingresso di Y-39a, stesso file `assets/+page.svelte`), Z-29s, Z-29d ridotto, Z-29fx (dopo Y-40).
  - Z-29s-a (21/10): la cura e i verdi sono nel worktree di Z (checkpoint consegnato al coordinatore, da committare):
    i `signals` si accettano con `max_points` / `resolution` / `sample_like` e la serie di prezzo e i segnali si ridu-
    cono sui secchi del prezzo (`sample_signal_series`). Restano Z-29b, Z-29d ridotto, Z-29fx; i residui R1–R4 sono in Z-40.
- ✅ **Z-28 · Due file di lock aperti con `open()`, che segue un symlink** — basso, sicurezza; Z, 17/10
  (dall'analisi di Z-23; via coordinatore, che l'ha assegnata). **Chiusa il 17/10 col lotto Z-28** (il commit è del
  coordinatore).
  - `db/post_migration/__init__.py` (`_exclusive_run`) e `services/brim/brim_provider.py` (`_acquire_file_lock`)
    aprono il loro lock con `open(…, "a+")`: un symlink al suo posto viene seguito (uno pendente crea un file vuoto
    altrove), e il modo viene dall'umask (di solito `0o644`).
  - Cura: `os.open` con `O_RDWR | O_CREAT | O_NOFOLLOW` e `0o600`, come i lock del backup e dello scheduler.
    Revisori: W (BRIM) e H (post-migrazione).
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-28 — due file di lock
  aperti con `open()`».
  - Prova (19/10): `3a3d5ab1c`, entrato in `2b9786ae5`; CHANGELOG `11a6f4ea1`.
- ✅ **Z-30 · Le righe di prezzi e cambi già salvate prima del 1900** — basso; coordinatore, 17/10 (X-R65, decisione
  D3). **Chiusa il 17/10 col lotto Z-30** (decisione: strada (a); il commit è del coordinatore; revisore MF).
  - Da X-R65 (N83) le scritture le rifiutano, ma una riga già nel database resta: il riempimento dei prezzi parte dal
    primo prezzo salvato, e uno del 0001-01-01 fa camminare ~740 000 giorni per asset (sotto il budget di 1 milione).
  - Strade: un pavimento in lettura nel riempimento (`_build_backward_filled_series` e `_fill_span` da
    `max(primo prezzo, 1900)`), o una correzione post-migrazione che le segnala o le toglie. Da decidere.
  - Fatto: in `get_prices_bulk` una storia intera (`requires_full_history`) si carica dal 1900-01-01, o dall'inizio
    visibile se è prima. Una riga più vecchia fa solo da seme: un giorno visibile cammina ~45 800 giorni, non
    ~740 000. I riscaldamenti finiti restano com'erano. I cambi non camminano dalla prima riga: fuori.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezioni «X-R65 (N83) — date assurde
  nelle scritture manuali di prezzi e cambi: analisi» e «Z-30 — le righe salvate prima del 1900: lavoro».
  - Prova (19/10): `501375cdc`, entrato in `fb514073b`; CHANGELOG `93065bc7c`; seguito `06ec7d443` in `80cef0e43`.
- **Z-31 · La query dei prezzi non limita l'inizio visibile** — basso, residuo di Z-30, **dopo la 1.3**
  (coordinatore, 17/10); Z, 17/10 (nota di test-author).
  - `get_prices_bulk` taglia solo la fine (`latest_range_end()`). Un intervallo chiesto a mano prima del 1900 su un
    asset con una riga vecchia emette ancora fino a ~740 000 punti visibili, dentro il budget di 1 milione.
  - Lo scope di rischio e la conversione FX limitano già l'inizio a 100 anni dalla fine (`range_span_floor`, X-R55);
    «All» della UI parte dal 2000-01-01. Rimedio: lo stesso limite nel percorso dei prezzi (file di MF).
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-30 — le righe salvate
  prima del 1900: lavoro», passo 4.
- **Z-32 · Le linee Yahoo in pence (`GBp`) salvate come sterline** — medio, dati; Z, 17/10 (verifica chiesta dal
  coordinatore, da una nota di E in MF-SEC9b). Da assegnare a chi possiede i provider.
  - **(c) chiusa il 17/10** (decisioni D1–D5 del coordinatore; il commit è suo; revisori X, MF, H): la valuta come la
    dice il provider (`FAHistoricalData.currency`, non normalizzata) salvata sull'assegnazione (`reported_currency`,
    migrazione 010), l'avviso `QUOTE_IN_MINOR_UNIT` nel report di qualità del portafoglio. Restano (a) e (b), per
    lo sviluppatore, dopo la 1.3; la strada 3 (chiusure contro operazioni) va nella sezione di MF (il coordinatore).
  - Yahoo dà `GBp` per le linee LSE in pence; gli schemi lo normalizzano a `GBP` senza scala: prezzi e dividendi
    restano in pence ma salvati come sterline. Nessuno imposta `quote_base_quantity`: con la base di default (1) la
    linea vale 100 volte il dovuto; con la base 100 messa a mano i valori tornano, ma i dividendi mostrati (dettaglio
    dell'asset, evento collegato di una transazione) restano in pence. `ZAc`, `ILA` e `GBX` sono invece rifiutati.
  - Strade: (a) Yahoo divide per 100 (dati puliti, ma le righe salvate vanno ricalcolate e la base messa a mano si
    rompe); (b) la base 100 impostata quando Yahoo dà `GBp` e divisa dove un evento diventa un importo; (c) un avviso
    di qualità dei dati. Parere: (c) nella 1.3 se serve, (b) dopo.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «GBp — i dividendi Yahoo e
  `quote_base_quantity`: verifica».
  - Stato (19/10): (c) ✅ `aa9e07544`, entrato in `46ea09b02`, CHANGELOG `22b9b90ce`; (a) e (b) restano per dopo la 1.3.
    La migrazione 010 di (c) è in discussione: piano 06, sezione «Z-33 ridotta».
  - **(c) tolta il 19/10** (Z-32cr; D8 del developer, testuale: «nessuna colonna nel db, sono certo»): via la colonna
    dal modello, la scrittura nel refresh, `QUOTE_IN_MINOR_UNIT`, la chiave i18n, la doc e i test; la migrazione 010 e
    il suo test li sostituisce H con la 005 unica. Restano `utils/currency_units.py` (lo legge `NON_ISO_CURRENCY` di
    E-19b2) e la valuta grezza della storia (`GBp`). Dettagli: piano 06, sezione «Z-32cr».
  - **(d) la base suggerita dal plugin** alla creazione (D8, testuale: «pre-popoliamo il campo della quantità base a
    100, potremmo farlo anche se il plugin ce lo suggerisce»): analisi breve consegnata il 19/10, in attesa del via e
    delle risposte Q-Q1…Q4. Dettagli: piano 06, sezione «Z-32 (d)».
- ✅ **Z-33 · I prezzi Yahoo delle borse a est di UTC salvati un giorno prima** — **alto**, dati; Z, 17/10 (trovato da
  test-author scrivendo la guardia di Z-32, confermato da Z e dal coordinatore). Proprietario Z; X rivede il plugin.
  Nella 1.3, subito dopo il checkpoint di Z-32 (c).
  - yfinance 1.7.0 (`scrapers/history.py:494–501`) data le barre giornaliere, i dividendi e gli split a mezzanotte
    nel fuso della borsa; `_normalize_yahoo_date` (`yahoo_finance/plugin.py:146–150`) le porta in UTC: a est di UTC
    è il giorno prima. Milano tutto l'anno, Londra con l'ora legale, Tokyo; New York è giusta.
  - Il prezzo salvato al giorno D è la chiusura vera di D+1; righe di domenica; dividendi e split un giorno prima.
  - La correzione del codice è semplice (la data locale); la riparazione dei dati già salvati è da decidere
    (sviluppatore): righe in più nei giorni senza borsa, eventi forse doppi a una risincronizzazione.
  - **Decisione N86** (coordinatore, 17/10), nella forma D″: il controllo una volta, in linea, nel refresh, insieme
    alla correzione; la storia intera di Yahoo solo come calendario (i valori non cambiano mai); migrazione 011
    (`exchange_timezone`, col segno `'legacy-utc'` sulle assegnazioni yfinance esistenti); anche la data del valore
    corrente. **Chiusa il 17/10 col lotto Z-33** (il commit è del coordinatore; revisori X, H, MF, W).
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezioni «Z-33 — … analisi» e
  «Z-33 — … lavoro».
  - Prova (19/10): `60170aae5`, entrato in `51b5c8db1`; CHANGELOG `b8bcc8cd2`; seguiti `79265b1a0` (dev `e20055213`) e
    `b5da2277d` (dev `d01a13b10`); devWiki `f74229303`. **19/10: riduzione decisa dal developer** (solo la correzione
    del plugin, niente riparazione né colonne): analisi «Z-33 ridotta» nel piano 06; finché non entra, la riparazione
    resta nel codice.
  - Z-33r (19/10, via del coordinatore): tolte la riparazione (passo 0 e controllo D″ nel refresh, aiuti di
    ridatazione), la colonna `exchange_timezone`, il segno e la migrazione 011; resta la correzione del plugin. Guida
    per i DB già alla 011: piano 06, sezione «Z-33r».
- **Z-36 · `tzdata` da PyPI: un server senza database dei fusi non risolve il fuso della borsa** — minimo (era basso
  fino a Z-33r), ambiente,
  **domanda per lo sviluppatore**; Z, 17/10 (dalla revisione di H a Z-33, archiviato su richiesta del coordinatore).
  - Su un host senza database dei fusi (Windows fuori da Docker, un container minimo) o con un nome che tzdata non ha,
    `exchange_zone()` dà None: un'assegnazione Yahoo ancora segnata dalla migrazione 011 non scrive nulla a ogni giro.
    L'immagine Docker è a posto.
  - Fatto nella 1.3 (la metà a basso costo): un avviso nel log, una volta per nome e processo (Z-33, terzo seguito).
  - Da decidere: aggiungere `tzdata` (PyPI) alle dipendenze, così `zoneinfo` ha sempre i fusi. Cambia l'ambiente:
    decisione dello sviluppatore. Nota (docs-writer, 17/10): pandas 3.0.5 dichiara `tzdata` per `win32`, ma il
    `Pipfile.lock`, risolto su macOS, non lo porta: su Windows c'è o no a seconda di come si è installato.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-33 — … lavoro», passo 12.
  - Stato (19/10): con la riduzione di Z-33 resta solo la data del valore corrente (in UTC senza fusi); vedi l'analisi
    «Z-33 ridotta» e la P-4 del coordinatore (`tzdata` nell'immagine). Con Z-33r l'avviso sta nel plugin
    (`_exchange_zone`) e dice che il valore corrente è datato in UTC.
- **Z-35 · Le chiusure Yahoo salvate con la rettifica del giorno in cui sono state lette** — medio, dati, **dopo la
  1.3**, decisione dello sviluppatore; proprietari X e MF; Z, 17/10 (trovato nell'analisi di Z-33, archiviato dal
  coordinatore).
  - Il plugin chiama `ticker.history(...)` senza `auto_adjust`; yfinance 1.7.0 rettifica di default
    (`auto_adjust=True`): OHLC salvati rettificati per dividendi e split al momento della lettura. Lo scheduler
    rilegge solo 14 giorni: le righe vecchie restano con rettifiche vecchie, le nuove con quella di oggi (una toppa).
  - Le metriche di rendimento possono contare due volte i dividendi: già nei prezzi rettificati e negli eventi.
  - Da decidere: `auto_adjust=False` (prezzi di borsa veri, split a parte) e la riscrittura della storia.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-33 — … lavoro».
- ✅ **Z-34 · Il rapporto (C) delle righe Yahoo rimaste spostate** — basso, dati, **dopo la 1.3**; Z, 17/10 (decisione
  N86, D4). **Chiusa il 19/10 come superata** (D7, via del coordinatore): con Z-33r non c'è più riparazione, tutte le
  righe salvate prima restano spostate per decisione del developer, e un rapporto non ha più oggetto.
  - La ridatazione di Z-33 avviene al primo giro di ogni assegnazione yfinance segnata dalla migrazione 011. Restano
    spostate le righe degli asset la cui assegnazione yfinance è stata tolta prima dell'aggiornamento, o prima del
    suo primo giro dopo; e quelle di un cambio di identificativo fra fusi di segno diverso prima di quel giro.
  - Proposta: un comando che le elenca (asset, righe `yfinance` senza assegnazione o col segno ancora presente,
    domeniche senza sabati come indizio) e, con la rete, le ridata con la stessa regola.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-33 — … lavoro».
  - Stato (19/10): con la riduzione di Z-33 (nessuna riparazione) il rapporto perde il suo oggetto; chiuderla o tenerla
    è una domanda nell'analisi «Z-33 ridotta».
- **Z-37 · Client generato: un apice inverso nella descrizione di un modello riferito da un campo obbligatorio rompe
  `generated.ts`** — minimo, strumenti; proprietario degli script di generazione da assegnare; Z, 19/10 (Z-29a).
  - openapi-zod-client 1.18, con `--with-description`, scrive un campo obbligatorio che è un `$ref` diretto con la
    descrizione del modello riferito in un letterale tra apici inversi: un apice inverso nella docstring lo chiude, e
    `api sync` si ferma («Tool codegen: invalid generated TypeScript»), con lui il server di prova.
  - Oggi curato solo in `FAPricePoint` (Z-29a: `json_schema_extra` mette apici semplici nello schema); gli altri `$ref`
    obbligatori (225) non portano a descrizioni con apici inversi.
  - Proposta: una pulizia generale nella generazione (`frontend/scripts`) o un cancello che nomini il modello al
    `api sync`; dopo, la cura di `FAPricePoint` si può togliere.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-29a (v3) e Z-29r — lavoro»,
  passo 4 di Z-29a.
- **Z-38 · `uniform.py` di AI Export tiene una sua copia della regola per secchio** — minimo, codice; proprietario J
  (revisore di Z-29r); Z, 19/10 (Z-29r).
  - `ai_export/temporal/uniform.py` (`uniform_observed_buckets`) sceglie primo, minimo, massimo e ultimo con la stessa
    regola del pari valore che Z-29r ha messo in una casa sola, `services/signals/aggregation.py`.
  - Proposta: farla passare da `aggregation.select_point`, a uscite invariate (i test di AI Export lo dicono).
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-29a (v3) e Z-29r — lavoro»,
  passo 3 di Z-29r.
- ✅ **Z-39 · Yahoo: `_fetch_currency` inghiotte un rifiuto per troppe richieste e tiene None per 24 h** — basso,
  fornitori; proprietario X (il plugin di Yahoo); Z, 20/10 (docs-writer, dalla doc di Z-32 d; verificato da Z).
  - `_fetch_currency` (`yahoo_finance/plugin.py:397-416`) legge `fast_info` senza `_yf_with_retry` e prende ogni
    eccezione, `YFRateLimitError` compreso: mette None nella cache delle valute per 24 ore e risponde normalmente.
  - Effetti: per un giorno, in quel processo, il simbolo non ha valuta nella ricerca e non ha suggerimento della base
    (Z-32 d); e `core.call_provider` non vede il rifiuto, quindi non mette in pausa il fornitore (la regola della guida:
    un rifiuto non si inghiotte). Prima di Z-32 (d) toccava già la ricerca.
  - Proposta: nessuna voce in cache per un rifiuto, e per `suggest_quote_base` lasciarlo salire (la sonda lo prende già
    come «nessun suggerimento»); nella ricerca, decidere se lo stesso o un risultato senza valuta.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-32 (d) — lavoro», passo 5.
  - ✅ 21/10 (riconciliazione): in `dev_release2` col treno 3 (`cac0ab76e`; commit `6011a9ff0`).
- **Z-40 · Segnali ridotti dal backend: quattro punti in cui la scheda e il grafico pieno possono differire** — minimo,
  qualità dei dati dei grafici; Z, 21/10 (Z-29s-a). I primi due sono stati accettati dal developer il 19/10.
  - R1: un secchio dove due corse (tratti senza buchi) si incontrano mostra un punto, quello della seconda, dove il
    browser ne disegnerebbe due. R2: una linea con regioni a stile viene divisa per stile dal browser dopo la
    riduzione. R3: due corse a un giorno di distanza alla fine del periodo non hanno posto per il segnaposto del buco.
    R4: oltre 30 corse il browser unisce i buchi di una linea senza stile; dopo la riduzione conta le corse ridotte.
  - R1 e R3 sono casi della tabella `signal_sampling_cases.v1.json` con `browser_parity: false` (più il caso «niente nel
    periodo», dove la riduzione lascia la serie com'è e il browser non disegna nulla), ognuno con la sua nota; il Vitest
    di `timeSeriesAggregation` li tiene documentati (il browser disegna altro). R2 e R4 vengono dal modo di disegnare
    del browser e **non** sono nella tabella né in un test.
  - Proposta: nessuna cura; sono differenze piccole e dette nel contratto. Da rivedere solo se un revisore (MF o Y) o il
    developer chiede la parità piena, che cambierebbe il contratto della serie ridotta.
  Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z-29s-a — i segnali ridotti dal
  backend, la metà backend: lavoro».

## B · Backup e Docker (fase 01)

Piano: [`07_backupDocker`](../Phase_1/07_backupDocker/plan-phase01BackupDocker.prompt.md). Sessione avviata il 15/10 alle
07:10, solo analisi, sulla base `ee5d81a6f`. Codice autorizzato il 15/10 alle 11:25 (delega del developer): B0 e B1,
sulla base `23f6578f3`.

- ✅ **B-1 · devWiki: F-073 e `domains/infrastructure` danno per fatto il backup completo** — minimo, doc; B, 15/10
  (analisi). **Chiusa il 15/10 con B1**: F-073 racconta il backup dell'istanza e il ripristino che manca, la nota sullo
  streaming è giusta, la riga di Impostazioni rimanda a B5; la riga di `domains/infrastructure.md` dice lo stesso.
  - `features/F-073.md` è `implemented`, ma il backup completo risponde 501; dice «streaming, nessun accumulo», ma gli
    export per serie materializzano le righe; chiama `GET /backup/export`, che è un `POST`; cita una sezione di
    backup in Impostazioni che non esiste.
  - `domains/infrastructure.md`, riga F-073: «export and import the full SQLite database — implemented».
  - Le righe «Source files» sono giuste da B0 (15/10); la prosa si corregge con B1, che fa il backup vero, o con
    `project-historian`.

  Dettagli: [piano 07](../Phase_1/07_backupDocker/plan-phase01BackupDocker.prompt.md), §2, punto 1.
  **In dev**: `629d63306` (15/10 19:06), con B1 (`e35388306`).
- **B-2 · Un commento di `DataEditor.test.ts` cita `backend/app/api/v1/backup.py`** — minimo; B, 15/10 (B0).
  `frontend/src/lib/components/ui/data-editor/DataEditor.test.ts:802`: l'export degli eventi ora sta in
  `backend/app/api/v1/backup/exports.py`. Il file è di T (`ui/data-editor`): non lo tocco. Dettagli: piano 07, §13, B0
  passo 3.
- ✅ **B-3 · La docstring di `backup_asset_prices` cita `backup_service.PRICE_COLUMNS`, ed è nell'OpenAPI** — minimo, doc;
  B, 15/10 (B0). **Chiusa il 15/10 con B1**, che cambia comunque l'API. `backend/app/api/v1/backup/exports.py:71`: il modulo ora è `series_export.py`. Un lotto di riordino
  lascia lo schema identico, quindi la correggo in B1, che cambia comunque l'API. Dettagli: piano 07, §13, B0 passo 2.
  **In dev**: `629d63306` (15/10 19:06), con B1 (`e35388306`).
- ✅ **B-4 · I comandi dell'immagine elencati senza `backup`** — minimo, doc; B, 15/10 (B6a, segnalato da docs-writer).
  `docker_advanced.en.md#docker-exec` («In the image, `user`, `db` and `info` work»), il commento in testa a
  `docker-compose.yml` e `admin/index.en.md:21` («user management, database upgrades») non dicono che anche
  `dev.py backup` funziona nell'immagine. I file Docker sono di H fino al CP7a. **Passata ad H dal coordinatore** (15/10,
  14:37). Dettagli: piano 07, §13, B6a.
  ✅ **Fatta il 16/10 da H** nel lotto «b-doc-notes» (`d7eb9c5f3`, in dev con `0ecc5ed27`, 16/10 12:44):
  `docker_advanced.en.md` («In the image, `user`, `db`, `info` and `backup` work»), il commento di
  `docker-compose.yml` e la riga di `admin/index.en.md`. Chiusa da B il 19/10, alla contabilità.
- ✅ **B-5 · `filesystem.en.md` «💾 Backup» non conosce `dev.py backup`** — piccolo, doc; B, 15/10 (B6a). Il file è di H
  (CP3). Mancano:
  - un rimando a `cli_tools.md#backup`, l'unico modo di fare un backup coerente a server acceso senza `sqlite3`;
  - la nota che la copia della cartella dati prende anche `backups/`, con gli archivi;
  - `backups/` nell'albero della cartella;
  - un'ancora esplicita `{: #what-to-back-up }` sul titolo «✅ What to Back Up», nelle 4 lingue: i titoli tradotti hanno
    slug diversi, quindi la pagina della CLI ora punta a `filesystem.md#backup`.

  Testo proposto da docs-writer nel piano 07, §13, B6a. **Passata ad H dal coordinatore** (15/10, 14:37).
  ✅ **Fatta il 16/10 da H** nel lotto «b-doc-notes» (`d7eb9c5f3`, in dev con `0ecc5ed27`, 16/10 12:44): i quattro
  punti, l'ancora `{: #what-to-back-up }` nelle quattro lingue compresa. Chiusa da B il 19/10, alla contabilità.
- **B-6 · Il polling della scheda Backup ha il suo ciclo** — minimo; B, 15/10 (B5a). `BackupJobController` legge il
  job con un suo `setTimeout`, perché nella base non c'è ancora l'aiuto comune di Z (F26, «un solo aiuto di polling per
  tutti i cicli»). Quando entra, il controller lo usa. Il ciclo è breve e solo durante un backup avviato dall'admin.
  Dettagli: piano 07, §13, B5a.
- **B-7 · Debito di traduzione di `cli_tools.{it,fr,es}.md`** — piccolo, doc; B, 15/10 (B6a). Mancano la sezione
  «💾 Back Up the Instance» (5 sottosezioni), una frase dell'introduzione e il punto Docker del suggerimento. La pagina
  inglese non è timbrata: la traduzione passa dalla pipeline Aphra, su richiesta del developer.
- ✅ **B-8 · Un backup avviato dalla UI la cui risposta si perde resta invisibile alla scheda** — minimo; B, 15/10 (B5a,
  segnalato da test-author). Se la risposta di `POST /backup/instance` si perde (rete, timeout), il job gira sul server
  ma la scheda non conosce il suo id. Nessuna rotta elenca il job in corso, e il rifiuto `backup_busy` non lo porta.
  - Effetto: «busy» finché quel job finisce; il suo archivio scade dopo un'ora senza essere offerto; lo spazio su disco
    resta occupato per quell'ora.
  - Cura possibile: l'id (e l'origine) del job in corso nel dettaglio di `backup_busy`, così la scheda lo segue. Con
    un'attenzione: un job della CLI si sposta fuori da `.jobs/` alla fine.

  Dettagli: piano 07, §13, B5a, terza tornata.
  ⏸️ **Parcheggiata il 19/10**: rossi e doc scritti il 17/10 sera, mai eseguiti, poi il fermo del developer; ora in
  una patch della sessione di B (`files/parked/b15-b8-reds-docs-on-739bf08e0.patch`). Riprende col via del
  coordinatore, dopo la lettura del developer. Dettagli: piano 07, «B-15 + B-8».
  ✅ **Fatta il 19/10** (via del developer alle 11:42, le scelte 1-3 del README del parcheggio):
  - il 409 `backup_busy` porta `job_id` e `origin` del backup in corso;
  - la scheda segue un backup `ui` ritrovato così, e ne ricorda l'id prima della prima lettura;
  - con un archivio in offerta, la scheda lo tiene.
  La domanda sul 409, che nomina anche i backup del pannello e della CLI, è chiusa dal developer (19/10, pomeriggio):
  - la risposta resta com'è;
  - a schermo la scheda dice solo «occupato», e segue il proprio backup `ui` come prima;
  - id, origine e stato vanno in console, con un `console.warn` per rifiuto. Fatto lo stesso giorno.
  Difetto trovato dalla revisione automatica prima dell'ingresso (19/10) e curato lo stesso giorno: una richiesta
  sicura poteva seguire il backup in chiaro di un altro. Ora una richiesta sicura non segue mai da un 409; una in
  chiaro non presenta un job adottato che finisce cifrato (decisione del coordinatore). Rifinitura (20/10): il job
  che la scheda segue già da sé non si adotta, quindi la sua fine si offre qualunque sia la modalità.
  Dettagli: piano 07, «B-15 + B-8 — la ripresa», «B-8, difetto della revisione automatica» e «B-8, rifinitura».
- ✅ **B-9 · Il token del pannello non è fra i controlli della configurazione** — piccolo; B, 15/10 (B8).
  - Oggi un `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` inutilizzabile (corto, non ASCII visibile, `_FILE` illeggibile) si vede
    solo alla prima richiesta del pannello: 503 `backup_panel_unavailable` e una riga d'errore nel log.
  - All'avvio, `log_configuration_audit()` non lo nomina, e la futura scheda «Sicurezza» non lo mostrerà.
  - Cura possibile, come ha fatto E per l'email: `BACKUP_CONFIG_CHECKS` in un modulo di B (stato `ok`, `info` se
    spento, `error` se inutilizzabile, mai il valore), una riga in `config_audit.CONFIG_CHECKS` (file di H) e le
    chiavi `backup.checks.*` nelle 4 lingue.

  Dettagli: piano 07, §13, «B8 — il token del pannello, rimesso sopra `ef61f0e7f`».

  ✅ **Fatto il 17/10** (checkpoint delle 07:12), col controllo del limite di upload in più (coordinatore, 06:36). Il
  modulo nuovo `instance_backup/checks.py` dà `backup.panel_token` e `backup.upload_limit`, in `CONFIG_CHECKS` dopo
  `check_log_level` e prima dei controlli di E, che chiudono ancora la tupla. All'avvio un token o un limite
  inutilizzabile (corto, non ASCII visibile, `_FILE` illeggibile; non intero, voce del profilo mancante o del tipo
  sbagliato, H-27/H-37) è una riga ERROR che nomina la variabile, e la partenza continua. Il token non impostato è
  `ok` (`.off`), non `info`: un avvio predefinito non scrive nulla di nuovo. Le chiavi `backup.checks.*` sono nei 4
  cataloghi, per la scheda «Sicurezza» (A8b). Test: `services backup-checks` (57), più nel file di H le 2 voci di
  `CHECK_IDS` e un blocco «Workstream B» in `_configure`. Dettagli: piano 07, «B-9».
  **In dev**: `997dc7ecf` (17/10 07:37), merge di `0f3f72961`.
- **B-10 · Un pulsante del pannello che chiede all'istanza il link di reset dell'admin** — piccolo; B, 15/10 (decisione
  40, assegnata a B dal coordinatore). Recupero dell'admin dopo un ripristino o una password persa: oggi passa da
  «password dimenticata» via email (E), o dall'assistenza con `dev.py user reset-link`.
  - Cura: una rotta col token del pannello, come B8 (`require_panel_token`, permessa sull'istanza bloccata se il
    developer lo vuole), che chiama la funzione dei link di reset di A e restituisce il link al pannello.
  - Non per la 1.3, a meno che resti tempo (coordinatore, 15/10).

  Dettagli: piano 07, §13, «Base `10697e618`, prove d'ingresso e decisioni 40–43».
- **B-11 · Debito di traduzione delle pagine admin di B2, B3 e B8** — piccolo, doc; B, 15/10 (B2; B3 il 16/10). Pagine
  inglesi scritte da docs-writer, senza timbro. In it, fr ed es mancano:
  - in `cli_tools`, la sezione «🧪 Try a Restore on a Copy»; da B3, le sezioni «♻️ Restore an Archive» (`#backup-restore`)
    e «⏳ Follow or Cancel a Restore» (`#backup-pending`), più i ritocchi del consiglio iniziale, dell'introduzione di
    «Back Up the Instance», di «Use an Archive on Another Installation» e del blocco Docker;
  - in `configuration`, le righe nuove di «Main Options» e di «Secrets»;
  - in `admin/index`, la riga di riepilogo, più tre aggiunte che le traduzioni non avevano già dal 12/10.

  `hosting_providers` non ha nessuna traduzione: tutta la pagina, con le sezioni nuove `#panel-backups` e
  `#restore-upload-limit`. Da B6a-bis: la pagina nuova `admin/backup_restore.en.md` (tutta), una frase in «💾 Backup» di
  `filesystem` e un punto in `admin/index`. Si fa con la pipeline Aphra, su richiesta del developer; si somma a B-7. Dettagli: piano 07,
  §13, «B2b — l'API della prova su copia».
- **B-12 · Un salto d'orologio fra i worker di un server con `--workers N`, nel primo avvio dopo un ripristino** —
  piccolo, nessun rischio per i dati; B, 16/10 (B3, revisione di sicurezza di metà percorso). Ogni processo legge il
  «boot» una volta (il master di uvicorn, con l'ora di creazione di psutil, che su Linux si sposta con un salto
  d'orologio). Se il salto cade fra la lettura di due worker, il secondo vede il ripristino «applicato da un altro boot»:
  se il primo tiene già il lock di «server acceso», l'avvio si ferma e quello dopo annulla il ripristino; se non lo tiene
  ancora, non ha letto niente, e aspetta a `serving-lock` che l'annullamento finisca (lock esclusivo durante le
  rinomine). Al più un `mkdir` del passo `data-directories` dentro le rinomine fa fallire l'annullamento: l'avvio si
  ferma e il seguente lo completa. In tutti i casi il ripristino va rifatto, i dati di prima restano. Lo stesso
  per due contenitori sulla stessa cartella dati (spazi di PID diversi). Cura: un'identità senza orologio su Linux
  (`starttime` in tick da `/proc/<pid>/stat`, più `/proc/sys/kernel/random/boot_id`).
  Dettagli: piano 07, §13, «B3 — revisione di sicurezza di metà percorso».
- ✅ **B-13 · I totali di controllo di J (CP-15) nel manifest, nella prova su copia e nell'e2e** — medio; B, 16/10 (B3).
  **Fatto il 16/10** nel lotto B-13 (commit del coordinatore dopo l'handoff delle 08:40).
  CP-15 è entrato (`financial_math/ledger_totals.py`: `compute_control_totals(session)`, `ControlTotals.to_json()`):
  il manifest li porta (§3.2 del piano 07), la prova li ricalcola sulla copia e li confronta con un avviso, l'e2e
  `backup-roundtrip` li confronta al posto dei report (il suo `TODO(CP-15)`). Dettagli: piano 07, §3.2 e §13.
  **In dev**: `0cd910a7e` (16/10 21:35), con B3 (`c374313c0`).
- ✅ **B-14 · La pagina di blocco non ha il pulsante del backup** — piccolo; B, 16/10 (docs-writer, B6a-bis). **Fatto il
  16/10**: la scheda nella pagina di blocco è entrata col lotto di H (H-12/21, base `0c79932a7`), che ha corretto anche la
  sua frase di `hosting_providers.en.md`; B ha corretto le due della guida (`backup_restore.en.md`: «Make a Backup» e
  «Bring Your LibreFolio Home») nel checkpoint della sera dopo `dbc2324d5`. Il piano 07
  (§3.11) voleva la scheda di scaricamento di B5a (`BackupDownloadCard.svelte`) anche nella pagina di blocco
  (`features/instance/components/InstanceBlockedPage.svelte`, di H); oggi un admin di un'istanza bloccata scarica il
  backup solo dall'API, dalla CLI o dal pannello (le rotte sono in `ALLOWED_WHEN_BLOCKED`), e la doc lo dice
  (`hosting_providers`, `backup_restore`). Proposta: in B5, con il permesso di H sulla pagina. Dettagli: piano 07, §13,
  «B6a-bis». **In corso, H** (coordinatore, 16/10 alle 05:52): la pagina di blocco monta `BackupDownloadCard.svelte`
  (senza props) sotto l'avviso, in una sezione sua, con un `ToastContainer`. Si chiude quando entra il lotto di H; poi B
  aggiorna le due frasi della doc («no backup button yet» in `backup_restore.en.md`, «the block page has no button for
  it yet» in `hosting_providers.en.md`).
- ✅ **B-15 · Un 413 di un proxy davanti a LibreFolio, sul caricamento di un archivio, dà un messaggio generico** — minimo;
  B, 16/10 (docs-writer, B5b). Un proxy (nginx `client_max_body_size`, Fly, un CDN) che rifiuta il corpo con un 413
  senza il `code` di LibreFolio fa dire alla scheda «The server answered with an error: the server's log has the
  cause.», ma il log di LibreFolio non ne sa niente. Proposta: un 413 senza codice → un codice suo della scheda
  (`proxy_too_large`, «A proxy in front of LibreFolio refused an archive this large: ask whoever runs it, or restore
  from the command line»), con la chiave nelle quattro lingue e un caso in `restoreFlow.test.ts`. La guida
  (`backup_restore.en.md`, «What Settings › Backup Says») descrive già il caso. Dettagli: piano 07, §13, «B5b».
  ⏸️ **Parcheggiata il 19/10**: rossi e doc scritti il 17/10 sera, mai eseguiti, poi il fermo del developer; ora in
  una patch della sessione di B (`files/parked/b15-b8-reds-docs-on-739bf08e0.patch`). Riprende col via del
  coordinatore, dopo la lettura del developer. Dettagli: piano 07, «B-15 + B-8».
  ✅ **Fatta il 19/10**: un 413 senza codice di LibreFolio, al caricamento di un archivio, è `proxy_too_large`, con la
  frase del contratto in 4 lingue. Dettagli: piano 07, «B-15 + B-8 — la ripresa».
- ✅ **B-16 · Un server che dopo «Restore and restart» non si ferma lascia l'overlay in attesa senza fine** — piccolo; B,
  16/10 (docs-writer, B5b). Se la richiesta di riavvio è accettata ma il server non scende (segnale perso, un processo
  che non esce), la sonda lo vede sempre su, lo stato resta `pending`, e la pagina continua a dire «LibreFolio is
  restarting» senza il suggerimento «has not come back yet», che parte solo col server giù. La guida lo spiega (riga
  di risoluzione dei problemi: riavvialo a mano). Proposta: server su e stato `pending` oltre `slowAfterMs` → un
  messaggio suo nell'overlay («LibreFolio did not stop: restart it yourself»), deciso con il coordinatore (cambia un
  caso fissato di `restoreFlow.test.ts`). Dettagli: piano 07, §13, «B5b».

  ✅ **Fatto il 17/10** (checkpoint delle 06:35), con la strada (B) decisa dal coordinatore. Col server mai sceso e il
  ripristino ancora in attesa un minuto dopo la richiesta (`slowAfterMs`, contato dalla risposta che accetta il
  riavvio, dopo una lettura dell'esito), l'overlay dice «LibreFolio has not stopped. If it does not restart by itself,
  restart it yourself: the restore is applied at that start.» (`restart-not-stopped`) e offre **Back to Backup**. Le
  sonde continuano finché non lo si preme, e un arresto tardivo procede come prima. Il controller ha il flag
  `notStopping`, che si azzera dove si azzera `slow` e col server visto giù. Ruoli e pulsante sono quelli che
  esistevano già. La guida aggiorna la riga dei problemi.
  **In dev**: `3896cb6b3` (17/10 06:31), merge di `916225c53`.
- ✅ **B-17 · «Cancel the restore» della scheda non toglie la copia di un ripristino confermato dalla CLI** — minimo; B,
  16/10 (docs-writer, B5b). **Fatto il 16/10 in B5c** (checkpoint delle 18:22): `DELETE /backup/restore/pending` chiama
  `cancel_restore(drop_copy=True)` come la CLI, e la copia si toglie dentro il lock del ripristino; la scheda non chiama
  più `dropCheck`. Testo d'origine: la scheda, dopo un annullamento accettato, toglie la copia con `DELETE /stage/{stage_id}`;
  la CLI non tiene il record della prova, quindi per un ripristino confermato da riga di comando la richiesta è
  rifiutata (ignorata) e la copia resta in `.restore/stage/` finché una prova avviata dalla scheda non la trova più
  vecchia di 24 ore; dopo l'annullamento dalla scheda, `backup pending --cancel` non la raggiunge più. La guida dice di
  annullarlo dalla riga di comando. Proposta: `DELETE /backup/restore/pending` chiama `cancel_restore(drop_copy=True)`
  come la CLI (una riga in `api/v1/backup/restore.py:309`, due casi di `test_backup_restore_apply.py`, la riga di
  `security.md`), e la scheda smette di chiamare `dropCheck` (i suoi casi tornano «nessuna cancellazione della
  copia»). Da fare insieme al biglietto dell'esito (B5c, se scelto): toccano la stessa API. Dettagli: piano 07, §13,
  «B5b».
  **In dev**: `0cd910a7e` (16/10 21:35), con B5c.
- ✅ **B-18 · `restore --instance-key-file`: ricifrare i segreti di un archivio in chiaro con la copia della chiave
  vecchia** — piccolo; B, 16/10 (analisi di B4, d'accordo il coordinatore: backlog). Un archivio in chiaro non porta la
  chiave d'istanza, e i segreti dei plugin restano «impostati ma illeggibili». Chi ha conservato la chiave vecchia (la
  copia di `secrets/instance.key`, o il vecchio `LIBREFOLIO_INSTANCE_KEY`, per esempio consegnato dal pannello all'uscita
  dal cloud) potrebbe darla alla CLI, che la usa per il rekey come quella di un backup sicuro (`derive_key_from`, la
  strada già descritta nella docstring di H). Solo CLI, mai un upload della chiave dalla UI. Dettagli: piano 07, «B4 —
  analisi sulla base nuova».

  ✅ **Fatto il 17/10** (checkpoint delle 10:51).
  - `dev.py backup restore --instance-key-file FILE`, anche con `--dry-run`: il file è letto da root prima del cambio
    di utente e prima della password.
  - `stage_archive(..., instance_key=…)` lo controlla prima di creare qualsiasi cosa (`instance_key_invalid`) e ricifra
    i segreti di un archivio che non porta la sua chiave.
  - D1: vince la chiave dell'archivio, con una riga ℹ️. D2: una riga ⚠️ quando la chiave data non ricifra nulla, e
    un'altra quando la chiave di questa istanza non si può usare.
  - Doc in `cli_tools.en.md`, con una sottosezione nuova, e in `backup_restore.en.md`. Revisione di H al checkpoint.
  Dettagli: piano 07, «B-18».
  - 17/10, 11:52: il cancello G era rosso, perché `instance_key_invalid` mancava in `RestoreErrorCode`. Ora è
    dichiarato, e `api backup-restore` dà 146 passati. Dettagli: piano 07, «B-18, riparazione».
  **In dev**: `5c4d7456a` (17/10 11:00), `7b1911fd6` con B-20; la riparazione del cancello G con `279c1bc1c` (11:52).
- ✅ **B-19 · `backup decrypt` lanciato da root scrive uno zip di root** — minimo; B, 17/10 (docs-writer, B4). Gli altri
  comandi di `dev.py backup` lavorano come il proprietario della cartella dei dati (`_drop_root_privileges`); `decrypt`
  non legge la cartella dei dati, quindi con `docker compose exec` lo zip appartiene a root. La guida lo dice. Proposta:
  se la cartella dei dati esiste, `decrypt` passa al suo proprietario come gli altri; senza, resta l'utente che lo
  lancia (per decifrare su un portatile). Dettagli: piano 07, «B4 — analisi sulla base nuova» e seguenti.

  ✅ **Fatto il 17/10** (checkpoint delle 09:23). Da root, con una cartella dei dati, `decrypt` passa al suo
  proprietario come gli altri comandi, prima di toccare l'archivio, `-o` o di fare domande; legge prima
  `--password-file` (un segreto di root funziona, come per `create`, `inspect`, `restore`). Senza essere root non legge
  l'impostazione della cartella dei dati. Un archivio illeggibile dà `archive_unreadable`, non più `not_an_envelope`.
  **In dev**: `e96158e9b` (17/10 09:24), merge di `20198ffc7`.
- ✅ **B-20 · knip segnala `RESTORE_TICKET_HEADER` come export inutilizzato** — minimo; B, 17/10 (controlli statici di
  B4). L'export è di B5c (`frontend/src/lib/features/backup/backupApi.ts`). Il suo test lo legge con un cast sul modulo,
  scritto quando era ancora rosso, e knip non lo conta come uso. Correzione: il test lo importa per nome. Non è un
  gate: `lint --dead-code` era già rosso prima, per voci di altri. Dettagli: piano 07, «B4 — analisi sulla base nuova»
  e seguenti.

  ✅ **Fatto il 17/10** (checkpoint delle 10:54). Il test importa `RESTORE_TICKET_HEADER` per nome. Vitest 198 su 198;
  knip: «Unused exports» da 20 a 19, e l'unica riga sparita è questa. Dettagli: piano 07, «B-20».
  **In dev**: `5c4d7456a` (17/10 11:00), `7b13e4d43`, con B-18.
- ✅ **B-21 · Le due rotte del ripristino non prendono `ProfileDefaultError`** — minimo; H tramite il coordinatore, 17/10
  (H-27, dev `bfdc1f72c`). `profile_default()` ora solleva `ProfileDefaultError`, un `TypeError`, quando la tabella dei
  profili dà un valore del tipo sbagliato. `backup_max_upload_mb()` la chiama, e le sue due sole chiamate, in
  `api/v1/backup/restore.py`, prendono solo `BackupConfigError`:
  - `_upload_limit()` (`PUT /restore/upload`) risponderebbe 500 invece del 503 `backup_upload_unavailable`;
  - `_readable_limit_mb()` (`GET /restore/status`) risponderebbe 500 invece di `upload_limit_mb: null`, e la scheda non
    leggerebbe più lo stato del ripristino.

  Correzione: prendere anche `ProfileDefaultError` nei due punti, con un caso per rotta. Si fa dopo l'ingresso di
  H-27 nel ramo di B. Il test di guardia H-17 mette `123`, un intero: resta compatibile. Dettagli: piano 07, «B4
  committato; validazione combinata…».

  ✅ **Fatto il 17/10 in B4b** (checkpoint delle 04:55, commit `964ecf434`): le due rotte prendono anche
  `ProfileDefaultError`: l'upload risponde 503 `backup_upload_unavailable`, lo stato 200 con `upload_limit_mb: null`.
  8 casi in `test_backup_restore.py`, rossi e poi verdi nello slot delle 04:44.
  **In dev**: `c7dd3934a` (17/10 04:50), con B4b.
- ✅ **B-22 · `totals.py` ripete la regola degli importi «testo decimale semplice» di J** — minimo; J tramite il
  coordinatore, 17/10 (J-27). J-27 è già nella base di B: `7336722ad`, entrato con `e221a0544`.
  `ledger_totals._as_amount` (la casa) rifiuta ogni testo che non sia decimale semplice prima di `Decimal()`, con la
  stessa regola (precisione 60). Così `_plain` e `_PLAIN_AMOUNT` in `instance_backup/totals.py` sono un doppione, e anche
  i loro controlli di struttura (righe che non sono una lista, una riga che non è un oggetto) finiscono in un
  `ValueError` di `from_json`. **Decisione di B: si tolgono** («una regola, una casa»). Lo stato resta `absent` in ogni
  caso. Da adattare: i casi di `test_backup_totals.py` che fissano «deciso prima che `from_json` veda il documento»
  diventano «rifiutato da J»; il fixture `j_reads` resta la difesa contro l'espansione nel test. Nel lotto B4b, dopo
  l'ingresso di B4. Dettagli: piano 07, «B4b — le note di E (R13-SEC4) e di J».

  ✅ **Fatto il 17/10 in B4b** (checkpoint delle 04:55, commit `964ecf434`): via `_plain` e `_PLAIN_AMOUNT` da
  `totals.py`: decide `ControlTotals.from_json` di J. Il test capovolto è
  `test_what_is_not_plain_text_in_lines_of_objects_is_refused_by_j_and_absent`.
  **In dev**: `c7dd3934a` (17/10 04:50), con B4b.
- ✅ **B-23 · Dopo un crash restano file in chiaro, e nessuno li toglie all'avvio** — piccolo; E (R13-SEC4, piano 08 in
  dev `110125350`), 17/10, più il punto (c) di B. Oggi la pulizia gira solo quando parte un nuovo controllo
  (`restore_jobs.prune` in `start_check`) o un nuovo backup (`remove_expired_jobs` in `_prepare`):
  - (a) `.restore/stage/<id>/archive.zip`, l'archivio decifrato con la chiave di origine, se il server muore fra la
    decifratura e lo spacchettamento;
  - (b) le cartelle `backups/.decrypt-*` di un `inspect` interrotto: il server non le toglie mai, la CLI solo al prossimo
    `inspect`. Chi sincronizza `backups/` altrove si porta dietro il chiaro;
  - (c) i file di lavoro di un job di backup interrotto, cioè lo zip in chiaro di un backup sicuro e la copia del DB in
    `backups/.jobs/<id>/`: `get_job` segna `backup_interrupted` ma non li toglie.

  Direzione: una pulizia all'avvio di (a), (b) e (c), con le regole della pulizia di B4: solo cartelle vere, mai un link;
  per `.decrypt-*` la regola dell'ora, perché un `inspect` può girare mentre il server parte; lo stato del job resta.
  Tocca la lista condivisa `STARTUP_STEPS` (`app_lifespan.py`, e i passi in `overview.md`): un passo nuovo dopo
  `restore-commit`, o dentro il suo. Lotto B4b. Dettagli: piano 07, «B4b — le note di E (R13-SEC4) e di J».

  ✅ **Fatto il 17/10 in B4b** (checkpoint delle 04:55, commit `964ecf434`): il passo `backup-leftovers` (N66) e il
  modulo `instance_backup/leftovers.py`. La revisione delle 03:58 aggiunge `archive.zip.part`, i link su due livelli e
  `checks_interrupted`; `get_job()` toglie anche i file di lavoro. 44 casi in `test_backup_leftovers.py`.
  **In dev**: `c7dd3934a` (17/10 04:50), con B4b.
- ✅ **B-24 · Il messaggio di `backup decrypt` non dice che lo zip apre anche le chiavi salvate** — minimo; E (R13-SEC4),
  17/10. Oggi dice: «It holds every user's data in clear». Uno zip decifrato di un backup che portava la chiave
  d'istanza contiene anche quella chiave, che apre ogni chiave dei fornitori salvata. Da aggiungere al messaggio e alla
  guida (`admin/backup_restore.en.md`, sezione `backup decrypt`). Lotto B4b.

  ✅ **Fatto il 17/10 in B4b** (checkpoint delle 04:55, commit `964ecf434`): dopo `decrypt` c'è la riga 🔑 quando il
  manifesto annuncia la chiave.
  **In dev**: `c7dd3934a` (17/10 04:50), con B4b.
- ✅ **B-25 · `--password-stdin` su un terminale mostra la password; i campi della creazione hanno `autocomplete="off"`** —
  minimo; E (R13-SEC4), 17/10. `--password-stdin` legge con `sys.stdin.readline()` (`scripts/backup_cli.py:100`) anche
  quando lo standard input è un terminale, e lì la password si vede mentre la si scrive: con `isatty()` va letta con
  `getpass`. Da decidere nell'analisi: alla creazione una o due volte. Nella scheda, i due campi della password di un
  backup sicuro passano a `autocomplete="new-password"`: i gestori delle password ignorano spesso `off` e proporrebbero
  quella dell'account. Lotto B4b.

  ✅ **Fatto il 17/10 in B4b** (checkpoint delle 04:55, commit `964ecf434`): `--password-stdin` a un terminale prende
  la strada di `getpass` (due volte per `create`), e i due campi del backup sicuro sono `new-password`.
  **In dev**: `c7dd3934a` (17/10 04:50), con B4b.
- ✅ **B-26 · Un file della chiave oltre 4096 byte si esporta, poi ogni ripristino lo rifiuta** — minimo; E (R13-SEC4),
  17/10. La creazione legge `secrets/instance.key` con `read_secret_file` (fino a 64 KiB); la lettura dall'archivio si
  ferma a `INSTANCE_KEY_MAX_BYTES` (4096, `archive.py`). Va rifiutato già all'esportazione: chiave non inclusa e avviso
  `instance_key_unusable`, come per le altre chiavi inutilizzabili. Lotto B4b.

  ✅ **Fatto il 17/10 in B4b** (checkpoint delle 04:55, commit `964ecf434`): `exportable_instance_key()` e
  `generated_key_unusable()` usano il limite di 4096 byte in UTF-8 (`INSTANCE_KEY_MAX_BYTES`).
  **In dev**: `c7dd3934a` (17/10 04:50), con B4b.
- ✅ **B-27 · Dopo un ripristino riuscito la scheda Backup non dice nulla** — piccolo; G (G-20) tramite il coordinatore,
  17/10, decisione notturna N67 (la rivede il developer). Dopo un ripristino `committed` la pagina va al login senza
  dire niente (FBKP-107), e al rientro la scheda tace: `restore-last-result` c'è solo per `rolled_back`
  (`RestoreCard.svelte:64`). Si aggiunge l'avviso «applied on {date}, backup of {date} (LibreFolio {version}),
  confirmed by {user}», in un ruolo info. Resta fino al ripristino seguente, come `rolled_back`. Solo frontend:
  `GET /restore/status` dà già `finished_at`, `backup_created_at`, `backup_app_version` e `confirmed_by`. Con i casi
  Vitest, una chiave i18n in 4 lingue, un E2E su uno stato finto (come FBKP-103, e dà la foto a G) e una riga nella
  guida. Dopo B4b. Dettagli: piano 07, «B4b — le note di E (R13-SEC4) e di J».

  ✅ **Chiusa il 17/10, non da fare** (coordinatore, 05:00): N67 è ritirato e resta la decisione P8 del developer
  (16/10, 11:25): un ripristino riuscito non dice nulla, «se ha funzionato lo vedi». Nell'elenco del developer va solo
  come nota. L'analisi è pronta nel piano 07, «B-27», se un giorno servisse.
- ✅ **B-28 · I trigger del DB caricato girano nel processo del server, senza limite di tempo** — basso (un DoS fuori dal
  perimetro: serve un admin che carichi l'archivio); E (revisione di sicurezza di B3) tramite il coordinatore, 17/10.
  Il coordinatore lo chiamava «B-19», ma quell'ID è già usato: un DB caricato può portare trigger propri, e scattano
  quando il controllo scrive sulla copia. Succede con l'`alembic upgrade` di un archivio più vecchio, con le correzioni
  post-migrazione (`_post_migration_fixes`, `staging.py`) e col rekey dei segreti. Una CTE ricorsiva in un trigger:
  - tiene `.stage.lock` fino al riavvio, quindi nessun altro controllo parte;
  - sul profilo `managed` tiene l'istanza sveglia, perché `backup_in_progress` vale vero.

  Direzione: un limite di tempo sulle scritture della copia (`set_progress_handler` di sqlite3, o un sottoprocesso con
  un tempo massimo), più `PRAGMA trusted_schema=OFF` sulle connessioni della copia. Dopo B4. Dettagli: piano 07, «B-27».

  ✅ **Fatto il 17/10** (checkpoint delle 05:50, commit `9403ecda0`), con la strada (B) decisa dal coordinatore. Subito
  dopo lo spacchettamento, il controllo legge `sqlite_master` in sola lettura e classifica ogni oggetto dal suo testo
  SQL. Un trigger, una vista o una tabella virtuale, che LibreFolio non crea mai, fanno rifiutare l'archivio con
  `database_foreign_objects` prima di ogni altro accesso; uno schema che SQLite non legge dà `database_damaged`. In
  più `trusted_schema=OFF` sulle cinque connessioni di B alla copia. L'`alembic upgrade` girava già in un processo a
  sé, col suo tempo massimo.
  **In dev**: `01f36e79d` (17/10 05:48).
- ✅ **B-29 · Un totale della copia che J non rilegge fa fallire tutto il controllo** — basso (robustezza, solo admin); E
  (revisione R13-SEC2) tramite il coordinatore, 17/10. In `compare_totals` (`instance_backup/totals.py`)
  `ControlTotals.from_json(current)` sta fuori dal `try`. Se i dati della copia danno un importo che il lettore di J
  rifiuta (oltre 60 cifre, J-27), il `ValueError` esce, e il controllo finisce con `stage_failed` invece di dire i
  totali `unreadable`. Correzione: leggere `current` dentro un `try` che risponde `unreadable`, con un WARNING come per
  i totali registrati. Dettagli: piano 07, «B-29».

  ✅ **Fatto il 17/10** (checkpoint delle 06:10, commit `c96861834`): `current` si legge dentro un `try`; un documento
  che J rifiuta dà `unreadable` col WARNING «The control totals of the copy cannot be read: they are not compared»,
  mai un controllo fallito. Test: 5 casi in `test_backup_totals.py`, più uno di staging (un registro con una quantità
  esatta 1e70). Nota di TA-B sulla gravità: il crollo richiedeva un manifesto riscritto (i totali registrati che J
  legge accanto a una copia che J non rilegge), perché un backup vero registra la stessa riga, e allora vince
  `absent`.
  **In dev**: `006773c99` (17/10 06:08).
- ✅ **B-30 · Un disco pieno negli avvii brevi del backup e del ripristino risponde col codice sbagliato, o senza codice**
  — piccolo; TA-B, 17/10 (B-9, rilettura delle etichette di `test_backup_restore.py`), allargato dall'analisi del 17/10.
  Annotato per la cartella degli upload. `jobs._out_of_space` copre le fasi lunghe, non gli avvii brevi:
  - la cartella degli upload e la fine dell'upload (`fsync`/`close`, dove NFS e le quote segnalano il disco pieno)
    danno 500 `backup_upload_failed`, non 507;
  - l'avvio di un controllo (`POST /restore/stage`) lascia uscire ogni `OSError` come 500 senza codice;
  - l'avvio di un backup (scheda e pannello) dà 500 `backup_failed`, non `backup_no_space`.
  Cura decisa dal coordinatore (17/10, 07:18), ambito 1+2+3+5: 507 `backup_no_space` per un disco pieno in tutti e
  quattro; all'avvio del controllo, ogni altro `OSError` → 500 `stage_failed` con una riga nel log. Solo backend, con
  codici e chiavi che esistono già. Dettagli: piano 07, «B-30».

  ✅ **Fatto il 17/10** (checkpoint delle 08:00). Un disco pieno (ENOSPC o EDQUOT, anche fra le cause) risponde 507
  `backup_no_space` alla cartella e alla fine dell'upload e all'avvio del backup (scheda e pannello), e 507 `no_space`
  (il codice del controllo) all'avvio del controllo; lì ogni altro `OSError` dà 500 `stage_failed` con una riga nel log,
  mai più il 500 senza codice. `jobs.out_of_space` è pubblica. Corretta anche la doppia `close` di `UploadWriter.finish()`
  (trovata da TA-B). Test: 21 rossi API e 18 nei servizi, poi tutti verdi; 4 guardie Vitest.
  **In dev**: `af9b7f482` (17/10 08:01), merge di `116df6800`.
- ✅ **B-31 · Conferma, annullamento e riavvio di un ripristino: un guasto del disco senza codice o senza messaggio** —
  basso; B, 17/10 (analisi di B-30). `POST /restore/stage/{id}/confirm` e `DELETE /restore/pending` lasciano uscire un
  `OSError` come 500 senza codice; `restore_restart_failed` (il biglietto del riavvio non scritto) ha un codice ma
  nessun messaggio nella UI (fuori da `ERROR_KEYS`: dice «unexpected») né una riga nella guida. Cura: un 500 con un
  codice e un messaggio suo per ciascuno (3 chiavi × 4 lingue, `ERROR_KEYS`, l'elenco §5 di `restoreI18n.test.ts`) e
  507 `backup_no_space` per un disco pieno alla conferma. Lotto separato, dopo B-30 (coordinatore, 07:18). Dettagli:
  piano 07, «B-30» (punti 4, 6, 7).

  ✅ **Fatto il 17/10** (checkpoint delle 08:46). Conferma: 507 `backup_no_space` su un disco pieno, 500
  `restore_confirm_failed` altrimenti, nulla confermato. Annullamento: 500 `restore_cancel_failed` prima di togliere il
  ripristino, che resta in attesa; una copia che non si toglie dopo → 204 e un WARNING (anche da CLI). Riavvio: il suo
  500 ora ha il messaggio e un test. Tre messaggi × 4 lingue in `ERROR_KEYS`. Test: 17 rossi API, 2 nei servizi, 6
  Vitest, poi tutti verdi.
  **In dev**: `997c358f5` (17/10 08:46), merge di `e14221a04`.
- ✅ **B-32 · Dopo un annullamento rifiutato: la scheda, la CLI e uno stato illeggibile** — basso; B, 17/10 (B-31: TA-F,
  TA-B, il docs-writer).
  - In `restoreFlow.cancelPending()` la riga `state = 'pending'` è morta (`#fail` mette subito `failed`): un
    annullamento rifiutato finisce sulla schermata di errore con «Try again», non sul blocco del ripristino in attesa con
    l'errore accanto, come per il riavvio. Da decidere quale delle due.
  - `dev.py backup pending --cancel` prende solo `RestoreNotPendingError`: un `OSError` prima della rimozione dello stato
    finisce in un traceback; e la riga ✅ dice «with its copy» anche quando la copia è rimasta (B-31 la registra con un
    WARNING).
  - Uno stato illeggibile (EACCES, EIO) fa dire a `_read_state` `None`: l'annullamento risponde 404 «not pending», lo
    stato del ripristino dice «none», mentre un ripristino può essere ancora in attesa.
  Dettagli: piano 07, «B-31».

  ✅ **Fatto il 17/10** (checkpoint delle 10:29).
  - Un annullamento rifiutato resta sul ripristino in attesa, con l'errore accanto, Riavvia e Annulla di nuovo.
  - `pending --cancel`:
    - un `OSError` → ❌ `restore_cancel_failed`, uscita 1, senza traceback;
    - una copia rimasta → ✅ senza «with its copy», più ⚠️. Lo dice un `lstat`: un errore conta come «ancora lì».
  - Uno stato che il file system non lascia leggere → `restore_state_unreadable`:
    - 500 su stato, annullamento, riavvio e conferma; la conferma non scrive sopra;
    - ❌ con uscita 1 in `pending`, `pending --cancel` e `restore`.
    Un link o un contenuto non valido restano «none»; l'avvio, l'esito e la pulizia leggono come prima.
  - Commenti «Settings › Administration › Backup». Dettagli: piano 07, «B-32».
  **In dev**: `7af21a5c1` (17/10 10:28), merge di `ca1343d6d`.
- **B-33 · Uno stato illeggibile all'avvio e nella pulizia** — basso; B, 17/10 (B-32, residuo dichiarato; il
  coordinatore lo ha messo nella lista del developer).
  - Un avvio che non riesce a leggere lo stato del ripristino registra l'errore e va avanti coi dati come sono, anche se
    quello stato era `applying` o `applied` (dati scambiati a metà). Fermare l'avvio (fail closed) o servire (com'è
    oggi) è una **decisione del developer**.
  - `protected_stage` legge «nessuno»: con uno stato illeggibile la pulizia (`prune`, `remove_check`) può togliere la
    copia di un ripristino forse ancora in attesa; l'avvio dopo direbbe `stage_missing`.
  - Un test per la FIFO al posto dello stato ora si può scrivere, con un timeout: la lettura `lstat`-prima la ignora,
    prima restava appesa.
  - **La pagina** (17/10, trovato in B-41): con uno stato illeggibile dopo un riavvio, il ripiego su `GET /status`
    riceve 500, che `readStatusWithSession` (`backupApi.ts`) prende per «server giù». L'overlay interroga ogni secondo
    per sempre: due righe d'errore a ogni giro col biglietto, una dopo la sua ora. E non dice perché. Va con la stessa
    decisione.
  Dettagli: piano 07, «B-32».
- ✅ **B-34 · `--instance-key-file`: la causa giusta quando questa istanza non ha ancora una chiave, e due frasi della doc**
  — basso; B, 17/10 (revisione di H su B-18: LOW-1 e due appunti; piano di H §14 «Review di B-18»).
  - **LOW-1**: su un'istanza senza chiave (dal cloud a un server nuovo), se la verifica non può crearla (`secrets/` non
    scrivibile) tutto resta illeggibile. Però `instance_key_status()` dice ancora `not_created` con `problem=None`, e la
    riga ⚠️ di D2 accusa la chiave data. Cura: in `_print_given_key`, il ramo dell'eccezione anche per
    `source == "not_created"`, più un caso accanto a c7.
  - **Doc**: `cli_tools` deve dire che un vecchio `LIBREFOLIO_INSTANCE_KEY` vale «as written, spaces included»;
    `backup_restore` deve aggiungere `chmod 600` sul file della chiave vecchia mentre sta in `backups/`.
  Niente codice prima del via del coordinatore. Dettagli: piano 07, «B-18».

  ✅ **Fatto il 17/10** (checkpoint delle 14:10).
  - `_print_given_key` prende il ramo dell'eccezione anche con `not_created`: «`<path>`: there is no instance key yet,
    and it could not be created». Un test accanto a c7.
  - `cli_tools`: «as written in the variable, spaces included», e la riga dell'eccezione.
  - Il `chmod 600`: dopo B-38 la chiave non passa più da `backups/`; va sul file `old-instance.key` dell'host
    (`backup_restore` l.320).
  Dettagli: piano 07, «B-34».
  **In dev**: `202849800` (17/10 14:10), merge di `731337a5a`.
- ✅ **B-35 · Il limite di caricamento non limita quanto un archivio scompatta** — 🟡 MEDIO nel profilo ospitato, basso
  nel self-hosted; B, 17/10 (BZ parte 1, F3).
  - `staging.space_needed` e `_check_space` (`staging.py:462-470`) confrontano le dimensioni dichiarate dal manifest
    (uguali alle intestazioni dello zip) soltanto con il disco libero.
  - `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` (500 MB nel cloud) limita lo zip, non quello che se ne scompatta. Un deflate da
    500 MB può dichiarare e scrivere centinaia di GB durante la verifica.
  - Il danno: un DoS dell'istanza stessa su un volume isolato; dell'host dove i volumi condividono un disco senza quote.
  - Cura: una soglia sul totale dichiarato, controllata prima di `_check_space`: `backup_too_large` con il limite.
    - La forma è una variabile `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` (senza valore di default, così il self-hosted non
      cambia) oppure K volte il limite di caricamento: **da decidere**.
    - Test: un manifest oltre la soglia è rifiutato prima di scrivere un byte.

  ✅ **Fatto il 17/10** (checkpoint delle 12:36).
  - `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`: senza default nel self-hosted; nel profilo ospitato 8 volte il limite di
    caricamento (decisione N82, K misurato); un valore esplicito vince.
  - Il controllo dello staging viene prima dello spazio (`unpacked_too_large`). L'avvio della verifica risponde 503
    `backup_restore_unavailable`, e la CLI segue la stessa regola.
  - Controllo della configurazione `backup.restore_limit`. Dettagli: piano 07, «B-35».
  **In dev**: `9fafc79b5` (17/10 12:42), merge di `d7efb5805`; le correzioni dopo la revisione di H con
  `c7f414827` (13:15).
- ✅ **B-36 · Nomi di tabella non quotati nei conteggi delle correzioni post-migrazione** — ⚪ basso; BZ parte 1, F1.
  - `post_migration._row_counts` (`backend/app/db/post_migration/__init__.py:70-72`) costruisce
    `f'SELECT count(*) FROM "{name}"'` senza raddoppiare `"`. B-28 lascia passare tabelle con qualsiasi nome.
  - Con una correzione da applicare, il nome di un archivio ostile rompe la verifica (`stage_failed`). Su un database
    ripristinato, rompe un avvio successivo in cui una correzione si applica.
  - sqlite3 esegue un solo statement e non carica estensioni: nessuna fuga dalla copia.
  - Cura: quotare come `snapshot._quoted` (oggi `snapshot._identifier`, dopo la nota di H). Test: una tabella `x"y`
    con una correzione pendente.
  - **Il modulo non è di B**: passa dal coordinatore.
  ✅ **Fatto il 17/10** con B-37 (checkpoint delle 13:33). **In dev**: `d1976bca8` (17/10 13:33), merge di `05d1dc76a`.
- ✅ **B-37 · `trusted_schema` resta acceso su due connessioni alla copia** — ⚪ basso, difesa in profondità; BZ parte 1, F2.
  - Le connessioni sono quella delle correzioni post-migrazione (`PM:211`) e il motore di Alembic su `-x sqlalchemy.url`.
    Sono le uniche alla copia senza `PRAGMA trusted_schema=OFF`.
  - Dopo B-28 restano solo tabelle e indici. La connessione `sqlite3` delle correzioni non registra funzioni, il
    motore di Alembic sì: SQLAlchemy (dialetto pysqlite, 2.0.52) registra `regexp` e `floor` in Python a ogni
    connessione. Senza `trusted_schema=OFF` un `CHECK` dell'archivio potrebbe eseguire `re.search` con un suo pattern
    durante l'upgrade: il listener di `env.py` è una cura vera, non solo coerenza (revisione di H, 17/10).
  - Cura: spegnerlo in entrambe. **Proprietari fuori da B** (post_migration, `env.py`).
  ✅ **Fatto il 17/10** (B-36 + B-37, checkpoint delle 13:33), con il permesso del coordinatore sui due file.
  - `_row_counts` quota i nomi raddoppiando `"`.
  - `run_post_migration_fixes` spegne `trusted_schema` per primo; `env.py` lo fa con un listener `connect`, per ogni URL.
  Dettagli: piano 07, «B-36 + B-37».
  **In dev**: `d1976bca8` (17/10 13:33), merge di `05d1dc76a`, con B-36.
- ✅ **B-38 · La CLI da root legge i file della password e della chiave attraverso link e FIFO** — ⚪ basso, rafforzamento;
  BZ parte 1, F4.
  - `read_secret_file` apre con `path.open("rb")`.
  - La guida di B-18 suggerisce `LibreFolio-data/backups/` per la chiave vecchia, una cartella dell'utente del server.
    Quell'utente può scambiare il file con un link a un file di root (letto da root, usato come chiave, mai stampato) o
    con una FIFO (il comando si blocca). Per farlo deve essere già ostile, e possiede già tutti i dati.
  - Cura:
    - nella CLI, per i file letti da root: `O_NOFOLLOW|O_NONBLOCK` e `fstat` regolare (o un'opzione di
      `read_secret_file`, che è di H);
    - nella guida, la chiave fuori dalla cartella dei dati.
    Test: un link o una FIFO come `--instance-key-file` da root → ❌, niente letto.
  ✅ **Fatto il 17/10** (B-38, checkpoint delle 13:58), con la rifinitura approvata dal coordinatore.
  - Ovunque, un file regolare aperto con `O_NONBLOCK`.
  - Da root, nessun componente del percorso è un link dentro la cartella dei dati; fuori si seguono (Kubernetes).
  - La guida usa `/root` del container.
  - La corsa fra le due aperture è nella riga H-47 di H. Dettagli: piano 07, «B-38».
  **In dev**: `c2a09b960` (17/10 13:57), merge di `1ed071c2f`.
- ✅ **B-39 · Formule nei CSV esportati** — ⚪ basso; BZ parte 1, F5.
  - Ogni utente può scrivere le `notes` degli eventi di un asset (`POST /assets/events`), e ogni utente può esportarle
    in CSV (`GET /backup/asset/{id}/events`, `series_export.stream_rows_as_csv`).
  - Una nota che comincia con `=`, `+`, `-`, `@`, tab o CR diventa una formula quando un altro utente apre il file in un
    foglio di calcolo.
  - Cura: un `'` davanti ai valori di testo che cominciano così, mai ai numeri (`-1.5` resta). Test: `=1+1` diventa
    `'=1+1`.
  ✅ **Fatto il 17/10** (B-39). All'export, un testo come una formula (`'*[=+\-@\t\r]` all'inizio, mai un numero
  puro) riceve un `'` in più; l'import degli eventi toglie esattamente quell'apostrofo dalle `notes`, quindi il ritorno
  è esatto. Dettagli: piano 07, «B-39».
  **In dev**: `25d00f192` (17/10 13:08), merge di `c8fc32bfa`.
- ✅ **B-40 · La tabella «What It Lists» della scheda Sicurezza non ha i due controlli di B-9** — minimo; H con H-46, 17/10.
  `admin/settings.en.md` («What It Lists») non elenca `backup.panel_token` e `backup.upload_limit`, e la pagina dice che
  i risultati seguono l'ordine della tabella. Le due righe vanno nel prossimo lotto, nel loro posto dell'ordine.
  ✅ **Fatto il 17/10** in B-35 (checkpoint delle 12:36): le tre righe di B (`backup.panel_token`,
  `backup.upload_limit`, `backup.restore_limit`) fra il «Log level» della piattaforma e il primo controllo di A.
  **In dev**: `9fafc79b5` (17/10 12:42), con B-35.
- ✅ **B-41 · `/restore/outcome` registra un errore a ogni chiamata quando lo stato è illeggibile** — basso; E, R13-SEC9,
  17/10.
  - Con uno stato del ripristino illeggibile, la rotta anonima `GET /backup/restore/outcome` legge lo stato prima del
    biglietto, e la lettura indulgente registra un errore a ogni chiamata. Un client anonimo può ripeterlo.
  - È rumore, com'era prima di B-32.
  - Cura economica: la rotta controlla prima il biglietto (forma, registro, impronta, scadenza) e legge lo stato
    soltanto per un biglietto valido; oppure un solo log per stato, o a livello debug.
  Dopo la 1.3, se non costa poco.

  ✅ **Fatto il 17/10** (checkpoint delle 14:56), nella 1.3 (coordinatore).
  - La rotta passa a `read_outcome` il modo di leggere lo stato, chiamato una volta e solo per il biglietto di un
    riavvio non scaduto. Chi non ha quel biglietto non fa più leggere lo stato, né registrare l'errore.
  - Il titolare del biglietto resta com'era (guardia b5).
  Dettagli: piano 07, «B-41 + B-42».
  **In dev**: `d46113236` (17/10 14:54), il codice in `299c19e2b`.
- ✅ **B-42 · Un file del biglietto dell'esito rotto registra un errore a ogni chiamata anonima** — basso; B, 17/10
  (trovato in B-41).
  - Ogni biglietto ben formato (43 caratteri URL-safe, senza sessione) arriva a `outcome._read_record`. Un file del
    biglietto illeggibile, un link, troppo grande o non valido registra un errore a ogni chiamata.
  - Cura: un errore la prima volta per cartella dati, poi `debug` finché dura lo stesso errore; di nuovo dopo che il file
    è stato scritto, tolto o letto, o se fallisce in altro modo.
  Dentro B-41 (coordinatore, 17/10). Dettagli: piano 07, «B-41 + B-42».

  ✅ **Fatto il 17/10** (checkpoint delle 14:56).
  - `outcome._report`: un errore la prima volta per cartella dati e processo, poi `debug` finché dura lo stesso errore.
  - `_forget` lo dimentica quando il file viene scritto, tolto, trovato mancante o letto.
  **In dev**: `d46113236` (17/10 14:54), con B-41.
- ✅ **B-43 · Una funzione che il lettore non ha, nello schema dell'archivio, ferma la verifica con un errore grezzo** —
  basso; H, 17/10 (H-51, revisione; misurato da B su SQLite 3.54.0).
  - B-28 rifiuta trigger, viste e tabelle virtuali per tipo, ma non legge le espressioni. Un'espressione di un indice o
    una colonna generata che chiama una funzione sconosciuta fanno fallire `integrity_check` anche in sola lettura: la
    verifica si ferma in `describe_database()`.
  - Un `CHECK` così passa invece la descrizione, perché in sola lettura SQLite salta i vincoli `CHECK`. Fallisce al primo
    `integrity_check` in lettura e scrittura, quello delle correzioni post-migrazione.
  - In tutti e due i casi esce un `sqlite3.OperationalError` grezzo: la verifica dell'app dice `stage_failed`, e
    `dev.py backup restore` finisce con un traceback.
  - Cura: in `_stage`, ogni errore `sqlite3` (non un `ProgrammingError`) mentre si legge o si controlla il database della
    copia diventa `database_damaged`. Nel log vanno solo la classe e il nome dell'errore di SQLite, mai la funzione, che
    è testo dell'archivio. Rossi prima.
  - **Parte 1, dentro B-43** (coordinatore, 16:25; trovata da DW-B43, misurata da B): da H-51 le connessioni del server
    registrano `regexp` e `floor` di SQLAlchemy e rileggono lo schema con `trusted_schema` spento. Uno schema che li
    chiama in un indice o in una colonna generata passa tutta la verifica, poi ogni connessione del server fallisce
    («unsafe use of …»), e il primo avvio dopo il ripristino cade. Cura: `_refuse_foreign_objects()` legge lo schema con
    i due nomi registrati come segnaposto, mai eseguiti.
  Dettagli: piano 07, «B-43 + B-44».

  ✅ **Fatto il 17/10** (checkpoint delle 16:45).
  - Ogni errore `sqlite3` della fase del database diventa `database_damaged`, con un solo avviso (classe e
    `sqlite_errorname`).
  - Lo schema si legge con i segnaposto di `regexp` e `floor`.
  - Il resto in B-45 (CHECK e DEFAULT) e B-46 (stderr dell'upgrade).
  **In dev**: `fc4d5eab4` (17/10 16:41), il codice in `7c8eb56c1`.
- ✅ **B-44 · I testi su `trusted_schema` dell'upgrade dopo H-51** — minimo, testo; H, 17/10 (H-51).
  - La docstring di `_schema_untrusted` in `env.py` dice «before anything else». Il listener di classe di
    `db/session.py`, che i suoi import caricano, gira però prima, e il dialetto registra `regexp` e `floor` dopo di lui.
  - Da H-51 il listener di classe spegne `trusted_schema` per primo e chiude con `writable_schema=RESET`.
  - Da allineare a `security.md#trusted-schema-server`: la docstring e il punto «`trusted_schema` off on every connection
    to the copy». Nello stesso checkpoint di B-43 (coordinatore).
  Dettagli: piano 07, «B-43 + B-44».

  ✅ **Fatto il 17/10** (checkpoint delle 16:45): la docstring di `_schema_untrusted` e il punto di `security.md`
  dicono l'ordine vero (listener di classe, dialetto, `_schema_untrusted`).
  **In dev**: `fc4d5eab4` (17/10 16:41), il testo in `a7afc2af6`.
- **B-45 · Un `CHECK` o un `DEFAULT` dell'archivio che chiama `regexp` o `floor` passa la verifica, poi rompe le
  scritture su quella tabella** — basso, dopo la 1.3; B, 17/10 (parte 2 della scoperta di DW-B43; H e il developer
  decidono).
  - SQLite risolve le funzioni di un `CHECK` o di un `DEFAULT` solo quando servono. Così la lettura dello schema con i
    segnaposto di B-43 non li vede. Su SQLite 3.54 `floor()` esiste anche senza SQLAlchemy, quindi un `CHECK` su `floor`
    passa anche il controllo d'integrità in lettura e scrittura.
  - Dopo il ripristino, da H-51, le scritture che li usano falliscono («unsafe use of …»): niente codice dell'archivio
    viene eseguito, ma quella tabella resta in parte inutilizzabile.
  - Cura possibile, più grande: confrontare l'SQL di ogni tabella e indice con lo schema di LibreFolio alla sua
    revisione (un elenco di ciò che è ammesso, invece del solo tipo di oggetto di B-28).
  Dettagli: piano 07, «B-43 + B-44».
- **B-46 · Il log dell'upgrade di una verifica contiene testo dell'archivio** — basso, dopo la 1.3; B, 17/10 (DW-B43).
  - `_upgrade()` registra `stderr=result.stderr[-4000:]` di Alembic. Il traceback porta il messaggio di SQLite, con nomi
    di oggetti e di funzioni dell'archivio. B-28 e B-43 tengono invece fuori dal log ogni testo dell'archivio.
  - È precedente a B-43. Da decidere: tenerlo, perché serve a capire un upgrade fallito di un archivio vero, o ridurlo
    alla classe dell'ultima eccezione.
  Dettagli: piano 07, «B-43 + B-44».
- **B-47 · Nel Bulk, un focus e un blur sulla cassa del Form fanno chiedere di scartare** — minimo, chiarezza; B,
  17/10 (W-B64 + W-B65, dalla lettura del codice; area di W).
  - Le somme tornano dall'API con almeno 6 decimali (`READ_MIN_SCALE`, `db/real_decimal.py`: `0.010000`). Il Bulk le
    tiene così, e `CompactCashCell` le mostra formattate (`0.01`). Al blur, però, emette sempre il valore formattato
    (`handleBlur` → `emit`) e `setCash` del Form lo prende senza confronto. Così un «Applica» dopo un focus sulla cassa,
    senza cambiare nulla, riscrive la riga come `0.01`, e la guardia della chiusura (`serializeOps`, che confronta il
    testo) chiede di scartare. Precedente a W-B65, che ha tolto le altre due cause (il segno, il `null` del
    suggerimento WAC).
  - Cura possibile: `CompactCashCell` emette al blur solo se il valore cambia (`exactDecimalEqual` con quello
    ricevuto), oppure la chiave della guardia legge i decimali per valore e non per testo.
  - Nello stesso giro: l'ingresso dell'import (`txCreateItemToPendingOp`) passa ancora la cassa da `Number`, e
    `isDraftReadyForValidation` legge `amount === '0'`.
  Dettagli: piano 07, «W-B64 + W-B65 (per W)».
- **B-48 · Il Form accetta una quantità che il backend rifiuta per le cifre significative** — minimo, chiarezza; B,
  17/10 (W-B64, nota del test-author; area di W).
  - Con W-B64 il Form tiene 15 cifre intere e 10 decimali, ma il backend ne tiene al massimo 15 significative in tutto
    (`REAL_SIGNIFICANT_DIGITS`). `999999999999999.5` passa il Form e si ferma solo alla validazione
    (`significantDigitsExceeded`, con un messaggio chiaro). Era già così a 12 + 10.
  - Un commento vecchio in `frontend/e2e/transactions/tx-bulk-promote-cost-basis.spec.ts` dice ancora «the form
    (12 integer digits, 6 decimals)».
  Dettagli: piano 07, «W-B64 + W-B65 (per W)».
- ✅ **B-49 · Un testo non UTF-8 nei dati di un backup passa la verifica del ripristino** (fatta il 17/10 da B,
  checkpoint delle 21:26: la verifica lo rifiuta, `database_damaged`, prima dell'upgrade) — basso, da decidere dopo
  W-B65; E, 17/10 (RNW-109 e la barriera SCA-036 di E; la decisione è di B).
  - E l'ha trovato in 4 posti: un valore TEXT con byte non UTF-8 passa la verifica su copia. `integrity_check`, i
    conteggi e i totali non leggono quei testi.
  - Dopo il ripristino, molto probabilmente rompe le letture del server di quelle righe: pysqlite lancia alla lettura
    («Could not decode to UTF-8 column …»), come prova la barriera SCA-036 di E. Non misurato su un server.
  - Un caso è già rifiutato, per caso: il nome utente non UTF-8 di un amministratore attivo. `_administrators` lancia
    `OperationalError`, che l'involucro di B-43 fa diventare `database_damaged`, con un messaggio generico. Le colonne
    che la verifica non legge passano.
  - Da decidere: la verifica rifiuta (un codice suo, senza mai citare il testo, che è dell'archivio) o avvisa come
    E-19b1. Per trovarli serve leggere i testi come byte (`text_factory = bytes`) e provarne la decodifica: un costo
    sui backup grandi.
  - ✅ **Decisione e cura** (17/10): rifiutare (il coordinatore d'accordo). Il passo `_refuse_undecodable_text()` di
    `staging.py` legge ogni testo della copia, prima dell'upgrade, e rifiuta con `database_damaged`; il log ha il solo
    numero di tabelle. RNW-109 di E riscritto da B (ora si aspetta il rifiuto). Il paragrafo di `security.md` l'ho
    aggiunto io dopo l'ingresso di H-52.
  Dettagli: piano 07, «B-49».
  **In dev**: `709dfb1e4` (17/10 21:29), il codice in `0eef55599`; il paragrafo di `security.md` e la descrizione
  del runner con `739bf08e0` (`08d58c6d3`).
- ✅ **B-50 · Uno `state.json` di un job leggibile come JSON ma malformato fa rispondere 500** — minimo, robustezza;
  B, 19/10 (TA-B8-STATE, durante B-8). Precedente a B-8.
  - Uno stato che è JSON ma non un oggetto (`[]`, `null`, `5`) fa alzare `AttributeError` a `BackupJob.from_json`.
    `remove_expired_jobs` non lo prende, e gira a ogni partenza (`_prepare`): ogni nuovo backup, dalla scheda, dal
    pannello o dalla CLI, finisce in un 500.
  - Uno stato senza campi (`{}`) o con tipi sbagliati alza `KeyError` o `TypeError`. `get_job` li lascia passare,
    quindi la lettura di quel job (`GET /backup/instance/jobs/{id}`) è un 500.
  - All'avvio non succede nulla di grave: `sweep_backup_leftovers` registra l'errore e continua.
  - Ci si arriva solo manomettendo `backups/.jobs/<id>/state.json` (l'app lo scrive in modo atomico), o con un disco
    rovinato.
  - Cura possibile: `from_json` trasforma ogni stato malformato in `ValueError`; poi si sceglie cosa risponde
    `get_job` (job non trovato, o fallito).
  - B-8 ha già allineato `_running_job` agli altri lettori (`TypeError` e `KeyError`): un 409 non diventa un 500.
  Dettagli: piano 07, «B-15 + B-8 — la ripresa».
  ✅ **Fatta il 20/10** (via del coordinatore alle 09:06, con il perimetro approvato):
  - uno stato di job illeggibile è «non trovato»: un documento che non è un oggetto JSON, una data senza fuso (trovata
    dalla sonda: faceva fallire ogni avvio), una cartella al suo posto, un file senza permesso di lettura;
  - le rotte rispondono 404 `backup_job_not_found`, mai 500, e `get_job` scrive un avviso con l'id e la classe
    dell'errore, mai il contenuto; un avvio va avanti, e la cartella scade per la sua data;
  - gli altri errori del disco, transitori, restano un 500 che la scheda riprova;
  - nel ripristino uno stato di controllo che non è un oggetto è «nessun controllo», come gli altri illeggibili, e il
    lettore chiude il descrittore che `fdopen` rifiuta (una cartella al posto dello stato ne lasciava aperto uno a
    ogni lettura).
  Dettagli: piano 07, «B-50».
- ✅ **B-51 · La colonna «⚠️» dei risultati di una lettura conta anche le note** — minimo, chiarezza; B, 19/10 (revisione
  di N74; area di W). Precedente a N74.
  - Nella tabella del passo di analisi, la colonna «⚠️» (tooltip «Parser warnings (skipped rows, ambiguous data)»)
    conta tutte le note di un file, anche quelle `info`.
  - Un file Fineco con solo righe non ancora regolate mostra «⚠️ 1», anche se N74 le dice in una nota blu.
  - Nel dettaglio della lettura la sezione s'intitola «Warnings», con le note dentro, ognuna nel suo colore.
  - Cura possibile: contare solo `severity !== 'info'`, oppure due conteggi.
  Dettagli: piano 07, «N74 di W — revisione», R1.
  - ✅ 21/10 (riconciliazione): in `dev_release2` col treno 3 (`00c5d9014`; commit `3cc5bed99`).
- ✅ **B-52 · La regola «solo righe sicure» e i plugin con una colonna di regolamento** — da decidere (W o il
  developer); B, 19/10 (revisione di N74; area di W).
  - La regola 9 della skill `brim-plugin` e della guida dice che una riga «con la data valuta o di regolamento dopo
    oggi» è provvisoria e resta fuori.
  - Directa, Saxo, InvestEngine, Degiro e Disnat hanno una colonna di regolamento, ma datano per operazione e
    importano tutto: il batch le accetta, ma alla lettera della regola le loro righe recenti sarebbero provvisorie.
  - Il generic CSV accetta `settlement_date` o `value_date` come colonna della data: una data oltre domani ora fa
    rifiutare il salvataggio (`dateOutOfRange`); prima di N74 passava fino a un anno.
  - Da chiarire: la regola riguarda solo chi data per valuta (Fineco) o per periodo (Danske), o quei plugin chiedono
    un seguito.
  Dettagli: piano 07, «N74 di W — revisione», F2.
  - ✅ 21/10 (riconciliazione): Fineco e Danske registrano la data dell'operazione, in `dev_release2` col treno 2 (`a79a223cd`; commit `56be23cf7`). Gli altri plugin: W-B88, dopo la 1.3.
- ✅ **B-53 · Altri due lettori di `.restore/` lasciano aperto un descrittore quando il loro file è una cartella** —
  piccolo, robustezza; B, 20/10 (B-50, sonda). Precedente a B-50.
  - `outcome._read_record` (`outcome.py:141`) risponde «nessun esito» e lo registra una volta, come deve, ma ogni
    lettura dell'esito con un biglietto lascia aperto un descrittore.
  - `staging.read_report` (`staging.py:262`) ne lascia uno a ogni lettura e alza `IsADirectoryError`, che
    `_stage_view` (`api/v1/backup/restore.py:211-215`) non prende: prende solo `FileNotFoundError`. A lettura del
    codice è un 500 sulla lettura del controllo, che la scheda ripete. La conferma (`apply.py:469`) lo prende, ma il
    descrittore resta.
  - Misurato il 20/10: 20 letture di una cartella lasciano 20 descrittori aperti su di essa, per ciascuno dei due.
  - `apply.py:329` è al riparo: controlla `S_ISREG` con `lstat` prima di aprire (resta solo una corsa).
  - Ci si arriva solo manomettendo `.restore/`, o con un disco rovinato.
  - Cura possibile: un aiuto unico che apre un file privato in lettura e chiude il descrittore se `fdopen` lo
    rifiuta, oppure controlla `S_ISREG` con `fstat` come `archive._add_file`; e `read_report` che risponde «nessun
    report» anche per una cartella.
  Dettagli: piano 07, «B-50».
  ✅ **Fatta il 20/10** (via del coordinatore alle 10:10, i job alle 10:39): un lettore unico,
  `paths.read_regular_file()`, legge gli stati dei job e dei controlli, i report e il biglietto dell'esito. Non segue
  mai un link, non aspetta mai una FIFO, chiude sempre il descrittore. Una cartella, un link o un file speciale al
  posto di uno di quei file è illeggibile: per un job «non trovato» con un avviso (un link al posto di `state.json`
  prima si seguiva), per un controllo «nessun controllo», per un report «nessun report» (la vista risponde senza, mai
  un 500). Trovato dalle sonde e curato nello stesso lotto: una FIFO al posto dello stato di un job o di un controllo
  bloccava la lettura per sempre, quindi l'avvio di un backup e la pulizia d'avvio, cioè ogni avvio.
  Dettagli: piano 07, «B-53 + B-54 + B-55».
- ✅ **B-54 · Uno stato di controllo del ripristino illeggibile non lo toglie nessuno** — minimo, pulizia; B, 20/10
  (B-50, domanda di test-author). Precedente a B-50.
  - `_prune_checks` lavora solo sui controlli che `_checks` sa leggere, e `_prune_unrecorded` pulisce i caricamenti e
    le copie, mai `checks/`.
  - Restano lì per sempre: un file vuoto, `{}`, un documento che non è un oggetto, una cartella, un file senza
    permessi. Sono pochi byte ciascuno.
  - Cura possibile: togliere da `checks/` gli stati illeggibili più vecchi del limite, quando nessun controllo gira.
  Dettagli: piano 07, «B-50».
  ✅ **Fatta il 20/10**: `prune`, quando nessun controllo gira, toglie da `checks/` gli stati che nessun controllo
  leggibile registra e quelli scritti a metà (`<id>.json.part`), più vecchi della durata di un controllo; mai quello
  della copia protetta, mai i nomi che non sono suoi, mai attraverso un link. In silenzio.
  Dettagli: piano 07, «B-53 + B-54 + B-55».
- ✅ **B-55 · Nel ripristino ogni `OSError` su uno stato di controllo è «nessun controllo», anche se transitorio** — da
  decidere (coordinatore o developer); B, 20/10 (B-50, domanda di test-author). Precedente a B-50.
  - `restore_jobs._read_state` prende ogni `OSError`: un errore passeggero del disco (`EIO`, `EMFILE`) diventa un 404
    `restore_stage_not_found`.
  - La scheda, mentre segue un controllo, a quel 404 lo dimentica (`restoreFlow.svelte.ts:593-597`); a un 500
    invece riprova.
  - Per i job B-50 ha deciso il contrario: i transitori restano un 500 che la scheda riprova.
  - Da decidere: la stessa regola nel ripristino (`IsADirectoryError` e `PermissionError` illeggibili, gli altri
    `OSError` che passano), oppure lasciarlo com'è.
  Dettagli: piano 07, «B-50».
  ✅ **Fatta il 20/10** (decisione del coordinatore: la stessa regola dei job): «nessun controllo» solo per una
  cartella, un link, un file speciale, un permesso negato o un contenuto illeggibile, ora anche una data senza fuso
  (faceva fallire ogni `prune` con un `TypeError`). Gli altri `OSError`, transitori, arrivano a chi chiama: un 500 che
  la scheda riprova. Lo stesso nella conferma: un errore transitorio sul report è un 500 `restore_confirm_failed`, non
  più «copia mancante».
  Dettagli: piano 07, «B-53 + B-54 + B-55».
- **B-56 · Un controllo a richiesta del DB vivo** — piccolo, dopo la 1.3; B, 20/10 (domanda di E sul ripristino a
  mano; proposta approvata dal coordinatore il 20/10).
  - Il ripristino a mano (`#by-hand`) non passa dal controllo dell'archivio: un danno che l'avvio non vede, come un
    testo non UTF-8 o una pagina rovinata del DB, si scopre solo quando una pagina legge quei dati.
  - Proposta: un comando in sola lettura, a richiesta (`dev.py db check` o simile), che fa sul DB vivo i controlli del
    ripristino: `integrity_check`, `foreign_key_check`, il testo non UTF-8 indicato con tabella e rowid (mai il
    contenuto), la revisione conosciuta. Serve al supporto dopo un ripristino a mano o un disco rovinato; mai
    all'avvio.
  - Nella 1.3 c'è la frase della guida in `#by-hand`: `backup inspect` e `backup restore --dry-run` prima di
    scompattare a mano.
  Dettagli: piano 07, «La domanda di E sul ripristino a mano».

## E · Email (fase 01)

Piano: [`08_email`](../Phase_1/08_email/plan-phase01Email.prompt.md). Sessione avviata il 15/10 alle 08:37, solo
analisi, sulla base `380a3e768`. Codice autorizzato il 15/10 alle 11:25 (delega del developer): E0 ed E1, sulla base
`23f6578f3`.

- ✅ **E-1 · I test del TLS vero dell'email si saltano finché manca `cryptography`** — minimo; E, 15/10 (E1).
  `EMD-017` (STARTTLS che consegna) ed `EMD-018` (un certificato non fidato è `TLS_FAILED`, nulla parte) fanno
  `importorskip("cryptography")`, quindi oggi saltano. Entrano da soli con la finestra delle dipendenze, che porta
  `cryptography` per X; allora vanno visti verdi una volta. Dettagli:
  [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E1.4».
  - 15/10, E: chiusa. Con `cryptography` 50.0.2 nell'ambiente condiviso (`dc9a5d232`), sulla base `fc99e9bfe`,
    `services email-delivery` dà 79 passati e nessun saltato: `EMD-017` consegna dopo STARTTLS ed `EMD-018` rifiuta
    il certificato non fidato. Dettagli: piano 08, «E1.8».
- **E-2 · Nel client generato il tipo di un campo facoltativo ammette anche una lista** — piccolo; E, 15/10 (E2a).
  `openapi-zod-client` traduce `anyOf [X, null]` in `(X | null) | Array<X | null>` nei tipi esportati (315 righe
  di `generated.ts`), più largo dello schema zod a runtime, che è giusto. Ogni lettore stringe il tipo da sé
  (`ProfileTab`: `typeof === 'string'`; `emailApi.fetchEmailStatus()`: normalizza una volta). Da correggere alla
  fonte (opzione del generatore o un passo come `fix-openapi-discriminators.mjs`), con `svelte-check` su tutto il
  frontend. Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E2.5».
  - 16/10, coordinatore: rimandata alla 1.4, perché tocca file condivisi (i passi del generatore di `api sync`).
- **E-3 · `ApiError` non lo costruisce nessuno: le rotte rifiutano con `AxiosError`** — piccolo; E, 15/10 (E2a).
  L'intercettore di `zodios-client.ts` dice «wrap in ApiError» ma lascia passare l'`AxiosError`; chi legge solo
  `error instanceof ApiError` vede ogni rifiuto come errore generico (la scheda Email ci era caduta: corretta, legge
  `isAxiosError`). Da decidere: convertire nell'intercettore, oppure togliere `ApiError` e il commento.
  Dettagli: piano 08, «E2.6».
  - 16/10, coordinatore: rimandata alla 1.4, perché tocca file condivisi (il client condiviso `zodios-client.ts`).
- ✅ **E-4 · `status.HTTP_422_UNPROCESSABLE_ENTITY` è deprecato in Starlette** — minimo; E, 15/10 (E2a). Dà un
  `StarletteDeprecationWarning` a ogni 422 delle quattro risposte di `api/v1/settings.py` che lo usano; il nome nuovo
  è `HTTP_422_UNPROCESSABLE_CONTENT` (lo usa `api/v1/email.py`); gli altri router scrivono `422`.
  Dettagli: piano 08, «E2.4».
  - 16/10, E: chiusa, con il via del coordinatore e di A (il file è di A). Le quattro righe ora usano
    `status.HTTP_422_UNPROCESSABLE_CONTENT`, con lo stesso codice 422 e senza avviso. In `backend/` non resta nessun
    `HTTP_422_UNPROCESSABLE_ENTITY`. Dettagli: piano 08, «E6.12». In `dev_release2` col merge `07700355f`.
- ✅ **E-5 · `api sync` non sfugge i backtick delle descrizioni su più righe** — piccolo; E, 15/10 (E2b).
  `openapi-zod-client` scrive una descrizione di più righe come template literal JavaScript senza sfuggire i
  backtick: una docstring di schema su più righe con ``` ``codice`` ``` rompe `generated.ts` al caricamento
  (`TypeError: "…" is not a function`), e con lui ogni pagina. Successo con `EmailInstanceConfig` (corretto: docstring
  su una riga). Le docstring di `backend/app/schemas` hanno 131 tratti tra doppi backtick: da sfuggire in
  `api sync` (un passo come `fix-openapi-discriminators.mjs`) o da vietare con un test sullo schema.
  Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E2b.4».
  - 16/10, E: chiusa con una guardia; il generatore non si tocca (decisione del coordinatore, nessun caso oggi). Il
    rischio è più stretto del previsto. Un testo esce solo in quattro forme, ognuna con i suoi caratteri vietati:
    `.describe()` su più righe e su una riga, le descrizioni Handlebars, il JSDoc. La docstring di un modello esce
    solo quando un campo è tipizzato direttamente con lui. Oggi nessun testo rompe il client, e 49 componenti sono
    latenti: basta un loro uso diretto come campo per romperlo.
    La guardia è `schemas openapi-client-text`
    (`test_openapi_client_text.py`, OCT-001…032). Legge `app.openapi()`, fallisce nominando campo, forma e
    carattere, e scatta se cambiano la versione o le opzioni del generatore. La regola 4 di «Contract Rules» è in
    `developer/api/overview.md`. Dettagli: piano 08, «E-5.0»…«E-5.3».
    Commit `43ad48952` (test) e `fc418255b` (journal), in `dev_release2` al treno 83 (merge `01598f9ad`).
- **E-6 · Il registro delle schede di Impostazioni importa ogni corpo di scheda** — minimo; E, 15/10 (E2b). Ogni
  scheda nuova obbliga ogni test che importa il registro vero ad aggiungere un mock, o il file non si carica
  (`page.tabs.test.ts` con la scheda Email); toccherà anche B e X. Da valutare con A: corpi caricati pigri o un
  aiuto di mock comune. Dettagli: piano 08, «E2b.4».
  - 16/10, coordinatore: rimandata alla 1.4, perché tocca file condivisi (il registro delle schede, di A, B e X).
- **E-7 · Un segno «in attesa di verifica» nella scheda Users** — piccolo; coordinatore, 15/10 (E5, domanda 7).
  Con la verifica dell'email accesa, chi si è registrato e non ha ancora cliccato il link compare nella scheda Users
  come un account disattivo qualunque: l'admin lo può attivare a mano, ma non vede che aspetta la verifica. Serve un
  campo nella lista di A (`pending_verification`) e un badge in `UserRow`. Fuori dalla 1.3 per decisione del
  coordinatore. Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E5.0».
- ✅ **E-8 · «Invia per email» non sceglie la lingua dell'invito** — minimo; E, 15/10 (E4a, decisione notturna da
  rivedere). L'azione manda l'invito sempre nella lingua predefinita dell'istanza; `POST /email/links` accetterebbe
  `language`, ma la 1.3 non mostra un selettore. Da aggiungere se serve invitare chi parla un'altra lingua.
  Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E4.1».
  - 17/10, E: analisi fatta; il coordinatore ha deciso con la decisione notturna **N69**: il default resta la lingua
    dell'istanza, il selettore cambia solo la lingua dell'email, e l'esito mostra la lingua usata. Il codice va dopo
    A8b, insieme all'allineamento del percorso «Settings › Email» all'etichetta del gruppo di A8b (coordinatore, 17/10:
    26 punti tra i18n, docs, `EmailSettingsTab.svelte` e devWiki, elencati nel piano). Dettagli: piano 08, «E-8.0»,
    «E-8.1» e la nota «Il percorso Settings › Email dopo A8b».
  - 17/10, E: fatta nella 1.3, in due parti.
    - **Parte 1**: il selettore della lingua dell'invito, cioè un `SimpleSelect` con la lingua dell'istanza come
      default, senza `language` nella richiesta. L'esito «Sent to {to}. Language: {language}.» prende la lingua dalla
      risposta.
    - **Parte 2**, dopo A8b: i percorsi «Settings › Administration › Email». Sono 8 valori i18n più circa 15 righe;
      A8b aveva già allineato il resto.
    - Commit: la parte 1 fino a `443eda316`, la parte 2 fino a `73decbb99`; tutte e due in `dev_release2` col merge
      `2aab994b8` (CHANGELOG `231566116`). Dettagli: piano 08, da «E-8.2» a «E-8.4».
  - 17/10, E: dopo l'ingresso, il gate G del coordinatore (dev `91f4de9cb`) ha trovato due rossi Vitest di E.
    - ETX-14 si aspettava ancora solo `{to}` in «sent».
    - Il mock di `$lib/i18n` di `linkShareRegistration.test.ts` non dava `DEFAULT_LOCALE` allo store della lingua, che
      il barile delle select carica.
    - Curati nei soli test (E-8.5); tutta la cartella `features/email` è verde. Dettagli: piano 08, «E-8.5». In
      `dev_release2` col merge `b49a2a716`.
- ✅ **E-9 · I limiti per casella non vedono gli alias (`+tag`, i punti di Gmail)** — piccolo; E, 16/10 (revisione di
  sicurezza finale, nota sotto la soglia). `strip().casefold()` fa di `victim+1@…` e `victim+2@…` caselle diverse:
  con la registrazione aperta si può puntare il budget orario dell'istanza su una casella sola, e ogni email porta lo
  username, testo libero di 50 caratteri. Il tetto resta `LIBREFOLIO_SMTP_MAX_PER_HOUR` per processo. Da valutare: una
  chiave che tolga il `+tag` (e i punti per i domini che li ignorano), oppure un controllo sullo username nelle
  email. Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E6.9».
  - 17/10, E: chiusa con la decisione notturna **N62** del coordinatore, da rivedere col developer. Le due cure
    servono entrambe.
    - (a) I tre limiti per casella contano su `delivery.mailbox_budget_key()`: `casefold`, il `+tag` tagliato su ogni
      dominio, i punti tolti per Gmail e `googlemail.com`. Solo come chiave: l'email va all'indirizzo salvato.
    - (b) Reset, verifica e avviso di cambio salutano senza username.
    - (c) L'avviso non mostra più niente del nuovo indirizzo, perché senza DNS anche il TLD è testo libero.
    - L'invariante: nessuna email che un estraneo può indirizzare porta testo scelto da lui.
    - Il DoS sul budget d'istanza, fatto con tante caselle diverse, è una domanda del cloud per il developer
      (coordinatore). Resta E-12.
    - Dettagli: piano 08, «E-9.0»…«E-9.2».
    - Commit `3dd23eaa4` (codice), `bb392de35` (docs), `7fc549fea` (journal); in `dev_release2` col merge `49c07a95a`.
- ✅ **E-11 · Su un'istanza bloccata, «Send the link again» legge il 401 del blocco come credenziali sbagliate** —
  minimo; E, 16/10 (E-10, nota del `test-author`).
  - `POST /email/verification/resend` è fuori da `ALLOWED_WHEN_BLOCKED`, quindi un chiamante anonimo riceve il 401 di
    `get_current_user`, e `readResendFailure()` legge ogni 401 come `INVALID_CREDENTIALS`: l'avviso dice che username
    o password sono sbagliati.
  - Lo incontra solo un account in attesa di verifica che si era registrato prima del blocco.
  - I due 401 si distinguono solo dal testo di `detail`: «Invalid credentials» della rotta, contro «Not authenticated»
    o «Session expired or invalid» del blocco. La configurazione pubblica, poi, non dice se l'istanza è bloccata
    (`GET /system/block` è per chi ha una sessione).
  - Le strade:
    - `blocked` in `GET /system/instance`, pubblico, così l'avviso lo dice (di H);
    - un codice proprio nel rifiuto anonimo del blocco (di H);
    - leggere il testo di `detail`, che è fragile.

  Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E-10».
  - 17/10, E: chiusa.
    - A7b non la risolve: A-13 tiene fuori dal redirect al login solo le pagine dei link, mentre «Send the link again»
      sta su `/`.
    - La strada scelta sta tutta nei file di E:
      - il 401 della rotta è ora codificato (`{"error_code": "INVALID_CREDENTIALS", …}`);
      - `readResendFailure()` legge ogni altro 401, o il 423 `instance_blocked`, come il blocco;
      - l'avviso mostra `auth.instanceBlocked`, la chiave di A7b.
    - Resta giusta anche se H darà un codice al rifiuto anonimo del blocco.
    - EVA-017 fissa `confirm` e `resend` fuori da `ALLOWED_WHEN_BLOCKED`.
    - Dettagli: piano 08, «E-11.0» e seguenti.
    - Commit `18d945d2e` (codice), `f2b459ebe` (docs), `fdd4acc6d` (journal); in `dev_release2` col merge `bca4bd6d3`.
- ✅ **E-12 · I domini catch-all e i sottodomini di Fastmail aggirano la chiave per casella** — basso; E, 17/10 (E-9).
  `mailbox_budget_key()` unisce gli alias `+tag` e i punti di Gmail. Restano due casi:
  - un dominio catch-all, dove ogni parte locale arriva alla stessa casella;
  - gli indirizzi a sottodominio di Fastmail (`qualsiasi@utente.fastmail.com`).

  In questi casi ogni parte locale è una chiave nuova, e li limita solo il budget orario dell'istanza. Un limite per
  dominio colpirebbe i grandi provider condivisi, quindi servirebbe un elenco di domini o un'altra idea. Dettagli:
  [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E-9.0», «Resti fuori da E-9».
  - 17/10, coordinatore: chiusa, il limite è accettato. Nessun codice.
    - Una regola Fastmail nella chiave non può essere completa: l'indirizzamento a sottodominio vale su tutti i domini
      di Fastmail, che sono decine, e sui domini personali dei clienti. Il catch-all resterebbe comunque.
    - Un limite per dominio destinatario vorrebbe un elenco di provider esenti, mai completo, oppure una variabile
      nuova: una scelta di prodotto per poco guadagno.
    - Dopo N62 queste email non portano testo dell'attaccante, e il budget orario dell'istanza le limita. La doc lo
      dice da E-9.
    - La leva vera è la registrazione aperta: la domanda anti-abuso **D-E9-1** (captcha o proof-of-work, limiti alla
      registrazione) è al developer.
    - Se il codice servirà, la strada è `LIBREFOLIO_SMTP_MAX_PER_DOMAIN`, spenta di default, con un default per il
      profilo `managed`, in un lotto suo.
    - Dettagli: piano 08, «E-12.0» ed «E-12.1».
- ✅ **E-14 · Uno sfratto mirato libera ancora un identificativo bloccato** — piccolo; E, 17/10 (revisione di N70, LOW).
  Con `eviction_scan=32`, sfrattare dal limitatore in memoria un identificativo bloccato costa 10 279 richieste,
  contro le 10 000 dell'LRU semplice (misurato). Il tetto ferma lo spruzzo ingenuo, non quello mirato. Dettagli:
  [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «La revisione di N70 a posteriori» ed «E-14».
  - 17/10, E: fatta nella 1.3 (via del coordinatore).
    - Il disegno proposto (un indice delle chiavi non piene) non bastava, e l'ho corretto prima del codice: chi si
      ferma a 9 fallimenti non rende mai piena la chiave, e uno spruzzo la libera per circa 1 100 richieste a
      tentativo, come oggi.
    - Ora si sfratta la chiave con meno colpi nella finestra, e tra quelle la meno usata. La scadenza è esatta (un
      heap), non c'è ricerca, e `eviction_scan` sparisce.
    - Il caso migliore per l'attaccante costa ora circa 10 000 richieste per tentativo, e nessuno spruzzo libera una
      chiave più pesante.
    - I docs «310 contro 100 000» sono corretti.
    - In `dev_release2` col merge `70dccc16f` (CHANGELOG `c2b4ec20e`).
- ✅ **E-15 · Nei run combinati il limite dei login si accende da solo, e i test di E vanno rossi** — piccolo; E, 17/10
  (triage dell'`all-backend` di W, coordinatore).
  - `conftest.py` mette `LIBREFOLIO_LOGIN_LIMIT=off` una volta sola, all'avvio.
  - I 60 moduli che chiamano `setup_test_database()` all'import passano da `configure_test_runtime()`, che toglie ogni
    `LIBREFOLIO_*`: nel processo il limite si accende alla raccolta.
  - Ne nascono 21 rossi nei servizi e 7 nelle API di `email-verification`, solo in combinato.
  - Decisione del coordinatore (17/10): la cura alla radice.
    - Un fixture autouse nel `conftest.py` condiviso rimette `off` prima di ogni test, se la variabile manca.
    - Niente fixture per modulo.
    - Va dopo la revisione X-R44.
  - 17/10, E: fatta.
    - `restore_login_limit`, nel `conftest.py` radice, di funzione, con un `MonkeyPatch` suo: rimette il valore della
      sessione (quello esplicito, o `off`) prima di ogni test che l'ha perso.
    - I fixture di A, che tolgono la variabile, girano dopo e vincono ancora.
    - `security.md` è allineato.
    - Prova: il modulo più un modulo che configura la corsia, prima 21 rossi, ora 179 verdi. Tutti i 13 moduli di E in
      un processo: 1 453 verdi.
    - In `dev_release2` col merge `da02ed816`.
  - Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E-15».
- ✅ **E-16 · Le due frasi di E sulla «password dimenticata» non dicono la richiesta della configurazione fallita** —
  minimo (doc, solo inglese); E, 17/10 (seguito della revisione di A9 e di FPM-08 di A, `d04ffde90`).
  - `admin/email.en.md` e `developer/backend/email.md` descrivono self-hosted e managed, non il caso in cui
    `GET /system/instance` fallisce: lì la scheda mostra solo «Ask your administrator…», in tutti e due i profili.
  - Una frase per pagina. Nessuna decisione.
  - 17/10, E: fatta (via del coordinatore, 12:22). Build stretta e `check-links` puliti. In `dev_release2` col merge
    `ac3c03177`.
  - Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E-16».
- ✅ **E-17 · Due errori di `tsc -p frontend/tsconfig.e2e.json`** — piccolo (test e configurazione); coordinatore, 17/10.
  - `onboarding-tour.spec.ts:863`: la lista dei passi è tipizzata dalle opzioni di `expectGuideStep`. Dietro c'era
    un secondo errore, il `backdrop` mancante: ora c'è un `backdrop: false`, che prende lo stesso ramo di prima.
  - `tsconfig.e2e.json`: la mappa `$lib`.
  - Nessun cambio a runtime, `tsc` senza i due errori, Prettier pulito.
  - Restano 3 TS2769 di C-66 (`c18517e31`): l'allargamento di E-2 contro `isStoredPoint`, di un ramo attivo.
  - In `dev_release2` col merge `fc979d0b4`. Dettagli:
    [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E-17».
- ✅ **E-18 · Codici di valuta stretti sulle scritture (MF-SEC9b)** — piccolo; coordinatore, 17/10 (analisi di E, 13:2x).
  - `Currency.validate_code` accetta nomi e numeri (`EURO`, `978`, `US DOLLAR`) e li salva così, senza
    canonicalizzarli; nelle transazioni senza limite di lunghezza.
  - Decisione: stretto solo sugli schemi di richiesta (tre lettere ASCII e `alpha_3` esistente; `XXX`/`XTS` ammessi);
    le letture restano tolleranti.
  - Il codice dopo l'ingresso di X-R59/SEC9-1 di MF; prima i rossi, in un file nuovo.
  - A parte: un avviso di qualità dei dati per i codici non ISO salvati, e la SQL di misura nella lista dello
    sviluppatore.
  - 17/10, E: fatta. `IsoCurrencyCode` e `IsoCurrencyAmount` sugli schemi di richiesta di transazioni, asset, eventi,
    FX (tassi e rotte) e sull'ingresso di Investimental. La lettura delle rotte resta sottoclasse e rinuncia col suo
    `ClassVar`. Lo schema OpenAPI è identico.
    - Prova: 17 selettori, 3 674 verdi, 0 rossi; build stretta e `check-links` puliti.
    - Restano fuori, aperti: l'avviso di qualità dei dati; il gap-fix del BRIM che costruisce `TXCreateItem` senza
      prendere l'errore (oggi irraggiungibile).
    - Commit `ed8b3c28e` (codice), `601b3714b` (docs), `c6a996275` (journal); in `dev_release2` col merge
      `73366626e` (CHANGELOG `e743fc6a3`).
  - Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «MF-SEC9b» ed «E-18».
- **E-19 · L'avviso dei codici di valuta non ISO salvati** — medio-piccolo (avviso), medio (correzione); coordinatore,
  17/10 (seguito di E-18).
  - Dopo E-18 una riga salvata con `978` o `EURO` non si salva più dopo una modifica, e l'utente non la vede: il
    selettore mostra un campo vuoto.
    - Gli asset danno 422 a ogni modifica, e correggerli dal modulo passa dal wipe della Policy D.
    - Le rotte FX in modifica si perdono.
    - Il cruscotto manda verso tassi che ora danno 422.
  - Ci sono altre due fonti:
    - il ripristino di un backup vecchio, sempre;
    - un buco di E-18: la `base_currency` dell'utente controlla solo la lunghezza.
  - Gap-fix del BRIM: i movimenti salvati con un codice non ISO restano fuori dal confronto, e propone un deposito
    correttivo per denaro che c'è già. La cura è nello stile di W-B74.
  - 17/10, E: analisi fatta. Decisioni dello sviluppatore aperte:
    - D1, il modello di correzione: A guidato dall'utente, B da riga di comando, C automatico in `post_migration`;
    - D2, la correzione degli asset senza wipe;
    - D3, la gravità.
  - 17/10, coordinatore: D3 deciso (`warning`); D1 e D2 allo sviluppatore. Via su E-19a (backend) ed E-19b (utente).
  - 17/10, E: **E-19a fatto**.
    - `base_currency` stretto; `suggested_iso_currency()` (limite 80, mai GBX/ZAC/ILA, ambiguo = nessuno); il 422 che
      nomina il codice.
    - `stored_currencies.py`: 14 posti, l'avviso d'avvio e `dev.py db currencies`.
    - La guardia del gap-fix (W rivede) e il passo d'avvio (H rivede).
    - 14 suite, 3 800 verdi; OpenAPI identico; build stretta e `check-links` puliti.
    - In `dev_release2` col merge `c7c6f94f0` (CHANGELOG `e98934eed`); il fix-forward col merge `09fe3f470`.
  - Resta **E-19b**: `IssueCode.NON_ISO_CURRENCY` al posto di `MISSING_FX_*`, il banner senza bottone, il selettore
    col valore salvato, l'avviso del ripristino (via di B), i18n nelle 4 lingue, `api sync`.
  - 17/10, E: **E-19b1** (il selettore, l'endpoint `suggest`, l'avviso `non_iso_currencies` del ripristino): parte 1 nel
    commit `6e539da02`; `staging.py` sopra B-43, con le tre condizioni di B, va col checkpoint E-19b1. Resta **E-19b2**:
    `NON_ISO_CURRENCY` nel rapporto di qualità, sul lettore di Z-32 (c).
  - 17/10, E: **E-19b1 entrato** (dev `1742aaaaa`), e le due LOW di H su E-19a (dev `0897502a9`: `trusted_schema` nella
    lettura, l'audit d'avvio in background dopo `plugin-secrets-check`). **E-19b2 fatto** (rossi `0e787dfb4`, codice al
    checkpoint): una voce `NON_ISO_CURRENCY` per valore salvato, senza CTA fino a D1/D2, e `MISSING_FX_*` senza le
    coppie con un lato non ISO. Resta di E-19 solo la correzione (D1/D2, dallo sviluppatore) ed E-20.
  - ✅ 19/10, contabilità: l'avviso è entrato tutto in `dev_release2`.
    - E-19a: merge `c7c6f94f0` (CHANGELOG `e98934eed`), col fix-forward `09fe3f470`.
    - E-19b1: merge `1742aaaaa` (CHANGELOG `2fbbf4c4c`).
    - Le due LOW di H su E-19a: merge `0897502a9`.
    - E-19b2: merge `b878f043c` (CHANGELOG `9e6faacf4`).
    - La voce resta aperta per la correzione, D1/D2, che sono dello sviluppatore.
  - Per D1, se si sceglie C: la rietichettatura automatica deve escludere anche `GBp`, non solo GBX/ZAC/ILA.
  - ✅ Il pezzo di J: la guardia di `Intl` in `riskAnalysisHelpers.ts:168`, entrata in dev `b13ed7944` (CHANGELOG
    `826f99f17`).
  - Smistati altrove dal coordinatore: il modale delle rotte FX che cancella prima di ripubblicare (X) e il `GBp` di
    Yahoo contro il confronto esatto del refresh (Z).
  - Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E-19».
- ✅ **E-20 · L'audit delle valute e i testi che non sono UTF-8** — piccolo; `test-author` di E-19b1.3 (dubbi 1 e 2),
  17/10.
  - Un solo valore TEXT che non è UTF-8 valido, in una delle 14 colonne, fa alzare a sqlite3 un `OperationalError` al
    `fetchall`, e l'audit intero cade:
    - l'avviso d'avvio dice «could not be checked» e non elenca nulla;
    - il controllo di un ripristino perde `non_iso_currencies`, quindi un archivio costruito apposta nasconde tutti gli
      altri codici non ISO. Non blocca e non perde testo (E-19b1.3), ma acceca.
  - Il messaggio di quell'errore cita il testo salvato. Il ramo «no such table / no such column» lo confronta con
    `str(error)`, quindi un testo che contiene quelle parole fa saltare il suo posto in silenzio.
  - La cura proposta, in `stored_currencies.py`:
    - leggere ogni posto come `typeof()` più `hex()` in un CTE intorno alle 14 query, e decodificare in Python;
    - un testo non UTF-8 diventa un reperto `X'…'` come un BLOB;
    - confrontare il messaggio solo per gli errori della `execute` (la preparazione), mai su quelli dei dati.
  - Cambia ciò che fissano SCA-036 e RNW-109: servirà un altro errore vero per il ramo del guasto.
  - Con questi resti, il `GBp` del suggerimento: `suggested_iso_currency("GBp")` dà `GBP` (CSG e CCA lo fissano, perché
    per una scrittura `GBp` si salva `GBP`), quindi l'endpoint `suggest` e il selettore di b1 direbbero a un `GBp` salvato
    che vale GBP, cioè pence come sterline. b2 lo esclude con `minor_unit_factor()` di Z; l'endpoint no. Improbabile,
    perché anche la vecchia regola portava `GBp` a `GBP`.
  - Il caso più ampio è di B: un testo non UTF-8 nei dati di un backup passa il controllo del ripristino (RNW-109, in
    quattro posti) e poi, con ogni probabilità, fa fallire le letture del server di quelle righe (pysqlite alza al
    `fetch`, come prova la barriera di SCA-036; non misurato sul server). Segnalato al coordinatore.
  - Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E-19b1.3».
  - 20/10, E: fatta nella 1.3 (via del coordinatore, 09:00). Dettagli: piano 08, «E-20» ed «E-20.3».
    - La metà d'avvio: l'audit legge con un `text_factory` permissivo, quindi un testo non UTF-8 è un reperto `X'…'`
      come un BLOB; il controllo d'avvio elenca anche tutti gli altri, e `db currencies` esce con 1 (SCA-016, SCA-036,
      SCA-046). Non è la cura proposta sopra (il CTE con `typeof()` e `hex()`): il factory tocca solo le letture
      dell'audit e torna com'era anche quando una lettura fallisce (SCA-017, SCA-018). E nessun errore dei dati arriva
      più al confronto del messaggio con «no such table».
    - La metà del ripristino l'ha chiusa B-49: un archivio con un testo non UTF-8 è rifiutato (`database_damaged`).
    - Il `GBp`: chiuso senza codice. Nessun percorso di LibreFolio salva `GBp`: le scritture (`iso_currency_code`), le
      letture (`Currency.validate_code`) e il validatore dell'ORM (`_validate_currency_field`, `models.py:48`, 8 campi,
      i prezzi dei provider compresi) lo portano tutti a `GBP`, come già la regola di prima. Un `GBp` salvato può venire
      solo da fuori: una modifica a mano, un altro programma.
- **E-21 · Le frasi `BRIMParseError` dei plugin arrivano in inglese, dentro la cornice tradotta** — medio, chiarezza;
  coordinatore, 17/10 (decisione (c) di C-70b). Da C-70b il 400 del parse è `parse_failed`, con una cornice tradotta
  («Il plugin X non ha potuto leggere Y: …»), ma il motivo resta la frase inglese del plugin: circa 60 `raise
  BRIMParseError(...)` in più di 30 plugin (`backend/app/services/brim_providers/*/plugin.py`). La cura, nello stile di
  K2a: un codice e un contesto per ogni causa che l'utente può correggere (`BRIMParseError(message, details={"code": …,
  "context": …})`, o un campo dedicato), tradotti in `importWizard.parseRefusal.<code>` dove lo dice la regola R1, e il
  risolutore di C-70b che li preferisce alla frase. Dopo la 1.3; W rivede. Dettagli: piano 08, «C-70b».
- **E-22 · A ogni risveglio un'istanza gestita rifà la scansione delle valute salvate** — piccolo, prestazioni; H,
  17/10 (revisione del seguito di E-19a, riferita dal coordinatore). Un'idea per dopo la 1.3: aperta, nessuna
  decisione.
  - Il passo d'avvio `stored-currencies` rifà l'audit di `stored_currencies.py` a ogni avvio, quindi a ogni risveglio
    di un'istanza gestita che si sospende. Da E-19a.4 gira in background, ma resta un picco di CPU e I/O accanto alle
    prime richieste: 0,6 s a un milione di righe di prezzi, 1,6 s a tre milioni (misure sintetiche di E-19a.4).
  - Dalla 1.3 le scritture rifiutano i codici non ISO: solo un aggiornamento o un ripristino possono riportarne, a
    parte una modifica a mano del database.
  - L'idea di H: un piccolo segno nella cartella dei dati, legato alla versione dell'app e alla testa di alembic e
    cancellato dal commit di un ripristino, con cui i risvegli normali saltano la scansione.
  - Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E-19a.4».
- ✅ **E-23 · AI Export: un asset con prezzi solo prima del periodo risulta coperto con una serie vuota** — piccolo,
  chiarezza; E, 19/10 (analisi di E-AI503). Preesistente, fuori da E-AI503: aperta, nessuna decisione (per J e lo
  sviluppatore).
  - Se l'ultimo prezzo salvato è anteriore al periodo, i punti del periodo sono solo riportati in avanti.
    `portfolio.technical_prices` tiene l'asset in `assets` con la valuta, i bucket tutti vuoti e `latest_close` nullo,
    e lo conta coperto. `portfolio.technical_coverage` lo dà invece non coperto (0 osservazioni).
  - Con la regola dello sviluppatore («il calcolo … sul ritorno di punti che il db dà») potrebbe passare fra gli
    `uncovered_assets` con un motivo suo; oggi il prompt non dice perché la serie è vuota.
  - Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E-AI503.0» e «E-AI503.5».
  - 20/10, E: fatta nella 1.3 (J chiude il suo J-65 come doppione), con le decisioni dello sviluppatore (E-23.1):
    - un asset senza prezzi nel periodo, ma con prezzi prima, va fra gli `uncovered_assets` con `no_price_in_period`,
      la valuta, l'ultimo prezzo salvato e la sua data; da solo, `asset.ohlc_returns` dice lo stesso codice;
    - ogni sequenza di secchi vuoti con almeno un giorno di mercato aperto (`market_calendar.py`) diventa un buco
      fuso, con l'ultimo valore salvato prima: la tabella `PRICE GAPS`, e `RATE GAPS` per i cambi (`fx.rate_ohlc` v2);
      un buco in testa senza prezzo prima ha le celle vuote.
    - Dettagli: piano 08, da «E-23» a «E-23.2».
- **E-25 · `/verify-email` spende il link all'apertura, senza un clic** — piccolo, sicurezza; E, 16/10 (E6, lista del
  mattino), analisi 20/10. Un filtro di posta che apre i link in un browser isolato verifica l'indirizzo al posto del
  titolare. Proposta: uno stato «Conferma» col pulsante, solo file di E. Da decidere (sviluppatore). Dettagli:
  [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E-25 ed E-26».
  - 20/10, sviluppatore (13:4x): approvata coi testi proposti; nella 1.3, via del coordinatore (14:28).
- **E-26 · Dopo la registrazione «We sent you an email» anche quando l'email è trattenuta** — minimo, chiarezza; E,
  16/10 (E6, lista del mattino), analisi 20/10. Il messaggio non dice la via d'uscita (accedere e chiedere un nuovo
  link). Proposta: solo il testo, una chiave di E ×4. Da decidere (sviluppatore). Dettagli: piano 08, «E-25 ed E-26».
  - 20/10, sviluppatore (14:3x): la (b), un campo nella risposta di `POST /auth/register` per l'email trattenuta, più il
    testo (a) per il caso normale. File di A e `api sync`: prima l'accordo con A sul contratto. Dopo E-25.

## Y · Cruscotto e grafici (fase 01)

Piano: [`09_dashboardCharts`](../Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md). Sessione avviata il
15/10 alle 11:28, solo analisi, sulla base `23f6578f3`. Codice autorizzato il 15/10 alle 12:47 (developer, via il
coordinatore): Y1 (taglio di `GrowthChart`, con B10) e Y2 (taglio di `DataTable`), sulla base `1e9e567f7`. Righe scritte
da Y il 15/10.

- **Le voci di Y vivono nelle loro sezioni** (C-85, C-62 e C-38 nella C; B10, 47-1, 48-1 e 54-1 nella I; T-U8 e
  T-FE2…FE11 nella T; K-13, K-15, C-15, C-34, I-01, I-03 e O-16 nel backlog 38; i difetti 2 e 5 nel README della 13):
  le chiude il coordinatore a ogni treno. Stato all'analisi e lotto di ciascuna: piano di Y, §2.
- ✅ **Y-1 · I-03 è curata solo a metà** — chiusa da Y8 il 15/10 (entrata in `dev_release2` con `160562b56`, treno 57): un `$effect`, a ogni
  caricamento finito, ripiega da `%` ad Abs quando la storia non ha dati in percentuale, e torna al `%` quando li
  ritrova, salvo una scelta esplicita nel frattempo. Rosso prima in `GrowthChart.test.ts` («% view without % data,
  after every load»); provata in Vitest, non ancora nel browser. Era: basso; Y, 15/10 (analisi). Il ripiego da % ad Abs
  scattava solo per la vista % ripristinata al caricamento (`GrowthChart.svelte:785-789`, dal 24/09); cambiando periodo
  o broker verso una storia senza dati in percentuale, il bottone restava premuto e disabilitato (`:2539-2546`).
  Dettagli: piano di Y, §2 e §7 «Y8 — passo 2».
- ✅ **Y-2 · Nella cascata settimanale una linea di broker che finisce a metà settimana diventa un buco** — basso, da
  verificare; `test-author` di Y, 15/10 (Y1). ✅ 17/10 (entrata con `14072c03d`, treno 209; CHANGELOG `abf8391fb`): `aggregateMetric` cerca il valore per
  `bucketEnd`, il secchio di
  calendario, invece che per `bucket.date`. Tre rossi in `chartCoreHelpers.test.ts` (settimanale, due settimane,
  mensile), poi verdi; E2E `dashboard` 27/27. Comportamento preesistente, spostato alla lettera in
  `dashboard/growthChartData.ts` (`aggregateMetric`): il valore di un secchio si cerca sull'ultimo giorno della settimana
  presente in storia (`bucket.date`), mentre `aggregateLineSeries` lo mette sull'ultimo giorno con un valore. Una serie
  con valori a inizio settimana e `null` l'ultimo giorno (una linea di broker che esce dal perimetro) mostra un buco in
  quel secchio; la scala delle candele, invece, tiene l'ultimo valore. Prima un test rosso. Dettagli: piano di Y, §7
  «Y1 — passo 4».
  - **Nessuna attesa** (16/10, coordinatore): DV-8 (`28f4bed75`, sul ramo di DV) tocca solo `lib/theme/chartPalettes.ts`, né
    `GrowthChart.svelte` né `growthChartSeries.ts`. Y-2 non è in calendario.
- ✅ **Y-3 · Il gate della privacy non conosce `t(` come chiamata di traduzione** — minimo; `test-author` di Y, 15/10 (Y1).
  `moneyRenderSites.test.ts` esclude dai token numerici solo `$_(`, `$t(` e `label(`: nel tooltip di GrowthChart, ora
  `growthChartTooltip.ts`, il traduttore si chiama `t`, e una chiave come `dashboard.totalPnl` conta come token
  numerico. Rende il gate più severo, non più cieco: oggi c'è un solo reperto, registrato. Da decidere se aggiungere
  `\bt\(` alla forma, misurando prima il rumore. Dettagli: come Y-2.
  ✅ 17/10 (`034f0f13a`, entrata con `73443c6db`, treno 237): misurato prima, gli stessi 8 colpi con la forma vecchia e
  con la nuova (rumore zero); ora `I18N_CALL = /\$_\(|\bt\(|label\(/`, con un caso sintetico attraverso `scanLine`;
  7/7. Dettagli: piano di Y, «Y-3 e Y-4».
- ✅ **Y-4 · I commenti di `SignalTreeSelect.test.ts` descrivono ancora la scelta a clic della galleria** — minimo; G
  (G-12), via il coordinatore, 15/10. Righe 16–17 e 306–310: `selectIndicatorFromTree` della galleria vi espande la
  famiglia con un clic e clicca l'opzione, mentre da G-9 (`1470bd693`) la galleria sceglie l'indicatore da tastiera. Va
  corretto solo il testo dei commenti, quando Y passa da quei file (FE2, lotto Y4). Dettagli: piano di Y, §2.
  ✅ 17/10 (`1130d2eff`, entrata con `73443c6db`, treno 237), senza aspettare FE2: il docblock e il commento del caso a
  clic descrivono la scelta da tastiera della galleria, e il titolo del caso non nomina più l'aiuto della galleria;
  28/28. Dettagli: piano di Y, «Y-3 e Y-4».
- ✅ **Y-5 · Il commento di `headerTooltip` in `table/types.ts:291` promette un'icona che non c'è** — minimo; `docs-writer`
  di Y, 15/10 (Y2). ✅ 16/10: ora il commento dice che il tooltip sta sull'etichetta dell'intestazione e che l'icona
  compare solo con `headerTooltipUrl`; svelte-check 0/0. Entrata con `149157025` (treno 162), insieme a Y-21. Diceva «(info icon)», ma `headerTooltip` da solo mette un tooltip sull'etichetta dell'intestazione:
  l'icona compare solo con `headerTooltipUrl`. La pagina `core-ui/data-table.md` è già corretta (Y2). Va corretto solo
  il commento, quando Y o altri toccano `types.ts`. Dettagli: piano di Y, §7 «Y2 — passi 5–6».
- ✅ **Y-6 · `AllocationPanel` passa ancora `emoji` alla torta, che dopo DV non lo legge più** — minimo; coordinatore (DV),
  15/10. Chiuso il 16/10 da Y10 (`1bb8dc990`, entrata con `4447814ed`, treno 104): campo e tipo tolti; la torta prende le emoji dallo store dei settori.
  `dashboard/AllocationPanel.svelte:65` (`toAllocEntries`) mette `emoji` in ogni voce, e il tipo `AllocEntry`
  (`:23`) lo dichiara: dopo l'ingresso di DV la torta non lo legge più, quindi è un dato morto. Da togliere in Y10,
  dopo DV. Dettagli: piano di Y, §2.
- **Y-7 · Dopo Y4a le primitive dei grafici importeranno dalla feature dei segnali** — medio-basso; Y (analisi di Y3 e
  Y4), approvata come residuo dal coordinatore, 15/10 (D-Y15).
  - Con `lib/charts` in `features/signals`, restano fuori i generici: `LineChart`, `CandlestickChart`,
    `PriceChartCompact`, `PriceChartFull`, `chartCoreHelpers`, `lineChartHelpers`, `priceChartHelpers`,
    `timeSeriesAggregation` di `components/charts`, e `stores/chartSettingsStore`.
  - Questi importano da `$lib/features/signals`: quasi solo `type RenderedSignal`, più `signalLabelToHtml` e, in
    `priceChartHelpers`, `backendSignalSchemas` e `getBackendSignalProblem`.
  - È un'inversione di livello: la UI generica dipende da una feature.
  - Da chiudere in FE9, spostando il contratto fra grafico e segnale in `components/charts` o in un modulo neutro.
  - Dettagli: piano di Y, §0.3 e §7 «Y3 e Y4 — analisi».
- ✅ **Y-8 · `updateArrowRotations()` legge `getOption()` a ogni passo dello zoom** — basso, prestazioni; `test-author` di
  Y, 15/10 (Y8). ✅ 17/10: le frecce si riallineano una volta, a gesto fermo, nel rinvio che già ridistanzia le etichette
  (`LineChart` e `CandlestickChart` nel timer da 120 ms, `PriceChartFull` nel ramo «risoluzione tenuta» del rinvio da
  200 ms); i gestori di `dataZoom` non leggono più `getOption()` e non riscrivono le serie. Nessuna cache: l'opzione si
  legge al momento, quindi la riscrittura porta i colori correnti (condizione del programma colori). Fissato da 3 rossi
  per passo e assestamento e da 4 guardie del colore chiaro → scuro → zoom (`LineChart.test.ts`,
  `PriceChartFull.test.ts`), con la prova del morso: una cache del primo `getOption()` porta le 4 guardie al rosso.
  Nello stesso lotto, Y-8b: `LineChart.renderChart()` ora ripristina lo zoom salvato prima di riallineare, come
  `CandlestickChart` (prima, dopo un ridisegno di un grafico zoomato, le frecce restavano orientate sull'asse intero fino
  all'assestamento); un rosso in `LineChart.test.ts`. Entrata con `823a2f6bc` (treno 225); CHANGELOG `039af67bb`.
  - Prima: `charts/lineChartHelpers.ts:594` chiamava `chart.getOption()`, che clona tutta l'opzione, e i tre gestori di
    `dataZoom` la chiamavano a ogni passo del gesto: `LineChart.svelte:399`, `CandlestickChart.svelte:290` e
    `PriceChartFull.svelte:612`, contro la nota di `PriceChartFull.svelte:604-609` («do NOT read
    chartInstance.getOption() here»).
  - Dettagli: piano di Y, «Y-8 · `updateArrowRotations()` e `getOption()` a ogni passo dello zoom».
- **Y-9 · Il layout del PAC da telefono, da rivedere sugli scatti mobile dopo Y7** — basso; Y, 15/10 (Y7), per la
  decisione 50 del developer. Y7 fa scorrere con la tabella le colonne di selezione e azioni sotto i 768 px (D-Y17).
  Restano le larghezze dichiarate di `TargetsStep` (`features/tools/pac-allocator/planner/steps/TargetsStep.svelte`:
  la tabella supera i 500 px). Va giudicato sugli scatti mobile `pac-step-targets` e `pac-step-review` della galleria
  d'ingresso di Y7, insieme alle altre note del developer. Dettagli: piano di Y, §4 «Y7».
- **Y-10 · Su un telefono la maniglia di ridimensionamento è invisibile** — minimo, UX; `test-author` di Y, 15/10 (Y7).
  - Dopo Y7 un dito ridimensiona una colonna (D-Y18). Ma la maniglia
    (`table/DataTableColumnHeader.svelte`, `.resize-handle`) resta trasparente finché la cella non è in hover, e un dito
    non fa hover: sul telefono funziona, ma non si vede.
  - Da decidere se mostrarla su `@media (hover: none)`. Cambierebbe gli scatti mobile, e il colore
    `--lf-cmp-datatable-resize-handle-bg` c'è già.
  - Dettagli: piano di Y, §7 «Y7».
- ✅ **Y-11 · Il corpus golden di `timeSeriesAggregation` è rosso dall'ingresso di Y8** — medio, test rosso sul target;
  Y, 16/10 (trovato nelle prove di Y3). Chiuso il 16/10: corpus ricatturato dopo I-01 (`4c1f2fee6`, entrata con `4447814ed`, treno 104).
  - I-01 (Y8, `a25d09a69`) ha cambiato di proposito `aggregateSumSeries`: i punti mancanti non entrano nella somma, e un
    secchio senza valori diventa un vuoto. Il corpus di `components/charts/__tests__/timeSeriesAggregationGolden.test.ts`
    registra invece il comportamento di prima (caso `all-missing-values|weekly`, e il digest).
  - Nelle prove di Y8 mancava `front-asset asset-unit`, e così 2 test sono rossi dal treno di Y8.
  - Rimedio proposto: `test-author` ricattura il corpus con la procedura del file, annotando che la differenza viene da
    I-01.
  - Dettagli: piano di Y, §7 «Y3».
- ✅ **Y-12 · In `brokers-detail.spec.ts` il controllo dei bottoni di presentazione non gira da luglio** — medio, test che
  passa senza provare; `test-author` di Y, 16/10 (durante il triage della corsa E2E unica). ✅ 16/10, `6ac6ead12` (entrata con `0c79932a7`, treno 130)
  («test(e2e): rewrite lots comparison toggles test»): il test morto riscritto in due test sui controlli di oggi (P25),
  con `aria-pressed` e il contatore dei rendering. La ✅ qui mancava: aggiunta il 17/10. **Serve una decisione del
  developer sulla funzione**, che porta il coordinatore. **Decisa il 16/10 (P25): si riscrive** sui controlli di oggi;
  è il prossimo lotto di Y, dopo Y12a.
  - Il test «Value presentation toggle…» (`e2e/brokers/brokers-detail.spec.ts:582`, numero di riga dopo la correzione
    delle attese) esce in anticipo a ogni corsa: `if (!(await presentationFilter.isVisible({timeout: 5_000})…)) return`.
  - I testid che cerca, `lots-value-presentation-filter` e i tre `lots-value-*-toggle`, sono entrati in `6b28d60df`
    (16/07) e usciti da `src` in `59c160325` (18/07, «chart cleanup»). Un verde prova quindi solo la navigazione, il
    pannello e un clic.
  - Nello stesso test, `:577` seleziona per classe CSS (`.checkbox-btn`), contro le regole dei test frontend.
  - Due strade: togliere la coda del test, oppure riscriverla sui controlli di oggi.
  - Dettagli: piano di Y, «Corsa E2E unica…», Fuori pista.
- ✅ **Y-13 · Due test dei lotti controllano la selezione con la classe `selected`** — minimo; `test-author` di Y, 16/10
  (riscrittura di Y-12). **→ T** (coordinatore, 16/10 14:20): lo chiude T, nel suo lotto dei token dei componenti, su
  `brokers-detail.spec.ts:392-419` con `toHaveAttribute('data-selected', …)`; Y non lo tocca. ✅ 17/10: chiuso da T in
  `4a7ba1d7e` (entrata con `4d8ae68c4`); il file usa `data-selected` (`:392-419`). Verificato da Y il 17/10.
  - In `e2e/brokers/brokers-detail.spec.ts`, il clic su un segmento del Gantt e quello sulla cella della custodia
    fanno `toHaveClass(/selected/)` sulla riga.
  - La regola 10 della skill design-system vuole lo stato, non le classi: la riga pubblica già `data-selected`
    (`DataTable.svelte:1098-1149`).
  - Rimedio: `test-author` passa a `toHaveAttribute('data-selected', 'true')`. Dettagli: piano di Y, «Y-12».
- ✅ **Y-14 · «Aggiorna» della lista dei broker non ricalcola le cifre delle schede** — minimo, già presente prima di Y11;
  `test-author` di Y, 16/10. ✅ 16/10: si sceglie «forzare» (coordinatore, 21:2x). `brokers-refresh` fa
  `requestPortfolioRefresh()` e chiede il report delle schede con `force`; rosso 9/10, verde 10/10 su
  `front-broker list`. Entrata con `47ed8ebc4` (treno 144).
  - `brokers-refresh` rilegge solo l'elenco (`GET /brokers?include_inaccessible=true`). Le cifre delle schede vengono
    dalla cache dei report finché questa è fresca.
  - Nella Dashboard e nella pagina del broker, invece, «Aggiorna» ricalcola tutto (documentazione utente, «Coming back
    and refreshing»).
  - Da decidere: forzare il report delle schede, oppure dire nella documentazione che lì «Aggiorna» rilegge l'elenco.
    Dettagli: piano di Y, «Passo 4 · BK e TR».
- **Y-15 · Il `title` di `brokers-refresh` è scritto in inglese nel codice** — minimo, già presente prima di Y11;
  `test-author` di Y, 16/10.
  - Il pulsante, solo icona, ha `title="Refresh"`, che è anche il suo nome accessibile. `common.refresh` in inglese vale
    «Reload», mentre la pagina del broker usa `dashboard.syncData`.
  - Quindi correggerlo vuol dire anche scegliere la chiave e la parola, nelle quattro lingue. Dettagli: piano di Y,
    «Passo 4 · BK e TR».
  - **Rimedio** (coordinatore, 16/10): Y propone la parola, «Refresh» o «Reload», nelle quattro lingue, insieme agli
    altri pulsanti «Aggiorna» delle pagine; la scelta spetta al developer.
- ✅ **Y-16 · Una vista Candele salvata si carica, su una Dashboard nuova, solo grazie a una dipendenza involontaria** —
  minimo, già presente prima di Y11; `test-author` di Y, 16/10. ✅ 17/10, opzione A (coordinatore; entrata con `14072c03d`, treno 209): il comportamento è
  fissato in modo esplicito da un E2E (`page-busy.spec.ts:867`), con una prova di mutazione. Con un `untrack` attorno
  alla chiamata vanno rossi questo test e la precondizione di N55 (`:774`); sul codice vero, 17/17. Più due commenti
  (`GrowthChart.svelte`, `loadPnlCandles` della Dashboard). La correzione vera, cioè dipendenza esplicita e niente
  ciclo, è Y-24, per il developer.
  - Il `$effect` di `GrowthChart` (976–980) chiama `onRequestPnlCandles()`. Il caricatore parte in modo sincrono,
    sia con `join` sia, prima, con `track`.
  - Le sue letture (`canAsk`, `pnlCandles`, la cache dei report) diventano così dipendenze di quell'effetto. È il
    cambio di `canAsk`, quando i broker diventano noti, a farlo ripartire.
  - Oggi lo fissa solo in modo indiretto la precondizione del test E2E di N55. Da rendere esplicito. Dettagli: piano di
    Y, «Passo 4b».
- ✅ **Y-17 · I pulsanti Holdings/Performance di `PositionsPanel` non pubblicano `aria-pressed`** — minimo, già presente
  prima di Y11; `test-author` di Y, 16/10. ✅ 16/10, chiusa da DV nel W6-d (`3805bf2ca`): `aria-pressed` sui 4 pulsanti
  Holdings/Performance e Table/Map.
  - I pulsanti di `GrowthChart` lo pubblicano. Quindi il test E2E di N55 legge la vista Performance da
    `contribution-table`. Dettagli: piano di Y, «Passo 4b».
- **Y-18 · Le candele non hanno un indicatore di caricamento proprio** — minimo; Y, 16/10, una conseguenza di N55 da
  rivedere con il developer.
  - Con N55, se l'utente passa direttamente alle Candele a pagina ferma, il pulsante della pagina non gira più.
  - `GrowthChart` ha solo lo scheletro della storia (`loading`), quindi finché le candele non arrivano nessun
    indicatore lo segnala. Era così anche prima di Y11. Il contributo invece ha `contributionLoading`.
  - Dettagli: piano di Y, «Passo 4b».
- ✅ **Y-19 · La durata della caduta peggiore può venire da una fonte diversa da quella della profondità** — minimo, già
  presente prima di Y12b; `test-author` di Y, 16/10. ✅ 16/10: ora la durata segue la fonte della profondità, con una
  riga in `levelHelpers.ts`. Il rosso era 1/513, il verde 513/513; entrata con `90b84ac9c` (treno 148).
  - In `buildHurtRows` (`levelHelpers.ts`) la durata è `maximum_drawdown_duration_days` del riepilogo, con ripiego sul
    KPI, mentre la profondità ha un ripiego suo.
  - Se il riepilogo c'è ma la sua profondità ha il segno sbagliato, si mostrano la profondità del KPI e la durata del
    riepilogo.
  - Y12b ha legato alla stessa fonte solo il recupero (`summaryDepth`). Dettagli: piano di Y, «Y12b».
- ✅ **Y-20 · `risk-lab.md`: numeri di riga scaduti fuori dal paragrafo di L1** — minimo, documentazione per sviluppatori;
  `docs-writer` di Y, 16/10. ✅ 16/10: aggiornati 20 riferimenti, nelle sezioni Requests, L1 e host, più quattro
  precisazioni di testo; `check-links` verde. Entrata con `b89985a8b` (treno 149).
  - Y12b ha aggiornato solo il paragrafo di L1. Restano scaduti i riferimenti delle righe 302–310 e 119 della pagina:
    - `l1Helpers.ts` e `ReturnHistogram.svelte`;
    - `lossMoney()` e `RiskMetricCard.svelte`;
    - `DOC_PATHS` e `TAIL_DOCS`;
    - `riskAnalysisHelpers.ts`.
  - La tabella con i valori di oggi è nel piano di Y, «Y12b».
- ✅ **Y-21 · L4 (D377): un `poll` di 3 s che non resiste al carico** — piccolo; Y, 16/10 (triage dell'E2E di Y12b,
  decisione del coordinatore delle 21:20). ✅ 17/10: D377 è verde nelle due corse, in 11,7 s e in 22,2 s, con le
  scadenze vere (`L4_OFFER_DEADLINE_MS`, 10 s) sui suoi quattro `poll`. Il budget di 90 s per tutto il blocco
  «functional integration» (opzione A del coordinatore) rende verdi D378 e il benchmark condiviso, rossi alle 23:25
  per la stessa causa. Prova sulla revisione combinata `a49a86a7b`; commit `92e04271d`, entrata con `149157025` (treno 162). Due rossi d'altro tipo, sotto
  carico 100+, vanno in Y-22.
  - In `risk-analysis.spec.ts:2812`, alla riga 2828, `expect.poll(offered)` usa il limite predefinito di 3 s.
  - Il 16/10 alle 21:17, con il carico fra 72 e 83, il predicato (`evaluateAll`) non è nemmeno tornato: subito dopo
    l'apertura del replay storico il thread principale è rimasto occupato per più di 3 s. Alla fine il DOM era giusto.
    Alle 20:45, con il carico a 35, era verde.
  - Rimedio: una scadenza vera per i `poll` di quel test, oppure un'apertura del replay che costi meno.
  - Prove in `files/logs/y12b_l4_*` della sessione di Y. Dettagli: piano di Y, «Y12b · E2E».
- ✅ **Y-22 · `risk-analysis.spec.ts` sotto carico 100+: due interazioni che non reggono** — piccolo; Y, 17/10 (seconda
  corsa di Y-21 sulla revisione combinata `a49a86a7b`, carico 94–115). Tutti e due i test erano verdi nelle tre corse
  precedenti. ✅ 17/10: `:3736` ha una scadenza più larga (20 s, con 3 s per tentativo), e da solo ×4 è verde.
  `:2871` ha la sua traccia: ×4 verde, il clic è subito eseguibile. Il verdetto è ambiente, non riprodotto; il test
  resta com'è. Entrata con `d7f3a49c3` (treno 167).
  - `:3736`, la tabella di L3 («each holding's beta and correlation are their own…»). `hoverUntilHelpOpens` non apre
    l'aiuto del «—» entro `HELP_OPEN_DEADLINE_MS`, 10 s.
    - La fotografia mostra la tabella completa: è un'assunzione sull'orologio.
    - Rimedio: una scadenza più larga, per esempio 20 s.
  - `:2871` («a benchmark chosen on the Dashboard is the benchmark in force on Broker Detail»). In `chooseBenchmark`
    (`:1476`), `option.click()` aspetta fino alla fine dei 90 s che l'opzione diventi «visible, enabled and stable»;
    un attimo prima era visibile.
    - Mancano fotografia e traccia, quindi nessun verdetto.
    - Primo passo: quel test da solo con `--trace on`, in uno slot tranquillo.
    - Da guardare anche il `.first()` su tutta la pagina (`search-select-option-*`).
    - Se ricompare, serve la traccia del caso rosso: la configurazione traccia solo `on-first-retry`, e in locale
      non ci sono tentativi ripetuti.
  - Prove in `files/logs/y21_reds_rerun/` e `files/logs/y22_*` della sessione di Y. Dettagli: piano di Y, «Y-21 ·
    seconda corsa» e «Y-22».
- ✅ **Y-23 · I mock di `$app/navigation` nei test del layout non esportano `onNavigate`** — minimo; difetto di Y
  (`ec018afdf`, Y11 passo 2), trovato da A in dev il 17/10.
  - `layout.gate.test.ts` e `layout.authGate.test.ts` (di H) avevano 20 rossi su `front-utility
    onboarding-component-unit`, con la causa «No "onNavigate" export is defined on the "$app/navigation" mock».
  - Allora quell'azione non era fra le mie prove leggere.
  - ✅ 17/10: `onNavigate: vi.fn()` nei due mock (`test-author`); 454/454. Entrata con `d7f3a49c3` (treno 167).
- ✅ **Y-24 · La richiesta delle candele (e del contributo) si riarma da sola dopo ogni errore, senza limite** — medio,
  per il developer, insieme a Y-18; Y, 17/10 (analisi di Y-16). Comportamento preesistente.
  - ✅ 17/10, **la parte del giro** (proposta di Y, via del coordinatore alle 17:47; entrata con `ad5104c4f`, treno 364,
    CHANGELOG `c1bdc380b`): `createLazyReportRetry`
    (`frontend/src/lib/stores/portfolio/lazyReportRetry.svelte.ts`) — dopo un errore, al più tre nuove richieste, 2, 4 e
    8 s dopo, poi nessuna finché cambia l'ambito (broker, periodo, valuta) o arriva un Refresh; nessuna UI nuova. Sulla
    Dashboard e sulla pagina del broker, per le candele e per il contributo; una risposta di un ambito già cambiato non si
    applica più. Sulla pagina del broker le candele, prima, non riprovavano mai (il loro flag non era un segnale): ora
    seguono la stessa regola. Rossi prima (20 d'unità; 7 E2E con l'orologio di Playwright, due dei quali per un buco
    trovato da `docs-writer` e chiuso nello stesso lotto), poi verdi; regressioni `page-busy`, `dashboard`,
    `dashboard-cache`, `front-broker detail`. Dettagli: piano di Y, «Y-24».
  - **Resta per il developer, con Y-18**: l'indicatore e lo stato d'errore delle candele (oggi lo schermo resta vuoto
    durante l'attesa e dopo l'ultimo tentativo).
  - Era:
  - `requestReport` (`stores/portfolio/portfolioStore.svelte.ts`) intercetta l'errore e restituisce `null`.
  - Nella Dashboard e nella pagina del broker, `loadPnlCandles` legge `pnlCandlesLoading` (e `pnlCandles`) dentro
    l'`$effect` di `GrowthChart` (`:975-979`), che quindi ne dipende: alla fine di una richiesta fallita il `finally`
    rimette `loading` a false, l'effetto riparte e chiede di nuovo.
  - Finché il backend fallisce, la vista Candele manda una richiesta dopo l'altra, senza limite e senza attesa.
    `PositionsPanel` (`:112-116`) fa lo stesso per il contributo, ma attraverso la sua prop dichiarata
    `contributionLoading`.
  - Oggi non si vede: lo schermo resta vuoto, come durante il caricamento.
  - Da decidere con Y-18 (l'indicatore e lo stato d'errore delle candele): l'opzione B di Y-16 (una prop esplicita
    `canRequestPnlCandles` più `untrack`) toglie il ciclo, ma serve una «chiave di scope» perché un cambio di periodo
    o un Refresh dopo un errore chiedano di nuovo.
  - Dettagli: piano di Y, «Y-16».
- ✅ **Y-25 · Il ridimensionamento riallinea le frecce a ogni callback, e la riscrittura parte anche senza angoli cambiati**
  — minimo, prestazioni; `test-author` di Y, 17/10 (analisi di Y-8). ✅ 17/10: (a) la riscrittura parte solo se una freccia
  gira di più di 0,01°; (b) i tre `ResizeObserver` riallineano all'assestamento (`LineChart` e `CandlestickChart` riarmano
  quello delle etichette, `PriceChartFull` lascia fare al suo rinvio da 200 ms), mai a ogni callback; (d)
  `noteArrowMarkers`, dopo ogni disegno completo, fa uscire `updateArrowRotations` prima di `getOption()` sui grafici senza
  frecce, cioè quasi tutti. 16 rossi prima (unità, componenti, pin), la prova del morso sul verso pericoloso di (d).
  Entrata con `73443c6db` (treno 237).
  - Il `ResizeObserver` di `LineChart`, `CandlestickChart` e `PriceChartFull` chiama `updateArrowRotations` a ogni
    callback, cioè a ogni frame mentre si trascina il bordo della finestra: una copia di `getOption()` e una riscrittura
    di tutte le serie ciascuna, oltre al `resize()`.
  - `updateArrowRotations` riscrive le serie appena trova una freccia, anche se nessun angolo è cambiato; il primo
    disegno fa tre copie e tre riscritture in circa 50 ms (il disegno e i due passi della stabilità); ogni ridisegno di
    un grafico zoomato ne fa una in più, 120 ms dopo, perché il ripristino dello zoom non è `silent`.
  - Possibili rimedi: rinviare il riallineamento del ridimensionamento come quello dello zoom; non riscrivere quando
    nessun angolo cambia (il test di Y-8 sull'assestamento va allora rifatto con lo zoom vero del registratore di
    Y-8b, che cambia gli angoli).
  - Dettagli: piano di Y, «Y-8 · `updateArrowRotations()` e `getOption()` a ogni passo dello zoom».
- **Y-26 · La vista percentuale dei grafici di prezzo, da un primo valore 0, mostra valori assoluti come percentuali** —
  basso, numeri; Y, 17/10 (revisione di J-44). Comportamento preesistente; serve una scelta del developer.
  - `toDisplaySeries` (`components/charts/priceChartHelpers.ts:369`) rende la serie intatta quando il primo valore è 0
    (lo dice il suo JSDoc): nella vista `%` la linea **e** il Δ del tooltip (`(Δ ${formatPercent(value)})`) mostrano
    valori assoluti come percentuali, cioè un 10 assoluto si legge «+10.00%». J-44 ha tolto lo 0 % solo dalla vista
    assoluta.
  - Altre copie dello stesso ribasamento, con tre comportamenti su una base nulla (regola 10): `computeGhostSeries`
    (`priceChartHelpers.ts:469`, tutto 0 %); `candlestickChartHelpers.toPercent` (`:35`) e
    `charts/signals/backendRenderer.ts::transformValue` (`:37`), il valore grezzo; `lotWacPriceChartHelpers.toPercentSeries`
    (`:130`), che ribasa sul primo valore non nullo e lascia null prima.
  - Da decidere: da un inizio a 0, (a) niente vista `%` (il commutatore spento, con una nota); (b) una serie vuota, `—`,
    cioè `changePct` dappertutto; (c) ribasare sul primo valore non nullo, come il grafico dei lotti. Poi una copia sola
    della regola per tutte.
  - Raro: un prezzo o un cambio esattamente a 0 all'inizio. Dettagli: piano di Y, «J-44 · revisione a posteriori».
- ✅ **Y-27 · `DataTable` pota le preferenze delle colonne assenti, e le colonne Δ le perdono a ogni caricamento** — medio-basso,
  preferenze; Y, 17/10 (revisione di X-R53). Il rimedio (a), affidato a Y dal coordinatore (08:55), lotto a parte. ✅ 17/10:
  `dataTableLogic.ts` con `withNewColumns` (aggiunge solo le colonne mai viste, al posto naturale) e `reorderKeepingAbsent`
  (il riordino rimette una colonna assente dopo quella che seguiva); `DataTable.svelte` tiene tutte le scelte di visibilità
  salvate e non pota più ordine, scelte e larghezze. 14 rossi prima (8 d'unità, 6 di componente con un `localStorage`
  finto). Entrata con `542c0e8b5` (treno 248).
  - `DataTable.svelte` toglie dall'ordine salvato gli id delle colonne assenti e salva subito, e scarta le loro scelte di
    visibilità e le loro larghezze. Da X-R53 le colonne Δ 1W…5Y di Asset e FX mancano al primo disegno (i periodi arrivano
    dal backend), quindi posto, visibilità e larghezza scelti dall'utente si azzerano a ogni caricamento; prima succedeva
    solo quando un intervallo più corto le nascondeva.
  - Dettagli: piano di Y, «Y-27»; devWiki `problems/datatable-pruned-preferences-of-absent-columns`.
- ✅ **Y-28 · Il test C-66 «sync all over a period whose prices are all filled backward» non può più passare dopo X-R55** —
  medio, test rosso su dev; Y, 17/10 (E2E di Y-27). Da instradare dal coordinatore. ✅ 17/10: chiuso da X (`c18517e31`, in dev
  `8aafffad8`): il test lavora su un fine settimana passato, portato avanti, sincronizzato dalla selezione.
  - `frontend/e2e/assets/asset-list.spec.ts:1084` (`32c64bbd9`, 16/10) chiede `POST /assets/prices/query` sul periodo da oggi+7
    a oggi+14 e pretende, come precondizione, che almeno un asset con un fornitore vi mostri prezzi portati avanti.
  - X-R55 (`a71d23e7e`, in dev dalle 08:30 con `ab7711f04`) taglia ogni intervallo a `latest_range_end()`, cioè domani: un
    elemento che comincia dopo riceve un risultato vuoto. Quindi «0 stored of 0 shown» per tutti, e il test cade sulla sua
    precondizione. Verde alle 08:43 su `039af67bb`, senza X-R55; rosso alle 10:05 su `73443c6db`.
  - Da scegliere: riscrivere il test su un periodo passato con giorni portati avanti e non salvati (un fine settimana, un
    festivo), o rivedere il tetto per il caso «sincronizza un periodo futuro». Dettagli: piano di Y, «Y-27», Fuori pista.
- ✅ **Y-29 · Il gate delle eccezioni esenta un file dichiarato anche dall'annualizzazione** — minimo, guardia; Y, 17/10
  (`test-author`, P5). ✅ 17/10: ogni voce di `DECLARED_EXCEPTIONS` dice `annualizes`, vero solo per `MeasureSignal.ts` e
  `CompoundSignal.ts`; la regola (C) ammette esponenti con 365 solo lì; rosso prima, e una guardia che morde. Entrata con
  `ce2452615` (treno 261). `financialMathExceptions.gate.test.ts` dichiara un file intero: la regola (C) (nessun esponente con 365
  fuori dai file dichiarati) non guarda più dentro i tre moduli dei lotti di D-MF6(b), che sommano, mediano e ribasano ma non
  annualizzano. Un'annualizzazione aggiunta un giorno lì passerebbe in silenzio. Rimedio possibile: un segnalino per voce
  («può annualizzare»), vero solo per `MeasureSignal.ts` e le curve di R19. Dettagli: piano di Y, «Y12b, il resto».
- ✅ **Y-30 · Con l'analisi dei lotti `FAILED` il grafico prezzo/WAC perde la linea del prezzo di mercato** — basso,
  chiarezza; Y, 17/10 (J-12, metà del pannello). Il coordinatore (11:4x) l'ha tenuta fuori da J-12. ✅ 17/10 (Y, backend
  compreso; J rivede il backend), via del coordinatore 20:3x: la serie del prezzo senza lotti `MARKET_PRICE_HISTORY` /
  `market_price_history` (`build_market_price_history`), tenuta con `FAILED` (`_REPLAY_FREE_ANALYSES`, con i suoi buchi di
  cambio); il pannello la usa **sempre** al posto dell'unione (decisione notturna N89, per il developer) e pubblica
  `data-price-line`. Committata in `6db475ac9` e `cc80f896f`, entrata con `ede7adf75` (19/10, dopo il sì del
  developer a N89: la linea del prezzo continua anche dopo l'ultima vendita). Dettagli: piano di Y, «Y-30».
  - Con `FAILED` (J-12, N81 opzione A) `price_history` torna `null`, perché è per lotto (`LotPriceHistoryPoint.lot_id`,
    un punto per ogni giorno di vita di ogni lotto). Il grafico costruiva la linea del prezzo dall'unione per data di quei
    punti, quindi mostrava solo le linee del costo medio, e senza lotti aperti la linea si interrompeva.
- ✅ **Y-31 · E2E di J-12: la regola della lingua dell'interfaccia (M-18) ricopiata in una spec, e due stati non
  pubblicati** — basso, test; Y, 17/10 (test-author di J-12). ✅ 17/10, versione minima (coordinatore, 13:21 e 13:36):
  `resolveUiLocale` in `stores/app/uiLocaleRule.ts`, senza import, riesportato da `uiLocale.ts`; la spec lo importa invece
  di ricopiarlo (`uiLocale.test.ts` controlla che il modulo non importi nulla); `LotWacPriceChart` pubblica
  `data-state="drawn" | "empty"` e J12-1 lo legge. Entrata con `8aa8a821e` (treno 294). **Resta, da girare a W** (la pagina delle
  transazioni è sua): il segno durevole della riga di `?highlight=`.
  - `brokers-detail.spec.ts::dayAsThePanelWritesIt` ricopia `resolveUiLocale`, perché Playwright non può importare
    `uiLocale.ts`; anche `fixtures/dates.ts` ricopia `dateOnly`. Se M-18 cambia, J12-1 diventa rosso per un motivo che
    non c'entra. Rimedio: una fixture condivisa della lingua dell'interfaccia.
  - Il grafico WAC non pubblica il suo stato «nessun dato» (il test guarda la tela). La pagina delle transazioni non
    lascia un segno durevole sulla riga di `?highlight=` (il test guarda la navigazione e la modale). Un `data-state` o un
    `data-highlighted` li renderebbe espliciti.
  - Dettagli: piano di Y, «J-12, la metà del pannello».
- **Y-32 · Le card della lista degli asset: prezzo live, Δ della serie** — basso, coerenza, domanda di prodotto per il
  developer; Y, 17/10 (X-R59, D2: il coordinatore ha scelto la parità per il lotto A).
  - La card mostra il prezzo live (`livePriceMap`, dal poll di `/prices/current`), ma la sua Δ sull'intervallo è quella della
    serie, fino al prezzo salvato su `as_of`: dopo X-R59, il `range_change` di `period-changes`. Finché il prossimo
    caricamento non la rilegge, la Δ non segue il prezzo mostrato. Succedeva già prima, con la Δ calcolata nel browser.
  - Rimedio possibile: quando l'intervallo finisce oggi, il poll della lista chiede `/prices/current?range_start=` e la card
    usa quel `range_change`, come la pagina dell'asset (lotto B di X-R59).
  - Attenzione, se si fa: le glob esatte `'**/api/v1/assets/prices/current'` delle spec che restano sulla lista (per esempio
    `asset-list.spec.ts`) non vedono più la richiesta con la query, perché in Playwright la glob è ancorata alla fine. Vanno
    allargate con un `*` finale, come il lotto B ha fatto per le spec che aprono la pagina dell'asset.
  - Dettagli: piano di Y, «X-R59».
- ✅ **Y-33 · `asset-detail.spec.ts`: 10 s per una navigazione a freddo sotto carico** — minimo, stabilità dei test; Y, 17/10
  (slot E2E di X-R59, 16:05). `goToSeededAssetDetail()` (`frontend/e2e/assets/asset-detail.spec.ts:107-114`) clicca la card
  di Apple e dà 10 s alla radice `asset-detail-page`. Al picco di carico dopo la build (carico a 1 minuto 93 alle 15:24) un
  contesto nuovo importa a freddo il bundle grosso della pagina, e «edit button opens asset modal» (`:240`) è caduto lì,
  ancora sulla lista; da solo, a carico normale, passa in 4,1 s, e gli altri test con lo stesso aiuto sono passati. La cura,
  come Y-22: più tempo alla navigazione, oppure aspettare prima l'URL e poi la radice. Spec dell'area degli asset: a chi
  la tocca. Dettagli: piano di Y, «X-R59».
  - ✅ 17/10: dopo il clic, prima l'URL (tetto 30 s), poi la radice (10 s), nell'aiuto e nella copia in riga del test della
    cache degli eventi; commento di `:332` senza totali (`test-author`). E2E `front-asset asset-detail` 39/39. Entrata con `c5b347a46`
    (treno 343); review di X: OK, con una nota chiusa in Y-34.
    Dettagli: piano di Y, «Y-33».
- ✅ **Y-34 · `brokers-detail.spec.ts`: 5 s per il pannello dei lotti dopo «analizza i lotti», sotto carico** — minimo, stabilità
  dei test; gate I, via il coordinatore, 17/10. Review di X. ✅ 17/10: `expectLotsPanelOpen` (prima l'URL con `?asset=`, 30 s,
  poi il pannello, 10 s) ed `expectLotsPanelClosed` per i 12 punti; 60 s sui describe «Live price direction flash» e «Asset
  Detail Page» di `asset-detail.spec.ts`. Entrata in dev `7dbd46aa6` (`69b2fe74e` + `2abcb35d9`). La nota di X a posteriori
  (il parametro `assetId` mai passato) è chiusa dentro Y-30.
  - `:355` («right-clicking a holding row shows a context menu with both actions») aspetta 5 s `lots-analysis-panel` dopo
    l'azione: caduto una volta col carico vicino a 90, verde da solo col carico a 28 (40/40). La stessa attesa di 5 s è in 12
    test del file (`:314`…`:610`). L'azione scrive `?asset=<id>` nell'URL (`assetPanelUrl.ts`), la pagina lo legge in un `$:`
    (`brokers/[id]/+page.svelte` ~:185-189) e monta il pannello sotto `{#if open && assetId != null}`
    (`LotsAnalysisPanel.svelte:470`): una navigazione nella stessa rotta più un montaggio, che sotto carico aspettano un thread
    principale occupato. Stessa classe di Y-33.
  - Rimedio deciso: un aiuto, prima l'URL con `?asset=` (tetto 30 s), poi il pannello (10 s), per i 12 punti.
  - Dentro anche la nota di X sulla review di Y-33: in `asset-detail.spec.ts` i quattro test «Live price direction flash»
    (`:8265`, `:8279`, `:8316`, `:8351`) abbassano il loro timeout a 20 s, sotto il tetto di 30 s dell'URL di
    `goToSeededAssetDetail`: sotto carico cadrebbero su «Test timeout of 20000ms exceeded». Un
    `test.describe.configure({timeout: 60_000})` sul loro describe.
  - **Residuo, da instradare**: `dashboard-cache.spec.ts:295` (`analyzeLots`) è della stessa classe (azione → `?asset=` →
    pannello) con un'attesa sola di 30 s per navigazione e montaggio: regge, ma cadrebbe su «pannello non visibile» invece che
    sull'URL. Le altre attese del pannello (`data-quality-real`, `data-quality-legacy`, `stale-price-banner`) seguono un deep
    link: fuori classe.
  - Dettagli: piano di Y, «Y-34».
- **Y-35 · `PRICE_HISTORY` (il prezzo per lotto) non ha più lettori nell'app** — minimo, domanda per il developer; Y, 17/10
  (Y-30). Dopo Y-30 il pannello dei lotti chiede `MARKET_PRICE_HISTORY`; `PRICE_HISTORY` / `price_history` resta
  nell'API pubblica (`POST /portfolio/lots/analysis`), con i suoi test, e l'AI Export non lo usa. Da decidere: tenerlo
  (API pubblica, nessun costo se nessuno lo chiede) o dichiararlo deprecato e toglierlo in una release successiva.
  Dettagli: piano di Y, «Y-30».
- **Y-36 · Un intervallo con la fine vuota: il frontend dice «da X in poi», il backend «solo X»** — minimo, latente;
  Y, 19/10 (Y-N65, nota di `docs-writer`, verificata).
  - Da Y-N65, nel filtro per data di una tabella una data sola in «Da» vale «da X in poi».
  - Nel backend, `DateRangeModel` (`backend/app/schemas/common.py`) legge `end: null` come un giorno solo, e
    `GET /api/v1/transactions` lo costruisce così da `date_start` senza `date_end`.
  - Oggi non si incontrano: la pagina delle transazioni chiede tutte le transazioni senza parametri e filtra nel
    browser.
  - Da allineare se un giorno il filtro passa al server: o il backend accetta un intervallo aperto, o il frontend
    manda la fine.
  - Dettagli: piano di Y, «Il lotto Y-N65».
- **Y-37 · `datePickers.md`: tre affermazioni che il codice smentisce** — minimo, documentazione; Y, 19/10 (Y-N65,
  nota di `docs-writer`, verificata).
  - Nella sezione `CalendarMonth`: «Keyboard navigation within the grid», ma la griglia non ha tasti (solo
    `numericArrows` sull'anno); «week starts on Monday for most locales», ma parte sempre da lunedì.
  - Il riferimento `DateRangePicker.svelte:36,216-251` (8/10) è approssimato.
  - Y-N65 non li tocca. Dettagli: piano di Y, «Il lotto Y-N65», passo 6.
- **Y-41 · Lista dei cambi: il confronto con un asset si può scegliere, ma non si disegna** — minimo, preesistente; Y,
  20/10 (Y-39a).
  - Nella lista dei cambi la finestra delle impostazioni offre il segnale di confronto con un asset, ma né la scheda né
    l'anteprima lo disegnano: la lista non carica le serie degli asset (`fxListSignalSources` dà `comparisonTarget`
    nullo).
  - Era così anche prima di Y-39a, e resta uguale. Da decidere: caricare le serie (come il dettaglio del cambio) o non
    offrire il confronto in quella lista.
  - Dettagli: piano di Y, «20/10 · Il lotto Y-39».
- **Y-42 · I due dettagli adottano il disegno comune dei segnali** — medio; Y, 20/10 (Y-39a, contratto concordato con
  X).
  - `assets/[id]/+page.svelte` (`overlaySignals`) e `fx/[pair]/+page.svelte` ricostruiscono ancora i segnali locali
    da soli. Possono passare a `lib/charts/chartSignalRendering.ts`: le fonti sono parametri, il punto del cambio porta
    `missing` e `staleDays`, il confronto nome, icona e tipo.
  - Il cancello `src/signalRendering.gate.test.ts` le tiene in `KNOWN_COPIES`, una lista che può solo accorciarsi.
  - Anche `FxCard.svelte` converte i punti del cambio in linea, due volte: può usare `fxPointToLineDataPoint`.
  - File di X (FE4, FE5): da proporre a X tramite il coordinatore. Dettagli: piano di Y, «20/10 · Il lotto Y-39».

## MF · Matematica finanziaria (fase 01)

Workstream nato il 16/10 (decisione del developer su P21). Piano:
[`Phase_1/11_financialMath/plan-phase01FinancialMath.prompt.md`](../Phase_1/11_financialMath/plan-phase01FinancialMath.prompt.md);
punto di partenza, l'audit dello stesso giorno:
[`Phase_1/11_financialMath/audit-matematica-finanziaria-20261016.md`](../Phase_1/11_financialMath/audit-matematica-finanziaria-20261016.md).

- **MF-A…MF-P · I 16 lotti dell'audit** — tutti nella 1.3 per decisione del developer (16/10). Voci per lotto
  scritte da MF nell'analisi del 16/10 (base `f77743d47`); la ripartizione con J (CP-3, CP-5, U3/U7, CP-12, CP-13) è
  la domanda Q1 al coordinatore. Ordine e ondate: piano MF, §4.
  **Stato al 19/10**: 14 lotti su 16 ✅ (A, B, C, D, F, G, H, I, J, K, M, N, O, P); aperti **E** (E2, gli short nello
  storico: esposizione lorda approvata il 19/10, in coda dopo P2 e MF-P1b) e **L** (D-MF1, domanda al developer).
  Tabella: piano MF, «Stato dei lotti (19/10)».
- ✅ **MF-A · Contributo per posizione dal motore** (CP-3 di J: B8, V2/P2, R4, B19; TRANSFER per broker secondo P22) —
  grande, numeri; audit 16/10. Dettagli: [piano MF](../Phase_1/11_financialMath/plan-phase01FinancialMath.prompt.md),
  sezione «MF-A».
  **Entrato** il 17/10: dev `536501541` (la tabella Performance valutata dal motore). Seguito MF-A2 (doc) in corso.
- ✅ **MF-B · NAV e utile per broker dal motore** — piccolo; audit 16/10. Dettagli: piano MF, sezione «MF-B».
  **Entrato** il 16/10: dev `bcc644491`.
- ✅ **MF-C · Una funzione «pesi» nella casa, HHI unico** (con i due difetti di Y su `allocation_percent` e
  `nav_weight_percent`; T-U7, W1–W5) — piccolo-medio, numeri nei casi limite; audit 16/10, Y. Decisione D-MF7.
  Dettagli: piano MF, sezione «MF-C».
  **Entrato** il 16/10: dev `0eb85aa9b`. Seguito: MF-C2 (decisione).
- ✅ **MF-D · Rapporti, rendimenti di prezzo, annualizzazione, composizione** (R6–R10 del 43; `drawdown_context.py:498`
  senza guardia sullo zero) — piccolo; audit 16/10. Dettagli: piano MF, sezione «MF-D».
  **Entrato** il 16–17/10: prima parte dev `8d244d1c6` (ondata 1/1b), resto dev `aca75c7ca`, D3 `482343eb3`, D4
  `c2feaf3e4`.
- **MF-E · Sintesi del lotto nella casa, segno dei corti nella storia di performance, T-B8** — medio, numeri (corti
  aperti); audit 16/10, riverifica MF (`histories.py:63-72`). Dettagli: piano MF, sezione «MF-E».
  **E1 entrato** il 17/10: dev `e43dfae68`. **E2** (corti nella storia di performance): il 19/10 il developer approva
  l'esposizione lorda con le D1–D3 di MF; via il 20/10 (E2-Q1: capitale = incassi cumulati, coordinatore); codice e test
  pronti il 20/10 (232 + 1 test, 17 + 1 rossi prima), in attesa dello slot e del checkpoint; la parità si rifà dopo L1a.
- ✅ **MF-F · Segno del reddito nei lotti e nella timeline dei redditi dell'AI Export** (O3, B9) — piccolo, numeri; audit
  16/10. Decisione D-MF3. Dettagli: piano MF, sezione «MF-F».
  **Entrato** il 16/10: F1 e F2 in dev `8d244d1c6`.
- ✅ **MF-G · Quantità e cassa senza `SUM` SQL** (PAC; `balances.py` col via di W, accanto a W-B19; O4) — piccolo-medio;
  audit 16/10. Dettagli: piano MF, sezione «MF-G».
  **G1 entrato** il 16/10 (dev `8d244d1c6`); **G2** (`balances.py`) resta col via di W, accanto a W-B19.
  **Chiusa** (riconciliazione del 19/10): G2 l'hanno fatta altri lotti — `transactions/balances.py` legge
  `ledger_totals.position_quantities` per le quantità (C-97, `bab52635d`) e `native_cash.native_balances` per la cassa
  (W-B19, `6be11ecf3`); nessun `SUM` SQL resta.
- ✅ **MF-H · Finestra di detenzione nella casa** (T-B4, T-U6, L1–L2) — piccolo-medio, numeri; audit 16/10. Decisione
  D-MF2. Dettagli: piano MF, sezione «MF-H».
  **Entrato** il 16/10: dev `bcc644491` (D-MF2 = arrivo al broker).
- ✅ **MF-I · Un caricatore degli split, `financial_math/splits.py`** (T-U2, S1–S3) — piccolo; audit 16/10. Dettagli:
  piano MF, sezione «MF-I».
  **Entrato** il 16/10: I1 dev `8d244d1c6`, I2 dev `3741b95b0`.
- ✅ **MF-J · `DailyStateBuilder` più lineare** (J1 refactor senza pre-frame; J2 ripartizione K/R all'arrivo) — medio
  (J1), piccolo-medio (J2, numeri); audit 16/10. Decisione D-MF4. Dettagli: piano MF, sezione «MF-J».
  **Entrato** il 17/10: J1 dev `d93de2899`, J2 dev `04a5088ff`. Seguiti: MF-J3 (decisione), MF-J4 (J).
- ✅ **MF-K · Un MWRR solo** (un costruttore dei flussi, una politica della radice; card = grafico anche con prelievi
  netti) — piccolo-medio, numeri; audit 16/10, riverifica MF (`portfolio_service.py:882`). Decisione D-MF5. Dettagli:
  piano MF, sezione «MF-K».
  **Entrato** il 16/10: K1 e K2 in dev `8d244d1c6`. Seguito: MF-K3 (decisione).
- **MF-L · `BRSummary.holdings`: togliere o valutare col motore** — piccolo/medio, API; audit 16/10. Decisione D-MF1,
  file di W. Dettagli: piano MF, sezione «MF-L».
- ✅ **MF-M · PAC: prova del cambio del WAC da `CostStep.conversion`** — piccolo; audit 16/10. Dettagli: piano MF, sezione
  «MF-M».
  **Entrato** il 16/10: dev `8d244d1c6`.
- ✅ **MF-N · AI Export: efficienza dei costi con la quota effettiva** (O3, B9) — piccolo, numeri (AI Export); audit
  16/10. Dettagli: piano MF, sezione «MF-N».
  **Entrato** il 16/10: dev `8d244d1c6`.
- ✅ **MF-O · Yield on Cost: mai il WAC convertito al cambio di `as_of`** — minimo; audit 16/10. Dettagli: piano MF,
  sezione «MF-O».
  **Entrato** il 16/10: dev `8d244d1c6`.
- ✅ **MF-P · Campi del backend per il frontend** (T-U8 lato backend, CP-13 meno CP-13a; W8, P4, P5, V11, R17 di Y; il
  consumo è di Y) — medio; audit 16/10, Y12a. Decisione D-MF6. Dettagli: piano MF, sezione «MF-P».
  **Lato backend entrato** il 17/10: P dev `536501541`, P4b `d93de2899`, P2 `aa4370905`, P2b `c9b1162d4`; il consumo
  nel web app è di Y.
  **Chiusa per MF** (19/10): il backend è entrato e Y lo usa; il consumo resta nelle voci di Y.
- ✅ **MF-O2 · Yield on Cost: un reddito netto negativo nella finestra fa fallire il report** — basso (dati legacy),
  robustezza; test-author di MF, 16/10 (letto nel codice, non provato). Il reddito per unità somma i redditi col segno
  (`yield_on_cost.py`, `_calculate_income_position`): se nei 365 giorni le correzioni negative superano i dividendi, il
  risultato `AVAILABLE` ha un valore negativo che il validatore di `YieldOnCostResult` rifiuta
  (`schemas/portfolio.py:335-340`), con un errore invece di «—». Cura proposta: `UNAVAILABLE` con un motivo nuovo
  (`negative_net_income`) nello schema di J, poi `api sync` e l'etichetta nei 4 cataloghi; rosso prima. Dettagli: piano
  MF, sezione «MF-F1».
  **Chiusa** il 16/10: `negative_net_income`, dev `8d244d1c6` (commit `2650a7da4`).
- **MF-K3 · La card e la linea del TWRR e del ROI semplice in due casi limite** — basso, numeri (proposta, da decidere);
  test-author di MF, 16/10 (K2). (1) Come l'MWRR prima di D-MF5: la card calcola il TWRR solo con NAV > 0
  (`portfolio_service.py`, `get_summary`), la linea (`calculate_twrr_series`) no: col portafoglio svuotato la card dice
  «—» e la linea resta piatta a −50 %. (2) Come l'MWRR prima di N54: il ROI semplice della card
  (`period_net_invested = Σ −flussi`) e la sua linea (`calculate_simple_roi_series`) vedono 0 di capitale quando
  l'intervallo comincia prima del primo giorno del portafoglio, quindi ROI 0. Proposta: le stesse regole (D-MF5, N54)
  anche per TWRR e ROI, nella casa, con i rossi prima; serve l'ok del developer (cambia card e grafico). Dettagli: piano
  MF, sezione «Ondata 1b», K2.
- **MF-C2 · Le fette d'allocazione su una somma che si annulla o va sotto zero** — basso, numeri (proposta, da decidere);
  test-author di MF, 16/10 (lotto C). Le fette dei grafici d'allocazione (`derived_views.py`, `_alloc` e
  `build_allocation_history`, ora `weights.slice_percents`) dividono per la somma con segno, e per 1 quando la somma è 0:
  con la liquidità negativa che annulla le posizioni (`{Azioni: 500, Liquidità: −500}`) escono 50000 % / −50000 %, e
  con una somma negativa (NAV < 0) ogni fetta cambia segno. È lo stesso difetto che D-MF7 toglie ai pesi delle
  posizioni; il lotto C l'ha lasciato identico apposta, fissato nei test (`test_weights.py`, «net-zero» e
  «negative-sum»). Proposta: con una somma ≤ 0 le fette restano `value` null («—») e gli importi restano; serve l'ok
  del developer (cambia il grafico, lo schema — `AllocationItem.value` oggi obbligatorio — e il dataset AI Export
  che lo copia, `portfolio_financial.py:251-253`). Dettagli: piano MF, sezione «Lotto C».
- ✅ **MF-W56 · L'anteprima del WAC arrotondata alla colonna dov'è usata** — basso, numeri oltre la 12ª cifra; W (W-B56) e
  MF, 17/10. `compute_wac_iterative` (facciata di `portfolio_service`) restituisce un WAC non arrotondato, a volte
  periodico: «congelato» in un costo manuale è rifiutato da C-97a (D2), e il costo automatico
  (`auto_cost._write_auto_cost`) lo scrive così in `cost_basis_override`. Cura concordata: alla facciata
  `round_computed_value(…, Transaction, "cost_basis_override")` (D6), mai nella casa (`average_cost` resta esatto). Di
  MF dopo MF-E, rossi prima. Dettagli: piano MF, sezione «MF-W56».
  **Chiusa** il 17/10: dev `04a5088ff` (commit `c129e82a9`).
- ✅ **MF-A2 · Documentare l'annualizzato delle posizioni chiuse nel periodo e la definizione del non realizzato** — basso,
  **chiusa il 17/10**: dev `4507f7507` (J: le tre pagine coincidono col motore).
  doc; MF (docs-writer), 17/10. `period-pnl`/`net-annualized-return` non dicono che una posizione chiusa nel periodo
  annualizza sul costo venduto e sul suo tempo di volo; `portfolio-engine/index` §5 definisce il non realizzato come
  NAV − Book (transito incluso) mentre il periodo usa valore di mercato − costo aperto (§7 ora lo dice). Dettagli:
  piano MF, sezione «MF-A — codice».
- **MF-A3 · Una posizione chiusa presto nel periodo annualizza sull'anno intero** — basso, numeri (domanda, da
  decidere); docs-writer di MF, 17/10 (MF-A2). Quando la regola delle posizioni chiuse non dà valore (nulla venduto al
  costo, o meno di 30 giorni tenuti: `closed_position_annualized`, `returns.cumulative_to_annualized`),
  `period_annualized` ricade sulla regola generale, |StartValue| su t₀→t₁: una posizione tenuta a t₀ e venduta dopo 10
  giorni d'un periodo d'un anno è annualizzata sull'anno. Documentato com'è (`net-annualized-return` «Positions Closed
  in the Period»). Scelte: (a) com'è; (b) «—» quando la regola chiusa non vale. Dettagli: piano MF, «MF-A2».
- ✅ **MF-A4 · Doc: il «non realizzato» della card punta alla pagina sbagliata** — minimo, doc; docs-writer di MF, 17/10.
  **Chiusa il 17/10**: il collegamento a `period-pnl` nelle quattro lingue e le descrizioni API, dev `a228b9d30`.
  `book-value.en.md` definisce il non realizzato come NAV − Book; `user/dashboard/kpi-cards.en.md:31` collega la card
  **Unrealized change** (che mostra la cifra di periodo, valore di mercato − costo aperto) a quella pagina; le
  descrizioni API di `period_unrealized_gain_loss_*` non dicono MV − OCB. Cura: il collegamento a
  `portfolio-engine/index#two-unrealized-figures` e una riga nelle descrizioni (`api sync`).
- **MF-J3 · Un trasferimento di cassa che attraversa il confine del perimetro non tocca i pool K/R** — basso-medio,
  numeri (proposta, da decidere); test-author e docs-writer di MF, 17/10 (J2), provato con una sonda su HEAD e su J2.
  Una gamba `linked_external_inflow`/`_outflow` (l'altra gamba è in un broker fuori dal perimetro scelto) entra nel
  capitale di riferimento come un versamento o un prelievo (`deposited-capital`, riga 33), ma `_apply_pool_rule` non la
  tratta: la cassa si muove, i pool no. Con il perimetro {B} e 650 in arrivo da A, la scomposizione dice versato 0 /
  generato 650 (capitale di riferimento 650); con B che aveva già K 100 e R 100, 425 / 425 invece di 750 / 100.
  Proposta: la gamba esterna in entrata come un DEPOSIT in K (senza il recupero di W, che è globale), in uscita come un
  WITHDRAWAL (K prima, poi R → W); da verificare anche le gambe orfane. Rossi prima; serve l'ok del developer (cambia
  la scomposizione della cassa nelle viste filtrate per broker). Dettagli: piano MF, sezione «MF-J2 — codice e misura».
- **MF-J4 · L'avviso di quote diverse non scatta per una coppia dello stesso giorno** — minimo, qualità dei dati;
  test-author di MF, 17/10 (J2). In `classifier.py` l'avviso «share mismatch» d'una coppia interna fra broker posseduti
  a quote diverse sta dentro il ramo `tx.date != paired.date`: una coppia dello stesso giorno non lo produce. Il divario
  è un risultato nel P&L (J2), l'avviso spiega perché. Da vedere con chi possiede la qualità dei dati (J). Dettagli:
  piano MF, sezione «MF-J2 — codice e misura».
- ✅ **MF-D3 · Il fattore d'annualizzazione riscritto nei validatori degli schemi del rischio** — minimo, nessun numero;
  **chiusa il 17/10**: `returns.observations_per_year`, letto dai due validatori (decisione D3 del coordinatore: uno
  schema può importare una funzione pura della casa; regola 8), commit `ad399d383`, entrato in dev `482343eb3`.
  MF, 17/10 (MF-D resto). `schemas/risk.py:514` e `:595` ricalcolano `n_observations * 365 / calendar_days` per
  controllare l'invariante del contratto, accanto alla funzione della casa `returns.observed_annualization`. Gli
  schemi non importano servizi per scelta: oggi è un controllo dichiarato, non una seconda implementazione. Da
  decidere se resta così (riga nella pagina dev) o se la formula scende in un modulo che entrambi possono leggere.
  Dettagli: piano MF, sezione «MF-D resto».
- ✅ **MF-SI1 · La storia della Scheduled Investment da «min» solleva** — basso, preesistente; test-author di MF, 17/10
  **chiusa il 17/10**: commit `f37b1d0ea`, entrato in dev `16f8c74ed`.
  (R13-SEC7-2). `get_history_value(start_date="min")` confronta il letterale `"min"` con le date
  (`start_date < min(cached.keys())`) e filtra gli eventi con `start_date` invece di `effective_start`: solleva
  `CALCULATION_ERROR`, su HEAD come dopo SEC7-2. La via del refresh può passare `"min"`. Cura: `effective_start` in quei
  due punti, rossi prima. Dettagli: piano MF, sezione «R13-SEC7-2».
- ✅ **MF-SI2 · Scheduled Investment: un tetto agli `asset_events` e un limite per utente alla sonda** — basso,
  **chiusa il 17/10**: `SCHEDULE_MAX_EVENTS` 10 000, la sonda a 30 al minuto per utente (`LIBREFOLIO_PROBE_RATE_LIMIT`,
  0 = spento, le corsie spente), commit `ad399d383`, entrato in dev `482343eb3`; la lettura a ogni sonda col lotto
  MF-SEC9a.
  sicurezza sotto soglia; E, 17/10 (revisione di R13-SEC7-2). Gli eventi manuali di un piano non hanno un numero
  massimo (costo lineare, solo il corpo della richiesta li limita), e `POST /assets/provider/probe` non ha un limite
  per utente. Proposta: un tetto agli eventi (p. es. 10 000) nello schema, e il limite della sonda dove vivono gli altri
  limiti delle richieste. Dettagli: piano MF, sezione «SEC7-2 entrato; MF-SI1».
- ✅ **MF-J45a · L'esecutore del motore non è chiuso allo spegnimento** — minimo; docs-writer di MF, 17/10 (J-45).
  **Chiusa il 17/10**: `shutdown_engine_executor()` nel passo `portfolio-engine` dello spegnimento, commit
  `ad399d383`, entrato in dev `482343eb3`.
  `_ENGINE_EXECUTOR` (`financial_math/portfolio/engine.py`) non è nella sequenza di spegnimento dell'app: una
  ricostruzione in corso tiene il processo fino alla fine, come l'esecutore predefinito di `asyncio.to_thread`.
  Proposta, se serve: `shutdown(wait=False, cancel_futures=True)` nel lifespan. Dettagli: piano MF, sezione «J-45».
- ✅ **MF-J45b · Nessun single-flight sulla cache del motore** — basso, carico; J, 17/10 (revisione di J-45). **Chiusa il
  17/10**: `_IN_FLIGHT` per chiave e intervallo in `calculate`, dev `a228b9d30`. Tra la
  lettura della cache `portfolio_blob` (`portfolio/engine.py` ~:316) e la sua scrittura (~:457) nessun lucchetto: due
  richieste identiche concorrenti ricostruiscono entrambe (con J-45 occupano i due worker). Nessuna azione ora; cura
  possibile: un `asyncio.Future` per chiave in volo. Dettagli: piano MF, sezione «J-45».
- ✅ **MF-SEC8-2a · Un avviso di qualità dati per le righe datate prima del 1900** — basso; coordinatore, 17/10 (decisione 2
  **chiusa il 17/10**: avviso `TRANSACTIONS_BEFORE_FLOOR` (warning, senza CTA), commit `871f75a38`, entrato in dev
  `482343eb3`; il caso API con `ad399d383`.
  di MF-SEC8-2). N74 impedisce le nuove; quelle già salvate si rigiocano ma la storia parte dal 1900-01-01 senza dirlo.
  Proposta: un codice `TRANSACTION_BEFORE_FLOOR` (INFO) con `navigate_asset`/il broker. Dettagli: piano MF, sezione
  «MF-SEC8-2».
- ✅ **MF-SEC8-2b · `date.min − 1 giorno` fuori dalla ricostruzione** — minimo, preesistente; MF, 17/10 (decisione 3 di
  **chiusa il 17/10**: `day_before()` accanto a `shift_date()`, commit `e864827d3`, entrato in dev `482343eb3`.
  MF-SEC8-2). Una coppia con l'arrivo datato `0001-01-01` (`portfolio/classifier.py:217`, `arrival.date − 1`) e un
  provento datato `0001-01-01` (`financial_math/yield_on_cost.py:631`) sollevano `OverflowError`. Cura: confrontare prima
  di sottrarre, o partire da `EARLIEST_RANGE_START`. Rossi prima. Dettagli: piano MF, sezione «MF-SEC8-2».
- ✅ **MF-SEC9a · Altri 500 dei prezzi che ripetono l'errore; `DELETE /prices` senza tetto** — basso, sicurezza;
  **chiusa il 17/10**: prima parte dev `dd416f5bb` (commit `34cc1a58b`), il resto (BRIM, WAC, bisezione LOW-1) dev
  `29e30b6cc`; E, W e H OK.
  test-author di MF, 17/10 (R13-SEC9). In `api/v1/assets/prices.py` restano `detail=str(e)` sui 500 di `POST /prices`
  (~:90), `DELETE /prices` (~:104) e `POST /prices/sync` (~:249). `DELETE /prices` costruisce un termine OR per
  intervallo senza tetto agli elementi: da ~1000 intervalli SQLite risponde «Expression tree is too large», un 500 che
  ripete l'SQL. Altre query con un termine OR per elemento, da verificare se raggiungibili con tanti elementi:
  `fx/storage.py:262`, `brim_provider.py:2030`, `fx/sync.py:234`, `pac_allocator/source/wac.py:44`. Cura: messaggio
  generico + log, `MAX_BULK_ITEMS`, blocchi come `FX_PAIRS_PER_QUERY`. Dettagli: piano MF, sezione «R13-SEC9».
  **In corso (17/10)**, allargata da E (revisione di R13-SEC9): anche `fx/storage.py:139`/`:262`, `price_store.py:461`,
  `fx/sync.py:234` in blocchi (`utils/sql_chunks.OR_TERMS_PER_QUERY`), un tetto di scrittura `MAX_BULK_WRITE_ITEMS`
  (10 000) su `POST`/`DELETE /fx/currencies/rate` e `DELETE /prices`, la sonda letta a ogni chiamata. Restano da
  verificare `brim_provider.py:2030` e `pac_allocator/source/wac.py:44`. Dettagli: piano MF, sezione «MF-SEC9a».
- ✅ **MF-J45c · Il report in cache `portfolio_layer2` è un oggetto condiviso fra le richieste** — minimo, robustezza;
  **Chiusa il 17/10**, dev `ab74aafbf`: guardia `test_financial/test_portfolio_l2_report_shared.py` (API, rischio, AI Export intero), nessuna
  scrittura trovata, nessun cambio di prodotto. Nota: i risultati del rischio portano l'oggetto `data_quality` del report
  in cache tale e quale (secondo riferimento, oggi nessuna scrittura; la guardia la vedrebbe).
  test-author di MF, 17/10 (MF-J45b). Come il risultato del motore (ora condiviso anche dal single-flight, con una
  guardia che i consumatori non lo modificano), il report Pydantic di `_portfolio_l2_cache` (`portfolio_service.py`,
  30 minuti) è restituito tale e quale a ogni richiesta: un consumatore che lo modificasse in luogo cambierebbe le
  risposte degli altri. Nessun caso visto; una guardia simile (istantanea profonda prima e dopo) lo fisserebbe.
  Dettagli: piano MF, «MF-J45b».
- ✅ **MF-J45d · Un errore deterministico della costruzione fa riprovare i seguaci uno dopo l'altro** — basso, carico; J,
  17/10 (revisione di MF-J45b). **Chiusa il 17/10**: l'errore del capofila arriva ai seguaci, `_LeaderGone` solo per la
  cancellazione; nit di doc sull'intervallo esatto; dev `685d76dab`. Compromesso dichiarato: anche un errore transitorio
  del capofila fa fallire i seguaci. Dettagli: piano MF, «MF-J45d».
- **MF-SEC9d · Nessun tetto globale alle chiamate concorrenti per fornitore** — basso, carico; E, 17/10 (revisione di
  R13-SEC9). Il semaforo di `get_current_prices_bulk` limita una richiesta, non il processo: 1 000 id distinti con un
  fornitore lento sono ~33 minuti di chiamate in uscita per richiesta, e più richieste si sommano. Proposta: un
  semaforo per fornitore, condiviso fra richieste e scheduler, accanto alle pause dopo un 429. Solo informazione per ora.
  Dettagli: piano MF, sezione «MF-SEC9a».
  **Entrata la prima parte** il 17/10 (dev `dd416f5bb`, E OK); il resto — `brim_provider.py` (soglia reale ~90 titoli
  con ISIN, ticker e nome: l'`or_()` annidato del nome conta 7 termini) e `wac.py`, più il ciclo di conteggio di
  `delete_rates_bulk` per bisezione (LOW-1 di E) — col lotto «BRIM/WAC/SEC9c».
- ✅ **MF-SEC9e · `bulk_delete_prices` conta con una query per intervallo** — basso, prestazioni; E, 17/10 (revisione di
  **chiusa il 17/10**: conteggi esatti dalle righe lette a blocchi, dev `4507f7507`.
  MF-SEC9a). Prima del DELETE a blocchi, i conteggi per asset sono una `COUNT` attesa per intervallo: fino a 10 000
  query al tetto `MAX_BULK_WRITE_ITEMS`. Lento, non blocca il ciclo degli eventi. Cura possibile: contare dalle righe
  lette a blocchi (id per asset), che rende esatti anche gli intervalli sovrapposti (oggi contati due volte).
  Dettagli: piano MF, sezione «MF-SEC9a».
- ✅ **MF-SEC9g · La classificazione dei candidati BRIM ferma il ciclo degli eventi** — medio, carico; E, 17/10 (revisione
  **chiusa il 17/10**: classificazione in `asyncio.to_thread` con indici ISIN/ticker esatti, dev `650c02b17`.
  del resto di MF-SEC9a). In `search_asset_candidates_bulk` (`brim_provider.py` ~2073) la catena di priorità in memoria
  scorre l'universo più volte per titolo, con 8 `_contains` per nome: O(titoli × universo) in Python sul ciclo. Misure di
  E con 5 000 asset: dati realistici 1 000 titoli 0,5 s, 3 000 4,5 s; nomi generici 90 titoli 7,9 s, 1 000 104 s. Prima
  dei blocchi il parse falliva oltre 91; ora gira, e il fermo arriva più in là. Cura: la classificazione in
  `asyncio.to_thread` (gli oggetti ORM sono già caricati) più indici per ISIN e ticker esatti; i test di parità
  guardano la riscrittura. Revisore W. Sonde in `files/mfsec9a_rest/probe/` di E. Dettagli: piano MF, «MF-SEC9g».
- ✅ **MF-A5 · Un trasferimento in uscita parziale falsa la regola delle posizioni chiuse** — basso-medio, numeri, nella
  **chiusa il 17/10**: il costo spostato nella base, la ricaduta per ogni altra uscita, dev `aa52a43f7`; la nota di
  doc di J inclusa. Seguito MF-A8 (il lato ricevente).
  1.3; J, 17/10 (revisione di MF-A2). La base è il costo delle unità vendute, ma il numeratore porta anche il P&L delle
  unità uscite per trasferimento (ΔUGL e il ritocco del tratto). Esempio: 10 unità, costo 1 000, valore iniziale 1 100;
  vendute 5 a 625, 5 trasferite a un broker del perimetro che valgono 600 all'arrivo: P&L di riga +125, la regola dà
  25 %, il giusto ~12,5 %. Cura: la regola chiusa solo se ogni unità è uscita con una cessione che il Realizzato conta,
  altrimenti la ricaduta (o il costo uscito nella base). Rossi prima. Con la nota di doc di `net-annualized-return`
  («scesa alla soglia della polvere o sotto»). Dettagli: piano MF, «MF-A5».
- ✅ **MF-A8 · Il lato ricevente della base delle posizioni chiuse** — medio-basso, numeri, nella 1.3; J, 17/10 (revisione
  **chiusa il 17/10**: Σ(V_arrivo − C_spostato) dei tratti ricevuti nella base, dev `bc466d969`.
  di MF-A5). Una riga che riceve unità da un tratto contato misura il suo P&L dal loro valore all'arrivo (−tratto), ma
  la sua base (il costo delle vendite) resta il costo storico. Esempio: comprato a 500 da A, spostato a B quando vale
  600, venduto da B a 660: +60 su 500 = 12 %, il giusto 60/600 = 10 %. **In corso (17/10)**: Σ(V_arrivo − C_spostato)
  dei tratti ricevuti nella base (la scelta preferita da J). Dettagli: piano MF, «MF-A8».
- ✅ **MF-A9 · Una riga ricevente ancora aperta annualizza sul costo storico** — basso, numeri (proposta);
  **chiusa il 17/10**: base `end_cost + Σ(V_a − C_a)` per le righe senza valore iniziale e senza uscite nel periodo,
  dev `130002b5c` (clausola CHANGELOG `5726486bc`).
  MF, 17/10 (MF-A8). Una posizione aperta nel periodo che ha ricevuto unità da un tratto contato e le tiene alla fine è
  annualizzata sul costo alla fine (storico), mentre il suo risultato le conta dal valore all'arrivo: nella catena
  A→B→C la riga di C dà 5/500 invece di 5/645. Cura possibile, il rovescio di MF-A8 sul costo alla fine:
  `annualized_period_return(..., end_cost + Σ(V_a − C_a))`. Rossi prima. Dettagli: piano MF, «MF-A8».
- **MF-A6 · La polvere rompe l'identità del §7** — basso, numeri, dopo la 1.3; J, 17/10 (revisione di MF-A2). Lo stato
  **Lato doc entrato (17/10, con MF-A7, dev `09d29671d`)**: §7 e `period-pnl` dicono «polvere a parte»; l'allineamento di
  `daily_state.py` alla stessa soglia resta dopo la 1.3 (coordinatore).
  giornaliero valuta ogni quantità > 0, le righe considerano ≤ 1e-5 come non tenuta: la stessa soglia dai due lati, o il
  §7 dice «polvere a parte». Dettagli: piano MF, «MF-A5».
- ✅ **MF-A7 · `oldest_open_lot_date` senza soglia della polvere** — basso, numeri, dopo la 1.3; J, 17/10 (revisione di
  **Chiusa il 17/10** (nella 1.3 per il coordinatore), dev `09d29671d`, CHANGELOG `5af05312b`: i lotti più vecchi che insieme tengono la polvere o meno sono messi
  da parte, None se la posizione tiene solo polvere.
  MF-A2). Un residuo di polvere può spostare l'inizio della finestra di ricaduta dell'annualizzato. Dettagli: piano MF,
  «MF-A5».
- ✅ **MF-A10 · Le finestre di detenzione leggono la quantità grezza, le righe quella alla quota** — basso, numeri, nella
  1.3 (coordinatore); J, 17/10 (revisione di MF-A7). **Chiusa il 17/10**: dev `4753b66f6`, CHANGELOG `e6d3e61e0`. `quantity_moves` → `oldest_open_lot_date`,
  `closed_position_window` leggono `tx.quantity`; il test della polvere della riga (`is_fully_sold`, `qty_at_end`) e la
  lista delle posizioni leggono la quantità del motore alla quota (`daily_state.py:380`). Su un broker posseduto in
  parte (s < 1) un residuo in (polvere, polvere/s] è polvere per la riga e non per la finestra: s = 0,5, residuo
  0,000012 del 2015 e un BUY del 2024 → la finestra parte ancora dal 2015; chiusa a polvere/quota con residuo grezzo
  sopra la polvere → `closed=None` (A2/A5). Cura: la convenzione del motore, `quantity_moves(..., share=…)`, i due
  chiamanti passano la quota del broker. Rossi prima con s = 0,5. Dettagli: piano MF, «MF-A10».
- **MF-A11 · Una base unica per le righe aperte nel periodo** — basso-medio, numeri (**da decidere, developer**); J,
  17/10 (revisione di MF-A9). Proposta di J: ogni riga aperta nel periodo prende la base `costo alla fine +
  closed_position_base(cost_sold, sales, moved_out, exits, moved_in)` quando ogni uscita è coperta, altrimenti il solo
  costo alla fine come oggi; la finestra parte dalla prima apertura nel periodo. Toglie il limite di MF-A9 (righe con
  uscite) ed è continua all'ultima vendita: oggi −10 % da aperta contro −1 % da chiusa. Cambia valori: nelle domande
  del developer (coordinatore). Caso estremo trovato col test di MF-A10: a broker intero un residuo di 0,000012 (sopra
  la polvere) lascia una riga tenuta con costo alla fine 0,0012, e l'annualizzato vale 1 774 600,33 (oggi): con la base
  proposta (0,0012 + il costo venduto) torna sensato. Dettagli: piano MF, «MF-A10».
- ✅ **MF-A12 · La variazione d'un giorno delle posizioni scritta in linea** — minimo, nessun valore (salvo un pareggio
  **Chiusa il 17/10 (N92)**: dev `5a6d71a1e`, CHANGELOG `5d87dec28`; `change_ratio` per le due colonne; identico al bit per ogni prezzo positivo, un prezzo negativo
  prende il segno della mossa.
  d'arrotondamento); MF, 17/10 (analisi di J-14). In `get_summary` `price_change_1d = ((corrente − precedente) /
  precedente).quantize(0,0001)` (`portfolio_service.py` ~:745) e `gain_loss_change_1d_percent = (variazione / |valore
  precedente| × 100).quantize(0,01)` con la guardia `|precedente| > 0,01` (~:759), accanto a `returns.price_return`
  (`fine/inizio − 1`) e `returns.change_ratio`. Nella 1.3 dopo J-14 se resta piccola (coordinatore): test di parità, il
  pareggio dichiarato. Dettagli: piano MF, «J-14 — analisi».
- **MF-A13 · Il tasso di cambio d'un punto di prezzo ricavato per divisione, tre volte** — medio, ultima cifra; **dopo la
  1.3** (coordinatore, 17/10); MF, 17/10 (J-1, voce 3: `series_preparation.py:184`, U1/CP-11). `price_query` converte
  il close con `convert_bulk` e poi ricava il fattore `convertito / originale` (`assets/price_query.py:651-652`);
  `market_series.py:167` (`close / native_close`) e `ai_export/components/asset_resources.py:209` lo ricavano di nuovo.
  Cura: portare sul punto il tasso usato (in `backward_fill_info` o in un campo dello schema dei prezzi) e leggerlo,
  senza divisioni. **Misura prima**: sul DB di prova (o una copia), per ogni punto convertito, il fattore ricavato
  contro il tasso di `convert_bulk` — quante differenze, a quale cifra, e se toccano valori arrotondati visibili
  (serie di mercato, AI Export: la sonda mirata dice se serve un aumento di versione). File di X (`price_query`, schema
  dei prezzi), di J (`market_series`) e AI Export; dopo il PL4 di X (D-J17). Dettagli: piano MF, «J-1 —
  riconciliazione».
- **MF-SEC9f · Altri OR per elemento, censiti da E** — minimo, informazione; E, 17/10 (revisione di MF-SEC9a).
  `scheduler/jobs.py:100` costruisce un termine per coppia configurata: rifiutato solo con ~1 000 coppie, improbabile.
  `portfolio/engine.py:133` è sicuro. Nessuna azione ora. Dettagli: piano 08 di E, «MF-SEC9a».
- **MF-SEC9b · `Currency.validate_code` accetta nomi e codici numerici** — basso, preesistente, tutta l'app;
  test-author di MF, 17/10 (Y D1). La ricerca generale di pycountry accetta `EURO`, `978`, `US Dollar` e restituisce
  l'input in maiuscolo (`EURO`, `978`, `US DOLLAR`), non il codice a tre lettere: ogni campo valuta li lascia passare
  (con D1 finiscono in `convert_bulk`, nessun cambio, variazioni null; nessun 500). Cura: solo alpha-3, cambio di
  contratto da decidere. Dettagli: piano MF, sezione «R13-SEC9».
- ✅ **MF-SEC9c · Il ripiego dal DB del prezzo corrente usa una sessione sola da task paralleli** — basso, preesistente;
  **chiusa il 17/10**: le quotazioni in parallelo senza sessione, i ripieghi in una lettura raggruppata dopo, dev
  `29e30b6cc`.
  test-author di MF, 17/10 (R13-SEC9). `get_current_prices_bulk` (`services/assets/price_query.py` ~:929) lancia i recuperi
  con `asyncio.gather`, e i ripieghi sul prezzo salvato interrogano la stessa `AsyncSession`, che SQLAlchemy non
  ammette fra task concorrenti. La deduplica degli id (SEC9-1) lo rende più raro, non lo toglie. Cura: le letture del
  ripiego in una query sola dopo il `gather`. Dettagli: piano MF, sezione «R13-SEC9».
- **MF-FV · Piano «formule veloci»: togliere i pavimenti all'indietro senza pagarli** — grande, nessun valore (parità al
  bit); developer, 19/10 (D1 un punto al giorno, D2 i pavimenti alla fine, uno per lotto, tutto nella 1.3). Lotti di MF:
  P1 ✅ (la linea del MWRR a partenza calda, codice `af479abe7`, giornale `bbbc085d2`), P2 ✅ (storia e viste solo per la
  finestra, `82e9454eb`), P3 pronto il 20/10 (i cambi a gradini nel motore e nella cassa nativa, con `unit_rate_steps` di X;
  0 differenze su tutto `get_report`), P4 (il motore a segmenti); poi i pavimenti. Dettagli:
  piano MF, «Piano «formule veloci»» e le voci P1, P2.
- **MF-P1b · Le due debolezze del MWRR già presenti** — piccolo, valori da dichiarare; MF, 19/10 (test di P1), via del
  developer il 19/10 come lotto a parte, dopo P2. (1) Il test del segno moltiplica i VAN e il prodotto va in underflow
  a zero; (2) `_is_xirr_root` scarta radici vere quando il VAN è mal condizionato (termini enormi che si annullano). P1
  le ha conservate al bit, fissate nei test con un commento. I valori che cambiano si dichiarano prima, come domanda se
  toccano numeri mostrati. Dettagli: piano MF, voce P1.
- ✅ **MF-E2b · Lo storico di performance dei lotti perde i flussi dei giorni senza valore** — piccolo, numeri (rari);
  test-author di MF, 20/10 (E2). `calculate_simple_roi_series` e `calculate_twrr_period_series` contano solo i flussi
  datati in un giorno con NAV: un acquisto o una vendita in un giorno senza valore dopo il primo (nel servizio, un prezzo
  senza cambio verso la valuta del rapporto) non entra mai in ROI e TWRR, mentre le sue quote sono nel valore del giorno
  dopo; vale anche per i soli lunghi (esempio: +50 %/+50 % dove il vero è 0 %). Cura proposta: spostare il flusso al primo
  giorno con valore successivo; domanda al developer. Dettagli: piano MF, «MF-E2 — via», domanda MF-E2b.
  **Il developer sceglie A** il 20/10; codice e test pronti il 20/10 (`returns.flows_by_snapshot_date`; 22 rossi prima;
  Dashboard invariata su 4 copie), in attesa del checkpoint. Dettagli: piano MF, «MF-E2b».
  - ✅ 21/10 (riconciliazione): in `dev_release2` col treno 4 (`015094472`; commit `bf748bbc3`).
