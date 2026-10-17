/**
 * tx-event-create-exists.spec.ts — «+ New event» never overwrites (release 1.3, decision 20; I-10 S4)
 *
 * The mini modal opened from the transaction form's event picker (EventCreateMiniModal) sends a new
 * event with `mode: 'create'`. When the asset already holds an event — manual or provider — on that
 * date and type, the server refuses (409 EVENT_EXISTS, nothing written) and the modal shows the
 * events already there (`event-exists-panel`, the form hidden, `event-create-submit` disabled):
 * - «Use this» (`event-exists-use`) links that event and writes nothing;
 * - «Edit this» (`event-exists-edit`, manual events only) opens it in the form with its own values —
 *   decimals kept — and saves it BY ID: same id, no new row;
 * - a provider event offers no edit, only a note (`event-exists-provider-note`) and «Use this»;
 * - «Cancel» (`event-exists-cancel`) goes back to the form as it was typed, nothing written.
 * After a save the picker holds the event the response names (`results[0].event_ids[0]`), never one
 * found again by date and type, and shows it as saved: after «Edit this» changed its notes, the
 * picker trigger reads the new notes, not the copy of the day it fetched before the edit (the picker
 * refreshes on the portfolio mutation bus, which already counts `POST /assets/events`). A refused
 * save reads as a sentence, never `[object Object]` nor a raw error code.
 *
 * Before E1b the modal sends a plain upsert: on a manual key it silently overwrites the stored event,
 * beside a provider event it adds a manual twin, then it closes and re-reads the day. Every test is
 * red on its first assertion about the new behaviour: the panel never appears, or the request carries
 * no mode. With the modal cured and the picker not, the three «Edit this» tests stay red on the
 * trigger: `fetchEvents` returns early on an unchanged key and finds the old copy, old notes.
 *
 * Data. Every test works on a USD asset of its own — never a seeded one: an asset is a global row,
 * and an event written on Apple is every other spec's input — with note markers only it writes. The
 * provider event comes from a `scheduled_investment` assignment on that asset: its planned event is
 * written under the assignment (`is_auto`) by a price sync, all computed locally, no network. The
 * asset is deleted after each test, and its events, prices and assignment go with it. The transaction
 * form is never saved: the seeded broker only completes it.
 */
import {expect, test, type Locator, type Page, type Request, type Response} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';

test.setTimeout(60_000);

const API = '/api/v1';
const EVENTS_PATH = `${API}/assets/events`;
/** The seeded broker that completes the DIVIDEND form (TEST_USER is its OWNER). The form is never saved. */
const BROKER_NAME = 'Interactive Brokers';

type OwnedAsset = {id: number; name: string};
type StoredEvent = {id: number; date: string; type: string; value: {code: string; amount: string}; notes: string | null; is_auto: boolean};
type SentItem = {asset_id: number; mode?: string; events: Array<{id?: number | null; date: string; type: string; value: {code: string; amount: number | string}; notes?: string}>};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

// ---------------------------------------------------------------------------
// API helpers — every row these write belongs to an asset this spec created
// ---------------------------------------------------------------------------

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** Today on the browser's calendar: the date the transaction form gives a new row, hence the mini modal's. */
async function browserToday(page: Page): Promise<string> {
    return page.evaluate(() => {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    });
}

/** `iso` moved by `days`, calendar arithmetic only (UTC on both ends, so no zone can shift it). */
function shiftIso(iso: string, days: number): string {
    const d = new Date(`${iso}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() + days);
    return d.toISOString().slice(0, 10);
}

/** A USD asset of this test's own. The id is recorded for cleanup before anything about the result is checked. */
async function createOwnedAsset(page: Page, ownedAssetIds: number[]): Promise<OwnedAsset> {
    const name = `E2E event exists ${uniqueSuffix()}`;
    const response = await page.request.post(`${API}/assets`, {data: [{display_name: name, currency: 'USD', asset_type: 'STOCK'}]});
    expect(response.ok(), `create the owned asset: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const body = (await response.json()) as {results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>};
    const created = body.results.find((item) => item.display_name === name);
    if (typeof created?.asset_id === 'number') ownedAssetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`The owned asset ${name} was not created: ${created?.message ?? 'missing result'}`);
    return {id: created.asset_id, name};
}

