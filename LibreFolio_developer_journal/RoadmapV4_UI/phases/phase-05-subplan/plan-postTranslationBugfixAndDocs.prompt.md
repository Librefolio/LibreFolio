# Plan: Piano di Rientro — Bug Frontend + Correzioni Docs + Artefatti Traduzione

**Data creazione**: 22 Marzo 2026
**Status**: ✅ COMPLETATO
**Priorità**: Alta (blocca il consolidamento Phase 5)
**Stima**: ~3-4 giorni
**Completato**: 22 Marzo 2026
**Dipendenze**: `plan-mkdocsI18nPipeline.prompt.md` completato ✅, traduzione completa (97/100 → 100/100) ✅

### Progress Tracking

| Blocco | Task | Status |
|--------|------|--------|
| **A1** | Valute filtro dopo delete | ✅ Completato |
| **A2** | FxPairSignal % mode | ✅ Completato |
| **A3** | Colori segnali distanti | ✅ Completato |
| **A4** | FxPairSignal pulsanti (fix `pairSlug`) | ✅ Completato |
| **A5** | Tabelle Files ridimensionamento | ✅ Completato (min-width: 0 + overflow) |
| **A6** | Nomi segnali tradotti | ✅ Verificato — chiavi i18n presenti in 4 lingue |
| **A7** | Mock data saldi cash negativi | ✅ Completato (DEGIRO deposit 5K→10K) |
| **B1** | FAQ licenza AGPL-3.0 (EN+IT+FR+ES) | ✅ Completato |
| **B2** | FAQ banner feature request (EN+IT+FR+ES) | ✅ Completato |
| **B3** | FAQ troubleshooting generalizzato (EN+IT+FR+ES) | ✅ Completato |
| **B4** | Files/Brokers chiarire BRIM (EN+IT+FR+ES) | ✅ Completato |
| **B5** | Sync dati sovrascritti (EN+IT+FR+ES) | ✅ Completato |
| **B6** | Provider fallback multipli prima (EN+IT+FR+ES) | ✅ Completato |
| **B7** | Chart rimuovere candlestick + Abs/% (EN+IT+FR+ES) | ✅ Completato |
| **B8** | Signals rimuovere Fast/Slow EMA (EN+IT+FR+ES) | ✅ Completato |
| **B9** | Measures emoji 📐→📏 (EN+IT+FR+ES) | ✅ Completato |
| **B10** | Data Editor sovrascrittura + cache (EN+IT+FR+ES) | ✅ Completato |
| **B11** | Chart Settings persistenza (EN+IT+FR+ES) | ✅ Completato |
| **B12** | Linear Growth dividendi/reinvestimento (EN+IT+FR+ES) | ✅ Completato |
| **B13** | Transaction types colonne Cash/Asset + `<strong>` (EN+IT+FR+ES) | ✅ Completato |
| **B14** | Nuova pagina Taxation (EN+IT+FR+ES) | ✅ Completato |
| **C1** | Icone rotte non-EN (index + asset/transaction-types) | ✅ Completato (fix path relativi IT+FR+ES) |
| **C2** | Scroll preservation 2-fase | ✅ Completato |
| **C3** | Sync docs↔app bidirezionale | ✅ Completato |
| **C4** | Footnote fix manuali (4 file) | ✅ Completato |
| **C4** | Footnote pipeline `_clean_translation()` | ✅ Completato |
| **C4** | Footnote pipeline `check_artifacts()` | ✅ Completato |
| **C5** | Provider IT heading fuso | ✅ Completato |
| **C6** | `<strong>` in `<td>` (IT+FR+ES) | ✅ Completato |
| **C7** | Admonition indent fix (173 righe, 51 file) | ✅ Completato |
| **C7** | Admonition indent check pipeline | ✅ Completato |
| **C8** | Allineamento lingua iniziale | ✅ Risolto con C3 |
| **D1** | Propagare fix EN a IT+FR+ES | ✅ Completato (strutturali diretti, non via agente) |
| **D2** | Validazione post-traduzione | ✅ Build pulito, zero errori |
| **D3** | Fix post-traduzione C6/C7 | ✅ Inline con D1 |
| **D4** | Build finale `--strict` | ✅ Build 6.72s, 0 errori, 0 warning |

---

## Contesto

Dopo il completamento della pipeline di traduzione i18n MkDocs con Aphra (Step 1–6.5), una sessione di test manuale ha rivelato ~35 problemi distribuiti su 4 aree:

1. **Bug frontend** (7): regressioni funzionali nell'app SvelteKit
2. **Errori contenuto EN** (14): imprecisioni, informazioni errate, contenuto mancante nella documentazione sorgente inglese
3. **Artefatti traduzione** (8): footnote del traduttore non rimossi, heading fusi, indentazione persa, path immagini rotti nelle versioni tradotte
4. **Ri-traduzione** (3): ri-tradurre i file EN modificati, validare, build finale

Tutti i fix vanno completati in questa iterazione. I blocchi A (frontend) e B+C (docs) sono parallelizzabili. Il blocco D (ri-traduzione) dipende dal completamento di B+C.

---

## Blocco A — Bug Frontend (Funzionalità)

### A1. Valute nel filtro non aggiornate dopo delete coppia

**File**: `frontend/src/routes/(app)/fx/+page.svelte`

