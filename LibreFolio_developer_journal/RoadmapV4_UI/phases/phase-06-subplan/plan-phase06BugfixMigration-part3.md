# Phase 06 Bugfix Migration — Part 3

> Continuazione di [plan-phase06BugfixMigration-part2.md](./plan-phase06BugfixMigration-part2.md)

---

## Panoramica Bug

| # | Bug | File coinvolti | Stato |
|---|-----|----------------|-------|
| **G1** | Bottoni bulk "Sync/Refresh/Delete" hardcoded in inglese | `assets/+page.svelte`, `fx/+page.svelte` | ✅ Fatto |
| **G2** | Layout `tablet-s` mancante su FX page | `fx/+page.svelte` | ✅ Fatto |
| **G3** | 14 errori TS: `EditableNumberCell` manca `min`/`max` | `table/types.ts` | ✅ Fatto |
| **G4** | 3 errori TS: `getUserStorage` return type troppo stretto | `utils/storage.ts` | ✅ Fatto |
| **G5** | 8 errori TS: `icon: Component` troppo restrittivo in `DataTableToolbar` | `DataTableToolbar.svelte` | ✅ Fatto |
| **G6** | Assets filter layout: in non-wide i filtri tornavano in riga (flex-wrap) | `assets/+page.svelte` | ✅ Fatto |
| **G7** | Assets action labels hardcoded ("Sync", "Refresh") + title attr inglesi | `assets/+page.svelte` | ✅ Fatto |
| **G8** | Migrazione i18n `fx.actions.*` → `sharedResource.*` | 4× `i18n/*.json`, `assets/+page.svelte`, `fx/+page.svelte` | ✅ Fatto |

**Totale errori svelte-check: 25** → Tutti riconducibili a **3 cause radice** (G3, G4, G5).
**Post-fix: 0 errori, 0 warning.**

---

## Spiegazione Tecnica degli Errori

### G3 — `EditableNumberCell` manca `min` / `max` (14 errori)

**Causa radice**: In `DataTable.svelte` (righe 1030–1050) il codice usa `cellContent.min` e
`cellContent.max` su celle di tipo `editable-number`, ma l'interfaccia `EditableNumberCell`
in `table/types.ts` (riga 97–107) **non dichiara** queste proprietà.

L'interfaccia attuale:
```typescript
export interface EditableNumberCell {
    type: 'editable-number';
    value: number | null;
    step?: number;
    placeholder?: string;
    onchange: (newValue: number | null) => void;
    // ← mancano min e max!
}
```

**Fix**: Aggiungere `min?: number` e `max?: number` opzionali all'interfaccia.

**File da modificare**: `frontend/src/lib/components/table/types.ts`

**Stima**: 1 minuto

---

### G4 — `getUserStorage` return type troppo stretto (4 errori: Sidebar, +layout, files ×2)

**Causa radice**: La funzione `getUserStorage` ha signature:
```typescript
export function getUserStorage<T extends string>(baseKey: string, defaultValue: T): T
```

Quando viene chiamata con un literal come `getUserStorage('sidebar-collapsed', 'false')`,
TypeScript inferisce `T = 'false'` (literal type), quindi il tipo di ritorno è `'false'`.

Poi il confronto `saved === 'true'` viene segnalato come "unintentional" perché i tipi
letterali `'false'` e `'true'` non si sovrappongono mai.

Stesso pattern in `files/+page.svelte`:
- `getUserStorage(key, 'list')` → tipo `'list'`, poi `=== 'grid'` → errore
- `getUserStorage(key, 'static')` → tipo `'static'`, poi `=== 'brim'` → errore

**Fix**: Cambiare il return type da `T` a `string` (la funzione legge da localStorage, quindi
il valore reale può essere qualsiasi stringa, non solo il tipo del default):

```typescript
export function getUserStorage(baseKey: string, defaultValue: string): string {
```

**File da modificare**: `frontend/src/lib/utils/storage.ts`

**Stima**: 1 minuto

---

### G5 — `icon: Component` troppo restrittivo in `DataTableToolbar` (8 errori: assets ×3, fx ×4)

**Causa radice**: `DataTableToolbar.svelte` definisce una interfaccia locale:
```typescript
import type {Component} from 'svelte';

interface BulkActionInfo {
    icon: Component;  // ← troppo restrittivo
    ...
}
```

