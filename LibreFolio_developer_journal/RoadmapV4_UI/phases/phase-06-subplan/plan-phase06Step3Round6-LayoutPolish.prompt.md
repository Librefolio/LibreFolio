# Plan: Phase 6 Step 3 — Round 6: Layout B + Provider Polish

Post Round 5.1. Layout B (Two-Panel Split) con responsive wrapping,
9 fix/feature (F1–F9), ScheduledInvestmentEditor strutturato.

---

## 🔍 Analisi Comparativa Provider — Campi Fissi vs params_schema

### Campi FISSI (comuni a TUTTI i provider)

| Campo | Tipo UI | Note |
|-------|---------|------|
| `provider_code` | SimpleSelect | Scelta del provider |
| `identifier` | Text input | Come il provider identifica l'asset |
| `identifier_type` | SimpleSelect **(filtrato per provider)** | Solo i tipi accettati dal provider |
| `fetch_interval` | **HH:MM** (frontend) → minuti (API) | Persistenza: `FAProviderAssignmentItem` |
| `user_url` | Text input | URL personalizzato dall'utente |
| `provider_url` | Text readonly | Auto-generato da `get_asset_url()` |
| `provider_params` | **DINAMICO — da params_schema** | Sub-panel visibile solo se presente |

### Campi DINAMICI per provider (params_schema)

#### 1. **yfinance** — `params_schema: []` · `accepted_identifier_types: [TICKER, ISIN]`

Nessun parametro extra. Azioni, ETF, crypto via Yahoo Finance.

```
┌─────────────────────────────┬────────────────────────────────────┐
│ Provider [🟡 Yahoo Fin. ▾]  │ [▶ Test Configuration]             │
│ ID Type [TICKER ▾]          │ ├ ✅ Price: 189.84 USD (0.5s)     │
│ Identifier [AAPL________]   │ ├ ✅ History: 5 pts (0.3s)        │
│ Fetch ⏱ [24:00] (hh:mm)    │ └ Total: 0.8s                     │
│                              │ Prov URL: [finance.yahoo.com/…] ↗ │
│                              │ User URL: [___________________]   │
└─────────────────────────────┴────────────────────────────────────┘
```

#### 2. **justetf** — `params_schema: []` · `accepted_identifier_types: [ISIN]`

Nessun parametro extra. Solo ETF europei via ISIN.

```
┌─────────────────────────────┬────────────────────────────────────┐
│ Provider [🔶 JustETF    ▾]  │ [▶ Test Configuration]             │
│ ID Type [ISIN] (auto-set)   │ ├ ✅ Price: 47.45 EUR (0.8s)     │
│ Identifier [IE00B0M63177]   │ ├ ✅ History: 8 pts (0.01s)       │
│ Fetch ⏱ [24:00] (hh:mm)    │ └ Total: 0.8s                     │
│                              │ Prov URL: [justetf.com/…] ↗       │
│                              │ User URL: [___________________]   │
└─────────────────────────────┴────────────────────────────────────┘
```

#### 3. **cssscraper** — `params_schema: [5 campi]` · `accepted_identifier_types: [OTHER]`

Provider complesso. Identifier = URL. 5 parametri custom in sub-panel.

```
┌─────────────────────────────┬────────���───────────────────────────┐
│ Provider [🌐 CSS Scraper ▾] │ [▶ Test Configuration]             │
│ ID Type [OTHER] (auto-set)  │ ├ ✅ Price: 12.34 EUR (2.1s)     │
│ Identifier [https://ex.com] │ └ Total: 2.1s                     │
│ Fetch ⏱ [24:00] (hh:mm)    │ Prov URL: [= identifier] ↗        │
│ ┌─ params ────────────────┐ │ User URL: [___________________]   │
│ │ CSS Selector * [.price] │ │                                    │
│ │ Currency *     [EUR   ] │ │                                    │
│ │ Decimal Format [us   ▾] │ │                                    │
│ │ Timeout        [30    ] │ │                                    │
│ │ User-Agent [Libre/1.0]  │ │                                    │
│ └─────────────────────────┘ │                                    │
└─────────────────────────────┴────────────────────────────────────┘
```

#### 4. **scheduled_investment** — `params_schema: [2 JSON]` · `accepted_identifier_types: [UUID]`