/** Delete the assets this test created; their events, prices and provider assignment go with them. */
async function deleteOwnedAssets(page: Page, ownedAssetIds: readonly number[]): Promise<void> {
    if (ownedAssetIds.length === 0) return;
    try {
        // Unmount the form first, so nothing on the page queries the asset while it goes.
        await page.goto('about:blank');
    } finally {
        for (const id of ownedAssetIds) {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean; message?: string}>}>(await page.request.delete(`${API}/assets?asset_ids=${id}`), `delete the owned asset ${id}`);
            const mine = result.results.find((item) => item.asset_id === id);
            expect(mine?.success, `owned asset ${id} and its events are deleted: ${mine?.message ?? 'missing result'}`).toBe(true);
        }
    }
}

/** Every event of the asset from 40 days before `day` up to `day`. */
async function eventsUpTo(page: Page, assetId: number, day: string): Promise<StoredEvent[]> {
    const body = await jsonFrom<{items: Array<{asset_id: number; events: StoredEvent[]}>}>(await page.request.post(`${EVENTS_PATH}/query`, {data: [{asset_id: assetId, date_range: {start: shiftIso(day, -40), end: day}}]}), `query the events of asset ${assetId}`);
    return body.items.find((item) => item.asset_id === assetId)?.events ?? [];
}

/** id → what a write would change: the "nothing written" check. */
async function snapshot(page: Page, assetId: number, day: string): Promise<Record<number, string>> {
    const rows = await eventsUpTo(page, assetId, day);
    return Object.fromEntries(rows.map((e) => [e.id, `${e.date} ${e.type} ${Number(e.value.amount)} ${e.value.code} ${e.notes ?? ''} auto=${e.is_auto}`]));
}

/**
 * Manual events written the way they exist today: one plain upsert (no mode, no id). Two events
 * on one date and type are both stored. Returns their ids in the order given, found by their notes.
 */
async function seedManualEvents(page: Page, assetId: number, day: string, events: Array<{amount: string; notes: string}>): Promise<number[]> {
    await jsonFrom(await page.request.post(EVENTS_PATH, {data: [{asset_id: assetId, events: events.map(({amount, notes}) => ({date: day, type: 'DIVIDEND', value: {code: 'USD', amount}, notes}))}]}), 'seed the manual events');
    const stored = await eventsUpTo(page, assetId, day);
    return events.map(({notes}) => {
        const matches = stored.filter((e) => e.notes === notes && !e.is_auto);
        if (matches.length !== 1) throw new Error(`Expected one manual event noted "${notes}", found ${matches.length}: ${JSON.stringify(stored)}`);
        return matches[0].id;
    });
}

/**
 * A provider event on `day`: the planned DIVIDEND of a `scheduled_investment` schedule assigned to
 * the asset, written under that assignment (`is_auto`) by a price sync. Local computation only.
 * `day` must be before today: a sync reads the provider's history up to yesterday only, and the
 * point it adds for today is the current value, which carries no event (refresh.py, `history_end`).
 */
async function seedProviderEvent(page: Page, assetId: number, day: string, notes: string, amount: string): Promise<number> {
    const providerParams = {
        initial_value: {code: 'USD', amount: '1000'},
        interest_type: 'SIMPLE',
        day_count: 'ACT/365',
        schedule: [{start_date: shiftIso(day, -60), end_date: shiftIso(day, 300), annual_rate: '0.02', maturation_frequency: 'MONTHLY'}],
        asset_events: [{date: day, type: 'DIVIDEND', value: {code: 'USD', amount}, notes}],
    };
    const assigned = await jsonFrom<{results: Array<{asset_id: number; success: boolean; message: string}>}>(
        await page.request.post(`${API}/assets/provider`, {data: [{asset_id: assetId, provider_code: 'scheduled_investment', identifier: '', identifier_type: 'AUTO_GENERATED', provider_params: providerParams}]}),
        'assign the scheduled_investment provider to the owned asset',
    );
    const assignment = assigned.results.find((r) => r.asset_id === assetId);
    if (!assignment?.success) throw new Error(`Precondition: the scheduled_investment assignment was refused: ${assignment?.message ?? JSON.stringify(assigned)}`);
    const synced = await jsonFrom<unknown>(await page.request.post(`${API}/assets/prices/sync`, {data: [{asset_id: assetId, date_range: {start: shiftIso(day, -60), end: day}}]}), 'sync the owned asset');
    const stored = await eventsUpTo(page, assetId, day);
    const matches = stored.filter((e) => e.is_auto && e.notes === notes && e.date === day && e.type === 'DIVIDEND');
    if (matches.length !== 1) throw new Error(`Precondition: the sync must write one provider DIVIDEND noted "${notes}" on ${day}, found ${matches.length}. Sync: ${JSON.stringify(synced)}; events: ${JSON.stringify(stored)}`);
    return matches[0].id;
}

