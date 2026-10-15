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
  - ✅ **Ricerca inversa chiusa il 15/10** da W (lotto I1 della 1.3, `5e96df752`; in `dev_release2` con `dc7e4e48e`):
    `GET /transactions?asset_event_id=`, nei broker che l'utente vede (C-65b nel piano 04). Resta aperta la modale al
    cambio di provider (C-65a, X e W).
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
  - ✅ **Parte a chiusa il 15/10** da W (lotto K2a della 1.3, `0eac8e1b6`; in `dev_release2` con `62c964242`):
    DEGIRO e il Generic CSV rifiutano un file con un `BRIMRefusal` a codice, tradotto in `importWizard.parseRefusal.*`
    (le chiavi stanno nella sorgente `importWizard`, non nel frammento del plugin, per la regola R1 di
    `gate-plugin-i18n-ownership`), e il rifiuto nomina il plugin col suo nome. Resta la parte b, il 400 del parse
    tradotto nel wizard e il codice dell'anteprima illeggibile (K2b, dopo un commit del coordinatore su `brokers.py`
    e `uploads.py`).
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
- **C-84 · Le versioni scritte a mano nei file del progetto** — minimo; coordinatore, 14/10. `pyproject.toml` e
  `frontend/package.json` dicono ancora 1.1.0, fissate il 05/08; nessuno le legge, perché la versione dell'app viene da
  `git describe`. Da allineare a ogni rilascio, o da togliere. **Metà chiusa da H il 15/10** (decisione 14):
  `pyproject.toml` a `0.0.0`, con un commento (`6e78b8c96`, in `dev_release2` con `9deb0ea08`); `frontend/package.json`
  e le due righe radice del lock con il CP5b di H, dopo la finestra della galleria.
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
- ✅ **C-89 · Spiegare le due date del cambio valuta** — minimo; utente C, chat del 04/09. Nel modulo, accanto alle date
  «Da» e «A» (`TransactionFormModal.svelte:1645`, `:1693`), un suggerimento: di solito coincidono, e si separano quando
  il broker accredita la nuova valuta in un altro giorno. La stessa frase nella guida (`user/transactions/form.*.md`).
  Dettagli: [mappatura dei suoi suggerimenti](38_postReleaseBacklog/feedback-early-user-C-20261014.md), voce 31.
  - ✅ **Chiusa il 15/10** da W (lotto K1 della 1.3, `532a1fd9c`; in `dev_release2` con `d915c869f`):
    il suggerimento nel form (`tx-form-fx-dates-hint`) e la stessa frase nella guida, nelle 4 lingue.
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
- **C-94 · Il server di test costruisce frontend e documentazione dentro i 300 s d'avvio** — basso, infrastruttura;
  J, 14/10 (era J-2), con una nota del coordinatore. In un worktree nuovo il primo `all-backend` cade anche dopo
  `npm ci`: prima di uvicorn `dev.py server --test` fa la build di debug del frontend (~4 min) e quella del sito, se
  mancano, dentro `STARTUP_TIMEOUT` (`scripts/test_runner/_server.py:48`), con lo stdout in `DEVNULL` (`:274-275`).
  Lo stesso succede dopo un merge che cambia il frontend o la doc. Rimedio di oggi, scritto in
  `.github/copilot-instructions.md`: `front build --debug` e `mkdocs build` prima della run, oppure
  `LIBREFOLIO_TEST_STARTUP_TIMEOUT=600`. Cura proposta: le build prima che parta il tempo massimo, con un messaggio
  che dica cosa sta costruendo. Nota: senza `node_modules` il runner arriva a `npx` attraverso `generate-api`, e
  dovrebbe fermarsi subito. Il runner è condiviso: va assegnato a una sessione. Dettagli: piano J, §10
  «`all-backend` — la base».
- **C-95 · L'albero dei moduli in `backend-schemas.instructions.md` è indietro** — minimo, doc per gli agenti; W, 15/10
  (K2a). L'albero di `.github/instructions/backend-schemas.instructions.md` non elenca `ai_export_runtime`,
  `pac_allocator/`, `portfolio`, `risk`, `risk_scenarios`, `signals`, `system`, `tools`, `wac`; le righe di
  `assets/` e `transactions/` le hanno già aggiornate X (CP4) e W (K2a). Da fare in una passata sola a fine
  riordino. Dettagli: piano 04, §12, K2a.
- **C-96 · Le corsie dei test prendono la configurazione dell'istanza dal `.env` del developer** — medio, sicurezza dei
  test; E, 15/10 (analisi). `scripts/cli_base.py:configure_test_runtime()` carica il `.env` e toglie solo
  `INSTANCE_TRUST_SECRETS` (S2 di H): ogni altra `LIBREFOLIO_*` arriva alle corsie. Con la configurazione SMTP di E i
  test spedirebbero email vere; con `LIBREFOLIO_BLOCKED` o il profilo gestito tutte le corsie cambierebbero
  comportamento. Cura: la corsia tiene solo le variabili del runner e scarta il resto della configurazione d'istanza
  venuta dal `.env`; un test usa `.env.example` come elenco. Assegnata a H dal coordinatore, prima del primo lotto di E;
  comprende A-9 (le quattro variabili di account di A5a). Dettagli: analisi di E; piano H.
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
  - ✅ **Parte di W chiusa il 15/10** (lotto K1 della 1.3, `532a1fd9c`; in `dev_release2` con `d915c869f`):
    i contatori e l'`aria-label` della levetta delle righe vecchie in `DataEditor`, «Help» e «Close» di
    `DataImportModal` (W-B8). «Date» era già `common.date`. Restano «Reset layout»
    (`components/table/ColumnVisibilityToggle.svelte:177`) e «max» (`BrokerSharingPanel:832`), a Y (decisione Q6 del
    piano 04).

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
    - **B6**, pulizia: sparisce l'override P1 di `app.css` su `text-gray-500`. Il test del selettore in scuro va ritirato o riportato su un nuovo soggetto P1, se ne resta uno. Decisione di L in quel momento.
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
- **L-16 · Giro 3 della designer nel Lab: ruoli di T-8 e colori di categoria** — medio; coordinatore, 15/10 (decisioni D1–D4). Il cursore dell'opacità (D2) è fatto e validato il 15/10.
  - **Dopo l'ingresso di T-8:** verifica del catalogo sui ruoli nuovi (barra verde, stati espliciti, terminale, interruttore, ombre, viola AI, hover dei campi) e una prova L1 a mano. Niente isole `.dark`/`.light`: T usa ruoli dedicati (D2).
  - **Dopo l'ingresso del modulo di DV** (`lib/theme/chartCategories.ts`, contratto C1–C4): livello `category` (scheda «Categorie», aggancio C3 con `categoryColor` su `LabHook`, segnale C4 `notifyChartColorsChange()`, export e `verify-export`, una riga nella skill, test unit ed E2E). «Per valore» non basta: tipi e settori condividono 7 esadecimali in chiaro e 11 in scuro.

  Dettagli: [piano di L](../Phase_1/10_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md), «Giro 3 della designer nel Lab» e «Cursore dell'opacità nell'editor».

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
- **G-13 · Nuova coppia di riferimento della gallery sul target, dopo l'ingresso di T** — medio; coordinatore, 15/10,
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

  Dettagli: [piano della 56](../Phase_1/10_colorSystem/G-galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md), §4, registro del 15/10, 16:05.

