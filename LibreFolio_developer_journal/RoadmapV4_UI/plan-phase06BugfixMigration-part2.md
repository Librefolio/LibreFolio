# Phase 06 Bugfix Migration — Part 2

> Continuazione di [plan-phase06BugfixMigration.prompt.md](./plan-phase06BugfixMigration.prompt.md)

---

## Bug Residui — Implementazione (Sessione 2 + 3)

| # | Bug | Stato |
|---|-----|-------|
| **E5** | Type filter dropdown si chiude al click su checkbox | ✅ Fixato + restyle DataTable-like |
| **E1** | Provider chain mostra testo `ECB` anche con `icon_url` | ✅ Fixato |
| **E1b** | AssetCard (griglia) mostra icone SVG Lucide invece di PNG | ✅ Fixato |
| **E2** | Timeout minimo sync 10s troppo basso | ✅ Fixato |
| **E3** | Assets 2×2: cella top-left vuota in grid mode → toggle Abs/% | ✅ Toggle aggiunto → Step 3 per effetto visivo |
| **E6** | Tablet: filtri accanto + action labels responsive | ✅ Fixato + showActionLabels |
| **E4** | Segnali tecnici non compaiono sulle AssetCard | ⏳ Spostato in plan-phase06Assets Step 3 |
| **E2E** | Backend E2E tests falliscono con 401 | ✅ Fixato (mancava auth) |
| **Build** | a11y warnings su div dropdown | ✅ Fixato |

---

### Sessione 3 — Feedback e Refinements

#### TODO_FUTURI cleanup
- ~~🪙 CurrencySearchSelect multi-mode~~ — rimosso (soluzione attuale con badge è migliore)
- ~~📊 Assets Step 3 Pending Tasks~~ — spostati nel piano corretto (`plan-phase06Assets.prompt.md` Step 3)

#### E3/E4 → plan-phase06Assets Step 3
Aggiunti come task nel Step 3 di `plan-phase06Assets.prompt.md`:
- `E3`: Toggle Abs/% + suffisso valuta + segnali PriceChartCompact
- `E4`: Segnali tecnici su PriceChartCompact (settings prop + overlay rendering)

#### E5 — Restyle dropdown DataTable-like
- **Bottoni Select All / Clear All**: ora sono veri bottoni con bordo e sfondo (come `enum-action-btn` in DataTableColumnFilter)
- **Opzioni**: `<button>` con checkmark icon (Check di lucide-svelte) + sfondo colorato libre-green (come `enum-checkbox.checked`)
- **Layout**: pannello con bordo `rounded-lg`, lista opzioni in sotto-container `rounded-md` con bordo
- **i18n**: `$t('selectAll')` / `$t('clearAll')`

#### E6 — showActionLabels
- Aggiunta variabile `showActionLabels` (soglia `w >= 690`)
- Bottoni Settings, Sync, Refresh: label condizionale `{#if showActionLabels}<span>...</span>{/if}`
- ColumnVisibilityToggle: `showLabel={showActionLabels}`

#### Build a11y
- `tabindex="0"` + `svelte-ignore a11y_interactive_supports_focus` (falso positivo del checker dentro `{#if}`)

---

## File Modificati (Sessione 3)

| File | Modifiche |
|------|-----------|
| `frontend/src/routes/(app)/assets/+page.svelte` | E5 restyle, showActionLabels, a11y fix, Check import |
| `TODO_FUTURI.md` | Rimosso CurrencySearchSelect multi-mode + E3/E4 |
| `plan-phase06Assets.prompt.md` | E3/E4 aggiunti a Step 3 tasks |
| `plan-phase06BugfixMigration-part2.md` | Questo file aggiornato |
