# Plan: Phase 6 Step 3 — Round 6: Provider Layout Redesign + Polish

Post Round 5.1. Include: redesign ProviderAssignmentSection layout,
5 fix minori dal feedback utente.

---

## 📐 Provider Assignment Section — 3 Proposte Layout

### Layout attuale (per confronto)

```
┌──────────────────────────────────────────────────────────────────┐
│ PROVIDER ASSIGNMENT                                     □ No Prov│
├──────────────────────────────────────────────────────────────────┤
│ Provider              Identifier Type                            │
│ [🔶 JustETF     ▾]   [ISIN            ▾]                        │
│                                                                  │
│ Identifier                                                       │
│ [IE00B0M63177________________________________]                    │
│                                                                  │
│ (params_schema area if present)                                  │
│                                                                  │
│ Fetch Interval (min) *                                           │
│ [1440        ]                                                   │
│ ⓘ How often the auto-sync job refreshes prices. 1440=24h...     │
│                                                                  │
│ User URL                     Provider URL                        │
│ [https://...         ]       [https://justetf.com/... (ro)] ↗   │
│                                                                  │
│ [▶ Test Configuration]                                           │
│                                                                  │
│ ├ ✅ Current Price: 47.45 EUR (0.79s)                            │
│ ├ ✅ History: 8 points — 2026-03-24 → 2026-03-31 (0.01s)       │
│ └ Total: 0.79s                                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Problemi**: 7 righe verticali → troppo lungo. Fetch Interval occupa una riga intera
per un campo usato raramente. Le URL sono lontane dal provider. Il bottone Test è
separato dai risultati da un gap visivo. Non c'è raggruppamento logico.

---

### Proposta A — "Compact Three-Row"

Raggruppa i 3 campi chiave (Provider, ID Type, Identifier) su una riga con griglia
a 3 colonne. Fetch interval affiancato alle URL. Test button inline coi risultati.

```
┌──────────────────────────────────────────────────────────────────┐
│ PROVIDER ASSIGNMENT                                     □ No Prov│
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Provider          ID Type        Identifier                     │
│  [🔶 JustETF ▾]   [ISIN    ▾]   [IE00B0M63177______________]   │
│                                                                  │
│  (params_schema — solo se presenti, indentati con border-left)   │
│                                                                  │
│  User URL                 Provider URL               Fetch ⏱     │
│  [_________________]      [_______________ (ro)] ↗   [1440] min  │
│                                                                  │
│  [▶ Test Configuration]                                          │
│  ├ ✅ Current Price: 47.45 EUR (2026-03-31)     0.79s           │
│  ├ ✅ History: 8 pts — 03-24 → 03-31            0.01s           │
│  └ Total: 0.79s                                                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Pro**: Compatto, 3 righe essenziali + risultati. Fetch Interval non spreca spazio.
**Contro**: Su mobile la riga a 3 colonne potrebbe essere stretta.

**Grid CSS**: `grid-cols-1 sm:grid-cols-[1fr_auto_2fr]` per la riga principale.
URL: `grid-cols-[1fr_1fr_auto]`. Fetch con `w-20` inline.

---

### Proposta B — "Two-Panel Split"

Separa in due zone: sinistra = configurazione provider, destra = test e risultati.
Dà un senso "causa → effetto": configuri a sinistra, vedi il risultato a destra.

```
┌──────────────────────────────────────────────────────────────────┐
│ PROVIDER ASSIGNMENT                                     □ No Prov│
├──────────────────────────┬───────────────────────────────────────┤
│                          │                                       │
│  Provider                │  [▶ Test Configuration]               │
│  [🔶 JustETF       ▾]   │                                       │
│                          │  ├ ✅ Current Price:                  │
│  ID Type                 │  │    47.45 EUR (2026-03-31) 0.79s   │
│  [ISIN              ▾]   │  ├ ✅ History:                       │
│                          │  │    8 pts — 03-24→03-31    0.01s   │
│  Identifier              │  └ Total: 0.79s                      │
│  [IE00B0M63177_____]     │                                       │
│                          │  ─────────────────────────────        │
│  Fetch Interval (min)    │  Provider URL                         │
│  [1440  ]                │  [https://justetf.com/...  ] ↗       │
│                          │                                       │
│  (params_schema)         │  User URL                             │
│                          │  [________________________]           │
│                          │                                       │
├──────────────────────────┴───────────────────────────────────────┤
```

