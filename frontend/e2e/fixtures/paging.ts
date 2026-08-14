/**
 * Paging helpers — find a row by walking the pages instead of assuming page 1.
 *
 * Every table in the app paginates client-side over the *whole* dataset. A test
 * that reads `locator(...).count()` right after opening a table is asking "is it
 * on the first page?", not "does it exist?" — and the answer changes whenever a
 * neighbouring test adds a row. These helpers ask the question the test means.
 */
import {expect, type Locator, type Page} from '@playwright/test';

/**
 * Walk a paginated container from its current page until `probe` reports a hit.
 *
 * Returns the page index where it was found, or `null` if every page was
 * visited without a hit. The caller decides whether absence is a failure — most
 * of the time it is, and should be asserted with a message naming the fixture.
 */
export async function findAcrossPages(container: Locator, probe: () => Promise<boolean>, opts: {maxPages?: number} = {}): Promise<number | null> {
    const maxPages = opts.maxPages ?? 25;
    const next = container.getByTestId('pagination-next');

    for (let pageIndex = 1; pageIndex <= maxPages; pageIndex++) {
        if (await probe()) return pageIndex;
        // No pagination bar at all → single page, nothing more to visit.
        if ((await next.count()) === 0) return null;
        if (!(await next.isEnabled().catch(() => false))) return null;

        const firstRowId = await container.locator('tbody tr[data-row-id]').first().getAttribute('data-row-id');
        await next.click();
        // The click is not the page turn: wait for the content to actually change.
        await expect.poll(async () => container.locator('tbody tr[data-row-id]').first().getAttribute('data-row-id'), {timeout: 5_000}).not.toBe(firstRowId);
    }
    return null;
}

/**
 * Walk the pages until at least one element matching `locator` is present,
 * and leave the table on that page. Fails with `reason` if never found.
 */
export async function pageUntilVisible(container: Locator, locator: Locator, reason: string, opts: {maxPages?: number} = {}): Promise<void> {
    const found = await findAcrossPages(container, async () => (await locator.count()) > 0, opts);
    expect(found, reason).not.toBeNull();
}

/**
 * Raise a table's page size to its largest option, so the whole dataset is on
 * one page. Cheaper than walking when the test only needs "exists anywhere".
 * No-op when the table has no pagination bar.
 */
export async function maximisePageSize(page: Page, container: Locator): Promise<void> {
    const pagination = container.getByTestId('data-table-pagination');
    if ((await pagination.count()) === 0) return;
    const btn = pagination.locator('.page-size-btn').first();
    if (!(await btn.isVisible().catch(() => false))) return;
    await btn.click();
    const options = pagination.locator('.page-size-dropdown button, .dropdown-option');
    await expect.poll(async () => options.count(), {timeout: 5_000}).toBeGreaterThan(0);
    await options.last().click();
    await expect(options.first()).toBeHidden({timeout: 5_000});
}
