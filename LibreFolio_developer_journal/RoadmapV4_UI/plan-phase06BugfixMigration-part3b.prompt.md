# Phase 06 Bugfix Migration — Part 3b

> Continuazione di [plan-phase06BugfixMigration-part3.md](./plan-phase06BugfixMigration-part3.md)
>
> Fix residui post-review manuale: soglie responsive, i18n refresh→ricarica, title hardcoded,
> layout tablet assets, provider chain detail, segnale FxPair (label+posizione+sync),
> bulk actions assets reali (API backend pronte).

---

## Panoramica Bug

| # | Bug | File coinvolti | Stato |
|---|-----|----------------|-------|
| **H1** | Rimuovere `title` da tutti i bottoni 2×2 + ColumnVisibility | `assets/+page.svelte`, `ColumnVisibilityToggle.svelte` | ✅ Fatto |
| **H2** | Soglie responsive errate (wide, labels) | `assets/+page.svelte`, `fx/+page.svelte` | ✅ Fatto |
| **H3** | Assets tablet: filtri vanno sotto datepicker ma dovrebbero stare accanto | `assets/+page.svelte` | ✅ Fatto |
| **H4** | i18n: "refresh/Aggiorna" confuso con "sync" → rinominare in "reload/Ricarica" | 4× `i18n/*.json` | ✅ Fatto |
| **H5** | 2 chiavi i18n orfane: `assets.table.active`, `fx.editPairConfig` | 4× `i18n/*.json` | ✅ Fatto |
| **H6** | FxTable row action `label: 'Sync'` hardcoded | `FxTable.svelte` | ✅ Fatto |
| **H7** | Provider chain mancante nel Detail FX (modal vuoto) | `FxPairAddModal.svelte` (diagnostica) | ⏳ Manuale |
| **H8** | Filtro colonna "Provider" inutile (disabilitare) | `FxTable.svelte`, `AssetTable.svelte` | ✅ Fatto |
| **H9** | Bottoni sync+open nel segnale FxPair: posizione errata (header → parametri) | `ChartSignalsSection.svelte` | ✅ Fatto |
| **H10** | `handleSyncPair` nel detail: toast non tradotto + nessun risultato reale | `fx/[pair]/+page.svelte` | ✅ Fatto |
| **H11** | FxPairSignal label: `A/B` → `🇦🇺 A → 🇪🇺 B` con bandiere | `FxPairSignal.ts` | ✅ Fatto |
| **H12** | Bulk Sync Assets: placeholder `console.log` → API reale | `assets/+page.svelte` | ✅ Fatto |
| **H13** | Bulk Delete Assets: placeholder `console.log` → API reale + ConfirmModal | `assets/+page.svelte` | ✅ Fatto |

**Totale issue: 13** — 3 cause radice (i18n, segnale FxPair, placeholder assets).

---

## Spiegazione Tecnica degli Errori

### H1 — Rimuovere `title` da bottoni 2×2 + ColumnVisibility

**Problema**: I 3 bottoni azione nella filter bar assets (Settings, Sync All, Refresh All)
hanno `title={$t('sharedResource.*')}`. In FX non ci sono. Vanno rimossi per coerenza.
Inoltre `ColumnVisibilityToggle.svelte` riga 118 ha `title="Column visibility"` hardcoded
in inglese — usato sia da Assets che da FX in modalità table.

**Fix**:
- [assets/+page.svelte](frontend/src/routes/(app)/assets/+page.svelte) righe 685, 694, 703:
  rimuovere `title={$t('sharedResource.*')}`
- [ColumnVisibilityToggle.svelte](frontend/src/lib/components/table/ColumnVisibilityToggle.svelte)
  riga 118: rimuovere `title="Column visibility"`

**Stima**: 2 minuti

---

### H2 — Soglie responsive errate

**Problema**: Il francese è la lingua più prolissa → in modalità wide i contenuti traboccano.
In mobile le label scompaiono troppo presto o troppo tardi.