## T (colori) · Token e tema (Phase_1/10_colorSystem)

> Workstream T del programma colori, aperto il 14/10 (D-T1). Da non confondere con la sezione «T · Matematica
> finanziaria e riordino (43)». Piano: [T-tokensTheme](../Phase_1/10_colorSystem/T-tokensTheme/plan-phase01TokensTheme.prompt.md).

- **T-B1 · I requisiti della password detti anche a chi usa un lettore di schermo** — basso; T, 14/10.
  - Oggi ✓ e ✗ distinguono un requisito soddisfatto senza affidarsi al colore, ma non hanno testo per i lettori di
    schermo.
  - Servono due chiavi i18n («soddisfatto», «non soddisfatto») in testo nascosto: lo fa A, che possiede la card di
    registrazione dopo il giro di T.

  Dettagli: piano di T, passo T-2.
- **T-B2 · Ruoli in attesa del giro 2 della designer** — medio; T, 14/10.
  - Sono derivati provvisori, calcolati solo dai suoi valori: hover e premuto in chiaro, fondale delle modali, inverso
    dei tooltip, tinte di avviso, errore e informazione.
  - Da decidere con lei:
    - guadagno e perdita distinti da successo ed errore;
    - l'info `#155EEF`, molto saturo;
    - le opacità delle colline del login in scuro;
    - palette categoriale e colori dei grafici.
  - Le otto correzioni minime di contrasto (D-T6) vanno confermate.

  Dettagli: piano di T, «Autorizzazione e decisioni»; `frontend/src/lib/theme/tokens.css`.
- **T-B3 · Uno scanner dei colori solo, con L** — basso; T, 14/10.
  - Il cricchetto (`frontend/scripts/theme/theme-roles.mjs`) copia la regex delle classi di palette dallo scanner del
    Designer Lab (`scan-colors.mjs`).
  - Quando L entra in `dev_release2`, un modulo comune evita che i due conteggi divergano.

  Dettagli: piano di T, passo T-1.
- **T-B4 · Le cinque regole della password scritte due volte** — basso; T (trovato da `test-author`), 14/10.
  - Le stesse regole stanno in `ui/input/PasswordStrength.svelte` (la lista mostrata) e in
    `auth/RegisterCard.svelte` (la validazione del modulo). Oggi coincidono; se divergessero, la lista direbbe
    «soddisfatta» mentre il modulo rifiuta la password.
  - Una fonte sola per le regole: è di A, che possiede la registrazione (F13).

  Dettagli: piano di T, passo T-2.

---

## DV · Colori dei grafici (Phase_1/10_colorSystem)

> Workstream DV del programma colori, aperto il 15/10 per le scelte GR1–GR5 del giro 2 della designer (D-T17): colore
> fisso per tipo e per settore, uguale in torta e storico; tavolozze per tema; emoji dei settori unificate. Codice a due
> lettere: «D» e «V» erano già usate (developer, 15/10).
>
> Valori e controlli: [giro 2 della designer](../Phase_1/10_colorSystem/designer-feedback/2026-10-15-round2-palette/README.md)
> e la sua [analisi](../Phase_1/10_colorSystem/designer-feedback/2026-10-15-round2-palette/analisi.md), §4–§6. Il piano
> arriverà in `../Phase_1/10_colorSystem/DV-chartColors/`. Gli ID di questa sezione sono `DV-n`.

---

## Sessioni della 1.3.0 (fase 01)

> Aperte il 14/10 dal coordinatore della 1.3. Piano: [fase 01](../Phase_1/README.md). Ogni sessione scrive solo la
> propria sezione, qui sotto, nello stesso checkpoint in cui la voce nasce; le voci di altre sezioni chiuse da una
> sessione della 1.3 le marca ✅ il coordinatore.

## H · Piattaforma (fase 01)

Piano: [`01_platform`](../Phase_1/01_platform/plan-phase01Platform.prompt.md).

- **H-1 · Nella prosa della devWiki restano menzioni dei percorsi spostati da CP1, CP2a e CP4** — minimo; H, 14-15/10.
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
- **H-2 · I test del backend costruiscono frontend e MkDocs dentro i 300 s d'avvio del server condiviso** — basso; H,
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
- **H-4 · `validate_test_data_dir` solleva un `PermissionError` grezzo per una cartella gestita non attraversabile** —
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

  Dettagli: piano H, §14 «CP5a passo 2» e «CP6 passo 4».
- **H-6 · Due controlli d'assenza in `AboutTab.test.ts` non possono fallire** — minimo; H (test-author, CP5b), 15/10.
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
- **H-9 · Una seconda chiamata di `configure_logging()` lascia aperti i gestori che toglie** — minimo; H (test-author,
  lotto del log di accesso), 15/10.
  - `logging_config.py` toglie i gestori della radice con `removeHandler` senza `close()`; poi `basicConfig(force=True)`
    non trova più niente da chiudere.
  - Conta solo per il file di log, e in produzione la chiamata è una per processo.
  - Cura: `close()` su ogni gestore tolto, oppure lasciare la pulizia a `basicConfig(force=True)`.

  Dettagli: piano H, §14 «Lotto "credenziali nei log di accesso"».
- **H-10 · `services static-uploads` è dichiarata `write-scoped`, ma svuota la cartella degli upload della corsia** —
  basso; H (test-author, G-10), 15/10.
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
- **H-12 · Un avvio fallito del server condiviso dei test non dice perché** — basso; H (verifica di A5), 15/10. Metà ✅
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

## A · Account e accessi (fase 01)

Piano: [`02_accounts`](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md).

- **A-1 · Un utente loggato vede più di «nomi broker e nomi utenti»** — medio, decisione (privacy; multi-utente e
  cloud); A (14/10).
  - Le email degli admin con `GET /users/search?admins=true`.
  - Nome e icona di tutti i broker con `GET /brokers?include_inaccessible=true`.
  - Elenco, anteprima e download di tutti i file caricati: `GET /uploads` e `/uploads/file/{id}`; solo la cancellazione
    controlla il proprietario.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), sezione «A1.8».
- **A-2 · `GET /settings/global` si legge senza login** — basso; A (14/10). Espone tutte le impostazioni globali:
  scheduler, durata della sessione, registrazione. Dettagli: idem, §2 «Da sapere».
- **A-3 · `reset_password` calcola bcrypt sul loop degli eventi** — basso; A (14/10).
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
  - Dettagli: idem, §2 «Deriva della devWiki», «A1.4» e «A2.3».
- **A-5 · Formato preesistente in file toccati da A1** — minimo; A (14/10).
  - black riformatterebbe 4 file, già così alla base: `scripts/user_cli.py`, `scripts/coverage_analysis.py`,
    `test_portfolio_api.py`, `test_portfolio_wac.py`.
  - ruff segnala W293 a `user_cli.py:208` e PLC0415 a `:271`.
  - ✅ **`user_cli.py` chiuso il 15/10** con A3, che ne tocca i comandi (L12): black, W293 e PLC0415, più il C901
    portato dal comando nuovo (ora una tabella). Restano gli altri tre file, fuori dal dominio di A.
  - Dettagli: idem, «A1.6» e «A3.3».
