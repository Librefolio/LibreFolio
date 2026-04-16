# Plan: i18n Duplicate Cleanup

**Data creazione**: 15 Aprile 2026  
**Status**: 📋 DA FARE  
**Parent**: [plan-phase06Step6-Polish-Test-Docs.prompt.md](plan-phase06Step6-Polish-Test-Docs.prompt.md) → S1b  
**Partenza**: 843 chiavi, 0 unused, 60 gruppi duplicati  
**Audit source**: [`audit_duplicate.md`](../../audit_duplicate.md)

---

## Principio guida

Consolidare sotto `common.*` solo quando **significato, contesto e valore coincidono in
tutte e 4 le lingue**. Se il valore differisce anche solo per capitalizzazione in una
lingua, prima si allinea la traduzione, poi si consolida.

Le coppie con significato diverso (es. "Close" bottone vs "Close" prezzo) restano separate.

---

## BATCH 0 — Rimuovi unused ✅ (già fatto)

| Chiave | Stato |
|--------|-------|
| `uploads.imageSize` | ✅ rimossa |
| `uploads.maxSize` | ✅ rimossa |

---

## BATCH 1 — Shared detail page keys (assetDetail ↔ fxDetail)

Queste chiavi hanno **esattamente** lo stesso valore in TUTTE le lingue (o differiscono
solo in ES/FR per una parola — va allineata prima). Vengono usate 1 volta ciascuna nelle
rispettive detail page. Consolidarle sotto `common.*` elimina 2 chiavi per coppia.

| # | Losers (rimuovere) | Winner (creare/usare) | Lingue identiche | Fix necessario |
|---|---|---|---|---|
| 1 | `assetDetail.measures` + `fxDetail.measures` | `common.measures` | ALL | — |
| 2 | `assetDetail.signals` + `fxDetail.signals` | `common.signals` | ALL | — |
| 3 | `assetDetail.addMeasure` + `fxDetail.addMeasure` | `common.addMeasure` | EN,IT,FR | fix ES: `fxDetail` "Añadir medición" → "Añadir medida" |
| 4 | `assetDetail.closeEditor` + `fxDetail.closeEditor` | `common.closeEditor` | EN,IT,ES | fix FR: `fxDetail` "Fermer l'éditeur" → "Fermer éditeur" |
| 5 | `assetDetail.exitMeasure` + `fxDetail.exitMeasure` | `common.exitMeasure` | EN,IT,FR | fix ES: `fxDetail` "Salir del modo de medición" → "Salir del modo medida" |

**Nota su `measure.addMeasure`**: è un 3° duplicato (IT only) con casing diverso
("Add Measure" vs "Add measurement"). Consolidare anche questo sotto `common.addMeasure`.

**Chiavi eliminate**: 2×5 + 1 = 11  
**Gruppi duplicati eliminati**: ~7

### Procedura Batch 1

```bash
# Per ogni coppia (esempio measures):
# 1. Creare la chiave common.* con il valore del winner
./dev.py i18n add "common.measures" "Measures" --it "Misure" --fr "Mesures" --es "Medidas"

# 2. Aggiornare i file sorgente
#    assetDetail.measures → common.measures  in assets/[id]/+page.svelte
#    fxDetail.measures    → common.measures  in fx/[pair]/+page.svelte

# 3. Rimuovere le chiavi vecchie
./dev.py i18n remove "assetDetail.measures" -f
./dev.py i18n remove "fxDetail.measures" -f
```

---

## BATCH 2 — Modal ↔ Detail duplicates (assets)

Chiavi usate sia come header nel modal create/edit sia come tab nella detail page.
Identiche in ALL lingue (differiscono solo per capitalizzazione IT — case-insensitive match).

| # | Losers (rimuovere) | Winner (creare/usare) | Note |
|---|---|---|---|
| 6 | `assetDetail.classification` + `assets.modal.classification` | `common.classification` | — |
| 7 | `assetDetail.identifiers` + `assets.modal.identifiers` | `common.identifiers` | — |
| 8 | `assetDetail.geoDistribution` + `assets.modal.geographicDistribution` | `common.geoDistribution` | — |
| 9 | `assetDetail.sectorDistribution` + `assets.modal.sectorDistribution` | `common.sectorDistribution` | — |

**Chiavi eliminate**: 2×4 = 8  
**Gruppi duplicati eliminati**: 4

---

## BATCH 3 — Cross-feature duplicates (→ `common.*`)

Chiavi usate in moduli diversi (assets, fx, help) con valore identico in ALL lingue.

| # | Losers (rimuovere) | Winner (creare/usare) | Note |
|---|---|---|---|
| 10 | `assets.allCurrencies` + `fx.filter.allCurrencies` | `common.allCurrencies` | — |
| 11 | `assets.empty.noMatchesTitle` + `fx.empty.noMatchesTitle` | `common.noMatchesTitle` | — |
| 12 | `assets.provider.documentation` + `help.documentation` | `common.documentation` | — |

**Chiavi eliminate**: 2×3 = 6  
**Gruppi duplicati eliminati**: 3

---

## BATCH 4 — Point to existing `common.*`

Chiavi duplicate dove `common.*` esiste già con lo stesso valore.

| # | Loser (rimuovere) | Winner (esistente) | Note |
|---|---|---|---|
| 13 | `assets.schedule.confirmDelete` | `common.confirmDelete` | case diff FR: "suppression" → "Suppression" → fix |
| 14 | `assets.schedule.deleteSelected` | `common.deleteSelected` (new) | case diff EN+IT → normalizzare |
| 15 | `brokers.name` | `common.name` | identico ALL |

