# Plan: Phase 5 — FX Management + Chart Library + User Docs + i18n MkDocs (v6)

**Data creazione**: 2 Marzo 2026
**Status**: 🔄 IN PROGRESS — Step 1-5 completati, Step 6 (Chart avanzati) in corso.
Completati in Step 6: DateRangePicker custom (dual-column semi-indipendenti, i18n weekdays/months, presets ridotti 1W/1M/1Y/Custom inline badge), LineChart fix Y-axis + colori % segmentati piecewise (rosso sotto 0%, verde sopra), MeasureOverlay 3-click cycle con Y coordinata mappata, fix 404 su FX detail initial load.
**Durata stimata**: ~7-8 giorni
**Dipendenze**: Phase 4 completata, Phase 4.8 (Broker Sharing) completata
**Riferimenti**:
- `plan-phase05-to-08-upgrade.md` §4 (versione precedente)
- `phases/phase-05-fx.md` (legacy plan, superato da questo documento)
- `TODO_FUTURI.md` §FX, §Cross-Rate

---

## ✅ Decisioni Confermate (2 Marzo 2026 — Review iterazione 3)

### DateRangePicker
- **Calendario custom dual-column**: NO input HTML nativi (brutti, non uniformi cross-OS). Implementare popover Svelte con 2 mesi affiancati, click su 2 date → min è "from", max è "to". Possono essere sulla stessa colonna.
- **Colonne semi-indipendenti**: ogni colonna ha il suo selettore mese e anno. Se la colonna sinistra viene impostata oltre la destra, le colonne si swappano automaticamente (e viceversa). Questo permette di selezionare date distanti tra loro.
- **Presets ridotti**: solo 1W, 1M, 1Y + Custom (inline badge editabile). Il Custom quando cliccato mostra amount + granularity (days/weeks/months/years) inline, senza creare una nuova sezione.
- **i18n completa**: weekdays e months tradotti in tutte le lingue supportate (EN/IT/FR/ES) via `$derived` pre-computed labels (necessario perché Svelte 5 non permette `$_()` dentro `{#snippet}`).
- **Componente su 2 righe nel filter bar**: riga 1 = presets (1W, 1M, 1Y, Custom), riga 2 = calendario From/To. Il tutto affiancato ai filtri valuta.

### LineChart ↔ DataZoomBar
- **Collegamento bidirezionale visivo**: zoom con rotellina nel chart DEVE aggiornare la barra e viceversa. Implementato tramite `onZoomChange` callback che propaga start/end percentuali.
- **DataZoomBar**: singolo grafico overview (linea assoluta), eliminati i grafici secondari confusi.

### Colori Percentuale (% mode)
- **Segmenti dinamici**: la linea diventa rossa quando il valore scende sotto lo 0% e verde sopra. Anche l'area fill cambia colore per segmento tramite ECharts `visualMap` piecewise su dimensione Y.
- **Nota informativa**: nel tooltip, chiarire che la % è relativa al primo giorno nel date-picker (giorno 0 del range selezionato), non al primo giorno visibile dopo zoom.
- **Asse Y visibile**: sempre mostrare asse Y con valori, sia in modalità assoluta che percentuale. Formatter: % in percentuale mode, numeri abbreviati (k) in assoluta.
- **Toggle abs/% nelle FxCard**: piccolo pulsante % nel header della card.
- **Toggle abs/% globale**: slider button nella pagina FX lista, sopra le card.

### Cache Bidirezionale Inversione
- **Calcolo locale client-side**: quando si inverte la coppia (swap), il valore invertito = `1/rate`. Calcolo fatto localmente per performance immediata, nessuna doppia chiamata al backend.
- **2 istanze TimeSeriesStore per coppia**: una per direzione originale, una per direzione inversa. Invalidare entrambe su refresh/sync.

### MeasureOverlay (Linea di tendenza)
- **3-click cycle**: 1° click = start point, 2° click = disegna misura con info box, 3° click = cancella e torna ad aspettare il 1° click. NO pulsante toggle separato per attivare/disattivare.
- **Y segue valori grafico**: la freccia e i pallini si posizionano all'altezza del valore del dato, non a un'altezza fissa. Coordinate Y mappate tramite `yRange` e `chartGridBounds`.
- **Arrow follows time axis**: se il secondo punto finisce prima del primo, i due punti vengono scambiati (la freccia punta sempre avanti nel tempo).
- Info box: valore partenza, valore arrivo, Δ assoluto, Δ%, intervallo giorni. "Click anywhere to dismiss" message.

### Layout pagina FX detail
- **Toolbar compatta**: presets + calendario su una riga a sinistra, Line/Candle + Abs/% + Measure + Refresh/Sync/Edit a destra. In mobile, bottoni con solo icona.
- **Fix 404 initial load**: date range inizializzate in modo sincrono (non reattivo) per evitare chiamate API con date vuote.

### Cross-Rate (USD→EUR→RON)
- Documentato in TODO_FUTURI.md — NON implementato ora. Placeholder visivo "Coming Soon" presente.

---

## Overview

Phase 5 comprende cinque macro-aree:

1. **TimeSeriesStore** — Cache client-side generica con registry condivisa tra card e detail page
2. **Libreria Chart ECharts** — 10+ sotto-componenti modulari (inclusa estrazione `SemiDonutChart` da BrokerSharing)
3. **Pagine FX** — Lista `/fx` con card + filtri/sync/refresh globali, dettaglio `/fx/[pair]` con chart avanzato e edit mode bulk
4. **Documentazione Utente GUI** — Pagine MkDocs per feature esistenti (Brokers, Files, Settings) e FX con screenshot gallery
5. **i18n MkDocs Globale** — Evoluzione selettore lingua da gallery-only a globale + configurazione `mkdocs-static-i18n` + rename file

**Nessun nuovo endpoint backend necessario.** I dati storici FX si ottengono da `POST /api/v1/fx/currencies/convert` passando `amount: 1`.

---

## Architettura Core: Finestra → Cache → Backend

### Distinzione Finestra / Sync / Refresh