**Fix** — 4 soglie da aggiustare:

| File | Soglia | Da | A | Motivo |
|------|--------|----|---|--------|
| `assets/+page.svelte` riga 198 | wide | `1200` | `1240` | FR prolisso |
| `assets/+page.svelte` riga 202 | labels | `400` | `460` | Label visibili troppo in basso |
| `fx/+page.svelte` riga 234 | wide | `1010` | `1030` | FR prolisso |
| `fx/+page.svelte` riga 237 | labels | `690` | `460` | Allineare con assets |

**Stima**: 2 minuti

---

### H3 — Assets tablet: filtri sotto datepicker (bug layout)

**Problema**: In modalità `tablet` (≥920px) il blocco filtri esterno usa `flex-col` — mette
il datepicker SOPRA i filtri. Ma a 920px c'è spazio per avere datepicker A FIANCO dei filtri
(con i filtri su 2 righe). Solo in `tablet-s` (<920px) i filtri devono andare sotto.

**Layout attuale sbagliato** (tablet):
```
┌─────────────────────────────────────┐
│ [datepicker]                  [2×2] │
│ [search active]                     │
│ [type currency ×]                   │
└─────────────────────────────────────┘
```

**Layout desiderato** (tablet):
```
┌─────────────────────────────────────┐
│ [datepicker] [search active]  [2×2] │
│              [type currency ×]      │
└─────────────────────────────────────┘
```

**Fix** in [assets/+page.svelte](frontend/src/routes/(app)/assets/+page.svelte):
- Riga 512-515 (Filters block esterno):
  - `tablet` → `flex-row items-center flex-1` (datepicker accanto ai filtri)
  - `tablet-s` → `flex-col items-start flex-1` (datepicker sopra)
  - Attualmente entrambi usano `flex-col` (sbagliato per tablet)
- Riga 528 (Inner filters block):
  - Resta `flex-col` sia per `tablet` che per `tablet-s` (i filtri interni sono sempre su 2 righe)
  - Solo `wide` usa `flex-row flex-wrap`

**Riepilogo layout completo**:
```
wide     → tutto in 1 riga
tablet   → [datepicker] [filtri 2 righe] | [2×2]
tablet-s → [datepicker]                  | [colonna btns]
           [filtri 2 righe]              |
mobile   → tutto impilato centrato
```

**Stima**: 5 minuti

---

### H4 — i18n: "refresh/Aggiorna" → "reload/Ricarica"

**Problema**: `common.refresh` (IT: "Aggiorna") si confonde con `common.sync` (IT: "Sincronizza").
"Refresh/Aggiorna" ricarica i dati dal DB locale; "Sync/Sincronizza" va al provider remoto.
La distinzione non è chiara all'utente.

**Fix**: Rinominare le chiavi i18n per chiarire la semantica:

| Chiave | EN attuale | EN nuovo | IT attuale | IT nuovo |
|--------|-----------|----------|-----------|----------|
| `common.refresh` | Refresh | Reload | Aggiorna | Ricarica |
| `sharedResource.refreshAll` | Refresh All | Reload All | Aggiorna Tutto | Ricarica Tutto |

Traduzioni FR/ES:

| Chiave | FR attuale | FR nuovo | ES attuale | ES nuovo |
|--------|-----------|----------|-----------|----------|
| `common.refresh` | Actualiser | Recharger | Actualizar | Recargar |
| `sharedResource.refreshAll` | Actualiser Tout | Recharger Tout | Actualizar Todo | Recargar Todo |

**Impatto codice**: Zero — solo modifica nei 4 file JSON. I 9 punti sorgente che usano
`common.refresh` e i 2 che usano `sharedResource.refreshAll` leggeranno automaticamente
il nuovo valore.

**Stima**: 5 minuti

---

### H5 — Chiavi i18n orfane

