# Phase 06 Bugfix Migration — Part 2

> Continuazione di [plan-phase06BugfixMigration.prompt.md](./plan-phase06BugfixMigration.prompt.md)

---

## Bug Residui — Stato Finale

| # | Bug | Stato |
|---|-----|-------|
| **E5** | Type filter dropdown: click-outside + restyle DataTable-like + i18n | ✅ Completo |
| **E5b** | Type filter dropdown: badge conteggio asset per tipo | ✅ Completo |
| **E1** | Provider chain icon-only quando icon_url presente | ✅ Completo (FxSyncModal) |
| **E1c** | FxTable provider chain: testo provider visibile in tabella | ✅ Completo |
| **E1b** | AssetCard (griglia) icone PNG invece di SVG Lucide | ✅ Completo |
| **E2** | Timeout minimo sync 10s → 20s | ✅ Completo |
| **E3** | Toggle Abs/% aggiunto nella cella vuota 2×2 | ✅ UI aggiunta → effetto visivo in Step 3 |
| **E6** | Filtri responsive + showActionLabels | ✅ Completo |
| **E6b** | Nuova modalità `tablet-s` | ✅ Implementato |
| **E4** | Segnali tecnici su AssetCard | ⏳ Spostato in plan-phase06Assets Step 3 |
| **E2E** | Backend E2E tests 401 fix | ✅ Completo |
| **Build** | a11y warnings risolti | ✅ Completo |
| **F1** | 404 su navigazione `/assets/{id}` — manca la route | ✅ Placeholder creato |
| **F2** | Bulk delete FX: cancella solo l'ultimo, modale riferisce un solo item | ✅ Completo |

---

## E6b — Nuova modalità `tablet-s` (DA IMPLEMENTARE)

### Contesto

Le modalità responsive attuali sono 3: `wide`, `tablet`, `mobile`.
Il range 500–770px è troppo largo per il layout `tablet` (filtri e bottoni non ci stanno in riga)
e troppo grande per `mobile` (dove tutto è impilato). Serve un layout intermedio.

### Layout proposto (approvato dall'utente)

```
                         Layout Responsive Assets Filter Bar

  ═══════════════════════════════════════════════════════════════════════════
  WIDE (≥1100)  — Tutto in riga
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  📅 [2025-09-23]→[2026-03-23]  🔍[search] [Active] [▾Type] [▾Cur] [×]  │
  │                                                                          │
  │  [Abs/%]  [⚙ Settings]  [⟳ Sync]  [↻ Refresh]                          │
  └──────────────────────────────────────────────────────────────────────────┘

  ═══════════════════════════════════════════════════════════════════════════
  TABLET (770–1100)  — Filtri su 2 righe, bottoni 2×2 a destra
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  📅 [2025-09-23]→[2026-03-23]  🔍[search]  [Active] │  [Abs/%] [⚙ Set] │
  │                                 [▾Type] [▾Cur]  [×]  │  [⟳ Sync] [↻ Ref]│
  └──────────────────────────────────────────────────────────────────────────┘

  ═══════════════════════════════════════════════════════════════════════════
  TABLET-S (500–770)  — Filtri sotto il datepicker, bottoni in colonna a destra
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  📅 [2025-09-23]→[2026-03-23]                        │  [Abs/%]         │
  │  🔍 [search]  [Active]  [▾ Type]  [▾ Cur]  [×]       │  [⚙]            │
  │                                                       │  [⟳]            │
  │                                                       │  [↻]            │
  └──────────────────────────────────────────────────────────────────────────┘
  Datepicker e filtri: allineati a sinistra, impilati verticalmente.
  Bottoni azione: colonna a destra, icon-only (showActionLabels = false).
  Se c'è spazio sufficiente (verso il range alto): label tornano visibili.

  ═══════════════════════════════════════════════════════════════════════════
  MOBILE (<500)  — Tutto impilato al centro
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                  📅 [2025-09-23]→[2026-03-23]                           │
  │                  🔍 [search...]                                         │
  │                  [Active]  [▾ Type]  [×]                                │
  │                  [▾ Currency]                                            │
  │                  [Abs/%]  [⚙]  [⟳]  [↻]                               │
  └──────────────────────────────────────────────────────────────────────────┘
```

### Piano implementazione

1. **Aggiungere `'tablet-s'` al tipo `layoutMode`** — da `'wide' | 'tablet' | 'mobile'` a `'wide' | 'tablet' | 'tablet-s' | 'mobile'`

2. **Aggiornare soglie ResizeObserver**:
   ```
   if (w >= 1100)      layoutMode = 'wide'
   else if (w >= 770)  layoutMode = 'tablet'
   else if (w >= 500)  layoutMode = 'tablet-s'    // ← NEW
   else                layoutMode = 'mobile'
   ```

3. **`showActionLabels`**: due soglie separate
   - In `tablet` e `wide`: label visibili (già funziona con `w >= 820`)
   - In `tablet-s`: label nascosti (icon-only) per default, opzionalmente visibili verso il range alto (~700+)
   - In `mobile`: sempre icon-only

