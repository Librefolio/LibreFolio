# Plan: F9 — ScheduledInvestmentEditor (Round 7 — Aggiornamento Completo)

Post Round 6. Aggiornamento dettagliato del piano F9 con le scelte dell'utente:
- Layout **β** (colonna "Period" con DateRangePicker embedded)
- Late interest come **riga speciale permanente** con toggle on/off + graying
- **Contiguità automatica** dei range (overlap impossibile by design)
- Operazioni CRUD avanzate: **Add**, **Delete** (modale data confine), **Split** (row action + modale), **Merge** (bulk action contigue)

Le sezioni F1–F8 del Round 6 restano invariate.

---

## §9.1 — Obiettivo

Componente che renderizza `FAScheduledInvestmentSchedule` come **DataTable editabile** con:

- Colonna "Period" singola con **DateRangePicker** embedded in `CustomCell` (layout β)
- Late Interest come **riga speciale sempre presente** in fondo, con toggle on/off e opacità ridotta quando off
- **Contiguità automatica** dei range: i periodi sono sempre contigui, overlap impossibile by design tramite propagazione automatica
- Operazioni CRUD: **Add** (start/end auto), **Delete** (modale data confine), **Split** (row action + modale), **Merge** (bulk action contigue)
- Tooltips con link alla documentazione finanziaria
- Mappatura bidirezionale JSON ↔ form strutturato
- Validazione client-side (rate ≥ 0, compound_frequency condizionale, empty state)

---

## §9.2 — `ui_component` Mapping Backend → Frontend

Nuovo campo `ui_component` in `FAProviderInfo` (livello provider):
- `null` → loop generico params_schema (yfinance, cssscraper)
- `"scheduled_investment"` → `ScheduledInvestmentEditor.svelte`

Estensibile: futuri provider potranno dichiarare il proprio editor custom.

### Backend

**`backend/app/schemas/provider.py`** — `FAProviderInfo`:
```python
ui_component: Optional[str] = Field(
    None,
    description="Custom UI component for provider_params editing. "
                "null = generic params loop, 'scheduled_investment' = ScheduledInvestmentEditor"
)
```

**`backend/app/services/asset_source.py`** — base class:
```python
@property
def ui_component(self) -> str | None:
    """Custom UI component name for provider_params. Default: None (generic)."""
    return None
```

**`backend/app/services/asset_source_providers/scheduled_investment.py`** — override:
```python
@property
def ui_component(self) -> str | None:
    return "scheduled_investment"
```

**`backend/app/api/v1/assets.py`** — `list_providers`:
```python
FAProviderInfo(
    …,
    ui_component=instance.ui_component,
)
```

### Frontend Switch

In `ProviderAssignmentSection.svelte`:
```svelte
{#if selectedProvider?.ui_component === 'scheduled_investment'}
    <ScheduledInvestmentEditor
        value={providerParams}
        onchange={(newParams) => { providerParams = newParams; emitChange(); }}
    />
{:else if paramsSchema.length > 0}
    <!-- Generic params loop -->
{/if}
```

---

## §9.3 — `CellDateRange.svelte` — Wrapper DateRangePicker per CustomCell

**Nuovo file**: `frontend/src/lib/components/assets/CellDateRange.svelte`

**Scopo**: Wrapper che mostra il range in formato compatto nella cella DataTable.
Click → popover con `DateRangePicker.svelte` configurato per date selection.

### DateRangePicker Config nel popover

| Prop | Valore |
|------|--------|
| `showPresets` | `false` |
| `showCustomWindow` | `false` |
| `showDateFields` | `true` |
| `compact` | `true` |
| `stacked` | `true` |

### Props di `CellDateRange`

```typescript
interface Props {
    start: string;              // ISO YYYY-MM-DD
    end: string;                // ISO YYYY-MM-DD
    disabled?: boolean;         // per la riga late interest (date readonly)
    isLateInterest?: boolean;   // se true, mostra "⚡ Late (+Nd grace → ∞)"
    graceDays?: number;         // solo per late interest, editabile inline
    onchange?: (start: string, end: string) => void;
    onGraceDaysChange?: (days: number) => void;
}
```

### Display nella cella

**Periodi normali**: `📅 25-01-01 → 25-06-30` (formato `YY-MM-DD` per compattezza)
Click → popover con DateRangePicker dual-calendar.

**Riga late interest**: `⚡ Late (+30d grace → ∞)`
Click → popover minimale con solo input "Grace Period Days: [30]".

### Posizionamento popover

Stessa strategia `position: fixed` + `getBoundingClientRect()` del fix F1 (SimpleSelect)
per evitare clipping da `overflow` del parent. Chiusura su click-outside e Escape.

---

## §9.4 — Layout Tabella β (aggiornato)

