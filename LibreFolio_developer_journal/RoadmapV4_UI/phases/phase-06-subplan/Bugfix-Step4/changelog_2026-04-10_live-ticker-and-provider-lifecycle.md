# Changelog 2026-04-10 — Live Ticker, Provider Lifecycle, Asset Events & Bugfixes

> 25+ files changed, ~1200 insertions(+), ~50 deletions(-)

---

## Richieste dell'utente (4 iterazioni)

### 1. Refactor lifespan shutdown dei provider
Rimuovere il `try/except` hardcoded in `main.py` che importava `shutdown_live_feeds` da JustETF. Creare un meccanismo generico: metodo `shutdown()` nelle ABC dei provider, chiamato dal registry su tutti i provider registrati.

### 2. Endpoint bulk current-price
`POST /api/v1/assets/prices/current` — accetta `List[int]` (body JSON diretto), restituisce il prezzo corrente di ciascun asset. Provider-first con fallback DB.

### 3. LiveTicker nel frontend
- **NON** nell'header globale (causava crash di navigazione)
- **SÌ** nella **dashboard** come sezione "Live Prices" con tutti gli asset
- **SÌ** nella **asset detail page** accanto al nome dell'asset (singolo badge)
- **SÌ** nelle **asset card** (lista asset) come prezzo live inline (nessun badge wrapper)
- **Niente** `CurrencySearchSelect` (rimosso)
- **Visibile anche su mobile**

### 4. Correzioni codice (iterazione 2)
- Import in cima ai file, non lazy nelle funzioni
- `provider_registry.py`: niente `hasattr` (il metodo è nella ABC, chiamarlo direttamente)
- `prices.py`: rimossa `FACurrentPriceRequest` (endpoint accetta `List[int]`), `FACurrentPriceResponse` estende `BaseBulkResponse`

### 5. Miglioramenti LiveTicker (iterazione 4)
- **Non-blocking**: mostra `--` placeholder finché i prezzi non sono disponibili, fetch in background fire-and-forget
- **Niente percentuale**: rimosso il delta %, mostrato solo il prezzo corrente
- **AssetIcon**: aggiunta icona dell'asset (custom o di tipo) accanto al nome in ogni badge
- **Badge morbidi + colori dinamici**: `rounded-full`, colori che cambiano in base al movimento prezzo (verde=su, rosso=giù, neutro=invariato)
- **Prezzo live nelle card**: `AssetCard` accetta prop `livePrice` per display inline (testo `Live: X.XX` senza badge wrapper)
- **Bulk fetch nella lista asset**: `fetchLivePrices()` fire-and-forget dopo `loadAssets()` nella pagina asset list

### 6. Aggiornamento documentazione MkDocs EN
- Registry Pattern: aggiunta sezione Provider Lifecycle (Shutdown)
- API Overview: documentato endpoint `POST /assets/prices/current`
- Asset Events: documentati eventi DIVIDEND/SPLIT generati da JustETF e Yahoo Finance
- JustETF Provider: aggiunta sezione Live Quote Streaming, rimossa limitazione "No events yet"
- Yahoo Finance Provider: aggiunta sezione Asset Events, rimossa limitazione "No events yet"
- Asset Architecture: aggiunto Current Price al AssetSourceManager
- Nuovo file `live-ticker.md`: documentazione completa del componente LiveTicker
- Frontend Components index: aggiunto LiveTicker alla tabella componenti
- `mkdocs.yml`: aggiunta voce nav per Live Ticker

---

## Modifiche effettuate — Backend

### Provider Lifecycle (shutdown generico)

| File | Modifica |
|------|----------|
| `backend/app/services/asset_source.py` | Aggiunto `shutdown()` no-op alla ABC `AssetSourceProvider` |
| `backend/app/services/fx.py` | Aggiunto `shutdown()` no-op alla ABC `FXRateProvider` |
| `backend/app/services/brim_provider.py` | Aggiunto `shutdown()` no-op alla ABC `BRIMProvider` |
| `backend/app/services/provider_registry.py` | Aggiunto `shutdown_all_providers()` classmethod a `AbstractProviderRegistry` — itera su tutti i provider, istanzia e chiama `shutdown()` direttamente (nessun `hasattr`) |
| `backend/app/main.py` | Import di `AssetProviderRegistry, FXProviderRegistry, BRIMProviderRegistry` spostato in cima. Lifespan shutdown: rimosso blocco hardcoded `try/except/import shutdown_live_feeds`, sostituito con 3 chiamate `*.shutdown_all_providers()` |