| Concetto | Trigger | Cosa fa | Tocca provider esterni? |
|---|---|---|---|
| **Finestra temporale** | Cambio date range (globale o locale) | Chart consulta `TimeSeriesStore` → fetch solo gap mancanti via `POST /fx/currencies/convert` (amount=1) | ❌ No |
| **Refresh** | Pulsante refresh (globale o per-card) | Invalida cache per range visibile → ri-chiede tutto al backend. | ❌ No |
| **Sync** | Pulsante sync (globale o locale) | `GET /fx/currencies/sync` → resta pending fino a esito → se OK, triggera refresh per area sincronizzata | ✅ Sì |

**Principio chiave**: La finestra temporale usa solo dati nel DB. Il sync aggiorna il DB dai provider esterni (ECB, FED, BOE, SNB). In futuro il sync sarà chiamato periodicamente da un demone; per ora avviene solo su richiesta esplicita dell'utente.

### TimeSeriesStore<T> — `src/lib/stores/TimeSeriesStore.ts`

Cache client-side generica, parametrica su `T extends { date: string }`:

```typescript
interface TimeSeriesStore<T extends { date: string }> {
    // Ritorna i punti presenti nel range + lista di intervalli mancanti (gap)
    getRange(start: string, end: string): { data: T[], gaps: Array<{start: string, end: string}> };

    // Inserisce/aggiorna punti (idempotente, merge per data)
    merge(points: T[]): void;

    // Rimuove punti nel range (per refresh)
    invalidateRange(start: string, end: string): void;

    // Svuota tutto
    invalidateAll(): void;
}
```

- **Struttura interna**: `Map<string, T>` (chiave = data ISO `YYYY-MM-DD`)
- **`getMissingIntervals(start, end)`**: scansiona il range e restituisce gli intervalli dove non ci sono dati, raggruppati in sub-range contigui (per minimizzare le chiamate)
- **Riusabile** per FX (`FxDataPoint`), Asset (`AssetPricePoint`), Dashboard (Phase 8)

### Registry Condivisa — `src/lib/stores/fxStoreRegistry.ts`

```typescript
// Map globale: slug coppia → istanza TimeSeriesStore
const fxStores: Map<string, TimeSeriesStore<FxDataPoint>> = new Map();

function getFxStore(slug: string): TimeSeriesStore<FxDataPoint> {
    if (!fxStores.has(slug)) {
        fxStores.set(slug, new TimeSeriesStore<FxDataPoint>());
    }
    return fxStores.get(slug)!;
}
```

**Condivisione**: la stessa istanza è usata dalla `FxCard` nella lista e dalla pagina dettaglio `/fx/[pair]`. Navigando dalla card al dettaglio i dati sono già presenti; il chart chiede solo i gap per range estesi. Se si arriva direttamente al dettaglio via URL, la registry crea una nuova istanza.

### EditBuffer<T> — `src/lib/stores/EditBuffer.ts`

Companion di `TimeSeriesStore` per gestire gli edit pendenti in modo bidirezionale (chart ↔ CSV):

```typescript
interface PendingEdit<T> {
    id: string;          // UUID univoco
    point: T;            // Il data point modificato/aggiunto
    csvLineNumber: number; // Riga corrispondente nel CSV
    source: 'click' | 'csv' | 'form'; // Come è stato creato
}
```

- Click su punto nel chart → aggiunge a `EditBuffer` + scrive riga nel CSV
- Modifica riga CSV → aggiorna punto nel `EditBuffer` + aggiorna preview chart
- Pulsante "+" → aggiunge a `EditBuffer` + scrive riga nel CSV
- Click su punto arancione nel chart → trova `PendingEdit` per ID → scrolla textarea alla riga
- Save → raccoglie tutti i `PendingEdit` → bulk `POST /fx/currencies/rate` → merge in `TimeSeriesStore` → svuota buffer
- Cancel → svuota buffer

Riusabile per Asset (Phase 6).

### FxDataPoint — Tipo specifico FX

```typescript
interface FxDataPoint {
    date: string;                  // ISO YYYY-MM-DD
    rate: number;                  // Tasso di conversione
    backward_fill_info?: {
        actual_rate_date: string;
        days_back: number;         // = staleDays per gradiente
    } | null;
}
```

Derivato dal response di `POST /fx/currencies/convert` con `from_amount: {code: base, amount: 1}`:
- `rate` = `FXConversionResult.rate`
- `backward_fill_info` = `FXConversionResult.backward_fill_info`
- `staleDays` per gradiente opacità = `backward_fill_info.days_back` (0 se null)

---

## Libreria Chart — `src/lib/components/charts/`

Componenti ECharts modulari, ognuno autonomo e riusabile. Implementazione incrementale: prima MVP, poi avanzati.

### Componenti

| Componente | Descrizione | Priorità | Riusato da |
|---|---|---|---|
| `LineChart.svelte` | Linea con gradiente stale (`opacity = max(0.3, 1.0 - staleDays * 0.15)`) + area fill opzionale | 🟢 MVP | FX (default), Asset, Dashboard |
| `CandlestickChart.svelte` | Candele OHLC sintetizzate client-side. FX: O=close giorno precedente, C=rate odierno, H=max(O,C), L=min(O,C). Asset: dati reali OHLC se disponibili. | 🟡 Secondo | FX (opzionale), Asset |
| `VolumeBar.svelte` | Barre variazione % giornaliera (verde positivo, rosso negativo). Ispirato al sub-chart di `candlestick-large` di ECharts. Per FX mostra Δ% dal giorno precedente. | 🟡 Secondo | FX, Asset |
| `DataZoomBar.svelte` | Slider/brush per zoomare su finestra più ristretta del range caricato. Fisso sotto il sub-chart. | 🟢 MVP | FX, Asset, Dashboard |
| `ChartToolbar.svelte` | Switch Line/Candlestick, toggle Absolute/Percentage, range presets (1W, 1M, 3M, 6M, 1Y, ALL) | 🟢 MVP | FX detail, Asset detail |
| `MeasureOverlay.svelte` | Click-drag su chart → freccia tendenza on-the-fly + info box con: valore partenza, valore arrivo, Δ assoluto, Δ%, intervallo giorni | 🟡 Secondo | FX detail, Asset detail |
| `EditPopup.svelte` | Click singolo su data point → popup con input numerico per modificare il rate (attivo solo in edit mode). Dopo modifica aggiorna `EditBuffer` e riga CSV. | 🟡 Secondo | FX detail, Asset detail |
| `SemiDonutChart.svelte` | **Estratto da `BrokerSharingModal.svelte`** — semicerchio ownership con avatar. Refactor: la modale importa il nuovo componente. | 🟢 MVP (refactor) | Broker sharing, Dashboard futuro |
| `PriceChartFull.svelte` | Compositore: assembla LineChart/Candlestick + VolumeBar + DataZoomBar + ChartToolbar + MeasureOverlay + EditPopup. Gestisce la comunicazione tra sotto-componenti. | 🟢 MVP (incrementale) | FX detail, Asset detail |
| `PriceChartCompact.svelte` | Solo LineChart in miniatura, senza toolbar/zoom/edit. Per card nelle liste. | 🟢 MVP | FX card, Asset card |