**Pro**: Chiara separazione logica. Risultati test immediatamente visibili accanto
alla config. Good for desktop.
**Contro**: Su mobile serve un fallback a stack verticale. Più complesso da implementare.

**Grid CSS**: `grid-cols-1 md:grid-cols-2 gap-4` con border divisore.

---

### Proposta C — "Single Row Header + Collapsible Details"

La "riga magica" (Provider + Identifier) è sempre visibile e compatta.
Tutto il resto (ID Type, Fetch, URLs, params) è in una sezione "Advanced" collapsible.
I risultati del test sono sotto la riga principale.

```
┌──────────────────────────────────────────────────────────────────┐
│ PROVIDER ASSIGNMENT                                     □ No Prov│
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [🔶 JustETF ▾]  [ISIN ▾]  [IE00B0M63177_________]   [▶ Test] │
│                                                                  │
│  ├ ✅ Price: 47.45 EUR (03-31) 0.79s                            │
│  ├ ✅ History: 8 pts (03-24→03-31) 0.01s                        │
│  └ Total: 0.79s                                                  │
│                                                                  │
│  ▸ Advanced Settings ─────────────────────────────────────       │
│  │ Fetch Interval: [1440] min  ⓘ hint                           │
│  │ User URL:    [_________________________]                      │
│  │ Provider URL: [https://justetf.com/... (ro)] ↗               │
│  │ (params_schema fields if any)                                 │
│  └───────────────────────────────────────────────────────        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Pro**: Ultra-compatto per il caso comune (la maggior parte degli utenti non tocca
Fetch Interval né le URL). La "riga magica" è autocontenuta: configura e testa in 1 riga.
**Contro**: Le Advanced Settings sono nascoste → meno discoverability. Il bottone Test
inline potrebbe essere stretto su mobile.

**Grid CSS**: Riga principale = `flex` con gap, collapsible = `<details>/<summary>`
nativo o toggle custom.

---

## 🐛 Fix minori dal feedback

### F1 — SimpleSelect dropdown troncato dentro panel collapsible

**Problema**: Il dropdown del SimpleSelect (es. identifier type select nella DataTable
degli identifiers) è `position: absolute` ma il parent container della modale ha
`overflow-y: auto`. Quando c'è poco spazio (es. 1 solo identifier) il dropdown
viene clippato.

**Causa**: Il `div.relative` del SimpleSelect è dentro un `div.max-h-[70vh].overflow-y-auto`
(il body della modale). Il dropdown con `z-50` non esce dal parent con overflow.

**Soluzione**: Nella `ModalBase` il body già ha `allowOverflow={true}` (prop della modale).
Ma `allowOverflow` agisce sul posizionamento del ModalBase, non sul scroll interno.
Il fix corretto è rendere il dropdown un **portal** (`document.body` append) oppure
assicurarsi che il container scorribile non clippe i figli con z-index alto.

Approccio suggerito — opzione meno invasiva:
1. Nel `SimpleSelect`, se `dropdownPosition="auto"` e la computed position
   risulterebbe clippata, usare `position: fixed` + coordinate calcolate
   da `getBoundingClientRect()` al posto di `position: absolute`.
   Questo fa uscire il dropdown da qualsiasi parent con overflow.
2. Aggiornare le coordinate su scroll del parent (listener).

**File coinvolti**:
- `frontend/src/lib/components/ui/select/SimpleSelect.svelte` — fixed positioning per dropdown

---

### F2 — "Other" in fondo alle distribuzioni di default

**Problema**: Nella DistributionEditor, quando i dati vengono dal provider con "Other"
come chiave geografica, "Other" finisce ordinato per peso come tutti gli altri.
L'utente si aspetta che "Other" sia sempre l'ultima voce.

**Soluzione**: Nel sort iniziale (`$effect` riga 88-100 di `DistributionEditor.svelte`),
aggiungere una regola secondaria: `key === 'Other'` → sort to bottom.

```typescript
entries = Object.entries(value)
    .map(([key, w]) => ({id: crypto.randomUUID(), key, weight: Number(w) * 100}))
    .sort((a, b) => {
        // "Other" always last
        if (a.key === 'Other' && b.key !== 'Other') return 1;
        if (b.key === 'Other' && a.key !== 'Other') return -1;
        // Then by weight descending
        return b.weight - a.weight;
    });