### JustETF Provider — Live Quote WebSocket + Dividend Events

| File | Modifica |
|------|----------|
| `backend/app/services/asset_source_providers/justetf.py` | **Riscrittura significativa (+155 righe)**:<br>• Rimosso `get_gettex_quote` (vecchia API), sostituito con `load_live_quote` + `iterate_live_quote` dal pacchetto `justetf-scraping`<br>• Aggiunto sistema **Live Quote Streaming** con thread persistenti per WebSocket: `_live_quote_store`, `_live_quote_threads`, `_live_quote_stop`, `_live_quote_lock`<br>• `_live_quote_worker()`: thread daemon con reconnect + exponential backoff<br>• `_ensure_live_feed()`: avvia feed per un ISIN se non già attivo<br>• `shutdown_live_feeds()`: ferma tutti i thread, chiamata da `JustETFProvider.shutdown()`<br>• `get_current_value()`: strategia fast-path (1. store istantaneo → 2. one-shot fallback → 3. avvia feed persistente)<br>• `get_history_value()`: parsing **DIVIDEND events** dalla colonna `dividends` del DataFrame di `load_chart()`<br>• Rimossa `_gettex_cache` (30s TTL), il live store la sostituisce |

### Yahoo Finance Provider — Dividend & Split Events

| File | Modifica |
|------|----------|
| `backend/app/services/asset_source_providers/yahoo_finance.py` | **+51 righe**:<br>• Importati `FAAssetEventPoint`, `CurrencyAmount`<br>• `get_history_value()`: rimosso TODO, implementato parsing di **DIVIDEND events** da `ticker.dividends` (Series) con filtro date range<br>• Implementato parsing di **SPLIT events** da `ticker.splits` con ratio ≠ 0 e ≠ 1<br>• Entrambi i tipi di evento restituiti in `FAHistoricalData.events` |

### Bulk Current-Price Endpoint

