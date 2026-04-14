# Plan: Parte C — Currency Conversion Backend + Frontend

La detail page asset ha già `CurrencySearchSelect` per `displayCurrency` e un warning FX, ma la conversione è puramente cosmetica — i prezzi non vengono convertiti. L'obiettivo è rendere funzionale la conversione: il backend converte via FX rates, il frontend mostra staleness combinata (prezzo + FX), e il live ticker rispetta la valuta selezionata.

---

## Contesto — Gap verificati nel codice

| Cosa | Dove | Stato |
|------|------|-------|
| `FAPricePoint` | `schemas/prices.py:51` | NO `original_currency` |
| `FAPriceQueryItem` | `schemas/prices.py:323` | NO `target_currency` |
| `FAPriceQueryResult` | `schemas/prices.py:338` | NO `errors[]` per warning FX |
| `get_prices_bulk()` | `asset_source.py:1586` | Nessuna conversione FX |
| `loadChartData()` | `assets/[id]/+page.svelte:441` | Non passa `target_currency` |
| `LineDataPoint` | `PriceChartFull.svelte` | `staleDays` solo prezzo, NO `fxStaleDays` |
| Asset LIST `oncreated` | `assets/+page.svelte:1152` | ❌ Solo `loadAssets()`, nessun sync |
| FX detail provider save | `fx/[pair]/+page.svelte:658` | ❌ Solo `loadProviders()`, nessun sync |
| Asset DETAIL `onupdated` | `assets/[id]/+page.svelte:678` | ✅ Fa `handleSync()` — OK |

---

## ✅ C1. Backend — AssetBackwardFillInfo + FAPricePoint esteso

**File:** `backend/app/schemas/prices.py`

- Creare `AssetBackwardFillInfo(BackwardFillInfo)` con campi aggiuntivi:
  - `fx_rate_date: Optional[date] = None` — data effettiva del tasso FX usato
  - `fx_days_back: Optional[int] = None` — giorni indietro del tasso FX
- Cambiare `FAPricePoint.backward_fill_info` da `Optional[BackwardFillInfo]` a `Optional[AssetBackwardFillInfo]`
- Aggiungere `original_currency: Optional[str] = None` a `FAPricePoint`
- Aggiungere `errors: List[str] = Field(default_factory=list)` a `FAPriceQueryResult`
- Aggiungere `target_currency: Optional[str] = None` a `FAPriceQueryItem` con validator
- **Backward-compatible:** i campi FX sono `Optional`, prezzi non convertiti funzionano identicamente.

**Done (12/04/2026):** Schema creati + `api sync` per rigenerare client TypeScript.

**⚠️ Breaking change (no backward compat):** `_build_backward_filled_series` ora usa `AssetBackwardFillInfo` al posto di `BackwardFillInfo`. Il vecchio tipo non è più usato in asset_source.py — rimosso l'import inutilizzato.

---

## ✅ C2. Backend — target_currency in query + conversione

**File:** `services/asset_source.py`

- In `get_prices_bulk()`, dopo la serie backward-filled, se `target_currency` presente e ≠ `point.currency`:
  - Raccogliere conversioni: `[(Currency(code=p.currency, amount=p.close), target, p.date), ...]`
  - Chiamare `convert_bulk(session, conversions, raise_on_error=False)` in batch
  - **Success:** sostituire OHLC (scaling proporzionale dal fattore close), impostare `original_currency`, `currency = target`, popolare `fx_rate_date`/`fx_days_back`
  - **Failure** (coppia FX mancante): prezzo nativo inalterato + warning in `result.errors`

**Done (12/04/2026):**
- Conversione implementata con FX factor scaling (close convertito, OHLC scalato proporzionalmente)
- `AssetBackwardFillInfo` composta: preserva price staleness + aggiunge FX staleness
- Import `convert_bulk` in cima al file (no import inline)
- **5 test backend** aggiunti in `test_asset_source.py` (Test 15-19):
  - `test_get_prices_with_target_currency` — conversione USD→EUR con FX backward-fill
  - `test_get_prices_no_target_currency` — nessuna conversione, valori nativi invariati
  - `test_get_prices_same_target_currency` — target = native = no-op
  - `test_get_prices_missing_fx_pair` — coppia mancante → prezzo nativo + errors[]
  - `test_query_result_errors_field` — errors è lista vuota quando conversione OK
- **17/17 test passati** (14 preesistenti + 5 nuovi, zero regressioni)

---

## ✅ C3. Frontend — Chart + staleness combinata

**File:** `assets/[id]/+page.svelte` + `PriceChartFull.svelte` + `lineChartHelpers.ts`

- **3a:** `loadChartData()` → passare `target_currency: displayCurrency !== assetInfo.currency ? displayCurrency : undefined`
- **3b:** `$effect` che richiama `loadChartData()` quando `displayCurrency` cambia (ora NON lo fa)
- **3c:** Aggiungere `fxStaleDays?: number` a `LineDataPoint`, mappato da `backward_fill_info.fx_days_back`
- **3d:** Gradiente opacità = `max(staleDays, fxStaleDays ?? 0)` → dato "fresco" solo se ENTRAMBI sono freschi. `getStaleOpacity()` riceve il max, nessuna modifica alla funzione
- **3e:** Tooltip breakdown: `⚠ Price: N days old` + `⚠ FX rate: N days old` (entrambi solo se > 0). Riga `💱 Converted from USD` quando `original_currency` presente
- **3f:** Y-axis/summary: mostra `displayCurrency`, badge "converted from XXX"

**Done (12/04/2026):** 3a-3e implementati. `LineDataPoint` esteso con `fxStaleDays` e `originalCurrency`. Tooltip mostra separatamente stale price/FX + 💱 badge conversione.

---

## ✅ C4. Live Ticker conversion

**File:** `livePriceService.ts` + `assets/[id]/+page.svelte`

- Quando `displayCurrency !== assetInfo.currency`:
  - Dopo aver ottenuto il live price (provider, valuta nativa), fare `convert()` via `POST /fx/currencies/convert` passando la data del giorno
  - Mostrare prezzo convertito in `AssetPriceSummary`
  - Se conversione fallisce → prezzo nativo + icona warning

**Done (13/04/2026):**
- `_fetchLivePrice` ora accetta `nativeCurrency`, `targetCurrency`, `fxMissing` e converte via FX API quando currency diversa
- `$effect` per live price traccia anche `displayCurrency` (ri-fetch + reconvert al cambio valuta)
- `livePriceConversionFailed` state + prop passata a `AssetPriceSummary` per warning visivo (⚠ tooltip)
- 1 chiave i18n aggiunta (`assetDetail.livePriceConversionFailed`)

---

## ✅ C5. Comparison overlays conversion

**File:** `loadComparisonData.ts` + `assets/[id]/+page.svelte`