### Vista normale (late interest ON)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ INTEREST SCHEDULE                                                           [+ Add Period]   │
├──────────────────────┬──────┬───────────┬──────────────┬─────────┬────────────────────────────┤
│Period  ℹ️              │Rate %│Compounding│Comp. Freq.   │Day Count│ Actions                    │
│                      │ ℹ️    │ ℹ️          │ ℹ️             │ ℹ️        │                            │
├──────────────────────┼──────┼───────────┼──────────────┼─────────┼────────────────────────────┤
│☐ 📅 25-01-01→25-06-30│[5.00]│[SIMPLE ▾] │ —            │[A365 ▾] │ ✂ Split    ✕ Delete        │
│☐ 📅 25-07-01→25-12-31│[6.00]│[COMPND ▾] │[MONTHLY   ▾] │[A365 ▾] │ ✂ Split    ✕ Delete        │
├──────────────────────┼──────┼───────────┼──────────────┼─────────┼────────────────────────────┤
│  ⚡ Late (+30d grace→∞)│[12.0]│[SIMPLE ▾] │ —            │[A365 ▾] │                   [🔘 on]  │
└──────────────────────┴──────┴───────────┴──────────────┴─────────┴────────────────────────────┘
  ✅ 2 periods, contiguous — 2025-01-01 → 2025-12-31 (365 days) + late interest
```

### Vista con late interest OFF (grayed out)

```
├──────────────────────┼──────┼───────────┼──────────────┼─────────┼────────────────────────────┤
│  ⚡ Late (+30d grace→∞)│[12.0]│[SIMPLE ▾] │ —            │[A365 ▾] │                  [⚪ off]  │
│ ↑ opacity-40, grigio │      │ disabled  │ disabled     │disabled │                            │
└──────────────────────┴──────┴───────────┴──────────────┴─────────┴────────────────────────────┘
```

### DataTableToolbar (selezione attiva)

```
  [DataTableToolbar: "2 selected ×   🔗 Merge   🗑 Delete"]    ← visibile solo con selezione
```

### Colonne DataTable

| # | Colonna | Cell Type | Sortable | Note |
|---|---------|-----------|----------|------|
| 1 | **Period** | `CustomCell` → `CellDateRange` | no | Click → DateRangePicker popover |
| 2 | **Rate %** | `EditableNumberCell` | no | step=0.01, min=0 |
| 3 | **Compounding** | `EditableSelectCell` | no | SIMPLE, COMPOUND |
| 4 | **Comp. Freq.** | `EditableSelectCell` | no | Condizionale: `—` se SIMPLE, dropdown se COMPOUND |
| 5 | **Day Count** | `EditableSelectCell` | no | ACT/365, ACT/360, ACT/ACT, 30/360 |

**Comp. Freq. options** (solo quando compounding=COMPOUND):
`DAILY`, `MONTHLY`, `QUARTERLY`, `SEMIANNUAL`, `ANNUAL`, `CONTINUOUS`

### DataTable Config

```typescript
enableSorting: false,          // ordine cronologico forzato
enableColumnFilters: false,
enableColumnResize: false,
enableColumnVisibility: false,
enableSelection: true,         // multi-select per merge/bulk-delete
enablePagination: false,       // tutti i periodi visibili
enableActions: true,
```

### Row Actions

| Azione | Icona | Visibilità | Disabilitato se |
|--------|-------|------------|-----------------|
| **Split** | `Scissors` | Solo periodi normali | Durata ≤ 1 giorno |
| **Delete** | `X` | Solo periodi normali | — |

La riga late interest NON ha row actions Split/Delete. Ha solo il toggle on/off nella colonna azioni.
La riga late interest NON è selezionabile (esclusa dalla multi-select).

---

## §9.5 — Late Interest

Il late interest è **sempre presente** come ultima riga della tabella.
Non è un periodo da aggiungere/rimuovere, ma una riga speciale permanente.

### Toggle ON/OFF

Un toggle switch nella colonna azioni della riga late:
- **ON**: riga completamente editabile, opacità 100%, serializzata come `late_interest: {...}`
- **OFF**: riga con opacità ridotta e sfondo grigio, tutti i campi `disabled`, serializzata come `late_interest: null`

### Stile CSS quando OFF

```css
.late-row-disabled {
    opacity: 0.4;
    background-color: rgb(249 250 251);  /* bg-gray-50 */
}

:global(.dark) .late-row-disabled {
    background-color: rgb(15 23 42 / 0.5);  /* bg-slate-900/50 */
}