4. **Container principale (filterBarRef div)**:
   - `tablet-s`: `flex-row items-start justify-between` (stesso del tablet, ma i figli si impilano diversamente)

5. **Filters block** (datepicker + filtri):
   - `tablet-s`: `flex-col` (datepicker sopra, filtri sotto — allineati a sinistra)

6. **Actions block** (Abs/%, Settings, Sync, Refresh):
   - `tablet-s`: `flex-col gap-1.5` (colonna verticale, non grid 2×2)

### File coinvolti
- `frontend/src/routes/(app)/assets/+page.svelte` — layout classes + soglie ResizeObserver

### Stima: ~15 min

---

## Checklist Verifica Step 2 (prima di procedere a Step 3)

Riferimento: checklist D1–D12 da `plan-phase06BugfixMigration.prompt.md` + Step 2 da `plan-phase06Assets.prompt.md`.

### Componenti creati (Step 2)
- [x] `ViewModeToggle.svelte` — toggle grid/table riusabile, localStorage persistence
- [x] `AssetIcon.svelte` — fallback chain: icon_url → PNG per tipo → BarChart3 SVG
- [x] `AssetCard.svelte` — header, price+Δ, PriceChartCompact, footer azioni
- [x] `AssetTable.svelte` — DataTable con colonne: name+icon, type badge, currency flag, last price, Δ multi-period, provider, actions
- [x] `FxTable.svelte` — DataTable per FX pairs con swap, provider chain, Δ multi-period

### Pagine aggiornate (Step 2)
- [x] `/assets/+page.svelte` — dual view grid/table, filtri, DateRangePicker, bulk actions
- [x] `/fx/+page.svelte` — aggiunto toggle grid/table, FxTable integrato

### Bugfix Migration (Step 2b–2e, D1–D12)
- [x] D1: ColumnVisibilityToggle centrato (`justify-center`)
- [x] D2: Provider chain ricca con icone favicon (FxTable + FxSyncModal) — icon-only con icon_url
- [x] D3: Fix bulk sync undefined — `onSelectionChange` mapping corretto
- [x] D4: ChartSettingsModal integrato nella pagina Assets (global + per-card placeholder)
- [x] D5: AssetTable filtro tipo con icone PNG nelle enumOptions
- [x] D6: i18n tipi asset (8 tipi × 4 lingue) + icona PNG nel badge card
- [x] D7: AssetCard icona asset (PNG) + pallino active
- [x] D8: `filterable: false` su colonne type e currency in AssetTable
- [x] D9: Filtro tipo globale multi-checkbox con pannello (restyled DataTable-like)
- [x] D10: Filtro valuta multi-select con badge rimuovibili + CurrencySearchSelect
- [x] D11: Layout responsive filter bar Assets (Proposta D + Opzione γ)
- [x] D12: Provider chain fallback iniziali (incluso in D2)

### Bug aggiuntivi trovati in review (E1–E6)
- [x] E1: Provider chain icon-only con icon_url (FxSyncModal)
- [x] E1b: AssetIcon PNG fallback (no più SVG Lucide)
- [x] E2: Timeout minimo sync → 20s
- [x] E3: Toggle Abs/% nella cella vuota 2×2 (effetto visivo → Step 3)
- [x] E4: Segnali tecnici su AssetCard → Step 3
- [x] E5: Type filter dropdown: click-outside fix + restyle + i18n `common.selectAll`/`common.clearAll`
- [x] E6: showActionLabels responsive
- [x] **E5b**: Badge conteggio asset per tipo nel dropdown — ✅ IMPLEMENTATO
- [x] **E6b**: Modalità `tablet-s` (500–770px) — ✅ IMPLEMENTATO
- [x] **E1c**: FxTable provider chain: testo ancora visibile in tabella — ✅ IMPLEMENTATO
- [x] **F1**: 404 su navigazione `/assets/{id}` — ✅ IMPLEMENTATO (placeholder page)
- [x] **F2**: Bulk delete FX: cancella solo ultimo, modale incompleta — ✅ IMPLEMENTATO

### Backend
- [x] E2E tests: auth aggiunta a `test_complete_e2e_flow_yfinance` e `test_search_provides_all_required_fields`
- [x] Endpoint bulk asset prices funzionante
- [x] Test suite: 6/8 categorie passed (E2E fixato, User e FX skipped/pending)

### Build & Quality
- [x] Zero warning a11y in build
- [x] 26 errori preesistenti (lucide-svelte type mismatch Svelte 5) — non bloccanti, funzionano a runtime
- [x] `@const` con annotazione TS rimosso (spostato a `TYPE_ICON_MAP` nello script)

### Verifiche manuali (risultati)

1. ✅ **Navigazione**: click card/riga → placeholder page `/assets/{id}` — **F1 fixato**
2. ✅ **Filtri**: search debounced, active toggle, type multi-checkbox, currency badge, reset × — tutti OK
3. ✅ **Responsive**: wide → tablet → tablet-s → mobile — **E6b implementato**
4. ✅ **Dark mode**: tutti i componenti verificati OK
5. ✅ **i18n**: label tradotte correttamente (Select All/Clear All, tipi asset, filtri)
6. ✅ **FX table**: provider chain icon-only — **E1c fixato** (preload `getCurrencyGraph()` in onMount)
7. ✅ **Bulk delete**: modale lista con bandiere flag — **F2 fixato** (flusso bulk dedicato con `confirmBulkDelete`)

