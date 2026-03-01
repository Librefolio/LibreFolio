<script lang="ts">
    /**
     * LazyImage - Image loading with placeholder and fallback
     *
     * Features:
     * - Shows SVG placeholder while loading
     * - Lazy loads actual image
     * - Handles errors with fallback image
     * - Smooth fade-in transition
     */

    export let src: string;
    export let alt: string = '';
    export let fallback: string = '';  // Fallback image URL
    export let placeholder: 'generic' | 'avatar' | 'broker' | 'icon' = 'generic';
    export let width: string = '100%';
    export let height: string = '100%';
    export let rounded: boolean = false;
    export let circle: boolean = false;

    let loaded = false;
    let error = false;
    let imgElement: HTMLImageElement;
    let previousSrc = src;

    // Reset state when src changes
    $: if (src !== previousSrc) {
        loaded = false;
        error = false;
        previousSrc = src;
    }

    // Placeholder SVGs
    const placeholders = {
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
        </svg>`
    };

    function onLoad() {
        loaded = true;
    }

    function onError() {
        error = true;
        if (fallback && imgElement) {
            imgElement.src = fallback;
        }
    }

    // Encode SVG for use as data URL
    $: placeholderDataUrl = `data:image/svg+xml,${encodeURIComponent(placeholders[placeholder])}`;

    // Classes for container
    $: containerClass = [
        'lazy-image-container',
        rounded ? 'rounded-lg' : '',
        circle ? 'rounded-full' : '',
        'overflow-hidden'
    ].filter(Boolean).join(' ');
</script>

<div class={containerClass} style="width: {width}; height: {height};">
    {#if !loaded && !error}
        <img
                src={placeholderDataUrl}
                {alt}
                class="placeholder-img"
        />
    {/if}

    <img
            {alt}
            bind:this={imgElement}
            class="actual-img"
            class:hidden={!loaded && !error}
            class:loaded
            on:error={onError}
            on:load={onLoad}
            src={src}
    />
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

