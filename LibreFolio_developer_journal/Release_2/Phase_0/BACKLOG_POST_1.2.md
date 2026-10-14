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
| [Programma colori](../Phase_1/10_colorSystem/README.md) | Analisi colori v1.2 (P1–P11), piano generale (token, Designer Lab), workstream L, R e G, materiale della designer | aperto il 14/10; spostato in `Phase_1/10_colorSystem` il 14/10 sera (era la 55); giro 1 della designer ricevuto |
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
- **C-49 · Il backend non si ferma al SIGTERM entro 5 s dopo alcuni E2E** — basso, da verificare; anche per
  `docker stop`. Dettagli: 38, C-49.
- ✅ **C-50 · L'AI Export di un Asset espone il nome interno `portfolio_weight_ratio`** — chiusa da T nel treno 39
  (`dd0a8d497`). Dettagli: 38, C-50.
- **C-51 · I dati sintetici scrivono la vecchia forma di `classification_params`** — basso. Dettagli: 38, C-51.
- **C-52 · La CLI della sonda dell'AI Export non sa scegliere l'Asset né l'utente sintetico** — minimo. Dettagli: 38, C-52.
- ✅ **C-53 · L'AI Export dice «non riconciliato» per un residuo di rumore** — chiusa nella 1.2 da T, treno 47
  (`876d2b430`). Dettagli: 38, C-53.
- **C-54 · «Novità dalla tua ultima versione» al login** — medio; **dopo la 1.2**, per decisione del developer (12/10).
  Al login, una versione più nuova dell'ultima vista apre il modale del changelog sui capitoli non visti, nella
  lingua dell'utente. Dettagli: 38, C-54.
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
- **C-62 · DataTable: il ridimensionamento delle colonne è provato su una tabella sola** — basso, da verificare; W (lint
  della devWiki), 12/10. La pagina della wiki, aperta dal 07/07, dice che in alcune tabelle la maniglia non allarga la
  colonna, senza una causa trovata (`onColumnResize` non letto dal genitore, o una `width` fissa che la rimette com'era).
  Un E2E lo prova solo sulla tabella L1° del Laboratorio di rischio (`risk-lab.spec.ts`, «value columns carry their
  help»): le altre DataTable vanno ritestate. Dettagli: [`datatable-column-resize-noop`](../../../LibreFolio_devWiki/wiki/problems/datatable-column-resize-noop.md).
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
- **C-66 · Sync: l'avviso prima di sovrascrivere i dati (F-094)** — basso; W (C-64), 12/10. Il dialogo c'è già ed è
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
- **C-71 · Due «Rolling Return» con lo stesso nome** — minimo; I, 13/10, controllo del CHANGELOG (D-I1). L'indicatore
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
- **C-73 · Le percentuali del planner del PAC arrotondano male i pareggi (D1)** — basso; T, 13/10 (T-PAC); dopo la
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
- **C-74 · L'aiuto di «Value after the plan» è sbagliato per il PAC (D2)** — basso; T, 13/10 (T-PAC); dopo la 1.2.
  - **Il difetto**: l'aiuto dice «the units you had plus the ones bought» (`planner/result/AssetTable.svelte:79-83`,
    chiave `…finalValueHelp`). Nel PAC invece `final_value = buy_mid_value` e `current_invested = 0`: lo impone lo
    schema (`backend/app/schemas/pac_allocator.py:1976-1981`, `:2026-2027`), e la stessa tabella lo dice in
    `buyMidHelp`.
  - **Anche «Ideal value»** nomina «already invested», che nel PAC vale sempre 0.
  - **Da fare**: i due testi nei 4 cataloghi con `dev.py i18n update`, senza chiavi nuove.

  Dettagli: piano della 53, §5 D2.
- **C-75 · Un limite di SCIP a -0.0 farebbe fallire la validazione del risultato (D3)** — basso; T, 13/10 (T-PAC);
  dopo la 1.2.
  - **Il difetto**: `_float_text` (`backend/app/services/pac_allocator/planner_report.py:1044-1059`) scrive -0.0
    come «-0» (`_decimal_text`, `:1086-1091`). `PlannerFixedDecimal` (`backend/app/schemas/pac_allocator.py:47`)
    rifiuta «-0» in `primal` e `dual`.
  - **L'effetto**: non è mai stato visto, ma un piano valido diventerebbe un risultato che non passa la validazione.
  - **Da fare**: il rosso con un limite -0.0 (TP-11), poi lo zero negativo scritto come «0».

  Dettagli: piano della 53, §5 D3.
