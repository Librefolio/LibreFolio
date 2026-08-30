/**
 * FX sync against deterministic providers — E2E
 *
 * The sync flow was, before this file, the least covered feature of the app: a
 * whole path from "press sync" to "here is what changed" that no test walked,
 * because walking it meant asking a central bank for rates. A suite that calls
 * the real ECB is testing today's weather — it is slow, it fails on a Sunday,
 * and it cannot assert a number.
 *
 * So this file syncs against the two providers we own and that answer without a
 * network: `MOCKFX`, which returns a fixed rate for every date, and
 * `MOCKFX_FAIL`, which always raises. Verified before writing a line: a route
 * through MOCKFX on a currency outside its declared `supported_currencies` list
 * still syncs `ok` (11 points over a 10-day window), and one through MOCKFX_FAIL
 * comes back `failed` with no points. Both are decisions the modal has to
 * render, and neither is reachable from a real provider on demand.
 *
 * What it proves:
 *   · the modal announces what it is about to sync before it starts;
 *   · a successful sync reports counts that came from the server;
 *   · a failing provider is reported as a failure, not quietly as a success;
 *   · a mixed batch is *both*, and offers to retry only the failures;
 *   · re-syncing unchanged data is surfaced as "nothing changed" rather than as
 *     a plain success — the rule that exists because a provider answering `ok`
 *     with zero rows written is indistinguishable, to the user, from one that
 *     worked.
 *
 * On assertions: the summary banner interleaves its five tallies with a
 * translated verb, so every number here is read from the `data-*` attributes
 * `SyncModalBase` publishes for exactly that reason — never from the sentence.
 *
 * The pairs are this file's own — one disjoint set per test, on currency codes
 * no other spec claims — and `afterAll` removes both the routes and the rates
 * they wrote.
 */

import {expect, test, type Page} from '../fixtures/playwright';
import type {APIRequestContext} from '@playwright/test';
import {login} from '../fixtures/auth-helpers';
import {maximisePageSize} from '../fixtures/paging';
import {TEST_USER} from '../fixtures/test-users';
import {goToFxPage} from './fx-helpers';

const API = '/api/v1';

/**
 * Currency codes owned by this file — and one set per test.
 *
 * Every quote sorts *after* `EUR`, and that is a requirement rather than a
 * style: a pair is stored and displayed in alphabetical order, so a route
 * created as `EUR-DKK` comes back as `DKK-EUR` and a spec looking for
 * `[data-row-id="EUR-DKK"]` finds nothing. Verified from the accessibility
 * snapshot of a failing run — the row was there, reading `DKK → EUR` — and
 * against the stored routes, every one of which is already ordered that way.
 *
 * Deliberately disjoint from `fx-destructive.spec.ts` (NZD/SGD/MXN/ZAR/HKD/
 * SEK/NOK/PLN) and from the seeded pairs. The per-test split is not tidiness:
 * `fx_conversion_routes` has no `user_id`, and `POST /fx/providers/routes` is
 * not safe against two callers upserting the same row at once (see the note on
 * `route()`), so sharing a pair between tests that run in parallel produces a
 * 500 rather than an idempotent write. Each test creating only what it uses
 * removes the contention instead of tolerating it.
 */
const PAIRS = {
    announce: [
        {base: 'EUR', quote: 'TRY'},
        {base: 'EUR', quote: 'THB'},
    ],
    success: [{base: 'EUR', quote: 'PHP'}],
    failure: [{base: 'EUR', quote: 'KRW'}],
    mixedOk: [
        {base: 'EUR', quote: 'TWD'},
        {base: 'EUR', quote: 'MYR'},
    ],
    mixedFail: [
        {base: 'EUR', quote: 'INR'},
        {base: 'EUR', quote: 'HUF'},
    ],
    unchanged: [{base: 'EUR', quote: 'ILS'}],
} as const;

const ALL_PAIRS = Object.values(PAIRS).flat();

const slug = (p: {base: string; quote: string}) => `${p.base}-${p.quote}`;

/**
 * Create a route through a named provider.
 *
 * Documented as an upsert on `(base, quote, priority)`, and it is — serially.
 * Two callers writing the same row concurrently get a 500 instead: either
 * `UNIQUE constraint failed: fx_conversion_routes.base, quote, priority` when
 * both pass the existence check and both insert, or `UPDATE statement ...
 * expected to update 1 row(s); 0 were matched` when the row goes away between
 * the check and the write. Observed at four workers; reported, not worked
 * around — this file avoids it by giving every test its own pairs.
 */