```

**File coinvolti**:
- `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

---

### F3 — Paginazione: aggiungere opzione "∞" (All) nelle distribuzioni

**Problema**: La DistributionEditor usa `pageSizeOptions={[5, 10, 25]}` senza l'opzione
∞ (show all). Il DataTable supporta già `0` come "mostra tutto" (mappato a `∞`
nell'UI di `DataTablePagination`).

**Soluzione**: Cambiare `pageSizeOptions={[5, 10, 25, 0]}`.

**File coinvolti**:
- `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

---

### F4 — Tooltip history sample_prices: mostrare valuta

**Problema**: Il tooltip della history mostra i sample prices senza valuta.
Il current price invece mostra `47.45 EUR`. Manca la coerenza.

**Soluzione**: Il backend in `_probe_history` conosce la valuta (è nel config o nella
risposta history). Passarla nel `sample_prices` come campo extra, oppure
propagare la `currency` dal current_price al frontend.

Approccio più semplice (frontend-only):
Il `testConfiguration()` in ProviderAssignmentSection già ha `cp.currency`
dal risultato current_price. Basta salvare `priceCurrency` anche nel
TestResult della history (copiandolo dal current_price result se presente).

```typescript
// Dopo aver processato current_price e history:
const cpCurrency = items.find(r => r.priceCurrency)?.priceCurrency ?? '';
for (const item of items) {
    if (item.samplePrices && !item.priceCurrency) {
        item.priceCurrency = cpCurrency;
    }
}
```

Poi nel tooltip, usare `result.priceCurrency`:
```typescript
html += `<tr><th>📅 Date</th><th>💰 Close (${result.priceCurrency})</th></tr>`;
```

**File coinvolti**:
- `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte`

---

### F5 — Layout scelto: implementazione (DIPENDE DALLA SCELTA UTENTE)

Dopo che l'utente sceglie una delle 3 proposte (A, B, C), implementare
il nuovo layout nel template HTML di `ProviderAssignmentSection.svelte`.

**File coinvolti**:
- `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte`

---

## Ordine di esecuzione consigliato

| # | Fix | Tipo | Effort |
|---|-----|------|--------|
| 1 | **F2** — "Other" in fondo | Bug fix | 2 min |
| 2 | **F3** — Paginazione ∞ | Bug fix | 1 min |
| 3 | **F4** — Valuta nel tooltip history | Bug fix | 5 min |
| 4 | **F1** — SimpleSelect dropdown fixed position | Bug fix | 20 min |
| 5 | **F5** — Layout redesign (da scelta utente) | Feature | 30 min |

**Tempo totale stimato**: ~1 ora

---

## Validation Checklist

- [ ] `npx svelte-check --threshold error` → 0 errors
- [ ] `npm run build` senza errori
- [ ] Manuale: Distribution "Other" sempre in fondo alla lista
- [ ] Manuale: Paginazione distribution ha opzione ∞
- [ ] Manuale: Tooltip history mostra valuta accanto ai prezzi
- [ ] Manuale: SimpleSelect dropdown non troncato dentro panel collapsibile
- [ ] Manuale: Layout provider assignment coerente desktop + mobile
- [ ] Code review: nessuna regressione sui fix Round 5.1