Per prestiti P2P e obbligazioni. Parametri complessi renderizzati da
`ScheduledInvestmentEditor.svelte` (form strutturato, non JSON grezzo).

```
┌─────────────────────────────────────────────────────────────────┐
│ Provider [📅 Sched. Invest. ▾]  │ [▶ Test Configuration]        │
│ ID Type [UUID] (auto-set)       │ ├ ✅ Price: 10250.00 EUR      │
│ Identifier [auto-filled]        │ └ Total: 0.1s                 │
│ Fetch ⏱ [24:00] (hh:mm)        │ User URL: [____________]      │
│ ┌─ Interest Schedule ──────────────────────────────────────────┐│
│ │ ┌──────────┬──────────┬──────┬───────────┬────────────┬────┐ ││
│ │ │Start Date│End Date  │Rate %│Compounding│Comp. Freq. │Days│ ││
│ │ ├──────────┼──────────┼──────┼───────────┼────────────┼────┤ ││
│ │ │2025-01-01│2025-06-30│ 5.00 │ SIMPLE    │ —          │A365│ ││
│ │ │2025-07-01│2025-12-31│ 6.00 │ COMPOUND  │ MONTHLY    │A365│ ││
│ │ └──────────┴──────────┴──────┴───────────┴────────────┴────┘ ││
│ │ [+ Add Period]                                    Total: 12m ││
│ │                                                               ││
│ │ □ Late Interest                                               ││
│ │ ┌ Rate: [12.00] %  Grace: [30] days  Day Count: [ACT/365 ▾] ┐││
│ │ └ Compounding: [SIMPLE ▾]                                    ┘││
│ └───────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**NOTA**: Quando il left panel è largo (scheduled_investment con DataTable),
il right panel wrappa automaticamente sotto — stack verticale via flex-wrap.

### Riepilogo

| Provider | params_schema | accepted_id_types | Sub-panel |
|----------|--------------|-------------------|-----------|
| yfinance | 0 campi | TICKER, ISIN | — |
| justetf | 0 campi | ISIN | — |
| cssscraper | 5 campi (string, select, number) | OTHER | Generico |
| scheduled_investment | 2 campi JSON | UUID | ScheduledInvestmentEditor |

---

## 📐 Layout B — "Two-Panel Split" con Responsive Wrapping

### Struttura

```
┌──────────────────────────────────────────────────────────────────┐
│ PROVIDER ASSIGNMENT                                     □ No Prov│
├──────────────────────────────────────────────────────────────────┤
│  ┌─ LEFT: Configuration ──────┐  ┌─ RIGHT: Test & URLs ────────┐│
│  │ Provider [▾]                │  │ [▶ Test Configuration]      ││
│  │ ID Type [▾] (filtered)     │  │ ├ ✅ Price: …    0.8s       ││
│  │ Identifier [__________]    │  │ ├ ✅ History: …  0.01s      ││
│  │ Fetch ⏱ [HH] h [MM] m     │  │ └ Total: 0.81s              ││
│  │ (params sub-panel if any)  │  │ Prov URL: [______] ↗        ││
│  └────────────────────────────┘  │ User URL: [______]          ││
│                                   └─────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

### Responsive Wrapping — CSS

```html
<div class="flex flex-wrap gap-4">
  <!-- LEFT: Configuration -->
  <div class="flex-1 min-w-[280px] space-y-3">
    … provider, id type, identifier, fetch, params …
  </div>
  <!-- RIGHT: Test & URLs -->
  <div class="flex-1 min-w-[250px] space-y-3 border-l border-gray-200 dark:border-slate-700 pl-4
              max-[599px]:border-l-0 max-[599px]:pl-0 max-[599px]:border-t max-[599px]:pt-4">
    … test button, results, provider url, user url …
  </div>
</div>
```

**Comportamento**:
- **Desktop (container ≥ 530px)**: Due colonne affiancate con border-left divisore
- **Mobile / left troppo largo**: Right wrappa sotto → stack verticale, border-top al posto di border-left
- Il wrapping è **automatico** via `flex-wrap` — nessun breakpoint rigido necessario
- `min-w-[280px]` + `min-w-[250px]` = 530px totale → sotto questa soglia si stacka

---

## 🐛 Fix e Feature — F1–F9

