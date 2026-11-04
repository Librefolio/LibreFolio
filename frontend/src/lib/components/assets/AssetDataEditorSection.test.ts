// @vitest-environment jsdom
/**
 * AssetDataEditorSection — the price save path, component test (Vitest + jsdom). N92 (i) with «clear» (developer's
 * decisions of 19/10).
 *
 * The section's save (`handleSave`) turns the dirty price rows into one `POST /assets/prices` body. Before N92 an erased
 * open/high/low/volume (the cell's eraser) went out as the sentinel -1, which the server read as «set NULL»; a row with
 * a close not above 0 was left out and counted in `pricesSkipped`; any other value went out as it was. So a -1 read from
 * a CSV erased the stored value, and another negative (only a CSV import can bring one: the editor's cells clamp a typed
 * value to `min: 0`) reached the server, which refused the whole save with a 422.
 *
 * The contract (N92):
 * - an erased field is sent as the text `'clear'` (and only that field);
 * - a row whose open, high, low or volume is a negative number — -1 included — is not sent: it is skipped and counted
 *   in `pricesSkipped`, like a close not above 0; 0 is a value, sent as 0.
 *
 * Driven as the user drives it: the eraser of the open cell of a stored row, or the CSV import of the editor
 * (`fx-data-import-btn`, `csv-editor-input`, `data-import-confirm`), then `asset-editor-save-btn`. `$lib/api` is the real
 * one but for the three write endpoints the section may call, recorded and answered here: the body sent is the subject.
 * The counts are read from the save's event (`assets.data.saved`, `detail`), never from the toast's words.
 *
 * The erased cell is also read on screen: it must show the cleared state (no text field), which it gets through
 * DataEditor, the component that renders the cell from the row's value. GUARD there, green today with -1; a cure that
 * coerces the row's `'clear'` to a number on the way to the cell (`Number('clear')` is NaN) turns it red.
 *
 * RED (expected failure before the cure): the erased open is sent as -1; the CSV rows with an open of -3 and a volume of
 * -1 are sent, and `pricesSkipped` is 1 instead of 3. GUARD (green before and after): a CSV row whose close is 0 is
 * skipped and counted, the sound row sent as it is, zeros included — it also proves the import harness works today.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, `front_component_unit` (action `component-unit`).
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {_ as t} from '$lib/i18n';
import {get} from 'svelte/store';
import {formatDay} from '$lib/utils/core/formatAxisDate';

const api = vi.hoisted(() => ({
    upsertPrices: vi.fn(),
    deletePrices: vi.fn(),
    upsertEvents: vi.fn(),
}));

// Typed loosely on purpose: `typeof import('$lib/api')` makes the checker expand the whole generated client type in this
// one expression, past its instantiation budget (svelte-check: «Type instantiation is excessively deep»). At run time
// nothing changes: the real module, with only the three write endpoints replaced.
vi.mock('$lib/api', async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>();
    return {
        ...actual,
        zodiosApi: {
            ...(actual.zodiosApi as object),
            upsert_prices_bulk_api_v1_assets_prices_post: api.upsertPrices,
            delete_prices_bulk_api_v1_assets_prices_delete: api.deletePrices,
            upsert_events_bulk_api_v1_assets_events_post: api.upsertEvents,
        },
    };
});

import AssetDataEditorSection from './AssetDataEditorSection.svelte';

const ASSET_ID = 92001;
/** The stored row the erasing case edits. */
const DAY = '2024-06-10';

/** A price point of the body the save sends. */
type SentPrice = {date: string; close: number; open?: unknown; high?: unknown; low?: unknown; volume?: unknown};

/** An app event as `notify()` keeps it in `window.__lf.events`. */
type AppEventLike = {seq: number; name: string; detail?: Record<string, unknown>};

/** A stored price as the price query answers it: decimals as text. */
function storedPrice(date: string, values: Record<string, string>) {
    return {date, currency: 'USD', ...values};
}