**Problema**: L'audit `./dev.py i18n audit` rileva 2 chiavi non usate da nessun sorgente:
- `assets.table.active` — non usata (il filtro active/all usa un'altra logica)
- `fx.editPairConfig` — non usata

**Fix**: Eliminare entrambe le chiavi da `en.json`, `it.json`, `fr.json`, `es.json`.

**Stima**: 3 minuti

---

### H6 — FxTable row action `'Sync'` hardcoded

**Problema**: In [FxTable.svelte](frontend/src/lib/components/fx/FxTable.svelte) riga 282,
il row action sync ha `label: 'Sync'` (stringa hardcoded in inglese) invece di usare la
funzione i18n.

**Fix**: Cambiare in `label: () => $t('common.sync')`.

**Stima**: 1 minuto

---

### H7 — Provider chain mancante nel Detail FX

**Problema**: Nella tabella FX list, una coppia come GBP/PLN mostra la catena provider:
```
🇵🇱 ⇆ ECB ⇆ 🇪🇺 ⇆ BOE ⇆ 🇬🇧
```
Ma nel detail (`/fx/GBP-PLN`) → bottone Provider (🔧) → il modal `FxPairAddModal` non
mostra nulla.

**Analisi del flusso**:
1. Il detail page (riga 930-940) apre `FxPairAddModal` in `editMode=true` con `editRoutes`
   derivato da `providers.chainSteps`
2. Il modal (riga 86-124) fa una propria call `GET /api/v1/fx/providers/routes` e filtra
   per `editBase`/`editQuote` (riga 100-106)
3. I route filtrati vengono messi in `selectedRoutes`
4. Se `selectedRoutes` è vuoto, il componente `FxProviderSelect` non mostra nulla

**Possibili cause**:
- Il filtro riga 101-103 filtra per `i.base === editBase && i.quote === editQuote` ma il
  backend potrebbe avere la coppia invertita (es. `base: PLN, quote: GBP` anziché
  `base: GBP, quote: PLN`). Il filtro gestisce entrambe le direzioni (`||`), ma verifica
  che `editBase` e `editQuote` siano corretti
- Il filtro riga 104 esclude le coppie MANUAL — se GBP/PLN ha solo MANUAL, nulla viene mostrato
- La response API potrebbe non contenere `chain_steps` per le catene multi-step

**Checklist Chrome DevTools per diagnostica**:

| # | Dove | Cosa verificare |
|---|------|----------------|
| 1 | **Network tab** | Aprire detail GBP-PLN → cliccare bottone 🔧 Provider → cercare request `GET /api/v1/fx/providers/routes` → verificare response: deve contenere items con `base`/`quote` matching GBP+PLN e `chain_steps` popolato |
| 2 | **Network tab** | Confrontare la response con quella caricata dalla list page (stessa API, stessa risposta) |
| 3 | **Console tab** | Cercare errore `Failed to load routes for edit mode` |
| 4 | **Elements tab** | Dopo apertura modal → ispezionare DOM del `FxPairAddModal` → cercare il `FxProviderSelect`, verificare che abbia route visualizzate |
| 5 | **Svelte Devtools** | Cercare componente `FxPairAddModal` → verificare props `editBase`, `editQuote` e state `selectedRoutes` → se `selectedRoutes` è array vuoto, il bug è nel filtro |

**Fix** (da determinare dopo diagnostica): probabile fix nel filtro del modal o nella
trasformazione dei dati. La tabella FX mostra le catene correttamente, quindi i dati API
sono corretti — il problema è nel modal.

**Stima**: 10-15 minuti (diagnostica + fix)

---

### H8 — Disabilitare filtro colonna "Provider"

**Problema**: Le tabelle FX e Assets hanno una colonna "Provider" con filtro attivo. Il filtro
non è utile nel formato attuale (filtra per singolo codice provider, non per catene che
contengono un certo provider). Potrebbe servire in futuro se filtrasse "catene che contengono
almeno 1 volta i provider selezionati", ma non ora.

**Fix**:
- [FxTable.svelte](frontend/src/lib/components/fx/FxTable.svelte) riga 241-250: aggiungere
  `filterable: false` alla colonna `providers`
- [AssetTable.svelte](frontend/src/lib/components/assets/AssetTable.svelte) riga 179-193:
  cambiare `type: 'enum'` → `type: 'text'`, rimuovere `enumOptions`, aggiungere
  `filterable: false`

**Stima**: 3 minuti

---

### H9 — Bottoni sync+open nel segnale FxPair: posizione errata

**Problema**: In [ChartSignalsSection.svelte](frontend/src/lib/components/charts/ChartSignalsSection.svelte),
quando un segnale è di tipo `fx-pair`, i bottoni Sync (⟳) e Open (↗) sono nel div header
(righe 303-323), accanto al cestino (🗑️). L'utente li vuole nella zona parametri, vicino
al selettore coppia e al bottone invert (↔), come se fossero azioni della coppia selezionata.

**Layout attuale**:
```
💱 Coppia FX                      [⟳] [↗] [🗑️]      ← header
[🔍 AUD-EUR ▾] [↔]                                    ← parametri
```

**Layout desiderato**:
```
💱 Coppia FX                                  [🗑️]   ← header
[🔍 AUD-EUR ▾] [↔] [⟳] [↗]                           ← parametri
```

**Fix** in [ChartSignalsSection.svelte](frontend/src/lib/components/charts/ChartSignalsSection.svelte):
1. Rimuovere i bottoni sync (righe 304-312) e open (righe 314-322) dal `div.flex.items-center.gap-0.5`
   nell'header (il div che contiene anche il cestino)
2. Aggiungerli DOPO il bottone invert `<ArrowLeftRight>` (riga 392) nella sezione parametri
   `configuredFxPairs`, dentro lo stesso `<div class="flex items-center gap-1">` del selettore
   coppia. Ordine: `[select] [↔ invert] [⟳ sync] [↗ open]`

**Stima**: 5 minuti

---

### H10 — `handleSyncPair` nel detail: toast non tradotto + nessun effetto

**Problema**: In [fx/[pair]/+page.svelte](frontend/src/routes/(app)/fx/[pair]/+page.svelte)
righe 402-417, la funzione `handleSyncPair(slug)` (chiamata dal pannello Segnali quando si
clicca Sync su un segnale FxPair) ha 2 bug:

1. **Toast non tradotto**: usa `fx.sync.toastSuccess` che **non esiste** — la chiave corretta
   è `fx.sync.toastOk`. Il toast mostra la chiave grezza come testo.

2. **Non legge la risposta API**: chiama `sync_rates` ma non legge `response.results[0]` per
   controllare lo status (ok/partial/skipped/failed). Mostra sempre success toast anche se
   la sync è fallita.

3. **Non fa refresh visivo**: dopo il sync, chiama `handleRefresh()` solo se `slug === data.canonicalSlug`
   ma non invalida lo store per il segnale esterno.

**Fix**: Riscrivere `handleSyncPair` seguendo il pattern di `handleSync` (righe 342-378):
```typescript
async function handleSyncPair(slug: string) {
    try {
        syncing = true;
        const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
            pairs: [slug], start: dateStart, end: dateEnd,
        });
        const r = (response as any)?.results?.[0];
        if (r) {
            const label = slug.replace('-', '/');
            const tr = get(t);
            if (r.status === 'ok') {
                toasts.success(tr('fx.sync.toastOk', {values: {pair: label, fetched: r.points_fetched ?? 0, changed: r.points_changed ?? 0, provider: r.provider_used ?? '?'}}));
            } else if (r.status === 'partial') {
                toasts.warning(tr('fx.sync.toastPartial', {values: {pair: label, changed: r.points_changed ?? 0}}));
            } else if (r.status === 'skipped') {
                toasts.info(tr('fx.sync.toastSkipped', {values: {pair: label}}));
            } else {
                toasts.error(tr('fx.sync.toastFailed', {values: {pair: label}}) + (r.message ? ': ' + r.message : ''));
            }
        }
        // Invalidate store + refresh if it's our pair
        const store = getFxStore(slug);
        store.invalidateRange(dateStart, dateEnd);
        if (slug === data.canonicalSlug) await handleRefresh();
    } catch (e: any) {
        toasts.error('Sync failed: ' + (e?.message || 'unknown'));
    } finally {
        syncing = false;
    }
}
```

**Stima**: 5 minuti

---

### H11 — FxPairSignal label: formato `A/B` → `🇦🇺 A → 🇪🇺 B`

**Problema**: In [FxPairSignal.ts](frontend/src/lib/charts/signals/FxPairSignal.ts) righe 88-94,
`getLabel()` restituisce il formato `AUD/EUR`. Ma nel pannello Misure, il segnale principale
mostra `🇬🇧 GBP → 🇵🇱 PLN` (con bandiere e →). Il segnale overlay mostra solo `● AUD/EUR`
che è visualmente incoerente.

**Fix**: Importare `getCurrencyInfo` da `$lib/stores/currencyStore` e cambiare `getLabel()`:
```typescript
getLabel(): string {
    const slug = String(this.params.pairSlug || '');
    const isInverted = Boolean(this.params._inverted);
    if (!slug) return 'FX Pair';
    const [a, b] = slug.split('-');
    const base = isInverted ? b : a;
    const quote = isInverted ? a : b;
    const baseFlag = getCurrencyInfo(base).flag_emoji;
    const quoteFlag = getCurrencyInfo(quote).flag_emoji;
    return `${baseFlag} ${base} → ${quoteFlag} ${quote}`;
}
```

Questo fix si propaga automaticamente a:
- **Pannello Segnali**: la label nel header del segnale
- **Tabella Misure**: la colonna "Signal" per i segnali overlay
- **Legenda chart**: il nome della serie nel tooltip

**Stima**: 3 minuti

---

### H12 — Bulk Sync Assets: placeholder → API reale

**Problema**: In [assets/+page.svelte](frontend/src/routes/(app)/assets/+page.svelte) riga 384,
`handleSyncAsset` è un placeholder:
```typescript
async function handleSyncAsset(asset: any) {
    // TODO: implement actual sync via POST /assets/prices/refresh
    console.log('Sync Asset clicked:', asset.id);
}
```

L'API backend è pronta: `POST /api/v1/assets/prices/refresh` (alias
`refresh_prices_bulk_api_v1_assets_prices_refresh_post`).

