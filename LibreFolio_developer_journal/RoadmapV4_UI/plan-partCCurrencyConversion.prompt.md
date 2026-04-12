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

## C4. Live Ticker conversion

**File:** `livePriceService.ts` + `assets/[id]/+page.svelte`

- Quando `displayCurrency !== assetInfo.currency`:
  - Dopo aver ottenuto il live price (provider, valuta nativa), fare `convert()` via `POST /fx/currencies/convert` passando la data del giorno
  - Mostrare prezzo convertito in `AssetPriceSummary`
  - Se conversione fallisce → prezzo nativo + icona warning

---

## C5. Comparison overlays conversion

**File:** `loadComparisonData.ts` + `assets/[id]/+page.svelte`

- Passare `target_currency` alla `query_prices_bulk` per gli asset di comparazione
- Se coppia FX non configurata per un asset di confronto:
  - Nella signal card: mostrare ⚠ triangle + pulsante "add FX pair" (stesso pattern di `AssetPriceSummary.fxConversionMissing`)
  - Dati della comparazione NON sovrapposti al chart (valute diverse = fuorviante)

---

## ✅ C6. Auto-sync dopo save provider

- **Asset LIST** (`assets/+page.svelte`): `oncreated` ora riceve `assetId` dalla modal e trigga `handleSyncAsset()`. Firma cambiata da `() => void` a `(assetId: number) => void`.
- **FX detail** (`fx/[pair]/+page.svelte`): `handleProviderModalCreated` → dopo `loadProviders()`, chiama `handleSync()` per sincronizzare tassi.

**Done (12/04/2026):** AssetModal passa `assetId` in entrambi i percorsi oncreated (success e partial failure). Asset list auto-sync. FX detail auto-sync.

- **Asset LIST** (`assets/+page.svelte`): `oncreated` deve ricevere `assetId` dalla modal e triggare `POST /assets/prices/sync` per il nuovo asset. Cambiare firma `oncreated` da `() => void` a `(assetId: number) => void`
- **FX detail** (`fx/[pair]/+page.svelte`): `handleProviderModalCreated` → dopo `loadProviders()`, chiamare `handleSync()` per sincronizzare tassi con il nuovo provider

---

## C7. i18n + Polish

- ~20-25 chiavi i18n (EN/IT/FR/ES) via `./dev.py i18n add`
- `./dev.py api sync` per rigenerare client TypeScript
- Dark mode check, responsive wide/tablet/tabletS/mobile

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

## C9. Tooltip mobile: offset adattivo per device

**File:** `PriceChartFull.svelte` (linea ~701)

**Problema:** L'offset di 30px sopra il dito per il tooltip è insufficiente su mobile (il dito copre il tooltip), ma va bene con il mouse su desktop.

**Fix:**
- Rilevare `'ontouchstart' in window` o `navigator.maxTouchPoints > 0`
- Desktop (mouse): mantenere `gap = 30`
- Mobile (touch): aumentare a `gap = 60` (o più, da testare)
- Applicare sia in FX chart che in Asset chart (entrambi usano `PriceChartFull`)

---

## C10. Mobile measure: touch fix + bottone "+Add Measure"

**File:** `PriceChartFull.svelte` + `ChartSignalsSection.svelte` (pannello misure)

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

---

## C11. Banner "tail precede il primo dato disponibile"

**File:** `assets/[id]/+page.svelte` + `fx/[pair]/+page.svelte`

**Problema:** Se l'utente seleziona un range temporale che inizia prima del primo prezzo/tasso disponibile nel DB, non c'è nessuna indicazione visiva — il chart mostra semplicemente un'area vuota a sinistra.

**Fix:**
- Dopo il caricamento dei dati, confrontare la data di inizio range visualizzata con la data del primo punto dati
- Se `visibleStart < firstDataPoint.date`:
  - Mostrare un banner in cima alla pagina (stesso stile dei banner esistenti per FX warning)
  - Testo: "⚠ Data available from {firstDate} — earlier dates have no data"
  - Il banner scompare quando l'utente zooma/panna in un range che ha dati completi
- Implementare sia in **Asset detail** che in **FX detail**

---

