<!--
  DataTableToolbar - The selection bar: the counter of the selected rows and the bulk actions.
  Shown when rows are selected and bulkActions are defined.

  Two variants:
  - `inline` (default): a compact row of icons, placed by the parent. It is the bar of the modals that hold a table.
  - `floating` (U8, the pages): a card fixed at the bottom of the content, centred on it (the sidebar is left out through
    `--lf-content-left`, set by the app layout), visible only while at least one row is selected. The words of the actions
    show from 1024 px up; at 640-1023 px only the primary and the destructive action keep theirs; below, icons only (the
    name is the tooltip and the `aria-label`). While it shows it reserves room at the bottom of the page
    (`--lf-selbar-space` on the root element, read by the layout) so the last row is never hidden behind it. It is a
    `role="toolbar"`; `Esc` deselects only while the focus is inside it. It sits over the content and under the dialogs and the mobile sidebar.

  In both: `data-testid="selection-toolbar"` with `data-selected-count`, the count button `selection-toolbar-clear`,
  one `toolbar-action-<id>` per action. A disabled action with a `hint` shows the hint as its tooltip (the label stays its
  name) and publishes its `reason` code as `data-disabled-reason`.
-->
<script lang="ts">
    import {onDestroy} from 'svelte';
    import {t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

    interface BulkActionInfo {
        id: string;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        icon: any;
        label: string | (() => string);
        /** The word shown in the floating bar when it is shorter than the label (the label stays the tooltip and the name). */
        shortLabel?: string | (() => string);
        variant?: 'default' | 'danger';
        /** The main action of the bar: drawn solid (floating variant). */
        primary?: boolean;
        onClick: () => void;
        /** CSS class applied to the icon (e.g. 'animate-spin' for loading) */
        iconClass?: string;
        /** Disable the button */
        disabled?: boolean;
        /** Why a disabled action is off: its tooltip while disabled (the label stays its name). Ignored when enabled. */
        hint?: string | (() => string);
        /** A code for why a disabled action is off, published as `data-disabled-reason` (tests read it, not the text). */
        reason?: string;
    }

    interface Props {
        selectedCount: number;
        bulkActions: BulkActionInfo[];
        onClearSelection?: () => void;
        variant?: 'inline' | 'floating';
    }

    let {selectedCount, bulkActions, onClearSelection, variant = 'inline'}: Props = $props();

    /** Room kept at the bottom of the page for the floating bar: its height, its gap and the phone's safe area. */
    const SELBAR_SPACE = 'calc(5.5rem + env(safe-area-inset-bottom, 0px))';

    function resolve(value: string | (() => string) | undefined): string {
        return typeof value === 'function' ? value() : (value ?? '');
    }

    function getActionLabel(action: BulkActionInfo): string {
        return resolve(action.label);
    }

    /** The tooltip: the hint of a disabled action that has one, the label otherwise. */
    function getTooltip(action: BulkActionInfo): string {
        return (action.disabled && resolve(action.hint)) || getActionLabel(action);
    }

    function getShownLabel(action: BulkActionInfo): string {
        return resolve(action.shortLabel) || getActionLabel(action);
    }

    let floating = $derived(variant === 'floating');
    let reserving = $derived(floating && selectedCount > 0);

    // The page keeps a margin at the bottom while the bar shows.
    $effect(() => {
        if (!reserving) return;
        document.documentElement.style.setProperty('--lf-selbar-space', SELBAR_SPACE);
        return () => document.documentElement.style.removeProperty('--lf-selbar-space');
    });
    onDestroy(() => {
        if (floating) document.documentElement.style.removeProperty('--lf-selbar-space');
    });

    // The destructive actions go last, apart from the others.
    let safeActions = $derived(bulkActions.filter((action) => action.variant !== 'danger'));
    let dangerActions = $derived(bulkActions.filter((action) => action.variant === 'danger'));

    function handleKeydown(event: KeyboardEvent) {
        if (event.key !== 'Escape' || !floating) return;
        event.stopPropagation();
        onClearSelection?.();
    }
</script>

{#snippet countButton()}
    <button type="button" class="selected-count-btn" data-testid="selection-toolbar-clear" onclick={() => onClearSelection?.()} title={$t('common.clearSelection') || 'Clear selection'}>
        <span class="count-text">{selectedCount} {$t('common.selected')}</span>
        <span class="clear-icon">×</span>
    </button>
{/snippet}

{#snippet floatingAction(action: BulkActionInfo)}
    {@const name = getActionLabel(action)}
    <button
        type="button"
        class="act"
        class:primary={action.primary}
        class:danger={action.variant === 'danger'}
        onclick={action.onClick}
        disabled={action.disabled}
        title={getTooltip(action)}
        aria-label={name}
        data-disabled-reason={action.disabled && action.reason ? action.reason : undefined}
        data-primary={action.primary ? 'true' : 'false'}
        data-danger={action.variant === 'danger' ? 'true' : 'false'}
        data-testid="toolbar-action-{action.id}"
    >
        <action.icon size={16} class={action.iconClass || ''} />
        <span class="lbl" class:keep={action.primary || action.variant === 'danger'} data-testid="toolbar-action-{action.id}-label">{getShownLabel(action)}</span>
    </button>
{/snippet}

{#if floating}
    {#if selectedCount > 0}
        <div class="floating-wrap">
            <!-- The toolbar itself takes no focus: its buttons do, and the key reaches it from them (roving focus is not needed for five buttons). -->
            <!-- svelte-ignore a11y_interactive_supports_focus -->
            <div class="floating" role="toolbar" aria-label={$t('common.selectionActions')} data-testid="selection-toolbar" data-variant="floating" data-selected-count={selectedCount} onkeydown={handleKeydown}>
                {@render countButton()}
                <span class="visually-hidden" role="status">{selectedCount} {$t('common.selected')}</span>
                <span class="sep" aria-hidden="true"></span>
                {#each safeActions as action (action.id)}
                    {@render floatingAction(action)}
                {/each}
                {#if dangerActions.length > 0 && safeActions.length > 0}
                    <span class="sep" aria-hidden="true"></span>
                {/if}
                {#each dangerActions as action (action.id)}
                    {@render floatingAction(action)}
                {/each}
            </div>
        </div>
    {/if}
{:else}
    <div class="toolbar" data-testid="selection-toolbar" data-variant="inline" data-selected-count={selectedCount}>
        <div class="toolbar-right">
            {#if selectedCount > 0}
                {@render countButton()}
                <div class="bulk-actions">
                    {#each bulkActions as action}
                        <Tooltip text={getTooltip(action)}>
                            <button type="button" class="bulk-btn" class:danger={action.variant === 'danger'} onclick={action.onClick} disabled={action.disabled} data-disabled-reason={action.disabled && action.reason ? action.reason : undefined} data-testid="toolbar-action-{action.id}">
                                <action.icon size={16} class={action.iconClass || ''} />
                            </button>
                        </Tooltip>
                    {/each}
                </div>
            {/if}
        </div>
    </div>
{/if}

<style>
    .toolbar {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        padding: 0.375rem 0;
        gap: 0.75rem;
    }

    .toolbar-right {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .selected-count-btn {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.25rem 0.5rem;
        border: 1px solid transparent;
        border-radius: 6px;
        background: var(--lf-selected);
        font-size: 0.8125rem;
        color: var(--lf-link);
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s;
        white-space: nowrap;
    }

    .selected-count-btn:hover {
        background: color-mix(in oklab, var(--lf-checked) 20%, transparent);
        border-color: color-mix(in oklab, var(--lf-checked) 20%, transparent);
        color: var(--lf-text-primary);
    }

    .selected-count-btn .clear-icon {
        font-size: 1rem;
        line-height: 1;
        opacity: 0.6;
    }

    .selected-count-btn:hover .clear-icon {
        opacity: 1;
    }

    .bulk-actions {
        display: flex;
        gap: 0.25rem;
    }

    .bulk-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: none;
        border-radius: 6px;
        background: var(--lf-surface-panel);
        color: var(--lf-text-muted);
        cursor: pointer;
        transition: all 0.15s;
    }

    .bulk-btn:hover {
        background: var(--lf-surface-neutral);
        color: var(--lf-text-primary);
    }

    .bulk-btn.danger {
        color: var(--lf-danger);
    }

    .bulk-btn.danger:hover {
        background: var(--lf-danger-soft);
        color: var(--lf-danger-on-soft);
    }

    /* ===== floating variant ===== */

    /* A full-width strip fixed at the bottom of the content area (`--lf-content-left` is the sidebar's width, set by the
       layout); it takes no clicks itself, only the card inside does. Over the content and the sticky header (z 30), under the mobile sidebar and its veil (z 40) and the dialogs (z 50). */
    .floating-wrap {
        position: fixed;
        left: var(--lf-content-left, 0px);
        right: 0;
        bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
        z-index: 35;
        display: flex;
        justify-content: center;
        padding: 0 1rem;
        pointer-events: none;
    }

    .floating {
        pointer-events: auto;
        display: flex;
        align-items: center;
        gap: 0.25rem;
        max-width: 100%;
        padding: 0.375rem 0.375rem 0.375rem 0.5rem;
        background: var(--lf-surface-card);
        border: 1px solid var(--lf-border-raised);
        border-radius: 14px;
        box-shadow: 0 10px 30px -8px var(--lf-shadow-raised);
        animation: selbar-rise 0.16s ease-out;
    }

    @keyframes selbar-rise {
        from {
            transform: translateY(12px);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .floating {
            animation: none;
        }
    }

    .floating .selected-count-btn {
        padding: 0.375rem 0.625rem;
        border-radius: 9px;
        font-weight: 600;
    }

    .sep {
        align-self: stretch;
        width: 1px;
        margin: 0.25rem 0.25rem;
        background: var(--lf-border-subtle);
    }

    .act {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.5rem 0.625rem;
        border: 0;
        border-radius: 9px;
        background: transparent;
        color: var(--lf-text-secondary);
        font-size: 0.875rem;
        font-weight: 500;
        white-space: nowrap;
        cursor: pointer;
        transition: background-color 0.15s;
    }

    .act:hover:not(:disabled) {
        background: var(--lf-surface-hover);
        color: var(--lf-text-primary);
    }

    .act:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .act.primary {
        background: var(--lf-action);
        color: var(--lf-on-action);
    }

    .act.primary:hover:not(:disabled) {
        background: var(--lf-action-hover);
        color: var(--lf-on-action);
    }

    .act.danger {
        color: var(--lf-danger);
    }

    .act.danger:hover:not(:disabled) {
        background: var(--lf-danger-soft);
        color: var(--lf-danger-on-soft);
    }

    .act:focus-visible,
    .floating .selected-count-btn:focus-visible {
        outline: 2px solid var(--lf-focus);
        outline-offset: 1px;
    }

    /* Words: all from 1024 px; from 640 px only the primary and the destructive action; below, icons only. */
    .lbl {
        display: inline;
    }

    @media (max-width: 1023px) {
        .lbl:not(.keep) {
            display: none;
        }
    }

    @media (max-width: 639px) {
        .lbl {
            display: none;
        }

        .act {
            padding: 0.625rem 0.6875rem;
        }
    }

    .visually-hidden {
        position: absolute;
        width: 1px;
        height: 1px;
        margin: -1px;
        padding: 0;
        overflow: hidden;
        clip: rect(0 0 0 0);
        border: 0;
        white-space: nowrap;
    }
</style>