/** The asset's DIVIDEND events on `day`, by id. */
async function dividendsOn(page: Page, assetId: number, day: string): Promise<StoredEvent[]> {
    return (await eventsUpTo(page, assetId, day)).filter((e) => e.date === day && e.type === 'DIVIDEND');
}

function isEventsPost(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === EVENTS_PATH;
}

function isEventsPostResponse(response: Response): boolean {
    return isEventsPost(response.request());
}

/** The item of the request that targets `assetId` — the request this spec's modal sent. */
function sentItem(request: Request, assetId: number): SentItem {
    const body = request.postDataJSON() as SentItem[];
    const item = body.find((candidate) => candidate.asset_id === assetId);
    if (!item) throw new Error(`The events request carries no item for asset ${assetId}: ${JSON.stringify(body)}`);
    return item;
}

// ---------------------------------------------------------------------------
// UI helpers — the DIVIDEND form, and its «+ New event»
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    // The table being visible is not the table being loaded: the page publishes data-busy.
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000});
}

/** The id of the seeded broker named exactly `name` — read, never assumed. */
async function seededBrokerId(page: Page, name: string): Promise<number> {
    const body = await jsonFrom<{items: Array<{id: number; name: string}>}>(await page.request.get(`${API}/brokers`), 'list the brokers');
    const matches = body.items.filter((broker) => broker.name === name);
    if (matches.length !== 1) throw new Error(`Expected exactly one broker named "${name}" visible to this user, found ${matches.length} — check populate_mock_data.py`);
    return matches[0].id;
}

