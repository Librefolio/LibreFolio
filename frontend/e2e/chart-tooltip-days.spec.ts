import {expect, test, type Locator, type Page} from './fixtures/playwright';
import {login} from './fixtures/auth-helpers';
import {TEST_USER} from './fixtures/test-users';
import {drawnDays, expectEdgesReachable, expectTooltipOnDay, msToDay, readTimeAxis, waitForTimeAxis} from './fixtures/timeAxisTooltip';
import {goToAssetsPage} from './assets/assets-helpers';
import {navigateTo} from './fixtures/auth-helpers';
import {goToFxDetailPage} from './fx/fx-helpers';
import {waitForSettled} from './fixtures/app-events';
import {installLocalUiPreferences} from './fixtures/local-ui-preferences';

/**
 * Which day does a chart open on? (Y2-I63, GitHub issue #63.)
 *
 * The Dashboard's growth chart once opened a tooltip with another day's data than the day under the cursor, and the newest days could not be
 * opened at all. These specs hold every chart with a time axis to the same two promises (`fixtures/timeAxisTooltip.ts`): a day the backend
 * served opens on that day, at two widths and on steps; the newest and the oldest day shown open from the edge of the plot and from a little
 * outside it. Nothing here reads a translated word: the pointer goes where the chart publishes its axis, and the tooltip header publishes the days it
 * stands for.
 */

test.setTimeout(120_000);

const WIDTHS = [1280, 600] as const;

/** The report calls this page issues, response included: what the backend served is what the chart is held to. */
async function recordReports(page: Page): Promise<Array<Record<string, any>>> {
    const served: Array<Record<string, any>> = [];
    await page.route(/\/api\/v1\/portfolio\/report(\?.*)?$/, async (route) => {
        const response = await route.fetch();
        const json = await response.json().catch(() => null);
        if (json) served.push(json);
        await route.fulfill({response});
    });
    return served;
}

/**
 * Choose the line shape for every chart, the way the user does: Settings → Preferences. The shape is a server-side preference
 * of the user, and TEST_USER is shared by every parallel worker: the choice is kept inside this page's browser context (the
 * settings reads carry it, the PUT never reaches the server and is answered with the merged preferences, which the store takes).
 */
async function chooseLineShape(page: Page, shape: 'segments' | 'steps' | 'spline'): Promise<void> {
    await installLocalUiPreferences(page.context());
    await page.goto('/settings');
    await page.getByTestId('settings-tab-preferences').click();
    await expect(page.getByTestId('preference-line-shape')).toBeVisible({timeout: 15_000});
    await page.getByTestId(`preference-line-shape-picker-${shape}`).click();
    await expect(page.getByTestId('preference-line-shape-picker')).toHaveAttribute('data-value', shape);
    // The pick is a draft until the row's Save (UIP-2). The context starts with no own shape (null), so any pick, 'segments'
    // included, differs from it and the row always offers Save.
    const save = page.getByTestId('preference-line-shape').getByTestId('setting-save');
    await save.click();
    await expect(save).toBeHidden();
}

/**
 * Change the viewport and wait until the chart has drawn its axis at the new width: the axis it reports is the same on two reads a few frames
 * apart (frames, not milliseconds: the chart redraws on the frame its container changed).
 */
async function resizeTo(page: Page, host: Locator, width: number): Promise<void> {
    await page.setViewportSize({width, height: 900});
    let previous = '';
    await expect
        .poll(
            async () => {
                await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))));
                const now = JSON.stringify(await readTimeAxis(host));
                const settled = now === previous;
                previous = now;
                return settled;
            },
            {timeout: 15_000},
        )
        .toBe(true);
}

type Shape = 'steps' | 'segments';
const SHAPES: readonly Shape[] = ['steps', 'segments'];

/** What a chart is held to: a day the backend served, its newest and its oldest. */
interface Served {
    newest: string;
    oldest: string;
    known: string;
    /** The days the chart draws, when its axis has one slot per day. */
    days?: readonly string[];
}

/** The steps of the first array in `json` made of `{date, through}` objects: the series the backend served for the chart. */
function servedSteps(json: unknown): Array<{date: string; through: string}> {
    if (Array.isArray(json)) {
        if (json.length > 0 && json.every((entry) => entry && typeof entry.date === 'string' && typeof entry.through === 'string')) return json;
        for (const entry of json) {
            const found = servedSteps(entry);
            if (found.length > 0) return found;
        }
    } else if (json && typeof json === 'object') {
        for (const value of Object.values(json)) {
            const found = servedSteps(value);
            if (found.length > 0) return found;
        }
    }
    return [];
}

