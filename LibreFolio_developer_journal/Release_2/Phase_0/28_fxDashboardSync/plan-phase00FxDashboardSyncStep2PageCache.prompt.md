# Piano — N / step 2: cache del frontend tra le pagine (Dashboard: Performance, lotti, Rischio)

> Perimetro nuovo chiesto dal developer il 06/10 e assegnato dal coordinator. Analisi §1–§6; decisioni E1–E7 del
> developer; **fase 1 implementata il 06/10** (via del coordinator alle 22:44) sul ramo a `593293b78`: passi in §7.
> Resta da aggiungere, al via del coordinator, la parte di `RiskLevelsPanel.svelte` (ora di A, passo 24).
>
> Segue lo step 1 ([`plan-phase00FxDashboardSync.prompt.md`](plan-phase00FxDashboardSync.prompt.md)).

| | |
|---|---|
| **Baseline** | analisi su `a7d0b37ec`; **riverificata su `ebf4752e2`** (06/10, con la famiglia Risk integrata). Le conclusioni non cambiano; righe di `riskStore` e della lista asset aggiornate |
| **Lane** | test `--test-port 6159 --data-dir /tmp/librefolio-r2-n`; server di review `127.0.0.1:6169`, avviato per le sonde e poi spento |
| **Dati** | sintetici: il DB di test della lane, utente `e2e_test_user` |
| **Sonde** | `/tmp/libreFolio_n_cache_probe.mjs`, `_scope_probe.mjs`, `_redraw_probe.mjs`, `_rows.mjs`, con il Playwright bloccato di `frontend/node_modules`. Esiti in `/tmp/libreFolio_n_cache_probe_*.json/.log` |

**L'appunto del developer** (testuale): «quando ci si muove tra le pagine, noto che i contenuti vengono ricalcolati
anche se erano appena stati aperti, ad esempio performace e rischio in dashboard. Bisognerebbe mettere su anche per
quelle pagine, come in asset e forex delle cache nel frontend che fanno si che se un pacchetto è stato appena
ricevuto, a parità di filtri e periodi, non deve rifare la chiamata ui da 0 a meno che non si clicca su aggiorna».

**Il percorso con cui lo riproduce:** «andando ad asset da performance, portfolio, go asset e poi tornando indietro
con la freccia nella ui, quella che usa backGo mi pare». In pratica: Dashboard → Posizioni → Performance → riga →
«Analizza lotti» → «Vedi Asset» → freccia ‹ del dettaglio asset (`goBack`).

---

## Riepilogo per il developer (IT)

**Le cache ci sono già e funzionano.** Andando Dashboard → Transazioni → Dashboard (e anche al Rischio) non parte
**nessuna** chiamata e la pagina è pronta in ~100 ms. Il problema è che qualcuno le svuota, o che si torna con una
chiave diversa.

**Perché sul tuo percorso si ricalcola tutto (misurato):**

1. **La pagina dell'asset svuota le cache.**
   - Appena aperta, e poi ogni 30 e 60 secondi, chiede il prezzo corrente (`POST /assets/prices/current`). Lo fa
     anche la lista asset, ogni 30 secondi.
   - Il filtro del frontend tratta quella chiamata come una modifica al portafoglio e svuota sia il report della
     Dashboard sia il Rischio.
   - Risultato: tornando con la freccia ripartono 3 richieste del report e 3 dei lotti; al tab Rischio, 2
     interrogazioni più il catalogo.
2. **Al ritorno si perdono i filtri.** La freccia ripristina tab, pannello lotti e periodo, ma **non la valuta**
   (USD torna EUR) né **il filtro broker** (torna «Tutti»). Con una chiave diversa la cache non può servire.
3. **Un difetto vero, legato a questo.**
   - Tornando sul tab Posizioni (con la freccia o col «indietro» del browser), la tabella Performance chiede i dati
     **prima di sapere quali broker possiedi**: richiesta senza `broker_ids`, cioè su tutti i broker accessibili.
   - Sui dati di test la tabella passa da 7 righe (i tuoi 2 broker) a **15 righe, con 4 broker che non possiedi**
     (viewer/editor, a importo pieno).
   - Oggi lo «salva» in parte proprio lo svuotamento della cache. Se aggiustassimo solo la cache, succederebbe a
     **ogni** ritorno: va corretto insieme.
4. **«Aggiorna» non aggiorna tutto.** Sul tab Rischio ricarica il report, ma non il Rischio, che resta quello
   in cache; nemmeno il pannello lotti si ricarica.

**Cosa propongo:**

- **Prezzo corrente**: non svuota più le cache (E1). Il prezzo intraday di oggi entra nella Dashboard con
  «Aggiorna», come chiedi.
- **Sincronizzazioni** (prezzi, FX): svuotano solo se la risposta dice che hanno scritto qualcosa (E2).
- **Modifiche reali che oggi non svuotano e dovrebbero**: la fusione di asset, «diventa viewer» e «lascia il
  broker».
- **Valuta e filtro broker della Dashboard**: restano per la sessione, come il periodo (E3).
- **«Aggiorna»**: forza davvero report, Rischio e lotti (E4).
- **Lotti**: avranno una cache come gli altri (E5).
- **Il difetto dei broker**: corretto, perché la Dashboard aspetta di conoscere i broker posseduti prima di
  chiedere Performance e lotti. Non è una decisione: va fatto.

**Cosa resta da vedere anche con la cache piena:** i numeri delle card ripartono da 0 e contano fino al valore (~1
secondo) e i grafici rifanno l'animazione d'ingresso. Non c'è rete e la CPU è trascurabile (~0,1 s), ma all'occhio
sembra un ricalcolo. L'ho solo misurato; correggerlo sarebbe un passo a parte (E7).

---

## 1. Stato attuale verificato (HEAD `a7d0b37ec`)

### 1.1 Le cache

**`portfolioStore`** (`frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts`):

- `reportCache` è una Map per sessione, senza scadenza (`:160`).
- La chiave è `utente | broker (ordinati) | dal | al | valuta` più i flag di inclusione (`:172-174`, `:244-255`).
  `fetchReport(force=false)` restituisce l'elemento in cache (`:259-262`).
- `invalidate()` svuota tutto (`:328-334`) ed è registrato sia sul reset di sessione sia sul listener di mutazione
  (`:336-337`).

**`riskStore`** (`frontend/src/lib/stores/risk/riskStore.svelte.ts`, righe su `ebf4752e2`):

- Le cache: `queryCache`, il catalogo, il catalogo degli scenari (`:23-27`) e, nuova con la famiglia Risk, la cache
  dei verdetti di idoneità `queryEligibility` (`:32-33`, `:195-…`).
- `invalidateRisk()` svuota **anche i cataloghi**, che sono statici, e la cache di idoneità (`:236-247`).
  È registrato a `:249-250`.
- Il commento a `:89-92` dice già: «opening the page persists today's price, which notifies the portfolio
  mutation listeners, which invalidate risk».
- La famiglia Risk ha limitato a tre i tentativi quando una risposta viene scartata (`RISK_DISCARD_ATTEMPTS`,
  `:61-71`), con un codice d'errore `answer_discarded` per le analisi su richiesta. Il commento ne indica la
  causa: «on Asset Global a slow request can cross more than one 30 s live-price poll, and each poll moves the
  cache generation». È proprio la chiamata di E1: la famiglia ha curato l'effetto, E1 ne toglie la causa.

**Chi svuota:** l'interceptor axios chiama `notifyPortfolioMutation(method, url)` per ogni risposta riuscita
(`frontend/src/lib/api/zodios-client.ts:121-124`). Il filtro `isPortfolioAffectingMutation`
(`frontend/src/lib/stores/portfolio/portfolioMutation.ts:19-61`) guarda solo metodo e percorso, mai la risposta.

**Backend:** la cache L2 del report è indicizzata su un'impronta di transazioni, prezzi, FX e accessi
(`backend/app/services/portfolio_service.py:2236-2410`, TTL 30 min). Una richiesta forzata dal frontend non
riceve quindi mai dati vecchi.

### 1.2 Chi la svuota senza modificare nulla, o solo per un tick intraday