### Note implementative

- **Gradiente stale**: `opacity = Math.max(0.3, 1.0 - staleDays * 0.15)` — dopo ~5 giorni stale, opacità fissa a 0.3
- **Candlestick sintetizzato** (FX): Le banche centrali non forniscono dati intraday, quindi OHLC è simulato: Open = Close del giorno precedente, Close = rate odierno, High = max(Open, Close), Low = min(Open, Close). Nota visibile nella UI: "Simulated OHLC from daily close rates"
- **Toggle Absolute/Percentage**: In modalità percentuale, tutti i valori sono espressi come variazione rispetto al primo punto visibile nella finestra (base = 0%)
- **MeasureOverlay**: Click su punto A, drag a punto B → freccia con info box: `Start: 1.0823 (2025-06-15)`, `End: 1.1045 (2025-09-20)`, `Δ: +0.0222 (+2.05%)`, `Days: 97`
- **Dark mode**: tutti i componenti supportano dark mode leggendo `document.documentElement.classList.contains('dark')`
- **ResizeObserver**: tutti i chart hanno ResizeObserver per responsività

### Estrazione SemiDonutChart

Il codice del semicerchio ECharts attualmente inline in `BrokerSharingModal.svelte` (linee ~255-430) viene estratto come componente autonomo `SemiDonutChart.svelte`. La modale broker sharing lo importa come:

```svelte
<SemiDonutChart
    data={ownerSlices}
    availableLabel={$_('brokers.sharing.available')}
    height="180px"
/>
```

---

## Pagine FX

### 1. Pagina Lista — `/fx`

**Route**: `src/routes/(app)/fx/+page.svelte` (riscrittura del placeholder attuale)

#### Barra Superiore (Filtri + Azioni globali)

- **Filtro valuta 2-step**: primo `SearchSelect` per inserire la 1ª valuta → filtra le card che contengono quella valuta. Una volta selezionata appare un secondo `SearchSelect` per la 2ª valuta (opzionale, restringe a quella coppia esatta). L'ordine non conta (coppie reversibili).
- **Date range globale**: due input date (start/end) con pulsante "Applica" → quando applicato, riconfigura i range di tutte le card
- **Pulsante "Sync All"** → apre `FxSyncModal`
- **Pulsante "Refresh All"** → invalida cache di tutte le card + re-fetch
- **Pulsante "Add Pair"** → apre `FxPairAddModal`

#### Griglia FxCard (responsive 1–3 colonne)

Ogni card rappresenta una coppia unica, derivata da `GET /api/v1/fx/providers/pair-sources` (raggruppate per coppia base/quote unica):

- **Header card**: "🇪🇺 EUR → 🇺🇸 USD" con flag emoji + pulsante **swap ⇄** (inverte visivamente la coppia)
- **Ultimo tasso**: valore numerico prominente + variazione % rispetto al giorno precedente (verde/rosso)
- **Mini-chart**: `PriceChartCompact` alimentato dalla `TimeSeriesStore` condivisa (dalla registry)
- **Pulsanti**:
  - Refresh (locale) — invalida cache di questa coppia + re-fetch
  - Edit (matita) → apre `FxPairEditModal` per configurare provider/priorità
  - Delete (cestino) → `ConfirmModal` con checkbox "Also delete historical rates"
- **Click sulla card** → naviga a `/fx/EUR-USD` (detail page)

#### API utilizzate

| Endpoint | Metodo | Uso |
|---|---|---|
| `/api/v1/fx/providers/pair-sources` | GET | Lista coppie configurate → genera le card |
| `/api/v1/fx/currencies/convert` | POST | Per ogni coppia, `{from_amount: {code: "EUR", amount: 1}, to: "USD", date_range: {start, end}}` → dati chart |
| `/api/v1/utilities/currencies?language={lang}` | GET | Nomi localizzati + simboli per i `SearchSelect` |

#### Performance

Ogni card lancia la propria `POST /fx/currencies/convert` indipendente — il backend gestisce il parallelismo con asyncio. L'endpoint convert accetta già range di date in una singola richiesta, quindi 1 call per coppia è sufficiente. La `TimeSeriesStore` fa sì che solo i gap mancanti vengano richiesti.

### 2. Pagina Dettaglio — `/fx/[pair]`

**Route**: `src/routes/(app)/fx/[pair]/+page.svelte` + `+page.ts`

**Slug**: ordine **alfabetico** (come il backend) — es. `/fx/EUR-USD`. Il pulsante swap ⇄ inverte solo la visualizzazione (la label diventa "USD → EUR" e i valori sono 1/rate), non il route.

#### Header

- Flag + "🇪🇺 EUR → 🇺🇸 USD" + pulsante swap ⇄
- Ultimo tasso + Δ% + data ultimo aggiornamento
- Pulsanti: **Back** (freccia ←), **Refresh** (locale), **Sync** (locale per questa coppia), **Edit Mode** (matita)

#### Chart Principale — `PriceChartFull`

