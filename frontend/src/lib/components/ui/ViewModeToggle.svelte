<!--
  ViewModeToggle — Reusable grid/list toggle with per-user localStorage persistence.
  Svelte 5 runes, dark mode support.
  Used by: /assets, /fx list pages
-->
<script lang="ts">
    import {LayoutGrid, List} from 'lucide-svelte';
    import {getUserStorage, setUserStorage} from '$lib/utils/storage';

    interface Props {
        /** Current view mode */
        mode: 'grid' | 'list';
        /** Base key for localStorage persistence (will be user-scoped) */
        storageKey: string;
        /** Callback when mode changes */
        onchange?: (mode: 'grid' | 'list') => void;
    }

    let {mode = $bindable('grid'), storageKey, onchange}: Props = $props();

    // Load initial value from localStorage on mount
    $effect(() => {
        const stored = getUserStorage(storageKey, 'grid') as 'grid' | 'list';
        if (stored === 'grid' || stored === 'list') {
            mode = stored;
        }
    });

    function setMode(newMode: 'grid' | 'list') {
        mode = newMode;
        setUserStorage(storageKey, newMode);
        onchange?.(newMode);
    }
</script>

<div class="flex rounded-lg border border-lf-subtle text-lf-primary overflow-hidden">
    <button
        aria-label="Grid view"
        data-testid="view-mode-grid"
        class="flex items-center justify-center px-2.5 py-1.5 transition-colors
               {mode === 'grid' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
        onclick={() => setMode('grid')}
        title="Grid view"
    >
        <LayoutGrid size={16} />
    </button>
    <button
        aria-label="Table view"
        data-testid="view-mode-list"
        class="flex items-center justify-center px-2.5 py-1.5 transition-colors
               {mode === 'list' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
        onclick={() => setMode('list')}
        title="Table view"
    >
        <List size={16} />
    </button>
</div>