/* Il toggle resta cliccabile anche quando la riga è off */
.late-row-disabled .toggle-container {
    opacity: 1;
    pointer-events: auto;
}
```

### Campi riga late

| Campo tabella | Comportamento |
|---------------|---------------|
| **Period** | Readonly: `⚡ Late (+{graceDays}d grace → ∞)`. Click → popover con solo input "Grace Period Days" |
| **Rate %** | Editabile (quando on), disabled (quando off) |
| **Compounding** | Editabile (quando on), disabled (quando off) |
| **Comp. Freq.** | Condizionale come periodi normali |
| **Day Count** | Editabile (quando on), disabled (quando off) |

### Start date implicito

`last_period.end_date + 1 + grace_period_days`. Non mostrato come data editabile — è calcolato automaticamente dal backend.

### Dati interni

```typescript
interface ScheduleRow {
    id: string;
    start_date: string;     // ISO YYYY-MM-DD
    end_date: string;       // ISO YYYY-MM-DD, '' per late interest (= ∞)
    annual_rate: number;    // as percentage (5.00 = 5%)
    compounding: 'SIMPLE' | 'COMPOUND';
    compound_frequency: string | null; // CompoundFrequency enum value
    day_count: string;      // DayCountConvention enum value
    isLate: boolean;        // true = riga late interest
    grace_period_days: number; // solo per late (default 0)
    enabled: boolean;       // toggle per late (true per periodi normali, true/false per late)
}
```

---

## §9.6 — Sistema di Contiguità Automatica (NUOVO)

### Principio fondamentale

I periodi normali (non late) devono essere **sempre contigui**:
`period[n].end_date + 1 giorno == period[n+1].start_date`.

Questo è garantito dal sistema di **propagazione automatica** che:
1. **Espansione** di un range → **contrae** o **elimina** i vicini
2. **Contrazione** di un range → **espande** i vicini
3. Rende **overlap e gap impossibili** by design

**Invariante**: dopo ogni operazione (edit, add, delete, split, merge), i range sono contigui.

### 9.6.1 — `handleRangeChange(rowIndex, newStart, newEnd)`

Chiamato da `CellDateRange.onchange`. L'utente ha modificato il range del periodo a `rowIndex`.

```typescript
function handleRangeChange(rowIndex: number, newStart: string, newEnd: string): void {
    const periods = getNormalPeriods(); // escluso late
    const row = periods[rowIndex];
    
    // Validazione base: end >= start
    if (newEnd < newStart) return; // ignora modifica invalida
    
    const oldStart = row.start_date;
    const oldEnd = row.end_date;
    
    // --- Propagazione verso SINISTRA (start cambiato) ---
    if (newStart !== oldStart) {
        if (rowIndex === 0) {
            // Primo periodo: bordo sinistro è LIBERO, nessuna propagazione
            row.start_date = newStart;
        } else {
            // Ha un predecessore → il suo end_date deve diventare newStart - 1
            const prev = periods[rowIndex - 1];
            const newPrevEnd = addDays(newStart, -1);
            
            if (newPrevEnd < prev.start_date) {
                // Il predecessore viene "mangiato" completamente
                // Rimuoverlo e propagare al predecessore del predecessore
                propagateStartBackward(periods, rowIndex - 1, newStart);
            } else {
                prev.end_date = newPrevEnd;
            }
            row.start_date = newStart;
        }
    }
    
    // --- Propagazione verso DESTRA (end cambiato) ---
    if (newEnd !== oldEnd) {
        if (rowIndex === periods.length - 1) {
            // Ultimo periodo (prima del late): bordo destro è LIBERO
            row.end_date = newEnd;
        } else {
            // Ha un successore → il suo start_date deve diventare newEnd + 1
            const next = periods[rowIndex + 1];
            const newNextStart = addDays(newEnd, 1);
            
            if (newNextStart > next.end_date) {
                // Il successore viene "mangiato" completamente
                // Rimuoverlo e propagare al successore del successore
                propagateEndForward(periods, rowIndex + 1, newEnd);
            } else {
                next.start_date = newNextStart;
            }
            row.end_date = newEnd;
        }
    }
    
    updatePeriodsAndEmit(periods);
}
```

### 9.6.2 — Funzioni di propagazione multi-riga

```typescript
/**
 * Propaga l'espansione dello start verso i predecessori.
 * Se un predecessore viene completamente "mangiato", viene eliminato
 * e la propagazione continua al predecessore precedente.
 */
function propagateStartBackward(
    periods: ScheduleRow[], 
    targetIndex: number, 
    newStartOfNext: string
): void {
    const newEndForTarget = addDays(newStartOfNext, -1);
    
    while (targetIndex >= 0) {
        const target = periods[targetIndex];
        if (newEndForTarget >= target.start_date) {
            // Il target sopravvive: aggiorna solo il suo end_date
            target.end_date = newEndForTarget;
            return;
        }
        // Il target viene mangiato completamente: rimuoverlo
        periods.splice(targetIndex, 1);
        targetIndex--;
    }
    // Se arriviamo qui, tutti i predecessori sono stati eliminati.
    // Il primo periodo inizierà da newStartOfNext (bordo sinistro libero).
}