Tutti i controlli:
- **ChartToolbar**: switch Line/Candlestick, toggle Absolute/Percentage, range presets (1W/1M/3M/6M/1Y/ALL)
- **LineChart** (default per FX) o **CandlestickChart** (selezionabile)
- **VolumeBar**: sotto il chart, barre Δ% giornaliera
- **DataZoomBar**: slider/brush per zoomare
- **MeasureOverlay**: click-drag per freccia tendenza + info box metriche
- **EditPopup**: click su punto per modifica (solo in edit mode)

#### Date Range Locale

Input date start/end sotto il chart (override del date range globale). Il chart chiede alla sua `TimeSeriesStore` i dati mancanti tramite la logica gap-filling.

#### Sezione Edit Mode

Attivata dal pulsante **"Edit"** nell'header. Quando attiva:

1. **Chart interattivo**: click su punto → `EditPopup` → modifica locale nel `EditBuffer`. Se il punto è un pending edit (arancione), il click:
   - **Scrolla automaticamente la textarea CSV alla riga corrispondente**
   - Apre l'`EditPopup` col valore attuale
   - Dopo modifica nel popup, la riga CSV si aggiorna col nuovo valore

2. **Pulsante "+"**: picker data + campi base (ISO), quote (ISO), valore base2quote → aggiunge punto arancione nel chart + riga in fondo al CSV

3. **Textarea CSV** con header obbligatorio: `date;base;quote;base2quote`
   - **Numeri di riga** a sinistra (stile mini-editor di codice)
   - **Validazione live per riga**: sfondo verde ✅ se valida (data parsabile, codici ISO validi, valore numerico > 0), sfondo rosso ❌ con messaggio errore
   - Punti validi mostrati nel chart in **colore arancione** come preview
   - Righe con errori non bloccano le altre
   - **Bidirezionale**: ogni edit via click-to-edit o "+" scrive automaticamente una riga nel CSV. Ogni modifica nel CSV aggiorna la preview nel chart.
   - **Info box ℹ️** con link a `user/fx-csv-format.md` (pagina di documentazione)

4. Dopo la prima modifica appaiono **"Save"** (verde) e **"Cancel"** (rosso):
   - **Save** → raccoglie tutti gli edit dall'`EditBuffer` → `POST /api/v1/fx/currencies/rate` (bulk) → aggiorna `TimeSeriesStore` coi risultati → esce da edit mode
   - **Cancel** → svuota `EditBuffer` → esce da edit mode

#### Sezione Configurazione Provider (sotto il chart)

Ispirata ai **mockup POC UX** (tree view):

- Lista provider per questa coppia con **priority** (numero), drag-reorder o input numerico
- Per ogni provider: badge con nome (ECB, FED, BOE, SNB), icona, `fetch_interval` (minuti)
- Pulsante **"Add Provider"** → riga con `SimpleSelect` provider + input priority
- Pulsante **Delete** per ogni provider → `ConfirmModal`
- **Placeholder "Intermediate Route — Coming Soon"** (per cross-rate futuro USD→EUR→RON) — icona lock + testo esplicativo

**API**:
- `GET /api/v1/fx/providers/pair-sources` (filtrato per questa coppia)
- `POST /api/v1/fx/providers/pair-sources` (bulk upsert)
- `DELETE /api/v1/fx/providers/pair-sources`
- `GET /api/v1/fx/providers` (lista provider disponibili)

#### API Dettaglio — Riepilogo

| Endpoint | Metodo | Uso |
|---|---|---|
| `/api/v1/fx/currencies/convert` | POST | Dati chart (amount=1, date range) |
| `/api/v1/fx/currencies/rate` | POST | Salvataggio edit manuali (bulk) |
| `/api/v1/fx/currencies/rate` | DELETE | Cancellazione rate (se richiesta da delete coppia) |
| `/api/v1/fx/currencies/sync` | GET | Sync locale per questa coppia |
| `/api/v1/fx/providers/pair-sources` | GET/POST/DELETE | CRUD configurazione provider |
| `/api/v1/fx/providers` | GET | Lista provider disponibili |
| `/api/v1/utilities/currencies` | GET | Nomi/simboli localizzati |

### 3. Modali

#### FxPairAddModal

- `ModalBase` con:
  - `SearchSelect` per base currency
  - `SearchSelect` per quote currency
  - Sezione configurazione provider: lista con `SimpleSelect` provider + input priority + drag-reorder
  - Pulsante "Add Provider" per aggiungere fallback
  - `fetch_interval` (opzionale)
- Validazione: base ≠ quote, almeno 1 provider
- Salvataggio: `POST /api/v1/fx/providers/pair-sources`

#### FxPairEditModal

Stessa struttura dell'Add, ma con coppia fissa (non modificabile). Provider pre-caricati dalla configurazione esistente.

#### FxSyncModal

- `ModalBase` con:
  - Date range picker (start + end)
  - Multi-currency chips selector (con `SearchSelect` per aggiungere valute)
  - Provider override opzionale (`SimpleSelect` con opzione "Use Configuration" di default)
  - ⚠️ **Warning banner arancione**: "This operation will overwrite existing rates in the selected range"
  - `ConfirmModal` di conferma prima di procedere
- Flusso: conferma → `GET /api/v1/fx/currencies/sync` → progress bar pending → risultato "N rates synced" → auto-refresh dei chart per area sincronizzata

---

## Documentazione Utente GUI (MkDocs)

### Nuove pagine

Tutte con screenshot gallery usando il pattern `<div class="screenshot-container"><img class="gallery-img" data-category="..." data-name="..." alt="..."></div>`:

| Pagina | Path | Screenshot gallery usati | Contenuto |
|---|---|---|---|
| **Brokers** | `user/brokers.en.md` | `brokers/list`, `brokers/detail`, `brokers/import-modal`, `brokers/sharing-modal` | Come creare un broker, significato dei campi (name, description, portal URL, default import plugin, allow cash overdraft, allow asset shorting), come fare upload file per BRIM, come funziona il broker sharing (ruoli Owner/Editor/Viewer, share percentage, warning >100%) |
| **Files** | `user/files.en.md` | `files/static-tab`, `files/static-grid`, `files/brim-tab` | Upload file, uso della tabella (filtri, colonne, azioni, vista griglia/lista), differenza file statici (generici, documenti) vs file BRIM (report broker per import), associazione file a broker |
| **Settings** | `user/settings.en.md` | `settings/profile`, `settings/user-preferences`, `settings/password-modal`, `settings/about` | Profilo (avatar, email, username), preferenze utente (lingua, valuta default, tema), come resettare la password, come eliminare l'account, tab About |
| **Global Settings (Admin)** | `admin/global-settings.en.md` | `settings/global-settings` | Parametri globali (auto-sync, registrazione aperta, ecc.), differenza tra utente normale e superutente, chi può accedere a questa sezione |
| **FX Rates** | `user/fx-rates.en.md` | *(nuovi screenshot da E2E Phase 5)* | Come leggere la pagina FX (card, filtri, date range), come navigare al dettaglio, come usare il chart (line/candlestick, zoom, measure), come sincronizzare i rate, come editare manualmente (click-to-edit, CSV, form "+"), come configurare i provider/priorità |
| **FX CSV Format** | `user/fx-csv-format.en.md` | — | Formato CSV dettagliato con header `date;base;quote;base2quote`. Spiegazione colonne: `date` = data ISO (YYYY-MM-DD), `base` = codice ISO 4217 valuta base (es. EUR), `quote` = codice ISO 4217 valuta quote (es. USD), `base2quote` = valore: quanto vale 1 unità di base in quote. Esempi completi, errori comuni (separatore virgola vs punto-virgola, ordine colonne), note sul backend (normalizza ordine alfabetico automaticamente) |

### Aggiornamento nav in mkdocs.yml

```yaml
  - User Manual:
      - Overview: user/index.md
      - Installation (Docker): user/installation.md
      - Brokers: user/brokers.md
      - Files: user/files.md
      - FX Rates: user/fx-rates.md
      - FX CSV Format: user/fx-csv-format.md
      - Settings: user/settings.md
  - Admin Manual:
      - Overview: admin/index.md
      - CLI Tools: admin/cli_tools.md
      - Advanced Docker: admin/docker_advanced.md
      - Exposing with Tailscale: admin/tailscale_exposure.md
      - Global Settings: admin/global-settings.md
```

### Aggiornamento user/index.md

Aggiungere link alle nuove pagine nella overview del manuale utente.

---

## i18n MkDocs Globale

### Evoluzione selettore lingua

Il `gallery-lang-selector.js` attuale:
- Appare **solo** nelle pagine gallery (`isGalleryPage()` check)
- Controlla solo la lingua delle immagini (`gallery-lang` in localStorage)

Evoluzione → **`site-lang-selector.js`** (rinominato):
- Appare **in tutte le pagine** (rimuovere check `isGalleryPage()`, rimuovere `body:not([data-gallery-page])` CSS hide rule)
- Quando l'utente seleziona una lingua:
  1. Aggiorna `gallery-lang` in localStorage (backward compatible per immagini)
  2. **Naviga alla versione tradotta della pagina corrente** — con `mkdocs-static-i18n`, la pagina IT di `/user/brokers/` è a `/it/user/brokers/`. Il JS costruisce il nuovo URL con il prefisso lingua e naviga.
  3. Se la pagina tradotta non esiste (404), fallback alla versione inglese
- Il `gallery-img-loader.js` continua a funzionare (legge `gallery-lang`), ma ora la lingua immagini si sincronizza con la lingua della pagina
- Aggiornare `gallery-img-loader.js` per leggere anche la lingua dal path URL (`/it/...`) se disponibile, come fallback rispetto a localStorage

### Configurazione `mkdocs-static-i18n`

La dipendenza è **già nel Pipfile** (`mkdocs-static-i18n = "*"`). Aggiungere in `mkdocs.yml`:

```yaml
plugins:
  - i18n:
      default_language: en
      languages:
        en: English
        it: Italiano
        fr: Français
        es: Español
```

### Rename file — approccio suffix-based

**Sezioni traducibili** — file da rinominare `*.md` → `*.en.md`:

| Sezione | File |
|---|---|
| Home | `index.md` → `index.en.md` |
| FAQ | `faq.md` → `faq.en.md` |
| Getting Started | `getting-started/introduction.md` → `.en.md`, `getting-started/installation.md` → `.en.md` |
| User Manual | `user/index.md` → `.en.md`, `user/installation.md` → `.en.md` |
| Admin Manual | `admin/index.md` → `.en.md`, `admin/cli_tools.md` → `.en.md`, `admin/docker_advanced.md` → `.en.md`, `admin/tailscale_exposure.md` → `.en.md` |
| Tutorials | `tutorials/track-first-stock.md` → `.en.md`, `tutorials/track-p2p-loan.md` → `.en.md` |
| Gallery | `gallery/index.md` → `.en.md`, `gallery/desktop.md` → `.en.md`, `gallery/mobile.md` → `.en.md` |
| Credits | `credits-legal.md` → `.en.md` |

**Totale**: ~18 file da rinominare.

**Sezioni solo inglese** (developer/, financial-theory/, POC_UX/): ~46 file — **restano `.md` senza suffisso**. Il plugin li tratta come lingua default (EN) e non genera varianti. Non servono traduzioni per contenuto tecnico.

### Traduzioni progressive

Phase 5 **non include** la traduzione effettiva delle pagine in IT/FR/ES — solo l'infrastruttura (plugin, rename, selettore, nuove pagine EN). Le traduzioni `.it.md`, `.fr.md`, `.es.md` vengono create progressivamente in seguito. Documentare in TODO_FUTURI.md.

---

## Implementation Steps

### Step 1 — TimeSeriesStore + EditBuffer + Registry

**File da creare**:
```
src/lib/stores/TimeSeriesStore.ts      # Cache generica <T extends {date: string}>
src/lib/stores/EditBuffer.ts           # Buffer edit pendenti bidirezionale
src/lib/stores/fxStoreRegistry.ts      # Map globale slug → TimeSeriesStore<FxDataPoint>
```