### F1 — SimpleSelect dropdown troncato dentro panel collapsible

**Problema**: Dropdown `position: absolute` clippato da parent `overflow-y: auto`.

**Soluzione**: Usare `position: fixed` + coordinate `getBoundingClientRect()` quando
`dropdownPosition="auto"`. Il dropdown esce da qualsiasi parent con overflow.
Aggiornare coordinate su scroll del parent.

**File**: `frontend/src/lib/components/ui/select/SimpleSelect.svelte`

---

### F2 — "Other" in fondo alle distribuzioni di default

**Problema**: "Other" ordinato per peso come gli altri, utente si aspetta sempre ultimo.

**Soluzione**: Sort secondario `key === 'Other'` → always last nel `$effect` sync.

```typescript
.sort((a, b) => {
    if (a.key === 'Other' && b.key !== 'Other') return 1;
    if (b.key === 'Other' && a.key !== 'Other') return -1;
    return b.weight - a.weight;
});
```

**File**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

---

### F3 — Paginazione ∞ nelle distribuzioni

**Soluzione**: `pageSizeOptions={[5, 10, 25, 0]}` (0 = ∞ nel DataTable).

**File**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

---

### F4 — Tooltip history: mostrare valuta

**Problema**: Sample prices senza valuta. Current price mostra EUR.

**Soluzione**: Dopo aver processato i test results, copiare `priceCurrency`
dal current_price alla history. Nel tooltip history header: `💰 Close (EUR)`.

```typescript
const cpCurrency = items.find(r => r.priceCurrency)?.priceCurrency ?? '';
for (const item of items) {
    if (item.samplePrices && !item.priceCurrency) item.priceCurrency = cpCurrency;
}
```

Nel tooltip:
```typescript
html += `<tr><th>📅 Date</th><th>💰 Close${result.priceCurrency ? ` (${result.priceCurrency})` : ''}</th></tr>`;
```

**File**: `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte`

---

### F5 — Layout B: Two-Panel Split + responsive wrap

Ristrutturare il template HTML di `ProviderAssignmentSection` secondo il layout B.

**Left panel**: Provider select, ID Type (filtrato), Identifier, Fetch ⏱ HH:MM, params sub-panel.
**Right panel**: Test button, risultati, Provider URL (readonly + link), User URL.

**CSS**: `flex flex-wrap gap-4`, left `flex-1 min-w-[280px]`, right `flex-1 min-w-[250px]`.
Border divisore destro su left: visibile solo quando affiancato.

**File**: `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte`

---

### F6 — Rimuovere bottoni "Remove" esterni a ImagePickerWrapper

**Problema**: Workaround pre-Round 5.1, ora ridondante.

**a) `BrokerForm.svelte`** (riga 288-296): Rimuovere bottone "Remove" sotto l'icona.
Tenere solo `{#if iconUrl} <p class="…truncate">{iconUrl}</p> {/if}` senza il `<button>`.

**b) `ProfileTab.svelte`**: Rimuovere:
- Bottone "Remove" (righe 375-383)
- State `showRemoveAvatarConfirm` (riga 229)
- Funzioni `requestRemoveAvatar`, `confirmRemoveAvatar`, `cancelRemoveAvatar` (righe 231-243)
- Modale "Confirm Remove Avatar" (righe 715-754)

**File**: `BrokerForm.svelte`, `ProfileTab.svelte`

---

### F7 — Fetch Interval: HH:MM nel frontend

**Problema**: Input numerico in minuti non intuitivo. 1440 = ?

**Soluzione**: Due input affiancati (ore + minuti) → conversione client-side.

```svelte
<div class="flex items-center gap-1">
  <input type="number" min={0} max={999} class="w-16 …"
         value={Math.floor(fetchInterval / 60)}
         oninput={(e) => {
             fetchInterval = Number(e.target.value) * 60 + (fetchInterval % 60);
             emitChange();
         }} />
  <span class="text-xs text-gray-400">h</span>
  <input type="number" min={0} max={59} class="w-14 …"
         value={fetchInterval % 60}
         oninput={(e) => {
             fetchInterval = Math.floor(fetchInterval / 60) * 60 + Number(e.target.value);
             emitChange();
         }} />
  <span class="text-xs text-gray-400">m</span>
</div>
<p class="text-[10px] text-gray-400">ⓘ 24h 00m = daily, 1h 00m = hourly, 168h 00m = weekly</p>
```