async function route(req: APIRequestContext, pair: {base: string; quote: string}, provider: string): Promise<void> {
    const res = await req.post(`${API}/fx/providers/routes`, {
        data: [{base: pair.base, quote: pair.quote, priority: 1, chain_steps: [{from: pair.base, to: pair.quote, provider}]}],
    });
    expect(res.ok(), `route ${slug(pair)} via ${provider}: ${res.status()} ${await res.text()}`).toBeTruthy();
}

/** Create every pair a test needs, in the order the test will use them. */
async function seed(req: APIRequestContext, ok: readonly {base: string; quote: string}[], failing: readonly {base: string; quote: string}[] = []): Promise<void> {
    for (const p of ok) await route(req, p, 'MOCKFX');
    for (const p of failing) await route(req, p, 'MOCKFX_FAIL');
}

/** Remove a pair's route and every rate it holds. Idempotent. */
async function dropPair(req: APIRequestContext, pair: {base: string; quote: string}): Promise<void> {
    await req.delete(`${API}/fx/providers/routes`, {data: [{base: pair.base, quote: pair.quote}]}).catch(() => {});
    await req.delete(`${API}/fx/currencies/rate`, {data: {from: pair.base, to: pair.quote, delete_all: true}}).catch(() => {});
}

/**
 * Select the given pairs in the list table and open the sync modal on them.
 *
 * The bulk action is what makes this file possible at all: "Sync all" would
 * reach every route in the database, including the seeded ones that point at
 * real central banks. Selecting first keeps the network out.
 *
 * Ends on the post-condition it promises — the modal open and announcing the
 * right number of items — so a failure lands here rather than three assertions
 * later.
 */
async function openSyncFor(page: Page, pairs: readonly {base: string; quote: string}[]): Promise<void> {
    await goToFxPage(page);
    await page.getByTestId('view-mode-list').click();

    // Every row has to be on screen at once, because the batch is the selection.
    // The list paginates over the whole dataset, and how many pairs exist depends
    // on which neighbours are mid-test — so page 1 holding all four is a property
    // of the moment, not of the fixture. Measured: green alone, red at four
    // workers, with `EUR-TRY` simply on another page.
    await maximisePageSize(page, page.getByTestId('fx-page'));

    for (const p of pairs) {
        const row = page.locator(`[data-row-id="${slug(p)}"]`);
        await expect(row).toBeVisible({timeout: 10_000});
        // The row selector is a button publishing `data-state`, not an `<input>`.
        // Asking for the state rather than clicking blind: a row that arrives
        // already selected would be *de*selected by an unconditional click, and
        // the spec would then sync the wrong set without saying so.
        const box = page.getByTestId(`dt-row-checkbox-${slug(p)}`);
        if ((await box.getAttribute('data-state')) !== 'checked') await box.click();
        await expect(box).toHaveAttribute('data-state', 'checked');
    }

    const toolbar = page.getByTestId('selection-toolbar');
    await expect(toolbar).toHaveAttribute('data-selected-count', String(pairs.length));
    await toolbar.getByTestId('toolbar-action-sync').click();

    const modal = page.getByTestId('fx-sync-modal');
    await expect(modal).toBeVisible({timeout: 5_000});
    await expect(modal.getByTestId('sync-modal-count')).toHaveAttribute('data-item-count', String(pairs.length));
}

/** Press start and wait for the summary — the modal reports in place, no toast. */
async function runSync(page: Page): Promise<void> {
    const modal = page.getByTestId('fx-sync-modal');
    await modal.getByTestId('sync-modal-start').click();
    await expect(modal.getByTestId('sync-modal-results')).toBeVisible({timeout: 60_000});
}

/** The five tallies the summary publishes, read as numbers. */
async function tallies(page: Page): Promise<{total: number; success: number; failed: number; fetched: number; changed: number}> {
    const results = page.getByTestId('fx-sync-modal').getByTestId('sync-modal-results');
    const read = async (name: string) => Number(await results.getAttribute(name));
    return {
        total: await read('data-total'),
        success: await read('data-success'),
        failed: await read('data-failed'),
        fetched: await read('data-fetched'),
        changed: await read('data-changed'),
    };
}