- **A-6 · Una fonte sola per le regole della password** (richiama T-B4 della sezione «T (colori)») — basso; A
  (15/10).
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
- **A-7 · Doc per sviluppatori non allineate al codice, trovate in A3** — minimo; A (15/10, `docs-writer`).
  - `architecture/access_control.md:116-123`:
    - dice che `set_user_admin()` non controlla l'ultimo admin, ma da `2fb8b8502` l'ultimo admin attivo non si
      declassa né si disattiva;
    - dice che un account disattivato riceve un 401, ma riceve un 403 `ACCOUNT_DISABLED`, e solo con la password
      giusta.
    - ✅ **Chiuse il 15/10** con A4b: `docs-writer` le ha corrette insieme alle righe sulle sessioni.
  - `frontend/components/features/settings.md`: il titolo «GlobalSettingsTab (Admin only)», ma la scheda la vedono
    tutti. Si sistema in A6, con le schede Utenti e Sicurezza (attenzione all'ancora).
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
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A3.5», «A4.5» e «A4b.4».
- **A-8 · Richiama TC-6** della sezione «T (colori)»: alla prima visita con il browser in `it-IT`, il selettore della
  lingua mostra l'inglese — basso; programma colori (15/10).
  - Probabile causa: `lib/stores/app/language.ts`, `init()`.
  - Si corregge in un lotto di A che tocca la pagina d'accesso o le preferenze, con il rosso visto prima (E2E con il
    locale del browser `it-IT`).
  - ✅ **Corretta in A5b** (15/10; commit all'ingresso di A5). Il negozio della lingua segue `locale` di
    svelte-i18n finché non c'è una preferenza salvata e nessuno ne sceglie una. Il selettore pubblica
    `data-language`. Rosso visto prima: `language.test.ts` (6 rossi su 7, poi 7 ✅). L'E2E `it-IT`/`fr-FR` in
    `auth.spec.ts` gira dopo la finestra.
  - Dettagli: idem, «A3.0».
- **A-9 · Il runner non toglie le variabili degli account dall'ambiente della corsia** — basso; A (15/10, trovata da
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
  - Le pagine EN di A5a e A5b sono nel lotto; IT, FR ed ES sono indietro su 6 pagine: `admin/configuration`,
    `admin/cli_tools`, `admin/settings`, `admin/service_exposure`, `community/faq`, `user/getting-started`.
  - Vanno tradotte insieme: si linkano con ancore esplicite nuove (`#accounts`, `#user-limit`, `#registration`,
    `#invite`, `#reset-link`, `#reset-onboarding`, `#invitation-link`, `#password-reset-link`), da tenere uguali
    in ogni lingua.
  - Finché non sono tradotte il build stretto resta verde: le pagine vecchie non puntano alle ancore nuove.
  - Si fa dopo A6–A9, che toccano di nuovo le stesse pagine. La prepara il lotto A10, solo su richiesta
    esplicita del developer (coordinatore, 15/10).
  - In `admin/configuration` IT, FR ed ES manca tutta la sezione «Accounts and Sign-ups» (`#accounts`): nessuna
    delle tre variabili `LIBREFOLIO_REGISTRATION`, `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_PUBLIC_URL`. Il coordinatore
    (15/10, 16:56) conferma che è debito di A.

  Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A5b.5».
- **A-11 · Un tema non valido in `user_settings` blocca l'accesso** — basso; trovata dal `test-author` di E (15/10),
  letta nel codice e non ancora provata; segnalata dal coordinatore.
  - Una riga di `user_settings` con un `theme` diverso da `light`, `dark` e `auto` farebbe rispondere 500 a
    `/auth/login` e a `/settings/user`.
  - Prima della correzione serve un rosso. È piccola: va in un lotto dopo A5.
- **A-12 · `e2e/settings.spec.ts`: selettori ancora fragili nei test non toccati da A5b** — minimo; A (15/10,
  `test-author` della riparazione).
  - I test dei numeri usano `.first()` su `.setting-row input[type="number"]`, i `title` tradotti «Save» e
    «Undo» e un XPath su una classe CSS.
  - Lo sblocco usa il `title` tradotto, mentre esiste `settings-lock-toggle`.
  - I due `beforeEach` aspettano la classe `.setting-row` invece di `data-busy` della scheda.
  - Il segnaposto «Coming soon» (disabilitato sempre) non ha più un test: lo copriva per caso il vecchio
    `.first()`. Basta un test di componente (`SettingToggle`, `disabled` e `badge`).
  - I test «non admin» non provano la sola lettura: manca l'asserzione che `settings-lock-toggle` non c'è.
  - Si fa con la scheda Utenti (A6), che tocca la stessa pagina.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A5b.9».
- **A-13 · Su un'istanza bloccata, `/invite` mostra il modulo e la registrazione finisce al login** — minimo;
  A (15/10, dal merge di H CP6; accettato dal coordinatore).
  - Contesto: per non perdere l'accesso, `auth.inspect_link_token` e `auth.reset_password_with_link` entrano in
    `ALLOWED_WHEN_BLOCKED` (lotto piccolo di H dopo A5); `auth.register` resta fuori.
  - Effetto: `tokens/inspect` risponde anche per gli inviti, quindi `/invite` mostra il modulo. La registrazione
    riceve poi un 401 (anonimo su una rotta bloccata), e l'interceptor del client porta al login senza spiegare.
  - Possibile cura: la pagina d'invito che riconosce il blocco (per esempio un campo pubblico e innocuo in
    `/system/instance`, da concordare con H e con la decisione 15), oppure `tokens/inspect` che sul blocco
    risponde come per un link non valido quando lo scopo è `invite`.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A5b.10».
