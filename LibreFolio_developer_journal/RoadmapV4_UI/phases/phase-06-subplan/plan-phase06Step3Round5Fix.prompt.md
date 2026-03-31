# Plan: Phase 6 Step 3 — Round 5 Fix

Rimozione enum duplicati, fix bug critico DistributionEditor ($effect loop), z-index SimpleSelect, card layout dinamico nel ComparisonModal, Tooltip custom per test, selettore icona con `ImagePickerWrapper`.

---

## Context

### Problemi riportati dall'utente dopo Round 4

1. **Enum duplicati in `assetTypes.ts`**: `ASSET_TYPES` e `IDENTIFIER_TYPES` sono hardcodati manualmente, ma esistono già come enum Zod in `generated.ts` (`schemas.AssetType`, `schemas.IdentifierType`). Codice duplicato da eliminare.

2. **Alias no-space nel backend**: aggiunti in Round 4 come safety net (`"consumerdiscretionary"`, `"realestate"`, ecc. in `sector_fin_utils.py`). L'utente li considera codice sporco e vuole rimuoverli — preferisce il rischio di un fallback a "Other" piuttosto che mantenere alias ridondanti.

3. **Confronto distribuzione settoriale**: funziona correttamente dopo Round 4, i nomi sono localizzati con emoji. ✅

4. **Freccia `→` nel ComparisonModal**: nei campi stringa (ISIN, Type, Currency, Description) la freccia è centrata verticalmente rispetto all'intera area (label + box valore) anziché rispetto ai soli box valore. Deve essere allineata tra i due rettangoli.

5. **Layout ComparisonModal**: i campi stringa sono in righe flat con `border-b`, le distribuzioni sono in card bordate. L'utente vuole **tutti** i campi in card, raggruppati nello stesso ordine della modale principale. Il sistema di raggruppamento deve essere **dinamico** (guidato da un array di configurazione) e non hardcoded nel template.

6. **Z-index SimpleSelect nel DataTable**: i dropdown dei SimpleSelect nelle celle della tabella finiscono **sotto** i SimpleSelect delle righe successive. Effetto comico ma da correggere.

7. **Bug editing pesi nel DistributionEditor** (critico):
   - Modificando il peso di una entry, i valori delle **altre** entries cambiano
   - Il totale percentuale fluttua del ±100% durante l'editing
   - Impossibile lavorare le opzioni — l'editor è inutilizzabile
   - **Root cause**: l'`$effect` alla riga 81 rigenera `entries` con nuovi `crypto.randomUUID()` a ogni cambio di `value`, ma `emitChange()` setta `value`, retriggherando il ciclo (loop infinito $effect → emitChange → $effect)
   - Non è chiaro se `.` e `,` sono accettati come separatore decimale
   - Mancano bottoni `+`/`-` stepper per incrementare/decrementare
   - Serve un'azione per bilanciare eccesso/deficit su una riga

8. **Tooltip nativo invece di custom**: i test results usano `title=` nativo (tooltip OS), ma dovrebbe usare `Tooltip.svelte` custom. Inoltre i 6 punti prezzo dello storico non vengono mostrati — solo il date range.

9. **Manca il selettore icona asset**: la modale non ha alcun componente UI per scegliere/caricare l'icona dell'asset. Era nel mockup originale (blocco 64×64 cliccabile a sinistra dei campi). Usare `ImagePickerWrapper` con preset `asset-icon` (già definito in `imageCrop.ts`, 256×256).

### File coinvolti

| File | Ruolo |
|------|-------|
| `frontend/src/lib/utils/assetTypes.ts` | Costanti centralizzate asset — rimuovere duplicati |
| `frontend/src/lib/api/generated.ts` | Schema Zod generati — fonte di verità per enum |
| `frontend/src/lib/types/common.ts` | Tipi derivati (`AssetType`, `IdentifierType`) |
| `backend/app/utils/sector_fin_utils.py` | Enum settori — rimuovere alias no-space |
| `backend/test_scripts/test_utilities/test_sector_normalization.py` | Test settori — rimuovere test alias no-space |
| `frontend/src/lib/components/ui/input/DistributionEditor.svelte` | Editor distribuzione — fix $effect loop |
| `frontend/src/lib/components/table/DataTable.svelte` | DataTable — fix z-index, editable-number |
| `frontend/src/lib/components/assets/ProviderComparisonModal.svelte` | Modal confronto — card layout dinamico + freccia |
| `frontend/src/lib/components/assets/AssetModal.svelte` | Modal asset — aggiungere icon picker + DiffItem group |
| `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` | Provider section — Tooltip custom |
| `frontend/src/lib/components/ui/Tooltip.svelte` | Tooltip custom (html prop) |
| `frontend/src/lib/components/assets/AssetIcon.svelte` | Componente icona asset |
| `frontend/src/lib/components/ui/media/ImagePickerWrapper.svelte` | Picker immagine (URL/Upload/Crop) |
| `frontend/src/lib/utils/imageCrop.ts` | Preset `asset-icon` (256×256, già esistente) |
| `backend/app/schemas/provider.py` | ProbeHistoryResult — aggiungere sample_prices |
| `backend/app/services/asset_source.py` | probe_provider_config — popolare sample_prices |

