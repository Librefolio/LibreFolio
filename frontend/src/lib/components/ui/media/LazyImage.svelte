<script lang="ts">
    /**
     * LazyImage - Image loading with placeholder, fallback, and optional preview cache.
     *
     * Two modes:
     * - Normal: pass `src` — renders <img> with lazy loading placeholder.
     * - Cache-aware: pass `fileId` + `previewUrl` — fetches as blob, caches objectUrl,
     *   reuses higher-res cached previews for lower-res requests.
     */

    import {cachePreview, extractFileIdFromUrl, getCachedPreview, parsePreviewWidth} from '$lib/stores/imagePreviewCache';

    interface Props {
        /** Normal mode: direct image URL */
        src?: string;
        alt?: string;
        fallback?: string;
        placeholder?: 'generic' | 'avatar' | 'broker' | 'icon';
        width?: string;
        height?: string;
        rounded?: boolean;
        circle?: boolean;
        /** Cache mode: file UUID (both fileId and previewUrl required) */
        fileId?: string;
        /** Cache mode: full preview URL e.g. `${file.url}?img_preview=120x120` */
        previewUrl?: string;
    }

    let {src = '', alt = '', fallback = '', placeholder = 'generic', width = '100%', height = '100%', rounded = false, circle = false, fileId, previewUrl}: Props = $props();

    let loaded = $state(false);
    let error = $state(false);
    let imgElement: HTMLImageElement | undefined = $state(undefined);
    let resolvedSrc = $state('');

    // Determine if we're in cache mode
    const cacheMode = $derived(!!(fileId && previewUrl));

    // Placeholder SVGs
    const placeholders: Record<string, string> = {
        generic: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
            <rect width="100" height="100" fill="#e5e7eb"/>
            <path d="M30 65 L50 40 L70 65" stroke="#9ca3af" stroke-width="3" fill="none"/>
            <circle cx="35" cy="35" r="8" fill="#9ca3af"/>
        </svg>`,
        avatar: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
            <rect width="100" height="100" fill="#e5e7eb"/>
            <circle cx="50" cy="35" r="18" fill="#9ca3af"/>
            <ellipse cx="50" cy="85" rx="30" ry="25" fill="#9ca3af"/>
        </svg>`,
        broker: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
            <rect width="100" height="100" fill="#e5e7eb"/>
            <rect x="20" y="25" width="60" height="50" rx="5" stroke="#9ca3af" stroke-width="3" fill="none"/>
            <path d="M35 50 h30 M35 60 h20" stroke="#9ca3af" stroke-width="3"/>
        </svg>`,
        icon: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
            <rect width="100" height="100" fill="#e5e7eb" rx="10"/>
            <circle cx="50" cy="50" r="25" stroke="#9ca3af" stroke-width="3" fill="none"/>
        </svg>`,
    };

    const placeholderDataUrl = $derived(`data:image/svg+xml,${encodeURIComponent(placeholders[placeholder])}`);

    const containerClass = $derived(['lazy-image-container', rounded ? 'rounded-lg' : '', circle ? 'rounded-full' : '', 'overflow-hidden'].filter(Boolean).join(' '));

    // Normal mode: auto-detect preview URLs for caching, or plain src passthrough
    $effect(() => {
        if (cacheMode) return;

        // Try auto-detect: if src is a preview URL, use blob cache
        const detectedFileId = src ? extractFileIdFromUrl(src) : null;
        const detectedWidth = src ? parsePreviewWidth(src) : 0;

        if (detectedFileId && detectedWidth > 0) {
            // Auto-detected preview URL → use cache logic
            loaded = false;
            error = false;

            const cached = getCachedPreview(detectedFileId, detectedWidth);
            if (cached) {
                resolvedSrc = cached;
                loaded = true;
                return;
            }

            const controller = new AbortController();
            fetch(src, {signal: controller.signal})
                .then((r) => {
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    return r.blob();
                })
                .then((blob) => {
                    if (controller.signal.aborted) return;
                    const objectUrl = URL.createObjectURL(blob);
                    cachePreview(detectedFileId, objectUrl, detectedWidth);
                    resolvedSrc = objectUrl;
                })
                .catch(() => {
                    if (controller.signal.aborted) return;
                    error = true;
                });

            return () => {
                controller.abort();
            };
        }

        // Plain mode: no caching, just pass src through
        resolvedSrc = src;
        loaded = false;
        error = false;
    });

    // Cache mode: check cache first, then fetch as blob
    $effect(() => {
        if (!cacheMode) return;

        const currentFileId = fileId!;
        const currentPreviewUrl = previewUrl!;
        const requestedWidth = parsePreviewWidth(currentPreviewUrl);

        // Reset state for new image
        loaded = false;
        error = false;

        // Check cache
        const cached = getCachedPreview(currentFileId, requestedWidth);
        if (cached) {
            resolvedSrc = cached;
            loaded = true;
            return;
        }

        // Fetch from backend as blob
        const controller = new AbortController();
        fetch(currentPreviewUrl, {signal: controller.signal})
            .then((r) => {
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                return r.blob();
            })
            .then((blob) => {
                if (controller.signal.aborted) return;
                const objectUrl = URL.createObjectURL(blob);
                cachePreview(currentFileId, objectUrl, requestedWidth);
                resolvedSrc = objectUrl;
            })
            .catch(() => {
                if (controller.signal.aborted) return;
                error = true;
            });

        return () => {
            controller.abort();
        };
    });

    function handleLoad() {
        loaded = true;
    }

    function handleError() {
        error = true;
        if (fallback && imgElement) {
            imgElement.src = fallback;
        }
    }
</script>

<div class={containerClass} style="width: {width}; height: {height};">
    {#if !loaded && !error}
        <img src={placeholderDataUrl} {alt} class="placeholder-img" />
    {/if}

    <img {alt} bind:this={imgElement} class="actual-img" class:hidden={!loaded && !error} class:loaded onerror={handleError} onload={handleLoad} src={resolvedSrc} />
</div>

<style>
    .lazy-image-container {
        position: relative;
        display: block;
        /* Transparent background to avoid border in dark mode */
        background-color: transparent;
    }

    .placeholder-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .actual-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
    }

    .actual-img.loaded {
        opacity: 1;
    }

    .actual-img.hidden {
        position: absolute;
        top: 0;
        left: 0;
    }
</style>