- **A-14 · `access_control.md`: «The last OWNER cannot remove themselves» contraddice «Self-Management»** — minimo;
  trovata dal `docs-writer` di A6a (15/10), fuori dal perimetro di A, segnalata al coordinatore.
  - In «Key Rules & Constraints» l'ultimo OWNER non può togliersi; in «Self-Management», e nel codice
    (`BrokerService.leave_broker`), l'ultimo OWNER che se ne va elimina il broker.
  - La pagina è del controllo d'accesso ai broker: la correzione è di chi la tiene (W, o chi decide il coordinatore).
  - **Assegnata a W** dal coordinatore (15/10, 16:56), con la doc di `leave_broker`.
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A6.5».
- **A-15 · La docstring di `instance_block.py` non cita la sonda dell'indirizzo** — minimo; trovata dal
  `docs-writer` di A6a (15/10). Il file è di H.
  - La docstring elenca come esempi le rotte pubbliche fuori da `ALLOWED_WHEN_BLOCKED`. Da A6a ce n'è un'altra,
    `GET /auth/address-probe`, che con l'istanza bloccata risponde 401 come le altre.
  - Una riga, da mettere nel lotto piccolo di H su `ALLOWED_WHEN_BLOCKED`, o da A al prossimo aggiornamento di base.
  - **Girata ad H** dal coordinatore (15/10, 16:56).
  - Dettagli: [piano 02_accounts](../Phase_1/02_accounts/plan-phase01Accounts.prompt.md), «A6.5».

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
- **X-R6 · `web_link_finder`: timeout e numero massimo di URL non validati** — piccolo; segnalato da H il 15/10 (lotto
  `web_link_finder`), girato a X dal coordinatore. Preesistente e invariato dagli spostamenti. `config/plugins.py:46-52`
  accetta `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` a `nan` o `inf` (`float()`), e `services/assets/web_link_finder.py:108`
  (`DDGS(timeout=int(timeout) or None)`) allora solleva: la ricerca rende `[]` scrivendo solo un debug (`:244-245`); un
  timeout sotto 1 diventa `int(…) == 0`, cioè nessun timeout; con `LIBREFOLIO_WEB_LINK_FINDER_MAX=0` il controllo di
  `:259` arriva dopo il primo `append`, e torna comunque un URL. Cura: valori finiti e ≥ 1 negli accessori di
  `config/plugins.py` (file di H: d'accordo con H) e un timeout non intero rispettato; con il CP6 (F05) o il CP10, che
  toccano la configurazione dei plugin. Dettagli: [piano 03](../Phase_1/03_pluginsAssets/plan-phase01PluginsAssets.prompt.md),
  sezione «15», quinto aggiornamento di base.
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

## W · Import e transazioni (fase 01)

Piano: [`04_importTransactions`](../Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md).

- **W-B1 · L'icona dei plugin servita con un controllo `startswith`** — basso, sicurezza; W, 14/10 (analisi).
  `serve_plugin_static` (`backend/app/api/v1/uploads.py:541`) confronta i percorsi come stringhe: una cartella sorella
  che comincia con lo stesso nome passerebbe il controllo. Oggi non ce n'è nessuna, e la rotta chiede il login. Cura:
  `Path.is_relative_to`, con U-B3 (lotto W5), d'accordo con H. Dettagli: piano 04, §1.1 e §7.
- **W-B2 · Il cambio di provider scollega in silenzio le transazioni dagli eventi automatici** — medio-basso, dati; W,
  14/10 (analisi). `asset_sources/provider_management.py:186-195` (di X): cambiando i parametri o il provider di un
  asset, gli eventi del provider si cancellano e le transazioni collegate perdono il collegamento senza avviso. È il
  caso che la modale di C-65 deve mostrare (C-65a, X e W). Dettagli: piano 04, §2 (C-65).
- **W-B3 · Un file BRIM senza `target_broker_id` è aperto a ogni utente** — da verificare, sicurezza; coordinatore,
  14/10. `_get_brim_file_with_access` (`backend/app/api/v1/brokers.py:119`) salta il controllo dei ruoli quando il file
  non ha un broker (i file vecchi, alla radice delle cartelle). Prima un rosso: se quei file possono ancora esistere, e
  chi li vede. Dettagli: piano 04.
- **W-B4 · Gli id dei file BRIM accettati senza controllo del formato** — basso, sicurezza; coordinatore, 14/10. Le rotte
  `/brokers/import/files/{file_id}` accettano una stringa qualsiasi: un controllo del formato UUID all'ingresso è una
  difesa in più sui percorsi. Dettagli: piano 04.
- **W-B5 · La cassa del broker conta le transazioni future** — da verificare, numeri; coordinatore, 14/10 (D-J16
  dell'analisi di J, con B15 lato broker). `TransactionService.get_cash_balances`
  (`backend/app/services/transactions/transaction_service.py:476-480`) somma tutte le transazioni del broker, anche
  quelle con una data futura. Dettagli: piano 04; analisi di J.
  ✅ 15/10, `6be11ecf3` (N1a): il riepilogo del broker prende `as_of`, il giorno dell'utente, per cassa, quantità e costo
  medio; la cassa dalla casa unica (`native_balances`). Il resto della copia per la convalida del batch è W-B19.
- **W-B6 · V-3, TRANSFER orfano: la scrittura e la migrazione dei dati** — basso; coordinatore, 14/10 (D-J4). A W la
  conversione in ADJUSTMENT della metà rimasta quando si cancella un broker, e la correzione degli orfani già presenti
  nei DB; a J i rossi su lotti e Dashboard. Dettagli: voce V-3 nella sezione V.
  ✅ 15/10, `6be11ecf3` (N1b-1, la cancellazione) e `5e19c6018` + `0e4bd9790` (N1b-2/N1b-3, la correzione
  post-migrazione `orphan_pair_halves`, entrata col punto 46 del developer): la gamba in arrivo di un TRANSFER diventa un
  ADJUSTMENT col suo costo (Auto se mancava, finché c'è il mittente; senza, «costo mancante» con l'avviso), quelle di
  cassa un DEPOSIT o un WITHDRAWAL. **Resta aperto il punto 47** del developer: la gamba in uscita di un TRANSFER perde
  solo il link, come prima; se si decide di convertirla, è un lotto nuovo.
- **W-B7 · `TODO_FUTURI`, eventi collegabili: percorso e conteggi superati** — minimo; W, 14/10 (analisi). L'endpoint è
  `POST /transactions/events/suggest`, i test API sono 10 e non 8, `suggest_events_bulk` sta in
  `services/transactions/transaction_service.py:492`. Si aggiorna quando la voce entra nel lotto K3. Dettagli: piano 04,
  §2.
- ✅ **W-B8 · `DataImportModal`: «Help» e «Close» in inglese** — minimo; W, 14/10 (analisi). Gli `aria-label` di
  `components/ui/data-editor/DataImportModal.svelte:211` e `:220` sono scritti nel codice; vanno con P-15 (lotto K1).
  Dettagli: piano 04, §2 (P-15). ✅ Chiusa il 15/10 (lotto K1 della 1.3, `532a1fd9c`; in `dev_release2` con `d915c869f`).
- ↪ **W-B9 · `test_fx_api.py` raggiunge ECB via rete** — spostata nella sezione X dal coordinatore il 15/10
  (dominio dei cambi), dove X l'ha già ripresa con i dettagli.
- **W-B10 · `access_control.md`: l'elenco degli endpoint d'accesso non è quello dell'API** — minimo, doc; W, 15/10 (W2).
  `mkdocs_src/docs/developer/architecture/access_control.md`, «API Endpoints», elenca `POST /brokers/{id}/access` e
  `PATCH`/`DELETE /brokers/{id}/access/{user_id}`; l'API ha `GET` e `PUT /brokers/{broker_id}/access` (tutta la
  configurazione in un colpo), `PATCH` e `DELETE /brokers/{broker_id}/access/me` (`backend/app/api/v1/brokers.py:408`,
  `:440`, `:493`, `:519`). L'elenco dei metodi sopra è stato corretto in W2. Dettagli: piano 04, §12, W2 passo 5.
- ✅ **W-B11 · `TransactionBulkModal.svelte`: `brokerName()` non ha chiamanti** — minimo, codice morto; W, 15/10 (I1). La
  funzione (`frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte:1597`) non è usata da nessuna
  parte del file né altrove; i nomi dei broker passano da `renderBrokerHtml`. Si toglie col taglio della modale (FE8a).
  Dettagli: piano 04, §12, I1. ✅ Chiusa il 15/10 (lotto FE8a-2: la funzione è tolta col taglio del Bulk).
- **W-B12 · `test_cross_broker_access_failure_is_atomic` lascia i suoi broker nel DB condiviso** — minimo, test; W
  (test-author di I1), 15/10. Il test (`backend/test_scripts/test_api/test_broker_multiuser_api.py`, MULTI-008d) crea
  due broker e non li cancella; i test V-23 della stessa classe nuova (`TestAccessRefusalPlacement`) puliscono anche dopo
  un rosso, e possono fargli da modello. Dettagli: piano 04, §12, I1.
- ↪ **W-B13 · `fx-csv-import.spec.ts` prende la ✕ della modale d'importazione per testo** — spostata nella sezione X
  dal coordinatore il 15/10 (spec di X).
- **W-B14 · La docstring di `IdentifierType` cita percorsi vecchi, ed è nell'OpenAPI** — minimo, doc; W, 15/10 (W4,
  CP6). `backend/app/db/models.py:127` dice ancora `backend/app/services/brim_provider.py` (ora `services/brim/`), accanto
  a `services/asset_source.py` e `schemas/assets.py` di X. La docstring diventa la descrizione dell'enum nell'OpenAPI,
  quindi un lotto di riordino, che vuole lo schema identico, non la tocca. Cura: un lotto che accetta la differenza
  nella descrizione, insieme a X per le sue due righe. Dettagli: piano 04, §12, W4.
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
- **W-B17 · L'API accetta una FX_CONVERSION fra due broker** — basso, dati; W, 15/10 (N1). I metadati vogliono le due
  metà sullo stesso broker (`backend/app/schemas/transactions/type_metadata.py:313-315`, `broker_id: equal`), e il form, la
  promozione e gli import le scrivono così; ma `_validate_linked_pair` (`backend/app/services/transactions/validation.py:64-89`)
  rifiuta TRANSFER e CASH_TRANSFER sullo stesso broker e non rifiuta una FX_CONVERSION su due broker, quindi
  `POST /transactions/commit` con un `link_uuid` su due broker la crea, e cancellando uno dei due broker ne resta una metà
  (N1b-1 la converte per segno, come lo split). Cura: `pairBrokerMismatch` per una FX_CONVERSION su due broker, con il
  rosso. Dettagli: piano 04, §12, N1.
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
- **W-B20 · `delete_bulk` non è atomico per broker** — basso, dati; W, 15/10 (N1, trovato da docs-writer; riscritta il
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
- **W-B28 · Debito di traduzione delle pagine utente di E1b** — minimo, doc; W, 15/10 (E1b). Cambiate solo in inglese,
  senza stamp: `user/assets/detail/data-editor.en.md` (§ 📅 Events tab: il salvataggio tutto o niente e l'elenco dei
  rifiuti; § 📥 Import from CSV: il `type` e la colonna `currency`), `user/assets/detail/events.en.md` («From you» e il
  nuovo H3 `#new-event`, da tenere con quell'àncora in ogni lingua: `form` la cita), `user/transactions/form.en.md`
  («Missing event?»). IT, FR ed ES con la pipeline, su richiesta del developer. Dettagli: piano 04, sezione E1, passo 5.
- **W-B29 · `asset-event-delete.spec.ts`: lo scenario 1 scrive su Apple condivisa a una data fissa** — minimo, test; W,
  15/10 (E1b, segnalato dal test-author). Lo scenario 1 salva un DIVIDEND sull'asset Apple condiviso a una data fissa,
  con un marcatore `Date.now()`: se i progetti desktop e mobile lo eseguono insieme, il secondo upsert sovrascrive la riga
  del primo. Lo scenario 2 marca le righe con una sonda `isVisible().catch`. Cura: un asset proprio per test, come in
  `asset-event-editor-save.spec.ts`. Dettagli: piano 04, sezione E1, passo 3.
- **W-B30 · Svuotare un costo manuale non lo toglie: la modifica lo tiene in silenzio** — basso, numeri; W, 15/10 (N2,
  test-author). In un aggiornamento `cost_basis_override: null` vale «invariato», come un campo assente
  (`_apply_update_values`, `backend/app/services/transactions/batch_edits.py`): il modulo, quando l'utente svuota un costo
  manuale, manda `null` e il backend tiene il costo di prima senza dirlo. Da decidere: un modo esplicito di togliere il
  costo (con la regola del costo obbligatorio che poi lo rifiuta dove serve) o un messaggio. Dettagli: piano 04, sezione
  N2.
- **W-B31 · La regola 12 del costo è una seconda copia scritta a mano** — minimo, codice; W, 15/10 (N2, test-author).
  `validate_transaction_business_rules` (`backend/app/schemas/transactions/transactions.py`, regola 12,
  `costBasisModeIncompatible`) ammette `cost_basis_mode` solo per TRANSFER e ADJUSTMENT con quantità > 0, a mano, mentre
  N2 legge dai metadati il costo obbligatorio (`cost_basis_required`). Leggerla da `TX_TYPE_METADATA` porterebbe un
  import circolare (`type_metadata.py` importa `transactions.py`): serve spostare la funzione o un import tardivo.
  Dettagli: piano 04, sezione N2.

## J · Numeri e analisi (fase 01)

Piano: [`05_numbersAnalysis`](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md). Righe scritte da J
il 14/10, nel checkpoint J-0; i numeri di riga sono di `c9bb8f257`. G-8 e J-4 scritte il 15/10, nel checkpoint CP-1.

- **J-1 · Copie della matematica comune fuori dall'inventario del 43** — basso; J, 14/10 (analisi). Ognuna va nel
  lotto che unifica la sua famiglia:
  - `risk/metrics.py:741` (giorni di calendario → osservazioni, con 365) → U4a, CP-10;
  - `portfolio_service.py:824` (G/L % della posizione) → U4b, CP-4;
  - `series_preparation.py:184` (fattore di cambio ricavato dal close) → U1, CP-11;
  - `fx.py:717` (inversione del tasso nella catena delle rotte) → U1, nei file di X dopo il suo PL4 (D-J17);
  - `ai_export/components/fx_timing_context.py:361-362` (rendimenti dal minimo e dal massimo) → U9, CP-12;
  - frontend, per Y con U8: `lib/charts/signals/CompoundSignal.ts:69` (curva what-if, eccezione interattiva da
    dichiarare, R19) e `lib/components/risk/levels/levelHelpers.ts:359` (rendimento che recupera una perdita).
  - **15/10, nella revisione di V-3 per W**: la quantità per posizione a una data non ha una funzione nella casa, e oggi
    si conta in più posti: in `transactions/balances.py` (`get_asset_holdings` e la metà delle quantità di
    `_get_balances_before_date` e del replay della validazione) e nel `cumulative_qty` del motore. Da decidere se il
    registro delle quantità appartiene alla casa. La metà della cassa la rifà W come W-B19, su `native_balances`.
  - **15/10, nel piano di CP-6**: un buco nei cambi si legge in due modi. Il motore valuta i titoli e la cassa in
    transito a giorno esatto (`fx_rate_map.get`: niente cambio → valore mancante, `daily_state.py:1031`,
    `_convert`); la cassa nativa porta avanti l'ultimo cambio noto senza limite (`native_cash._rate_at`). Con un buco
    oltre la finestra di riempimento di `convert_bulk`, la cassa resta valutata e i titoli no. Una sola regola per i
    buchi → U1, CP-11. CP-6 usa una sola funzione dei giorni di cambio, che riceve la lettura del chiamante.

  Dettagli: [piano J](../Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md), §1.2 «Copie nuove».
- ↪ **J-2 · Il server di test costruisce frontend e documentazione dentro i 300 s d'avvio** — spostata nella sezione C
  dal coordinatore il 15/10 (runner condiviso), come C-94.
- **J-3 · Monte Carlo e ricampionamento a 365 giorni fissi** — da verificare; T, 11/10 (piano 43, §5, «da segnalare a
  parte»), ripresa da J, che ora possiede il rischio. `risk/quant/quantlib_worker.py:116,195` e
  `risk/quant/resampling.py:235` contano 365 giorni all'anno, mentre il resto del rischio usa il fattore osservato. Può
  essere una convenzione di calendario coerente: prima un test che lo provi, poi l'eventuale cura in CP-10. Dettagli:
  [piano 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), §5.
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
- **J-9 · Il lotto da ADJUSTMENT-in prende la valuta della riga, non quella del costo** — medio, numeri; trovata dal
  test-author di W (V-3), verificata da J il 15/10. `fifo/engine.py:353` apre il lotto con la `currency` della riga,
  mentre il prezzo è `cost_basis_override`, che sta in `cost_basis_currency`. Con `currency` nulla, ammessa perché
  l'importo è 0 (`db/models.py`, docstring di `Transaction`), `FxRateResolver.convert` (`financial_math/lots/conversions.py:59-60`)
  tratta il costo come già nella valuta del report: niente conversione, niente segnalazione. Il costo medio legge
  invece `cost_basis_currency` (`average_cost.py:280-289`), quindi i due motori leggono lo stesso costo in due valute.
  Tocca ogni ADJUSTMENT-in con il costo in un'altra valuta, e anche le righe convertite da V-3. Cura: la valuta del
  lotto è `cost_basis_currency` quando il prezzo viene dall'override. Prima il rosso: un ADJUSTMENT-in in USD e un
  report in EUR, con `currency` diversa e con `currency` nulla. Dettagli: piano J, §10 «Domande di W N1».
- **J-10 · I lotti falliscono quando il broker mittente di un TRANSFER è fuori dallo scope** — medio, numeri e
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

  Dettagli: piano J, §10 «Domande di W N1».
- **J-12 · Con l'analisi dei lotti `FAILED` il pannello disegna lo stesso lotti e cifre** — medio, chiarezza (utenti
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
- **J-13 · Volatilità, Sharpe e Beta mobili mostrano «giorni» ma contano osservazioni** — basso, chiarezza (utenti
  non esperti); J, 15/10, nella nota sul punto 29 per il coordinatore.
  - `rolling_volatility`, `rolling_sharpe` e `rolling_beta` dichiarano `"x-suffix": "days"` sulla finestra (come oggi
    `rolling_return`), mentre il tooltip condiviso `signals.tooltips.riskWindow` dice «Number of prepared daily return
    observations».
  - Per questi stimatori le osservazioni sono la misura giusta (annualizzazione per periodi): si cambia **solo
    l'etichetta**, in «osservazioni», nei 4 cataloghi. Deciso dal coordinatore il 15/10: nessun cambio di calcolo.
  -   Va con CP-10a, insieme al punto 29 (un solo Rolling Return a giorni di calendario, approvato dal developer il 15/10).

  Dettagli: piano J, §10 «Decisioni 26–30 (15/10) e piano dei lotti sbloccati».
- **J-14 · Copie del realizzato e della G/L % da portare alla regola del punto 26** — medio, numeri; J, 15/10. Il
  developer (punto 26): «se ci sono altre aree di codice che fanno una cosa simile, magari duplicando, segna che bisogna
  fattorizzare e ottenere il meglio dalle 2 con la policy corretta». Regola: costo al cambio dell'acquisto, proventi al
  cambio della vendita; il motore della Dashboard la applica già.
  - nei lotti di J (CP-7, con un rosso per ogni comportamento che cambia): `lots/histories.py:160-182`,
    `lots_analysis_service.py:728-770` e `:1042-1045`, e di riflesso l'AI Export (`payloads/portfolio_broker.py:604-606`,
    `:775-776`);
  - duplicati senza cambio di valore: l'identità del periodo nell'AI Export (`portfolio_financial.py:489`,
    `broker_financial.py:434`, CP-12); la G/L % in `portfolio_service.py:824`, `:939` (CP-4);
  - **in un file di W**: `brokers/summary.py:119-135`, terza copia della G/L %, nella valuta dell'asset: da smistare
    dal coordinatore.

  Dettagli: piano J, §10 «Decisioni 26–30 (15/10) e piano dei lotti sbloccati», «Inventario del punto 26».
- **J-15 · La galleria ristampa l'output di Playwright senza flush** — basso, strumenti (programma colori); J, 15/10,
  nella prova di C-94. `dev.py`, `cmd_mkdocs_gallery`, `print(line, end='')` nel ciclo su `proc.stdout`: su una pipe
  (il `tee` di `gallery_snapshot.sh`, i log) Python bufferizza a blocchi, e l'avanzamento di Playwright arriva a pezzi da
  8 KB o tutto alla fine, nell'ordine giusto ma senza l'ora vera; sul terminale va bene. Com'era prima di C-94. Cura
  proposta: `flush=True` su quella riga, col via del coordinatore colori.

  Dettagli: piano J, §10, C-94, passo 6 (3), «Fuori pista».

## Z · Sospensione e risveglio (fase 01)

Piano: [`06_sleepWake`](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md).

- **C-49 (sezione C) · presa in carico da Z** — prove senza codice in Z6a (autorizzate il 15/10), cura in Z6b con il
  punto 35 delle decisioni. Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione
  «Z6a — prove su C-49, senza codice di prodotto».
  - 15/10, Z: 9 cicli di vita puliti su spec singole; il coordinatore cerca l'avviso nelle sue run di categoria. Dalla
    lettura di uvicorn 0.52.4, con SIGTERM l'ipotesi dei thread è esclusa; restano le richieste in volo (la più
    probabile), i passi del lifespan e i processi figli. Disegno della cura: piano 06, sezione «Z6b — disegno».
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
- **Z-3 · `isHeadToday` confronta con la data UTC** — basso, da verificare; Z, 14/10. Le due pagine degli asset usano
  `new Date().toISOString().slice(0, 10)`: tra mezzanotte locale e mezzanotte UTC il «fino a oggi» sbaglia giorno
  (classe `utc-today-vs-user-calendar` della devWiki). Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md),
  sezione «1. Stato reale».