Nessuna modifica backend — l'API resta in minuti.

**File**: `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte`

---

### F8 — `accepted_identifier_types` per provider

**Problema**: Dropdown ID Type mostra tutti i 7 tipi. JustETF accetta solo ISIN, ecc.

#### Backend (4 file)

**a)** `backend/app/services/asset_source.py` — base class, nuova property:
```python
@property
def accepted_identifier_types(self) -> list["IdentifierType"]:
    """Identifier types accepted by this provider. Default: all."""
    from backend.app.db import IdentifierType
    return list(IdentifierType)
```

**b)** Ogni provider concreto — override:

| Provider | File | Override |
|----------|------|---------|
| yfinance | `yahoo_finance.py` | `[IdentifierType.TICKER, IdentifierType.ISIN]` |
| justetf | `justetf.py` | `[IdentifierType.ISIN]` |
| cssscraper | `css_scraper.py` | `[IdentifierType.OTHER]` |
| scheduled_investment | `scheduled_investment.py` | `[IdentifierType.UUID]` |
| mockprov | `mockprov.py` | `[IdentifierType.TICKER, IdentifierType.UUID]` |

**c)** `backend/app/schemas/provider.py` — `FAProviderInfo`:
```python
accepted_identifier_types: List[str] = Field(
    default_factory=list,
    description="Identifier types accepted by this provider"
)
```

**d)** `backend/app/api/v1/assets.py` — `list_providers`:
```python
FAProviderInfo(
    …,
    accepted_identifier_types=[t.value for t in instance.accepted_identifier_types],
)
```

#### Frontend (1 file + api sync)

**e)** `ProviderAssignmentSection.svelte`:
- Aggiornare `ProviderInfo` interface con `accepted_identifier_types?: string[]`
- `idTypeOptions` derivato: filtrare per provider selezionato
- Auto-set: se provider ha 1 solo tipo → impostarlo automaticamente

```typescript
let idTypeOptions = $derived<SelectOption[]>(() => {
    const accepted = selectedProvider?.accepted_identifier_types;
    const types = (accepted && accepted.length > 0)
        ? IDENTIFIER_TYPES.filter(t => accepted.includes(t))
        : IDENTIFIER_TYPES;
    return types.map(t => ({value: t, label: t}));
});
```

**f)** `./dev.py api sync` per rigenerare `generated.ts`.

---

### F9 — ScheduledInvestmentEditor.svelte — DETTAGLIO COMPLETO

#### 9.1 — Obiettivo

Componente che renderizza `FAScheduledInvestmentSchedule` come una **DataTable editabile**
con late interest nella stessa tabella, tooltips con link alla documentazione finanziaria,
e mappatura bidirezionale JSON ↔ form strutturato.

#### 9.2 — Come il backend dichiara "usa questo componente"

Aggiungere `ui_component` a `FAProviderInfo` (livello provider, non per-campo):

```python
# backend/app/schemas/provider.py
class FAProviderInfo(BaseModel):
    # ...existing fields...
    ui_component: Optional[str] = Field(
        None,
        description="Custom UI component for provider_params editing. "
                    "null = generic params loop, 'scheduled_investment' = ScheduledInvestmentEditor"
    )
```

```python
# backend/app/services/asset_source.py — AssetSourceProvider base
@property
def ui_component(self) -> str | None:
    """Custom UI component name for provider_params. Default: None (generic)."""
    return None
```

```python
# scheduled_investment.py override
@property
def ui_component(self) -> str | None:
    return "scheduled_investment"
```

```python
# backend/app/api/v1/assets.py — list_providers
FAProviderInfo(
    …,
    ui_component=instance.ui_component,
)
```

**Frontend switch**:
```svelte
{#if selectedProvider?.ui_component === 'scheduled_investment'}
    <ScheduledInvestmentEditor … />
{:else if paramsSchema.length > 0}
    <!-- Generic params loop -->
{/if}
```

Questo pattern è estensibile: futuri provider potranno dichiarare il proprio `ui_component`.

#### 9.3 — Nuova cell type: `editable-date` per DataTable

Per le date individuali (non il DateRangePicker), aggiungere un tipo cella nativo:

```typescript
// frontend/src/lib/components/table/types.ts
export interface EditableDateCell {
    type: 'editable-date';
    value: string;         // ISO YYYY-MM-DD
    min?: string;          // Min date constraint
    max?: string;          // Max date constraint
    disabled?: boolean;
    onchange: (newValue: string) => void;
}
```

Aggiungere a `CellContent` union + renderizzare in DataTable come `<input type="date">`.

#### 9.4 — Layout Tabella: DUE ALTERNATIVE

##### Alternativa α — Due colonne date separate + DateRangePicker come azione

Ogni periodo ha `Start Date` e `End Date` come colonne `editable-date`.
Il DateRangePicker è accessibile via un bottone "📅" inline che apre il popover
e pre-compila le due date.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ INTEREST SCHEDULE                                                        [+ Add Period] │
├──────────┬──────────┬──────┬───────────┬──────────────┬─────────┬───────────────────────┤
│Start Date│End Date  │Rate %│Compounding│Comp. Freq.   │Day Count│                     ✕ │
│  ℹ️       │  ℹ️       │ ℹ️    │ ℹ️          │ ℹ️             │ ℹ️        │                       │
├──────────┼──────────┼──────┼───────────┼──────────────┼─────────┼───────────────────────┤
│[25-01-01]│[25-06-30]│[5.00]│[SIMPLE ▾] │ —            │[A365 ▾] │                     ✕ │
│[25-07-01]│[25-12-31]│[6.00]│[COMPND ▾] │[MONTHLY   ▾] │[A365 ▾] │                     ✕ │
├──────────┴──────────┼──────┼───────────┼──────────────┼─────────┼───────────────────────┤
│ ⚡ Late Interest     │[12.0]│[SIMPLE ▾] │Grace: [30] d │[A365 ▾] │                   □ on│
│  (from 26-01-01 →∞) │      │           │              │         │                       │
└──────────────────────┴──────┴───────────┴──────────────┴─────────┴───────────────────────┘
  ✅ Periods contiguous       Total span: 2025-01-01 → 2025-12-31 (365 days)
```

**Pro**: Semplice, usa il cell type `editable-date` nativo, ogni campo è indipendente.
**Contro**: Due colonne date occupano più spazio orizzontale. Il DateRangePicker non
è usato direttamente nelle celle (ma potrebbe essere un bottone "📅 Select Range"
che pre-compila entrambe le celle).

##### Alternativa β — Colonna "Period" singola con DateRangePicker embedded

Una sola colonna "Period" che usa `CustomCell` con un wrapper di DateRangePicker
in modalità compatta (no presets, no custom window, stacked, compact).

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ INTEREST SCHEDULE                                              [+ Add Period] │
├──────────────────────┬──────┬───────────┬──────────────┬─────────┬───────────┤
│Period  ℹ️              │Rate %│Compounding│Comp. Freq.   │Day Count│         ✕ │
│                      │ ℹ️    │ ℹ️          │ ℹ️             │ ℹ️        │           │
├──────────────────────┼──────┼───────────┼──────────────┼─────────┼───────────┤
│📅 25-01-01 → 25-06-30│[5.00]│[SIMPLE ▾] │ —            │[A365 ▾] │         ✕ │
│📅 25-07-01 → 25-12-31│[6.00]│[COMPND ▾] │[MONTHLY   ▾] │[A365 ▾] │         ✕ │
├──────────────────────┼──────┼───────────┼──────────────┼─────────┼───────────┤
│⚡ Late (+30d grace →∞)│[12.0]│[SIMPLE ▾] │ —            │[A365 ▾] │       □ on│
└──────────────────────┴──────┴───────────┴──────────────┴─────────┴───────────┘
  ✅ Periods contiguous       Total span: 365 days
```

Click sulla cella "Period" → apre il DateRangePicker come popover:

```
  ┌──────────────────────────────────────┐
  │ 📅 25-01-01 → 25-06-30     [click]  │
  │ ┌────────────────────────────────┐   │
  │ │ From: [2025-01-01]             │   │
  │ │ To:   [2025-06-30]             │   │
  │ │    ┌ January 2025 ┐ ┌ June 25 ┐│   │
  │ │    │ ... calendar  │ │ ...     ││   │
  │ │    └───────────────┘ └─────────┘│   │
  │ └────────────────────────────────┘   │
  └──────────────────────────────────────┘
```

