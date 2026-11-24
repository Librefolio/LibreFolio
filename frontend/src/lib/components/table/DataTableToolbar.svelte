<!--
  DataTableToolbar - The selection bar: the counter of the selected rows and the bulk actions.
  Shown when rows are selected and bulkActions are defined.

  Four variants:
  - `inline` (default): a compact row of icons, placed by the parent. It is the bar of the modals that hold a table.
  - `top` (77 SEL-A): the bar at the top of a table. It keeps its row while nothing is selected, holding a grey hint so the
    table does not jump at the first tick (Q-SEL-15) — the hint only: `selection-toolbar` exists only with a selection; with a selection, the count button and the actions with their
    words (the rule below) and their numbers. In the flow: nothing fixed, nothing reserved.
  - `dock` (77 SEL-A): the actions row of a table's dock, the balloon at its bottom: the floating card's content, in the
    flow of its dock, without reserving room at the bottom of the page. Only with a selection.
  - `floating` (U8, the pages): a card fixed at the bottom of the content, centred on it (the sidebar is left out through
    `--lf-content-left`, set by the app layout), visible only while at least one row is selected. The words of the actions
    show from 1024 px up; at 640-1023 px only the primary and the destructive action keep theirs; below, icons only (the
    name is the tooltip and the `aria-label`). While it shows it reserves room at the bottom of the page
    (`--lf-selbar-space` on the root element, read by the layout) so the last row is never hidden behind it. It is a
    `role="toolbar"`; `Esc` deselects only while the focus is inside it. It sits over the content and under the dialogs and the mobile sidebar.

  In all: `data-testid="selection-toolbar"` with `data-variant` and `data-selected-count`, the count button
  `selection-toolbar-clear`, one `toolbar-action-<id>` per action, and `toolbar-action-<id>-count` for an action that
  carries the number of rows it acts on (`count`, Q-SEL-1: always shown when given). A disabled action with a `hint` shows the hint as its tooltip (the label stays its
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
        /** The number of rows the action acts on (77 SEL-A, `resolveSelectionAction`): drawn beside it. */
        count?: number;
        /** The button's test id when the table keeps its own (77 SEL-E); its label and count take it as their prefix. */
        testid?: string;
    }

    interface Props {
        selectedCount: number;
        bulkActions: BulkActionInfo[];
        onClearSelection?: () => void;
        variant?: 'inline' | 'floating' | 'top' | 'dock';
        /** The `top` bar's words while nothing is selected; absent: the shared hint. */
        hint?: string;
        /** The `top` bar sits in a section's head (77 SEL-D2): one line, and the compact form when the head is narrow. */
        inHead?: boolean;
    }

    let {selectedCount, bulkActions, onClearSelection, variant = 'inline', hint, inHead = false}: Props = $props();

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

    /**
     * A disabled action that says why (66 F7): `aria-disabled`, not the native `disabled`, so it keeps the focus, the
     * tap and the click that open its reason in the shared Tooltip (a natively disabled button gets none of them, and
     * a phone shows no `title`). Its own click never runs the action. Without a hint the native `disabled` stays.
     */
    function offWithReason(action: BulkActionInfo): boolean {
        return !!action.disabled && !!resolve(action.hint);
    }

    /** The button's test id: the table's own, or `toolbar-action-<id>`. */
    function testIdOf(action: BulkActionInfo): string {
        return action.testid ?? `toolbar-action-${action.id}`;
    }

    function runAction(action: BulkActionInfo) {
        if (action.disabled) return;
        action.onClick();
    }

    /** The action's word is out of view (a head's compact form): only then its name tooltip adds something. */
    function wordHidden(trigger: HTMLElement): boolean {
        const word = trigger.querySelector('.lbl');
        return !word || word.getClientRects().length === 0;
    }

    function getShownLabel(action: BulkActionInfo): string {
        return resolve(action.shortLabel) || getActionLabel(action);
    }

    let floating = $derived(variant === 'floating');
    /** The variants drawn as a toolbar with the words of the actions: the floating card, the top bar, the dock row. */
    let worded = $derived(variant !== 'inline');
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
        if (event.key !== 'Escape' || !worded) return;
        event.stopPropagation();
        onClearSelection?.();
    }
</script>