- **C-76 · Il cancello locale del planner non controlla segno e zero (D4)** — basso; T, 13/10 (T-PAC); dopo la 1.2.
  - **Il difetto**: `localProblems` (`planner/request.ts:154-175`) controlla solo «vuoto» e «non è un numero» per
    l'importo da usare, il contributo e il passo dell'ordine. Un negativo o uno zero arriva al codec o al backend.
    L'utente legge l'errore generico «A field does not match the planner contract: {path}», non un messaggio sul
    passo.
  - **In più**: il backend riporta un importo selezionato negativo sul percorso di `available`
    (`backend/app/services/pac_allocator/normalize.py:449-450`).
  - **Da fare**: `localProblems` a tabella (TP-12) e i controlli, con chiavi nuove per i messaggi.

  Dettagli: piano della 53, §5 D4.
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
- **C-79 · Cancellare un broker lascia il suo lock e la sua cartella vuota in `broker_reports`** — minimo; R, 14/10, run
  finale. Alla cancellazione di un broker restano `.locks/broker_N.lock` e la cartella vuota `uploaded/broker_N/`: nella
  run finale, 89 lock e circa 107 cartelle dei broker temporanei delle spec di import. Nessun file di report resta
  orfano. Cura: la pulizia del file system nella cancellazione del broker (BRIM/import), dopo la 1.2. Dettagli:
  [rapporto della run finale](38_postReleaseBacklog/report-R-final-run-coverage-20261013.md), §3.
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
- **C-84 · Le versioni scritte a mano nei file del progetto** — minimo; coordinatore, 14/10. `pyproject.toml` e
  `frontend/package.json` dicono ancora 1.1.0, fissate il 05/08; nessuno le legge, perché la versione dell'app viene da
  `git describe`. Da allineare a ogni rilascio, o da togliere.
- **C-85 · Mostrare che si sta aspettando il server, nelle richieste importanti** — medio; developer, 14/10, dalla
  verifica sul server della build `v1.1.0-1674-g797a7e432` (voce 7). Le sue parole: «quando un pacchetto è in volo non si
  ha chiaro che si sta attendendo la risposta, dobbiamo aggiungere nel backlog un task che si occupa di rendere palese
  in qualche modo che si sta aspettando una risposta dal server per le domande importanti».
  - Il caso visto: nel grafico P&L della Dashboard, cambiando i broker del filtro, le linee si aggiornano solo quando
    arriva la risposta, e nel frattempo niente dice che il calcolo è in corso.
  - Da fare: l'elenco delle richieste lente o importanti (il report della Dashboard e dei broker, il Rischio, i lotti,
    l'AI Export, il PAC, i sync), e per ciascuna un segnale uniforme di attesa sul contenuto che cambierà: uno stato
    «in aggiornamento» sul grafico o sul pannello, e i dati vecchi attenuati invece che lasciati come se fossero
    attuali. Da progettare insieme, con un componente comune, e dopo la 1.2.
- **C-86 · Un provider di prezzi con le API di Interactive Brokers** — basso; utente C (uno dei primi utenti), chat del
  04/09, ritrovata dal developer il 14/10. Prezzo corrente e storico letti con la chiave dell'utente. Dipende da un
  posto dove salvare le chiavi dei plugin (`TODO_FUTURI.md`, «⚙️ Impostazioni per plugin») e da un account per le
  prove. Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 4.
- **C-87 · Rendimento a scadenza (YTM) e duration delle obbligazioni** — basso; utente C, chat del 04/09. Salvarli con
  la loro data, perché cambiano nel tempo, e mostrarli nella pagina dell'asset. Da decidere se leggerli da un provider
  o calcolarli in `backend/app/services/financial_math/`. Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 5.
- **C-88 · Un pacchetto di dati di qualità in abbonamento** — minimo, un'idea da valutare per `TODO_FUTURI.md`; utente
  C, chat del 04/09. Prezzi storici e composizioni dei fondi a pagamento, per chi li vuole, anche come sostegno al
  progetto. Da valutare: licenze dei dati, costi, convivenza con l'installazione self-hosted. Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 14.
