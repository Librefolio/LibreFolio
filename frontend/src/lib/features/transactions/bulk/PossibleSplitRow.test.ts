// @vitest-environment jsdom
/**
 * PossibleSplitRow — component test (Vitest + jsdom). W-B87, the Bulk's «possible stock split» banner.
 *
 * An importer enters a stock split as an incoming ADJUSTMENT at no cost and asks the Bulk to link it to a SPLIT event
 * (`possible_split`, see bulkTodos.ts). One row of the banner is one such ADJUSTMENT. Props in, three callbacks out:
 *
 *   entry    — the row, as `possibleSplitEntries` builds it (tempId, rowId, rowNumber, assetId, date, ticker, addedQuantity,
 *              isin, and the ratio the plugin worked out: ratio, suggestedRatio, roundingDelta, heldBefore)
 *   onGoto   — `possible-split-goto`: leads to the row, called with `entry.rowId` (the visible row of a pair)
 *   onCreate — `possible-split-create`: «create the SPLIT event and link it», called with the entry
 *   onLink   — `possible-split-link` opens, and closes again, an inline AssetEventPicker for the asset on the row's date;
 *              the event it answers is handed over; its «no event» answer is not
 *
 * The two actions exist only when the asset is resolved (`assetId` a number above 0): an unresolved asset has no events to
 * link or to create on, and says so (`possible-split-asset-needed`) instead. The ratio the plugin worked out is shown
 * (`possible-split-ratio`) when there is one, and a rounding warning (`possible-split-rounding`, values `ratio` and
 * `delta`) only when the shares held do not give the added ones exactly.
 *
 * On text. `$lib/i18n` is replaced by a translator that renders a key with its values (`key(name=value)`), so a label is
 * proved by its KEY, never by a translation; every control is found by `data-testid`. The picker is the shared stand-in
 * `$test/harness/AssetEventPickerStub.svelte`: it publishes the props it was given and answers event 555, or none.
 *
 * The component is loaded lazily: while it does not exist each test fails on its own, naming the file.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import type {Component} from 'svelte';
import {readable, writable} from 'svelte/store';
import {fireEvent, render, screen} from '$test/component';

vi.mock('$lib/i18n', () => {
    const shown = (key: string, options?: {values?: Record<string, unknown>}) => {
        const values = options?.values;
        if (!values) return key;
        const listed = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return `${key}(${listed.join(', ')})`;
    };
    const translator = readable(shown);
    return {_: translator, t: translator, locale: writable('en')};
});
vi.mock('$lib/features/transactions/events/AssetEventPicker.svelte', async () => ({default: (await import('$test/harness/AssetEventPickerStub.svelte')).default}));

/** The entry as `possibleSplitEntries` hands it over (contract of W-B87). */
interface Entry {
    tempId: string;
    rowId: string;
    rowNumber: string;
    assetId: number | null;
    date: string;
    ticker: string;
    addedQuantity: string;
    isin: string | null;
    ratio: string | null;
    suggestedRatio: string | null;
    roundingDelta: string | null;
    heldBefore: string | null;
}

const PICKED_EVENT_ID = 555;
const KEY = 'transactions.bulk.possibleSplit';

const MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./PossibleSplitRow.svelte');

async function loadRow(): Promise<Component<Record<string, unknown>>> {
    const load = MODULES['./PossibleSplitRow.svelte'];
    if (!load) throw new Error('PossibleSplitRow.svelte cannot be found — not implemented yet (W-B87)');
    return (await load()).default;
}

function entryOf(overrides: Partial<Entry> = {}): Entry {
    return {
        tempId: 'tmp-4',
        rowId: 'tmp-4',
        rowNumber: '12',
        assetId: 7,
        date: '2022-08-25',
        ticker: 'TSLA',
        addedQuantity: '0.16431924',
        isin: null,
        ratio: null,
        suggestedRatio: null,
        roundingDelta: null,
        heldBefore: null,
        ...overrides,
    };
}

const onCreate = vi.fn<(entry: Entry) => void>();
const onLink = vi.fn<(eventId: number) => void>();
const onGoto = vi.fn<(rowId: string) => void>();

async function mountRow(entry: Entry) {
    const Row = await loadRow();
    return render(Row, {props: {entry, onCreate, onLink, onGoto}});
}

beforeEach(() => {
    onCreate.mockReset();
    onLink.mockReset();
    onGoto.mockReset();
});

describe('PossibleSplitRow — what the row says', () => {
    it('is one `possible-split-row` that names its visible row in data-row-id', async () => {
        await mountRow(entryOf({tempId: 'hidden-half', rowId: 'shown-half'}));

        expect(screen.getByTestId('possible-split-row')).toHaveAttribute('data-row-id', 'shown-half');
    });

    it('shows the row number, the ticker, the shares added and the date', async () => {
        await mountRow(entryOf({rowNumber: '12', ticker: 'TSLA', addedQuantity: '0.16431924', date: '2022-08-25'}));

        const text = screen.getByTestId('possible-split-row').textContent ?? '';
        expect(text).toContain('#12');
        expect(text).toContain('TSLA');
        expect(text, 'the shares added, their digits').toContain('0.16431924');
        expect(text, 'the date of the row, in whatever format').toContain('2022');
    });

    it('words the added shares through the quantityAdded key', async () => {
        await mountRow(entryOf());

        expect(screen.getByTestId('possible-split-row').textContent ?? '').toContain(`${KEY}.quantityAdded`);
    });
});