test.describe('FX sync — deterministic providers', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test.afterAll(async ({browser}) => {
        const page = await browser.newPage();
        await login(page, TEST_USER);
        for (const p of ALL_PAIRS) await dropPair(page.request, p);
        await page.close();
    });

    // -----------------------------------------------------------------------
    // FSM-001 — the modal says what it will do before it does it
    // -----------------------------------------------------------------------
    test('FSM-001: the modal announces the batch, and does nothing until asked', async ({page}) => {
        await seed(page.request, PAIRS.announce);
        await openSyncFor(page, PAIRS.announce);
        const modal = page.getByTestId('fx-sync-modal');

        // One section (FX), two items, and no results yet: opening is not running.
        await expect(modal.getByTestId('sync-modal-count')).toHaveAttribute('data-section-count', '1');
        await expect(modal.getByTestId('sync-modal-results')).toHaveCount(0);
        await expect(modal.getByTestId('sync-modal-body')).toHaveAttribute('data-busy', 'false');

        await modal.getByTestId('sync-modal-dismiss').click();
        await expect(modal).toBeHidden();
    });

    // -----------------------------------------------------------------------
    // FSM-002 — a successful sync reports numbers that came from the server
    // -----------------------------------------------------------------------
    test('FSM-002: a working provider is counted as a success, with its points', async ({page}) => {
        await seed(page.request, PAIRS.success);
        await openSyncFor(page, PAIRS.success);
        await runSync(page);

        const t = await tallies(page);
        expect(t.total).toBe(1);
        expect(t.success).toBe(1);
        expect(t.failed).toBe(0);
        // MOCKFX answers for every day in the window, so the count is positive
        // whatever range the page defaulted to. The exact number belongs to the
        // range, not to the contract under test.
        expect(t.fetched).toBeGreaterThan(0);

        const section = page.getByTestId('fx-sync-modal').getByTestId('sync-section');
        await expect(section).toHaveAttribute('data-section-id', 'fx');
        await expect(section).toHaveAttribute('data-result-count', '1');
    });

    // -----------------------------------------------------------------------
    // FSM-003 — a failing provider is reported as a failure
    // -----------------------------------------------------------------------
    test('FSM-003: a failing provider is counted as failed, not quietly as done', async ({page}) => {
        await seed(page.request, [], PAIRS.failure);
        await openSyncFor(page, PAIRS.failure);
        await runSync(page);

        const t = await tallies(page);
        expect(t.total).toBe(1);
        expect(t.success).toBe(0);
        expect(t.failed).toBe(1);
        expect(t.fetched).toBe(0);
    });

    // -----------------------------------------------------------------------
    // FSM-004 — a mixed batch is both, and offers to retry only the failures
    // -----------------------------------------------------------------------
    test('FSM-004: a mixed batch reports both halves and offers a retry of the failed', async ({page}) => {
        await seed(page.request, PAIRS.mixedOk, PAIRS.mixedFail);
        await openSyncFor(page, [...PAIRS.mixedOk, ...PAIRS.mixedFail]);
        await runSync(page);

        const t = await tallies(page);
        expect(t.total).toBe(4);
        expect(t.success).toBe(2);
        expect(t.failed).toBe(2);

        // The retry control only appears above one failure — with a single one the
        // per-row retry is the affordance instead.
        const modal = page.getByTestId('fx-sync-modal');
        const retry = modal.getByTestId('sync-modal-retry-failed');
        await expect(retry).toBeVisible();

        // Arm the barrier *before* acting. `data-busy` is already `false` here, so
        // waiting for it would prove nothing — the classic counter-barrier trap.
        // The request is the subject: what is under test is that the retry reaches
        // the server, and it always does (there is no cache on this path).
        const retried = page.waitForResponse((r) => r.url().includes('/fx/currencies/sync') && r.request().method() === 'POST', {timeout: 60_000});
        await retry.click();
        const body = (await (await retried).json()) as {results?: Array<{pair: string}>};

        // Only the failures go back out — the successes are not re-fetched.
        expect(new Set((body.results ?? []).map((r) => r.pair))).toEqual(new Set(PAIRS.mixedFail.map(slug)));

        await expect(modal.getByTestId('sync-modal-body')).toHaveAttribute('data-busy', 'false', {timeout: 60_000});

        // And the summary still counts all four: a retry *merges* into the batch
        // rather than replacing it, so what already worked is not thrown away
        // and re-fetched. MOCKFX_FAIL fails again, deterministically.
        const after = await tallies(page);
        expect(after.total).toBe(4);
        expect(after.success).toBe(2);
        expect(after.failed).toBe(2);
    });

    // -----------------------------------------------------------------------
    // FSM-005 — syncing the same data twice says so
    // -----------------------------------------------------------------------
    test('FSM-005: a second sync of unchanged data reports nothing changed', async ({page}) => {
        // MOCKFX returns the same fixed rate every time, so the second pass
        // writes nothing. That is the shape of the silent-failure the rule
        // exists to catch, produced here on purpose and from a provider we own.
        await seed(page.request, PAIRS.unchanged);
        await openSyncFor(page, PAIRS.unchanged);
        await runSync(page);
        await page.getByTestId('fx-sync-modal').getByTestId('sync-modal-close').click();

        await openSyncFor(page, PAIRS.unchanged);
        await runSync(page);

        const t = await tallies(page);
        expect(t.success).toBe(1);
        expect(t.fetched).toBeGreaterThan(0);
        expect(t.changed).toBe(0);
    });
});