- **C-89 · Spiegare le due date del cambio valuta** — minimo; utente C, chat del 04/09. Nel modulo, accanto alle date
  «Da» e «A» (`TransactionFormModal.svelte:1645`, `:1693`), un suggerimento: di solito coincidono, e si separano quando
  il broker accredita la nuova valuta in un altro giorno. La stessa frase nella guida (`user/transactions/form.*.md`).
  Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 31.
- **C-90 · «Testa configurazione» dice che è solo una prova** — minimo; utente C, chat del 04/09. Accanto al risultato
  dello storico, una riga: la prova legge gli ultimi giorni, e alla creazione dell'asset LibreFolio scarica tutto lo
  storico disponibile. Oggi lo dice solo la guida (`user/assets/create-edit.en.md:67`). Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 11.
- **C-91 · Collaudare gli import di Interactive Brokers e Fineco su report veri** — minimo; utente C, chat del 04/09.
  Sono ancora Beta, scritti su esempi trovati online: chiedere all'utente un report vero con i numeri cambiati,
  ricavarne fixture sintetiche e, se regge, togliere il Beta. Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 32.
- **C-92 · Il capitolo 1.2.0 del CHANGELOG non cita due idee dell'utente C che sono nel codice** — minimo, decisione
  del developer; coordinatore, 14/10. I settori «Obbligazioni societarie» e «Titoli di Stato», assegnati da Borsa
  Italiana, e l'import CSV delle distribuzioni per settore e paese sono nella 1.2.0, ma il capitolo non li nomina. Due
  strade: aggiungerle come correzione dopo il rilascio, in 4 lingue con lo stamp del pezzo (il capitolo è rilasciato,
  quindi `translate-validate` è severo), oppure lasciare il capitolo com'è. Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voci 8 e 17.
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
- **B10 · `periodBasePnl` dichiarato e mai usato** — minimo; I, 10/10. `GrowthChart.svelte:594-600`.
- **B11 · I giorni «dirty» non contano i cambi dei titoli** — medio, ½ g; test-author di I, 10/10. I giorni di cambio
  si contano solo per le valute tenute in cassa (`native_cash.py:271-279`; motore `:808` e `:922-923`). La cura cambia
  NAV e linee anche con la sola cassa in valuta base, quindi il golden della guardia andrebbe rigenerato: serve una
  decisione. Va in T-U1 o T-U5. Dettagli: idem, §14 e §17.6.
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
- **47-1 · Sotto zoom gli assi a categoria perdono le etichette** — basso, preesistente; I, 12/10 (piano 47, punto 3
  dell'analisi). In compatto l'`interval` si calcola su tutti i punti (`responsiveXAxis.ts:149`, da `2d22130bd`), e i
  gestori del `dataZoom` di `CandlestickChart.svelte:249`, `LineChart.svelte:358` e `PriceChartFull.svelte:579` non lo
  ricalcolano sulla finestra visibile. Prova SSR, un anno giornaliero a 800 px con spazio per 12 etichette: 12 senza
  zoom, 7 con metà periodo, 4 con un quinto, solo i due bordi su una finestra di 33 punti. Gli assi time non ne
  soffrono. Dettagli: [piano della 47](47_chartAxisDayLabels/plan-phase00ChartAxisDayLabels.prompt.md), §4 «Fuori» e
  §9, passo 7.
- **48-1 · Il pulsante dell'AI Export più largo dei vicini nella barra** — minimo, cosmetico; I, 12/10 (piano 48,
  V-19). Il trigger di `AiExportMenu.svelte:298` ha `px-3 gap-2`, i pulsanti vicini `px-2.5 gap-1.5`
  (`assets/[id]/+page.svelte:2826-2861`). Allinearlo stringe la colonna di «Exportación IA» di circa 12 px. Da solo
  non avrebbe curato V-19, che sforava fino a 18,8 px: lo ha curato C5 con le soglie `denseRow`. Resta un ritocco di
  coerenza. Dettagli: [piano della 48](48_uiPolish/plan-phase00UiPolish.prompt.md), §1.5 e passo 5.
- **49-1 · Il debito di lint di `_frontend_broker.py`** — minimo, preesistente; I, 12/10 (piano 49, §6). `ruff check`
  dà E701 a `:44`, `:45`, `:52`, `:53` e PLC0415 a `:96`; `black --check` lo riformatterebbe in due pezzi. Viene da
  `1a29e0523`, `547c06cf0` e `7d3463e2f`, ed è fuori dal gate: ruff e black del gate passano solo `backend/`
  (`dev.py:1841`, `:1848`). Nel runner intero sono 149 errori ruff in 17 file, e black riformatterebbe 15 file su 30:
  se pulirlo in una volta sola lo decide il coordinatore. Dettagli:
  [piano della 49](49_requestCountRace/plan-phase00RequestCountRace.prompt.md), §6.