---

## ASCII Art — Design Finali

### AssetModal — Sezione "Asset Details"

```
┌──────────────────────────────────────────────────────────────────┐
│  ─── ASSET DETAILS ──────────────────────── [🔄 Ask Provider]   │
│                                                                  │
│  ┌──────────┐   Name *       [Apple Inc.                     ]  │
│  │          │                                                    │
│  │   ICON   │   Type *       [📈 Stock                    ▾]   │
│  │  64×64   │                                                    │
│  │ (click   │   Currency *   [🇺🇸 USD                      ▾]   │
│  │ to edit) │                                                    │
│  └──────────┘   Description                                      │
│                 [Apple Inc. — American multinational         ]   │
│                 [technology company headquartered in...      ]   │
│                                                                  │
│  ▸ More Info (Identifiers + Classification)                      │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ IDENTIFIERS                       [+Add] [🔄 Ask Provider] ││
│  │ ┌──────────────┬──────────────────────┬──────┐              ││
│  │ │ Type ▾       │ Value                │  ✕   │              ││
│  │ ├──────────────┼──────────────────────┼──────┤              ││
│  │ │ ISIN         │ US0378331005         │  ✕   │              ││
│  │ │ TICKER       │ AAPL                 │  ✕   │              ││
│  │ └──────────────┴──────────────────────┴──────┘              ││
│  │                                                              ││
│  │ SECTOR DISTRIBUTION               [+Add] [🔄 Ask Provider] ││
│  │ ┌──────────────────────┬─────────────┬────────┬──────┬─────┐││
│  │ │ Sector ▾             │ ▓▓▓▓▓▓░░░░  │ Wt %   │  ⚖  │  ✕  │││
│  │ ├──────────────────────┼─────────────┼────────┼──────┼─────┤││
│  │ │ 💻 Technology        │ ▓▓▓▓▓▓▓░░░  │ 60.00  │  ⚖  │  ✕  │││
│  │ │ 🏦 Financials        │ ▓▓▓▓░░░░░░  │ 40.00  │  ⚖  │  ✕  │││
│  │ └──────────────────────┴─────────────┴────────┴──────┴─────┘││
│  │                                   Total: 100.00% ✅          ││
│  │                                                              ││
│  │ GEOGRAPHIC DISTRIBUTION            [+Add] [🔄 Ask Provider] ││
│  │ ┌──────────────────────┬─────────────┬────────┬──────┬─────┐││
│  │ │ Country ▾            │ ▓▓▓▓▓▓░░░░  │ Wt %   │  ⚖  │  ✕  │││
│  │ ├──────────────────────┼─────────────┼────────┼──────┼─────┤││
│  │ │ 🇺🇸 USA               │ ▓▓▓▓▓▓▓▓░░  │ 80.00  │  ⚖  │  ✕  │││
│  │ │ 🇩🇪 DEU               │ ▓▓░░░░░░░░  │ 20.00  │  ⚖  │  ✕  │││
│  │ └──────────────────────┴─────────────┴────────┴──────┴─────┘││
│  │                                   Total: 100.00% ✅          ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ─── PROVIDER ───────────────────────────────────────────────    │
│  (ProviderAssignmentSection — invariato)                         │
│                                                                  │
│  ─────────────────────────────────────── [Cancel] [💾 Save]     │
└──────────────────────────────────────────────────────────────────┘
```

### DistributionEditor — Dettaglio cella peso con azione Bilancia

```
┌──────────────────────┬─────────────┬────────┬──────┬──────┐
│ 💻 Technology    ▾   │ ▓▓▓▓▓▓▓░░░  │ 60.00  │  ⚖  │  ✕   │
│ 🏦 Financials    ▾   │ ▓▓▓░░░░░░░  │ 25.00  │  ⚖  │  ✕   │
│ 🏥 Health Care   ▾   │ ▓░░░░░░░░░  │  5.00  │  ⚖  │  ✕   │
└──────────────────────┴─────────────┴────────┴──────┴──────┘
                                 Total: 90.00% ⚠ (10.00% missing)

   ⚖ = "Bilancia" — click su una riga assegna a quella riga
       tutto il deficit/eccesso (in questo caso +10% → 15.00%)
```