function servedOf(steps: Array<{date: string; through: string}>): Served {
    expect(steps.length, 'the backend served a series with at least two steps').toBeGreaterThan(1);
    return {newest: steps.at(-1)!.through, oldest: steps[0].date, known: steps[Math.floor(steps.length / 2)].date};
}

/** The chart is held to its promises at two widths. `exact`: the tooltip stands for the pointed day alone (steps at the daily resolution). */
async function holdChart(page: Page, host: Locator, served: Served, exact: boolean, readsThePointedDay = true): Promise<void> {
    // a day in the middle of what the chart draws: at a coarser resolution the days the backend served are not all drawn
    const drawn = await drawnDays(host);
    if (drawn.length > 1) served = {...served, known: drawn[Math.floor(drawn.length / 2)]};
    for (const width of WIDTHS) {
        await resizeTo(page, host, width);
        // a chart that reads the nearest drawn point (not the pointed day) answers a day nothing was drawn on with the point beside it
        if (readsThePointedDay) await expectTooltipOnDay(page, host, served.known, {exact, days: served.days});
        await expectEdgesReachable(page, host, {newest: served.newest, oldest: served.oldest, days: served.days});
    }
}

/** The aggregation the chart shows, from its badge; 'daily' when it shows none (a chart with no badge is not grouped). */
async function resolutionOf(card: Locator): Promise<string> {
    const badge = card.getByTestId('chart-resolution-badge').first();
    return (await badge.count()) === 0 ? 'daily' : ((await badge.getAttribute('data-resolution')) ?? 'daily');
}

async function openDashboardOverview(page: Page): Promise<void> {
    await page.goto('/dashboard');
    await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
    await expect(page.getByTestId('dashboard-page')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
}

test.describe('The Dashboard growth chart opens on the day under the pointer (issue #63)', () => {
    for (const shape of SHAPES) {
        test(`${shape}: a served day, the newest and the oldest, at two widths`, async ({page}) => {
            await login(page, TEST_USER);
            await chooseLineShape(page, shape);
            const reports = await recordReports(page);

            await openDashboardOverview(page);
            const card = page.getByTestId('growth-chart');
            const host = card.locator('[data-chart-ready]');
            await expect(host).toHaveAttribute('data-chart-ready', 'true', {timeout: 15_000});
            await waitForTimeAxis(host);

            const served = servedOf(reports.at(-1)?.history ?? []);
            await holdChart(page, host, served, shape === 'steps' && (await resolutionOf(card)) === 'daily');
            // the axis the chart drew ends on the newest served day
            const axis = await waitForTimeAxis(host);
            expect(axis.kind === 'time' ? await msToDay(page, axis.toMs) : null).toBe(served.newest);
        });
    }
});

test.describe('The Dashboard allocation history opens on the day under the pointer (issue #63)', () => {
    for (const shape of SHAPES) {
        test(`${shape}: a served day, the newest and the oldest, at two widths`, async ({page}) => {
            await login(page, TEST_USER);
            await chooseLineShape(page, shape);
            const reports = await recordReports(page);

            await openDashboardOverview(page);
            await page.getByTestId('allocation-view-history').click();
            const host = page.getByTestId('allocation-history-chart');
            await expect(host).toHaveAttribute('data-chart-ready', 'true', {timeout: 20_000});
            await waitForTimeAxis(host);

            const served = servedOf(servedSteps(reports.filter((report) => report.allocation_history).at(-1)?.allocation_history));
            await holdChart(page, host, served, shape === 'steps' && (await resolutionOf(page.getByTestId('allocation-panel'))) === 'daily');
        });
    }
});

test.describe('The Dashboard positions chart opens on the day under the pointer (issue #63)', () => {
    for (const shape of SHAPES) {
        test(`${shape}: the portfolio line, a served day, the newest and the oldest, at two widths`, async ({page}) => {
            await login(page, TEST_USER);
            await chooseLineShape(page, shape);
            const reports = await recordReports(page);

            await page.goto('/dashboard?tab=posizioni');
            await expect(page.getByTestId('positions-panel')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
            await page.getByTestId('positions-toggle-holdings').click();
            await page.getByTestId('positions-toggle-table').click();
            const card = page.getByTestId('positions-return-chart');
            await expect(card).toBeVisible({timeout: 15_000});
            const host = page.getByTestId('positions-chart-canvas');
            await expect(host).toHaveAttribute('data-chart-ready', 'true', {timeout: 20_000});
            await waitForTimeAxis(host);

            // nothing ticked: the chart draws the portfolio's own line, the history the report served
            const served = servedOf(reports.filter((report) => report.history).at(-1)?.history ?? []);
            await holdChart(page, host, served, shape === 'steps');
        });
    }
});

/** What the chart drew: its newest and oldest day, and one in the middle. The price charts are not step series: the pointer reaches the points. */
async function drawnOf(host: Locator): Promise<Served> {
    const days = await drawnDays(host);
    expect(days.length, 'the chart draws a line of at least two days').toBeGreaterThan(1);
    return {newest: days.at(-1)!, oldest: days[0], known: days[Math.floor(days.length / 2)], days};
}

test.describe('The asset price chart opens on the day under the pointer (issue #63)', () => {
    for (const shape of SHAPES) {
        test(`${shape}: a drawn day, the newest and the oldest, at two widths`, async ({page}) => {
            await login(page, TEST_USER);
            await chooseLineShape(page, shape);
            await goToAssetsPage(page);
            const card = page.locator('[data-testid^="asset-card-"]').filter({hasText: /Apple/i}).first();
            await expect(card, 'the seeded Apple asset must be on the list').toBeVisible({timeout: 10_000});
            await card.click();
            await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 30_000});
            await waitForSettled(page.getByTestId('asset-detail-page'), 20_000);
            const host = page.getByTestId('asset-detail-chart').locator('[data-chart-ready]');
            await expect(host).toHaveAttribute('data-chart-ready', 'true', {timeout: 20_000});
            await waitForTimeAxis(host);
            await holdChart(page, host, await drawnOf(host), false);
        });
    }
});

