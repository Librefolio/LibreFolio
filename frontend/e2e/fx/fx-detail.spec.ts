/**
 * FX Detail Page — E2E Tests
 *
 * Tests the FX detail page: chart rendering, panels, swap direction, sync.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 *   EUR-USD pair must exist.
 */

import type {Route} from '@playwright/test';
import {expect, test as base} from '../fixtures/playwright';
import type {Locator, Page, Request, Response} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
import {daysAgoIso, localIso, todayIso} from '../fixtures/dates';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxDetailPage} from './fx-helpers';

type SyntheticRange = {
    start: string;
    end: string;
};

type SyntheticSignal = {
    id: string;
    signalType: 'asset-comparison';
    params: {assetId: string};
    style: {
        color: string;
        lineWidth: number;
        lineType: 'solid' | 'dashed' | 'dotted';
        markerStart: null;
        markerEnd: null;
    };
};

type DeferredGate = {
    wait: Promise<void>;
    release: () => void;
};

type ControlledPlan<T> = {
    id: string;
    outcome: T;
    hold: DeferredGate | null;
    entered: DeferredGate;
    completed: DeferredGate;
    requestBody?: unknown;
};

function createDeferredGate(): DeferredGate {
    let release!: () => void;
    const wait = new Promise<void>((resolve) => {
        release = resolve;
    });
    return {wait, release};
}

function createControlledPlan<T>(id: string, outcome: T, held = false): ControlledPlan<T> {
    return {
        id,
        outcome,
        hold: held ? createDeferredGate() : null,
        entered: createDeferredGate(),
        completed: createDeferredGate(),
    };
}

function comparisonSignal(id: string, assetId: number, color: string): SyntheticSignal {
    return {
        id,
        signalType: 'asset-comparison',
        params: {assetId: String(assetId)},
        style: {
            color,
            lineWidth: 2,
            lineType: 'solid',
            markerStart: null,
            markerEnd: null,
        },
    };
}

function syntheticChartSettings(signals: SyntheticSignal[]) {
    return {
        colorByBaseline: true,
        areaFill: true,
        gridLines: true,
        staleGradient: true,
        axisScales: {
            absolute: {mode: 'auto'},
            percentage: {mode: 'include0'},
            secondary: {},
        },
        signals,
    };
}

async function seedSyntheticChartSettings(page: Page, entries: Array<[string, SyntheticSignal[]]>): Promise<void> {
    const meResponse = await page.request.get('/api/v1/auth/me');
    expect(meResponse.ok()).toBe(true);
    const mePayload = (await meResponse.json()) as {user?: {id?: unknown}};
    const userId = mePayload.user?.id;
    expect(userId, 'authenticated user id is required for synthetic chart settings').toEqual(expect.any(Number));
    if (typeof userId !== 'number' || !Number.isSafeInteger(userId)) {
        throw new Error('GET /api/v1/auth/me did not return a safe integer user id');
    }

    await page.evaluate(
        ({storageKey, pairOverrides}) => {
            const emptySettings = {
                colorByBaseline: true,
                areaFill: true,
                gridLines: true,
                staleGradient: true,
                axisScales: {
                    absolute: {mode: 'auto'},
                    percentage: {mode: 'include0'},
                    secondary: {},
                },
                signals: [],
            };
            localStorage.setItem(
                storageKey,
                JSON.stringify({
                    version: 2,
                    globalSettings: emptySettings,
                    pairOverrides,
                }),
            );
        },
        {
            storageKey: `lf_${userId}_chartSettingsStore`,
            pairOverrides: entries.map(([key, signals]) => [key, syntheticChartSettings(signals)]),
        },
    );
}

function waitForTaggedResponse(page: Page, pathname: string, planId: string) {
    return page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === pathname && response.headers()['x-e2e-plan-id'] === planId, {timeout: 10_000});
}

async function ensureSignalsPanelOpen(toggle: Locator, panel: Locator): Promise<void> {
    await expect(toggle).toBeVisible();
    if ((await toggle.getAttribute('aria-expanded')) !== 'true') {
        await toggle.click();
    }
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await expect(panel).toBeVisible();
}

async function cycleSignalsPanel(toggle: Locator, panel: Locator): Promise<void> {
    await ensureSignalsPanelOpen(toggle, panel);
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(panel).toBeHidden();
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await expect(panel).toBeVisible();
}

async function dismissOwnedToast(page: Page, variant: 'success' | 'warning' | 'info' | 'error'): Promise<void> {
    const toast = page.getByTestId(`toast-${variant}`);
    await expect(toast).toHaveCount(1);
    await toast.getByTestId('toast-dismiss').click();
    await expect(toast).toHaveCount(0);
}

async function expectNoSyncToasts(page: Page): Promise<void> {
    for (const variant of ['success', 'warning', 'info', 'error'] as const) {
        await expect(page.getByTestId(`toast-${variant}`)).toHaveCount(0);
    }
}

async function expectComparisonDataState(card: Locator, syncButton: Locator, hasData: boolean): Promise<void> {
    await expect(card).toBeVisible();
    await expect(syncButton).toBeVisible();
    const issue = card.getByTestId('signal-issue');
    if (hasData) {
        await expect(issue).toHaveCount(0);
    } else {
        await expect(issue).toBeVisible();
        await expect(issue).toHaveAttribute('data-severity', 'error');
    }
}

type SyntheticAsset = {
    id: number;
    display_name: string;
    currency: string;
    asset_type: string;
    active: boolean;
    has_metadata: boolean;
    provider_code: string | null;
    tx_count: number;
    tx_count_own: number;
};

type PriceQueryFixture = {
    asset_id?: number;
    date_range?: {start?: string; end?: string};
    include_price?: boolean;
    include_events?: boolean;
    target_currency?: string;
};

type FxConvertRequestFixture = {
    from_amount: {code: string; amount: string | number};
    to: string;
    date_range: {start: string; end?: string | null};
};

type FxSyncStatusFixture = 'ok' | 'partial' | 'failed' | 'skipped';

function parsePriceQueries(raw: unknown): PriceQueryFixture[] {
    return Array.isArray(raw) ? (raw as PriceQueryFixture[]) : [];
}

function requestedAssetIds(raw: unknown): number[] {
    return parsePriceQueries(raw)
        .flatMap((query) => (typeof query.asset_id === 'number' ? [query.asset_id] : []))
        .sort((left, right) => left - right);
}

function matchesAssetIds(raw: unknown, expectedIds: readonly number[]): boolean {
    const actual = requestedAssetIds(raw);
    const expected = [...new Set(expectedIds)].sort((left, right) => left - right);
    return actual.length === expected.length && actual.every((id, index) => id === expected[index]);
}

function assertComparisonRequest(raw: unknown, expectedIds: readonly number[], range: SyntheticRange, targetCurrency?: string): void {
    const queries = parsePriceQueries(raw);
    expect(requestedAssetIds(queries)).toEqual([...new Set(expectedIds)].sort((left, right) => left - right));
    for (const expectedId of new Set(expectedIds)) {
        const query = queries.find((candidate) => candidate.asset_id === expectedId);
        expect(query, `comparison request must contain asset ${expectedId}`).toEqual({
            asset_id: expectedId,
            date_range: range,
            include_events: true,
            ...(targetCurrency ? {target_currency: targetCurrency} : {}),
        });
    }
}

function assertAssetSyncRequest(raw: unknown, assetId: number, range: SyntheticRange): void {
    expect(raw).toEqual([
        {
            asset_id: assetId,
            date_range: range,
        },
    ]);
}

function assertFxSyncRequest(raw: unknown, slug: string, range: SyntheticRange): void {
    expect(raw).toEqual({
        pairs: [slug],
        start: range.start,
        end: range.end,
    });
}

function syntheticPricePoints(range: SyntheticRange, currency: string, seed: number) {
    return [
        {
            date: range.start,
            open: String(seed),
            high: String(seed + 2),
            low: String(seed - 1),
            close: String(seed + 1),
            volume: '100',
            currency,
        },
        {
            date: range.end,
            open: String(seed + 1),
            high: String(seed + 3),
            low: String(seed),
            close: String(seed + 2),
            volume: '110',
            currency,
        },
    ];
}

async function openSyntheticDetail(page: Page, path: string, rootTestId: 'asset-detail-page' | 'fx-detail-page'): Promise<Locator> {
    await navigateTo(page, path);
    const root = page.getByTestId(rootTestId);
    await expect(root).toBeVisible({timeout: 15_000});
    await waitForSettled(root, 20_000);
    return root;
}

async function installAssetFxRetryFixture(page: Page) {
    const range: SyntheticRange = {start: '2026-01-02', end: '2026-06-30'};
    const asset: SyntheticAsset = {
        id: 930_100,
        display_name: 'Synthetic FX retry owner',
        currency: 'EUR',
        asset_type: 'STOCK',
        active: true,
        has_metadata: false,
        provider_code: null,
        tx_count: 0,
        tx_count_own: 0,
    };
    const peers = [
        {
            id: 930_101,
            display_name: 'Synthetic GBP retry peer',
            currency: 'GBP',
            asset_type: 'STOCK',
            slug: 'EUR-GBP',
            signalId: 'asset-fx-retry-gbp',
            color: '#2563eb',
        },
        {
            id: 930_102,
            display_name: 'Synthetic CHF retry peer',
            currency: 'CHF',
            asset_type: 'STOCK',
            slug: 'CHF-EUR',
            signalId: 'asset-fx-retry-chf',
            color: '#dc2626',
        },
    ] as const;
    const signals = peers.map((peer) => comparisonSignal(peer.signalId, peer.id, peer.color));
    const conversionFailures = new Set(peers.map((peer) => peer.slug));
    const syncPlans = new Map<string, Array<ControlledPlan<FxSyncStatusFixture>>>();
    const stats = {
        syncRequests: [] as unknown[],
        unplannedSyncRequests: 0,
        fxRefillRequests: [] as FxConvertRequestFixture[][],
        fxRefillsBySlug: new Map<string, number>(),
        mainPriceRequests: [] as PriceQueryFixture[][],
        comparisonRequests: [] as PriceQueryFixture[][],
    };

    const enqueueSync = (id: string, slug: string, status: FxSyncStatusFixture, held = false) => {
        const plan = createControlledPlan(id, status, held);
        const queued = syncPlans.get(slug) ?? [];
        queued.push(plan);
        syncPlans.set(slug, queued);
        return plan;
    };

    await page.route('**/api/v1/assets/query*', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            json: [
                asset,
                ...peers.map((peer) => ({
                    id: peer.id,
                    display_name: peer.display_name,
                    currency: peer.currency,
                    asset_type: peer.asset_type,
                    active: true,
                    has_metadata: false,
                    provider_code: null,
                    tx_count: 0,
                    tx_count_own: 0,
                })),
            ],
        });
    });

    await page.route('**/api/v1/fx/providers/routes*', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            json: {
                items: peers.map((peer, index) => ({
                    base: peer.slug.split('-').find((code) => code !== 'EUR'),
                    quote: 'EUR',
                    priority: index + 1,
                    chain_steps: [{from: peer.currency, to: 'EUR', provider: 'MOCKFX'}],
                    is_chain: false,
                    providers_used: ['MOCKFX'],
                })),
            },
        });
    });

    await page.route('**/api/v1/assets/prices/query', async (route) => {
        const queries = parsePriceQueries(route.request().postDataJSON());
        const isMainRequest = queries.some((query) => query.asset_id === asset.id);
        if (isMainRequest) stats.mainPriceRequests.push(queries);
        else stats.comparisonRequests.push(queries);

        const items = queries
            .map((query) => {
                const requestedId = query.asset_id;
                const requestedRange: SyntheticRange = {
                    start: query.date_range?.start ?? range.start,
                    end: query.date_range?.end ?? range.end,
                };
                if (requestedId === asset.id) {
                    return {
                        asset_id: asset.id,
                        prices: query.include_price === false ? [] : syntheticPricePoints(requestedRange, asset.currency, 100),
                        events: [],
                        errors: [],
                        signals: [],
                    };
                }
                const peer = peers.find((candidate) => candidate.id === requestedId);
                if (!peer) throw new Error(`Unexpected synthetic comparison asset: ${String(requestedId)}`);
                const conversionFailed = conversionFailures.has(peer.slug);
                return {
                    asset_id: peer.id,
                    prices: syntheticPricePoints(requestedRange, conversionFailed ? peer.currency : asset.currency, peer.id - 930_000),
                    events: [],
                    errors: conversionFailed ? [`synthetic-conversion-failure-${peer.slug}`] : [],
                    signals: [],
                };
            })
            .reverse();
        await route.fulfill({status: 200, contentType: 'application/json', json: {items}});
    });

    await page.route('**/api/v1/assets/prices/current', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            json: {results: [], success_count: 0, errors: []},
        });
    });

    await page.route('**/api/v1/fx/currencies/convert', async (route) => {
        const requests = route.request().postDataJSON() as FxConvertRequestFixture[];
        stats.fxRefillRequests.push(requests);
        for (const request of requests) {
            const slug = [request.from_amount.code, request.to].sort((left, right) => left.localeCompare(right)).join('-');
            stats.fxRefillsBySlug.set(slug, (stats.fxRefillsBySlug.get(slug) ?? 0) + 1);
        }
        const results = requests.flatMap((request) => {
            const dates = request.date_range.end && request.date_range.end !== request.date_range.start ? [request.date_range.start, request.date_range.end] : [request.date_range.start];
            return dates.map((date) => ({
                from_amount: {code: request.from_amount.code, amount: String(request.from_amount.amount)},
                to_amount: {code: request.to, amount: '1.25'},
                conversion_date: date,
                rate: '1.25',
                backward_fill_info: null,
            }));
        });
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            json: {results, success_count: results.length, signal_results: []},
        });
    });

    await page.route('**/api/v1/fx/currencies/sync', async (route) => {
        const requestBody = route.request().postDataJSON() as {pairs?: unknown; start?: unknown; end?: unknown};
        const pairs = Array.isArray(requestBody.pairs) ? requestBody.pairs.filter((pair): pair is string => typeof pair === 'string') : [];
        const slug = pairs.find((candidate) => syncPlans.has(candidate));
        const plan = slug ? syncPlans.get(slug)?.shift() : undefined;
        stats.syncRequests.push(requestBody);
        if (!slug || pairs.length !== 1 || !plan) {
            stats.unplannedSyncRequests += 1;
            await route.fulfill({
                status: 500,
                contentType: 'application/json',
                json: {detail: `Unexpected synthetic FX sync: ${JSON.stringify(requestBody)}`},
            });
            return;
        }
        plan.requestBody = requestBody;
        plan.entered.release();
        if (plan.hold) await plan.hold.wait;
        const accepted = plan.outcome === 'ok' || plan.outcome === 'partial';
        try {
            await route.fulfill({
                status: 200,
                headers: {'x-e2e-plan-id': plan.id},
                contentType: 'application/json',
                json: {
                    results: [
                        {
                            pair: slug,
                            status: plan.outcome,
                            points_fetched: accepted ? 2 : 0,
                            points_changed: accepted ? 2 : 0,
                            provider_used: accepted ? 'MOCKFX' : null,
                            message: accepted ? null : `synthetic-${plan.outcome}`,
                            errors: accepted ? [] : [`synthetic-${plan.outcome}`],
                        },
                    ],
                    success_count: accepted ? 1 : 0,
                    date_range: {start: requestBody.start, end: requestBody.end},
                    total_points_changed: accepted ? 2 : 0,
                },
            });
        } finally {
            plan.completed.release();
        }
    });

    await seedSyntheticChartSettings(page, [[`asset-${asset.id}`, signals]]);

    return {
        asset,
        peers,
        range,
        conversionFailures,
        enqueueSync,
        stats,
    };
}

type AssetSyncOutcomeFixture = FxSyncStatusFixture | 'missing-result' | 'transport-error';

function assetSyncResponseBody(assetId: number, outcome: AssetSyncOutcomeFixture) {
    if (outcome === 'transport-error') {
        return {detail: 'synthetic-asset-sync-transport-error'};
    }
    if (outcome === 'missing-result') {
        return {results: [], success_count: 0, errors: []};
    }
    const accepted = outcome === 'ok' || outcome === 'partial';
    return {
        results: [
            {
                asset_id: assetId,
                status: outcome,
                points_fetched: accepted ? 2 : 0,
                points_changed: accepted ? 2 : 0,
                provider_used: accepted ? 'MOCKASSET' : null,
                changed_points: [],
                events_fetched: 0,
                events_changed: 0,
                errors: accepted ? [] : [`synthetic-${outcome}`],
            },
        ],
        success_count: accepted ? 1 : 0,
        errors: accepted ? [] : [`synthetic-${outcome}`],
    };
}

async function installFxComparisonSyncFixture(page: Page) {
    const range: SyntheticRange = {start: '2026-02-01', end: '2026-06-30'};
    const changedRange: SyntheticRange = {start: '2026-03-01', end: '2026-07-31'};
    const peer: SyntheticAsset = {
        id: 930_201,
        display_name: 'Synthetic FX detail comparison peer',
        currency: 'GBP',
        asset_type: 'STOCK',
        active: true,
        has_metadata: false,
        provider_code: 'MOCKASSET',
        tx_count: 0,
        tx_count_own: 0,
    };
    const replacementPeer: SyntheticAsset = {
        id: 930_202,
        display_name: 'Synthetic FX detail replacement peer',
        currency: 'CAD',
        asset_type: 'STOCK',
        active: true,
        has_metadata: false,
        provider_code: 'MOCKASSET',
        tx_count: 0,
        tx_count_own: 0,
    };
    const peers = [peer, replacementPeer] as const;
    const signal = comparisonSignal('fx-detail-sync-peer', peer.id, '#7c3aed');
    const mainConvertPlans: Array<ControlledPlan<{hasData: boolean; seed: number}>> = [];
    const comparisonPlans: Array<ControlledPlan<{hasData: boolean; seed: number}>> = [];
    const assetSyncPlans: Array<ControlledPlan<AssetSyncOutcomeFixture>> = [];
    const stats = {
        comparisonRequests: [] as PriceQueryFixture[][],
        assetSyncRequests: [] as unknown[],
        mainConvertRequests: [] as FxConvertRequestFixture[][],
        unplannedComparisonRequests: 0,
        unplannedAssetSyncRequests: 0,
    };

    const enqueueMainConvert = (id: string, hasData: boolean, seed: number, held = false) => {
        const plan = createControlledPlan(id, {hasData, seed}, held);
        mainConvertPlans.push(plan);
        return plan;
    };
    const enqueueComparison = (id: string, hasData: boolean, seed: number, held = false) => {
        const plan = createControlledPlan(id, {hasData, seed}, held);
        comparisonPlans.push(plan);
        return plan;
    };
    const enqueueAssetSync = (id: string, outcome: AssetSyncOutcomeFixture, held = false) => {
        const plan = createControlledPlan(id, outcome, held);
        assetSyncPlans.push(plan);
        return plan;
    };

    await page.route('**/api/v1/fx/currencies/signals', async (route) => {
        await route.fulfill({status: 200, contentType: 'application/json', json: {items: []}});
    });

    await page.route('**/api/v1/fx/providers/routes*', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            json: {
                items: [
                    {
                        base: 'EUR',
                        quote: 'USD',
                        priority: 1,
                        chain_steps: [{from: 'EUR', to: 'USD', provider: 'MOCKFX'}],
                        is_chain: false,
                        providers_used: ['MOCKFX'],
                    },
                ],
            },
        });
    });

    await page.route('**/api/v1/assets/all*', async (route) => {
        await route.fulfill({status: 200, contentType: 'application/json', json: peers});
    });

    await page.route('**/api/v1/fx/currencies/convert', async (route) => {
        const requests = route.request().postDataJSON() as FxConvertRequestFixture[];
        stats.mainConvertRequests.push(requests);
        const plan = mainConvertPlans.shift();
        if (plan) {
            plan.requestBody = requests;
            plan.entered.release();
            if (plan.hold) await plan.hold.wait;
        }
        const results =
            plan?.outcome.hasData === false
                ? []
                : requests.flatMap((request, requestIndex) => {
                      const end = request.date_range.end ?? request.date_range.start;
                      const dates = end === request.date_range.start ? [request.date_range.start] : [request.date_range.start, end];
                      return dates.map((date, dateIndex) => {
                          const rate = (plan?.outcome.seed ?? 1.1 + requestIndex / 10) + dateIndex / 100;
                          return {
                              from_amount: {code: request.from_amount.code, amount: String(request.from_amount.amount)},
                              to_amount: {code: request.to, amount: String(rate)},
                              conversion_date: date,
                              rate: String(rate),
                              backward_fill_info: null,
                          };
                      });
                  });
        try {
            await route.fulfill({
                status: 200,
                ...(plan ? {headers: {'x-e2e-plan-id': plan.id}} : {}),
                contentType: 'application/json',
                json: {results, success_count: results.length, signal_results: []},
            });
        } finally {
            plan?.completed.release();
        }
    });

    await page.route('**/api/v1/assets/prices/query', async (route) => {
        const requestBody = parsePriceQueries(route.request().postDataJSON());
        stats.comparisonRequests.push(requestBody);
        const plan = comparisonPlans.shift();
        if (!plan) {
            stats.unplannedComparisonRequests += 1;
            const items = requestBody.map((query) => ({
                asset_id: query.asset_id,
                prices: syntheticPricePoints(
                    {
                        start: query.date_range?.start ?? range.start,
                        end: query.date_range?.end ?? range.end,
                    },
                    peer.currency,
                    900,
                ),
                events: [],
                errors: [],
                signals: [],
            }));
            await route.fulfill({status: 200, contentType: 'application/json', json: {items}});
            return;
        }
        plan.requestBody = requestBody;
        plan.entered.release();
        if (plan.hold) await plan.hold.wait;
        const items = requestBody.map((query) => {
            const requestedPeer = peers.find((candidate) => candidate.id === query.asset_id);
            if (!requestedPeer) throw new Error(`Unexpected synthetic FX comparison asset: ${String(query.asset_id)}`);
            const requestedRange = {
                start: query.date_range?.start ?? range.start,
                end: query.date_range?.end ?? range.end,
            };
            return {
                asset_id: query.asset_id,
                prices: plan.outcome.hasData ? syntheticPricePoints(requestedRange, requestedPeer.currency, plan.outcome.seed) : [],
                events: [],
                errors: [],
                signals: [],
            };
        });
        try {
            await route.fulfill({
                status: 200,
                headers: {'x-e2e-plan-id': plan.id},
                contentType: 'application/json',
                json: {items},
            });
        } finally {
            plan.completed.release();
        }
    });

    await page.route('**/api/v1/assets/prices/sync', async (route) => {
        const requestBody = route.request().postDataJSON();
        stats.assetSyncRequests.push(requestBody);
        const syncedAssetId = parsePriceQueries(requestBody).find((query) => typeof query.asset_id === 'number')?.asset_id;
        const plan = assetSyncPlans.shift();
        if (!plan || typeof syncedAssetId !== 'number') {
            stats.unplannedAssetSyncRequests += 1;
            await route.fulfill({
                status: 500,
                contentType: 'application/json',
                json: {detail: `Unexpected synthetic Asset sync: ${JSON.stringify(requestBody)}`},
            });
            return;
        }
        plan.requestBody = requestBody;
        plan.entered.release();
        if (plan.hold) await plan.hold.wait;
        try {
            await route.fulfill({
                status: plan.outcome === 'transport-error' ? 503 : 200,
                headers: {'x-e2e-plan-id': plan.id},
                contentType: 'application/json',
                json: assetSyncResponseBody(syncedAssetId, plan.outcome),
            });
        } finally {
            plan.completed.release();
        }
    });

    await seedSyntheticChartSettings(page, [['EUR-USD', [signal]]]);

    return {
        range,
        changedRange,
        peer,
        replacementPeer,
        signal,
        enqueueMainConvert,
        enqueueComparison,
        enqueueAssetSync,
        stats,
    };
}