**Implementazione**: Nuovo componente `CellDateRange.svelte`:
```svelte
<script lang="ts">
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';
    interface Props {
        start: string;
        end: string;
        disabled?: boolean;
        isLateInterest?: boolean;
        graceDays?: number;
        onchange?: (start: string, end: string) => void;
        onGraceDaysChange?: (days: number) => void;
    }
    // ...click to toggle popover, compact DateRangePicker inside
</script>
```

Usato via `CustomCell` nella definizione colonne:
```typescript
{
    id: 'period', type: 'custom',
    cell: (row) => ({
        type: 'custom',
        component: CellDateRange,
        props: {
            start: row.start_date, end: row.end_date,
            isLateInterest: row.isLate, graceDays: row.grace_period_days,
            onchange: (s, e) => updatePeriodDates(row.id, s, e),
        },
    }),
}
```

**Pro**: Una sola colonna, riuso del DateRangePicker, UX coerente con il resto dell'app.
**Contro**: Il DateRangePicker è un componente pesante con dual-calendar e presets;
serve una prop per disabilitare presets/custom-window. Il popover in una cella
DataTable potrebbe avere problemi di z-index (come il SimpleSelect — stesso fix F1).

#### 9.5 — Late Interest come riga speciale nella stessa tabella

Il `FALateInterestConfig` backend ha:
- `annual_rate`, `grace_period_days`, `compounding`, `compound_frequency`, `day_count`

Mappatura nella tabella unificata:

| Campo tabella | Periodo normale | Late Interest |
|---------------|-----------------|---------------|
| Period / Start | Editabile | Auto: `last_period.end_date + 1` (readonly) |
| Period / End | Editabile | `∞` (readonly) |
| Rate % | Editabile | Editabile |
| Compounding | Editabile | Editabile |
| Comp. Freq. | Condizionale | Condizionale |
| Day Count | Editabile | Editabile |
| Grace Period | — (nascosto) | Editabile (visible solo per late) |

**Per Alternativa α** (due colonne date):
La colonna "Comp. Freq." mostra `Grace: [30] d` al posto della frequenza nella riga late.

**Per Alternativa β** (colonna Period singola):
Il grace period è dentro la cella Period: `⚡ Late (+30d grace → ∞)`.
Click sulla cella → popover con solo un campo "Grace Period Days: [30]".

**Toggle on/off**: Un checkbox nella colonna azioni della riga late (non un row action,
ma inline). Quando off, la riga late è nascosta/rimossa dal JSON.

**Dati interni**:
```typescript
interface ScheduleRow {
    id: string;
    start_date: string;     // ISO
    end_date: string;       // ISO, or '' for late interest
    annual_rate: number;    // as percentage (5.00 = 5%)
    compounding: string;    // 'SIMPLE' | 'COMPOUND'
    compound_frequency: string | null;
    day_count: string;      // 'ACT/365' etc.
    isLate: boolean;        // true = late interest row
    grace_period_days: number; // only for late
    enabled: boolean;       // toggle for late interest
}
```

**Ordinamento**: Solo cronologico per `start_date`. La riga late è sempre ultima.
DataTable sorting disabilitato — ordine forzato dal componente.

#### 9.6 — Tooltips con link alla documentazione

Ogni header di colonna ha un `ℹ️` (già supportato da DataTable via `headerTooltip`)
che mostra una spiegazione rapida + link alla pagina financial-theory.

| Colonna | Tooltip | Link doc |
|---------|---------|----------|
| Period / Dates | "Start and end dates for this interest period" | — |
| Rate % | "Annual interest rate applied during this period" | `financial-theory/returns` |
| Compounding | "SIMPLE = interest on principal only. COMPOUND = interest on interest." | `financial-theory/synthetic-benchmarks#compound-growth` |
| Comp. Freq. | "How often compound interest is calculated (MONTHLY, QUARTERLY, ...)" | `financial-theory/synthetic-benchmarks#compound-growth` |
| Day Count | "Convention for counting days between dates (ACT/365, 30/360, ...)" | `financial-theory/day-count` |

