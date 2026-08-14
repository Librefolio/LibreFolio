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
    const busy = scope.locator('[data-busy]').first();
    await busy.waitFor({state: 'attached', timeout});
    await expect(busy).toHaveAttribute('data-busy', 'false', {timeout});
}
