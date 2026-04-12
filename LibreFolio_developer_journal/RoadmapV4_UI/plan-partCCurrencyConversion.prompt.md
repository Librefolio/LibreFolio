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

## C1. Backend — AssetBackwardFillInfo + FAPricePoint esteso

**File:** `backend/app/schemas/prices.py`

- Creare `AssetBackwardFillInfo(BackwardFillInfo)` con campi aggiuntivi:
  - `fx_rate_date: Optional[date] = None` — data effettiva del tasso FX usato
  - `fx_days_back: Optional[int] = None` — giorni indietro del tasso FX
- Cambiare `FAPricePoint.backward_fill_info` da `Optional[BackwardFillInfo]` a `Optional[AssetBackwardFillInfo]`
- Aggiungere `original_currency: Optional[str] = None` a `FAPricePoint`
- Aggiungere `errors: List[str] = Field(default_factory=list)` a `FAPriceQueryResult`
- **Backward-compatible:** i campi FX sono `Optional`, prezzi non convertiti funzionano identicamente.

---

## C2. Backend — target_currency in query + conversione

**File:** `schemas/prices.py` + `services/asset_source.py`

- Aggiungere `target_currency: Optional[str] = None` a `FAPriceQueryItem` con validator
- In `get_prices_bulk()`, dopo la serie backward-filled, se `target_currency` presente e ≠ `point.currency`:
  - Raccogliere conversioni: `[(Currency(code=p.currency, amount=p.close), target, p.date), ...]` per OHLC
  - Chiamare `convert_bulk(session, conversions, raise_on_error=False)` in batch
  - **Success:** sostituire OHLC, impostare `original_currency`, `currency = target`, popolare `fx_rate_date`/`fx_days_back` se il tasso è backfilled — il `days_back` originale (staleness prezzo) resta inalterato
  - **Failure** (coppia FX mancante): prezzo nativo inalterato + warning in `result.errors`

---

## C3. Frontend — Chart + staleness combinata

**File:** `assets/[id]/+page.svelte` + `PriceChartFull.svelte` + `lineChartHelpers.ts`

- **3a:** `loadChartData()` → passare `target_currency: displayCurrency !== assetInfo.currency ? displayCurrency : undefined`
- **3b:** `$effect` che richiama `loadChartData()` quando `displayCurrency` cambia (ora NON lo fa)
- **3c:** Aggiungere `fxStaleDays?: number` a `LineDataPoint`, mappato da `backward_fill_info.fx_days_back`
- **3d:** Gradiente opacità = `max(staleDays, fxStaleDays ?? 0)` → dato "fresco" solo se ENTRAMBI sono freschi. `getStaleOpacity()` riceve il max, nessuna modifica alla funzione
- **3e:** Tooltip breakdown: `⚠ Price: N days old` + `⚠ FX rate: N days old` (entrambi solo se > 0). Riga `💱 Converted from USD` quando `original_currency` presente
- **3f:** Y-axis/summary: mostra `displayCurrency`, badge "converted from XXX"

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

## C6. Auto-sync dopo save provider

- **Asset LIST** (`assets/+page.svelte`): `oncreated` deve ricevere `assetId` dalla modal e triggare `POST /assets/prices/sync` per il nuovo asset. Cambiare firma `oncreated` da `() => void` a `(assetId: number) => void`
- **FX detail** (`fx/[pair]/+page.svelte`): `handleProviderModalCreated` → dopo `loadProviders()`, chiamare `handleSync()` per sincronizzare tassi con il nuovo provider

---

## C7. i18n + Polish

- ~20-25 chiavi i18n (EN/IT/FR/ES) via `./dev.py i18n add`
- `./dev.py api sync` per rigenerare client TypeScript
- Dark mode check, responsive wide/tablet/tabletS/mobile

---

## C8. Fix broken frontend → docs links

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

1. **C8** → fix link rotti + script validazione (15 min)
2. **C1** → schema (10 min)
3. **C2** → logica conversione `get_prices_bulk` (30 min)
4. **C7 partial** → api sync + i18n keys
5. **C3** → frontend chart + staleness (40 min)
6. **C4** → live ticker conversion (15 min)
7. **C5** → comparison overlays (20 min)
8. **C6** → auto-sync dopo save (15 min)
9. **C9** → tooltip mobile offset (10 min)
10. **C10** → measure touch fix + bottone add (30 min)
11. **C11** → banner tail/data mismatch (20 min)
12. **C12** → docker env conflict warning (15 min)
13. **C7 final** → polish, dark mode, responsive
