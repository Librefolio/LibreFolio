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
     *  start-aligned, full-width — column). Actions stay a 2×2 grid (beside the stacked column). */
    stackFilters: number; // e.g., FX: 530,  Asset: 500
    /** Below this width the textual labels on action buttons hide (icon-only). Independent axis
     *  from everything else here — usually (but not necessarily) equal to `iconOnly`. */
    labelHide: number; // Both: 460
    /** Optional 5th, narrower-than-mobile breakpoint. Only used when explicitly provided —
     *  omitting it (existing callers, e.g. assets/fx) preserves the classic 4-mode behavior
     *  unchanged. Meant for callers (e.g. PageToolbar) that need an ultra-narrow fallback state
     *  (icon-only row) below their normal "mobile" treatment. */
    iconOnly?: number;
    /** Optional — only meaningful strictly BETWEEN `stackFilters` and `iconOnly` (i.e. within
     *  what `layoutMode` calls "mobile"). Above this value (down to `stackFilters`): actions
     *  render as a 4×1 vertical column instead of a 2×2 grid. Below this value (down to
     *  `iconOnly`): actions revert to the 2×2 grid — a narrow "column" sub-band, not a whole new
     *  tier. Omit to skip the column state entirely (actions stay 2×2 all the way to `iconOnly`). */
    actionsColumn?: number;
}

export type LayoutMode = 'oneRow' | 'denseRow' | 'stackFilters' | 'mobile' | 'iconOnly';

/**
 * Creates a ResizeObserver-based responsive layout tracker.
 * Call attach(el) in $effect, returns reactive getters.
 *
 * @example
 * ```svelte
 * const layout = createResponsiveLayout({oneRow: 1030, denseRow: 700, stackFilters: 530, labelHide: 460});
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

    // Round 10.2: layoutMode values now match the threshold names exactly (one threshold, one
    // matching mode name) — no more "two vocabularies" to keep in sync. 'mobile' is the only
    // exception: it has no single dedicated threshold of its own (it's simply the range between
    // `stackFilters` and `iconOnly`), so it keeps its original name.
    let layoutMode = $derived.by((): LayoutMode => {
        const w = width;
        if (w >= thresholds.oneRow) return 'oneRow';
        if (w >= thresholds.denseRow) return 'denseRow';
        if (w >= thresholds.stackFilters) return 'stackFilters';
        if (thresholds.iconOnly != null && w < thresholds.iconOnly) return 'iconOnly';
        return 'mobile';
    });
    let showActionLabels = $derived(width >= thresholds.labelHide);

    // Actions become a 4×1 column ONLY in a narrow sub-band strictly inside "mobile" (between
    // stackFilters and iconOnly) — never in oneRow/denseRow/stackFilters (always 2×2 there) nor
    // once width drops below actionsColumn (back to 2×2, "true mobile"). Omitting actionsColumn
    // keeps the pre-Round-10 behavior: always 2×2 up to iconOnly.
    let actionsStacked = $derived(layoutMode === 'mobile' && thresholds.actionsColumn != null && width >= thresholds.actionsColumn);

    function attach(el: HTMLElement) {
        detach(); // cleanup previous
        observer = new ResizeObserver(([entry]) => {
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
        get actionsStacked() {
            return actionsStacked;
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
