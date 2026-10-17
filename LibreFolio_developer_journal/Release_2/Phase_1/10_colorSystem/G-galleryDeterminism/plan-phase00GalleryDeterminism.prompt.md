# Piano — Gallery deterministica (workstream G, cartella 56)

> Aperto il 14/10/2026 da G (sessione `G - Gallery deterministica`, worktree `e-alfy-laughing-spoon`, branch
> `e-alfy-g-gallery-deterministica`). Coordinatore: sessione `aec04834-1532-4d86-9e3f-f942e82aca89`.
> Problema e misura di partenza: [README della 56](README.md), [stabilità del 14/10](evidence/stability-2026-10-14.md).
> Programma: [piano dei colori](../plan-phase00ColorSystemThemeLab.prompt.md). Backlog: sezione «G · Gallery
> deterministica (56)» di [BACKLOG_POST_1.2.md](../../../Phase_0/BACKLOG_POST_1.2.md).
> Dal merge di `dev_release2` del 14/10 (`424adb31c`) la cartella 56 è `Phase_1/10_colorSystem/G-galleryDeterminism/` e
> il programma 55 è `Phase_1/10_colorSystem/`: «la 56» resta il nome del workstream.
>
> **✅ Chiuso il 15/10/2026** su decisione del coordinatore (16:05).
> - La DoD finale (§1) è raggiunta con la misura `g-final3` (passo 6). Dopo sono arrivati il passo 7, G-9 (passo 8) e
>   G-10 (corretta da H).
> - Unico residuo di G nel backlog: G-11.
> - Il prossimo compito di G, fuori da questo piano, è G-13: la nuova coppia di riferimento sul target dopo l'ingresso
>   di T (§4, registro del 15/10, 16:05).

## 0. Baseline e corsia

- HEAD di partenza `b631308d5` = `dev_release2` (fast-forward da `6d0b1266c` fatto dal coordinatore il 14/10).
- Corsia: porta **6153**, dati **`/tmp/librefolio-r2-g`**; Python con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc`.
- **Regole delle run (coordinatore, 14/10 20:10):**
  - run filtrate fino a 5 worker: basta avvisare;
  - gallery complete e run a 10 worker: serve il via;
  - `uptime` all'inizio e alla fine di ogni run, nel log;
  - prima di attribuire alla gallery una schermata instabile o un rosso, quel test va rifatto da solo: una differenza che
    sparisce con meno carico è rumore della macchina.

  Contesto del 14/10 sera: carico 19–27 su 10 core per cause esterne (Spotlight dopo il riavvio, un aggiornamento di macOS,
  build di R e verifiche di L sulla 6152).
- Prove del 14/10 (coordinatore): `/Users/ea_enel/Documents/00_My/LibreFolio_subRepo/LibreFolio_visual_review/`
  (`snapshots/baseline-r1`, `baseline-r1-retry`, `baseline-r2`; `diffs/noise__r1__vs__r2` con maschere e compositi).

## 1. Decisioni del developer (14/10/2026, riportate dal coordinatore)

Testuale: «chat a noi non serve che in questa analisi ogni numero sia identico, basta che lo stile lo sia, lo scopo di
questa analisi e questi screen è evidenziare l'aspetto estetico, non la correttezza del contenuto, quello è compito di
altre chat» e «riguardo a d4 hai il mio benestare».

**Principio.** Si rende deterministico ciò che cambia **stile o inquadratura**: fase delle animazioni, scroll e
posizione, header, transizioni dei modali, grafici fermi, immagini caricate, puntatore e hover. Le differenze di **solo
contenuto** (numeri, orari, dimensioni delle cache, ordine dei dati del seed, dati mossi dagli altri test) si accettano
come rumore coperto dalle maschere.

| # | Decisione |
|---|---|
| D1 | Animazioni infinite fissate a un istante t*: **3600 ms**, scelto dal developer il 14/10 (19:49) dal foglio di anteprime (0 / 3,6 / 5,4 / 7,6 s): «una linea intera, onde a metà movimento» |
| D2 | Nessuna normalizzazione delle ore del seed, nessuna voce di backlog («rischia di rompere altri test») |
| D3 | Pannello cache accettato così com'è; il wizard su IB si isola solo se cambia stile o inquadratura di altri scatti |
| D4 | G assorbe la parte gallery di M-15 (`tx-picker-pagination.spec.ts:161` resta fuori); registrata nella sezione G |
| D5 | R prende i suoi riferimenti dopo il merge di G |
| D6 | Run complete e a 10 worker quando servono, con un avviso al coordinatore poco prima |
| D7 | Prove nel percorso indicato sopra (`LF_VISUAL_REVIEW_DIR` o `--work-dir`) |

**Definition of done finale:** instabili di **stile** ridotte al minimo spiegabile; differenze di solo contenuto
elencate come accettate.
- ✅ **Raggiunta il 15/10** con `g-final3` (passo 6): da 27 a 6 instabili su 177. Il contenuto accettato è elencato
  nell'[analisi del 15/10](evidence/analysis-final-2026-10-15.md).
- Le 4 instabili di inquadratura sono corrette al passo 7 e verificate con run mirate. Resta 1 variante su 16 di
  `assets/detail-measures`, che diventa G-11 nel backlog.
- `media/asset-picker-modal` è corretta alla radice da G-10 (H, `b4533a949`).
- Chiusura decisa dal coordinatore il 15/10 alle 16:05.

## 2. Analisi (14/10/2026)

### 2.1 G-1 — cause, verificate nel codice e nei compositi del rumore

| Classe | Meccanismo (codice) | Visto nei compositi r1 vs r2 | Scatti |
|---|---|---|---|
| A · fase delle animazioni infinite | `freezeAnimations()` mette `paused` + `animation-delay:-0.1s` **dopo** il caricamento: fase = tempo trascorso + 0,1 s; annulla i ritardi 0/4/8 s delle linee di `AnimatedBackground` (solo CSS, ignora reduced-motion) | onde e linee in fasi diverse | auth/01, 02, 03 |
| B · inquadratura | `LotsAnalysisPanel` (slide 200 ms) fa da sé uno scroll smooth quando il suo rettangolo è fermo; la spec scrolla subito e aspetta 800 ms. `scrollIntoViewIfNeeded`/`center` su blocchi che crescono mentre arrivano i dati | stesso contenuto, scroll diverso di 35–70 px (titolo del pannello tagliato in A) | fifo-lots-panel/wac ×2, positions-holdings-table, detail-classification |
| C · sonde che decidono in silenzio | preset di data `appears(btn, 500)`; Preferenze solo se `prefsTab.isVisible()` è vero nell'istante; catene `appears(…, 1–3 s)`; `isVisible({timeout})` istantanei | — (amplificano B, D, E) | positions, signals, fifo, asset-picker, classification |
| D · scatto durante il caricamento | `waitForNetworkSettled()` usa `waitForLoadState('networkidle')`: in una SPA si risolve subito dopo il primo load, quindi in `screenshot()` resta solo una pausa di 200 ms | «Cargando…» in Preferenze; scheletri KPI e Refresh disabilitato in broker/detail; «Caricamento…» nel modale import; «Cargando…» sotto la select plugin (edit-modal, +riga → altezza diversa); ciambella della condivisione non disegnata (info-tab); miniature grigie (asset-picker) | user-preferences, brokers/detail, import-modal, edit-modal, info-tab, asset-picker |
| E · grafici e numeri in corsa | ECharts anima sempre (600/800 ms, `echartsAnimationConfig.ts`); `data-chart-ready` resta true nei ridisegni; `TweenedValue` 900 ms | coda della linea diversa | fifo comparison-chart-return (16/16), detail-chart(-candlestick), signals-tree |
| F · comparsa tardiva nell'intestazione | `AssetBrowseNav` («1/16», pubblica `data-state` pending/ready/none) e nome del provider | intestazione asset più alta in B → tutto sotto spostato | detail-chart, detail-signals, (tutti gli scatti del dettaglio asset su mobile) |
| G · puntatore e hover | il puntatore resta sull'ultimo click | pannello «Misure» evidenziato in B | detail-chart-rolling-return |
| H · solo contenuto (accettato) | ore del seed (`formatDateTime(uploaded_at)`, «Aggiornato», scheduler), cache per processo (`_cache_registry`), ordine del seed (immagini del picker, colonne del confronto n-vie) | ordine diverso, orari diversi | static-grid, static-tab, brim-*, cache-panel, global-settings (testo), asset-picker (ordine), import-nway-compare |

**Difetto del prodotto trovato (da segnalare, fuori perimetro):** in `routes/(app)/assets/[id]/+page.svelte` il nome del
provider è `{getAssetProviderName(assetInfo.provider_code)}`, che legge una `Map` non reattiva. Se `assetInfo` arriva
prima del catalogo dei provider, il chip resta sul codice («yfinance») anche dopo: l'icona viene aggiornata dopo
`Promise.all`, il nome no. Sotto carico l'ordine delle due risposte cambia → l'intestazione va a capo in modo diverso.

### 2.2 G-2 — prove (log del 14/10)

- **r1:** 4 test del primo blocco (update-modal, main dashboard, growth, privacy) fermi su `auth-loading at /` per 30 s
  in `login()`. Il retry isolato (`--desktop-only -w 5`) li fa passare.
- **r2:** update-modal di nuovo su `auth-loading`; poi tre test Transactions: `navigateTo` senza `data-i18n-ready` in
  15 s (lista), `transactions-page` con `data-busy="true"` per 20 s (picker), timeout del test a 240 s dentro
  `navigateTo` (promote-merge).
- `auth-loading` resta finché finiscono `appBootstrap.load()` (impostazioni utente, onboarding, impostazioni globali in
  parallelo) e il `goto` verso la destinazione (chunk JS).
- Ipotesi in ordine (test-triage §4, poi §2 e §1): ambiente all'avvio (3 worker uvicorn per 10 browser, avvio a freddo)
  / lentezza sotto carico (un rosso che appare solo sotto carico può essere un difetto del prodotto) / forma della
  risposta (picker sulla prima riga, promote-merge sulle prime 4). Nessun verdetto: servono le richieste in volo al
  momento del fallimento.

### 2.3 G-3 — what-if

- r1 e r1-retry: «the crisis menu never highlighted "global_financial_crisis"».
- Ipotesi H1 (codice): in `SimpleSelect` `onmouseenter` evidenzia l'opzione sotto il puntatore; il puntatore resta dove
  ha cliccato «Aggiungi replay» e la tendina si apre lì sotto; `stepSelectable` non fa il giro → se l'evidenziazione cade
  sotto la voce cercata, un ciclo di soli ↓ non la raggiunge. H2: il `$effect` che riporta l'evidenziazione all'opzione
  scelta quando arriva un nuovo array `options` (`historicalReplayOptions` è `$derived`).

## 3. Passi

### Passo 0 — Preparazione ✅ (14/10/2026)
> **Note implementazione**: `npm ci` dal lock (pre-approvato, `node_modules` assente); piano creato; prove D7 lette;
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build` → exit 0 (genera anche il client
> API, ignorato da git; nessun file tracciato toccato).
> **⚠️ Fuori pista**: `tsc -p frontend/tsconfig.e2e.json` sulla baseline dava 62 errori, tutti dovuti al client API
> generato assente in un worktree nuovo (`src/lib/api/generated`): non sono difetti della gallery. Dopo la build il gate
> statico va letto filtrando i file della gallery.
> **⚠️ Fuori pista**: dai compositi è emerso che `waitForNetworkSettled()` (networkidle) in una SPA si risolve subito
> dopo il primo caricamento: è la causa comune degli scatti presi durante un caricamento (classe D). Da qui il contatore
> delle richieste `/api/` del passo 1.
> **⚠️ Fuori pista**: difetto del prodotto trovato (nome del provider non reattivo nel dettaglio asset, §2.1),
> segnalato al coordinatore il 14/10 con la correzione proposta.

### Passo 1 — Assestamento comune dello scatto e diagnostica ✅ (14/10; verificato in `g-smoke1`, `g-verify1`, `g-final`, `g-verify2`)
- Nuova fixture `frontend/e2e/fixtures/galleryShot.ts`, chiamata da `screenshot()`:
  - contatore delle richieste `/api/` in volo, installato nel `beforeEach`: lo scatto aspetta 300 ms senza richieste;
  - nessun caricamento visibile (`aria-busy`/`data-busy` true, animazioni `spin`/`pulse`/`ping` su elementi visibili);
  - font caricati, immagini visibili arrivate, grafici fermi (pixel e contatori, `data-chart-ready` true), testo fermo;
  - animazioni finite concluse; animazioni infinite fissate a t* (`GALLERY_ANIMATION_TIME_MS`, rispettando i ritardi);
  - scroll fermo e header assestato; puntatore parcheggiato e nessun tooltip; nessun toast;
  - eccezioni dichiarate per gli scatti con hover voluto (Security, delete-pair, event popover).
- Riga di impronta per scatto nel log (`🔎`): scrollY, altezza documento, header, richieste in volo, preset, hover.
- Alla fine di un test fallito: richieste `/api/` ancora in volo e le più lente (prove per G-2).
- DoD: describe toccati verdi in corsia; `tsc -p tsconfig.e2e.json` e prettier verdi.
> **Note implementazione** (14/10, test-author `g-settle-core`, statica soltanto): nuova
> `frontend/e2e/fixtures/galleryShot.ts` (705 righe: `trackApiRequests`, `apiQuiet`, `noLoaderOnScreen`,
> `finishFiniteAnimations`, `pinLoopingAnimations`/`LOOP_TIME_MS` con `GALLERY_ANIMATION_TIME_MS`, `chartsStill`
> spostata da `galleryTallShots.ts`, `textStill`, `scrollStill`, `imagesInViewComplete`, `settleShot`, `shotFingerprint`,
> `logApiOnFailure`); in `gallery.spec.ts` `screenshot(…, options)` chiama `settleShot`, `freezeAnimations` non forza più
> `animation-delay`, tracker nel `beforeEach` e `logApiOnFailure` nell'`afterEach`; `ANY_TOAST` esportata da
> `galleryReportSets.ts`. Eccezioni `keepPointer`: Security, event popover, onboarding `core-tour-step` e
> `contextual-guide` (il pannello resta pieno solo col puntatore sopra). Nessun `allowLoaders`/`allowToast`.
> `tsc` 0 errori nei file della gallery, prettier pulito.
> **Smoke run** `g-smoke1` (corsia 6153, `-w 6`, 18 test × 2 progetti, populate completo, 18:04, 7,2 min):
> **33 passati, 3 falliti**; 521 scatti, 505 impronte `🔎`, 0 animazioni finite «a mano». Snapshot e log:
> `LibreFolio_visual_review/snapshots/g-smoke1/`; failure artifacts:
> `LibreFolio_visual_review/g-workstream/2026-10-14/test-results-g-smoke1/`.
> **⚠️ Fuori pista — Security (desktop e mobile), aperto**: `apiQuiet` fallisce a 45 s su una richiesta che dal punto di
> vista della pagina non finisce mai, sotto il nome LAN `lf-e2e.lan` (desktop `GET /api/v1/brokers/import/plugins`
> 59,6 s; mobile `GET /api/v1/brokers?include_inaccessible=true` 53,7 s). Prima nessuno lo vedeva: `waitForNetworkSettled`
> non aspettava. Da capire se la richiesta resta davvero appesa (route `keepTempDataHiddenUnder` / risoluzione del nome
> in Node) o se il tracker perde l'evento di fine sotto l'alias. Non è ancora un verdetto.
> **⚠️ Fuori pista — Asset detail chart (desktop), aperto**: dopo un `settleShot` completo (impronta scritta per
> `desktop/fr/light/assets/detail-chart`, schermo 1280×865) `page.screenshot` va in timeout a 20 s («fonts loaded», poi
> fermo). Mobile verde. Da triare (§2 orologio o §4 ambiente) prima di toccare budget.
> **Rischi segnalati da test-author, da verificare**: budget dei test con molti scatti (growth P&L 24 scatti, già vicino
> ai 240 s); le misure degli schermi alti (`extendScreenToBlock`, `fitScreenToDialog`) avvengono prima dell'assestamento
> (edit-modal, broker detail) → da correggere al passo 3; con t* = 3,6 s il login mostra una sola linea (passo 4).

