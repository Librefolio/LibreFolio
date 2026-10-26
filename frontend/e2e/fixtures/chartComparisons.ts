/**
 * Saved chart comparisons, for the specs that need a card to draw one (lot Y-41).
 *
 * The chart settings live in the browser's `localStorage` (`chartSettingsStore`, under the user's id): seeding them
 * writes nothing shared, and the next page load reads them. A comparison is saved as a config (`asset-comparison` with
 * `params.assetId`, `fx-pair` with `params.pairSlug`); the series it draws are the page's to load, which is what the
 * specs read: a card publishes how many overlay lines it draws (`data-overlay-count`), so no spec reads a canvas.
 */

import {expect, type Page} from '@playwright/test';

/** A saved comparison, as the settings keep it. */
export interface SavedComparison {
    id: string;
    signalType: 'asset-comparison' | 'fx-pair';
    params: Record<string, unknown>;
    style: {color: string; lineWidth: number; lineType: 'solid'; markerStart: null; markerEnd: null};
}

const style = (color: string) => ({color, lineWidth: 2, lineType: 'solid' as const, markerStart: null, markerEnd: null});

/** A comparison with an asset. */
export function assetComparison(id: string, assetId: number, color = '#f59e0b'): SavedComparison {
    return {id, signalType: 'asset-comparison', params: {assetId}, style: style(color)};
}

/** A comparison with an FX pair. */
export function pairComparison(id: string, pairSlug: string, color = '#10b981'): SavedComparison {
    return {id, signalType: 'fx-pair', params: {pairSlug}, style: style(color)};
}

/** The id of an asset of the signed-in user, by its exact name (the seeded mock data's). */
export async function assetIdByName(page: Page, name: string): Promise<number> {
    const response = await page.request.get('/api/v1/assets/query');
    expect(response.ok(), `GET /api/v1/assets/query answered HTTP ${response.status()}`).toBe(true);
    const assets = (await response.json()) as Array<{id: number; display_name: string}>;
    const found = assets.find((asset) => asset.display_name === name);
    if (!found) throw new Error(`the seeded asset «${name}» is not listed: it comes from populate_mock_data.py`);
    return found.id;
}

/**
 * Seed the chart settings of the signed-in user: each `[slug, comparisons]` is the settings of that chart alone (an asset
 * card's slug is `asset-<id>`, an FX card's `EUR-USD`), the rest default. Run it after a first navigation, so that the
 * page it is called on holds the origin's storage; the next load reads it.
 */
export async function seedChartComparisons(page: Page, perChart: ReadonlyArray<readonly [string, ReadonlyArray<SavedComparison>]>): Promise<void> {
    const me = await page.request.get('/api/v1/auth/me');
    expect(me.ok(), `GET /api/v1/auth/me answered HTTP ${me.status()}`).toBe(true);
    const userId = ((await me.json()) as {user?: {id?: unknown}}).user?.id;
    if (typeof userId !== 'number' || !Number.isSafeInteger(userId)) throw new Error(`GET /api/v1/auth/me gave no user id (${String(userId)}): the chart settings are stored under it`);
    await page.evaluate(
        ({storageKey, charts}) => {
            const base = {colorByBaseline: true, areaFill: true, gridLines: true, staleGradient: true, axisScales: {absolute: {mode: 'auto'}, percentage: {mode: 'include0'}, secondary: {}}, primaryView: 'percentage', signals: [] as unknown[]};
            localStorage.setItem(storageKey, JSON.stringify({version: 3, globalSettings: base, pairOverrides: charts.map(([slug, signals]) => [slug, {...base, signals}])}));
        },
        {storageKey: `lf_${userId}_chartSettingsStore`, charts: perChart.map(([slug, signals]) => [slug, [...signals]] as const)},
    );
}