**Nota**: `dataEditor.deleteSelected` è stato già rimosso. Creare `common.deleteSelected`
e puntare sia `assets.schedule.deleteSelected` che le eventuali nuove occorrenze lì.

**Chiavi eliminate**: 3  
**Gruppi duplicati eliminati**: 3

---

## BATCH 5 — Same-namespace merge

Chiavi nello stesso namespace con valore identico — una è ridondante.

| # | Tenere | Rimuovere | Note |
|---|---|---|---|
| 16 | `assets.schedule.emptyTitle` | `assets.schedule.empty` | stessa stringa, usarne una sola |
| 17 | `assets.modal.title` | `assets.addAsset` | "Add Asset" — il modale usa il title, il button può usare lo stesso |

**Chiavi eliminate**: 2  
**Gruppi duplicati eliminati**: 2

---

## KEEP SEPARATE — Duplicati accettabili (~30 gruppi)

Questi hanno valore identico ma **significato o contesto diverso**. Non consolidare.

### Significato diverso nonostante valore uguale
| Gruppo | Motivo |
|--------|--------|
| `common.close` / `dataEditor.col.close` | "Chiudi" (bottone) vs "Chiusura" (prezzo OHLC) |
| `common.reset` / `common.undo` | Significato EN diverso ("Reset to Default" vs "Undo"), stesso IT |
| `common.retry` / `error.tryAgain` | "Retry" vs "Try Again" — contesto diverso |
| `chartSettings.discardTitle` / `common.discardChanges` | Formulazione diversa ("Discard changes?" vs "Discard Changes?") |
| `assets.confirm.confirmChange` / `assets.confirm.identifierChanged` | EN diverso ("Confirm Change" vs "Confirm Asset Change") |
| `assets.modal.saveChanges` / `common.save` | "Save Changes" vs "Save" |
| `assetDetail.syncPrices` / `assets.sync.modalTitle` | "Sync Prices" vs "Sync Asset Prices" |

### Dynamic prefix / singolare-plurale
| Gruppo | Motivo |
|--------|--------|
| `assets.types.OTHER` / `common.other` | dynamic prefix `assets.types` |
| `uploads.file` / `uploads.files` / `uploads.title` | singolare/plurale/titolo |
| `brokers.title` / `uploads.broker` | page title vs field label |
| `brokers.sharing.editors` / `brokers.sharing.roleEditorShort` | plurale vs singolare |

### Contesto UI diverso
| Gruppo | Motivo |
|--------|--------|
| `assets.sync.assetsCount` / `assets.title` / `dashboard.assetCount` | count label / page title / dashboard stat |
| `assets.type` / `common.type` | specifico assets vs generico — potrebbe divergere |
| `assets.schedule.currency` / `settings.categoryCurrency` / `common.currency` | contesti diversi, ES diverge ("Moneda" vs "Divisa") |
| `assets.schedule.period` / `chartSettings.params.period` | contesti diversi |
| `assets.provider.selectProvider` / `assets.table.provider` | dropdown label vs column header |
| `assets.search.providers` / `fx.providers` | label in contesti diversi |
| `nav.settings` / `sharedResource.settings` | ES diverso ("Configuración" vs "Ajustes") |
| `settings.resetAllToDefault` / `uploads.resetAll` / `common.resetAll` | EN diverso ("Reset All" vs "Reset All to Defaults") |
| `fileStatus.uploaded` / `uploads.uploadDate` | stato vs data |
| `chartSettings.discard` / `common.discard` | FR diverso ("Rejeter" vs "Abandonner") |
| `dataEditor.clearSelection` / `table.clearSelection` | IT diverso |

### Abbreviazioni signal (intenzionali)
| Gruppo | Motivo |
|--------|--------|
| `chartSettings.signals.ema` / `emaAbbr` | nome vs abbreviazione — stessi oggi, potrebbero divergere |
| `chartSettings.signals.macd` / `macdAbbr` | idem |
| `chartSettings.signals.rsi` / `rsiAbbr` | idem |
| `chartSettings.signals.fxPair` / `fxPairAbbr` | "FX Pair" vs "FX" |
| `chartSettings.signals.assetComparisonAbbr` | caso specifico IT |

### Unità settings (dynamic prefix)
| Gruppo | Motivo |
|--------|--------|
| `settings.globalSettingUnits.*_hours` | 2 chiavi "hours" — dynamic prefix |

---

## Riepilogo impatto

| Metrica | Prima | Dopo |
|---------|-------|------|
| Chiavi totali | 843 | ~813 (−30) |
| Gruppi duplicati | 60 | ~30 |
| Unused | 0 | 0 |
| Nuove `common.*` | — | ~14 |

---

## Ordine esecuzione

```
BATCH 1 (detail shared)    → 11 chiavi eliminate, ~7 gruppi
BATCH 2 (modal/detail)     → 8 chiavi eliminate, 4 gruppi
BATCH 3 (cross-feature)    → 6 chiavi eliminate, 3 gruppi
BATCH 4 (→ existing)       → 3 chiavi eliminate, 3 gruppi
BATCH 5 (same-namespace)   → 2 chiavi eliminate, 2 gruppi
                             ────────────────────────────
                             30 chiavi, ~19 gruppi
```

Per ogni batch: creare `common.*` → aggiornare sorgente → rimuovere vecchie → audit.