- Passare `target_currency` alla `query_prices_bulk` per gli asset di comparazione
- Se coppia FX non configurata per un asset di confronto:
  - Nella signal card: mostrare ⚠ triangle + pulsante "add FX pair" (stesso pattern di `AssetPriceSummary.fxConversionMissing`)
  - Dati della comparazione NON sovrapposti al chart (valute diverse = fuorviante)

**Done (13/04/2026):**
- `loadComparisonAssetsData` accetta `targetCurrency?` parametro, passa come `target_currency` nella query
- Se `result.errors` non vuoto: `_resolvedData = undefined` (no overlay) + `_conversionFailed = true`
- `ChartSignalsSection` mostra ⚠ warning con tooltip per signal con `_conversionFailed`
- 1 chiave i18n aggiunta (`chartSettings.conversionFailed`)

---

## ✅ C6. Auto-sync dopo save provider

- **Asset LIST** (`assets/+page.svelte`): `oncreated` ora riceve `assetId` dalla modal e trigga `handleSyncAsset()`. Firma cambiata da `() => void` a `(assetId: number) => void`.
- **FX detail** (`fx/[pair]/+page.svelte`): `handleProviderModalCreated` → dopo `loadProviders()`, chiama `handleSync()` per sincronizzare tassi.

**Done (12/04/2026):** AssetModal passa `assetId` in entrambi i percorsi oncreated (success e partial failure). Asset list auto-sync. FX detail auto-sync.

- **Asset LIST** (`assets/+page.svelte`): `oncreated` deve ricevere `assetId` dalla modal e triggare `POST /assets/prices/sync` per il nuovo asset. Cambiare firma `oncreated` da `() => void` a `(assetId: number) => void`
- **FX detail** (`fx/[pair]/+page.svelte`): `handleProviderModalCreated` → dopo `loadProviders()`, chiamare `handleSync()` per sincronizzare tassi con il nuovo provider

---

## ✅ C7. i18n + Polish

- ~20-25 chiavi i18n (EN/IT/FR/ES) via `./dev.py i18n add`
- `./dev.py api sync` per rigenerare client TypeScript
- Dark mode check, responsive wide/tablet/tabletS/mobile

**Done (13/04/2026):**
- 6 chiavi i18n aggiunte nelle sessioni C4-C12:
  - `assetDetail.livePriceConversionFailed` (4 lingue)
  - `chartSettings.conversionFailed` (4 lingue)
  - `measure.addMeasure` (4 lingue)
  - `assetDetail.dataAvailableFrom` (4 lingue)
  - `chart.tooltip.fxStale` (4 lingue) — tooltip FX staleness i18n
  - `chart.tooltip.convertedFrom` (4 lingue) — tooltip currency conversion i18n
- Dark mode verificato su tutti i componenti nuovi/modificati: banner data-available, warning FX, bottone Add Measure, tooltip conversion
- Responsive verificato: label "Add Measure" nascosta su mobile (solo icona `+`), touch gap 60px su mobile vs 30px desktop
- 2 stringhe hardcoded nel tooltip ECharts (`"FX rate: Xd old"`, `"Converted from XXX"`) sostituite con prop i18n (`fxStaleLabel`, `convertedFromLabel`)

---

## ✅ C8. Fix broken frontend → docs links

I link dal frontend alla documentazione MkDocs sono rotti perché la struttura docs è stata riorganizzata (pagine singole → cartelle dedicate). I percorsi sono usati tramite il componente `DocsLink` e la proprietà `static docsPath` nelle classi Signal.

### Mappatura link rotti → percorsi corretti

| Attuale (rotto) | Corretto | File sorgente |
|-----------------|----------|---------------|
| `financial-theory/technical-indicators/#ema` | `financial-theory/technical-analysis/indicators/ema/` | `EmaSignal.ts:31` |
| `financial-theory/technical-indicators/#macd` | `financial-theory/technical-analysis/indicators/macd/` | `MacdSignal.ts:39` |
| `financial-theory/technical-indicators/#rsi` | `financial-theory/technical-analysis/indicators/rsi/` | `RsiSignal.ts:27` |
| `financial-theory/technical-indicators/#bollinger-bands` | `financial-theory/technical-analysis/indicators/bollinger-bands/` | `BollingerSignal.ts:31` |
| `financial-theory/synthetic-benchmarks/#compound-growth` | `financial-theory/technical-analysis/synthetic-benchmarks/compound/` | `CompoundSignal.ts:28` + `ScheduledInvestmentEditor.svelte:918` |
| `financial-theory/synthetic-benchmarks/#linear-growth` | `financial-theory/technical-analysis/synthetic-benchmarks/linear/` | `LinearSignal.ts:22` |
| `financial-theory/synthetic-benchmarks/#sine-wave` | `financial-theory/technical-analysis/synthetic-benchmarks/sine-wave/` | `SineSignal.ts:30` |
| `financial-theory/asset-events/dividend` | `financial-theory/instruments/asset-events/dividend` | `AssetDataEditorSection.svelte:74` |
| `financial-theory/asset-events/interest` | `financial-theory/instruments/asset-events/interest` | `AssetDataEditorSection.svelte:75` |
| `financial-theory/asset-events/split` | `financial-theory/instruments/asset-events/split` | `AssetDataEditorSection.svelte:76` |
| `financial-theory/asset-events/price-adjustment` | `financial-theory/instruments/asset-events/price-adjustment` | `AssetDataEditorSection.svelte:77` |
| `financial-theory/asset-events/maturity-settlement` | `financial-theory/instruments/asset-events/maturity-settlement` | `AssetDataEditorSection.svelte:78` |
| `user/assets/detail/prices/` | `user/assets/detail/data-editor/` | `PriceDataImportModal.svelte:49` |

**Link verificati OK** (non rotti):
- `user/assets/detail/events/` ✅ — risolve a `events.en.md`
- `user/assets/providers/scheduled-investment/` ✅
- `developer/backend/fx/providers_list/` ✅

### Validazione sistematica (riusabile)

Aggiungere `./dev.py mkdocs check-links` (si affianca a build, serve, gallery, translate, etc.):

**Scope 1 — Frontend → docs:**
1. Estrae tutti i `docsPath` e `/mkdocs/` URL da `frontend/src/` (`grep -rn`)
2. Normalizza il percorso a file `.en.md` sul filesystem (`mkdocs_src/docs/`)
3. Verifica esistenza del file + eventuale anchor (`#section`)
4. Report: ✅ valido / ❌ rotto con suggerimento del percorso corretto

**Scope 2 — Backend `docs_url` → docs:**
1. Importa i provider registrati (FX + Asset) e legge la property `docs_url`
2. Verifica che il percorso punta a un file esistente

> **Nota:** `mkdocs build --strict` già valida i link interni tra file `.md`.
> Il nuovo comando copre i riferimenti **cross-boundary** (frontend/backend → docs)
> che MkDocs non può verificare.