/**
 * Propaga l'espansione dell'end verso i successori.
 * Se un successore viene completamente "mangiato", viene eliminato
 * e la propagazione continua al successore seguente.
 */
function propagateEndForward(
    periods: ScheduleRow[], 
    targetIndex: number, 
    newEndOfPrev: string
): void {
    const newStartForTarget = addDays(newEndOfPrev, 1);
    
    while (targetIndex < periods.length) {
        const target = periods[targetIndex];
        if (newStartForTarget <= target.end_date) {
            // Il target sopravvive: aggiusta solo il suo start_date
            target.start_date = newStartForTarget;
            return;
        }
        // Il target viene mangiato: rimuoverlo
        periods.splice(targetIndex, 1);
        // Non incrementare targetIndex: il prossimo elemento scivola in posizione
    }
    // Se arriviamo qui, tutti i successori sono stati eliminati.
    // L'ultimo periodo finirà a newEndOfPrev (bordo destro libero).
}
```

### 9.6.3 — Vincoli DateRangePicker nelle celle

Nessun vincolo `min`/`max` rigido nel DateRangePicker — l'utente può selezionare qualsiasi data.
La propagazione automatica corregge i vicini in tempo reale.

**Feedback UX**: Quando una modifica causa eliminazione di righe vicine,
mostrare un toast breve via `sonner`: `"Period 2 absorbed by expansion"`.

### 9.6.4 — Helper date utility

```typescript
function addDays(isoDate: string, days: number): string {
    const d = new Date(isoDate + 'T00:00:00');
    d.setDate(d.getDate() + days);
    return d.toISOString().slice(0, 10);
}

function addMonths(isoDate: string, months: number): string {
    const d = new Date(isoDate + 'T00:00:00');
    d.setMonth(d.getMonth() + months);
    return d.toISOString().slice(0, 10);
}

function daysBetween(start: string, end: string): number {
    const s = new Date(start + 'T00:00:00');
    const e = new Date(end + 'T00:00:00');
    return Math.round((e.getTime() - s.getTime()) / (1000 * 60 * 60 * 24));
}

function todayISO(): string {
    return new Date().toISOString().slice(0, 10);
}

function midpointDate(start: string, end: string): string {
    const days = daysBetween(start, end);
    return addDays(start, Math.floor(days / 2));
}
```

---

## §9.7 — Operazioni CRUD sui Periodi (NUOVO)

### 9.7.1 — Add Period

**Trigger**: Bottone `[+ Add Period]` sopra la tabella (accanto al titolo "INTEREST SCHEDULE").

```typescript
function handleAddPeriod(): void {
    const periods = getNormalPeriods();
    let newStart: string;
    let newEnd: string;
    
    if (periods.length === 0) {
        // Primo periodo: start = oggi, end = oggi + 1 mese
        newStart = todayISO();
        newEnd = addMonths(newStart, 1);
    } else {
        // Start = end dell'ultimo periodo + 1 giorno
        const lastEnd = periods[periods.length - 1].end_date;
        newStart = addDays(lastEnd, 1);
        newEnd = addMonths(newStart, 1);
    }
    
    const newRow: ScheduleRow = {
        id: crypto.randomUUID(),
        start_date: newStart,
        end_date: newEnd,
        // Copia configurazione dall'ultimo periodo (se esiste), altrimenti default
        annual_rate: periods.length > 0 ? periods[periods.length - 1].annual_rate : 5.00,
        compounding: periods.length > 0 ? periods[periods.length - 1].compounding : 'SIMPLE',
        compound_frequency: periods.length > 0 ? periods[periods.length - 1].compound_frequency : null,
        day_count: periods.length > 0 ? periods[periods.length - 1].day_count : 'ACT/365',
        isLate: false,
        grace_period_days: 0,
        enabled: true,
    };
    
    addPeriodAndEmit(newRow);
}
```

**Nessuna propagazione necessaria**: il nuovo periodo si aggiunge al bordo libero (dopo l'ultimo).

### 9.7.2 — Delete Period (con modale data confine)

**Trigger**: Row action `✕ Delete` su un periodo normale.

**3 casi**:

#### a) Primo periodo (nessun predecessore)

Il successore si espande: il suo `start_date` diventa lo `start_date` del periodo eliminato.
**Nessuna modale.**

#### b) Ultimo periodo (nessun successore tra i normali)

Il predecessore si espande: il suo `end_date` diventa l'`end_date` del periodo eliminato.
**Nessuna modale.**

#### c) Periodo nel mezzo (ha predecessore E successore)

**Modale** `DeletePeriodModal.svelte` con:
- Titolo: "Delete Period — Choose Boundary"
- Messaggio: "Choose the boundary date to redistribute this period's range between its neighbors."
- **DatePicker** (`<input type="date">`) vincolato a `[deleted.start_date, deleted.end_date]`
- **Default**: punto medio del range eliminato (`midpointDate(start, end)`)
- Bottone "Confirm Delete"

**Logica conferma**:
- Tutto fino a `boundaryDate` → il predecessore espande il suo `end_date` a `boundaryDate`
- Tutto dopo `boundaryDate` → il successore anticipa il suo `start_date` a `addDays(boundaryDate, 1)`

```typescript
function handleDelete(rowIndex: number): void {
    const periods = getNormalPeriods();
    const toDelete = periods[rowIndex];
    
    if (periods.length === 1) {
        // Unico periodo: elimina e basta → empty state
        periods.splice(rowIndex, 1);
        updatePeriodsAndEmit(periods);
        return;
    }
    
    const hasPrev = rowIndex > 0;
    const hasNext = rowIndex < periods.length - 1;
    
    if (hasPrev && hasNext) {
        // MEZZO: apri modale con date picker per boundary
        pendingDeleteIndex = rowIndex;
        deleteModalStart = toDelete.start_date;
        deleteModalEnd = toDelete.end_date;
        deleteModalDefault = midpointDate(toDelete.start_date, toDelete.end_date);
        showDeleteModal = true;
        return;
    }
    
    if (hasPrev && !hasNext) {
        // Ultimo: predecessore prende tutto
        periods[rowIndex - 1].end_date = toDelete.end_date;
    } else if (!hasPrev && hasNext) {
        // Primo: successore prende tutto
        periods[rowIndex + 1].start_date = toDelete.start_date;
    }
    
    periods.splice(rowIndex, 1);
    updatePeriodsAndEmit(periods);
}