async function selectType(page: Page, typeCode: string) {
    await page.getByTestId('tx-form-type').click();
    const option = page.getByTestId(`search-select-option-${typeCode}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionsClosed(page);
}

async function pickBroker(page: Page, brokerName: string) {
    const brokerId = await seededBrokerId(page, brokerName);
    await page.getByTestId('tx-form-broker-wrap').getByRole('combobox').click();
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionsClosed(page);
}

/** Pick exactly the asset with this id: search its name, then click the option carrying its id. */
async function pickAsset(page: Page, asset: OwnedAsset) {
    await page.getByTestId('tx-form-asset-trigger').click();
    const searchInput = page.getByTestId('tx-form-asset-search');
    await expect(searchInput).toBeVisible({timeout: 3_000});
    await searchInput.fill(asset.name);
    await expect(searchInput).toHaveValue(asset.name);
    const option = page.getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionsClosed(page);
}

async function openOptionalSection(page: Page) {
    const toggle = page.getByTestId('tx-form-optional-toggle');
    const details = toggle.locator('..');
    if ((await details.getAttribute('open')) === null) {
        await toggle.click();
        await expect(details).toHaveAttribute('open', '', {timeout: 3_000});
    }
}

/** Date the transaction form, typed as a user types it; Enter commits it and puts the calendar away. */
async function setFormDate(page: Page, date: string) {
    const dateRoot = page.getByTestId('tx-form-date-wrap').getByTestId('single-date-picker-root');
    const dateInput = dateRoot.locator('input[type="text"]');
    await dateInput.click();
    await dateInput.fill(date);
    await dateInput.press('Enter');
    await expect(dateRoot).toHaveAttribute('data-open', 'false');
    await expect(dateRoot).toHaveAttribute('data-invalid', 'false');
    await expect(dateInput).toHaveValue(date);
}

/**
 * A DIVIDEND form on the owned asset, and its «+ New event». The form is dated today (its default)
 * unless `date` is given; the modal opens on the form's date.
 * The page is loaded after the asset exists: it keeps its assets in a session cache.
 */
async function openMiniModal(page: Page, asset: OwnedAsset, date?: string): Promise<Locator> {
    await goToTransactions(page);
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
    await selectType(page, 'DIVIDEND');
    await pickBroker(page, BROKER_NAME);
    await pickAsset(page, asset);
    if (date) await setFormDate(page, date);
    await openOptionalSection(page);
    const trigger = page.getByTestId('tx-form-event-picker-trigger');
    await expect(trigger).toBeVisible({timeout: 5_000});
    await trigger.click();
    const createNew = page.getByTestId('tx-form-event-create-new');
    await expect(createNew).toBeVisible({timeout: 3_000});
    await createNew.click();
    const modal = page.getByTestId('event-create-mini-modal');
    await expect(modal).toBeVisible({timeout: 3_000});
    // A DIVIDEND form opens the modal on DIVIDEND: its icon, not its translated label.
    await expect(modal.getByTestId('event-create-type')).toContainText('💰');
    return modal;
}

/** Type a new event's amount and notes, as a user does, and check they are held. */
async function typeNewEvent(modal: Locator, amount: string, notes: string) {
    const amountInput = modal.getByTestId('event-create-amount');
    await amountInput.fill(amount);
    const notesInput = modal.getByTestId('event-create-notes');
    await notesInput.fill(notes);
    await expect(amountInput).toHaveValue(amount);
    await expect(notesInput).toHaveValue(notes);
}

/** The panel item of one event, by the id it carries. */
function existsItem(modal: Locator, eventId: number): Locator {
    return modal.locator(`[data-testid="event-exists-item"][data-event-id="${eventId}"]`);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('«+ New event» never overwrites', () => {
    /** Assets created by the running test; deleted after it, whatever its outcome. */
    let ownedAssetIds: number[] = [];

    test.beforeEach(async ({page}) => {
        ownedAssetIds = [];
        await login(page, TEST_USER);
    });

    // afterEach, not `finally`: it runs after a timeout too, and its own error is reported beside the test's.
    test.afterEach(async ({page}) => {
        await deleteOwnedAssets(page, ownedAssetIds);
    });

    test('a new event on a date and type the asset already holds shows that event, writes nothing, and Cancel goes back to the form as typed', async ({page}) => {
        const today = await browserToday(page);
        const asset = await createOwnedAsset(page, ownedAssetIds);
        const marker = `E1b exists ${uniqueSuffix()}`;
        const [storedId] = await seedManualEvents(page, asset.id, today, [{amount: '1.25', notes: `${marker} stored`}]);
        const before = await snapshot(page, asset.id, today);

        const modal = await openMiniModal(page, asset);
        await typeNewEvent(modal, '2.00', `${marker} typed`);
        await modal.getByTestId('event-create-submit').click();

        // Before E1b: the plain upsert overwrites the stored event in place and the modal closes.
        const panel = modal.getByTestId('event-exists-panel');
        await expect(panel, 'the create is refused (EVENT_EXISTS) and the modal shows the event already there').toBeVisible({timeout: 10_000});
        const items = panel.getByTestId('event-exists-item');
        await expect(items).toHaveCount(1);
        await expect(items).toHaveAttribute('data-event-id', String(storedId));
        // A manual event can be used or edited, and carries no provider note.
        await expect(items.getByTestId('event-exists-use')).toBeVisible();
        await expect(items.getByTestId('event-exists-edit')).toBeVisible();
        await expect(items.getByTestId('event-exists-provider-note')).toHaveCount(0);
        // The form gives way to the panel and cannot be sent again from there.
        await expect(modal.getByTestId('event-create-amount')).toBeHidden();
        await expect(modal.getByTestId('event-create-notes')).toBeHidden();
        await expect(modal.getByTestId('event-create-submit')).toBeDisabled();
        expect(await snapshot(page, asset.id, today), 'a refused create writes nothing').toEqual(before);

        await panel.getByTestId('event-exists-cancel').click();
        await expect(panel).toBeHidden();
        await expect(modal.getByTestId('event-create-amount'), 'Cancel goes back to the amount as typed').toHaveValue('2.00');
        await expect(modal.getByTestId('event-create-notes'), 'and to the notes as typed').toHaveValue(`${marker} typed`);
        await expect(modal.getByTestId('event-create-submit')).toBeEnabled();
        expect(await snapshot(page, asset.id, today), 'Cancel writes nothing').toEqual(before);
    });

    test('«Use this» links the event already there and writes nothing', async ({page}) => {
        const today = await browserToday(page);
        const asset = await createOwnedAsset(page, ownedAssetIds);
        const marker = `E1b use ${uniqueSuffix()}`;
        const [storedId] = await seedManualEvents(page, asset.id, today, [{amount: '1.25', notes: `${marker} stored`}]);
        const before = await snapshot(page, asset.id, today);

        const modal = await openMiniModal(page, asset);
        await typeNewEvent(modal, '2.00', `${marker} typed`);
        await modal.getByTestId('event-create-submit').click();

        const item = existsItem(modal, storedId);
        await expect(item, 'the event already there is offered (EVENT_EXISTS)').toBeVisible({timeout: 10_000});
        await item.getByTestId('event-exists-use').click();

        await expect(modal).toBeHidden({timeout: 5_000});
        await expect(page.getByTestId('tx-form-event-picker-trigger'), 'the picker holds the event already there').toContainText(`${marker} stored`);
        expect(await snapshot(page, asset.id, today), '«Use this» writes nothing').toEqual(before);
    });

    // The stored amount comes back with its own decimals: six stay six, trailing zeros go down to two.
    for (const {stored, shown} of [
        {stored: '0.123456', shown: '0.123456'},
        {stored: '1.5', shown: '1.50'},
    ]) {
        test(`«Edit this» opens the stored event with its own values (${stored} shows ${shown}), saves it by its id, and the picker shows it as saved`, async ({page}) => {
            const today = await browserToday(page);
            const asset = await createOwnedAsset(page, ownedAssetIds);
            const marker = `E1b edit ${uniqueSuffix()}`;
            const [storedId] = await seedManualEvents(page, asset.id, today, [{amount: stored, notes: `${marker} stored`}]);

            const modal = await openMiniModal(page, asset);
            await typeNewEvent(modal, '9.99', `${marker} typed`);
            await modal.getByTestId('event-create-submit').click();
            const item = existsItem(modal, storedId);
            await expect(item, 'the event already there is offered (EVENT_EXISTS)').toBeVisible({timeout: 10_000});
            await item.getByTestId('event-exists-edit').click();

            // The form is back, holding the stored event — not what was typed.
            const amountInput = modal.getByTestId('event-create-amount');
            await expect(amountInput, 'the stored amount, its decimals kept').toHaveValue(shown);
            await expect(modal.getByTestId('event-create-notes'), 'the stored notes').toHaveValue(`${marker} stored`);
            await expect(modal.getByTestId('event-create-type'), 'the stored type (DIVIDEND, by its icon)').toContainText('💰');

            // Change the amount and the notes; six decimals must survive the save as well.
            await amountInput.fill('0.654321');
            const notesInput = modal.getByTestId('event-create-notes');
            await notesInput.fill(`${marker} edited`);
            await expect(amountInput).toHaveValue('0.654321');
            await expect(notesInput).toHaveValue(`${marker} edited`);
            const sent = page.waitForRequest(isEventsPost, {timeout: 10_000});
            await modal.getByTestId('event-create-submit').click();

            const item0 = sentItem(await sent, asset.id);
            expect(item0.mode ?? 'upsert', 'an edit is saved by its id, not created').toBe('upsert');
            expect(
                item0.events.map((e) => ({id: e.id ?? null, date: e.date, type: e.type, notes: e.notes})),
                'the edit names the stored event and carries its new notes',
            ).toEqual([{id: storedId, date: today, type: 'DIVIDEND', notes: `${marker} edited`}]);
            await expect(modal).toBeHidden({timeout: 10_000});
            // The picker fetched the day before the edit, with the stored notes: it must show the
            // event as the server now holds it, not that copy.
            const trigger = page.getByTestId('tx-form-event-picker-trigger');
            await expect(trigger, 'the picker shows the edited event as saved: its new notes').toContainText(`${marker} edited`, {timeout: 10_000});
            await expect(trigger, 'not the copy it fetched before the edit').not.toContainText(`${marker} stored`);

            const after = await dividendsOn(page, asset.id, today);
            expect(
                after.map((e) => ({id: e.id, amount: Number(e.value.amount), notes: e.notes})),
                'the same row, with the new amount and notes; no second one',
            ).toEqual([{id: storedId, amount: 0.654321, notes: `${marker} edited`}]);
        });
    }

    test('after «Edit this», the picker holds the event the server saved — not another one on the same date and type', async ({page}) => {
        // I-10 S4. Two manual DIVIDENDs share the day (two events without id on one key are both
        // stored). Re-reading the day by date and type finds the first; the save names the second.
        const today = await browserToday(page);
        const asset = await createOwnedAsset(page, ownedAssetIds);
        const marker = `E1b S4 ${uniqueSuffix()}`;
        const [firstId, secondId] = await seedManualEvents(page, asset.id, today, [
            {amount: '1.00', notes: `${marker} first`},
            {amount: '2.00', notes: `${marker} second`},
        ]);

        const modal = await openMiniModal(page, asset);
        await typeNewEvent(modal, '3.00', `${marker} typed`);
        await modal.getByTestId('event-create-submit').click();
        const panel = modal.getByTestId('event-exists-panel');
        await expect(panel, 'both events already there are offered (EVENT_EXISTS)').toBeVisible({timeout: 10_000});
        await expect.poll(async () => (await panel.getByTestId('event-exists-item').evaluateAll((items) => items.map((el) => el.getAttribute('data-event-id')))).sort()).toEqual([String(firstId), String(secondId)].sort());

        await existsItem(modal, secondId).getByTestId('event-exists-edit').click();
        const amountInput = modal.getByTestId('event-create-amount');
        const notesInput = modal.getByTestId('event-create-notes');
        await expect(amountInput).toHaveValue('2.00');
        await expect(notesInput).toHaveValue(`${marker} second`);
        await amountInput.fill('2.50');
        await notesInput.fill(`${marker} second edited`);
        await expect(amountInput).toHaveValue('2.50');
        await expect(notesInput).toHaveValue(`${marker} second edited`);
        const answered = page.waitForResponse(isEventsPostResponse, {timeout: 10_000});
        await modal.getByTestId('event-create-submit').click();

        const response = await answered;
        expect(response.status()).toBe(200);
        const result = ((await response.json()) as {results: Array<{asset_id: number; event_ids?: number[]}>}).results.find((r) => r.asset_id === asset.id);
        expect(result?.event_ids, 'the response names the row the save wrote').toEqual([secondId]);
        await expect(modal).toBeHidden({timeout: 10_000});
        // Which event first (either copy of the second reads "second"), then which copy of it.
        const trigger = page.getByTestId('tx-form-event-picker-trigger');
        await expect(trigger, 'the picker holds the edited event').toContainText(`${marker} second`);
        await expect(trigger, 'not the other one on the same date and type').not.toContainText(`${marker} first`);
        await expect(trigger, 'as saved: its new notes, not the copy fetched before the edit').toContainText(`${marker} second edited`, {timeout: 10_000});

        const after = Object.fromEntries((await dividendsOn(page, asset.id, today)).map((e) => [e.id, {amount: Number(e.value.amount), notes: e.notes}]));
        expect(after).toEqual({[firstId]: {amount: 1, notes: `${marker} first`}, [secondId]: {amount: 2.5, notes: `${marker} second edited`}});
    });

    test('a provider event on that date and type can only be used: no edit, a note says why', async ({page}) => {
        const today = await browserToday(page);
        // A sync writes no provider event dated today (see seedProviderEvent): the planned event
        // is yesterday's, and the form — hence the modal — is dated yesterday too.
        const day = shiftIso(today, -1);
        const asset = await createOwnedAsset(page, ownedAssetIds);
        const marker = `E1b provider ${uniqueSuffix()}`;
        const providerId = await seedProviderEvent(page, asset.id, day, `${marker} planned`, '0.42');
        const before = await snapshot(page, asset.id, today);

        const modal = await openMiniModal(page, asset, day);
        await typeNewEvent(modal, '0.42', `${marker} typed`);
        await modal.getByTestId('event-create-submit').click();

        // Before E1b: an upsert never touches a provider event, so it adds a manual twin beside it.
        const item = existsItem(modal, providerId);
        await expect(item, 'the provider event already there is offered (EVENT_EXISTS)').toBeVisible({timeout: 10_000});
        await expect(item.getByTestId('event-exists-use')).toBeVisible();
        await expect(item.getByTestId('event-exists-provider-note'), 'a note says why it cannot be edited here').toBeVisible();
        await expect(item.getByTestId('event-exists-edit'), 'a provider event is rewritten by every refresh: no edit').toHaveCount(0);

        await item.getByTestId('event-exists-use').click();
        await expect(modal).toBeHidden({timeout: 5_000});
        await expect(page.getByTestId('tx-form-event-picker-trigger'), 'the picker holds the provider event').toContainText(`${marker} planned`);
        expect(await snapshot(page, asset.id, today), 'no manual twin is written').toEqual(before);
    });

    test('a new event on a free date and type is sent in create mode, and the picker holds the id the server returns', async ({page}) => {
        const today = await browserToday(page);
        const asset = await createOwnedAsset(page, ownedAssetIds);
        const marker = `E1b create ${uniqueSuffix()}`;

        const modal = await openMiniModal(page, asset);
        await typeNewEvent(modal, '1.75', `${marker} new`);
        const sent = page.waitForRequest(isEventsPost, {timeout: 10_000});
        const answered = page.waitForResponse(isEventsPostResponse, {timeout: 10_000});
        await modal.getByTestId('event-create-submit').click();

        const item0 = sentItem(await sent, asset.id);
        // Before E1b: the request carries no mode, so it would overwrite a manual event on that key.
        expect(item0.mode, 'a new event is created, never upserted onto another (decision 20)').toBe('create');
        expect(item0.events.map((e) => e.id ?? null)).toEqual([null]);
        const response = await answered;
        expect(response.status()).toBe(200);
        const result = ((await response.json()) as {results: Array<{asset_id: number; event_ids?: number[]}>}).results.find((r) => r.asset_id === asset.id);

        await expect(modal).toBeHidden({timeout: 10_000});
        await expect(page.getByTestId('tx-form-event-picker-trigger')).toContainText(`${marker} new`);
        const stored = await dividendsOn(page, asset.id, today);
        expect(
            stored.map((e) => e.id),
            'one new row',
        ).toHaveLength(1);
        expect(result?.event_ids, 'the response names that row').toEqual([stored.find((e) => e.notes === `${marker} new`)?.id]);
    });

    test('a save the server refuses reads as a sentence in the error banner — never [object Object], never a raw code', async ({page}) => {
        const today = await browserToday(page);
        const asset = await createOwnedAsset(page, ownedAssetIds);
        const marker = `E1b refused ${uniqueSuffix()}`;
        const [storedId] = await seedManualEvents(page, asset.id, today, [{amount: '1.25', notes: `${marker} stored`}]);

        const modal = await openMiniModal(page, asset);
        await typeNewEvent(modal, '2.00', `${marker} typed`);
        await modal.getByTestId('event-create-submit').click();
        const item = existsItem(modal, storedId);
        await expect(item, 'the event already there is offered (EVENT_EXISTS)').toBeVisible({timeout: 10_000});
        await item.getByTestId('event-exists-edit').click();
        await expect(modal.getByTestId('event-create-notes')).toHaveValue(`${marker} stored`);

        // Meanwhile the event goes — another tab, another user. The save by id is now refused (EVENT_NOT_EDITABLE).
        const removed = await jsonFrom<{results: Array<{event_id: number; status: string}>}>(await page.request.delete(`${EVENTS_PATH}?asset_id=${asset.id}&ids=${storedId}`), 'delete the stored event behind the modal');
        expect(removed.results.find((r) => r.event_id === storedId)?.status).toBe('deleted');

        const amountInput = modal.getByTestId('event-create-amount');
        await amountInput.fill('3.00');
        await expect(amountInput).toHaveValue('3.00');
        const answered = page.waitForResponse(isEventsPostResponse, {timeout: 10_000});
        await modal.getByTestId('event-create-submit').click();
        expect((await answered).status(), 'the save by id of a deleted event is refused').toBe(400);

        const banner = modal.getByTestId('info-banner-error');
        await expect(banner).toBeVisible({timeout: 5_000});
        await expect(banner, 'a sentence, not an empty banner').toHaveText(/\S/);
        await expect(banner).not.toContainText('[object Object]');
        await expect(banner, 'never the raw code').not.toContainText(/EVENT_[A-Z]/);
        await expect(modal, 'the modal stays open: nothing was saved').toBeVisible();
        expect(await dividendsOn(page, asset.id, today), 'nothing written').toEqual([]);
    });
});