`configuredCurrencies` (riga 99) è `$derived` da `pairs` e si aggiorna correttamente quando `confirmDelete()` rimuove un elemento da `pairs` (riga 379). Il bug è che `filterCurrency1` / `filterCurrency2` possono restare settati su una valuta che non esiste più dopo la delete.

**Fix**: in `confirmDelete()`, dopo `pairs = pairs.filter(...)`, aggiungere un reset condizionale:

```typescript
// Reset filters if selected currency no longer exists
const remaining = new Set(pairs.flatMap(p => [p.config.base, p.config.quote]));
if (filterCurrency1 && !remaining.has(filterCurrency1)) filterCurrency1 = '';
if (filterCurrency2 && !remaining.has(filterCurrency2)) filterCurrency2 = '';
```

---

### A2. Switch % non ricalcola FxPairSignal nella detail page

**File**: `frontend/src/lib/charts/signals/FxPairSignal.ts`, `frontend/src/lib/charts/signals/ChartSignal.ts`

In `ChartSignal.render()` (riga 273), la conversione in % usa `baseData[0].value` come `p0` per tutti i segnali su asse primario. Per `FxPairSignal`, il cui range di valori è completamente diverso dal base chart (es. EUR/USD ~1.10 vs GBP/JPY ~190), la normalizzazione rispetto a `p0` del base produce valori insensati.

**Fix**: override `render()` in `FxPairSignal` per normalizzare rispetto al *proprio* primo valore (`absData[0].value`), così entrambe le curve partono da 0% e sono confrontabili:

```typescript
// In FxPairSignal.ts
override render(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal {
    const absData = this.computePoints(baseData);
    let data = absData;
    if (viewMode === 'percentage' && absData.length > 0) {
        const p0 = absData[0].value; // Normalize to OWN first value, not base chart
        if (p0 !== 0) {
            data = absData.map(d => ({
                ...d,
                value: ((d.value - p0) / p0) * 100,
            }));
        }
    }
    return {
        id: this.id, label: this.getLabel(), data,
        color: this.style.color, lineWidth: this.style.lineWidth,
        lineType: this.style.lineType,
        markerStart: this.style.markerStart, markerEnd: this.style.markerEnd,
        yAxisIndex: 0,
    };
}
```

---

### A3. Colori segnali troppo simili a quelli già presenti

**File**: `frontend/src/lib/charts/signals/registry.ts`

In `createSignal()` (riga 80), il colore viene scelto con `existingCount % 6` dalla palette `DEFAULT_SIGNAL_COLORS`. Questo non considera i colori già in uso (dal grafico base, dagli altri segnali), producendo potenziali collisioni.

**Fix**: cambiare la firma di `createSignal()` per ricevere anche i colori già in uso, e scegliere dalla palette il colore con massima distanza hue circolare:

```typescript
export function createSignal(
    signalType: string,
    existingCount: number,
    usedColors?: string[],  // hex colors already in use
): ChartSignal | null {
    // ...existing logic...
    const color = pickBestColor(usedColors ?? []);
    // ...rest...
}

/** Pick the palette color with max min-distance from all usedColors (hue-based). */
function pickBestColor(usedColors: string[]): string {
    if (!usedColors.length) return DEFAULT_SIGNAL_COLORS[0];
    const usedHues = usedColors.map(hexToHue);
    let bestColor = DEFAULT_SIGNAL_COLORS[0];
    let bestDist = -1;
    for (const c of DEFAULT_SIGNAL_COLORS) {
        const h = hexToHue(c);
        const minDist = Math.min(...usedHues.map(uh => {
            const d = Math.abs(h - uh);
            return Math.min(d, 360 - d); // circular hue distance
        }));
        if (minDist > bestDist) { bestDist = minDist; bestColor = c; }
    }
    return bestColor;
}

function hexToHue(hex: string): number {
    const r = parseInt(hex.slice(1,3), 16) / 255;
    const g = parseInt(hex.slice(3,5), 16) / 255;
    const b = parseInt(hex.slice(5,7), 16) / 255;
    const max = Math.max(r,g,b), min = Math.min(r,g,b), d = max - min;
    if (d === 0) return 0;
    let h = 0;
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    return ((h * 60) + 360) % 360;
}
```

Aggiornare tutti i callsite di `createSignal()` per passare i colori in uso.

---

### A4. FxPairSignal: pulsanti "vai al detail" e "sync range"

**File**: `frontend/src/lib/components/charts/ChartSignalsSection.svelte`

Nella card di ogni segnale con `signalType === 'fx-pair'`, aggiungere due icon-button:

1. **ExternalLink** → naviga a `/fx/{pairSlug}` (callback `ondetailpair(slug)`)
2. **RotateCw** → sync il range corrente per quella coppia (callback `onsyncpair(slug)`)

Aggiornare l'interfaccia `Props` per accettare i due nuovi callback. Il parent (`[pair]/+page.svelte`) implementa `onsyncpair` chiamando l'API convert per il range corrente.

---

### A5. Tabelle Files non si ridimensionano

**File**: `frontend/src/lib/components/files/FilesTable.svelte`, `frontend/src/lib/components/table/DataTable.svelte`

Le tabelle nella pagina Files non si ridimensionano più correttamente. Investigare con devtools se:
- Un wrapper `div` ha `overflow: hidden` anziché `auto`
- Manca un `min-width: 0` su un flex child
- Un cambio CSS recente (Tailwind v4 upgrade) ha alterato il layout