function confirmDelete(boundaryDate: string): void {
    const periods = getNormalPeriods();
    const rowIndex = pendingDeleteIndex;
    
    periods[rowIndex - 1].end_date = boundaryDate;
    periods[rowIndex + 1].start_date = addDays(boundaryDate, 1);
    
    periods.splice(rowIndex, 1);
    showDeleteModal = false;
    updatePeriodsAndEmit(periods);
}
```

### 9.7.3 — Split Period (row action + modale)

**Trigger**: Row action `✂️ Split` (icona `Scissors` da `lucide-svelte`).

**Stessa modale** `DeletePeriodModal.svelte` riutilizzata con `mode: 'split'`:
- Titolo: "Split Period — Choose Boundary"
- Messaggio: "Choose the date where this period will be split into two."
- **DatePicker** vincolato a `[start_date + 1, end_date - 1]` (serve spazio per 2 sotto-periodi)
- **Default**: punto medio del periodo
- **Disabilitato**: se la durata è ≤ 1 giorno (il bottone Split è grigio nella row action)

```typescript
function handleSplit(rowIndex: number, boundaryDate: string): void {
    const periods = getNormalPeriods();
    const original = periods[rowIndex];
    
    const row1: ScheduleRow = {
        ...structuredClone(original),
        id: crypto.randomUUID(),
        end_date: boundaryDate,
    };
    const row2: ScheduleRow = {
        ...structuredClone(original),
        id: crypto.randomUUID(),
        start_date: addDays(boundaryDate, 1),
    };
    
    // Sostituisci l'originale con i due nuovi
    periods.splice(rowIndex, 1, row1, row2);
    updatePeriodsAndEmit(periods);
}
```

Le due nuove righe hanno configurazioni identiche (rate, compounding, day count) eccetto il date range.

### 9.7.4 — Merge Periods (bulk action contigue)

**Trigger**: Bulk action `🔗 Merge` nella `DataTableToolbar`.

**Visibilità**: Quando ≥ 2 righe normali sono selezionate.

**Vincolo**: Le righe selezionate devono essere **contigue** (indici consecutivi senza buchi).
Se non contigue → bottone Merge `disabled` con tooltip "Only contiguous periods can be merged".

```typescript
function areContiguous(sortedIndices: number[]): boolean {
    for (let i = 1; i < sortedIndices.length; i++) {
        if (sortedIndices[i] !== sortedIndices[i - 1] + 1) return false;
    }
    return true;
}

