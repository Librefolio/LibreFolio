<!--
  PageToolbar — Unified page-level toolbar shell: Filters · optional Summary · optional Actions · optional Tabs.

  Owns the responsive ResizeObserver (via createResponsiveLayout) and the
  "justified" stacking/alignment across the 5 breakpoints (oneRow/denseRow/
  stackFilters/mobile/iconOnly — layoutMode values match their triggering
  threshold name 1:1, except "mobile" which has no single dedicated
  threshold), so pages stop re-implementing the same layoutMode conditional
  Tailwind classes. This component owns LAYOUT ONLY — content for each zone,
  and any signal wiring (onchange, data fetching, etc.), stays with the page
  and is supplied via snippets.

  "Justified" here means: zones stack full-width and start-aligned instead of
  the whole block floating centered (see docs/history in
  LibreFolio_devWiki/wiki/concepts/responsive-4mode-layout.md, where mobile
  was originally documented as "everything stacked and centered").

  Zones:
  - filters (required)  — primary controls, anchored by a DateRangePicker.
                           Pass align="start" to the DateRangePicker itself —
                           this shell stacks left-justified, not centered.
                           Receives {layoutMode, isStacked, filtersStacked}.
  - summary (optional)  — contextual info (e.g. AssetPriceSummary, FxPriceSummary).
                           Receives {layoutMode, isStacked, filtersStacked}.
  - actions (optional)  — action buttons. Receives {layoutMode, showActionLabels,
                           stretchActions, actionsStacked}. showActionLabels is false only in
                           the narrowest "iconOnly" fallback (icon-only row), if defined.
                           actionsStacked is true only in the narrow "actionsColumn" sub-band
                           (see responsiveLayout.svelte.ts) — a 4×1 column instead of 2×2 grid.
  - tabs (optional)     — pass `tabs` + bind:activeTab to render a TabBar row
                           below the filter row. Omitted entirely (no
                           placeholder) when `tabs` isn't passed.

  isStacked/filtersStacked/stretchActions/actionsStacked are the semantic flags pages should
  read instead of comparing raw layoutMode strings (e.g. `layoutMode === 'mobile'`) — when a
  layoutMode's meaning changes, only this component needs updating.

  Round 10.2: `isStacked` (whole bar incl. Actions moves below Filters+Summary) and
  `filtersStacked` (ONLY Filters+Summary stack — Center moves below the DateRangePicker,
  Actions stay beside) are now DIFFERENT flags — `isStacked` used to also fire for "mobile",
  which pushed Actions below the filters column a whole tier too early (bug report: "in
  modalità mobile mi aspettavo i bottoni ancora accanto"). Now: `filtersStacked` covers
  stackFilters + mobile + iconOnly; `isStacked` covers iconOnly ONLY.
-->
<script lang="ts">
    import {type Snippet, untrack} from 'svelte';
    import TabBar, {type TabItem} from '$lib/components/ui/tabs/TabBar.svelte';
    import {createResponsiveLayout, registerLayoutDebug, type LayoutMode, type LayoutThresholds} from '$lib/utils/layout/responsiveLayout.svelte';

    interface Props {
        /** Breakpoints for this page — deliberately per-page (not shared), same shape as createResponsiveLayout. */
        thresholds: LayoutThresholds;
        /** Zone A — primary controls (required), anchored by a DateRangePicker. Receives current layoutMode + isStacked + filtersStacked. */
        filters: Snippet<[{layoutMode: LayoutMode; isStacked: boolean; filtersStacked: boolean}]>;
        /** Zone B — optional contextual summary. */
        summary?: Snippet<[{layoutMode: LayoutMode; isStacked: boolean; filtersStacked: boolean}]>;
        /** Zone C — action buttons. */
        actions?: Snippet<[{layoutMode: LayoutMode; showActionLabels: boolean; stretchActions: boolean; actionsStacked: boolean}]>;
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
        /** Optional read-out of the current layoutMode, for pages that need it OUTSIDE the filters/summary/actions snippets too (e.g. a hint elsewhere on the page). Snippet params remain the primary source inside the toolbar itself. */
        layoutMode?: LayoutMode;
        /** Optional read-out of isStacked, same rationale as layoutMode above. */
        isStacked?: boolean;
        /** Optional read-out of showActionLabels, same rationale as layoutMode above. */
        showActionLabels?: boolean;
    }

    let {
        thresholds,
        filters,
        summary,
        actions,
        tabs,
        activeTab = $bindable(''),
        ontabchange,
        testId,
        filterRowTestId,
        layoutDebugName,
        class: className = '',
        layoutMode: layoutModeOut = $bindable('denseRow'),
        isStacked: isStackedOut = $bindable(false),
        showActionLabels: showActionLabelsOut = $bindable(true),
    }: Props = $props();

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
    /** True everywhere except the narrowest "iconOnly" fallback — action buttons stretch to fill their grid cell/row. */
    let stretchActions = $derived(layoutMode !== 'iconOnly');
    /** True ONLY in "iconOnly" — the WHOLE bar (filters+summary AND actions) stacks in one column. */
    let isStacked = $derived(layoutMode === 'iconOnly');
    /** True in "stackFilters", "mobile" and "iconOnly" — the filters+summary zone stacks into a
     *  column (Center moves below the DateRangePicker, "justified" full-width) — but Actions stay
     *  BESIDE that column unless `isStacked` is ALSO true (iconOnly only). */
    let filtersStacked = $derived(layoutMode === 'stackFilters' || layoutMode === 'mobile' || layoutMode === 'iconOnly');
    /** True only in the narrow "actionsColumn" sub-band inside "mobile" (Round 10) — actions
     *  render as a 4×1 vertical column instead of the normal 2×2 grid. See responsiveLayout.svelte.ts. */
    let actionsStacked = $derived(layout.actionsStacked);

    // Mirror the (synchronous, $derived) values above onto the optional bindable props, for
    // pages that need layoutMode/isStacked/showActionLabels OUTSIDE the filters/summary/actions
    // snippets too (e.g. a hint elsewhere on the page). The template below always reads the
    // internal $derived values directly (never *Out), so this mirroring can never introduce a
    // render lag for the toolbar itself — it's a one-way export for external consumers only.
    $effect(() => {
        layoutModeOut = layoutMode;
    });
    $effect(() => {
        isStackedOut = isStacked;
    });
    $effect(() => {
        showActionLabelsOut = showActionLabels;
    });
</script>

<div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm overflow-hidden {className}" data-testid={testId}>
    <div bind:this={barRef} class="flex gap-3 p-4 {isStacked ? 'flex-col items-stretch' : 'flex-row items-center justify-between'}" data-testid={filterRowTestId}>
        <!-- Zones A+B: filters (anchored by date range) + optional summary.
             Justified: full-width & start-aligned when stacked, never centered.
             oneRow/denseRow: flex-nowrap (not flex-wrap) — the DateRangePicker is the ONLY zone
             meant to give up space when the row is squeezed (it sheds jolly badges via its own
             verify+shed loop); other zones (currency selector, broker filter, ...) must get
             `shrink-0` from the page so CSS never wraps THEM to a new line instead. With
             flex-wrap here, the picker (flex-grow) would greedily claim the whole line first,
             pushing its sibling(s) to a whole new line rather than shrinking itself. -->
        <div class="flex gap-3 {isStacked ? 'flex-col items-stretch' : filtersStacked ? 'flex-col items-start flex-1' : 'flex-row items-center flex-1 flex-nowrap'}">
            {@render filters({layoutMode, isStacked, filtersStacked})}
            {#if summary}
                {@render summary({layoutMode, isStacked, filtersStacked})}
            {/if}
        </div>

        <!-- Zone C: actions — 2×2 grid with labels (oneRow/denseRow/stackFilters/most of
             mobile), 4×1 column with labels (ONLY the narrow "actionsColumn" sub-band inside
             mobile — Round 10), icon-only row (iconOnly — the narrowest fallback, for when even
             the 2×2-with-labels grid doesn't fit). `*:w-full` forces every direct child (plain
             button or a dropdown-trigger wrapper div) to stretch to its full cell/row width —
             a safety net so pages don't need to remember w-full on each action individually. -->
        {#if actions}
            <div class="flex shrink-0 gap-1.5 {!stretchActions ? 'flex-row justify-center flex-wrap' : actionsStacked ? 'flex-col items-stretch *:w-full' : 'grid grid-cols-2 *:w-full'}">
                {@render actions({layoutMode, showActionLabels, stretchActions, actionsStacked})}
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
