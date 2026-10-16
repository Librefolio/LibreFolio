/**
 * asset-event-editor-save.spec.ts — how the Events tab of the asset data editor saves
 * (release 1.3, workstream W lot E1b: I-10, I-11c, decisions 21–22 and the decision of 15/10 16:20)
 *
 * A save is ONE `POST /assets/events`: the rows marked deleted travel as `delete_ids`, the edited and
 * new rows as `events`, in one transaction. No `DELETE` is sent during a save.
 * - Deletions go first (I-10): one save that deletes an event and moves another onto the date and
 *   type it frees is kept whole. The editor cannot move a saved row to another date (DataEditor.svelte:
 *   only an appended row has a date picker), so the move is a retype onto the deleted event's key —
 *   the same server rule (an edit landing on a key a manual event holds).
 * - A row keeps its currency (I-11c): a CSV line in another currency is sent with its own code and
 *   refused (EVENT_CURRENCY_MISMATCH), never relabelled with the asset's; the valid line of the same
 *   save is not kept either (decision 22).
 * - An event a transaction realises cannot be deleted: the save is refused whole (409 EVENT_IN_USE),
 *   with an error toast, and nothing of it is kept — not the edit beside it either. Before, the edit
 *   was saved and the delete skipped with a warning.
 * - A refused save is an error toast and keeps nothing. The sentence naming the row is pinned in
 *   eventSaveError.test.ts; here only the toast and the stored rows are asserted.
 *
 * Before E1b the editor sends the upsert, then a `DELETE`: the first test is refused (HTTP 400, and
 * the request carries no `delete_ids`), the second sees the EUR line relabelled USD and saved, the
 * third sees the edit saved and a warning. The fourth is a GUARD of today's behaviour.
 *
 * Data. Each test creates a USD asset of its own — two closes, because only a chart with prices offers
 * the editor button — its own events, noted with markers only it writes, and, for an event in use, a
 * broker of its own with the one DIVIDEND that realises it. Afterwards the brokers go first (with
 * `force`, which takes their transactions), then the assets with their prices and events. The helpers
 * that do it live in asset-events-owned.ts, shared with asset-event-delete.spec.ts.
 */
import {expect, test, type Locator, type Page, type Request, type Response} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedAsset, deleteOwned, eventRow, EVENTS_PATH, linkDividend, markDeleted, openEventsEditor, seedEvents, snapshot, storedEvents, type Owned} from './asset-events-owned';

test.setTimeout(60_000);

type SentItem = {asset_id: number; delete_ids?: number[]; events?: Array<{id?: number | null; date: string; type: string; value: {code: string; amount: number | string}; notes?: string}>};

function isEventsPost(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === EVENTS_PATH;
}

function isEventsPostResponse(response: Response): boolean {
    return isEventsPost(response.request());
}

/**
 * Every write the page sends to `/assets/events` (not `/query`) from now on, as a list it keeps
 * filling. Armed before the save, so nothing it sends can be missed; `stop()` disarms it.
 */
function recordEventWrites(page: Page): {writes: Array<{method: string; body: unknown}>; stop: () => void} {
    const writes: Array<{method: string; body: unknown}> = [];
    const listener = (request: Request) => {
        if (request.method() === 'GET' || new URL(request.url()).pathname !== EVENTS_PATH) return;
        writes.push({method: request.method(), body: request.method() === 'POST' ? request.postDataJSON() : null});
    };
    page.on('request', listener);
    return {writes, stop: () => page.off('request', listener)};
}

/** The item of a recorded `POST /assets/events` body that targets `assetId`. */
function sentItem(body: unknown, assetId: number): SentItem {
    const item = (body as SentItem[]).find((candidate) => candidate.asset_id === assetId);
    if (!item) throw new Error(`The events request carries no item for asset ${assetId}: ${JSON.stringify(body)}`);
    return item;
}

/** Retype a row. The Type cell is the row's only select; its options carry the type in their id, not in a translated label. */
async function retype(page: Page, row: Locator, type: string) {
    const typeSelect = row.getByRole('combobox');
    const listboxId = await typeSelect.getAttribute('aria-controls');
    expect(listboxId, 'the type select names its listbox').toBeTruthy();
    await typeSelect.click();
    const listbox = page.locator(`[id="${listboxId}"]`);
    await expect(listbox).toBeVisible();
    await listbox.locator(`[role="option"][id="${listboxId}-option-${type}"]`).click();
    await expect(listbox).toBeHidden();
}