describe('PossibleSplitRow — the ratio the plugin worked out', () => {
    it('shows no ratio and no warning when the file had no history', async () => {
        await mountRow(entryOf());

        expect(screen.queryByTestId('possible-split-ratio')).toBeNull();
        expect(screen.queryByTestId('possible-split-rounding')).toBeNull();
    });

    it('shows the ratio when there is one, and no warning when it is exact', async () => {
        await mountRow(entryOf({heldBefore: '0.08215962', ratio: '3', suggestedRatio: '3', roundingDelta: null}));

        expect(screen.getByTestId('possible-split-ratio').textContent ?? '', 'the ratio, its digits').toContain('3');
        expect(screen.queryByTestId('possible-split-rounding'), 'an exact ratio has nothing to warn about').toBeNull();
    });

    it('warns about a rounding with the rounding key and the difference, when the delta is not null', async () => {
        await mountRow(entryOf({heldBefore: '10', ratio: '2.97', suggestedRatio: '3', roundingDelta: '0.2'}));

        const warning = screen.getByTestId('possible-split-rounding');
        const text = warning.textContent ?? '';
        expect(text).toContain(`${KEY}.rounding`);
        expect(text, 'the delta is a value of the message').toContain('delta=0.2');
        expect(text, 'and so is a ratio').toMatch(/ratio=\S+/);
        expect(screen.getByTestId('possible-split-ratio')).toBeInTheDocument();
    });
});

describe('PossibleSplitRow — go to the row', () => {
    it('`possible-split-goto` hands the visible row id to onGoto, with an unresolved asset too', async () => {
        await mountRow(entryOf({tempId: 'hidden-half', rowId: 'shown-half'}));
        await fireEvent.click(screen.getByTestId('possible-split-goto'));
        expect(onGoto).toHaveBeenCalledExactlyOnceWith('shown-half');
        expect(onCreate).not.toHaveBeenCalled();
        expect(onLink).not.toHaveBeenCalled();
    });

    it('is there when the asset is not resolved', async () => {
        await mountRow(entryOf({assetId: null}));
        expect(screen.getByTestId('possible-split-goto')).toBeInTheDocument();
    });
});

describe('PossibleSplitRow — a resolved asset: create the event, or link one', () => {
    it('offers create and link, and not the «asset needed» line', async () => {
        await mountRow(entryOf({assetId: 7}));

        expect(screen.getByTestId('possible-split-create')).toBeInTheDocument();
        expect(screen.getByTestId('possible-split-link')).toBeInTheDocument();
        expect(screen.queryByTestId('possible-split-asset-needed')).toBeNull();
    });

    it('«create» hands the entry to onCreate, once, and links nothing itself', async () => {
        const entry = entryOf({ratio: '3', suggestedRatio: '3'});
        await mountRow(entry);

        await fireEvent.click(screen.getByTestId('possible-split-create'));

        expect(onCreate).toHaveBeenCalledExactlyOnceWith(entry);
        expect(onLink).not.toHaveBeenCalled();
    });

    it('«link» opens an inline picker for the asset on the row date, and a second click closes it', async () => {
        await mountRow(entryOf({assetId: 7, date: '2022-08-25'}));
        expect(screen.queryByTestId('event-picker-stub'), 'closed at first').toBeNull();

        await fireEvent.click(screen.getByTestId('possible-split-link'));

        const picker = screen.getByTestId('event-picker-stub');
        expect(picker).toHaveAttribute('data-asset-id', '7');
        expect(picker).toHaveAttribute('data-tx-date', '2022-08-25');
        expect(picker, 'no event is chosen yet').toHaveAttribute('data-value', '');

        await fireEvent.click(screen.getByTestId('possible-split-link'));
        expect(screen.queryByTestId('event-picker-stub'), 'closed again').toBeNull();
    });

    it('hands the picked event to onLink', async () => {
        await mountRow(entryOf());
        await fireEvent.click(screen.getByTestId('possible-split-link'));

        await fireEvent.click(screen.getByTestId('event-picker-stub-pick'));

        expect(onLink).toHaveBeenCalledExactlyOnceWith(PICKED_EVENT_ID);
        expect(onCreate).not.toHaveBeenCalled();
    });

    it('does not call onLink when the picker answers «no event»', async () => {
        await mountRow(entryOf());
        await fireEvent.click(screen.getByTestId('possible-split-link'));

        await fireEvent.click(screen.getByTestId('event-picker-stub-clear'));

        expect(onLink).not.toHaveBeenCalled();
    });
});

describe('PossibleSplitRow — an asset still to resolve', () => {
    it.each([
        ['null', null],
        ['0', 0],
        ['a negative placeholder id', -3],
    ])('assetId %s: no create, no link, no picker, and the line that says why', async (_label, assetId) => {
        await mountRow(entryOf({assetId}));

        expect(screen.queryByTestId('possible-split-create')).toBeNull();
        expect(screen.queryByTestId('possible-split-link')).toBeNull();
        expect(screen.queryByTestId('event-picker-stub')).toBeNull();
        expect(screen.getByTestId('possible-split-asset-needed').textContent ?? '').toContain(`${KEY}.assetNeeded`);
    });
});