### ProviderComparisonModal — Layout dinamico a card raggruppate per sezione

```
┌──────────────────────────────────────────────────────────────┐
│  Confronto Dati Provider                              [✕]   │
│─────────────────────────────────────────────────────────────│
│  Il provider ha restituito valori diversi...                 │
│                                                              │
│  ─── IDENTIFIERS ───  (sezione da DIFF_FIELD_SECTIONS[0])   │
│                                                              │
│  ┌─ ☑ ISIN ──────────────────────────────────────────────┐  │
│  │  ┌──────────────────┐       ┌──────────────────────┐  │  │
│  │  │ VALORE ATTUALE   │       │ VALORE PROVIDER      │  │  │
│  │  │ IE00B0sadM63177  │   →   │ IE00B0M63177         │  │  │
│  │  └──────────────────┘       └──────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ─── ASSET DETAILS ───  (sezione da DIFF_FIELD_SECTIONS[1]) │
│                                                              │
│  ┌─ ☑ Type ──────────────────────────────────────────────┐  │
│  │  ┌──────────────────┐       ┌──────────────────────┐  │  │
│  │  │ BOND             │   →   │ ETF                  │  │  │
│  │  └──────────────────┘       └──────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ ☑ Currency ──────────────────────────────────────────┐  │
│  │  ┌──────────────────┐       ┌──────────────────────┐  │  │
│  │  │ ALL              │   →   │ USD                  │  │  │
│  │  └──────────────────┘       └──────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ─── CLASSIFICATION ───  (sezione da DIFF_FIELD_SECTIONS[2])│
│                                                              │
│  ┌─ ☑ Description ───────────────────────────────────────┐  │
│  │  ┌──────────────────┐       ┌──────────────────────┐  │  │
│  │  │ asd              │   →   │ The iShares MSCI...  │  │  │
│  │  └──────────────────┘       └──────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ ☑ Distribuzione Settoriale ──────────────────────────┐  │
│  │  ┌──────────────────┐       ┌──────────────────────┐  │  │
│  │  │ 💻 Tecnologia    │       │ 💻 Tecnologia        │  │  │
│  │  │   33.34%         │       │   33.34%             │  │  │
│  │  │ 🏥 Sanità        │       │ 🏦 Finanziari        │  │  │
│  │  │   32.00%         │   →   │   19.44%             │  │  │
│  │  │ 💡 Servizi pubb. │       │ 🛍️ Beni voluttuari   │  │  │
│  │  │   31.00%         │       │    9.53%             │  │  │
│  │  │ ...              │       │ ...                  │  │  │
│  │  └──────────────────┘       └──────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ ☑ Distribuzione Geografica ──────────────────────────┐  │
│  │  ┌──────────────────┐       ┌──────────────────────┐  │  │
│  │  │ AFG 100.00%      │   →   │ TWN 25.36%           │  │  │
│  │  │                  │       │ CHN 24.81%           │  │  │
│  │  │                  │       │ KOR 21.08%           │  │  │
│  │  └──────────────────┘       └──────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  [Seleziona Tutto] [Deseleziona Tutto]                       │
│─────────────────────────────────────────────────────────────│
│                           [Annulla]  [✅ Applica (6/6)]      │
└──────────────────────────────────────────────────────────────┘
```

### ProviderAssignmentSection — Test Results con Tooltip custom

```
  ─── PROVIDER ───
  Provider   [yfinance                 ▾]   ID Type  [ISIN ▾]
  Identifier [IE00B0M63177                                   ]
  User URL   [https://...              ]   Provider URL [...]

  [▶ Test Configuration]

  │ ✅ Current Price: 42.87 USD (2026-03-29)  (0.45s)
  │                   ┌─────────────────────────┐
  │                   │  💰 42.87 USD            │ ← Tooltip.svelte
  │                   │  📅 as of 2026-03-29     │    (on hover)
  │                   └─────────────────────────┘
  │
  │ ✅ History: 6 points — 2026-03-23 → 2026-03-29  (1.23s)
  │             ┌───────────────────────────────┐
  │             │  📅 Date       │  💰 Close    │ ← Tooltip.svelte
  │             │  2026-03-23    │   41.50      │    (html table)
  │             │  2026-03-24    │   41.80      │
  │             │  2026-03-25    │   42.10      │
  │             │  2026-03-26    │   42.30      │
  │             │  2026-03-27    │   42.65      │
  │             │  2026-03-29    │   42.87      │
  │             └───────────────────────────────┘
  │
  Total: 1.68s
```

---

## Steps

