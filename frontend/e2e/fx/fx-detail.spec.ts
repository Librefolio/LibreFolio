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

import {expect, test} from '../fixtures/playwright';
import type {Locator, Page, Response} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
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
    test('aesthetics panel toggles visibility', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const toggle = page.getByTestId('fx-detail-aesthetics-toggle');
        await toggle.click();
        await expect(page.getByTestId('fx-detail-aesthetics-panel')).toBeVisible();
        await toggle.click();
        await expect(page.getByTestId('fx-detail-aesthetics-panel')).not.toBeVisible();
    });

    // ========================================================================
    // Test 7: Signals panel fold/unfold
    // ========================================================================
    test('signals panel toggles visibility', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        const toggle = page.getByTestId('fx-detail-signals-toggle');
        await toggle.click();
        await expect(page.getByTestId('fx-detail-signals-panel')).toBeVisible();
        await toggle.click();
        await expect(page.getByTestId('fx-detail-signals-panel')).not.toBeVisible();
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

        await page.getByTestId('fx-detail-aesthetics-toggle').click();
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
        await page.getByTestId('fx-detail-aesthetics-toggle').click();
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

        fixture.conversionFailures.add(gbpPeer.slug);
        const restoreComparisonResponsePromise = page.waitForResponse(isComparisonResponse, {timeout: 10_000});
        await activateByKeyboard(page.getByTestId('asset-detail-refresh-btn'));
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
    test('sync single pair reports its outcome in the modal', async ({page}) => {
        // A real provider round-trip for every pair on the page; the default 30s
        // budget is spent before the sync answers.
        test.setTimeout(120_000);
        await goToFxDetailPage(page, 'EUR-USD');
        // The button opens the sync modal — it does not sync. And the modal it
        // opens is the *page* one (assets + FX for this page), not `fx-sync-modal`,
        // which belongs to the FX list. The test has to go all the way: open,
        // start, and read the verdict. Reading a locator without asserting on it,
        // as this did before, is a green that proves nothing.
        await page.getByTestId('fx-detail-sync-btn').click();
        const syncModal = page.getByTestId('page-sync-modal');
        await expect(syncModal).toBeVisible({timeout: 10_000});

        await syncModal.getByTestId('sync-modal-start').click();
        // No toast here, by design: the modal reports in place, so the summary
        // banner *is* the notification. Success or failure, it always appears.
        await expect(syncModal.getByTestId('sync-modal-results')).toBeVisible({timeout: 60_000});
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