Il tipo `Component` (Svelte 5) è `Component<{}, {}, string>`, che richiede una signature
specifica. Le icone di **lucide-svelte** (es. `RotateCw`, `RefreshCw`, `Trash2`) sono
esportate come componenti Svelte 4-style (classi) che non matchano la signature Svelte 5
`Component<{}, {}, string>`.

Il file `table/types.ts` aveva già risolto questo problema usando `type AnyComponent = any;`
con un `eslint-disable` comment.

**Fix**: Usare lo stesso approccio `any` nella `BulkActionInfo` locale di `DataTableToolbar`:

```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any
icon: any;
```

Oppure importare e usare `AnyComponent` da `types.ts` (non è esportato, ma si può esportare).

**File da modificare**: `frontend/src/lib/components/table/DataTableToolbar.svelte`

**Stima**: 1 minuto

---

### G1 — Bottoni bulk hardcoded in inglese

**Problema**: I bulk actions nella toolbar assets e fx usano label stringa hardcoded:
```typescript
{ id: 'sync', label: 'Sync', ... }
{ id: 'refresh', label: 'Refresh', ... }
{ id: 'delete', label: 'Delete', ... }
{ id: 'invert', label: 'Invert', ... }
```

Nota: `BulkActionInfo.label` supporta già `string | (() => string)`, quindi si può usare
una funzione che chiama `$t()` o `$_()`.

**Fix applicata**: Sostituiti tutti con lambda i18n. Chiavi usate:
- `common.sync` → "Sincronizza" (IT)
- `common.refresh` → "Aggiorna" (IT)
- `common.delete` → "Elimina" (IT)
- `common.swapDirection` → "Inverti direzione" (IT) — per il bulk "Invert" in FX

```typescript
// assets/+page.svelte (usa $t = _ as t)
{ id: 'sync', icon: RotateCw, label: () => $t('common.sync'), ... }
{ id: 'refresh', icon: RefreshCw, label: () => $t('common.refresh'), ... }
{ id: 'delete', icon: Trash2, label: () => $t('common.delete'), variant: 'danger', ... }

// fx/+page.svelte (usa $_)
{ id: 'sync', icon: RotateCw, label: () => $_('common.sync'), ... }
{ id: 'refresh', icon: RefreshCw, label: () => $_('common.refresh'), ... }
{ id: 'invert', icon: ArrowLeftRight, label: () => $_('common.swapDirection'), ... }
{ id: 'delete', icon: Trash2, label: () => $_('common.delete'), variant: 'danger', ... }
```

**File modificati**: `assets/+page.svelte`, `fx/+page.svelte`

---

### G2 — Layout `tablet-s` mancante su FX page

**Problema**: La pagina Assets ha 4 modalità responsive: `wide`, `tablet`, `tablet-s`, `mobile`.
La pagina FX ne aveva solo 3: `wide`, `tablet`, `mobile`. Nel range ~500–610px il layout FX
usava `tablet` che è troppo stretto, risultando in filtri/bottoni che non ci stanno.

**Fix applicata**: Allineato al pattern Assets:

1. Aggiunto `'tablet-s'` al tipo di `layoutMode`
2. Aggiunta soglia `else if (w >= 500) layoutMode = 'tablet-s'` nel resize observer
3. Aggiornate le classi CSS condizionali:
   - Container principale: `tablet-s` → `flex-row items-start justify-between`
   - Filters block: `tablet-s` → `flex-col items-start flex-1`
   - Actions block: `tablet-s` → `flex-col` (bottoni in colonna, icon-only)

**Layout proposto**:
```
                         Layout Responsive FX Filter Bar

  ═══════════════════════════════════════════════════════════════════════════
  WIDE (≥1010)  — Tutto in riga
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  📅 [datepicker]  [🔍 cur1] [🔍 cur2] [×]    [Abs/%] [⚙] [⟳] [↻]    │
  └──────────────────────────────────────────────────────────────────────────┘

  ═══════════════════════════════════════════════════════════════════════════
  TABLET (610–1010)  — Filtri impilati, actions 2×2 a destra
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  📅 [datepicker]            │  [Abs/%] [⚙]                             │
  │  [🔍 cur1] [🔍 cur2] [×]   │  [⟳]    [↻]                             │
  └──────────────────────────────────────────────────────────────────────────┘

  ═══════════════════════════════════════════════════════════════════════════
  TABLET-S (500–610)  — Come tablet ma bottoni in colonna, icon-only
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  📅 [datepicker]            │  [Abs/%]                                 │
  │  [🔍 cur1] [🔍 cur2] [×]   │  [⚙]                                    │
  │                             │  [⟳]                                    │
  │                             │  [↻]                                    │
  └──────────────────────────────────────────────────────────────────────────┘

  ═══════════════════════════════════════════════════════════════════════════
  MOBILE (<500)  — Tutto impilato centrato
  ┌──────────────────────────────────────────────────────────────────────────┐
  │              📅 [datepicker]                                            │
  │            [🔍 cur1] [🔍 cur2] [×]                                     │
  │         [Abs/%] [⚙] [⟳] [↻]                                          │
  └──────────────────────────────────────────────────────────────────────────┘
```