// ---------------------------------------------------------------------------
// A pair of its own for «sync single pair reports its outcome in the modal»
// ---------------------------------------------------------------------------
//
// That test used to sync the seeded EUR-USD through the ECB: a network round-trip that passed offline too (the summary
// appears on failure as well) and, online, rewrote the seeded EUR-USD rates of the page's three-month period with live
// fixings for every category that runs after this one in the same invocation. It now brings a pair of its own and
// removes it: EUR-GTQ on the desktop project, EUR-HNL on mobile — currencies no seed, spec or other test uses
// (fx-sync.spec.ts reserves TTD/JMD for its own sync test), sorting after EUR so the pair is stored as EUR-X — routed
// through MOCKFX alone, the registered test provider that answers every calendar day with 1.2345 without a network.
// Leftovers of an interrupted run are deleted and the empty pair verified before the route is created; rates and
// route are deleted, and the pair verified empty again, in the teardown of `ownedFxQuotes`. Created and removed within
// one test, the pair is out of reach of the 1-worker recovery net (`populate_mock_data --force` truncates the routes),
// which runs only between tests and not at all above one worker.

const API = '/api/v1';
const FX_SYNC_PATH = `${API}/fx/currencies/sync`;
const FX_RATE_PATH = `${API}/fx/currencies/rate`;
const FX_CONVERT_PATH = `${API}/fx/currencies/convert`;
const FX_ROUTES_PATH = `${API}/fx/providers/routes`;

/** What MOCKFX stores for every calendar day: 1 EUR = 1.2345 of the quote (`MOCKFX_FIXED_RATE` in the backend). */
const MOCKFX_RATE = 1.2345;

/** Days in the period the sync test opens the page on: the ten days before today, never one the backend calls future. */
const SYNC_PERIOD_DAYS = 10;

/**
 * The quote currency of the sync test's pair, one per Playwright project, because FX routes and rates are global rows.
 * Each sorts after EUR, so the pair is stored as EUR-X and the MOCKFX rate is kept as is; none is used by any seed, spec
 * or other test (grep of the whole worktree). The runner runs the desktop project only; the mobile code keeps a manual
 * two-project run from sharing a pair.
 */
const RESERVED_QUOTE: Readonly<Record<string, string>> = {desktop: 'GTQ', mobile: 'HNL'};

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type PairResults = {results: Array<{base: string; quote: string; success: boolean}>};

// ---------------------------------------------------------------------------
// What the page saw, for the two fold/unfold tests (V-35)
// ---------------------------------------------------------------------------
//
// «aesthetics panel toggles visibility» went red once under load: after the second click the panel stayed open, and
// 50 probe runs with CPU and API throttling never reproduced it. Both fold/unfold tests now check each click in two
// halves, the state the toggle publishes (`aria-expanded`) and then the panel, and a red of either carries the page's
// own log of the clicks, the toggle states, the panel mounts and `data-busy`.

/** What `recordFxPanelEvents` watches, by test id. */
type FxPanelWatch = {toggles: string[]; panels: string[]; container: string};

const FX_PANEL_WATCH: FxPanelWatch = {
    toggles: ['fx-detail-aesthetics-toggle', 'fx-detail-signals-toggle'],
    panels: ['fx-detail-aesthetics-panel', 'fx-detail-signals-panel'],
    container: 'fx-detail-page',
};

/**
 * An init script: it runs before the app's own code and keeps, on the page clock (`performance.now()`, ms), every click
 * in the capture phase of `window` (so before any handler), every change of a toggle's `aria-expanded` and of the
 * container's `data-busy`, every mount and unmount of a watched element, and every uncaught error or rejection. It only
 * reads: no `preventDefault`, no stopped propagation, no DOM write. Playwright sends its source to the page, so it may
 * use nothing but its argument.
 */
function recordFxPanelEvents(watch: FxPanelWatch): void {
    const log: Array<Record<string, unknown>> = [];
    (window as unknown as {__lfFxPanelLog?: typeof log}).__lfFxPanelLog = log;
    const note = (entry: Record<string, unknown>) => {
        if (log.length < 500) log.push({t: Math.round(performance.now() * 10) / 10, ...entry});
    };
    const describe = (el: Element) => ({testid: el.getAttribute('data-testid'), expanded: el.getAttribute('aria-expanded') ?? undefined, busy: el.getAttribute('data-busy') ?? undefined});
    window.addEventListener(
        'click',
        (event) => {
            const target = event.target instanceof Element ? event.target : null;
            note({kind: 'click', target: target?.closest('[data-testid]')?.getAttribute('data-testid') ?? null, tag: target?.tagName.toLowerCase() ?? null, x: event.clientX, y: event.clientY, trusted: event.isTrusted});
        },
        {capture: true, passive: true},
    );
    window.addEventListener('error', (event) => note({kind: 'error', message: event.message}));
    window.addEventListener('unhandledrejection', (event) => note({kind: 'rejection', reason: String(event.reason?.message ?? event.reason)}));
    const selector = [...watch.toggles, ...watch.panels, watch.container].map((id) => `[data-testid="${id}"]`).join(', ');
    // A batch can report a node and its ancestor as added (the parser does): note each element once per change.
    const last = new WeakMap<Element, 'mount' | 'unmount'>();
    const scan = (nodes: NodeList, kind: 'mount' | 'unmount') => {
        for (const node of Array.from(nodes)) {
            if (!(node instanceof Element)) continue;
            const found = Array.from(node.querySelectorAll(selector));
            if (node.matches(selector)) found.unshift(node);
            for (const el of found) {
                if (last.get(el) === kind) continue;
                last.set(el, kind);
                note({kind, ...describe(el)});
            }
        }
    };
    new MutationObserver((records) => {
        for (const record of records) {
            if (record.type === 'childList') {
                scan(record.addedNodes, 'mount');
                scan(record.removedNodes, 'unmount');
            } else if (record.target instanceof Element) {
                const testid = record.target.getAttribute('data-testid') ?? '';
                const name = record.attributeName ?? '';
                if (name === 'aria-expanded' ? watch.toggles.includes(testid) : testid === watch.container) note({kind: 'attr', testid, name, from: record.oldValue, to: record.target.getAttribute(name)});
            }
        }
    }).observe(document, {childList: true, subtree: true, attributeFilter: ['aria-expanded', 'data-busy'], attributeOldValue: true});
}

/**
 * The EUR-X pairs a test registers here are deleted, and verified gone, after it — whatever happened in between.
 *
 * A fixture rather than a `finally` in the test body: a test that times out is abandoned together with its page,
 * while a fixture that depends on `page` is torn down before it, with the session still signed in. Every other test
 * of this file leaves it unrequested, so for them nothing changes.
 */
const test = base.extend<{ownedFxQuotes: string[]; fxPanelLog: void}>({
    ownedFxQuotes: async ({page}, use) => {
        const quotes: string[] = [];
        try {
            await use(quotes);
        } finally {
            for (const quote of quotes) await resetReservedPair(page, quote, 'cleanup');
        }
    },
    /**
     * Opt-in by name, like `ownedFxQuotes`: from its next navigation on, the test's page runs `recordFxPanelEvents`.
     * On a red the log is attached as `fx-panel-log` and also printed, because the list reporter shows no JSON
     * attachment and the next invocation overwrites the HTML report. On a green nothing is read.
     */
    fxPanelLog: async ({page}, use, testInfo) => {
        await page.addInitScript(recordFxPanelEvents, FX_PANEL_WATCH);
        await use();
        if (testInfo.status === testInfo.expectedStatus) return;
        const log = await page
            .evaluate((watch) => {
                const atRead = [...watch.toggles, ...watch.panels, watch.container].map((testid) => {
                    const found = Array.from(document.querySelectorAll(`[data-testid="${testid}"]`));
                    return {testid, count: found.length, expanded: found[0]?.getAttribute('aria-expanded') ?? undefined, busy: found[0]?.getAttribute('data-busy') ?? undefined};
                });
                const entries = (window as unknown as {__lfFxPanelLog?: unknown[]}).__lfFxPanelLog ?? null;
                return {url: location.href, timeOrigin: performance.timeOrigin, readAt: Math.round(performance.now() * 10) / 10, atRead, entries};
            }, FX_PANEL_WATCH)
            .catch((error: unknown) => ({unreadable: String(error), entries: null}));
        await testInfo.attach('fx-panel-log', {body: JSON.stringify(log, null, 2), contentType: 'application/json'});
        const {entries, ...head} = log;
        console.log([`[fx-panel-log] ${testInfo.title} ${JSON.stringify(head)}`, ...(entries ?? []).map((entry) => `[fx-panel-log] ${JSON.stringify(entry)}`)].join('\n'));
    },
});

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** A wait armed before the action and awaited after it: a failure in between leaves no rejection unobserved. */
function armed<T>(wait: Promise<T>): Promise<T> {
    wait.catch(() => undefined);
    return wait;
}

function isFxSync(req: Request): boolean {
    return req.method() === 'POST' && new URL(req.url()).pathname === FX_SYNC_PATH;
}

function reservedQuote(): string {
    const project = test.info().project.name;
    const quote = RESERVED_QUOTE[project];
    if (!quote) throw new Error(`No currency is reserved for project "${project}": reserve one that sorts after EUR and that no seed, spec or test uses`);
    return quote;
}

/** The `count` calendar days before today, oldest first, on the local calendar the application uses. */
function daysBeforeToday(count: number): string[] {
    const today = new Date();
    return Array.from({length: count}, (_, index) => {
        const day = new Date(today);
        day.setDate(today.getDate() - (count - index));
        return localIso(day);
    });
}

/** Delete every rate and every route of EUR-`quote`; on an empty pair both succeed with nothing to delete. */
async function deleteReservedPair(page: Page, quote: string): Promise<void> {
    const rates = await jsonFrom<PairResults>(await page.request.delete(FX_RATE_PATH, {data: [{from: 'EUR', to: quote, delete_all: true}]}), `delete every EUR-${quote} rate`);
    expect(rates.results.find((item) => item.base === 'EUR' && item.quote === quote)?.success, `delete every EUR-${quote} rate`).toBe(true);
    const routes = await jsonFrom<PairResults>(await page.request.delete(FX_ROUTES_PATH, {data: [{base: 'EUR', quote}]}), `delete the EUR-${quote} routes`);
    expect(routes.results.find((item) => item.base === 'EUR' && item.quote === quote)?.success, `delete the EUR-${quote} routes`).toBe(true);
}

/** Delete what EUR-`quote` holds, then verify — not infer — that no route and no rate is left. */
async function resetReservedPair(page: Page, quote: string, moment: 'precondition' | 'cleanup'): Promise<void> {
    await deleteReservedPair(page, quote);
    const routes = await jsonFrom<{items?: Array<{base: string; quote: string}>}>(await page.request.get(FX_ROUTES_PATH), 'list the FX routes');
    expect(
        (routes.items ?? []).filter((route) => route.base === 'EUR' && route.quote === quote),
        `${moment}: no EUR-${quote} route is configured`,
    ).toEqual([]);
    // Backward fill is unlimited: a single stored rate on or before today would answer, so a 404 means none is left.
    const probe = await page.request.post(FX_CONVERT_PATH, {data: [{from_amount: {code: quote, amount: '1'}, to: 'EUR', date_range: {start: todayIso()}}]});
    expect(probe.status(), `${moment}: no EUR-${quote} rate is stored, so converting ${quote} today must fail — got ${await probe.text()}`).toBe(404);
}

/** EUR-`quote` served by MOCKFX alone: a provider other than MANUAL, so the detail page offers to sync the pair. */
async function createMockFxRoute(page: Page, quote: string): Promise<void> {
    const route = {base: 'EUR', quote, priority: 1, chain_steps: [{from: 'EUR', to: quote, provider: 'MOCKFX'}]};
    schemas.FXConversionRouteItem.parse(route);
    const response = await page.request.post(FX_ROUTES_PATH, {data: [route]});
    expect(response.status(), `create the EUR-${quote} MOCKFX route: ${await response.text()}`).toBe(201);
    const body = (await response.json()) as PairResults;
    expect(body.results.find((item) => item.base === 'EUR' && item.quote === quote)?.success, `the EUR-${quote} route is stored`).toBe(true);
}

