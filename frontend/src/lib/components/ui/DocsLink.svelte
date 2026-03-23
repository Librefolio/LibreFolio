<script lang="ts">
    import {HelpCircle} from 'lucide-svelte';
    import Tooltip from './Tooltip.svelte';

    /** MkDocs path (relative to /mkdocs/) */
    export let path: string;
    /** Tooltip label shown on hover (may contain $...$ LaTeX) */
    export let label: string = 'Documentation';
    /** Icon size in pixels */
    export let size: number = 12;
    /** Enable KaTeX math rendering in tooltip */
    export let math: boolean = false;

    /**
     * Build the MkDocs URL with locale prefix if the current app language
     * is not English, so docs open in the correct language.
     */
    function getDocsUrl(): string {
        const lang = localStorage.getItem('librefolio-locale') || 'en';
        const prefix = lang !== 'en' ? `${lang}/` : '';
        return `/mkdocs/${prefix}${path}`;
    }
</script>

<Tooltip text={label} position="top" maxWidth="320px" {math}>
    <button
        type="button"
        class="p-0.5 rounded text-gray-400 hover:text-libre-green transition-colors"
        onclick={() => window.open(getDocsUrl(), '_blank')}
    >
        <HelpCircle {size} />
    </button>
</Tooltip>