function mount() {
    const onsave = vi.fn();
    const chartData = [storedPrice(DAY, {close: '10', open: '9', high: '11', low: '8', volume: '1000'})];
    const {container} = render(AssetDataEditorSection, {props: {assetId: ASSET_ID, chartData, events: [], onsave}});
    return {onsave, container};
}

/** The editor's row of `rowId` (a price row's id is its date), or null before it is rendered. */
function rowOf(container: HTMLElement, rowId: string): HTMLElement | null {
    return container.querySelector<HTMLElement>(`tr[data-row-id="${rowId}"]`);
}

/** The cell of column `columnId` in the row of `rowId`. */
function cellOf(container: HTMLElement, rowId: string, columnId: string): HTMLElement {
    const cell = container.querySelector<HTMLElement>(`tr[data-row-id="${rowId}"] td[data-column-id="${columnId}"]`);
    if (!cell) throw new Error(`no ${columnId} cell in the row ${rowId}`);
    return cell;
}

/** The ring of app events `notify()` publishes, and its sequence. */
function appEvents(): {events: AppEventLike[]; seq: () => number} {
    return (window as unknown as {__lf: {events: AppEventLike[]; seq: () => number}}).__lf;
}

/** The `assets.data.saved` event published after `since`. */
function savedSince(since: number): AppEventLike | undefined {
    return appEvents().events.find((event) => event.seq > since && event.name === 'assets.data.saved');
}

/** The price points of the one upsert the save sent, for this unit's asset. */
function sentPrices(): SentPrice[] {
    expect(api.upsertPrices, 'the save sent one price upsert').toHaveBeenCalledTimes(1);
    const [body] = api.upsertPrices.mock.calls[0] as [Array<{asset_id: number; prices: SentPrice[]}>];
    const item = body.find((entry) => entry.asset_id === ASSET_ID);
    if (!item) throw new Error(`the upsert names no asset ${ASSET_ID}: ${JSON.stringify(body)}`);
    return item.prices;
}

/** Import `csv` through the editor's CSV import, once its `validRows` lines are all read as valid. */
async function importCsv(csv: string, validRows: number) {
    await fireEvent.click(screen.getByTestId('fx-data-import-btn'));
    const input = await screen.findByTestId('csv-editor-input');
    await fireEvent.input(input, {target: {value: csv}});
    const confirm = screen.getByTestId('data-import-confirm');
    await waitFor(() => {
        expect(confirm).toHaveAttribute('data-valid-rows', String(validRows));
        expect(confirm).toHaveAttribute('data-error-count', '0');
    });
    await fireEvent.click(confirm);
    await waitFor(() => expect(screen.queryByTestId('data-import-modal')).toBeNull());
}

/** Click Save once it is enabled, and wait for the save to finish (`onsave`). */
async function save(onsave: ReturnType<typeof vi.fn>) {
    const button = screen.getByTestId('asset-editor-save-btn');
    await waitFor(() => expect(button).toBeEnabled());
    await fireEvent.click(button);
    await waitFor(() => expect(onsave).toHaveBeenCalledTimes(1));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    api.upsertPrices.mockReset();
    api.upsertPrices.mockImplementation(async (body: Array<{asset_id: number; prices: unknown[]}>) => ({
        results: body.map((item) => ({asset_id: item.asset_id, count: item.prices.length, message: `Upserted ${item.prices.length} prices`, rejected: []})),
        success_count: body.length,
        errors: [],
        inserted_count: body.reduce((total, item) => total + item.prices.length, 0),
        updated_count: 0,
    }));
    api.deletePrices.mockReset();
    api.upsertEvents.mockReset();
});

