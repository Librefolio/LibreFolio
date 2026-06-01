# Plan: LazyImage Client-Side Preview Cache

**Data**: 1 Giugno 2026
**Status**: ✅ DONE (2026-06-01)
**Priority**: P3 (ottimizzazione UX — no breaking)
**Tipo**: Independent mini-plan (frontend puro, no backend, no transazioni)

## 🤖 Modello Suggerito & Effort

| Parametro | Valore |
|-----------|--------|
| **Modello** | `claude-sonnet-4.6` (non Haiku: la migrazione Svelte 4→5 richiede più ragionamento) |
| **Effort stimato** | ~3-4h |
| **Difficoltà** | Media |
| **Rationale** | Due step extra rispetto al piano originale: migrazione Svelte 4→5 di LazyImage e FileGrid (vecchi remnants). La logica cache è semplice ma la migrazione dei componenti richiede attenzione ai pattern Svelte 5 del progetto. |

---

## 🎯 Obiettivo

Quando si passa da modalità **griglia** (preview `120x120`) a modalità **lista** (preview `48x48`)
nella pagina files, il browser fa nuove richieste HTTP per le stesse immagini a risoluzione inferiore.
Le URL differiscono: `?img_preview=120x120` vs `?img_preview=48x48`.

Il fix: una cache client-side che, prima di fare fetch, verifica se esiste già un'immagine
dello stesso file a risoluzione ≥ quella richiesta → riusa l'objectUrl già in memoria.

**Zero backend** — il server continua a servire le immagini normalmente.

---

## Stato Attuale (code-verified 2026-06-01)

| Componente | Stato | Note |
|---|---|---|
| `LazyImage.svelte` | ✅ Esiste, **Svelte 4** (vecchio remnant) | Solo `<img src={url}>` — nessun fetch interno |
| `FileGrid.svelte` | ✅ Esiste, **Svelte 4** (vecchio remnant) | Usa `LazyImage` con `src={file.url + ?img_preview=120x120}` |
| `FilesTable.svelte` | ✅ Esiste, **Svelte 5** | DataTable cell `type:'image'` con `src: file.url + ?img_preview=48x48` |
| Cache client-side | ❌ Non esiste | |
| `AssetPickerModal.svelte` | Svelte 4 remnant | Usa LazyImage con `src` diretto — fuori scope |
| `BrokerSharingModal.svelte` | Svelte 4 remnant | Usa LazyImage con `src` diretto — fuori scope |

### API URL reale
`file.url` = `/api/v1/uploads/file/{id}` → preview: `${file.url}?img_preview=WxH`

---

## Decisioni Architetturali

### ❌ No Ref Counting (rimosso dal piano originale)
Il piano originale includeva `incrementRef`/`decrementRef`. Crea un conflitto critico:
- Grid view (LazyImage) distrutto → `decrementRef` → `revokeObjectURL` quando count=0
- List view (DataTable) usa lo stesso objectUrl come plain `src` → **già revocato, immagine rotta!**

**Decisione**: cache tiene gli objectUrl per tutta la vita della pagina. Memory: ~2MB per 100 immagini — accettabile (verificato nel piano originale). `clearImagePreviewCache()` per cleanup al logout.

### Props cache: `fileId` + `previewUrl` (non `previewSize`)
Invece di `fileId`+`previewSize` (richiederebbe hardcodare il pattern URL in LazyImage),
usiamo `fileId` + `previewUrl` (URL completa, es. `${file.url}?img_preview=120x120`).
La larghezza viene parsata dal query param. La costruzione dell'URL resta in FileGrid.

---

## Step 1 — Creare `imagePreviewCache.ts` ✅ (2026-06-01)

> **Note implementazione**: Creato con `cachePreview`, `getCachedPreview`, `parsePreviewWidth` (helper per estrarre width da URL), `clearImagePreviewCache`. Tab indentation per coerenza con progetto.

**Path**: `frontend/src/lib/stores/imagePreviewCache.ts`

Plain `.ts` (non `.svelte.ts`) — nessuna reattività Svelte necessaria, solo un Map:

```typescript
/**
 * imagePreviewCache — Client-side cache for image preview objectUrls.
 *
 * Stores the highest-resolution fetched objectUrl per fileId.
 * When a lower resolution is requested, the cached version is reused
 * and CSS object-fit handles the visual downscaling.
 * objectUrls are held for page lifetime (~2MB for 100 images — acceptable).
 *
 * @module stores/imagePreviewCache
 */

interface CachedPreview {
    /** objectUrl created from blob */
    objectUrl: string;
    /** The pixel width of the fetched image (e.g. 120 for "120x120") */
    maxWidth: number;
}

const cache = new Map<string, CachedPreview>();

/**
 * Register a fetched image in the cache.
 * Only updates if the new resolution is higher than what's stored.
 */
export function cachePreview(fileId: string, objectUrl: string, width: number): void {
    const existing = cache.get(fileId);
    if (!existing || width > existing.maxWidth) {
        if (existing) URL.revokeObjectURL(existing.objectUrl);
        cache.set(fileId, { objectUrl, maxWidth: width });
    }
}

/**
 * Look up a cached preview. Returns objectUrl if cached width >= requestedWidth, else null.
 */
export function getCachedPreview(fileId: string, requestedWidth: number): string | null {
    const cached = cache.get(fileId);
    return cached && cached.maxWidth >= requestedWidth ? cached.objectUrl : null;
}

/** Free all blob memory. Call on logout. */
export function clearImagePreviewCache(): void {
    for (const entry of cache.values()) URL.revokeObjectURL(entry.objectUrl);
    cache.clear();
}
```

---

## Step 2 — Migrare + aggiornare `LazyImage.svelte` → Svelte 5 ✅ (2026-06-01)

> **Note implementazione**: Riscrittura completa Svelte 4→5. Aggiunto `parsePreviewWidth` helper nel cache store. Due `$effect`: uno per normal mode (sync src), uno per cache mode (fetch+blob+objectUrl). AbortController nel cleanup. Template usa `onload`/`onerror` (Svelte 5). Backward compat mantenuta — caller con solo `src` funzionano identicamente.

**Path**: `frontend/src/lib/components/ui/media/LazyImage.svelte`

Attualmente **Svelte 4** (vecchio remnant). Riscrivere in Svelte 5 runes + aggiungere cache mode.

### Props interface (nuova):
```typescript
interface Props {
    src?: string;        // Modalità normale: URL diretta (backward compat)
    alt?: string;
    fallback?: string;
    placeholder?: 'generic' | 'avatar' | 'broker' | 'icon';
    width?: string;
    height?: string;
    rounded?: boolean;
    circle?: boolean;
    // Modalità cache (entrambi richiesti):
    fileId?: string;     // Chiave cache (UploadedFile.id)
    previewUrl?: string; // URL completa es. `${file.url}?img_preview=120x120`
}
```

### Logica:

**Modalità normale** (`src` presente, no `fileId`/`previewUrl`):
- `$effect` che watch `src` → reset `loaded`/`error`
- Template usa `resolvedSrc` (= `src`)
- Comportamento identico a prima per tutti i caller esistenti

**Modalità cache** (`fileId && previewUrl` entrambi presenti):
- Parsare larghezza da `?img_preview=WxH` in `previewUrl`
- `$effect`: chiama `getCachedPreview(fileId, width)`
  - Se hit: `resolvedSrc = cachedObjectUrl`
  - Se miss: `fetch(previewUrl)` → blob → `URL.createObjectURL` → `cachePreview` → `resolvedSrc = url`
- AbortController nel cleanup del `$effect` per fetch in corso

### Svelte 4 → 5 migration:
- `export let` → `interface Props` + `$props()`
- `let loaded = false` → `let loaded = $state(false)`
- `$: placeholderDataUrl = ...` → `const placeholderDataUrl = $derived(...)`
- `$: containerClass = ...` → `const containerClass = $derived(...)`
- `$: if (src !== previousSrc)` → `$effect(() => { ... })`
- `on:load={onLoad}` → `onload={handleLoad}`
- `on:error={onError}` → `onerror={handleError}`
- Rimuovere `previousSrc` (non più necessario con `$effect`)

---

## Step 3 — Migrare + aggiornare `FileGrid.svelte` → Svelte 5 ✅ (2026-06-01)

> **Note implementazione**: Full migration: `$props()`, callback props (`onselect`, `ondblselect`, `ondelete`, `oncopyLink`), `$state`, `$derived`, `onclick`/`ondblclick`. LazyImage usa `fileId` + `previewUrl`. Aggiornati i 2 caller: `files/+page.svelte` e `AssetPickerModal.svelte` (da `on:delete={(e) => e.detail.id}` a `ondelete={(e) => e.id}`).

