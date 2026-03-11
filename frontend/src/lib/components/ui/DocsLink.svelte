<!--
  DocsLink.svelte - Reusable documentation link button.
  Shows a small HelpCircle (?) icon that:
  - On hover: displays a Tooltip with the provided label
  - On click: opens the MkDocs page at /docs/{path} in a new tab
-->
<script lang="ts">
    import {HelpCircle} from 'lucide-svelte';
    import Tooltip from './Tooltip.svelte';

    /** MkDocs path (relative to /docs/) */
    export let path: string;
    /** Tooltip label shown on hover (may contain $...$ LaTeX) */
    export let label: string = 'Documentation';
    /** Icon size in pixels */
    export let size: number = 12;
    /** Enable KaTeX math rendering in tooltip */
    export let math: boolean = false;
</script>

<Tooltip text={label} position="top" maxWidth="320px" {math}>
    <button
        type="button"
        class="p-0.5 rounded text-gray-400 hover:text-libre-green transition-colors"
        onclick={() => window.open("/docs/" + path, '_blank')}
    >
        <HelpCircle {size} />
    </button>
</Tooltip>