- **Z-4 · Risvegli orari per singolo titolo** — medio; Z, 14/10, dalla decisione D-19 del business plan. Serve un campo
  per asset; nella 1.3 c'è solo l'intraday globale, spento di default (D8). Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «4. Decisioni».
- **Z-5 · Recupero dall'ultima data salvata invece dei 14 giorni fissi** — basso; Z, 14/10 (F07, priorità bassa). Serve
  a un self-hosted spento per più di due settimane. Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md),
  sezione «2. Già fatto o contraddetto».
- **Z-6 · Il docstring dello scheduler dice che l'elezione del leader gira in un thread** — minimo; Z, 14/10.
  `services/platform/scheduler/scheduler.py:108` chiama `am_i_leader()` (psutil) sul loop. Dettagli:
  [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «2. Già fatto o contraddetto».
- **Z-7 · Calendario dei risvegli: prossima esecuzione per job, `next_wake_at` e jitter** — medio; developer, 15/10
  (decisione 33: «il next_wakeup per ora non serve [...] è una cosa per il futuro quando servirà»). Quando il pannello
  del cloud terrà un calendario: la prossima esecuzione di ogni job (con l'ora legale), `next_wake_at` nella risposta di
  `wake-sync` e in un GET con lo stesso token, il jitter per istanza. La risposta di `wake-sync` nasce estendibile per
  questo. Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «4. Decisioni».
- **Z-8 · Il dettaglio di un asset senza fornitore chiede il prezzo dal vivo ogni 30 s** — basso; Z, 15/10 (Z1). Il
  ciclo unico ha mantenuto la guardia del vecchio ciclo del riepilogo, che non guardava il fornitore: per un asset
  manuale `POST /assets/prices/current` restituisce il valore salvato, e il frontend lo conta come una scrittura del
  portafoglio (`portfolioMutation.ts`). La testa del grafico invece salta senza fornitore. Cura possibile: non avviare il
  ciclo senza un fornitore assegnato. Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md),
  sezione «Passi di Z1».
- **Z-9 · Doc delle pause dei fornitori** — basso; Z, 15/10 (Z7a). Due pagine:
  - la pagina admin `admin/configuration.en.md`, con le due variabili, il default acceso e l'eccezione della decisione
    34;
  - la pagina d'architettura degli asset: il confine e le pause.

  Le variabili esistono da Z7a ma non hanno effetto finché X non aggancia il confine (X1–X4): la doc va scritta con
  l'aggancio. Dettagli: [piano 06](../Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md), sezione «Z7a», passo 5.

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
- **B-2 · Un commento di `DataEditor.test.ts` cita `backend/app/api/v1/backup.py`** — minimo; B, 15/10 (B0).
  `frontend/src/lib/components/ui/data-editor/DataEditor.test.ts:802`: l'export degli eventi ora sta in
  `backend/app/api/v1/backup/exports.py`. Il file è di T (`ui/data-editor`): non lo tocco. Dettagli: piano 07, §13, B0
  passo 3.
- ✅ **B-3 · La docstring di `backup_asset_prices` cita `backup_service.PRICE_COLUMNS`, ed è nell'OpenAPI** — minimo, doc;
  B, 15/10 (B0). **Chiusa il 15/10 con B1**, che cambia comunque l'API. `backend/app/api/v1/backup/exports.py:71`: il modulo ora è `series_export.py`. Un lotto di riordino
  lascia lo schema identico, quindi la correggo in B1, che cambia comunque l'API. Dettagli: piano 07, §13, B0 passo 2.
- **B-4 · I comandi dell'immagine elencati senza `backup`** — minimo, doc; B, 15/10 (B6a, segnalato da docs-writer).
  `docker_advanced.en.md#docker-exec` («In the image, `user`, `db` and `info` work»), il commento in testa a
  `docker-compose.yml` e `admin/index.en.md:21` («user management, database upgrades») non dicono che anche
  `dev.py backup` funziona nell'immagine. I file Docker sono di H fino al CP7a. **Passata ad H dal coordinatore** (15/10,
  14:37). Dettagli: piano 07, §13, B6a.