**Tasks**:
- [x] Implementare `TimeSeriesStore<T>` con `getRange`, `getMissingIntervals`, `merge`, `invalidateRange`, `invalidateAll`
- [x] Implementare `EditBuffer<T>` con `add`, `update`, `remove`, `getAll`, `getByDate`, `getCsvLines`, `clear`
- [x] Implementare `fxStoreRegistry` con `getFxStore(slug)`, `invalidateAll()`
- [x] Definire `FxDataPoint` interface
- [ ] Test unitari per TimeSeriesStore e EditBuffer

### Step 2 — Libreria Chart MVP

**File da creare**:
```
src/lib/components/charts/LineChart.svelte
src/lib/components/charts/DataZoomBar.svelte
src/lib/components/charts/ChartToolbar.svelte
src/lib/components/charts/PriceChartCompact.svelte
src/lib/components/charts/PriceChartFull.svelte
src/lib/components/charts/SemiDonutChart.svelte
src/lib/components/charts/CandlestickChart.svelte     # stub
src/lib/components/charts/VolumeBar.svelte             # stub
src/lib/components/charts/MeasureOverlay.svelte        # stub
src/lib/components/charts/EditPopup.svelte             # stub
src/lib/components/charts/index.ts                     # barrel export
```

**Tasks**:
- [x] Creare `LineChart.svelte` — ECharts line series con gradiente stale, area fill, dark mode, ResizeObserver
- [x] Creare `DataZoomBar.svelte` — ECharts dataZoom slider
- [x] Creare `ChartToolbar.svelte` — switch Line/Candlestick, toggle Abs/%, range presets
- [x] Creare `PriceChartCompact.svelte` — solo LineChart in miniatura
- [x] Creare `PriceChartFull.svelte` — compositore (inizialmente solo LineChart + DataZoom + Toolbar)
- [x] Estrarre `SemiDonutChart.svelte` da `BrokerSharingModal.svelte` → refactor la modale per importare il nuovo componente
- [x] Creare stub per: `CandlestickChart`, `VolumeBar`, `MeasureOverlay`, `EditPopup`
- [x] `index.ts` barrel export

### Step 3 — Pagina Lista FX + FxCard

**File da creare/modificare**:
```
src/routes/(app)/fx/+page.svelte           # riscrittura
src/lib/components/fx/FxCard.svelte        # nuovo
src/lib/components/fx/index.ts             # barrel export
```

**Tasks**:
- [x] Riscrivere `fx/+page.svelte` con barra filtri (SearchSelect 2-step, date range globale, Sync All, Refresh All, Add Pair)
- [x] Creare `FxCard.svelte` con header (flag+coppia+swap+Δ%), `PriceChartCompact`, pulsanti refresh/edit/delete
- [x] Caricare pair-sources da `GET /fx/providers/pair-sources`, raggruppare per coppia unica
- [x] Per ogni coppia: `POST /fx/currencies/convert` (amount=1) → alimenta `TimeSeriesStore` dalla registry
- [x] Click card → `goto('/fx/EUR-USD')`
- [ ] Implementare logica Sync All (apre modal) e Refresh All (invalida tutte le cache)

### Step 4 — Pagina Dettaglio FX + Edit Mode

**File da creare**:
```
src/routes/(app)/fx/[pair]/+page.svelte
src/routes/(app)/fx/[pair]/+page.ts
src/lib/components/fx/FxEditSection.svelte        # sezione edit mode con CSV + form "+"
src/lib/components/fx/FxProviderConfig.svelte      # config provider tree view
src/lib/components/fx/CsvEditor.svelte             # textarea CSV con numeri riga + validazione
```

**Tasks**:
- [x] Creare `+page.ts` con parsing slug `[pair]` → `{base, quote}`
- [x] Creare `+page.svelte` con header, `PriceChartFull`, edit section, provider config
- [x] Swap ⇄ inverte solo visualizzazione (non route)
- [x] Implementare `CsvEditor.svelte`: textarea con numeri riga a sinistra, validazione live (verde/rosso per riga), parsing header `date;base;quote;base2quote`
- [x] Implementare `FxEditSection.svelte`: toggle edit mode, `CsvEditor`, pulsante "+", `EditPopup` integrazione, Save/Cancel bulk, info box ℹ️ con link a docs
- [ ] Bidirezionalità: click chart → scroll CSV + open popup; modifica CSV → aggiorna chart preview; modifica popup → aggiorna riga CSV
- [x] Implementare `FxProviderConfig.svelte`: tree view provider/priority, add/delete, drag-reorder, `fetch_interval`, placeholder "Intermediate Route — Coming Soon"
- [x] Refresh locale + Sync locale (pending → auto-refresh)

### Step 5 — Modali FX

**File da creare**:
```
src/lib/components/fx/FxPairAddModal.svelte
src/lib/components/fx/FxPairEditModal.svelte
src/lib/components/fx/FxSyncModal.svelte
```

