// @vitest-environment jsdom
/**
 * DataTableColumnFilter — component test (Vitest + jsdom).
 *
 * This is the filter popover every DataTable in the app opens from a column
 * header, so a regression here is a regression on assets, transactions, files,
 * brokers and FX at once. Reaching it through Playwright means picking one page
 * that happens to expose the mode you want to exercise — and three of the seven
 * modes (`size`, `multi-enum`, `currency-stack`) live on pages where setting up
 * the data is most of the work. Here every mode is one prop.
 *
 * The contract under test is narrow and entirely observable: the component owns
 * no state that outlives the popover, it hands the parent a `FilterValue | null`
 * through `onApply`. So the assertions are on **what the parent receives**, not
 * on what the popover looks like. The one recurring subtlety is that `null` is a
 * meaningful answer — "the user's input describes no restriction" — and several
 * paths reach it in ways that are easy to break silently (a full enum selection,
 * a range that spans the whole column, a blank query).
 *
 * What it deliberately does NOT assert:
 *   - translated text. Labels come from the catalogue in four languages; every
 *     control here is addressed by `data-testid`, and the values compared are
 *     the ones the test itself passed in as props.
 *   - CSS classes. The checked state of an enum row is published as
 *     `data-checked`; `.enum-checkbox.checked` exists for styling and is left
 *     to the E2E that already uses it.
 *   - the `date` mode's editing model. The filter's own share of it is three
 *     lines of pass-through; the parsing, the arrow stepping and the display
 *     format all belong to `DateRangePicker` (1400+ lines) and to
 *     `parseTypedDate`, which has its own unit tests. Only the pass-through is
 *     covered below.
 *   - the popover's fixed positioning. It is arithmetic on
 *     `getBoundingClientRect`, and jsdom reports zeroes for every rect, so any
 *     assertion on it would be measuring the absence of a layout engine.
 */
import {describe, expect, it, vi} from 'vitest';
import type {Mock} from 'vitest';
import type {ComponentProps} from 'svelte';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import DataTableColumnFilter from './DataTableColumnFilter.svelte';
import type {EnumOption, FilterValue} from './types';

/** Options with a count, a hidden `searchText` and a plain one, to tell the three apart. */
const OPTIONS: EnumOption[] = [
    {value: 'a', label: 'Apple', count: 3, searchText: 'US0378331005'},
    {value: 'b', label: 'Banana', count: 1},
    {value: 'c', label: 'Cherry'},
];

const TEN_MB = 10 * 1024 * 1024;

function mount(props: Omit<ComponentProps<typeof DataTableColumnFilter>, 'onApply' | 'onClose'>) {
    const onApply = vi.fn();
    const onClose = vi.fn();
    const utils = render(DataTableColumnFilter, {...props, onApply, onClose});
    return {onApply, onClose, ...utils};
}

/** What the parent was handed last. `undefined` means it was never called at all. */
function lastFilter(onApply: Mock): FilterValue | null | undefined {
    return onApply.mock.calls.at(-1)?.[0];
}

/**
 * Commits a value into a bound field.
 *
 * Two events, because they do two different things: Svelte's `bind:value` listens
 * on `input`, while the component's own handler runs on `change`. Firing only the
 * second would run the handler against the previous value — a test that passes
 * while proving the opposite of what it claims.
 */
async function commit(el: HTMLElement, value: string) {
    await fireEvent.input(el, {target: {value}});
    await fireEvent.change(el);
}

/** Picks an option in a `<select>`: the binding and the handler both run on `change`. */
async function choose(el: HTMLElement, value: string) {
    await fireEvent.change(el, {target: {value}});
}