- **B-5 · `filesystem.en.md` «💾 Backup» non conosce `dev.py backup`** — piccolo, doc; B, 15/10 (B6a). Il file è di H
  (CP3). Mancano:
  - un rimando a `cli_tools.md#backup`, l'unico modo di fare un backup coerente a server acceso senza `sqlite3`;
  - la nota che la copia della cartella dati prende anche `backups/`, con gli archivi;
  - `backups/` nell'albero della cartella;
  - un'ancora esplicita `{: #what-to-back-up }` sul titolo «✅ What to Back Up», nelle 4 lingue: i titoli tradotti hanno
    slug diversi, quindi la pagina della CLI ora punta a `filesystem.md#backup`.

  Testo proposto da docs-writer nel piano 07, §13, B6a. **Passata ad H dal coordinatore** (15/10, 14:37).
- **B-6 · Il polling della scheda Backup ha il suo ciclo** — minimo; B, 15/10 (B5a). `BackupJobController` legge il
  job con un suo `setTimeout`, perché nella base non c'è ancora l'aiuto comune di Z (F26, «un solo aiuto di polling per
  tutti i cicli»). Quando entra, il controller lo usa. Il ciclo è breve e solo durante un backup avviato dall'admin.
  Dettagli: piano 07, §13, B5a.