**Tasks**:
- [x] `FxPairAddModal`: `ModalBase` + 2x `SearchSelect` (base/quote) + config provider con priority
- [x] `FxPairEditModal`: `ModalBase` + coppia fissa + config provider (riusa struttura dell'Add)
- [x] `FxSyncModal`: `ModalBase` + date range + chips valute + provider override + warning banner + progress pending

### Step 6 — Componenti Chart Avanzati

**File da completare** (erano stub):
```
src/lib/components/charts/CandlestickChart.svelte
src/lib/components/charts/VolumeBar.svelte
src/lib/components/charts/MeasureOverlay.svelte
src/lib/components/charts/EditPopup.svelte
```

**Tasks**:
- [ ] Completare `CandlestickChart.svelte` con OHLC sintetizzato + nota "Simulated OHLC"
- [ ] Completare `VolumeBar.svelte` con barre Δ% (verde/rosso)
- [x] Completare `MeasureOverlay.svelte` con click-drag → freccia time-axis aligned + info box (Δ assoluto, Δ%, giorni, valori start/end). Freccia punta sempre avanti nel tempo.
- [ ] Completare `EditPopup.svelte` con popup numerico + integrazione `EditBuffer`
- [x] Integrare `MeasureOverlay` in `PriceChartFull.svelte` con toggle "Measure" in toolbar
- [x] `DateRangePicker` custom dual-calendar: popover Svelte con 2 mesi affiancati, click su 2 date, range highlight, hover preview, Escape/click-outside per chiudere
- [x] `LineChart` colori % segmentati: ECharts `visualMap` pieces, rosso sotto 0%, verde sopra, con area fill dinamica + markLine a y=0 + nota informativa "% relative to day 0"
- [x] `LineChart` asse Y: sempre visibile con valori, sia in modalità assoluta che percentuale
- [x] `LineChart` ↔ `DataZoomBar` zoom bidirezionale: chart emette `onZoomChange` → aggiorna `DataZoomBar`; `DataZoomBar` aggiorna chart
- [x] `FxCard` toggle abs/%: bottone 📊 nel header per switchare tra valore assoluto e percentuale, con colore linea dinamico

### Step 7 — i18n MkDocs

**Tasks**:
- [ ] Aggiungere sezione `plugins` con `i18n` in `mkdocs.yml`
- [ ] Rinominare ~18 file traducibili `*.md` → `*.en.md` (sezioni: Home, FAQ, Getting Started, User, Admin, Tutorials, Gallery, Credits)
- [ ] Aggiornare nav in `mkdocs.yml` (i riferimenti restano senza suffisso, il plugin risolve)
- [ ] Rinominare `gallery-lang-selector.js` → `site-lang-selector.js`
- [ ] Rimuovere check `isGalleryPage()` e regola CSS `body:not([data-gallery-page])`
- [ ] Aggiungere logica navigazione a pagina tradotta (costruisce URL con prefisso lingua)
- [ ] Aggiungere fallback: se pagina tradotta 404, resta sulla versione inglese
- [ ] Aggiornare `gallery-img-loader.js` per leggere lingua dal path URL come fallback
- [ ] Aggiornare riferimenti in `mkdocs.yml` extra_javascript (rinominare file JS)
- [ ] Testare con `./dev.py mkdocs serve`

### Step 8 — Documentazione Utente

**File da creare**:
```
mkdocs_src/docs/user/brokers.en.md
mkdocs_src/docs/user/files.en.md
mkdocs_src/docs/user/settings.en.md
mkdocs_src/docs/user/fx-rates.en.md
mkdocs_src/docs/user/fx-csv-format.en.md
mkdocs_src/docs/admin/global-settings.en.md
```

**Tasks**:
- [ ] Scrivere `user/brokers.en.md` con screenshot gallery (broker list, detail, import modal, sharing modal)
- [ ] Scrivere `user/files.en.md` con screenshot gallery (static tab, grid view, brim tab)
- [ ] Scrivere `user/settings.en.md` con screenshot gallery (profile, preferences, password, about)
- [ ] Scrivere `admin/global-settings.en.md` con screenshot gallery (global settings)
- [ ] Scrivere `user/fx-rates.en.md` con screenshot gallery (nuovi da E2E Phase 5)
- [ ] Scrivere `user/fx-csv-format.en.md` — formato CSV dettagliato, esempi, errori comuni
- [ ] Aggiornare `user/index.en.md` con link alle nuove pagine
- [ ] Aggiornare nav in `mkdocs.yml`

### Step 9 — i18n Frontend + E2E + Cleanup

**Tasks**:
- [ ] Aggiungere ~50 chiavi i18n in EN/IT/FR/ES via `./dev.py i18n add` per: card FX, chart toolbar, edit mode, CSV editor, sync modal, pair config, filtri, conferme delete, errori
- [ ] Scrivere E2E test Playwright per: griglia card, filtro valuta 1-step e 2-step, date range globale, swap coppia, CRUD pair sources, sync con risultato, chart rendering (line + candlestick), edit mode (CSV + click-to-edit + form "+"), delete con conferma, dark mode
- [ ] Generare gallery screenshot FX (light/dark, 4 lingue)
- [ ] Aggiungere cross-rate a `TODO_FUTURI.md`
- [ ] Aggiungere roadmap traduzioni MkDocs progressive a `TODO_FUTURI.md`
- [ ] Aggiornare `phases/phase-05-fx.md` con riferimento a questo plan

---

## i18n Keys (Frontend)

```
fx.title, fx.subtitle, fx.syncRates, fx.syncAll, fx.refreshAll, fx.addPair,
fx.filter.firstCurrency, fx.filter.secondCurrency, fx.filter.dateRange,
fx.filter.apply, fx.filter.clear,
fx.card.lastRate, fx.card.change, fx.card.swap, fx.card.refresh,
fx.card.edit, fx.card.delete, fx.card.deleteConfirm,
fx.card.deleteAlsoRates, fx.card.deleteAlsoRatesHint,
fx.detail.back, fx.detail.refresh, fx.detail.sync, fx.detail.editMode,
fx.chart.line, fx.chart.candlestick, fx.chart.absolute, fx.chart.percentage,
fx.chart.simulatedOhlc, fx.chart.staleData, fx.chart.noData,
fx.chart.measure.start, fx.chart.measure.end, fx.chart.measure.delta,
fx.chart.measure.percent, fx.chart.measure.days,
fx.edit.title, fx.edit.save, fx.edit.cancel, fx.edit.addPoint,
fx.edit.csvPlaceholder, fx.edit.csvInfo, fx.edit.csvInfoLink,
fx.edit.csvError, fx.edit.csvValid, fx.edit.csvLineError,
fx.edit.pending, fx.edit.savedSuccess, fx.edit.savedError,
fx.pair.add, fx.pair.edit, fx.pair.base, fx.pair.quote,
fx.pair.provider, fx.pair.priority, fx.pair.fetchInterval,
fx.pair.addProvider, fx.pair.deleteProvider, fx.pair.deleteConfirm,
fx.pair.intermediateRoute, fx.pair.comingSoon,
fx.sync.title, fx.sync.dateRange, fx.sync.startDate, fx.sync.endDate,
fx.sync.currencies, fx.sync.providerOverride, fx.sync.useConfig,
fx.sync.warningOverwrite, fx.sync.syncing, fx.sync.result,
fx.sync.ratesSynced, fx.sync.confirm, fx.sync.error
```

---

## E2E Test Ideas

- [ ] Pagina lista: griglia card visibile con flag + coppia + tasso
- [ ] Filtro 1ª valuta → card filtrate
- [ ] Filtro 2ª valuta → singola card visibile
- [ ] Date range globale → tutti i chart aggiornati
- [ ] Swap coppia su card → label e valore invertiti
- [ ] Click card → navigazione a dettaglio
- [ ] Dettaglio: chart line visibile con DataZoom
- [ ] Switch a Candlestick → chart cambia tipo
- [ ] Toggle Percentage → valori in %
- [ ] Range preset 1M → zoom automatico
- [ ] Edit mode: click su punto → popup edit
- [ ] Edit mode: modifica CSV → preview arancione nel chart
- [ ] Edit mode: pulsante "+" → riga aggiunta al CSV + punto nel chart
- [ ] Edit mode: click punto arancione → scroll textarea
- [ ] Edit mode: Save → rate salvati, edit mode chiuso
- [ ] Edit mode: Cancel → tutto annullato
- [ ] CRUD pair source: add provider con priority
- [ ] CRUD pair source: delete provider
- [ ] Sync modal: conferma → pending → risultato
- [ ] Refresh → dati ricaricati
- [ ] Delete coppia → card rimossa
- [ ] Dark mode coerente su tutti i componenti

---

## File Creati/Modificati (Riepilogo)

### Nuovi file frontend
```
src/lib/stores/TimeSeriesStore.ts
src/lib/stores/EditBuffer.ts
src/lib/stores/fxStoreRegistry.ts
src/lib/components/charts/LineChart.svelte
src/lib/components/charts/CandlestickChart.svelte
src/lib/components/charts/VolumeBar.svelte
src/lib/components/charts/DataZoomBar.svelte
src/lib/components/charts/ChartToolbar.svelte
src/lib/components/charts/MeasureOverlay.svelte
src/lib/components/charts/EditPopup.svelte
src/lib/components/charts/SemiDonutChart.svelte
src/lib/components/charts/PriceChartFull.svelte
src/lib/components/charts/PriceChartCompact.svelte
src/lib/components/charts/index.ts
src/lib/components/fx/FxCard.svelte
src/lib/components/fx/FxEditSection.svelte
src/lib/components/fx/FxProviderConfig.svelte
src/lib/components/fx/CsvEditor.svelte
src/lib/components/fx/FxPairAddModal.svelte
src/lib/components/fx/FxPairEditModal.svelte
src/lib/components/fx/FxSyncModal.svelte
src/lib/components/fx/index.ts
src/routes/(app)/fx/+page.svelte              # riscrittura
src/routes/(app)/fx/[pair]/+page.svelte       # nuovo
src/routes/(app)/fx/[pair]/+page.ts           # nuovo
```

### File frontend modificati
```
src/lib/components/brokers/BrokerSharingModal.svelte  # estrazione SemiDonutChart
```

### Nuovi file documentazione
```
mkdocs_src/docs/user/brokers.en.md
mkdocs_src/docs/user/files.en.md
mkdocs_src/docs/user/settings.en.md
mkdocs_src/docs/user/fx-rates.en.md
mkdocs_src/docs/user/fx-csv-format.en.md
mkdocs_src/docs/admin/global-settings.en.md
```

### File documentazione rinominati (~18)
```
mkdocs_src/docs/index.md → index.en.md
mkdocs_src/docs/faq.md → faq.en.md
mkdocs_src/docs/credits-legal.md → credits-legal.en.md
mkdocs_src/docs/getting-started/introduction.md → .en.md
mkdocs_src/docs/getting-started/installation.md → .en.md
mkdocs_src/docs/user/index.md → .en.md
mkdocs_src/docs/user/installation.md → .en.md
mkdocs_src/docs/admin/index.md → .en.md
mkdocs_src/docs/admin/cli_tools.md → .en.md
mkdocs_src/docs/admin/docker_advanced.md → .en.md
mkdocs_src/docs/admin/tailscale_exposure.md → .en.md
mkdocs_src/docs/tutorials/track-first-stock.md → .en.md
mkdocs_src/docs/tutorials/track-p2p-loan.md → .en.md
mkdocs_src/docs/gallery/index.md → .en.md
mkdocs_src/docs/gallery/desktop.md → .en.md
mkdocs_src/docs/gallery/mobile.md → .en.md
```

### File documentazione modificati
```
mkdocs_src/mkdocs.yml                                    # plugins i18n, nav aggiornata
mkdocs_src/docs/javascripts/gallery-lang-selector.js     # → site-lang-selector.js (rinominato + evoluto)
mkdocs_src/docs/javascripts/gallery-img-loader.js        # aggiornato per leggere lingua da path URL
```

### File vari
```
TODO_FUTURI.md                                            # cross-rate, traduzioni MkDocs progressive
```

---

## Dipendenze tra Steps

```
Step 1 (TimeSeriesStore)
    │
    ├──→ Step 2 (Chart Library MVP)
    │       │
    │       ├──→ Step 3 (Lista FX + FxCard)
    │       │       │
    │       │       └──→ Step 4 (Dettaglio FX + Edit Mode)
    │       │               │
    │       │               └──→ Step 5 (Modali FX)
    │       │
    │       └──→ Step 6 (Chart Avanzati) ←── può procedere in parallelo con Step 4-5
    │
    Step 7 (i18n MkDocs) ←── indipendente, può procedere in parallelo con Step 2-6
    │
    └──→ Step 8 (Documentazione Utente) ←── dipende da Step 7 (rename file) + Step 3-4 (screenshot FX)
         │
         └──→ Step 9 (i18n Frontend + E2E + Cleanup) ←── dopo tutto il resto
```

