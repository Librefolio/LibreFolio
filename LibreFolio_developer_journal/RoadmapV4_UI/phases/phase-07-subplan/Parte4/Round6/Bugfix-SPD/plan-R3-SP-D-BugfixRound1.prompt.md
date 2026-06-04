# Plan: R3-SP-D Bugfix Round 1 — Event Picker UX + WAC FX + Issue Index

**Date**: 2 Giugno 2026
**Status**: ✅ DONE (2026-06-04)
**Priority**: P1
**Parent**: [`plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md`](./plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md)
**Origin**: Walktest manuale post-implementazione SP-D

---

## 🎯 Obiettivo

Risolvere 8 bug + 3 miglioramenti estetici emersi dal walktest del plan SP-D (FormModal Props, Event Picker, WAC FX Feedback).

---

## Bug Inventory

| # | Area | Descrizione | Gravità |
|---|------|-------------|---------|
| **B1** | EventPicker | Dropdown illeggibile: doppia emoji, 6 decimali, "—" come not-set | Media |
| **B2** | EventPicker | Slider range max 90gg eccessivo → max 30 | Bassa |
| **B3** | BulkModal | Event cell mostra solo `#ID` invece di tipo+data+importo | Media |
| **B4** | BulkModal | **Issue row index sbagliato** — `issue.index` (posizione in creates[]/updates[]) usato direttamente come ops[] index + "Riga N" sbagliato + click non scrolla | **Alta** |
| **B5** | BulkModal | Banner issues: pairs senza bandiera, Sync FX button mancante | Media |
| **B6** | WacPreview | 3 bottoni sempre visibili (Add FX, Sync FX, Sync Prices) → logica contestuale mancante. Link `/fx` perde contesto. | Media |
| **B7** | Validation | Messaggio "Costo base obbligatorio" poco chiaro, parametri non in bold | Bassa |
| **B8** | FormModal | Asset type INDEX selezionabile (dovrebbe essere greyed out) | Bassa |