**Implementazione tooltip**: `headerTooltip` restituisce HTML con link:
```typescript
headerTooltip: () => `${$t('assets.schedule.compoundingHint')}
    <br/><a href="/docs/financial-theory/synthetic-benchmarks#compound-growth"
    target="_blank" class="underline text-libre-green">📖 ${$t('common.learnMore')}</a>`
```

**Pagina docs mancante**: Serve una pagina dedicata **`compounding.{en,it,fr,es}.md`**
sotto `financial-theory/` che spieghi:
- Simple vs Compound interest (formule)
- Compound Frequency (DAILY, MONTHLY, QUARTERLY, SEMIANNUAL, ANNUAL, CONTINUOUS)
- Esempi numerici

Attualmente `synthetic-benchmarks.en.md` contiene la teoria del compound growth
ma è focalizzata sui benchmark, non sull'interest schedule. Opzioni:
1. **Estrarre** una sezione dedicata `compounding.md` e linkare da synthetic-benchmarks
2. **Aggiungere** anchor `#compounding-types` a synthetic-benchmarks e linkarla

Suggerisco opzione 1 (pagina separata) per chiarezza — la documentazione su
compounding/frequency è un concetto standalone usato sia da benchmark che da
scheduled_investment.

#### 9.7 — Validazione client-side

| Regola | Tipo | Visuale |
|--------|------|---------|
| Contiguità: `period[n].end + 1d == period[n+1].start` | Warning (amber) | Banner sotto tabella |
| Overlap: `period[n].end >= period[n+1].start` | Error (red) | Banner + celle date bordate rosso |
| Rate ≥ 0 | Error (red) | Input con bordo rosso |
| Almeno 1 periodo | Error (red) | Empty state con messaggio |
| `compound_frequency` richiesto se `compounding == COMPOUND` | Error (red) | Select evidenziato |
| `end_date >= start_date` per ogni periodo | Error (red) | Celle date evidenziate |
| Late interest: `grace_period_days ≥ 0` | Error (red) | Input bordo rosso |

**Banner di stato** sotto la tabella (come `DistributionEditor` con il total badge):
```
✅ 2 periods, contiguous — 2025-01-01 → 2025-12-31 (365 days) + late interest
```
oppure
```
⚠️ Gap between period 1 (end 2025-06-30) and period 2 (start 2025-07-15): 14 days
```

#### 9.8 — Serializzazione JSON ↔ Form

