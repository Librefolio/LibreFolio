/**
 * Z-29d (reduced): the settings preview of a sampled card draws a comparison the user has just picked, before saving.
 *
 * What it protects. A card of the asset list draws a sampled series — one point a week or a month when its range is wider
 * than its plot (Z-29b) — and its comparisons are read on its own buckets (`sample_like` its `key`). A comparison saved
 * earlier is read by the list as it loads. One the user has just picked in the card's settings is not read yet, and the
 * preview would not draw it until the save: the page reads it as soon as it is picked (`targetSampleLoader.ts`,
 * `readTargetSample` in `assets/+page.svelte`), once, into the preview only.
 *
 * What is observed, with no hook in the product beyond the card's own settings button:
 *   · the read: a price query with an item `sample_like` the card's key, for the picked asset, leaves the page after the
 *     pick and before any click on Apply; it is answered sampled (weekly or monthly), with prices;
 *   · the drawing: the preview's canvas is not the one it was before the pick, once the read is answered — before the
 *     pick the new card holds no asset and draws nothing, so what changes is the line;
 *   · the cancel: closing the dialog leaves the card's settings as they were — stored, and shown on reopening — and no
 *     other read leaves the page for the target.
 *
 * Isolation. The test creates its own two assets (a card and the target) with 900 days of prices each, narrows the list to
 * them by a token in their names, and deletes them at the end. The chart settings live in this test's browser storage: no
 * shared setting is written. Nothing is located by position or counted among the neighbours' rows.
 */

import {expect, test, type Locator, type Page, type Response} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {daysAgoIso} from '../fixtures/dates';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueToken} from '../fixtures/unique';
import {waitForChart} from '../fixtures/app-events';
import {goToAssetsPage} from './assets-helpers';

const ASSET_PRICE_QUERY = /\/api\/v1\/assets\/prices\/query(\?.*)?$/;

/**
 * The card's settings button, inside the card. The name is the one agreed with Y for the list's `AssetCard`
 * (checkpoint 0 of wave 4): change it here and nowhere else when it differs.
 */
const CARD_SETTINGS_TESTID = 'asset-card-settings';

/** Days of daily prices each asset stores: far more than a card's plot takes, so the list shows it weekly or monthly. */
const HISTORY_DAYS = 900;

/** One query the page sent and the answer it got: item `index` of the request is item `index` of the answer. */
interface Exchange {
    items: Array<{asset_id?: number; key?: string; sample_like?: string; max_points?: number; include_price?: boolean}>;
    results: Array<{asset_id?: number; resolution?: string; prices?: unknown[]}>;
}

/** Every price query of the page from now on, with its answer: armed before the page opens. */
function recordPriceQueries(page: Page): Exchange[] {
    const log: Exchange[] = [];
    page.on('response', (response: Response) => {
        if (response.request().method() !== 'POST' || !ASSET_PRICE_QUERY.test(response.url())) return;
        void (async () => {
            try {
                const items = response.request().postDataJSON() as Exchange['items'];
                const body = (await response.json()) as {items?: Exchange['results']};
                if (Array.isArray(items)) log.push({items, results: body.items ?? []});
            } catch {
                // A request without a JSON body, or an answer that is not one: not a query the test reads.
            }
        })();
    });
    return log;
}

/** The queries of `log` that carry an item satisfying `wanted`, each with that item and the answer to it. */
function itemsAsked(log: readonly Exchange[], wanted: (item: Exchange['items'][number]) => boolean) {
    return log.flatMap((exchange) => exchange.items.flatMap((item, index) => (wanted(item) ? [{item, answer: exchange.results[index]}] : [])));
}

/**
 * A fingerprint of what a canvas shows now (a hash of its pixels): two reads equal mean the same picture. ECharts animates
 * a series in, so callers read it until it stops changing.
 */
async function canvasFingerprint(canvas: Locator): Promise<string> {
    return canvas.evaluate((element) => {
        const url = (element as HTMLCanvasElement).toDataURL();
        let hash = 5381;
        for (let index = 0; index < url.length; index += 1) hash = ((hash << 5) + hash + url.charCodeAt(index)) | 0;
        return `${url.length}:${hash}`;
    });
}

/** The picture of `canvas` once it has stopped changing: the same fingerprint on three reads in a row. */
async function settledPicture(canvas: Locator): Promise<string> {
    let previous = '';
    let stable = 0;
    await expect
        .poll(
            async () => {
                const now = await canvasFingerprint(canvas);
                stable = now === previous ? stable + 1 : 0;
                previous = now;
                return stable;
            },
            {message: 'the preview never stopped changing', timeout: 15_000, intervals: [250]},
        )
        .toBeGreaterThanOrEqual(3);
    return previous;
}