function handleMerge(selectedRows: ScheduleRow[]): void {
    const periods = getNormalPeriods();
    
    // Trova gli indici e verifica contiguità
    const indices = selectedRows
        .map(r => periods.findIndex(p => p.id === r.id))
        .filter(i => i >= 0)
        .sort((a, b) => a - b);
    
    if (!areContiguous(indices)) return; // safety check
    
    const first = periods[indices[0]];
    const last = periods[indices[indices.length - 1]];
    
    // Il merged period prende le configurazioni della PRIMA riga
    const merged: ScheduleRow = {
        ...structuredClone(first),
        id: crypto.randomUUID(),
        end_date: last.end_date,  // range esteso fino alla fine dell'ultima
    };
    
    // Rimuovi tutte le righe selezionate e inserisci il merged al posto della prima
    periods.splice(indices[0], indices.length, merged);
    
    // Clear selection
    selectedIds = [];
    updatePeriodsAndEmit(periods);
}
```

### 9.7.5 — Bulk Delete

**Trigger**: Bulk action `🗑 Delete` nella `DataTableToolbar`, `variant: 'danger'`.

Quando si cancellano **più righe contigue** in bulk:
- Se il blocco eliminato ha sia predecessore che successore → stessa modale boundary date
- Se il blocco è all'inizio → il successore (prima riga NON selezionata) si espande a sinistra
- Se il blocco è alla fine → il predecessore (ultima riga NON selezionata) si espande a destra
- Se si eliminano TUTTE le righe → empty state

```typescript
function handleBulkDelete(selectedRows: ScheduleRow[]): void {
    const periods = getNormalPeriods();
    const indices = selectedRows
        .map(r => periods.findIndex(p => p.id === r.id))
        .filter(i => i >= 0)
        .sort((a, b) => a - b);
    
    if (indices.length === 0) return;
    
    const firstIdx = indices[0];
    const lastIdx = indices[indices.length - 1];
    const blockStart = periods[firstIdx].start_date;
    const blockEnd = periods[lastIdx].end_date;
    
    const hasPrev = firstIdx > 0;
    const hasNext = lastIdx < periods.length - 1;
    
    if (hasPrev && hasNext) {
        // Blocco nel mezzo → modale boundary
        pendingBulkDeleteIndices = indices;
        deleteModalStart = blockStart;
        deleteModalEnd = blockEnd;
        deleteModalDefault = midpointDate(blockStart, blockEnd);
        showDeleteModal = true;
        return;
    }
    
    if (hasPrev) {
        periods[firstIdx - 1].end_date = blockEnd;
    } else if (hasNext) {
        periods[lastIdx + 1].start_date = blockStart;
    }
    
    // Rimuovi dal fondo per non invalidare gli indici
    for (let i = indices.length - 1; i >= 0; i--) {
        periods.splice(indices[i], 1);
    }
    
    selectedIds = [];
    updatePeriodsAndEmit(periods);
}
```

### Riepilogo Bulk Actions per DataTableToolbar

```typescript
const bulkActions = [
    {
        id: 'merge',
        icon: Link2,           // lucide-svelte
        label: () => $t('assets.schedule.merge'),
        onClick: () => handleMerge(getSelectedRows()),
        disabled: !areSelectedContiguous(),  // disabilitato se non contigue
    },
    {
        id: 'delete',
        icon: Trash2,
        label: () => $t('assets.schedule.deleteSelected'),
        variant: 'danger',
        onClick: () => handleBulkDelete(getSelectedRows()),
    },
];
```

---

## §9.8 — Tooltips con link docs

Ogni header di colonna ha un `ℹ️` (già supportato da DataTable via `headerTooltip`)
con spiegazione rapida + link cliccabile alla documentazione.

| Colonna | Tooltip i18n Key | Link doc |
|---------|-----------------|----------|
| Period | `assets.schedule.periodHint` | — |
| Rate % | `assets.schedule.rateHint` | `financial-theory/returns` |
| Compounding | `assets.schedule.compoundingHint` | `financial-theory/compounding` (**NUOVA** pagina) |
| Comp. Freq. | `assets.schedule.freqHint` | `financial-theory/compounding` |
| Day Count | `assets.schedule.dayCountHint` | `financial-theory/day-count` |

**Implementazione tooltip**: `headerTooltip` restituisce HTML con link:
```typescript
headerTooltip: () => `${$t('assets.schedule.compoundingHint')}
    <br/><a href="/docs/financial-theory/compounding"
    target="_blank" class="underline text-libre-green">📖 ${$t('common.learnMore')}</a>`
