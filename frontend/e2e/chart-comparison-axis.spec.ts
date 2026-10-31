import {expect, test, type Locator, type Page} from './fixtures/playwright';
import {login} from './fixtures/auth-helpers';
import {TEST_USER} from './fixtures/test-users';
import {waitForSettled} from './fixtures/app-events';
import {assetComparison, assetIdByName, seedChartComparisons} from './fixtures/chartComparisons';
import {drawnDays, pixelOfDay, readTimeAxis, spanHolds, tooltipAt, waitForTimeAxis} from './fixtures/timeAxisTooltip';
import {goToFxDetailPage} from './fx/fx-helpers';
import {goToAssetsPage} from './assets/assets-helpers';

/**
 * A comparison older (or younger) than the page's own series: the chart starts on the older of the two (Y2-CMP).
 *
 * The developer's rule (30/10): with «All», the chart of an asset or of an FX pair starts on the oldest day of the two series, the page's own
 * line is empty until its own first day (no invented line, no zero), and the percentage view measures each line from its own first price. The
 * other way round (the page's series is the older) nothing changes, and a comparison that starts years later must not break the chart.
 *
 * The seeded prices are recent, so the older comparison is made by the spec: the answer of the price query is the real one with thirty days of
 * the year 2001 put in front of the comparison asset's prices (a mock authored in the spec). The younger one cuts the comparison asset's
 * prices to its last five days. Both are asserted on what the chart drew (`__lfChart`, see `fixtures/timeAxisTooltip.ts`) and on the tooltip's
 * published days: no translated word is read.
 */

test.setTimeout(120_000);

/** The comparison asset, by its name in the seeded data. */
const PEER_NAME = 'S&P 500';

const PRICE_QUERY = /\/api\/v1\/assets\/prices\/query(\?.*)?$/;

/** The thirty weekdays the older comparison gets before its own first price. */
const OLD_DAYS: string[] = (() => {
    const days: string[] = [];
    const cursor = new Date(Date.UTC(2001, 2, 5));
    while (days.length < 30) {
        if (cursor.getUTCDay() !== 0 && cursor.getUTCDay() !== 6) days.push(cursor.toISOString().slice(0, 10));
        cursor.setUTCDate(cursor.getUTCDate() + 1);
    }
    return days;
})();

type Way = 'older' | 'younger';

interface PriceItem {
    asset_id?: number;
    prices?: Array<Record<string, unknown>>;
}

/** What the page asked the comparison asset for, and what it got. */
interface PeerTraffic {
    starts: string[];
}

/** Make the comparison asset's prices older (30 days of 2001 in front) or younger (its last five days only), and record how it was asked. */
async function shapePeerPrices(page: Page, peerId: number, way: Way): Promise<PeerTraffic> {
    const traffic: PeerTraffic = {starts: []};
    await page.route(PRICE_QUERY, async (route) => {
        const body = route.request().postDataJSON() as Array<{asset_id?: number; date_range?: {start?: string}}> | null;
        for (const item of Array.isArray(body) ? body : []) {
            if (item.asset_id === peerId && typeof item.date_range?.start === 'string') traffic.starts.push(item.date_range.start);
        }
        const response = await route.fetch();
        const json = (await response.json().catch(() => null)) as {items?: PriceItem[]} | null;
        const peer = json?.items?.find((item) => item.asset_id === peerId);
        if (peer?.prices?.length) {
            if (way === 'older') {
                const template = peer.prices[0];
                const first = Number(template.close ?? 100);
                peer.prices = [...OLD_DAYS.map((date, index) => ({...template, date, close: String(first * (0.5 + index / 100)), original_close: null, backward_fill_info: null})), ...peer.prices];
            } else {
                peer.prices = peer.prices.slice(-5);
            }
        }
        await route.fulfill({response, json});
    });
    return traffic;
}

/** The chart of the page, drawn: its host, and the days it laid its axis on. */
async function drawnChart(page: Page, cardTestId: string): Promise<{host: Locator; days: string[]}> {
    const host = page.getByTestId(cardTestId).locator('[data-chart-ready]');
    await expect(host).toHaveAttribute('data-chart-ready', 'true', {timeout: 30_000});
    await waitForTimeAxis(host);
    return {host, days: await drawnDays(host)};
}

/**
 * The values the chart drew for the page's own series and for the comparison named `peerName`, one per day of the axis (a gap is null). The page's own
 * line may be drawn as several series (the red and green segments of the baseline colouring): they are merged day by day; a signal's helper series
 * (`__…`) and the unconverted ghost (`💱 …`) are not lines of either.
 */
async function lineValues(host: Locator, peerName: string): Promise<{own: Array<number | null>; peer: Array<number | null>}> {
    return host.evaluate((node, peer) => {
        type Series = {type?: string; name?: string; data?: unknown[]};
        const chart = (node as unknown as {__lfChart: {getOption: () => {series: Series[]}}}).__lfChart;
        const lines = chart.getOption().series.filter((series) => series.type === 'line' && !(series.name ?? '').startsWith('__') && !(series.name ?? '').startsWith('💱'));
        const numbers = (series: Series) => (series.data ?? []).map((datum) => (typeof datum === 'number' ? datum : null));
        const peerLine = lines.find((series) => series.name === peer);
        const owns = lines.filter((series) => series !== peerLine).map(numbers);
        const length = Math.max(0, ...owns.map((values) => values.length));
        const own = Array.from({length}, (_, index) => owns.map((values) => values[index] ?? null).find((value) => value !== null) ?? null);
        return {own, peer: peerLine ? numbers(peerLine) : []};
    }, peerName);
}