**Done (12/04/2026):**
- 13 link frontend corretti (7 signal docsPath, 5 asset-events docsPath, 1 PriceDataImportModal)
- 4 anchor backend FX provider corretti (slug completo → attr_list anchor)
- `./dev.py mkdocs check-links` creato: scope 1 (frontend→docs, 18 link) + scope 2 (backend docs_url→docs, 8 link) = **26/26 ✅**
- JSDoc comments aggiornati in 9 file signal per coerenza
- Homepage link "Getting Started" corretto in 4 lingue (`getting-started/introduction/` → `user/getting-started/`)

---

## ✅ C9. Tooltip mobile: offset adattivo per device

**File:** `PriceChartFull.svelte` (linea ~701)

**Problema:** L'offset di 30px sopra il dito per il tooltip è insufficiente su mobile (il dito copre il tooltip), ma va bene con il mouse su desktop.

**Fix:**
- Rilevare `'ontouchstart' in window` o `navigator.maxTouchPoints > 0`
- Desktop (mouse): mantenere `gap = 30`
- Mobile (touch): aumentare a `gap = 60` (o più, da testare)
- Applicare sia in FX chart che in Asset chart (entrambi usano `PriceChartFull`)

**Done (13/04/2026):** Implementato con `isTouch` detection, gap = 60 su touch, 30 su desktop.

---

## ✅ C10. Mobile measure: touch fix + bottone "+Add Measure"

**File:** `PriceChartFull.svelte` + `MeasurePanel.svelte`

### 10a. Touch handling per measure creation

**Problema:** Su mobile, il secondo tap per completare una misura viene interpretato come movimento (drag) invece che come click. Il chart probabilmente non distingue `touchstart`+`touchend` (tap) da `touchmove` (pan).

**Fix:**
- Nella logica di creazione misura, per touch: usare `touchend` con soglia di movimento (< 10px dal `touchstart` = tap, altrimenti pan)
- Oppure entrare in "measure mode" che cattura il prossimo tap senza confonderlo col pan

### 10b. Bottone "+Add Measure" nel pannello misure

**Dove:** Nella sezione misure di `ChartSignalsSection.svelte` (sia FX che Asset)

- Aggiungere un bottone `+ Add Measure` (label che scompare su schermi stretti → solo icona `+`)
- Al click: crea automaticamente una misura con gli estremi dell'area attualmente visualizzata nel chart
- L'utente può poi editare gli estremi nel pannello misure
- Questo bypassa completamente il problema del double-tap su mobile
- **i18n:** chiave per label bottone (EN: "Add Measure", IT/FR/ES da tradurre) via `./dev.py i18n add`

**Done (13/04/2026):**
- 10a: Touch tap detection in `PriceChartFull.svelte`: `touchStartTime` tracking + short tap (< 400ms, < 10px) triggers `handlePointClick` in measure mode
- 10b: `addMeasureFromChartData()` method in MeasurePanel + bottone `+ Add Measure` (label hidden su mobile, solo icona `+`)
- 1 chiave i18n aggiunta (`measure.addMeasure`)

---

## ✅ C11. Banner "tail precede il primo dato disponibile"

**File:** `assets/[id]/+page.svelte` + `fx/[pair]/+page.svelte`

**Problema:** Se l'utente seleziona un range temporale che inizia prima del primo prezzo/tasso disponibile nel DB, non c'è nessuna indicazione visiva — il chart mostra semplicemente un'area vuota a sinistra.

**Fix:**
- Dopo il caricamento dei dati, confrontare la data di inizio range visualizzata con la data del primo punto dati
- Se `visibleStart < firstDataPoint.date`:
  - Mostrare un banner in cima alla pagina (stesso stile dei banner esistenti per FX warning)
  - Testo: "⚠ Data available from {firstDate} — earlier dates have no data"
  - Il banner scompare quando l'utente zooma/panna in un range che ha dati completi
- Implementare sia in **Asset detail** che in **FX detail**

**Done (13/04/2026):**
- `firstDataDate` e `rangeStartsBeforeData` derived in entrambe le pagine (asset + FX)
- Banner sky-blue con 📊 icona, testo "Data available from {date} — earlier dates have no data"
- Appare solo quando range start < first data point, scompare con loading/error
- 1 chiave i18n aggiunta (`assetDetail.dataAvailableFrom`)

---

## ✅ C12. Docker env conflict warning in dev.py

**File:** `dev.py` → funzioni `cmd_docker_up()`, `cmd_docker_rebuild()`

**Problema:** Le variabili d'ambiente del terminale (`PORT`, `TEST_PORT`) hanno priorità sulle variabili in `.env` per `docker compose`. Se l'utente ha `export PORT=3000` nel terminale ma `PORT=8000` nel `.env`, Docker usa 3000 silenziosamente.

**Fix — aggiungere check in `_check_env_file()`:**
1. Leggere il file `.env` e parsare le coppie `KEY=VALUE`
2. Per ogni variabile presente in `.env`, controllare se esiste anche nell'ambiente del terminale (`os.environ`)
3. Se il valore differisce:
   ```
   ⚠ Warning: env variable PORT is set in terminal (3000) but differs from .env (8000)
     Terminal value takes priority. To use .env value: unset PORT
   ```
4. NON bloccare l'avvio — solo warning informativo
5. Variabili da controllare: `PORT`, `TEST_PORT` (quelle usate in `docker-compose.yml`)

**Done (13/04/2026):** `_check_env_file()` estesa con parsing `.env` e confronto con `os.environ`. Warning informativo non-bloccante per PORT e TEST_PORT.

---

## ✅ C13. Rimozione Dead Code + Test Coverage Funzioni Core

Analisi coverage (12/04/2026) ha identificato 94 funzioni con `def` coperto ma body mai eseguito.
Di queste, 17 classificate HIGH priority. L'analisi call-graph ha rivelato che **7 sono dead code** e **10 sono codice vivo non testato**.

### ✅ C13a. Rimozione Dead Code

Eliminare le seguenti funzioni che non sono più chiamate da nessun punto del codebase:

#### `backend/app/services/asset_source.py`

| Linea | Funzione | Motivo |
|-------|----------|--------|
| ~~1474~~ | ~~`AssetSourceManager._fetch_provider_history()`~~ | ✅ Rimossa |
| ~~1518~~ | ~~`AssetSourceManager._fetch_db_price_map()`~~ | ✅ Rimossa |
| ~~3056~~ | ~~`AssetMetadataService.update_asset_metadata()`~~ | ✅ Rimossa |

#### `backend/app/services/broker_service.py`

| Linea | Funzione | Motivo |
|-------|----------|--------|
| ~~830~~ | ~~`BrokerService.add_access()`~~ | ✅ Rimossa |
| ~~903~~ | ~~`BrokerService.update_access()`~~ | ✅ Rimossa |
| ~~974~~ | ~~`BrokerService.remove_access()`~~ | ✅ Rimossa |
| ~~794~~ | ~~`BrokerService._count_owners()`~~ | ✅ Rimossa |
| ~~808~~ | ~~`BrokerService._sum_share_percentages()`~~ | ✅ Rimossa |

