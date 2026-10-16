/**
 * asset-events-owned.ts — data a spec of the asset events editor owns, and the way into that editor.
 *
 * Shared by asset-event-editor-save.spec.ts and asset-event-delete.spec.ts (W-B29): a spec never
 * imports another spec, so what both need lives here. Moved unchanged from asset-event-editor-save.spec.ts.
 * asset-data-editor.spec.ts uses the asset too (W-B43), with closes of its own choosing.
 *
 * Data. A test creates a USD asset of its own — two closes, because only a chart with prices offers
 * the editor button — its own events, noted with markers only it writes, and, for an event in use, a
 * broker of its own with the one DIVIDEND that realises it. Afterwards `deleteOwned` removes the
 * brokers first (with `force`, which takes their transactions), then the assets with their prices and
 * events. Nothing here reads or writes the shared mock data.
 */
import {expect, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {API_BASE} from './assets-helpers';

/** The path of an events save (POST) and of the old delete (DELETE): the same, told apart by the method. */
export const EVENTS_PATH = `${API_BASE}/assets/events`;

export type OwnedAsset = {id: number; name: string};
/** One stored close of an owned asset. */
export type OwnedClose = {date: string; close: number};
/** What one test created, deleted afterwards in FK-safe order. */
export type Owned = {assetIds: number[]; brokerIds: number[]};
export type StoredEvent = {id: number; date: string; type: string; value: {code: string; amount: string}; notes: string | null; is_auto: boolean};
type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};

export async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/**
 * A USD asset of this test's own, with two closes so the chart — and its editor button — is drawn.
 * `closes` replaces those two when the prices themselves are the subject (the stale rows of
 * asset-data-editor.spec.ts); `label` names the asset after its test, for whoever reads a leftover.
 */
export async function createOwnedAsset(page: Page, owned: Owned, options: {label?: string; closes?: OwnedClose[]} = {}): Promise<OwnedAsset> {
    const {
        label = 'E2E event editor',
        closes = [
            {date: daysAgoIso(30), close: 10},
            {date: daysAgoIso(10), close: 11},
        ],
    } = options;
    const name = `${label} ${uniqueSuffix()}`;
    const response = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'USD', asset_type: 'STOCK'}]});
    expect(response.ok(), `create the owned asset: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const body = (await response.json()) as {results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>};
    const created = body.results.find((item) => item.display_name === name);
    if (typeof created?.asset_id === 'number') owned.assetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`The owned asset ${name} was not created: ${created?.message ?? 'missing result'}`);
    await jsonFrom(await page.request.post(`${API_BASE}/assets/prices`, {data: [{asset_id: created.asset_id, prices: closes}]}), `store ${closes.length} closes on the owned asset`);
    return {id: created.asset_id, name};
}

/**
 * A DIVIDEND on a broker of this test's own that realises `eventId`: what makes the event "in use".
 * The broker is recorded for cleanup before anything about the result is checked.
 */
export async function linkDividend(page: Page, owned: Owned, assetId: number, eventId: number, date: string): Promise<number> {
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
export async function deleteOwned(page: Page, owned: Owned): Promise<void> {
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
export async function seedEvents(page: Page, assetId: number, events: Array<{date: string; type: string; amount: string; notes: string}>): Promise<number[]> {
    await jsonFrom(await page.request.post(EVENTS_PATH, {data: [{asset_id: assetId, events: events.map(({date, type, amount, notes}) => ({date, type, value: {code: 'USD', amount}, notes}))}]}), 'seed the manual events');
    const stored = await storedEvents(page, assetId);
    return events.map(({notes}) => {
        const matches = stored.filter((e) => e.notes === notes);
        if (matches.length !== 1) throw new Error(`Expected one event noted "${notes}", found ${matches.length}: ${JSON.stringify(stored)}`);
        return matches[0].id;
    });
}

/** Every event of the owned asset in the window the tests write in. */
export async function storedEvents(page: Page, assetId: number): Promise<StoredEvent[]> {
    const body = await jsonFrom<{items: Array<{asset_id: number; events: StoredEvent[]}>}>(await page.request.post(`${EVENTS_PATH}/query`, {data: [{asset_id: assetId, date_range: {start: daysAgoIso(60), end: todayIso()}}]}), `query the events of asset ${assetId}`);
    return body.items.find((item) => item.asset_id === assetId)?.events ?? [];
}

/** id → what a save would change. */
export async function snapshot(page: Page, assetId: number): Promise<Record<number, string>> {
    return Object.fromEntries((await storedEvents(page, assetId)).map((e) => [e.id, `${e.date} ${e.type} ${Number(e.value.amount)} ${e.value.code} ${e.notes ?? ''}`]));
}

/** The asset page on a range holding the events, and its editor on the Events tab. */
export async function openEventsEditor(page: Page, asset: OwnedAsset): Promise<Locator> {
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
export function eventRow(panel: Locator, eventId: number): Locator {
    return panel.locator(`tbody tr[data-row-id="${eventId}"]`);
}

/** Mark a saved event's row deleted, through its row action. */
export async function markDeleted(page: Page, panel: Locator, eventId: number) {
    await panel.getByTestId(`row-actions-${eventId}`).click();
    const deleteAction = page.getByTestId('context-menu-action-delete');
    await deleteAction.click();
    await expect(deleteAction).toBeHidden();
}