test.describe('FX Detail Page', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Direct slug navigation
    // ========================================================================
    test('can navigate to detail page via slug', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await expect(page.getByTestId('fx-detail-page')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Inverted slug displays inverted direction
    // ========================================================================
    test('inverted slug displays inverted direction', async ({page}) => {
        await goToFxDetailPage(page, 'USD-EUR');
        await expect(page.getByTestId('fx-detail-page')).toBeVisible();
        const pairLabel = page.getByTestId('fx-detail-pair-label');
        const text = await pairLabel.textContent();
        expect(text).toContain('USD');
    });

    // ========================================================================
    // Test 3: Chart is visible (canvas element rendered)
    // ========================================================================
    test('chart is visible with canvas element', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        // ECharts renders into a canvas — assert the drawn content, not just the frame
        await expectChartCanvas(page, 'fx-detail-chart');
    });

    // ========================================================================
    // Test 4: Swap direction changes URL
    // ========================================================================
    test('swap direction changes URL', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-swap-btn').click();
        await expect(page).toHaveURL(/\/fx\/USD-EUR/, {timeout: 10_000});
    });

    // ========================================================================
    // Test 6: Aesthetics panel fold/unfold
    // ========================================================================
    // Each click is checked in two halves, the state the toggle publishes and then the panel it gates, so a red says
    // which one failed; `fxPanelLog` adds what the page itself saw.
    test('aesthetics panel toggles visibility', async ({page, fxPanelLog}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const toggle = page.getByTestId('fx-detail-aesthetics-toggle');
        const panel = page.getByTestId('fx-detail-aesthetics-panel');
        await expect(toggle, 'the page opens with the toggle closed').toHaveAttribute('aria-expanded', 'false');
        await toggle.click();
        await expect(toggle, 'after click 1, the toggle publishes open').toHaveAttribute('aria-expanded', 'true');
        await expect(panel, 'after click 1, the panel follows the toggle').toBeVisible();
        await toggle.click();
        await expect(toggle, 'after click 2, the toggle publishes closed').toHaveAttribute('aria-expanded', 'false');
        await expect(panel, 'after click 2, the panel follows the toggle').not.toBeVisible();
    });

    // ========================================================================
    // Test 7: Signals panel fold/unfold
    // ========================================================================
    // Same two halves per click as test 6, same log on a red.
    test('signals panel toggles visibility', async ({page, fxPanelLog}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const toggle = page.getByTestId('fx-detail-signals-toggle');
        const panel = page.getByTestId('fx-detail-signals-panel');
        await expect(toggle, 'the page opens with the toggle closed').toHaveAttribute('aria-expanded', 'false');
        await toggle.click();
        await expect(toggle, 'after click 1, the toggle publishes open').toHaveAttribute('aria-expanded', 'true');
        await expect(panel, 'after click 1, the panel follows the toggle').toBeVisible();
        await toggle.click();
        await expect(toggle, 'after click 2, the toggle publishes closed').toHaveAttribute('aria-expanded', 'false');
        await expect(panel, 'after click 2, the panel follows the toggle').not.toBeVisible();
    });

    test('AI Export lives in the page toolbar instead of Signals', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const aiExportButton = page.getByTestId('fx-detail-filter-bar').getByTestId('ai-export-button');
        await expect(aiExportButton).toBeVisible({timeout: 10_000});
        await expect(aiExportButton).toBeEnabled({timeout: 10_000});
        await aiExportButton.click();
        await expect(page.getByTestId('ai-export-menu-panel')).toBeVisible();
        await page.keyboard.press('Escape');
        await expect(page.getByTestId('ai-export-menu-panel')).toBeHidden();
        await expect(page.getByTestId('fx-detail-signals-header').getByTestId('ai-export-button')).toHaveCount(0);
    });

    // ========================================================================
    // Test 8: Measures panel fold/unfold
    // ========================================================================
    test('measures panel toggles visibility', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const toggle = page.getByTestId('fx-detail-measures-toggle');
        await toggle.click();
        // MeasurePanel is always mounted but hidden via CSS class
        const panel = page.getByTestId('fx-detail-measures-panel');
        await expect(panel).toBeVisible();
        // Check it's not hidden
        await expect(panel).not.toHaveClass(/hidden/);
    });

    // ========================================================================
    // Test 9: Toggle Abs/%
    // ========================================================================
    test('Abs/% control is chart-local and synchronizes page view mode', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const filterBar = page.getByTestId('fx-detail-filter-bar');
        const chart = page.getByTestId('fx-detail-chart');
        await expect(filterBar.getByTestId('chart-view-mode-toggle')).toHaveCount(0);
        await expect(chart.getByTestId('chart-view-mode-toggle')).toBeVisible({timeout: 10_000});
        await expect(chart).toHaveAttribute('data-view-mode', 'percentage');

        await chart.getByTestId('chart-view-absolute').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'absolute');
        await expect(chart.getByTestId('chart-view-absolute')).toHaveAttribute('aria-pressed', 'true');

        await chart.getByTestId('chart-view-percentage').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'percentage');
    });

    test('persists distinct primary scales and the semantic RSI scale across reload', async ({page}) => {
        type MockConvertRequest = {
            from_amount: {code: string; amount: string | number};
            to: string;
            date_range: {start: string; end?: string | null};
            signals?: Array<{
                instance_id: string;
                signal_code: string;
                params?: Record<string, unknown>;
            }>;
        };

        const datesFor = (range: MockConvertRequest['date_range']): string[] => (range.end && range.end !== range.start ? [range.start, range.end] : [range.start]);

        await page.route('**/api/v1/fx/currencies/signals', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                json: {
                    items: [
                        {
                            signal_code: 'RSI',
                            implementation_version: '1.0.0',
                            category: 'momentum',
                            display_name_key: 'signals.rsi',
                            description_key: 'signals.rsi.description',
                            semantic_id: 'technical.rsi',
                            semantic_description: 'Relative Strength Index.',
                            icon: '📊',
                            params_schema: {type: 'object', properties: {}},
                            default_params: {},
                            input_requirements: {
                                price_fields: ['close'],
                                data_policy: 'strict_contiguous',
                                minimum_coverage: 1,
                            },
                            output_specs: [
                                {
                                    key: 'rsi',
                                    label_key: 'signals.rsi.value',
                                    semantic_id: 'technical.rsi.value',
                                    semantic_description: 'Relative Strength Index values.',
                                    unit: 'index',
                                    axis: {
                                        key: 'rsi',
                                        role: 'independent',
                                        minimum: 0,
                                        maximum: 100,
                                    },
                                    view_transform: 'none',
                                    kind: 'line',
                                    aggregation_profile: 'last_with_range',
                                },
                            ],
                            compatible_domains: ['fx'],
                        },
                    ],
                },
            });
        });

        await page.route('**/api/v1/fx/currencies/convert', async (route) => {
            const requests = route.request().postDataJSON() as MockConvertRequest[];
            const results = requests.flatMap((request) =>
                datesFor(request.date_range).map((date) => {
                    const rate = date === request.date_range.start ? '1.10' : '1.20';
                    return {
                        from_amount: {code: request.from_amount.code, amount: '1'},
                        to_amount: {code: request.to, amount: rate},
                        conversion_date: date,
                        rate,
                        backward_fill_info: null,
                    };
                }),
            );
            const signalResults = requests.flatMap((request, requestIndex) => {
                const signals = request.signals ?? [];
                if (signals.length === 0) return [];
                return [
                    {
                        request_index: requestIndex,
                        from_currency: request.from_amount.code,
                        to_currency: request.to,
                        date_range: request.date_range,
                        signals: signals.map((signal) => {
                            if (signal.signal_code !== 'RSI') {
                                throw new Error(`Unexpected mocked FX signal request: ${signal.signal_code}`);
                            }
                            return {
                                instance_id: signal.instance_id,
                                signal_code: signal.signal_code,
                                implementation_version: '1.0.0',
                                normalized_params: signal.params ?? {},
                                status: 'ok',
                                series: [
                                    {
                                        key: 'rsi',
                                        label_key: 'signals.rsi.value',
                                        semantic_id: 'technical.rsi.value',
                                        semantic_description: 'Relative Strength Index values.',
                                        unit: 'index',
                                        axis: {
                                            key: 'rsi',
                                            role: 'independent',
                                            minimum: 0,
                                            maximum: 100,
                                        },
                                        view_transform: 'none',
                                        points: datesFor(request.date_range).map((date) => ({
                                            date,
                                            value: date === request.date_range.start ? 20 : 80,
                                        })),
                                        kind: 'line',
                                    },
                                ],
                            };
                        }),
                    },
                ];
            });

            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                json: {
                    results,
                    success_count: results.length,
                    signal_results: signalResults,
                },
            });
        });

        await goToFxDetailPage(page, 'EUR-USD');
        const chart = page.getByTestId('fx-detail-chart');
        await expect(chart.getByTestId('chart-view-mode-toggle')).toBeVisible({timeout: 10_000});
        await expect(chart).toHaveAttribute('data-view-mode', 'percentage');

        await page.getByTestId('fx-detail-signals-toggle').click();
        await expect(page.getByTestId('fx-detail-signals-panel')).toBeVisible();
        await page.getByTestId('signals-indicator-select-button').click();
        const rsiOption = page.getByTestId('signal-tree-option-rsi');
        await expect(rsiOption).toBeVisible();
        const rsiRequestPromise = page.waitForRequest((request) => {
            if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/fx/currencies/convert') return false;
            const requests = request.postDataJSON() as MockConvertRequest[];
            return requests.some((item) => item.signals?.some((signal) => signal.signal_code === 'RSI'));
        });
        await rsiOption.click();
        const rsiRequest = await rsiRequestPromise;
        const requestedSignals = (rsiRequest.postDataJSON() as MockConvertRequest[]).flatMap((request) => request.signals ?? []);
        expect(requestedSignals).toEqual([expect.objectContaining({signal_code: 'RSI'})]);

        const aestheticsToggle = page.getByTestId('fx-detail-aesthetics-toggle');
        await aestheticsToggle.click();
        await expect(aestheticsToggle, 'the toggle publishes open').toHaveAttribute('aria-expanded', 'true');
        const aesthetics = page.getByTestId('fx-detail-aesthetics-panel');
        await expect(aesthetics).toBeVisible();

        const percentageRow = aesthetics.getByTestId('chart-axis-row-primary-percentage');
        const percentageMin = percentageRow.getByTestId('chart-axis-primary-percentage-min');
        const percentageMax = percentageRow.getByTestId('chart-axis-primary-percentage-max');
        await expect(percentageRow).toBeVisible();
        await percentageRow.getByTestId('chart-axis-primary-percentage-custom').click();
        await expect(percentageMin).toBeVisible();
        await percentageMin.fill('-12.5');
        await percentageMax.fill('34.5');
        await expect(percentageMin).toHaveValue('-12.5');
        await expect(percentageMax).toHaveValue('34.5');

        const rsiRow = aesthetics.getByTestId('chart-axis-row-independent-rsi');
        const rsiMin = rsiRow.getByTestId('chart-axis-independent-rsi-min');
        const rsiMax = rsiRow.getByTestId('chart-axis-independent-rsi-max');
        await expect(rsiRow).toBeVisible({timeout: 10_000});
        const rsiAuto = rsiRow.getByTestId('chart-axis-independent-rsi-auto');
        await expect(rsiAuto).toHaveAttribute('aria-pressed', 'true');
        await expect(rsiMin).toHaveCount(0);
        await expect(rsiMax).toHaveCount(0);

        const rsiInclude0 = rsiRow.getByTestId('chart-axis-independent-rsi-include0');
        await rsiInclude0.click();
        await expect(rsiInclude0).toHaveAttribute('aria-pressed', 'true');
        await expect(rsiAuto).toHaveAttribute('aria-pressed', 'false');
        await expect(rsiMin).toHaveCount(0);
        await expect(rsiMax).toHaveCount(0);

        await rsiRow.getByTestId('chart-axis-independent-rsi-custom').click();
        await expect(rsiMin).toBeVisible();
        await rsiMin.fill('20');
        await rsiMax.fill('80');
        await expect(rsiMin).toHaveValue('20');
        await expect(rsiMax).toHaveValue('80');

        await chart.getByTestId('chart-view-absolute').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'absolute');
        const absoluteRow = aesthetics.getByTestId('chart-axis-row-primary-absolute');
        const absoluteMin = absoluteRow.getByTestId('chart-axis-primary-absolute-min');
        const absoluteMax = absoluteRow.getByTestId('chart-axis-primary-absolute-max');
        await expect(absoluteRow).toBeVisible();
        await absoluteRow.getByTestId('chart-axis-primary-absolute-custom').click();
        await expect(absoluteMin).toBeVisible();
        await absoluteMin.fill('0.75');
        await absoluteMax.fill('1.25');
        await expect(absoluteMin).toHaveValue('0.75');
        await expect(absoluteMax).toHaveValue('1.25');
        await expect(rsiMin).toHaveValue('20');
        await expect(rsiMax).toHaveValue('80');

        await chart.getByTestId('chart-view-percentage').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'percentage');
        await expect(percentageRow).toBeVisible();
        await expect(percentageMin).toHaveValue('-12.5');
        await expect(percentageMax).toHaveValue('34.5');
        await expect(rsiRow).toBeVisible();
        await expect(rsiMin).toHaveValue('20');
        await expect(rsiMax).toHaveValue('80');

        type PersistedPairSettings = {
            signals?: Array<{signalType?: string}>;
            axisScales?: {
                absolute?: {mode?: string; min?: number; max?: number};
                percentage?: {mode?: string; min?: number; max?: number};
                secondary?: Record<string, {mode?: string; min?: number; max?: number}>;
            };
        };
        const readPersistedPairSettings = () =>
            page.evaluate((pairSlug) => {
                for (const key of Object.keys(localStorage)) {
                    if (!key.endsWith('_chartSettingsStore')) continue;
                    const raw = localStorage.getItem(key);
                    if (!raw) continue;
                    const payload = JSON.parse(raw) as {
                        pairOverrides?: Array<[string, PersistedPairSettings]>;
                    };
                    const pairEntry = payload.pairOverrides?.find(([slug]) => slug === pairSlug);
                    if (!pairEntry) continue;
                    const [, pairSettings] = pairEntry;
                    return {
                        signalTypes: (pairSettings.signals ?? []).map(({signalType}) => signalType),
                        absolute: pairSettings.axisScales?.absolute ?? null,
                        percentage: pairSettings.axisScales?.percentage ?? null,
                        secondary: pairSettings.axisScales?.secondary?.['independent:rsi'] ?? null,
                    };
                }
                return null;
            }, 'EUR-USD');

        await expect.poll(readPersistedPairSettings, {timeout: 5_000}).toEqual({
            signalTypes: ['rsi'],
            absolute: {mode: 'custom', min: 0.75, max: 1.25},
            percentage: {mode: 'custom', min: -12.5, max: 34.5},
            secondary: {mode: 'custom', min: 20, max: 80},
        });

        await page.reload();
        await waitForSettled(page.getByTestId('fx-detail-page'), 20_000);
        await expect(chart).toHaveAttribute('data-view-mode', 'percentage');
        await aestheticsToggle.click();
        await expect(aestheticsToggle, 'after the reload, the toggle publishes open').toHaveAttribute('aria-expanded', 'true');
        await expect(aesthetics).toBeVisible();
        await expect(percentageRow).toBeVisible();
        await expect(percentageMin).toHaveValue('-12.5');
        await expect(percentageMax).toHaveValue('34.5');
        await expect(rsiRow).toBeVisible();
        await expect(rsiMin).toHaveValue('20');
        await expect(rsiMax).toHaveValue('80');

        await chart.getByTestId('chart-view-absolute').click();
        await expect(chart).toHaveAttribute('data-view-mode', 'absolute');
        await expect(absoluteRow).toBeVisible();
        await expect(absoluteMin).toHaveValue('0.75');
        await expect(absoluteMax).toHaveValue('1.25');
        await expect(rsiRow).toBeVisible();
        await expect(rsiMin).toHaveValue('20');
        await expect(rsiMax).toHaveValue('80');
    });

    test('keeps standalone Asset FX retry ownership monotonic per slug', async ({page}) => {
        test.setTimeout(90_000);
        const fixture = await installAssetFxRetryFixture(page);
        const gbpPeer = fixture.peers.find((peer) => peer.slug === 'EUR-GBP');
        const chfPeer = fixture.peers.find((peer) => peer.slug === 'CHF-EUR');
        if (!gbpPeer || !chfPeer) throw new Error('Synthetic retry peers are incomplete');
        const comparisonPeerIds = fixture.peers.map((peer) => peer.id);
        const isComparisonResponse = (response: Response) => {
            const request = response.request();
            return request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/assets/prices/query' && matchesAssetIds(request.postDataJSON(), comparisonPeerIds);
        };

        const initialComparisonResponsePromise = page.waitForResponse(isComparisonResponse, {timeout: 10_000});
        await openSyntheticDetail(page, `/assets/${fixture.asset.id}?start=${fixture.range.start}&end=${fixture.range.end}`, 'asset-detail-page');
        const initialComparisonResponse = await initialComparisonResponsePromise;
        expect(initialComparisonResponse.status()).toBe(200);
        expect(await initialComparisonResponse.finished()).toBeNull();
        assertComparisonRequest(initialComparisonResponse.request().postDataJSON(), comparisonPeerIds, fixture.range, fixture.asset.currency);

        const signalsToggle = page.getByTestId('asset-detail-signals-toggle');
        const signalsPanel = page.getByTestId('asset-detail-signals-panel');
        await ensureSignalsPanelOpen(signalsToggle, signalsPanel);
        const gbpCard = signalsPanel.getByTestId(`signal-card-${gbpPeer.signalId}`);
        const chfCard = signalsPanel.getByTestId(`signal-card-${chfPeer.signalId}`);
        const gbpSync = gbpCard.getByTestId(`signal-fx-sync-${gbpPeer.signalId}`);
        const chfSync = chfCard.getByTestId(`signal-fx-sync-${chfPeer.signalId}`);
        const gbpDetail = gbpCard.getByTestId(`signal-fx-detail-${gbpPeer.signalId}`);
        const chfDetail = chfCard.getByTestId(`signal-fx-detail-${chfPeer.signalId}`);
        const activateByKeyboard = async (control: Locator) => {
            await control.focus();
            await expect(control).toBeFocused();
            await expect(control).toBeEnabled();
            await control.press('Enter');
        };
        await expect(gbpCard).toBeVisible();
        await expect(chfCard).toBeVisible();
        await expect(gbpSync).toBeVisible();
        await expect(chfSync).toBeVisible();

        const initialMainPriceRequests = fixture.stats.mainPriceRequests.length;
        const initialComparisonRequests = fixture.stats.comparisonRequests.length;
        const initialGbpRefills = fixture.stats.fxRefillsBySlug.get(gbpPeer.slug) ?? 0;

        // A1 remains pending while A2 for the same slug completes. A2 then
        // relinquishes active ownership before A3 starts: deriving A3 from the
        // active map would reuse A1's token and recreate the classic ABA hole.
        const oldPlan = fixture.enqueueSync('asset-aba-old', gbpPeer.slug, 'ok', true);
        const oldResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/sync', oldPlan.id);
        await activateByKeyboard(gbpSync);
        await oldPlan.entered.wait;
        assertFxSyncRequest(oldPlan.requestBody, gbpPeer.slug, fixture.range);

        fixture.conversionFailures.delete(gbpPeer.slug);
        const middlePlan = fixture.enqueueSync('asset-aba-middle', gbpPeer.slug, 'ok');
        const middleResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/sync', middlePlan.id);
        const middleComparisonResponsePromise = page.waitForResponse(isComparisonResponse, {timeout: 10_000});
        await activateByKeyboard(gbpSync);
        await middlePlan.entered.wait;
        assertFxSyncRequest(middlePlan.requestBody, gbpPeer.slug, fixture.range);
        const middleResponse = await middleResponsePromise;
        expect(middleResponse.status()).toBe(200);
        expect(await middleResponse.finished()).toBeNull();
        expect(await middleResponse.json()).toEqual({
            results: [
                {
                    pair: gbpPeer.slug,
                    status: 'ok',
                    points_fetched: 2,
                    points_changed: 2,
                    provider_used: 'MOCKFX',
                    message: null,
                    errors: [],
                },
            ],
            success_count: 1,
            date_range: fixture.range,
            total_points_changed: 2,
        });
        await dismissOwnedToast(page, 'success');
        const middleComparisonResponse = await middleComparisonResponsePromise;
        expect(middleComparisonResponse.status()).toBe(200);
        expect(await middleComparisonResponse.finished()).toBeNull();
        assertComparisonRequest(middleComparisonResponse.request().postDataJSON(), comparisonPeerIds, fixture.range, fixture.asset.currency);
        await expect(gbpDetail).toBeVisible();
        await expect(gbpSync).toHaveCount(0);
        expect(fixture.stats.fxRefillsBySlug.get(gbpPeer.slug) ?? 0).toBe(initialGbpRefills + 1);
        expect(fixture.stats.mainPriceRequests.length).toBe(initialMainPriceRequests + 1);
        expect(fixture.stats.comparisonRequests.length).toBe(initialComparisonRequests + 1);

        // Y11: Refresh is disabled while the page's big requests are in flight, and a
        // disabled button takes no focus: wait until it can be pressed. A sync's own
        // reload is not one of them (P3), so the A1 sync still held does not keep it.
        const assetRefreshButton = page.getByTestId('asset-detail-refresh-btn');
        await expect(assetRefreshButton).toBeEnabled({timeout: 10_000});
        fixture.conversionFailures.add(gbpPeer.slug);
        const restoreComparisonResponsePromise = page.waitForResponse(isComparisonResponse, {timeout: 10_000});
        await activateByKeyboard(assetRefreshButton);
        const restoreComparisonResponse = await restoreComparisonResponsePromise;
        expect(restoreComparisonResponse.status()).toBe(200);
        expect(await restoreComparisonResponse.finished()).toBeNull();
        assertComparisonRequest(restoreComparisonResponse.request().postDataJSON(), comparisonPeerIds, fixture.range, fixture.asset.currency);
        await expect(gbpSync).toBeVisible();
        await expect(gbpDetail).toHaveCount(0);

        const beforeOldCompletion = {
            gbpRefills: fixture.stats.fxRefillsBySlug.get(gbpPeer.slug) ?? 0,
            mainPriceRequests: fixture.stats.mainPriceRequests.length,
            comparisonRequests: fixture.stats.comparisonRequests.length,
        };
        const currentPlan = fixture.enqueueSync('asset-aba-current', gbpPeer.slug, 'partial', true);
        const currentResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/sync', currentPlan.id);
        await activateByKeyboard(gbpSync);
        await currentPlan.entered.wait;
        assertFxSyncRequest(currentPlan.requestBody, gbpPeer.slug, fixture.range);

        oldPlan.hold?.release();
        const oldResponse = await oldResponsePromise;
        expect(oldResponse.status()).toBe(200);
        expect(await oldResponse.finished()).toBeNull();
        expect(await oldResponse.json()).toMatchObject({
            success_count: 1,
            results: [{pair: gbpPeer.slug, status: 'ok'}],
        });
        // The close/open round trip is a browser-task barrier after A1's
        // response. If A1 regains ownership, its toast and first refill are
        // necessarily observable before this later interaction completes.
        await cycleSignalsPanel(signalsToggle, signalsPanel);
        await expectNoSyncToasts(page);
        expect(fixture.stats.fxRefillsBySlug.get(gbpPeer.slug) ?? 0).toBe(beforeOldCompletion.gbpRefills);
        expect(fixture.stats.mainPriceRequests.length).toBe(beforeOldCompletion.mainPriceRequests);
        expect(fixture.stats.comparisonRequests.length).toBe(beforeOldCompletion.comparisonRequests);

        const currentComparisonResponsePromise = page.waitForResponse(isComparisonResponse, {timeout: 10_000});
        currentPlan.hold?.release();
        const currentResponse = await currentResponsePromise;
        expect(currentResponse.status()).toBe(200);
        expect(await currentResponse.finished()).toBeNull();
        expect(await currentResponse.json()).toMatchObject({
            success_count: 1,
            results: [{pair: gbpPeer.slug, status: 'partial'}],
        });
        await dismissOwnedToast(page, 'warning');
        const currentComparisonResponse = await currentComparisonResponsePromise;
        expect(currentComparisonResponse.status()).toBe(200);
        expect(await currentComparisonResponse.finished()).toBeNull();
        assertComparisonRequest(currentComparisonResponse.request().postDataJSON(), comparisonPeerIds, fixture.range, fixture.asset.currency);
        await cycleSignalsPanel(signalsToggle, signalsPanel);
        await expect(gbpSync).toBeVisible();
        await expect(page.getByTestId('toast-success')).toHaveCount(0);
        expect(fixture.stats.fxRefillsBySlug.get(gbpPeer.slug) ?? 0).toBe(beforeOldCompletion.gbpRefills + 1);
        expect(fixture.stats.mainPriceRequests.length).toBe(beforeOldCompletion.mainPriceRequests + 1);
        expect(fixture.stats.comparisonRequests.length).toBe(beforeOldCompletion.comparisonRequests + 1);

        // Ownership is keyed per slug, not globally. Let CHF complete while
        // GBP is held, then let GBP complete; each must independently refill
        // and publish without retiring the other request.
        fixture.conversionFailures.add(gbpPeer.slug);
        fixture.conversionFailures.add(chfPeer.slug);
        await expect(gbpSync).toBeVisible();
        await expect(chfSync).toBeVisible();
        const beforeConcurrent = {
            gbpRefills: fixture.stats.fxRefillsBySlug.get(gbpPeer.slug) ?? 0,
            chfRefills: fixture.stats.fxRefillsBySlug.get(chfPeer.slug) ?? 0,
            mainPriceRequests: fixture.stats.mainPriceRequests.length,
            comparisonRequests: fixture.stats.comparisonRequests.length,
        };
        const gbpPlan = fixture.enqueueSync('asset-independent-gbp', gbpPeer.slug, 'partial', true);
        const chfPlan = fixture.enqueueSync('asset-independent-chf', chfPeer.slug, 'ok', true);
        const gbpResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/sync', gbpPlan.id);
        const chfResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/sync', chfPlan.id);
        await activateByKeyboard(gbpSync);
        await activateByKeyboard(chfSync);
        await Promise.all([gbpPlan.entered.wait, chfPlan.entered.wait]);
        assertFxSyncRequest(gbpPlan.requestBody, gbpPeer.slug, fixture.range);
        assertFxSyncRequest(chfPlan.requestBody, chfPeer.slug, fixture.range);

        fixture.conversionFailures.delete(chfPeer.slug);
        const chfComparisonResponsePromise = page.waitForResponse(isComparisonResponse, {timeout: 10_000});
        chfPlan.hold?.release();
        const chfResponse = await chfResponsePromise;
        expect(chfResponse.status()).toBe(200);
        expect(await chfResponse.finished()).toBeNull();
        expect(await chfResponse.json()).toMatchObject({
            success_count: 1,
            results: [{pair: chfPeer.slug, status: 'ok'}],
        });
        await dismissOwnedToast(page, 'success');
        const chfComparisonResponse = await chfComparisonResponsePromise;
        expect(chfComparisonResponse.status()).toBe(200);
        expect(await chfComparisonResponse.finished()).toBeNull();
        assertComparisonRequest(chfComparisonResponse.request().postDataJSON(), comparisonPeerIds, fixture.range, fixture.asset.currency);
        await expect(chfDetail).toBeVisible();
        await expect(chfSync).toHaveCount(0);
        await expect(gbpSync).toBeVisible();
        expect(fixture.stats.fxRefillsBySlug.get(chfPeer.slug) ?? 0).toBe(beforeConcurrent.chfRefills + 1);
        expect(fixture.stats.fxRefillsBySlug.get(gbpPeer.slug) ?? 0).toBe(beforeConcurrent.gbpRefills);
        expect(fixture.stats.mainPriceRequests.length).toBe(beforeConcurrent.mainPriceRequests + 1);
        expect(fixture.stats.comparisonRequests.length).toBe(beforeConcurrent.comparisonRequests + 1);

        fixture.conversionFailures.delete(gbpPeer.slug);
        const gbpComparisonResponsePromise = page.waitForResponse(isComparisonResponse, {timeout: 10_000});
        gbpPlan.hold?.release();
        const gbpResponse = await gbpResponsePromise;
        expect(gbpResponse.status()).toBe(200);
        expect(await gbpResponse.finished()).toBeNull();
        expect(await gbpResponse.json()).toMatchObject({
            success_count: 1,
            results: [{pair: gbpPeer.slug, status: 'partial'}],
        });
        await dismissOwnedToast(page, 'warning');
        const gbpComparisonResponse = await gbpComparisonResponsePromise;
        expect(gbpComparisonResponse.status()).toBe(200);
        expect(await gbpComparisonResponse.finished()).toBeNull();
        assertComparisonRequest(gbpComparisonResponse.request().postDataJSON(), comparisonPeerIds, fixture.range, fixture.asset.currency);
        await expect(gbpDetail).toBeVisible();
        await expect(gbpSync).toHaveCount(0);
        await expect(chfDetail).toBeVisible();
        expect(fixture.stats.fxRefillsBySlug.get(gbpPeer.slug) ?? 0).toBe(beforeConcurrent.gbpRefills + 1);
        expect(fixture.stats.fxRefillsBySlug.get(chfPeer.slug) ?? 0).toBe(beforeConcurrent.chfRefills + 1);
        expect(fixture.stats.mainPriceRequests.length).toBe(beforeConcurrent.mainPriceRequests + 2);
        expect(fixture.stats.comparisonRequests.length).toBe(beforeConcurrent.comparisonRequests + 2);
        expect(fixture.stats.unplannedSyncRequests).toBe(0);
        await expectNoSyncToasts(page);
    });

    test('keeps pending FX comparison work for every unaccepted Asset sync outcome and refreshes only accepted outcomes', async ({page}) => {
        test.setTimeout(90_000);
        const fixture = await installFxComparisonSyncFixture(page);
        const initialComparison = fixture.enqueueComparison('fx-sync-initial', true, 300);
        const initialComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', initialComparison.id);
        const pageRoot = await openSyntheticDetail(page, `/fx/EUR-USD?start=${fixture.range.start}&end=${fixture.range.end}`, 'fx-detail-page');
        await initialComparison.entered.wait;
        assertComparisonRequest(initialComparison.requestBody, [fixture.peer.id], fixture.range);
        const initialComparisonResponse = await initialComparisonResponsePromise;
        expect(initialComparisonResponse.status()).toBe(200);
        expect(await initialComparisonResponse.finished()).toBeNull();
        await expect(pageRoot).toHaveAttribute('data-chart-pair', 'EUR-USD');

        const signalsToggle = page.getByTestId('fx-detail-signals-toggle');
        const signalsPanel = page.getByTestId('fx-detail-signals-panel');
        await ensureSignalsPanelOpen(signalsToggle, signalsPanel);
        const signalCard = signalsPanel.getByTestId(`signal-card-${fixture.signal.id}`);
        const syncAssetButton = signalCard.getByTestId(`signal-sync-asset-${fixture.signal.id}`);
        const refreshButton = page.getByTestId('fx-detail-refresh-btn');
        await expectComparisonDataState(signalCard, syncAssetButton, true);

        const unacceptedCases = [
            {outcome: 'failed', toast: 'error'},
            {outcome: 'skipped', toast: 'info'},
            {outcome: 'missing-result', toast: 'error'},
            {outcome: 'transport-error', toast: 'error'},
        ] as const;
        let currentHasData = true;

        for (const [caseIndex, scenario] of unacceptedCases.entries()) {
            await test.step(`${scenario.outcome} preserves the pending comparison`, async () => {
                const pendingHasData = !currentHasData;
                const comparisonRequestsBefore = fixture.stats.comparisonRequests.length;
                const pendingComparison = fixture.enqueueComparison(`fx-sync-pending-${scenario.outcome}`, pendingHasData, 400 + caseIndex, true);
                const pendingComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', pendingComparison.id);
                await expect(refreshButton).toBeEnabled();
                await refreshButton.click();
                await pendingComparison.entered.wait;
                assertComparisonRequest(pendingComparison.requestBody, [fixture.peer.id], fixture.range);
                expect(fixture.stats.comparisonRequests.length).toBe(comparisonRequestsBefore + 1);

                const syncPlan = fixture.enqueueAssetSync(`fx-sync-${scenario.outcome}`, scenario.outcome, true);
                const syncResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/sync', syncPlan.id);
                await syncAssetButton.click();
                await syncPlan.entered.wait;
                assertAssetSyncRequest(syncPlan.requestBody, fixture.peer.id, fixture.range);
                await expect(syncAssetButton).toBeDisabled();
                syncPlan.hold?.release();

                const syncResponse = await syncResponsePromise;
                expect(syncResponse.status()).toBe(scenario.outcome === 'transport-error' ? 503 : 200);
                expect(await syncResponse.finished()).toBeNull();
                expect(await syncResponse.json()).toEqual(assetSyncResponseBody(fixture.peer.id, scenario.outcome));
                await expect(syncAssetButton).toBeEnabled();
                await dismissOwnedToast(page, scenario.toast);
                expect(fixture.stats.comparisonRequests.length).toBe(comparisonRequestsBefore + 1);

                pendingComparison.hold?.release();
                const pendingResponse = await pendingComparisonResponsePromise;
                expect(pendingResponse.status()).toBe(200);
                expect(await pendingResponse.finished()).toBeNull();
                await cycleSignalsPanel(signalsToggle, signalsPanel);
                await expectComparisonDataState(signalCard, syncAssetButton, pendingHasData);
                expect(fixture.stats.comparisonRequests.length).toBe(comparisonRequestsBefore + 1);
                currentHasData = pendingHasData;
            });
        }

        for (const [caseIndex, status] of (['ok', 'partial'] as const).entries()) {
            await test.step(`${status} invalidates the old comparison and forces one successor`, async () => {
                const oldHasData = !currentHasData;
                const successorHasData = currentHasData;
                const comparisonRequestsBefore = fixture.stats.comparisonRequests.length;
                const oldComparison = fixture.enqueueComparison(`fx-sync-old-${status}`, oldHasData, 500 + caseIndex, true);
                const oldComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', oldComparison.id);
                await expect(refreshButton).toBeEnabled();
                await refreshButton.click();
                await oldComparison.entered.wait;
                assertComparisonRequest(oldComparison.requestBody, [fixture.peer.id], fixture.range);

                const successorComparison = fixture.enqueueComparison(`fx-sync-successor-${status}`, successorHasData, 600 + caseIndex, true);
                const successorComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', successorComparison.id);
                const syncPlan = fixture.enqueueAssetSync(`fx-sync-accepted-${status}`, status, true);
                const syncResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/sync', syncPlan.id);
                await syncAssetButton.click();
                await syncPlan.entered.wait;
                assertAssetSyncRequest(syncPlan.requestBody, fixture.peer.id, fixture.range);
                await expect(syncAssetButton).toBeDisabled();
                syncPlan.hold?.release();

                const syncResponse = await syncResponsePromise;
                expect(syncResponse.status()).toBe(200);
                expect(await syncResponse.finished()).toBeNull();
                expect(await syncResponse.json()).toEqual(assetSyncResponseBody(fixture.peer.id, status));
                await successorComparison.entered.wait;
                assertComparisonRequest(successorComparison.requestBody, [fixture.peer.id], fixture.range);
                expect(fixture.stats.comparisonRequests.length).toBe(comparisonRequestsBefore + 2);
                await expect(syncAssetButton).toBeDisabled();
                await dismissOwnedToast(page, status === 'ok' ? 'success' : 'warning');

                successorComparison.hold?.release();
                const successorResponse = await successorComparisonResponsePromise;
                expect(successorResponse.status()).toBe(200);
                expect(await successorResponse.finished()).toBeNull();
                await expect(syncAssetButton).toBeEnabled();
                await cycleSignalsPanel(signalsToggle, signalsPanel);
                await expectComparisonDataState(signalCard, syncAssetButton, successorHasData);

                oldComparison.hold?.release();
                const oldResponse = await oldComparisonResponsePromise;
                expect(oldResponse.status()).toBe(200);
                expect(await oldResponse.finished()).toBeNull();
                await cycleSignalsPanel(signalsToggle, signalsPanel);
                await expectComparisonDataState(signalCard, syncAssetButton, successorHasData);
                expect(fixture.stats.comparisonRequests.length).toBe(comparisonRequestsBefore + 2);
                currentHasData = successorHasData;
            });
        }

        expect(fixture.stats.assetSyncRequests).toHaveLength(unacceptedCases.length + 2);
        expect(fixture.stats.unplannedAssetSyncRequests).toBe(0);
        expect(fixture.stats.unplannedComparisonRequests).toBe(0);
        await expectNoSyncToasts(page);
    });

    test('discards accepted FX comparison Asset sync completions after range, swap, and navigation changes', async ({page}) => {
        test.setTimeout(90_000);
        const fixture = await installFxComparisonSyncFixture(page);
        const initialComparison = fixture.enqueueComparison('fx-stale-initial', true, 700);
        const initialComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', initialComparison.id);
        const pageRoot = await openSyntheticDetail(page, `/fx/EUR-USD?start=${fixture.range.start}&end=${fixture.range.end}`, 'fx-detail-page');
        await initialComparison.entered.wait;
        assertComparisonRequest(initialComparison.requestBody, [fixture.peer.id], fixture.range);
        const initialComparisonResponse = await initialComparisonResponsePromise;
        expect(initialComparisonResponse.status()).toBe(200);
        expect(await initialComparisonResponse.finished()).toBeNull();

        const signalsToggle = page.getByTestId('fx-detail-signals-toggle');
        const signalsPanel = page.getByTestId('fx-detail-signals-panel');
        await ensureSignalsPanelOpen(signalsToggle, signalsPanel);
        const signalCard = signalsPanel.getByTestId(`signal-card-${fixture.signal.id}`);
        const syncAssetButton = signalCard.getByTestId(`signal-sync-asset-${fixture.signal.id}`);
        await expectComparisonDataState(signalCard, syncAssetButton, true);

        const remountAssetSyncRequestsBefore = fixture.stats.assetSyncRequests.length;
        const remountUnplannedAssetSyncRequestsBefore = fixture.stats.unplannedAssetSyncRequests;
        const rangeSync = fixture.enqueueAssetSync('fx-stale-range', 'ok', true);
        const rangeSyncResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/sync', rangeSync.id);
        await syncAssetButton.click();
        await rangeSync.entered.wait;
        assertAssetSyncRequest(rangeSync.requestBody, fixture.peer.id, fixture.range);
        await expect(syncAssetButton).toBeDisabled();
        await expect(syncAssetButton.locator('svg')).toHaveClass(/animate-spin/);

        // The page owns this per-peer pending state. Collapsing the section
        // destroys ChartSignalsSection; its replacement must still render the
        // same peer action disabled and spinning. A native click() on the
        // disabled remounted button must not admit a second request.
        await signalsToggle.click();
        await expect(signalsToggle).toHaveAttribute('aria-expanded', 'false');
        await expect(signalsPanel).toHaveCount(0);
        await signalsToggle.click();
        await expect(signalsToggle).toHaveAttribute('aria-expanded', 'true');
        await expect(signalsPanel).toBeVisible();
        const remountedSyncAssetButton = signalsPanel.getByTestId(`signal-sync-asset-${fixture.signal.id}`);
        await expect(remountedSyncAssetButton).toBeDisabled();
        await expect(remountedSyncAssetButton.locator('svg')).toHaveClass(/animate-spin/);
        await remountedSyncAssetButton.evaluate((button) => {
            if (!(button instanceof HTMLButtonElement)) throw new Error('FX comparison Asset sync control is not a button');
            button.click();
        });
        expect(fixture.stats.assetSyncRequests.length).toBe(remountAssetSyncRequestsBefore + 1);
        expect(fixture.stats.unplannedAssetSyncRequests).toBe(remountUnplannedAssetSyncRequestsBefore);

        const rangeComparison = fixture.enqueueComparison('fx-stale-range-successor', false, 710);
        const rangeComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', rangeComparison.id);
        const dateRangePicker = page.getByTestId('fx-detail-filter-bar').getByTestId('date-range-picker-root');
        const startInput = dateRangePicker.getByTestId('date-range-input-start');
        const endInput = dateRangePicker.getByTestId('date-range-input-end');
        await startInput.fill(fixture.changedRange.start);
        await expect(startInput).toHaveValue(fixture.changedRange.start);
        await endInput.fill(fixture.changedRange.end);
        await expect(endInput).toHaveValue(fixture.changedRange.end);
        await endInput.press('Enter');
        await rangeComparison.entered.wait;
        assertComparisonRequest(rangeComparison.requestBody, [fixture.peer.id], fixture.changedRange);
        const rangeComparisonResponse = await rangeComparisonResponsePromise;
        expect(rangeComparisonResponse.status()).toBe(200);
        expect(await rangeComparisonResponse.finished()).toBeNull();
        await expect(dateRangePicker).toHaveAttribute('data-open', 'false');
        await expectComparisonDataState(signalCard, syncAssetButton, false);
        await expect(syncAssetButton).toBeDisabled();

        const comparisonsAfterRangeChange = fixture.stats.comparisonRequests.length;
        rangeSync.hold?.release();
        const staleRangeResponse = await rangeSyncResponsePromise;
        expect(staleRangeResponse.status()).toBe(200);
        expect(await staleRangeResponse.finished()).toBeNull();
        expect(await staleRangeResponse.json()).toEqual(assetSyncResponseBody(fixture.peer.id, 'ok'));
        await expect(syncAssetButton).toBeEnabled();
        await cycleSignalsPanel(signalsToggle, signalsPanel);
        await expectNoSyncToasts(page);
        await expectComparisonDataState(signalCard, syncAssetButton, false);
        expect(fixture.stats.comparisonRequests.length).toBe(comparisonsAfterRangeChange);

        const swapSync = fixture.enqueueAssetSync('fx-stale-swap', 'partial', true);
        const swapSyncResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/sync', swapSync.id);
        await syncAssetButton.click();
        await swapSync.entered.wait;
        assertAssetSyncRequest(swapSync.requestBody, fixture.peer.id, fixture.changedRange);
        await expect(syncAssetButton).toBeDisabled();

        const swapComparison = fixture.enqueueComparison('fx-stale-swap-successor', true, 720);
        const swapComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', swapComparison.id);
        await page.getByTestId('fx-detail-swap-btn').click();
        await expect(page).toHaveURL(/\/fx\/USD-EUR(?:\?|$)/, {timeout: 10_000});
        await swapComparison.entered.wait;
        assertComparisonRequest(swapComparison.requestBody, [fixture.peer.id], fixture.changedRange);
        const swapComparisonResponse = await swapComparisonResponsePromise;
        expect(swapComparisonResponse.status()).toBe(200);
        expect(await swapComparisonResponse.finished()).toBeNull();
        await expect(pageRoot).toHaveAttribute('data-chart-pair', 'EUR-USD');
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        await expect(syncAssetButton).toBeDisabled();

        const comparisonsAfterSwap = fixture.stats.comparisonRequests.length;
        swapSync.hold?.release();
        const staleSwapResponse = await swapSyncResponsePromise;
        expect(staleSwapResponse.status()).toBe(200);
        expect(await staleSwapResponse.finished()).toBeNull();
        expect(await staleSwapResponse.json()).toEqual(assetSyncResponseBody(fixture.peer.id, 'partial'));
        await expect(syncAssetButton).toBeEnabled();
        await cycleSignalsPanel(signalsToggle, signalsPanel);
        await expectNoSyncToasts(page);
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        expect(fixture.stats.comparisonRequests.length).toBe(comparisonsAfterSwap);

        const navigationSync = fixture.enqueueAssetSync('fx-stale-navigation', 'ok', true);
        await syncAssetButton.click();
        await navigationSync.entered.wait;
        assertAssetSyncRequest(navigationSync.requestBody, fixture.peer.id, fixture.changedRange);
        await expect(syncAssetButton).toBeDisabled();
        const comparisonsBeforeNavigationCompletion = fixture.stats.comparisonRequests.length;

        await navigateTo(page, '/fx');
        await expect(page).toHaveURL(/\/fx(?:\?|$)/, {timeout: 10_000});
        await expect(page.getByTestId('fx-page')).toBeVisible({timeout: 10_000});
        navigationSync.hold?.release();
        await navigationSync.completed.wait;
        const addPairButton = page.getByTestId('fx-add-pair-button');
        await expect(addPairButton).toBeVisible();
        await addPairButton.click();
        await expect(page.getByTestId('fx-add-pair-modal')).toBeVisible();
        await expectNoSyncToasts(page);
        expect(fixture.stats.comparisonRequests.length).toBe(comparisonsBeforeNavigationCompletion);
        expect(fixture.stats.unplannedAssetSyncRequests).toBe(0);
        expect(fixture.stats.unplannedComparisonRequests).toBe(0);
    });

    // ========================================================================
    // Test 11: Sync single pair
    // ========================================================================
    // Proves the detail page's sync button all the way: the button opens the sync modal — it does not sync — and the
    // modal is the *page* one (assets + FX for this page), not `fx-sync-modal`, which belongs to the FX list. That
    // modal is scoped to this page's pair; starting it syncs exactly that pair over the page's period; the verdict
    // counts what the server stored; the chart reloads onto the synced rates, which are stored day by day; and the
    // button is usable again. On a MOCKFX pair of its own, not the seeded EUR-USD: see the section above the describe.
    test('sync single pair reports its outcome in the modal', async ({page, ownedFxQuotes}) => {
        // Localhost and an offline provider: the budget covers sign-in, setup, the page, the sync and the teardown.
        test.setTimeout(60_000);
        const quote = reservedQuote();
        const pair = `EUR-${quote}`;
        const days = daysBeforeToday(SYNC_PERIOD_DAYS);
        const period = {start: days[0], end: days[days.length - 1]};

        await test.step(`setup: ${pair} routed through MOCKFX alone, with no rate`, async () => {
            // Registered before it exists: the teardown deletes whatever this step got to create.
            ownedFxQuotes.push(quote);
            await resetReservedPair(page, quote, 'precondition');
            await createMockFxRoute(page, quote);
        });

        // Opened by URL: on a full load the query is what seeds the page's period.
        const detail = await openSyntheticDetail(page, `/fx/${pair}?start=${period.start}&end=${period.end}`, 'fx-detail-page');
        await expect(detail, 'the page shows the pair this test created').toHaveAttribute('data-chart-pair', pair);
        await expect(detail, 'precondition: the page has no rate to show').toHaveAttribute('data-chart-last-rate', '');
        // Enabled once the page has loaded a provider other than MANUAL for the pair — the MOCKFX route.
        const syncBtn = page.getByTestId('fx-detail-sync-btn');
        await expect(syncBtn).toBeEnabled({timeout: 10_000});
        await syncBtn.click();

        // One section with one item — this pair, nothing else — and nothing run yet.
        const syncModal = page.getByTestId('page-sync-modal');
        await expect(syncModal).toBeVisible({timeout: 10_000});
        const scope = syncModal.getByTestId('sync-modal-count');
        await expect(scope).toHaveAttribute('data-section-count', '1');
        await expect(scope).toHaveAttribute('data-item-count', '1');
        await expect(syncModal.getByTestId('sync-modal-results')).toHaveCount(0);

        // Armed before the click. The request is part of the subject: it must name this pair over this period, and
        // the answer must come from MOCKFX — which is what keeps the network out.
        const syncRequest = armed(page.waitForRequest(isFxSync, {timeout: 10_000}));
        const syncResponse = armed(page.waitForResponse((response) => isFxSync(response.request()), {timeout: 20_000}));
        await syncModal.getByTestId('sync-modal-start').click();
        assertFxSyncRequest((await syncRequest).postDataJSON(), pair, period);
        const answer = schemas.FXSyncBulkResponse.parse(await jsonFrom(await syncResponse, 'the sync answer'));
        const expected = {pair, status: 'ok', provider_used: 'MOCKFX', points_fetched: days.length, points_changed: days.length};
        expect(answer.results, 'one result, for this pair, served by MOCKFX for every day of the period').toMatchObject([expected]);

        // No toast here, by design: the modal reports in place, so the summary banner *is* the notification. Its
        // tallies are read from the data-* attributes SyncModalBase publishes, never from the translated sentence.
        // Changed = fetched: the pair had no rate.
        const results = syncModal.getByTestId('sync-modal-results');
        await expect(results).toBeVisible({timeout: 10_000});
        const tallies = {'data-total': 1, 'data-success': 1, 'data-failed': 0, 'data-fetched': days.length, 'data-changed': days.length};
        for (const [name, value] of Object.entries(tallies)) await expect(results, name).toHaveAttribute(name, String(value));
        await expect(syncModal.locator(`[data-testid="sync-result-row"][data-row-id="${pair}"]`)).toHaveAttribute('data-status', 'ok');

        await syncModal.getByTestId('sync-modal-close').click();
        await expect(syncModal).toBeHidden();
        await expect(syncBtn).toBeEnabled();
        // A completed sync reloads the chart, which now ends on the rate MOCKFX stored.
        await expect(detail, 'the chart shows the synced rate').toHaveAttribute('data-chart-last-rate', String(MOCKFX_RATE), {timeout: 10_000});

        // Read back through the API: every day of the period has a rate of its own, 1 EUR = 1.2345.
        const readBack = await page.request.post(FX_CONVERT_PATH, {data: [{from_amount: {code: 'EUR', amount: '1'}, to: quote, date_range: period}]});
        const conversion = schemas.FXConvertResponse.parse(await jsonFrom(readBack, `convert 1 EUR to ${quote} over the period`));
        expect(
            conversion.results.map((item) => ({day: item.conversion_date, rate: Number(item.rate), backfilled: item.backward_fill_info ?? null})),
            'one stored rate per day of the period, none carried from another day',
        ).toEqual(days.map((day) => ({day, rate: MOCKFX_RATE, backfilled: null})));
    });

    // ========================================================================
    // Test 12: Refresh data
    // ========================================================================
    test('refresh ownership survives compatible edits and rejects stale continuations', async ({page}) => {
        test.setTimeout(120_000);
        const fixture = await installFxComparisonSyncFixture(page);
        const initialMain = fixture.enqueueMainConvert('fx-refresh-initial-main', true, 1.2, true);
        const initialMainResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', initialMain.id);

        await navigateTo(page, `/fx/EUR-USD?start=${fixture.range.start}&end=${fixture.range.end}`);
        const pageRoot = page.getByTestId('fx-detail-page');
        await expect(pageRoot).toBeVisible({timeout: 15_000});
        await initialMain.entered.wait;
        await expect(pageRoot).toHaveAttribute('data-busy', 'true');

        const signalsToggle = page.getByTestId('fx-detail-signals-toggle');
        const signalsPanel = page.getByTestId('fx-detail-signals-panel');
        await ensureSignalsPanelOpen(signalsToggle, signalsPanel);
        const signalCard = signalsPanel.getByTestId(`signal-card-${fixture.signal.id}`);
        const syncAssetButton = signalCard.getByTestId(`signal-sync-asset-${fixture.signal.id}`);
        const signalStyle = signalCard.getByTestId(`signal-style-${fixture.signal.id}`);
        const styleToggle = signalStyle.getByRole('button');
        const stylePopover = signalStyle.getByTestId('signal-style-popover');
        const selectComparisonAsset = async (assetId: number): Promise<void> => {
            const selectTestId = `signal-param-${fixture.signal.id}-assetId-select`;
            const trigger = signalCard.getByTestId(`${selectTestId}-trigger`);
            await expect(signalCard.getByTestId(selectTestId)).toBeVisible();
            await trigger.press('ArrowDown');
            await expect(trigger).toHaveAttribute('aria-expanded', 'true');
            const option = page.getByTestId(`search-select-option-${assetId}`);
            await expect(option).toBeVisible();
            await option.click();
            await expect(trigger).toHaveAttribute('aria-expanded', 'false');
        };
        const readPersistedSignalState = () =>
            page.evaluate(
                ({pairSlug, signalId}) => {
                    for (const key of Object.keys(localStorage)) {
                        if (!key.endsWith('_chartSettingsStore')) continue;
                        const raw = localStorage.getItem(key);
                        if (!raw) continue;
                        const payload = JSON.parse(raw) as {
                            pairOverrides?: Array<
                                [
                                    string,
                                    {
                                        signals?: Array<{
                                            id?: string;
                                            params?: {assetId?: unknown};
                                            style?: {lineType?: unknown};
                                        }>;
                                    },
                                ]
                            >;
                        };
                        const settings = payload.pairOverrides?.find(([storedSlug]) => storedSlug === pairSlug)?.[1];
                        const signal = settings?.signals?.find((candidate) => candidate.id === signalId);
                        if (signal) {
                            return {
                                assetId: signal.params?.assetId ?? null,
                                lineType: signal.style?.lineType ?? null,
                            };
                        }
                    }
                    return null;
                },
                {pairSlug: 'EUR-USD', signalId: fixture.signal.id},
            );

        // The signal edit calls maybeLoadComparison() while the initial main
        // series is still empty. That early state must not be remembered as a
        // successful fingerprint: initialization must fetch the same peer set
        // once the main conversion arrives.
        await selectComparisonAsset(fixture.replacementPeer.id);
        await expect.poll(readPersistedSignalState).toMatchObject({
            assetId: String(fixture.replacementPeer.id),
        });
        expect(fixture.stats.comparisonRequests).toHaveLength(0);

        const initialComparison = fixture.enqueueComparison('fx-refresh-initial-comparison', true, 300, true);
        const initialComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', initialComparison.id);
        initialMain.hold?.release();
        const initialMainResponse = await initialMainResponsePromise;
        expect(initialMainResponse.status()).toBe(200);
        expect(await initialMainResponse.finished()).toBeNull();
        await initialComparison.entered.wait;
        assertComparisonRequest(initialComparison.requestBody, [fixture.replacementPeer.id], fixture.range);
        initialComparison.hold?.release();
        const initialComparisonResponse = await initialComparisonResponsePromise;
        expect(initialComparisonResponse.status()).toBe(200);
        expect(await initialComparisonResponse.finished()).toBeNull();
        await waitForSettled(pageRoot, 20_000);
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        expect(fixture.stats.comparisonRequests).toHaveLength(1);

        // Once that promise has settled, return from a held range change to the
        // exact applied fingerprint. Both the new owner and the late old owner
        // call maybeLoadComparison(force=false); neither may duplicate it.
        await cycleSignalsPanel(signalsToggle, signalsPanel);
        const dateRangePicker = page.getByTestId('fx-detail-filter-bar').getByTestId('date-range-picker-root');
        const startInput = dateRangePicker.getByTestId('date-range-input-start');
        const endInput = dateRangePicker.getByTestId('date-range-input-end');
        const comparisonsBeforeAppliedReuse = fixture.stats.comparisonRequests.length;
        const awayMain = fixture.enqueueMainConvert('fx-refresh-away-main', true, 1.4, true);
        await startInput.fill(fixture.changedRange.start);
        await expect(startInput).toHaveValue(fixture.changedRange.start);
        await endInput.fill(fixture.changedRange.end);
        await expect(endInput).toHaveValue(fixture.changedRange.end);
        await endInput.press('Enter');
        await awayMain.entered.wait;

        await startInput.fill(fixture.range.start);
        await expect(startInput).toHaveValue(fixture.range.start);
        await endInput.fill(fixture.range.end);
        await expect(endInput).toHaveValue(fixture.range.end);
        await endInput.press('Enter');
        await expect(dateRangePicker).toHaveAttribute('data-open', 'false');
        await cycleSignalsPanel(signalsToggle, signalsPanel);
        await expect(pageRoot).toHaveAttribute('data-busy', 'false');
        expect(fixture.stats.comparisonRequests.length).toBe(comparisonsBeforeAppliedReuse);

        const awayMainResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', awayMain.id);
        awayMain.hold?.release();
        const awayMainResponse = await awayMainResponsePromise;
        expect(awayMainResponse.status()).toBe(200);
        expect(await awayMainResponse.finished()).toBeNull();
        await cycleSignalsPanel(signalsToggle, signalsPanel);
        await expect(startInput).toHaveValue(fixture.range.start);
        await expect(endInput).toHaveValue(fixture.range.end);
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        expect(fixture.stats.comparisonRequests.length).toBe(comparisonsBeforeAppliedReuse);

        // A refresh also captures the URL range. Publish a changed-range main
        // series and comparison while the old refresh is held; the late old
        // response must stop before its forced comparison continuation and
        // must not clear the changed-range state.
        const staleRangeComparisonsBefore = fixture.stats.comparisonRequests.length;
        const staleRangeRefreshMain = fixture.enqueueMainConvert('fx-refresh-stale-range-main', false, 8.1, true);
        const staleRangeRefreshResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', staleRangeRefreshMain.id);
        const refreshButton = page.getByTestId('fx-detail-refresh-btn');
        await expect(refreshButton).toBeEnabled();
        await refreshButton.click();
        await staleRangeRefreshMain.entered.wait;

        const changedRangeMain = fixture.enqueueMainConvert('fx-refresh-changed-range-main', true, 1.55);
        const changedRangeComparison = fixture.enqueueComparison('fx-refresh-changed-range-comparison', true, 310);
        const changedRangeMainResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', changedRangeMain.id);
        const changedRangeComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', changedRangeComparison.id);
        await startInput.fill(fixture.changedRange.start);
        await expect(startInput).toHaveValue(fixture.changedRange.start);
        await endInput.fill(fixture.changedRange.end);
        await expect(endInput).toHaveValue(fixture.changedRange.end);
        await endInput.press('Enter');
        const changedRangeMainResponse = await changedRangeMainResponsePromise;
        expect(changedRangeMainResponse.status()).toBe(200);
        expect(await changedRangeMainResponse.finished()).toBeNull();
        await changedRangeComparison.entered.wait;
        assertComparisonRequest(changedRangeComparison.requestBody, [fixture.replacementPeer.id], fixture.changedRange);
        const changedRangeComparisonResponse = await changedRangeComparisonResponsePromise;
        expect(changedRangeComparisonResponse.status()).toBe(200);
        expect(await changedRangeComparisonResponse.finished()).toBeNull();
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        expect(fixture.stats.comparisonRequests.length).toBe(staleRangeComparisonsBefore + 1);

        staleRangeRefreshMain.hold?.release();
        const staleRangeRefreshResponse = await staleRangeRefreshResponsePromise;
        expect(staleRangeRefreshResponse.status()).toBe(200);
        expect(await staleRangeRefreshResponse.finished()).toBeNull();
        expect((await staleRangeRefreshResponse.json()) as {results?: unknown[]}).toMatchObject({results: []});
        await cycleSignalsPanel(signalsToggle, signalsPanel);
        await expect(startInput).toHaveValue(fixture.changedRange.start);
        await expect(endInput).toHaveValue(fixture.changedRange.end);
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        expect(fixture.stats.comparisonRequests.length).toBe(staleRangeComparisonsBefore + 1);

        const restoreRangeMain = fixture.enqueueMainConvert('fx-refresh-restore-range-main', true, 1.58);
        const restoreRangeComparison = fixture.enqueueComparison('fx-refresh-restore-range-comparison', true, 315);
        const restoreRangeMainResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', restoreRangeMain.id);
        const restoreRangeComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', restoreRangeComparison.id);
        await startInput.fill(fixture.range.start);
        await expect(startInput).toHaveValue(fixture.range.start);
        await endInput.fill(fixture.range.end);
        await expect(endInput).toHaveValue(fixture.range.end);
        await endInput.press('Enter');
        const restoreRangeMainResponse = await restoreRangeMainResponsePromise;
        expect(restoreRangeMainResponse.status()).toBe(200);
        expect(await restoreRangeMainResponse.finished()).toBeNull();
        await restoreRangeComparison.entered.wait;
        assertComparisonRequest(restoreRangeComparison.requestBody, [fixture.replacementPeer.id], fixture.range);
        const restoreRangeComparisonResponse = await restoreRangeComparisonResponsePromise;
        expect(restoreRangeComparisonResponse.status()).toBe(200);
        expect(await restoreRangeComparisonResponse.finished()).toBeNull();
        await expectComparisonDataState(signalCard, syncAssetButton, true);

        // A real force owner still reloads that same fingerprint exactly once.
        const forcedComparisonsBefore = fixture.stats.comparisonRequests.length;
        const forcedMain = fixture.enqueueMainConvert('fx-refresh-forced-main', true, 1.6);
        const forcedComparison = fixture.enqueueComparison('fx-refresh-forced-comparison', true, 320, true);
        const forcedMainResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', forcedMain.id);
        const forcedComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', forcedComparison.id);
        await page.getByTestId('fx-detail-refresh-btn').click();
        await forcedMain.entered.wait;
        expect(forcedMain.requestBody).toEqual([
            expect.objectContaining({
                from_amount: expect.objectContaining({code: 'EUR'}),
                to: 'USD',
                date_range: fixture.range,
            }),
        ]);
        const forcedMainResponse = await forcedMainResponsePromise;
        expect(forcedMainResponse.status()).toBe(200);
        expect(await forcedMainResponse.finished()).toBeNull();
        await forcedComparison.entered.wait;
        assertComparisonRequest(forcedComparison.requestBody, [fixture.replacementPeer.id], fixture.range);
        forcedComparison.hold?.release();
        const forcedComparisonResponse = await forcedComparisonResponsePromise;
        expect(forcedComparisonResponse.status()).toBe(200);
        expect(await forcedComparisonResponse.finished()).toBeNull();
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        expect(fixture.stats.comparisonRequests.length).toBe(forcedComparisonsBefore + 1);

        // The disabled state is committed after the browser task. Dispatching
        // both genuine button activations in one task deterministically starts
        // two handlers without a force click; only the second token may own the
        // final chart and comparison.
        const tokenMainRequestsBefore = fixture.stats.mainConvertRequests.length;
        const tokenComparisonsBefore = fixture.stats.comparisonRequests.length;
        const staleTokenMain = fixture.enqueueMainConvert('fx-refresh-token-old', false, 9.1, true);
        const currentTokenMain = fixture.enqueueMainConvert('fx-refresh-token-current', true, 2.1);
        const currentTokenComparison = fixture.enqueueComparison('fx-refresh-token-comparison', true, 340, true);
        const currentTokenMainResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', currentTokenMain.id);
        const currentTokenComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', currentTokenComparison.id);
        await expect(refreshButton).toBeEnabled();
        await refreshButton.evaluate((button) => {
            if (!(button instanceof HTMLButtonElement)) throw new Error('FX refresh control is not a button');
            button.click();
            button.click();
        });
        await Promise.all([staleTokenMain.entered.wait, currentTokenMain.entered.wait]);
        const currentTokenMainResponse = await currentTokenMainResponsePromise;
        expect(currentTokenMainResponse.status()).toBe(200);
        expect(await currentTokenMainResponse.finished()).toBeNull();
        await currentTokenComparison.entered.wait;
        assertComparisonRequest(currentTokenComparison.requestBody, [fixture.replacementPeer.id], fixture.range);
        currentTokenComparison.hold?.release();
        const currentTokenComparisonResponse = await currentTokenComparisonResponsePromise;
        expect(currentTokenComparisonResponse.status()).toBe(200);
        expect(await currentTokenComparisonResponse.finished()).toBeNull();
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        await expect(pageRoot).toHaveAttribute('data-chart-last-rate', /.+/);
        const currentTokenLastRate = await pageRoot.getAttribute('data-chart-last-rate');
        if (!currentTokenLastRate) throw new Error('Current FX refresh did not publish a chart rate');
        expect(fixture.stats.mainConvertRequests.length).toBe(tokenMainRequestsBefore + 2);
        expect(fixture.stats.comparisonRequests.length).toBe(tokenComparisonsBefore + 1);

        const staleTokenMainResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', staleTokenMain.id);
        staleTokenMain.hold?.release();
        const staleTokenMainResponse = await staleTokenMainResponsePromise;
        expect(staleTokenMainResponse.status()).toBe(200);
        expect(await staleTokenMainResponse.finished()).toBeNull();
        expect((await staleTokenMainResponse.json()) as {results?: unknown[]}).toMatchObject({results: []});
        await cycleSignalsPanel(signalsToggle, signalsPanel);
        await expect(pageRoot).toHaveAttribute('data-chart-last-rate', currentTokenLastRate);
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        expect(fixture.stats.comparisonRequests.length).toBe(tokenComparisonsBefore + 1);

        // Runtime comparison params and line style are not computational
        // context. Update both while a refresh awaits its main conversion; the
        // owner must remain valid and issue its one forced successor.
        const compatibleComparisonsBefore = fixture.stats.comparisonRequests.length;
        const compatibleMain = fixture.enqueueMainConvert('fx-refresh-compatible-main', true, 2.3, true);
        const compatibleMainResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', compatibleMain.id);
        await refreshButton.click();
        await compatibleMain.entered.wait;

        const runtimeSync = fixture.enqueueAssetSync('fx-refresh-runtime-sync', 'ok');
        const runtimeComparison = fixture.enqueueComparison('fx-refresh-runtime-comparison', true, 360);
        const runtimeSyncResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/sync', runtimeSync.id);
        const runtimeComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', runtimeComparison.id);
        await expect(syncAssetButton).toBeEnabled();
        await syncAssetButton.click();
        await runtimeSync.entered.wait;
        assertAssetSyncRequest(runtimeSync.requestBody, fixture.replacementPeer.id, fixture.range);
        const runtimeSyncResponse = await runtimeSyncResponsePromise;
        expect(runtimeSyncResponse.status()).toBe(200);
        expect(await runtimeSyncResponse.finished()).toBeNull();
        await runtimeComparison.entered.wait;
        assertComparisonRequest(runtimeComparison.requestBody, [fixture.replacementPeer.id], fixture.range);
        const runtimeComparisonResponse = await runtimeComparisonResponsePromise;
        expect(runtimeComparisonResponse.status()).toBe(200);
        expect(await runtimeComparisonResponse.finished()).toBeNull();
        await dismissOwnedToast(page, 'success');

        await expect(styleToggle).toBeVisible();
        await styleToggle.click();
        await expect(stylePopover).toBeVisible();
        await signalStyle.getByRole('button', {name: 'dashed', exact: true}).click();
        await expect.poll(readPersistedSignalState).toMatchObject({
            assetId: String(fixture.replacementPeer.id),
            lineType: 'dashed',
        });
        await page.keyboard.press('Escape');
        await expect(stylePopover).toHaveCount(0);

        const compatibleSuccessor = fixture.enqueueComparison('fx-refresh-compatible-successor', true, 380, true);
        const compatibleSuccessorResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', compatibleSuccessor.id);
        compatibleMain.hold?.release();
        const compatibleMainResponse = await compatibleMainResponsePromise;
        expect(compatibleMainResponse.status()).toBe(200);
        expect(await compatibleMainResponse.finished()).toBeNull();
        await compatibleSuccessor.entered.wait;
        assertComparisonRequest(compatibleSuccessor.requestBody, [fixture.replacementPeer.id], fixture.range);
        compatibleSuccessor.hold?.release();
        const compatibleSuccessorResponse = await compatibleSuccessorResponsePromise;
        expect(compatibleSuccessorResponse.status()).toBe(200);
        expect(await compatibleSuccessorResponse.finished()).toBeNull();
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        await expect.poll(readPersistedSignalState).toMatchObject({
            assetId: String(fixture.replacementPeer.id),
            lineType: 'dashed',
        });
        expect(fixture.stats.comparisonRequests.length).toBe(compatibleComparisonsBefore + 2);

        // Changing assetId is computational. Its newer comparison is current;
        // the held refresh captured the replacement peer and must stop before
        // forcing that old peer back over the newly applied result.
        const computationalComparisonsBefore = fixture.stats.comparisonRequests.length;
        const computationalMain = fixture.enqueueMainConvert('fx-refresh-computational-main', true, 2.5, true);
        const computationalMainResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', computationalMain.id);
        await refreshButton.click();
        await computationalMain.entered.wait;

        const computationalComparison = fixture.enqueueComparison('fx-refresh-computational-comparison', true, 400);
        const computationalComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', computationalComparison.id);
        await selectComparisonAsset(fixture.peer.id);
        await computationalComparison.entered.wait;
        assertComparisonRequest(computationalComparison.requestBody, [fixture.peer.id], fixture.range);
        const computationalComparisonResponse = await computationalComparisonResponsePromise;
        expect(computationalComparisonResponse.status()).toBe(200);
        expect(await computationalComparisonResponse.finished()).toBeNull();
        await expect.poll(readPersistedSignalState).toMatchObject({
            assetId: String(fixture.peer.id),
            lineType: 'dashed',
        });
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        expect(fixture.stats.comparisonRequests.length).toBe(computationalComparisonsBefore + 1);

        computationalMain.hold?.release();
        const computationalMainResponse = await computationalMainResponsePromise;
        expect(computationalMainResponse.status()).toBe(200);
        expect(await computationalMainResponse.finished()).toBeNull();
        await cycleSignalsPanel(signalsToggle, signalsPanel);
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        await expect.poll(readPersistedSignalState).toMatchObject({
            assetId: String(fixture.peer.id),
            lineType: 'dashed',
        });
        expect(fixture.stats.comparisonRequests.length).toBe(computationalComparisonsBefore + 1);

        // Finally change the displayed route while an empty refresh response is
        // held. The swapped route's main and comparison data are the positive
        // barrier; the old route may not clear either or force another request.
        const routeComparisonsBefore = fixture.stats.comparisonRequests.length;
        const staleRouteMain = fixture.enqueueMainConvert('fx-refresh-route-old', false, 9.3, true);
        const staleRouteMainResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', staleRouteMain.id);
        await refreshButton.click();
        await staleRouteMain.entered.wait;

        const swappedMain = fixture.enqueueMainConvert('fx-refresh-route-current', true, 2.7);
        const swappedComparison = fixture.enqueueComparison('fx-refresh-route-comparison', true, 420);
        const swappedMainResponsePromise = waitForTaggedResponse(page, '/api/v1/fx/currencies/convert', swappedMain.id);
        const swappedComparisonResponsePromise = waitForTaggedResponse(page, '/api/v1/assets/prices/query', swappedComparison.id);
        await page.getByTestId('fx-detail-swap-btn').click();
        await expect(page).toHaveURL(/\/fx\/USD-EUR(?:\?|$)/, {timeout: 10_000});
        const swappedMainResponse = await swappedMainResponsePromise;
        expect(swappedMainResponse.status()).toBe(200);
        expect(await swappedMainResponse.finished()).toBeNull();
        await swappedComparison.entered.wait;
        assertComparisonRequest(swappedComparison.requestBody, [fixture.peer.id], fixture.range);
        const swappedComparisonResponse = await swappedComparisonResponsePromise;
        expect(swappedComparisonResponse.status()).toBe(200);
        expect(await swappedComparisonResponse.finished()).toBeNull();
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        await expect(pageRoot).toHaveAttribute('data-chart-last-rate', /.+/);
        const swappedLastRate = await pageRoot.getAttribute('data-chart-last-rate');
        if (!swappedLastRate) throw new Error('Swapped FX route did not publish a chart rate');
        expect(fixture.stats.comparisonRequests.length).toBe(routeComparisonsBefore + 1);

        staleRouteMain.hold?.release();
        const staleRouteMainResponse = await staleRouteMainResponsePromise;
        expect(staleRouteMainResponse.status()).toBe(200);
        expect(await staleRouteMainResponse.finished()).toBeNull();
        expect((await staleRouteMainResponse.json()) as {results?: unknown[]}).toMatchObject({results: []});
        await cycleSignalsPanel(signalsToggle, signalsPanel);
        await expect(page).toHaveURL(/\/fx\/USD-EUR(?:\?|$)/);
        await expect(pageRoot).toHaveAttribute('data-chart-last-rate', swappedLastRate);
        await expectComparisonDataState(signalCard, syncAssetButton, true);
        expect(fixture.stats.comparisonRequests.length).toBe(routeComparisonsBefore + 1);
        expect(fixture.stats.unplannedComparisonRequests).toBe(0);
        expect(fixture.stats.unplannedAssetSyncRequests).toBe(0);
    });

    // ========================================================================
    // Test 13: Provider config modal opens in edit mode
    // ========================================================================
    test('provider config modal opens', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-provider-btn').click();
        // The FxPairAddModal should be visible
        const modal = page.getByTestId('fx-add-pair-modal');
        await expect(modal).toBeVisible({timeout: 3000});
    });

    // ========================================================================
    // Test 14: Back to list
    // ========================================================================
    test('back button navigates to FX list', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-back-btn').click();
        await expect(page).toHaveURL(/\/fx$/, {timeout: 10_000});
    });
});

