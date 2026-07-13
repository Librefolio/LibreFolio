/**
 * Shared responsive layout helper — used by fx/+page.svelte, assets/+page.svelte, and
 * PageToolbar.svelte (dashboard, broker detail).
 *
 * Uses ResizeObserver to determine the current layout mode based on configurable
 * thresholds. Returns reactive $state values for layoutMode and showActionLabels.
 *
 * Thresholds are stored reactively (see `thresholds` on the returned instance) so they can be
 * tuned live from the browser console via `registerLayoutDebug` below — mutating a field (e.g.
 * `instance.thresholds.iconOnly = 300`) recomputes layoutMode immediately, no resize needed.
 */

export interface LayoutThresholds {
    /** Min width for the DateRangePicker to render as a SINGLE row (badges shed via real
     *  measurement as space shrinks). Below this: picker is ALWAYS 2 internal rows — a direct,
     *  deterministic switch driven by this threshold, not by autonomous content measurement. */
    oneRow: number; // e.g., FX: 1030, Asset: 1240
    /** Below `oneRow`, still side-by-side (Center beside the picker, actions still 2×2) — same
     *  PageToolbar structure as `oneRow`, just denser. Some pages (e.g. assets list) use crossing
     *  this threshold to reflow their OWN "Centro" content (e.g. search+filters block goes from
     *  inline to an internal 2-row block) even though the outer row stays side-by-side. */
    denseRow: number; // e.g., FX: 700,  Asset: 920
    /** Below this: Center moves BELOW the DateRangePicker (both stack into one "justified" —
     *  start-aligned, full-width — column). Actions stay a 2×2 grid, but BESIDE that column
     *  (whole bar is still a row: `[Picker+Centro column] ─── [Azioni 2×2]`). */
    stackFilters: number; // e.g., FX: 530,  Asset: 500
    /** Below this: the WHOLE bar becomes a single column — Picker, Centro AND Azioni now stack
     *  one under the other (previously the unnamed "mobile" gap; Round 11 gives it its own name
     *  + dedicated threshold since Azioni moving here is a first-class layout decision, not an
     *  afterthought). Azioni stay a 2×2 grid WITH labels here — only their position changes
     *  (from beside to below); `iconOnly` below is what strips labels/switches to icon-only. */
    oneColumn: number; // e.g., dashboard: 365, brokerDetail: 470
    /** Below this width the textual labels on action buttons hide (icon-only). Independent axis
     *  from everything else here — usually (but not necessarily) equal to `iconOnly`. */
    labelHide: number; // Both: 460
    /** Narrowest tier: same single-column structure as `oneColumn`, but Azioni (and Tabs, if
     *  any) additionally lose their text labels and reflow from a 2×2 grid into a single
     *  centered, wrapping icon-only row — the last-resort fallback when even a labeled 2×2 grid
     *  no longer fits. */
    iconOnly: number; // Both: 330
}

export type LayoutMode = 'oneRow' | 'denseRow' | 'stackFilters' | 'oneColumn' | 'iconOnly';

/**
 * Creates a ResizeObserver-based responsive layout tracker.
 * Call attach(el) in $effect, returns reactive getters.
 *
 * @example
 * ```svelte
 * const layout = createResponsiveLayout({oneRow: 1030, denseRow: 700, stackFilters: 530, oneColumn: 460, labelHide: 400, iconOnly: 400});
 * $effect(() => {
 *     const el = filterBarRef;
 *     if (!el) return;
 *     layout.attach(el);
 *     return () => layout.detach();
 * });
 * ```
 */
