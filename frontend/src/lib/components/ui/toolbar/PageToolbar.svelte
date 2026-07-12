<!--
  PageToolbar — Unified page-level toolbar shell: Filters · optional Summary · optional Actions · optional Tabs.

  Owns the responsive ResizeObserver (via createResponsiveLayout) and the
  "justified" stacking/alignment across the 4 standard breakpoints (wide/tablet/
  tablet-s/mobile) plus an optional narrower 5th "compact" fallback (icon-only
  actions row, only if the page's thresholds define `compact`), so pages stop
  re-implementing the same layoutMode conditional Tailwind classes. This
  component owns LAYOUT ONLY — content for each zone, and any signal wiring
  (onchange, data fetching, etc.), stays with the page and is supplied via
  snippets.

  "Justified" here means: zones stack full-width and start-aligned instead of
  the whole block floating centered (see docs/history in
  LibreFolio_devWiki/wiki/concepts/responsive-4mode-layout.md, where mobile
  was originally documented as "everything stacked and centered").

  Zones:
  - filters (required)  — primary controls, anchored by a DateRangePicker.
                           Pass align="start" to the DateRangePicker itself —
                           this shell stacks left-justified, not centered.
                           Receives {layoutMode, isStacked}.
  - summary (optional)  — contextual info (e.g. AssetPriceSummary, FxPriceSummary).
                           Receives {layoutMode, isStacked}.
  - actions (optional)  — action buttons. Receives {layoutMode, showActionLabels, stretchActions}.
                           showActionLabels is false only in the narrowest
                           "compact" fallback (icon-only row), if defined.
  - tabs (optional)     — pass `tabs` + bind:activeTab to render a TabBar row
                           below the filter row. Omitted entirely (no
                           placeholder) when `tabs` isn't passed.

  isStacked/stretchActions are the semantic flags pages should read instead of
  comparing raw layoutMode strings (e.g. `layoutMode === 'mobile'`) — when a
  layoutMode's meaning changes, only this component needs updating.
-->
<script lang="ts">
    import {type Snippet, untrack} from 'svelte';
    import TabBar, {type TabItem} from '$lib/components/ui/tabs/TabBar.svelte';
    import {createResponsiveLayout, registerLayoutDebug, type LayoutMode, type LayoutThresholds} from '$lib/utils/layout/responsiveLayout.svelte';

    interface Props {
        /** Breakpoints for this page — deliberately per-page (not shared), same shape as createResponsiveLayout. */
        thresholds: LayoutThresholds;
        /** Zone A — primary controls (required), anchored by a DateRangePicker. Receives current layoutMode + isStacked. */
        filters: Snippet<[{layoutMode: LayoutMode; isStacked: boolean}]>;
        /** Zone B — optional contextual summary. */
        summary?: Snippet<[{layoutMode: LayoutMode; isStacked: boolean}]>;
        /** Zone C — action buttons. */
        actions?: Snippet<[{layoutMode: LayoutMode; showActionLabels: boolean; stretchActions: boolean}]>;
        /** Zone D — optional tab pagination row (omitted entirely, no placeholder, when not passed). */
        tabs?: TabItem[];
        activeTab?: string;
        ontabchange?: (id: string) => void;
        /** data-testid for the outer card. */
        testId?: string;
        /** data-testid for the inner filter row (existing e2e tests target this specifically per page). */
        filterRowTestId?: string;
        /** Registers the layout instance on window.__lfLayouts.<name> for live threshold tuning from the browser console (see registerLayoutDebug). Omit to skip registration. */
        layoutDebugName?: string;
        class?: string;
    }

    let {thresholds, filters, summary, actions, tabs, activeTab = $bindable(''), ontabchange, testId, filterRowTestId, layoutDebugName, class: className = ''}: Props = $props();

    let barRef = $state<HTMLDivElement | null>(null);
    // thresholds is a fixed per-page config, not meant to change reactively — untrack() avoids
    // the `state_referenced_locally` warning (same pattern used elsewhere for prop-seeded state).
    const layout = createResponsiveLayout(untrack(() => thresholds));

    // layoutDebugName is a fixed per-page config too — untrack() for the same reason as thresholds above.
    const debugName = untrack(() => layoutDebugName);
    if (debugName) registerLayoutDebug(debugName, layout);

    $effect(() => {
        const el = barRef;
        if (!el) return;
        layout.attach(el);
        return () => layout.detach();
    });

    let layoutMode = $derived(layout.layoutMode);
    let showActionLabels = $derived(layout.showActionLabels);

    // Centralized semantics for what each layoutMode MEANS — pages consume these instead of
    // comparing raw layoutMode strings, so a future redefinition (like Round 4 repurposing
    // "mobile") only needs a change HERE, not in every page that reads layoutMode.
    /** True everywhere except the narrowest "compact" icon-only fallback — action buttons stretch to fill their grid cell/row. */
    let stretchActions = $derived(layoutMode !== 'compact');
    /** True in "mobile" and "compact" — the filters zone stacks full-width in a column instead of a row. */
    let isStacked = $derived(layoutMode === 'mobile' || layoutMode === 'compact');
</script>

<div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm overflow-hidden {className}" data-testid={testId}>
    <div bind:this={barRef} class="flex gap-3 p-4 {isStacked ? 'flex-col items-stretch' : 'flex-row items-center justify-between'}" data-testid={filterRowTestId}>
        <!-- Zones A+B: filters (anchored by date range) + optional summary.
             Justified: full-width & start-aligned when stacked, never centered. -->
        <div class="flex gap-3 {isStacked ? 'flex-col items-stretch' : layoutMode === 'tablet-s' ? 'flex-col items-start flex-1' : 'flex-row items-center flex-1 flex-wrap'}">
            {@render filters({layoutMode, isStacked})}
            {#if summary}
                {@render summary({layoutMode, isStacked})}
            {/if}
        </div>

        <!-- Zone C: actions — 2×2 grid with labels (wide/tablet/mobile), column with labels
             (tablet-s), icon-only row (compact — the narrowest fallback, for when even the
             2×2-with-labels grid doesn't fit). `*:w-full` forces every direct child (plain
             button or a dropdown-trigger wrapper div) to stretch to its full cell/row width —
             a safety net so pages don't need to remember w-full on each action individually. -->
        {#if actions}
            <div class="flex shrink-0 gap-1.5 {!stretchActions ? 'flex-row justify-center flex-wrap' : layoutMode === 'tablet-s' ? 'flex-col items-stretch *:w-full' : 'grid grid-cols-2 *:w-full'}">
                {@render actions({layoutMode, showActionLabels, stretchActions})}
            </div>
        {/if}
    </div>

    <!-- Zone D: optional tab pagination row.
         showLabels reuses the same container-ResizeObserver signal as the action
         buttons (labelHide threshold) instead of TabBar's own viewport-based sm:
         breakpoint — fixes label truncation/bad wrapping in narrow cards on wide viewports.
         fillWidth: tabs always stretch to occupy all available card width. -->
    {#if tabs && tabs.length > 0}
        <TabBar {tabs} bind:activeTab onchange={ontabchange} showLabels={showActionLabels} fillWidth />
    {/if}
</div>
