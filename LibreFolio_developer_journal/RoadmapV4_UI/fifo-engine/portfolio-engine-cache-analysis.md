# Analisi architetturale — Portfolio Engine, FIFO history e cache

> **Tipo di documento**: analisi di architettura, nessuna implementazione.
> **Data**: 2026-07-15
> **Contesto**: quarto report della serie FIFO/WAC/Transfer, dopo:
> 1. `REPORT-fifo-lots-transfer-mismatch.md` — sintomi osservati su dashboard reale + 3 opzioni di redesign
> 2. `fifo-engine-current-state.md` — formule rigorose FIFO/WAC, semantica `cost_basis_override`
> 3. `fifo-segment-model-analysis.md` — validazione di 11 ipotesi su un modello a "segmenti", naming, short position
> 4. **Questo report** — l'unico dei quattro focalizzato su **infrastruttura**, non su matematica: cache,
>    responsabilità dei componenti, dipendenza dal range, fattibilità di ricostruzione, DTO/API.
>
> Nessuna modifica al codice è stata effettuata per produrre questo documento. Ogni affermazione è verificata
> leggendo il codice reale (citazioni `file:riga`) — non ci sono ipotesi non verificate.

---

## Indice

1. [Executive summary](#1-executive-summary)
2. [Architettura a 4 livelli — forma, I/O, responsabilità](#2-architettura-a-4-livelli)
3. [Mappa cache backend](#3-mappa-cache-backend)
4. [Mappa cache/stato frontend](#4-mappa-cachestato-frontend)
5. [Dati giornalieri/transazionali esistenti per tipo](#5-dati-giornalieritransazionali-esistenti-per-tipo)
6. [Fattibilità di ricostruzione lotti/vendite/transfer/custodia](#6-fattibilità-di-ricostruzione)
7. [Dipendenza dal range: inception, date_from, ritaglio in output](#7-dipendenza-dal-range)
8. [Confronto delle 5 opzioni architetturali](#8-confronto-delle-5-opzioni-architetturali)
9. [DTO/API proposte](#9-dtoapi-proposte)
10. [Caching proposto (backend + frontend)](#10-caching-proposto)
11. [Invalidazione cache dopo mutazioni](#11-invalidazione-cache-dopo-mutazioni)
12. [Codice duplicato e rischi di divergenza](#12-codice-duplicato-e-rischi-di-divergenza)
13. [Raccomandazione, piano incrementale, invarianti, test](#13-raccomandazione-finale)

---

## 1. Executive Summary

Il Portfolio Engine (`portfolio_engine.py`, 1988 righe) è un motore **pool-based**: per ogni `(broker_id,
asset_id)` mantiene un **unico accumulatore WAC aggregato** (`wac_pool_qty`, `wac_pool_cost`) — non una lista di
lotti. Questo è il fatto architetturale più importante di questo report: **l'Engine non può, per costruzione,
ricostruire lotti FIFO individuali**, perché l'informazione (prezzo/data di ciascun acquisto) viene distrutta
nel momento in cui due acquisti si fondono nel pool (§6). L'unico codice con granularità per-lotto è
`fifo_utils.calculate_fifo_lots()`, usato **solo** da `get_lots()`, completamente **disaccoppiato e non
cache-ato**, con lo stesso bug di filtro BUY/SELL-only già documentato nei report 1-3.

Punti salienti (dettagliati nelle sezioni citate):

- **Cache backend a 2 livelli funziona meglio di quanto sembri, ma con una promessa non mantenuta.** Il blob
  cache dell'Engine (§3.1) è pensato per essere "range-aware" con estensione incrementale, ma il codice che
  dovrebbe fare l'estensione incrementale è un **`pass` — mai implementato** (`portfolio_engine.py:1787-1790`).
  L'impatto pratico è limitato perché **tutti i call site reali passano `date_from=None`** (§7): il motore
  calcola sempre dall'inception a `date_to`, quindi l'unica "estensione" richiesta in pratica è l'avanzare di
  `date_to` di un giorno — che forza comunque un ricalcolo completo almeno una volta al giorno per ogni
  `(user, scope, currency)`.
- **`get_asset_history()` e `get_lots()` non usano NESSUNA delle cache di alto livello.** Il primo, in
  particolare, richiama `compute_wac_iterative()` **una volta per ogni punto prezzo** (potenzialmente centinaia
  per asset), e la cache dedicata (`_wac_cache`, maxsize=200) è troppo piccola per il proprio carico di lavoro
  entro una singola chiamata — rischio di *thrashing* interno (§3.4, §12).
- **Frontend**: 3 pattern di cache hand-rolled coerenti e ben progettati (`portfolioStore`, `entityStore`,
  `TimeSeriesStore`), nessuna libreria esterna (niente TanStack Query/SWR). Il pannello FIFO Lots **non usa
  alcuna cache** — ogni apertura/cambio asset richiama l'endpoint da zero (§4).
- **Nessun Redis o cache esterna**: tutto è in-process via `theine` (Rust, W-TinyLFU). In produzione single-worker
  (default di `dev.py`/Dockerfile) questo è sicuro; con `--workers > 1` le cache **non sono condivise tra
  processi** — rischio latente, non attivo di default (§3.5).
- **Tre percorsi di calcolo WAC paralleli e potenzialmente divergenti** coesistono nel backend: (a) l'inline
  WAC dell'Engine, (b) `wac_utils.compute_wac_iterative()` (usato da `/portfolio/wac` e da
  `get_asset_history()`), (c) `fifo_utils.calculate_fifo_lots()` (usato da `get_lots()`). Nessuno dei tre
  richiama gli altri; ogni bugfix matematico deve essere applicato fino a 3 volte (§12).

**Raccomandazione anticipata** (motivata in dettaglio al §13): **non estendere il Portfolio Engine esistente**
per la granularità di lotto. Costruire un **nuovo `FifoLotEngine` puro** (stesso stile di `fifo_utils.py`:
nessuna I/O, testabile in isolamento), che consuma le stesse transazioni pre-caricate ma produce una struttura
a **segmenti** (vedi `fifo-segment-model-analysis.md`) invece di un pool. Riusare l'infrastruttura di cache
esistente (`get_ttl_cache`) con una **nuova cache dedicata**, non sovraccaricare `_wac_cache` o il blob esistente.

---

## 2. Architettura a 4 livelli

```
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                             │
│  portfolioStore.svelte.ts  (L2 cache lato client, Map in-memory)     │
└───────────────────────────────┬───────────────────────────────────────┘
                                 │ POST /portfolio/report
                                 │ GET  /portfolio/asset-history
                                 │ GET  /portfolio/lots
                                 │ POST /portfolio/wac
┌────────────────────────────────▼──────────────────────────────────────┐
│ portfolio_api.py (200 righe) — 4 endpoint, nessuna logica propria     │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │
┌────────────────────────────────▼──────────────────────────────────────┐
│ portfolio_service.py (2434 righe) — PortfolioService                  │
│  orchestrazione, assemblaggio DTO, 2 cache proprie (L2 + WAC)         │
│  get_summary() / get_history() / get_positions_contribution() /      │
│  get_report() / get_asset_history() / get_lots()                     │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │ engine.calculate()  (4 call site — §7)
┌────────────────────────────────▼──────────────────────────────────────┐
│ portfolio_engine.py (1988 righe) — calcolo puro                       │
│  1. ScopeAwareTransactionClassifier  → classifica tx, in-transit      │
│  2. DailyStateBuilder.build()        → vettore DailyPortfolioState[]  │
│  3. DerivedViewsBuilder              → summary/history/allocation    │
│  4. PortfolioCalculationEngine       → orchestratore async + blob cache│
└────────────────────────────────┬──────────────────────────────────────┘
                                 │
┌────────────────────────────────▼──────────────────────────────────────┐
│ roi_utils / fifo_utils / wac_utils / valuation_utils — funzioni pure   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.1 `PortfolioCalculationEngine` (`portfolio_engine.py:1645-1988`)

**Ruolo**: orchestratore `async`. Input: `user_id, broker_ids, date_from, date_to, target_currency`. Output:
`PortfolioCalculationResult` (dataclass, non un DTO API).

Pipeline interna (`calculate()`, riga 1658):
1. Risolve `target_currency` e scope broker (`V(u)` visibili, `S` selezionati — `portfolio_engine.py:1676-1698`).
2. Carica **tutte** le transazioni dei broker in scope, **senza filtro di data** (`portfolio_engine.py:1701`:
   `select(Transaction).where(Transaction.broker_id.in_(scope_broker_ids))` — nessun `.where(date >= ...)`).
3. Classifica le transazioni (`ScopeAwareTransactionClassifier`).
4. Precarica `last_buy_prices` da TUTTI i broker visibili `V(u)` (non solo scope) per il fallback di valutazione.
5. Calcola `tx_fingerprint`/`price_fingerprint` e verifica il **blob cache** (§3.1).
6. Se manca, precarica prezzi/FX/asset-metadata in blocco.
7. Costruisce `DailyStateBuilder` e chiama `.build()`.
8. Salva il risultato nel blob cache e lo ritorna.

### 2.2 `DailyStateBuilder` (`portfolio_engine.py:418-1306`, la classe più grande del file)

**Ruolo**: funzione pura, **nessuna I/O**. Input: liste/mappe pre-caricate (transazioni classificate,
in-transit, prezzi, FX, valute asset). Output: `PortfolioCalculationResult` con `daily_states`,
`position_states_start/end`, accumulatori di periodo, `end_state`.

Divisione interna in **pre-frame** e **frame** (`portfolio_engine.py:464-471`, dettagliata al §7):

```
Pre-frame [inception, frame_start):        Frame [frame_start, date_to]:
  aggiorna cash, qty, WAC, pool K/R/W        applica tx del giorno
  NESSUNA valutazione di mercato             valuta prezzo/FX per il giorno
  NESSUNA emissione di DailyPortfolioState   emette DailyPositionState + DailyPortfolioState
```

Ogni posizione `(asset_id, broker_id)` è tracciata con **due soli numeri**:

```python
wac_pool_qty[(asset_id, broker_id)]   # quantità cumulata
wac_pool_cost[(asset_id, broker_id)]  # costo cumulato (nella valuta dell'asset)
# WAC corrente = wac_pool_cost / wac_pool_qty
```

Questo è **l'accumulatore centrale di tutto il motore** — e la ragione strutturale per cui l'Engine non può
rappresentare lotti (§6).

### 2.3 `DerivedViewsBuilder` (`portfolio_engine.py:1352-1632`)

**Ruolo**: funzione pura, converte `list[DailyPortfolioState]` in dict pronti per i DTO. Metodi: `build_history()`,
`build_performance_inputs()`, `build_allocation_current()`, `build_allocation_history()`,
`build_data_quality_report()`. Non tocca mai posizioni per-lotto: lavora solo sul livello "portafoglio
giornaliero" (`DailyPortfolioState`), che è già un aggregato del pool WAC.

### 2.4 `PortfolioService` (`portfolio_service.py`, 2434 righe)

**Ruolo**: orchestrazione + cache L2 + assemblaggio DTO finali (arricchimento con nomi broker/asset, calcolo ROI,
enrichment P&L). Metodi pubblici principali:

| Metodo | Output | Usa l'Engine? | Ha cache propria? |
|---|---|---|---|
| `get_summary()` | `PortfolioSummary` | Sì (o riusa `_precomputed_engine_result`) | No (eredita L2 di `get_report`) |
| `get_history()` | `list[PortfolioHistoryPoint]` | Sì (idem) | No (idem) |
| `get_positions_contribution()` | `PositionsContribution` | Sì (idem) | No (idem) |
| `get_report()` | `PortfolioReportResponse` | Sì, **un'unica volta**, poi passa il risultato agli altri 3 | **Sì — L2** (§3.2) |
| `get_asset_history()` | `list[AssetHistoryPoint]` | **No** — usa `compute_wac_iterative()` (percorso legacy, §12) | No — eredita solo la cache-per-punto di `_wac_cache` |
| `get_lots()` | `FIFOLotsResponse` | **No** — usa `fifo_utils.calculate_fifo_lots()` puro | **No, nessuna cache** |

**Osservazione strutturale importante**: solo 4 endpoint espongono questa logica
(`portfolio_api.py:38-200`): `POST /portfolio/wac`, `POST /portfolio/report`, `GET /portfolio/asset-history`,
`GET /portfolio/lots`. Gli endpoint standalone `/summary`, `/history`, `/allocation-history` sono stati
rimossi (commento di file, `portfolio_api.py:10-11`) — `get_summary()`/`get_history()`/
`get_positions_contribution()` sopravvivono solo come metodi Python richiamati internamente da `get_report()`.

---

## 3. Mappa cache backend

Tutta la cache backend usa un solo meccanismo (`backend/app/utils/cache_utils.py`, 171 righe): un registro
globale di `NamedCache`, wrapper sottile su **`theine.Cache`** (Rust, W-TinyLFU, thread-safe, timer wheel per
la scadenza — nessuna scansione periodica). **Non esiste Redis o altra cache esterna** nel repository (verificato:
nessun riferimento a Redis in `Pipfile`, solo un commento generico in `docker-compose.yml`).

```python
# cache_utils.py:94-117
def get_ttl_cache(name: str, maxsize: int = 1000, ttl: int = 3600) -> NamedCache:
    if name not in _cache_registry:
        _cache_registry[name] = NamedCache(name=name, maxsize=maxsize, ttl=ttl)
    return _cache_registry[name]
```

### 3.1 Blob cache dell'Engine — `_portfolio_blob_cache`

```python
# portfolio_engine.py:49
_portfolio_blob_cache = get_ttl_cache("portfolio_blob", maxsize=30, ttl=86400)  # 24h
```

**Chiave** (`portfolio_engine.py:1766-1772`, **non contiene `date_from`/`date_to`**):

```python
blob_key = (
    user_id,
    tuple(sorted(scope_broker_ids)),
    target_currency,
    tx_fingerprint,     # md5(id:updated_at per ogni tx) — portfolio_engine.py:1633-1642
    price_fingerprint,  # f"{count}:{max(fetched_at)}" — portfolio_engine.py:1868-1891
)
```

**Contenuto**: l'intero `PortfolioCalculationResult` (tutti i `daily_states` calcolati, non solo la finestra
richiesta).

**Logica di hit/miss** (`portfolio_engine.py:1774-1793`):

```
SE blob_from ≤ richiesta.from  AND  blob_to ≥ richiesta.to:
    → HIT CONTENUTO — ritorna il blob intero (nessun ritaglio qui: il ritaglio
      avviene più a valle, in get_history(), per-punto — vedi §7)

SE blob_from ≤ richiesta.from  AND  blob_to < richiesta.to  AND  end_state esiste:
    → dovrebbe fare "estensione forward" (ricalcolo incrementale da blob_to+1)
    → IN REALTÀ: -----------------------------------------------
       # Will proceed to full compute but with frame_start = blob_to + 1
       # and initial accumulators from end_state
       # (full extension with state resume deferred — for now recompute)
       pass                                    # portfolio_engine.py:1787-1790
      -----------------------------------------------
    → ricalcolo COMPLETO da zero (pre-frame + frame interi), come un miss pieno

ALTRIMENTI:
    → MISS — ricalcolo completo, il nuovo blob SOVRASCRIVE il vecchio alla stessa chiave
```

`EngineEndState` (`portfolio_engine.py:1307-1321`) esiste già come dataclass — contiene esattamente lo stato
serializzato necessario per riprendere il calcolo (`cumulative_cash`, `wac_pool_qty`, `wac_pool_cost`,
`capital_pool`, `returns_pool`, `withdrawn_pool`) ed è **popolato correttamente** ad ogni build
(`portfolio_engine.py:971-978`). **L'infrastruttura per l'estensione incrementale è pronta ma il punto di
ripresa non è mai collegato.**

**Impatto pratico limitato** (non "grave" come potrebbe sembrare a prima vista): come dimostrato al §7, tutti i
call site reali passano `date_from=None`, quindi `blob_from` è sempre la data della prima transazione mai
fatta dall'utente — è quindi STABILE tra richieste diverse dello stesso utente. L'unica variabile che cambia è
`date_to`, che nella pratica avanza di un giorno alla volta (quasi sempre "oggi"). Con `ttl=86400` (24h), il
blob comunque scadrebbe e richiederebbe un ricalcolo circa una volta al giorno — quindi il costo del "gap"
architetturale coincide quasi esattamente con il costo che il TTL avrebbe comunque imposto. **Il vero rischio è
in un caso diverso**: richieste con `date_to` **crescenti nello stesso giorno** per lo stesso
`(user, scope, currency)` (es. confrontare "come eri una settimana fa" e poi "come sei oggi" nella stessa
sessione) — ogni richiesta con `date_to` più recente del blob forza un **ricalcolo completo dall'inception**,
non un'estensione.

### 3.2 Layer-2 cache di `PortfolioService` — `_portfolio_l2_cache`

```python
# portfolio_service.py:87
_portfolio_l2_cache = get_ttl_cache("portfolio_layer2", maxsize=20, ttl=1800)  # 30 min
```

**Chiave** (`portfolio_service.py:2022-2035`, **contiene** `date_from`/`date_to` **richiesti dall'utente**,
oltre a tutti gli `include_*` flag):

```python
l2_key = (
    user_id, tuple(scope_broker_ids), base_currency,
    str(date_from), str(date_to),                 # finestra di visualizzazione ESATTA
    query.include_summary, query.include_history, query.include_allocation_history,
    query.include_breakdown, query.include_positions_contribution,
    tx_fp, price_fp,
)
```

**Perché questo funziona bene insieme al blob cache**: il blob cache (§3.1) non dipende dalla finestra di
visualizzazione (dato che l'engine calcola sempre da `date_from=None`), quindi un **miss** dell'L2 per una
NUOVA finestra (es. l'utente passa da "1M" a "3M") quasi sempre **hit** il blob cache sottostante (stesso
`tx_fingerprint`/`price_fingerprint`, stesso scope) — il "costo" del miss L2 è solo il ri-esecuzione di
`DerivedViewsBuilder` + filtro Python in-memory (§7), non un nuovo giro DB+calcolo. È un design **a due
livelli complementare**, anche se non documentato esplicitamente in questi termini nel codice.

### 3.3 WAC cache — `_wac_cache`

```python
# portfolio_service.py:90
_wac_cache = get_ttl_cache("portfolio_wac", maxsize=200, ttl=3600)  # 1h
```

**Chiave** (`portfolio_service.py:134`, usata sia da `compute_wac_iterative()` sia dalla variante multi-broker
a riga 369):

```python
wac_cache_key = (broker_id, asset_id, as_of_date.isoformat(), asset_currency,
                  target_currency_override, excluded_key, wac_fp)
```

dove `wac_fp` è un md5 calcolato **ad ogni chiamata**, PRIMA del lookup in cache, su tutte le transazioni
`(broker_id, asset_id)` con `date ≤ as_of_date` (`portfolio_service.py:117-132`):

```python
stmt = select(Transaction).where(Transaction.broker_id == broker_id, Transaction.asset_id == asset_id,
                                  Transaction.date <= as_of_date, Transaction.quantity.is_not(None),
                                  Transaction.quantity != 0)
db_rows = list((await session.execute(stmt)).scalars().all())
# ... hash di (id, updated_at) per ogni riga → wac_fp
wac_cache_key = (..., wac_fp)
cached_wac, wac_hit = _wac_cache.get(wac_cache_key)
if wac_hit: return cached_wac
```

**Conseguenza importante**: la query DB **viene sempre eseguita**, hit o miss — la cache salva solo il calcolo
matematico puro (`compute_wac_from_txlist()`), non il costo DB. Per un singolo asset con poca storia questo è
irrilevante; per `get_asset_history()` (§3.4) diventa un problema.

### 3.4 `get_asset_history()` e `get_lots()` — nessuna cache di alto livello

`get_asset_history()` (`portfolio_service.py:2205-2329`) itera **un punto prezzo alla volta**:

```python
for ph in prices:                                    # può essere centinaia/migliaia di righe
    wac_result = await compute_wac_iterative(         # una query DB + un md5 PER PUNTO
        session=self.db, broker_id=resolved_broker_id, asset_id=asset_id,
        as_of_date=ph.date, asset_currency=asset.currency or base_currency,
    )
```

Per un asset con 2 anni di prezzi giornalieri (~500 righe) su 2 broker, questo genera **~1000 chiavi distinte**
in `_wac_cache` — ma `maxsize=200`. Il risultato è **thrashing**: la cache evince le proprie voci più vecchie
prima che la funzione chiamante finisca di iterare, quindi anche una SECONDA chiamata identica a
`get_asset_history()` per lo stesso asset probabilmente NON trova quasi nulla in cache dei ~500 punti
necessari. La cache non è "rotta", è semplicemente **dimensionata per un pattern di accesso diverso**
(query singole sparse, non un ciclo denso mono-chiamata).

`get_lots()` (`portfolio_service.py:2331-2434`) non usa **nessuna** cache: ogni chiamata rifà
`_get_transactions()` (query DB semplice, `portfolio_service.py:756-772`, nessuna cache) +
`calculate_fifo_lots()` (puro, ricalcolato sempre). È più leggero di `get_asset_history()` (niente loop sui
prezzi), ma comunque a costo pieno ad ogni apertura del pannello.

### 3.5 Storage e rischi

- **Storage**: esclusivamente **in-process** (heap Python/Rust del singolo worker uvicorn). Nessuna
  persistenza tra restart, nessuna condivisione tra processi.
- **Scope**: implicitamente per-processo, non per-utente in modo isolato a livello di storage — l'isolamento
  utente è garantito solo dal fatto che `user_id` è il primo campo di ogni chiave di cache, non da meccanismi di
  storage separati.
- **Rischio identificato**: `dev.py` supporta esplicitamente `--workers N` (`dev.py:142,318-319`) con un
  commento che riconosce già un problema analogo per il JWT secret (`dev.py:258-261`: *"each worker would
  generate its own random secret"*). Il `Dockerfile` di default (riga 72) usa `uvicorn` **senza** `--workers`
  (quindi 1 worker) — **oggi il rischio non è attivo**, ma se un deployer aumenta i worker, ogni processo avrà
  le proprie cache **non sincronizzate**: un'invalidazione (es. dopo una modifica di transazione) in un worker
  non si propaga agli altri. Non è un bug introdotto da questo report, ma è una precondizione da annotare per
  qualsiasi nuova cache (§10) — se si vuole scalare a multi-worker in futuro, **serve un cache store esterno
  condiviso** (Redis o simile), non più `theine` in-process.
- **TTL come rete di sicurezza, non meccanismo primario**: l'invalidazione primaria è sempre by-fingerprint
  (cambia il dato → cambia il fingerprint → cambia la chiave → miss naturale). Il TTL (24h/30min/1h) è un
  limite superiore alla "vita" di una entry se il fingerprint non cambiasse per errore (bug) — ma nella pratica
  ogni scrittura DB pertinente cambia sempre `updated_at` o `fetched_at`, quindi il fingerprint cambia sempre
  correttamente quando serve.

---

## 4. Mappa cache/stato frontend

Nessuna libreria di data-fetching esterna: **niente TanStack Query, SWR, RTK Query** (verificato:
`grep -r "tanstack|swr|react-query" frontend/src frontend/package.json` → solo TanStack **Table** è presente,
non Query). Il client Zodios (`frontend/src/lib/api/zodios-client.ts:81-137`) è un thin wrapper axios +
validazione Zod — **zero cache**, tutta la cache è nei 3 pattern hand-rolled sottostanti.

```
┌──────────────────────────────────────────────────────────────────┐
│ dashboard/+page.svelte                                            │
│   dateRangeController → onDateRangeChange() → loadAll()           │
│   broker filter → scheduleReload() [debounce 2s] → loadAll()      │
│   sync button → invalidate() + loadAll(force)                     │
└───────────────┬────────────────────────────────────────────────────┘
                │ fetchReport(brokerIds, dateFrom, dateTo, currency, force)
┌───────────────▼────────────────────────────────────────────────────┐
│ portfolioStore.svelte.ts (191 righe) — L2 cache lato client        │
│   reportCache: Map<key, {data, timestamp}>   (Svelte 5 $state)     │
│   reportInflight: Map<key, Promise>          (dedup richieste)     │
│   key = brokerIds.sort().join(',') + dateFrom + dateTo + currency  │
│         + flag contrib/breakdown/nohist/noalloc                    │
│   TTL: NESSUNO — "timestamp" salvato ma mai controllato             │
│   invalidate(): svuota TUTTA la Map (non per-chiave)                │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ entityStore.ts (createEntityStore<T,Id>, 193 righe) — liste limitate│
│   assetStore, brokerStore = istanze della stessa factory             │
│   merge(items): upsert parziale — chiavi presenti sovrascrivono      │
│   invalidate(id): rimuove + resetta loaded=false (invariante chiave) │
│   version: Readable<number> per la reattività Svelte                │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ TimeSeriesStore.ts (222 righe) — serie storiche (prezzi, FX)        │
│   Map<ISO-date, T> — merge() idempotente, getRange() con gap-detect │
│   getRange(start,end) → {data: [...], gaps: [{start,end}, ...]}     │
│   il chiamante fetcha SOLO i gap dal backend (delta-fetch)          │
│   nessun limite di dimensione — cresce per tutta la vita della tab  │
│   registry: assetPriceStoreRegistry (key "assetId:CCY"),            │
│             fxStoreRegistry (key slug alfabetico "EUR-USD")         │
└─────────────────────────────────────────────────────────────────────┘
```

**Pannello FIFO Lots — nessuna cache**: `FIFOLotsPanel.svelte` chiama direttamente
`zodiosApi.get_fifo_lots_api_v1_portfolio_lots_get(...)` ad ogni apertura o cambio di asset/scope, senza
passare da nessuno dei tre pattern sopra. `OpenLotsTable.svelte`/`ClosedLotsTable.svelte`/
`BubbleLotTimeline.svelte` sono puramente presentazionali (nessuna chiamata propria). **Non esiste oggi alcun
meccanismo di drill-down/history-per-lotto** nel frontend — l'interazione con una bolla o una riga non apre
nessuna vista storica specifica di quel lotto.

**Trigger di invalidazione mappati** (agente di esplorazione, verificato su file reali):

| Azione utente | Cosa invalida |
|---|---|
| Click "Sync" sul dashboard | `invalidate()` di `portfolioStore` (svuota tutto) + `loadAll(force)` |
| CRUD transazione riuscito | `invalidatePortfolioCache()` (`transactions/+page.svelte:132-137`) |
| Creazione/modifica asset | `mergeAssets(...)` (upsert ottimistico) |
| Eliminazione asset | `invalidateAfterMutation(id)` |
| Creazione/modifica broker | `mergeBrokers(...)` |
| Sync/refresh prezzi asset | `invalidateAssetPriceStore(asset.id)` |
| — | `invalidateAllFxStores()` esiste ma nessun call site trovato — **probabile dead code o funzione di riserva mai collegata** |

---

## 5. Dati giornalieri/transazionali esistenti per tipo

| Tipo transazione | Cash ledger | Quantity ledger (`position_txs_by_date`) | WAC pool | 3-pool K/R/W | In-transit |
|---|---|---|---|---|---|
| `BUY` | Sì, se `amount≠0` | Sì (`quantity>0`, `asset_id` presente) | Aggiunta: `_buy_unit_cost()` → `|amount|/qty` | Sì, dedicato (BUY case, riga 563) | No |
| `SELL` | Sì | Sì (`quantity<0`) | Riduzione a WAC corrente (nessun ricalcolo del WAC) | Sì, dedicato (legge WAC **prima** di ridurre — invariante critico) | No |
| `TRANSFER` | No (di norma `amount=0`) | Sì — **nessun filtro di tipo** in `position_txs_by_date` (riga 484-488) | Tramite `_buy_unit_cost()`: usa `cost_basis_override` se presente, altrimenti `None` → *add-at-current-WAC* | **Non gestito esplicitamente** nel dispatch pre-frame (righe 544-582: solo DEPOSIT/WITHDRAWAL/DIVIDEND/INTEREST/FEE/TAX/BUY/SELL/CASH_TRANSFER/FX_CONVERSION) | **Sì**, via `InTransitInterval` (classificazione dedicata) |
| `ADJUSTMENT` | Se `amount≠0` | Sì — stesso "nessun filtro" di sopra | **Stesso fallback "auto"** di TRANSFER se manca `cost_basis_override` — **stesso bug matematico per split positivi già documentato in `fifo-segment-model-analysis.md`, ora confermato anche a livello Engine, non solo in `wac_utils.py`** | Non gestito esplicitamente | No |
| `DEPOSIT`/`WITHDRAWAL` | Sì | No | N/A | Sì, dedicato | No |
| `DIVIDEND`/`INTEREST` | Sì | No | N/A | Sì, dedicato (solo R) | No |
| `FEE`/`TAX` | Sì | No | N/A | Sì, dedicato (drena R poi K) | No |
| `CASH_TRANSFER`/`FX_CONVERSION` | Sì | No | N/A | Sì, dedicato (gambe linked) | Sì, se date diverse tra le gambe |

**`share_percentage`**: vive su `BrokerUserAccess` (`backend/app/db/models.py:423-447`), **non** su
`Transaction` — è una percentuale di comproprietà per `(user, broker)`, applicata uniformemente a ogni
transazione di quel broker (`ClassifiedTransaction.share`, `portfolio_engine.py:107`,
`ctxn.share` moltiplica ogni importo/quantità). Non esiste `share_percentage` per singolo lotto o transazione.

**FX**: precaricato in blocco (`_preload_fx_rates()`, `portfolio_engine.py:1893-1988`) come mappa
`(currency, target_currency, date) → rate`, per ogni giorno del range richiesto **quando serve per valutazione
di mercato** — non per ogni transazione singolarmente salvo quando la valuta della transazione differisce dal
target.

---

## 6. Fattibilità di ricostruzione

Domanda del task: *l'Engine conserva abbastanza informazione per ricostruire lotti FIFO, vendite attribuite ai
lotti, biforcazioni da transfer parziali, intervalli di custodia/transito, incassi cumulati per lotto, e
valore/P&L giornaliero del lotto?*

**Risposta sintetica: NO, per nessuno dei 6 punti**, per una ragione strutturale unica: `DailyPositionState`
(`portfolio_engine.py:352-370`) ha **un solo record per `(date, broker_id, asset_id)`**, con un singolo
`wac`/`cost_basis` aggregato — non una lista. Il dettaglio:

| Ricostruzione richiesta | Possibile oggi? | Perché |
|---|---|---|
| **Lotti FIFO individuali** | ❌ No | `wac_pool_qty`/`wac_pool_cost` sono **somme cumulative**; il momento in cui un secondo BUY si aggiunge al pool (`portfolio_engine.py:599`: `wac_pool_cost[key] = old_cost + unit_cost_asset_ccy * tx_qty`), il prezzo/data del primo BUY specifico è perso — resta solo la media. |
| **Vendite attribuite a un lotto specifico** | ❌ No | Una SELL riduce il pool aggregato (`portfolio_engine.py:611-619`) usando il WAC corrente, non un "primo lotto in coda" — l'Engine non sa quale acquisto storico la vendita ha "consumato". |
| **Biforcazioni da transfer parziali** | ❌ No | `InTransitInterval` (`portfolio_engine.py:110-131`) descrive un **intervallo aggregato** per la coppia di gambe transfer (quantità totale, `cost_basis_amount` totale) — non una lista di lotti trasferiti con id di provenienza. |
| **Intervalli di custodia/transito** | ⚠️ Parziale | Gli intervalli **esistono** a livello aggregato (`start_date`/`end_date` per l'intera gamba transfer) — sufficienti per "quanto cash/valore era in transito in un giorno", **non** sufficienti per "quale lotto specifico era in transito". |
| **Incassi cumulati per lotto** | ❌ No | Non esiste alcun accumulatore per-lotto; solo `per_realized[(asset_id, broker_id)]` aggregato per periodo (`portfolio_engine.py:1333`). |
| **Valore/P&L giornaliero del lotto** | ❌ No | `DailyPositionState.unrealized_pnl` è calcolato su `market_value - cost_basis` **aggregati** (riga 370); non esiste alcuna disaggregazione per lotto in nessuna struttura del motore. |

**L'unico codice con vera granularità di lotto** è `fifo_utils.calculate_fifo_lots()` (`fifo_utils.py:66-148`),
usato esclusivamente da `get_lots()`. Ma:
- **Non è integrato con l'Engine**: rilegge le transazioni da zero (`_get_transactions(broker_id,
  tx_types=_HOLDING_TYPES)`), non riusa `ClassifiedTransaction` né alcuna cache.
- **`_HOLDING_TYPES = {BUY, SELL}`** (`portfolio_service.py:698`) esclude **TRANSFER e ADJUSTMENT** — bug già
  documentato nei report 1-3, qui confermato essere anche l'ostacolo diretto a qualsiasi vista Gantt "lotti +
  transfer" con i dati attuali.
- **Nessuna fusione per data/prezzo**: ogni BUY è un lotto separato per costruzione (`buy_queue.append([tx,
  tx.quantity])`, `fifo_utils.py:99`) — coerente con l'ipotesi 2 già smentita in `fifo-segment-model-analysis.md`
  (nessuna fusione avviene oggi, indipendentemente dal prezzo).

**Conclusione**: costruire una vista "Gantt dei lotti" o "history on-demand del lotto" **richiede
necessariamente un nuovo motore o una nuova struttura dati** — non è raggiungibile con un'estensione additiva
di `DailyPositionState`, perché quella struttura è *per design* un aggregato irreversibile (la somma non è
invertibile in lotti individuali senza rifare il calcolo da zero con un algoritmo diverso).

---

## 7. Dipendenza dal range

**Scoperta principale**: tutti e 4 i call site reali di `engine.calculate()` passano `date_from=None`:

```python
# get_summary()               — portfolio_service.py:967
date_from=None,
# get_history()                — portfolio_service.py:1480
date_from=None,  # Always compute from t=0 for correct cumulative values
# get_positions_contribution() — portfolio_service.py:1938
date_from=None,
# get_report()                 — portfolio_service.py:2047
date_from=None,  # always from t=0 for correct cumulative values
```

Conseguenza diretta in `PortfolioCalculationEngine.calculate()`:

```python
first_tx_date = min(tx.date for tx in all_txs)
actual_from = date_from or first_tx_date     # SEMPRE first_tx_date, dato che date_from è sempre None
actual_to = date_to or date_type.today()
```

E in `DailyStateBuilder.__init__`:

```python
self.frame_start = frame_start if frame_start is not None else date_from
# frame_start non è MAI passato esplicitamente ai call site reali (verificato: nessuna chiamata a
# DailyStateBuilder(...) nel file passa frame_start=), quindi self.frame_start == date_from == actual_from
# == first_tx_date SEMPRE.
```

**Cosa significa in pratica**: il **pre-frame è sempre vuoto** nell'uso reale attuale. Ogni richiesta — anche
per un grafico "ultima settimana" — fa valutare a mercato **ogni giorno da quando l'utente ha fatto la prima
transazione**, poi filtra il risultato SOLO a valle, in Python, dopo il calcolo completo:

```python
# get_history() — portfolio_service.py:1497-1500 (ribasamento per il ROI di periodo)
if date_from and nav_snapshots:
    pre_period = [s for s in nav_snapshots if s.date <= date_from]
    ...
```

```
┌─────────────────────────────────────────────────────────────────────────┐
│ COSA VIENE CALCOLATO                                                    │
│ [prima transazione mai fatta] ═══════════════════════════════ [date_to] │
│                                     (valutazione di mercato per OGNI    │
│                                      giorno di questo intero intervallo)│
├─────────────────────────────────────────────────────────────────────────┤
│ COSA VIENE MOSTRATO ALL'UTENTE (filtro Python, in-memory, dopo)         │
│                          [date_from] ══════════════ [date_to]          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Perché questo non è "solo" uno spreco**: la motivazione originale del pre-frame (documentata nel graphify wiki,
`concepts/pre-frame-frame-separation.md`) era evitare di valutare a mercato l'intera storia per grafici corti.
Nella pratica attuale questo beneficio **non si realizza mai** perché nessun chiamante lo attiva — ma la
scelta di calcolare sempre da `date_from=None` non è arbitraria: serve a garantire `cumulative_external_cash_flow`,
`capital_baseline`, MWRR/TWRR corretti *dall'inizio del portafoglio*, che sono grandezze intrinsecamente
cumulative e non "ri-basabili" parzialmente senza conoscere lo stato iniziale — motivo per cui il ribasamento
avviene a valle sui `nav_snapshots` già calcolati, non modificando l'input dell'Engine.

**Implicazione per una nuova feature "history per lotto"**: dato che l'Engine calcola *sempre* l'intera storia
per lo stesso `(user, scope, currency)`, un nuovo `FifoLotEngine` che riusi lo stesso pattern (sempre
dall'inception) **erediterebbe gratuitamente la compatibilità con il blob cache esistente in termini di
scope/valuta** — cioè non introdurrebbe una NUOVA dimensione di cache-miss per range, perché il range non è mai
stato realmente una dimensione della cache dell'Engine (§3.1). Sarebbe però necessaria una **cache dedicata**
(non condivisa con `_portfolio_blob_cache`) perché la struttura del risultato (segmenti/lotti) è diversa da
`PortfolioCalculationResult` (§10).

---

## 8. Confronto delle 5 opzioni architetturali

| Opzione | Riuso codice | Isolamento/testabilità | Rischio di rottura dell'esistente | Costo cache | Adatta a short position (report 3) |
|---|---|---|---|---|---|
| **A. Estendere il Portfolio Engine** (aggiungere lista lotti a `DailyPositionState`) | Alto (stesso pipeline) | Basso — la classe `DailyStateBuilder` è già 900 righe, ogni modifica rischia regressioni su NAV/3-pool/MWRR già stabili e testati (20 unit test in `test_portfolio_engine_vnext.py`) | **Alto** — `wac_pool_qty/cost` sono usati per NAV, K/R/W, allocazioni; introdurre lotti nello stesso ciclo rischia di raddoppiare la complessità di una funzione già centrale e ben rodata | Nessuna nuova cache, ma il blob esistente diventerebbe molto più pesante (ogni giorno× ogni lotto anziché ogni giorno×ogni posizione) | Difficile: bisognerebbe modificare la STESSA struttura dati con semantica negativa, alto rischio di regressione su codice già fragile (report 3: shorting "a metà" già oggi) |
| **B. Nuovo `FifoLotEngine` puro, event-sourced** | Medio — riusa `ClassifiedTransaction`/`InTransitInterval` come input, ma logica di stato indipendente | **Alto** — stesso stile isolato di `fifo_utils.py` (0 I/O), testabile con liste di transazioni sintetiche senza DB | Basso — non toccando `DailyStateBuilder`, zero rischio per NAV/MWRR/3-pool esistenti | Cache dedicata nuova, chiave naturale = stessi fingerprint già calcolati per il blob esistente (riuso del *pattern*, non della cache) | **Sì** — un motore nuovo può nativamente modellare segmenti con quantità negativa come proposto in `fifo-segment-model-analysis.md` §modello short |
| **C. Helper dentro `PortfolioService`** (funzione che pos-processa l'output engine) | Alto (nessun nuovo modulo) | Basso — mescolerebbe orchestrazione (già 2434 righe) con logica di dominio | Basso per l'Engine, ma alto per la manutenibilità di `PortfolioService` (già la classe più grande del backend) | Riuso di `_wac_cache`/L2 — rischio di ripetere il problema di thrashing già osservato in `get_asset_history()` (§3.4) | Scomodo — la logica short richiede stato dedicato, non un post-processing leggero |
| **D. Precomputazione di tutte le history** (calcolare lotti/segmenti per ogni asset ad ogni scrittura) | Basso | Alto (nessuna logica request-time) | Basso per le richieste in lettura, **alto per la scrittura**: ogni BUY/SELL/TRANSFER dovrebbe invalidare/ricalcolare potenzialmente TUTTI gli asset di un utente | Costo di storage permanente (serve una tabella persistita, non solo cache TTL) | Complesso: ogni transazione che tocca una posizione short richiederebbe una ripropagazione completa |
| **E. History lazy per lotto selezionato** (calcolo solo quando l'utente apre il drill-down di UN lotto) | Alto (riusa B) | Alto | Basso | Cache naturale per singolo `lot_id` (piccola, mirata) — pattern analogo a `TimeSeriesStore` col gap-detection già esistente lato frontend | Sì, si presta bene: un lotto short è comunque "un lotto", la history è la stessa forma |

**Nota su D vs E**: non sono mutuamente esclusive. La lista aperta/chiusa dei lotti (vista d'insieme, tabella +
Gantt) deve necessariamente essere calcolata per **tutti** i lotti di un asset (non si può "laziare" la lista
stessa) — questo è già il pattern odierno di `get_lots()`. **La history giornaliera (valore/P&L/prezzo nel
tempo) di UN lotto specifico**, invece, è naturalmente lazy: nessun utente guarda la history di 50 lotti
contemporaneamente. Le opzioni B (per il motore) + E (per la history drill-down) sono complementari, non
alternative — vedi raccomandazione al §13.

---

## 9. DTO/API proposte

Basandomi sulle convenzioni esistenti (`OpenLotSchema`/`ClosedLotSchema`/`FIFOLotsResponse`,
`AssetHistoryPoint`, `PortfolioReportQuery/Response`), estensione **additiva**, nessuna rottura dei DTO
esistenti:

### 9.1 Elenco lotti + segmenti Gantt

```python
class LotSegmentSchema(BaseModel):
    """Un segmento di lotto per la vista Gantt — estende OpenLotSchema/ClosedLotSchema
    con l'identità stabile e gli intervalli di custodia necessari per il rendering a barre."""

    lot_id: str                      # oggi = str(buy_transaction_id); con transfer parziali
                                      # diventa "{buy_transaction_id}:{broker_id}" (vedi report 3)
    broker_id: int
    asset_id: int
    origin_date: date_type           # rinominato da buy_date — coerente con naming report 3
    origin_unit_price: SafeDecimal   # rinominato da buy_price
    original_quantity: SafeDecimal
    remaining_quantity: SafeDecimal
    status: Literal["open", "closed", "partially_transferred"]
    custody_intervals: list["CustodyInterval"]   # NUOVO — assente oggi

class CustodyInterval(BaseModel):
    """Un intervallo di possesso continuo dello stesso segmento presso un broker."""
    broker_id: int
    start_date: date_type
    end_date: Optional[date_type]    # None = ancora in corso
    transfer_in_tx_id: Optional[int] = None
    transfer_out_tx_id: Optional[int] = None

class LotsGanttResponse(BaseModel):
    asset_id: int
    segments: list[LotSegmentSchema]
    total_realized_pnl: SafeDecimal
    total_unrealized_quantity: SafeDecimal
```

### 9.2 Dettaglio/history on-demand di un lotto

```python
class LotHistoryPoint(BaseModel):
    date: date_type
    market_price: SafeDecimal
    market_value: SafeDecimal
    unit_cost: SafeDecimal           # origin_unit_price O recognized_unit_cost, esplicito
    cost_basis: SafeDecimal
    unrealized_pnl: SafeDecimal
    cumulative_proceeds: SafeDecimal  # NUOVO — incassi cumulati (dividendi attribuiti? vedi nota)

class LotHistoryResponse(BaseModel):
    lot_id: str
    asset_id: int
    broker_id: int
    points: list[LotHistoryPoint]
```

> **Nota aperta**: "incassi cumulati per lotto" (`cumulative_proceeds`) presuppone una regola di attribuzione
> di DIVIDEND/INTEREST ai lotti (es. pro-rata per quantità posseduta quel giorno) — questa regola **non esiste
> oggi in nessuna forma nel codice** (i dividendi sono attribuiti per asset/broker in `per_income`, mai per
> lotto). È una decisione di prodotto da prendere esplicitamente, non un dettaglio implementativo — la
> propongo qui come domanda aperta, non come soluzione decisa.

**Endpoint proposti** (seguendo lo stile REST esistente in `portfolio_api.py`):

```
GET /portfolio/lots/gantt?asset_id=&broker_ids=&as_of_date=   → LotsGanttResponse
GET /portfolio/lots/{lot_id}/history?date_from=&date_to=      → LotHistoryResponse
```

### 9.3 WAC broker singolo/cumulato — già esistente, nessuna nuova API

`POST /portfolio/wac` (esistente, `portfolio_api.py:41-129`) già copre "WAC singolo broker" per query esplicita
`(broker_id, asset_id, date_range)`. `get_asset_history()` (esistente) già copre "WAC cumulato" quando
`len(resolved_broker_ids) > 1` (via `compute_wac_iterative_multi_broker`, `portfolio_service.py:2308`). **Non
serve nulla di nuovo qui** — vale la pena solo segnalare che `get_asset_history()` andrebbe ottimizzato (§12)
prima di aggiungergli altro carico.

---

## 10. Caching proposto

**Principio guida**: non riusare `_wac_cache` (già a rischio thrashing, §3.4) né `_portfolio_blob_cache`
(struttura del risultato incompatibile — vedi §6). Creare **due nuove cache dedicate**, stesso meccanismo
(`get_ttl_cache`), dimensionate per il pattern di accesso reale:

```python
# Nuova cache 1: lista lotti/segmenti per asset — pattern di accesso: 1 lookup per apertura pannello,
# stesso ordine di grandezza di _portfolio_l2_cache
_lots_gantt_cache = get_ttl_cache("portfolio_lots_gantt", maxsize=50, ttl=1800)  # 30 min, come L2 report

# Nuova cache 2: history per singolo lotto — pattern: molte chiavi piccole, TTL più lungo perché
# la history di un lotto CHIUSO non cambia mai più (a meno di correzioni retroattive)
_lot_history_cache = get_ttl_cache("portfolio_lot_history", maxsize=300, ttl=3600)  # 1h
```

**Chiavi proposte**:

```python
# Lista lotti (analoga a l2_key esistente, ma senza date_from/date_to display — vedi §7:
# i lotti sono "as of date_to", non un periodo)
lots_key = (user_id, tuple(sorted(broker_ids)), asset_id, str(as_of_date), tx_fingerprint)

# History di un lotto (price_fingerprint SOLO per l'asset del lotto, non per tutto il portafoglio —
# più stretto del price_fingerprint del blob Engine, che è per l'intero scope)
lot_history_key = (lot_id, asset_id, broker_id, str(date_to), tx_fingerprint_single_asset, price_fingerprint_single_asset)
```

**Perché `tx_fingerprint`/`price_fingerprint` più stretti (per singolo asset, non per scope)**: il
`tx_fingerprint` del blob Engine (§3.1) cambia ad ogni modifica di QUALSIASI transazione dello scope —
efficiente per l'Engine (che comunque deve leggere tutto lo scope per NAV/allocazioni), ma **eccessivo** per
"history di un lotto di UN asset": modificare una transazione di un asset diverso invaliderebbe inutilmente la
cache di questo lotto. Un fingerprint a grana più fine (`select(...).where(Transaction.asset_id == asset_id)`,
sullo stile già usato in `compute_wac_iterative()`, `portfolio_service.py:117-123`) evita invalidazioni
incrociate tra asset non correlati.

**Frontend**: riusare il pattern `TimeSeriesStore` esistente (§4) per la history del lotto selezionato — è
**esattamente** il caso d'uso per cui `TimeSeriesStore` è stato progettato (serie temporale con gap-detection,
delta-fetch). Per la lista lotti/Gantt (bounded, un array per asset), il pattern `entityStore`-like è più
adatto (bounded list, invalidazione per id) — ma probabilmente sufficiente anche uno `$state` locale al
componente `FIFOLotsPanel.svelte`, dato che oggi già funziona così senza cache e il volume dati è piccolo
(decine di lotti, non migliaia).

---

## 11. Invalidazione cache dopo mutazioni

| Mutazione | Cache backend da invalidare | Meccanismo | Già gestito oggi? |
|---|---|---|---|
| Crea/modifica/elimina transazione (qualsiasi tipo) | `_portfolio_blob_cache`, `_portfolio_l2_cache`, `_wac_cache`, **nuove** `_lots_gantt_cache`/`_lot_history_cache` | `tx_fingerprint` cambia automaticamente (usa `updated_at`) → miss naturale, nessuna azione esplicita richiesta | Sì per i primi 3 (by design); le nuove andrebbero collegate allo stesso meccanismo di fingerprint |
| Crea/modifica coppia TRANSFER | Stesse cache sopra + eventuale ricalcolo di `cost_basis_override` sulla gamba destinazione (meccanismo "snapshot" già esistente in `_compute_wac_for_auto_items()`, report 2 §7) | Idem (fingerprint) | Sì, meccanismo di fingerprint esistente coprirebbe anche le nuove cache senza modifiche |
| ADJUSTMENT | Idem | Idem | Sì |
| Aggiornamento prezzi (scheduler o manuale) | `_portfolio_blob_cache` (`price_fingerprint`), **nuova** `_lot_history_cache` (fingerprint per singolo asset) | `price_fingerprint` usa `MAX(fetched_at)` — cambia automaticamente ad ogni scrittura | Sì per il blob; la nuova cache history-lotto andrebbe agganciata allo stesso pattern ma filtrato per asset |
| Aggiornamento FX | **Nessuna cache attuale ha un `fx_fingerprint` esplicito** — l'Engine ricalcola comunque ad ogni miss di `tx_fingerprint`/`price_fingerprint`, ma un cambiamento SOLO di un tasso FX (senza nuove transazioni o prezzi asset) **non invaliderebbe né il blob né l'L2 cache** | — | **No — gap esistente, non introdotto da questo report**: verificare se `convert_bulk`/le tabelle FX hanno un proprio meccanismo di cache-busting collegato; se non lo hanno, è un bug di staleness preesistente da segnalare separatamente (fuori scope di questo report, per rispetto della direttiva di non correggere bug non richiesti in task non correlati) |
| Modifica `share_percentage` (BrokerUserAccess) | Tutte le cache che includono quel `user_id`/`broker_id` nello scope | **Nessun fingerprint dedicato oggi** — `share_percentage` non entra in `tx_fingerprint` né in `price_fingerprint` | **No — gap esistente**: una modifica di comproprietà cambierebbe silenziosamente i numeri visualizzati SENZA invalidare blob/L2/WAC cache già popolate per quell'utente, fino al naturale scadere del TTL (max 24h per il blob). Anche questo è un gap preesistente, segnalato qui per completezza ma non nello scope di correzione di questo report. |

> **Due gap di invalidazione preesistenti segnalati, non corretti**: FX rate changes e `share_percentage`
> changes non fanno parte di alcun fingerprint di cache oggi. Li segnalo qui per completezza dell'analisi
> richiesta al punto 10 del task, ma **non li ho corretti** perché sono bug preesistenti scoperti durante
> l'analisi, non modifiche richieste — coerente con la direttiva di riportare bug scoperti fuori scope invece
> di sistemarli silenziosamente.

---

## 12. Codice duplicato e rischi di divergenza

Tre percorsi di calcolo "WAC-simile" coesistono, **nessuno chiama gli altri**:

```
┌─────────────────────────────┬──────────────────────────────┬─────────────────────────────────┐
│ Percorso                     │ Usato da                      │ Caratteristiche                  │
├─────────────────────────────┼──────────────────────────────┼─────────────────────────────────┤
│ (a) Inline WAC dell'Engine   │ get_summary/get_history/       │ Pool aggregato, un solo passaggio│
│     (portfolio_engine.py)    │ get_report/get_positions_      │ per tutte le posizioni, calcolo  │
│                               │ contribution (via engine)      │ dentro DailyStateBuilder         │
├─────────────────────────────┼──────────────────────────────┼─────────────────────────────────┤
│ (b) wac_utils.compute_wac_   │ POST /portfolio/wac,            │ Iterativo ma ESTERNO all'Engine, │
│     iterative() + _from_     │ get_asset_history()             │ chiamato N volte (una per punto  │
│     txlist()                 │                                 │ prezzo in get_asset_history!)    │
├─────────────────────────────┼──────────────────────────────┼─────────────────────────────────┤
│ (c) fifo_utils.              │ get_lots()                      │ Granularità di lotto reale, ma   │
│     calculate_fifo_lots()    │                                 │ BUY/SELL-only, nessuna cache     │
└─────────────────────────────┴──────────────────────────────┴─────────────────────────────────┘
```

**Rischio concreto già osservato in questa serie di report**: il bug del fallback "auto" per ADJUSTMENT
positivi che rappresentano uno split (documentato in `fifo-segment-model-analysis.md`) esiste **in entrambi**
(a) e (b) **indipendentemente** — confermato in questo report leggendo `_buy_unit_cost()`
(`portfolio_engine.py:1207-1250`, usato dal percorso (a)) che ha la stessa logica di fallback già trovata in
`wac_utils.compute_wac_from_txlist()` (percorso (b), report 3). **Se in futuro si decide di correggere questo
bug, va corretto in (a) E in (b) separatamente — non c'è un solo punto di verità.** Il percorso (c) non è
neanche esposto al problema (non gestisce TRANSFER/ADJUSTMENT per via del filtro `_HOLDING_TYPES`), il che
crea una divergenza ulteriore: se un giorno (c) viene estesa a gestire ADJUSTMENT, dovrà scegliere UNA delle
interpretazioni già divergenti tra (a) e (b), oppure introdurne una terza.

**Rischio di performance specifico**: (b) applicato in loop da `get_asset_history()` è l'unico dei tre percorsi
che **non beneficia mai** dell'ottimizzazione "inline WAC" (introdotta specificamente per eliminare gli N×M
round-trip DB — concetto `inline-wac-computation` nel wiki). `get_asset_history()` è rimasto sull'architettura
pre-refactor, probabilmente perché nessuno l'ha aggiornato quando l'Engine è stato introdotto (Phase 09 M2,
commit `39106380`) — è un caso di **debito tecnico silenzioso**, non di feature nuova mancante.

---

## 13. Raccomandazione finale

### 13.1 Raccomandazione

**Non estendere `DailyStateBuilder`/`DailyPositionState` per la granularità di lotto (opzione A).** Il rischio
di regressione su un componente già centrale, testato (20 unit test) e recentemente stabilizzato (3 refactor
maggiori secondo la cronologia wiki: M1 iniziale, M2 3-pool/inline-WAC, M2 holdings/performance) supera il
beneficio di riuso. È la stessa cautela già raccomandata nei report precedenti per il codice FIFO/WAC esistente.

**Costruire un nuovo `FifoLotEngine` puro (opzione B), con drill-down lazy per singolo lotto (opzione E) come
meccanismo per la history.** Motivazioni:
- Isolamento totale dal codice NAV/MWRR/3-pool già fragile — zero rischio di regressione sull'esistente.
- Naturalmente compatibile con il modello a segmenti già proposto e validato in `fifo-segment-model-analysis.md`
  (incluso il supporto a segmenti short, che l'attuale pool WAC non può rappresentare correttamente).
- Il pattern "lazy per lotto selezionato" è già presente e maturo lato frontend (`TimeSeriesStore` con
  gap-detection) — non richiede innovazione architetturale, solo applicazione del pattern esistente a un nuovo
  dominio dati.
- Non introduce nuove dimensioni di cache-miss per range (§7): il nuovo motore erediterebbe lo stesso pattern
  "calcola sempre dall'inception" che già oggi coesiste bene con il blob cache dell'Engine.

**Prima di costruire qualcosa di nuovo**, correggere il debito tecnico silenzioso già identificato in questo
report che altrimenti si propagherebbe al nuovo motore per imitazione:
1. `get_asset_history()` non deve essere usato come modello — va esso stesso ottimizzato (o sostituito) prima,
   altrimenti il nuovo `FifoLotEngine` rischia di replicarne il pattern N-query-per-punto.
2. Il filtro `_HOLDING_TYPES`/`_QTY_TYPES` (BUY/SELL-only) deve essere risolto **nel nuovo motore fin da subito**
   (include TRANSFER e ADJUSTMENT nativamente), non ereditato come limitazione "provvisoria".

### 13.2 Piano incrementale (4 fasi, nessuna in questo task)

```
Fase 1 — Fondamenta pure (no DB, no cache, no API)
  └─ fifo_lot_engine.py: stessa forma di fifo_utils.py ma con SEGMENTI (report 3), non solo BUY/SELL
  └─ Input: ClassifiedTransaction[] (riuso del tipo esistente dell'Engine, nessuna nuova classificazione)
  └─ Output: LotSegment[] (nuova dataclass interna, non ancora un DTO API)
  └─ Test: casi sintetici per ogni invariante (§13.3), incluso il caso BTC del report 1/2

Fase 2 — Integrazione dati, ancora nessuna cache
  └─ Collegare a PortfolioService come nuovo metodo get_lot_segments() (analogo a get_lots() esistente,
     stesso pattern di accesso ai dati, ma output = segmenti non lotti aggregati per broker)
  └─ Sostituire get_lots() internamente (o farlo convivere finché il frontend non migra)

Fase 3 — DTO/API (§9) + cache dedicata (§10)
  └─ LotsGanttResponse, LotHistoryResponse, i due endpoint proposti
  └─ _lots_gantt_cache, _lot_history_cache — MAI riusare _wac_cache/_portfolio_blob_cache

Fase 4 — Frontend
  └─ FIFOLotsPanel.svelte esteso con vista Gantt (nuovo componente, es. LotsGanttChart.svelte)
  └─ Drill-down: riuso di TimeSeriesStore per la history del lotto selezionato
```

### 13.3 Invarianti da preservare (nuovo motore)

1. `Σ(remaining_quantity dei lotti aperti) == quantità corrente della posizione secondo l'Engine esistente`
   — invariante di riconciliazione tra i due motori, da testare esplicitamente (nessun test attuale la verifica,
   perché oggi `get_lots()` e l'Engine non vengono mai confrontati tra loro).
2. Nessun lotto/segmento deve fondersi con un altro a meno di identico `(asset_id, origin_date,
   origin_unit_price, broker_id)` — coerente con l'ipotesi 1 di `fifo-segment-model-analysis.md`.
3. Un TRANSFER deve **preservare** `origin_date`/`origin_unit_price` del segmento trasferito — non crearne uno
   nuovo con la data del transfer (questo è già oggi vero per `_buy_unit_cost()` quando c'è
   `cost_basis_override`, deve restare vero nel nuovo motore).
4. La somma dei `custody_intervals` di un segmento non deve avere sovrapposizioni né buchi tra l'apertura e
   l'eventuale chiusura/vendita completa.

### 13.4 Test necessari (oltre alle unità pure)

- Test di **non-regressione numerica**: per un dataset esistente (es. `db populate`), il totale
  `total_realized_pnl` e `total_unrealized_quantity` del nuovo `FifoLotEngine` deve coincidere con quello
  prodotto oggi da `get_lots()` per gli stessi identici input (stesso filtro di tipo, se lasciato BUY/SELL-only
  in una prima fase) — per isolare i bug "nuovi" da eventuali differenze di risultato attese (dovute
  all'inclusione di TRANSFER/ADJUSTMENT).
- Test di cache: fingerprint a grana singolo-asset (§10) non deve invalidarsi per modifiche a transazioni di
  ALTRI asset dello stesso scope (oggi non testabile perché la funzionalità non esiste — da scrivere insieme
  all'implementazione).
- Test di performance: `get_lot_segments()`/`LotHistoryResponse` per un asset con storia lunga (multi-anno,
  multi-broker) non deve degradare a O(N_price_points) come `get_asset_history()` fa oggi (§3.4, §12) — un test
  di conteggio query DB (già un pattern esistente nel repository per altri servizi, da verificare come si chiama
  esattamente prima di riusarlo) sarebbe il modo più diretto per prevenire la regressione.

---

## Domande aperte (non risolte in questo report, per decisione futura)

1. **Attribuzione di dividendi/interessi a un lotto specifico** (§9.2, `cumulative_proceeds`): serve una regola
   di prodotto esplicita (pro-rata per quantità posseduta quel giorno? Solo al lotto più vecchio? Nessuna
   attribuzione, mostrare solo a livello posizione?) — non decidibile solo dal codice esistente.
2. **Gap di invalidazione FX e `share_percentage`** (§11): sono bug preesistenti di staleness, non introdotti
   da questo report. Vanno probabilmente corretti indipendentemente dalla feature Gantt/lotti, con priorità da
   discutere separatamente.
3. **`lot_id` stabile attraverso trasferimenti a catena**: il report 3 (`fifo-segment-model-analysis.md`)
   discute il naming ma non fissa definitivamente lo schema di id per segmenti forkati da transfer parziali
   multipli — necessario prima della Fase 3 di questo piano.
4. **Multi-worker in produzione** (§3.5): se LibreFolio prevede di scalare a `--workers > 1` in futuro, tutta
   la strategia di cache in-process (esistente E proposta in questo report) andrebbe rivista con uno store
   condiviso — non è un problema di oggi, ma condiziona quanto "investire" nelle nuove cache proposte al §10 se
   questo cambiamento è già pianificato a breve termine.