**Request body** (`FARefreshItem[]`):
```json
[{ "asset_id": 123, "date_range": { "start": "2026-01-01", "end": "2026-03-25" } }]
```

**Response** (`FABulkRefreshResponse`):
```json
{
  "results": [{ "asset_id": 123, "fetched_count": 90, "inserted_count": 85, "updated_count": 5, "errors": [] }],
  "success_count": 1
}
```

**Fix**:
```typescript
async function handleSyncAsset(asset: any) {
    try {
        const response = await zodiosApi.refresh_prices_bulk_api_v1_assets_prices_refresh_post([{
            asset_id: asset.id,
            date_range: { start: dateStart, end: dateEnd },
        }]);
        const r = (response as any)?.results?.[0];
        if (r && (!r.errors || r.errors.length === 0)) {
            toasts.success($t('assets.sync.toastOk', {
                values: { name: asset.display_name, fetched: r.fetched_count ?? 0 }
            }));
        } else {
            toasts.error($t('assets.sync.toastFailed', {
                values: { name: asset.display_name }
            }) + (r?.errors?.[0] ? ': ' + r.errors[0] : ''));
        }
        await fetchAllPriceData();
    } catch (e: any) {
        toasts.error($t('assets.sync.toastFailed', {
            values: { name: asset.display_name }
        }) + ': ' + (e?.message || 'unknown'));
    }
}
```

