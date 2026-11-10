<!--
  ViewModeToggle — Reusable grid/list toggle with per-user localStorage persistence.
  Svelte 5 runes, dark mode support.
  Used by: /assets, /fx list pages
-->
<script lang="ts">
    import {LayoutGrid, List} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
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

<!-- Each button says what it does in the design system's tooltip; a click is the button's own, so it stops before the tooltip's click, which would pin the hint over the list that is redrawn. -->
<div class="flex rounded-lg border border-lf-subtle text-lf-primary overflow-hidden">
    <Tooltip text={$t('sharedResource.viewGrid')} position="bottom" interactiveChild testId="view-mode-grid-tooltip">
        <button
            aria-label={$t('sharedResource.viewGrid')}
            aria-pressed={mode === 'grid'}
            data-testid="view-mode-grid"
            class="flex items-center justify-center px-2.5 py-1.5 transition-colors
                   {mode === 'grid' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
            onclick={(event) => {
                event.stopPropagation();
                setMode('grid');
            }}
        >
            <LayoutGrid size={16} />
        </button>
    </Tooltip>
    <Tooltip text={$t('sharedResource.viewTable')} position="bottom" interactiveChild testId="view-mode-list-tooltip">
        <button
            aria-label={$t('sharedResource.viewTable')}
            aria-pressed={mode === 'list'}
            data-testid="view-mode-list"
            class="flex items-center justify-center px-2.5 py-1.5 transition-colors
                   {mode === 'list' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
            onclick={(event) => {
                event.stopPropagation();
                setMode('list');
            }}
        >
            <List size={16} />
        </button>
    </Tooltip>
</div>