**Done (13/04/2026):** 8 funzioni rimosse, `./dev.py test services all` + `./dev.py test api broker-multiuser` — zero regressioni.

> **Nota:** `bulk_update_access()` (L1029) implementa la stessa logica in modo atomico.
> I singoli metodi erano il design originale pre-refactoring.

#### `backend/app/services/fx.py` — Dead Code rimosso (13/04/2026 — Round 2)

| Funzione | Motivo rimozione |
|----------|------------------|
| ~~`convert()`~~ | ✅ Wrapper di `convert_bulk()` single-item. Dipendenza inutile e scomoda: tutti i call site (test) migrati a `convert_bulk()` tramite helper locale `_convert_single()` nel file test. |
| ~~`sync_pair()`~~ | ✅ Sostituita da `sync_pairs_bulk()` che implementa la pipeline 3-fasi con parallelismo inter-provider. Zero call site residui. |
| ~~Costanti ECB legacy~~ | ✅ `ECB_BASE_URL`, `ECB_DATASET`, `ECB_FREQUENCY`, `ECB_REFERENCE_AREA`, `ECB_SERIES` — migrate al provider `ECBProvider`. Residuo pre-provider system. |
| ~~Import `DateRangeModel`~~ | ✅ Non usato in fx.py. |

**Test migrati:** 7 test in `test_fx_conversion.py` (Test 1-7) che usavano `convert()` ora usano `_convert_single()` (helper locale che wrappa `convert_bulk()` con `raise_on_error=True`). Zero cambiamenti alla semantica dei test.

**Bug fix collaterale:** Corrette 2 variabili non risolte (`total_fetched`, `total_changed`) nel branch single-step di `sync_pairs_bulk._process_route()` → sostituite con `len(computed_rates)` e `actual_changed`.

#### Dead code confermato da rimuovere in C14

| File | Funzione | Motivo |
|------|----------|--------|
| `backend/app/utils/finance_utils.py` | `validate_compound_frequency()` | Non chiamata da nessun punto. La validazione della frequency avviene in Pydantic validators. |

#### Dead code da valutare (non rimosso — fuori scope C13)

| File | Funzione | Stato | Note |
|------|----------|-------|------|
| `backend/app/utils/geo_utils.py` | `normalize_country_multilang()` | ❄️ Tenere | Design esplorativo pre-`normalize_country_to_iso3()`. Potrebbe servire per endpoint `/api/v1/utilities/normalize-country` user-facing. |
| `backend/app/services/static_uploads.py` | `get_upload_by_user()` | ❄️ Tenere | Predisposta per TODO "👥 Filtro Utente nella Files Page" (`TODO_FUTURI.md` L81-98). Controllo ownership per colonna "Uploaded by" + filtro. |
| `backend/app/services/global_settings_service.py` | `get_session_ttl_hours_sync()` | ⚠️ Dead | Fallback sync che legge solo i defaults hardcoded. Mai usata — l'init app usa sempre la versione async. |
| `backend/app/services/global_settings_service.py` | `get_max_upload_mb_sync()` | ⚠️ Dead | Stessa situazione di sopra. |
| `backend/app/services/global_settings_service.py` | `is_registration_enabled_sync()` | ⚠️ Dead | Stessa situazione di sopra. |
| `backend/app/services/global_settings_service.py` | `get_default_language()` | ⚠️ Dead | Backend-only: pensata per assegnare lingua default a nuovi utenti alla registrazione. Non ancora integrata. |
| `backend/app/services/global_settings_service.py` | `get_default_currency()` | ⚠️ Dead | Backend-only: stessa situazione. Frontend legge valuta da user settings, non da global settings. |
| `backend/app/utils/cache_utils.py` | `clear_cache()` | ❄️ Dead | Predisposta per futuro endpoint admin `/api/v1/system/caches`. Triviale da ricreare. |
| `backend/app/utils/cache_utils.py` | `clear_all_caches()` | ❄️ Dead | Idem. |
| `backend/app/utils/cache_utils.py` | `get_cache_stats()` | ❄️ Dead | Idem. |
| `backend/app/utils/cache_utils.py` | `list_caches()` | ❄️ Dead | Idem. |
| `backend/app/services/fx_providers/snb.py` | `if __name__` block | 🔌 Plugin test | Serve per test manuali del plugin. Fuori scope. |

**Procedura:**
1. `git diff` per confermare zero call site
2. Eliminare le funzioni
3. Eseguire `./dev.py test api all` e `./dev.py test services all` — zero regressioni attese
4. Commit: `chore: remove dead code (convert, sync_pair, ECB legacy constants)`

---

### ✅ C13b. Test per funzioni core vive ma scoperte

#### FX Core — `compute_chain_rate()` (priorità 1)

**File test:** `backend/test_scripts/test_services/test_fx_conversion.py` (estendere)

- **Test `compute_chain_rate`:** chiamata pura (no DB), test con 2-step chain (es. GBP→EUR→USD), verifica rate = prodotto
- ~~Test `sync_pair`:~~ **Rimossa come dead code in C13a** (sostituita da `sync_pairs_bulk`)

> `sync_pairs_bulk` è testata indirettamente via test E2E FX sync. Test unitari diretti rimandati (richiede mock provider complessi).

#### FX Provider — `FXRateProvider.generate_static_url()` (priorità 2)

**File test:** `backend/test_scripts/test_services/test_provider_registry.py` (estendere)

- Test: `generate_static_url("ecb/logo.svg")` restituisce `/api/v1/uploads/provider-static/fx/ecb/logo.svg`
- Verifica che il path sia relativo alla cartella del provider

#### Asset Prices Bulk — `get_current_prices_bulk()` (priorità 2)

**File test:** `backend/test_scripts/test_api/test_assets_prices.py` (nuovo test)

- Creare 2+ asset con provider assignment
- Chiamare `POST /assets/prices/current-bulk` con lista di asset_ids
- Verificare risposta contenga current price per ogni asset (o null se nessun dato)

#### Asset Search Stream — `search_stream()` (priorità 3)

**File test:** `backend/test_scripts/test_api/test_assets_crud.py` (nuovo test)

- Chiamare `GET /assets/search?q=AAPL` (SSE endpoint)
- Verificare che la risposta sia `text/event-stream`
- Parsare almeno un evento SSE e verificare struttura (provider_code, results)

#### User Service — `list_users()`, `reset_password()`, `set_user_active()` (priorità 3)

**File test:** `backend/test_scripts/test_services/test_user_profile.py` (estendere)

- **Test `list_users`:** creare 2 utenti, verificare lista restituisce entrambi
- **Test `reset_password`:** creare utente, reset password, verificare login con nuova password
- **Test `set_user_active`:** creare utente, disattivare, verificare login rifiutato, riattivare, login OK

#### Asset Provider — `map_identifier_type_to_input_type()` (priorità 3)

**File test:** `backend/test_scripts/test_services/test_asset_source.py` (estendere)