test.describe('Asset events editor: how a save is sent', () => {
    /** What the running test created; deleted after it, whatever its outcome. */
    let owned: Owned = {assetIds: [], brokerIds: []};

    test.beforeEach(async ({page}) => {
        owned = {assetIds: [], brokerIds: []};
        await login(page, TEST_USER);
    });

    test.afterEach(async ({page}) => {
        await deleteOwned(page, owned);
    });

    test('one save deletes an event and retypes another onto its date and type: one POST, the deletion first, both kept', async ({page}) => {
        const asset = await createOwnedAsset(page, owned);
        const day = daysAgoIso(20);
        const marker = `E1b order ${uniqueSuffix()}`;
        const [aId, bId] = await seedEvents(page, asset.id, [
            {date: day, type: 'INTEREST', amount: '0.50', notes: `${marker} A`},
            {date: day, type: 'DIVIDEND', amount: '1.00', notes: `${marker} B`},
        ]);

        const panel = await openEventsEditor(page, asset);
        await expect(eventRow(panel, aId), 'the INTEREST this test created is listed').toBeVisible({timeout: 15_000});
        const rowB = eventRow(panel, bId);
        await expect(rowB, 'the DIVIDEND this test created is listed').toBeVisible();

        await markDeleted(page, panel, aId);
        await retype(page, rowB, 'INTEREST');
        const saveButton = panel.getByTestId('asset-editor-save-btn');
        await expect(saveButton).toBeEnabled();

        const recorder = recordEventWrites(page);
        try {
            const upsert = page.waitForResponse(isEventsPostResponse, {timeout: 15_000});
            await saveButton.click();
            const response = await upsert;
            const item = sentItem(response.request().postDataJSON(), asset.id);
            // Before E1b the save carries no deletions: they follow in a DELETE, after an upsert the
            // server refuses (EVENT_KEY_CONFLICT, HTTP 400) while A still holds (day, INTEREST).
            expect(item.delete_ids ?? [], 'the deletion travels in the same request').toEqual([aId]);
            expect(
                (item.events ?? []).map((e) => ({id: e.id ?? null, type: e.type})),
                'beside the retype of B',
            ).toEqual([{id: bId, type: 'INTEREST'}]);
            expect(response.status(), 'deleted first, A frees the key B moves onto').toBe(200);
            // The page closes the editor only once the save has been answered.
            await expect(panel).toBeHidden({timeout: 15_000});
        } finally {
            recorder.stop();
        }
        expect(
            recorder.writes.map((w) => w.method),
            'a save is one POST, and never a DELETE',
        ).toEqual(['POST']);

        const after = (await storedEvents(page, asset.id)).map(({id, date, type}) => ({id, date, type}));
        expect(after, 'A deleted; B now INTEREST, under its own id').toEqual([{id: bId, date: day, type: 'INTEREST'}]);
    });

    test('a CSV line in another currency is sent with its own code and refused, and nothing of the save is kept', async ({page}) => {
        const asset = await createOwnedAsset(page, owned);
        const marker = `E1b currency ${uniqueSuffix()}`;
        const usdDay = daysAgoIso(25);
        const eurDay = daysAgoIso(15);
        const before = await snapshot(page, asset.id);

        const panel = await openEventsEditor(page, asset);
        await panel.getByTestId('fx-data-import-btn').click();
        const modal = page.getByTestId('data-import-modal');
        await expect(modal).toBeVisible();
        const csv = `date;currency;type;amount;notes\n${usdDay};USD;DIVIDEND;1.00;${marker} usd\n${eurDay};EUR;DIVIDEND;2.00;${marker} eur`;
        const input = modal.getByTestId('csv-editor-input');
        await input.fill(csv);
        await expect(input).toHaveValue(csv);
        const confirm = modal.getByTestId('data-import-confirm');
        await expect(confirm, 'both lines are valid import rows').toHaveAttribute('data-valid-rows', '2');
        await expect(confirm).toHaveAttribute('data-error-count', '0');
        await confirm.click();
        await expect(modal).toBeHidden();

        const saveButton = panel.getByTestId('asset-editor-save-btn');
        await expect(saveButton).toBeEnabled();
        const sent = page.waitForRequest(isEventsPost, {timeout: 15_000});
        await saveButton.click();

        const item = sentItem((await sent).postDataJSON(), asset.id);
        const codes = Object.fromEntries((item.events ?? []).map((e) => [e.notes ?? '', e.value.code]));
        // Before E1b every row is relabelled with the asset's currency, and the EUR line is saved as USD.
        expect(codes, 'each line travels in its own currency').toEqual({[`${marker} usd`]: 'USD', [`${marker} eur`]: 'EUR'});

        await expect(page.getByTestId('toast-error'), 'the refusal (EVENT_CURRENCY_MISMATCH) is reported').toBeVisible({timeout: 10_000});
        await expect(panel, 'the editor stays open: nothing was saved').toBeVisible();
        expect(await snapshot(page, asset.id), 'all or nothing: the valid USD line is not kept either').toEqual(before);
    });

    test('one save deletes an event a transaction realises and edits another: refused whole, nothing kept, an error toast', async ({page}) => {
        const asset = await createOwnedAsset(page, owned);
        const day = daysAgoIso(22);
        const otherDay = daysAgoIso(18);
        const marker = `E1b in use ${uniqueSuffix()}`;
        const [linkedId, editedId] = await seedEvents(page, asset.id, [
            {date: day, type: 'DIVIDEND', amount: '1.00', notes: `${marker} linked`},
            {date: otherDay, type: 'DIVIDEND', amount: '2.00', notes: `${marker} edited`},
        ]);
        await linkDividend(page, owned, asset.id, linkedId, day);
        const before = await snapshot(page, asset.id);

        const panel = await openEventsEditor(page, asset);
        await expect(eventRow(panel, linkedId), 'the realised DIVIDEND this test created is listed').toBeVisible({timeout: 15_000});
        await markDeleted(page, panel, linkedId);
        // The edit beside the deletion: the other event's amount, typed into its cell (no dropdown).
        const amountInput = eventRow(panel, editedId).locator('td[data-column-id="amount"] input');
        await amountInput.fill('2.75');
        await amountInput.press('Enter');
        await expect(amountInput).toHaveValue('2.75');
        const saveButton = panel.getByTestId('asset-editor-save-btn');
        await expect(saveButton).toBeEnabled();

        const upsert = page.waitForResponse(isEventsPostResponse, {timeout: 15_000});
        await saveButton.click();
        // Before E1b the edit is saved (200) and the delete, sent apart, comes back in_use with a warning.
        expect((await upsert).status(), 'an event in use cannot be deleted: the save is refused whole (EVENT_IN_USE)').toBe(409);

        await expect(page.getByTestId('toast-error'), 'the refusal is reported as an error').toBeVisible({timeout: 10_000});
        await expect(panel, 'the editor stays open with the edits').toBeVisible();
        expect(await snapshot(page, asset.id), 'nothing kept: the realised event and the edited one as they were').toEqual(before);
    });

    test('GUARD: a save the server refuses is an error toast, and nothing of it is kept', async ({page}) => {
        // Green before E1b too: the refusal comes from the events of one item (decision 22: the whole
        // item is checked before anything is written), and this save deletes nothing.
        const asset = await createOwnedAsset(page, owned);
        const day = daysAgoIso(20);
        const otherDay = daysAgoIso(12);
        const marker = `E1b refused ${uniqueSuffix()}`;
        const [aId, bId, cId] = await seedEvents(page, asset.id, [
            {date: day, type: 'INTEREST', amount: '0.50', notes: `${marker} A`},
            {date: day, type: 'DIVIDEND', amount: '1.00', notes: `${marker} B`},
            {date: otherDay, type: 'DIVIDEND', amount: '2.00', notes: `${marker} C`},
        ]);
        const before = await snapshot(page, asset.id);

        const panel = await openEventsEditor(page, asset);
        await expect(eventRow(panel, aId), 'the INTEREST this test created is listed').toBeVisible({timeout: 15_000});
        // C alone would be a valid edit; B onto A's key, with A kept, is refused (EVENT_KEY_CONFLICT).
        await retype(page, eventRow(panel, cId), 'SPLIT');
        await retype(page, eventRow(panel, bId), 'INTEREST');
        const saveButton = panel.getByTestId('asset-editor-save-btn');
        await expect(saveButton).toBeEnabled();

        const upsert = page.waitForResponse(isEventsPostResponse, {timeout: 15_000});
        await saveButton.click();
        expect((await upsert).status(), 'B cannot take the key A still holds').toBe(400);

        await expect(page.getByTestId('toast-error'), 'the refusal is reported').toBeVisible({timeout: 10_000});
        await expect(panel, 'the editor stays open with the edits').toBeVisible();
        expect(await snapshot(page, asset.id), 'nothing of the save is kept, C included').toEqual(before);
    });
});