Probabile causa: il DataTable è wrappato in un flex container dove manca `min-w-0` o `overflow-x-auto`. Fixare il layout.

---

### A6. Nomi segnali non tradotti (sempre in inglese)

**File**: `frontend/src/lib/charts/signals/*.ts`, `frontend/src/lib/components/charts/ChartSignalsSection.svelte`, `frontend/src/lib/components/charts/ChartSettingsModal.svelte`

I `displayName` statici nelle classi signal (es. `'Linear Growth'`, `'EMA'`) sono in inglese hardcoded. La UI in `ChartSignalsSection.svelte` (riga 69) traduce correttamente via `$t('chartSettings.signals.${key}')`. 

**Verifiche**:
1. Che `ChartSettingsModal` usi lo stesso mapping i18n `SIGNAL_TYPE_I18N_KEY` nei dropdown "Add signal"
2. Che tutte le chiavi `chartSettings.signals.*` e `chartSettings.params.*` esistano in `it.json`, `fr.json`, `es.json`
3. Se mancanti, aggiungerle con `./dev.py i18n add`

Le chiavi EN esistono già (confermate: `en.json` righe 565–591). Verificare le traduzioni IT/FR/ES con `./dev.py i18n audit`.

---

### A7. Mock data: saldi cash negativi con overdraft disabilitato

**File**: `backend/test_scripts/test_db/populate_mock_data.py`

Tutti i broker hanno `allow_cash_overdraft: False` e `allow_asset_shorting: False`, ma le transazioni mock generate probabilmente producono BUY/WITHDRAWAL che portano il saldo cash sotto zero.

**Fix**: nella funzione che genera transazioni, calcolare un saldo cash running e:
- Non generare `BUY` che renderebbero il cash negativo
- Non generare `WITHDRAWAL` superiori al saldo disponibile
- Assicurare che i `DEPOSIT` iniziali siano sufficienti a coprire le operazioni successive

---

## Blocco B — Correzioni Documentazione EN + Nuovi Contenuti

### B1. FAQ: licenza AGPL-3.0 (non MIT)

**File**: `mkdocs_src/docs/faq.en.md` riga 14

Il progetto usa la licenza **GNU Affero General Public License v3** (file `LICENCE` alla root). Correggere:

```diff
- Yes! LibreFolio is completely free and open-source under the MIT license.
+ Yes! LibreFolio is completely free and open-source under the [AGPL-3.0 license](https://www.gnu.org/licenses/agpl-3.0.html).
```

---

### B2. FAQ: banner "feature request"

**File**: `mkdocs_src/docs/faq.en.md`

Dopo il blocco "What assets can I track?", aggiungere:

```markdown
!!! tip "Missing something? 💡"
    If there's an asset class or feature you'd like to see that we haven't thought of yet, we'd love to hear from you! Open a [feature request on GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement&template=feature_request.md) and let us know.
```

---

### B3. FAQ: troubleshooting generalizzato (asset + FX)

**File**: `mkdocs_src/docs/faq.en.md`, sezione "My prices aren't updating"

Generalizzare: parlare di "asset data provider" con yfinance come esempio principale. Aggiungere un punto per FX rates:

```markdown
### 📉 My prices aren't updating

Check that:

1. Auto-sync is enabled in Global Settings
2. Your assets have valid ISINs or symbols recognized by the configured **data provider** (e.g., [yfinance](https://pypi.org/project/yfinance/) — the default provider for stocks and ETFs)
3. The provider's service is available (check server logs for errors)

For **FX rates**, verify that:

1. The currency pair has at least one [data provider configured](user/fx/detail/provider.md)
2. The provider's API is reachable (ECB, FED, BOE, SNB)
3. You've run a [sync](user/fx/sync.md) for the desired date range
```

---

### B4. Files/Brokers: chiarire associazione BRIM

**File**: `mkdocs_src/docs/user/files/index.en.md`, sezione "Broker Reports"

Chiarire che:
- L'utente sceglie a quale broker **associare** il file caricato
- L'analisi del formato (riconoscimento plugin BRIM) è indipendente dal broker
- Più broker possono accettare lo stesso formato/plugin BRIM
- Il parsing effettivo avviene in uno step successivo (WIP)

---

### B5. Sync: i dati vengono sovrascritti, non preservati

**File**: `mkdocs_src/docs/user/fx/sync.en.md`

Correggere la sezione "How Sync Works" e l'admonition "No duplicate data":

```markdown
## ⚙️ How Sync Works

The sync process:

1. Fetches rates from the configured provider's API (ECB, FED, BOE, SNB, etc.)
2. **Overwrites** existing data points in the downloaded date range with the provider's values — the provider is treated as the authoritative source
3. Adds new data points for dates not yet in the database
4. If the primary provider fails, the system automatically falls back to the next configured provider

After sync, you'll see the number of **points downloaded** and how many were **actually new** (not previously present in the database).

!!! warning "Provider is authoritative"
    Re-syncing a pair will overwrite any manually edited values in the synced date range. If you need to preserve manual edits, consider using a pair configured with the [MANUAL provider](detail/provider.md) (no automatic data source).

!!! info "Chain conversion precision"
    When using chain routes (e.g., RON → EUR → JPY), each intermediate conversion introduces a minimal rounding error. While negligible for most purposes, be aware that chain-converted rates may differ slightly from direct market quotes.
```

