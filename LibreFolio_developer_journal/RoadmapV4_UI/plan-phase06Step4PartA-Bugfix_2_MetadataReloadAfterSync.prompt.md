# Plan: Fix metadata stale dopo sync — Asset Detail Page

Dopo una sync (`handleSync`), i dati metadata (come `last_fetch_at`, `has_metadata`, classification) non vengono ricaricati perché `handleRefresh()` ricarica solo i dati del grafico. La fix richiede che `handleSync` ri-fetchi anche le info asset e provider assignment, e — se `has_metadata` diventa `true` — ricarichi anche i dati di classificazione.

---

## Bug Analysis

**Sintomo**: dopo aver premuto "Sync" sulla detail page, la sezione metadata continua a mostrare "never fetched" finché non si fa F5.

**Root cause** in `frontend/src/routes/(app)/assets/[id]/+page.svelte`:

1. **`handleSync()`** (riga 430) → chiama `handleRefresh()` (riga 450)
2. **`handleRefresh()`** (riga 425) → chiama **solo** `loadChartData()` + `overlayDataVersion++`
3. **`loadProviderAssignment()`** e **`loadAssetInfo()`** vengono chiamate **solo in `onMount()`** (riga 264) e in `handleAssetUpdated()` (riga 481, ma solo dopo il modale)

Quindi `providerAssignment.last_fetch_at` e `assetInfo.has_metadata` non vengono mai aggiornati dopo una sincronizzazione.

---

## Steps

### Step 1 — Estrarre helper `reloadMetadata()` ✅

In `+page.svelte`, sezione Actions (dopo `handleRefresh`, riga ~428), creare:

```typescript
async function reloadMetadata() {
    await Promise.all([loadAssetInfo(), loadProviderAssignment()]);
    // Update provider icon if changed
    if (assetInfo?.provider_code) {
        providerIconUrl = getAssetProviderIconUrl(assetInfo.provider_code);
    }
    // Reload classification if metadata became available
    if (assetInfo?.has_metadata && !sectorDistribution && !geographicDistribution) {
        await loadClassificationData();
    }
}
```

### Step 2 — Chiamare `reloadMetadata()` in `handleSync()` ✅

Modificare `handleSync()`: dopo `await handleRefresh()` (riga 450), aggiungere `await reloadMetadata()`.

```typescript
async function handleSync() {
    syncing = true;
    try {
        // ...existing sync API call...
        await handleRefresh();
        await reloadMetadata();  // ← NEW
    } catch (e: any) {
        // ...existing error handling...
    } finally {
        syncing = false;
    }
}
```

### Step 3 — Semplificare `handleAssetUpdated()` ✅

`handleAssetUpdated()` (riga 481) già chiama `loadAssetInfo()` + `loadProviderAssignment()` manualmente. Sostituire con `reloadMetadata()` per evitare duplicazione:

```typescript
async function handleAssetUpdated() {
    editModalOpen = false;
    await reloadMetadata();
    if (providerAssignment) {
        await handleSync();
    } else {
        await handleRefresh();
    }
}
```

**Nota**: `handleSync` ora chiama già `reloadMetadata()`, ma la chiamata in `handleAssetUpdated` è necessaria PRIMA del check `if (providerAssignment)` — serve avere i dati aggiornati per decidere se sincronizzare.

### Step 4 — Semplificare `onMount()` ⏭️ Skipped (nessuna modifica, come da piano)

La logica post-load in `onMount()` (righe 274-281) che aggiorna `providerIconUrl` e carica classification è ora duplicata con `reloadMetadata()`. Sostituire:

```typescript
onMount(async () => {
    await Promise.all([
        ensureCurrenciesLoaded(get(currentLanguage)),
        ensureAssetProvidersCached(),
        loadAssetInfo(),
        loadProviderAssignment(),
        loadChartData(),
        loadFxPairSlugs(),
        loadAssetList(),
    ]);
    // Resolve derived metadata (icon, classification)
    if (assetInfo?.provider_code) {
        providerIconUrl = getAssetProviderIconUrl(assetInfo.provider_code);
    }
    if (assetInfo?.has_metadata) {
        await loadClassificationData();
    }
});
```

Questo rimane identico — `reloadMetadata()` è per i reload successivi, `onMount` fa il caricamento iniziale con le stesse fetch già in parallelo. Non toccare `onMount` per evitare regressioni.

---

## Further Considerations

1. **Nessun impatto backend** — il bug è puramente frontend, non servono nuovi endpoint.
2. **`handleAssetUpdated` chiama `handleSync` se c'è un provider** (riga 485-486) — con `reloadMetadata()` sia in `handleAssetUpdated` che in `handleSync`, la seconda chiamata è idempotente (stesse GET, nessun side effect). Costo: 2 GET extra ma garantisce dati freschi.
3. **Traduzione nazioni**: NON usare i18n frontend. Il backend Python con `babel` gestisce già il mapping dei nomi nazione. Se serve, creare un endpoint backend dedicato per il remapping ISO→nome localizzato, ma probabilmente non è necessario.
4. **Svelte 5**: la migrazione è già in atto (runes `$state`, `$derived`, `$effect`). Nessun blocco.

---

## Ordine di Esecuzione

1. Step 1 → Step 2 (fix principale)
2. Step 3 (refactor `handleAssetUpdated`)
3. Step 4 → skip (onMount resta com'è)

Dopo tutti gli step: verificare manualmente che dopo sync la sezione Provider mostri la data `last_fetch_at` aggiornata senza F5.

