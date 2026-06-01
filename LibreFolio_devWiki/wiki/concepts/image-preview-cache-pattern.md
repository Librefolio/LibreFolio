---
title: "Image Preview Cache Pattern"
category: concept
tags: [frontend, images, cache, performance, objecturl, lazy-loading]
related: [features/F-086, concepts/timeseries-store-pattern]
---

# Concept: Image Preview Cache Pattern

## Definition

A client-side `Map<fileId, {objectUrl, maxWidth}>` that caches fetched image preview blobs for the page lifetime. When a lower-resolution preview is requested for an already-cached file, the higher-resolution cached objectUrl is reused — CSS `object-fit` handles visual downscaling.

## Where It Applies

`frontend/src/lib/stores/imagePreviewCache.ts` — used by `LazyImage.svelte` in cache mode (when `fileId` + `previewUrl` props are provided).

## Key Design Decisions

1. **No ref counting** — objectUrls held until page unload or explicit `clearImagePreviewCache()` on logout. Rationale: ref counting + `revokeObjectURL` causes broken images when the same objectUrl is shared between Grid view (LazyImage) and Table view (DataTable cell).
2. **Size-based reuse** — cache stores the pixel width of the fetched preview. If `cachedWidth >= requestedWidth`, the existing objectUrl is returned without network fetch.
3. **Memory budget** — ~2MB for 100 images (acceptable for a files page).

## API

```typescript
cachePreview(fileId: string, objectUrl: string, width: number): void
getCachedPreview(fileId: string, requestedWidth: number): string | null
clearImagePreviewCache(): void  // call on logout
```

## Source files

| Role | Path |
|------|------|
| Cache store | `frontend/src/lib/stores/imagePreviewCache.ts` |
| LazyImage (Svelte 5) | `frontend/src/lib/components/ui/media/LazyImage.svelte` |
| Source plan | `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-LazyImageCache.prompt.md` |
