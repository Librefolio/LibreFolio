/**
 * Shared responsive layout helper — used by fx/+page.svelte, assets/+page.svelte, and
 * PageToolbar.svelte (dashboard, broker detail).
 *
 * Uses ResizeObserver to determine the current layout mode based on configurable
 * thresholds. Returns reactive $state values for layoutMode and showActionLabels.
 *
 * Thresholds are stored reactively (see `thresholds` on the returned instance) so they can be
 * tuned live from the browser console via `registerLayoutDebug` below — mutating a field (e.g.
 * `instance.thresholds.stackFilters = 300`) recomputes layoutMode immediately, no resize needed.
 *
 * ⚠️ Round 12.1: `thresholds.oneColumn` is the one exception — it's currently INERT (see the
 * comment on its declaration below and on the `layoutMode` derivation) because `oneColumn` is
 * the narrowest tier today, with nothing left below it to bound. Left in place on purpose for a
 * possible future narrower sub-tier, not dead code to clean up.
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
     *  (from beside to below). This is now the NARROWEST tier (Round 12 removed the separate
     *  `iconOnly` tier below it — labels never disappear on their own anymore; see
     *  `labelHideActions`/`labelHideTabs`, the only remaining independent axes for that).
     *
     *  ⚠️ Round 12.1: this NUMBER currently has NO effect on `layoutMode` — since `oneColumn` is
     *  the narrowest tier (nothing left below it to bound), the derivation below falls through
     *  to `'oneColumn'` unconditionally once width drops under `stackFilters`, without ever
     *  comparing against this value. Confirmed by live tuning: crossing it produces no visible
     *  change, by design, not a bug. Kept (not removed) so a future narrower sub-tier can reuse
     *  this exact threshold slot without another rename/migration across all 6 pages. */
    oneColumn: number; // e.g., dashboard: 365, brokerDetail: 470
    /** Below this width the textual labels on action buttons hide entirely. Independent axis
     *  from the tier system above — tuned per-page. Split from a single shared `labelHide`
     *  (Round 13) after live tuning showed Actions and Tabs need different values — this one
     *  is the Actions half; see `labelHideTabs` for the Tab half. No longer tied to a matching
     *  `iconOnly` layout tier (removed in Round 12; labels shrink via `labelShrink.ts` before
     *  ever reaching this threshold, see TabBar.svelte/PageToolbar.svelte). */
    labelHideActions: number; // Both: 250
    /** Below this width the textual labels on Tab buttons hide entirely — the Tab half of the
     *  Round 13 `labelHide` split (see `labelHideActions` above for the Actions half). Same
     *  independent-axis rationale, tuned separately because Tab labels and Action labels don't
     *  need to disappear at the same width in practice. */
    labelHideTabs: number; // Both: 370
    /** Optional (Round 13) — independent of the tier system AND of `labelHideActions`/
     *  `labelHideTabs` above. Below this width, a page can hide one or more of its OWN "extra"
     *  decorative labels (e.g. dashboard's "Valuta:" text prefix in front of the currency
     *  selector) while keeping the actual control itself — read via `showExtraLabels` in the
     *  `filters`/`summary` snippet. Optional and per-page opt-in: omit it entirely on pages that
     *  don't have such an extra label to shed (their `showExtraLabels` then defaults to always
     *  `true`, i.e. today's unaffected behavior). Not part of the `LayoutMode` tier system on
     *  purpose — nothing structural changes at this width, only this one label's visibility. */
    noExtraLabel?: number; // e.g., dashboard: 300
}

export type LayoutMode = 'oneRow' | 'denseRow' | 'stackFilters' | 'oneColumn';

/**
 * Creates a ResizeObserver-based responsive layout tracker.
 * Call attach(el) in $effect, returns reactive getters.
 *
 * @example
 * ```svelte
 * const layout = createResponsiveLayout({oneRow: 1030, denseRow: 700, stackFilters: 530, oneColumn: 460, labelHideActions: 250, labelHideTabs: 370});
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
    // checks needed below. Round 12: the separate `iconOnly` tier below `oneColumn` was removed
    // entirely (labels never auto-hide via a layout tier anymore — see `labelHideActions`/
    // `labelHideTabs`/`labelShrink.ts` for how narrow labels are now handled instead) —
    // `oneColumn` is the narrowest tier, a plain fallback below `stackFilters`.
    let layoutMode = $derived.by((): LayoutMode => {
        const w = width;
        if (w >= thresholds.oneRow) return 'oneRow';
        if (w >= thresholds.denseRow) return 'denseRow';
        if (w >= thresholds.stackFilters) return 'stackFilters';
        // Round 12.1: `thresholds.oneColumn` is intentionally NEVER read here — with `iconOnly`
        // gone, there's no narrower tier left to bound it against, so once width drops under
        // `stackFilters` we're unconditionally in 'oneColumn' regardless of its numeric value.
        // Confirmed by the user's own live tuning (moving the threshold produces no change).
        // The field stays in LayoutThresholds/all 6 pages' config anyway — not dead code to
        // delete, just a currently-inert knob reserved for a possible future narrower sub-tier.
        return 'oneColumn';
    });
    // Round 13: split from a single shared `labelHide` — Actions and Tabs labels don't need to
    // disappear at the same width in practice (live-tuned: 250 for Actions, 370 for Tabs).
    let showActionLabels = $derived(width >= thresholds.labelHideActions);
    let showTabLabels = $derived(width >= thresholds.labelHideTabs);
    // Round 13: independent, OPTIONAL, per-page axis — defaults to always-shown when a page
    // doesn't configure it (the 5 pages without an "extra" decorative label to shed today).
    let showExtraLabels = $derived(thresholds.noExtraLabel == null || width >= thresholds.noExtraLabel);

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
        get showTabLabels() {
            return showTabLabels;
        },
        get showExtraLabels() {
            return showExtraLabels;
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
 *   window.__lfLayouts.dashboard.thresholds.stackFilters = 550
 *   window.__lfLayouts.assetsList.thresholds.denseRow = 900
 *
 * Recomputes layoutMode immediately (no resize needed) since thresholds are read reactively.
 * Always available — not gated behind a debug flag — since this is a harmless numeric knob and
 * the whole point is tuning breakpoints live on a local prod build without rebuilding.
 * (`thresholds.oneColumn` is the one exception, currently inert — see its declaration in
 * `LayoutThresholds` above.)
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
