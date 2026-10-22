/**
 * The line of a compared FX pair on a detail page's chart (lot Y-41).
 *
 * A list card publishes how many overlay lines it draws (`data-overlay-count`); a detail page's chart publishes none,
 * so the spec reads what the chart handed ECharts: the chart root holds the instance as `__lfChart`, and the line of an
 * `fx-pair` signal is the series named after its pair (`🇪🇺 EUR → 🇬🇧 GBP`: the two currency codes, never a translated word).
 * «Drawn» is a series of that pair with at least one value, aligned on the category axis of the chart's dates.
 */

import {expect, type Page} from '@playwright/test';

/** What the chart draws of one pair: how many values the line holds and the first and last date it has one on. */
export interface PairLine {
    points: number;
    firstDate: string | null;
    lastDate: string | null;
}

/** The line the chart `chartTestId` draws for `pairSlug` (`EUR-GBP`), the longest if several series carry its name; none reads as 0 points. */
export async function readPairLine(page: Page, chartTestId: string, pairSlug: string): Promise<PairLine> {
    return page.evaluate(
        ({testId, slug}): {points: number; firstDate: string | null; lastDate: string | null} => {
            type Option = {series?: unknown; xAxis?: unknown};
            type ChartHost = HTMLElement & {__lfChart?: {getOption: () => Option}};
            const none: {points: number; firstDate: string | null; lastDate: string | null} = {points: 0, firstDate: null, lastDate: null};
            const root = document.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
            if (!root) return none;
            const candidates = [root, ...root.querySelectorAll<HTMLElement>('*')];
            const host = candidates.find((candidate) => typeof (candidate as ChartHost).__lfChart?.getOption === 'function') as ChartHost | undefined;
            const option = host?.__lfChart?.getOption();
            if (!option || !Array.isArray(option.series)) return none;
            const axis = Array.isArray(option.xAxis) ? (option.xAxis[0] as {data?: unknown} | undefined) : undefined;
            const dates: unknown[] = Array.isArray(axis?.data) ? axis.data : [];
            const [base, quote] = slug.split('-');
            const valueOf = (datum: unknown): unknown => (Array.isArray(datum) ? datum[1] : datum !== null && typeof datum === 'object' ? (datum as {value?: unknown}).value : datum);

            let best = none;
            for (const raw of option.series) {
                const series = raw as {name?: unknown; data?: unknown};
                const name = typeof series.name === 'string' ? series.name : '';
                if (!name.includes(base) || !name.includes(quote) || !Array.isArray(series.data)) continue;
                const filled: number[] = [];
                series.data.forEach((datum, index) => {
                    const value = valueOf(datum);
                    if (typeof value === 'number' && Number.isFinite(value)) filled.push(index);
                });
                if (filled.length > best.points) {
                    const first = dates[filled[0]];
                    const last = dates[filled[filled.length - 1]];
                    best = {points: filled.length, firstDate: typeof first === 'string' ? first : null, lastDate: typeof last === 'string' ? last : null};
                }
            }
            return best;
        },
        {testId: chartTestId, slug: pairSlug},
    );
}

/** The pair's line is on the chart, whenever the page gets its rates in. */
export async function expectPairLineDrawn(page: Page, chartTestId: string, pairSlug: string, why: string, timeout = 15_000): Promise<void> {
    await expect.poll(async () => (await readPairLine(page, chartTestId, pairSlug)).points, {message: why, timeout}).toBeGreaterThan(0);
}

/**
 * The pair's line reaches back to `firstDateAtMost` (an ISO date): the rates of the whole period are in, not only the ones
 * the page held before the period grew. The bound leaves room for the resolution the chart chooses (a weekly or monthly
 * point is dated within its bucket) and for the weekend a period may start on.
 */
export async function expectPairLineReaches(page: Page, chartTestId: string, pairSlug: string, firstDateAtMost: string, why: string, timeout = 15_000): Promise<void> {
    await expect
        .poll(
            async () => {
                const line = await readPairLine(page, chartTestId, pairSlug);
                return line.points > 0 && line.firstDate !== null && line.firstDate.slice(0, 10) <= firstDateAtMost;
            },
            {message: why, timeout},
        )
        .toBe(true);
}
