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

<div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
    <button
        aria-label="Grid view"
        class="flex items-center justify-center px-2.5 py-1.5 transition-colors
               {mode === 'grid' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
        onclick={() => setMode('grid')}
        title="Grid view"
    >
        <LayoutGrid size={16} />
    </button>
    <button
        aria-label="Table view"
        class="flex items-center justify-center px-2.5 py-1.5 transition-colors
               {mode === 'list' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
        onclick={() => setMode('list')}
        title="Table view"
    >
        <List size={16} />
    </button>
</div>