**Da JSON (input) → righe tabella**:
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
    // Late interest row
    const li = value?.late_interest;
    rows.push({
        id: 'late-interest',
        start_date: rows.length > 0 ? addDays(rows[rows.length-1].end_date, 1) : '',
        end_date: '',  // ∞
        annual_rate: li ? Number(li.annual_rate) * 100 : 12,
        compounding: li?.compounding ?? 'SIMPLE',
        compound_frequency: li?.compound_frequency ?? null,
        day_count: li?.day_count ?? 'ACT/365',
        isLate: true,
        grace_period_days: li?.grace_period_days ?? 0,
        enabled: !!li,
    });
    return rows;
}
```

**Da righe tabella → JSON (output)**:
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

#### 9.9 — File coinvolti (riepilogo F9)

| File | Azione |
|------|--------|
| `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte` | **NUOVO** — componente principale |
| `frontend/src/lib/components/assets/CellDateRange.svelte` | **NUOVO** — wrapper DateRangePicker per CustomCell (solo se Alt. β) |
| `frontend/src/lib/components/table/types.ts` | Aggiungere `EditableDateCell` a CellContent union |
| `frontend/src/lib/components/table/DataTable.svelte` | Renderizzare `editable-date` cell type |
| `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` | Switch `ui_component` |
| `backend/app/schemas/provider.py` | `ui_component` in `FAProviderInfo` |
| `backend/app/services/asset_source.py` | `ui_component` property in base class |
| `backend/app/services/asset_source_providers/scheduled_investment.py` | Override `ui_component` |
| `backend/app/api/v1/assets.py` | Popolare `ui_component` in list_providers |
| `mkdocs_src/docs/financial-theory/compounding.{en,it,fr,es}.md` | **NUOVA** pagina compounding |
| `mkdocs_src/docs/financial-theory/index.{en,it,fr,es}.md` | Aggiungere link a compounding |
| Frontend i18n files (`en.json`, `it.json`, `fr.json`, `es.json`) | Chiavi tooltip schedule |

#### 9.10 — Effort stimato rivisto

| Sub-task | Effort |
|----------|--------|
| `EditableDateCell` in DataTable types + rendering | 10 min |
| `CellDateRange.svelte` (solo Alt. β) | 20 min |
| `ScheduledInvestmentEditor.svelte` (DataTable + serialize/deserialize) | 45 min |
| Late interest row + toggle + grace_period | 15 min |
| `ui_component` backend (schema + base class + override + endpoint) | 10 min |
| Tooltip con link docs | 10 min |
| `compounding.md` docs (4 lingue) | 20 min |
| Validazione client-side (contiguità, overlap, required) | 15 min |
| i18n chiavi + api sync | 5 min |
| **Totale F9** | **~2.5 ore** |

---

## Ordine di esecuzione

| # | Fix | Tipo | Effort |
|---|-----|------|--------|
| 1 | **F2** — "Other" in fondo | Bug fix | 2 min |
| 2 | **F3** — Paginazione ∞ | Bug fix | 1 min |
| 3 | **F4** — Valuta tooltip history | Bug fix | 5 min |
| 4 | **F6** — Rimuovere Remove esterno | Cleanup | 10 min |
| 5 | **F1** — SimpleSelect dropdown fixed | Bug fix | 20 min |
| 6 | **F8** — `accepted_identifier_types` (BE+FE) | Feature | 25 min |
| 7 | **F7** — Fetch Interval HH:MM | Feature | 15 min |
| 8 | **F5** — Layout B Two-Panel + wrap | Feature | 35 min |
| 9 | **F9** — ScheduledInvestmentEditor (dettaglio §9) | Feature | **150 min** |

**Tempo totale stimato**: ~4.5 ore

**Razionale**: F2-F4 micro-fix indipendenti → F6 cleanup → F1 prerequisito dropdown →
F8 identifier filtering (serve prima del layout) → F7 fetch interval UI →
F5 layout B completo → F9 componente complesso per ultimo.

**⚠️ Scelta tabella F9**: Alternativa α (due colonne date) o β (colonna Period con DateRangePicker)?
Vedi §9.4 per ASCII art comparative.

---

## Validation Checklist

- [ ] `npx svelte-check --threshold error` → 0 errors
- [ ] `npm run build` senza errori
- [ ] `./dev.py api sync` completato
- [ ] `./dev.py test schemas all` passano
- [ ] Manuale: Distribution "Other" sempre in fondo alla lista
- [ ] Manuale: Paginazione distribution ha opzione ∞
- [ ] Manuale: Tooltip history mostra valuta accanto ai prezzi
- [ ] Manuale: SimpleSelect dropdown non troncato dentro panel collapsibile
- [ ] Manuale: BrokerForm — no bottone "Remove" esterno
- [ ] Manuale: ProfileTab — no bottone "Remove" esterno
- [ ] Manuale: `GET /assets/provider` → `accepted_identifier_types` + `ui_component` per ogni provider
- [ ] Manuale: justetf → ID Type auto-set ISIN (unico accettato)
- [ ] Manuale: yfinance → dropdown mostra solo TICKER e ISIN
- [ ] Manuale: Fetch Interval mostra HH MM (24h 00m → 1440, 1h 00m → 60)
- [ ] Manuale: Layout two-panel su desktop, stack su mobile / left largo
- [ ] Manuale: cssscraper → params sub-panel + right panel a lato o sotto
- [ ] Manuale: ScheduledInvestmentEditor → DataTable con periodi editabili
- [ ] Manuale: SI → Add/Remove period, ordinamento solo cronologico
- [ ] Manuale: SI → Late Interest nella stessa tabella come riga speciale + toggle
- [ ] Manuale: SI → Contiguità date (warning), overlap (error), rate ≥ 0
- [ ] Manuale: SI → compound_frequency condizionale (solo se COMPOUND)
- [ ] Manuale: SI → Tooltips ℹ️ su header con link a docs financial-theory
- [ ] Manuale: SI → Serializzazione JSON ↔ form bidirezionale corretta
- [ ] Manuale: Pagina `compounding.md` presente in docs (4 lingue)
- [ ] Code review: nessuna regressione Round 5.1