---

## Nuovi Bug — Dettagli e Piano Fix

### F1 — 404 su `/assets/{id}` (manca la route)

**Problema**: La directory `src/routes/(app)/assets/[id]/` non esiste. Click su una card o riga nella tabella chiama `goto('/assets/{id}')` che genera 404.

**Fix**: Creare una pagina placeholder `src/routes/(app)/assets/[id]/+page.svelte` che mostra un messaggio "Asset detail — Coming in Step 4" con un bottone "← Back to Assets".

**File da creare**:
- `frontend/src/routes/(app)/assets/[id]/+page.svelte`

**Stima**: 5 min

---

### E1c — FxTable provider chain mostra testo in tabella

**Problema**: `providerIconHtml()` in `FxTable.svelte` chiama `getCachedFxProviders()` che restituisce `[]` se il grafo currency non è stato ancora costruito al momento del primo render. Risultato: `info` è `undefined`, cade nel fallback testuale (es. `ECB` invece dell'icona).

Il fix E1 precedente funziona solo quando i provider sono già in cache (es. FxSyncModal che si apre dopo, o dopo navigazione). Ma al primo render della tabella, la cache è vuota.

**Fix**: Due opzioni:
- **Opzione A (semplice)**: Nella FX page, assicurarsi che `getCurrencyGraph()` venga chiamato in `onMount` PRIMA che `data` venga passato alla tabella, così i provider sono in cache.
- **Opzione B (robusta)**: Aggiungere un `providerVersion` counter reattivo in FxTable, aggiornato quando i provider si caricano, per forzare il re-render delle celle.

**File**: `frontend/src/routes/(app)/fx/+page.svelte` (opzione A) oppure `FxTable.svelte` (opzione B)

**Stima**: 5 min (opzione A), 15 min (opzione B)

---

### E5b — Badge conteggio asset per tipo nel dropdown

**Problema**: Il dropdown type filter non mostra quanti asset ci sono per ogni tipo. L'utente vorrebbe un badge numerico accanto a ciascun tipo.

**Fix**: Calcolare un `typeCounts` derivato da `assets`, mostrare badge `(N)` accanto a ogni label nel dropdown. Se il conteggio è 0, nascondere l'opzione dal dropdown.

**Implementazione**:
```svelte
let typeCounts = $derived(
    assets.reduce((acc, a) => {
        const t = a.asset_type ?? 'OTHER';
        acc[t] = (acc[t] ?? 0) + 1;
        return acc;
    }, {} as Record<string, number>)
);
```
Nel template: mostrare solo tipi con conteggio > 0, badge `(N)` dopo il nome.

**File**: `frontend/src/routes/(app)/assets/+page.svelte`

**Stima**: 10 min

---

### F2 — Bulk delete FX: cancella solo l'ultimo, modale singola

**Problema**: `handleBulkDeleteFx()` itera i `selectedFxRows` e chiama `handleDeletePair()` per ciascuno. Ma `handleDeletePair()` setta `deletingPair = detail` e apre la modale di conferma. In un loop, ogni iterazione sovrascrive `deletingPair`, e la modale si apre solo per l'ultimo item.

**Fix**: Creare un flusso bulk delete dedicato:
1. Nuovo state `deletingPairs: Array<{base, quote, slug}>` (lista, non singolo)
2. Nuova modale (o ConfirmModal esteso) che mostra la lista completa di coppie da cancellare, con le bandiere flag
3. `confirmBulkDelete()` che itera sulla lista e cancella sequenzialmente
4. Stesso pattern anche per Assets bulk delete (placeholder per Step 3)

**File**: `frontend/src/routes/(app)/fx/+page.svelte`

**Stima**: 20 min

---

## File Modificati (Tutte le sessioni)

| File | Sessione | Modifiche |
|------|----------|-----------|
| `frontend/src/lib/components/assets/AssetIcon.svelte` | 2 | PNG fallback chain (no più Lucide SVG) |
| `frontend/src/lib/components/assets/AssetCard.svelte` | 2 | `deltaDisplayMode` prop |
| `frontend/src/lib/components/fx/FxTable.svelte` | 2 | Provider icon-only con icon_url |
| `frontend/src/lib/components/fx/FxSyncModal.svelte` | 2 | Provider icon-only + timeout 20s |
| `frontend/src/routes/(app)/assets/+page.svelte` | 2+3+4 | E5 restyle, E6 layout, showActionLabels, i18n fix, a11y |
| `backend/test_scripts/test_e2e/test_search_to_prices.py` | 2 | Auth aggiunta a 2 test |
| `TODO_FUTURI.md` | 3 | Rimosso CurrencySearchSelect multi-mode + E3/E4 |
| `plan-phase06Assets.prompt.md` | 3 | E3/E4 aggiunti a Step 3 tasks |