---

### B6. Provider: menzionare fallback multipli prima nella guida

**File**: `mkdocs_src/docs/user/fx/detail/provider.en.md`

Nella sezione "Changing Providers" (riga 29), anticipare la possibilità di più provider:

```markdown
## 🔧 Changing Providers

You can configure **one or more** data providers for each pair. Multiple providers act as a **fallback chain** — if the primary source fails, the system automatically tries the next one.

To change or add providers:

1. Open the Provider Configuration modal
2. **Remove** the current route if needed
3. **Add a new route** — the system will discover available routes (same as when [adding a new pair](../add-pair.md))
4. **Reorder** routes to set priorities (drag & drop or arrow buttons)
5. Select the new route and **confirm**

The next sync will fetch data from the highest-priority available provider.
```

---

### B7. Chart/Detail: rimuovere Candlestick per FX, aggiungere Abs/%

**File**: `mkdocs_src/docs/user/fx/detail/chart.en.md`

Riscrivere la sezione "Chart Types" (righe 11–18): rimuovere riferimento candlestick (non implementato per FX, sarà per gli asset). Al suo posto spiegare il toggle **Abs / %**:

```markdown
## 🔀 View Modes

Toggle between two display modes using the toolbar:

- 📈 **Absolute** — Shows the raw exchange rate values (e.g., 1 EUR = 1.0845 USD)
- 📊 **Percentage (%)** — Shows the percentage change from the first visible data point (useful for comparing relative movements)

When switching to % mode, all overlay signals are also recalculated as percentages from their respective starting points.
```

Nella sezione "Toolbar" (riga 49–50), correggere i preset temporali:

```markdown
- 📊 **View mode toggle** — Absolute / Percentage
- ⏱️ **Time range** — 1W, 1M, 3M, 6M, 1Y, 2Y, Custom

!!! info "Data availability"
    If the selected time range exceeds the available data, LibreFolio displays whatever is available. Use **Sync** to try fetching older data from the provider — but note that some providers have limited historical coverage.
```

---

### B8. Signals: rimuovere Fast/Slow EMA, ristrutturare per FX

**File**: `mkdocs_src/docs/user/fx/detail/signals.en.md`

Ristrutturare la sezione EMA (righe 13–18): rimuovere il riferimento "Fast EMA / Slow EMA" (quello è il MACD). Ogni indicatore diventa un breve intro con significato nel contesto FX + link alla teoria finanziaria:

```markdown
### 📉 [EMA — Exponential Moving Average](../../../financial-theory/technical-indicators.md#ema)

Smooths daily rate noise to reveal the **underlying trend**. In FX, an EMA crossing above the rate line often suggests a weakening base currency (or strengthening quote currency). Configurable period: shorter = more reactive, longer = smoother.
```

---

### B9. Measures: emoji 📐→📏

**File**: `mkdocs_src/docs/user/fx/detail/measures.en.md`

Cambiare l'emoji del pulsante misure da 📐 (squadra/triangolo) a 📏 (righello) dove si riferisce al pulsante nell'UI. Verificare che il link al rendimento annualizzato (riga 34–36) punti correttamente a `financial-theory/returns.md`.

---

### B10. Data Editor: correggere semantica sovrascrittura + cache locale

**File**: `mkdocs_src/docs/user/fx/detail/data-editor.en.md`

1. **Riga 41–42** — Correggere il warning errato:

```markdown
!!! warning "Synced data overwrites manual edits"
    If you manually edit a data point and then run a sync that covers the same date, the provider's value will **overwrite** your manual edit. The provider is always treated as the authoritative source. For pairs where you want full manual control, use the [MANUAL provider](provider.md) (no automatic data source).
```

2. **Sezione "Merge Behavior"** (righe 147–155) — Aggiungere nota sulla cache locale:

```markdown
### 🔀 Merge Behavior

When importing via CSV or adding points manually in the editor:

- Changes are first applied to the **local client cache** (visible immediately in the chart)
- Changes are **not persisted** to the database until you click **Save**
- 🔄 **Existing data points** in the database will be **overwritten** with the imported values upon save
- 🆕 **New dates** are added
- ✅ **Dates not in the import** are left untouched
```

3. Aggiungere nota che l'editor ha più senso per coppie MANUAL (senza provider automatico).

---

### B11. Chart Settings: persistenza con scadenza cache browser

**File**: `mkdocs_src/docs/user/fx/chart-settings.en.md`

Aggiungere alla fine della sezione sulla persistenza:

```markdown
!!! info "Persistence"
    Chart settings are stored in your browser's `localStorage` and survive across sessions — even after closing and reopening the browser. They will be lost only if you clear your browser cache/storage or if the storage expires (browser-dependent, typically months to years).
```

---

### B12. Linear Growth: dividendi, reinvestimento, intro a tassazione

**File**: `mkdocs_src/docs/financial-theory/synthetic-benchmarks.en.md`

Ampliare la sezione "Financial Meaning" della Linear Growth (righe 19–23):