```

**Pagina docs nuova**: `compounding.{en,it,fr,es}.md` sotto `financial-theory/`:
- Simple vs Compound interest (formule)
- Compound Frequency (DAILY, MONTHLY, QUARTERLY, SEMIANNUAL, ANNUAL, CONTINUOUS)
- Esempi numerici
- Link da `index.{en,it,fr,es}.md`

---

## §9.9 — Validazione (aggiornata)

### Regole eliminate (by design)

| Regola | Stato | Motivo |
|--------|-------|--------|
| ~~Overlap~~ | **Impossibile** | Propagazione automatica (§9.6) |
| ~~Gap / Non contiguità~~ | **Impossibile** | Propagazione automatica (§9.6) |
| ~~end_date < start_date~~ | **Impedito** | DateRangePicker non consente selezione invalida |

### Regole attive

| Regola | Tipo | Visuale |
|--------|------|---------|
| `annual_rate ≥ 0` | Error (red) | Input con bordo rosso |
| Almeno 1 periodo | Error (red) | Empty state con CTA |
| `compound_frequency` richiesto se `compounding == 'COMPOUND'` | Error (red) | Select evidenziato rosso |
| Late: `grace_period_days ≥ 0` | Error (red) | Input bordo rosso |

### Banner di stato (sotto la tabella)

Stile `DistributionEditor` con total badge:

```
✅ 2 periods, contiguous — 2025-01-01 → 2025-12-31 (365 days) + late interest
```
oppure (senza late):
```
✅ 2 periods, contiguous — 2025-01-01 → 2025-12-31 (365 days)
```
oppure (errori):
```
❌ Rate must be ≥ 0 in period 2  |  ❌ Compound frequency required when compounding is COMPOUND
```

### Empty state (0 periodi)

```
┌─────────────────────────────────────────────┐
│   📅 No interest periods defined             │
│   Add at least one period to configure       │
│   the investment schedule.                   │
│                                              │
│          [+ Add First Period]                │
└─────────────────────────────────────────────┘
```

### `isFormValid` derivato

```typescript
let isFormValid = $derived.by(() => {
    const normals = getNormalPeriods();
    if (normals.length === 0) return false;
    for (const p of normals) {
        if (p.annual_rate < 0) return false;
        if (p.compounding === 'COMPOUND' && !p.compound_frequency) return false;
    }
    const late = rows.find(r => r.isLate);
    if (late?.enabled) {
        if (late.annual_rate < 0) return false;
        if (late.grace_period_days < 0) return false;
        if (late.compounding === 'COMPOUND' && !late.compound_frequency) return false;
    }
    return true;
});
```

---

## §9.10 — Serializzazione JSON ↔ Form

### Deserializzazione (`provider_params` JSON → `ScheduleRow[]`)

```typescript
function deserialize(value: Record<string, any>): ScheduleRow[] {
    const rows: ScheduleRow[] = [];
    const schedule = value?.schedule ?? [];
    
    for (const p of schedule) {
        rows.push({
            id: crypto.randomUUID(),
            start_date: p.start_date,
            end_date: p.end_date,
            annual_rate: Number(p.annual_rate) * 100,  // 0.05 → 5.00
            compounding: p.compounding ?? 'SIMPLE',
            compound_frequency: p.compound_frequency ?? null,
            day_count: p.day_count ?? 'ACT/365',
            isLate: false,
            grace_period_days: 0,
            enabled: true,
        });
    }
    
    // Late interest row — SEMPRE presente (anche se late_interest è null nel JSON)
    const li = value?.late_interest;
    rows.push({
        id: 'late-interest',
        start_date: rows.length > 0 ? addDays(rows[rows.length - 1].end_date, 1) : '',
        end_date: '',  // ∞
        annual_rate: li ? Number(li.annual_rate) * 100 : 12,
        compounding: li?.compounding ?? 'SIMPLE',
        compound_frequency: li?.compound_frequency ?? null,
        day_count: li?.day_count ?? 'ACT/365',
        isLate: true,
        grace_period_days: li?.grace_period_days ?? 0,
        enabled: !!li,  // true se late_interest esiste nel JSON, false altrimenti
    });
    
    return rows;
}
```

### Serializzazione (`ScheduleRow[]` → JSON)

```typescript
function serialize(rows: ScheduleRow[]): Record<string, any> {
    const schedule = rows
        .filter(r => !r.isLate)
        .map(r => ({
            start_date: r.start_date,
            end_date: r.end_date,
            annual_rate: (r.annual_rate / 100).toFixed(4),  // 5.00 → "0.0500"
            compounding: r.compounding,
            compound_frequency: r.compounding === 'COMPOUND' ? r.compound_frequency : undefined,
            day_count: r.day_count,
        }));
    
    const lateRow = rows.find(r => r.isLate && r.enabled);
    const late_interest = lateRow ? {
        annual_rate: (lateRow.annual_rate / 100).toFixed(4),
        grace_period_days: lateRow.grace_period_days,
        compounding: lateRow.compounding,
        compound_frequency: lateRow.compounding === 'COMPOUND' ? lateRow.compound_frequency : undefined,
        day_count: lateRow.day_count,
    } : null;
    
    return { schedule, late_interest };
}
```

---

## §9.11 — File coinvolti (aggiornato)

| File | Azione |
|------|--------|
| `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte` | **NUOVO** — componente principale: DataTable + CRUD + contiguità + serializzazione |
| `frontend/src/lib/components/assets/CellDateRange.svelte` | **NUOVO** — wrapper DateRangePicker compatto per CustomCell |
| `frontend/src/lib/components/assets/BoundaryDateModal.svelte` | **NUOVO** — modale riusabile per scelta data confine (delete + split) |
| `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` | Switch `ui_component` → mount ScheduledInvestmentEditor |
| `backend/app/schemas/provider.py` | `ui_component: Optional[str]` in `FAProviderInfo` |
| `backend/app/services/asset_source.py` | `ui_component` property in base class |
| `backend/app/services/asset_source_providers/scheduled_investment.py` | Override `ui_component = "scheduled_investment"` |
| `backend/app/api/v1/assets.py` | Popolare `ui_component` in `list_providers` |
| `mkdocs_src/docs/financial-theory/compounding.{en,it,fr,es}.md` | **NUOVA** pagina docs compounding |
| `mkdocs_src/docs/financial-theory/index.{en,it,fr,es}.md` | Aggiungere link a compounding |
| Frontend i18n (`en.json`, `it.json`, `fr.json`, `es.json`) | Chiavi tooltip schedule + label CRUD |

---

## §9.12 — Effort stimato (aggiornato)

| Sub-task | Effort |
|----------|--------|
| `CellDateRange.svelte` (wrapper DateRangePicker + popover positioning) | 25 min |
| `ScheduledInvestmentEditor.svelte` (DataTable + colonne + serialize/deserialize) | 40 min |
| Late interest riga speciale + toggle on/off + graying CSS | 15 min |
| Sistema contiguità automatica (`handleRangeChange` + propagazione multi-riga) | 35 min |
| Add Period (auto start/end, copy config from last) | 5 min |
| Delete Period + `BoundaryDateModal.svelte` (modale riusabile) | 20 min |
| Split Period (row action + riuso modale boundary) | 15 min |
| Merge Periods (bulk action + contiguity check + DataTableToolbar) | 15 min |
| Bulk Delete (con modale boundary per blocco nel mezzo) | 10 min |
| `ui_component` backend (schema + base + override + endpoint) | 10 min |
| Tooltip con link docs + i18n chiavi | 10 min |
| `compounding.md` docs (4 lingue) | 20 min |
| Validazione client-side (rate, compound_freq, empty state, banner) | 10 min |
| `./dev.py api sync` + test integrazione | 10 min |
| **Totale F9** | **~4 ore** |

---

## Scelte di design — Riepilogo

| Decisione | Scelta |
|-----------|--------|
| Layout tabella | **β** — colonna Period singola con DateRangePicker |
| Late Interest | Riga speciale permanente con toggle on/off, graying quando off |
| Contiguità | Propagazione automatica, overlap impossibile by design |
| Add | Start auto, end +1 mese, copy config da ultimo periodo |
| Delete (mezzo) | Modale con data confine (boundary date) |
| Delete (estremi) | Espansione automatica del vicino, nessuna modale |
| Split | Row action ✂️, modale con data confine, 2 righe identiche eccetto range |
| Merge | Bulk action 🔗, solo righe contigue, config della prima riga |
| Modale | `BoundaryDateModal.svelte` condivisa tra Delete e Split (`mode: 'delete' \| 'split'`) |
| Feedback cascata | Toast breve (sonner) quando propagazione elimina righe vicine |

---

## Validation Checklist (solo F9)

- [ ] `ScheduledInvestmentEditor` renderizza DataTable con colonne corrette
- [ ] `CellDateRange` apre DateRangePicker in popover, posizionamento fixed corretto
- [ ] Late interest riga sempre presente, toggle on/off funzionante
- [ ] Late interest OFF: opacità ridotta, campi disabled, toggle cliccabile
- [ ] Add Period: start auto, end +1m, copy config
- [ ] Delete primo/ultimo: espansione automatica vicino, no modale
- [ ] Delete mezzo: modale boundary date, ridistribuzione corretta
- [ ] Split: modale boundary, 2 righe identiche eccetto range
- [ ] Merge: solo contigue, config prima riga, range unificato
- [ ] Contiguità: espansione/contrazione propaga ai vicini
- [ ] Contiguità: eliminazione cascata se vicino "mangiato" completamente
- [ ] Serializzazione: JSON ↔ form bidirezionale corretta
- [ ] `compound_frequency` condizionale (visibile solo se COMPOUND)
- [ ] Validazione: rate ≥ 0, compound_freq richiesto se COMPOUND
- [ ] Empty state con CTA "Add First Period"
- [ ] Banner stato sotto tabella (✅ contiguous, ❌ errors)
- [ ] Tooltips ℹ️ su header con link docs
- [ ] `ui_component` backend → frontend switch funzionante
- [ ] `compounding.md` docs presente (4 lingue)
- [ ] i18n chiavi complete (EN, IT, FR, ES)