### Step 1 — Eliminare enum duplicati da `assetTypes.ts`, derivarli da `generated.ts`

**File**: `frontend/src/lib/utils/assetTypes.ts`

Rimuovere le costanti `ASSET_TYPES` e `IDENTIFIER_TYPES` hardcodate e derivarle dagli schema Zod già generati:

```typescript
import {schemas} from '$lib/api/generated';

export const ASSET_TYPES = schemas.AssetType.options;
export const IDENTIFIER_TYPES = schemas.IdentifierType.options;
```

Rimuovere i tipi `AssetTypeCode` e `IdentifierTypeCode` — usare i tipi già derivati in `common.ts` (`AssetType`, `IdentifierType`).

Il `PNG_MAP`, `getAssetTypeIconUrl`, `buildAssetTypeOptions`, `SECTOR_KEYS`, `sectorI18nKey` restano — i settori non hanno un enum nel generated perché la distribuzione è un `Record<string, number>` libero.

Aggiornare tutti i file che importano `ASSET_TYPES`/`IDENTIFIER_TYPES` da `assetTypes` — dovrebbero continuare a funzionare poiché il valore runtime è identico.

### Step 2 — Rimuovere alias no-space dal backend

**File**: `backend/app/utils/sector_fin_utils.py`

Rimuovere dal mapping di `from_string()` le 4 righe di alias senza spazi aggiunte in Round 4:
- `"consumerdiscretionary"` → rimuovere
- `"realestate"` → rimuovere
- `"basicmaterials"` → rimuovere
- `"consumerstaples"` → rimuovere

Nota: `"healthcare"` è un alias pre-esistente (non no-space, è un'abbreviazione storica) — **non** rimuoverlo.

**File**: `backend/test_scripts/test_utilities/test_sector_normalization.py`

Rimuovere i test parametrizzati per i no-space alias aggiunti in Round 4:
- `("ConsumerDiscretionary", FinancialSector.CONSUMER_DISCRETIONARY)` → rimuovere
- `("RealEstate", FinancialSector.REAL_ESTATE)` → rimuovere
- `("BasicMaterials", FinancialSector.BASIC_MATERIALS)` → rimuovere
- `("ConsumerStaples", FinancialSector.CONSUMER_STAPLES)` → rimuovere
- `("HealthCare", FinancialSector.HEALTH_CARE)` → **non** rimuovere (è un alias legittimo)

Eseguire `pytest backend/test_scripts/test_utilities/test_sector_normalization.py -v` per confermare.

### Step 3 — Fix loop `$effect` nel DistributionEditor (bug critico)

**File**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

**Root cause**: l'`$effect` alla riga 81 osserva `value` e rigenera `entries` con nuovi UUID. Ma `emitChange()` setta `value = result`, retriggherando l'effect (loop). Ogni iterazione crea nuovi UUID → reset focus → valori impazziti.

**Fix** — strategia "skip internal updates":

```typescript
let skipNextSync = false;

// Sync from prop value → internal entries (only external changes)
$effect(() => {
    if (skipNextSync) {
        skipNextSync = false;
        return;
    }
    if (value) {
        entries = Object.entries(value)
            .map(([key, w]) => ({id: crypto.randomUUID(), key, weight: Number(w) * 100}))
            .sort((a, b) => b.weight - a.weight);
    } else {
        entries = [];
    }
});

function emitChange() {
    const result: Record<string, number> = {};
    for (const e of entries) {
        result[e.key] = Number((e.weight / 100).toFixed(4));
    }
    skipNextSync = true;  // ← prevent $effect re-trigger
    value = result;
    onchange?.(result);
}
```

**Inoltre** — fix editing pesi nel DataTable:

**File**: `frontend/src/lib/components/table/DataTable.svelte`

Per `editable-number`: cambiare da `oninput` a `onchange`+`onblur` per evitare aggiornamenti intermedi durante la digitazione. Gestire `,` → `.` per internazionalizzazione:

```svelte
<input
    type="number"
    class="cell-editable-number"
    value={cellContent.value ?? ''}
    step={cellContent.step ?? 1}
    min={cellContent.min}
    max={cellContent.max}
    placeholder={cellContent.placeholder ?? ''}
    onblur={(e) => {
        let raw = e.currentTarget.value.replace(',', '.');
        if (raw === '') { cellContent.onchange(null); return; }
        let num = Number(raw);
        if (isNaN(num)) return;
        if (cellContent.min !== undefined && num < cellContent.min) num = cellContent.min;
        if (cellContent.max !== undefined && num > cellContent.max) num = cellContent.max;
        e.currentTarget.value = String(num);
        cellContent.onchange(num);
    }}
    onkeydown={(e) => {
        if (e.key === 'Enter') e.currentTarget.blur();
    }}
    onclick={(e) => e.stopPropagation()}
/>
```

**Inoltre** — aggiungere row action "Bilancia" nel DistributionEditor:

In `rowActions`, aggiungere un'azione che calcola `100 - totalPercent + entry.weight` e assegna il risultato alla entry corrente, bilanciando l'eccesso/deficit. Icona: `Scale` da lucide-svelte. Label: "Balance to 100%". Visibile solo quando `!isValid`.

### Step 4 — Sistema dinamico di raggruppamento + card layout nel ProviderComparisonModal

**4a) Definire la configurazione delle sezioni — `DIFF_FIELD_SECTIONS`**