**File modificato**: `fx/+page.svelte`

---

### G6 — Assets filter layout: non-wide rimette filtri in riga

**Problema**: In modalità `tablet` (e `tablet-s`), il blocco filtri usava `flex-row flex-wrap`,
quindi quando c'era abbastanza spazio i filtri tornavano su una sola riga. L'utente vuole che
una volta usciti da `wide`, i filtri siano **sempre su 2 righe** (datepicker sopra, search/type/currency sotto).

**Fix applicata**: Cambiata la logica CSS condizionale:
- Container principale: solo `wide` → `flex-row items-center`, tutto il resto → `flex-row items-start`
- Filters block: solo `wide` → `flex-row flex-wrap`, `tablet`+`tablet-s` → `flex-col`
- Inner filters block: solo `wide` → `flex-row flex-wrap`, `tablet`+`tablet-s` → `flex-col`

**File modificato**: `assets/+page.svelte`

---

### G7 ��� Assets action labels hardcoded in inglese

**Problema**: I bottoni azione nella filter bar assets usavano:
- `<span>Sync</span>` e `<span>Refresh</span>` (hardcoded)
- `title="Settings"`, `title="Sync all assets with providers"`, `title="Refresh all prices from DB"` (hardcoded)

**Fix applicata**: Sostituiti con chiavi `sharedResource.*` (vedi G8):
```svelte
{#if showActionLabels}<span>{$t('sharedResource.syncAll')}</span>{/if}
{#if showActionLabels}<span>{$t('sharedResource.refreshAll')}</span>{/if}
title={$t('sharedResource.settings')}
```

**File modificato**: `assets/+page.svelte`

---

### G8 — Migrazione i18n `fx.actions.*` → `sharedResource.*`

**Problema**: Le chiavi `fx.actions.syncAll`, `fx.actions.refreshAll`, `fx.actions.settings`
erano sotto il namespace `fx` ma usate anche dalla pagina Assets. La label "Sync"
corrispondeva a `common.sync` = "Sincronizza" (singolo), mentre il bottone intendeva
"Sync All" = "Sinc. Tutto".

**Fix applicata**:
1. Creata nuova sezione `sharedResource` in tutti e 4 i file i18n:
   ```json
   "sharedResource": {
     "syncAll": "Sync All / Sinc. Tutto / Sync. Tout / Sinc. Todo",
     "refreshAll": "Refresh All / Aggiorna Tutto / Actualiser Tout / Actualizar Todo",
     "settings": "Settings / Impostazioni / Paramètres / Ajustes"
   }
   ```
2. Rimossi `syncAll`, `refreshAll`, `settings` da `fx.actions` (mantenuto solo `addPair`)
3. Aggiornati tutti i riferimenti in `fx/+page.svelte` e `assets/+page.svelte`

**File modificati**: `en.json`, `it.json`, `fr.json`, `es.json`, `fx/+page.svelte`, `assets/+page.svelte`

---

## Ordine di Implementazione

1. ✅ **G3** — Aggiunto `min?`/`max?` a `EditableNumberCell` in `table/types.ts`
2. ✅ **G4** — Rimosso generic `<T>` da `getUserStorage`, return type `string` in `storage.ts`
3. ✅ **G5** — Cambiato `icon: Component` → `icon: any` in `DataTableToolbar.svelte`
4. ✅ **G1** — i18n label nei bulk actions in `assets/+page.svelte` e `fx/+page.svelte`
5. ✅ **G2** — Layout `tablet-s` per FX page in `fx/+page.svelte`
6. ✅ **G6** — Assets filter layout: non-wide sempre 2 righe
7. ✅ **G7** — Assets action labels → `sharedResource.*`
8. ✅ **G8** — Migrazione `fx.actions.*` → `sharedResource.*`

---

## Verifica Finale

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio/frontend && npx svelte-check --threshold error
# Risultato: 0 errori, 0 warning ✅
```