**Nuove chiavi i18n** da aggiungere:
| Chiave | EN | IT | FR | ES |
|--------|----|----|----|----|
| `assets.sync.toastOk` | `{name}: {fetched} prices synced` | `{name}: {fetched} prezzi sincronizzati` | `{name}: {fetched} prix synchronisés` | `{name}: {fetched} precios sincronizados` |
| `assets.sync.toastFailed` | `Sync failed for {name}` | `Sincronizzazione fallita per {name}` | `Échec de sync pour {name}` | `Sincronización fallida para {name}` |

**Nota**: `handleBulkSyncAssets` (riga 403) chiama `handleSyncAsset` in loop per ogni riga
selezionata con `has_provider` — funzionerà automaticamente una volta implementato il singolo.

**Stima**: 10 minuti (codice + i18n)

---

### H13 — Bulk Delete Assets: placeholder → API reale + ConfirmModal

**Problema**: In [assets/+page.svelte](frontend/src/routes/(app)/assets/+page.svelte) riga 394,
`handleDeleteAsset` è un placeholder:
```typescript
function handleDeleteAsset(asset: any) {
    // Placeholder — Step 3 will add delete confirm
    console.log('Delete Asset clicked:', asset.id);
}
```

L'API backend è pronta: `DELETE /api/v1/assets` (alias
`delete_assets_bulk_api_v1_assets_delete`).