| Chiamata | Chi la fa e quando | Il filtro oggi | Cosa scrive davvero |
|---|---|---|---|
| `POST /assets/prices/current` | Dettaglio asset: all'apertura e ogni 30 s (`assets/[id]/+page.svelte:1474-1475`, `_fetchLivePrice` → `livePriceService.ts:26-28`, che usa lo stesso `axiosInstance`); a +5 s e ogni 60 s (`:1979`, `:2043-2047`). Lista asset: all'apertura e ogni 30 s, per tutti gli asset elencati (`assets/+page.svelte:436`, `:447-448`, `:783`; dopo la correzione della famiglia Risk è una sola chiamata all'apertura, non più fino a 4) | **mutazione** (prefisso `/assets/prices`, `:43-46`); lo fissa anche il test `portfolioMutation.test.ts:13` | crea o estende la candela OHLC di **oggi** quando il provider risponde con la data di oggi (`backend/app/api/v1/assets.py:765-806`, `price_query.py:694-…`). La risposta non dice se il valore è cambiato |
| `POST /assets/prices/sync` | pulsanti di sync: comparazione, `AssetSyncModal`, `PageSyncModal`, banner STALE_PRICE | mutazione, sempre | scrive solo se `points_changed`/`events_changed` > 0 (`FARefreshResult`, `total_points_changed`; `backend/app/schemas/refresh.py`) |
| `POST /fx/currencies/sync` | pulsanti di sync FX, creazione di una coppia, banner N | mutazione, sempre | scrive solo se `total_points_changed` > 0 (`FXSyncBulkResponse`) |

> **Correzione al brief del coordinator**: i sync `assets/[id]:2368` e `fx/[pair]:1166` **non sono
> automatici**. Partono dai pulsanti di sync dei chip di confronto (`handleSyncAsset` ← `onsyncasset`). Nelle sonde
> l'unica chiamata automatica che svuota le cache è `/assets/prices/current`.

### 1.3 Modifiche vere che il filtro non vede

| Chiamata | Dove | Effetto mancato |
|---|---|---|
| `POST /assets/merge` con `dry_run:false` | `AssetMergeModal.svelte:167-171` | la fusione sposta le transazioni da un asset all'altro, ma Dashboard e Rischio restano in cache (`schemas/assets.py:926`, risposta `dry_run` a `:949`) |
| `PATCH /brokers/{id}/access/me` | `BrokerSharingPanel.svelte:162`, «diventa viewer» | cambia la scala delle quote, ma `PATCH /brokers/\d+` è un'altra rotta |
| `DELETE /brokers/{id}/access/me` | `BrokerSharingPanel.svelte:178`, «lascia il broker» | idem |

Restano già coperte le altre scritture:

- transazioni (commit, promote);
- broker (CRUD, `PUT /access`);
- asset (CRUD, wipe);
- prezzi ed eventi (POST/DELETE);
- provider (assegna, rimuovi, `refresh`);
- tassi FX e rotte.

### 1.4 La freccia «indietro» e che cosa ripristina

- `goBack()` (`frontend/src/lib/stores/app/navigationStore.ts:91-103`) fa `goto` dell'ultimo URL completo
  registrato per la pagina precedente.
  - Il percorso viene da `trackNavigation`, che aggiorna l'ultima voce anche dopo i `replaceState` di tab e
    pannello (`:41-73`).
  - Quindi **tab e pannello lotti tornano**: le sonde danno `/dashboard?tab=posizioni&asset=6`.
- **Il periodo torna**: è nello store globale `dateRangeStore`, in sessionStorage. Un `goto` semplice non lo
  riscrive (lo spiega anche `ContributionTable.svelte:209-213`).
- **Non tornano la valuta e il filtro broker.**
  - `targetCurrency` riparte dalla valuta predefinita (`dashboard/+page.svelte:158`).
  - `selectedBrokerIds` riparte da `[]` (`:109`).
  - Sonda «restore»: impostati USD e solo Coinbase, al ritorno si legge «EUR» e «All brokers», e il report
    riparte con EUR su tutti i broker posseduti.

### 1.5 Il difetto della chiave broker al ritorno su Posizioni (perimetro F2)

- Al montaggio diretto su `?tab=posizioni`, `PositionsPanel` chiede subito il contributo
  (`PositionsPanel.svelte:112-114` → `loadContribution`, `dashboard/+page.svelte:529-541`). A quel punto
  `allBrokers` è ancora vuoto, perché viene riempito dopo `ensureBrokersLoaded()` (`:677`).
- Quindi `activeBrokerIds` vale `undefined` (`:200-204`) e la richiesta parte **senza `broker_ids`**: il backend
  usa tutti i broker accessibili.
- Lo stesso succede a `LotsAnalysisPanel`, che riceve `brokerIds=[]` (`:889`).
- Prova (`/tmp/libreFolio_n_scope_probe.mjs`):
  - prima visita: 7 righe, broker 1 e 5 (posseduti);
  - dopo «indietro»: **15 righe**, broker 1, 2, 3, 4, 5, 6. L'utente di test è EDITOR o VIEWER su 2, 3, 4, 6 e 7,
    quindi a importo pieno.
- Oggi, se nel frattempo qualcosa ha svuotato la cache, il ricaricamento completo fa partire una seconda richiesta
  di contributo, corretta, che sostituisce la prima. Con la cache piena la prima resta. Correggere solo le
  invalidazioni renderebbe il difetto **sistematico**.
- C'è anche una seconda conseguenza: quella richiesta usa la chiave `all` invece di `1,5`, quindi non trova mai la
  cache.

### 1.6 «Aggiorna»

- Dashboard, `handleSync` (`dashboard/+page.svelte:582-586`, pulsante `sync-button`, IT «Aggiorna»): fa
  `invalidate()` + `loadAll(true)`.
  - Il report e il contributo vengono ricaricati.
  - **Il Rischio no**: `invalidateRisk()` non viene chiamato e il pannello non ha un segnale per ricaricare. Nella
    sonda F1, «Aggiorna» sul tab Rischio fa 1 richiesta del report e 0 interrogazioni rischio.
  - **Il pannello lotti no**: non ha cache e i suoi props non cambiano.
- Dettaglio broker, `handleRefresh` (`brokers/[id]/+page.svelte:396-397`): stesso schema, stesso buco sul rischio.

### 1.7 Lotti senza cache

`LotsAnalysisPanel` richiama `POST /portfolio/lots/analysis` a ogni montaggio e a ogni cambio di `brokerIds`
(`LotsAnalysisPanel.svelte:158-292`). Al ritorno la sonda ne conta 3.

---

## 2. Prove di rete (corsia N, review server 6169, carico 4–12)

**Giro principale** (`/tmp/libreFolio_n_cache_probe_a6.json`). La sonda risponde nel browser a
`/assets/prices/current`, così nessun provider viene interrogato; l'interceptor gira come con una risposta vera.

| Fase | `/portfolio/report` | `/risk/query` (+ catalogo) | `/lots/analysis` | Chiamate che il filtro tratta come mutazione |
|---|---|---|---|---|
| prima Dashboard | 1 | – | – | – |
| Posizioni → Performance | 1 (contributo, broker [5,1]) | – | – | – |
| «Analizza lotti» | 0 | – | 2 ([5,1]) | – |
| dettaglio asset 6, 5 s | 0 | – | – | **2× `POST /assets/prices/current`** |
| **freccia ‹ → Dashboard** | **3** (contributo **senza broker**, principale [5,1], contributo [5,1]); 1,28 s | – | **3** (senza broker, [5,1], [5,1]) | – |
| tab Rischio | 0 | **2 + 1** | – | – |
| Panoramica → Rischio (nella pagina) | 0 | 0 | – | – |
| Transazioni → Dashboard (controllo) | **0**; pronta in 118 ms | – | – | – |
| Rischio dopo il controllo | – | **0**; 103 ms | – | – |
| «Aggiorna» sul tab Rischio | 1 | **0** | – | – |
| Posizioni + lotti → Transazioni → «indietro» del browser (nessuna invalidazione) | **1** (contributo **senza broker**) | – | 3 | – |
| lista asset 5 s → Dashboard | 1 | – | – | 2× `/prices/current` |
| lista FX 5 s → Dashboard | 0 | – | – | – |

- **Giro «restore»** (`…_restore.json`): la Dashboard era impostata su USD e solo Coinbase [5]. Dopo la freccia, i
  report ripartono in EUR, con `broker_ids` assenti e poi [5,1]; sullo schermo «EUR» e «All brokers».
- **Primo giro** (`…_stay5.json`): asset 6 è assegnato a `yfinance` nel DB di test, quindi in questo giro
  `/prices/current` ha raggiunto davvero Yahoo (2 chiamate: un ticker, nessun dato privato). Lo schema è lo
  stesso: 2 report al ritorno. Dal secondo giro rispondo nel browser.

---

## 3. Regola proposta

### 3.1 Il filtro guarda anche la risposta

- `notifyPortfolioMutation(method, url, data)`, con l'interceptor che passa `response.data`.
- Il filtro diventa una funzione pura di metodo, percorso e risposta: si testa a unità.

| Chiamata | Regola nuova |
|---|---|
| `POST /assets/prices/current` | **resta un trigger** (E1 deciso, §3.1-ter): marca i dati come vecchi, e la pagina li mostra mentre li rinnova in background |
| `POST /assets/prices/sync` | solo se un risultato ha `points_changed > 0` o `events_changed > 0` |
| `POST /fx/currencies/sync` | solo se `total_points_changed > 0` |
| `POST /assets/merge` | solo se la risposta ha `dry_run: false` |
| `PATCH`/`DELETE /brokers/{id}/access/me` | sempre (oggi mancano) |
| Tutte le altre scritture di oggi | invariato |
| Letture via POST (`/prices/query`, `/events/query`, `/provider/probe`, `/fx/currencies/convert`, `/transactions/validate`, `/portfolio/*`) | invariato: mai |

### 3.1-quater Principio generale del developer (06/10 22:21): «mostra il vecchio, aggiorna in background» ovunque

> «questa logica e1 rendiamola un pricipio generale, anche per gli asset e le forex, file, tutto, se la cache si
> invalida, mandiamo la richiesta asincrona di aggiornamento ma non la scartiamo immediatamete.»

**La regola, per tutto il frontend:**

- Invalidare una cache **non cancella** i dati: li segna come vecchi.
- Chi li legge li mostra subito e fa partire il rinnovo in background.
- Quando arriva la risposta, la pagina si aggiorna con le animazioni che esistono già.
- Il segnaposto di caricamento («Caricamento…», scheletri) compare **solo quando non c'è ancora niente da
  mostrare**. È il modello che la lista broker usa già (`brokers/+page.svelte:380`,
  `{#if loading && brokers.length === 0 …}`).

**Inventario (verificato su `593293b78`): come si comporta oggi ogni area**

| Area | Cache di oggi | Cosa vede l'utente quando la cache si invalida o torna sulla pagina | Con il principio |
|---|---|---|---|
| Dashboard, broker, Rischio, lotti | `portfolioStore`, `riskStore`; lotti senza cache | dati ricalcolati da zero, KPI da 0 (§1-§4) | §3.1-ter (fase 1) |
| Prezzi asset (grafici, lista) | `TimeSeriesStore` per asset (`assetPriceStoreRegistry.ts`); `invalidateAll` cancella i punti (`TimeSeriesStore.ts:194-214`) | dopo un sync o un aggiornamento il grafico si svuota e si ricarica (`assets/+page.svelte:865`, `:888`, `:959`; `assets/[id]:2014`, `:2103`, `:2446-2495`) | i punti restano; le date vengono richieste di nuovo e **sostituite** |
| Lista asset (l'elenco) | nessuna: `loadAssets()` a ogni apertura (`assets/+page.svelte:515-516`) | scheletro a ogni ritorno (`:1626`) | elenco in cache per la sessione, mostrato subito, rinnovato |
| Tassi FX (grafici, schede) | `TimeSeriesStore` per coppia (`fxStoreRegistry.ts:139-151`) | dopo un sync le schede si svuotano (`fx/+page.svelte:942-944`, `data: [], loading: true`) | i tassi restano e si aggiornano al loro posto |
| Lista FX (le coppie) | `fxRoutesStore` c'è, ma la pagina rilegge le rotte da sé (`fx/+page.svelte:307-316`) | scheletro a ogni ritorno (`:1115`) | la pagina usa lo store; scheletro solo la prima volta |
| File | nessuna (`files/+page.svelte:314-331`) | «Caricamento…» al posto della lista a ogni caricamento, anche dopo un upload (`:779`) | liste in cache per la sessione; dopo un upload la lista resta e si aggiorna |
| Transazioni | `txStore` in memoria, ma la pagina ricarica tutto all'apertura con `loading = true` (`transactions/+page.svelte:132`, `:161-171`, `:768`) | tabella vuota a ogni ritorno | idratazione da `txStore`, poi rinnovo in background |
| Anagrafiche (asset, broker) | `entityStore`: `invalidate` cancella le voci (`entityStore.ts:180-191`) | i nomi o le icone spariscono per un attimo | le voci restano e vengono riscritte dal rinnovo |

**Cose da fare bene perché il principio non mostri dati sbagliati:**

1. **Le cancellazioni.** Un rinnovo che si limita a fondere (`merge`) lascerebbe per sempre una data o una voce
   cancellata sul backend. Il rinnovo di un intervallo deve **sostituirlo**: ciò che manca nella risposta sparisce
   (nuovo `replaceRange` in `TimeSeriesStore`; nelle liste si sostituisce l'elenco). E se è l'utente a cancellare
   qualcosa, quella cosa sparisce subito dallo schermo, come oggi.
2. **Cambio utente o logout: si svuota sempre**, come oggi (`registerClientSessionReset`). I dati di un altro
   utente non si mostrano mai.
3. **Le bozze non cambiano.** `EditBuffer`, i modali e le modifiche non salvate sono stato dell'utente, non cache.
4. **Rinnovo fallito:** restano i dati vecchi, più un toast di errore. Niente schermata vuota né errore al posto dei
   dati.
5. **Corse:** una risposta arrivata dopo che la chiave, la pagina o la sessione sono cambiate si scarta, come oggi
   (`isClientSessionCurrent`, contatori di generazione).
6. **`data-busy`** resta `true` durante il rinnovo: i test aspettano su quello. È l'unico segnale macchina e
   l'utente non lo vede.
7. **La regola diventa scritta:** una riga nelle istruzioni del frontend (`.github/instructions/frontend.instructions.md`,
   § «Publish state») e nella pagina sviluppatore sullo stato. Così il prossimo componente la segue.

**Proposta di fasi** (da coordinare: tocca file di altri workstream):

- **Fase 1** (già verificata dal coordinator, 20 file): Dashboard, Rischio, lotti, dettaglio broker; regola dei sync
  (E2); valuta e filtri (E3); «Aggiorna» (E4); F2.
- **Fase 2** (questo principio, il resto):
  - core: `TimeSeriesStore` (+ `replaceRange`), `entityStore`;
  - pagine: lista e dettaglio asset, lista e dettaglio FX, file, transazioni;
  - i loro test.
  Si parte dopo la fase 1, con un nuovo elenco esatto da far verificare al coordinator (`assets/[id]` è di K,
  `assets/+page.svelte` l'ha appena toccato la famiglia Risk, i file e le transazioni vanno verificati).

### 3.1-ter Decisione del developer su E1 (06/10 21:36): stale-while-revalidate nel frontend

> «mmm non ci avevo pensato, no non mettiamoci a fare cose strane con la cache nel backen, potremmo invece fare
> che se vado in una pagina con cache invalidata, ma che prima aveva dei dati, faccio partire la chiamata al
> backend, e intanto mostro i vecchi, e in asinc, quando i dati tornano aggiorno la pagina, se non ci sono
> modifiche non mi accorgo di nulla, altrimenti vedrò i numeri muoversi lievemente, ma l'esperienza dall'app sarà
> fluida e rapida.
>
> per l'animazione nella correzione dei dati, cerca di prendere spunto da kpi e grafici di dashboard, che sono
> ottimi ora»

Questa decisione **sostituisce E1-A e E1-D**: niente marcature mirate, niente confronti di prezzo, niente nel
backend. La regola diventa generale:

- **L'invalidazione non cancella i dati: li segna «vecchi».** Vale per tutti i trigger di oggi, prezzo corrente
  compreso, e per «Aggiorna».
  - `portfolioStore`: report e contributo.
  - `riskStore`: interrogazioni e idoneità; i cataloghi restano esclusi (E6).
  - Cache dei lotti (E5).
- **Una pagina che trova dati vecchi per la sua chiave li mostra subito** e chiede quelli nuovi in background.
  Quando arrivano sostituisce lo stato. Se nel frattempo la chiave è cambiata o la sessione è un'altra, la risposta
  si scarta come oggi.
- **Correzione animata con quello che c'è già** (spunto da KPI e grafici della Dashboard):
  - `TweenedValue` passa dal vecchio valore al nuovo (900 ms, cubicOut);
  - i grafici ECharts usano `CHART_SET_OPTION_OPTS` (`echartsAnimationConfig.ts:40-48`): i punti con lo stesso
    nome si spostano alla nuova Y, quelli nuovi entrano, quelli tolti escono.
  - È lo stesso effetto che si vede oggi cambiando un filtro nella pagina.
- **Perché «se non ci sono modifiche non mi accorgo di nulla» sia vero**, al montaggio con dati già noti, dalla
  cache o vecchi:
  - i KPI partono **dal valore**, non da 0 (oggi `TweenedValue` parte sempre da `tweened(0)`, §4);
  - i grafici compaiono già disegnati, senza l'animazione d'ingresso.
  - Il conteggio da 0 e il disegno restano solo per il primissimo caricamento, quando non c'è ancora nessun dato.
  - È la parte di E7 che serve a questa decisione; il resto di E7 non c'è più.
- **`data-busy`** resta `true` durante il rinnovo in background: è il segnale macchina per i test, l'utente non lo
  vede.
- **Restano valide** (in attesa dell'OK):
  - E2: un sync senza scritture non segna i dati vecchi, quindi niente richieste inutili;
  - le modifiche mancanti: `merge`, `access/me`;
  - E3: valuta e broker per la sessione. Senza, la chiave al ritorno è diversa e non ci sono dati da mostrare;
  - E4: «Aggiorna» copre anche Rischio e lotti;
  - E6;
  - la correzione F2.
- **Test, da rivedere:**
  - E2E: al ritorno la pagina è già pronta con i dati vecchi (KPI ≠ vuoto) **prima** che la richiesta in
    background risponda (risposta trattenuta dal test). Dopo la risposta i valori nuovi sono sullo schermo e
    `data-busy="false"`;
  - unità: `invalidate` conserva i dati come vecchi; `fetchReport` restituisce i dati vecchi e avvia il rinnovo.

### 3.1-bis Variante E1-D: aggiornare la cache invece di svuotarla (domanda del developer, 06/10 21:30) — superata da 3.1-ter

> «riguardo il current price, capisco aggiornare, ma non si può aggiornare la cache invece di invalitarla tutta al
> get currenprice?»

- **Ricalcolare nel browser: no.** Il prezzo di un asset entra nel report tramite il motore:
  - NAV, P&L del periodo e totale, pesi dell'allocazione;
  - ultimo punto della storia, TWRR/MWRR;
  - conversione FX alla data di fine e quota dei broker co-posseduti;
  - obbligazioni quotate per 100 nominali.
  Rifarlo nel frontend duplicherebbe il motore e romperebbe la regola «calcoli solo nel backend». Correggere solo
  la colonna del prezzo lascerebbe i totali incoerenti.
- **Aggiornare dal backend, senza buttare la cache: sì** (stale-while-revalidate mirato):
  1. Quando arriva `/prices/current`, nessuna cache viene svuotata. Il report in cache viene **segnato «da
     aggiornare»** solo se valgono tutte e tre le condizioni:
     - il suo periodo arriva fino alla data del prezzo;
     - l'asset è tra le posizioni (`summary.holdings`);
     - il prezzo è diverso da quello usato: `valuation_reference_unit_price`/`_date`/`_currency` della posizione,
       `schemas/portfolio.py:378-380`.
     Fuori orario, per un asset che non possiedi o con un periodo nel passato non succede niente.
  2. Al ritorno sulla Dashboard la pagina mostra **subito** il report in cache, senza attese. Parte **una sola**
     richiesta in background e i numeri passano ai valori nuovi. Con E7 il passaggio è dal vecchio valore al
     nuovo, non da 0.
  3. I lotti seguono la stessa regola, ma per asset: diventa «da aggiornare» solo la voce dell'asset che ha cambiato
     prezzo.
  4. Rischio: raccomando di **non** rifarlo per il tick intraday. È calcolato sulle chiusure giornaliere ed è
     pesante; si aggiorna con «Aggiorna» o con le modifiche vere. In alternativa anche lui in background.
- **Costo:** una richiesta al ritorno, e solo se un asset posseduto ha cambiato prezzo.
  - In orario di borsa, sul percorso del developer succede quasi sempre: l'asset aperto da Performance di solito è
    posseduto.
  - Il backend ricalcola, perché la sua cache L2 è legata ai prezzi (`portfolio_service.py:2236-2410`): circa 1 s
    sui dati di test, invisibile perché intanto si vede la cache.
- **Rispetto a E1-A:** A fa zero chiamate, ma la Dashboard resta al prezzo di quando era stata aperta finché non si
  preme «Aggiorna». D tiene la Dashboard sempre aggiornata con una chiamata in background, al massimo una per
  ritorno.
- **Raccomandazione aggiornata: E1-D** per report e lotti, Rischio con «Aggiorna» (E1-A). Elimina il «da 0» che il
  developer vede senza mostrare prezzi vecchi.
- **Superfici in più:** `portfolioStore` (segno «da aggiornare» + rinnovo in background) e il listener riceve
  `response.data`, già previsto in §3.1. Nessun calcolo finanziario nel frontend.
- **Test in più:**
  - unità: un prezzo uguale non segna niente; un prezzo diverso su un asset posseduto segna solo i report che
    arrivano a oggi; un asset non posseduto non segna niente;
  - E2E: al ritorno c'è **al massimo una** richiesta `/portfolio/report`, partita **dopo** che la pagina mostra già
    i dati in cache.

### 3.2 Effetto su chi oggi conta sull'invalidazione

- **Banner N `sync_fx_pair`, banner STALE_PRICE, `onsynced` del Rischio, `handleFxPairCreated`**: fanno già
  `invalidate()` e `loadAll(true…)` da sé, quindi non cambia niente. Con un sync a 0 punti non si perde niente,
  perché non c'era niente di nuovo.
- **Dettaglio asset dopo un sync manuale con punti**: invalida come oggi.
- **Prezzo intraday di oggi** (E1 deciso): dopo aver guardato un asset, la Dashboard mostra subito il report in
  cache, segnato come vecchio, e ne chiede uno nuovo in background. Se il prezzo è cambiato, i numeri si spostano
  al valore nuovo.
- **`riskStore`, ramo di scarto** (`:89-92` e `RISK_DISCARD_ATTEMPTS`, `:61-71`, irrobustito dalla famiglia Risk):
  resta valido.
  - Con lo SWR una risposta scartata durante un rinnovo non svuota più lo schermo: restano i dati vecchi.
  - **Attenzione**: il rinnovo in background va scartato **solo** se cambia la chiave o la sessione, non a ogni
    marcatura come vecchio. Altrimenti, sul dettaglio asset con i tick ogni 30-60 s, non arriverebbe mai.
- **I cataloghi del rischio** non dipendono dal portafoglio: l'invalidazione da mutazione non li tocca (E6).
  Restano svuotati dal reset di sessione.
- **La cache di idoneità** (`queryEligibility`) dipende dai prezzi: su ogni trigger, prezzo corrente compreso,
  viene marcata come vecchia e rinnovata.

### 3.3 «Aggiorna» forza davvero (E4)

- Una funzione unica `refreshPortfolioViews()`: `invalidate()` + `invalidateRisk()` + un contatore di versione
  reattivo.
- Il controller del rischio e il pannello lotti osservano il contatore e ricaricano.
- La usano «Aggiorna» della Dashboard (`handleSync`) e quello del dettaglio broker (`handleRefresh`).

### 3.4 Restano filtri e valuta (E3)

- Valuta e filtro broker della Dashboard vanno in uno store di sessione per utente (sessionStorage, svuotato al
  logout con `registerClientSessionReset`), come il periodo.
- Si ripristinano sia con la freccia sia con la sidebar.

### 3.5 Prima i broker, poi le richieste (obbligatorio)

- `loadContribution` e `LotsAnalysisPanel` partono solo quando i broker posseduti sono noti.
- Così la richiesta ha sempre i `broker_ids` giusti e la chiave coincide con quella della prima visita.

### 3.6 Cache dei lotti (E5)

- Piccolo store di sessione `lotsAnalysisStore`, con chiave `asset | broker | parametri`.
- Si registra sul listener di mutazione e sul contatore di «Aggiorna».

---

## 4. Ricalcolo lato client con la cache piena (misurato, non corretto)

Sonda `/tmp/libreFolio_n_redraw_probe.mjs`, tre ritorni Transazioni → Dashboard:

- **Rete:** 0 richieste del report.
- **Pagina pronta** (`data-busy="false"`): 97–101 ms.
- **CPU:** passo dal clic a «pronta» ~84–108 ms di task e ~29–35 ms di script; dopo, 2 s quasi a zero.
- **Quello che si vede:** il valore principale del P&L Periodo conta da ~€365 a **€2.317,78** in ~1 s, ogni volta.
  - Campioni: `0ms:+423,23 € | 150ms:+1.259,64 € | 300ms:+1.808,47 € | 600ms:+2.272,10 € | 1000ms:+2.317,78 €`.
  - Causa: `TweenedValue.svelte` parte sempre da `tweened(0)` al montaggio (900 ms).
  - I grafici ECharts rifanno l'animazione d'ingresso (`echartsAnimationConfig.ts`: 600 ms).
- **Proposta per un passo a parte (E7):** niente tween al primo montaggio quando il dato arriva dalla cache, e
  niente animazione d'ingresso dei grafici quando i dati sono identici.

---

## 5. Decisioni aperte (raccomandazione in grassetto)

- **E1 — Prezzo corrente.** → **Deciso dal developer il 06/10 alle 21:36: stale-while-revalidate generale
  (§3.1-ter).** Le opzioni sotto restano come traccia.
  - **A: non svuota mai.**
  - B: aggiornamento in background al ritorno (stale-while-revalidate). È una chiamata in più, contro la tua regola.
  - C: svuota solo se il periodo finisce oggi. Durante la borsa svuoterebbe comunque ogni 30–60 s.
  - **D (nuova raccomandazione, §3.1-bis): non svuota.** Segna «da aggiornare» solo i report e i lotti toccati
    davvero (periodo fino a oggi, asset posseduto, prezzo cambiato). Al ritorno si vede subito la cache e c'è un
    solo rinnovo in background. Il Rischio resta su «Aggiorna».
- **E2 — Sync:** **svuotano solo se la risposta conta scritture** (campi del §3.1).
- **E3 — Valuta e filtro broker.**
  - **A: per la sessione, come il periodo.**
  - B: nell'URL (`?ccy=…&brokers=…`): tornano solo con la freccia, ma il link si può condividere.
  - C: com'è oggi.
- **E4 — «Aggiorna»:** **forza report, Rischio e lotti**, in Dashboard e nel dettaglio broker.
- **E5 — Cache dei lotti:** **sì**. Il pannello è nel tuo percorso e oggi lo si richiede 3 volte.
- **E6 — Cataloghi del rischio:** **non si svuotano** su una mutazione. La cache di idoneità invece sì, perché
  dipende dai prezzi.
- **E7 — Ricalcolo visivo** (tween e animazioni): **passo a parte**, dopo questo.

---

## 6. Superfici, conflitti, complessità

**Elenco esatto aggiornato col nuovo E1 (06/10, 21:45).** Sostituisce la tabella precedente.

| # | File | Modifica | Dipende da |
|---|---|---|---|
| 1 | `frontend/src/lib/stores/portfolio/portfolioMutation.ts` | regola con la risposta: un sync senza scritture non marca i dati come vecchi; aggiunte `merge` (`dry_run:false`) e `access/me`. `/prices/current` **resta** un trigger: marca i dati come vecchi, come vuole il developer | E2, mutazioni |
| 2 | `frontend/src/lib/stores/portfolio/portfolioMutation.test.ts` | casi con la risposta | E2 |
| 3 | `frontend/src/lib/api/zodios-client.ts:123` | passa `response.data` (una riga) | E2 |
| 4 | `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` | `invalidate()` marca i dati come vecchi invece di cancellarli; lettura sincrona della cache per l'idratazione; dati vecchi restituiti più rinnovo in background | **E1** |
| 5 | `frontend/src/lib/stores/portfolio/portfolioStore.test.ts` | casi SWR | E1 |
| 6 | `frontend/src/lib/stores/risk/riskStore.svelte.ts` | interrogazioni e idoneità marcate come vecchie; cataloghi non toccati dalle mutazioni; versione di «Aggiorna» | E1, E4, E6 |
| 7 | `frontend/src/lib/stores/risk/riskStore.test.ts` | casi SWR, E6, versione | |
| 8 | `frontend/src/lib/stores/risk/riskPanelController.svelte.ts` | idratazione sincrona da `getRiskQuerySnapshot`, rinnovo in background, reazione ad «Aggiorna» | E1, E4 |
| 9 | `frontend/src/lib/components/risk/levels/RiskLevelsPanel.svelte` | imposta il contesto «idratato dalla cache» per le sue card (una riga) | animazione |
| 10 | `frontend/src/lib/stores/portfolio/lotsAnalysisStore.svelte.ts` (**nuovo**) + `lotsAnalysisStore.test.ts` (**nuovo**) | cache dei lotti, SWR | E5 |
| 11 | `frontend/src/lib/components/brokers/lots/LotsAnalysisPanel.svelte` | usa lo store: mostra i dati vecchi e rinnova | E5 |
| 12 | `frontend/src/routes/(app)/dashboard/+page.svelte` | SWR in `loadAll` (idratazione sincrona), **F2** (broker posseduti prima di contributo e lotti), E3, «Aggiorna» = tutto, contesto «idratato» | E1, F2, E3, E4 |
| 13 | `frontend/src/lib/stores/portfolio/dashboardViewStore.ts` (**nuovo**) + test (**nuovo**) | valuta e filtro broker di sessione | E3 |
| 14 | `frontend/src/routes/(app)/brokers/[id]/+page.svelte` | `handleRefresh` (`:396-397`) → aggiorna tutto; contesto «idratato» per la sua `KpiSection` (una riga) | E4 |
| 15 | `frontend/src/lib/components/ui/TweenedValue.svelte` | il primo valore compare senza contare da 0 quando il sottoalbero è «idratato dalla cache» (contesto Svelte letto all'avvio). Per default non cambia nulla: al primo caricamento si conta ancora da 0 | animazione |
| 16 | `frontend/src/lib/components/dashboard/KpiSection.test.ts` (esistente) | casi del contesto: montata con dati in cache il valore compare subito; poi passa da vecchio a nuovo | animazione |
| 17 | `frontend/e2e/portfolio/dashboard-cache.spec.ts` (**nuovo**) | percorso del developer: dati vecchi a schermo **prima** della risposta trattenuta, poi i valori nuovi; perimetro dei broker; ripristino dei filtri; «Aggiorna» | |
| 18 | `scripts/test_runner/_frontend_portfolio.py` | +2 file nella lista `store-unit` (`:77`), +1 azione E2E e il suo posto in `all` | catalogo condiviso |
| 19 | `mkdocs_src/docs/user/dashboard/index.en.md` | cosa fa «Aggiorna», quali filtri restano, i dati vecchi mostrati durante l'aggiornamento | doc |
| 20 | `mkdocs_src/docs/developer/frontend/state/domain-state.md` | SWR e regola delle mutazioni (oggi la pagina è falsa) | doc |

**Non si toccano:**
- `KpiSection.svelte`, `KpiMetricBar.svelte`, `RiskMetricCard.svelte`: il contesto arriva da solo a `TweenedValue`,
  senza passarlo prop per prop;
- tutti i grafici, **`GrowthChart.svelte` compreso** (in lavorazione da A);
- backend, API, i18n.

**Animazione della correzione** («prendi spunto da KPI e grafici di Dashboard»): c'è già, nessuna modifica.
- `TweenedValue` passa dal vecchio valore al nuovo in KPI, `KpiMetricBar` e `RiskMetricCard`.
- I grafici con `CHART_SET_OPTION_OPTS` o il merge spostano i punti: `GrowthChart`, `AllocationHistoryChart`,
  `SemiDonutChart`, `GeographyMap`, `ScatterChart`, `CorrelationHeatmap`, i grafici dei lotti.
- Cambiano in un colpo, senza vuoto e senza spinner: `LineChart` (`setOption(option, true)`, `:807`, condiviso con
  asset e FX: Underwater e Simulazione del Rischio), `PerformanceChart:1081`, le tabelle e `KpiCard`.

**Fuori elenco, da decidere: l'animazione d'ingresso dei grafici al ritorno con la cache.**
- Per farli comparire già disegnati serve un `skipAnimation` al primo disegno in circa 9 componenti.
- Tra questi `GrowthChart.svelte` di A: la regola di `skipAnimation` (`:1700-1711`, oggi solo per il cambio di
  risoluzione) e il `setOption` (`:1742-1752`).
- Proposta: passo a parte, dopo il checkpoint di A, solo se il developer lo vuole. Oggi i grafici rifanno
  l'ingresso in ~0,6 s, ma i dati non vengono ricaricati.

- **Conflitti da verificare col coordinator:**
  - `dashboard/+page.svelte` (chi altro ci lavora?);
  - `riskStore`/`riskPanelController`: la famiglia Risk è già in `ebf4752e2`, quindi niente conflitto testuale con
    un ramo aperto. Le modifiche toccano però il suo codice appena integrato (cataloghi, contatore di versione):
    meglio avvisarla;
  - `brokers/[id]/+page.svelte`;
  - `LotsAnalysisPanel.svelte` (lotti, K o la famiglia?);
  - il catalogo test.
  - `portfolioMutation.ts` e `zodios-client.ts`: nessun ramo, già verificato.
- **Complessità:** media. Una regola pura, tre punti di ricarica, uno store di sessione, una cache nuova, una corsa
  da chiudere.
- **Rischi:**
  - la freschezza intraday si sposta su «Aggiorna» (voluto, da documentare);
  - una modifica che il filtro non conosce resterebbe in cache fino ad «Aggiorna»: va mitigato con il test di
    classificazione che elenca le rotte di scrittura;
  - la sessione deve svuotare lo store dei filtri al logout.

---

## 7. Passi ordinati (fase 1: via del coordinator il 06/10, 22:44)

0. Rileggere HEAD (`593293b78`); perimetro: i 22 percorsi del §6 più `create-edit.en.md`. **Da non toccare**
   (lavoro aperto di A): `e2e/portfolio/dashboard.spec.ts`, `GrowthChart` (+ test), `growthLadderBuckets`, i 4
   cataloghi i18n, `user/dashboard/charts.en.md`.
1. ✅ (06/10) Allineare il piano a E1 (§3.1-ter): questo passo.

   > **Note implementazione**: allineati §3.1 (riga `/prices/current`: resta un trigger), §3.2, §7 (DoD in due
   > casi: senza trigger 0 richieste; con trigger dati vecchi subito e un solo rinnovo per chiave) e §8 (test per
   > SWR).
   >
   > Contratti scelti per i rossi:
   > - `portfolioStore`: `invalidate()` marca i dati come vecchi; nuova `resetPortfolioCache()`, la pulizia
   >   completa al cambio di sessione; nuova `peekReport(...)` sincrona; `fetchReport` deduplica e non scarta su
   >   una marcatura.
   > - `riskStore`: nuova `markRiskStale()` per le mutazioni (cataloghi esclusi); `invalidateRisk()` resta la
   >   pulizia completa; `getRiskQuerySnapshot().stale`.
   > - Nuovo `lotsAnalysisStore`, nuovo `dashboardViewStore`.
   > - `TweenedValue`: `setTweenHydration()` e la chiave di contesto, nel `<script module>`.
   > - `portfolioMutation`: `requestPortfolioRefresh()`. Una risposta mancante conta come scrittura (default
   >   prudente).
   >
   > Messaggi d'errore riusati: `common.refresh` col messaggio, come fa già `fxCreationSync`;
   > `risk.states.loadFailed`; `brokers.lots.loadFailed`.
   >
   > **⚠️ Fuori pista**: per E6, due test della famiglia Risk cambiano contratto (`riskStore.test.ts:270`, `:324`:
   > il catalogo non si richiede più dopo una mutazione). Va segnalato nella review di Risk.
2. ✅ (06/10) Test rossi (test-author): §8.

   > **Note implementazione**: test-author, rossi per il motivo giusto (modulo o export mancante, oppure
   > asserzione sul contratto nuovo); i test preesistenti non toccati restano verdi.
   > - Unità, `vitest` diretto: store 33 rossi / 19 verdi (`portfolioMutation` 8 nuovi, `portfolioStore` 8 nuovi
   >   + 2 col `beforeEach` passato a `resetPortfolioCache`, `lotsAnalysisStore` 8, `dashboardViewStore` 7);
   >   rischio 13 / 125 (`riskStore` 8 nuovi + 2 riscritti per E6, `riskPanelController` 3 nuovi + 1
   >   asserzione girata); `KpiSection` 3 / 13.
   > - E2E `dashboard-cache.spec.ts`, corsia 6159: 5 su 5 rossi dopo tutto il setup (conteggio da 0 al primo
   >   fotogramma, scheletro al ritorno, righe di broker non posseduti `pos-4-1`, `pos-3-1`…, valuta EUR al
   >   ritorno, 0 `/risk/query` su «Aggiorna»).
   > - Runner: +2 file in `store-unit`, nuova azione `dashboard-cache`. `front_portfolio_all` si costruisce
   >   dal registro (`_common.py:347`), quindi la riga `add_test` è già la sua voce. `check-orphans` pulito.
   > - Log: `/tmp/libreFolio_n_cache_red_{store,risk,kpi,e2e,controller}.log`.
   >
   > **⚠️ Fuori pista**: `riskPanelController.test.ts:707-710` ('drops every on-demand result after a sync')
   > affermava `invalidateRisk` dopo `handleSynced()`, il contrario di D. Girata da test-author su mia
   > richiesta (`markRiskStale` una volta, `invalidateRisk` mai); da segnalare nella review di Risk insieme a
   > `riskStore.test.ts:278` e `:336`.
3. ✅ (06/10) Filtro e interceptor (E2, modifiche mancanti; `/prices/current` resta un trigger).

   > **Note implementazione**: `portfolioMutation.ts`: `isPortfolioAffectingMutation(method, url, data?)` legge la
   > risposta solo per `/assets/prices/sync` (`points_changed`/`events_changed` > 0), `/fx/currencies/sync`
   > (`total_points_changed`, altrimenti somma per coppia) e `/assets/merge` (`dry_run !== true`). Una risposta
   > illeggibile conta come scrittura. Aggiunte `PATCH`/`DELETE /brokers/{id}/access/me`. Il segnale ai listener
   > diventa `{kind: 'mutation', method, path} | {kind: 'refresh'}`; nuova `requestPortfolioRefresh()`.
   > `zodios-client.ts:123` passa `response.data`. Prova: `vitest run portfolioMutation.test.ts` → 27/27.
4. ✅ (06/10) SWR negli store: `portfolioStore` (vecchio invece di cancellato, lettura sincrona, rinnovo in background);
   `riskStore` (interrogazioni e idoneità; E6; versione di «Aggiorna»); `lotsAnalysisStore` (E5).

   > **Note implementazione**: stesso schema nei tre store. Ogni risposta in cache e ogni richiesta in volo
   > portano la marcatura (`seq`) sotto cui la domanda è partita. Vecchia = `seq` minore dell'ultima marcatura.
   > - Un chiamante si aggancia alla richiesta in volo solo se è partita dopo l'ultima marcatura; altrimenti
   >   parte un rinnovo.
   > - Una risposta più vecchia non sovrascrive mai una più nuova.
   > - Scarto solo per cambio di sessione o pulizia completa (`cacheGeneration`).
   >
   > Store per store:
   > - `portfolioStore`: `invalidate()` marca; `resetPortfolioCache()` è la pulizia completa, registrata sul
   >   reset di sessione; `peekReport(...)` condivide la chiave con `fetchReport` (`reportKey`); un rinnovo fallito
   >   risolve `null` e lascia la voce vecchia.
   > - `riskStore`: `markRiskStale()` è il listener delle mutazioni (cataloghi intatti, E6; toglie gli errori
   >   ricordati); `invalidateRisk()` resta la pulizia completa; `getRiskQuerySnapshot().stale`; un errore si
   >   ricorda solo se non c'è una risposta su cui ripiegare.
   > - Nuovo `lotsAnalysisStore.svelte.ts` (chiave: utente + domanda con le tre liste ordinate) e nuovo
   >   `dashboardViewStore.ts` (sessionStorage per utente, prefisso `librefolio_dashboardView:`, svuotato al
   >   reset di sessione).
   >
   > Prove: `vitest run src/lib/stores/portfolio/` → 52/52; `riskStore.test.ts` → 39/39.
   > La «versione di Aggiorna» non serve nello store: è `requestPortfolioRefresh()` (passo 3) più il
   > `refreshVersion` già esistente nel controller (passo 5).
5. ✅ (06/10, salvo `RiskLevelsPanel`) Pagine e componenti:
   - Dashboard (SWR in `loadAll`, F2, E3, E4, contesto «idratato»);
   - `riskPanelController` (idratazione, rinnovo, «Aggiorna»);
   - `RiskLevelsPanel` (contesto);
   - `LotsAnalysisPanel`;
   - dettaglio broker (`handleRefresh`, contesto).

   > **Note implementazione**:
   > - **Dashboard**:
   >   - all'init legge E3 (`dashboardViewStore`) e i broker posseduti, se la lista è già in memoria
   >     (`getAllBrokers().length > 0`, cioè ogni ritorno in-app); poi `hydrateFromCache()` mette report e
   >     contributo in cache sullo schermo **prima del primo render**;
   >   - `loadAll`: `peekReport` → mostra; chiede solo se vecchio, mancante o `force`; la richiesta più
   >     recente vince (`loadSeq`); un rinnovo fallito tiene i dati e mostra il toast
   >     `common.refresh — <errore>`;
   >   - contributo vecchio rinnovato in background (`contributionRefreshing` in `data-busy`, niente
   >     scheletro); stesso oggetto in cache → nessuna riassegnazione (`shownReport`, `shownContribution`);
   >   - F2: `brokersReady`; `onRequestContribution` arriva a `PositionsPanel` solo con i broker noti, e il
   >     pannello lotti riceve `ready`;
   >   - E3: valuta e filtro broker scritti al cambio, ripristinati all'init, ripuliti dagli id non più
   >     posseduti;
   >   - E4: «Aggiorna» = `requestPortfolioRefresh()` + `refreshVersion` a `RiskLevelsPanel` (prop già
   >     esistente) e a `LotsAnalysisPanel` + `loadAll(true)`;
   >   - contesto: `setTweenHydration(() => summary !== null && activeTab !== 'rischio')`.
   > - **`riskPanelController`**: in `loadBaseAttempt` legge gli snapshot (freschi o vecchi). Se c'è tutta la
   >   wave la mette a schermo subito (`initialLoading=false`, `refreshing=true`, `hydratedFromCache` solo se
   >   lo schermo era vuoto), poi chiede. `handleSynced` → `markRiskStale()`. Nuova opzione
   >   `onrefreshfailed`: se c'è e i risultati sono a schermo, un rinnovo fallito li tiene; senza, resta
   >   `loadError` come oggi.
   > - **`LotsAnalysisPanel`**: principale e storico della selezione passano da `lotsAnalysisStore` (cache
   >   subito, rinnovo se vecchio). Un rinnovo fallito tiene i lotti e mostra il toast
   >   `brokers.lots.loadFailed`. Nuove prop `ready` (default `true`) e `refreshVersion`. Gli effetti leggono
   >   gli input e caricano in `untrack`.
   > - **Dettaglio broker**: `handleRefresh` → `requestPortfolioRefresh()` + `refreshVersion` (rischio e lotti)
   >   + `loadOverview(true)`; contesto come la Dashboard.
   > - Prove: `dev.py front check` → 0 errori, 0 avvisi; Prettier su tutti i file toccati; `git diff --check`
   >   pulito.
   >
   > **⚠️ Fuori pista**:
   > - **`RiskLevelsPanel.svelte` passato ad A** (passo 24, D378, messaggio del coordinator 06/10): non
   >   toccato. Restano da aggiungere, al via, due righe nel `<script>` più due import:
   >   - `setTweenHydration(() => controller.hydratedFromCache)`;
   >   - `onrefreshfailed: () => toasts.error($t('risk.states.loadFailed'))`.
   >
   >   Fino ad allora sul Rischio i dati in cache compaiono subito e si rinnovano in background, ma le card
   >   contano ancora da 0 e un rinnovo fallito mostra il riquadro d'errore. Per questo il contesto di
   >   Dashboard e broker esclude il tab Rischio.
   > - Dashboard: anche `activeTab` e `activeAssetId` si leggono dall'URL all'init. Senza, un ritorno a
   >   `?tab=posizioni` montava prima la Panoramica (KPI, `GrowthChart`, allocazione) e la smontava subito.
   > - Dettaglio broker: anche `loadOverview` legge prima la cache (`peekReport`), altrimenti con dati
   >   vecchi il contesto non scattava mai. Il contributo del broker resta com'è: fase 2.
6. ✅ (06/10) `TweenedValue`: contesto opt-in, default invariato.

   > **Note implementazione**: `<script module>` esporta `TWEEN_HYDRATION_CONTEXT` (un `Symbol`) e
   > `setTweenHydration(isHydrated)`. Al montaggio, se il getter del contesto risponde `true`, il valore parte
   > da sé stesso (`tweened(untrack(() => value))`), altrimenti da 0 come oggi. I cambi successivi animano
   > come prima. `KpiSection`, `KpiMetricBar` e `RiskMetricCard` restano intatti. Prova:
   > `vitest run KpiSection.test.ts` → 16/16.
7. Gate della corsia, un comando per volta:
   - `front check`;
   - `front-portfolio store-unit` e `risk-unit`, `front-utility core-unit` e `component-unit`;
   - E2E: il nuovo spec, `front-portfolio banners`, `stale-price-banner`, `risk`;
   - `front-asset asset-detail`, `front-broker`.
   - `front-portfolio dashboard` va rifatto sulla revisione comune dopo l'ingresso di A.

   > **Evidenze (06/10–07/10, corsia 6159, `/tmp/librefolio-r2-n`, un comando per volta)**:
   >
   > | Gate | Esito | Carico |
   > |---|---|---|
   > | `dev.py front check` | 0 errori, 0 avvisi | — |
   > | `front-portfolio store-unit` | 52/52 | — |
   > | `front-portfolio risk-unit` | 39/39 | — |
   > | `front-portfolio risk-controller-unit` | 99/99 | — |
   > | `front-utility core-unit` | 3317/3317 (112 file), 26 s | ~6 |
   > | `front-utility component-unit` | 2725/2725 (108 file), 77 s | ~6 |
   > | `front-portfolio dashboard-cache` (nuovo) | **5/5**, 156 s | 9–14 |
   > | `front-portfolio banners` | 18/18, 59 s | 13 |
   > | `front-portfolio stale-price-banner` | 1/1, 25 s | 15 |
   > | `front-portfolio risk` | 33/33, 117 s | 17 |
   > | `front-asset asset-detail` | 29/29, 169 s | 17 |
   > | `front-asset asset-merge` | 3/3, 31 s | 10 |
   > | `front-broker detail` | 32/33, poi il rosso 3/3 da solo | 10–13 |
   > | `front-portfolio dashboard` | 26/26, 115 s (da rifare dopo A) | 8 |
   > | `front-portfolio broker-filter-label` | 2/2 (E3 non tocca il filtro di un contesto nuovo) | 7 |
   > | `front-portfolio privacy-masking` | 18/18 (legge i KPI) | 8 |
   > | `front-portfolio broker-icons` | 1/1 | 22 |
   > | `front-fx fx-flag-font` | 7/7 (legge i KPI) | 29 |
   > | `front-broker list` / `broker-recovery` / `broker-create-feedback` / `broker-unit` | 9/9 · 5/5 · 2/2 · 26/26 | 20–30 |
   >
   > Log: `/tmp/libreFolio_n_gate_*.log`.
   >
   > **⚠️ Fuori pista: un rosso, non di N.** `brokers-detail.spec.ts:1072` ('line and income submodes render
   > this broker own figures'), alle `:1088`, ha ricevuto `broker_ids [5, 1]` invece di `[1]`. Triage
   > (skill `test-triage`, §1): verdetto **assumption**.
   > - `[5, 1]` è il report principale della Dashboard su cui atterra `login()`. La pagina broker chiede sempre
   >   `[data.brokerId]`.
   > - Il test installa `recordBrokerReports` subito dopo il login, senza attendere che quella Dashboard sia
   >   ferma, e poi prende con `find` il **primo** report con i flag di reddito.
   > - Era già così alla base: la Dashboard chiedeva gli stessi flag e i tempi della sua richiesta non
   >   cambiano.
   > - Da solo: 3/3 verdi (`/tmp/libreFolio_n_triage_broker_{1,2,3}.log`).
   > - File fuori perimetro: segnalato al coordinator con la cura proposta (attendere `dashboard-page`
   >   `data-busy="false"` prima di registrare, o filtrare le chiamate fatte dalla pagina broker).
   >
   > **⚠️ Fuori pista: F2 senza broker posseduti** (segnalato dal docs-writer, verificato nel codice). Un utente
   > che non possiede broker poteva ancora chiedere senza `broker_ids`, e il backend allargava la richiesta a
   > tutti i broker visibili. Succedeva con «Aggiorna» e i cambi di filtro (`loadAll`), col contributo, le
   > candele e i lotti aperti da `?asset=`. Era così già alla base.
   > - Cura: `canAsk = brokersReady && ownedBrokerIds.length > 0` in `loadAll`, `loadContribution`,
   >   `loadPnlCandles`, nella prop `onRequestContribution` e in `ready` dei lotti.
   > - Rifatti dopo la cura: `front check` (0/0), Prettier, `front-portfolio dashboard-cache` 5/5 (128 s, carico
   >   12–15) e `dashboard` 26/26 (118 s).
8. ✅ (07/10) Doc EN (docs-writer, nessuno stamp):
   - `user/dashboard/index.en.md`;
   - `developer/frontend/state/domain-state.md`;
   - `user/assets/create-edit.en.md:233-237` (§8-bis).
   Poi consegna e FROZEN.

   > **Note implementazione**:
   > - `user/dashboard/index.en.md`:
   >   - paragrafo su periodo, filtro broker e valuta che restano per la sessione;
   >   - nuova sezione «🔄 Coming back and refreshing» (`#coming-back-and-refreshing`);
   >   - nota «Sharing affects these numbers» riscritta: era falsa, diceva che Editor e Viewer contano a importo
   >     pieno sulla Dashboard.
   > - `domain-state.md`: riga e sezioni di `portfolioStore` riscritte (descrivevano un calcolo nel frontend che
   >   non esiste); nuovo diagramma; regole del bus; listener; uso nelle pagine.
   > - `create-edit.en.md`: apertura della fusione col testo del developer; tolto «asset detail page».
   >   L'etichetta del menu della tabella è **Merge with…** (`assets.merge.action`).
   > - Prove: `dev.py mkdocs build` (strict) pulito due volte (`/tmp/libreFolio_n_cache_mkdocs_build{,2}.log`).
   >   `check-links`: 89 validi, 3 eccezioni note, 1 rotto già alla base (`assets/detail/chart/#rolling-return`,
   >   ancora solo in EN, link in `assets/[id]/+page.svelte:3010`, non toccato).
   > - Debito di traduzione (nessuno stamp): IT/FR/ES di `dashboard/index` (sezione nuova, nota Sharing ancora
   >   falsa) e di `assets/create-edit` (paragrafo della fusione). Log:
   >   `/tmp/libreFolio_n_cache_translate_validate.log`.
   >
   > **⚠️ Fuori pista**:
   > - Una frase del docs-writer sulle card del Rischio («non animano») era falsa per L2: le tre card di
   >   `L2Diversification.svelte:255-282` animano. Corretta: `hydratedFromCache` aspetta la riga di
   >   `RiskLevelsPanel`.
   > - **Fuori dai miei file, da decidere**:
   >   - `user/brokers/sharing.en.md:76` ripete l'affermazione falsa sulla Dashboard;
   >   - `developer/frontend/state/index.md:13`, `state/registries.md:41-53` e `developer/frontend/index.md:50`
   >     descrivono ancora il vecchio store;
   >   - il **tab Rischio della Dashboard non segue F2**: `scope={{kind: 'portfolio'}}` senza `broker_ids`, e
   >     `risk/service.py:490-492` prende tutti i broker accessibili, Editor e Viewer compresi. La doc utente lo
   >     dice come eccezione; se il developer vuole solo i posseduti, cambia una prop della Dashboard e una
   >     frase.

9. ✅ (07/10) Checkpoint della fase 1: review e concessioni del coordinator.

   > **Review di Risk** (sola lettura, su `riskStore`, `riskPanelController` e i test): OK, con 2 richieste.
   > - **`onrefreshfailed` troppo largo** (`riskPanelController.svelte.ts:481-485` al checkpoint). Al cambio di
   >   firma la vecchia ondata resta a schermo mentre parte la domanda nuova. Se quella fallisce, l'opzione
   >   avrebbe tenuto le cifre vecchie sotto gli input nuovi.
   >   - Cura: `shownQuestion` (le chiavi `makeRiskRequestKey` delle due ondate), scritto all'idratazione e al
   >     successo. Il toast parte solo se fallisce quella stessa domanda, altrimenti `loadError`.
   >   - Test del test-author, rossi prima: la cura è tenuta da parte in `/tmp/libreFolio_n_controller_fixed.svelte.ts`
   >     e la condizione vecchia è rimessa (marcata `TEMP red-first`) per la corsa rossa.
   >   - ✅ Rosso: il caso negativo nuovo (figure di A a schermo, B fallisce) chiamava `onrefreshfailed` una volta.
   >     I due positivi (B già a schermo, caricato o idratato) erano verdi, gli altri casi anche: 141/142
   >     (`/tmp/libreFolio_n_risk_review_red.log`).
   >   - ✅ Cura rimessa, nessuna riga `TEMP` rimasta. `vitest run src/lib/stores/risk/` → **155/155**
   >     (`/tmp/libreFolio_n_risk_review_green.log`), Prettier pulito.
   > - ✅ `riskStore.test.ts`: rimesso il controllo della ri-domanda del catalogo dopo uno scarto da
   >   `invalidateRisk()` (2 chiamate, torna la seconda risposta), subito dopo il caso E6, che resta. Verde.
   > - **`riskStore.test.ts:278`**: riscrivendolo per E6 si era perso l'unico controllo positivo della
   >   ri-domanda del catalogo. Va rimesso con lo scarto causato da `invalidateRisk()`.
   >
   > **Concessi in questo checkpoint**:
   > - `brokers-detail.spec.ts:1072` (cura dell'assunzione, test-author, rosso forzando la corsa, poi verde). ✅
   >   - Nel `beforeEach` del describe 'GrowthChart P&L mode' si attende `dashboard-page` visibile e ferma
   >     (`waitForSettled`), con `test.setTimeout(60_000)` sull'hook.
   >   - Rosso forzato: il primo report registrato era `[5,1]` con reddito (la Dashboard), atteso `[1]`
   >     (`/tmp/libreFolio_n_broker_race_red.log`).
   >   - Verde con la cura (`..._green.log`). L'action intera passa 33/33 a 1 worker e **33/33 a 4 worker**.
   >   - Il test-author segnala lo stesso rischio, non verificato, dove si intercetta `/portfolio/report`:
   >     `dashboard.spec.ts:282`/`:416`, `data-quality-banners.spec.ts:101`, `risk-lab.spec.ts`.
   > - 4 pagine EN (docs-writer, ✅): `user/brokers/sharing.en.md:76`, `developer/frontend/state/index.md`,
   >   `state/registries.md`, `developer/frontend/index.md`. Build strict pulito, `check-links` invariato.
   >   - Due modifiche oltre la richiesta in `state/index.md`, da approvare: tolti due archi falsi del diagramma.
   >   - Restano false, non toccate: in `registries.md` WebSocket/SSE e `getStore("AAPL")`; in
   >     `frontend/index.md` le cartelle `registries/` e `app/` DateRange.
   >
   > **Decisione del developer sul tab Rischio** (07/10, testuale): «Solo i broker posseduti, come il resto della
   > Dashboard». **Lotto successivo**, dopo l'ingresso del passo 24 di A e un fast-forward:
   > - la prop `scope` della Dashboard e le frasi delle due pagine utente;
   > - `risk-analysis.spec.ts` `:1422`, `:2779`, `:3561` (concessione futura);
   > - le 2 righe di `RiskLevelsPanel`;
   > - i commenti superati di `AssetSetRiskPanel.svelte` `:180`, `:188`.

   > **Prove finali sul codice definitivo** (07/10, corsia 6159):
   > - `front check` 0/0;
   > - `vitest run src/lib/stores/risk/` 155/155;
   > - `front-portfolio risk` 33/33 (91 s, carico 22);
   > - `front-portfolio dashboard-cache` **5/5 a 4 worker** (30 s, carico 12);
   > - `front-broker detail` **33/33 a 4 worker** (61 s, carico 19);
   > - porta 6159 libera.

10. ✅ (07/10) **Lotto 2**: tab Rischio solo sui broker posseduti, le due righe di `RiskLevelsPanel`, i commenti
    superati. Via del developer alle 13:10 («avviamoli adesso, sfruttiamo il tempo della coverage»); base
    `d07412899` (fast-forward delle 13:25).

    > **Decisione del developer** (07/10, testuale): «Solo i broker posseduti, come il resto della Dashboard».
    >
    > **Design confermato dal coordinator**:
    > - scope = tutti i broker posseduti, `{kind: 'portfolio', broker_ids: ownedBrokerIds}`, indipendente dal
    >   filtro: il sottotitolo `risk.dashboardFullPortfolio` resta vero;
    > - L1 (`scopeValue`, dal `summary` non filtrato) ora coincide con lo scope;
    > - il pannello si monta solo con `canAsk`, quindi un caricamento a freddo su `?tab=rischio` non manda
    >   richieste senza `broker_ids`;
    > - chi non possiede broker vede il vuoto con `common.noData`, nessuna chiave nuova.
    >
    > **Concessioni**:
    > - `dashboard/+page.svelte` (prop, montaggio, getter del contesto);
    > - `RiskLevelsPanel.svelte` (`setTweenHydration`, `onrefreshfailed`);
    > - `brokers/[id]/+page.svelte` (getter e commento);
    > - commenti di `AssetSetRiskPanel.svelte` (`:180`, `:188`, `:494-503`);
    > - `risk-analysis.spec.ts` (condizioni della Dashboard);
    > - `risk-lab.spec.ts` (commenti);
    > - un caso nuovo in `dashboard-cache.spec.ts`;
    > - doc EN: `user/dashboard/index`, `user/brokers/sharing`, il paragrafo Rischio di `domain-state.md`.
    >
    > Il CHANGELOG lo scrive il coordinator con le mie frasi.
    >
    > **Ordine**: il test-author scrive le specifiche senza lanciarle. Io lancio i rossi con la produzione invariata,
    > poi applico `/tmp/libreFolio_n_batch2_prod.py`, poi i verdi a 1 e a 4 worker. Il docs-writer lavora in
    > parallelo, fuori dalla corsia.
    >
    > **Doc (docs-writer, ✅)**:
    > - `user/dashboard/index.en.md`:
    >   - bullet Rischio: «every broker you own»;
    >   - nota Sharing senza eccezione;
    >   - «Coming back»: la sfumatura sul cambio di periodo o valuta;
    >   - bullet del filtro broker.
    > - `user/brokers/sharing.en.md`: tolta l'eccezione.
    > - `domain-state.md`: paragrafo Rischio; nel bullet Lotti `brokersReady` diventa `canAsk`. Quest'ultimo
    >   era falso dal lotto 1 ed è una parola sola, fuori dal paragrafo Rischio: lo dichiaro.
    > - Build strict pulito (`/tmp/libreFolio_n_b2_mkdocs_build2.log`); `check-links` invariato.
    >
    > **Rosso 1** (`dashboard-cache`, caso nuovo, produzione invariata): fallisce a `:532`. Ci sono 2 domande di
    > rischio `{"kind":"portfolio"}` senza `broker_ids` al caricamento a freddo; posseduti `[1, 5]`
    > (`/tmp/libreFolio_n_b2_red_dashcache.log`, carico 27).
    >
    > **Specifiche (test-author, senza lanciarle)**:
    > - `risk-analysis.spec.ts`:
    >   - la Dashboard si riconosce dall'insieme dei broker posseduti (`portfolioOver`, mai su un insieme vuoto),
    >     letto due volte, prima del caricamento e a pagina ferma: un vicino parallelo
    >     (`dashboard-broker-filter-label`) crea e cancella un broker di TEST_USER;
    >   - premessa: l'insieme posseduto non è `[brokerId]`;
    >   - aggiunto un controllo della base-wave in `openWithStoredBenchmark`, accettato e dichiarato;
    >   - corretto il commento sul live price (`:1135-1154`).
    > - `dashboard-cache.spec.ts`: caso nuovo (`:507-565`), con tre letture dell'insieme posseduto.
    > - `risk-lab.spec.ts`: solo commenti. Il test-author ha corretto anche due falsi vecchi in `holdLivePricePoll`:
    >   il trigger è l'insieme degli id, e `runGuarded` era già stato corretto il 25/09 in `b02f49727`.
    >
    > **Rosso 2** (`front-portfolio risk`, produzione invariata, carico 38): 9 falliti, 29 verdi, ed esattamente
    > i previsti:
    > - `:2814` → `:2839`;
    > - `:2920` → `:2970`;
    > - `:3701` → `:3720`;
    > - i 5 D378 → `:3808` («asked: {"kind":"portfolio"}»);
    > - `:4360` → `:4394`.
    >
    > Log: `/tmp/libreFolio_n_b2_red_risk.log`.
    >
    > **Produzione applicata** (`/tmp/libreFolio_n_batch2_prod.py`, poi Prettier):
    > - Dashboard: `{#if canAsk}`, `scope` sui posseduti, vuoto `common.noData` (`dashboard-risk-no-owned`),
    >   getter `summary !== null`;
    > - dettaglio broker: getter `portfolioSummary !== null`;
    > - `RiskLevelsPanel`: 2 import, `onrefreshfailed`, `setTweenHydration`;
    > - `AssetSetRiskPanel`: i 3 commenti.
    >
    > **Cancelli** (corsia 6159, un comando per volta, carico 13–59 per la coverage nella 6150):
    >
    > | Cancello | Esito |
    > |---|---|
    > | `front check` | 0 errori, 0 avvisi (rifatto dopo la cura) |
    > | unità risk · risk-controller · store · risk-levels-component · component | 40 · 102 · 52 · 247 · 2829 |
    > | `dashboard-cache` | 6/6 a 1 worker (anche dopo la cura) · 6/6 a 4 |
    > | `risk` | 38/38 a 1 · a 4 prima 37/38, poi **38/38** dopo la cura |
    > | `risk-lab` | 44/44 a 1 · 44/44 a 4 |
    > | `dashboard` · broker `detail` · `banners` | 26 · 33 · 18 |
    > | `mkdocs build` strict | 0 avvisi (anche con `#risk-tab`) |
    > | `check-links` | solo il rotto già alla base (`#rolling-return`) |
    >
    > Log: `/tmp/libreFolio_n_b2_*.log`, `/tmp/libreFolio_n_b2r_*.log`. Porta 6159 libera.
    >
    > **⚠️ Fuori pista: un difetto trovato dal test a 4 worker.** `risk-analysis.spec.ts:3849` (D378 «blocked»)
    > falliva a `:1316`: `dashboard-risk-tab` era nascosta. Triage (`test-triage`), verdetto **defect**: al
    > caricamento a freddo, finché i broker posseduti non arrivano, `{#if canAsk}` non rendeva niente, e la tab
    > restava **vuota** anche per l'utente. Sotto carico 40 sono serviti più di 8 s.
    > - Cura nel prodotto (§6 della skill): un ramo `{:else}` con lo spinner della tab Transazioni
    >   (`dashboard-risk-loading`), senza testo né chiave i18n.
    > - Rifatti: il test da solo 1/1, `risk` a 4 worker 38/38, `dashboard-cache` 6/6.
    >
    > **Ancora per Q**: `user/dashboard/index.en.md#risk-tab`, nuova sezione `## 🛡️ Risk Tab {: #risk-tab }`
    > (`:41`). Ci sono la spiegazione della voce 3, che ora rimanda alla sezione. È un titolo in più: debito di
    > traduzione IT/FR/ES.

11. ✅ (07/10) **Due rossi della coverage completa** (`d07412899`, carico 30–50, 2 worker), assegnati dal
    coordinator alle 16:08. Base `c958f857c`. Metodo: `test-triage`; i test li scrive il test-author; i difetti di
    prodotto si dicono al coordinator prima di correggerli.

    > Log della coverage letti in `/tmp/libreFolio_triage_20261007/`: il checkout principale non si legge.
    >
    > **1. `test_fx_conversion.py::test_missing_rate_error`, verdetto «assumption» (§1/§3).**
    > - Il test leggeva il **più vecchio** EUR/USD del DB condiviso e pretendeva che `+365` giorni fosse coperto dal
    >   backward-fill. Il seed FX (`populate_fx_rates()`, `populate_mock_data.py:2886-2961`, solo feriali `:2938`)
    >   copre ogni feriale da `max(prima tx − 7, oggi − 3 anni)` a oggi, quindi `+365` cade su un feriale con un suo
    >   cambio.
    > - Riprodotto sulla 6159 con il DB seminato: più vecchio 2025-09-23, chiesto 2026-09-23, `AssertionError`
    >   (`/tmp/libreFolio_n_tr_fx_seeded_old.log`). Su un DB fresco lo stesso test passa: verdetto diverso a
    >   seconda del contenuto del DB condiviso.
    > - In più `:400-401` ingoiava un `RateNotFoundError` con un `print_error`.
    > - **Cura** (test-author, solo quel test): la coppia **EUR/XTS** (codice ISO 4217 riservato ai test) con
    >   cambi il 2001-01-08 (1,25) e il 2001-01-12 (1,40), in `flush` **senza commit** e `rollback` in `finally`.
    >   La finestra viene verificata vuota prima di scrivere.
    >   - 7.1: prima del 2001-01-08 c'è `RateNotFoundError`;
    >   - 7.2: il 2001-01-10 usa il backward-fill dal 2001-01-08, e 100 EUR → 125 XTS (il cambio del 12 fa da
    >     trappola);
    >   - 7.3: nel giorno esatto niente backward-fill.
    >   - Tolto il `try/except` che ingoiava l'errore.
    > - Prove:
    >   - DB seminato, test nuovo: verde (`/tmp/libreFolio_n_fx_missing_rate_seeded.log`); nessuna riga EUR/XTS
    >     rimasta;
    >   - `services fx-conversion` su DB fresco: 18/18 (`/tmp/libreFolio_n_fx_conv_action.log`);
    >   - `ruff` e `black` puliti.
    > - Fuori perimetro, segnalati:
    >   - `_backend_services.py:929` cita ancora il «missing-rate boundary» fra i motivi dell'esclusiva;
    >   - la fixture del modulo fa commit di 12 righe MOCK senza ripulire.
    >
    > **2. `ai-export-contract.spec.ts:133`, verdetto «defect» (prodotto, già alla base).**
    > - La Dashboard abilita AI Export appena arriva il catalogo (`:949`), e `handleAiExport` manda
    >   `brokerIds: activeBrokerIds`, che resta `undefined` finché i broker posseduti non sono noti.
    > - Un export fatto in quella finestra parte senza `broker_ids`, e il backend lo allarga a tutti i broker
    >   accessibili (F2).
    > - Esisteva già dal 07/2026 (`c51e9930c`, `18225592e`); l'asserzione F2 dello spec è del 03/09 (`2572b2403`).
    >   Il carico l'ha esposto: sulla 6159, a carico 28, 3/3 verdi.
    > - Cura proposta (`!canAsk` nel `disabled` e nel `handleAiExport`) e test nuovo, rosso prima: **in attesa
    >   del via** del coordinator.
    >
    > **3. Nello stesso log, non assegnato: `ai-export-panel.spec.ts:19`, verdetto «assumption».**
    > - Fallisce in modo deterministico sulla 6159: Δy = 36, AI Export sopra Refresh.
    > - `3e5313d3e` (30/09) ha alzato `denseRow` della Dashboard da 810 a 950, e a 1280×720 il prodotto impila
    >   apposta; lo spec di agosto afferma ancora la stessa riga.
    > - Proposta inviata; decide il coordinator.
    >
    > **Via del developer** (16:29, testuale): «Approva tutte e tre le correzioni». Concessi
    > `ai-export-contract.spec.ts` (solo il caso nuovo) e `ai-export-panel.spec.ts` (il punto 3 passa da K a me).
    >
    > **Punto 2, fatto**:
    > - Test (test-author): caso nuovo `ai-export-contract.spec.ts:312`. Trattiene `GET /api/v1/brokers` su una
    >   Dashboard a freddo; dopo il catalogo il trigger deve essere disabilitato; al rilascio si abilita, e l'export
    >   porta l'insieme posseduto, letto dalla risposta che la pagina stessa ha ricevuto.
    > - **Rosso** a produzione invariata: `:334` («AI Export is enabled while the owned brokers are still unknown»);
    >   gli altri 3 casi verdi (`/tmp/libreFolio_n_ae_red-contract.log`).
    > - Cura nel prodotto (`dashboard/+page.svelte`): `disabled={… || !canAsk}`; `handleAiExport` rifiuta con
    >   `!canAsk`, e l'errore porta al toast esistente `aiExport.genericFailed`. Nessuna chiave nuova.
    > - Verdi: contract 4/4 a 1 e a 4 worker.
    >
    > **Punto 3, fatto**: lo spec del pannello legge il tier pubblicato su `window.__lfLayouts.dashboard`, a
    > larghezza stabilizzata come nello sweep. In `stackFilters` i due bottoni sono in colonna, accostati
    > (gap ≤ 12 px); negli altri tier stanno sulla stessa riga. Nessun controllo tra i due. Verde 6/6 a 1 e a 4
    > worker, già a produzione invariata.
    >
    > **⚠️ Fuori pista: la cura del punto 2 rompe `ai-export-memory.spec.ts:108`** (e `cutover`, che ne è l'alias).
    > Verdetto: **assumption**.
    > - Il test usa `e2e_test_user2`, che non possiede broker (VIEWER al 0%); con la regola approvata
    >   («…e ce n'è almeno uno») il suo export sulla Dashboard resta disabilitato.
    > - Prima partiva senza `broker_ids`, cioè proprio la falla F2.
    > - Proposti: secondo utente `TEST_ADMIN` (OWNER di tutti i broker) più l'asserzione «senza broker posseduti
    >   il bottone è disabilitato»; e una frase nella doc `user/ai-export/portfolio.en.md`. **In attesa della
    >   concessione.**
    >
    > **Altri cancelli verdi** (dopo la cura): `front check` 0/0, `services fx-conversion` 18/18, ai-export unit 353,
    > catalog, `dashboard-cache` 6/6, `dashboard` 26/26, toolbar-width-sweep 15/15.
    >
    > **Concessi** (17:37): `ai-export-memory.spec.ts` (solo `:108`) e `user/ai-export/portfolio.en.md` («Scope and
    > Data»).
    > - Test (test-author): il secondo utente diventa `TEST_ADMIN`, OWNER di tutti i broker. Prima del cambio
    >   utente, con `e2e_test_user2` (nessun broker posseduto, letto da `GET /brokers`), si verifica che
    >   `ai-export-button` resti **disabilitato** a pagina ferma (catalogo arrivato, `data-busy="false"`).
    > - In più, accettato e dichiarato: `route.abort()` su `api.github.com` per la pagina. Dopo il login
    >   dell'admin il browser chiederebbe a GitHub una nuova versione.
    > - **Rosso provato**: tolto per prova `|| !canAsk` dal `disabled`, il test fallisce a `:160` («AI Export is
    >   enabled for e2e_test_user2, who owns no broker…», `/tmp/libreFolio_n_aem_red.log`, carico 30). Il file
    >   è stato ripristinato identico (`81e1c1f99`).
    > - Doc (docs-writer): «Scope and Data» dice che l'export copre gli stessi broker della Dashboard (solo quelli
    >   posseduti, oltre lo 0%, ristretti dal filtro; mai quelli condivisi come Editor o Viewer), e che il bottone
    >   è disponibile solo quando la Dashboard ha caricato i broker; resta disabilitato se non se ne possiede
    >   nessuno. Build strict pulito.
    > - Segnalati, non toccati:
    >   - «follows the date range» è impreciso: l'export usa la fine del periodo come data dello snapshot, e la
    >     finestra è il periodo AI scelto. Succede anche in `dashboard/index.en.md` e `ai-export/index.en.md:141`;
    >   - la nota «Sharing» della Dashboard non elenca l'AI Export;
    >   - nessun segnale pubblicato di «catalogo applicato» (proposto un `data-catalog` sul trigger, come in
    >     `RiskAnalysisPanel`: decisione di interfaccia).
    >
    > **Cancelli finali** (codice definitivo, corsia 6159, carico 20–44):
    > - Prettier, `ruff`, `black` e `front check` (0/0) puliti;
    > - `front-ai-export all`: 18 E2E e 353 unità; sei action verdi (unit, catalog, contract, cutover, memory,
    >   panel);
    > - `memory` 4/4 a 4 worker; `services fx-conversion` 18/18;
    > - `mkdocs build` strict pulito; `check-links` solo il rotto già alla base (`#rolling-return`);
    > - `git diff --check` pulito; porta 6159 libera.
    >
    > Log: `/tmp/libreFolio_n_fin_*.log`.

**Definition of done:**

- **Ritorno senza trigger** (es. Dashboard → Transazioni → Dashboard): **0** `/portfolio/report`, **0**
  `/risk/query`, **0** `/lots/analysis`; i KPI compaiono subito al loro valore, senza contare da 0.
- **Ritorno dopo un trigger** (il percorso del developer: almeno una `/prices/current` sul dettaglio, poi la
  freccia ‹):
  - i **dati vecchi sono a schermo subito**: KPI non vuoti, niente scheletro, niente conteggio da 0, **prima** che
    la risposta trattenuta arrivi;
  - parte **un solo** rinnovo in background per chiave: `/portfolio/report`, e `/risk/query` sul Rischio già
    visto;
  - al rilascio compaiono i valori nuovi e `data-busy="false"`.
- **Perimetro (F2):** ogni richiesta del report e dei lotti ha i `broker_ids` posseduti; la tabella Performance
  mostra solo i broker posseduti.
- **Filtri (E3):** valuta e filtro broker ripristinati al ritorno.
- **«Aggiorna» (E4)** fa ripartire report, rischio e lotti; i dati vecchi restano a schermo intanto.
- **Rinnovo fallito:** restano i dati vecchi, con un toast che usa un messaggio d'errore già esistente; nessuna
  chiave i18n nuova.
- **Mutazioni (E2):** un sync a 0 punti non marca niente come vecchio; una fusione (`dry_run:false`) o un
  `access/me` sì.
- Test verdi; doc allineata.

---

## 8. Test, rossi prima

- **Unità** — `portfolioMutation.test.ts`, esistente, registrato in `front-portfolio store-unit`:
  - `/prices/current` → **true**: la riga `:13` resta com'è (E1 deciso, resta un trigger);
  - `/assets/prices/sync`: risposta con 0 punti e 0 eventi → false; con `points_changed: 3` → true;
  - `/fx/currencies/sync`: `total_points_changed` 0 → false; 5 → true;
  - `/assets/merge`: `dry_run: true` → false; `false` → true;
  - `PATCH` e `DELETE /brokers/7/access/me` → true;
  - le letture restano false.
- **Unità** — `portfolioStore.test.ts`, esistente, `store-unit`:
  - `invalidate()` conserva i dati come vecchi;
  - `fetchReport` sulla chiave vecchia restituisce subito i dati vecchi e fa partire **un solo** rinnovo, anche con
    più chiamanti;
  - a rinnovo concluso, la cache ha i dati nuovi e non sono più vecchi;
  - un rinnovo fallito lascia i dati vecchi;
  - un cambio di sessione svuota tutto, mai dati di un altro utente;
  - una lettura sincrona dalla cache esiste per l'idratazione.
- **Unità** — `riskStore.test.ts`, esistente, `risk-unit`:
  - una mutazione marca come vecchie interrogazioni e idoneità ma **non** tocca i cataloghi;
  - una interrogazione vecchia restituisce i dati e rinnova;
  - il rinnovo **non** si scarta perché arriva un'altra marcatura (tick), ma solo se cambiano chiave o sessione;
  - la versione di «Aggiorna» cresce.
- **Unità** — `lotsAnalysisStore.test.ts`, nuovo, `store-unit`: chiave `asset | broker | parametri`; SWR come sopra.
- **Unità** — `dashboardViewStore.test.ts`, nuovo, `store-unit`: valuta e filtro broker per utente, in
  sessionStorage, svuotati al logout.
- **Componente** — `KpiSection.test.ts`, esistente, `component-unit`:
  - montata nel contesto «idratato», il valore della KPI è **subito** quello finale;
  - senza contesto conta da 0 come oggi;
  - aggiornando la prop, passa dal vecchio al nuovo.
- **E2E** — `e2e/portfolio/dashboard-cache.spec.ts`, nuovo:
  - Ogni richiesta è contata da `page.on('request')` della pagina del test.
  - `/assets/prices/current` riceve una risposta nel browser, così nessun provider viene interrogato e
    l'interceptor gira comunque.
  - Isolamento: utente `TEST_USER`, sola lettura.
  1. Ritorno senza trigger: Dashboard → Transazioni → Dashboard (e il tab Rischio già visto) → **0**
     `/portfolio/report`, **0** `/risk/query`; i KPI sono al valore finale appena la pagina compare.
  2. Percorso del developer, attraverso `dashboard-tab-posizioni`, `positions-toggle-performance`,
     `positions-toggle-table`, riga `pos-*`, `context-menu-action-analyze-lots`, `lots-analysis-panel-asset-link`,
     attesa di almeno una `/prices/current`, `asset-detail-back-btn`. Il test trattiene `/portfolio/report`:
     - la Dashboard mostra già i dati: KPI non vuoti, niente scheletro, valore uguale a quello di prima del viaggio,
       **prima** del rilascio;
     - è partito **un solo** `/portfolio/report` per chiave;
     - dopo il rilascio, `data-busy="false"`.
     Lo stesso per il Rischio già visto: un solo `/risk/query` per richiesta, dati vecchi a schermo nel frattempo.
     Rosso oggi: scheletro e 3 richieste.
  3. Perimetro: dopo il ritorno, le righe `contribution-table tbody tr[data-row-id]` hanno solo broker posseduti, e
     ogni richiesta del report ha `broker_ids`. Rosso oggi: broker 2, 3, 4, 6 e una richiesta senza broker.
  4. Ripristino: con `dashboard-target-currency` su USD e `broker-filter-item-{id}`, il ritorno mostra i dati di
     quella chiave, e i rinnovi (se ci sono) sono in USD con quel broker. Asserzione su `data-*` e sul corpo delle
     richieste, non sul testo tradotto. Rosso oggi.
  5. «Aggiorna» (`sync-button`) sul tab Rischio fa partire almeno una `/risk/query`. Rosso oggi: 0.
- **Comandi** (corsia 6159, uno per volta): `front-portfolio store-unit`, `risk-unit`,
  `front-utility component-unit`, il nuovo spec.

---

## 8-bis. Decisione a margine: la fusione degli asset (06/10, 22:41)

Nata dalla domanda del developer su «Fondere due asset». Storia: piano «Identità dell'asset», decisione D9, commit
`0e07359b4` dell'08/08/2026.

> «no è sufficiente lasciarlo in asset global, io me ne ero anche scordato, nella guida spieghiamo che serve in
> caso ci si acccorge in un secondo momento che lo stesso asset era stato creato 2 volte ma con nomi lievemente
> diversi e non ci si era accorti della cosa»

- **Codice:** nessuna modifica. «Unisci» resta solo in Asset Global: il pulsante della card (`asset-card-merge`,
  `AssetCard.svelte:306`) e il menu contestuale della tabella (`AssetTable.svelte:348`). Nel dettaglio asset non si
  aggiunge.
- **Guida** (`mkdocs_src/docs/user/assets/create-edit.en.md:233-237`, fuori dal mio perimetro):
  - togliere «and on the asset detail page», perché è falso;
  - riscrivere l'apertura sul caso indicato dal developer.
  - Proposta EN:

  > If you only notice later that the same instrument was created twice — by hand once and by an import another
  > time, under slightly different names, or under its subscription code once and its market code another — each
  > copy holds part of its history and neither shows the whole position. On the **Assets** page, the **Merge**
  > action folds one into the other: a button on each card, or **Merge** in the right-click menu of the table.

  - Esistono anche IT/FR/ES: la traduzione la decide il coordinator. Niente stamp.
- **Effetto sulla cache** (fase 1): la fusione con `dry_run:false` diventa una modifica che segna i dati come
  vecchi (§3.1).

## 9. CHANGELOG (proposta, scrive il coordinator)

Allineata alla decisione E1 (§3.1-ter): i dati non si buttano, si mostrano e si rinnovano.

- **Coming back to the Dashboard no longer reloads what you just saw.**
  - With the same period, currency and broker filter, the KPIs, charts, Performance table, lots and Risk tab
    appear at once, also after opening an asset and returning with its back button (←). The KPI figures no longer
    count up from zero when they are already known.
  - If something changed meanwhile, such as a new transaction, new prices, or the live price an asset page
    checks, the figures stay on screen and move to the new values when the background refresh lands.
  - A price or rate sync that brought nothing new no longer forces a reload.
  - The currency and broker filter now stay for the session, like the period.
  - **Refresh** reloads everything, risk and lots included. If it fails, the previous figures stay and a
    message says so.
- **The Dashboard's Performance table and lots panel show only the brokers you own**, also when you come back to
  them. Coming back to the Positions tab used to include brokers shared with you as viewer or editor.