- Test mapping: `"ISIN"` → `ProviderInputType.ISIN`, `"TICKER"` → `ProviderInputType.TICKER`, `"unknown"` → `None`

**Done (13/04/2026):** 18 test aggiunti:
- `test_fx_conversion.py`: 6 test `TestComputeChainRate` (single/multi-step, inverse, missing leg, empty) + 7 test migrati da `convert()` a `_convert_single()` (wrapper `convert_bulk`)
- `test_provider_registry.py`: 3 test `generate_static_url` (FX, Asset, nested path)
- `test_asset_source.py`: 6 test `TestMapIdentifierTypeToInputType` (TICKER, ISIN, OTHER, UUID, CUSIP→None, FIGI→None)
- `test_user_profile.py`: 3 test `TestListUsers` + 2 test `TestResetPassword` + 3 test `TestSetUserActive`
- Priorità 1-2-3 coperte. SSE `search_stream` rimandato (richiede mock provider complesso).

---

### ✅ C13c. Coverage differenziata Backend/Frontend

Implementare `./dev.py test coverage` con sotto-comandi per gestire separatamente coverage backend (pytest-cov) e frontend (Playwright + sitecustomize.py).

**Struttura directory coverage:**

```
htmlcov/                  # Combined (default)
htmlcov-backend/          # Solo backend tests
htmlcov-frontend/         # Solo frontend E2E → backend
```

**Comandi:**

```bash
# Coverage separata
./dev.py test coverage show backend     # open htmlcov-backend/index.html
./dev.py test coverage show frontend    # open htmlcov-frontend/index.html
./dev.py test coverage show combined    # combine + open htmlcov/index.html

# Generazione
./dev.py test coverage combine          # merge .coverage.* → .coverage + html report
```

**Implementazione in `dev.py` / `test_runner.py`:**

- `--coverage` su test backend: `--cov-report=html:htmlcov-backend`
- `--coverage` su test frontend: `.coverage.<pid>` scritti da sitecustomize → `coverage combine` → `coverage html -d htmlcov-frontend`
- `coverage show combined`: `coverage combine` tutti i file → `coverage html -d htmlcov` → `open`

---

### Ordine C13

1. **C13a** — rimozione dead code (10 min, zero rischio)
2. **C13b** — test FX core: `compute_chain_rate` (20 min)
3. **C13b** — test `get_current_prices_bulk` API (10 min)
4. **C13b** — test user service (10 min)
5. **C13c** — coverage differenziata backend/frontend (15 min)

---

## C14. Test Coverage File Core (Non Provider)

Aumentare la coverage dei file core del backend. I file dei provider (FX e Asset Source) sono **fuori scope** — verranno coperti in un passo dedicato.

### Scope: file da coprire

I file target sono quelli sotto `backend/app/` esclusi:
- `backend/app/services/fx_providers/` (FX provider plugins)
- `backend/app/services/asset_source_providers/` (Asset source provider plugins)

### ✅ C14a. Rimozione dead code residuo

Dead code rimosso + documentazione in `TODO_FUTURI.md`:

| File | Funzione/Elemento | Azione |
|------|-------------------|--------|
| ~~`backend/app/utils/validation_utils.py`~~ | ~~`validate_compound_frequency()`~~ | ✅ File eliminato (unica funzione, mai importata) |
| ~~`backend/app/services/global_settings_service.py`~~ | ~~`get_session_ttl_hours_sync()`~~ | ✅ Eliminata — documentata in TODO_FUTURI.md |
| ~~`backend/app/services/global_settings_service.py`~~ | ~~`get_max_upload_mb_sync()`~~ | ✅ Eliminata — idem |
| ~~`backend/app/services/global_settings_service.py`~~ | ~~`is_registration_enabled_sync()`~~ | ✅ Eliminata — idem |
| ~~`backend/app/services/global_settings_service.py`~~ | ~~`get_default_language()`~~ | ✅ Eliminata — documentata in TODO_FUTURI con snippet per ricreazione |
| ~~`backend/app/services/global_settings_service.py`~~ | ~~`get_default_currency()`~~ | ✅ Eliminata — idem |
| ~~`backend/app/utils/geo_utils.py`~~ | ~~`normalize_country_multilang()`~~ | ✅ Eliminata — TODO_FUTURI documenta `normalize_country_to_iso3()` come base |
| `backend/app/utils/cache_utils.py` | `clear_cache()`, etc. | ✅ MANTENUTE + aggiunta `close_all_caches()` per shutdown pulito |

**Miglioramenti aggiuntivi:**
- `close_all_caches()` aggiunta a `cache_utils.py` — chiude tutti i timer wheel thread delle cache
- `lifespan()` in `main.py` ora chiama `close_all_caches()` durante lo shutdown
- `get_upload_by_user()` — mantenuta, documentata in TODO "Filtro Utente Files Page"
- `TODO_FUTURI.md` aggiornato con 6 nuove sezioni: multilang country, default language/currency, sync fallbacks, FX rate cache TTL 5min, uploads cache improvement

**Done (13/04/2026):** 7 funzioni rimosse, 1 file eliminato, `close_all_caches()` aggiunta, `./dev.py test services all` + `./dev.py test utils all` — zero regressioni.

---

### ✅ C14e. Fix frontend coverage pipeline

**Bug:** `_dispatch_test_command()` in `test_runner.py` non conteneva la logica di finalizzazione coverage (combine + html report). Questa logica era solo in `main()`, usata quando `test_runner.py` viene eseguito direttamente (non tramite `dev.py`).

**Fix applicata (3 round):**
1. **Round 1:** Aggiunta logica completa di coverage finalization a `_dispatch_test_command()`: `coverage combine` + `coverage html -d htmlcov-frontend` + summary report.
2. **Round 2:** Risolto root cause aggiuntivo — il vecchio `.coverage` file referenziava `validation_utils.py` cancellato → `coverage html` falliva silenziosamente. Fix:
   - Erase stale `.coverage` prima di `coverage combine` (sia in `_dispatch_test_command()` che in `main()`)
   - Rimosso `--append` da `coverage combine` → solo `.coverage.<pid>` nuovi
   - Aggiunto `--ignore-errors` a `coverage html` e `coverage report`
   - Check `returncode` di `coverage html` con warning esplicito
3. **Round 3 (fix definitivo):** I file `.coverage.<pid>` non venivano MAI creati. Due root cause:
   - **Root cause A:** `sitecustomize.py` del progetto era shadowed dal `sitecustomize.py` di sistema (`/opt/homebrew/.../python3.13/sitecustomize.py`). Quindi `coverage.process_startup()` non veniva mai chiamato. **Fix:** sostituita l'approach `sitecustomize.py` con `coverage run --parallel-mode -m uvicorn` in `cmd_server()` di `dev.py`. Il server in coverage mode ora viene avviato direttamente con `coverage run` che traccia il processo senza bisogno di sitecustomize.
   - **Root cause B:** SIGTERM (inviato da Playwright al webServer) non fa scattare gli atexit handler in Python (SIGTERM usa il default OS = terminate immediately). **Fix:** aggiunto `sigterm = true` in `.coveragerc` → coverage 7.2+ installa un handler SIGTERM che salva i dati prima dell'exit.
   - **Diagnostica aggiunta:** `test_runner.py` ora lista i file `.coverage.*` prima di combinare e mostra warning se nessun file trovato.
   - **Nota:** `--reload` non è usato in coverage mode perché `coverage run` traccia solo il processo diretto.