Creare in `ProviderComparisonModal.svelte` un array di configurazione che definisce le sezioni e i campi in ordine, rispecchiando la struttura dell'AssetModal:

```typescript
/**
 * Configuration for field grouping in the comparison modal.
 * Order matches the AssetModal layout. Each section has an i18n title key
 * and a list of field prefixes/names. Fields not matching any section
 * go into an "Other" fallback group.
 */
const DIFF_FIELD_SECTIONS: Array<{
    titleKey: string;           // i18n key for section header
    fields: string[];           // field names or prefixes (prefix match for identifier_*)
    matchPrefix?: boolean;      // if true, fields are treated as prefixes
}> = [
    {
        titleKey: 'assets.modal.identifiers',
        fields: ['identifier_'],
        matchPrefix: true,
    },
    {
        titleKey: 'assets.modal.assetDetails',
        fields: ['display_name', 'asset_type', 'currency'],
    },
    {
        titleKey: 'assets.modal.classification',
        fields: ['short_description', 'sector_area', 'geographic_area'],
    },
];
```

Aggiungere una nuova chiave i18n `assets.modal.classification` in tutte e 4 le lingue (en/it/fr/es) — "Classification" / "Classificazione" / "Classification" / "Clasificación".

**4b) Logica di raggruppamento derivata**

```typescript
/** Group items by section, preserving config order */
let groupedItems = $derived.by(() => {
    const groups: Array<{title: string; items: Array<{item: DiffItem; index: number}>}> = [];
    const used = new Set<number>();

    for (const section of DIFF_FIELD_SECTIONS) {
        const sectionItems: Array<{item: DiffItem; index: number}> = [];
        items.forEach((item, idx) => {
            const match = section.matchPrefix
                ? section.fields.some(p => item.field.startsWith(p))
                : section.fields.includes(item.field);
            if (match && !used.has(idx)) {
                sectionItems.push({item, index: idx});
                used.add(idx);
            }
        });
        if (sectionItems.length > 0) {
            groups.push({title: $t(section.titleKey), items: sectionItems});
        }
    }

    // Fallback: any unmatched fields go into "Other"
    const remaining = items
        .map((item, idx) => ({item, index: idx}))
        .filter(({item}, idx) => !used.has(idx));
    if (remaining.length > 0) {
        groups.push({title: 'Other', items: remaining});
    }

    return groups;
});
```

**4c) Template unificato — card per tutti i tipi, iterazione per gruppo**

Il template è un unico `{#each}` annidato che:
1. Itera sui gruppi → stampa header di sezione
2. Itera sugli items del gruppo → stampa una card bordata identica per string e distribution
3. Dentro ogni card: checkbox+label in alto, poi griglia `[1fr_auto_1fr]` con box Current, freccia `→`, box Provider
4. La freccia è nella stessa riga dei box (sotto la label), quindi si centra perfettamente