describe('AssetDataEditorSection — an erased field is sent as clear (N92)', () => {
    it('the eraser of the open cell: the cell shows the cleared state, and the save sends open clear, that field alone', async () => {
        const {onsave, container} = mount();
        await waitFor(() => expect(rowOf(container, DAY), 'premise: the stored row is rendered').not.toBeNull());

        await fireEvent.click(within(cellOf(container, DAY, 'open')).getByTestId('erasable-cell-eraser'));
        await waitFor(() => expect(within(cellOf(container, DAY, 'open')).queryByRole('textbox'), 'GUARD: the erased cell must show its cleared state (no text field) — through DataEditor, which renders it from the row value').toBeNull());
        await save(onsave);

        const sent = sentPrices();
        expect(sent.map((point) => point.date)).toEqual([DAY]);
        expect(sent[0], 'N92: an erased open is sent as the text clear, not the -1 sentinel').toMatchObject({date: DAY, close: 10, open: 'clear'});
        const cleared = Object.entries(sent[0])
            .filter(([, value]) => value === 'clear')
            .map(([name]) => name);
        expect(cleared, 'only the erased field is sent as clear').toEqual(['open']);
    });
});

describe('AssetDataEditorSection — a row with a negative open, high, low or volume is not sent (N92)', () => {
    it('CSV rows with an open of -3 and a volume of -1 are skipped and counted, as a close of 0 is; the sound row is sent, zeros included', async () => {
        const {onsave, container} = mount();
        await waitFor(() => expect(rowOf(container, DAY), 'premise: the editor is rendered').not.toBeNull());
        const since = appEvents().seq();

        await importCsv(['date;currency;close;open;high;low;volume', '2024-06-12;USD;10;-3;;;', '2024-06-13;USD;11;;;;-1', '2024-06-14;USD;0;;;;', '2024-06-15;USD;12;0;;;0'].join('\n'), 4);
        await save(onsave);

        const sent = sentPrices();
        expect(
            sent.map((point) => point.date),
            'N92: a row with a negative open, high, low or volume (-1 included) is not sent',
        ).toEqual(['2024-06-15']);
        expect(sent[0]).toMatchObject({date: '2024-06-15', close: 12, open: 0, volume: 0});
        expect(savedSince(since)?.detail, 'N92: the two rows with a negative value are counted as skipped, with the close of 0').toMatchObject({pricesSkipped: 3, pricesSaved: 1});
    });

    it('GUARD: a CSV row whose close is 0 is skipped and counted, the sound row sent as it is, zeros included', async () => {
        const {onsave, container} = mount();
        await waitFor(() => expect(rowOf(container, DAY), 'premise: the editor is rendered').not.toBeNull());
        const since = appEvents().seq();

        await importCsv(['date;currency;close;open;high;low;volume', '2024-06-14;USD;0;;;;', '2024-06-15;USD;12;0;13;11;0'].join('\n'), 2);
        await save(onsave);

        const sent = sentPrices();
        expect(sent.map((point) => point.date)).toEqual(['2024-06-15']);
        expect(sent[0]).toMatchObject({date: '2024-06-15', close: 12, open: 0, high: 13, low: 11, volume: 0});
        expect(savedSince(since)?.detail).toMatchObject({pricesSkipped: 1, pricesSaved: 1});
    });
});