## C12. Docker env conflict warning in dev.py

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

---

## Ordine di implementazione (aggiornato)

1. ✅ **C8** → fix link rotti + script validazione
2. ✅ **C1** → schema + api sync
3. ✅ **C2** → logica conversione `get_prices_bulk` + 5 test backend
4. ✅ **C3** → frontend chart + staleness + tooltip FX
5. **C6** → auto-sync dopo save provider (15 min) ← **NEXT** (prerequisito UX per C4/C5)
6. **C4** → live ticker conversion (15 min)
7. **C5** → comparison overlays (20 min)
8. **C9** → tooltip mobile offset (10 min)
9. **C10** → measure touch fix + bottone add (30 min)
10. **C11** → banner tail/data mismatch (20 min)
11. **C12** → docker env conflict warning (15 min)
12. **C13** → rimozione dead code + test coverage funzioni core (45 min)
13. **C7 final** → i18n keys, polish, dark mode, responsive

---

## C13. Rimozione Dead Code + Test Coverage Funzioni Core

Analisi coverage (12/04/2026) ha identificato 94 funzioni con `def` coperto ma body mai eseguito.
Di queste, 17 classificate HIGH priority. L'analisi call-graph ha rivelato che **7 sono dead code** e **10 sono codice vivo non testato**.

### C13a. Rimozione Dead Code

Eliminare le seguenti funzioni che non sono più chiamate da nessun punto del codebase:

#### `backend/app/services/asset_source.py`

| Linea | Funzione | Motivo |
|-------|----------|--------|
| 1474 | `AssetSourceManager._fetch_provider_history()` | Helper mai collegato — nessun `self._fetch_provider_history` nel codice |
| 1518 | `AssetSourceManager._fetch_db_price_map()` | Helper mai collegato — nessun `self._fetch_db_price_map` nel codice |
| 3056 | `AssetMetadataService.update_asset_metadata()` | Mai chiamata da API endpoint né da altri servizi |

#### `backend/app/services/broker_service.py`

| Linea | Funzione | Motivo |
|-------|----------|--------|
| 830 | `BrokerService.add_access()` | Sostituita da `bulk_update_access()` — l'API usa solo `bulk_update_access` |
| 903 | `BrokerService.update_access()` | Idem |
| 974 | `BrokerService.remove_access()` | Idem |
| 794 | `BrokerService._count_owners()` | Helper usato solo da `update_access`/`remove_access` (dead) |
| 808 | `BrokerService._sum_share_percentages()` | Helper usato solo da `add_access`/`update_access` (dead) |

> **Nota:** `bulk_update_access()` (L1029) implementa la stessa logica in modo atomico.
> I singoli metodi erano il design originale pre-refactoring.

**Procedura:**
1. `git diff` per confermare zero call site
2. Eliminare le 8 funzioni
3. Eseguire `./dev.py test api all` e `./dev.py test services all` — zero regressioni attese
4. Commit: `chore: remove 8 dead functions (pre-bulk_update_access legacy + unused asset helpers)`

---

### C13b. Test per funzioni core vive ma scoperte

#### FX Core — `compute_chain_rate()` + `sync_pair()` (priorità 1)

**File test:** `backend/test_scripts/test_services/test_fx_conversion.py` (estendere)

- **Test `compute_chain_rate`:** chiamata pura (no DB), test con 2-step chain (es. GBP→EUR→USD), verifica rate = prodotto
- **Test `sync_pair` 1-step:** mock provider fetch, verifica upsert rates nel DB
- **Test `sync_pair` multi-step:** mock 2 leg fetch, verifica chain rate calcolato e persistito
- **Test `sync_pair` provider failure:** mock provider che fallisce, verifica fallback + error message

> `sync_pair` è async e richiede DB + provider mock. Usare `AsyncSession` fixture esistente.

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

---

### C13c. Coverage differenziata Backend/Frontend

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
2. **C13b** — test FX core: `compute_chain_rate` + `sync_pair` (20 min)
3. **C13b** — test `get_current_prices_bulk` API (10 min)
4. **C13b** — test user service (10 min)
5. **C13c** — coverage differenziata backend/frontend (15 min)