### Passo 2 — G-3, scelta del preset del replay ✅ (codice 14/10; DoD raggiunta il 15/10: 6 run desktop sotto carico su 6, tutte verdi)
- Messaggio d'errore con la sequenza; puntatore parcheggiato prima dell'apertura; scelta che non dipende dal verso.
- DoD: 0 rossi su 5 run desktop sotto carico.
> **Note implementazione** (14/10, test-author `g-whatif-preset`): `chooseReplayPreset` in `galleryRiskDashboard.ts`
> (+213/−14) legge il menu dal contratto del combobox (`aria-controls`, `aria-activedescendant`, id delle opzioni),
> parcheggia il puntatore prima di aprirlo, aspetta la crisi tra le opzioni (unica attesa che incolpa il catalogo), poi
> cammina con ↓/↑ verso la crisi rileggendo a ogni tasto; un fallimento cita gli ultimi stati (aperto, evidenziata i/n,
> crisi, opzione sotto il puntatore). In `g-smoke1` il test passa su desktop e mobile (1/1 ciascuno). Riproduzione
> deterministica della vecchia rossa e 5 run sotto carico: ancora da fare (ricetta nel rapporto dell'agente: hover
> dell'ultima opzione prima del vecchio ciclo).
> **Chiusura (15/10):** `what-if crisis replay` verde su desktop in 6 run su 6 sotto carico:
> - `g-smoke1` a 6 worker;
> - `g-final-r1` e `r2` a 10 worker, carico 17–35;
> - `g-verify2` a 5 worker, carico fino a 94;
> - `g-final3-r1` e `r2` a 6 worker, carico 11–16.
>
> La riproduzione deterministica della vecchia rossa non è servita: nessun rosso in nessuna run dopo la riscrittura.

### G-4 — Nome del provider non reattivo nel dettaglio asset ✅ (14/10)
> **Note implementazione**: autorizzazione del coordinatore (solo il nome reso reattivo, test rosso→verde, `front check`
> pulito). In `frontend/src/routes/(app)/assets/[id]/+page.svelte` due `$derived` sul modello di `isParametric`
> (`void $assetProvidersVersion`): `assetProviderName` (chip dell'intestazione) e `assignmentProviderName` (riga
> «Provider» del pannello classificazione, stesso difetto). Test di test-author in `frontend/e2e/assets/asset-detail.spec.ts`
> (righe 8425–8537): trattiene il catalogo dei provider con una route finché l'intestazione mostra l'asset, poi lo
> rilascia e verifica il nome del catalogo nel chip (trovato tramite l'icona del catalogo).
> - Rosso prima: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6153 --data-dir
>   /tmp/librefolio-r2-g front-asset asset-detail "the header chip trades the raw provider code"` → 1 failed,
>   `Expected: "Yahoo Finance" Received: " yfinance"`.
> - Verde dopo, stesso comando: 1 passed (3,0 s). `dev.py front check`: 0 errori, 0 warning. Prettier pulito.
> - Riga di changelog proposta (al coordinatore 1.3): «🐛 Fixed — The asset page now names the data provider (for
>   example «Yahoo Finance») instead of its internal code when the provider list arrives after the asset.»

### Passo 3 — Correzioni del percorso dei test ✅ (14/10; verificato con `g-verify1`, `g-alone1/2`, `g-verify2`)
- Preset di data e sonde → `expect` (M-15 gallery, D4); Preferenze via `?tab=preferences`.
- Inquadratura deterministica: FIFO, posizioni, classification, editor, measures, signals, rolling-return.
- Dettaglio asset: `asset-browse` non più `pending`; broker scelti per nome invece che con `.first()`.
- DoD: scatti delle classi A–G identici in 2 run filtrate dello stesso giorno.
> **Note implementazione** (14/10, test-author `g-paths-m15`, statica soltanto: `tsc` solo i 2 errori di base, prettier
> pulito). Toccati `gallery.spec.ts` e `fixtures/galleryTallShots.ts`, nessun budget cambiato. Per voce:
> 1. `selectDatePreset(page, '1y'|'max')`: aspetta il preset fino a 15 s, clicca solo se non attivo, verifica
>    `data-active`; tolto il ripiego su 2Y (dashboard e broker offrono «Tutto»).
> 2. Preferenze da `/settings?tab=preferences` + `aria-selected` + `waitForSettled(settings-layout)`.
> 3. `openGlobalSettings` aspetta il `data-busy` della scheda; sblocco e categoria Memoria come passi certi (desktop:
>    barra laterale; mobile: menu a tendina). **Effetto sullo scatto: `settings/cache-panel` su mobile mostra ora solo la
>    categoria Memoria**, come su desktop.
> 4. FIFO: scheletro sparito, grafici WAC e Gantt disegnati, scroll del pannello concluso (`scrollStill`), poi
>    `frameFromTop(panel, 8)`; il modo «Rendimento» aspetta che il contatore di render del grafico avanzi. Nel test della
>    dashboard un solo poll da 45 s distingue «pannello disegnato» / «pagina di login» (un solo nuovo tentativo) / errore.
> 5. Posizioni: inquadratura `frameFromTop(panel, 8)` per ogni vista non «alta»; le viste alte del desktop restano dall'alto
>    con lo schermo esteso. **Cambia l'inquadratura** degli scatti delle posizioni su mobile e di due viste desktop del broker.
> 6. Dettaglio asset: `GALLERY_ASSET = 'Apple Inc.'`, nuovo `openGalleryAsset` sui 12 punti d'ingresso. **Scelta:** niente
>    ricerca, perché la lista applica il testo 300 ms dopo la digitazione, fuori dal suo `data-busy`, e il clic cadeva prima o
>    dopo il filtro (frecce «1/16» sì o no: la classe F). Si clicca la scheda dell'asset nella lista intera e si verifica
>    `asset-browse` `ready` con `data-source=list`, quindi le frecce ci sono sempre. Classificazione, editor e rendimento mobile
>    inquadrati con `frameFromTop`; candele e ritorno alla linea aspettano il contatore di render.
> 7. Broker: `openBrokerCardByName` aspetta lista e pagina; modale di modifica e di import su «Charles Schwab» per nome.
> 8. Selettore di icone: catena di `expect`, Charles Schwab per nome, tolta l'attesa da 1,5 s.
> 9. M-15: `selectTransactionType`, le viste tabella (asset e FX), la ricerca degli asset, i tre test del wizard (file
>    trovato per id, avvisi gestiti dalla risposta del parse, non da una sonda), lo scatto del passo 2 con `waitForSettled`.
> 10. Picker: riga autonoma seminata «Initial EUR funding from bank», tabella filtrata per id. Promote-merge: coppia
>     seminata `promote-test` letta dall'API, selezionata con `dt-row-checkbox-tx-<id>`; se manca, fallisce invece di saltare.
> 11. `extendScreenToBlock` e `fitScreenToDialog` aspettano `apiQuiet` e `noLoaderOnScreen` prima di misurare.
> **Residui segnalati da test-author, non toccati:** il FIFO del broker analizza la prima posizione; bulk-staging e
> clone-flow lavorano sulla prima riga; i tre test del wizard analizzano in parallelo lo stesso `generic_simple.csv`.
> Candidati alla regola 4 (stato non pubblicato dal prodotto): debounce della ricerca asset fuori dal `data-busy`;
> `ViewModeToggle`, bottoni del tipo di grafico, lucchetto e categorie delle impostazioni, tre interruttori del dettaglio
> asset senza `aria-expanded`/`aria-pressed`. Restano 47 sonde: classe D (pulizie), letture dopo una barriera, B/A su FX e
> sul create-wizard fuori dalla lista M-15.
> **Verifica:** `verify_unstable.sh g-verify1 5` (corsia 6153, 5 worker, populate a ogni run, 35 test × 2 progetti, poi
> diff `--common-only` + stability), avviata alle ~20:05.
> **Risultato g-verify1** (r1 20:08–20:18, r2 20:18–20:28; carico misurato ogni minuto in
> `g-workstream/2026-10-14/logs/load_samples.log`: 20–46 su 10 core, esterno alla corsia):
> - **Test:** 66 passati e 4 falliti in ogni run. Gli stessi 2 test falliscono su entrambi i progetti in entrambe le run,
>   quindi sono difetti deterministici introdotti dal compito B:
>   - *Asset detail chart*: `switchAssetChartType` aspetta che il contatore di render salga, ma passando alle candele
>     `PriceChartFull` sostituisce l'elemento del grafico, il cui contatore riparte da zero («> 6», ricevuto 3);
>   - *broker positions tab*: `frameFromTop` pretende l'header nascosto, ma la pagina del broker finisce prima che il
>     pannello arrivi in cima (scroll limitato), quindi l'header resta visibile.
>   Correzioni chieste a test-author (`g-paths-m15`, seguito): sostituzione dell'elemento attesa invece del contatore;
>   nuovo `frameTarget` che accetta lo stato dell'header quando la pagina non può nasconderlo; tendina dell'albero aperta
>   solo su pagina ferma, con verifica dell'allineamento.
> - **58 schermate in comune:** 13 stabili, 23 rumore minimo, 16 medio, 6 instabili. Delle 27 instabili del 14/10,
>   **10 sono ora `stable`**:
>   - auth/01, auth/02;
>   - classification;
>   - edit-modal, import-modal;
>   - fifo-lots-panel e wac-chart della dashboard;
>   - user-preferences;
>   - assets/detail-chart (2 varianti).
>
>   **10 sono `low`**, con max ≤ 0,05 %:
>   - auth/03;
>   - detail-signals, detail-editor, rolling-return;
>   - sharing-modal, info-tab, brokers/detail;
>   - fifo panel, wac e comparison-return del broker.
> - **Ancora instabili, contenuto accettato** (D2, D3 e la conferma del coordinatore delle 19:00):
>   - asset-picker-modal: ordine delle immagini del seed;
>   - cache-panel: righe e numeri delle cache, +31 px di pagina;
>   - static-grid: orari del seed;
>   - import-nway-compare: colonne scambiate;
>   - global-settings: una riga di cache in più, quindi +29 px e 4 immagini di altezza diversa.
> - **Ancora instabile, stile:** assets/detail-signals-tree (mobile, fino al 9,8 %). La tendina dell'albero è spostata di
>   4 px a pagina identica (impronte uguali). `TreeSelect` calcola la posizione una sola volta all'apertura e la ricalcola
>   solo su scroll/resize.
> - **Da prima `stable` a `medium`:** dashboard/fifo-lots-table e comparison-chart (mobile, 0,48 % e 0,18 %).
>   - Nella tabella la prima colonna, fissata con CSS sticky, è sfasata di circa 2 px a scroll identico (impronte uguali).
>   - Il grafico ha fatto un render in più in r2 (3 → 4).
>   - Prima di attribuirli si rifanno da soli (regola del coordinatore).
> - **Impronte:** 882 scatti in entrambe le run.
>   - `charts` diverso in 67: render in più, non per forza pixel diversi;
>   - `focus` diverso in 16: falso allarme, il test id contiene l'UUID del segnale creato a ogni run;
>   - `dh`/`vh` diversi in 5, `y` in 1: le pagine delle cache.
> **⚠️ Fuori pista — difetto del toolkit** (`scripts/visual_review/gallery_snapshot.sh`, perimetro del coordinatore):
> `meta.json` scrive `extra_args` senza escape JSON. Il filtro con `\(admin\)` ha prodotto un JSON non valido e il `diff`
> è fallito. Ho riparato i due `meta.json` delle mie run; d'ora in poi niente barre inverse nei filtri. Da segnalare al
> coordinatore.
> **Correzioni dopo g-verify1** (test-author `g-paths-m15`, seguito; statica: `tsc` con i soli 2 errori di base, prettier
> pulito):
> - `switchAssetChartType` segna i disegni del grafico prima del clic, aspetta il disegno nuovo del tipo scelto (non
>   segnato, con `data-chart-ready="true"`) e verifica che quello sostituito non ci sia più;
> - nuovo `frameTarget` in `galleryShot.ts`, nei 5 punti del compito B; `frameFromTop` resta per Risk Lab e Dashboard Risk.
>   Aspetta che scroll, altezza della pagina, stato e riquadro dell'header e riquadro del blocco stiano fermi per 300 ms di
>   frame. Accetta lo scroll limitato a fine o a inizio pagina e lo scrive nel log (`↕️`); altrimenti verifica il margine
>   di 8 px e ritenta fino a 3 volte;
> - nuovi `settledToOpen` (API ferme, nessun caricamento, attivatore fermo) ed `expectDropdownAt` (tendina a 4 px
>   dall'attivatore, ±1 px, altrimenti rosso con i due riquadri) per l'albero dei segnali e per il filtro «Caricato da»
>   di `files/brim-report-sets`.
> **Rifatti da soli** (`rerun_alone.sh g-alone1`, 1 worker, due volte di fila, `--no-populate`; run A 20:50–20:59 con
> carico 37 → 14, run B 20:59–21:08 con carico 14 → 6):
> - **8 passati e 2 falliti in entrambe le run.** Verdi su entrambi i progetti: `Asset detail chart` (il cambio di tipo),
>   `broker positions tab` (`frameTarget`, con scroll limitato registrato `↕️`), `signals tree select open`, FIFO della
>   dashboard.
> - **I 2 rossi** sono `brim-report-sets` su entrambi i progetti: «la tendina sta 8 px sotto l'attivatore, non 4».
>   - Verdetto: assunzione del test.
>   - `DataTableColumnFilter.svelte` calcola `top = rect.bottom + 4` in uno stile inline `position: fixed`, ma la classe
>     `.filter-popover` conserva `margin-top: 0.25rem`. Il risultato è 8 px per costruzione, uguale in ogni run.
>   - Corretto il test (costante del filtro di colonna = 8, test-author), prodotto invariato.
>   - Lo spazio doppio è un dettaglio estetico, da far vedere eventualmente alla designer; non è determinismo.
> - **Diff A/B** (14 schermate, 224 immagini): 3 stabili, 8 rumore minimo, 3 medio.
>   - `assets/detail-signals-tree`: da 9,8 % a `low` (0,005 %).
>   - posizioni del broker e `assets/detail-chart(-candlestick)`: `low`.
> - **Residuo spiegato, medio:** `dashboard/fifo-lots-table` 0,29–0,50 % e `comparison-chart(-return)` 0,20 %.
>   - Le differenze stanno solo nelle colonne fissate (sticky) della tabella dei lotti: la checkbox a sinistra e, su
>     desktop, «Azioni» a destra. Una run mostra le righe separatrici bianche sotto la colonna fissata, l'altra no.
>   - Contenuto, scroll, header e puntatore sono identici (impronte uguali, `hover: app-shell`), e la differenza resta
>     anche da soli a carico basso.
>   - Classificato come resa del browser per le celle sticky di una tabella con bordi collassati, non della gallery.
>     Coperto dalle maschere.
> **Correzione della distanza del filtro di colonna** (test-author): `COLUMN_FILTER_GAP = 8` accanto a `DROPDOWN_GAP = 4`
> in `galleryShot.ts`, usato per `brim-report-sets`. Verifica da sola (`rerun_alone.sh g-alone2`, 21:12–21:15, carico 6–8):
> **2 passati in entrambe le run**. La schermata resta `medium` (≤ 0,68 %), come nella baseline (0,50 %): orari di
> caricamento e account usa e getta, cioè contenuto accettato.
> **Coordinatore (21:16):** lo spazio doppio del filtro «Caricato da» va nella lista per la designer, il prodotto non si
> tocca. Il difetto di `meta.json` lo corregge il coordinatore in `dev_release2`.

### Passo 6a — Prima misura finale (14/10) ❌ non valida per G-6 → correzioni e verifica del checkpoint ✅
- Via del coordinatore per 2 gallery complete a 10 worker, con la macchina riservata **dalle 21:25 alle 22:45** (L e R
  fermi; T in sola lettura).
- Script `final_measure.sh` (cartella di sessione, copia in `g-workstream/2026-10-14/`): attende le 21:25, poi
  `g-final-r1` e `g-final-r2` con la stessa configurazione delle baseline (nessun argomento in più: worker = 10, populate a
  ogni run); `uptime` a inizio e fine di ogni run, campioni ogni minuto in `load_samples_final.log`, `test-results` di ogni
  run salvati nello snapshot; poi `diff --emit-masks` e `stability` → `diffs/g-final__r1__vs__r2`.
> **Risultato g-final** (14/10; carico 17 → 35, Spotlight compreso; log in `g-workstream/2026-10-14/logs/`):
> - r1 21:25–21:49: 249 passati, 2 falliti, 1 saltato. r2 21:49–22:16: 248 passati, 3 falliti, 1 saltato. Diff e
>   stability alle 22:20, porta 6153 libera, macchina restituita al coordinatore alle 22:21.
> - Rossi: promote-merge, desktop e mobile, in entrambe le run («a tooltip lies over the shot»); `about plugin
>   diagnostics` desktop, solo in r2 (`tool-about-panel` in `data-state="error"`: `GET /api/v1/tools/catalog` 503 in
>   2.649 ms). Nessun rosso di auth-loading, what-if verde 4/4 (2 run × 2 progetti), Security verde.
> - Classi: 31 stabili, 89 basse, 26 medie, 30 instabili (14/10: 57, 74, 19, 27). 12 schermate stabili il 14/10 sono
>   instabili, quasi tutte di risk, what-if, lotti FIFO, misure e dettaglio asset.
> **⚠️ Fuori pista — misura non valida, fuga del prezzo live (G-6)**:
> - Nel log del backend della corsia, alle 22:02:33 (r2): `current_value for AAPL: 342.96 USD` (Yahoo) e
>   `[Intra-day price extend] asset=1 date=2026-10-14 new_close=342.96 patch_fields=['high', 'close']`, scritto nel DB
>   condiviso. È l'unica riga di questo tipo in tutte le run del 14/10 dalle 19:25.
> - Diviso per l'ora di cattura in r2 (`/tmp/libreFolio_g_leak_split.py`): gli scatti presi dopo le 22:02:33 sono
>   cambiati quasi in ogni variante (risk lab, what-if e risk della dashboard 16/16; lotti FIFO, dettaglio asset,
>   broker 8/8), quelli presi prima quasi mai. Nella correlazione cambiano solo le coppie con Apple; il grafico del
>   dettaglio finisce con un salto all'ultimo punto.
> - Meccanismo, già presente in `b631308d5`: l'`afterEach` della gallery fa `page.unrouteAll()` — toglie la guardia
>   offline — con la pagina ancora sull'ultima schermata, poi `expectFaviconImagesLoading` (un `expect.poll` sulla pagina
>   viva). Il dettaglio asset interroga `POST /assets/prices/current` per il suo asset ogni 30 s (`_fetchLivePrice`) e ogni
>   60 s dopo 5 s (`pollCurrentPriceOnce`): un tick in quel varco arriva al backend, che chiede a Yahoo e scrive la
>   candela di oggi (effetto collaterale documentato di `/prices/current`). Lo scheduler è spento
>   (`LIBREFOLIO_NO_SCHEDULER`); il service worker gestisce solo le navigazioni. Stesso varco, più breve, in
>   `cleanupGalleryAccount` (`unrouteAll` prima di `about:blank`).
> - Fuori dalla gallery lo stesso ordine c'è in `assets/asset-browse.spec.ts:149`, `assets/asset-mobile-layout.spec.ts:113`,
>   `layout/toolbar-width-sweep.spec.ts:320` (rotte tolte, poi `about:blank`), `layout/app-start-auth.spec.ts:193`
>   (rotte tolte nell'`afterEach`, nessun `about:blank`), `portfolio/dashboard-cache.spec.ts:334–563` (rotte tolte nel
>   `finally`, sulla dashboard). Voce di backlog, nessuna correzione (decisione del coordinatore).
> **Decisioni del coordinatore (14/10, sera)**:
> - Correzione nel perimetro di G, scritta da test-author: controllo favicon → `about:blank` → `unrouteAll` → registro
>   offline; lo stesso in `cleanupGalleryAccount`. Verifica: zero `current_value for` e zero `Intra-day price extend` nel
>   log della corsia.
> - Run filtrate fino a 5 worker con avviso per il rerun di `about plugin diagnostics` e per promote-merge.
> - Ordine nuovo: checkpoint di G appena pronto (correzioni verificate con run filtrate e log pulito, statica, test di
>   G-4) → integrazione in `dev_release2` → il 15/10, in una finestra riservata, la misura finale su `dev_release2` con G
>   dentro (2 gallery complete a 10 worker): misura del rumore e maschere della 56, e riferimento dello stesso giorno per
>   il cancello di R → evidenze e conclusioni in un piccolo checkpoint successivo.
> **Triage di promote-merge** (skill `test-triage`): verdetto *assunzione del test*, deterministico (4/4).
> - Il pulsante `toolbar-action-promote` sta dentro un `<Tooltip>`: qualunque clic (anche da tastiera) risale a `toggle()`
>   e fissa il tooltip, che si chiude solo con un clic sul documento fuori da sé, un secondo clic sull'attivatore, o 30 s
>   dopo che il puntatore se ne va (`PINNED_LEAVE_GRACE_MS`). Il clic dentro il modale non arriva al documento
>   (`ModalBase`: `stopPropagation` sul contenuto).
> - La baseline del 14/10 mostra «Promuovi coppia» sopra il titolo del modale in ogni variante, ed è stabile (`low`,
>   0,0004 %). Il rosso nasce dal parcheggio del puntatore del passo 1, che vieta ogni tooltip.
> - Scelta: lo scatto dichiara il tooltip fissato come parte del soggetto (presente, unico, fermo) invece di fallire; il
>   prodotto non si tocca. La sovrapposizione al titolo va alla lista della designer.
> **Triage di `about plugin diagnostics`** (skill `test-triage`): verdetto *rosso che compare solo sotto carico*.
> - Da solo (`alone3.sh` → `rerun_alone.sh g-alone3`, desktop, 1 worker, due volte, `--no-populate`; 22:31–22:33, carico
>   24 → 17, dovuto a Spotlight che indicizza gli snapshot appena scritti): **2 passati**, scatti identici 8/8, zero
>   righe di prezzo live nel log della corsia.
> - Causa del rosso in r2: `ToolRoute` (`backend/app/api/v1/tools.py:92`) limita ogni richiesta `/tools` a
>   `ingress_timeout_ms = 2000` (`schemas/tools.py:83`); il catalogo ha impiegato 2.649 ms con carico 35. Per la regola
>   del wiki «un rosso solo sotto carico è un difetto del prodotto», è un candidato difetto dei Tools, fuori dal
>   perimetro di G → backlog G-8, da instradare dal coordinatore.
> **Backlog** (sezione G, 14/10 sera): stato di G-1, G-2, G-3; G-4 e G-5 ✅ nel checkpoint; nuove G-6 (fuga, corretta
> da G), G-7 (stesso varco in 5 spec fuori dalla gallery, senza correzione), G-8 (catalogo Tools 503 sotto carico).
> **Correzioni chieste a test-author** (`g-leak-tooltip`, 14/10 sera, solo statica): ordine nuovo dell'`afterEach` e di
> `cleanupGalleryAccount`; opzione dello scatto per il tooltip fissato e test di promote-merge. Verifica preparata in
> `verify_leakfix.sh` (cartella di sessione, copia in `g-workstream/2026-10-14/`): promote-merge da solo due volte, poi
> una run filtrata a 5 worker (31 test × 2 progetti: liste e dettaglio asset, onboarding e report set con account usa e
> getta, risk lab, what-if, about, promote-merge), ciascuna con il conteggio delle righe di prezzo live nel log della
> corsia.
> **Note implementazione** (14/10, 22:55, test-author `g-leak-tooltip`, solo statica: `tsc` con i soli 2 errori di base,
> prettier pulito, `git diff --check` pulito):
> - nuovo `leaveGalleryPage(page, who)` in `galleryReportSets.ts`: `goto('about:blank')` con 10 s, poi
>   `unrouteAll({behavior: 'ignoreErrors'})`; se l'uscita fallisce le rotte restano (riga ⚠️). Lo usano l'`afterEach`
>   esterno (controllo favicon → uscita → registro offline; con due errori il registro guida e il favicon è la causa) e
>   `cleanupGalleryAccount`;
> - `ShotOptions.pinnedTooltip`: puntatore parcheggiato come sempre, esattamente un `tooltip-content`, fermo; chiave
>   `tip` nell'impronta 🔎 solo se c'è un tooltip; `parkPointer(page, {pinnedTooltip})` con il comportamento di prima
>   come predefinito;
> - promote-merge: zero tooltip prima del clic, uno dopo, scatto con `pinnedTooltip`, ancora uno dopo lo scatto.
> **Revisione (14/10, 23:00) → seguito chiesto a test-author:**
> - *Snapshot della pagina sui fallimenti.* Verificato in `node_modules/playwright/lib/index.js` (1.61):
>   `_takePageSnapshot` gira in `willCloseBrowserContext`/`didFinishTest`, dopo gli `afterEach`, quindi con il nuovo
>   ordine `error-context.md` fotograferebbe `about:blank`. Nuovo helper che allega `page.ariaSnapshot({mode: 'ai'})`
>   prima dell'uscita quando il test è fallito: `afterEach` esterno e i due interni con `cleanupGalleryAccount`.
> - *`beforeunload` del PAC planner.* `PacPlannerTool.svelte:252` annulla un `leave` con la bozza modificata (A8);
>   SvelteKit (`client.js:2421`) fa `preventDefault` sul `beforeunload`; Playwright, senza ascoltatori, chiude il dialogo
>   con «resta» → l'uscita fallirebbe su ogni test PAC. Durante il solo `goto` si accetta il `beforeunload` e si chiude
>   ogni altro dialogo.
> - *Il test di G-4 aveva lo stesso varco.* Nel suo `finally` toglieva la risposta al prezzo live con la pagina
>   dell'asset ancora aperta (warm-up del poll a 5 s): ora lascia la pagina prima di togliere le rotte.
> **Note implementazione — seguito di test-author** (14/10, 23:20, solo statica: `tsc` con i soli 2 errori di base,
> prettier e `git diff --check` puliti):
> - `attachPageSnapshotOnFailure(page, testInfo)` in `galleryReportSets.ts` allega
>   `page-snapshot-before-leave.md` (`page.ariaSnapshot({mode: 'ai'})` con l'URL), una volta per test e solo se il test
>   è fallito. Lo chiamano l'`afterEach` esterno e i due interni (Onboarding, Import report sets).
> - In `leaveGalleryPage`, solo durante il `goto`, un ascoltatore accetta il `beforeunload` e chiude ogni altro dialogo.
> **⚠️ Fuori pista — premessa sbagliata sul `beforeunload`**: verificato in `playwright-core/lib/coreBundle.js:12573`.
> Senza ascoltatori Playwright 1.61 **accetta** il `beforeunload` (`Dialog._close`), mentre la documentazione dice che
> chiude ogni dialogo. Quindi l'uscita dalle pagine PAC non sarebbe fallita. L'ascoltatore resta: fissa il comportamento
> se un giorno il codice si allineerà alla documentazione.
> **Decisioni sul seguito (23:25):**
> - *Test di G-4.* Lasciare la pagina nel `finally` costa la schermata del fallimento, perché il `finally` gira dentro il
>   test, prima della schermata. La `page` del blocco vive quanto il test, quindi le rotte muoiono con lei: il `finally`
>   tiene solo `release()`. La risposta al prezzo live sopravvive così alla pagina dell'asset.
> - *Lacuna preesistente.* `logApiOnFailure` anche nei due `afterEach` interni, prima della pulizia che lascia la
>   pagina, e reso idempotente per test.
> **Verifica del checkpoint** ✅ (14/10, 23:10–23:41, corsia 6153). Carico esterno da 32 a 94 su 10 core, dovuto alle
> 5 corsie 1.3 con le suite backend; la mia corsia era ferma tra una run e l'altra. Script `verify_leakfix.sh` e
> `rerun_alone.sh` (cartella di sessione, copie in `g-workstream/2026-10-14/`).
> - *Statica:* `tsc -p frontend/tsconfig.e2e.json` con i soli 2 errori di base; prettier pulito sugli 8 file frontend
>   toccati; `git diff --check` pulito, anche sui file nuovi; `dev.py front check` 0 errori e 0 warning (23:40); ruff e
>   black puliti su `live_price_check.py`.
> - *G-4* (`verify_leakfix.sh g4`, 23:11, carico 34): 1 passato (7,8 s), 0 righe di prezzo live.
> - *promote-merge da solo* (`g-alone4`, 1 worker, 2 run × 2 progetti, 23:12–23:15, carico 33–41): 2/2 e 2/2.
>   - `"tip":1` in tutte le 16 impronte, uguali tra le run.
>   - 12 scatti identici; 4 cambiati ≤ 0,0025 % con Δ ≤ 3 (antialiasing, `low`).
>   - `live_price_check` 0 su entrambe.
> - *g-verify2* (31 test × 2 progetti, 5 worker, populate nuovo, 23:15–23:34, carico 40 → 94): **64 passati, 2 falliti**,
>   entrambi desktop. `live_price_check` 0.
>   - Nessuna uscita fallita né errore di callback delle rotte, nessuna riga 🧹.
>   - what-if verde su desktop e mobile; `about plugin diagnostics` verde; tutti i test con account usa e getta verdi.
>   - I 2 rossi: `Asset detail classification` (`frameTarget`, 10 s, all'8ª variante) e `risk lab historical replay
>     (injected)` (`headerOutOfShot`, 3 s, aiuto preesistente). Entrambi «Timeout … exceeded while waiting on the
>     predicate»: la lettura nella pagina (`evaluate` sui frame resi, posizione dell'header) non è tornata entro la
>     scadenza. Nello stesso minuto «the browser took 13,6 s to capture the shot».
>   - Il primo ha allegato `page-snapshot-before-leave.md` senza schermata del fallimento: anche la cattura di Playwright
>     (5 s) non ce l'ha fatta.
> - *Rifatti da soli* (`g-alone5`, 1 worker, 2 volte, desktop, 23:35–23:39, carico esterno 65–85): **2/2 e 2/2**, 16
>   scatti su 16 identici, `live_price_check` 0. Verdetto (skill `test-triage`): **lentezza dell'ambiente**, renderer
>   affamato a carico 87–94. Nessuna modifica. Nelle 2 gallery complete del 14/10 (carico fino a 35) nessuno dei due è
>   fallito.
> - *G-3:* what-if verde in 4 run desktop sotto carico su 5: smoke a 6 worker, `g-final-r1` e `r2` a 10, `g-verify2` a 5
>   con carico fino a 94.
> - *Residuo proposto, non fatto:* a carico esterno estremo le attese che leggono i frame resi possono scadere.
>   `headerOutOfShot` usa la scadenza predefinita di `expect` (3 s) contro i 10 s di `frameTarget`; armonizzarla è una
>   riga. Annotata in G-2.
> **Comunicato al coordinatore (22:59):** avviso delle run filtrate; la misura su `dev_release2` va bene per la DoD a tre
> condizioni (log della corsia senza righe di prezzo live, stesse condizioni delle baseline, elenco dei commit oltre G).
> **Coordinatore (23:05 circa):** accetta le tre condizioni. La misura finale la lancia lui il 15/10 dalle 09:00, su
> `dev_release2` con G, nella sua corsia (6150, `/tmp/librefolio-r2-main`), con le altre corsie ferme, anche quelle
> della 1.3. Chiede nell'handoff la riga di comando esatta, il controllo del log (uno script nel commit) e il comando
> del diff; poi passa i percorsi degli snapshot e l'elenco dei commit oltre G. G-8 instradata a J (1.3), priorità
> bassa.
> **Note implementazione — controllo del log** (14/10, 23:15): nuovo `scripts/visual_review/live_price_check.py`, sola
> libreria standard, Python 3.11+. È aggiuntivo nella cartella del toolkit, come chiesto dal coordinatore.
> - Per ogni snapshot legge da `meta.json` inizio, durata e `data_dir`; con `meta.json` non valido (difetto di escape)
>   ripiega su una lettura con regex.
> - Conta nel log della corsia, compresi i file ruotati e gzippati, le righe del percorso del prezzo live nella finestra
>   della cattura: `current_value for`, `[Intra-day price extend]`, `[F.2 bootstrap]`, `Current-price persist`,
>   `Current-price cache HIT`, `Provider current-price failed`, `Current-price OHLC persist failed`. Sono scritte solo
>   da quel percorso (verificato con grep su `backend/app`).
> - Uscita 0 pulito, 1 cattura nulla, 2 non verificabile: nessuna riga del log nella finestra, cioè log sbagliato,
>   oppure nessuna riga DEBUG.
> - Prova sui dati veri: `g-final-r2` → 1, con le 4 righe delle 22:02:33; `g-final-r1`, `g-alone3-a/b`,
>   `g-verify1-r1` → 0; log sbagliato e cartella senza `meta.json` → 2. Circa 14 s su 224 MB. Log in
>   `g-workstream/2026-10-14/final/`.
> - ruff e black puliti, dopo C901 risolto dividendo `main` e UP017 con `datetime.UTC`.
> - README del toolkit: riga nella tabella dei file e il controllo nei flussi 1 (rumore) e 2 (riferimento e candidato).

### Passo 4 — t* (D1) ✅ (t* = 3600 ms, decisione del developer del 14/10)
- 3 anteprime del login (chiaro/scuro), scelta del developer, costante fissata.
> **Note implementazione** (14/10, 19:50): 4 run filtrate (`login page - all`, desktop, 1 worker, `--no-populate`),
> una per istante, con `GALLERY_ANIMATION_TIME_MS` = 0, 3600, 5400, 7600 → 4 × 1 passed (script
> `tstar_previews.sh` nella cartella di sessione; snapshot `g-tstar-<ms>`). Foglio per il developer:
> `LibreFolio_visual_review/g-workstream/2026-10-14/tstar-previews/tstar_login_previews.png`. Inviato al coordinatore.
> Nello smoke ogni scatto del login aveva fissato 6 animazioni infinite (`"loop":6` nella riga 🔎): 3 onde e 3 linee.
> **Decisione del developer (14/10, 19:49, riportata dal coordinatore): t\* = 3600 ms**, l'opzione consigliata. È già il
> valore predefinito di `LOOP_TIME_MS`; test-author toglie «provvisorio» dal commento e scrive la ragione. Resta da
> verificare: auth/* identici in 2 run dello stesso giorno (run di verifica del passo 3).
> Verificato in `g-verify1`: auth/01 e auth/02 `stable`, auth/03 `low` (≤ 0,05 %).

### Passo 5 — G-2 ✅ (verdetto del 15/10: saturazione a 10 worker; a 6 worker 0 rossi in 2 run complete)
- Riproduzione del primo blocco a 10 worker (con avviso), richieste in volo, verdetto per ogni rosso.
> **Note implementazione** (14/10): nelle 2 gallery complete a 10 worker (`g-final-r1/r2`, carico 17–35) nessun rosso
> del tipo originale: né «auth-loading» né modali delle transazioni. Verdetti dei rossi rimasti (skill `test-triage`):
> - promote-merge: assunzione del test, deterministico, corretto con `pinnedTooltip`;
> - `about plugin diagnostics`: lentezza sotto carico del limite di 2 s di `/tools` → G-8, instradata a J (1.3);
> - `Asset detail classification` e `risk lab historical replay (injected)`, solo in `g-verify2` a carico esterno
>   87–94: renderer affamato, verdi da soli 2/2.
> La riproduzione del primo blocco non è servita: nessun rosso di auth-loading in nessuna run a 5–10 worker del 14/10.
> **Verdetto (15/10).**
> - **10 worker.** Il coordinatore ha fermato dopo 10 minuti la prima r1 a 10 worker (`g-final2-r1`), con carico 65
>   generato dalla run stessa e 8 rossi desktop:
>   - `main dashboard`, `dashboard fifo lots panel`, `dashboard empty state`;
>   - `user preferences`, `changelog modal`, `static resources grid view`;
>   - `transaction list`, `transaction picker modal`.
>
>   Le righe ⏳ mostrano richieste in volo da 10–20 s: un chunk JS 20 s, `GET /api/v1/brokers/8` 10 s, icone statiche
>   10 s. Rifatti da soli a 2 worker, passano tutti.
> - **6 worker:** 0 rossi in 2 run complete.
> - **Causa:** `dev.py mkdocs gallery` avvia di default un worker browser per CPU più 3 worker server, e 10 CPU non
>   bastano. È la stessa firma dei rossi «ogni volta diversi» del 14/10.
> - **Esito:** il README del toolkit dice `-- --workers 6`. Il default in `dev.py` va a J (C-94, decisione del
>   coordinatore): C-94 sta già cambiando `cmd_mkdocs_gallery`, e G non tocca `dev.py`.
> - G-8 è chiusa da J (`6ce5ea180`): le rotte di lettura di `/tools` non passano più per la finestra di ingresso di 2 s.

### Passo 6 — Misura finale ✅ (15/10, `g-final3`; 4 inquadrature corrette dopo, al passo 7)
- 2 run complete nello stesso giorno, diff + stability, maschere per R; README, evidence e backlog aggiornati.
- DoD: instabili di stile al minimo spiegabile; differenze di solo contenuto elencate come accettate.
> Prima misura del 14/10 non valida (fuga del prezzo live, sopra). Rinviata al 15/10 su `dev_release2` con G dentro,
> dopo il checkpoint (decisione del coordinatore, 14/10 sera).
- **Esecuzione del 15/10** (coordinatore, dalle 09:00, corsia 6150 + `/tmp/librefolio-r2-main`, altre corsie ferme), con
  le stesse condizioni delle baseline del 14/10: nessun argomento dopo `--`, quindi 10 worker (numero di CPU) e populate
  nuovo a ogni run. Comandi nell'handoff del checkpoint, ripetuti qui:
  ```bash
  export PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc
  export LF_VISUAL_REVIEW_DIR=/Users/ea_enel/Documents/00_My/LibreFolio_subRepo/LibreFolio_visual_review
  W=$LF_VISUAL_REVIEW_DIR
  pipenv run python dev.py front build          # una volta: r1 e r2 sulla stessa build
  uptime; scripts/visual_review/gallery_snapshot.sh g-final2-r1 --port 6150 --data-dir /tmp/librefolio-r2-main; uptime
  pipenv run python -m scripts.visual_review.live_price_check $W/snapshots/g-final2-r1    # deve uscire con 0
  uptime; scripts/visual_review/gallery_snapshot.sh g-final2-r2 --port 6150 --data-dir /tmp/librefolio-r2-main; uptime
  pipenv run python -m scripts.visual_review.live_price_check $W/snapshots/g-final2-r2    # deve uscire con 0
  pipenv run python -m scripts.visual_review.gallery_tool diff $W/snapshots/g-final2-r1 $W/snapshots/g-final2-r2 \
      --out $W/diffs/g-final2__r1__vs__r2 --emit-masks
  pipenv run python -m scripts.visual_review.gallery_tool stability $W/diffs/g-final2__r1__vs__r2
  ```
- Validità: stesso `commit` e `dirty_files` 0 nei due `meta.json`; `live_price_check.py` con uscita 0 per entrambe (con 1
  la run è nulla e va rifatta, sempre nello stesso giorno). Poi analisi, maschere ed evidenze di G, nel checkpoint
  successivo.
> **⚠️ Fuori pista — 6 worker, non 10.** La prima r1 a 10 worker (`g-final2-r1`) è stata fermata dal coordinatore dopo
> 10 minuti: 8 rossi a carico 65, generato dalla run stessa (passo 5). La misura è stata rifatta con `-- --workers 6` e
> le etichette `g-final3-*`. Le baseline del 14/10 erano a 10 worker: il confronto delle classi resta valido, perché ogni
> misura confronta due run della stessa configurazione.
> **Risultato** (15/10, coordinatore; analisi di G in sola lettura, poi
> [evidence/analysis-final-2026-10-15.md](evidence/analysis-final-2026-10-15.md)).
> - **Condizioni:** X = `2338aaf79`, checkout principale, corsia 6150, altre corsie ferme, carico 11–16.
>   - r1 09:14:58, 1833 s; r2 09:45:57, 1791 s;
>   - exit 0, 2824 PNG ciascuna, stessi 32 stale;
>   - `app_version` fissata (`v0.0.0-review`, toolkit `70c84accc`);
>   - `live_price_check` 0 su entrambe. I 7 marcatori sono ancora nel codice dopo il riordino di X
>     (`services/assets/price_query.py`).
> - **Classi:** 40 stabili, 112 basse, 19 medie, 6 instabili (14/10: 57, 74, 19, 27). Delle 27 instabili del 14/10, 8
>   sono ora stabili, 16 basse, 1 media (`files/static-grid`, orari) e 2 ancora instabili, di solo contenuto.
> - **Le 6 instabili:**
>   - 2 di contenuto, già accettate: `asset-picker-modal`, `import-nway-compare`;
>   - 4 di inquadratura: `detail-measures`, `detail-measures-active`, `about-plugin-diagnostics` (mobile) e la pagina
>     dietro il modale di `scheduler-config`. Tutte da uno `scrollIntoViewIfNeeded()` il cui esito dipendeva da dove era
>     la pagina, o da un layout ancora in movimento.
> - **Le 19 medie:** contenuto (orari, account usa e getta, codici casuali, durate, ordine dei file) e due residui di resa
>   (celle sticky della tabella dei lotti, antialiasing dei canvas RSI e MACD). Ritagli A | B in
>   `g-workstream/2026-10-15/final3/crops/`.
> - **Da `stable` a `low`, 27 schermate:** 24 con Δ ≤ 15 livelli, 3 con Δ 43–70 su poche decine di pixel (spigoli di
>   icone). Raster, nessuno stile.
> - **Impronte:** su 2696 scatti il frame differisce solo nei 3 scatti mobile. `🔎` non vede lo spostamento di
>   `scheduler-config`: `ModalBase` blocca lo scroll del body (`position: fixed`, `top: -scrollY`).
> **⚠️ Fuori pista — le 4 di inquadratura erano stabili il 14/10.** Prima lo scatto partiva 200 ms dopo un
> `networkidle` che in una SPA si risolve subito, quindi coglieva sempre lo stesso stato transitorio. Con `settleShot`
> lo scatto aspetta il contenuto finale, e lo scroll fatto prima nel test corre contro il layout. È un difetto messo a
> nudo da G, non introdotto: l'inquadratura era già fragile. `scheduler-config` lo mostrava già la sera del 14/10, con
> il solo codice di G.

### Passo 7 — Correzioni dopo la misura (checkpoint 2) ✅ (15/10; 4 inquadrature su 5 stabili, 1 variante residua → G-11)
- **Inquadrature** (test-author `g-frames-c2`, solo statica):
  - measures e diagnostica su mobile con `frameTarget`; la diagnostica aspetta il pannello Tools su entrambi i viewport;
  - un nuovo helper per i due modali dello scheduler: pagina ferma, pagina in cima, poi scroll solo se serve;
  - `🔎` legge l'offset bloccato dal modale (`"lock":1`).

  Le inquadrature desktop non cambiano.
- **Modifiche leggere** (G): la docstring di `live_price_check.py` con pipenv; i percorsi spostati dal riordino di X in
  `galleryOfflineData.ts` (`api/v1/fx/providers.py`, provider in una cartella ciascuno), `galleryProviderCompare.ts` e
  `galleryReportSets.ts` (`services/assets/search.py`); README del toolkit (`-- --workers 6`, «Known gallery
  behaviour» al 15/10); evidenze (`stability-2026-10-15.md`, `analysis-final-2026-10-15.md`); README di G; backlog.
- **Verifica**, dopo la chiusura della finestra annunciata dal coordinatore, corsia 6153: i 4 test da soli ×2, più
  `live_price_check`. Fino ad allora nessuna E2E, neanche da test-author.
- DoD: le 4 inquadrature uguali nelle due run (impronte e pixel, a parte l'orario del server); statica pulita.
> **Note implementazione** (15/10, 11:20, test-author `g-frames-c2`, solo statica; rivisto da G):
> - *`detail-measures` e `-active`* (`gallery.spec.ts` ~5548–5575): su mobile `frameTarget(page, detailChart, …)` prima
>   di ogni scatto; su desktop resta il percorso di prima (`scrollIntoViewIfNeeded`, `extendScreenToBlock`).
> - *`about-plugin-diagnostics`* (~2160–2178): l'attesa del pannello Tools (`ready|degraded`, 15 s) vale per entrambi i
>   viewport. Tolti il primo scroll, che correva contro il pannello, e `waitForTimeout(300)`. Desktop come prima, mobile
>   con `frameTarget`.
> - *Modali dello scheduler* (~2015–2025, ~2048–2056): nuovo `bringIntoViewFromTop` in `galleryShot.ts` (~862–884).
>   1. `settledToOpen`: API ferme, nessun caricamento, attivatore fermo;
>   2. pagina in cima, header `visible`;
>   3. `scrollIntoViewIfNeeded`;
>   4. il frame fermo (`standsStill` con l'header), poi l'attivatore nello schermo.
>
>   `settledToOpen` riceve un quarto parametro opzionale, il nome dell'ancora nei messaggi; i due chiamanti di prima non
>   cambiano.
> - *`🔎`:* con la pagina bloccata da un modale (`body` `position: fixed`, `top` in px ≤ 0), `y` è l'offset congelato e
>   compare `"lock":1`; senza blocco la riga resta identica. Lo `0px`/`-0px` di un modale aperto in cima conta come
>   blocco (scelta di test-author, tenuta).
> - *Revisione:* l'header è `pinned` solo con guida, menu, modale aperto o focus dentro di sé (`Header.svelte`,
>   `isPinned`). Prima della cima il focus è sul pulsante cliccato nella pagina, come per gli altri chiamanti di
>   `frameTarget`, quindi l'asserzione `visible` regge.
> - *Statica, rifatta da G:* `tsc -p frontend/tsconfig.e2e.json` con gli stessi 2 errori di base; prettier pulito sui 5
>   file e2e toccati; `git diff --check` pulito, anche sui file nuovi.
> - *Da misurare nella verifica:* la `y` desktop della diagnostica deve restare 1367/1397; le 3 inquadrature mobile
>   cambiano una volta (blocco a 8 px dal bordo); dietro `scheduler-config` la pagina deve stare in cima (`"y":0,"lock":1`).
> **Coordinatore (12:22):** via alle run mirate, in parallelo alla candidata di T a 6 worker nella corsia 6155. Due
> segnalazioni per il backlog, analizzate in sola lettura durante le run:
> - *`assets/detail-signals-macd`, candidata di L, mobile it chiaro:* scattato col menu degli indicatori aperto e il MACD
>   non applicato. `selectIndicatorFromTree` non verifica l'esito del clic, e `waitForSignalCardsSettled` passa a vuoto
>   finché la card non esiste → **G-9**, correzione proposta in perimetro G, non ancora fatta.
> - *`files/static-grid`, miniatura diversa da corsia a corsia:* tutti gli avatar del seed hanno lo stesso `uploaded_at`,
>   e `list_uploads` li ordina solo per data, lasciando i pari nell'ordine della directory, cioè degli UUID casuali. È la
>   causa anche di `media/asset-picker-modal`, la prima instabile rimasta → **G-10**, prodotto, da instradare.
> - *C-94 (J):* porterà il default dei worker a circa il 60 % dei core. Non è ancora in `dev_release2` (`9d57aa4c0`); il
>   README del toolkit dice «until C-94».
> **⚠️ Fuori pista — rebuild e carico all'avvio:** la run A ha ricostruito la build debug con la versione fissata
> (`build.log` nello snapshot, toolkit di X) e ha rifatto il populate: carico 57 alle 12:29, con la candidata di T in
> parallelo.
> **Verifica** ✅ (`verify_frames_c2.sh 1`, corsia 6153, 1 worker, i 4 test × 2 progetti):
> - A `g-c2-w1-a`: populate nuovo, 12:23–12:35, carico 13 → 72 → **8 passati** (7,8 min);
> - B `g-c2-w1-b`: `--no-populate`, 12:35–12:43, carico 72 → 28 → **8 passati** (7,2 min);
> - `live_price_check` 0 su entrambe; porta 6153 libera alla fine;
> - diff A↔B (`diffs/g-c2-w1__a__vs__b`), 80 immagini, 47 identiche:
>   - `about-plugin-diagnostics` stable 0/16, da 39,6 %;
>   - `scheduler-log` stable;
>   - `scheduler-config` low 0,026 %, l'orario del server;
>   - `detail-measures-active` low, Δ ≤ 5;
>   - `detail-measures` unstable per 1 variante, mobile es/light: l'header visibile in A, nascosto in B, 5,8 %.
> - Impronte A↔B: frame identico in 80 scatti su 80, salvo quell'header. La diagnostica desktop resta 1367/1397.
> - Rispetto a `g-final3-r1` cambiano una volta le 3 inquadrature mobile e il desktop di `scheduler-config` nelle 5
>   varianti che r1 aveva non centrate. `scheduler-log` cambia solo per il contenuto: il log seminato a orari fissi del
>   giorno prima esce dalla finestra «Last 24 hours» con l'ora del giorno (D2).
> **⚠️ Fuori pista — previsione sbagliata su `scheduler-config`.** Avevo detto che dietro il modale la pagina sarebbe
> tornata in cima (`"y":0,"lock":1`). Misurato invece `"y":880,"lock":1` in tutte le 8 varianti desktop: dalla cima il
> pulsante sta sotto il primo schermo e viene centrato. È l'inquadratura della baseline del 14/10 (y≈359) e di r2; era r1
> quella diversa. Corretti l'analisi e il commento di `bringIntoViewFromTop` (solo commento, prettier pulito).
> **⚠️ Fuori pista — residuo es/light (G-11).** A scroll fermo in fondo alla pagina, l'header di
> `mobile/es/light/assets/detail-measures` è rimasto visibile in A (↕️ «header visible»). È successo solo in spagnolo, 3
> volte su 4 run contando `g-final3`. La causa sta fra i `syncScrollContext()` di `Header.svelte`; serve una run
> strumentata. Registrato G-11, non corretto ora.

### Passo 8 — G-9, scelta dell'indicatore verificata ✅ (15/10: codice `5da3c9eba`; DoD 10/10 alle 15:56, i rossi di carico rifatti da soli a 1 worker sulla revisione fusa `6f0198a08`)
- **Difetto.** Nella candidata di L lo scatto `mobile/it/light/assets/detail-signals-macd` ha il menu degli indicatori
  aperto e il MACD non applicato, in 1 variante su 16, con il test verde.
- **Prova (impronta 🔎).** Lo scatto sbagliato ha `{"y":798,"dh":1538,…,"focus":"signal-tree-option-macd"}`; le altre 15
  varianti hanno `{"y":1140,"dh":1880,…,"focus":"-"}`. Un mousedown ha raggiunto l'opzione MACD, che tiene il focus, ma
  nessun clic l'ha selezionata: manca il pannello MACD, la pagina è 342 px più corta. La voce attiva è CCI, la riga sopra.
- **Meccanismo** (codice verificato; la tempistica è la spiegazione plausibile):
  - `TreeSelect.open()` rimanda con due `setTimeout(0)` annidati l'attivazione della prima voce, il focus della ricerca e
    uno `scrollIntoView` della voce attiva;
  - sotto carico Chromium esegue l'input prima dei timer in attesa, quindi quei passi possono cadere fra mousedown e
    mouseup sul MACD;
  - la lista si muove, il mouseup cade su CCI, e il clic non arriva a nessuna delle due;
  - `selectIndicatorFromTree` non verifica l'esito, e `waitForSignalCardsSettled` passa a vuoto se la card non esiste.
- **Correzione** (test-author `g-g9-select`, brief in `files/taskG9_prompt.md`):
  - pagina ferma prima di aprire (`settledToOpen`);
  - attesa dei passi rimandati di `open()`;
  - scelta senza puntatore, con le frecce fino a `aria-activedescendant` e poi Invio, come `chooseReplayPreset`;
  - verifica del menu chiuso e della card `signal-card-*` con `data-signal-type`;
  - `waitForSignalCardsSettled` che pretende almeno una card.
- **Verifica:** `verify_g9.sh 5`, una run filtrata dei 5 test che usano l'helper (EMA, RSI, MACD, Bollinger e drawdown,
  che usa lo stesso helper), `--no-populate`. Poi `live_price_check`, nessuna opzione con il focus, frame uguali a
  `g-final3-r1`.
- DoD: 5 test × 2 progetti verdi; in ogni scatto dei segnali nessun `signal-tree-option-*` con il focus; statica pulita.
> **Note implementazione** (15/10, 13:25, test-author `g-g9-select`, solo statica, nessun Python per lo STOP; rivisto da G).
> Tutto in `frontend/e2e/gallery.spec.ts`, intorno alle righe 158–305.
> - `selectIndicatorFromTree(page, groupKey, optionValue, shot)` riceve il nome dello scatto come quarto parametro, così
>   un fallimento nomina la variante.
> - Prima di aprire: menu chiuso, puntatore parcheggiato (`parkPointer`), picker nello schermo, `settledToOpen`.
> - Apertura con ↓ sul trigger. Il focus sulla ricerca prova che il passo rimandato di `open()` è avvenuto; poi
>   `aria-activedescendant` impostato.
> - Famiglia chiusa: camminata fino alla sua riga, poi →. Poi camminata fino all'opzione con
>   `walkIndicatorTreeTo`: ↓ o ↑ secondo dove sta l'evidenza, rilettura dopo ogni tasto, al massimo il numero di righe
>   più 2 tasti. Un fallimento cita l'ultimo stato, le righe, il puntatore e gli ultimi 8 tasti.
> - Prima di Invio, `aria-activedescendant` della ricerca deve coincidere con l'`id` dell'opzione.
> - Dopo Invio: menu chiuso, e almeno una card `signal-card-*` con `data-signal-type` uguale all'opzione nel pannello.
>   I valori coincidono per i 5 chiamanti (`ema`, `rsi`, `macd`, `bollinger`, `risk-drawdown`), senza mappature.
> - `waitForSignalCardsSettled` pretende almeno una card prima di aspettare zero `signal-loading`.
> - *Statica, rifatta da G:* `tsc` e2e con i soli 2 errori di base; prettier pulito; `git diff --check` pulito.
> - *Da verificare nella run:* il modello da tastiera in Chromium (in jsdom è fissato da `TreeSelect.test.ts:256–286`), i
>   frame uguali a `g-final3-r1`, la durata entro i 240 s per test.
> - *Fuori dal perimetro, non toccato:* `SignalTreeSelect.test.ts` (righe 16–17 e 306–310) descrive ancora il vecchio
>   flusso a clic dell'helper; `TreeSelect.svelte:17–19` resta vero per lo scatto con la tendina aperta. Su richiesta del
>   coordinatore (15/10, 13:58) sono la voce **G-12** del backlog, con il proprietario da instradare.
> **Ripresa (13:36):** `cryptography` installato (`dc9a5d232`); comandi Python di nuovo permessi.
> **⚠️ Fuori pista — build scadute dopo il merge.** La base `9f3b141a8` porta sorgenti frontend più recenti della build
> delle 12:26, e 6 pagine della documentazione. Il server di test le ricostruisce all'avvio se le date dei sorgenti sono
> più recenti, entro un limite di 300 s. Ricostruite prima, sotto carico 32–44:
> - build debug con la versione fissata `v0.0.0-review`: 13:37–13:42, 4 min 37 s, rc 0;
> - sito MkDocs: 13:42–13:45, 170 s, rc 0, 3020 URL relativi risolti.
>
> Sommate all'avvio, avrebbero sforato il limite.
> **Verifica** (`verify_g9.sh 5`, corsia 6153, 5 worker, `--no-populate`, 13:46–13:56). Il carico è salito da 84 a 150,
> poi è sceso a 86: altre corsie, prima del budget comune annunciato dal coordinatore alle 13:50.
> - **5 passati, 5 falliti.** Verdi MACD desktop e mobile, EMA, RSI e Bollinger mobile.
> - **L'helper nuovo ha funzionato in tutti gli scatti presi: 63 su 63.** Ogni scatto viene dopo la scelta verificata:
>   menu chiuso, card del tipo giusto.
> - In tutti i 63 scatti `focus` è "-": nessuna opzione tiene il focus. Il frame (`y`, `dh`, `vh`, `hdr`, `focus`) è
>   identico a `g-final3-r1` in tutti i 63 scatti in comune; cambiano solo i contatori `charts` in 29.
> - Nessun messaggio d'errore viene dall'helper. `live_price_check` 0.
> - **I 5 rossi sono tutti fuori dall'helper, in passi già esistenti, per lentezza.** Verdetto con la skill
>   `test-triage`: carico.
>   - EMA e RSI desktop: `goToAssetsPage`, la lista asset ancora `data-busy` dopo 20 s, alla quarta combinazione
>     (3 scatti presi);
>   - Bollinger desktop: il clic sul tema oltre i 20 s, dopo 6 scatti;
>   - drawdown desktop: `textStill` su es/dark, poi il limite di 240 s del test, dopo 7 scatti;
>   - drawdown mobile: `page.screenshot` oltre i 60 s su it/dark (lo stallo del compositore sotto carico), dopo 4 scatti.
> - **Per chiudere la DoD (10/10 verdi)** serve rifare da soli a 1 worker i 4 test con rossi (EMA, RSI, Bollinger,
>   drawdown). Dalle 13:50 vale il budget comune con la 1.3 (al massimo 3 suite pesanti, 1 nostra), quindi lo chiedo
>   nell'handoff. Snapshot `g-g9-w5`; log, confronto con `g-final3-r1` e log delle build in
>   `g-workstream/2026-10-15/logs/`.
>
> **DoD chiusa (15/10, 15:48–15:56): 10/10.** Codice committato dal coordinatore in `5da3c9eba`; journal in `e3153b75d`.
> Il coordinatore ha poi fatto il merge di base con `dev_release2` (`8f1abf89e`: Y1, A5 e l'archivio del giro 2 della
> designer): HEAD `6f0198a08`. Del nostro perimetro il target non tocca nulla; `frontend/e2e/fixtures/instance-config.ts`
> è nuovo e la gallery non lo importa.
> - *Prima della run, sulla revisione fusa* (`files/prebuild_alone.sh` della sessione):
>   - build debug con la versione fissata `v0.0.0-review`: 15:39–15:46, 6 min 30 s, carico da 40 a 58, rc 0;
>   - sito MkDocs: 15:46–15:48, 2 min 9 s, rc 0, 3036 URL relativi risolti.
> - *Migrazione.* Il merge porta `006_registration_mode`. Con `--no-populate` il server ha portato il DB della corsia a
>   head all'avvio: dopo la run il DB è a `006_registration_mode`, con `registration_mode` = `open`. I test dei segnali
>   entrano con l'account della gallery e non ne registrano uno nuovo.
> - *Dipendenze.* `package.json` e il lock cambiano solo la versione del progetto (`1.1.0` → `0.0.0`); il `Pipfile`
>   aggiunge `cryptography`, già installato dal developer (`dc9a5d232`). Nessun `npm ci`.
> - *Run* (`files/verify_g9_alone.sh` della sessione): corsia 6153, `--no-populate`, `-w 1`, un test per invocazione,
>   carico da 42 a 91 (altre corsie attive).
>
>   | Test | Progetto | Durata | Esito | Snapshot |
>   |---|---|---|---|---|
>   | EMA | desktop | 57,8 s | ✅ | `g-g9-alone-ema` |
>   | RSI | desktop | 39,0 s | ✅ | `g-g9-alone-rsi` |
>   | Bollinger | desktop | 47,5 s | ✅ | `g-g9-alone-bollinger` |
>   | drawdown | desktop | 54,3 s | ✅ | `g-g9-alone-drawdown` |
>   | drawdown | mobile | 57,5 s | ✅ | `g-g9-alone-drawdown` |
>
>   Il drawdown su mobile non era nell'elenco del coordinatore, ma era rosso anch'esso in `g-g9-w5`: senza, la DoD si
>   fermava a 9/10. Insieme ai 5 verdi della run a 5 worker fa **10/10**.
> - *Controlli:*
>   - 40 PNG e 40 impronte 🔎 su 40 scatti;
>   - in nessuno scatto un'opzione del menu tiene il focus;
>   - frame (`y`, `dh`, `vh`, `hdr`, `focus`) identici a `g-final3-r1` in tutti e 40: 0 differenze;
>   - nessun messaggio d'errore dell'helper;
>   - `live_price_check` rc 0 sui 4 snapshot, nessun prezzo dal vivo nelle loro finestre di log.
> - *Statica sulla revisione fusa:* `tsc` e2e con i soli 2 errori di base (`onboarding-tour.spec.ts:863`,
>   `src/lib/types/files.ts:9`).
> - Porta 6153 libera alle 15:56:02. Log delle run e confronti dei frame in `g-workstream/2026-10-15/logs/`
>   (`libreFolio_g_g-g9-alone-*.log`, `g-g9-alone-*_frames_vs_final3.txt`, `libreFolio_g_build_debug_6f0198a08.log`,
>   `libreFolio_g_mkdocs_6f0198a08.log`).

## ⏸️ Pausa del 14/10

Richiesta dal developer tramite il coordinatore (circa 18:20). Stato al momento della pausa:

- **Ultimo passo completo:** G-4 (correzione + test rosso→verde + `front check`); prima, passo 0.
- **In corso:** passo 1 (assestamento comune), implementato e provato una volta (`g-smoke1`: 33/36), con due rossi aperti
  (Security sotto alias LAN, `page.screenshot` in timeout su Asset detail chart desktop). Passo 2 (G-3): codice fatto,
  verde in `g-smoke1`, prova sotto carico da fare.
- **File toccati, non committati (coerenti, statica verde):** `frontend/e2e/fixtures/galleryShot.ts` (nuovo),
  `frontend/e2e/gallery.spec.ts`, `frontend/e2e/fixtures/galleryTallShots.ts`, `frontend/e2e/fixtures/galleryReportSets.ts`,
  `frontend/e2e/fixtures/galleryRiskDashboard.ts`, `frontend/e2e/assets/asset-detail.spec.ts`,
  `frontend/src/routes/(app)/assets/[id]/+page.svelte`, `BACKLOG_POST_1.2.md` (G-4, G-5), questo piano (nuovo).
- **Corsia:** 6153 libera; DB in `/tmp/librefolio-r2-g` (può sparire con un riavvio: in quel caso togliere
  `--no-populate`). Nessun sotto-agente in esecuzione. Log copiati da `/tmp` in
  `LibreFolio_visual_review/g-workstream/2026-10-14/logs/` e negli artefatti della sessione.
- **Primo comando alla ripresa** (dopo aver letto `keepTempDataHiddenUnder` e il tracker per l'alias LAN), i due rossi da
  soli, 2 worker:

  ```bash
  cd /Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-laughing-spoon && \
  export PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
         LF_VISUAL_REVIEW_DIR=/Users/ea_enel/Documents/00_My/LibreFolio_subRepo/LibreFolio_visual_review && \
  scripts/visual_review/gallery_snapshot.sh g-smoke1b --checkout "$PWD" --port 6153 --data-dir /tmp/librefolio-r2-g \
      -- --no-populate -f "connection indicator|Asset detail chart" -w 2
  ```
- **Attese aperte:**
  - le cause dei due rossi di `g-smoke1` (sopra);
  - le anteprime di t* per il developer (passo 4: con 3,6 s il login mostra una sola linea);
  - il compito B (passo 3) da lanciare dopo i due rossi;
  - le 5 run sotto carico di G-3 e la riproduzione di G-2, a 10 worker, con avviso al coordinatore (D6).

## ▶️ Ripresa del 14/10 (19:15)

- «RIPRENDI» del coordinatore alle 19:15. HEAD `b631308d5`, 9 righe di `git status`, porta 6153 libera.
- **⚠️ Fuori pista — il Mac è stato riavviato durante la pausa** (`uptime`: 11 minuti alle 19:21): `/tmp` vuota, quindi
  DB della corsia e log in `/tmp` persi. I log erano già stati copiati. DB ripopolato alle 19:25:
  `LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r2-g pipenv run python dev.py test --data-dir /tmp/librefolio-r2-g -q db
  populate --force --clean --with-static --with-reports` → PASSED, 14 s. Carico alla ripresa: medie 14 / 61 / 59
  (Spotlight dopo il riavvio, build vite di un'altra corsia), poi in discesa.
- **⚠️ Fuori pista — gli agenti in background della sessione precedente non esistono più** dopo il riavvio: i compiti
  sono stati rilanciati da capo, con un prompt completo.

### Triage dei due rossi di `g-smoke1` (skill `test-triage`)

- **Security › connection indicator (desktop e mobile) — verdetto: assunzione (del test).**
  - Prova: alla fine del test fallito `logApiOnFailure` elenca, in volo da 59 s, `GET /api/v1/brokers/import/plugins`,
    `localhost:6153/icons/asset-types/liquidity.png` e `api.github.com/.../releases/latest`, partiti a 0,4 s l'uno
    dall'altro, mentre la pagina era già su `lf-e2e.lan`. Un'icona di `localhost` può venire solo dal documento
    precedente (la dashboard aperta da `login()`), chiuso da `signInThroughFormUnder` con una navigazione verso un altro
    sito, quindi in un altro processo.
  - Meccanismo: per le richieste di un documento chiuso così Playwright 1.61 non emette né `requestfinished` né
    `requestfailed`. Le navigazioni dello stesso origine segnalano invece le cancellazioni: nelle 🐢 compaiono voci
    `… failed`.
  - Correzione (test-author `g-shot-fixes`): il tracker dimentica le richieste del documento chiuso quando l'origine del
    frame principale cambia, e mostra l'origine delle richieste nei messaggi.
- **Assets › Asset detail chart (desktop) — verdetto: lentezza/ambiente.**
  - Prova: `settleShot` completo (riga 🔎 scritta) e `expectDrawnUnder` passato; poi `page.screenshot` è andato oltre i
    20 s dell'action timeout. In Playwright 1.61, dopo «fonts loaded», restano solo `Page.getLayoutMetrics` e
    `Page.captureScreenshot` dentro Chromium. La pagina rispondeva; lo screenshot di fallimento preso subito dopo è
    normale. Le chiamate `/api/` arrivavano a 2,5 s (macchina carica, 6 worker).
  - Frequenza: 0 su 5.625 scatti nelle run di base del 14/10, 1 su 521 nello smoke. Resta sotto osservazione.
  - Mitigazione (test-author `g-shot-fixes`): la cattura ha un budget proprio di 60 s (`captureShot`) e scrive `⚠️` nel
    log quando supera 5 s, così uno stallo resta visibile e non viene nascosto.

### Compito B lanciato (passo 3)

- Test-author `g-paths-m15`, in parallelo con `g-shot-fixes` su regioni separate. Prompt:
  `LibreFolio_visual_review/g-workstream/2026-10-14/taskB_prompt.md` (10 voci + emendamenti).
- Voce 11 aggiunta agli emendamenti: le misure degli schermi alti (`extendScreenToBlock`, `fitScreenToDialog`) vengono
  prese dopo `apiQuiet` e `noLoaderOnScreen`, per le 6 immagini di altezza variabile.

## 4. Registro

- **14/10, 23:50 — Checkpoint 1 di G (codice) pronto, FROZEN.**
  - HEAD `b631308d5` = target `dev_release2`; 9 file tracciati modificati e 3 nuovi.
  - Evidenze: «Verifica del checkpoint» sopra.
  - Commit proposti in `files/commit_g4.txt` e `files/commit_gallery.txt` della sessione.
  - Prossimo: misura finale del coordinatore il 15/10 dalle 09:00, su `dev_release2` con G (passo 6). Poi il checkpoint
    2 di G: analisi, maschere, evidenze, README della 56 e chiusura di G-1, G-2, G-3.
- **14/10, 23:55 — Merge di base di `dev_release2` (`424adb31c`) risolto, non chiuso: lo chiude il coordinatore.**
  - HEAD `0076f4269`: il checkpoint 1, committato dal coordinatore in `e23bf842c` + `0076f4269`.
  - Tre conflitti, risolti e messi in stage solo loro:
    - *backlog*: la sezione G intera, poi la sezione «T (colori)» intatta; i link di G puntano a
      `../Phase_1/10_colorSystem/G-galleryDeterminism/…`, dove il target ha spostato la cartella 56;
    - *questo piano*: spostato dal rename della cartella. Link relativi corretti; `live_price_check` lanciato con
      `pipenv run python -m scripts.visual_review.live_price_check`;
    - *README del toolkit*: la riga `W=` del target più le mie righe, con pipenv.
  - Gate sulla revisione combinata, corsia 6153 (`validate_merge.sh`, log in `g-workstream/2026-10-14/logs/merge-424adb31c/`):
    - `theme-roles.mjs --check` pulito;
    - `front-utility core-unit`: 130 file e 4245 test verdi;
    - `front check` 0/0;
    - G-4 da solo: 1 passato, 0 righe di prezzo live, sulla build ricostruita dopo `app.css`;
    - `live_price_check` come modulo pipenv: 0 su `g-alone5-b` e su `g-verify2`.
  - Residuo per il checkpoint 2: la docstring di `live_price_check.py` mostra ancora `python3 …`. È una riga, in un file
    non in conflitto, quindi non toccato ora.
- **15/10, 10:20–11:00 — Checkpoint 2 di G aperto.**
  - Misura finale del coordinatore su X = `2338aaf79` (`g-final3`). Analisi di G in sola lettura, con l'albero pulito per
    l'aggiornamento di base.
  - Il coordinatore ha portato il ramo a `6ed99c694` con un avanzamento veloce (X più un commit di journal della 1.3).
  - Decisioni del coordinatore:
    - piano approvato: test-author sulle 4 inquadrature, poi le modifiche leggere;
    - run mirate solo dopo la chiusura della finestra, che annuncia lui; fino ad allora nessuna E2E;
    - il default dei worker in `dev.py` passa a J (C-94);
    - il prossimo riferimento dello stesso giorno per R deve contenere G2.
  - test-author `g-frames-c2` lanciato (passo 7); modifiche leggere fatte da G.
- **15/10, 12:50 — Checkpoint 2 di G pronto, FROZEN.**
  - HEAD `6ed99c694`.
  - Il delta del passo 7 più evidenze, README e backlog: G-1 aggiornata; G-2, G-3, G-6 ✅; nuove G-9, G-10, G-11.
  - Verifica: `g-c2-w1-a/b`, 8 + 8 verdi, `live_price_check` 0.
  - Commit proposto in `files/commit_c2.txt` della sessione.
- **15/10, 12:53 — Checkpoint 2 committato e integrato** dal coordinatore.
  - Commit `fcf6c6686`, fuso con il target `09a536cd0` in `9f3b141a8` (uguale alla simulazione, `tsc` e2e con i soli 2
    errori di base); `dev_release2` = `9f3b141a8`. Verificato da G in sola lettura alle 12:54.
  - G-10 girata alla 1.3 (difetto del prodotto, probabilmente H, che ha `services/files`). G-11 resta in backlog.
  - G-9 rinviata alla chiusura della finestra. Durante il FROZEN, in sola lettura: diagnosi (passo 8) e brief di
    test-author preparato fuori dal repo.
- **15/10, 13:01 — Via a G-9** (coordinatore): test-author più una run filtrata dei test dei segnali, corsia 6153, base
  `9f3b141a8`. test-author `g-g9-select` lanciato alle 13:03.
- **15/10, 13:12 — STOP ai comandi Python** (coordinatore): il developer installa `cryptography` nell'ambiente Python
  condiviso, circa 10 minuti. Nessun comando Python di G era in corso. test-author continua sul codice con la statica
  Node; la run filtrata di G-9 aspetta la «ripresa».
- **15/10, 13:36 — Ripresa**; 13:46–13:56 run G-9 (passo 8). Alle 13:50 il coordinatore fissa il budget comune con la 1.3:
  al massimo 3 suite pesanti, 1 nostra. Dopo questa run, nessuna E2E, gallery o suite completa senza chiedere il posto.
- **15/10, 13:58 — G-9 pronto per il checkpoint, FROZEN.**
  - HEAD `9f3b141a8`.
  - Delta: `gallery.spec.ts`, il piano, il backlog.
  - Commit proposto in `files/commit_g9.txt` della sessione.
  - Chiesto il posto per rifare da soli i 4 test con rossi di carico.
- **15/10, 13:58 — G-9 committata dal coordinatore:** `5da3c9eba`, sopra `9f3b141a8`.
  - Entra nel target dopo la ripetizione da soli, a 1 worker, dei 4 test con rossi di carico, quando la DoD è 10/10.
  - G è in coda per il posto dopo L, che chiude L-10 in circa 25 minuti; il via lo dà il coordinatore.
  - Le due note fuori perimetro diventano **G-12** nel backlog, con il proprietario da instradare.
  - FROZEN; delta non committato: questa riga, il passo 8 e il backlog (G-9, G-12).
- **15/10, 15:36 — Slot pesante a G** (coordinatore), in tre passi.
  - Journal committato in `e3153b75d`. Merge di base con `dev_release2` (`8f1abf89e`): HEAD `6f0198a08`, padri
    `e3153b75d` e `8f1abf89e`, worktree pulito.
  - 15:39–15:48 build debug e MkDocs sulla revisione fusa.
  - 15:48–15:56 i test con rossi di carico, da soli a 1 worker: 5 verdi su 5 → **G-9 ✅, DoD 10/10** (passo 8).
  - 15:56 porta 6153 libera, comunicata al coordinatore: lo slot passa alla gallery Y2 della 1.3.
  - Handoff per l'ingresso; delta non committato: il passo 8, queste righe e il backlog (G-9 ✅). FROZEN.
- **15/10, 16:00 — G-9 in `dev_release2`** (coordinatore): `1470bd693`, merge di `c635da129` (il journal di G-9). Il
  ramo di G è stato portato al target con un avanzamento veloce: HEAD `1470bd693`, albero pulito. La base contiene la
  correzione di H per G-10 (`b4533a949`, entrata con `744f5a0ee`).
  - **G-10 ✅** nel backlog, con il commit di H.
  - **G-12 instradata alla 1.3** dal coordinatore: `SignalTreeSelect.test.ts` è del perimetro dei grafici.
  - **Cosa resta del piano di G:**
    - *Nel perimetro di G resta solo G-11*: l'header visibile in spagnolo su mobile in `assets/detail-measures`, 1
      variante su 16, peso basso. Serve una run filtrata con un osservatore delle transizioni dell'header, quindi uno
      slot pesante e test-author.
    - *G-1 e la DoD della 56:* la misura `g-final3` del 15/10 l'ha raggiunta: 6 instabili su 177 contro 27, maschere e
      `stability.json`, fallimenti sotto carico analizzati (G-2, G-3, G-8). Dopo la misura sono arrivati il checkpoint 2
      (4 inquadrature), G-9 e G-10, verificati solo con run mirate. Alla prossima coppia di run dello stesso giorno ci
      si aspetta 0 instabili di inquadratura, salvo la variante di G-11. Fra quelle di contenuto resterebbe
      `brokers/import-nway-compare`, mentre `media/asset-picker-modal` dovrebbe diventare stabile.
    - *Decisione del coordinatore e del developer:* chiudere G-1 e la 56 adesso, lasciando G-11 in backlog, oppure
      dopo la conferma con la prossima coppia di run sul target. In entrambi i casi senza gallery complete dedicate a G.
    - *Fuori da G, aperte:* G-7, il varco di G-6 negli E2E fuori dalla gallery, senza correzione per decisione del
      coordinatore; G-12, nella 1.3.
    - *Dipendenza:* in `dev.py` il default dei worker della gallery è ancora `os.cpu_count()`, cioè 10 su questa
      macchina. Finché C-94 di J non entra nel target, le gallery complete vanno lanciate con `-- --workers 6`, come
      dice il README del toolkit.
  - Delta non committato: questa riga e il backlog (G-10 ✅, G-12 instradata). FROZEN.
- **15/10, 16:05 — Piano chiuso** (decisione del coordinatore). Journal `5fb5d3767`, portato in `dev_release2` con un
  avanzamento veloce; HEAD di G `5fb5d3767`.
  - **DoD ✅** (§1) e **G-1 ✅** nel backlog, con la misura `g-final3`. G-11 resta aperta nel backlog.
  - **Prossimo compito di G, assegnato dal coordinatore: G-13**, la nuova coppia di riferimento.
    - Quando T entra in `dev_release2`: D-T20, dopo la revisione di T-8 da parte del developer.
    - Due gallery complete dello stesso giorno sul target, con `-- --workers 6`, più l'analisi di stabilità.
    - Diventano il riferimento delle ondate e della 1.3.
    - Devono confermare la previsione: 0 instabili di inquadratura e `media/asset-picker-modal` stabile.
    - Via e slot li dà il coordinatore; fino ad allora G resta in attesa, senza run.
  - Delta non committato: questa riga, l'intestazione, la DoD (§1), il README di G e il backlog (G-1 ✅, G-13).
    FROZEN.
- **Dopo la chiusura (15–16/10), fuori dal piano: le voci del backlog.**
  - Revisioni in sola lettura degli scatti nuovi di Settings:
    - E2b `settings/email`, A6b `settings/users`, B `settings/backup-ready`: doppio lancio `g-new3-a/b`, 6/6 ×2;
    - X `settings/plugins`.
  - Voci nuove: G-14 (fuso orario della gallery), G-15 (barra delle schede di Settings in spagnolo).
  - **G-16** (`tools/pac-result-exposures`): verificata, e `stable` nella coppia.
  - **G-13 ✅, 16/10.**
    - Tre gallery complete di `a2c1c39f4`: r1 con 6 rossi di carico, r2 e r3 verdi.
    - **Coppia del rumore r1↔r2**; r2↔r3 attraversa la data UTC (il planner del PAC, N26).
    - **Riferimento `g-ref13-r3`.** Candidata della notte `g-cand16a` (`72e66d1a6`), verde, con il foglio di
      confronto per il developer.
    - Evidenze: [analisi G-13](evidence/analysis-g13-2026-10-16.md), [stabilità](evidence/stability-2026-10-16.md).
    - README del toolkit: la regola della data UTC, le durate, il comportamento al 16/10.
    - Nuova G-17 (nome dell'account usa e getta).
  - **Foglio di confronto nel toolkit ✅, 16/10**, su richiesta del coordinatore (07:28): `gallery_tool sheet`.
    > **Note implementazione**: il `contact_sheet.py` della notte diventa il sottocomando `sheet` di
    > `scripts/visual_review/gallery_tool.py`.
    > - Misura per immagine i pixel con cambio massimo di canale >4, >12 e >32 livelli, maschere del rumore applicate.
    > - Ordina gli scatti per mediana >12; in cima le immagini nuove, sparite o ridimensionate.
    > - Scrive `contact_sheet.<lang>.html` e `visible.json`, che riusa finché corrisponde alla diff.
    > - `diff` registra in `summary.json` le cartelle dei due snapshot, che `sheet` legge.
    >
    > Prove: ruff e black puliti. Sulla diff della notte, valori identici allo script di sessione e fasce 91/53/20/18.
    > Su `g-new3__a__vs__b`: il ripiego sull'etichetta, `--recompute` e la cache. Nessuna run.

    > **⚠️ Fuori pista**: la mediana di `stability` è quella alta, e sbilancia gli scatti con viewport diversi.
    > `sheet` usa `statistics.median`: solo così le fasce tornano uguali a quelle della notte.

## G-18 · Guardia G3 a runtime nella galleria (16/10)

Richiesta del coordinatore alle 10:43; il developer gli aveva detto «vedi tu». Piano approvato alle 10:53. Base
`8f2824046`.

**Il problema.** Il gate G3 di `theme-roles` trova gli elementi misti solo se sono scritti così nel sorgente. Non vede
le classi composte a runtime:
- le prop di classe passate fra aree (`className`, `contentClass`…);
- le costanti importate;
- le concatenazioni.

In tema scuro un elemento misto si rompe: `app.css` esenta dal rimappaggio legacy chi porta una classe `-lf-`.

**La guardia.** A ogni scatto la galleria scandisce il DOM con le regex del gate, `ROLE_CLASS_RE` e `LEGACY_CLASS_RE`,
esportate da `theme-roles.mjs` e lette, non copiate. Gli elementi misti finiscono in `mixed_elements.json`, nella
cartella dello snapshot. **Solo segnalazione:** non fa mai fallire la run.

**Decisioni del coordinatore**
- **D1:** la guardia è attiva solo negli snapshot. `gallery_snapshot.sh` imposta `LF_GALLERY_MIXED_DIR`; CI e
  `dev.py mkdocs gallery` restano come sono.
- **D2:** il riassunto raggruppa di default per la cartella del file candidato, con `--by section` come opzione.
  - Il testid è un indizio, non una prova: la classe può arrivare dal chiamante.

**Il contratto fra la fixture e il toolkit.** Una riga JSON per scatto, in `worker-<pid>.jsonl`:
- `shot`, `t`, `ms`;
- i conteggi `elements`, `role`, `legacy`;
- `mixed`: per ogni elemento distinto `tag`, `testid`, `owner`, `selector`, `legacy`, `role`, `classes`, `onScreen`,
  `count`;
- oppure `error`.

**Passi**
1. ✅ 16/10 — La fixture `frontend/e2e/fixtures/galleryMixed.ts` e la chiamata dentro `captureShot` (`galleryShot.ts`),
   dopo lo scatto. Le scrive test-author.
   - DoD: `tsc` E2E con i soli 2 errori di base;
   - una prova Node con Chromium headless su un HTML fisso, senza server.

   > **Note implementazione** (test-author):
   > - `recordMixedElements(page, shot)` legge `LF_GALLERY_MIXED_DIR` a ogni chiamata; senza, esce subito e non
   >   importa nemmeno il gate.
   > - Le regex del gate arrivano con un `import()` dallo specificatore non letterale, una volta per worker, e solo il
   >   loro `.source` entra nella pagina.
   > - Una sola `page.evaluate` in sola lettura, al massimo 10 s, scrive una riga per scatto in `worker-<pid>.jsonl`.
   > - Mai un `expect`, mai un'eccezione: un gate non caricato o una scrittura fallita danno un ⚠️ per worker, una
   >   scansione fallita un record `error` e un ⚠️ per scatto.
   > - `galleryShot.ts`: l'import, una frase nel commento, la chiamata come ultima istruzione di `captureShot`.
   >
   > Prove:
   > - `tsc` E2E: i soli 2 errori di base (`/tmp/libreFolio_g18_tsc.log`);
   > - Prettier pulito sui due file;
   > - la sonda `/tmp/libreFolio_g18_probe.mjs`, PASS in 1 s. Copre misti con e senza testid, SVG e `foreignObject`, i
   >   doppioni (`count` 2), gli invisibili, il selettore oltre 4 livelli, `data-[…]:`. Verifica anche che DOM, scroll e
   >   focus restino uguali, e il record `error` a pagina chiusa;
   > - la sonda dei guasti (`/tmp/libreFolio_g18_probe_failures.mjs`): il gate che non si carica, la scansione bloccata
   >   a 10 s, la scrittura che fallisce.
   >
   > Prova congiunta: i JSONL della sonda, passati da `gallery_tool mixed --collect` e dal riassunto, danno 11 misti in
   > 1 di 2 scatti, 1 errore e 0 PNG senza record. Non resta nessun browser aperto.
2. ✅ 16/10 — `gallery_tool mixed`: `--collect` fonde le parti in `mixed_elements.json`; senza, stampa il riassunto per area.
   - DoD: ruff e black puliti; JSONL sintetici con due worker, un retry e un errore.

   > **Note implementazione**: sottocomando `mixed` in `scripts/visual_review/gallery_tool.py`.
   > - `--collect` tiene una riga per scatto: su un retry vince la più recente (`t`). Conta errori, righe illeggibili e
   >   record sostituiti, scrive `mixed_elements.json` con regola e commit, poi cancella le parti (`--keep-parts`).
   > - Senza parti scrive niente ed esce 0: una checkout prima di G-18 non sporca lo snapshot.
   > - Il riassunto:
   >   - raggruppa gli elementi distinti (tag, testid, owner, classi di ruolo e legacy) per cartella del file candidato;
   >     `--by section` per sezione della galleria; `--area`, `--on-screen`;
   >   - conta i PNG senza un record, che è la DoD della run;
   >   - avverte che il testid è un indizio e non una prova.
   > - File candidati: il testid, dell'elemento o del suo antenato, scritto intero fra virgolette nei sorgenti di
   >   produzione. Se non c'è, il prefisso più lungo composto (`global-settings-category-{cat.id}`, `` `tag-chip-${i}` ``).
   >   I sorgenti sono quelli del gate (`isProductionSource`): niente test, mock, Designer Lab, file generati.
   >
   > Prova: `/tmp/libreFolio_g18_toolkit_test.py`, PASS, con due worker, un retry, un errore, una riga illeggibile, un
   > PNG senza record e testid reali (`profile-save-all` intero, `global-settings-category-display` composto,
   > `app-header` come antenato). ruff e black puliti.

   > **⚠️ Fuori pista**: ruff C901 su `print_mixed` (complessità 14). L'ho divisa in intestazione, gruppi ed elemento.

   > **⚠️ Fuori pista**: la prova congiunta ha mostrato candidati sbagliati. Il testid `pair` della sonda trovava 9 file
   > solo perché `'pair'` è una stringa del codice. Ora la ricerca va a gradini:
   > - prima il testid dopo una chiave di test id (`data-testid=`, `testid=`, `testId:`), intero o composto;
   > - poi come stringa qualsiasi. Questo è un indizio debole: quegli elementi stanno in un gruppo a parte e non decidono
   >   l'area.
   >
   > La ricerca si fa una volta per testid: molti elementi hanno lo stesso antenato.
3. ✅ 16/10 — `gallery_snapshot.sh` esporta la variabile e a fine run raccoglie.
   - DoD: `bash -n`; la raccolta provata su una cartella finta.

   > **Note implementazione**:
   > - Esporta `LF_GALLERY_MIXED_DIR=<snapshot>/mixed` solo per il comando della galleria.
   > - Dopo `meta.json` chiama `gallery_tool.py mixed <snapshot> --collect`, quello accanto allo script. Se fallisce
   >   stampa un WARNING e lascia le parti: il codice d'uscita resta quello della galleria.
   > - L'intestazione, e quindi `usage`, lo dice in tre righe.
   >
   > Prova: `bash -n`; `usage`; lo stesso blocco eseguito su uno snapshot finto, sia il successo sia la cartella
   > mancante, con lo script che va avanti. La variabile passa il filtro della corsia: `cli_base` toglie solo i
   > `LIBREFOLIO_*` e i nomi documentati.
4. ✅ 16/10 — README del toolkit, questa sezione, la voce G-18 del backlog.

   > **Note implementazione**: nel README le righe della tabella (`gallery_snapshot.sh` scrive anche
   > `mixed_elements.json`; `gallery_tool.py` ha `mixed`) e una sezione 6, «Mixed elements (the runtime twin of G3)»:
   > perché, cosa c'è nel file, i tre comandi, l'avvertenza sul file candidato, `--collect` a mano. Backlog: G-18 ⏳.
5. ✅ 16/10 — Checkpoint al coordinatore (codice in `07fe58276`, base `5489d7a28`). Poi, nello slot della coda pesante:
   - la run filtrata `gallery_snapshot.sh g-mixed-probe … -- -f "Settings" --workers 4`;
   - DoD: un record per PNG, 0 errori, conteggi di ruolo e legacy maggiori di 0, il riassunto per area;
   - e quanti elementi misti ci sono oggi.

   > **Note implementazione**: partenza alle 11:35:35, quando il carico a 1 minuto è sceso a 56,2. La regola del
   > coordinatore era sotto 60, attesa al massimo 20 min; alle 11:28 il carico era 145. Fine alle 11:55:24.
   > - La cartella dati della corsia era sparita col riavvio: l'ha ripopolata il comando stesso.
   > - Il build ha preso 427 s, poi 36 test: 23 passati e 13 rossi.
   > - **DoD della guardia, tutta verde:**
   >   - 192 scatti scansionati e 192 PNG, nessuno senza record;
   >   - 0 errori di scansione, 0 righe illeggibili, 0 troncati;
   >   - ruolo e legacy maggiori di 0 in ogni scatto (mediane 66 e 115 su 374 elementi con classi);
   >   - scansione in 4 ms di mediana e 24 ms al massimo, a carico 110;
   >   - `live_price_check` pulito.
   > - **Misti oggi in Settings: 0**, su 22 scatti distinti e 192 varianti. Il riassunto per area è vuoto.
   >
   > Controllo positivo del ramo dei misti, che la run non ha attraversato: la stessa fixture nel runner vero di
   > Playwright, con la sua trasformazione TS, su una pagina fissa (`files/g18/pw/` nella sessione), PASS. Trova
   > `div`, `span`, `rect` SVG e `p` doppio; ogni selettore nomina un solo elemento.

   > **⚠️ Fuori pista — triage dei 13 rossi** (skill `test-triage`). Verdetto: **ambiente**, la macchina satura da
   > processi fuori dalla corsia: carico 110–145 su 10 CPU, le 2 corsie pesanti della 1.3 e un render Remotion.
   > - 11 test desktop sono rossi al login: l'app resta su `auth-loading` per 30 s. Sono i primi 12 della run, in tre
   >   ondate da 4 nei primi 3 minuti (il 10° è verde). Dal 13° in poi è tutto verde.
   >   - `POST /auth/login` risponde in 5,8–11,5 s, contro i 251 ms dell'unico normale.
   >   - Un test chiude con 27 richieste statiche ancora in volo: i blocchi JS, quindi l'app non parte.
   > - 2 test mobile (diagnostica plugin e tool) sono rossi con «an image on screen is still loading»: i loghi
   >   `deposit.png` e `broker.png` arrivano in 16–18 s.
   > - Le ipotesi in ordine:
   >   - la forma della risposta non c'entra: non si legge un dato;
   >   - nessun orologio fisso: si attendono lo stato d'arrivo e le immagini complete;
   >   - nessuno stato condiviso: gli stessi test sono verdi minuti dopo su mobile, e lo erano in r2 e r3;
   >   - la cascata ha una causa sola, il carico all'avvio del server.
   > - **G-18 è escluso per costruzione:** ogni test rosso cade prima della sua prima cattura, e la scansione gira solo
   >   dopo una cattura. Da quei test non c'è nessun record.
   >
   > Il coordinatore credeva la run morta col turno della sessione, caduto per la rete fra le 11:53 e le 11:57. In
   > realtà era già finita da sola alle 11:55:24, e lo script ha raccolto i record.

## Dopo G-18: lavori chiesti dal coordinatore (16/10)

- **Verifica in galleria di FE5c (X) ✅, 16/10 pomeriggio.** X ha diviso la pagina di dettaglio dell'asset (da 3.603 a
  2.757 righe), senza cambiare classi né `data-testid`.
  - Due snapshot filtrati sui 15 test che aprono il dettaglio, `-f "Asset (detail|chart settings|distribution)"`, a 6
    worker nella corsia 6153:
    - A `d69e14a6e`: la testa di X con i 27 file di FE5c riportati a dev;
    - B `668d27837`: la testa di X.
  - Kit di sessione, `files/fe5c/`: `fe5c_verify.sh` (preflight, prebuild, snap, fill, compare) e `fe5c_check.py`
    (lockcheck, select, paths, merge, verdict).
  - I rossi di carico (carico 80–166) li hanno recuperati dei fill sullo stesso SHA e nello stesso giorno: 6 su A, 5 su B.
  - Verdetto: **identiche entro il rumore.**
    - 288 immagini contro 288: 223 identiche, 40 dentro il rumore, 10 trascurabili, 13 su scatti instabili, 0
      strutturali.
    - 2 «oltre il rumore»: l'antialiasing di un'icona SVG, in 1 variante su 16.
    - Pixel oltre 12 livelli: 6 immagini, ognuna allo 0,002 % al massimo.
    - Misti a runtime: 0 e 0.

  > **⚠️ Fuori pista**:
  > - «rolling return» desktop si è ripetuto rosso nel fill di B. `test-triage`: verdetto ambiente.
  >   - Richieste ferme per 25 s.
  >   - Lo stesso percorso di codice in A e in B.
  >   - Verde da solo a carico normale.
  >   - Resta una debolezza della spec: G-19 nel backlog.
  > - Su mobile `detail-events` tre icone SVG cambiano a due stati, con lo stesso schema esatto fra r1 e r2, che sono
  >   dello stesso commit: rumore noto.
  > - Durante `snap a` ho modificato lo script che stava girando: errore di sintassi a fine run, dopo il salvataggio dei
  >   risultati. Nessun dato perso. Non si modifica uno script mentre gira.
- **Pacchetto per la designer, giro 3 ⏳.** Chiesto dal developer (testuale, via coordinatore): rifare il lavoro
  comparativo dall'output della galleria e preparare uno zip con:
  - le schermate;
  - il prima e dopo;
  - i colori residui;
  - le domande aperte;
  - ogni pagina anche in Markdown.

  Piano approvato con D1 (WebP lossless) e D2 (checkpoint del builder prima della galleria).
  - Nuovo `scripts/visual_review/build_designer_round.py`.
    - I colori residui da `color_inventory.py`, tenuti solo dove li conta il gate: codice di produzione, fuori dai
      commenti. Su HEAD dà gli stessi 185 file del baseline del gate.
    - Durante lo sviluppo, la regex dei vecchi token prendeva anche i ruoli (`text-lf-primary`): 100 file di troppo,
      corretto.
  - Prova a secco: diff `baseline-r2` → `g-cand16a`, inventario di HEAD.
  - Poi la galleria completa `designer-16b` sul target con il lotto di T, i fill dei rossi, il diff con `sheet` e il
    pacchetto `LibreFolio_review_colori_giro3_2026-10-16`.

  > **Note implementazione**: builder committato dal coordinatore in `390aa3b11` (README §3b).
  > - Prova a secco su `baseline-r2` → `g-cand16a`: zip da 133 MB in 630 s.
  > - Link controllati: 6.543, tutti presenti nel pacchetto, tranne `SKILL.md` nella palette copiata così com'è.

  > **⚠️ Fuori pista — pacchetto rimandato dal developer (16/10, 17:55)**: oggi la designer non ha tempo. Lo zip si
  > farà quando sarà disponibile, su una galleria nuova, perché nel frattempo entreranno altri lotti.
  > - La galleria `designer-16b` è finita; i fill non servono più e `package` non è stato lanciato.
  > - Il builder resta pronto: `files/g16b/g16b.sh package` della sessione rifà inventario, diff, `sheet` e zip.
- **Riferimento della sera del 16/10: lo snapshot `designer-16b`** (lasciato così com'è, su richiesta del coordinatore).
  - Commit `fa374e41d`: il target con il lotto di T, più il builder.
  - Cattura 16:53–17:52, 6 worker, carico 60–170: in parallelo W e Y della 1.3 e un vitest di B.
  - 2.862 PNG; 249 test verdi, 1 saltato (`mobile menu open`, solo mobile), **10 rossi di carico, non recuperati**:
    - desktop: dashboard empty state, data-quality banner, profile tab, transaction form modal e le varianti es/dark
      e fr/light;
    - import wizard conditional steps, image edit modal crop view, FX add pair direct routes, Asset detail signals RSI.
  - Le loro immagini mancano dallo snapshot: sono in `stale_not_regenerated.txt`, 42 file.
  - `live_price_check` pulito.
  - **G-18, primo conto su una galleria completa:** 2.862 scatti scansionati, nessuno senza record, 0 errori.
    - Per scatto, di mediana: 506 elementi con classi, 173 con un ruolo, 7 con una classe legacy.
    - **72 elementi misti, 2 distinti**, tutti e due composti a runtime: il gate statico non li vede.
      - `pac-planner-timing-segment` (`BackendTimingBar.svelte`): `border-white dark:border-gray-800` insieme a
        `bg-lf-neutral`. 4 scatti PAC, 40 varianti.
      - `lot-custody-modal > div` (`LotCustodyModal.svelte`): `border-lf-raised text-lf-primary` del modale insieme
        a `bg-white dark:bg-slate-800`, probabilmente da una prop del chiamante. 2 scatti, 32 varianti; motivo
        «attesa-1.3». In scuro lo sfondo resta il vecchio slate.
- **`settings/plugins` per la 1.3 ✅, 16/10 18:27–18:34.** Commit `ccfabfd6d`: la punta, con X-R27 e X-R28. Due run
  identiche, `g-plugins-a` e `g-plugins-b`, sullo stesso build, filtro `-f "Settings plugins"`, 2 worker, carico 23–28.
  - Esito: 2 test su 2 verdi per run, 16 PNG ciascuna, `live_price_check` pulito.
  - **a↔b: 16 immagini identiche su 16**: lo scatto è `stable`.
  - Misti a runtime (G-18): 0.
  - Le impronte sono uguali in tutte le varianti: desktop `dh` 761, schermo allungato a 745 per un blocco di 656 px;
    mobile `dh` 887.
  - Guardate a occhio es/light desktop e it/dark mobile: rese corrette, nessun trabocco della barra delle schede.
- **`settings/email` per la 1.3 ✅, 16/10 21:22–21:37.** Commit `102fa9ec1`: la punta, con E (`56759b2c8`) e Y12b.
  Due run identiche, `g-email-a` e `g-email-b`, sullo stesso build, 2 worker. Il filtro
  `-f "Settings email \(admin\) - all languages and themes"` seleziona solo `gallery.spec.ts:2069`.
  - Carico: a è partita con carico 58. b è partita a 122, dopo l'attesa massima di 5 min: giravano le corsie di W, Z,
    X e B e `mediaanalysisd` di macOS. Entrambe verdi.
  - Esito: 2 test su 2 verdi per run, 16 PNG ciascuna, `live_price_check` pulito. Misti a runtime (G-18): 0.
  - **a↔b: 15 immagini identiche su 16.**
    - L'unica cambiata, `desktop/it/light`, cambia di 1 livello in 38 pixel: l'avatar della barra laterale, riquadro
      32×32 a (24, 548).
    - È il rumore già misurato in G-13 (`low`, al massimo 0,0041 %, Δ 1), e lo stesso riquadro cambiava nella coppia
      di FE5c. Lo scatto resta `low`.
  - **G-15 chiusa.** La barra delle schede ora scorre (`affae6ffe`, 15/10) e tiene in vista la scheda attiva: «Correo» e
    «E-mail» si vedono.
    - In francese e spagnolo, nella vista admin su desktop, la barra trabocca ancora: «Perfil»/«Profil» è fuori vista e
      la seconda scheda è tagliata al bordo («…ferencias»). Nello scatto non c'è segno che la barra scorra.
    - La posizione è deterministica (a = b). In inglese e italiano la barra ci sta.
- **Nota per la prossima galleria completa, quella del giro della designer** (coordinatore, 16/10 sera; corretta il
  17/10, dopo la galleria della notte). Rispetto a `designer-16b` e `baseline-r2` sono attese differenze **di dato,
  non di colore**, che arrivano dalla 1.3. Nel confronto vanno classificate come cambi di dato, senza indagarle come
  regressioni.
  - **Prima di tutto, cosa legge la galleria.** I test della Dashboard servono `frontend/e2e/dashboard-report.json`,
    una fotografia reale con le date spostate a oggi, a ogni `POST /api/v1/portfolio/report` (`setupDashboardMockReport`
    in `gallery.spec.ts`). Così le card dei KPI, il grafico di crescita e P&L, le allocazioni, le posizioni con la vista
    Periodo e la scheda delle transazioni non risentono di un cambio del motore. Leggono invece il backend:
    - il pannello dei lotti FIFO della Dashboard, che analizza Apple;
    - il dettaglio del broker, che apre «Interactive Brokers»;
    - le posizioni e i lotti del dettaglio broker, che aprono «Coinbase»;
    - la lista dei broker.
  - **MF N54**, entrato in `8d244d1c6`: dove prima c'era «—» può comparire un MWRR, nei portafogli più giovani
    dell'intervallo. Nella galleria solo dove si legge il backend, non nelle card della Dashboard.
  - **J-24**, entrato in `31a59bdb1`: nella demo circa **−165 EUR** di realizzato e di P&L. L'aggiustamento AAPL −3 di
    IBKR esce a 160 USD contro un costo medio di circa 220.
    - Nel prodotto cambiano le card dei KPI, il grafico di crescita e P&L dal giorno −20 e la tabella Performance della
      Dashboard, il dettaglio del broker IBKR e la vista Periodo. Non cambiano NAV e lotti.
    - **Nella galleria (correzione del 17/10) cambia solo `brokers/detail`**, il dettaglio di IBKR. Gli scatti della
      Dashboard vengono dalla fixture, e la vista Periodo del dettaglio broker si fotografa su Coinbase.
    - Dettagli: piano di J, §10 «J-24».
  - **J CP-7b**, entrato in `48da9bf3c`, solo backend (coordinatore, 16/10 22:23):
    - AAPL, il lotto ADJUSTMENT (tx 60, IBKR): il prezzo di riferimento passa da 300.0201 a **299.82 USD**, «Open
      Return» da 2,342 % a **2,410 %**, e il banner `REFERENCE_PRICE_FALLBACK` mostra 299.82.
    - Test KRW Stock (Directa): sparisce il banner «No market price available … estimated at cost».
    - Il resto non cambia. Nella galleria può vedersi nei lotti di Apple, `dashboard/fifo-lots-*`, dove compare quel
      lotto.
  - **MF-A**, entrato in `536501541` (17/10): la vista Performance delle posizioni prende i valori dal motore. Nella
    galleria cambiano solo `brokers/positions-performance-table` e `-map` (Coinbase), non quelli della Dashboard.
    MF-P, nello stesso ingresso, aggiunge campi che il frontend non legge ancora.
  - **J-27**, entrato in `e221a0544`: i totali del registro leggono solo importi decimali semplici. Nella notte del
    17/10 i passi del PAC senza grafici sono identici o nel rumore, e i target hanno gli stessi numeri: nessun effetto
    visto.
  - **X, sotto-lotto 3**, entrato in `4469f37b6`: la ricerca della galleria dell'import risponde con errori, e la
    modale dell'asset precompilata mostra «Can't find it? Let us know» sotto «nessun risultato».
  - **B4 dei backup**, entrato con `df1f0d52c` (17/10): lo scatto `settings/backup-ready` cambia di testo e di forma.
    - La descrizione della card del backup è riscritta.
    - Fra il backup pronto e «Create a new backup» c'è la scelta «Kind of backup», chiaro o sicuro (`backup-mode`,
      chiaro di partenza), con le due descrizioni. L'avviso sulla riservatezza (`backup-privacy-notice`) resta, legato
      alla scelta «chiaro».
    - La fixture `galleryBackup.ts` risponde ora `encrypted: false`, quindi la nota della copia cifrata non compare.
    - La card si allunga ancora, e su mobile la card del ripristino scende più in basso (G-20).
  - **Y, lotto R17/W8/P4**, entrato in `1565b6bbb` (17/10 05:27). La Dashboard legge dal backend la variazione del
    giorno, l'effetto timing e il G/L dei gruppi. `dashboard-report.json` non ha quei campi (`pnl_change_1d` e le sue
    due percentuali, `timing_effect_percent`, `holding_groups`), e resta così finché il developer non la ricattura (sua
    decisione (c)). Il prodotto è corretto. Verificato nel codice e sulle immagini del 16 e 17/10:
    - nella card del P&L sparisce la riga del giorno sotto il totale («−253,50 € (−4,04 %)» nella fixture);
    - nella card dei rendimenti l'effetto timing mostra «—», senza la scritta «Favorable timing», e sparisce la
      variazione del giorno sul NAV («−0,50 %»);
    - si vede in `dashboard/kpi-top`, `privacy-masked`, `data-quality-banner`, `data-quality-sync-rates` e
      `security/connection-indicator`, nei due schermi, e in `dashboard/menu-open` su mobile, al bordo destro oltre il
      menu;
    - su desktop le tre card restano alte uguali (quella del patrimonio non cambia); su mobile sono una sotto l'altra, e
      quello che sta sotto le prime due sale di due righe. Gli scatti inquadrati su un grafico non cambiano;
    - il G/L dei gruppi del treemap sta solo nel tooltip, che nessuno scatto apre: nella galleria non si vede;
    - P4, le percentuali della vista Performance prese dal backend: nella fixture la percentuale accanto a ogni barra è
      identica alla vecchia (14 righe su 14), e quelle delle componenti stanno nel tooltip. Nessun cambio visibile;
    - il dettaglio del broker usa le stesse card ma legge il backend, che ha quei campi: le righe restano.
  - **J-43**, entrato in `09cb9231a` (17/10 07:07): il DB popolato dà agli utenti demo, admin compreso (IB al 40 %), una
    riga INFO nel banner della qualità dei dati, per un trasferimento fra broker posseduti a quote diverse. **Nella
    galleria non si vede**, finché il report vero dell'admin tiene il suo avviso:
    - il banner del report vero è chiuso in ogni scatto. Con un avviso, l'intestazione conta solo errori e avvisi
      («1 warning», visto il 16/10), e le righe INFO compaiono solo aprendolo (`DataQualityBanner.svelte`,
      `getHeaderText`);
    - leggono il report vero dell'admin:
      - `settings/changelog-modal` e `-search`, `support/donation-popup`: il banner è dietro la modale, chiuso;
      - `dashboard/fifo-lots-*`, `dashboard/risk-hurt`, `-diversification`, `-paid`, `-whatif` e
        `risk/whatif-simulation`: il banner sta sopra l'inquadratura;
    - i due scatti col banner aperto, `dashboard/data-quality-banner` e `-sync-rates`, leggono la fixture, con le issue
      che vi scrive il test;
    - se l'avviso dell'admin sparisse, il banner chiuso direbbe la frase delle sole note (`dataQuality.headerInfoOnly`),
      nel tono informativo.
  - **A8b**, entrato in `6e2b2c8b7` (17/10 09:10): cambiano tutti gli scatti della pagina Settings, nella struttura e
    non nel colore. Misurato nella run del punto 33 (record più sotto):
    - la barra in alto ha «Amministrazione» a destra, il gruppo di Impostazioni globali, Utenti, Backup, Email e
      Security;
    - aperto un membro, sotto c'è una seconda barra coi cinque membri (`settings-subtabs`). Su desktop gli scatti alti
      quanto la pagina crescono: `global-settings` di 25 px, `users` di 54, `backup-ready` di 182–202 (anche per B4
      dei backup). Quelli a schermo fisso (`email`, `cache-panel`, `scheduler-*`) restano di 720 px, col contenuto più
      in basso;
    - il badge su «Amministrazione» e su «Security» (`tab-badge`): oggi «1», il conto dei controlli della corsia, finché
      G-22 non lo serve da una fixture;
    - la sfumatura ai bordi (`data-fade`) non compare: a 1280 e a 430 px le barre ci stanno;
    - nella vista del membro (`plugins`, e2e_test_user) «Amministrazione» prende il posto di Impostazioni globali, senza
      seconda barra e senza badge;
    - fuori dalla run cambiano allo stesso modo, nella barra in alto: `about`, `about-plugin-diagnostics`,
      `about-tool-diagnostics`, `user-preferences`, `onboarding-replay`, `password-modal` e
      `support/social-share-modal`, tutti aperti dall'admin sulla pagina Settings.
- **`settings/backup-ready` per la 1.3 ✅, 16/10 22:54–23:11.** Commit `b89985a8b`: la punta, con B (`0cd910a7e`: B3
  ripristino, B5b, B5c). Due run identiche, `g-backup-a` e `g-backup-b`, sullo stesso build, 2 worker. Il filtro
  `-f "Settings backup ready \(admin\) - all languages and themes"` seleziona solo `gallery.spec.ts:2126`.
  - Carico e orario:
    - a è partita alle 22:54, con carico 57, dopo 4,5 min di attesa;
    - b è partita alle 23:09, con carico 55. Per G-13 doveva partire entro le 23:45, quindi entrambe sono finite prima
      di mezzanotte.
    - Il build di a ha preso 581 s (frontend e MkDocs, base nuova); b l'ha riusato.
  - Esito: 2 test su 2 verdi per run, 16 PNG ciascuna, `live_price_check` pulito. Misti a runtime (G-18): 0.
  - **a↔b: 16 immagini identiche su 16.** In G-13 lo scatto era `low` (3 varianti su 16, Δ 1).
  - **Lo scatto è cambiato con B:** sotto la card del backup c'è ora la card del ripristino (`restore-card`).
    - Desktop: il blocco passa da 488–508 a 756–796 px secondo la lingua (en da 508 a 776), e lo schermo si allunga da
      720 a 845–885 px (en 865). Le due card si vedono intere.
    - Mobile: lo schermo resta di 740 px mentre la pagina si allunga (`dh` en da 787 a 1167). Lo scatto si ferma, come
      il 15/10, al pulsante «Create a new backup»: la card del ripristino non si vede. Da decidere con G-20.
    - Desktop fr ed es: la striscia delle schede non ci sta intera. In es parte scorsa («…erfil» tagliato a sinistra);
      in fr la scheda dell'e-mail resta fuori a destra. È la domanda 33 per la designer.
  - Il backup mostrato è quello della fixture `galleryBackup.ts` (`librefolio-backup-20261015-094112.zip`, 46,0 MB):
    lo scatto non dipende dal giorno.
- **Galleria della notte del 17/10 ✅, 02:02–04:28.** Chiesta dal coordinatore (16/10 23:2x) per il mattino del
  developer: gli scatti dei lotti colore della notte, con un foglio prima/dopo. Alle 23:34 il coordinatore ha scelto
  un «prima» dello stesso giorno, invece del confronto con `designer-16b`, per isolare i lotti.
  - **Il filtro:** 78 test su 123, 126 scatti su 182, a 6 worker. L'insieme esatto è verificato su entrambi i commit.
    - Per gruppo: tabelle (T) 23 test e 44 scatti; file, media e menu (AF) 16 e 19; grafici (DV B4) 26 e 45; stati
      vuoti e banner d'import (T) 13 e 18.
    - Fuori: Auth, Onboarding, Security, Support, Settings, l'hub dei Tool, le griglie a card, le modali di creazione
      e modifica, i form delle transazioni. Lì non ci sono `DataTable` né grafici.
    - La mappa scatto → test (182 scatti, 123 test) è ricavata dalla spec, con gli aiuti condivisi risolti a mano.
  - **Kit di sessione**, `files/night/`:
    - `night.sh` (`preflight`, `run`, `fill`, `compare`, `expected`, `status`), con gli orari limite e i fill
      automatici dei rossi sullo stesso SHA e nello stesso giorno;
    - `selection.py`, `selcheck.py`, `reds.py`, `groups.py`, `summary.py`, `unpaired.py`;
    - `expected_notes.md`, le differenze attese.

    Provato prima della notte senza toccare la corsia: il confronto su una coppia piccola, e `run` con uno stub.
  - **«Prima», `778156983`** (16/10 23:19), lanciato alle 02:01 da un'automazione della sessione.
    - Base 02:02–02:47, con circa 10 min di build. 7 rossi di carico:
      - 5 desktop fra le 02:13 e le 02:16, col carico a 172 (le corsie della 1.3 sulle porte 6182, 6185 e 6189, e il
        Playwright di un altro worktree);
      - 2 mobile alle 02:44, col carico a 141.
    - Fill a 2 worker, desktop 02:47–03:00 e mobile 03:00–03:03: tutti verdi. 2.016 PNG.
  - **«Dopo», `55b53d8c1`**, al via del coordinatore delle 03:33.
    - Base 03:36–04:13 (build 247 s). 3 rossi di carico, col carico a 74–82:
      - allocazioni desktop: il click sul tema non è tornato in 20 s;
      - editor dei dati dell'asset desktop: `GET /api/v1/ai-export/catalog` ha risposto in 44,5 s;
      - passi del PAC mobile: il fuoco non è arrivato in 3 s.
    - Fill a 2 worker 04:13–04:18: tutti verdi. 2.016 PNG.
  - **Triage:** ambiente per tutti e 10 (skill `test-triage`). Per le allocazioni ho escluso un rallentamento portato
    da B4: sui test verdi in tutte e due le run, il «dopo» ha impiegato 0,89 volte il tempo del «prima» (mediana), e il
    test è passato nel fill.
  - In tutte e 6 le catture nessun prezzo live. **Misti G-18: 0 su 2.016, da tutti e due i lati.**
  - **Fra i due commit:**
    - colore: T, le tabelle (`9016f47c3`); AF, media, file e menu (`9d3607eb6`); T, `CompactCashCell` (`b58108665`);
      DV, B4 (`323c61b73`); AF, i colori disegnati (`55b53d8c1`);
    - dato: J-27, MF-A e MF-P; testo: X, sotto-lotto 3;
    - la cattura cambia di una sola riga, in `galleryBackup.ts` (B4 dei backup), che serve solo allo scatto del
      backup, fuori dal filtro.
  - **Il confronto**, 04:21–04:28, al netto delle maschere del rumore di G-13: 2.016 coppie, 205 identiche, 52 nel
    rumore, 3 trascurabili, 64 su scatti instabili, 1.692 cambiate, 0 strutturali. Per gruppo, gli scatti per
    mediana del cambio visibile (oltre 12 livelli su un canale):
    - tabelle (T), 44: 17 sopra il 10 %, 16 fra l'1 e il 10 %, 6 fra lo 0,1 e l'1 %, 5 sotto lo 0,1 %;
    - file, media e menu (AF), 19: 13 sopra il 10 %, 4 fra l'1 e il 10 %, 2 fra lo 0,1 e l'1 %;
    - grafici (DV B4), 45: 2 sopra il 10 %, 17 fra l'1 e il 10 %, 16 fra lo 0,1 e l'1 %, 10 sotto lo 0,1 %;
    - stati vuoti e banner d'import (T), 18: 4 sopra il 10 %, 3 fra l'1 e il 10 %, 11 sotto lo 0,1 %.
    - I più visibili: il caricamento dei file (37 %), gli editor dei dati di cambi e asset (29 %), le pagine e le
      anteprime dei file (23–28 %), la tabella delle posizioni (23 %).
    - Quasi identici: lo stato vuoto e i due banner della Dashboard, `kpi-top`, i passi del PAC senza grafici.
  - **Controlli a occhio:**
    - la tabella Performance della Dashboard ha gli stessi numeri al centesimo: viene dalla fixture, cambia solo il
      colore;
    - i target del PAC hanno gli stessi numeri (30/30/40 %): J-27 non si vede;
    - negli scatti dei file l'ora di «Uploaded» è quella del popolamento del DB (02:02 contro 03:36). G-13 la maschera
      già come rumore (`medium`).
  - **G-18 non vede questi lotti:** gli elementi con una classe legacy sono 22.592 da tutti e due i lati.
    - I lotti della notte lavorano su `<style>`, token di componente e colori dei grafici in JS.
    - I 4 file usciti dal baseline (m1 da 697 a 674) non compaiono negli scatti del filtro.
    - La guardia resta utile per le classi miste; non misura una migrazione fatta nel CSS.
  - **Dove guardare:** `LibreFolio_visual_review/diffs/g-night17-prima-778156983__vs__g-night17-dopo-55b53d8c1/`, con
    `contact_sheet.it.html` (il foglio), `night_summary.it.md` (il riassunto per gruppo), `night_expected_notes.md`,
    `night_expected.txt`, `night_report.md` e `index.html`.

  > **⚠️ Fuori pista**:
  > - Alle 02:13 il carico è salito a 172: la galleria non era stata annunciata come blocco alle corsie della 1.3
  >   (nota del coordinatore). Su sua richiesta la 1.3 ha fermato i passi pesanti fino alle 03:30. Il «dopo» ha avuto
  >   il blocco annunciato, 03:35–04:35.
  > - Alle 02:25 macOS ha toccato `frontend/src/.DS_Store`, e il primo fill del «prima» ha rifatto il build dello
  >   stesso commit (6 min in più). Nel «dopo» c'era già `c53012fcb` («ignore hidden and test files in build check»):
  >   i fill hanno riusato il build.
  > - La nota di MF-A citava `5c9ad06d7`, che porta solo il diario di MF: il codice è in `536501541`.
  > - Leggendo la spec ho trovato che la Dashboard della galleria viene dalla fixture: corrette la nota di J-24 e la
  >   classificazione di MF-A, qui sopra.
- **Commento di `gallery.spec.ts` corretto ✅, 17/10 mattina** (coordinatore, dopo J-43). Il commento del test
  `dashboard data-quality banner (mocked issues)` diceva «The populated DB produces no data-quality issues
  deterministically». Con J-43 non è più vero, e non lo era già prima: il 16/10 il report vero dell'admin aveva un
  avviso.
  - Ora dice come funziona lo scatto: il banner viene dalla fixture servita da `setupDashboardMockReport`, che non ha
    issue, e il test vi scrive le due che fotografa. Le issue del DB non arrivano allo scatto.
  - Allineato anche il commento del test dopo, `missing exchange rates`, che partiva dallo stesso presupposto sul DB.
  - Solo commenti: nessuna riga di codice cambia, nessuna run.
  - Note di Y R17/W8/P4 e J-43 qui sopra, nella «Nota per la prossima galleria completa».
- **Punto 33 della designer ✅, 17/10 09:24–09:46.** La barra delle schede nella vista admin di Settings, dopo A8b
  (`6e2b2c8b7`: il gruppo «Amministrazione», la seconda barra, la sfumatura ai bordi, il badge). Chiesta dal
  coordinatore alle 09:13; via alle 09:23, nello slot lasciato libero dalla spike di B. Commit `e58be67fe`.
  - **La modifica di A alla spec**, letta prima della run: `openGlobalSettings` chiama `openSettingsTab(page, 'admin')`
    (`fixtures/settings-tabs.ts`), che apre il gruppo e poi Impostazioni globali nella seconda barra; restano
    `aria-selected` e l'attesa su `data-busy`. È corretta: i quattro chiamanti entrano come TEST_ADMIN, e gli altri
    membri si aprono con `?tab=`, che la pagina instrada nel gruppo. La run la prova: 4 dei 9 test ci passano.
  - **Il filtro:** 9 test su 123, verificato sull'HEAD. La base di A (Impostazioni globali, le due modali dello
    scheduler, il pannello della cache), più i membri Email, Backup e Utenti, `profile` (la barra in alto, col gruppo
    non selezionato) e `plugins` (la vista del membro). 144 immagini per cattura.
  - **Doppio a/b sullo stesso build**, 4 worker. Regola del coordinatore sul carico: si parte sotto 50, e dopo 5 minuti
    di attesa ci si ferma invece di partire (`LOAD_STRICT`).
    - a: 09:24:27–09:37:15, carico 36. Build da capo: il frontend, poi MkDocs in 131 s. 18 test su 18 verdi, 144 PNG.
    - b: 09:37:16–09:45:42, carico 31, lo stesso build (5 s). 18 su 18 verdi, 144 PNG.
    - Nessun rosso, quindi nessun fill. Nessun prezzo live. Misti G-18: 0 e 0.
  - **a↔b: 75 immagini identiche, 69 cambiate, nessuna nelle barre.**
    - **Le barre sono ripetibili.** Nelle 88 immagini in cui si vedono, 81 sono identiche e 7 differiscono di al più 2
      livelli in 1–15 pixel (antialiasing). Nelle altre 56 l'inquadratura è sotto le barre.
    - `cache-panel`, 16 su 16, fino all'8,9 % dei pixel: stato condiviso (ipotesi 3 di `test-triage`). Il pannello
      mostra le cache in memoria del server di test. In a `portfolio_blob` e `portfolio_layer2` avevano un elemento,
      scritto da un test vicino; in b no. La tabella di b ha una riga in meno e la pagina è più corta di 31 px (1122
      contro 1153), quindi l'inquadratura, presa dal fondo, scende. → G-23.
    - `scheduler-config`, 16 su 16: l'ora del server nella modale («Server UTC: 07:34» contro «07:40»).
      `scheduler-log`, 8 su 16: gli orari del log. `global-settings`, 16 su 16: «Last updated», l'ora del popolamento
      del DB (9:24:45 contro 9:37:31). È il rumore già misurato in G-13 per questi scatti (`low`).
    - `email` 5 su 16 e `profile` 7 su 16: al più 2 livelli. `users` 1 su 16: 15 pixel del logo della barra laterale.
      Invisibili.
  - **Cosa mostrano le barre:**
    - su desktop, in francese e in spagnolo, la barra in alto ha a sinistra le quattro schede comuni (in francese
      Profil, Préférences, Plugins, À propos) e a destra «Administration»; la seconda barra mostra i cinque membri
      interi («Paramètres Globaux … Sécurité», «Configuración Global … Seguridad»);
    - nessuna barra scorre, quindi la sfumatura non compare. Su mobile le schede sono solo icone, e ci stanno;
    - la sfumatura si vedrebbe solo a larghezze intermedie, che la galleria non fotografa;
    - il badge «1» compare su «Amministrazione» in ogni scatto admin, anche su Profilo, e su «Security» nella seconda
      barra: è il conto dei controlli della corsia. → G-22, con la decisione del coordinatore (una fixture).
  - **Il foglio per la designer:** `LibreFolio_visual_review/sheets/p33-2026-10-17/index.html`.
    - In testa i fatti; poi francese e spagnolo su desktop, inglese e italiano, mobile, e in fondo la vista del membro.
    - Ogni immagine ha accanto la stessa del 16/10, con l'etichetta «giorno diverso» e senza diff di pixel (G-13). Per
      email, backup e plugins sono le coppie di G-15 della sera del 16/10.
    - Ogni immagine porta il segno a = b o a ≠ b. WebP lossless, 288 immagini, 20 MB.
  - **Kit di sessione**, `files/p33/`: `p33.sh` (preflight, pair, status), `reds.py`, `sheet.py`. In più
    `runs/filtered.sh` ora passa gli argomenti in più (`--desktop-only`), e con `LOAD_STRICT` si ferma invece di
    partire col carico alto.