```svelte
{#each groupedItems as group}
    <!-- Section header -->
    <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider pt-2">
        {group.title}
    </div>

    {#each group.items as {item, index}}
        <div class="border border-gray-200 dark:border-slate-700 rounded-lg p-3">
            <!-- Checkbox + label -->
            <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={item.selected}
                       onchange={() => toggleItem(index)} ... />
                <span class="text-sm font-medium ...">{item.label}</span>
            </label>

            <!-- Values grid -->
            <div class="grid grid-cols-[1fr_auto_1fr] gap-2 mt-2 items-center">
                <!-- Current box -->
                <div class="bg-gray-50 dark:bg-slate-800 rounded p-2">
                    <span class="text-[10px] uppercase text-gray-400 block mb-0.5">
                        {$t('assets.comparison.currentValue')}
                    </span>
                    {#if item.type === 'distribution'}
                        <div class="text-xs space-y-0.5">
                            {#each formatDistribution(item.currentValue?.distribution ?? item.currentValue) as entry}
                                <div class="flex justify-between">
                                    <span>{formatDistKey(entry.key, item.field)}</span>
                                    <span class="font-mono">{entry.pct}</span>
                                </div>
                            {:else}
                                <span class="text-gray-400 italic">—</span>
                            {/each}
                        </div>
                    {:else}
                        <div class="text-xs font-mono">{truncate(item.currentValue)}</div>
                    {/if}
                </div>

                <!-- Arrow (perfectly centered between boxes) -->
                <div class="text-gray-400 text-lg font-light">→</div>

                <!-- Provider box -->
                <div class="bg-green-50 dark:bg-green-900/20 rounded p-2">
                    <span class="text-[10px] uppercase text-gray-400 block mb-0.5">
                        {$t('assets.comparison.providerValue')}
                    </span>
                    {#if item.type === 'distribution'}
                        <div class="text-xs space-y-0.5">
                            {#each formatDistribution(item.providerValue?.distribution ?? item.providerValue) as entry}
                                <div class="flex justify-between">
                                    <span>{formatDistKey(entry.key, item.field)}</span>
                                    <span class="font-mono text-libre-green">{entry.pct}</span>
                                </div>
                            {:else}
                                <span class="text-gray-400 italic">—</span>
                            {/each}
                        </div>
                    {:else}
                        <div class="text-xs font-mono text-libre-green">{truncate(item.providerValue)}</div>
                    {/if}
                </div>
            </div>
        </div>
    {/each}
{/each}
```

Con questo approccio:
- **Nessun campo è hardcoded nel template** — l'ordine e il raggruppamento sono guidati da `DIFF_FIELD_SECTIONS`
- **Aggiungere un nuovo campo** richiede solo aggiungerlo all'array di config (e alla logica `compareField` in AssetModal)
- **La freccia è centrata tra i box** perché è nella stessa sub-grid, sotto la label
- **Tutti i campi hanno lo stesso aspetto card** — nessuna distinzione visiva tra string e distribution

### Step 5 — Fix z-index SimpleSelect nel DataTable

**File**: `frontend/src/lib/components/table/DataTable.svelte`

Il problema: il dropdown di un SimpleSelect in una cella td compare sotto le righe successive della tabella, perché `tr` non ha `position: relative` e lo stacking context è determinato dall'ordine DOM.

**Fix CSS**:

```css
/* Ensure table rows with open SimpleSelect dropdown are on top */
tbody tr:has(.cell-editable-select-wrapper) {
    position: relative;
    z-index: 1;
}

/* When dropdown is actually open (focus-within), bump z-index above sibling rows */
tbody tr:focus-within {
    z-index: 10;
}
```

Verificare che `td:has(.cell-editable-select-wrapper) { overflow: visible; }` (aggiunto in Round 4) sia ancora presente.

### Step 6 — Tooltip custom per test results + sample prices nel probe

**6a) Backend**: aggiungere campo a ProbeHistoryResult

**File**: `backend/app/schemas/provider.py`

```python
class ProbeHistoryResult(BaseProbeOperationResult):
    """Result of history probe operation."""
    points_count: Optional[int] = Field(None, description="Number of price points found")
    date_range: Optional[str] = Field(None, description="Date range of found data (start → end)")
    sample_prices: Optional[list[dict]] = Field(None, description="Sample price points [{date, close}]")
```

**File**: `backend/app/services/asset_source.py` — in `_probe_history()`

```python
sample = None
if points:
    sample = [{"date": str(p.date), "close": float(p.close)} for p in points[:7]]
return ProbeHistoryResult(
    success=True, points_count=len(points), date_range=date_range_str,
    sample_prices=sample,
    execution_time_ms=...
)
```

Rigenerare il client zodios dopo la modifica dello schema.

**6b) Frontend**: sostituire tooltip nativi con `Tooltip.svelte`

**File**: `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte`

Importare `Tooltip` e wrappare ogni test result item:

```svelte
<Tooltip html={buildTooltipHtml(result, response)} position="top">
    <div class="flex items-center gap-2 text-sm">
        ...existing result rendering...
    </div>
</Tooltip>
```

Helper `buildTooltipHtml`:
- Per **Current Price**: `"<strong>123.45 USD</strong><br><small>📅 as of 2026-03-29</small>"`
- Per **History**: tabella HTML con i sample prices:

```html
<table style="font-size:12px; border-collapse:collapse;">
  <tr><th style="text-align:left; padding:2px 8px;">📅 Date</th>
      <th style="text-align:right; padding:2px 8px;">💰 Close</th></tr>
  <tr><td style="padding:2px 8px;">2026-03-23</td>
      <td style="text-align:right; padding:2px 8px;">41.50</td></tr>
  ...
</table>
```

Salvare la response raw del probe in uno state (`lastProbeResponse`) per accedere ai campi `sample_prices`, `as_of_date`, ecc.