- **54-1 · Con la liquidità negativa la storia dell'allocazione sfora il 100 % e il grafico la taglia** — basso,
  preesistente; I, 13/10 (piano 54, passo 8). La liquidità entra in Tipo e Settore col suo segno, non in Geografia
  (`daily_state.py:715-717`, `cumulative_cash + it_cash`), e ogni lista divide per il totale con segno
  (`derived_views.py:231-243`): un saldo negativo porta le quote positive sopra 100. ECharts impila i negativi sotto lo
  zero (`stackStrategy` di default `samesign`, `echarts/lib/processor/dataStack.js:103`, `:132`) e `max: 100` taglia
  la cima (`AllocationHistoryChart.svelte:703`, `:802`). Tooltip e famiglie scartano le voci fino a 0,01 (`:623`,
  `:626`, `:775`), la torta quelle fino a 0 (`AllocationPanel.svelte:60-67`): la liquidità negativa non compare da
  nessuna parte. Nessun caso nella corsia né nella fixture. Da decidere se mostrare la leva o togliere la liquidità
  negativa dal totale. Dettagli: [piano della 54](54_galleryFixtureShares/plan-phase00GalleryFixtureShares.prompt.md),
  passo 8.

## P · Transazioni e Bulk (42)

Dettagli: [piano della 42](42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md) e 38, sezione «P · Costo medio e
impostazioni». C-46…C-48 sono nel treno 37. Righe mandate da P l'11/10 e trascritte dal coordinatore; P-5 è passata nella
sezione T, e P-7 (chiudere le issue #32 e #35) è un compito del rilascio, non di dopo.

- **P-2 · Anteprima WAC: etichetta sbagliata per le righe di split e ramo `add_at_wac` morto** — basso; P, archivio
  della 30 (09/10). Dettagli: [38](38_postReleaseBacklog/README.md), sezione «P · Costo medio e impostazioni», P-2.
- ✅ **P-3 · Contributo per posizione: dividendi e costi senza cambio esclusi senza segnale** — chiusa da F nel treno 42
  (B14 di I, `c04e44ff5`). Era: basso; P, archivio della 30 (09/10). Dettagli: idem, P-3.
- **P-4 · Fuso orario: verificare il database IANA nell'immagine Docker** — basso; P, archivio della 30 (09/10).
  Dettagli: idem, P-4.
- **P-8 · `tx-clone.spec.ts`: commento di testa superato** — minimo; P, archivio della 30 (09/10). Dettagli: idem, P-8.
- **P-9 · Black: riformattare `test_portfolio_api.py` e `test_portfolio_wac.py`** — minimo; P, archivio della 30
  (09/10). Dettagli: idem, P-9.
- **P-10 · `MISSING_COST_BASIS` raggiungibile dall'app riclassificando uno SPLIT** — basso, serve una decisione; P,
  analisi della 39 (09/10). Dettagli: idem, P-10.
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

## T · Matematica finanziaria e riordino (43)

Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md). Prima della 1.2: B1–B3 (B1, B2 e B3a nel treno 37, B3b nel checkpoint successivo), PL3, BU1, T-1
(dopo F) e FE1, perché l'onboarding è libero dall'11/10. Righe scritte da T dal riallineamento al treno 37; le voci B9 e
P-5 le ha trascritte il coordinatore. Dopo la 1.2:

**Difetti e motore**

- **T-B4 · La data del lotto più vecchio dopo uno split** — medio; T, 11/10. Va con U6. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione
  «7.1 Lotti, passi, peso, quando».
- **T-B5 · Il P&L di una chiusura FIFO mescola le valute** — peso da stimare, serve una decisione; T, 11/10. Se un lotto
  è aperto e chiuso in valute diverse, `_close_position_piece` (`fifo_lot_engine.py:905-940`) sottrae il prezzo del
  lotto da quello di vendita senza convertirli. Limite già documentato nella pagina dev del servizio dei lotti.
  Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3a — Lotti, niente ripiego sull'importo non convertito».