**Request**: `DELETE /api/v1/assets?asset_ids=123`

**Response** (`FABulkAssetDeleteResponse`):
```json
{
  "results": [{ "asset_id": 123, "success": true, "message": "Asset deleted successfully" }],
  "success_count": 1,
  "failed_count": 0
}
```

**Fix**:
1. Aggiungere state per il dialog:
```typescript
let deleteDialogOpen = $state(false);
let deletingAsset: any = $state(null);
let deleteLoading = $state(false);
```

2. Riscrivere `handleDeleteAsset` per aprire il dialog:
```typescript
function handleDeleteAsset(asset: any) {
    deletingAsset = asset;
    deleteDialogOpen = true;
}
```

3. Aggiungere `confirmDeleteAsset`:
```typescript
async function confirmDeleteAsset() {
    if (!deletingAsset) return;
    deleteLoading = true;
    try {
        const response = await zodiosApi.delete_assets_bulk_api_v1_assets_delete({
            queries: { asset_ids: [deletingAsset.id] },
        });
        const r = (response as any)?.results?.[0];
        if (r?.success) {
            assets = assets.filter(a => a.id !== deletingAsset.id);
            toasts.success($t('assets.delete.toastOk', { values: { name: deletingAsset.display_name } }));
        } else {
            toasts.error(r?.message || $t('assets.delete.toastFailed', { values: { name: deletingAsset.display_name } }));
        }
    } catch (e: any) {
        toasts.error($t('assets.delete.toastFailed', { values: { name: deletingAsset.display_name } }));
    } finally {
        deleteLoading = false;
        deleteDialogOpen = false;
        deletingAsset = null;
    }
}
```

4. Aggiungere `ConfirmModal` nel template (dopo la filter bar):
```svelte
<ConfirmModal
    open={deleteDialogOpen}
    title={$t('common.confirmDelete')}
    message={$t('assets.delete.confirmMessage', { values: { name: deletingAsset?.display_name ?? '' } })}
    confirmText={$t('common.delete')}
    danger={true}
    loading={deleteLoading}
    onConfirm={confirmDeleteAsset}
    onCancel={() => { deleteDialogOpen = false; deletingAsset = null; }}
/>
```

