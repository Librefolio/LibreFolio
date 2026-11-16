import {expect, test, type APIRequestContext, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';

/**
 * Project 74 — the «Globale / Broker» switch of Dashboard › Positions (issue #80).
 *
 * TEST_USER's seeded book (populate_mock_data.py) holds the same assets at several of its own brokers. Nothing here is
 * found by position or text: the spec asks the report which asset sits at two owned brokers, then looks for that asset's
 * rows by their keys (`dt-row-checkbox-<asset>-<broker>`, `-0` for a row summed over its brokers), and reads the
 * switch by its test ids. The figures are the backend's (its API tests prove the sums); here the page must show one row
 * per asset in «Globale», ask the series of the asset summed over its brokers, and remember the choice.
 *
 * Earned parallel: each test owns its browser context (the choice lives in its localStorage) and reads the seeded book
 * without writing it.
 */
test.describe.configure({mode: 'parallel'});

/** An asset TEST_USER holds at two of the brokers the Dashboard shows, and those brokers. */
async function sharedAsset(request: APIRequestContext): Promise<{assetId: number; brokerIds: number[]}> {
    const brokers = await request.get('/api/v1/brokers');
    expect(brokers.ok()).toBe(true);
    const owned = (((await brokers.json()) as {items?: Array<{id: number; user_role?: string | null}>}).items ?? []).filter((broker) => broker.user_role === 'OWNER').map((broker) => broker.id);
    const report = await request.post('/api/v1/portfolio/report', {data: {broker_ids: owned, include_summary: true, include_history: false, include_allocation_history: false}});
    expect(report.ok()).toBe(true);
    const holdings = ((await report.json()) as {summary: {holdings: Array<{asset_id: number; broker_id: number}>}}).summary.holdings;
    const byAsset = new Map<number, number[]>();
    for (const holding of holdings) byAsset.set(holding.asset_id, [...(byAsset.get(holding.asset_id) ?? []), holding.broker_id]);
    const found = [...byAsset.entries()].find(([, ids]) => ids.length >= 2);
    if (!found) throw new Error('TEST_USER holds no asset at two owned brokers: the seed of populate_mock_data.py must give it one');
    return {assetId: found[0], brokerIds: found[1]};
}

async function openPositions(page: Page): Promise<void> {
    await page.goto('/dashboard?tab=posizioni');
    await expect(page.getByTestId('positions-panel')).toBeVisible({timeout: 15_000});
    await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
}

/** A row of the Portfolio table (`<asset>-<broker>`, broker 0 for a row summed over its brokers). */
const row = (page: Page, assetId: number, brokerId: number | null) => page.getByTestId(`dt-row-checkbox-${assetId}-${brokerId ?? 0}`);
/** A row of the Period table (`pos-<broker>-<asset>`, `all` for a row summed over its brokers). */
const periodRow = (page: Page, assetId: number, brokerId: number | null) => page.getByTestId(`dt-row-checkbox-pos-${brokerId ?? 'all'}-${assetId}`);

test.describe('Dashboard › Positions — «Globale / Broker» (project 74)', () => {
    test.beforeEach(async ({page}) => {
        await login(page);
    });

    test('Broker by default; Globale shows one row per asset, and the choice survives a reload', async ({page}) => {
        const {assetId, brokerIds} = await sharedAsset(page.request);
        await openPositions(page);
        await expect(page.getByTestId('positions-grouping-broker')).toHaveAttribute('aria-pressed', 'true', {timeout: 5_000});
        for (const brokerId of brokerIds) await expect(row(page, assetId, brokerId)).toBeAttached({timeout: 5_000});

        await page.getByTestId('positions-grouping-asset').click();
        await expect(page.getByTestId('positions-grouping-asset')).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(row(page, assetId, null)).toBeAttached({timeout: 15_000});
        for (const brokerId of brokerIds) await expect(row(page, assetId, brokerId)).toHaveCount(0);

        // The choice is read before the first request: a reload asks the positions grouped, never per broker first
        const contributionQuestions: Array<{group_by?: string}> = [];
        page.on('request', (request) => {
            if (!request.url().includes('/api/v1/portfolio/report') || request.method() !== 'POST') return;
            const body = request.postDataJSON() as {include_positions_contribution?: boolean; group_by?: string};
            if (body.include_positions_contribution) contributionQuestions.push(body);
        });
        await page.reload();
        await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(page.getByTestId('positions-grouping-asset')).toHaveAttribute('aria-pressed', 'true', {timeout: 5_000});
        await expect(row(page, assetId, null)).toBeAttached({timeout: 15_000});
        expect(contributionQuestions.length).toBeGreaterThan(0);
        expect(
            contributionQuestions.every((body) => body.group_by === 'asset'),
            'a per-broker contribution was asked before the grouped one',
        ).toBe(true);

        await page.getByTestId('positions-grouping-broker').click();
        await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        for (const brokerId of brokerIds) await expect(row(page, assetId, brokerId)).toBeAttached({timeout: 15_000});
    });

    test('Globale asks the chart the asset summed over its brokers (broker_id null): one line, no dashed twin', async ({page}) => {
        const {assetId} = await sharedAsset(page.request);
        await openPositions(page);
        await page.getByTestId('positions-grouping-asset').click();
        await expect(row(page, assetId, null)).toBeAttached({timeout: 15_000});
        const asked = page.waitForRequest((request) => request.url().includes('/api/v1/portfolio/positions-series') && request.method() === 'POST');
        await row(page, assetId, null).click();
        const body = (await asked).postDataJSON() as {positions: Array<{asset_id: number; broker_id?: number | null}>};
        expect(body.positions).toContainEqual({asset_id: assetId, broker_id: null});
        expect(body.positions.filter((position) => position.asset_id === assetId)).toHaveLength(1);
    });

    test('the Period view in Globale has one row for the asset too', async ({page}) => {
        const {assetId, brokerIds} = await sharedAsset(page.request);
        await openPositions(page);
        await page.getByTestId('positions-grouping-asset').click();
        await page.getByTestId('positions-toggle-performance').click();
        await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(periodRow(page, assetId, null)).toBeAttached({timeout: 15_000});
        for (const brokerId of brokerIds) await expect(periodRow(page, assetId, brokerId)).toHaveCount(0);
    });

    test('a broker’s page has no switch: one broker, the two views coincide', async ({page}) => {
        const {brokerIds} = await sharedAsset(page.request);
        await page.goto(`/brokers/${brokerIds[0]}`);
        await page.getByTestId('broker-tab-posizioni').click();
        await expect(page.getByTestId('positions-panel')).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(page.getByTestId('positions-grouping-toggle')).toHaveCount(0);
    });
});