/** The first and last index of the values that are drawn (not null). */
function drawnSpan(values: Array<number | null>): {first: number; last: number} {
    const first = values.findIndex((value) => value !== null);
    const last = values.length - 1 - [...values].reverse().findIndex((value) => value !== null);
    return {first, last};
}

/** The text of the tooltip on screen: every row, the rows' names in the data's own words. */
async function tooltipText(page: Page): Promise<string> {
    return page.evaluate(() => {
        for (const header of Array.from(document.querySelectorAll<HTMLElement>('[data-tooltip-from]'))) {
            let node: HTMLElement | null = header;
            let shown = true;
            while (node && node !== document.body) {
                const style = getComputedStyle(node);
                if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) shown = false;
                node = node.parentElement;
            }
            if (shown) return header.parentElement?.textContent ?? '';
        }
        return '';
    });
}

async function chooseAll(page: Page): Promise<void> {
    await page.getByTestId('date-range-picker-root').getByTestId('date-preset-max').click();
}

async function openAssetDetail(page: Page, assetId: number): Promise<void> {
    await page.goto(`/assets/${assetId}`);
    await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 30_000});
    await waitForSettled(page.getByTestId('asset-detail-page'), 30_000);
}

const PAGES = [
    {
        name: 'the asset detail',
        card: 'asset-detail-chart',
        open: async (page: Page, mainId: number) => openAssetDetail(page, mainId),
        slug: (mainId: number) => `asset-${mainId}`,
        ownName: 'Apple Inc.',
    },
    {
        name: 'the FX detail',
        card: 'fx-detail-chart',
        open: async (page: Page) => goToFxDetailPage(page, 'EUR-USD'),
        slug: () => 'EUR-USD',
        ownName: null,
    },
] as const;

for (const detail of PAGES) {
    test.describe(`${detail.name}: the chart starts on the older of the two series (Y2-CMP)`, () => {
        for (const way of ['older', 'younger'] as const) {
            test(`a comparison ${way} than the page's series: «All», the percentage view`, async ({page}) => {
                await login(page, TEST_USER);
                await goToAssetsPage(page);
                const mainId = await assetIdByName(page, 'Apple Inc.');
                const peerId = await assetIdByName(page, PEER_NAME);
                await seedChartComparisons(page, [[detail.slug(mainId), [assetComparison('cmp', peerId)]]]);
                const traffic = await shapePeerPrices(page, peerId, way);

                await detail.open(page, mainId);
                await chooseAll(page);

                // «All» asks the comparison from its own first price, not from the day this series starts. The page asks the comparison once
                // for the period it opened on and again for «All»: it is the second ask that is waited for, not the first.
                await expect.poll(() => traffic.starts, {message: 'the comparison was never asked from `min`', timeout: 30_000}).toContain('min');
                const {host} = await drawnChart(page, detail.card);
                // the answer to that ask is what the chart draws: both lines are on the chart, and, the older way, the axis starts on the older day
                await expect
                    .poll(
                        async () => {
                            const {own, peer} = await lineValues(host, PEER_NAME);
                            if (!own.some((value) => value !== null) || !peer.some((value) => value !== null)) return 'a line is not drawn yet';
                            const first = (await drawnDays(host))[0];
                            return way === 'older' && first !== OLD_DAYS[0] ? `the axis starts on ${first}` : 'drawn';
                        },
                        {timeout: 30_000},
                    )
                    .toBe('drawn');
                const days = await drawnDays(host);

                const {own, peer} = await lineValues(host, PEER_NAME);
                const ownSpan = drawnSpan(own);
                const peerSpan = drawnSpan(peer);
                if (way === 'older') {
                    expect(days[0], 'the chart starts on the comparison\'s first day').toBe(OLD_DAYS[0]);
                    expect(ownSpan.first, 'the page\'s own line is empty before its own first day').toBeGreaterThanOrEqual(OLD_DAYS.length);
                    expect(ownSpan.last).toBe(days.length - 1);
                    // in the percentage view each line is 0 on its own first day: the page's own on the day it starts, the comparison on 2001's
                    expect(own[ownSpan.first]).toBe(0);
                    expect(peer[peerSpan.first]).toBe(0);
                    expect(peerSpan.first).toBe(0);
                    // the date picker's From is the older of the two (its field shows the ISO day while focused)
                    const from = page.getByTestId('date-range-input-start');
                    await from.focus();
                    await expect(from).toHaveValue(OLD_DAYS[0]);
                    await from.blur();
                    // the tooltip on the oldest day lists the comparison, and not the page's own series
                    const axis = await readTimeAxis(host);
                    const x = await pixelOfDay(page, axis, OLD_DAYS[0], days);
                    const span = await tooltipAt(page, host, Math.ceil(x));
                    expect(spanHolds(span, OLD_DAYS[0]), 'the tooltip opens on the oldest day').toBe(true);
                    const text = await tooltipText(page);
                    expect(text).toContain(PEER_NAME);
                    if (detail.ownName) expect(text).not.toContain(detail.ownName);
                } else {
                    expect(ownSpan.first, 'the chart keeps the page\'s own first day: nothing is added before it').toBe(0);
                    expect(peerSpan.first, 'the comparison starts after the page\'s series and the chart is not broken').toBeGreaterThan(0);
                    expect(peer[peerSpan.first]).toBe(0);
                    expect(peerSpan.last).toBe(days.length - 1);
                    expect(days[0] > OLD_DAYS[OLD_DAYS.length - 1], 'the axis was not extended into the past').toBe(true);
                }
            });
        }
    });
}