| File | Modifica |
|------|----------|
| `backend/app/schemas/prices.py` | Aggiunti `FACurrentPriceItem` (BaseModel con `asset_id, value, currency, as_of_date, source, error`) e `FACurrentPriceResponse` (estende `BaseBulkResponse[FACurrentPriceItem]`). Nessun `FACurrentPriceRequest` (l'endpoint accetta `List[int]` direttamente) |
| `backend/app/services/asset_source.py` | Aggiunto `get_current_prices_bulk()` a `AssetSourceManager` (+122 righe): fetch parallelo via provider (semaphore=5, timeout=10s), fallback a ultimo `PriceHistory` row dal DB. Read-only, nessuna scrittura |
| `backend/app/api/v1/assets.py` | Aggiunto endpoint `POST /prices/current` — accetta `List[int]`, chiama `get_current_prices_bulk()`, restituisce `FACurrentPriceResponse` |

---

## Modifiche effettuate — Frontend

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/layout/LiveTicker.svelte` | **Nuovo componente** (refactored): props `assetIds?`, `pollInterval?`, `maxItems?`. **Non-blocking**: mostra `--` come placeholder finché i prezzi non arrivano, fetch fire-and-forget. **No percentuale delta**. **AssetIcon** integrato in ogni badge. **Badge `rounded-full`** con colori dinamici: verde (prezzo su), rosso (giù), grigio (neutro). CSS `transition-colors duration-300` per animazione fluida |
| `frontend/src/lib/components/assets/AssetCard.svelte` | Aggiunta prop opzionale `livePrice: number \| null`. Se fornita, mostra inline "Live: X.XX" in verde accanto al prezzo storico nella card (senza badge wrapper) |
| `frontend/src/routes/(app)/assets/+page.svelte` | Aggiunto import `axiosInstance`, stato `livePriceMap`, funzione `fetchLivePrices()` (bulk fetch fire-and-forget in `onMount`). Passata `livePrice={livePriceMap.get(asset.id)}` a ogni `AssetCard` nella grid view |
| `frontend/src/lib/components/layout/Header.svelte` | **Ripristinato** — nessun LiveTicker nell'header globale |
| `frontend/src/lib/components/layout/index.ts` | Esportato `LiveTicker` dal modulo layout |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | Aggiunta sezione "Live Prices" con `<LiveTicker />` (tutti gli asset) tra Quick Stats e Quick Actions |
| `frontend/src/routes/(app)/assets/[id]/+page.svelte` | Aggiunto `<LiveTicker assetIds={[assetInfo.id]} maxItems={1} />` accanto al nome asset nell'header della detail page |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | Aggiunte chiavi `ticker.noAssets`, `ticker.loading`, `ticker.errorFetching`, `ticker.livePrices` |
| `frontend/src/lib/api/generated.ts` | Auto-rigenerato: aggiunto tipo `FACurrentPriceResponse`, `FACurrentPriceItem`, endpoint `POST /prices/current` |
| `frontend/src/lib/api/openapi.json` | Auto-rigenerato: schema OpenAPI con nuovo endpoint e schemi |

---

## Modifiche effettuate — Journal / Docs

| File | Modifica |
|------|----------|
| `LibreFolio_developer_journal/RoadMapV1/grep-cmd.txt` | Aggiunto nuovo comando grep con context lines (±3 righe attorno ai TODO) |
| `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase06Step1-to-4PartA-ConsolidationTestDockerDocs.prompt.md` | Rinominato → `phases/phase-06-subplan/Bugfix-Step4/` |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step4/plan-phase06Step1-to-4PartA-DocsAudit.md` | Rinominato da `plan-phase06Step4PartB-DocsAudit.md` → posizione in sotto-cartella |
| `LibreFolio_developer_journal/changelog_2026-04-10_live-ticker-and-provider-lifecycle.md` | Questo file |

## Modifiche effettuate — Documentazione MkDocs EN

| File | Modifica |
|------|----------|
| `mkdocs_src/docs/developer/architecture/patterns/registry_pattern.md` | Aggiunta sezione "Provider Lifecycle — Shutdown" con spiegazione di `shutdown()` nelle ABC, `shutdown_all_providers()` nel registry, esempio JustETF |
| `mkdocs_src/docs/developer/api/overview.md` | Aggiunto endpoint `POST /api/v1/assets/prices/current` con schema request/response e strategia di risoluzione |
| `mkdocs_src/docs/developer/backend/assets/events.md` | Aggiunte sezioni per eventi generati da Yahoo Finance (DIVIDEND + SPLIT) e JustETF (DIVIDEND da chart data) |
| `mkdocs_src/docs/developer/backend/assets/provider_justetf.md` | Aggiunta sezione "Live Quote Streaming" (WebSocket, daemon threads, store). Aggiunta sezione "Asset Events". Rimossa limitazione "No events yet" |
| `mkdocs_src/docs/developer/backend/assets/provider_yahoo_finance.md` | Aggiunta sezione "Asset Events" (DIVIDEND + SPLIT). Rimossa limitazione "No events yet" |
| `mkdocs_src/docs/developer/backend/assets/architecture.md` | Aggiunto "Current Price" all'elenco operazioni di `AssetSourceManager` con link a LiveTicker docs |
| `mkdocs_src/docs/developer/frontend/components/live-ticker.md` | **Nuovo file**: documentazione completa del componente LiveTicker (props, architettura, sequence diagram, visual behaviour, related links) |
| `mkdocs_src/docs/developer/frontend/components/index.md` | Aggiunto LiveTicker alla tabella dei componenti |
| `mkdocs_src/docs/developer/frontend/index.md` | Aggiunto LiveTicker alla lista componenti layout |
| `mkdocs_src/mkdocs.yml` | Aggiunta voce nav `Live Ticker: developer/frontend/components/live-ticker.md` sotto Frontend > Components |

---

## Architettura

### Provider Lifecycle (shutdown)
```
ABC (no-op shutdown)          Registry                    main.py lifespan
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ AssetSourceProv. │    │ AbstractProviderReg.  │    │ yield               │
│   shutdown()     │◄───│ shutdown_all_provs()  │◄───│ AssetProvReg.shut() │
│   (pass)         │    │   for each provider:  │    │ FXProvReg.shut()    │
├─────────────────┤    │     instance.shutdown()│    │ BRIMProvReg.shut()  │
│ JustETFProvider  │    └──────────────────────┘    └─────────────────────┘
│   shutdown()     │
│   → shutdown_    │
│     live_feeds() │
└─────────────────┘
```

### JustETF Live Quote Streaming
```
onMount (first request)              Background (persistent)
┌──────────────────┐           ┌───────────────────────────┐
│ get_current_value │           │ _live_quote_worker(isin)  │
│  1. check store   │──miss──► │  iterate_live_quote(isin) │
│  2. one-shot fetch │          │  → updates store on each  │
│  3. ensure_feed() ─┘          │    quote received          │
│  ◄── return price  │          │  reconnect on error       │
└──────────────────┘           │  stop on _live_quote_stop  │
                                └───────────────────────────┘
```

### Bulk Current-Price Flow
```
Frontend                    API                         Service
POST [1,2,3] ──────► /prices/current ──────► get_current_prices_bulk()
                                                │
                                                ├─ Batch query: Asset + Assignment
                                                ├─ Parallel: provider.get_current_value()
                                                │            (semaphore=5, timeout=10s)
                                                ├─ Fallback: last PriceHistory row from DB
                                                │
                                         ◄──────┤ FACurrentPriceResponse
                                                  { results: [...], success_count: N }
```

### LiveTicker Component Usage
```
Dashboard (+page.svelte)           Asset Detail ([id]/+page.svelte)
┌──────────────────────┐           ┌───────────────────────────────┐
│ <LiveTicker />       │           │ <h2>Apple Inc.</h2>           │
│   → loads ALL assets │           │ <LiveTicker                   │
│   → polls every 30s  │           │   assetIds={[42]}             │
│   → badge con icon + │           │   maxItems={1} />             │
│     prezzo + colori  │           └───────────────────────────────┘
│     dinamici         │
└──────────────────────┘           Asset Cards (+page.svelte)
                                    ┌───────────────────────────────┐
                                    │ <AssetCard                    │
                                    │   livePrice={livePriceMap     │
                                    │     .get(id)} />              │
                                    │   → inline "Live: X.XX"       │
                                    │   → no badge wrapper          │
                                    └───────────────────────────────┘
```

---

## TODO smarcati in questo commit

| File | TODO rimosso | Implementazione |
|------|-------------|-----------------|
| `justetf.py:262` | `TODO [AssetEvent]: Scrape distribution events from justETF profile page` | Parsing colonna `dividends` da `load_chart()` DataFrame → `FAAssetEventPoint(type=DIVIDEND)` |
| `yahoo_finance.py:292` | `TODO [AssetEvent]: Fetch dividend events from Yahoo Finance API` | Parsing `ticker.dividends` + `ticker.splits` → `FAAssetEventPoint(type=DIVIDEND/SPLIT)` |

## TODO rimasti dal grep (analizzati, non smarcabili ora)

| File | TODO | Motivo |
|------|------|--------|
| `schemas/transactions.py:516` | Aggiornare icone TX types | Serve artwork/design |
| `schemas/fx.py:64` | Deprecare `base_currency` in favore di `base_currencies` | Richiede migrazione frontend+API |
| `api/v1/utilities.py:37` | Test multilingua per normalizzazione paesi | Task di testing lungo |
| `test_fx_providers.py:27` | pytest-xdist per parallelizzare test | Decisione architetturale futura |
| `test_asset_providers.py:126` | `expected_symbol` nella test list | Miglioramento minore test |