- **T-B6 · Lotti: la fonte del prezzo di riferimento dice «exact» anche quando il prezzo convertito manca** — minimo;
  T, 11/10, dalla sonda di B3b. Senza cambio `reference_unit_price` è `None`, ma `reference_price_source` resta
  `exact`, e l'AI Export lo copia. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3b», «Sonda».
- **T-B7 · AI Export: segnalare le colonne tolte perché nulle in ogni riga, in tutti i componenti** — medio-basso;
  coordinatore, 11/10. Il renderer compatto toglie una colonna nulla in ogni riga; solo i lotti ne hanno la traccia
  (`unavailable_amount_lot_count`, B3b). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3b», «Scoperte sul renderer dell'AI Export».

- **T-B8 · Sintesi FIFO dell'AI Export: valore aperto e P&L non realizzato sommano insiemi di lotti diversi** — basso;
  T, 11/10, dal docs-writer di B3b. Ognuna delle due somme prende i lotti aperti in cui quel campo è noto, mentre i
  conteggi della copertura contano i lotti in cui sono noti entrambi; con il costo di un lotto ignoto (B3b) le due
  somme non coprono più gli stessi lotti. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3b», «Passo 6».
- **T-B9 · AI Export: un residuo reale sotto l'unità minima della valuta si stampa `0` accanto a `reconciled` falso** —
  minimo; T, 12/10, dal docs-writer di C-53. Il renderer stampa `0` un residuo monetario più piccolo dell'unità minima
  (`monetary_residuals_zeroed`); dopo C-53 `reconciled` tollera solo `CONVERSION_DUST` (1e-9), quindi un residuo fra le
  due soglie si contraddirebbe. Improbabile: il riepilogo chiude la scomposizione per costruzione. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «C-53 — implementazione».

**Unificazioni della matematica comune (parte 1)**

- **T-U1 · Un piano dei cambi unico: mancanti e provenienza** — medio; T, 11/10. Esclude i giri del portafoglio, che
  ha chiuso F (O2; X5 sui movimenti): le 4 conversioni dei prezzi di X5 restano qui e in U5. Comprende il servizio
  dei lotti, che con FEE/TAX presenti converte ogni BUY/SELL come peso possibile e può segnalare il cambio di un trade
  che nessun pool legge (docs-writer di B3b). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.3» e «7.1».
- **T-U2 · Frazionamenti: caricamento, validazione, rapporto cumulato** — medio-basso; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezioni «2.7» e «7.1».
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
- **T-U5 · Prezzo del giorno e valorizzazione** — medio-alto; T, 11/10. Comprende R4 (il P&L di periodo della posizione),
  con B8 di I. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.2» e «7.1».