```markdown
### 💡 Financial Meaning

A linear growth benchmark represents **simple interest** — the value increases by a
fixed absolute amount each period. This models the scenario where you **do not reinvest**
earnings (dividends, interest, coupons): cash payouts are received but kept aside.

If instead you **reinvest** those earnings — either manually or automatically through
accumulating instruments (e.g., accumulating ETFs, which reinvest dividends internally
and benefit from [tax deferral](taxation.md#deferral-advantage)) — you should expect
**compound growth**, where returns generate further returns.

In practice, the difference between linear and compound growth widens dramatically over
long horizons. This is why the Linear benchmark appears as a straight line while the
[Compound benchmark](#compound-growth) curves upward exponentially.

!!! abstract "Capital gains & losses"
    When selling an asset above its purchase price, the difference is a **capital gain**
    (plusvalenza); below, a **capital loss** (minusvalenza). Each jurisdiction has its
    own rules regarding tax rates, holding period thresholds, loss carry-forward duration,
    and matching methods (FIFO, LIFO, specific identification). For a theoretical overview,
    see [Taxation](taxation.md).
```

---

### B13. Transaction types: colonne Cash/Asset + fix `<strong>` in `<td>`

**File**: `mkdocs_src/docs/financial-theory/transaction-types.en.md`

1. Aggiungere 2 colonne alla tabella HTML: **Cash** e **Asset** con emoji frecce per mostrare l'effetto:

| Type | Cash | Asset |
|------|------|-------|
| BUY | ⬇️ | ⬆️ |
| SELL | ⬆️ | ⬇️ |
| DIVIDEND | ⬆️ | — |
| INTEREST | ⬆️ | — |
| DEPOSIT | ⬆️ | — |
| WITHDRAWAL | ⬇️ | — |
| FEE | ⬇️ | — |
| TAX | ⬇️ | — |
| FX_CONVERSION | ⬆️⬇️ | — |
| TRANSFER_IN | — | ⬆️ |
| TRANSFER_OUT | — | ⬇️ |
| ADJUSTMENT | ⬆️⬇️ | ⬆️⬇️ |

2. Convertire tutti i `**...**` markdown inside `<td>` → `<strong>...</strong>` (markdown non renderizza dentro tag HTML raw).

---

### B14. NUOVA: pagina Taxation (`financial-theory/taxation.en.md`)

**File da creare**: `mkdocs_src/docs/financial-theory/taxation.en.md`

Contenuto (solo EN per ora, traduzione in Blocco D):

```
# 💰 Taxation & Tax Efficiency

## 📊 Capital Gains & Losses
- Definizione teorica: plusvalenza vs minusvalenza
- Realized vs unrealized gains
- Matching methods: FIFO, LIFO, specific identification (teoria, non giurisdizione-specifica)

## 🔄 Loss Carry-Forward (Compensazione)
- Concetto: compensare plusvalenze con minusvalenze
- Nota: ogni giurisdizione ha durata diversa (es. 4 anni IT, illimitato DE, 3 anni US wash sale rule)

## ⏳ Tax Deferral Advantage (#deferral-advantage)
- Formula matematica: confronto rendimento netto con tassazione immediata vs differita
- Esempio numerico: 10 anni, 7% annuo, 26% aliquota → differenza significativa
- Collegamento a Compound Growth (synthetic-benchmarks.md)

## 📦 Accumulating vs Distributing Instruments
- ETF ad accumulo: dividendi reinvestiti internamente, nessun evento tassabile fino alla vendita
- ETF a distribuzione: dividendi pagati → tassazione immediata
- Vantaggio matematico dell'accumulo su orizzonti lunghi

## ⚠️ Jurisdiction Disclaimer
- Nota prominente: ogni stato ha regole proprie
- Soglie, aliquote, holding period, scadenza minusvalenze, doppia imposizione
- LibreFolio non fornisce consulenza fiscale
```

**Aggiungere al `nav:`** in `mkdocs_src/mkdocs.yml` sotto Financial Theory, dopo "Synthetic Benchmarks":

```yaml
      - Taxation & Tax Efficiency: financial-theory/taxation.md
```

---

## Blocco C — Artefatti Traduzione & Fix i18n MkDocs

### C1. Icone/immagini rotte su pagine non-EN (path relativi)

**File affetti**: `index.{it,fr,es}.md`, `financial-theory/asset-types.{it,fr,es}.md`, `financial-theory/transaction-types.{it,fr,es}.md`

**Problema**: il plugin `mkdocs-static-i18n` con suffix strategy genera URL come `/it/financial-theory/asset-types/`. I path relativi `../../static/icons/...` nelle pagine profonde funzionano per EN (che sta a `/financial-theory/asset-types/`), ma per le versioni tradotte l'URL ha un livello in più (`/it/...`).

**Nota dalla scoperta pipeline**: "il `nav:` deve usare path SENZA suffisso lingua. Il plugin risolve automaticamente." — i file `.it.md` vivono nella stessa cartella dei `.en.md`, ma l'URL generata ha il prefisso `/it/`.

**Fix (nei file sorgente EN, propagato poi via traduzione)**:

Per la **homepage** (`index.en.md`): i path `src="static/logo.png"` sono relativi alla pagina corrente. Nella versione EN la URL è `/` quindi `static/logo.png` → `/static/logo.png` ✅. Nella versione IT la URL è `/it/` quindi `static/logo.png` → `/it/static/logo.png` ❌.