- **B-7 · Debito di traduzione di `cli_tools.{it,fr,es}.md`** — piccolo, doc; B, 15/10 (B6a). Mancano la sezione
  «💾 Back Up the Instance» (5 sottosezioni), una frase dell'introduzione e il punto Docker del suggerimento. La pagina
  inglese non è timbrata: la traduzione passa dalla pipeline Aphra, su richiesta del developer.
- **B-8 · Un backup avviato dalla UI la cui risposta si perde resta invisibile alla scheda** — minimo; B, 15/10 (B5a,
  segnalato da test-author). Se la risposta di `POST /backup/instance` si perde (rete, timeout), il job gira sul server
  ma la scheda non conosce il suo id. Nessuna rotta elenca il job in corso, e il rifiuto `backup_busy` non lo porta.
  - Effetto: «busy» finché quel job finisce; il suo archivio scade dopo un'ora senza essere offerto; lo spazio su disco
    resta occupato per quell'ora.
  - Cura possibile: l'id (e l'origine) del job in corso nel dettaglio di `backup_busy`, così la scheda lo segue. Con
    un'attenzione: un job della CLI si sposta fuori da `.jobs/` alla fine.

  Dettagli: piano 07, §13, B5a, terza tornata.
- **B-9 · Il token del pannello non è fra i controlli della configurazione** — piccolo; B, 15/10 (B8).
  - Oggi un `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` inutilizzabile (corto, non ASCII visibile, `_FILE` illeggibile) si vede
    solo alla prima richiesta del pannello: 503 `backup_panel_unavailable` e una riga d'errore nel log.
  - All'avvio, `log_configuration_audit()` non lo nomina, e la futura scheda «Sicurezza» non lo mostrerà.
  - Cura possibile, come ha fatto E per l'email: `BACKUP_CONFIG_CHECKS` in un modulo di B (stato `ok`, `info` se
    spento, `error` se inutilizzabile, mai il valore), una riga in `config_audit.CONFIG_CHECKS` (file di H) e le
    chiavi `backup.checks.*` nelle 4 lingue.

  Dettagli: piano 07, §13, «B8 — il token del pannello, rimesso sopra `ef61f0e7f`».

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
- **E-3 · `ApiError` non lo costruisce nessuno: le rotte rifiutano con `AxiosError`** — piccolo; E, 15/10 (E2a).
  L'intercettore di `zodios-client.ts` dice «wrap in ApiError» ma lascia passare l'`AxiosError`; chi legge solo
  `error instanceof ApiError` vede ogni rifiuto come errore generico (la scheda Email ci era caduta: corretta, legge
  `isAxiosError`). Da decidere: convertire nell'intercettore, oppure togliere `ApiError` e il commento.
  Dettagli: piano 08, «E2.6».