/** The chart settings the list keeps for the card under test, from this test's browser storage: its signals' types. */
async function storedCardSignalTypes(page: Page, assetId: number): Promise<string[]> {
    const me = await page.request.get('/api/v1/auth/me');
    expect(me.ok(), `GET /api/v1/auth/me answered HTTP ${me.status()}`).toBe(true);
    const userId = ((await me.json()) as {user?: {id?: unknown}}).user?.id;
    return page.evaluate(
        ({storageKey, pairKey}) => {
            const raw = localStorage.getItem(storageKey);
            if (!raw) return [];
            const store = JSON.parse(raw) as {pairOverrides?: Array<[string, {signals?: Array<{signalType?: string}>}]>};
            const entry = store.pairOverrides?.find(([key]) => key === pairKey);
            return (entry?.[1].signals ?? []).map((signal) => String(signal.signalType));
        },
        {storageKey: `lf_${String(userId)}_chartSettingsStore`, pairKey: `asset-${assetId}`},
    );
}

test.describe('Assets list — the settings preview of a sampled card draws a comparison before it is saved (Z-29d)', () => {
    // A ceiling, never a delay: the test seeds two assets, loads the list in its waves, and opens a dialog that reads.
    test.describe.configure({timeout: 90_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('a comparison picked in the card’s settings is read on the card’s buckets and drawn in the preview; cancelling leaves the card without it', async ({page}) => {
        const token = uniqueToken(6);
        const names = {card: `E2E Z29d ${token} card`, target: `E2E Z29d ${token} target`};
        const range = {start: daysAgoIso(HISTORY_DAYS), end: daysAgoIso(1)};
        const ownIds: number[] = [];
        try {
            // The two assets, with a history that starts before the range and covers all of it, day by day.
            const created = await page.request.post('/api/v1/assets', {data: Object.values(names).map((display_name) => ({display_name, currency: 'EUR', asset_type: 'STOCK'}))});
            const createdBody = (await created.json().catch(() => null)) as {results?: Array<{asset_id?: number | null; display_name?: string; success?: boolean}>} | null;
            for (const result of createdBody?.results ?? []) if (typeof result.asset_id === 'number') ownIds.push(result.asset_id);
            expect(created.ok(), `creating the two assets must succeed: HTTP ${created.status()} ${JSON.stringify(createdBody)}`).toBe(true);
            const idOf = (name: string): number => {
                const result = createdBody?.results?.find((entry) => entry.display_name === name);
                if (!result?.success || typeof result.asset_id !== 'number') throw new Error(`"${name}" was not created: ${JSON.stringify(createdBody)}`);
                return result.asset_id;
            };
            const cardId = idOf(names.card);
            const targetId = idOf(names.target);

            const history = (base: number, slope: number) => Array.from({length: HISTORY_DAYS + 5}, (_, index) => ({date: daysAgoIso(HISTORY_DAYS + 4 - index), close: (base + slope * index + 3 * Math.sin(index / 7)).toFixed(4)}));
            const upserts = [
                {asset_id: cardId, prices: history(100, 0.05)},
                {asset_id: targetId, prices: history(40, 0.12)},
            ];
            const stored = await page.request.post('/api/v1/assets/prices', {data: upserts});
            const storedBody = (await stored.json().catch(() => null)) as {results?: Array<{asset_id: number; count: number}>} | null;
            expect(stored.ok(), `POST /api/v1/assets/prices: HTTP ${stored.status()} ${JSON.stringify(storedBody)}`).toBe(true);
            for (const {asset_id, prices} of upserts) expect(storedBody?.results?.find((entry) => entry.asset_id === asset_id)?.count, `every close of asset ${asset_id} is stored`).toBe(prices.length);

            const queries = recordPriceQueries(page);
            await goToAssetsPage(page, range);
            // The list narrowed to the two assets of the test: the card under test, wherever the neighbours' rows sort.
            await page.getByTestId('assets-search-input').fill(token);
            const card = page.getByTestId(`asset-card-${cardId}`);
            await expect(card, 'the card under test is listed').toBeVisible({timeout: 10_000});
            await expect(page.getByTestId('assets-page')).toHaveAttribute('data-busy', 'false', {timeout: 20_000});

            // Premise: the list asked this card's series sampled and was answered weekly or monthly, not day by day.
            const cardKey = `asset:${cardId}`;
            await expect.poll(() => itemsAsked(queries, (item) => item.key === cardKey && item.include_price !== false).length, {message: 'the list never asked the card’s own series', timeout: 15_000}).toBeGreaterThan(0);
            const ownReads = itemsAsked(queries, (item) => item.key === cardKey && item.include_price !== false);
            expect(ownReads.at(-1)?.item.max_points, 'the card asks the points its plot takes').toBeGreaterThan(0);
            expect(['weekly', 'monthly'], `premise: a ${HISTORY_DAYS}-day range is wider than the card’s plot, so its series is sampled`).toContain(ownReads.at(-1)?.answer.resolution);

            // The dialog, from the card's own settings button.
            await card.getByTestId(CARD_SETTINGS_TESTID).click();
            const modal = page.getByTestId('chart-settings-modal');
            await expect(modal).toBeVisible();
            await expect(modal.locator('[data-signal-type="asset-comparison"]'), 'premise: the card has no comparison yet').toHaveCount(0);
            const previewCanvas = modal.locator('canvas').first();
            await waitForChart(modal);
            const pictureBefore = await settledPicture(previewCanvas);

            // Add a comparison the way a user does: Comparison, asset comparison, then the asset in the new signal card.
            const comparisonPicker = modal.getByTestId('signals-comparison-select-button');
            await expect(comparisonPicker, 'the comparison picker renders once the signal catalogue has loaded').toBeVisible({timeout: 15_000});
            await comparisonPicker.click();
            await modal.getByTestId('signal-tree-option-asset-comparison').click();
            const signalCard = modal.locator('[data-testid^="signal-card-"][data-signal-type="asset-comparison"]');
            await expect(signalCard).toHaveCount(1);
            const signalId = (await signalCard.getAttribute('data-testid'))?.slice('signal-card-'.length);
            if (!signalId) throw new Error('the new comparison card carries no signal id');
            const assetPicker = signalCard.getByTestId(`signal-param-${signalId}-assetId-select`);
            const assetTrigger = assetPicker.getByTestId(`signal-param-${signalId}-assetId-select-trigger`);

            // Before the pick, the new signal holds no asset: nothing of it is asked, nothing of it is drawn.
            const targetReads = () => itemsAsked(queries, (item) => item.asset_id === targetId && item.sample_like === cardKey);
            expect(targetReads(), 'nothing reads the target before it is picked').toHaveLength(0);

            await assetTrigger.click();
            await expect(assetTrigger).toHaveAttribute('aria-expanded', 'true');
            // Narrowed by the name the test gave it, as a user would: the row is then at the top of the list.
            const assetSearch = assetPicker.getByTestId(`signal-param-${signalId}-assetId-select-search`);
            await assetSearch.fill(names.target);
            await expect(assetSearch).toHaveValue(names.target);
            await assetPicker.getByTestId(`search-select-option-${targetId}`).click();

            // The read: the target on the card's buckets, asked now — Apply has not been clicked.
            await expect.poll(() => targetReads().length, {message: 'the target was never read for the preview', timeout: 15_000}).toBeGreaterThan(0);
            const read = targetReads()[0];
            await expect.poll(() => targetReads()[0]?.answer !== undefined, {message: 'the read of the target was never answered'}).toBe(true);
            expect(['weekly', 'monthly'], 'the target comes on the card’s step').toContain(read.answer.resolution);
            expect(read.answer.prices?.length ?? 0, 'the target’s sample holds prices').toBeGreaterThan(0);
            expect(read.item.include_price, 'the target’s item asks its prices').not.toBe(false);

            // The drawing: the preview shows another picture than before the pick.
            await expect.poll(async () => (await settledPicture(previewCanvas)) !== pictureBefore, {message: 'the preview still draws what it drew before the comparison was picked', timeout: 20_000}).toBe(true);

            // Once, however often the preview is drawn: a second read would be a loop.
            expect(targetReads(), 'one read of the target for the whole pick').toHaveLength(1);

            // Cancel: Escape asks the dialog to close, and a dialog with unsaved changes asks to discard them first.
            // Discarding is the cancel: nothing is saved, so the card has no comparison, in storage or on reopening.
            await page.keyboard.press('Escape');
            const discard = page.getByTestId('confirm-modal-confirm');
            await expect(discard, 'the dialog holds an unsaved comparison, so closing asks before discarding it').toBeVisible();
            await discard.click();
            await expect(modal).toBeHidden();
            expect(await storedCardSignalTypes(page, cardId), 'nothing was saved for the card').not.toContain('asset-comparison');
            await card.getByTestId(CARD_SETTINGS_TESTID).click();
            await expect(modal).toBeVisible();
            await expect(modal.locator('[data-signal-type="asset-comparison"]'), 'reopened, the dialog holds no comparison').toHaveCount(0);
            await page.keyboard.press('Escape');
            await expect(modal).toBeHidden();
            expect(targetReads(), 'cancelling and reopening read the target no more').toHaveLength(1);
        } finally {
            if (ownIds.length > 0) await page.request.delete(`/api/v1/assets?asset_ids=${ownIds.join(',')}`).catch(() => undefined);
        }
    });
});
