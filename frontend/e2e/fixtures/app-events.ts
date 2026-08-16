/**
 * Waiting on what the app did, instead of on the clock.
 *
 * Two things a test may need to know after acting:
 *
 *   1. "is it finished?"  -> waitForSettled(), which reads `data-busy`
 *   2. "what happened?"   -> waitForEvent(), which reads the event ring
 *
 * Neither is an edge, so neither can be missed. `page.on('console')` and
 * `page.waitForEvent('console')` are edges: they must be armed before the
 * action, and a test that forgets is flaky in exactly the way a sleep is.
 *
 * The product side lives in `$lib/stores/app/notify.svelte.ts`.
 */

import {expect, type Locator, type Page} from '@playwright/test';

export interface AppEvent {
    seq: number;
    name: string;
    detail?: Record<string, unknown>;
    at: number;
}

/**
 * Read the event counter *before* acting, then pass it as `since`. Without it,
 * a test that acts twice on one page would match its own earlier event.
 */
export async function eventSeq(page: Page): Promise<number> {
    return page.evaluate(() => (window as unknown as {__lf?: {seq?: () => number}}).__lf?.seq?.() ?? 0);
}

/**
 * Resolve with the first event named `name` recorded after `since`.
 *
 * Retained, so this is safe to call *after* the action that produced it:
 *
 *   const since = await eventSeq(page);
 *   await saveButton.click();
 *   const ev = await waitForEvent(page, 'asset.saved', {since});
 *   expect(ev.detail.id).toBe(assetId);
 */
export async function waitForEvent(page: Page, name: string, opts: {since?: number; timeout?: number} = {}): Promise<AppEvent> {
    const {since = 0, timeout = 10_000} = opts;
    const handle = await page.waitForFunction(
        ({n, s}: {n: string; s: number}) => {
            const events = (window as unknown as {__lf?: {events?: AppEvent[]}}).__lf?.events;
            return events?.find((e) => e.name === n && e.seq > s) ?? null;
        },
        {n: name, s: since},
        {timeout},
    );
    return handle.jsonValue() as Promise<AppEvent>;
}

/**
 * Wait until a container says it has stopped reloading.
 *
 * `scope` is the page or any container publishing `data-busy`. Pages that load
 * in waves (rows first, prices second) only go `false` when every wave is in —
 * which is the whole point: "the rows are painted" and "the page is finished"
 * are different moments, and a test usually means the second.
 *
 * The attribute is re-read on the *same* element rather than waiting for any
 * `[data-busy="false"]` to appear: on a page with nested busy containers the
 * latter would match a neighbour that was never busy to begin with.
 */
export async function waitForSettled(scope: Page | Locator, timeout = 15_000): Promise<void> {
    // `:scope` first, so passing the busy container *itself* works as naturally
    // as passing an ancestor. Without it `locator()` only searches descendants,
    // and handing this function the very element that carries the flag would
    // silently wait out the full timeout — the exact failure mode it exists to
    // remove. In DOM order the scope element precedes its descendants, so
    // `.first()` still prefers it when both match.
    const busy = scope.locator('css=:scope[data-busy], [data-busy]').first();
    await busy.waitFor({state: 'attached', timeout});
    await expect(busy).toHaveAttribute('data-busy', 'false', {timeout});
}

/**
 * Wait until an ECharts container has finished drawing.
 *
 * `attachChartReady` (src/lib/utils/chartReady.ts) flips `data-chart-ready` on
 * the container once ECharts fires `finished` — i.e. after the render *and* its
 * animations. Waiting for the attribute replaces the `waitForTimeout(400)`-style
 * guesses that were really "long enough for the animation, probably".
 *
 * `scope` may be the container itself or any ancestor: the first descendant
 * carrying the attribute is used, which is how the panel-level test ids in the
 * suite already address their charts.
 */
export async function waitForChart(scope: Page | Locator, timeout = 15_000): Promise<void> {
    const chart = scope.locator('[data-chart-ready]').first();
    // Two stages on purpose. "Is there a chart here at all?" is answered in a
    // second — pages legitimately without one must not pay the full budget —
    // while "has it finished drawing?" gets the real timeout.
    await chart.waitFor({state: 'attached', timeout: Math.min(2_000, timeout)});
    await expect(chart).toHaveAttribute('data-chart-ready', 'true', {timeout});
}

/**
 * Wait for a chart to draw *again*.
 *
 * `data-chart-ready` stays `true` once set, so a test that changes the range and
 * then waits for it would be satisfied by the previous drawing. `renders`
 * increments on every completed pass, so the caller can read it before acting
 * and wait for it to move afterwards.
 */
export async function chartRenders(scope: Page | Locator): Promise<number> {
    const chart = scope.locator('[data-chart-ready]').first();
    const raw = await chart.getAttribute('data-chart-renders');
    return Number(raw ?? '0');
}

export async function waitForChartRerender(scope: Page | Locator, since: number, timeout = 15_000): Promise<void> {
    const chart = scope.locator('[data-chart-ready]').first();
    await expect(async () => {
        const raw = await chart.getAttribute('data-chart-renders');
        expect(Number(raw ?? '0')).toBeGreaterThan(since);
    }).toPass({timeout});
}

/**
 * Count the validate runs a transaction modal has completed.
 *
 * The FormModal and the BulkModal validate server-side behind a debounce, so
 * "has the verdict been recomputed?" cannot be answered by a busy flag alone:
 * a reader arriving between the edit and the debounce firing sees `false` and
 * concludes, wrongly, that the numbers on screen are current. The counter is
 * read before acting and awaited afterwards, which no timing can defeat.
 *
 * `scope` is the modal root (`tx-form-modal-root` or `tx-bulk-modal-root`).
 */
export async function validateRuns(scope: Locator): Promise<number> {
    const raw = await scope.getAttribute('data-validate-runs');
    return Number(raw ?? '0');
}

export async function waitForValidateRun(scope: Locator, since: number, timeout = 20_000): Promise<void> {
    await expect(async () => {
        const raw = await scope.getAttribute('data-validate-runs');
        expect(Number(raw ?? '0')).toBeGreaterThan(since);
    }).toPass({timeout});
    await waitForSettled(scope, timeout);
}

/**
 * Wait for the import wizard's parse to reach a verdict, and insist it is usable.
 *
 * Waiting on the Continue button alone cannot tell "still parsing" from "every file
 * failed": both leave it disabled. A failure therefore spent the whole budget and then
 * reported nothing beyond "a button was disabled", which is the least useful thing that
 * could be said about it.
 *
 * The wizard already renders *why* a parse failed — this reads it, so the failure names
 * its own cause. `data-parse-state` on the step-3 container carries the verdict:
 * `idle` | `parsing` | `ok` | `partial` | `error`.
 */
export async function waitForParseVerdict(page: Page, timeout = 30_000): Promise<void> {
    const step3 = page.getByTestId('import-wizard-step3');
    await expect(step3).toHaveAttribute('data-parse-state', /^(ok|partial|error)$/, {timeout});

    if ((await step3.getAttribute('data-parse-state')) === 'error') {
        const reason = await page
            .getByTestId('import-wizard-parse-errors')
            .innerText()
            .catch(() => '(the wizard rendered no detail)');
        throw new Error(`Parse produced no usable file. The wizard reports:\n${reason}`);
    }

    await expect(page.getByTestId('import-wizard-continue')).toBeEnabled({timeout: 5_000});
}