- **E-4 · `status.HTTP_422_UNPROCESSABLE_ENTITY` è deprecato in Starlette** — minimo; E, 15/10 (E2a). Dà un
  `StarletteDeprecationWarning` a ogni 422 delle quattro risposte di `api/v1/settings.py` che lo usano; il nome nuovo
  è `HTTP_422_UNPROCESSABLE_CONTENT` (lo usa `api/v1/email.py`); gli altri router scrivono `422`.
  Dettagli: piano 08, «E2.4».
- **E-5 · `api sync` non sfugge i backtick delle descrizioni su più righe** — piccolo; E, 15/10 (E2b).
  `openapi-zod-client` scrive una descrizione di più righe come template literal JavaScript senza sfuggire i
  backtick: una docstring di schema su più righe con ``` ``codice`` ``` rompe `generated.ts` al caricamento
  (`TypeError: "…" is not a function`), e con lui ogni pagina. Successo con `EmailInstanceConfig` (corretto: docstring
  su una riga). Le docstring di `backend/app/schemas` hanno 131 tratti tra doppi backtick: da sfuggire in
  `api sync` (un passo come `fix-openapi-discriminators.mjs`) o da vietare con un test sullo schema.
  Dettagli: [piano 08](../Phase_1/08_email/plan-phase01Email.prompt.md), «E2b.4».
- **E-6 · Il registro delle schede di Impostazioni importa ogni corpo di scheda** — minimo; E, 15/10 (E2b). Ogni
  scheda nuova obbliga ogni test che importa il registro vero ad aggiungere un mock, o il file non si carica
  (`page.tabs.test.ts` con la scheda Email); toccherà anche B e X. Da valutare con A: corpi caricati pigri o un
  aiuto di mock comune. Dettagli: piano 08, «E2b.4».

## Y · Cruscotto e grafici (fase 01)

Piano: [`09_dashboardCharts`](../Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md). Sessione avviata il
15/10 alle 11:28, solo analisi, sulla base `23f6578f3`. Codice autorizzato il 15/10 alle 12:47 (developer, via il
coordinatore): Y1 (taglio di `GrowthChart`, con B10) e Y2 (taglio di `DataTable`), sulla base `1e9e567f7`. Righe scritte
da Y il 15/10.

- **Le voci di Y vivono nelle loro sezioni** (C-85, C-62 e C-38 nella C; B10, 47-1, 48-1 e 54-1 nella I; T-U8 e
  T-FE2…FE11 nella T; K-13, K-15, C-15, C-34, I-01, I-03 e O-16 nel backlog 38; i difetti 2 e 5 nel README della 13):
  le chiude il coordinatore a ogni treno. Stato all'analisi e lotto di ciascuna: piano di Y, §2.
- **Y-1 · I-03 è curata solo a metà** — basso; Y, 15/10 (analisi). Il ripiego da % ad Abs scatta solo per la vista %
  ripristinata al caricamento (`GrowthChart.svelte:785-789`, dal 24/09); cambiando periodo o broker verso una storia
  senza dati in percentuale, il bottone resta premuto e disabilitato (`:2539-2546`). Da confermare nel browser, nel lotto
  Y8. Dettagli: piano di Y, §2.
- **Y-2 · Nella cascata settimanale una linea di broker che finisce a metà settimana diventa un buco** — basso, da
  verificare; `test-author` di Y, 15/10 (Y1). Comportamento preesistente, spostato alla lettera in
  `dashboard/growthChartData.ts` (`aggregateMetric`): il valore di un secchio si cerca sull'ultimo giorno della settimana
  presente in storia (`bucket.date`), mentre `aggregateLineSeries` lo mette sull'ultimo giorno con un valore. Una serie
  con valori a inizio settimana e `null` l'ultimo giorno (una linea di broker che esce dal perimetro) mostra un buco in
  quel secchio; la scala delle candele, invece, tiene l'ultimo valore. Prima un test rosso. Dettagli: piano di Y, §7
  «Y1 — passo 4».
- **Y-3 · Il gate della privacy non conosce `t(` come chiamata di traduzione** — minimo; `test-author` di Y, 15/10 (Y1).
  `moneyRenderSites.test.ts` esclude dai token numerici solo `$_(`, `$t(` e `label(`: nel tooltip di GrowthChart, ora
  `growthChartTooltip.ts`, il traduttore si chiama `t`, e una chiave come `dashboard.totalPnl` conta come token
  numerico. Rende il gate più severo, non più cieco: oggi c'è un solo reperto, registrato. Da decidere se aggiungere
  `\bt\(` alla forma, misurando prima il rumore. Dettagli: come Y-2.
- **Y-4 · I commenti di `SignalTreeSelect.test.ts` descrivono ancora la scelta a clic della galleria** — minimo; G
  (G-12), via il coordinatore, 15/10. Righe 16–17 e 306–310: `selectIndicatorFromTree` della galleria vi espande la
  famiglia con un clic e clicca l'opzione, mentre da G-9 (`1470bd693`) la galleria sceglie l'indicatore da tastiera. Va
  corretto solo il testo dei commenti, quando Y passa da quei file (FE2, lotto Y4). Dettagli: piano di Y, §2.
- **Y-5 · Il commento di `headerTooltip` in `table/types.ts:291` promette un'icona che non c'è** — minimo; `docs-writer`
  di Y, 15/10 (Y2). Dice «(info icon)», ma `headerTooltip` da solo mette un tooltip sull'etichetta dell'intestazione:
  l'icona compare solo con `headerTooltipUrl`. La pagina `core-ui/data-table.md` è già corretta (Y2). Va corretto solo
  il commento, quando Y o altri toccano `types.ts`. Dettagli: piano di Y, §7 «Y2 — passi 5–6».
- **Y-6 · `AllocationPanel` passa ancora `emoji` alla torta, che dopo DV non lo legge più** — minimo; coordinatore (DV),
  15/10. `dashboard/AllocationPanel.svelte:65` (`toAllocEntries`) mette `emoji` in ogni voce, e il tipo `AllocEntry`
  (`:23`) lo dichiara: dopo l'ingresso di DV la torta non lo legge più, quindi è un dato morto. Da togliere in Y10,
  dopo DV. Dettagli: piano di Y, §2.