### Step 7 — Aggiungere selettore icona asset nella modale

**File**: `frontend/src/lib/components/assets/AssetModal.svelte`

**7a) Stato**: aggiungere `let showImagePicker = $state(false);`

**7b) Handler**:

```typescript
function handleImagePickerChange(url: string) {
    iconUrl = url;
    showImagePicker = false;
}
```

**7c) Layout**: cambiare la sezione "Asset Details" in un grid `grid-cols-[auto_1fr]`:

```svelte
<div class="grid grid-cols-[auto_1fr] gap-4 items-start">
    <!-- Left: Icon (clickable) -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="group relative cursor-pointer"
         onclick={() => showImagePicker = true}
         title={$t('uploads.selectIcon')}>
        <AssetIcon iconUrl={iconUrl} assetType={assetType} size="lg" />
        <div class="absolute inset-0 rounded-full bg-black/40 opacity-0 group-hover:opacity-100
                    flex items-center justify-center transition-opacity">
            <Upload class="text-white" size={16}/>
        </div>
    </div>

    <!-- Right: Name, Type+Currency, Description -->
    <div class="space-y-3">
        <!-- Name field -->
        ...existing name input...
        <!-- Type + Currency grid -->
        ...existing grid sm:grid-cols-2...
        <!-- Description textarea -->
        ...existing textarea...
    </div>
</div>
```

**7d) ImagePickerWrapper** (fuori dal form, nel template root della modale):

```svelte
<ImagePickerWrapper
    open={showImagePicker}
    preset="asset-icon"
    title={$t('uploads.selectIcon')}
    initialUrl={iconUrl ?? ''}
    circularPreview={false}
    filterImages={true}
    onchange={handleImagePickerChange}
    oncancel={() => showImagePicker = false}
/>
```

Nota: `circularPreview={false}` perché le icone asset sono quadrate con bordi arrotondati, non cerchi come gli avatar.

### Step 8 — Selezione righe e azioni bulk con ribilanciamento pesato

Aggiungere selezione multi-riga e azioni bulk (cancellazione con ConfirmModal, ribilanciamento pesato ⚖) tramite `DataTableToolbar.svelte`, posizionata nella barra header accanto ai bottoni + e 🔄 esistenti.

**8a) DistributionEditor** — `enableSelection={!isReadonly && !disabled}`, `DataTableToolbar` nella header bar:
- **Bulk Delete** (Trash2, variant danger): mostra `ConfirmModal` con conteggio, poi rimuove righe selezionate.
- **Bulk Balance ⚖** (Scale): distribuisce il deficit/surplus **proporzionalmente** al peso pre-esistente delle righe selezionate:
  - `totalSelectedWeight = somma dei pesi delle righe selezionate`
  - Per ogni riga selezionata: `nuovoPeso = vecchioPeso + delta × (vecchioPeso / totalSelectedWeight)`
  - Caso limite: se tutte le righe selezionate hanno peso 0, fallback a distribuzione uguale (`delta / N`)
  - Clamp a `[0, 100]` per ogni riga
- **Row action ⚖ (singola riga)**: assegna l'intero deficit/surplus alla riga cliccata. Visibile solo quando `!isValid`.

**8b) Identifiers table in AssetModal** — `enableSelection={true}`, `DataTableToolbar` nella header bar:
- Solo **Bulk Delete** (Trash2, variant danger): mostra `ConfirmModal`, poi rimuove righe selezionate.
- Nessuna azione balance (non applicabile agli identificatori).

**Chiavi i18n** (aggiunte via `./dev.py i18n add`):
- `assets.distribution.balanceRow` — "Balance to 100%"
- `assets.distribution.balanceSelected` — "Balance selected rows"
- `assets.distribution.deleteSelected` — "Delete selected rows"
- `assets.distribution.deleteConfirmMessage` — "Delete {count} entries from this distribution?"
- `assets.identifiers.deleteSelected` — "Delete selected identifiers"
- `assets.identifiers.deleteConfirmMessage` — "Delete {count} identifiers?"

### Step 9 — SECTOR_KEYS da backend API (sectorStore)

`SECTOR_KEYS` era hardcodato in `assetTypes.ts`. Ora:
- **`sectorStore.ts`** (nuovo): carica i settori da `GET /utilities/sectors` (pattern identico a `countryStore`).
- **`assetTypes.ts`**: esporta `getSectorKeysList()` che restituisce i dati dallo store (con fallback statico se non ancora caricato).
- **`DistributionEditor`**: chiama `ensureSectorsLoaded()` in un `$effect` per kind='sector', usa `getSectorKeysList()` al posto di `SECTOR_KEYS`.
- `SECTOR_KEYS` resta come export deprecated per eventuali riferimenti residui.