**Verificato (13/04/2026):** Test manuale completo:
- `coverage run --parallel-mode -m uvicorn` → server parte OK
- SIGTERM → `.coverage.<pid>` creato (77KB con dati reali)
- `coverage combine` → "Combined data file .coverage...."
- `coverage html -d htmlcov-frontend` → "Wrote HTML report" → cartella con 90+ file HTML

---

### ✅ C14f. Fix icone MkDocs (404 su titoli e tabelle)

**Bug:** I tag `<img src="...">` raw HTML nelle pagine di financial theory non venivano adjustati da MkDocs per le directory URLs. MkDocs converte `page.md` → `page/index.html`, aggiungendo un livello di directory che rende i percorsi relativi errati.

**Fix:**
1. **Titoli (120 occorrenze in 60 file):** Convertiti da `<img src="...">` a sintassi Markdown `![](...)` con `attr_list`. MkDocs regola automaticamente i percorsi Markdown.
2. **Tabelle overview (8 file index × 4 lingue):** Convertite da HTML `<table>` a tabelle Markdown con immagini Markdown. `md_in_html` non processa contenuto inline in `<td>`.
3. **Bug preesistente corretto:** typo `admre` → `adm_re` in `dev.py` `_check_admonition_empty_lines()`.

**Done (13/04/2026):** 68 file heading + 8 file index = 76 file modificati, 120+ sostituzioni. `./dev.py mkdocs build` OK, `./dev.py mkdocs check-links` 26/26 ✅.

### ✅ C14b. Test coverage — Utilities core

**Status:** ✅ COMPLETATO — Implementato in D12 (plan-partC_1_PostValidation).

- Test `cache_utils.py`: 17 test (NamedCache set/get/delete/clear, TTL expiration, registry, stats, list_caches)
- Test `decimal_utils`, `geo_utils`, `sector_fin_utils`, `currency_utils`: pre-esistenti, 6/6 passati

### ✅ C14c. Test coverage — Services core

**Status:** ✅ COMPLETATO (14/04/2026)

**Done:**
- `test_global_settings_service.py`: 19 test — `_convert_value` (int/bool/json/string), `get_setting_value` (DB/default/global), typed getters (TTL, upload MB, registration) con e senza DB row
- `test_fx_core.py`: 17 test — `normalize_rate_for_storage`, `upsert_rates_bulk` (insert/update/validation/normalize), `delete_rates_bulk` (single/range/not found/empty), `_count_actual_changes` (new/same/mixed/empty)
- `test_static_uploads.py`: 20 test — `save_upload` (basic/blocked ext), `get_upload_info` (exists/not found/missing file), `list_uploads` (empty/with files/filter user), `delete_upload` (exists/not found/from list), `get_upload_by_user` (owner/not owner), `validate_upload_security` (safe/blocked/unknown)
- Tutti registrati in `TEST_REGISTRY` di `test_runner.py`
- `./dev.py test services all` → 14/14 suite passate ✅

### ✅ C14d. Registrazione test in dev.py

**Status:** ✅ COMPLETATO (14/04/2026)

- `services_global_settings()`, `services_fx_core()`, `services_static_uploads()` registrati in `test_runner.py`
- Entry `"global-settings"`, `"fx-core"`, `"static-uploads"` aggiunte a `TEST_REGISTRY["services"]`
- `./dev.py test services all` → 14/14 suite (include le 3 nuove)
- Knowledge base `01_backend.md` aggiornata con i nuovi file test

### ✅ C14g. Verifica runtime fix coverage frontend

**Status:** ✅ VERIFICATO (13/04/2026)

**Test manuale effettuato:**
1. `coverage run --parallel-mode -m uvicorn backend.app.main:app` → server avviato
2. `kill $PID` (SIGTERM) → `.coverage.<pid>` creato (77KB) grazie a `sigterm = true`
3. `coverage combine` → "Combined data file .coverage...."
4. `coverage html -d htmlcov-frontend` → report HTML generato con 90+ file

**Root cause risolta (Round 3):**
- `sitecustomize.py` shadowed da sistema → sostituito con `coverage run -m uvicorn`
- SIGTERM non salva atexit → aggiunto `sigterm = true` in `.coveragerc`
- Diagnostica `.coverage.*` files aggiunta a `test_runner.py`

**⏳ Resta da verificare con E2E completo:** `./dev.py test --coverage front-fx fx-csv-import` + `./dev.py test coverage show frontend`

### Ordine C14

1. **C14a** — ✅ cleanup dead code residuo
2. **C14e** — ✅ fix frontend coverage pipeline
3. **C14f** — ✅ fix icone MkDocs
4. **C14g** — ✅ verifica runtime fix coverage frontend
5. **C14b** — ✅ test utilities core (completato in D12)
6. **C14c** — ✅ test services core (14/04/2026): 56 test in 3 file
7. **C14d** — ✅ registrazione + verifica (14/04/2026): 14/14 suite services

---

## ✅ C15. Manutenzione e Fix Infrastrutturali (13 Apr 2026)

### ✅ C15a. main.py — import top-level

**Problema:** `main.py` aveva import inline dentro `lifespan()`, `_initialize_global_settings()`, `_prewarm_provider_caches()` per evitare import circolari. Tuttavia non ci sono import circolari reali — le dipendenze sono unidirezionali (main → services → db → schemas).

**Fix applicata:**
- Spostati tutti gli import inline al top-level di `main.py`:
  - `seed_default_avatars` da `static_uploads`
  - `close_all_caches` da `cache_utils`
  - `AsyncSession` da `sqlalchemy.ext.asyncio`
  - `get_async_engine` da `db.session`
  - `initialize_global_settings` da `settings_service`
- Rimosso re-import di `AssetProviderRegistry` (già importato al top)

**Verificato nel codice:** `main.py` L35-40 contiene tutti gli import al top-level. ✅

### ✅ C15b. MkDocs build — verifica icon path

**Problema:** Dopo il lavoro sulle icone asset in mkdocs, non c'era verifica che i path `<img src="...static/icons/...">` dentro gli HTML generati puntassero a file esistenti.

**Fix applicata:**
- Aggiunta `_check_image_paths_in_built_site()` in `dev.py` (L530-571)
- Scansiona tutti i `.html` nel sito generato
- Per ogni `<img src>` che contiene `static/icons`, risolve il path relativo e verifica che il file esista
- Print warning visibile `❌` con path HTML + src se broken
- Print `✅ All static icon paths verified` se tutto ok
- Chiamata automaticamente dopo `mkdocs build` (solo se build OK, L581)

