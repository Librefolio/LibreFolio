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
 * `force`, which takes their transactions), then the assets with their prices and events.
 */
import {expect, test, type Locator, type Page, type Request, type Response} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {API_BASE} from './assets-helpers';

test.setTimeout(60_000);

const EVENTS_PATH = `${API_BASE}/assets/events`;

type OwnedAsset = {id: number; name: string};
/** What one test created, deleted afterwards in FK-safe order. */
type Owned = {assetIds: number[]; brokerIds: number[]};
type StoredEvent = {id: number; date: string; type: string; value: {code: string; amount: string}; notes: string | null; is_auto: boolean};
type SentItem = {asset_id: number; delete_ids?: number[]; events?: Array<{id?: number | null; date: string; type: string; value: {code: string; amount: number | string}; notes?: string}>};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** A USD asset of this test's own, with two closes so the chart — and its editor button — is drawn. */
async function createOwnedAsset(page: Page, owned: Owned): Promise<OwnedAsset> {
    const name = `E2E event editor ${uniqueSuffix()}`;
    const response = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'USD', asset_type: 'STOCK'}]});
    expect(response.ok(), `create the owned asset: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const body = (await response.json()) as {results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>};
    const created = body.results.find((item) => item.display_name === name);
    if (typeof created?.asset_id === 'number') owned.assetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`The owned asset ${name} was not created: ${created?.message ?? 'missing result'}`);
    await jsonFrom(
        await page.request.post(`${API_BASE}/assets/prices`, {
            data: [
                {
                    asset_id: created.asset_id,
                    prices: [
                        {date: daysAgoIso(30), close: 10},
                        {date: daysAgoIso(10), close: 11},
                    ],
                },
            ],
        }),
        'store two closes on the owned asset',
    );
    return {id: created.asset_id, name};
}

/**
 * A DIVIDEND on a broker of this test's own that realises `eventId`: what makes the event "in use".
 * The broker is recorded for cleanup before anything about the result is checked.
 */
async function linkDividend(page: Page, owned: Owned, assetId: number, eventId: number, date: string): Promise<number> {
    const brokerName = `E2E event editor broker ${uniqueSuffix()}`;
    const brokers = await jsonFrom<{results: Array<{broker_id?: number; name: string; success: boolean}>}>(await page.request.post(`${API_BASE}/brokers`, {data: [{name: brokerName, allow_cash_overdraft: true}]}), 'create the owned broker');
    const broker = brokers.results.find((item) => item.name === brokerName);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`The owned broker was not created: ${JSON.stringify(brokers)}`);
    const committed = await jsonFrom<{committed: boolean; results: Array<{operation: string; index: number; ids: number[]}>}>(
        await page.request.post(`${API_BASE}/transactions/commit`, {
            data: {creates: [{broker_id: broker.broker_id, asset_id: assetId, type: 'DIVIDEND', date, cash: {code: 'USD', amount: '1.25'}, asset_event_id: eventId}]},
        }),
        'commit the DIVIDEND that realises the event',
    );
    expect(committed.committed, JSON.stringify(committed)).toBe(true);
    const txId = committed.results.find((r) => r.operation === 'create' && r.index === 0)?.ids[0];
    if (typeof txId !== 'number') throw new Error(`The DIVIDEND was not created: ${JSON.stringify(committed)}`);
    return txId;
}

/** Delete what this test created: brokers first (`force` takes their transactions), then assets with their prices and events. */
async function deleteOwned(page: Page, owned: Owned): Promise<void> {
    if (owned.assetIds.length === 0 && owned.brokerIds.length === 0) return;
    try {
        // Leave the page first: an editor still open on these rows goes with it, unsaved.
        await page.goto('about:blank');
    } finally {
        for (const id of owned.brokerIds) {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API_BASE}/brokers?ids=${id}&force=true`), `delete the owned broker ${id}`);
            expect(result.results.find((item) => item.id === id)?.success, `owned broker ${id} deleted`).toBe(true);
        }
        for (const id of owned.assetIds) {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean; message?: string}>}>(await page.request.delete(`${API_BASE}/assets?asset_ids=${id}`), `delete the owned asset ${id}`);
            const mine = result.results.find((item) => item.asset_id === id);
            expect(mine?.success, `owned asset ${id} and its events are deleted: ${mine?.message ?? 'missing result'}`).toBe(true);
        }
    }
}

/** Manual events written in one plain upsert; returns their ids in the order given, found by their notes. */
async function seedEvents(page: Page, assetId: number, events: Array<{date: string; type: string; amount: string; notes: string}>): Promise<number[]> {
    await jsonFrom(await page.request.post(EVENTS_PATH, {data: [{asset_id: assetId, events: events.map(({date, type, amount, notes}) => ({date, type, value: {code: 'USD', amount}, notes}))}]}), 'seed the manual events');
    const stored = await storedEvents(page, assetId);
    return events.map(({notes}) => {
        const matches = stored.filter((e) => e.notes === notes);
        if (matches.length !== 1) throw new Error(`Expected one event noted "${notes}", found ${matches.length}: ${JSON.stringify(stored)}`);
        return matches[0].id;
    });
}

/** Every event of the owned asset in the window the tests write in. */
async function storedEvents(page: Page, assetId: number): Promise<StoredEvent[]> {
    const body = await jsonFrom<{items: Array<{asset_id: number; events: StoredEvent[]}>}>(await page.request.post(`${EVENTS_PATH}/query`, {data: [{asset_id: assetId, date_range: {start: daysAgoIso(60), end: todayIso()}}]}), `query the events of asset ${assetId}`);
    return body.items.find((item) => item.asset_id === assetId)?.events ?? [];
}

/** id → what a save would change. */
async function snapshot(page: Page, assetId: number): Promise<Record<number, string>> {
    return Object.fromEntries((await storedEvents(page, assetId)).map((e) => [e.id, `${e.date} ${e.type} ${Number(e.value.amount)} ${e.value.code} ${e.notes ?? ''}`]));
}

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

/** The asset page on a range holding the events, and its editor on the Events tab. */
async function openEventsEditor(page: Page, asset: OwnedAsset): Promise<Locator> {
    // The page polls POST /assets/prices/current, which may ask live providers and write today's price
    // into the shared database. Nothing here is about live prices: it is answered locally.
    await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
    // A full page load: the range in the URL is read once, when the app starts.
    await navigateTo(page, `/assets/${asset.id}?start=${daysAgoIso(40)}&end=${todayIso()}`);
    // The editor is handed the events the page loaded: it is only as ready as the page.
    await waitForSettled(page.getByTestId('asset-detail-page'), 30_000);
    const editButton = page.getByTestId('asset-detail-editdata-btn');
    await expect(editButton).toBeVisible({timeout: 10_000});
    await editButton.click();
    const panel = page.getByTestId('asset-detail-editor-panel');
    await expect(panel).toBeVisible();
    const eventsTab = panel.getByTestId('asset-editor-events-tab');
    await eventsTab.click();
    await expect(eventsTab).toHaveAttribute('aria-selected', 'true');
    return panel;
}

/** A saved event's row, by its id. */
function eventRow(panel: Locator, eventId: number): Locator {
    return panel.locator(`tbody tr[data-row-id="${eventId}"]`);
}

/** Mark a saved event's row deleted, through its row action. */
async function markDeleted(page: Page, panel: Locator, eventId: number) {
    await panel.getByTestId(`row-actions-${eventId}`).click();
    const deleteAction = page.getByTestId('context-menu-action-delete');
    await deleteAction.click();
    await expect(deleteAction).toBeHidden();
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