// ============================================================================
// The summary's Δ over the range is the backend's (workstream Y, lot X-R59 A)
// ============================================================================

/** The FX period changes, whatever their query string. */
const FX_PERIOD_CHANGES = /\/api\/v1\/fx\/currencies\/period-changes(\?.*)?$/;

/** The pair the summary is read on: the seeded EUR/USD, canonical (alphabetical) as the backend and the stores key it. */
const RANGE_PAIR = {base: 'EUR', quote: 'USD'} as const;

/** One pair of a period-changes request (`FXPeriodChangesRequest`). */
type FxRangeChangesQuery = {base: string; quote: string; as_of: string; range_start?: string | null};

/** A pair's Δ over the range as a stub answers it (`FXRangeChange`): decimal strings, null where the backend has none. */
type FxRangeChange = {change_abs: string | null; change_ratio: string | null; inverse_change_abs: string | null; inverse_change_ratio: string | null};

/**
 * +42.42 % as configured, −21.21 % inverted, which is neither the inversion of the first (−29.79 %) nor its negation,
 * so the inverted page shows it only by reading `inverse_change_ratio`. No seeded rate moves 42 % in two months: a
 * figure on screen comes from the answer.
 */
const STUBBED_RANGE_CHANGE: FxRangeChange = {change_abs: '0.1234', change_ratio: '0.4242', inverse_change_abs: '-0.0567', inverse_change_ratio: '-0.2121'};