**Verificato nel codice.** ✅

### ✅ C15c. FX Rate Cache TTL 5min

**Problema:** Sync ripetute/ossessive causano richieste multiple identiche ai provider FX (ECB, FED, BOE, SNB). I tassi FX sono aggiornati giornalmente, quindi una cache breve è ragionevole.

**Fix applicata:**
- Creata `_fx_fetch_cache = get_ttl_cache("fx_provider_responses", maxsize=200, ttl=300)` in `fx.py` (L31)
- Cache key: `(provider_code, frozenset(target_currencies), date_range)` (L901)
- Nella `_fetch_provider()` di `sync_pairs_bulk()` (L900-909):
  - Prima del fetch, check cache → se hit, skip fetch e usa dati cached
  - Dopo il fetch, salva result in cache
- Log debug su cache hit per diagnostica
- Cleanup automatico via `close_all_caches()` nel lifespan shutdown

**Verificato nel codice.** ✅

### ✅ C15d. Upload Metadata Cache TTL 1h

**Problema:** `_load_metadata()` in `static_uploads.py` leggeva JSON sidecar dal disco ad ogni richiesta. Con molti file o richieste frequenti, I/O inutile.

**Fix applicata:**
- Creata `_upload_meta_cache = get_ttl_cache("upload_metadata", maxsize=500, ttl=3600)` in `static_uploads.py` (L53)
- `_load_metadata()` → check cache prima di leggere disco, popola cache al read (L141-150)
- `_save_metadata()` → aggiorna cache dopo scrittura su disco (L161)
- `delete_upload()` → invalida entry dalla cache dopo eliminazione (L455)
- TTL 1h evita stale data; eviction W-TinyLFU più efficiente del LRU puro

**Verificato nel codice.** ✅

### ✅ C15e. Frontend Coverage — Fix definitivo (3 round)

**Problema:** `./dev.py test --coverage front-fx ...` non generava il report HTML in `htmlcov-frontend/`.

**Root cause (3 livelli):**
1. **Round 1:** `_dispatch_test_command()` mancava della logica di coverage finalization → aggiunta
2. **Round 2:** Stale `.coverage` referenziava file cancellati → erase stale + `--ignore-errors`
3. **Round 3 (definitivo):** I file `.coverage.<pid>` non venivano MAI creati perché:
   - `sitecustomize.py` del progetto shadowed dal sistema (`/opt/homebrew/.../python3.13/sitecustomize.py`)
   - SIGTERM (da Playwright) non fa scattare atexit handlers in Python

**Fix applicata:**
1. **`dev.py` `cmd_server()`:** In coverage mode, usa `coverage run --parallel-mode -m uvicorn` invece di `uvicorn` direttamente. No `--reload` in coverage mode.
2. **`.coveragerc`:** Aggiunto `sigterm = true` → coverage installa un SIGTERM handler che salva dati prima dell'exit.
3. **`test_runner.py`:** Diagnostica aggiunta: lista `.coverage.*` files prima di combine, warning se nessun file trovato.

**Verificato manualmente (13/04/2026):** Server avviato con `coverage run`, SIGTERM → `.coverage.<pid>` creato (77KB), `coverage combine` OK, `coverage html` genera report completo.

### C15f. Pipeline Coverage — Documentazione Completa

#### Come funziona il coverage tracking

**Backend tests** (`./dev.py test --coverage services all`, `api all`, etc.):
1. `test_runner.py` rileva che il comando è `pytest` + `_COVERAGE_MODE=True`
2. Aggiunge automaticamente `--cov=backend/app --cov-append --cov-report=html:htmlcov-backend`
3. `pytest-cov` traccia la coverage direttamente nel processo pytest
4. Report HTML generato in `htmlcov-backend/`

**Frontend E2E tests** (`./dev.py test --coverage front-fx all`, `front-user all`, etc.):
1. `_run_playwright(coverage=True)` → setta `env["COVERAGE_BACKEND"] = "1"`
2. Playwright config vede `COVERAGE_BACKEND` → appende `--coverage` al comando server
3. `dev.py server --coverage` → avvia server con `coverage run --parallel-mode -m uvicorn` (NO `--reload`)
4. `sigterm = true` in `.coveragerc` → coverage installa SIGTERM handler
5. Test E2E eseguiti → il server serve le richieste tracciando la coverage backend
6. Playwright termina → SIGTERM al server → coverage salva `.coverage.<pid>`
7. `test_runner.py` → `coverage combine` → `coverage html -d htmlcov-frontend`

#### Flag CLI `./dev.py test`

| Flag | Effetto |
|------|---------|
| `--coverage` | **Backend:** aggiunge `--cov=backend/app --cov-append --cov-report=html:htmlcov-backend` a pytest. **Frontend:** setta `COVERAGE_BACKEND=1` → server avviato con `coverage run`. Post-test: `coverage combine` + `coverage html -d htmlcov-frontend`. |
| `--cov-clean` | Esegue `coverage erase` prima dei test → cancella vecchi `.coverage` e `.coverage.*` files. Utile per partire da zero. |
| `--db-reset` | ⚠️ **Non implementato** — il flag è accettato dal parser ma non ha effetto nel codice. Pensato per resettare il DB test prima dei test DB, ma la logica non è stata scritta. |

#### Visualizzare i report

```bash
./dev.py test coverage show backend     # apre htmlcov-backend/index.html
./dev.py test coverage show frontend    # apre htmlcov-frontend/index.html
./dev.py test coverage show combined    # combine + apre htmlcov/index.html
```

> **Nota:** `sitecustomize.py` nel project root **non è più usato** per il coverage tracking. Il file resta come documentazione/fallback ma il meccanismo attivo è `coverage run -m uvicorn` in `cmd_server()`.

---

## Documentazione — Task Completati

### C1. Backend — AssetBackwardFillInfo + FAPricePoint esteso

- Creazione di `AssetBackwardFillInfo(BackwardFillInfo)` con campi aggiuntivi per la gestione dei tassi di cambio.
- Estensione di `FAPricePoint` per includere informazioni sulla valuta originale e gestione degli errori nei risultati delle query di prezzo.

### C2. Backend — target_currency in query + conversione

- Implementazione della logica per la conversione dei prezzi in base alla valuta target nelle query di prezzo.
- Aggiunta di test per verificare il corretto funzionamento della conversione dei prezzi e della gestione degli errori.

### C3. Frontend — Chart + staleness combinata

- Modifiche al frontend per gestire la visualizzazione dei prezzi in diverse valute e la loro "freschezza" basata sui tassi di cambio.
- Aggiunta di badge e tooltip informativi per indicare la provenienza e l'età dei dati sui prezzi.

### C4. Live Ticker conversion

- Aggiornamenti al servizio di ticker dal vivo per convertire i prezzi nella valuta selezionata e gestire gli errori di conversione.

### C5. Comparison overlays conversion