export function createResponsiveLayout(initialThresholds: LayoutThresholds) {
    // Reactive copy — mutating any field (typically from the console debug registry) recomputes
    // layoutMode/showActionLabels immediately via the $derived below, without needing a resize.
    const thresholds = $state({...initialThresholds});
    // Defaults to the denseRow threshold so the pre-attach layoutMode matches the old hardcoded
    // 'denseRow' default (oneRow is always > denseRow, so this satisfies w>=denseRow but not w>=oneRow).
    let width = $state(initialThresholds.denseRow);
    let observer: ResizeObserver | null = null;

    // Round 10.2: layoutMode values match the threshold names exactly (one threshold, one
    // matching mode name) — no more "two vocabularies" to keep in sync. Round 11: the former
    // unnamed "mobile" gap (between stackFilters and iconOnly) is now itself a named, thresholded
    // tier ("oneColumn") — every tier has its own dedicated threshold, no exceptions, no nullable
    // checks needed below.
    let layoutMode = $derived.by((): LayoutMode => {
        const w = width;
        if (w >= thresholds.oneRow) return 'oneRow';
        if (w >= thresholds.denseRow) return 'denseRow';
        if (w >= thresholds.stackFilters) return 'stackFilters';
        if (w >= thresholds.oneColumn) return 'oneColumn';
        return 'iconOnly';
    });
    let showActionLabels = $derived(width >= thresholds.labelHide);

    function attach(el: HTMLElement) {
        detach(); // cleanup previous
        observer = new ResizeObserver((entries) => {
            const entry = entries[0];
            // Round 11.1: back to CONTENT-BOX (contentRect), reverting the Round 10.3 border-box
            // attempt — confirmed by direct user measurement that border-box was the wrong
            // choice: user debugs by reading the INTERIOR width (excludes the bar's own `p-4` =
            // 32px horizontal padding), not the full border-box size, so comparing thresholds
            // against border-box made every breakpoint appear to fire ~32px "late" relative to
            // what the user actually reads/resizes to. contentRect is also the ResizeObserver
            // default (no `box` option needed), simpler and more broadly supported than
            // borderBoxSize.
            width = entry.contentRect.width;
        });
        observer.observe(el);
    }

    function detach() {
        if (observer) {
            observer.disconnect();
            observer = null;
        }
    }

    return {
        get layoutMode() {
            return layoutMode;
        },
        get showActionLabels() {
            return showActionLabels;
        },
        get width() {
            return width;
        },
        /** Reactive thresholds — mutate fields to live-tune breakpoints (see registerLayoutDebug). */
        thresholds,
        attach,
        detach,
    };
}

export type ResponsiveLayout = ReturnType<typeof createResponsiveLayout>;

/**
 * Registers a layout instance on `window.__lfLayouts.<name>` for live threshold tuning from the
 * browser console, e.g.:
 *
 *   window.__lfLayouts.dashboard.thresholds.iconOnly = 300
 *   window.__lfLayouts.assetsList.thresholds.stackFilters = 550
 *
 * Recomputes layoutMode immediately (no resize needed) since thresholds are read reactively.
 * Always available — not gated behind a debug flag — since this is a harmless numeric knob and
 * the whole point is tuning breakpoints live on a local prod build without rebuilding.
 */
export function registerLayoutDebug(name: string, layout: ResponsiveLayout) {
    if (typeof window === 'undefined') return;
    const w = window as unknown as {__lfLayouts?: Record<string, Record<string, unknown>>};
    w.__lfLayouts ??= {};
    const existing = w.__lfLayouts[name];
    const target = layout as unknown as Record<string, unknown>;
    // Merge-safe: DateRangePicker (via attachLayoutDebugExtra, e.g. for pickerConfig) and
    // PageToolbar/the page itself (via this function, for thresholds/layoutMode) can run in
    // EITHER order depending on the page — Svelte doesn't guarantee which sibling/child
    // component's script runs first. Preserve whatever the other side already put on this same
    // registry entry instead of blindly overwriting it.
    //
    // Only copy keys that DON'T already exist on the fresh `layout` — never blindly
    // Object.assign the whole `existing` object onto it. `existing` can also be a STALE
    // ResponsiveLayout from a previous mount of the same page (e.g. client-side back/forward
    // navigation remounts the page and calls this again for the same `name`): its
    // `layoutMode`/`showActionLabels`/`width` are getter-only accessors, and so are the fresh
    // `layout`'s — writing one getter's value onto another throws "Cannot set property ... which
    // has only a getter". Skipping keys already present on `target` avoids that entirely while
    // still bringing over genuine extras (e.g. `pickerConfig`).
    if (existing) {
        for (const key of Object.keys(existing)) {
            if (!(key in target)) target[key] = existing[key];
        }
    }
    w.__lfLayouts[name] = target;
}

/**
 * Attaches extra reactive fields to `window.__lfLayouts.<name>` for live console tuning, without
 * requiring a full `ResponsiveLayout` instance — used by components (e.g. DateRangePicker, for
 * its own `pickerConfig.maxWidth`) that live alongside but independently of a page's
 * `createResponsiveLayout`/`registerLayoutDebug` call. Merge-safe in the same way as
 * `registerLayoutDebug` — safe to call before OR after it, for the same `name`.
 *
 * Example: `attachLayoutDebugExtra('dashboard', {pickerConfig})` then, from the console:
 *   window.__lfLayouts.dashboard.pickerConfig.maxWidth = 900
 */
export function attachLayoutDebugExtra(name: string, extra: Record<string, unknown>) {
    if (typeof window === 'undefined') return;
    const w = window as unknown as {__lfLayouts?: Record<string, Record<string, unknown>>};
    w.__lfLayouts ??= {};
    w.__lfLayouts[name] = Object.assign(w.__lfLayouts[name] ?? {}, extra);
}
