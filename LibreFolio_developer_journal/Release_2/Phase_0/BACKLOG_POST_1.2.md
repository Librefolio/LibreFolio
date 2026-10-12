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
| [README della 09](09_feedbackJobs/README.md) | Backlog strutturale P4 e feedback, «Cosa resta aperto» in cima (09/10) | 7 voci: 6 nella sezione 09, SP14 nella D |
| [`TODO_FUTURI.md`](../../../TODO_FUTURI.md) | Il futuro deliberato, non backlog | 52 temi |

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
- **C-58 · Dettaglio broker: un test sfora i 30 s sotto carico** — basso; coordinatore, 12/10. Nel gate del treno 59,
  con carico ~56, «the lot detail modal renders its three sections and the net breakdown»
  (`frontend/e2e/brokers/brokers-detail.spec.ts:410`) è scaduto durante la navigazione, prima del pannello (40,1 s);
  rilanciato con carico 30, è passato in 2,9 s. Nei 30 s stanno login, `ensureBrokerExists`, due navigazioni e il
  pannello. Da valutare con `test-triage`: un budget esplicito o una navigazione in meno.
- **C-59 · L'immagine Docker installa `uvicorn[standard]` fuori dal lock** — medio-basso; coordinatore, 12/10, dalla
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
  - Consiglio: la 1.2 resta su 3.13 (sicurezza fino a ottobre 2029); dopo la 1.2 la **3.14 con la build normale**;
    la 3.15 verso il primo trimestre 2027, dopo una nuova verifica delle wheel; il free-threading più avanti.
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
- **C-64 · Devwiki: il secondo giro di lint** — basso; W, 12/10. Il lint del 12/10 (a base `4d0cedec7`) non ha
  controllato: date e hash in conflitto fra pagine; le feature `planned` o `in-progress` (F-048, F-077–F-108) contro il
  codice; il contenuto degli 11 piani di `phases/06_betaTestingReportAndFixing`. Da fare insieme alla voce qui sotto.
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
- **Devwiki e grafo** — medio: il passo 3 dell'historian e la ricostruzione del grafo dopo la 1.2 (P-6).

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
- **T-ISO · Le date d'osservazione restano ISO nei tooltip del grafico dei prezzi e nella sonda** — basso; T, 13/10
  (trovato con T-EN1; dopo la 1.2, per decisione del coordinatore). Con M-18 le date seguono la lingua
  dell'interfaccia, ma alcune date d'osservazione si leggono ancora `2024-03-01`.
  - In `components/charts/PriceChartFull.svelte`: il segnaposto `{date}` di `chart.tooltip.valueAt` (`:1017`, `:1020`,
    `:1029`), le righe `↩` (`:1018`) e `💱` (`:1023`) del riferimento, la data dell'evento nei periodi aggregati
    (`:778`) e quella del cambio (`chart.tooltip.fxRateDate`, `:789`).
  - In `components/assets/ProviderAssignmentSection.svelte`: la data del prezzo corrente (`:335`) e l'intervallo dello
    storico, `date_range`, che arriva dal backend come una stringa sola (`:355`).

  Da fare: le date con `formatDateTime`/`formatAxisDate` nella lingua della UI; `date_range` va prima esposto come due
  date. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «T-EN — analisi».
- **T-FB · I ripieghi inglesi dei segnali di confronto** — minimo; T, 13/10 (trovato con T-EN2; dopo la 1.2, per
  decisione del coordinatore). Se l'asset di confronto non c'è più, l'etichetta dice `Asset #N` o `Asset`
  (`charts/signals/AssetComparisonSignal.ts:173-174`, e `routes/(app)/assets/[id]/+page.svelte:690`, `:871`, `:895`,
  `:1004`, `:1274`). Una coppia vuota dice `FX Pair` (`charts/signals/FxPairSignal.ts:94`). Si vede solo con una
  configurazione salvata che punta a un asset cancellato. Da fare: chiavi nel catalogo, lette con `ChartSignal.text`
  (T-EN2). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «T-EN — analisi».

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
- **V-3 · TRANSFER orfano: i lotti falliscono, la Dashboard lo conta come capitale in natura** — basso, serve una
  decisione; test-author di V (B1), 12/10. L'analisi dei lotti risponde `FAILED` con `TRANSFER_PAIR_MISSING`. Nessun
  test lo fissa. Dettagli: idem, §9 «Passo 1».
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
- **V-8 · Il pannello Rischio con un broker sparito: 403 e nessuna rilettura** — basso, serve una decisione; V,
  12/10. Se un broker posseduto sparisce dopo che la Dashboard ha letto i broker, per esempio cancellato in un'altra
  scheda, la `risk/query` riceve 403 «Requested portfolio broker subset is not fully accessible» (`risk.py:73,89`).
  Il tab Rischio mostra «Risk data could not be loaded» finché la pagina non rilegge i broker. Da decidere se il
  pannello debba rileggere i broker posseduti e riprovare. Dettagli: piano della 46, §9 «Passo 7» e §11.
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
    - gli altri test di File Preview: i PDF puliscono in `finally` con 30 s, mentre markdown, immagine, dettaglio, zoom
      e commenti non cancellano mai il loro upload (la lista `ownedStaticFiles` ora c'è);
    - il modo griglia/lista si legge dalla classe `active`: servirebbe `aria-pressed` su `view-mode-grid` e
      `view-mode-list` in `files/+page.svelte` (~`:704/707`);
  - la fixture `logout()` (`auth-helpers.ts`) usa ancora i 3 s di default.

  Dettagli: piano della 46, §12.8.
- **V-22 · «+ New event» può modificare un evento esistente dicendo di averlo creato** — da decidere; letto da
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
- **U-B3 · Le icone dentro la cartella del plugin** — basso; U, 12/10, decisione D-7, che le lascia dove sono nella 1.2.
  Servono `static/` nella cartella, la rotta di `uploads.py` e `generate_static_url` nelle 3 basi. Dettagli: piano della
  45, sezione «9».
- **U-B4 · `sample_reports/` per plugin** — basso-medio; U, 12/10, decisione D-7. Ci sono 25 percorsi fra E2E e test
  backend. Dettagli: piano della 45, sezione «9».
- **U-B5 · I vecchi percorsi `<famiglia>/<nome>.py` fuori da U** — basso; U, 12/10. Restano le 84 citazioni in 47
  pagine del devWiki, per l'historian, come T-W1. ✅ `financial-theory/fundamentals/day-count.{en,it,fr,es}.md:10` è già
  corretto nelle 4 lingue (`18e872872`). Dettagli: piano della 45, sezione «3».
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