- Modifiche al caricamento dei dati di confronto per includere la valuta target e gestire i casi in cui manca la coppia di valute per il confronto.

### C6. Auto-sync dopo save provider

- Implementazione della sincronizzazione automatica dopo il salvataggio di un provider, sia nella lista degli asset che nei dettagli del provider FX.

### C7. i18n + Polish

- Aggiunta di chiavi di internazionalizzazione e miglioramenti estetici per supportare più lingue e garantire coerenza visiva.

### C8. Fix broken frontend → docs links

- Correzione dei link interrotti nella documentazione MkDocs a seguito di riorganizzazioni della struttura delle cartelle.

### C9. Tooltip mobile: offset adattivo per device

- Adeguamento dell'offset dei tooltip sui dispositivi mobili per evitare che il dito copra le informazioni del tooltip.

### C10. Mobile measure: touch fix + bottone "+Add Measure"

- Risoluzione dei problemi di interazione touch per la creazione di misure sui dispositivi mobili e aggiunta di un pulsante per semplificare la creazione di nuove misure.

### C11. Banner "tail precede il primo dato disponibile"

- Aggiunta di un banner informativo quando l'intervallo di date selezionato dall'utente non ha dati disponibili nel database.

### C12. Docker env conflict warning in dev.py

- Implementazione di avvisi per conflitti di variabili d'ambiente quando si utilizza Docker, per evitare comportamenti imprevisti.

### C13. Rimozione Dead Code + Test Coverage Funzioni Core

- Rimozione di codice non utilizzato e non raggiungibile, con conseguente pulizia del codebase e miglioramento della copertura dei test.

### C14. Test Coverage File Core (Non Provider)

- Aumento della copertura dei test per i file core del backend, escludendo i provider FX e Asset Source.

### C15. Manutenzione e Fix Infrastrutturali

- Varie attività di manutenzione e fix infrastrutturali, tra cui la rimozione di import circolari, la verifica dei percorsi delle icone nella documentazione, l'implementazione di cache TTL per i tassi di cambio FX e i metadati degli upload, e miglioramenti alla pipeline di coverage per il frontend.

---

## 📊 Recap Globale — Stato al 13 Aprile 2026

### ✅ Completato e verificato nel codice

| Step | Descrizione | File principali modificati |
|------|-------------|---------------------------|
| C1-C7 | Conversione valuta completa (backend + frontend + i18n) | `prices.py`, `asset_source.py`, `fx.py`, `+page.svelte` (asset/fx), `PriceChartFull.svelte` |
| C8 | Fix link frontend → docs MkDocs | 9 file signal `.ts`, `AssetDataEditorSection.svelte` |
| C9 | Tooltip mobile offset adattivo | `PriceChartFull.svelte` |
| C10 | Touch fix + bottone Add Measure | `PriceChartFull.svelte`, `MeasurePanel.svelte` |
| C11 | Banner "data available from" | `assets/[id]/+page.svelte`, `fx/[pair]/+page.svelte` |
| C12 | Docker env conflict warning | `dev.py` |
| C13a | Dead code removal (8 funzioni broker + 3 asset_source) | `broker_service.py`, `asset_source.py` |
| C13a-R2 | Dead code removal (`convert()`, `sync_pair()`, ECB legacy) | `fx.py`, `test_fx_conversion.py` |
| C13b | Test core (18 test: chain_rate, static_url, identifier_type, user ops) | `test_fx_conversion.py`, `test_provider_registry.py`, `test_asset_source.py`, `test_user_profile.py` |
| C13c | Coverage differenziata backend/frontend | `test_runner.py` |
| C14a | Dead code residuo (7 funzioni + 1 file eliminato) | `global_settings_service.py`, `geo_utils.py`, `validation_utils.py` (deleted) |
| C14e | Fix frontend coverage pipeline (2 round) | `test_runner.py` |
| C14f | Fix icone MkDocs (76 file, 120+ sostituzioni) | 68 heading `.md` + 8 index `.md` |
| C15a | main.py import top-level | `main.py` |
| C15b | MkDocs build verifica icon path | `dev.py` |
| C15c | FX Rate Cache TTL 5min | `fx.py` |
| C15d | Upload Metadata Cache TTL 1h | `static_uploads.py` |
| C15e | Frontend coverage fix (3 round: finalization + stale + sigterm) | `test_runner.py`, `dev.py`, `.coveragerc` |

### 🧪 Da verificare con E2E — test umano

| Cosa | Comando | Risultato atteso |
|------|---------|-----------------|
| Coverage frontend E2E | `./dev.py test --coverage front-fx fx-csv-import` poi `./dev.py test coverage show frontend` | Report HTML aperto con coverage del backend tracciata durante i test E2E |
| Coverage frontend user | `./dev.py test --coverage front-user all` poi `./dev.py test coverage show frontend` | Idem |
| Icone MkDocs | `./dev.py mkdocs build` poi navigare su financial-theory/instruments/ | Tutte le icone visibili nei titoli e nelle tabelle overview |
| MkDocs icon path check | `./dev.py mkdocs build` | "✅ All static icon paths in built site verified" |

### ⏳ Pendente — da implementare

| Step | Descrizione | Stima | Priorità |
|------|-------------|-------|----------|
| **C14b** | Test coverage utilities core (`finance_utils`, `geo_utils`, `decimal_utils`, `cache_utils`) | 30 min | 🟡 Media |
| **C14c** | Test coverage services core (`global_settings_service`, `fx.py` funzioni, `static_uploads`) | 30 min | 🟡 Media |
| **C14d** | Registrazione test in dev.py + verifica coverage incremento | 5 min | 🟡 Media |

### ✅ Flag CLI aggiornati (13/04/2026)

- `--db-reset` **rimosso** dal parser (era dead code — mai implementato)
- `--cov-clean` **split** in `--cov-clean-backend` e `--cov-clean-frontend`
- `all-backend` e `all-frontend` **aggiunti** come sotto-gruppi di test

### 📝 Note su TODO_FUTURI.md aggiornati

I seguenti TODO sono stati documentati ma **NON richiedono implementazione immediata** (sono feature future):
- 🌍 Normalizzazione Paese Multilingua (endpoint user-facing)
- ⚙️ Default Language/Currency per nuovi utenti
- 🔄 Fallback Sync (SCARTATO)
- 💾 FX Rate Cache TTL 5min → **✅ IMPLEMENTATO** (status aggiornato in TODO_FUTURI)
- 📁 Upload Cache TTL → **✅ IMPLEMENTATO** (status aggiornato in TODO_FUTURI)
- 👥 `get_upload_by_user()` → mantenuta, collegata a TODO "Filtro Utente Files Page"

---

## ➡️ Seguito: Part C.1 — Post-Validazione

La validazione manuale di C1-C12 ha rivelato 2 bug e 9 miglioramenti UX/feature.
Vedi → [plan-partC_1_PostValidation.prompt.md](plan-partC_1_PostValidation.prompt.md)

