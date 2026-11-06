/**
 * The icons of the allocation pie by asset (F-10, B8): each slice wears its asset's own icon, else its type's. The cash slice (no id) wears
 * the Liquidity one.
 *
 * ECharts draws a rich-text image with no hook for a failed load, so an own icon is probed first: until the probe says it loads, and for good
 * when it does not (a dead link, a foreign site that refuses), the slice wears the type's icon. A rebuild follows each answer.
 *
 * @module components/charts/assetPieIcons
 */

import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';

/** What the icon of a slice depends on. */
export interface AssetSliceIconSource {
    /** The asset's id; null for the cash slice. */
    assetId: number | null;
    /** The asset's own icon, when it has one. */
    iconUrl?: string | null;
    /** The asset's type, for its icon when it has no icon of its own. */
    assetType?: string | null;
}

/** The icon URL a slice draws: the own one once it is known to load, else the type's (the cash: Liquidity). */
export function assetSliceIconUrl(slice: AssetSliceIconSource, loaded: ReadonlySet<string>): string {
    if (slice.assetId === null || slice.assetId === undefined) return getAssetTypeIconUrl('LIQUIDITY');
    const own = (slice.iconUrl ?? '').trim();
    if (own !== '' && loaded.has(own)) return own;
    return getAssetTypeIconUrl(slice.assetType);
}

/** Loads an image to see whether it can be drawn. The default is the browser's. */
export type ImageLoader = (url: string) => Promise<boolean>;

export const browserImageLoader: ImageLoader = (url) =>
    new Promise((resolve) => {
        if (typeof Image === 'undefined') return resolve(false);
        const image = new Image();
        image.onload = () => resolve(true);
        image.onerror = () => resolve(false);
        image.src = url;
    });

/**
 * The answers of the probes, per URL: each URL is asked once. `onchange` runs after a probe that found the image loadable (a failure changes
 * nothing: the type's icon is already drawn).
 */
export function createIconProbe(load: ImageLoader = browserImageLoader, onchange: () => void = () => {}) {
    const loaded = new Set<string>();
    const asked = new Set<string>();
    let disposed = false;
    return {
        /** The URLs known to load. */
        loaded: loaded as ReadonlySet<string>,
        /** Asks, once each, for the own icons of these slices. */
        ask(slices: ReadonlyArray<AssetSliceIconSource>): void {
            for (const slice of slices) {
                const url = (slice.iconUrl ?? '').trim();
                if (slice.assetId === null || slice.assetId === undefined || url === '' || asked.has(url)) continue;
                asked.add(url);
                void load(url)
                    .catch(() => false)
                    .then((ok) => {
                        if (!ok || disposed) return;
                        loaded.add(url);
                        onchange();
                    });
            }
        },
        dispose(): void {
            disposed = true;
        },
    };
}