- **T-U6 · Finestre di detenzione dal FIFO** — medio; T, 11/10. Comprende L1 e L2 di I e T-B4. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezioni «2.5» e «7.1».
- **T-U7 · Pesi e concentrazione** — medio; T, 11/10. Comprende W1 (l'allocazione senza il valore in viaggio). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.8» e «7.1».
- **T-U8 · Il frontend solo di presentazione: Δ, KPI, lotti** — medio-alto; T, 11/10. Comprende il valore d'apertura
  che il modale della custodia ricalcola come quantità × prezzo d'apertura (`LotCustodyModal.svelte`) invece di
  leggere `original_cost`, trovato in B3b, e la dichiarazione nel codice delle misure interattive che la regola
  ammette (`MeasureSignal.ts`, `CompoundSignal.ts`, `LinearSignal.ts`, `SineSignal.ts`; docs-writer di T-1). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «7.1».
- **T-U9 · L'AI Export dalle case comuni** — medio; T, 11/10. Comprende il `reason_code` di `broker.concentration_comparison`,
  trovato con C-55 (12/10): `broker_summary_unavailable` (`broker_concentration_context.py:390`) esce anche quando il
  riepilogo del broker c'è ma non ha posizioni, mai avute o tutte chiuse. Il messaggio è esatto, il codice no; cambiarlo
  cambia il contratto, quindi la v2. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «7.1» e «C-55 — analisi».
- **T-U10 · Interessi e convenzioni di calendario (`interest.py`)** — basso-medio; T, 11/10, decisione D-8. Dettagli:
  [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.10» e «7.1».
- **T-D9 · MeasureSignal: la soglia dei 30 giorni sull'annualizzato** — minimo; T, 11/10, decisione D-9. Dettagli:
  [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «2.1», riga R18.
- **P-5 (di P) · Migrare `roi_utils` e `valuation_utils` in `financial_math`** — basso, refactor; decisione D1 del
  developer, registrata da P (09/10). Coperta da T-1 e BU1 se entrano nella 1.2. Dettagli:
  [38](38_postReleaseBacklog/README.md), sezione «P · Costo medio e impostazioni», P-5.

**Code reordering (parte 2)**

- **T-PL1 · Il runtime dei segnali in `services/signals/`, fine del ciclo rischio↔segnali** — medio; T, 11/10.
  Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
- **T-PL2 · Un registro per famiglia di plugin** — medio; T, 11/10, decisione D-P1. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
- **T-PL4 · `fx.py` diventa `services/fx/`** — medio; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
- **T-PL5 · `brim_provider.py` diventa `services/brim/`** — medio-alto; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
- **T-PL6 · Asset: `base.py`, via lo shim `asset_source.py`** — medio-basso; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
- **T-PL7 · Un router proprio per i segnali, con gli URL invariati** — medio-basso; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «P2.1».
- **T-P2.2 · I file grandi del backend, divisi per cuciture** — medio; T, 11/10. L'evaluator del PAC,
  `portfolio_service`, le transazioni, `broker_service`, `price_store`, i router, gli schemi. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «P2.2».
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
- **T-R1 · Nomi privati attraverso il confine dello strato** — minimo; T, 12/10. `risk/service.py:439` chiama
  `PortfolioService._get_configured_fx_pair_sets()`, che avvolge `load_configured_fx_pair_sets`
  (`financial_math/portfolio/data_quality.py`); `portfolio_service` importa `_compute_tx_fingerprint` dal motore. Il
  PAC l'ha già fatto in T-1 (`QUANTITY_DUST_THRESHOLD` pubblico). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «B2 — motore del portafoglio in sei moduli».
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
- **M-25 · Un `dev.py docker build` locale può riusare un frontend con un'altra versione** — basso; M (lotto 34), 13/10.
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
- **V-3 · TRANSFER orfano: i lotti falliscono, la Dashboard lo conta come capitale in natura** — basso, dopo la 1.2
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
- **V-4 · Se si chiude P-10, E2 di `data-quality-real.spec.ts` va ricostruito** — minimo; V, 12/10. E2 ottiene
  `MISSING_COST_BASIS` dall'app riclassificando uno SPLIT in PRICE_ADJUSTMENT. E4 (righe legacy) e B1 restano validi.
  Dettagli: idem, §4.
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
- **V-11 · `TRANSACTION_IMPLIED` può dire «nessun prezzo di mercato da oltre 2 settimane» per un asset quotato ieri**
  — basso, da confermare con un test; docs-writer di V, 12/10. Per lettura del codice:
  - `AssetPriceSeries.resolve` (`financial_math/price_marks.py:197-223`) prende l'osservazione più recente, quote o
    trade che sia. Un BUY registrato oggi, prima del sync della quotazione di oggi, batte quindi la quotazione di ieri:
    `LAST_TRADE_PRICE`, l'asset è «implied»;
  - superato il periodo di grazia, contato dal primo BUY/SELL e non dall'ultima quotazione
    (`portfolio_service.py:1083-1088`), compare l'avviso, e il testo di `en.json:1719` parla di oltre 2 settimane
    senza prezzo di mercato.
  La valutazione al prezzo del trade è sensata; sbagliato è solo il messaggio. Dettagli: piano della 46, §12.2.
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
- **V-23 · Il bulk editor nasconde il broker di sola lettura e attacca l'errore d'accesso alla riga sbagliata** — basso,
  UX; test-author di V (triage di WB5), 12/10:
  - un TRANSFER verso un broker di sola lettura mostra il ricevente come «To: —». `renderBrokerHtml`
    (`TransactionBulkModal.svelte` ~`:1608`) cerca il broker solo nella lista dei broker modificabili
    (`getEditableBrokers()`, ~`:593`). L'utente non vede quale broker causa l'errore, e il banner lo chiama solo
    «Broker #2»;
  - `_append_access_issues` (`transaction_batch_stages.py` ~`:158-178`) riporta ogni errore d'accesso come
    `operation="create", index=0`. La griglia lo mette sulla riga 1a (IB, modificabile) e non sulla 1b (DEGIRO).

  Dettagli: piano della 46, §12.8.

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
- **V-38 · Il form elenca un problema di saldo tra i problemi dei campi** — basso, UX; letto nel codice da test-author
  di V, 13/10, e verificato da me; **non visto a schermo**.
  - Il form divide i problemi per indice: `index >= 0` sono dei campi, `< 0` di saldo
    (`TransactionFormModal.svelte:944-945`).
  - Il server attacca `balanceCashNegative` alla riga che lo causa (`index: 0`). Nel form finisce quindi sotto il titolo
    dei problemi dei campi, non sotto «This configuration causes data inconsistencies».
  - Il bulk editor divide invece per codice (`isBulkBalanceIssue`, `utils/transactions/bulkDisplay.ts:145`), e mette lo
    stesso problema sotto il titolo del saldo.
  - Da verificare a schermo prima di decidere. Dettagli: piano della 46, §12.14.

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
- **R2 · `VERSION` stantio** — medio; manca la decisione: leggerlo solo senza `.git/`, o cancellarlo dopo la build.
  Dettagli: idem, e [08](09_feedbackJobs/08_review_visiva_20260922.md) R2.
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
- **U-B8 · Un passo superato nella guida dei plugin BRIM** — basso; docs-writer in U-6, 13/10.
  - Il passo 3 di «Register the user-facing docs» in `brim_plugin_guide.md` (la «Capacity table», l.~1598) chiede
    una riga nella tabella `??? info "📊 Importer Capabilities"` delle pagine `user/transactions/import/index.*.md`.
    Quella tabella non c'è più.
  - Fuori dal perimetro di U-6, quindi non l'ho toccato: si toglie il passo, oppure lo si riscrive per le schede
    dell'indice.

  Dettagli: piano della 45, sezione «10», U-6.
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

  Dettagli: [progetto](55_colorSystem/design-designerLab.md); piano del figlio in `55_colorSystem/L-designerLab/`.

## R · Fattorizzazione colori a parità di aspetto (55)

Ogni ondata va dimostrata con una gallery dello stesso giorno `identical` (a parte le schermate instabili della 56).
Ciò che cambia l'aspetto non è di R: aspetta il report della designer (piano generale, «Decisioni del developer»).

- **R-1 · Colori dei grafici in un modulo unico** — alto; coordinatore, 14/10.
  - Oggi: 4 set per assi, griglie e tooltip; 3 palette di allocazione; coppie chiaro/scuro scritte in 17 grafici.
  - Stessi valori, divergenze con un nome.

  Dettagli: [report 04](55_colorSystem/analysis/04_charts_dataviz.md), §1–§3.
  - Stato (R, 14/10): codice nel checkpoint del lotto B (W3–W5). `lib/theme/themePair.ts` (`themed()`),
    `chartTheme.ts`, `chartPalettes.ts`, `chartColorScales.ts`: 229 siti in 33 file; neutri, palette, serie, formule e
    lotti; ogni divergenza ha un nome (`CHART_GAIN_LOSS.price` `#ef4444` / `.portfolio` `#dc2626`, box del tooltip
    comune e della candela, interesse di Growth e dei lotti…). Il dividendo di Growth e dei lotti è ora una voce sola. Si
    chiude con il commit e il cancello B.
- **R-2 · Funzioni condivise per segno, stati e badge** — medio; coordinatore, 14/10.
  - Oggi: ternario guadagno/perdita in almeno 20 punti e 7 mappe di stato indipendenti.
  - Output identici.

  Dettagli: [report 03](55_colorSystem/analysis/03_semantic_dynamic_logic.md), §1–§3.
  - Stato (R, 14/10): codice nel checkpoint del lotto A (W1–W2): `lib/theme/toneClasses.ts` (`SIGN_TEXT`, `SIGN_BAR`,
    `POLARITY_TONES`, `STATUS_TONES`, `KIND_TONES`), 42 siti di segno in 20 file e 11 mappe di stato in 9 file; CSS
    compilato identico alla baseline. Si chiude con il commit del checkpoint e il cancello A.
- **R-3 · Hex nei `<style>` in variabili CSS con lo stesso valore** (P8: `DataTable*`, modali file e immagini,
  `ConfirmModal`) — medio; coordinatore, 14/10. Dettagli: [report 02](55_colorSystem/analysis/02_ui_components.md), §4.
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
- **R-4 · Funzioni fragili e refusi senza effetto visibile** — basso; coordinatore, 14/10.
  - `hexToRgba` e la concatenazione `+ '88'` accettano solo `#rrggbb`.
  - La meta `theme-color` scura è `#156534` invece di `#166534`.

  Dettagli: [report 01](55_colorSystem/analysis/01_theme_foundation.md), §6.5; [report 04](55_colorSystem/analysis/04_charts_dataviz.md), §5.
  - Stato (R, 14/10): codice e test nel checkpoint del lotto A (W0); `lib/theme/colorAlpha.ts`, meta corretta nei tre
    punti con gate di concordanza. Si chiude con il commit del checkpoint e il cancello A. Piano:
    [R-colorRefactor](55_colorSystem/R-colorRefactor/plan-phase00ColorRefactor.prompt.md), «W0».
- **R-5 · `withAlpha` su `hsl()` con spazi produce un colore non valido** — minimo; R, 14/10.
  - `hsla(210 68% 44%, a)` mescola le due sintassi; oggi nessun chiamante ci passa (`lotColor` non arriva a `withAlpha`).
  - Da correggere quando un colore con spazi ci arriverà (fase B), con la gallery.

  Dettagli: piano R, «W0», nota «Fuori pista».
- **R-6 · Viola della linea di anteprima negli editor dei dati** — minimo; coordinatore, 14/10.
  - `color: '#a855f7'` scritto a mano in `assets/AssetDataEditorSection.svelte:248` e in
    `fx/FxDataEditorSection.svelte:129`.
  - Fuori dal perimetro di R: sono cartelle della 1.3. Passa alla fase B.
  - Fino ad allora è un'eccezione del cricchetto (W10).

  Dettagli: piano R, «W7», nota sulle eccezioni del cricchetto.

## G · Gallery deterministica (56)

- **G-1 · 27 schermate instabili su 177** — medio; coordinatore, 14/10, misura di due esecuzioni identiche.
  - Sfondo animato del login non congelato.
  - Scorrimento di pochi pixel nel pannello lotti.
  - Altre instabili da analizzare.

  Dettagli: [README della 56](56_galleryDeterminism/README.md) e [stabilità](56_galleryDeterminism/evidence/stability-2026-10-14.md).
- **G-2 · 4–5 test desktop falliti in ogni esecuzione completa a 10 worker, ogni volta diversi** — medio; coordinatore,
  14/10.
  - Login fermo su «auth-loading» nel primo blocco; modali delle transazioni.
  - Passano in un secondo tentativo isolato.
  - Da analizzare con `test-triage`: non sono classificati.

  Dettagli: README della 56.
- **G-3 · `Dashboard Risk › what-if crisis replay` su desktop** — medio-basso; coordinatore, 14/10.
  - Fallisce in 2 esecuzioni su 3.
  - Il menu contiene «Global Financial Crisis», ma `chooseReplayPreset`
    (`frontend/e2e/fixtures/galleryRiskDashboard.ts:146`) non si ferma mai sulla voce.
  - Il messaggio d'errore non descrive ciò che succede.

  Dettagli: README della 56.

---

## Sessioni della 1.3.0 (fase 01)

> Aperte il 14/10 dal coordinatore della 1.3. Piano: [fase 01](../Phase_1/README.md). Ogni sessione scrive solo la
> propria sezione, qui sotto, nello stesso checkpoint in cui la voce nasce; le voci di altre sezioni chiuse da una
> sessione della 1.3 le marca ✅ il coordinatore.

## H · Piattaforma (fase 01)

Piano: [`01_platform`](../Phase_1/01_platform/plan-phase01Platform.prompt.md).

## A · Account e accessi (fase 01)

Piano: [`02_accounts`](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md).

## X · Plugin, asset e ricerca (fase 01)

Piano: [`03_pluginsAssets`](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md).

## W · Import e transazioni (fase 01)

Piano: [`04_importTransactions`](../Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md).

## J · Numeri e analisi (fase 01)

Piano: [`05_numbersAnalysis`](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md).

## Z · Sospensione e risveglio (fase 01)

Piano: [`06_sleepWake`](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md).

## B · Backup e Docker (fase 01)

Piano: [`07_backupDocker`](../Phase_1/07_backupDocker/plan-phase01BackupDocker.prompt.md). Sessione non ancora avviata.

## E · Email (fase 01)

Piano: [`08_email`](../Phase_1/08_email/plan-phase01Email.prompt.md). Sessione non ancora avviata.

## Y · Cruscotto e grafici (fase 01)

Piano: [`09_dashboardCharts`](../Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md). Sessione non ancora
avviata.