Soluzione: usare path assoluti con il site base path. Siccome MkDocs Material non supporta Jinja in `.md`, usare la convenzione con `../`:

- **`index.en.md`**: le immagini `src="static/..."` → nessun `../` necessario per EN. Per le versioni i18n, il path deve salire di 1 livello.

Alternativa più robusta: far gestire al **gallery-img-loader.js** anche le icone della homepage e delle tabelle asset-types/transaction-types, con lo stesso meccanismo `data-*` delle gallery images. Oppure, fixare i path tradotti direttamente nei file `.{it,fr,es}.md` aggiungendo un `../` extra.

**Decisione**: fixare i path nei file tradotti aggiungendo il livello extra `../`. Poi migliorare `_clean_translation()` per preservare i path `src=` identici al sorgente (non dovrebbe alterarli, ma verificare).

Per i file in `financial-theory/`: i path `../../static/icons/...` sono corretti sia per EN che per le versioni tradotte (entrambe hanno la stessa profondità di cartella nel filesystem sorgente, e il plugin genera URL con la stessa profondità + prefisso lingua). **Verificare** con `mkdocs build --strict` se effettivamente il problema è solo sulla homepage.

---

### C2. Scroll preservation con immagini lazy-loaded

**File**: `mkdocs_src/docs/javascripts/site-lang-selector.js` (righe 342–353)

**Problema**: lo scroll viene ripristinato con un singolo `requestAnimationFrame` che esegue prima che le immagini siano caricate. La pagina ha un'altezza diversa da quella salvata, quindi lo scroll finisce nel punto sbagliato.

**Fix a 2 fasi**:

```javascript
// Replace the current scroll restoration (lines 342-353) with:
var savedPct = sessionStorage.getItem('docs-scroll-pct');
if (savedPct !== null) {
    sessionStorage.removeItem('docs-scroll-pct');
    var pct = parseFloat(savedPct);
    if (!isNaN(pct) && pct > 0) {
        var userScrolled = false;
        
        // Phase 1: Apply immediately after layout
        requestAnimationFrame(function () {
            var targetY = pct * document.documentElement.scrollHeight;
            window.scrollTo(0, targetY);
        });
        
        // Track if user manually scrolls (don't override their intent)
        var onUserScroll = function () { userScrolled = true; };
        window.addEventListener('scroll', onUserScroll, { passive: true });
        
        // Phase 2: Re-apply after all images loaded (if user hasn't scrolled)
        window.addEventListener('load', function () {
            window.removeEventListener('scroll', onUserScroll);
            if (!userScrolled) {
                requestAnimationFrame(function () {
                    var targetY = pct * document.documentElement.scrollHeight;
                    window.scrollTo(0, targetY);
                });
            }
        });
        
        // Safety: clean up scroll listener after 10s regardless
        setTimeout(function () {
            window.removeEventListener('scroll', onUserScroll);
        }, 10000);
    }
}
```

---

### C3. Sync tema/lingua docs → app mancante (bidirezionale)

**File**: `mkdocs_src/docs/javascripts/app-sync.js`, `mkdocs_src/docs/javascripts/site-lang-selector.js`

**Problema attuale**: il sync funziona solo **app → docs**:
- `app-sync.js`: `syncTheme()` legge `librefolio-theme` → scrive palette MkDocs
- `app-sync.js`: `syncLanguage()` legge `librefolio-locale` → scrive `gallery-lang`

Manca il **docs → app**:
- Quando l'utente cambia lingua nel selettore docs, `gallery-lang` viene scritto ma `librefolio-locale` no
- Quando l'utente clicca il toggle palette Material, la palette MkDocs cambia ma `librefolio-theme` no

**Fix 1 — Lingua docs → app**: in `site-lang-selector.js`, nella funzione `saveLang()` (riga 119–122), aggiungere:

```javascript
function saveLang(lang) {
    localStorage.setItem(STORAGE_KEY, lang);
    // Sync to SvelteKit app (reverse direction)
    localStorage.setItem('librefolio-locale', lang);
    window.dispatchEvent(new CustomEvent('gallery-lang-change', {detail: {lang}}));
}
```

**Fix 2 — Tema docs → app**: in `app-sync.js`, aggiungere un observer sul toggle palette Material:

```javascript
// ── Reverse theme sync: MkDocs palette → app ──
function watchPaletteToggle() {
    var toggles = document.querySelectorAll('[data-md-component=palette] input');
    toggles.forEach(function (toggle) {
        toggle.addEventListener('change', function () {
            // Read which scheme is now active
            var scheme = document.body.getAttribute('data-md-color-scheme');
            var appTheme = (scheme === 'slate') ? 'dark' : 'light';
            localStorage.setItem('librefolio-theme', appTheme);
        });
    });
}

// Run after DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', watchPaletteToggle);
} else {
    watchPaletteToggle();
}
```

**Fix 3 — Sync iniziale senza cambio lingua**: il problema "se non si cambia la lingua non si allinea" è perché `syncLanguage()` scrive `gallery-lang` solo se `librefolio-locale` esiste. Se l'utente non ha mai aperto l'app (nessun `librefolio-locale` in localStorage), il docs resta in EN. Questo è il comportamento corretto: la lingua di default è EN. Documentare questo flow.

---

### C4. Note Traduttore e footnote `[^N]:` — fix manuale + miglioramento pipeline