/** What the range of the range-change test answers once changed: −13.13 % as configured, a figure of its own. */
const CHANGED_RANGE_CHANGE: FxRangeChange = {change_abs: '-0.0321', change_ratio: '-0.1313', inverse_change_abs: '0.0222', inverse_change_ratio: '0.1515'};

/** A Δ over the range the backend could not compute: every field null, both ways. */
const NO_RANGE_CHANGE: FxRangeChange = {change_abs: null, change_ratio: null, inverse_change_abs: null, inverse_change_ratio: null};

/** The first day the backend values (`EARLIEST_RANGE_START`): it refuses an earlier `range_start`, and the whole request with it. */
const EARLIEST_RANGE_START = '1900-01-01';

/** What `routePairRangeChanges` saw: every item asked, what went wrong, how many requests it answered. */
type FxRangeChangesLog = {asked: FxRangeChangesQuery[]; failures: string[]; answered: number};

/**
 * The FX period changes, routed through the backend: every request is recorded, and each answer goes back with each
 * pair's `range_change` replaced by what `stubFor` gives for the item that asked it — null: as the backend gave it. A
 * non-OK answer is a failure, passed on as it came.
 */
async function routePairRangeChanges(page: Page, stubFor: (asked: FxRangeChangesQuery) => FxRangeChange | null): Promise<FxRangeChangesLog> {
    const log: FxRangeChangesLog = {asked: [], failures: [], answered: 0};
    await page.route(FX_PERIOD_CHANGES, async (route) => {
        try {
            const body = (route.request().postDataJSON() as FxRangeChangesQuery[] | null) ?? [];
            log.asked.push(...body);
            const response = await route.fetch();
            if (!response.ok()) {
                log.failures.push(`HTTP ${response.status()}: ${await response.text()}`);
                await route.fulfill({response});
                return;
            }
            const answer = (await response.json()) as {items?: Array<{base: string; quote: string; range_change?: Record<string, unknown> | null}>};
            const items = (answer.items ?? []).map((item) => {
                const asked = body.find((query) => query.base === item.base && query.quote === item.quote);
                const stub = asked ? stubFor(asked) : null;
                return stub ? {...item, range_change: {...(item.range_change ?? {}), ...stub}} : item;
            });
            await route.fulfill({response, json: {...answer, items}});
        } catch (error) {
            // Nobody awaits a route callback, so what it throws would land on whatever runs next: recorded, and the
            // request let through, for the test to fail on its own assertions.
            log.failures.push(String(error));
            await route.continue().catch(() => undefined);
        } finally {
            log.answered += 1;
        }
    });
    return log;
}

