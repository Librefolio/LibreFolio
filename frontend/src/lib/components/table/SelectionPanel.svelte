<!--
  SelectionPanel.svelte — the selection panel around one or more tables (plan 77: SEL-A in `DataTable`, SEL-C outside it).

  - **The bar at the top** (`dt-selection-top`, `data-in-view`): the hint while nothing is selected, the actions with a
    selection. Its slot is always drawn and keeps its height; it is what the watcher observes.
  - **The content**: the table (`DataTable`), or several tables sharing one selection (the «Relink events» window).
  - **The dock** (`dt-dock`, `data-actions`): the actions come down into it only while the top is out of view, above the
    pager when one is given (`pager`, called with `docked`). Without either, nothing is drawn.
  - The actions are in one place at a time, so `toolbar-action-<id>` stays unique.
  - **In a section** (SEL-D, Q-SEL-8): the caller's head (`head`, its title and its own buttons) takes the place of the
    bar at the top, and places the bar inside itself. The whole head is what the watcher observes. While nothing is
    selected the head stays as it was: no hint, unless `hint` is given. Its slot keeps the bar's height, so the head
    does not grow at the first tick.

  The actions arrive resolved (`selectionToolbarActions`): the caller owns the rows, the rule and what a click does.
  Uses Svelte 5 runes.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import DataTableToolbar from './DataTableToolbar.svelte';
    import type {SelectionToolbarAction} from './selectionActions';
    import {watchInView} from './selectionDock';

    interface Props {
        /** The actions to draw, each with its number and its click on its own rows. */
        actions: SelectionToolbarAction[];
        /** How many rows are selected (the count chip). */
        selectedCount: number;
        /** The bar's text while nothing is selected (default: the shared hint). */
        hint?: string;
        /** The count chip's ×: clear the selection. */
        onClearSelection: () => void;
        /** The table(s) the selection belongs to. */
        children: Snippet;
        /** A pager to host in the dock, with whether it is docked under the actions. */
        pager?: Snippet<[boolean]>;
        /** A section's head, in place of the bar at the top: it draws the bar it is given where the bar goes (SEL-D). */
        head?: Snippet<[Snippet]>;
    }

    let {actions, selectedCount, hint, onClearSelection, children, pager, head}: Props = $props();

    let topEl = $state<HTMLDivElement | null>(null);
    let topInView = $state(true);
    $effect(() => {
        if (!topEl) return;
        return watchInView(topEl, (inView) => (topInView = inView));
    });
    /** The actions are in one place at a time: at the top while it is in view, in the dock otherwise. */
    let dockHasActions = $derived(selectedCount > 0 && !topInView);
</script>

<!-- The bar at the top. Its slot stays (and keeps its height) while the actions are down in the dock. -->
{#snippet headBar()}
    <div class="dt-head-bar">
        {#if selectedCount > 0 ? topInView : hint !== undefined}
            <DataTableToolbar variant="top" {selectedCount} bulkActions={actions} {onClearSelection} {hint} />
        {/if}
    </div>
{/snippet}
<div class="dt-selection-top" class:in-head={!!head} bind:this={topEl} data-testid="dt-selection-top" data-in-view={topInView ? 'true' : 'false'}>
    {#if head}
        {@render head(headBar)}
    {:else if selectedCount === 0 || topInView}
        <DataTableToolbar variant="top" {selectedCount} bulkActions={actions} {onClearSelection} {hint} />
    {/if}
</div>

{@render children()}

<!-- The dock. The pager is the same instance in both states (only its `docked` changes). Without either, nothing is drawn. -->
{#if pager || dockHasActions}
    <div class="dt-dock-wrap" class:active={dockHasActions} data-testid="dt-dock" data-actions={dockHasActions ? 'true' : 'false'}>
        <div class="dt-dock" class:active={dockHasActions}>
            {#if dockHasActions}
                <DataTableToolbar variant="dock" {selectedCount} bulkActions={actions} {onClearSelection} />
            {/if}
            {#if pager}
                {@render pager(dockHasActions)}
            {/if}
        </div>
    </div>
{/if}

<style>
    .dt-selection-top {
        min-height: 2rem;
        margin-bottom: 0.5rem;
    }

    /* In a section's head the slot of the bar keeps the bar's height (32 px on a phone), so the head does not grow. */
    .dt-head-bar {
        display: flex;
        align-items: center;
        min-height: 2rem;
        min-width: 0;
    }

    .dt-head-bar:empty {
        flex: 0 0 0;
    }

    /* Without actions the dock adds nothing: the pager keeps its own sticky balloon, as without the panel. */
    .dt-dock-wrap:not(.active) {
        display: contents;
    }

    .dt-dock-wrap:not(.active) > .dt-dock {
        display: contents;
    }

    /* With the actions it is the balloon: sticky at the bottom (lifted by `--lf-pager-lift` above a page's fixed panel,
       as the pager), the actions row on top, the pager under it. */
    .dt-dock-wrap.active {
        position: sticky;
        bottom: calc(1rem + var(--lf-pager-lift, 0px));
        z-index: 30;
        display: flex;
        justify-content: center;
        padding: 0.5rem 0;
        pointer-events: none;
    }

    .dt-dock.active {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        max-width: calc(100vw - 2rem);
        pointer-events: auto;
        background: var(--lf-surface-card);
        border: 1px solid var(--lf-border-raised);
        border-radius: 16px;
        box-shadow: 0 10px 30px -8px var(--lf-shadow-raised);
        animation: dt-dock-rise 0.16s ease-out;
    }

    @keyframes dt-dock-rise {
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
        .dt-dock.active {
            animation: none;
        }
    }

    @media (max-width: 480px) {
        .dt-dock-wrap.active {
            bottom: calc(0.5rem + var(--lf-pager-lift, 0px));
        }
    }
</style>