test.describe('The FX price chart opens on the day under the pointer (issue #63)', () => {
    for (const shape of SHAPES) {
        test(`${shape}: a drawn day, the newest and the oldest, at two widths`, async ({page}) => {
            await login(page, TEST_USER);
            await chooseLineShape(page, shape);
            await goToFxDetailPage(page, 'EUR-USD');
            const host = page.getByTestId('fx-detail-chart').locator('[data-chart-ready]');
            await expect(host).toHaveAttribute('data-chart-ready', 'true', {timeout: 20_000});
            await waitForTimeAxis(host);
            await holdChart(page, host, await drawnOf(host), false);
        });
    }
});

/** The broker the mock gives positions to, and so lots. */
const BROKER_WITH_LOTS = 'Interactive Brokers';

test.describe('The lot charts open on the day under the pointer (issue #63)', () => {
    for (const shape of SHAPES) {
        test(`${shape}: the WAC chart and the comparison chart, a drawn day, the newest and the oldest, at two widths`, async ({page}) => {
            await login(page, TEST_USER);
            await chooseLineShape(page, shape);
            await navigateTo(page, '/brokers');
            const brokerCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: BROKER_WITH_LOTS}).first();
            await expect(brokerCard, `${BROKER_WITH_LOTS} is the broker the mock gives positions to: check populate_mock_data.py`).toBeVisible({timeout: 15_000});
            await brokerCard.click();
            await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 15_000});
            await page.getByTestId('broker-tab-posizioni').click();
            const row = page.locator('[data-testid="broker-holdings"] tbody tr[data-row-id]').first();
            await expect(row, `${BROKER_WITH_LOTS} must have a position: check populate_mock_data.py`).toBeVisible({timeout: 15_000});
            await row.getByTestId(/^row-actions-/).click();
            await page.getByTestId('context-menu-action-analyze-lots').click();
            await expect(page.getByTestId('lots-analysis-panel')).toBeVisible({timeout: 15_000});

            for (const [name, hostId] of [
                ['the WAC chart', 'lot-wac-price-chart'],
                ['the comparison chart', 'lot-comparison-chart'],
            ] as const) {
                const host = page.getByTestId(hostId).locator('[data-chart-ready]');
                await expect(host, name).toHaveAttribute('data-chart-ready', 'true', {timeout: 30_000});
                await waitForTimeAxis(host);
                await host.scrollIntoViewIfNeeded();
                await holdChart(page, host, await drawnOf(host), false);
            }
        });
    }
});