/**
 * A percentage as any of the four languages writes it, matched whole, as `percentCell` reads a Δ cell of the lists:
 * `+1.25%` (English), `+1,25%` (Italian), `+1,25 %` (French, Spanish: a no-break space before the sign); a minus may be
 * `-` or `−`. The figure is read, never a translation.
 */
function percentText(figure: string): RegExp {
    const parts = /^([+-])(\d+)\.(\d+)$/.exec(figure);
    if (!parts) throw new Error(`percentText: ${figure} is not a signed decimal such as +1.25`);
    return new RegExp(`^\\s*${parts[1] === '+' ? '\\+' : '[-\\u2212]'}${parts[2]}[.,]${parts[3]}\\s?%\\s*$`);
}

/**
 * The pair page's summary shows the pair's Δ over the range on screen (X-R59, lot A): the change from the first to the
 * last day of the range, which the backend computes both ways — the `range_change` of
 * `POST /fx/currencies/period-changes`, asked for the pair canonical (alphabetical) whichever way the URL shows it, from
 * the first day of the range (`range_start`, raised to 1900-01-01, the first day the backend values, for a range that
 * starts before it) to its last (`as_of`): on load, on a range change and after a refresh. Shown as configured the
 * summary reads `change_ratio`; inverted, `inverse_change_ratio`; where the backend has none it draws no Δ beside the
 * rate. The browser computes none.
 *
 * The pair is the seeded EUR/USD, read and never written: the real answer is fetched and only its `range_change` is
 * changed, with figures its rates do not give over these days. The range before 1900 has its rates answered in the
 * browser, empty, so no conversion is walked back over a century; its period changes still reach the backend, which says
 * whether it takes the first day asked. The refresh button publishes the page's big requests (`data-busy`, `pageBusy`),
 * the Δ over the range among them: the barrier before reading what an answer left.
 *
 * Red before the cure of lot A: the page never asks the endpoint — the route never fires — and computes its Δ from the
 * rates it charted.
 */