5. Aggiornare `handleBulkDeleteAssets` per bulk:
```typescript
async function handleBulkDeleteAssets() {
    const ids = selectedAssetRows.map(r => r.id);
    if (ids.length === 0) return;
    try {
        const response = await zodiosApi.delete_assets_bulk_api_v1_assets_delete({
            queries: { asset_ids: ids },
        });
        const res = (response as any);
        const succeeded = res.results?.filter((r: any) => r.success).map((r: any) => r.asset_id) ?? [];
        assets = assets.filter(a => !succeeded.includes(a.id));
        if (succeeded.length > 0) {
            toasts.success($t('assets.delete.bulkOk', { values: { count: succeeded.length } }));
        }
        if (res.failed_count > 0) {
            toasts.warning($t('assets.delete.bulkPartial', { values: { failed: res.failed_count } }));
        }
    } catch (e: any) {
        toasts.error('Delete failed: ' + (e?.message || 'unknown'));
    } finally {
        assetTableComponent?.getTableRef()?.clearSelection();
        selectedAssetRows = [];
    }
}
```

**Nuove chiavi i18n** da aggiungere:
| Chiave | EN | IT | FR | ES |
|--------|----|----|----|----|
| `assets.delete.confirmMessage` | `Delete "{name}"? Provider assignments and price history will be removed.` | `Eliminare "{name}"? Assegnazioni provider e storico prezzi verranno rimossi.` | `Supprimer "{name}" ? Les assignations et l'historique seront supprimés.` | `¿Eliminar "{name}"? Las asignaciones y el historial serán eliminados.` |
| `assets.delete.toastOk` | `{name} deleted` | `{name} eliminato` | `{name} supprimé` | `{name} eliminado` |
| `assets.delete.toastFailed` | `Failed to delete {name}` | `Impossibile eliminare {name}` | `Échec de suppression de {name}` | `Error al eliminar {name}` |
| `assets.delete.bulkOk` | `{count} assets deleted` | `{count} asset eliminati` | `{count} actifs supprimés` | `{count} activos eliminados` |
| `assets.delete.bulkPartial` | `{failed} assets could not be deleted (have transactions)` | `{failed} asset non eliminabili (hanno transazioni)` | `{failed} actifs non supprimés (ont des transactions)` | `{failed} activos no eliminados (tienen transacciones)` |

**Import necessario**: Aggiungere `ConfirmModal` agli import se non già presente.

**Stima**: 15 minuti (codice + i18n + template)

---

## Ordine di Implementazione

| # | Step | Dipendenze | Stima |
|---|------|-----------|-------|
| 1 | **H1** — Rimuovere `title` dai bottoni 2×2 + ColumnVisibility | — | 2 min |
| 2 | **H2** — Soglie responsive | — | 2 min |
| 3 | **H3** — Fix layout tablet assets | — | 5 min |
| 4 | **H4** — Rinominare refresh → reload/ricarica | — | 5 min |
| 5 | **H5** — Rimuovere chiavi i18n orfane | — | 3 min |
| 6 | **H6** — Tradurre `'Sync'` in FxTable | — | 1 min |
| 7 | **H8** — Disabilitare filtro Provider | — | 3 min |
| 8 | **H9** — Spostare bottoni sync+open segnale FxPair | — | 5 min |
| 9 | **H10** — Fix `handleSyncPair` detail | — | 5 min |
| 10 | **H11** — FxPairSignal label con bandiere | — | 3 min |
| 11 | **H12** — Implementare `handleSyncAsset` | H4 (chiavi i18n) | 10 min |
| 12 | **H13** — Implementare `handleDeleteAsset` + ConfirmModal + bulk | H12 | 15 min |
| 13 | **H7** — Diagnostica provider chain (manuale con DevTools) | — | 10-15 min |

**Tempo totale stimato**: ~70 minuti

---

## Riepilogo Chiavi i18n da Aggiungere/Modificare

### Chiavi MODIFICATE (rename refresh → reload):

| Chiave | EN | IT | FR | ES |
|--------|----|----|----|----|
| `common.refresh` | Reload | Ricarica | Recharger | Recargar |
| `sharedResource.refreshAll` | Reload All | Ricarica Tutto | Recharger Tout | Recargar Todo |