describe('DataTableColumnFilter', () => {
    it('publishes the mode it is rendering', async () => {
        await setupI18n();
        mount({type: 'multi-enum', enumOptions: OPTIONS});

        expect(screen.getByTestId('column-filter')).toHaveAttribute('data-filter-type', 'multi-enum');
    });

    describe('text', () => {
        it('applies the trimmed query after the debounce', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'text'});

            await commit(screen.getByTestId('filter-text-input'), '  hello  ');

            // 300 ms debounce: polled, never slept on.
            await waitFor(() => expect(onApply).toHaveBeenCalledWith({type: 'text', value: 'hello', matchMode: 'contains'}), {timeout: 3_000});
        });

        it('treats a whitespace-only query as no restriction', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'text', initialValue: {type: 'text', value: 'hello', matchMode: 'contains'}});

            await commit(screen.getByTestId('filter-text-input'), '   ');

            await waitFor(() => expect(onApply).toHaveBeenCalledWith(null), {timeout: 3_000});
        });

        it('re-applies immediately when the match mode changes', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'text', initialValue: {type: 'text', value: 'hello', matchMode: 'contains'}});

            await choose(screen.getByTestId('filter-text-match-mode'), 'endsWith');

            // No debounce on this path: picking a mode is an explicit decision.
            expect(lastFilter(onApply)).toEqual({type: 'text', value: 'hello', matchMode: 'endsWith'});
        });

        it('drops the filter at once from the inline clear button', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'text', initialValue: {type: 'text', value: 'hello', matchMode: 'startsWith'}});

            await fireEvent.click(screen.getByTestId('filter-text-clear'));

            expect(lastFilter(onApply)).toBeNull();
            expect(screen.getByTestId('filter-text-input')).toHaveValue('');
        });
    });

    describe('number', () => {
        it('reports only the bound the user actually moved', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'number', numberMin: 0, numberMax: 100});

            await commit(screen.getByTestId('filter-number-min'), '10');

            // `max` is absent, not 100: the column's own maximum restricts nothing.
            expect(lastFilter(onApply)).toEqual({type: 'number', min: 10});
        });

        it('puts a reversed pair back in order instead of matching nothing', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'number', numberMin: 0, numberMax: 100});

            await commit(screen.getByTestId('filter-number-min'), '10');
            await commit(screen.getByTestId('filter-number-max'), '5');

            expect(lastFilter(onApply)).toEqual({type: 'number', min: 5, max: 10});
            // The two fields are repainted too, so the user sees the range they meant.
            expect(screen.getByTestId('filter-number-min')).toHaveValue(5);
            expect(screen.getByTestId('filter-number-max')).toHaveValue(10);
        });

        it('stops filtering once the range spans the whole column again', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'number', numberMin: 0, numberMax: 100});

            await commit(screen.getByTestId('filter-number-min'), '10');
            expect(lastFilter(onApply)).not.toBeNull();

            await commit(screen.getByTestId('filter-number-min'), '0');
            expect(lastFilter(onApply)).toBeNull();
        });

        it('rounds to whole numbers on an integer column', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'number', numberMin: 0, numberMax: 100, integerOnly: true});

            const min = screen.getByTestId('filter-number-min');
            expect(min).toHaveAttribute('step', '1');

            await commit(min, '10.6');

            expect(lastFilter(onApply)).toEqual({type: 'number', min: 11});
            expect(min).toHaveValue(11);
        });

        it('snaps the slider to the exact bound near the edge', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'number', numberMin: 0, numberMax: 100});
            const slider = screen.getByTestId('filter-number-slider-min');

            // Mid-track: an ordinary value, and the number field follows the handle.
            await fireEvent.input(slider, {target: {value: '50'}});
            expect(lastFilter(onApply)).toEqual({type: 'number', min: 50});
            expect(screen.getByTestId('filter-number-min')).toHaveValue(50);

            // Within the snap threshold of the left edge: the value becomes the exact
            // column minimum, which by definition restricts nothing. Without the snap
            // the user could never quite switch the filter off by dragging.
            await fireEvent.input(slider, {target: {value: '2'}});
            expect(lastFilter(onApply)).toBeNull();
        });
    });

    describe('size', () => {
        it('converts the chosen unit into bytes', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'size', numberMin: 0, numberMax: TEN_MB});

            await commit(screen.getByTestId('filter-size-min'), '5');
            await choose(screen.getByTestId('filter-size-min-unit'), 'MB');

            expect(lastFilter(onApply)).toEqual({type: 'size', minBytes: 5 * 1024 * 1024});
        });

        it('reorders crossed bounds and repaints both fields with their units', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'size', numberMin: 0, numberMax: TEN_MB});

            await commit(screen.getByTestId('filter-size-min'), '5');
            await choose(screen.getByTestId('filter-size-min-unit'), 'MB');
            await commit(screen.getByTestId('filter-size-max'), '1');
            await choose(screen.getByTestId('filter-size-max-unit'), 'MB');

            expect(lastFilter(onApply)).toEqual({type: 'size', minBytes: 1024 * 1024, maxBytes: 5 * 1024 * 1024});
            expect(screen.getByTestId('filter-size-min')).toHaveValue(1);
            expect(screen.getByTestId('filter-size-max')).toHaveValue(5);
            // The unit boxes swap with the numbers — otherwise "1" would read as 1 B.
            expect(screen.getByTestId('filter-size-min-unit')).toHaveValue('MB');
            expect(screen.getByTestId('filter-size-max-unit')).toHaveValue('MB');
        });
    });

    describe('enum', () => {
        it('renders one row per option and publishes its checked state', async () => {
            await setupI18n();
            mount({type: 'enum', enumOptions: OPTIONS, initialValue: {type: 'enum', selected: ['b']}});

            expect(screen.getByTestId('filter-enum-option-a')).toHaveAttribute('data-checked', 'false');
            expect(screen.getByTestId('filter-enum-option-b')).toHaveAttribute('data-checked', 'true');
            expect(screen.getByTestId('filter-enum-option-c')).toHaveAttribute('data-checked', 'false');
            // The count the parent computed is shown; the option that has none shows none.
            expect(screen.getByTestId('filter-enum-option-a')).toHaveTextContent('3');
        });

        it('accumulates the ticked values', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'enum', enumOptions: OPTIONS});

            await fireEvent.click(screen.getByTestId('filter-enum-option-a'));
            expect(lastFilter(onApply)).toEqual({type: 'enum', selected: ['a']});

            await fireEvent.click(screen.getByTestId('filter-enum-option-c'));
            expect(lastFilter(onApply)).toEqual({type: 'enum', selected: ['a', 'c']});

            // Ticking twice unticks: the row is a toggle, not an add button.
            await fireEvent.click(screen.getByTestId('filter-enum-option-a'));
            expect(lastFilter(onApply)).toEqual({type: 'enum', selected: ['c']});
        });

        it('treats a full selection as no filter at all', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'enum', enumOptions: OPTIONS});

            await fireEvent.click(screen.getByTestId('filter-enum-select-all'));

            // Every value passes, so the column is unrestricted — sending the full list
            // instead would make every row re-check a condition it always satisfies.
            expect(lastFilter(onApply)).toBeNull();
            expect(screen.getByTestId('filter-enum-option-a')).toHaveAttribute('data-checked', 'true');
        });

        it('limits select-all to what the search left visible', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'enum', enumOptions: OPTIONS});

            await fireEvent.input(screen.getByTestId('filter-enum-search'), {target: {value: 'apple'}});
            await fireEvent.click(screen.getByTestId('filter-enum-select-all'));

            expect(lastFilter(onApply)).toEqual({type: 'enum', selected: ['a']});
        });

        it('searches the hidden search text as well as the label', async () => {
            await setupI18n();
            mount({type: 'enum', enumOptions: OPTIONS});

            // 'US0378331005' is an ISIN attached to Apple and never rendered.
            await fireEvent.input(screen.getByTestId('filter-enum-search'), {target: {value: 'US03'}});

            expect(screen.getByTestId('filter-enum-option-a')).toBeInTheDocument();
            expect(screen.queryByTestId('filter-enum-option-b')).toBeNull();
            expect(screen.queryByTestId('filter-enum-option-c')).toBeNull();
        });

        it('says the search matched nothing instead of showing a blank list', async () => {
            await setupI18n();
            mount({type: 'enum', enumOptions: OPTIONS});

            await fireEvent.input(screen.getByTestId('filter-enum-search'), {target: {value: 'zzz'}});

            expect(screen.getByTestId('filter-enum-empty')).toBeInTheDocument();
            expect(screen.queryByTestId('filter-enum-option-a')).toBeNull();
        });

        it('clears the selection from clear-all', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'enum', enumOptions: OPTIONS, initialValue: {type: 'enum', selected: ['a', 'b']}});

            await fireEvent.click(screen.getByTestId('filter-enum-clear-all'));

            expect(lastFilter(onApply)).toBeNull();
            expect(screen.getByTestId('filter-enum-option-a')).toHaveAttribute('data-checked', 'false');
        });
    });

    describe('multi-enum', () => {
        it('keeps a full selection as a filter, unlike enum', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'multi-enum', enumOptions: OPTIONS});

            await fireEvent.click(screen.getByTestId('filter-multi-enum-select-all'));

            // The semantics differ on purpose: a multi-enum cell holds a *set* of
            // values, so "all of these" is not the same statement as "anything".
            // A row whose set is empty passes the first and fails the second.
            expect(lastFilter(onApply)).toEqual({type: 'multi-enum', selected: ['a', 'b', 'c']});
        });

        it('publishes each toggled value and falls back to null when emptied', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'multi-enum', enumOptions: OPTIONS});

            await fireEvent.click(screen.getByTestId('filter-multi-enum-option-b'));
            expect(lastFilter(onApply)).toEqual({type: 'multi-enum', selected: ['b']});
            expect(screen.getByTestId('filter-multi-enum-option-b')).toHaveAttribute('data-checked', 'true');

            await fireEvent.click(screen.getByTestId('filter-multi-enum-clear-all'));
            expect(lastFilter(onApply)).toBeNull();
        });

        it('says the search matched nothing instead of showing a blank list', async () => {
            await setupI18n();
            mount({type: 'multi-enum', enumOptions: OPTIONS});

            await fireEvent.input(screen.getByTestId('filter-multi-enum-search'), {target: {value: 'zzz'}});

            expect(screen.getByTestId('filter-multi-enum-empty')).toBeInTheDocument();
        });

        it('searches the hidden search text as well as the label, exactly like enum', async () => {
            await setupI18n();
            mount({type: 'multi-enum', enumOptions: OPTIONS});

            // 'US0378331005' is an ISIN attached to Apple and never rendered — the same case the
            // enum branch covers at line ~275. A multi-enum that matched the label alone left the
            // box looking live while filtering nothing the user typed into it.
            await fireEvent.input(screen.getByTestId('filter-multi-enum-search'), {target: {value: 'US03'}});

            expect(screen.getByTestId('filter-multi-enum-option-a')).toBeInTheDocument();
            expect(screen.queryByTestId('filter-multi-enum-option-b')).toBeNull();
            expect(screen.queryByTestId('filter-multi-enum-option-c')).toBeNull();
        });

        it('limits select-all to what the search left visible, like enum', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'multi-enum', enumOptions: OPTIONS});

            await fireEvent.input(screen.getByTestId('filter-multi-enum-search'), {target: {value: 'apple'}});
            await fireEvent.click(screen.getByTestId('filter-multi-enum-select-all'));

            // Only Apple survives the search, so "select all" means Apple — selecting the hidden
            // rows too would tick things the user can no longer see. This mirrors the enum branch,
            // whose select-all is scoped to `filteredEnumOptions` for the same reason.
            expect(lastFilter(onApply)).toEqual({type: 'multi-enum', selected: ['a']});
        });

        it('adds to the selection instead of replacing it when a search is active', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'multi-enum', enumOptions: OPTIONS});

            // Tick one row, then search for a different one and press select-all. Scoping
            // select-all to the visible rows is right; *replacing* the set with them is not,
            // because it unticks whatever the search is hiding. Two searches in a row would
            // then keep only the last batch, which is "select only these" under another name.
            await fireEvent.click(screen.getByTestId('filter-multi-enum-option-c'));
            await fireEvent.input(screen.getByTestId('filter-multi-enum-search'), {target: {value: 'apple'}});
            await fireEvent.click(screen.getByTestId('filter-multi-enum-select-all'));

            const filter = lastFilter(onApply) as {type: string; selected: string[]};
            expect(filter.type).toBe('multi-enum');
            expect([...filter.selected].sort()).toEqual(['a', 'c']);
        });

        it('does not drop a ticked value when the search hides it', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'multi-enum', enumOptions: OPTIONS});

            // Tick Apple, then type a query that leaves only Banana on screen.
            await fireEvent.click(screen.getByTestId('filter-multi-enum-option-a'));
            expect(lastFilter(onApply)).toEqual({type: 'multi-enum', selected: ['a']});

            await fireEvent.input(screen.getByTestId('filter-multi-enum-search'), {target: {value: 'banana'}});
            expect(screen.queryByTestId('filter-multi-enum-option-a')).toBeNull();

            // Filtering the view is not deselecting: typing publishes no new filter, and clearing
            // the box brings Apple back still ticked. This is the enum branch's behaviour too.
            expect(lastFilter(onApply)).toEqual({type: 'multi-enum', selected: ['a']});
            await fireEvent.click(screen.getByTestId('filter-multi-enum-search-clear'));
            expect(screen.getByTestId('filter-multi-enum-option-a')).toHaveAttribute('data-checked', 'true');
        });
    });

    describe('currency-stack', () => {
        const RANGES = new Map([
            ['EUR', {min: 0, max: 1000}],
            ['USD', {min: 0, max: 1000}],
            ['GBP', {min: 0, max: 1000}],
        ]);

        function mountStack(codes: string[]) {
            return mount({
                type: 'currency-stack',
                currencyOptions: [...RANGES.keys()],
                currencyMinMaxByCode: RANGES,
                initialValue: {type: 'currency-stack', items: codes.map((code) => ({code}))},
            });
        }

        it('offers nothing to edit until a currency is picked', async () => {
            await setupI18n();
            mount({type: 'currency-stack', currencyOptions: ['EUR']});

            expect(screen.getByTestId('filter-currency-empty')).toBeInTheDocument();
        });

        it('reports a per-currency range from the row editor', async () => {
            await setupI18n();
            const {onApply} = mountStack(['EUR', 'USD']);

            await fireEvent.click(screen.getByTestId('filter-currency-funnel-EUR'));
            await fireEvent.change(screen.getByTestId('filter-currency-min-EUR'), {target: {value: '100'}});
            await fireEvent.change(screen.getByTestId('filter-currency-max-EUR'), {target: {value: '900'}});

            // USD stays bound-less: the ranges are per currency, not one global pair.
            expect(lastFilter(onApply)).toEqual({
                type: 'currency-stack',
                items: [{code: 'EUR', min: 100, max: 900}, {code: 'USD'}],
            });
        });

        it('reorders a reversed per-currency pair', async () => {
            await setupI18n();
            const {onApply} = mountStack(['EUR']);

            await fireEvent.click(screen.getByTestId('filter-currency-funnel-EUR'));
            await fireEvent.change(screen.getByTestId('filter-currency-min-EUR'), {target: {value: '900'}});
            await fireEvent.change(screen.getByTestId('filter-currency-max-EUR'), {target: {value: '100'}});

            expect(lastFilter(onApply)).toEqual({type: 'currency-stack', items: [{code: 'EUR', min: 100, max: 900}]});
        });

        it('drops the whole filter when the last currency is removed', async () => {
            await setupI18n();
            const {onApply} = mountStack(['EUR', 'USD']);

            await fireEvent.click(screen.getByTestId('filter-currency-trash-EUR'));
            expect(lastFilter(onApply)).toEqual({type: 'currency-stack', items: [{code: 'USD'}]});
            expect(screen.queryByTestId('filter-currency-row-EUR')).toBeNull();

            await fireEvent.click(screen.getByTestId('filter-currency-trash-USD'));
            expect(lastFilter(onApply)).toBeNull();
        });

        it('does not leave a removed row behind as a phantom slider on its neighbour', async () => {
            // Non-regression. The rows are keyed by currency code, but the editor state
            // beside them — both slider thumbs — was keyed by array index, so removing a
            // row shifted every later one down a slot and made it inherit the departed
            // row's handles. USD, with no bound at all and a row reading "any amount",
            // showed EUR's handle at 80% and produced a value nobody aimed at when
            // dragged from there.
            await setupI18n();
            mountStack(['EUR', 'USD']);

            await fireEvent.click(screen.getByTestId('filter-currency-funnel-EUR'));
            await fireEvent.change(screen.getByTestId('filter-currency-min-EUR'), {target: {value: '800'}});
            const eurThumb = screen.getByTestId('filter-currency-slider-min-EUR');
            expect(eurThumb).toHaveValue('80');

            await fireEvent.click(screen.getByTestId('filter-currency-trash-EUR'));
            await fireEvent.click(screen.getByTestId('filter-currency-funnel-USD'));

            // USD has no minimum, so its handle belongs at the far left — and the field
            // beside it is the assertion's witness: the two must agree.
            expect(screen.getByTestId('filter-currency-min-USD')).toHaveValue(null);
            expect(screen.getByTestId('filter-currency-slider-min-USD')).toHaveValue('0');
        });

        it('keeps the open editor on its own row when an earlier one is removed', async () => {
            // Second half of the same defect: `currencyOpenIdx` is an index into a list
            // addressed by code, so deleting a row above the expanded one used to close
            // it — the user lost the range they were in the middle of typing.
            await setupI18n();
            mountStack(['EUR', 'USD', 'GBP']);

            await fireEvent.click(screen.getByTestId('filter-currency-funnel-GBP'));
            expect(screen.getByTestId('filter-currency-editor-GBP')).toBeInTheDocument();

            await fireEvent.click(screen.getByTestId('filter-currency-trash-EUR'));

            expect(screen.getByTestId('filter-currency-editor-GBP')).toBeInTheDocument();
            // And it did not simply move onto the survivor above it.
            expect(screen.queryByTestId('filter-currency-editor-USD')).toBeNull();
        });
    });

    describe('date', () => {
        it('forwards the range the picker committed', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'date'});

            const start = screen.getByTestId('date-range-input-start');
            await fireEvent.input(start, {target: {value: '2024-03-15'}});
            await fireEvent.blur(start);

            // Only the pass-through is the subject: what the picker does with an empty
            // end field is the picker's contract, and it has its own tests.
            expect(lastFilter(onApply)).toMatchObject({type: 'date', from: '2024-03-15'});
        });
    });

    describe('popover lifecycle', () => {
        it('resets every mode from the header button', async () => {
            await setupI18n();
            const {onApply} = mount({type: 'enum', enumOptions: OPTIONS, initialValue: {type: 'enum', selected: ['a']}});

            await fireEvent.input(screen.getByTestId('filter-enum-search'), {target: {value: 'apple'}});
            await fireEvent.click(screen.getByTestId('column-filter-reset'));

            expect(lastFilter(onApply)).toBeNull();
            expect(screen.getByTestId('filter-enum-option-a')).toHaveAttribute('data-checked', 'false');
            // The search box is emptied too, so every option is reachable again.
            expect(screen.getByTestId('filter-enum-option-c')).toBeInTheDocument();
        });

        it('asks the parent to close on an outside click, and not on an inside one', async () => {
            await setupI18n();
            const {onClose} = mount({type: 'text'});

            // The outside-click guard arms itself a tick after mount, so the first half
            // is polled rather than timed. It doubles as the barrier for the second
            // half: once a body click has landed, the listener is provably live, and
            // the inside click that follows is a real negative rather than a race won.
            await waitFor(
                () => {
                    fireEvent.click(document.body);
                    expect(onClose).toHaveBeenCalled();
                },
                {timeout: 3_000},
            );
            const closesSoFar = onClose.mock.calls.length;

            await fireEvent.click(screen.getByTestId('filter-text-input'));

            expect(onClose).toHaveBeenCalledTimes(closesSoFar);
        });
    });
});