#### Fix manuali nei file già tradotti:

| File | Problema | Azione |
|------|----------|--------|
| `user/fx/detail/signals.it.md` riga 65 | Sezione `## 📝 Note del Traduttore` | Rimuovere intera sezione (da riga 65 a fine file) |
| `user/fx/detail/provider.es.md` righe 67–74 | 7 footnote `[^1]:`…`[^7]:` | Rimuovere tutte le righe, rimuovere i `[^N]` inline nel testo |
| `financial-theory/day-count.it.md` righe 12, 54 | `[^1]` inline + definizione `[^1]:` in fondo | Rimuovere entrambi |
| `financial-theory/synthetic-benchmarks.it.md` righe 153–162 | 9 footnote `[^1]:`…`[^9]:` | Rimuovere tutte le definizioni in fondo, rimuovere i `[^N]` inline |

#### Miglioramento `_clean_translation()` in `translate_docs.py`:

Aggiungere 2 nuovi pattern dopo il punto 4 esistente:

```python
# 5. Remove footnote definitions [^N]: ... (LLM translator notes disguised as footnotes)
#    These are NOT standard markdown footnotes from the source — the EN source has none.
#    They appear only in translations as "Translator Notes" in footnote format.
text = re.sub(r'^\[\^\d+\]:.*$', '', text, flags=re.MULTILINE)

# 6. Remove inline footnote references [^N] (not markdown links)
text = re.sub(r'\[\^\d+\]', '', text)

# 7. Clean up blank lines left by removed footnotes (collapse 3+ blank lines to 2)
text = re.sub(r'\n{3,}', '\n\n', text)
```

#### Miglioramento `check_artifacts()` in `validate_translations.py`:

Aggiungere check per footnote:

```python
# Footnote definitions [^N]: (translator notes in disguise)
footnote_defs = re.findall(r'^\[\^\d+\]:.*$', translated, re.MULTILINE)
if footnote_defs:
    issues.append(Issue(
        severity=Severity.WARN,
        file=cache_key, lang=lang,
        check="artifact-footnote-defs",
        message=f"Footnote definitions found ({len(footnote_defs)}): "
                f"likely translator notes in footnote format",
    ))

# Inline footnote references [^N]
footnote_refs = re.findall(r'\[\^\d+\]', translated)
if footnote_refs:
    issues.append(Issue(
        severity=Severity.WARN,
        file=cache_key, lang=lang,
        check="artifact-footnote-refs",
        message=f"Inline footnote refs found ({len(footnote_refs)}): [{'], ['.join(footnote_refs[:5])}]",
    ))
```

---

### C5. Provider IT: heading fuso con testo

**File**: `mkdocs_src/docs/user/fx/detail/provider.it.md` riga 40

Testo attuale (heading e contenuto fusi sulla stessa riga):
```
## 🔢 Priorità & fallbackQuando sono configurati più percorsi per una coppia:
```

**Fix**:
```markdown
## 🔢 Priorità & Fallback

Quando sono configurati più percorsi per una coppia:
```

---

### C6. `<strong>` in `<td>` — tutte le lingue

**File**: `mkdocs_src/docs/financial-theory/transaction-types.{en,it,fr,es}.md`

Il markdown `**...**` dentro tag HTML `<td>` non viene renderizzato come grassetto. Convertire tutte le occorrenze in `<strong>...</strong>`.

File affetti (IT verificato, cercare pattern anche in FR/ES):
- `transaction-types.it.md`: righe 21, 27, 75, 81, 87 — `**posizioni**`, `**in**`, `**da**`
- Verificare e fixare anche EN (riga 75: `*into*`, riga 81: `*out of*` — usano `*` corsivo, non `**` grassetto, ma convertire comunque a `<em>` per sicurezza).

---

### C7. Admonition con contenuto fuori dal blocco (indentazione persa)

**File noto**: `mkdocs_src/docs/admin/cli_tools.it.md` riga 5–6

L'admonition ha l'indentazione compressa dalla traduzione:

```markdown
!!! info "👩‍💻 Per Sviluppatori"
 Per i comandi specifici...    ← solo 1 spazio, serve 4
```

**Fix manuale**: ripristinare l'indentazione a 4 spazi per il contenuto dell'admonition.

**Fix sistematico**: cercare in tutti i file tradotti (`*.{it,fr,es}.md`) admonition con contenuto non correttamente indentato. Pattern di ricerca:

```bash
grep -n -P '^!!! ' mkdocs_src/docs/**/*.{it,fr,es}.md
# Poi verificare che la riga successiva abbia 4 spazi di indentazione
```

**Miglioramento pipeline** — aggiungere `check_admonitions()` in `validate_translations.py`:

```python
def check_admonitions(source: str, translated: str, cache_key: str, lang: str) -> list[Issue]:
    """Check that admonition content lines are properly indented (4 spaces)."""
    issues = []
    lines = translated.splitlines()
    for i, line in enumerate(lines):
        if re.match(r'^!!! \w+', line) or re.match(r'^\?\?\? \w+', line):
            # Check next non-empty line for proper indentation
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = lines[j]
                if next_line.strip() == '':
                    continue
                if next_line.startswith('    ') or next_line.startswith('!!! ') or next_line.startswith('---'):
                    break  # Properly indented or new block
                if next_line.strip():
                    issues.append(Issue(
                        severity=Severity.ERROR,
                        file=cache_key, lang=lang,
                        check="admonition-indent",
                        line=j + 1,
                        message=f"Admonition content not indented (needs 4 spaces): '{next_line.strip()[:50]}'",
                    ))
                    break
    return issues
```