**Path**: `frontend/src/lib/components/files/FileGrid.svelte`

Attualmente **Svelte 4** (vecchio remnant). Migrare + usare LazyImage in cache mode.

### Svelte 4 → 5 migration:
| Prima (Svelte 4) | Dopo (Svelte 5) |
|---|---|
| `export let files: UploadedFile[] = []` | `interface Props { files?: UploadedFile[] }` + `$props()` |
| `createEventDispatcher<{...}>()` + `dispatch(...)` | Callback props: `onselect?`, `ondblselect?`, `ondelete?`, `oncopyLink?` |
| `$: filteredFiles = ...` | `const filteredFiles = $derived(...)` |
| `on:click={...}` | `onclick={...}` |
| `on:click\|stopPropagation` | `onclick={(e) => { e.stopPropagation(); ... }}` |

### Cache mode per LazyImage:
```svelte
<!-- Prima -->
<LazyImage src={getPreviewUrl(file, cardSize === 'compact' ? '120x120' : previewSize)} .../>

<!-- Dopo -->
<LazyImage fileId={file.id} previewUrl={getPreviewUrl(file, cardSize === 'compact' ? '120x120' : previewSize)} .../>
```

`getPreviewUrl` resta come helper locale (costruisce la stringa URL).

---

## Step 4 — Aggiornare `FilesTable.svelte` ✅ (2026-06-01)

> **Note implementazione**: Import `getCachedPreview`, usato nel cell renderer image. Se cache hit → objectUrl usato direttamente, altrimenti fallback alla URL originale. Build OK, svelte-check passa (errori solo pre-esistenti in fxStoreRegistry.test.ts).

**Path**: `frontend/src/lib/components/files/FilesTable.svelte`

Già Svelte 5. Aggiungere solo la lettura dalla cache nel cell renderer.

Il DataTable `type:'image'` cell renderizza `<img src={...}>` direttamente (no lifecycle).
Lettura sincrona della cache nella cell function — funziona perché la cache è già popolata
quando l'utente passa da grid → list.

**Modifiche**:
1. Import `getCachedPreview` da `$lib/stores/imagePreviewCache`
2. In `getColumns()` → image cell:
```typescript
const f = row as UploadedFile;
const cached = getCachedPreview(f.id, 48);
return {
    type: 'image',
    src: cached ?? getPreviewUrl(row),  // objectUrl se in cache, altrimenti URL
    alt: getFileName(row),
    text: getFileName(row),
    fallbackIcon: ImageIcon,
    size: 32,
};
```

**Timing**: `$derived(getColumns())` si ricalcola a ogni render. Dopo switch grid→list, la cache
è già popolata → hit sincrono funziona ✅.

---

## Comportamento Atteso

1. Grid (120x120) → fetch backend → cache entry `{objectUrl, maxWidth: 120}`
2. Passa a List (48x48) → `getCachedPreview(id, 48)` → `120 >= 48` ✅ → objectUrl cached
3. CSS `object-fit: cover` gestisce il ridimensionamento visuale
4. **0 nuove richieste HTTP** per thumbnail già viste in grid

---

## File Coinvolti

| File | Modifica |
|------|----------|
| `frontend/src/lib/stores/imagePreviewCache.ts` | **NUOVO** — cache |
| `frontend/src/lib/components/ui/media/LazyImage.svelte` | **Svelte 4→5** + cache mode (explicit + auto-detect) |
| `frontend/src/lib/components/files/FileGrid.svelte` | **Svelte 4→5** + usa cache mode |
| `frontend/src/lib/components/files/FilesTable.svelte` | Legge cache nel cell renderer |
| `frontend/src/lib/components/ui/media/AssetPickerModal.svelte` | Aggiornato caller (callback props Svelte 5) |
| `frontend/src/routes/(app)/files/+page.svelte` | Aggiornato caller (callback props Svelte 5) |

**Non modificati**: DataTable.svelte, types.ts, BrokerSharingModal.svelte

---

## Pending (fuori scope, da fare separatamente)

| File | Issue |
|---|---|
| `AssetPickerModal.svelte` | Svelte 4 remnant — usa LazyImage con `src` diretto, funziona ancora |
| `BrokerSharingModal.svelte` | Svelte 4 remnant — stessa situazione |