describe('AssetDataEditorSection — the events import reads the source column (W-B16, lot X6-3)', () => {
    const FILE = ['date;currency;type;amount;notes;source', '2024-06-20;USD;DIVIDEND;1.25;;PROVIDER', '2024-06-21;USD;DIVIDEND;2.5;;MANUAL', '2024-06-22;USD;INTEREST;0.4;;PROVIDER'].join('\n');

    /** The section on its Events tab, the events import opened and the file imported (all three lines valid). */
    async function importEvents(props: {hasProvider?: boolean}) {
        const {container} = render(AssetDataEditorSection, {props: {assetId: ASSET_ID, chartData: [], events: [], onsave: vi.fn(), ...props}});
        await fireEvent.click(await screen.findByTestId('asset-editor-events-tab'));
        await importCsv(FILE, 3);
        return container;
    }

    it('an asset with a provider: the PROVIDER lines are left out and counted in one warning, the MANUAL line is added', async () => {
        const warning = vi.spyOn(toasts, 'warning');
        const container = await importEvents({hasProvider: true});

        await waitFor(() => expect(rowOf(container, '2024-06-21'), 'the MANUAL line is added').not.toBeNull());
        expect(rowOf(container, '2024-06-20'), 'a PROVIDER line is not added: the provider writes it').toBeNull();
        expect(rowOf(container, '2024-06-22')).toBeNull();
        expect(warning, 'the two left out are told once').toHaveBeenCalledTimes(1);
        expect(String(warning.mock.calls[0][0]), 'the warning counts them').toContain('2');
        warning.mockRestore();
    });

    it('an asset without a provider: every line is added, the PROVIDER ones as manual events, with no warning', async () => {
        const warning = vi.spyOn(toasts, 'warning');
        const container = await importEvents({hasProvider: false});

        await waitFor(() => expect(rowOf(container, '2024-06-21')).not.toBeNull());
        expect(rowOf(container, '2024-06-20'), 'nothing else will write it: it is added').not.toBeNull();
        expect(rowOf(container, '2024-06-22')).not.toBeNull();
        expect(warning).not.toHaveBeenCalled();
        warning.mockRestore();
    });
});

describe('AssetDataEditorSection — a save that stops after a write says so, and names a date as the interface writes it (X-R39, W-B27; lot X6-5)', () => {
    /** A refused events save, as the API client throws it: a 400 with the coded detail. */
    function keyConflict(date: string) {
        return {response: {status: 400, data: {detail: {error_code: 'EVENT_KEY_CONFLICT', message: 'two manual events', params: {date, type: 'DIVIDEND'}}}}};
    }

    /** The section with a price line (Prices tab) and an event line (Events tab) imported, ready to save. */
    async function dirtyPriceAndEvent() {
        const onsave = vi.fn();
        render(AssetDataEditorSection, {props: {assetId: ASSET_ID, chartData: [], events: [], onsave}});
        await importCsv(['date;currency;close', '2024-06-12;USD;10'].join('\n'), 1);
        await fireEvent.click(await screen.findByTestId('asset-editor-events-tab'));
        await importCsv(['date;currency;type;amount', '2024-06-21;USD;DIVIDEND;2.5'].join('\n'), 1);
        return onsave;
    }

    it('the prices were written and the events refused: the error says the prices are already saved', async () => {
        api.upsertEvents.mockRejectedValue(keyConflict('2024-06-21'));
        await dirtyPriceAndEvent();
        const since = appEvents().seq();

        await fireEvent.click(screen.getByTestId('asset-editor-save-btn'));

        const error = await screen.findByTestId('asset-editor-error');
        expect(error.textContent, 'X-R39: the prices already written are named').toContain(get(t)('dataEditor.savePartial', {values: {saved: 1, deleted: 0}}));
        const failed = appEvents().events.find((event) => event.seq > since && event.name === 'assets.data.saveFailed');
        expect(failed?.detail, 'the event carries what was written').toMatchObject({pricesSaved: 1, pricesDeleted: 0});
    });

    it('GUARD: the first request refused, nothing written: no partial sentence', async () => {
        api.upsertPrices.mockRejectedValue({response: {status: 500, data: {detail: 'boom'}}});
        await dirtyPriceAndEvent();

        await fireEvent.click(screen.getByTestId('asset-editor-save-btn'));

        const error = await screen.findByTestId('asset-editor-error');
        expect(error.textContent).not.toContain(get(t)('dataEditor.savePartial', {values: {saved: 1, deleted: 0}}));
    });

    it('a refused event names its date as the interface writes a date (W-B27), not as ISO', async () => {
        api.upsertEvents.mockRejectedValue(keyConflict('2024-06-21'));
        await dirtyPriceAndEvent();

        await fireEvent.click(screen.getByTestId('asset-editor-save-btn'));

        const error = await screen.findByTestId('asset-editor-error');
        expect(error.textContent).toContain(formatDay('2024-06-21'));
        expect(error.textContent).not.toContain('2024-06-21');
    });
});