{#snippet countButton()}
    <button type="button" class="selected-count-btn" data-testid="selection-toolbar-clear" onclick={() => onClearSelection?.()} title={$t('common.clearSelection') || 'Clear selection'}>
        <span class="count-text">{selectedCount} <span class="count-word">{$t('common.selected')}</span></span>
        <span class="clear-icon">×</span>
    </button>
{/snippet}

{#snippet floatingAction(action: BulkActionInfo)}
    {#if offWithReason(action)}
        <!-- The reason of a disabled action, in every form (66 F7); in a head it opens on keyboard focus too. -->
        <Tooltip text={getTooltip(action)} interactiveChild openOnFocus={inHead}>
            {@render floatingButton(action)}
        </Tooltip>
    {:else if inHead}
        <!-- In a head's compact form the action is an icon: its name is its tooltip, on hover and on keyboard focus. With
             its word in view the tooltip would only repeat it, so it opens only while the word is hidden (77 SEL-D2). -->
        <Tooltip text={getTooltip(action)} interactiveChild openOnFocus showIf={wordHidden}>
            {@render floatingButton(action)}
        </Tooltip>
    {:else}
        {@render floatingButton(action)}
    {/if}
{/snippet}

{#snippet floatingButton(action: BulkActionInfo)}
    {@const name = getActionLabel(action)}
    {@const reachable = offWithReason(action)}
    <button
        type="button"
        class="act"
        class:compact={variant === 'top'}
        class:primary={action.primary}
        class:danger={action.variant === 'danger'}
        onclick={() => runAction(action)}
        disabled={action.disabled && !reachable}
        aria-disabled={reachable ? 'true' : undefined}
        title={reachable || inHead ? undefined : getTooltip(action)}
        aria-label={action.count !== undefined ? `${getShownLabel(action)}, ${action.count}` : name}
        data-disabled-reason={action.disabled && action.reason ? action.reason : undefined}
        data-primary={action.primary ? 'true' : 'false'}
        data-danger={action.variant === 'danger' ? 'true' : 'false'}
        data-testid={testIdOf(action)}
    >
        <action.icon size={16} class={action.iconClass || ''} />
        <span class="lbl" class:keep={action.primary || action.variant === 'danger'} data-testid="{testIdOf(action)}-label">{getShownLabel(action)}</span>
        {@render countBadge(action)}
    </button>
{/snippet}

{#snippet countBadge(action: BulkActionInfo)}
    {#if action.count !== undefined}
        <span class="n" data-testid="{testIdOf(action)}-count">{action.count}</span>
    {/if}
{/snippet}

{#snippet wordedActions()}
    {#each safeActions as action (action.id)}
        {@render floatingAction(action)}
    {/each}
    {#if dangerActions.length > 0 && safeActions.length > 0}
        <span class="sep" aria-hidden="true"></span>
    {/if}
    {#each dangerActions as action (action.id)}
        {@render floatingAction(action)}
    {/each}
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
                {@render wordedActions()}
            </div>
        </div>
    {/if}
{:else if variant === 'dock'}
    {#if selectedCount > 0}
        <!-- svelte-ignore a11y_interactive_supports_focus -->
        <div class="dock-row" role="toolbar" aria-label={$t('common.selectionActions')} data-testid="selection-toolbar" data-variant="dock" data-selected-count={selectedCount} onkeydown={handleKeydown}>
            {@render countButton()}
            <span class="visually-hidden" role="status">{selectedCount} {$t('common.selected')}</span>
            <span class="sep" aria-hidden="true"></span>
            {@render wordedActions()}
        </div>
    {/if}
{:else if variant === 'top'}
    {#if selectedCount > 0}
        <!-- svelte-ignore a11y_interactive_supports_focus -->
        <div class="top-bar" class:in-head={inHead} role="toolbar" aria-label={$t('common.selectionActions')} data-testid="selection-toolbar" data-variant="top" data-in-head={inHead ? 'true' : undefined} data-selected-count={selectedCount} onkeydown={handleKeydown}>
            {@render countButton()}
            <span class="visually-hidden" role="status">{selectedCount} {$t('common.selected')}</span>
            {@render wordedActions()}
        </div>
    {:else}
        <!-- No selection: the hint holds the row, and there is no bar yet (`selection-toolbar` exists only with a selection). -->
        <div class="top-bar" data-variant="top" data-in-head={inHead ? 'true' : undefined}>
            <span class="top-hint" data-testid="selection-toolbar-hint">{hint ?? $t('table.selectionHint')}</span>
        </div>
    {/if}
{:else}
    <div class="toolbar" data-testid="selection-toolbar" data-variant="inline" data-selected-count={selectedCount}>
        <div class="toolbar-right">
            {#if selectedCount > 0}
                {@render countButton()}
                <div class="bulk-actions">
                    {#each bulkActions as action}
                        {@const reachable = offWithReason(action)}
                        <Tooltip text={getTooltip(action)} interactiveChild={reachable}>
                            <button
                                type="button"
                                class="bulk-btn"
                                class:danger={action.variant === 'danger'}
                                onclick={() => runAction(action)}
                                disabled={action.disabled && !reachable}
                                aria-disabled={reachable ? 'true' : undefined}
                                data-disabled-reason={action.disabled && action.reason ? action.reason : undefined}
                                data-testid={testIdOf(action)}
                            >
                                <action.icon size={16} class={action.iconClass || ''} />
                                {@render countBadge(action)}
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
        position: relative;
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

    .bulk-btn:hover:not([aria-disabled='true']) {
        background: var(--lf-surface-neutral);
        color: var(--lf-text-primary);
    }

    .bulk-btn.danger {
        color: var(--lf-danger);
    }

    .bulk-btn.danger:hover:not([aria-disabled='true']) {
        background: var(--lf-danger-soft);
        color: var(--lf-danger-on-soft);
    }

    .bulk-btn[aria-disabled='true'] {
        opacity: 0.5;
        cursor: not-allowed;
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

    .act:hover:not(:disabled):not([aria-disabled='true']) {
        background: var(--lf-surface-hover);
        color: var(--lf-text-primary);
    }

    .act:disabled,
    .act[aria-disabled='true'] {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .act.primary {
        background: var(--lf-action);
        color: var(--lf-on-action);
    }

    .act.primary:hover:not(:disabled):not([aria-disabled='true']) {
        background: var(--lf-action-hover);
        color: var(--lf-on-action);
    }

    .act.danger {
        color: var(--lf-danger);
    }

    .act.danger:hover:not(:disabled):not([aria-disabled='true']) {
        background: var(--lf-danger-soft);
        color: var(--lf-danger-on-soft);
    }

    .act:focus-visible,
    .floating .selected-count-btn:focus-visible,
    .dock-row .selected-count-btn:focus-visible,
    .top-bar .selected-count-btn:focus-visible {
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

    /* ===== the number of rows an action takes (77 SEL-A) ===== */
    .n {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 18px;
        height: 18px;
        padding: 0 5px;
        border-radius: 9999px;
        font-size: 0.6875rem;
        font-weight: 600;
        background: var(--lf-surface-panel);
        color: var(--lf-text-secondary);
    }

    .act.primary .n {
        background: var(--lf-on-action);
        color: var(--lf-action);
    }

    .bulk-btn .n {
        position: absolute;
        top: -6px;
        right: -6px;
        min-width: 16px;
        height: 16px;
        padding: 0 4px;
        font-size: 0.625rem;
    }

    /* ===== top: the bar at the top of a table (77 SEL-A) ===== */
    .top-bar {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.375rem;
        min-height: 2rem;
    }

    /* The actions on the selected rows, when they are not floating, sit on the right edge (81 U20); the hint before the
       first tick sits there too, so the bar grows from one edge and nothing jumps when it appears. A section's head
       (`in-head`, `data-in-head`) places the bar itself. */
    .top-bar:not(.in-head):not([data-in-head]) {
        justify-content: flex-end;
    }

    /* In a section's head (77 SEL-D2) the bar keeps one line, so the head keeps its height: below 50rem of head (the
       `dt-head` container, `SelectionPanel`) it takes the compact form of the phone — «2 ×», each action an icon with
       its number on the corner; its name is the tooltip and the `aria-label`. Measured on the heads of SEL-D2 in the
       four languages: the whole bar fits from 800 px of head (the sectors with «Balance», in French, the widest; the
       Asset window's heads are 812 px), not at 760 px (the same sectors) nor at 645 px (the schedule in French). */
    .top-bar.in-head {
        flex-wrap: nowrap;
    }

    @container dt-head (max-width: 49.98rem) {
        .top-bar.in-head .count-word,
        .top-bar.in-head .lbl {
            display: none;
        }

        .top-bar.in-head .act {
            position: relative;
        }

        .top-bar.in-head .act .n {
            position: absolute;
            top: -6px;
            right: -6px;
            min-width: 16px;
            height: 16px;
            padding: 0 4px;
            font-size: 0.625rem;
        }
    }

    .top-hint {
        font-size: 0.75rem;
        color: var(--lf-text-muted);
    }

    .act.compact {
        height: 28px;
        padding: 0 0.5rem;
        border-radius: 6px;
        background: var(--lf-surface-panel);
        font-size: 0.8125rem;
    }

    .act.compact.primary {
        background: var(--lf-action);
    }

    .act.compact .n {
        background: var(--lf-surface-card);
    }

    .act.compact.primary .n {
        background: var(--lf-on-action);
    }

    /* On a phone the top bar, the dock row and a page's fixed panel keep the number only (the mock B2/B6; the status line
       still says it all). In the fixed panel and the dock row the number of each action becomes a dot on the icon's
       corner, as in the inline bar (`.bulk-btn .n`): the button keeps its width, so four actions fit a 320 px screen up
       to three digits, and its name says the number (the designer, 20/11, 77 SEL-B). The top bar wraps instead. */
    @media (max-width: 639px) {
        .top-bar .count-word,
        .dock-row .count-word,
        .floating .count-word {
            display: none;
        }

        .act.compact {
            height: 32px;
            padding: 0 0.5625rem;
        }

        .floating .act,
        .dock-row .act {
            position: relative;
        }

        .floating .act .n,
        .dock-row .act .n {
            position: absolute;
            top: -6px;
            right: -6px;
            min-width: 16px;
            height: 16px;
            padding: 0 4px;
            font-size: 0.625rem;
        }
    }

    /* ===== dock: the actions row of a table's dock (77 SEL-A) ===== */
    .dock-row {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.25rem;
        padding: 0.375rem 0.375rem 0.375rem 0.5rem;
    }

    .dock-row .selected-count-btn {
        padding: 0.375rem 0.625rem;
        border-radius: 9px;
        font-weight: 600;
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