| # | Area | Miglioramento |
|---|------|---------------|
| **I1** | WacPreview | Badge `💱 FX` nel titolo sezione quando qualifying_txs hanno conversione FX |
| **I2** | WacPreview + Backend | Riga qualifying: freccia `originale → convertito` (richiede backend: `original_unit_cost` + `original_currency`) |
| **I3** | BulkModal | Event cell: mostrare emoji tipo + data breve (non solo #ID) |
| **I4** | EventPicker | Delta/spread tra TX cash e evento amount per aiutare la selezione |

---

## Decisioni di Design (feedback utente 2026-06-03)

| Decisione | Scelta | Rationale |
|---|---|---|
| Partner row index in banner | **Na/Nb notation** (es. "Riga 5a", "Riga 5b") | Per l'utente sono 1 riga visiva. Il frontend filtra il suffisso. |
| I2 — Original unit cost | **Backend change** (aggiungere `original_unit_cost` + `original_currency` + `fx_rate_used` a WACQualifyingTX) | Il dato esiste nel calcolo ma non viene propagato. |
| Mock data dates | **Relative** (`date.today() - timedelta(...)`) | Coerente con il resto di populate_mock_data.py (6 occorrenze relative). |
| Event picker spread | **Delta inline** (`Δ+0.01`) colorato verde/amber in base alla distanza | Aiuta scelta dell'evento giusto confrontando con draft.cash |
| Banner FX info (non stale) | **No banner separato** — solo il badge `💱 FX` nel titolo con Tooltip che mostra il disclaimer | Il tooltip è sufficiente, il banner info separato è ridondante con il badge e ruba spazio |
| Tono disclaimer FX | **Neutro/tecnico** | "Il tasso FX utilizzato potrebbe differire da quello applicato dal broker. Verifica il costo medio con il broker." |
| Sync FX success | **Toast verde + ri-validate** | Se dopo ri-validate ci sono ancora problemi → banner riappare naturalmente |
| Sync FX button: dove | **Solo nel banner issues** (BulkModal/FormModal in alto) | WacPreviewSection mostra solo dettagli/errori. L'azione Sync è nel banner globale. Da rimuovere il bottone dal WacPreview (implementato per errore in Step 6). |
| Tooltip FX | **Usa `html` prop** del Tooltip con `formatCurrencyCodeHtml` per formattare valute con bandiere | Coerente con il resto del progetto |
| Badge 💱 FX nel titolo | **Il badge ha un Tooltip** con il disclaimer FX (messaggio neutro sulle conversioni) | Nessun banner info separato: il tooltip del badge copre il caso "FX usato ma non stale" |
| fx_rate_used derivazione | **Calcolato in-place** nel `wac_service.py`: `rate = converted.amount / original_amount` | `convert_bulk` non ritorna il rate direttamente ma i dati per calcolarlo ci sono già (conversion lineare) |

---

## Step 1 — B4: Fix Issue Row Index Mapping (CRITICO) ✅ (2026-06-03)

### Root Cause

```javascript
// BulkModal.svelte:1798-1803
function jumpToIssue(issue: ValidationIssue) {
    const draft = ops[issue.index];  // ❌ BUG: issue.index è l'indice IN creates[]/updates[], NON in ops[]
    tableRef?.navigateToRowId(draft.tempId);
}

// BulkModal.svelte:2515
{$t('transactions.bulk.rowN', {values: {n: issue.index + 1}})}  // ❌ Mostra posizione sbagliata
```

Il backend emette `{operation: "create", index: 0}` = "primo elemento di creates[]".
Il frontend usa `ops[0]` che potrebbe essere un UPDATE (ordine misto nella tabella).

### Fix (100% frontend — no backend change)

Il mapping `"operation:index" → tempId` **esiste già** in `buildOpsIndexMap()` (riga 995, usato per WAC results dal 1097). Il map gestisce anche i partner (create:0=main, create:1=partner). Basta riusarlo per le issues:

1. **Dopo validate**, salvare `lastOpsIndexMap = buildOpsIndexMap(resolved)` nello stato
2. **`jumpToIssue(issue)`** → lookup via `lastOpsIndexMap.get(`${issue.operation}:${issue.index}`)` → `tempId` → `navigateToRowId(tempId)`
3. **Display "Riga N"** con suffisso a/b per paired:
   ```typescript
   function getVisualRowLabel(issue: ValidationIssue): string {
       const key = `${issue.operation}:${issue.index}`;
       const tempId = lastOpsIndexMap.get(key);
       if (!tempId) return String(issue.index + 1); // fallback
       // Find visual position in visibleOps
       const op = ops.find(o => o.tempId === tempId);
       // If this is a partner (hidden row), find the main row
       const mainTempId = op?.pairedWith ? op.pairedWith : tempId;
       const mainOp = ops.find(o => o.tempId === mainTempId);
       const visIdx = visibleOps.findIndex(o => o.tempId === (mainOp?.tempId ?? tempId));
       const rowNum = visIdx >= 0 ? visIdx + 1 : issue.index + 1;
       // Suffix a/b: if the issue is on the partner, it's "b"
       const suffix = op?.pairedWith ? 'b' : (getPartnerOp(tempId) ? 'a' : '');
       return `${rowNum}${suffix}`;
   }
   ```

### Substeps

1. Aggiungere `let lastOpsIndexMap = $state(new Map<string, string>())` al componente
2. In `validateFn`, dopo `buildOpsIndexMap(resolved)` per WAC, salvare anche `lastOpsIndexMap = opsMap`
3. Riscrivere `jumpToIssue`: usa lastOpsIndexMap → trova mainTempId → `navigateToRowId`
4. Estrarre `getVisualRowLabel(issue)` con logica Na/Nb
5. Sostituire `issue.index + 1` con `getVisualRowLabel(issue)` nei banner (4 occorrenze)

### File da modificare

| File | Modifica |
|------|----------|
| `TransactionBulkModal.svelte` | `lastOpsIndexMap` state + riscrivere jumpToIssue + getVisualRowLabel + aggiornare banner display |

---

## Step 2 — B1 + I4: Event Picker Dropdown Redesign + Spread ✅ (2026-06-03)

> **Note implementazione**: Riscritto AssetEventSelect con card-style snippets (icon box colorato per tipo, data formattata locale, note, amount senza trailing zeros). Aggiunta prop `txCash` per calcolo delta inline (Δ±N.NN verde/amber). Opzione "none" = icona ∅ + testo italic. Rimossa emoji duplicata. Slider ridotto a max 30gg. svelte-check 0 errori.

### Root Cause

```svelte
<!-- AssetEventSelect.svelte:141-143 -->
label: `${icon} ${e.date} — ${e.amount} ${e.code}${noteSuffix}`,
icon,  // ← duplicato! SimpleSelect rende ICON + LABEL, quindi emoji appare 2 volte
```

- Emoji duplicata (campo `icon` + emoji in `label`)
- Amount raw "0.240000" (6 decimali dal backend, nessun format)
- "—" come opzione "none" è confusa (sembra un dato rotto)

### Design: Card-style (ispirato ad AssetSelect) + Delta

Usare **custom `item` snippet** di SimpleSelect (supportato, riga 277) per card ricche con delta:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  [💰]  4 Mar 2026 · Q1 dividend              0.24 USD   Δ+0.01 ✓       │
├──────────────────────────────────────────────────────────────────────────┤
│  [💰]  12 Feb 2026 · Q4 dividend             0.22 USD   Δ+0.03         │
├──────────────────────────────────────────────────────────────────────────┤
│  [✂️]   1 Jan 2026 · 2:1 stock split          —                         │
├──────────────────────────────────────────────────────────────────────────┤
│  [ ∅ ]  Nessun evento collegato                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Struttura card item:**
```svelte
<div class="flex items-center gap-2 min-w-0 py-0.5">
    <!-- Icon box (come AssetSelect) -->
    <span class="shrink-0 w-6 h-6 flex items-center justify-center bg-amber-50 dark:bg-amber-900/20 rounded text-sm">
        {emoji}
    </span>
    <!-- Content: date + note -->
    <div class="flex-1 min-w-0">
        <div class="text-sm font-medium truncate">{formattedDate} · {notes || typeLabel}</div>
    </div>
    <!-- Amount -->
    <span class="text-xs font-mono text-gray-500 shrink-0">{formattedAmount} {code}</span>
    <!-- Delta (se cash del draft è compilato) -->
    {#if delta != null}
        <span class="text-[10px] font-mono shrink-0 {Math.abs(delta) < 0.05 ? 'text-green-600' : 'text-amber-500'}">
            Δ{delta >= 0 ? '+' : ''}{delta.toFixed(2)}
        </span>
    {/if}
</div>
```

**Opzione "not set":**
```svelte
<div class="flex items-center gap-2 text-gray-400">
    <span class="w-6 h-6 flex items-center justify-center rounded border border-dashed border-gray-300 dark:border-gray-600 text-xs">∅</span>
    <span class="text-sm italic">{$t('transactions.form.eventPickerNone')}</span>
</div>
```

**Delta logic** (nuova prop `txCash: {amount: string, code: string} | null`):
- Se `txCash` ha amount > 0 e stesso `code` dell'evento → `delta = txCash.amount - event.amount`
- Se diversa valuta → non mostrare delta (incomparabile)
- Se `txCash` null/zero → non mostrare delta

### Substeps

1. Aggiungere prop `txCash?: {amount: string, code: string} | null` ad AssetEventSelect
2. Rimuovere `icon` dal campo opzioni (evita duplicato SimpleSelect)
3. Formattare `amount` con `formatDecimalForDisplay()` (rimuove trailing zeros)
4. Aggiungere `{#snippet item}` e `{#snippet selectedItem}` a SimpleSelect call
5. Redesign opzione "none" → icona ∅ + testo italic
6. Aggiungere `data` field nelle options con l'evento raw per accesso nel snippet
7. Calcolare e mostrare delta nel snippet
8. Nel FormModal: passare `txCash={draft.cash}` ad AssetEventSelect

### File da modificare

| File | Modifica |
|------|----------|
| `AssetEventSelect.svelte` | Riscrivere options + snippets + prop txCash + delta |
| `TransactionFormModal.svelte` | Passare `txCash={draft.cash}` |

---

## Step 3 — B2: Slider Range Ridotto ✅ (2026-06-03, incluso in Step 2)

### Fix

```diff
- <input type="range" min="1" max="90" ...>
+ <input type="range" min="1" max="30" ...>
```

E nel `loadDays()`:
```diff
- if (n >= 1 && n <= 90) return n;
+ if (n >= 1 && n <= 30) return n;
```

### File: `AssetEventSelect.svelte`

---

## Step 4 — B3 + I3: BulkModal Event Cell → Card mini ✅ (2026-06-03)

> **Note implementazione**: Aggiunta `eventCache: Map<number, EventCacheEntry>` allo stato. Dopo validate, fetch batch via `GET /assets/events?ids=...` (più semplice di POST query). Cell renderer: emoji tipo + data locale breve + importo formattato. Fallback a `#ID` se cache miss.

### Root Cause

```typescript
cell: (row) => ({type: 'html', html: `<span class="font-mono text-xs">#${row.fields.asset_event_id}</span>`})
```

### Fix

Fetch batch degli eventi presenti nel workspace (cache leggera):
1. `eventCache: Map<number, {type: string, date: string, amount: string, code: string}>` nello stato
2. Dopo validate, fetch events via `POST /assets/events/query`
3. Cell renderer con card mini inline

**Cell rendering:**
```html
<span class="inline-flex items-center gap-1 text-xs">
    <span class="text-sm">💰</span>
    <span class="text-gray-600 dark:text-gray-400">4 Mar</span>
    <span class="font-mono text-gray-500">0.24 USD</span>
</span>
```

### File: `TransactionBulkModal.svelte`

---

## Step 5 — B5: Sync FX Button nel Banner Issues ✅ (2026-06-03)

> **Note implementazione**: Aggiunto `hasWacFxIssues` derived + `handleSyncFx()` handler nel BulkModal. Bottone `🔄 Sync FX` appare via `titleAction` snippet di TransactionResultBanner (sia warning che error banner). Handler: raggruppa pairs dagli issues, calcola date range ±7gg dalle ops coinvolte, chiama `POST /fx/currencies/sync`. On success → toast + re-trigger validate. FormModal già implementato nel round precedente. TransactionResultBanner: aggiunto prop `titleAction?: Snippet` per azione inline nel titolo.

### Fix

Il bottone Sync FX vive **solo nel banner issues** (BulkModal + FormModal), NON nel WacPreviewSection.

**Layout banner con Sync FX:**
```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⚠️ Sono stati identificati degli errori nei campi          [ 🔄 Sync FX ]│
│                                                                           │
│  • Riga 2b: ❌ Calcolo WAC fallito: coppia/e FX                           │
│    $ 🇺🇸 USD / € 🇪🇺 EUR non disponibile/i                                 │
│  • Riga 5: ❌ <b>Aggiustamento</b> con quantità positiva...               │
└──────────────────────────────────────────────────────────────────────────┘
```

**Regole:**
1. `hasWacFxIssues = $derived(fieldIssues.some(i => i.code === 'wac_fx_unavailable'))`
2. Bottone `🔄 Sync FX` appare nella riga del titolo (flex, allineato a destra) solo se `hasWacFxIssues`
3. Aggregare tutte le pairs: `allMissingPairs = [...new Set(fieldIssues.filter(i => i.code === 'wac_fx_unavailable').flatMap(i => i.params?.pairs ?? []))]`
4. Handler `handleSyncFx()`:
   - Raggruppa le issues per pair → per ogni pair, raccogli le date delle ops che la necessitano
   - Per ogni pair (o cluster con range simile): calcola `start = min(date) - 7gg`, `end = max(date) + 7gg`
   - L'API (`POST /fx/currencies/sync`) accetta `{pairs[], start, end}` — singolo range per batch
   - **Strategia**: se tutte le pair hanno range sovrapposti → 1 chiamata con superset. Se no → N chiamate raggruppate per range compatibile. In pratica, per la maggior parte dei casi reali (singola TX o batch con date vicine) sarà 1 sola chiamata.
   - Converte pair slugs: `"EUR/USD"` → `"EUR-USD"` per l'API
   - On success → toast verde + ri-trigger validate
   - On error → toast errore
5. Se dopo ri-validate le issues spariscono → banner sparisce naturalmente. Se persistono → banner riappare con le issues residue.

### Formattazione pairs nel messaggio issue

In `resolveValidationMessage.ts` il campo `pairs` è già formattato con `formatCurrencyCodeHtml` (implementato nello step 7). L'output HTML è renderizzato via `{@html}` nel banner.

### File da modificare

| File | Modifica |
|------|----------|
| `TransactionBulkModal.svelte` | Sync FX button nel banner (warning + error) + handler |
| `TransactionFormModal.svelte` | Stesso pattern per il banner issues del FormModal |

---

## Step 6 — B6: WacPreviewSection Bottoni Contestuali ✅ (2026-06-03)

> **Note implementazione**: Rimosso link `<a href="/fx">` e bottone "Sync asset prices". Rimosso anche "Sync FX" dal WacPreview (l'azione Sync vive solo nel banner issues globale — Step 5). Il WacPreview mostra solo gli errori di dettaglio. Aggiunto badge `💱 FX` nel titolo (Step 9 incluso). Prop `onSyncFx` mantenuta per retrocompatibilità ma non usata nel design finale — **da rimuovere** in Step 5 quando il Sync è solo nel banner.

> **✅ CONFLITTO C1 RISOLTO** (2026-06-03): Rimossa prop `onSyncFx` dall'interface Props, dal destructuring, e il blocco `{#if onSyncFx}` con bottone Sync FX. Il WacPreview mostra ora solo l'elenco testuale delle missing pairs. Il Sync FX vive solo nel banner issues (Step 5).

### Fix

**Rimuovere**: link `<a href="/fx">` + bottone "Sync asset prices"
**Tenere**: solo "🔄 Sync FX" con handler inline (prop callback `onSyncFx`)
**Post-sync fallito**: messaggio testo "Pair non configurata — aggiungi da Impostazioni FX" (senza link)

### File da modificare

| File | Modifica |
|------|----------|
| `WacPreviewSection.svelte` | Rimuovere bottoni extra, prop onSyncFx |
| `TransactionFormModal.svelte` | Passare onSyncFx |

---

## Step 7 — B7: Validation Message Migliorato ✅ (2026-06-03)

> **Note implementazione**: Riformulati messaggi 4 lingue con `<b>` tags. BulkModal banner usa `{@html}` per fieldIssues (come balanceIssues). resolveValidationMessage formatta pairs con currency flags (bandiere).

### Fix

Riformulare con `<b>` tags:
- **IT**: `"❌ <b>{type}</b> con quantità positiva richiede un costo base. Usa la modalità <b>Auto</b> (PMC) oppure inserisci un valore <b>manuale</b>."`
- **EN**: `"❌ <b>{type}</b> with positive quantity requires a cost basis. Use <b>Auto</b> mode (WAC) or enter a <b>manual</b> value."`

Uniformare uso di `{@html}` per fieldIssues nel banner (come balanceIssues).

### File: i18n 4 lingue + `TransactionBulkModal.svelte`

---

## Step 8 — B8: INDEX Asset Type Greyed Out ✅ (2026-06-03)

### Fix

```typescript
disabled: !a.active || a.asset_type === 'INDEX',
```

### File: `AssetSelect.svelte`

---

## Step 9 — I1: Badge 💱 FX nel Titolo WAC ✅ (2026-06-03, incluso in Step 6)

### Fix

```svelte
{#if hasAnyFxConversion}
    <span class="text-[9px] px-1 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-medium">
        💱 FX
    </span>
{/if}
```

### File: `WacPreviewSection.svelte`

---

## Step 10 — I2: Backend + Frontend — Original Unit Cost in Qualifying ✅ (2026-06-03)

> **Note implementazione**: Backend: aggiunto `original_unit_cost`, `original_currency`, `fx_rate_used` a WACQualifyingTX. wac_service.py: traccia `fx_rates` dict + `original_unit_costs` dict per propagarli nei qualifying. Frontend: cella qualifying mostra freccia `originale → convertito` con tooltip FX (rate, data, stale warning). Badge 💱 FX con tooltip disclaimer + elenco coppie. Banner stale riscritta come elenco puntato con formatCurrencyCodeHtml. Missing pairs: elenco puntato formattato. i18n 4 lingue: 7 nuove chiavi (fxStaleBannerTitle, fxDisclaimer, fxTooltipStale, fxTooltipDate, fxDaysAgo, convertedPairs, noRateAvailable). api sync eseguito.

### Backend Change

Aggiungere a `WACQualifyingTX` (in `backend/app/schemas/wac.py`):
```python
original_unit_cost: Optional[SafeDecimal] = Field(None, description="Unit cost in original currency (before FX)")
original_currency: Optional[str] = Field(None, description="Original currency before FX conversion")
fx_rate_used: Optional[SafeDecimal] = Field(None, description="FX rate applied (derived: converted/original)")
```

In `wac_service.py`:
- Nella sezione FX (riga 138-144), calcolare `rate = converted.amount / amt_ccy.amount` e salvarlo in un dict parallelo `fx_rates: dict[int, Decimal]`
- Nella costruzione `input_txs` (riga 150-186), tracciare `original_unit_cost` (il costo per unità PRIMA della conversione FX) in un dict parallelo
- Nella costruzione `qualifying_txs` (riga 197-210), propagare `original_unit_cost`, `original_currency`, `fx_rate_used` dai dict

**Nota**: `convert_bulk` non ritorna il rate direttamente ma `fx_rate_used = converted.amount / amt_ccy.amount` (derivato, conversione lineare). Nessun refactor di `convert_bulk`.

### Frontend Change — Qualifying Table (Proposta A + tooltip stile B)

**Layout cella "Unit cost"** — inline con freccia:
```
┌───────────────────────────────────────────────────────────────────────────────────┐
│  #  │  Tipo      │   Data    │ Qty │   Costo unitario              │ Effetto │WAC│
├───────────────────────────────────────────────────────────────────────────────────┤
│  ●  │ 🛒 Buy     │ 1 Jun '26 │ 300 │ 0.10 $ 🇺🇸 USD → 0.11 € 🇪🇺 EUR 💱│ Pesata │9.5│
│  42 │ 🛒 Buy     │ 15 May    │  50 │ 150.00 € 🇪🇺 EUR               │ Pesata │8.2│
│  ●  │ ↕ Transfer │ 3 Jun '26 │  10 │ 40.00 $ 🇺🇸 USD → 37.2 € 🇪🇺 EUR⚠️│ Ered. │9.5│
└───────────────────────────────────────────────────────────────────────────────────┘
```

**Regole rendering cella**:
- Se `original_currency !== currency` (FX applicato):
  - Mostrare: `{formatCurrencyAmountPlain(original_unit_cost, original_currency)} → {formatCurrencyAmountPlain(unit_cost, currency)}`
  - Suffisso: `💱` se fresh (stale_days ≤ 5), `⚠️` se stale (stale_days > 5)
- Se nessuna FX: solo `{formatCurrencyAmountPlain(unit_cost, currency)}` (come ora)
- Usare `formatCurrencyAmountPlain` da `currencyFormat.ts` (include symbol + flag)

**Tooltip** (SEMPRE quando c'è FX, anche se fresh) — usa prop `html` del Tooltip con formattazione:
```
┌─────────────────────────────────────────────┐
│  ↳ Rate: 0.923                              │
│    $ 🇺🇸 USD → € 🇪🇺 EUR                     │
│    Data rate: 1 Jun 2026 (0gg fa)           │
└─────────────────────────────────────────────┘
```

Per stale (⚠️):
```
┌─────────────────────────────────────────────┐
│  ↳ Rate: 0.918                              │
│    $ 🇺🇸 USD → € 🇪🇺 EUR                     │
│    Data rate: 28 May 2026 (6gg fa)          │
│    ⚠️ Rate non aggiornato                    │
└─────────────────────────────────────────────┘
```

**Implementazione tooltip**: `<Tooltip html={buildFxTooltipHtml(qtx)} position="top">` dove il builder usa `formatCurrencyCodeHtml` per formattare le valute con simbolo+bandiera+codice. Il tooltip supporta già HTML rendering (prop `html`).

### Frontend Change — Badge 💱 FX con Tooltip disclaimer (già implementato badge, aggiungere tooltip)

Il badge `💱 FX` nel titolo della sezione WAC (già implementato) diventa **cliccabile/hoverable** con Tooltip:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Override costo medio ⓘ  [💱 FX]←hover      [ Auto | Manuale ]          │
│                            ↓                                              │
│                    ┌─────────────────────────────────────┐                │
│                    │ Il tasso FX utilizzato potrebbe      │                │
│                    │ differire da quello applicato dal    │                │
│                    │ broker. Verifica il costo medio     │                │
│                    │ con il broker.                       │                │
│                    │                                      │                │
│                    │ Coppie convertite:                   │                │
│                    │  • $ 🇺🇸 USD → € 🇪🇺 EUR              │                │
│                    └─────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────────────────┘
```

**Nessun banner info separato.** Il tooltip del badge copre il caso "FX usato ma non stale".

### Frontend Change — Banner Stale FX (sopra tabella qualifying)

**Quando appare**: almeno 1 qualifying TX con `fx_info.fx_days_back > 5` E tabella espansa (`showQualifying = true`).

**Layout (elenco puntato, formattato con `formatCurrencyCodeHtml`)**:
```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⚠️ Conversioni FX con tassi non aggiornati                               │
│                                                                           │
│  • $ 🇺🇸 USD / € 🇪🇺 EUR — rate del 28 May 2026 (6gg fa)                 │
│  • £ 🇬🇧 GBP / € 🇪🇺 EUR — rate del 25 May 2026 (9gg fa)                 │
│                                                                           │
│  Il tasso FX utilizzato potrebbe differire da quello applicato            │
│  dal broker. Verifica il costo medio con il broker.                       │
└──────────────────────────────────────────────────────────────────────────┘
```

**Regole**:
- Titolo: i18n `transactions.wac.fxStaleBannerTitle`
- Elenco puntato: 1 bullet per coppia unica (deduplicata tra qualifying_txs che hanno stale_days > 5)
- Ogni bullet: `{@html formatCurrencyCodeHtml(base)} / {@html formatCurrencyCodeHtml(quote)} — rate del {date} ({N}gg fa)`
- Footer disclaimer: i18n `transactions.wac.fxDisclaimer` — tono neutro/tecnico
- Colore: `bg-amber-50 text-amber-700` (warning)

### Frontend Change — Missing Pairs Section (nel WacPreviewSection)

**Nota**: Nessun bottone Sync FX qui (l'azione vive solo nel banner issues globale — Step 5). Solo elenco informativo.

**Layout (elenco puntato)**:
```
┌──────────────────────────────────────────────────────────────────────────┐
│ ⚠️ Impossibile calcolare il costo medio: tassi FX mancanti               │
│                                                                           │
│  • $ 🇺🇸 USD / € 🇪🇺 EUR — nessun tasso disponibile                       │
│  • ¥ 🇯🇵 JPY / € 🇪🇺 EUR — nessun tasso disponibile                       │
└──────────────────────────────────────────────────────────────────────────┘
```

**Regole**:
- Titolo: i18n `transactions.wacPreview.missingFx`
- Elenco puntato: 1 bullet per pair mancante, formattato con `{@html formatCurrencyCodeHtml}`
- Nessun bottone qui (Sync è nel banner issues globale)
- Toggle Auto forzato a Manual (`forcedManual` derived, già implementato)

### File da modificare

| File | Modifica |
|------|----------|
| `backend/app/schemas/wac.py` | Aggiungere 3 campi a WACQualifyingTX |
| `backend/app/services/wac_service.py` | Propagare original_unit_cost + original_currency + fx_rate_used |
| `WacPreviewSection.svelte` | Rendering freccia + tooltip + banner stale/info + missing pairs redesign |
| `frontend/src/lib/i18n/*.json` | Chiavi per banner stale/info/disclaimer |

### Post-modifica

```bash
./dev.py api sync   # Rigenera TypeScript client
```

---

## Step 11 — Mock Data per Test ✅ (2026-06-03)

> **Note implementazione**: 1) Aggiunto evento DIVIDEND Apple a `today-3` (entro range ±7gg per event picker). 2) 2 BUY Apple su Directa in EUR (days -10 e -4) per WAC FX test. 3) Asset "Test KRW Stock" in KRW + BUY in EUR su Directa (EUR→KRW pair non configurata → missing pair scenario). Usato KRW anziché JPY perché EUR/JPY è già configurato nelle routes. Validate OK, balance OK.

### Modifiche a `populate_mock_data.py` (date relative)

1. Evento DIVIDEND Apple a `today - 3 giorni` (range ±7 di default)
2. 2 BUY Apple su Directa (broker #3) in EUR a date recenti (per WAC FX test)
3. Asset "Test JPY Stock" in JPY (senza FX pair EUR/JPY → scenario missing pair)

---

## Step 12 — Test Automatici ✅ (2025-07-14)

> **Note implementazione**: Created `frontend/e2e/transactions/tx-event-picker.spec.ts` with 4 tests: picker hidden for BUY, picker visible for DIVIDEND, slider max=30, card-style emoji options. All 4 pass. Registered `front_tx_event_picker()` in `_frontend_transaction.py` with `add_test` and added to `front_transaction_all()` tests list. The more complex tests from the plan (delta, persistence, clear) are deferred — the current tests validate the core functionality.

### Nuovo file: `frontend/e2e/transactions/tx-event-picker.spec.ts`

| Test | Scenario |
|------|----------|
| `event picker shows card-style options` | DIVIDEND Apple → dropdown con card ricche (emoji, data, amount) |
| `event picker shows delta` | Cash compilato → delta visibile nella card |
| `event picker respects slider range` | Cambia slider → lista si aggiorna |
| `event picker selection persists` | Seleziona → Apply → edit → ancora selezionato |
| `event picker hidden for BUY` | Tipo BUY → no picker |
| `event picker clear works` | Seleziona → clear (∅) → payload senza asset_event_id |

### Aggiunta a `transactions-modals.spec.ts`

| Test | Scenario |
|------|----------|
| `issue row index maps correctly with Na/Nb` | Batch creates+updates misti → banner mostra riga corretta con suffisso |
| `issue click scrolls to correct row` | Click su "Riga Na" → row pulse/scroll |
| `WAC FX missing pair shows sync button` | Asset JPY → banner con 🔄 Sync FX |
| `cost_basis_required on correct row` | ADJUSTMENT in batch → riga corretta |

### Registrazione: `scripts/test_runner/_frontend_transaction.py`

---

## Ordine di Esecuzione

```
Step 1  (B4 — index mapping Na/Nb)    ← critico
  ↓
Step 2  (B1+I4 — event picker card)   ← alta visibilità
  ↓
Step 3  (B2 — slider 30gg)            ← 1 riga
  ↓
Step 4  (B3+I3 — event cell)
  ↓
Step 5  (B5 — sync fx banner)
  ↓
Step 6  (B6 — bottoni WacPreview)
  ↓
Step 7  (B7 — messaggi bold)
  ↓
Step 8  (B8 — INDEX greyed)
  ↓
Step 9  (I1 — badge 💱 FX)
  ↓
Step 10 (I2 — backend original_unit_cost + frontend freccia)
  ↓
Step 11 (Mock data)
  ↓
Step 12 (Test automatici)
```

---

## ⚠️ Conflitti & Punti Aperti

| # | Conflitto | Stato | Risoluzione |
|---|-----------|-------|-------------|
| **C1** | Step 6 ha implementato `onSyncFx` prop + bottone Sync nel WacPreviewSection | ❗ Da correggere in Step 5 | Rimuovere bottone Sync dal WacPreview. L'azione Sync vive SOLO nel banner issues (BulkModal/FormModal). Piccola modifica: rimuovere il bottone, tenere solo la sezione testuale con elenco puntato. |
| **C2** | Step 10 riscrive banner stale (elenco puntato) ma banner attuale (riga 284-288) è monolitico | Da fare in Step 10 | Sostituire il banner semplice con formato elenco puntato. Rimuovere il banner info separato (non esiste più: il tooltip del badge 💱 copre quel caso). |
| **C3** | `formatCurrencyCodeHtml` produce HTML ma la qualifying table è template Svelte | ✅ Risolto | Cella tabella: `formatCurrencyAmountPlain()` (plain text con emoji bandiera). Tooltip: prop `html` con `formatCurrencyCodeHtml`. Banner stale `<li>`: `{@html formatCurrencyCodeHtml()}`. |
| **C4** | `fx_rate_used` — da dove viene? | ✅ Risolto | Derivato in-place: `converted.amount / amt_ccy.amount`. Nessun refactor di `convert_bulk`. |

---

## 🧪 Walktest Manuale (test rimanenti)

I test seguenti NON sono stati eseguiti nel primo walktest. Da completare prima di chiudere il plan.

### WT-1: Sync FX Button nel Banner (B5)

**Prerequisito**: Nel mock data esiste già 1 BUY di "Test KRW Stock" (KRW) su Directa in EUR (riga 1047). EUR/KRW non è configurato nelle FX routes.

**Scenario**: Creare un TRANSFER IN (ricevente) per Test KRW Stock che richiede WAC auto.

1. **BulkModal** → aggiungi riga paired TRANSFER:
   - Asset: **Test KRW Stock**, broker sorgente: **Directa SIM**, qty: **-5**
   - Il partner automatico avrà qty: **+5**, broker destinazione: scegli **Interactive Brokers**, cost_basis: **Auto**
2. Click **Apply** → il WAC per il lato ricevente deve convertire EUR→KRW (le transazioni esistenti su Directa sono in EUR, l'asset è in KRW) → errore `wac_fx_unavailable`
3. ✅ Verifica: bottone `🔄 Sync FX` nel banner errori (titolo, allineato a destra)
4. ✅ Verifica: bottone **NON** nel WacPreviewSection in basso
5. Click `🔄 Sync FX` → toast (errore perché EUR/KRW non ha provider) + ri-validate automatico

**Alternativa semplificata (FormModal)**:
1. **FormModal** → tipo TRANSFER, asset Test KRW Stock, qty +5, broker **Interactive Brokers**, cost_basis **Auto**
2. Apply → errore WAC FX missing pair

guà questo test non è chiaro, hai fatto un casino. in oltre mi pare di vedere che non si sta rispettando la logica che la valuta finale dipende dalle transazioni di maggioranza, mentre pare dipenda dalla valuta dell'asset:
<div class="mt-3"><div class="flex flex-col gap-1.5" data-testid="tx-form-cost-basis"><div class="flex items-center gap-2"><span class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap flex items-center gap-1">Override costo medio <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-400 dark:text-gray-500"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path></svg><!----></div> <!----><!----> <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><span class="text-[9px] px-1 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-medium cursor-help">💱 FX</span><!----></div> <!----><!----></span> <div class="flex items-center gap-1 text-[10px] ml-auto" data-testid="tx-form-cost-basis-toggle"><button type="button" class="px-1.5 py-0.5 rounded bg-libre-green/10 text-libre-green font-medium" data-testid="tx-form-cost-basis-toggle-auto">Auto</button> <span class="text-gray-300 dark:text-gray-600">|</span> <button type="button" class="px-1.5 py-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" data-testid="tx-form-cost-basis-toggle-manual">Manuale</button></div><!----></div> <div class="flex items-center gap-2 opacity-60 italic"><div class="compact-cash svelte-1a4aanh sign-ok" data-testid="tx-form-cost-basis-input"><input type="number" step="any" inputmode="decimal" autocomplete="off" class="amount-input svelte-1a4aanh" placeholder="auto" data-testid="tx-form-cost-basis-input-amount"> <div class="currency-wrap svelte-1a4aanh"><div class="relative "><div aria-haspopup="listbox" role="combobox" aria-controls="searchselect-listbox-5kwoncy" aria-expanded="false" class="w-full flex items-center justify-between px-3 py-2 text-sm border rounded-lg
               transition-all text-left gap-2
               bg-white dark:bg-slate-700 dark:border-slate-600 hover:border-gray-400 dark:hover:border-slate-500 cursor-pointer
               " tabindex="0"><!----><!----><div class="flex-1 min-w-0"><!----><div class="flex items-center gap-1.5 min-w-0"><span class="text-sm shrink-0 leading-none">🇺🇸</span><!----> <span class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">USD&nbsp;<span class="text-gray-400 text-xs">$</span><!----></span></div><!----></div><!----> <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-chevron-down text-gray-400 shrink-0 transition-transform "><!----><path d="m6 9 6 6 6-6"></path><!----><!----><!----></svg><!----></div> <!----></div><!----> <span class="sr-only svelte-1a4aanh" data-testid="tx-form-cost-basis-input-currency">USD</span></div></div><!----> <!----></div> <div class="flex items-center gap-1 text-[10px] text-gray-500 dark:text-gray-400" data-testid="tx-form-cost-basis-suggestion"><div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-lightbulb text-amber-500 shrink-0 cursor-help"><!----><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"></path><!----><path d="M9 18h6"></path><!----><path d="M10 22h4"></path><!----><!----><!----></svg><!----></div> <!----><!----> <button type="button" class="flex items-center gap-0.5 hover:text-gray-700 dark:hover:text-gray-200" data-testid="tx-form-cost-basis-show-qualifying"><svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-chevron-down"><!----><path d="m6 9 6 6 6-6"></path><!----><!----><!----></svg><!----> <span>PMC suggerito
                    (6
                    transazioni utilizzate)</span></button> <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><button class="p-0.5 rounded text-gray-400 hover:text-libre-green transition-colors" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-circle-question-mark"><!----><circle cx="12" cy="12" r="10"></circle><!----><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><!----><path d="M12 17h.01"></path><!----><!----><!----></svg><!----></button><!----></div> <!----><!----></div><!----> <!----> <!----> <!----> <div class="mt-1 max-h-40 w-0 min-w-full overflow-x-auto overflow-y-auto border border-gray-200 dark:border-slate-700 rounded text-[10px] scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-slate-600" data-testid="tx-form-cost-basis-qualifying-table"><table class="w-max min-w-full"><thead class="bg-gray-50 dark:bg-slate-800 sticky top-0"><tr><th class="px-2 py-1 text-left min-w-[28px]">#</th><th class="px-2 py-1 text-left min-w-[120px]">Tipo</th><th class="px-2 py-1 text-left min-w-[90px]">Data</th><th class="px-2 py-1 text-center min-w-[35px]">Qtà</th><th class="px-2 py-1 text-center min-w-[120px]">Costo unitario</th><th class="px-2 py-1 text-right min-w-[110px]">Effetto</th><th class="px-2 py-1 text-left min-w-[80px]">PMC</th></tr></thead><tbody><tr class="border-t border-gray-100 dark:border-slate-800 "><td class="px-2 py-0.5">18<!----></td><td class="px-2 py-0.5"><span class="inline-flex items-center gap-1"><img alt="" class="w-3 h-3 object-contain" src="/icons/transactions/buy.png"><!----> <span>Acquisto</span></span></td><td class="px-2 py-0.5">2026-05-28</td><td class="px-2 py-0.5 text-right font-mono">10</td><td class="px-2 py-0.5 text-right font-mono">55,51 € 🇪🇺 EUR<!----></td><td class="px-2 py-0.5 text-right"><span class="inline-block px-1 rounded text-[9px] bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400">Pesata</span></td><td class="px-2 py-0.5 text-left font-mono">55,5117 € 🇪🇺 EUR</td></tr><tr class="border-t border-gray-100 dark:border-slate-800 bg-indigo-50/50 dark:bg-indigo-900/10"><td class="px-2 py-0.5"><div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><span class="cursor-help text-indigo-500">●</span><!----></div> <!----><!----></td><td class="px-2 py-0.5"><span class="inline-flex items-center gap-1"><img alt="" class="w-3 h-3 object-contain" src="/icons/transactions/buy.png"><!----> <span>Acquisto</span></span></td><td class="px-2 py-0.5">2026-06-03</td><td class="px-2 py-0.5 text-right font-mono">10</td><td class="px-2 py-0.5 text-right font-mono">5,61 € 🇪🇺 EUR<!----></td><td class="px-2 py-0.5 text-right"><span class="inline-block px-1 rounded text-[9px] bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400">Pesata</span></td><td class="px-2 py-0.5 text-left font-mono">30,5594 € 🇪🇺 EUR</td></tr><tr class="border-t border-gray-100 dark:border-slate-800 bg-indigo-50/50 dark:bg-indigo-900/10"><td class="px-2 py-0.5"><div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><span class="cursor-help text-indigo-500">●</span><!----></div> <!----><!----></td><td class="px-2 py-0.5"><span class="inline-flex items-center gap-1"><img alt="" class="w-3 h-3 object-contain" src="/icons/transactions/buy.png"><!----> <span>Acquisto</span></span></td><td class="px-2 py-0.5">2026-06-03</td><td class="px-2 py-0.5 text-right font-mono">50</td><td class="px-2 py-0.5 text-right font-mono">0,40 $ 🇺🇸 USD<!----></td><td class="px-2 py-0.5 text-right"><span class="inline-block px-1 rounded text-[9px] bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400">Pesata</span></td><td class="px-2 py-0.5 text-left font-mono">9,017 $ 🇺🇸 USD</td></tr><tr class="border-t border-gray-100 dark:border-slate-800 bg-indigo-50/50 dark:bg-indigo-900/10"><td class="px-2 py-0.5"><div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><span class="cursor-help text-indigo-500">●</span><!----></div> <!----><!----></td><td class="px-2 py-0.5"><span class="inline-flex items-center gap-1"><img alt="" class="w-3 h-3 object-contain" src="/icons/transactions/buy.png"><!----> <span>Acquisto</span></span></td><td class="px-2 py-0.5">2026-06-03</td><td class="px-2 py-0.5 text-right font-mono">50</td><td class="px-2 py-0.5 text-right font-mono">0,40 $ 🇺🇸 USD<!----></td><td class="px-2 py-0.5 text-right"><span class="inline-block px-1 rounded text-[9px] bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400">Pesata</span></td><td class="px-2 py-0.5 text-left font-mono">5,4266 $ 🇺🇸 USD</td></tr><tr class="border-t border-gray-100 dark:border-slate-800 bg-indigo-50/50 dark:bg-indigo-900/10"><td class="px-2 py-0.5"><div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><span class="cursor-help text-indigo-500">●</span><!----></div> <!----><!----></td><td class="px-2 py-0.5"><span class="inline-flex items-center gap-1"><img alt="" class="w-3 h-3 object-contain" src="/icons/transactions/buy.png"><!----> <span>Acquisto</span></span></td><td class="px-2 py-0.5">2026-06-03</td><td class="px-2 py-0.5 text-right font-mono">50</td><td class="px-2 py-0.5 text-right font-mono">0,40 $ 🇺🇸 USD<!----></td><td class="px-2 py-0.5 text-right"><span class="inline-block px-1 rounded text-[9px] bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400">Pesata</span></td><td class="px-2 py-0.5 text-left font-mono">3,9482 $ 🇺🇸 USD</td></tr><tr class="border-t border-gray-100 dark:border-slate-800 bg-indigo-50/50 dark:bg-indigo-900/10"><td class="px-2 py-0.5"><div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><span class="cursor-help text-indigo-500">●</span><!----></div> <!----><!----></td><td class="px-2 py-0.5"><span class="inline-flex items-center gap-1"><img alt="" class="w-3 h-3 object-contain" src="/icons/transactions/transfer.png"><!----> <span>Trasferimento Titoli</span></span></td><td class="px-2 py-0.5">2026-06-03</td><td class="px-2 py-0.5 text-right font-mono">-4</td><td class="px-2 py-0.5 text-right font-mono">3,95 ₩ 🇰🇷 KRW<!----></td><td class="px-2 py-0.5 text-right"><span class="inline-block px-1 rounded text-[9px] bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400">Quantità ridotta</span></td><td class="px-2 py-0.5 text-left font-mono">3,9482 ₩ 🇰🇷 KRW</td></tr></tbody></table></div><!----></div><!----></div>
                    
Poi in generale credo che forse sarebbe più corretto se la valuta target oltre ad essere auto calcolata, possa comunque essere scelta dal selettore senza andare in manuale, e se scelta, tutti i calcoli sottostanti vengono ricalcolati in questa valuta.                    

### WT-2: WacPreview — Badge 💱 FX + Tooltip (I1)

**Prerequisito**: Nel mock data esistono 2 BUY Apple su Directa in EUR (righe 1025-1046). Apple è in USD. EUR/USD **è** configurata nelle routes.

**Scenario**: Creare un TRANSFER IN per Apple che richiede WAC con conversione FX.

1. **FormModal** → tipo TRANSFER, asset **Apple**, qty **+2**, broker **Interactive Brokers**, cost_basis: **Auto**
   - (Il WAC deve guardare le transazioni Apple su tutti i broker dell'utente. Le TX su Directa sono in EUR, l'asset è in USD → conversione EUR→USD necessaria)
2. Apply → la sezione WAC appare in basso
3. ✅ Verifica: badge `💱 FX` nel titolo sezione WAC
4. Hover badge → tooltip con disclaimer + elenco coppie convertite (EUR/USD)

### WT-3: Original → Converted Arrow (I2)

1. Nella situazione WT-2, espandi "qualifying transactions" (click sul toggle/freccia)
2. ✅ Verifica: le righe BUY provenienti da Directa (in EUR) mostrano freccia `X.XX € 🇪🇺 EUR → Y.YY $ 🇺🇸 USD`
3. ✅ Verifica: le righe BUY su Interactive Brokers (se in USD) mostrano solo il costo unitario senza freccia
4. ✅ Hover icona 💱/⚠️ → tooltip con rate, data, stale warning se applicabile

### WT-4: Banner Stale FX

1. Stessa situazione di WT-2/3 — se i rate EUR/USD sono vecchi (>5 giorni dal dato più recente in DB), espandi qualifying
2. ✅ Verifica: banner amber sopra la tabella qualifying con elenco puntato delle coppie stale
3. (Se i rate sono freschi <5gg, il banner NON appare — questo è corretto. Per forzare lo stale: non sincronizzare FX da più di 5 giorni)

### WT-5: Validation Message Bold (B7)

1. **BulkModal** → aggiungi ADJUSTMENT, asset **Apple**, qty **+3**, cost_basis: **manuale**, **lascia vuoto il valore** → Apply
   - (Oppure: cost_basis "auto" ma senza transazioni pre-esistenti su quell'asset)
2. ✅ Verifica: messaggio errore con parole in **grassetto** (nome tipo, "Auto", "manuale")

### WT-6: Missing Pairs (WacPreview)

**Stesso scenario di WT-1 ma nel FormModal per vedere il WacPreview in dettaglio.**

1. **FormModal** → tipo TRANSFER, asset **Test KRW Stock**, qty **+5**, broker **Interactive Brokers**, cost_basis: **Auto** → Apply
2. ✅ Verifica: WacPreview mostra elenco puntato "tassi FX mancanti" con valute formattate (🇪🇺 EUR / 🇰🇷 KRW)
3. ✅ Verifica: NO bottone Sync FX nel WacPreview (il Sync è SOLO nel banner errori in alto)

### WT-7: Balance Issue index=-1 Display

1. **BulkModal** → aggiungi TRANSFER paired:
   - Asset Apple, broker sorgente **Directa SIM**, qty **-50** (più di quanto possiedi su Directa — ci sono solo 8 azioni Apple lì)
   - Data: **oggi** o recente
2. Apply → errore balance "quantity goes negative"
3. ✅ Verifica: banner mostra "?" o messaggio globale (non "Riga -1" e non crash)
4. Click sull'issue → nessun crash (graceful no-op)

---

## 🐛 Bug Residui — Bugfix Round 2 (emersi dal walktest 2026-06-03)

| # | Area | Bug | Gravità |
|---|------|-----|---------|
| **R1** | i18n | Chiavi `transactions.form.eventPickerNone` + `eventPickerPlaceholder` mancanti (4 lingue) | Media |
| **R2** | EventPicker | Delta non visibile: (a) nel dropdown se txCash.code ≠ event.code → incomparabile (design ok?) (b) nel selectedItem compatto post-selezione = manca completamente | Media |
| **R3** | EventPicker | Slider fuori dal dropdown — dovrebbe essere header interno al menu | Bassa |
| **R4** | FormModal | Hint "deve essere 0" confuso (si riferisce a qty ma appare accanto a "Importo") — rimuovere o riformulare come "Dividendo totale lordo" | Bassa |
| **R5** | AssetSelect | Valuta plain `USD` senza symbol/flag nel selectedItem e dropdown | Bassa |
| **R6** | BulkModal | Event cell valuta plain `0.25 USD` senza formatting | Bassa |
| **R7** | BulkModal | `index: -1` (balance issue globale) → label "?" poco utile → migliorare con "Broker N" | Bassa |

### Decisioni aperte (Round 2)

| Domanda | Opzioni | Decisione |
|---------|---------|-----------|
| R2a — Delta con valute diverse | (A) Non mostrare (attuale) (B) Mostrare con ⚠️ "valute diverse" | TBD |
| R3 — Slider dove | (A) Header interno al dropdown (B) Footer dropdown (C) Lasciare fuori con design migliorato | TBD |
| R4 — Hint qty=0 per DIVIDEND | (A) Rimuovere del tutto (B) Riformulare: "Importo totale del dividendo" (C) Mostrare n° titoli posseduti | TBD |
| R7 — Balance issue globale | (A) "Broker {name}" (B) "Saldo negativo" senza riga (C) Evidenziare tutte le righe coinvolte | TBD |

---

## 🔗 Cross-links

- **Parent plan**: [`../plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md`](../plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md)
- **Phase 7 macro**: [`../phases/phase-07-transactions.md`](../phases/phase-07-transactions.md)
- **Next (Round 2)**: [`plan-R3-SP-D-BugfixRound2.prompt.md`](./plan-R3-SP-D-BugfixRound2.prompt.md)

