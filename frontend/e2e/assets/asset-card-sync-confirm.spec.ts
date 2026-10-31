/**
 * The card's Sync asks before it replaces stored prices — E2E (X-R61 + X-R29, lot X6-1).
 *
 * The Sync button of an asset's card used to start at once, with no word about the prices the range already holds. It now
 * asks `POST /api/v1/assets/prices/stored-count` for the range first: with stored prices, the page opens a confirmation
 * (`asset-sync-confirm`) that names how many it replaces and how many of them were entered by hand, and sends the sync only
 * on the user's yes; with none, the sync starts as before.
 *
 * Everything here is answered in the browser — the asset, its prices, the count and the sync — so nothing is written and no
 * provider is called; the tests create nothing, there is nothing to clean up.
 */

import {IntlMessageFormat} from 'intl-messageformat';
import {expect, test} from '../fixtures/playwright';
import type {Locator, Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {t} from '../fixtures/i18n-data';
import {pageLanguage} from '../fixtures/sync-overwrite';

const ASSET_ID = 88101;
const ASSET_NAME = 'Sync confirm asset';

const ASSET = {
    id: ASSET_ID,
    display_name: ASSET_NAME,
    currency: 'EUR',
    asset_type: 'STOCK',
    active: true,
    has_metadata: false,
    provider_code: 'mockprov',
    tx_count: 0,
    tx_count_own: 0,
    held_by_me: false,
    held_by_others: false,
};

type Counts = {stored_count: number; manual_count: number};

/** The list with one asset that has a provider, an empty price answer, and the two calls under test recorded. */
async function mockPage(page: Page, counts: Counts | 'fails') {
    const sent = {count: [] as unknown[], sync: [] as unknown[]};
    await page.route('**/api/v1/assets/query*', (route) => route.fulfill({json: [ASSET]}));
    await page.route('**/api/v1/assets/prices/query', async (route) => {
        const requested = (route.request().postDataJSON() as Array<{asset_id: number}> | null) ?? [];
        await route.fulfill({json: {items: requested.map(({asset_id}) => ({asset_id, prices: [], events: [], errors: [], signals: []}))}});
    });
    await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
    await page.route('**/api/v1/assets/prices/stored-count', async (route) => {
        sent.count.push(route.request().postDataJSON());
        if (counts === 'fails') return route.fulfill({status: 500, json: {detail: 'boom'}});
        await route.fulfill({json: {items: [{asset_id: ASSET_ID, ...counts}]}});
    });
    await page.route('**/api/v1/assets/prices/sync', async (route) => {
        sent.sync.push(route.request().postDataJSON());
        await route.fulfill({json: {results: [{asset_id: ASSET_ID, status: 'ok', points_fetched: 1, points_changed: 1, inserted_count: 1, updated_count: 0, errors: []}], success_count: 1, errors: []}});
    });
    return sent;
}

async function openPage(page: Page) {
    await navigateTo(page, '/assets');
    await expect(page.getByTestId('assets-page')).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
}

/** The card of the test's asset: the page's other cards never carry its id. */
function card(page: Page): Locator {
    return page.getByTestId(`asset-card-${ASSET_ID}`);
}

function confirmDialog(page: Page): Locator {
    return page.getByRole('dialog').filter({has: page.getByTestId('asset-sync-confirm')});
}

async function clickCardSync(page: Page) {
    await expect(card(page)).toBeVisible();
    await card(page).getByTestId('asset-card-sync-btn').click();
}

test.describe('Asset card Sync asks before replacing stored prices (X-R61)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('stored prices in the range: the sync waits for a yes, and the count names the manual ones', async ({page}) => {
        const sent = await mockPage(page, {stored_count: 3, manual_count: 2});
        await openPage(page);

        await clickCardSync(page);

        const dialog = confirmDialog(page);
        await expect(dialog, 'the confirmation opens').toBeVisible();
        // The range asked is the sync's own: the asset, a start (a date or "min") and an end date.
        expect(sent.count).toHaveLength(1);
        expect(sent.count[0], 'the count is asked for the card’s asset and the range the sync would ask for').toMatchObject([{asset_id: ASSET_ID, date_range: {end: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/)}}]);
        const lang = await pageLanguage(page);
        const message = String(new IntlMessageFormat(t(lang, 'assets.sync.confirmMessage'), lang).format({stored: 3}));
        const manual = String(new IntlMessageFormat(t(lang, 'assets.sync.confirmManual'), lang).format({manual: 2}));
        await expect(dialog.getByTestId('confirm-modal-message')).toHaveText(message);
        await expect(dialog).toContainText(manual);
        expect(sent.sync, 'no sync left the page before the yes').toEqual([]);

        // No: nothing is sent, the dialog closes.
        await dialog.getByTestId('confirm-modal-cancel').click();
        await expect(dialog).toBeHidden();
        expect(sent.sync).toEqual([]);

        // Yes: one sync, for this asset.
        await clickCardSync(page);
        await expect(dialog).toBeVisible();
        await dialog.getByTestId('confirm-modal-confirm').click();
        await expect(dialog).toBeHidden();
        await expect.poll(() => sent.sync.length, {message: 'the confirmed sync is sent once'}).toBe(1);
        expect(sent.sync[0]).toMatchObject([{asset_id: ASSET_ID}]);
        await waitForSettled(page.getByTestId('assets-page'), 20_000);
    });

    test('stored prices that are all from the provider: the confirmation names no manual ones', async ({page}) => {
        await mockPage(page, {stored_count: 1, manual_count: 0});
        await openPage(page);

        await clickCardSync(page);

        const dialog = confirmDialog(page);
        await expect(dialog).toBeVisible();
        const lang = await pageLanguage(page);
        const manual = String(new IntlMessageFormat(t(lang, 'assets.sync.confirmManual'), lang).format({manual: 0}));
        await expect(dialog.getByTestId('confirm-modal-message')).toBeVisible();
        await expect(dialog.getByText(manual, {exact: false})).toHaveCount(0);
    });

    test('nothing stored in the range: the sync starts at once, with no confirmation', async ({page}) => {
        const sent = await mockPage(page, {stored_count: 0, manual_count: 0});
        await openPage(page);

        await clickCardSync(page);

        await expect.poll(() => sent.sync.length, {message: 'the sync is sent without asking'}).toBe(1);
        await expect(confirmDialog(page)).toHaveCount(0);
    });

    test('a count that cannot be read does not stop the sync', async ({page}) => {
        const sent = await mockPage(page, 'fails');
        await openPage(page);

        await clickCardSync(page);

        await expect.poll(() => sent.sync.length, {message: 'the sync is sent although the count failed'}).toBe(1);
        await expect(confirmDialog(page)).toHaveCount(0);
    });
});
