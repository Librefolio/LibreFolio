# Piano — Gallery deterministica (workstream G, cartella 56)

> Aperto il 14/10/2026 da G (sessione `G - Gallery deterministica`, worktree `e-alfy-laughing-spoon`, branch
> `e-alfy-g-gallery-deterministica`). Coordinatore: sessione `aec04834-1532-4d86-9e3f-f942e82aca89`.
> Problema e misura di partenza: [README della 56](README.md), [stabilità del 14/10](evidence/stability-2026-10-14.md).
> Programma: [piano dei colori](../plan-phase00ColorSystemThemeLab.prompt.md). Backlog: sezione «G · Gallery
> deterministica (56)» di [BACKLOG_POST_1.2.md](../../../Phase_0/BACKLOG_POST_1.2.md).
> Dal merge di `dev_release2` del 14/10 (`424adb31c`) la cartella 56 è `Phase_1/10_colorSystem/G-galleryDeterminism/` e
> il programma 55 è `Phase_1/10_colorSystem/`: «la 56» resta il nome del workstream.

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
