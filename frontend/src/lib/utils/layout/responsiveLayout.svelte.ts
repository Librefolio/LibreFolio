/**
 * Shared responsive layout helper — used by fx/+page.svelte and assets/+page.svelte.
 *
 * Uses ResizeObserver to determine the current layout mode based on configurable
 * thresholds. Returns reactive $state values for layoutMode and showActionLabels.
 */

export interface LayoutThresholds {
    wide: number; // e.g., FX: 1030, Asset: 1240
    tablet: number; // e.g., FX: 700,  Asset: 920
    tabletS: number; // e.g., FX: 530,  Asset: 500
    labelHide: number; // Both: 460
}

export type LayoutMode = 'wide' | 'tablet' | 'tablet-s' | 'mobile';

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
export function createResponsiveLayout(thresholds: LayoutThresholds) {
    let layoutMode = $state<LayoutMode>('tablet');
    let showActionLabels = $state(true);
    let observer: ResizeObserver | null = null;

    function attach(el: HTMLElement) {
        detach(); // cleanup previous
        observer = new ResizeObserver(([entry]) => {
            const w = entry.contentRect.width;
            if (w >= thresholds.wide) layoutMode = 'wide';
            else if (w >= thresholds.tablet) layoutMode = 'tablet';
            else if (w >= thresholds.tabletS) layoutMode = 'tablet-s';
            else layoutMode = 'mobile';
            showActionLabels = w >= thresholds.labelHide;
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
        attach,
        detach,
    };
}