---

### C8. Allineamento lingua iniziale (app → docs senza cambio manuale)

**Analisi**: il flusso attuale funziona così:
1. `app-sync.js` esegue prima di tutto: `syncLanguage()` copia `librefolio-locale` → `gallery-lang`
2. `site-lang-selector.js` `init()`: legge lingua da URL. Se URL = EN ma `gallery-lang` = IT → redirect a `/it/...`

Il caso "se non si cambia la lingua non si allinea" accade quando:
- L'utente apre i docs direttamente (non dall'app) → `librefolio-locale` non esiste ancora → nessun sync
- L'utente ha l'app aperta in IT ma apre docs in un'altra tab → `librefolio-locale` = `it` → il sync e redirect funzionano

**Verifica**: testare il flow end-to-end. Se il bug persiste, probabilmente il `syncLanguage()` non viene eseguito abbastanza presto (race condition con `site-lang-selector.js` `init()`). Verificare l'ordine di caricamento degli `extra_javascript` in mkdocs.yml:

```yaml
extra_javascript:
  - javascripts/app-sync.js              # ← DEVE essere PRIMA di site-lang-selector.js
  - javascripts/site-lang-selector.js
  - javascripts/gallery-img-loader.js
```

---

## Blocco D — Ri-traduzione e Validazione Finale

### D1. Ri-tradurre i file EN modificati

Dopo aver completato il Blocco B (correzioni EN) e i fix Blocco C (pipeline), eseguire:

```bash
./dev.py mkdocs translate
```

Il cache hash rileva automaticamente i file EN modificati e ri-traduce solo quelli. La nuova pagina `taxation.en.md` (B14) verrà tradotta come file nuovo. File che saranno ri-tradotti:

| File EN modificato | Step |
|---|---|
| `faq.en.md` | B1, B2, B3 |
| `user/files/index.en.md` | B4 |
| `user/fx/sync.en.md` | B5 |
| `user/fx/detail/provider.en.md` | B6 |
| `user/fx/detail/chart.en.md` | B7 |
| `user/fx/detail/signals.en.md` | B8 |
| `user/fx/detail/measures.en.md` | B9 |
| `user/fx/detail/data-editor.en.md` | B10 |
| `user/fx/chart-settings.en.md` | B11 |
| `financial-theory/synthetic-benchmarks.en.md` | B12 |
| `financial-theory/transaction-types.en.md` | B13 |
| `financial-theory/taxation.en.md` | B14 (nuovo) |

Stima: ~12 file × 3 lingue = 36 traduzioni. Con `stepfun/step-3.5-flash:free` → ~1-2h, costo $0.

### D2. Fix post-traduzione

Dopo la ri-traduzione, i miglioramenti a `_clean_translation()` (C4) dovrebbero prevenire i footnote `[^N]:`. Verificare con:

```bash
./dev.py mkdocs translate-validate
```

Fix manuale per eventuali artefatti residui.

### D3. Fix C6/C7 nei file ri-tradotti

I fix C6 (`<strong>` in `<td>`) e C7 (indentazione admonition) vanno ri-applicati nei file ri-tradotti se il modello li riproduce. Verificare con il validation script.

### D4. Build finale

```bash
cd mkdocs_src && pipenv run python -m mkdocs build --strict
```

Verificare zero warning. Controllare manualmente:
- Homepage (logo + icone asset) in tutte le lingue
- `financial-theory/asset-types` e `transaction-types` (icone tabella) in tutte le lingue
- Nuova pagina `taxation` in tutte le lingue
- Scroll preservation su cambio lingua in pagine con immagini

---

## Ordine di Esecuzione

```
┌─────────────────────────────┐  ┌──────────────────────────────────┐
│  Blocco A (Frontend bugs)   │  │  Blocco B (EN docs corrections)  │
│  A1–A7 (parallelizzabili)   │  │  B1–B14 (sequenziali)            │
│  ~1-2 giorni                │  │  ~1-2 giorni                     │
└─────────────────────────────┘  └──────────────────────────────────┘
                                          ↓
                                 ┌──────────────────────────────────┐
                                 │  Blocco C (Translation artifacts) │
                                 │  C1–C8 (mix manuale + pipeline)  │
                                 │  ~0.5 giorni                     │
                                 └──────────────────────────────────┘
                                          ↓
                                 ┌──────────────────────────────────┐
                                 │  Blocco D (Re-translate + validate│
                                 │  D1–D4                           │
                                 │  ~0.5 giorni                     │
                                 └──────────────────────────────────┘
```

A e B+C sono parallelizzabili. D dipende da B+C completati.

---

## Tempo Stimato Totale

| Blocco | Stima |
|--------|-------|
| A — Bug Frontend (7 fix) | ~1-2 giorni |
| B — Correzioni EN + Taxation page (14 task) | ~1-2 giorni |
| C — Artefatti traduzione + pipeline (8 task) | ~0.5 giorni |
| D — Ri-traduzione + validazione (4 task) | ~0.5 giorni |
| **Totale** | **~3-4 giorni** |

