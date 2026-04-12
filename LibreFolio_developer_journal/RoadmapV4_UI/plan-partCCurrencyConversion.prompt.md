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

## Ordine di implementazione

1. **C1** → schema (10 min)
2. **C2** → logica conversione `get_prices_bulk` (30 min)
3. **C7 partial** → api sync + i18n keys
4. **C3** → frontend chart + staleness (40 min)
5. **C4** → live ticker conversion (15 min)
6. **C5** → comparison overlays (20 min)
7. **C6** → auto-sync dopo save (15 min)
8. **C7 final** → polish, dark mode, responsive

