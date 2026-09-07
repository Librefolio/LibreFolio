<script lang="ts">
    import {BookOpen, HelpCircle} from 'lucide-svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import Tooltip from './feedback/Tooltip.svelte';

    /** MkDocs path (relative to /mkdocs/) */
    export let path: string;
    /** Localized fallback used when the requested page exists only in English */
    export let localizedFallbackPath: string | undefined = undefined;
    /** Tooltip label shown on hover (may contain $...$ LaTeX) */
    export let label: string = 'Documentation';
    /** Icon size in pixels */
    export let size: number = 12;
    /** Enable KaTeX math rendering in tooltip */
    export let math: boolean = false;
    /** Icon variant */
    export let icon: 'help' | 'book' = 'help';
    /** Stable E2E selector */
    export let testId: string | undefined = undefined;

    function getDocsUrl(): string {
        const lang = $currentLanguage;
        const prefix = lang !== 'en' ? `${lang}/` : '';
        const resolvedPath = lang !== 'en' && localizedFallbackPath ? localizedFallbackPath : path;
        return `/mkdocs/${prefix}${resolvedPath}`;
    }
</script>

<Tooltip {math} interactiveChild maxWidth="320px" position="top" text={label}>
    <button class="rounded p-0.5 text-gray-400 transition-colors hover:text-libre-green focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70" onclick={() => window.open(getDocsUrl(), '_blank', 'noopener')} type="button" aria-label={label} data-testid={testId}>
        {#if icon === 'book'}
            <BookOpen {size} aria-hidden="true" />
        {:else}
            <HelpCircle {size} aria-hidden="true" />
        {/if}
    </button>
</Tooltip>
