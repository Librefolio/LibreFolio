import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {expect, test, type Page} from '../fixtures/playwright';
import {waitForSettled} from '../fixtures/app-events';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

/**
 * The growth chart over a very long history (Y2 FB-6): the resolution badge says what the chart did with the days.
 *
 * The dashboard is served a synthetic report whose history is one step a day for 26 years (the shape of a real history: the
 * value changes whenever a price does). On a plot a few hundred pixels wide that is far over the density a line takes, so the
 * chart groups the days into weeks or months, and the badge says so. The report is the captured `dashboard-report.json` with
 * its `history` replaced, so every other section keeps the shape the schema accepts. Nothing here reads a number or a
 * translated word: the badge's own `data-resolution` is the contract.
 *
 * Own browser context and an intercepted response, nothing shared: parallel by default.
 */

const FIXTURE = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'dashboard-report.json');

/** A served history: one step every `everyDays` days, `count` of them, from `firstDay`. */
interface Shape {
    firstDay: string;
    everyDays: number;
    count: number;
}

/** 26 years, a step a day. */
const DAILY_26_YEARS: Shape = {firstDay: '2000-01-03', everyDays: 1, count: 9_497};
/** 140 years, a step every ten days: 1 680 months, more than a line takes on any plot this page draws. */
const TEN_DAYS_140_YEARS: Shape = {firstDay: '1886-01-01', everyDays: 10, count: 5_110};

/** `firstDay` plus `days` days, as an ISO day. */
function dayAt(firstDay: string, days: number): string {
    const [year, month, day] = firstDay.split('-').map(Number);
    return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);
}

/** The captured report with a history of this shape in place of its own year. */
function longHistoryReport(shape: Shape): Record<string, unknown> {
    const report = JSON.parse(fs.readFileSync(FIXTURE, 'utf8')) as {history: Array<Record<string, unknown>>; range: {start: string; end: string}; mwrr_line: unknown[]} & Record<string, unknown>;
    const template = report.history[0];
    const amount = (value: number) => ({code: 'EUR', amount: value.toFixed(2)});
    report.history = Array.from({length: shape.count}, (_, index) => ({
        ...template,
        date: dayAt(shape.firstDay, index * shape.everyDays),
        through: dayAt(shape.firstDay, index * shape.everyDays + shape.everyDays - 1),
        market_value: amount(30_000 + index),
        broker_nav_value: amount(30_060 + index),
        nav_value: amount(30_060 + index),
        total_pnl: amount(1_500 + index),
        twrr: (index / 1e5).toFixed(6),
        roi: (index / 1e5).toFixed(6),
    }));
    report.range = {start: shape.firstDay, end: dayAt(shape.firstDay, shape.count * shape.everyDays - 1)};
    report.mwrr_line = [];
    return report;
}

async function serveLongHistory(page: Page, shape: Shape): Promise<void> {
    const body = JSON.stringify(longHistoryReport(shape));
    await page.route('**/api/v1/portfolio/report', (route) => route.fulfill({status: 200, contentType: 'application/json', body}));
}

test.describe('the growth chart on a 26-year history', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    async function openChart(page: Page, shape: Shape) {
        await serveLongHistory(page, shape);
        await page.goto('/dashboard');
        await waitForSettled(page.getByTestId('dashboard-page'), 20_000);
        const chart = page.getByTestId('growth-chart');
        await expect(chart).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('growth-toggle-pct'), 'the served report reached the chart').toBeEnabled({timeout: 10_000});
        return chart;
    }

    test('groups the days of 26 years and says so with its resolution badge', async ({page}) => {
        const chart = await openChart(page, DAILY_26_YEARS);
        const badge = chart.getByTestId('chart-resolution-badge');
        await expect(badge, 'nine and a half thousand days on a plot of a few hundred pixels are grouped: the badge says how').toBeVisible({timeout: 10_000});
        expect(['weekly', 'monthly']).toContain(await badge.getAttribute('data-resolution'));
    });

    test('groups 140 years by year, and the badge says Yearly', async ({page}) => {
        const chart = await openChart(page, TEN_DAYS_140_YEARS);
        await expect(chart.getByTestId('chart-resolution-badge')).toHaveAttribute('data-resolution', 'yearly', {timeout: 10_000});
    });
});
