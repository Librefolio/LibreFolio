<!--
  ViewModeToggle — a segmented toggle of view modes, each an icon (and, when asked, a label), with the design system's tooltip.
  Svelte 5 runes, colour roles.

  Without `options` it is the grid/list toggle of the /assets and /fx list pages, persisted per user in localStorage under
  `storageKey`. With `options` it toggles any set of modes (project 74: the Positions panel's «Globale / Broker»); the
  caller may then own the persistence (no `storageKey`), so that the mode is known before the first request.
-->
<script lang="ts" module>
    import type {ComponentType} from 'svelte';

    export interface ViewModeOption {
        value: string;
        /** A lucide icon (a legacy class component, as `CheckMenu` and `TabBar` type it). */
        icon: ComponentType;
        /** The button's accessible name, its tooltip and, with `showLabels`, its text. */
        label: string;
        /** A longer tooltip than the label; the label when absent. */
        hint?: string;
        testId: string;
    }
</script>

<script lang="ts">
    import {LayoutGrid, List} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import {getUserStorage, setUserStorage} from '$lib/utils/storage';

    interface Props {
        /** Current view mode */
        mode: string;
        /** Base key for localStorage persistence (will be user-scoped); none: the caller persists the mode itself. */
        storageKey?: string;
        /** Callback when mode changes */
        onchange?: (mode: string) => void;
        /** The modes; default: grid and list. */
        options?: ViewModeOption[];
        /** Show each option's label beside its icon, from the `sm` breakpoint up; below it the icon alone (the tooltip says it). */
        showLabels?: boolean;
        /** The height of the panel toggles beside it (`text-xs`, a 14 px icon) instead of a page header's. */
        compact?: boolean;
        /** Accessible name of the group. */
        groupLabel?: string;
        testId?: string;
    }

    let {mode = $bindable('grid'), storageKey, onchange, options, showLabels = false, compact = false, groupLabel, testId}: Props = $props();

    let items = $derived<ViewModeOption[]>(
        options ?? [
            {value: 'grid', icon: LayoutGrid, label: $t('sharedResource.viewGrid'), testId: 'view-mode-grid'},
            {value: 'list', icon: List, label: $t('sharedResource.viewTable'), testId: 'view-mode-list'},
        ],
    );

    // Load the stored value on mount, when the toggle persists it itself
    $effect(() => {
        if (!storageKey) return;
        const stored = getUserStorage(storageKey, items[0]?.value ?? 'grid');
        if (items.some((item) => item.value === stored)) mode = stored;
    });

    function setMode(newMode: string) {
        mode = newMode;
        if (storageKey) setUserStorage(storageKey, newMode);
        onchange?.(newMode);
    }
</script>

<!-- Each button says what it does in the design system's tooltip; a click is the button's own, so it stops before the tooltip's click, which would pin the hint over the list that is redrawn. -->
<div class="flex rounded-lg border border-lf-subtle text-lf-primary overflow-hidden {compact ? 'text-xs' : ''}" role="group" aria-label={groupLabel} data-testid={testId}>
    {#each items as item (item.value)}
        {@const Icon = item.icon}
        <Tooltip text={item.hint ?? item.label} position="bottom" interactiveChild testId="{item.testId}-tooltip">
            <button
                type="button"
                aria-label={item.label}
                aria-pressed={mode === item.value}
                data-testid={item.testId}
                class="flex items-center justify-center gap-1.5 transition-colors focus-visible:outline-lf-focus
                       {compact ? 'px-2.5 py-1' : 'px-2.5 py-1.5'}
                       {mode === item.value ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                onclick={(event) => {
                    event.stopPropagation();
                    setMode(item.value);
                }}
            >
                <Icon size={compact ? 14 : 16} />
                {#if showLabels}
                    <span class="hidden sm:inline" data-testid="{item.testId}-label">{item.label}</span>
                {/if}
            </button>
        </Tooltip>
    {/each}
</div>
