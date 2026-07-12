/**
 * Shared responsive layout helper — used by fx/+page.svelte, assets/+page.svelte, and
 * PageToolbar.svelte (dashboard, broker detail).
 *
 * Uses ResizeObserver to determine the current layout mode based on configurable
 * thresholds. Returns reactive $state values for layoutMode and showActionLabels.
 *
 * Thresholds are stored reactively (see `thresholds` on the returned instance) so they can be
 * tuned live from the browser console via `registerLayoutDebug` below — mutating a field (e.g.
 * `instance.thresholds.compact = 300`) recomputes layoutMode immediately, no resize needed.
 */

export interface LayoutThresholds {
    wide: number; // e.g., FX: 1030, Asset: 1240
    tablet: number; // e.g., FX: 700,  Asset: 920
    tabletS: number; // e.g., FX: 530,  Asset: 500
    labelHide: number; // Both: 460
    /** Optional 5th, narrower-than-mobile breakpoint. Only used when explicitly provided —
     *  omitting it (existing callers, e.g. assets/fx) preserves the classic 4-mode behavior
     *  unchanged. Meant for callers (e.g. PageToolbar) that need an ultra-narrow fallback state
     *  (icon-only row) below their normal "mobile" treatment. */
    compact?: number;
}

export type LayoutMode = 'wide' | 'tablet' | 'tablet-s' | 'mobile' | 'compact';

/**
 * Creates a ResizeObserver-based responsive layout tracker.
 * Call attach(el) in $effect, returns reactive getters.
 *
 * @example
 * ```svelte
 * const layout = createResponsiveLayout({wide: 1030, tablet: 700, tabletS: 530, labelHide: 460});
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
    // Defaults to the tablet threshold so the pre-attach layoutMode matches the old hardcoded
    // 'tablet' default (wide is always > tablet, so this satisfies w>=tablet but not w>=wide).
    let width = $state(initialThresholds.tablet);
    let observer: ResizeObserver | null = null;

    let layoutMode = $derived.by((): LayoutMode => {
        const w = width;
        if (w >= thresholds.wide) return 'wide';
        if (w >= thresholds.tablet) return 'tablet';
        if (w >= thresholds.tabletS) return 'tablet-s';
        if (thresholds.compact != null && w < thresholds.compact) return 'compact';
        return 'mobile';
    });
    let showActionLabels = $derived(width >= thresholds.labelHide);

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
 *   window.__lfLayouts.dashboard.thresholds.compact = 300
 *   window.__lfLayouts.assetsList.thresholds.tabletS = 550
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
    // Merge-safe: DateRangePicker (via attachLayoutDebugExtra, e.g. for pickerConfig) and
    // PageToolbar/the page itself (via this function, for thresholds/layoutMode) can run in
    // EITHER order depending on the page — Svelte doesn't guarantee which sibling/child
    // component's script runs first. Preserve whatever the other side already put on this same
    // registry entry instead of blindly overwriting it.
    if (existing) Object.assign(layout as unknown as Record<string, unknown>, existing);
    w.__lfLayouts[name] = layout as unknown as Record<string, unknown>;
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