### Chiavi AGGIUNTE:

| Chiave | EN | IT | FR | ES |
|--------|----|----|----|----|
| `assets.sync.toastOk` | `{name}: {fetched} prices synced` | `{name}: {fetched} prezzi sincronizzati` | `{name}: {fetched} prix synchronisés` | `{name}: {fetched} precios sincronizados` |
| `assets.sync.toastFailed` | `Sync failed for {name}` | `Sincronizzazione fallita per {name}` | `Échec de sync pour {name}` | `Sincronización fallida para {name}` |
| `assets.delete.confirmMessage` | `Delete "{name}"? Provider assignments and price history will be removed.` | `Eliminare "{name}"? Assegnazioni provider e storico prezzi verranno rimossi.` | `Supprimer "{name}" ? Les assignations et l'historique seront supprimés.` | `¿Eliminar "{name}"? Las asignaciones y el historial serán eliminados.` |
| `assets.delete.toastOk` | `{name} deleted` | `{name} eliminato` | `{name} supprimé` | `{name} eliminado` |
| `assets.delete.toastFailed` | `Failed to delete {name}` | `Impossibile eliminare {name}` | `Échec de suppression de {name}` | `Error al eliminar {name}` |
| `assets.delete.bulkOk` | `{count} assets deleted` | `{count} asset eliminati` | `{count} actifs supprimés` | `{count} activos eliminados` |
| `assets.delete.bulkPartial` | `{failed} assets could not be deleted (have transactions)` | `{failed} asset non eliminabili (hanno transazioni)` | `{failed} actifs non supprimés (ont des transactions)` | `{failed} activos no eliminados (tienen transacciones)` |

### Chiavi RIMOSSE:

| Chiave |
|--------|
| `assets.table.active` |
| `fx.editPairConfig` |

---

## Verifica Finale

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio/frontend && npx svelte-check --threshold error
# Atteso: 0 errori

cd /Users/ea_enel/Documents/00_My/LibreFolio && ./dev.py i18n audit
# Atteso: 0 chiavi unused, 0 missing
```

### Checklist verifica manuale post-implementazione

| # | Cosa verificare |
|---|----------------|
| 1 | Assets wide (≥1240): tutto in 1 riga, nessun overflow in FR |
| 2 | Assets tablet: datepicker ACCANTO ai filtri (2 righe), bottoni 2×2 a destra |
| 3 | Assets tablet-s: datepicker SOPRA i filtri, bottoni in colonna |
| 4 | Assets mobile (<500): tutto impilato, label spariscono a 460px |
| 5 | FX wide (≥1030): tutto in riga, nessun overflow in FR |
| 6 | FX mobile: label spariscono a 460px |
| 7 | Nessun `title` tooltip su bottoni 2×2 (assets+fx) né su ColumnVisibility |
| 8 | Lingua IT: "Ricarica" (non "Aggiorna"), "Ricarica Tutto" (non "Aggiorna Tutto") |
| 9 | Segnale FxPair: bottoni sync+open accanto al selettore coppia (non nel header) |
| 10 | Segnale FxPair: sync chiama API reale con toast tradotti (non raw key) |
| 11 | Segnale FxPair nel pannello Misure: label `🇦🇺 AUD → 🇪🇺 EUR` (non `AUD/EUR`) |
| 12 | Bulk Sync Assets: selezionare righe → Sync → API chiamata → toast con risultato |
| 13 | Bulk Delete Assets: selezionare righe → Delete → ConfirmModal → asset rimosso dalla lista |
| 14 | Delete singolo Asset: click delete nella row action → ConfirmModal → asset rimosso |
| 15 | FxTable: nessun filtro dropdown sulla colonna Provider |
| 16 | AssetTable: nessun filtro dropdown sulla colonna Provider |
| 17 | `./dev.py i18n audit`: 0 unused, 0 missing |