test.describe('FX pair page — the summary’s Δ over the range is the backend’s (X-R59)', () => {
    // A ceiling, never a delay: the page loads the pair's rates, its signals and its Δ, and some tests load them again.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('the page asks the canonical pair from the first day of the range on screen; the summary shows the answer’s Δ, the inverse one once swapped', async ({page}) => {
        // About two months ending on a known day in the past.
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const expected = {...RANGE_PAIR, as_of: range.end, range_start: range.start};
        try {
            const log = await routePairRangeChanges(page, () => STUBBED_RANGE_CHANGE);
            // Opened by URL: on a full load the query is what seeds the page's period.
            const root = await openSyntheticDetail(page, `/fx/EUR-USD?start=${range.start}&end=${range.end}`, 'fx-detail-page');
            await expect(root, 'premise: the page shows the seeded EUR-USD').toHaveAttribute('data-chart-pair', 'EUR-USD');

            await expect.poll(() => log.answered, {message: 'the pair page never asked POST /fx/currencies/period-changes: its Δ is still computed in the browser', timeout: 10_000}).toBeGreaterThan(0);
            expect(log.failures, 'the period changes reached the page').toEqual([]);
            expect(log.asked, 'the page asks the pair from the first day of the range on screen to the last').toContainEqual(expected);

            const delta = page.getByTestId('fx-price-summary-range-delta');
            await expect(delta, 'as configured: change_ratio 0.4242').toHaveText(percentText('+42.42'), {timeout: 10_000});

            // The page's own swap: the URL shows the pair inverted, and the summary reads the inverse field.
            await page.getByTestId('fx-detail-swap-btn').click();
            await expect(page).toHaveURL(/\/fx\/USD-EUR(?:\?|$)/, {timeout: 10_000});
            await expect(delta, 'inverted: inverse_change_ratio -0.2121').toHaveText(percentText('-21.21'), {timeout: 10_000});
            await expect(page.getByTestId('fx-detail-refresh-btn'), 'what the swap asked is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            expect(log.failures, 'the period changes reached the page').toEqual([]);
            for (const item of log.asked) expect(item, 'whichever way the URL shows the pair, every request asks it canonical over the range on screen').toEqual(expected);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('opened inverted, the page still asks the canonical pair, and the summary shows the answer’s inverse Δ', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const expected = {...RANGE_PAIR, as_of: range.end, range_start: range.start};
        try {
            const log = await routePairRangeChanges(page, () => STUBBED_RANGE_CHANGE);
            const root = await openSyntheticDetail(page, `/fx/USD-EUR?start=${range.start}&end=${range.end}`, 'fx-detail-page');
            await expect(root, 'premise: the page keys the pair canonical, EUR-USD').toHaveAttribute('data-chart-pair', 'EUR-USD');
            await expect(page.getByTestId('fx-detail-pair-label'), 'premise: and shows it inverted, USD → EUR').toHaveText(/USD[\s\S]*EUR/);

            await expect.poll(() => log.answered, {message: 'the pair page never asked POST /fx/currencies/period-changes: its Δ is still computed in the browser', timeout: 10_000}).toBeGreaterThan(0);
            expect(log.failures, 'the period changes reached the page').toEqual([]);
            expect(log.asked, 'the page asks the pair canonical, EUR first, though the URL shows it inverted').toContainEqual(expected);

            await expect(page.getByTestId('fx-price-summary-range-delta'), 'inverted: inverse_change_ratio -0.2121, not the direct +42.42 %').toHaveText(percentText('-21.21'), {timeout: 10_000});
            await expect(page.getByTestId('fx-detail-refresh-btn'), 'the load is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            for (const item of log.asked) expect(item, 'every request asks the pair canonical over the range on screen').toEqual(expected);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('a range change asks the Δ from the new first day, and the summary shows the new answer', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        // A later first day, the same last: the range shrinks to about a month.
        const changed = {start: daysAgoIso(40), end: range.end};
        try {
            // The answer depends on the first day asked: the stub for the first range, a figure of its own for the changed one.
            const log = await routePairRangeChanges(page, (asked) => (asked.range_start === changed.start ? CHANGED_RANGE_CHANGE : STUBBED_RANGE_CHANGE));
            await openSyntheticDetail(page, `/fx/EUR-USD?start=${range.start}&end=${range.end}`, 'fx-detail-page');
            const delta = page.getByTestId('fx-price-summary-range-delta');
            await expect(delta, 'the first range: change_ratio 0.4242').toHaveText(percentText('+42.42'), {timeout: 10_000});
            const refresh = page.getByTestId('fx-detail-refresh-btn');
            await expect(refresh, 'the load is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            const askedBefore = log.asked.length;

            // The range on screen changes through the page's own picker.
            const picker = page.getByTestId('fx-detail-filter-bar').getByTestId('date-range-picker-root');
            const startInput = picker.getByTestId('date-range-input-start');
            const endInput = picker.getByTestId('date-range-input-end');
            await startInput.fill(changed.start);
            await expect(startInput).toHaveValue(changed.start);
            await endInput.fill(changed.end);
            await expect(endInput).toHaveValue(changed.end);
            await endInput.press('Enter');
            await expect(picker, 'the picker closed on the new range').toHaveAttribute('data-open', 'false');

            await expect(delta, 'the changed range: its own answer, change_ratio -0.1313').toHaveText(percentText('-13.13'), {timeout: 10_000});
            await expect(refresh, 'the reload of the changed range is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            expect(log.failures, 'the period changes reached the page').toEqual([]);
            const askedAfter = log.asked.slice(askedBefore);
            expect(askedAfter.length, 'the range change asked the Δ over the range again').toBeGreaterThan(0);
            for (const item of askedAfter) expect(item, 'after the change, every request asks the pair from the new first day to the last').toEqual({...RANGE_PAIR, as_of: changed.end, range_start: changed.start});
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('a refresh asks the Δ again, and an answer with every field null leaves the summary its rate and no Δ', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const expected = {...RANGE_PAIR, as_of: range.end, range_start: range.start};
        let answer: FxRangeChange = STUBBED_RANGE_CHANGE;
        try {
            const log = await routePairRangeChanges(page, () => answer);
            const root = await openSyntheticDetail(page, `/fx/EUR-USD?start=${range.start}&end=${range.end}`, 'fx-detail-page');
            const delta = page.getByTestId('fx-price-summary-range-delta');
            // Presence first: the load's answer is on screen, beside the pair's rate.
            await expect(delta, 'the load: change_ratio 0.4242').toHaveText(percentText('+42.42'), {timeout: 10_000});
            const refresh = page.getByTestId('fx-detail-refresh-btn');
            await expect(refresh, 'the load is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            await expect(refresh).toBeEnabled();

            // The page's refresh, over the same range: this time the backend has no Δ.
            answer = NO_RANGE_CHANGE;
            const askedBefore = log.asked.length;
            const answeredBefore = log.answered;
            await refresh.click();
            await expect.poll(() => log.answered, {message: 'the refresh never asked the Δ over the range again', timeout: 10_000}).toBeGreaterThan(answeredBefore);
            await expect(refresh, 'the refresh is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            expect(log.failures, 'the period changes reached the page').toEqual([]);
            for (const item of log.asked.slice(askedBefore)) expect(item, 'the refresh asks the same pair over the same range').toEqual(expected);

            // The summary still draws its rate — the half the Δ sits beside — and no Δ.
            await expect(root, 'the pair still shows a rate').toHaveAttribute('data-chart-last-rate', /\d/);
            await expect(page.getByTestId('fx-price-summary-missing')).toHaveCount(0);
            await expect(delta, 'every field of range_change is null: no Δ in the summary').toHaveCount(0);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('a range that starts before 1900 asks the Δ from 1900-01-01, which the backend takes', async ({page}) => {
        // A month before the first day the backend values: sent as is, the backend would refuse the whole request.
        const range = {start: '1899-12-01', end: daysAgoIso(10)};
        const expected = {...RANGE_PAIR, as_of: range.end, range_start: EARLIEST_RANGE_START};
        try {
            // The chart's rates answered in the browser, empty: no conversion is walked back over a century.
            await page.route(`**${FX_CONVERT_PATH}`, async (route) => {
                await route.fulfill({json: {results: [], success_count: 0, errors: []}});
            });
            const log = await routePairRangeChanges(page, () => null);
            await openSyntheticDetail(page, `/fx/EUR-USD?start=${range.start}&end=${range.end}`, 'fx-detail-page');

            await expect.poll(() => log.answered, {message: 'the pair page never asked POST /fx/currencies/period-changes', timeout: 10_000}).toBeGreaterThan(0);
            await expect(page.getByTestId('fx-detail-refresh-btn'), 'the load is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            expect(log.failures, 'the backend took every request: none asks a day before the first it values').toEqual([]);
            expect(log.asked, `the page asks the pair from ${EARLIEST_RANGE_START} to the last day of the range`).toContainEqual(expected);
            for (const item of log.asked) expect(item, `never from ${range.start}: the backend would refuse the whole request`).toEqual(expected);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });
});

// ============================================================================
// The provider editor replaces the pair's routes in one write (workstream X, lot X-R75)
// ============================================================================

/** `GET /fx/providers`: the provider capabilities the editor's route picker builds its graph from — not `/routes`. */
const FX_PROVIDERS_PATH = `${API}/fx/providers`;

/** What the browser answers the editor's refused POST with: a fixture string, read on the banner without a translation. */
const REFUSED_ROUTE_WRITE = 'owned-e2e-route-write-refused';

/**
 * The quote currencies of the provider editor's tests, one per test and per Playwright project, because FX routes are
 * global rows. As for `RESERVED_QUOTE`: none is used by any seed, spec or other test (grep of the whole worktree), and
 * each sorts after EUR, so the pair is stored as EUR-X — what `createMockFxRoute` and `resetReservedPair` address.
 */
const EDITOR_QUOTE: Readonly<Record<string, Readonly<Record<'failedSave' | 'removeAll', string>>>> = {
    desktop: {failedSave: 'NIO', removeAll: 'SRD'},
    mobile: {failedSave: 'MOP', removeAll: 'ZMW'},
};

function editorQuote(owner: 'failedSave' | 'removeAll'): string {
    const project = test.info().project.name;
    const quote = EDITOR_QUOTE[project]?.[owner];
    if (!quote) throw new Error(`No currency is reserved for the ${owner} editor test on project "${project}": reserve one that sorts after EUR and that no seed, spec or test uses`);
    return quote;
}

/** The FX routes endpoint, whatever its query string: the cured editor's POST carries `?replace=true`. */
function isFxRoutesUrl(url: URL): boolean {
    return url.pathname === FX_ROUTES_PATH;
}

/** A route as the backend stores it, reduced to what the editor decides: its priority and its steps. */
type StoredRoute = {priority: number; chain_steps: Array<{from: string; to: string; provider: string}>};

/** EUR-`quote` served by MOCKFX alone, as `createMockFxRoute` stores it. */
function mockFxRoute(quote: string): StoredRoute {
    return {priority: 1, chain_steps: [{from: 'EUR', to: quote, provider: 'MOCKFX'}]};
}

/** EUR-`quote` kept with no provider: its MANUAL route, priority 999, the item creation posts for a manual pair. */
function manualRoute(quote: string): StoredRoute {
    return {priority: 999, chain_steps: [{from: 'EUR', to: quote, provider: 'MANUAL'}]};
}

/** The routes stored for EUR-`quote`, by priority, read through the API: never inferred from the page. */
async function storedRoutes(page: Page, quote: string): Promise<StoredRoute[]> {
    const listing = schemas.FXConversionRoutesResponse.parse(await jsonFrom<unknown>(await page.request.get(FX_ROUTES_PATH), 'list the FX routes'));
    return (listing.items ?? [])
        .filter((item) => item.base === 'EUR' && item.quote === quote)
        .sort((a, b) => a.priority - b.priority)
        .map((item) => ({priority: item.priority, chain_steps: item.chain_steps.map(({from, to, provider}) => ({from, to, provider}))}));
}

/** EUR-`quote` with one MOCKFX route and no rate, registered for the teardown before it exists, and verified. */
async function setUpOwnedMockFxPair(page: Page, ownedFxQuotes: string[], quote: string): Promise<void> {
    await test.step(`setup: EUR-${quote} routed through MOCKFX alone, with no rate`, async () => {
        // Registered before it exists: the teardown deletes whatever this step got to create.
        ownedFxQuotes.push(quote);
        await resetReservedPair(page, quote, 'precondition');
        await createMockFxRoute(page, quote);
        expect(await storedRoutes(page, quote), `precondition: EUR-${quote} has its MOCKFX route and no other`).toEqual([mockFxRoute(quote)]);
    });
}

/**
 * `GET /fx/providers` answered in the browser for EUR-`quote`: MOCKFX, the provider of the pair's stored route, native
 * EUR→`quote`, and MOCKFX_FAIL, a second direct route to add, native `quote`→EUR. The picker's DFS walks an edge both
 * ways, so it offers EUR→`quote` through either.
 *
 * Never two providers in the same direction: the picker's currency graph is graphology's default export, the plain
 * `Graph` (mixed, not multi — whatever its local name `MultiDirectedGraph` in `currencyGraph.ts`), which refuses a
 * second edge between the same two currencies in the same direction. `buildCurrencyGraph` then throws, and the picker
 * shows nothing but its error: this setup's first run did exactly that, both providers declared EUR→`quote`.
 *
 * Both are registered test providers (`test_only`), which is why the real list never names them: without this answer
 * the picker could neither show the stored MOCKFX route nor remove it. Answered here, it also keeps ECB's and SNB's
 * currency discovery off the network. Registered before the page is opened: the page builds its graph once and keeps
 * it (`currencyGraphStore`). Every other request goes on.
 */
async function answerProviderCatalog(page: Page, quote: string): Promise<void> {
    const native: ReadonlyArray<readonly [code: string, base: string, target: string]> = [
        ['MOCKFX', 'EUR', quote],
        ['MOCKFX_FAIL', quote, 'EUR'],
    ];
    const catalog = native.map(([code, base, target]) => schemas.FXProviderInfo.parse({code, name: `Owned ${code} fixture`, base_currency: base, base_currencies: [base], target_currencies: [target], description: 'Browser-local deterministic fixture'}));
    const directions = catalog.flatMap((provider) => provider.base_currencies.flatMap((base) => (provider.target_currencies ?? []).map((target) => `${base}→${target}`)));
    if (new Set(directions).size !== directions.length) throw new Error(`answerProviderCatalog: two providers share a direction (${directions.join(', ')}); the picker's graph is not multi and would refuse the second edge`);
    await page.route(
        (url) => url.pathname === FX_PROVIDERS_PATH,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            await route.fulfill({json: catalog});
        },
    );
}

/** The editor's row of one selected route, found by its key (`EUR-X:PROVIDER`), never by its position. */
function selectedRoute(modal: Locator, key: string): Locator {
    return modal.locator(`[data-testid="fx-route-selected"][data-route-key="${key}"]`);
}

/** What a reported text says, without its stack frames: minified, they say where, not what. */
function whatItSays(text: string): string {
    const lines = text.split('\n').filter((line) => !/^\s+at /.test(line));
    return lines.join(' ⏎ ').slice(0, 600);
}

/**
 * What the page reports as broken from now on — its `console.error` lines, with where they come from, and its uncaught
 * exceptions — as a note for the message of a precondition: the first run of this setup failed on «element(s) not found»
 * while the page had logged why. Diagnostics only, never the subject of an assertion: a console message is an edge, so
 * the watch is armed before the navigation it explains.
 */
function watchPageErrors(page: Page): () => string {
    const reported: string[] = [];
    page.on('console', (message) => {
        if (message.type() !== 'error') return;
        const where = message.location().url.replace(/^https?:\/\/[^/]+/, '');
        reported.push(`console.error: ${whatItSays(message.text())}${where ? ` (${where})` : ''}`);
    });
    page.on('pageerror', (error) => reported.push(`uncaught: ${whatItSays(error.stack ?? `${error.name}: ${error.message}`)}`));
    return () => (reported.length === 0 ? ' (the page reported nothing broken)' : `\nWhat the page reported as broken since it was opened:\n${reported.map((line) => `  - ${line}`).join('\n')}`);
}

/**
 * `assertion` retried until it passes or `timeout` runs out, with its message's `note` rebuilt at every attempt from
 * what the page has reported so far: the last attempt's message is the red's, and it lists what was logged until then.
 */
async function expectExplained(note: () => string, assertion: (note: string) => Promise<void>, timeout = 10_000): Promise<void> {
    await expect(async () => assertion(note())).toPass({timeout});
}

/**
 * EUR-`quote`'s page, and its provider editor (the FxPairAddModal in edit mode) opened on it: returned once the editor
 * shows the pair's one stored route, MOCKFX, selected at priority 1 and alone. A precondition that fails says what the
 * page reported as broken (`watchPageErrors`).
 */
async function openProviderEditor(page: Page, quote: string): Promise<Locator> {
    const pair = `EUR-${quote}`;
    const reported = watchPageErrors(page);
    await goToFxDetailPage(page, pair);
    await expect(page.getByTestId('fx-detail-page'), 'the page shows the pair this test created').toHaveAttribute('data-chart-pair', pair);
    // Enabled once the page has loaded a provider other than MANUAL for the pair — the MOCKFX route.
    const syncBtn = page.getByTestId('fx-detail-sync-btn');
    await expectExplained(reported, (note) => expect(syncBtn, `precondition: the page sees the MOCKFX route${note}`).toBeEnabled({timeout: 1_000}));
    await page.getByTestId('fx-detail-provider-btn').click();
    const modal = page.getByTestId('fx-add-pair-modal');
    await expect(modal).toBeVisible();
    // Edit mode loads the pair's stored routes and maps them onto the routes the picker computed from the catalogue.
    const stored = selectedRoute(modal, `${pair}:MOCKFX`);
    await expectExplained(reported, (note) => expect(stored, `the editor shows the stored MOCKFX route${note}`).toBeVisible({timeout: 1_000}));
    await expect(stored).toHaveAttribute('data-priority', '1');
    await expect(modal.getByTestId('fx-route-selected'), 'and no other route').toHaveCount(1);
    return modal;
}

/**
 * The pair page's provider editor (the FxPairAddModal in edit mode) writes the pair's new configuration in one POST that
 * replaces its routes (X-R75): `POST /fx/providers/routes?replace=true`, which keeps exactly the routes posted for the
 * pair, atomically; nothing is deleted first. With every route removed it posts the MANUAL route, priority 999: the
 * pair is kept, manual, as the user guide says.
 *
 * Each test brings a pair of its own, EUR-X with one MOCKFX route and no rate, set up and removed as the sync test's
 * (`ownedFxQuotes`, see the section above the first describe), on a currency reserved per test and per project
 * (`EDITOR_QUOTE`). Only `GET /fx/providers` is answered in the browser (`answerProviderCatalog`), and in the first test
 * the editor's POST: every other request, the routes' reads and writes included, reaches the backend, and what the pair
 * holds is read back through the API.
 *
 * Red before the cure, where the editor DELETEs the whole pair and then POSTs: «a failed save …» — the DELETE went
 * through and the refused POST left the pair with no route; «removing every route …» — with no route picked there is no
 * POST at all, and the pair is gone. Green once cured: the first on the editor's cure alone (its one POST is refused in
 * the browser), the second once the backend honours `replace` too.
 */
test.describe('FX pair page — the provider editor replaces the pair’s routes in one write (X-R75)', () => {
    // A ceiling, never a delay: sign-in, the pair's setup, the page, the editor, a reload and the teardown.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('a failed save keeps the pair’s route', async ({page, ownedFxQuotes}) => {
        const quote = editorQuote('failedSave');
        const pair = `EUR-${quote}`;
        await setUpOwnedMockFxPair(page, ownedFxQuotes, quote);
        try {
            await answerProviderCatalog(page, quote);
            const modal = await openProviderEditor(page, quote);

            // The edit: MOCKFX_FAIL added after the stored MOCKFX route.
            await modal.getByTestId('fx-route-picker-toggle').click();
            await modal.getByTestId('fx-route-picker').getByTestId('fx-route-direct-MOCKFX_FAIL').click();
            await expect(selectedRoute(modal, `${pair}:MOCKFX`)).toHaveAttribute('data-priority', '1');
            await expect(selectedRoute(modal, `${pair}:MOCKFX_FAIL`)).toHaveAttribute('data-priority', '2');

            // From here every write to the routes is recorded, and a POST is refused in the browser with a 500, as a
            // server error would refuse it. Everything else, a DELETE included, reaches the backend.
            const writes: string[] = [];
            const refusePost = async (route: Route) => {
                const request = route.request();
                if (request.method() === 'GET') return route.fallback();
                writes.push(`${request.method()} ${new URL(request.url()).search || '(no query)'}`);
                if (request.method() !== 'POST') return route.fallback();
                await route.fulfill({status: 500, json: {detail: REFUSED_ROUTE_WRITE}});
            };
            await page.route(isFxRoutesUrl, refusePost);
            try {
                const refused = armed(page.waitForRequest((request) => request.method() === 'POST' && isFxRoutesUrl(new URL(request.url())), {timeout: 10_000}));
                await modal.getByTestId('fx-add-pair-save').click();
                await refused;

                // The failure is reported on the editor, which stays open on its draft, ready to save again.
                const banner = modal.getByTestId('info-banner-error');
                await expect(banner, 'the editor shows the refusal').toBeVisible({timeout: 10_000});
                await expect(banner).toContainText(REFUSED_ROUTE_WRITE);
                await expect(modal).toBeVisible();
                await expect(modal.getByTestId('fx-add-pair-save')).toBeEnabled();
                await expect(selectedRoute(modal, `${pair}:MOCKFX_FAIL`), 'the draft is kept').toHaveAttribute('data-priority', '2');
            } finally {
                // Stop refusing: from here on the page talks to the backend again.
                await page.unroute(isFxRoutesUrl, refusePost);
            }

            // A fresh page, on what the backend holds.
            await page.reload();
            const detail = page.getByTestId('fx-detail-page');
            await expect(detail).toBeVisible({timeout: 15_000});
            await waitForSettled(detail, 20_000);

            expect(await storedRoutes(page, quote), `the failed save left ${pair} its MOCKFX route — what the save sent: ${writes.join(', ')}`).toEqual([mockFxRoute(quote)]);
            // Enabled once the page has loaded a provider other than MANUAL for the pair: the MOCKFX route is still there.
            await expect(page.getByTestId('fx-detail-sync-btn'), 'the page still offers to sync the pair').toBeEnabled({timeout: 10_000});
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('removing every route keeps the pair, manual', async ({page, ownedFxQuotes}) => {
        const quote = editorQuote('removeAll');
        const pair = `EUR-${quote}`;
        await setUpOwnedMockFxPair(page, ownedFxQuotes, quote);
        try {
            await answerProviderCatalog(page, quote);
            const modal = await openProviderEditor(page, quote);

            // The edit: the only route removed. The picker offers the catalogue's routes again, none of them selected.
            await selectedRoute(modal, `${pair}:MOCKFX`).getByTestId('fx-route-remove').click();
            await expect(modal.getByTestId('fx-route-picker-toggle'), 'the editor offers routes to add').toBeVisible();
            await expect(modal.getByTestId('fx-route-selected'), 'no route is left selected').toHaveCount(0);

            const since = await eventSeq(page);
            await modal.getByTestId('fx-add-pair-save').click();
            const updated = await waitForEvent(page, 'fx.pair.updated', {since});
            expect(updated.detail, 'the editor saved this pair, with no provider').toMatchObject({slug: pair, hasRealProvider: false});
            await expect(modal).toBeHidden();

            expect(await storedRoutes(page, quote), `${pair} is still configured, with exactly its MANUAL route`).toEqual([manualRoute(quote)]);
            // After the save the page reloads its providers: the sync control, enabled while MOCKFX served the pair (the
            // editor's precondition), is disabled now that only MANUAL is left — `isManualOnly`, MANUAL being no provider.
            await expect(page.getByTestId('fx-detail-sync-btn'), 'the page shows the pair as manual').toBeDisabled({timeout: 10_000});
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });
});

// ============================================================================
// X-R16 — an invalid backend signal result must not cost the pair page its rates
// ============================================================================
// With a backend signal configured, the page asks for the rates of its range and for the signal results in one
// `POST /fx/currencies/convert` (`signals` on the item, `signal_results` on the answer). An invalid result in
// `signal_results[request_index 0].signals` must cost the signal side alone — no result applied, and the
// `signal-backend-error` banner saying the signal results are unavailable — while the rates stay on the chart and
// «All» resolves its start to the first rate date.
//
// Today the invalid result throws, and no branch of the catch resolves «All»: the `withSignals` one never calls
// `resolveMaxStartFromChartData()`. Read statically, the throw does not come from the page's own
// `parseBackendSignalResults` (~563, called ~856) but earlier, from the API client: `zodiosApi` validates every JSON
// answer (`validate: 'response'`, `lib/api/zodios-client.ts`), and `FXSignalQueryResult.signals` is
// `z.array(SignalResult)`, the very schema the page parses with. The whole answer is rejected before its rates reach
// the store, so the catch finds none to keep (`chartData = []`, the client's message in the page's error banner), and
// the page's own parse only ever sees answers the client has already accepted. A try/catch around that parse alone
// therefore leaves both REDs below red: they turn green once the answer is read with signal isolation, as the asset
// page reads its own (`queryAssetPricesBulkWithSignalIsolation` → `parseAssetPriceQueryWithSignalIsolation`).
//
// The pair is the seeded EUR-USD, read and never written: its rates (60 daily rates ending yesterday), its signal
// catalog (RSI alone, the definition «persists distinct primary scales and the semantic RSI scale across reload»
// serves) and its signal results all come from route mocks. The RSI signal is stored in this context's localStorage,
// where the chart settings live. «All» is opened by URL (`?start=min&end=max`, the form the page writes itself), so the
// first load is the «All» load, signal included. Nothing reaches the database: there is nothing to clean up.
// ============================================================================
test.describe('X-R16 FX detail: an invalid signal result keeps the rates and the All range', () => {
    // A ceiling, never a delay: a sign-in, the stored signal, a page load and the round trips each test waits for by name.
    test.describe.configure({timeout: 60_000});

    /** The seeded pair, canonical: read, never written — every rate on screen comes from the route below. */
    const PAIR = 'EUR-USD';
    /** The RSI signal stored on the pair: the page asks for it under this `instance_id`. */
    const RSI_ID = 'x-r16-rsi';
    /** The FX signal catalog the page loads: RSI alone, without parameters, so the stored signal needs none. */
    const RSI_DEFINITION = {
        signal_code: 'RSI',
        implementation_version: '1.0.0',
        category: 'momentum',
        display_name_key: 'signals.rsi',
        description_key: 'signals.rsi.description',
        semantic_id: 'technical.rsi',
        semantic_description: 'Relative Strength Index.',
        icon: '📊',
        params_schema: {type: 'object', properties: {}},
        default_params: {},
        input_requirements: {price_fields: ['close'], data_policy: 'strict_contiguous', minimum_coverage: 1},
        output_specs: [
            {
                key: 'rsi',
                label_key: 'signals.rsi.value',
                semantic_id: 'technical.rsi.value',
                semantic_description: 'Relative Strength Index values.',
                unit: 'index',
                axis: {key: 'rsi', role: 'independent', minimum: 0, maximum: 100},
                view_transform: 'none',
                kind: 'line',
                aggregation_profile: 'last_with_range',
            },
        ],
        compatible_domains: ['fx'],
    };
    /** The RSI series of a valid answer, without its points. */
    const RSI_SERIES = {key: 'rsi', label_key: 'signals.rsi.value', semantic_id: 'technical.rsi.value', semantic_description: 'Relative Strength Index values.', unit: 'index', axis: {key: 'rsi', role: 'independent', minimum: 0, maximum: 100}, view_transform: 'none', kind: 'line'};

    /** The fields of a `/fx/currencies/convert` item these tests read. */
    type ConvertAsk = {from_amount?: {code?: string}; to?: string; date_range?: {start?: string; end?: string | null}; signals?: Array<{instance_id?: string; signal_code?: string}>};
    /** An item the route has answered: logged once its answer is delivered, not when it is asked. */
    type DeliveredAsk = {start: string | null; signalCodes: string[]};
    /** How the route answers each signal asked: with a result the schema rejects, or with an RSI series over the rates it answers. */
    type SignalAnswer = 'invalid' | 'valid';

    /** Stores the RSI signal on the pair where the page reads it: this context's localStorage, under the signed-in user's key. */
    async function storeRsiSignal(page: Page): Promise<void> {
        const me = await page.request.get('/api/v1/auth/me');
        expect(me.ok(), `GET /api/v1/auth/me answered HTTP ${me.status()}`).toBe(true);
        const userId = ((await me.json()) as {user?: {id?: unknown}}).user?.id;
        if (typeof userId !== 'number' || !Number.isSafeInteger(userId)) throw new Error('GET /api/v1/auth/me returned no user id, and the chart settings are stored under it');
        const settings = (signals: object[]) => ({colorByBaseline: true, areaFill: true, gridLines: true, staleGradient: true, axisScales: {absolute: {mode: 'auto'}, percentage: {mode: 'include0'}, secondary: {}}, signals});
        const rsi = {id: RSI_ID, signalType: 'rsi', params: {}, style: {color: '#7c3aed', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null}};
        await page.evaluate(({key, value}) => localStorage.setItem(key, value), {key: `lf_${userId}_chartSettingsStore`, value: JSON.stringify({version: 3, globalSettings: settings([]), pairOverrides: [[PAIR, settings([rsi])]]})});
    }

    /** The FX signal catalog, RSI alone. */
    async function routeRsiCatalog(page: Page): Promise<void> {
        await page.route(
            (url) => url.pathname === '/api/v1/fx/currencies/signals',
            (route) => route.fulfill({status: 200, contentType: 'application/json', json: {items: [RSI_DEFINITION]}}),
        );
    }

    /**
     * Serves the pair's conversions: 60 daily rates ending yesterday, those inside each item's range, and for an item
     * that asks for signals its `signal_results` group, answered as `answer` says. Returns the items delivered, the date
     * of the first rate and the last rate as the page publishes it (`data-chart-last-rate`).
     */
    async function routePairRates(page: Page, answer: SignalAnswer) {
        const history = Array.from({length: 60}, (_, index) => daysAgoIso(60 - index));
        const rateAt = (index: number) => (1.1 + index / 1000).toFixed(4);
        const delivered: DeliveredAsk[] = [];
        await page.route(
            (url) => url.pathname === '/api/v1/fx/currencies/convert',
            async (route) => {
                // postDataJSON throws on an empty or non-JSON body, and nobody awaits a route callback: read it as no item.
                let asks: ConvertAsk[] = [];
                try {
                    const body: unknown = route.request().postDataJSON();
                    asks = Array.isArray(body) ? body.filter((ask): ask is ConvertAsk => ask !== null && typeof ask === 'object') : [];
                } catch {
                    asks = [];
                }
                const results: object[] = [];
                const signalResults: object[] = [];
                asks.forEach((ask, requestIndex) => {
                    const from = ask.from_amount?.code ?? 'EUR';
                    const to = ask.to ?? 'USD';
                    const start = ask.date_range?.start ?? '';
                    const end = ask.date_range?.end ?? start;
                    const days = history.flatMap((date, index) => (date >= start && date <= end ? [{date, rate: rateAt(index)}] : []));
                    for (const day of days) results.push({from_amount: {code: from, amount: '1'}, to_amount: {code: to, amount: day.rate}, conversion_date: day.date, rate: day.rate, backward_fill_info: null});
                    const asked = ask.signals ?? [];
                    if (asked.length === 0) return;
                    signalResults.push({
                        request_index: requestIndex,
                        from_currency: from,
                        to_currency: to,
                        date_range: {start, end},
                        signals: asked.map((signal) => {
                            const identity = {instance_id: signal.instance_id ?? RSI_ID, signal_code: signal.signal_code ?? 'RSI'};
                            if (answer === 'invalid') return {...identity, status: 'not-a-status'};
                            if (days.length === 0) return {...identity, status: 'unavailable'};
                            return {...identity, implementation_version: '1.0.0', normalized_params: {}, status: 'ok', series: [{...RSI_SERIES, points: days.map((day, index) => ({date: day.date, value: 40 + (index % 20)}))}]};
                        }),
                    });
                });
                await route.fulfill({status: 200, contentType: 'application/json', json: {results, success_count: results.length, signal_results: signalResults}});
                for (const ask of asks) delivered.push({start: ask.date_range?.start ?? null, signalCodes: (ask.signals ?? []).map((signal) => signal.signal_code ?? '')});
            },
        );
        return {delivered, firstRateDate: history[0], lastRate: String(Number(rateAt(history.length - 1)))};
    }

    /** Opens the pair page on «All» by URL and verifies, rather than assumes, that «All» is the range on screen; returns the page's root and the start field of the range. */
    async function openPairOnAll(page: Page): Promise<{root: Locator; startInput: Locator}> {
        await navigateTo(page, `/fx/${PAIR}?start=min&end=max`);
        const root = page.getByTestId('fx-detail-page');
        await expect(root, 'the pair page renders once its URL has landed').toBeVisible({timeout: 10_000});
        await waitForSettled(root, 20_000);
        // By design the page keeps the generic sentinel in its URL for as long as «All» is selected.
        await expect(page, '«All» is selected: the URL keeps its min sentinel').toHaveURL(/[?&]start=min(?:&|$)/, {timeout: 30_000});
        const picker = page.getByTestId('fx-detail-filter-bar').getByTestId('date-range-picker-root');
        await expect(picker.getByTestId('date-preset-max'), '«All» is the active preset').toHaveAttribute('data-active', 'true', {timeout: 10_000});
        return {root, startInput: picker.getByTestId('date-range-input-start')};
    }

    /**
     * The first load was the «All» one with the stored signal: the rates were asked for from the 2000-01-01 sentinel
     * together with RSI, and answered. The page builds that request only from the catalog's RSI definition — with the
     * catalog failed it falls back to the local definitions, which hold no RSI — so this also proves the catalog loaded.
     */
    async function expectRsiAskedOverAll(delivered: DeliveredAsk[]): Promise<void> {
        await expect.poll(() => delivered.some((ask) => ask.start === '2000-01-01' && ask.signalCodes.includes('RSI')), {message: 'the page asked for the «All» rates from the 2000-01-01 sentinel together with the stored RSI signal, and the route answered', timeout: 15_000}).toBe(true);
    }

    /** Unfolds the signals panel, and returns it once it lists the stored RSI signal. */
    async function openSignalsPanel(page: Page): Promise<Locator> {
        const toggle = page.getByTestId('fx-detail-signals-toggle');
        const panel = page.getByTestId('fx-detail-signals-panel');
        await expect(toggle).toBeVisible({timeout: 10_000});
        if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
        await expect(toggle, 'the toggle publishes open').toHaveAttribute('aria-expanded', 'true');
        await expect(panel).toBeVisible();
        await expect(panel.getByTestId(`signal-card-${RSI_ID}`), 'the panel lists the stored RSI signal').toBeVisible({timeout: 10_000});
        return panel;
    }

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // RED — pins the «All» half on the pair page. Before the cure toHaveValue times out on the picker's pending label
    // (`Received: "Finding…"` in English): no branch of the catch resolves «All». Green once the answer is read with
    // signal isolation and the rates go on — not with a try/catch around the page's own parse alone (see above).
    test('X-R16 RED FX: an invalid signal result still lets All resolve its start to the first rate date', async ({page}) => {
        await storeRsiSignal(page);
        await routeRsiCatalog(page);
        const rates = await routePairRates(page, 'invalid');
        const {startInput} = await openPairOnAll(page);
        await expectRsiAskedOverAll(rates.delivered);

        await expect(startInput, '«All» resolves its start to the first rate').toHaveValue(rates.firstRateDate, {timeout: 10_000});
    });

    // RED — pins the rates half: the rates of the answer stay on the chart. Before the cure the attribute is empty
    // (`Received: ""`): the API client rejects the whole answer before its rates reach the store, so the catch has none
    // to keep. Asserted apart from the start field, so each RED pins one of the two things the invalid result costs.
    test('X-R16 RED FX: an invalid signal result still leaves the rates on the chart', async ({page}) => {
        await storeRsiSignal(page);
        await routeRsiCatalog(page);
        const rates = await routePairRates(page, 'invalid');
        const {root} = await openPairOnAll(page);
        await expectRsiAskedOverAll(rates.delivered);

        await expect(root, 'the chart ends on the last rate answered').toHaveAttribute('data-chart-last-rate', rates.lastRate, {timeout: 10_000});
    });

    // GUARD — the intended part, green before the cure and after it: the signal side fails, and says so. The banner can
    // only be the signal results one: the request carried RSI, so the catalog loaded (expectRsiAskedOverAll), and the
    // catalog banner needs the catalog failed. Asserted by its test id, never by its sentence.
    test('X-R16 GUARD FX: an invalid signal result shows the signal results banner', async ({page}) => {
        await storeRsiSignal(page);
        await routeRsiCatalog(page);
        const rates = await routePairRates(page, 'invalid');
        await openPairOnAll(page);
        await expectRsiAskedOverAll(rates.delivered);

        const panel = await openSignalsPanel(page);
        await expect(panel.getByTestId('signal-backend-error'), 'the panel says the signal results are unavailable').toBeVisible({timeout: 10_000});
    });

    // GUARD — the same flow with a valid RSI answer, green before the cure and after it: «All» resolves to the first
    // rate, the rates stay on the chart, and no banner shows — absent once the panel and the signal's card are on screen.
    test('X-R16 GUARD FX: with a valid signal result, All resolves, the rates stay and no banner shows', async ({page}) => {
        await storeRsiSignal(page);
        await routeRsiCatalog(page);
        const rates = await routePairRates(page, 'valid');
        const {root, startInput} = await openPairOnAll(page);
        await expectRsiAskedOverAll(rates.delivered);

        await expect(startInput, '«All» resolves its start to the first rate').toHaveValue(rates.firstRateDate, {timeout: 10_000});
        await expect(root, 'the chart ends on the last rate answered').toHaveAttribute('data-chart-last-rate', rates.lastRate, {timeout: 10_000});
        const panel = await openSignalsPanel(page);
        await expect(panel.getByTestId('signal-backend-error'), 'a valid answer raises no banner').toHaveCount(0);
    });
});

// ============================================================================
// N64 — FX pair detail: a signal result already answered is not asked again
// ============================================================================
// The pair page keeps a client cache of the backend's signal results beside its rate cache. Before N64 every load with a
// backend indicator configured re-posted `/api/v1/fx/currencies/convert`, even for a period the page had already
// answered with that very indicator. Now the return to such a period asks nothing, and the Refresh button — which empties
// the caches — still does.
//
// The pair is the seeded EUR-USD, read and never written: its rates (130 daily rates ending yesterday), its signal catalog
// (RSI alone, as in the X-R16 block above) and its signal results come from route mocks, so that every request is
// answered the same way and the period change is a cache question, not a data one. The RSI signal is stored in this
// context's localStorage, where the chart settings live: Playwright gives each test a context of its own, so the signal
// never reaches another test, and nothing reaches the database — there is nothing to clean up.
//
// The requests are counted by a listener armed right before the last action and removed right after it. «Drawn» is read
// from the number of series the chart's ECharts option holds, never from the points of a series: the chart re-chooses its
// resolution (daily, weekly, monthly) with hysteresis, so the same range can legitimately draw another number of points.
// ============================================================================
test.describe('N64 FX detail: a signal result already answered is not asked again', () => {
    // A ceiling, never a delay: a sign-in, the stored signal, a page load and the round trips each test waits for by name.
    test.describe.configure({timeout: 60_000});

    /** The seeded pair, canonical: read, never written — every rate on screen comes from the route below. */
    const PAIR = 'EUR-USD';
    /** The RSI signal stored on the pair: the page asks for it under this `instance_id`. */
    const RSI_ID = 'n64-rsi';
    const CONVERT_PATH = '/api/v1/fx/currencies/convert';
    /** The FX signal catalog the page loads: RSI alone, without parameters, so the stored signal needs none (as in the X-R16 block above). */
    const RSI_DEFINITION = {
        signal_code: 'RSI',
        implementation_version: '1.0.0',
        category: 'momentum',
        display_name_key: 'signals.rsi',
        description_key: 'signals.rsi.description',
        semantic_id: 'technical.rsi',
        semantic_description: 'Relative Strength Index.',
        icon: '📊',
        params_schema: {type: 'object', properties: {}},
        default_params: {},
        input_requirements: {price_fields: ['close'], data_policy: 'strict_contiguous', minimum_coverage: 1},
        output_specs: [
            {
                key: 'rsi',
                label_key: 'signals.rsi.value',
                semantic_id: 'technical.rsi.value',
                semantic_description: 'Relative Strength Index values.',
                unit: 'index',
                axis: {key: 'rsi', role: 'independent', minimum: 0, maximum: 100},
                view_transform: 'none',
                kind: 'line',
                aggregation_profile: 'last_with_range',
            },
        ],
        compatible_domains: ['fx'],
    };
    /** The RSI series of a valid answer, without its points. */
    const RSI_SERIES = {key: 'rsi', label_key: 'signals.rsi.value', semantic_id: 'technical.rsi.value', semantic_description: 'Relative Strength Index values.', unit: 'index', axis: {key: 'rsi', role: 'independent', minimum: 0, maximum: 100}, view_transform: 'none', kind: 'line'};

    /** The fields of a `/fx/currencies/convert` item these tests read. */
    type ConvertAsk = {from_amount?: {code?: string}; to?: string; date_range?: {start?: string; end?: string | null}; signals?: Array<{instance_id?: string; signal_code?: string}>};
    /** An item the route has answered: logged once its answer is delivered, not when it is asked. */
    type DeliveredAsk = {start: string | null; signalCodes: string[]};

    /** Stores the RSI signal on the pair where the page reads it: this context's localStorage, under the signed-in user's key. */
    async function storeRsiSignal(page: Page): Promise<void> {
        const me = await page.request.get('/api/v1/auth/me');
        expect(me.ok(), `GET /api/v1/auth/me answered HTTP ${me.status()}`).toBe(true);
        const userId = ((await me.json()) as {user?: {id?: unknown}}).user?.id;
        if (typeof userId !== 'number' || !Number.isSafeInteger(userId)) throw new Error('GET /api/v1/auth/me returned no user id, and the chart settings are stored under it');
        const settings = (signals: object[]) => ({colorByBaseline: true, areaFill: true, gridLines: true, staleGradient: true, axisScales: {absolute: {mode: 'auto'}, percentage: {mode: 'include0'}, secondary: {}}, signals});
        const rsi = {id: RSI_ID, signalType: 'rsi', params: {}, style: {color: '#7c3aed', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null}};
        await page.evaluate(({key, value}) => localStorage.setItem(key, value), {key: `lf_${userId}_chartSettingsStore`, value: JSON.stringify({version: 3, globalSettings: settings([]), pairOverrides: [[PAIR, settings([rsi])]]})});
    }

    /** The FX signal catalog, RSI alone. */
    async function routeRsiCatalog(page: Page): Promise<void> {
        await page.route(
            (url) => url.pathname === '/api/v1/fx/currencies/signals',
            (route) => route.fulfill({status: 200, contentType: 'application/json', json: {items: [RSI_DEFINITION]}}),
        );
    }

    /**
     * Serves the pair's conversions: 130 daily rates ending yesterday, those inside each item's range, and for an item that
     * asks for signals its `signal_results` group with a valid RSI series over the rates it answers. Returns the items
     * delivered — logged once their answer is out, not when they are asked.
     */
    async function routePairRates(page: Page): Promise<DeliveredAsk[]> {
        const history = Array.from({length: 130}, (_, index) => daysAgoIso(130 - index));
        const rateAt = (index: number) => (1.1 + index / 1000).toFixed(4);
        const delivered: DeliveredAsk[] = [];
        await page.route(
            (url) => url.pathname === CONVERT_PATH,
            async (route) => {
                // postDataJSON throws on an empty or non-JSON body, and nobody awaits a route callback: read it as no item.
                let asks: ConvertAsk[] = [];
                try {
                    const body: unknown = route.request().postDataJSON();
                    asks = Array.isArray(body) ? body.filter((ask): ask is ConvertAsk => ask !== null && typeof ask === 'object') : [];
                } catch {
                    asks = [];
                }
                const results: object[] = [];
                const signalResults: object[] = [];
                asks.forEach((ask, requestIndex) => {
                    const from = ask.from_amount?.code ?? 'EUR';
                    const to = ask.to ?? 'USD';
                    const start = ask.date_range?.start ?? '';
                    const end = ask.date_range?.end ?? start;
                    const days = history.flatMap((date, index) => (date >= start && date <= end ? [{date, rate: rateAt(index)}] : []));
                    for (const day of days) results.push({from_amount: {code: from, amount: '1'}, to_amount: {code: to, amount: day.rate}, conversion_date: day.date, rate: day.rate, backward_fill_info: null});
                    const asked = ask.signals ?? [];
                    if (asked.length === 0) return;
                    signalResults.push({
                        request_index: requestIndex,
                        from_currency: from,
                        to_currency: to,
                        date_range: {start, end},
                        signals: asked.map((signal) => {
                            const identity = {instance_id: signal.instance_id ?? RSI_ID, signal_code: signal.signal_code ?? 'RSI'};
                            if (days.length === 0) return {...identity, status: 'unavailable'};
                            return {...identity, implementation_version: '1.0.0', normalized_params: {}, status: 'ok', series: [{...RSI_SERIES, points: days.map((day, index) => ({date: day.date, value: 40 + (index % 20)}))}]};
                        }),
                    });
                });
                await route.fulfill({status: 200, contentType: 'application/json', json: {results, success_count: results.length, signal_results: signalResults}});
                for (const ask of asks) delivered.push({start: ask.date_range?.start ?? null, signalCodes: (ask.signals ?? []).map((signal) => signal.signal_code ?? '')});
            },
        );
        return delivered;
    }

    /** True for a `/fx/currencies/convert` POST one of whose items asks for the RSI signal. */
    function asksForRsi(request: Request): boolean {
        if (request.method() !== 'POST' || new URL(request.url()).pathname !== CONVERT_PATH) return false;
        let body: unknown;
        try {
            body = request.postDataJSON();
        } catch {
            return false;
        }
        return Array.isArray(body) && body.some((item) => item !== null && typeof item === 'object' && ((item as ConvertAsk).signals ?? []).some((signal) => signal.signal_code === 'RSI'));
    }

    /** The `/fx/currencies/convert` POSTs the page sends from now until `stop()`. Armed before the action it measures, so none it sends is missed. */
    function watchConvertPosts(page: Page) {
        const sent: Request[] = [];
        const onRequest = (request: Request) => {
            if (request.method() === 'POST' && new URL(request.url()).pathname === CONVERT_PATH) sent.push(request);
        };
        page.on('request', onRequest);
        return {sent, stop: () => page.off('request', onRequest)};
    }

    /** How many series the pair chart's ECharts option holds: the rates, the indicators, the event markers. 0 while no chart is mounted. */
    async function readSeriesCount(page: Page): Promise<number> {
        return page.evaluate((): number => {
            type ChartHost = HTMLElement & {__lfChart?: {getOption: () => {series?: unknown}}};
            const root = document.querySelector<HTMLElement>('[data-testid="fx-detail-chart"]');
            if (!root) return 0;
            const candidates = [root, ...root.querySelectorAll<HTMLElement>('*')];
            const host = candidates.find((candidate) => typeof (candidate as ChartHost).__lfChart?.getOption === 'function') as ChartHost | undefined;
            const series = host?.__lfChart?.getOption().series;
            return Array.isArray(series) ? series.length : 0;
        });
    }

    /**
     * Opens the pair with its stored RSI on the page's default period and waits until the first load has asked for the
     * indicator, been answered and released the page token. 1M and 3M are core presets of the picker, drawn at any width.
     */
    async function openPairWithRsi(page: Page) {
        await storeRsiSignal(page);
        await routeRsiCatalog(page);
        const delivered = await routePairRates(page);
        await goToFxDetailPage(page, PAIR);
        await expect.poll(() => delivered.some((ask) => ask.signalCodes.includes('RSI')), {message: 'the first load asked for the stored RSI signal, and the route answered', timeout: 15_000}).toBe(true);
        const refresh = page.getByTestId('fx-detail-refresh-btn');
        await expect(refresh, 'the first load has released the page token').toHaveAttribute('data-busy', 'false', {timeout: 15_000});
        const picker = page.getByTestId('fx-detail-filter-bar').getByTestId('date-range-picker-root');
        const startInput = picker.getByTestId('date-range-input-start');
        const shortPeriod = picker.getByTestId('date-preset-1m');
        const longPeriod = picker.getByTestId('date-preset-3m');
        // The stored RSI is on the chart beside the rates: more than one series, or the returns below could not tell it was drawn.
        await expect.poll(() => readSeriesCount(page), {message: 'the stored RSI is drawn beside the rates', timeout: 10_000}).toBeGreaterThan(1);

        /** A period nothing has answered yet: the click asks the server, with the indicator, and the page is waited on until it is quiet again. */
        const pickPeriodAsked = async (period: Locator): Promise<string> => {
            await period.click();
            await expect(period, 'the period is selected').toHaveAttribute('data-active', 'true');
            const start = await startInput.inputValue();
            await expect.poll(() => delivered.some((ask) => ask.start === start && ask.signalCodes.includes('RSI')), {message: `the page asked for the RSI over the rates from ${start}, and the route answered`, timeout: 15_000}).toBe(true);
            await expect(refresh, 'the page token of the period change is released').toHaveAttribute('data-busy', 'false', {timeout: 15_000});
            await expect.poll(() => readSeriesCount(page), {message: 'the RSI is drawn over this period', timeout: 10_000}).toBeGreaterThan(1);
            return start;
        };
        return {refresh, startInput, shortPeriod, longPeriod, pickPeriodAsked};
    }

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // The pair's own version of the developer's test: with a backend indicator configured, period A, period B, period A.
    // Before N64 every load with a signal re-posted the conversion; the return to A now asks nothing.
    test('N64 returning to a period already answered, with an indicator configured, posts no conversion request', async ({page}) => {
        const {refresh, startInput, shortPeriod, longPeriod, pickPeriodAsked} = await openPairWithRsi(page);
        const root = page.getByTestId('fx-detail-page');
        const shortStart = await pickPeriodAsked(shortPeriod);
        const seriesOfShortPeriod = await readSeriesCount(page);
        const longStart = await pickPeriodAsked(longPeriod);
        expect(longStart, 'the second period is another range, or the return below proves nothing').not.toBe(shortStart);

        // The return: asked and answered once, so it comes from the cache — rates and indicator alike.
        const converts = watchConvertPosts(page);
        await shortPeriod.click();
        await expect(shortPeriod, 'the period is selected again').toHaveAttribute('data-active', 'true');
        await expect(startInput, 'the range is the first period again').toHaveValue(shortStart);
        await expect(refresh, 'the page token of the period change is released').toHaveAttribute('data-busy', 'false', {timeout: 15_000});
        await waitForSettled(root, 20_000);
        await expect.poll(() => readSeriesCount(page), {message: 'the cached period draws its indicator again', timeout: 10_000}).toBe(seriesOfShortPeriod);
        converts.stop();

        expect(
            converts.sent.map((request) => request.postData() ?? ''),
            'the return to a period already answered posts no conversion request',
        ).toEqual([]);
    });

    // GUARD — the cache must not make the page deaf: Refresh empties the caches, so it still asks, with the indicator.
    test('N64 the Refresh button still posts a conversion request after a period was served from the cache', async ({page}) => {
        const {refresh, shortPeriod, longPeriod, pickPeriodAsked} = await openPairWithRsi(page);
        await pickPeriodAsked(shortPeriod);
        await pickPeriodAsked(longPeriod);
        await shortPeriod.click();
        await expect(shortPeriod, 'the period is selected again').toHaveAttribute('data-active', 'true');
        await expect(refresh).toHaveAttribute('data-busy', 'false', {timeout: 15_000});

        const refreshAsked = page.waitForRequest(asksForRsi, {timeout: 15_000});
        refreshAsked.catch(() => undefined);
        await refresh.click();
        await refreshAsked;
        await expect(refresh, 'the page token of the refresh is released').toHaveAttribute('data-busy', 'false', {timeout: 15_000});
    });
});
