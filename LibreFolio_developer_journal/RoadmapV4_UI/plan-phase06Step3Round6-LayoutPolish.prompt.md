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

### F9 — ScheduledInvestmentEditor.svelte

**Nuovo componente** per i params JSON di `scheduled_investment`.
Renderizza `FAScheduledInvestmentSchedule` come form strutturato.

#### Props
```typescript
interface Props {
    value?: Record<string, any>;  // bindable, JSON-compatible
    disabled?: boolean;
    readonly?: boolean;
    onchange?: (value: Record<string, any>) => void;
}
```

#### Struttura interna

**a) Schedule (lista periodi)** — DataTable editabile:

| Colonna | Tipo | Input |
|---------|------|-------|
| Start Date | date | `<input type="date">` |
| End Date | date | `<input type="date">` |
| Annual Rate % | number | `<input type="number" step="0.01">` |
| Compounding | enum | SimpleSelect: SIMPLE, COMPOUND |
| Comp. Freq. | enum | SimpleSelect (solo se COMPOUND): DAILY…CONTINUOUS |
| Day Count | enum | SimpleSelect: ACT/365, ACT/360, ACT/ACT, 30/360 |

Azioni riga: ✕ Remove. Azione globale: + Add Period.
Validazione client-side:
- Contiguità date: `period[n].end_date + 1 day == period[n+1].start_date`
- Warning visuale (amber) se gap/overlap, non bloccante
- Rate ≥ 0

**b) Late Interest** — Toggle checkbox on/off:

| Campo | Input |
|-------|-------|
| Annual Rate % | `<input type="number" step="0.01">` |
| Grace Period (days) | `<input type="number" min="0">` |
| Compounding | SimpleSelect: SIMPLE, COMPOUND |
| Comp. Freq. | SimpleSelect (condizionale: solo se COMPOUND) |
| Day Count | SimpleSelect |

**c) Serializzazione**:
- Stato interno → `{schedule: [...], late_interest: {...} | null}`
- `onchange` emette il dict JSON
- `value` in input → deserializzazione nel form strutturato

#### Integrazione in ProviderAssignmentSection

```svelte
{#if providerCode === 'scheduled_investment'}
    <ScheduledInvestmentEditor
        value={paramsValues}
        disabled={disabled || readonly}
        onchange={(v) => { paramsValues = v; providerParams = v; emitChange(); }}
    />
{:else if paramsSchema.length > 0}
    <!-- Generic params loop (existing code) -->
{/if}
```

#### Enums dal backend (già in OpenAPI)

- `CompoundingType`: SIMPLE, COMPOUND
- `CompoundFrequency`: DAILY, MONTHLY, QUARTERLY, SEMIANNUAL, ANNUAL, CONTINUOUS
- `DayCountConvention`: ACT/365, ACT/360, ACT/ACT, 30/360

Disponibili in `generated.ts` dopo `api sync` come Zod schemas.

**File**:
- `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte` (NUOVO)
- `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` (integrazione)

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
| 9 | **F9** — ScheduledInvestmentEditor | Feature | 60 min |

**Tempo totale stimato**: ~3 ore

**Razionale**: F2-F4 micro-fix indipendenti → F6 cleanup → F1 prerequisito dropdown →
F8 identifier filtering (serve prima del layout) → F7 fetch interval UI →
F5 layout B completo → F9 componente complesso per ultimo.

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
- [ ] Manuale: `GET /assets/provider` → `accepted_identifier_types` per ogni provider
- [ ] Manuale: justetf → ID Type auto-set ISIN (unico accettato)
- [ ] Manuale: yfinance → dropdown mostra solo TICKER e ISIN
- [ ] Manuale: Fetch Interval mostra HH MM (24h 00m → 1440, 1h 00m → 60)
- [ ] Manuale: Layout two-panel su desktop, stack su mobile / left largo
- [ ] Manuale: cssscraper → params sub-panel + right panel a lato o sotto
- [ ] Manuale: scheduled_investment → ScheduledInvestmentEditor con DataTable
- [ ] Manuale: SI → Add/Remove period, contiguità dates, rate ≥ 0
- [ ] Manuale: SI → Late Interest toggle, compound_frequency condizionale
- [ ] Code review: nessuna regressione Round 5.1