---

## Round 5.1 — Feedback dal testing manuale (9 fix)

### Fix 1 — Auto-fetch metadata dopo selezione search result
Dopo `applySearchResult()`, oltre al test automatico (`autoTriggerProbe`), si lancia anche `autoFetchMetadata()` che fa un probe silenzioso con `operations: ['metadata']`. Popola solo i campi vuoti (identifiers, description, distribuzioni) senza mostrare la comparison modal. Se il metadata fallisce, non mostra errore (best-effort).

### Fix 2 — Bottone "Remove Image" nell'AssetPickerModal (tab URL)
Nel tab URL di `AssetPickerModal.svelte`:
- Aggiunto bottone ✕ inline per cancellare il campo URL
- Quando l'utente svuota il campo e c'era un `initialUrl`, appare un bottone rosso "Remove Image" che dispatcha `select` con URL vuoto
- `AssetModal.handleImagePickerChange` tratta URL vuoto come `null` (rimozione icona)
- Funziona in tutti gli usi di AssetPickerModal (broker, asset, avatar)

### Fix 3 — Toast per distribuzioni assenti nel provider
In `handleAskProvider()` (globale), se il provider non restituisce `sector_area` o `geographic_area`, si accumula il nome del campo mancante e si mostra un toast info: "Provider has no data for: Sector Distribution, Geographic Distribution".

### Fix 4 — Tolleranza distribuzione corretta
Backend usa `Decimal` con 4 decimali e tolleranza `1e-6`. Frontend `emitChange()` già arrotonda a 4 decimali (`.toFixed(4)`). La tolleranza nel DistributionEditor era `0.05%` → corretta a `0.01%` (consistente con 4 decimali).

### Fix 5 — Ribilanciamento confermato ✅
Già funzionante da Step 3 + Step 8.

### Fix 6 — Paginazione DataTable distribuzione
`enablePagination={true}`, `defaultPageSize={5}`, `pageSizeOptions={[5, 10, 25]}`.

### Fix 7 — Z-index SimpleSelect confermato ✅
Già funzionante da Step 5.

### Fix 8 — "Other" nella distribuzione geografica
- **Frontend**: aggiunta opzione `{value: 'Other', label: '🏳️ Other — Altro'}` in coda alle country options. `formatLabel` gestisce "Other" come caso speciale con flag bianca.
- **Backend**: `normalize_country_keys()` in `geo_utils.py` ora tratta "Other" (case-insensitive) come pass-through, senza tentare la normalizzazione ISO-3166.

### Fix 9 — Tooltip test results: formato tabella HTML per entrambi
- **Current Price**: tabella 1 riga `📅 Date | 💰 Current Price` con valore, valuta e data
- **History**: tabella N righe `📅 Date | 💰 Close` con tutti i sample_prices
- Label da i18n (`$t('common.date')`, `$t('assets.probe.currentPrice')`), non più hardcoded

---

## Validation Checklist

- [x] `npx svelte-check --threshold error` → 0 errors, 0 warnings ✅
- [x] `pytest backend/test_scripts/test_utilities/test_sector_normalization.py -v` → all 45 pass ✅
- [ ] `./dev.py i18n audit` → 730+ keys, 100% coverage, no new missing
- [ ] Rigenerare client zodios se schema backend cambiato (Step 6a)
- [x] Manuale: editing pesi nel DistributionEditor non causa loop/reset (skipNextSync fix)
- [x] Manuale: SimpleSelect dropdown visibile sopra righe successive (z-index fix)
- [x] Manuale: ComparisonModal mostra card uniformi raggruppate per sezione (DIFF_FIELD_SECTIONS)
- [x] Manuale: aggiungere un campo futuro richiede solo modifica a `DIFF_FIELD_SECTIONS`
- [x] Manuale: click su icona asset apre ImagePickerWrapper
- [x] Manuale: Tooltip custom su test results mostra tabella prezzi
- [x] Manuale: selezione righe + bulk delete con ConfirmModal su distribuzioni e identificatori
- [x] Manuale: bulk balance ⚖ distribuisce proporzionalmente al peso pre-esistente
- [x] Manuale: search selection auto-popola tutti i campi (metadata silenzioso)
- [x] Manuale: Remove Image funziona da AssetPickerModal tab URL
- [x] Manuale: toast per distribuzioni assenti quando Ask Provider
- [x] Manuale: tolleranza 100.00% esatta (±0.01%)
- [x] Manuale: paginazione distribuzione con default 5 righe
- [x] Manuale: "Other" ammesso nella distribuzione geografica

