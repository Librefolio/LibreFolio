/**
 * DataTable pure logic — unit tests (Vitest, node env).
 *
 * These are the decisions that used to live inside `DataTable.svelte`'s
 * `$derived.by` blocks and `{@const}` template expressions, extracted into
 * `dataTableLogic.ts` so their many branches are reachable with a literal
 * instead of a mounted component on a page that happens to configure the mode.
 *
 * Every case names the row/column/filter shape that reaches the branch — the
 * user is "a column whose cell returns X, filtered/sorted by Y". The handful of
 * branches that no caller can reach (a typed cell is stringified by the filter
 * before its object sub-paths can fire; a matchMode outside the four the type
 * allows) are documented at the bottom, not forced with a cast.
 */
import {describe, expect, it} from 'vitest';
import {compareRowsByColumn, extractRawValue, formatCellDate, getColumnMinMax, getCurrencyMinMaxByCode, getCurrencyOptions, getEnumOptionsWithCounts, getMultiEnumOptions, getMultiEnumOptionsWithCounts, matchesColumnFilter} from './dataTableLogic';
import type {CellContent, ColumnDef, EnumOption, FilterValue} from './types';

interface Row {
    id: string;
    name: string;
    qty: number | null;
}

/** Build a column def with only the fields a given test needs. */
function col(over: Partial<ColumnDef<Row>> = {}): ColumnDef<Row> {
    return {
        id: 'c',
        header: 'C',
        type: 'text',
        cell: (r) => r.name,
        ...over,
    };
}

const rowsOf = (...qtys: (number | null)[]): Row[] => qtys.map((q, i) => ({id: `r${i}`, name: `n${i}`, qty: q}));

describe('extractRawValue', () => {
    it('returns a primitive cell unchanged', () => {
        // A plain text/number column: the cell renderer returns the value itself.
        expect(extractRawValue('hello')).toBe('hello');
        expect(extractRawValue(42)).toBe(42);
    });

    it('returns null unchanged (the second half of the object guard)', () => {
        expect(extractRawValue(null as unknown as CellContent)).toBeNull();
    });

    it('reads an icon-text cell by its text, not its icon', () => {
        expect(extractRawValue({type: 'icon-text', icon: {}, text: 'Zürich'})).toBe('Zürich');
    });

    it('reads a badge cell by its text, not its variant', () => {
        expect(extractRawValue({type: 'badge', text: 'Active', variant: 'success'})).toBe('Active');
    });

    it('turns a date cell into a Date at the instant it names', () => {
        const out = extractRawValue({type: 'date', value: '2020-03-01T00:00:00Z'});
        expect(out).toBeInstanceOf(Date);
        expect((out as Date).getTime()).toBe(new Date('2020-03-01T00:00:00Z').getTime());
    });

    it('reads a size cell by its byte count, not its printed form', () => {
        expect(extractRawValue({type: 'size', bytes: 2048})).toBe(2048);
    });

    it('reads a link cell by its label, not its href', () => {
        expect(extractRawValue({type: 'link', text: 'Docs', href: 'https://x'})).toBe('Docs');
    });

    it('reads each editable shape by its underlying value', () => {
        expect(extractRawValue({type: 'editable-number', value: 7, onchange: () => {}})).toBe(7);
        expect(extractRawValue({type: 'editable-text', value: 'ed', onchange: () => {}})).toBe('ed');
        expect(extractRawValue({type: 'editable-select', value: 'opt', options: [], onchange: () => {}} as unknown as CellContent)).toBe('opt');
        expect(extractRawValue({type: 'editable-checkbox', value: true, onchange: () => {}})).toBe(true);
    });

    it('strips the markup from an html cell so it sorts on the text', () => {
        expect(extractRawValue({type: 'html', html: '<b>Bold</b> text'})).toBe('Bold text');
    });

    it('falls back to String() for a cell shape it does not special-case (image)', () => {
        // image/custom cells are valid CellContent but not in the switch → default arm.
        const out = extractRawValue({type: 'image', src: 's', alt: 'a'});
        expect(out).toBe('[object Object]');
    });
});

describe('matchesColumnFilter — text', () => {
    const textCol = col({getValue: (r) => r.name});
    const row = (name: string): Row => ({id: 'x', name, qty: 0});

    const tf = (value: string, matchMode: 'contains' | 'startsWith' | 'endsWith' | 'equals'): FilterValue => ({type: 'text', value, matchMode});

    it('contains matches a substring anywhere, case-insensitively', () => {
        expect(matchesColumnFilter(textCol, row('Alphabet'), tf('pha', 'contains'))).toBe(true);
        expect(matchesColumnFilter(textCol, row('Alphabet'), tf('zzz', 'contains'))).toBe(false);
    });

    it('startsWith only matches the prefix', () => {
        expect(matchesColumnFilter(textCol, row('Alphabet'), tf('alp', 'startsWith'))).toBe(true);
        expect(matchesColumnFilter(textCol, row('Alphabet'), tf('bet', 'startsWith'))).toBe(false);
    });

    it('endsWith only matches the suffix', () => {
        expect(matchesColumnFilter(textCol, row('Alphabet'), tf('bet', 'endsWith'))).toBe(true);
        expect(matchesColumnFilter(textCol, row('Alphabet'), tf('alp', 'endsWith'))).toBe(false);
    });

    it('equals demands the whole string', () => {
        expect(matchesColumnFilter(textCol, row('Alphabet'), tf('alphabet', 'equals'))).toBe(true);
        expect(matchesColumnFilter(textCol, row('Alphabet'), tf('alpha', 'equals'))).toBe(false);
    });

    it('falls back to the cell renderer when the column has no getValue', () => {
        // No getValue: the predicate reads through `cell`, which returns r.name.
        const noGetValue = col();
        expect(matchesColumnFilter(noGetValue, row('Banana'), tf('ana', 'contains'))).toBe(true);
    });

    it('folds a typed cell to its String() form when there is no getValue', () => {
        // A column with no getValue whose cell renders a typed object: the filter
        // reads String(cellValue) — "[object Object]" — not the badge's text. This
        // is why filterable columns supply getValue; the fold itself is the branch.
        const badgeCol = col({cell: (r) => ({type: 'badge', text: r.name, variant: 'default'})});
        expect(matchesColumnFilter(badgeCol, row('Whatever'), tf('object', 'contains'))).toBe(true);
        expect(matchesColumnFilter(badgeCol, row('Whatever'), tf('whatever', 'contains'))).toBe(false);
    });
});

describe('matchesColumnFilter — number', () => {
    const numCol = col({type: 'number', getValue: (r) => r.qty});
    const row = (qty: number): Row => ({id: 'x', name: 'n', qty});

    it('keeps a value at or above the lower bound only', () => {
        expect(matchesColumnFilter(numCol, row(9), {type: 'number', min: 10})).toBe(false);
        expect(matchesColumnFilter(numCol, row(10), {type: 'number', min: 10})).toBe(true);
    });

    it('keeps a value at or below the upper bound only', () => {
        expect(matchesColumnFilter(numCol, row(21), {type: 'number', max: 20})).toBe(false);
        expect(matchesColumnFilter(numCol, row(20), {type: 'number', max: 20})).toBe(true);
    });

    it('applies both bounds together', () => {
        expect(matchesColumnFilter(numCol, row(15), {type: 'number', min: 10, max: 20})).toBe(true);
    });

    it('restricts nothing when neither bound is set', () => {
        expect(matchesColumnFilter(numCol, row(-999), {type: 'number'})).toBe(true);
    });
});

describe('matchesColumnFilter — size', () => {
    // Size filtering is driven by a getValue that returns the byte count directly;
    // the SizeCell object sub-path is documented as unreachable below.
    const sizeCol = col({type: 'size', getValue: (r) => r.qty});
    const row = (bytes: number): Row => ({id: 'x', name: 'n', qty: bytes});

    it('excludes files below the byte floor', () => {
        expect(matchesColumnFilter(sizeCol, row(500), {type: 'size', minBytes: 1000})).toBe(false);
        expect(matchesColumnFilter(sizeCol, row(1000), {type: 'size', minBytes: 1000})).toBe(true);
    });

    it('excludes files above the byte ceiling', () => {
        expect(matchesColumnFilter(sizeCol, row(5000), {type: 'size', maxBytes: 4096})).toBe(false);
        expect(matchesColumnFilter(sizeCol, row(4096), {type: 'size', maxBytes: 4096})).toBe(true);
    });
});

describe('matchesColumnFilter — date', () => {
    // Real date columns expose an ISO string through getValue (the string path).
    const dateCol = col({type: 'date', getValue: (r) => r.name});
    const row = (iso: string): Row => ({id: 'x', name: iso, qty: 0});

    it('excludes dates before the from bound', () => {
        expect(matchesColumnFilter(dateCol, row('2020-01-01'), {type: 'date', from: '2020-06-01'})).toBe(false);
        expect(matchesColumnFilter(dateCol, row('2020-07-01'), {type: 'date', from: '2020-06-01'})).toBe(true);
    });

    it('excludes dates after the to bound', () => {
        expect(matchesColumnFilter(dateCol, row('2020-12-01'), {type: 'date', to: '2020-06-01'})).toBe(false);
        expect(matchesColumnFilter(dateCol, row('2020-03-01'), {type: 'date', to: '2020-06-01'})).toBe(true);
    });

    it('restricts nothing when the range is open on both ends', () => {
        expect(matchesColumnFilter(dateCol, row('1999-01-01'), {type: 'date'})).toBe(true);
    });
});

describe('matchesColumnFilter — enum', () => {
    const enumCol = col({type: 'enum', getValue: (r) => r.name});
    const row = (v: string): Row => ({id: 'x', name: v, qty: 0});

    it('keeps a row whose value is in the selected set', () => {
        expect(matchesColumnFilter(enumCol, row('buy'), {type: 'enum', selected: ['buy', 'sell']})).toBe(true);
        expect(matchesColumnFilter(enumCol, row('fee'), {type: 'enum', selected: ['buy', 'sell']})).toBe(false);
    });
});

describe('matchesColumnFilter — multi-enum', () => {
    const row = (name: string): Row => ({id: 'x', name, qty: 0});

    it('restricts nothing when the selection is empty', () => {
        const c = col({type: 'multi-enum', getMultiValue: () => ['a']});
        expect(matchesColumnFilter(c, row('n'), {type: 'multi-enum', selected: []})).toBe(true);
    });

    it('uses getMultiValue and passes on any overlap', () => {
        const c = col({type: 'multi-enum', getMultiValue: (r) => r.name.split('|')});
        expect(matchesColumnFilter(c, row('x|y'), {type: 'multi-enum', selected: ['y', 'z']})).toBe(true);
        expect(matchesColumnFilter(c, row('x|w'), {type: 'multi-enum', selected: ['y', 'z']})).toBe(false);
    });

    it('reads an array returned by getValue when there is no getMultiValue', () => {
        const c = col({type: 'multi-enum', getValue: (r) => r.name.split('|')});
        expect(matchesColumnFilter(c, row('p|q'), {type: 'multi-enum', selected: ['q']})).toBe(true);
    });

    it('splits a comma string when the value is neither array nor multi-accessor', () => {
        const c = col({type: 'multi-enum', getValue: (r) => r.name});
        expect(matchesColumnFilter(c, row('red,green'), {type: 'multi-enum', selected: ['green']})).toBe(true);
        expect(matchesColumnFilter(c, row('red,green'), {type: 'multi-enum', selected: ['blue']})).toBe(false);
    });

    it('treats a null value as the empty string before splitting', () => {
        // getValue returns null for a tag-less row: `String(null ?? '')` → '' →
        // [''] , which intersects nothing the user could have selected.
        const c = col({type: 'multi-enum', getValue: () => null});
        expect(matchesColumnFilter(c, row('n'), {type: 'multi-enum', selected: ['green']})).toBe(false);
    });
});

describe('matchesColumnFilter — currency-stack', () => {
    const row = (code: string, amount: number): Row => ({id: 'x', name: code, qty: amount});
    const ccyCol = col({type: 'currency-stack', getCurrencyValue: (r) => ({code: r.name, amount: r.qty ?? 0})});

    it('restricts nothing when no currency ranges are set', () => {
        expect(matchesColumnFilter(ccyCol, row('EUR', 100), {type: 'currency-stack', items: []})).toBe(true);
    });

    it('matches a row inside one of the per-currency ranges', () => {
        const f: FilterValue = {type: 'currency-stack', items: [{code: 'EUR', min: 50, max: 150}]};
        expect(matchesColumnFilter(ccyCol, row('EUR', 100), f)).toBe(true);
        expect(matchesColumnFilter(ccyCol, row('EUR', 200), f)).toBe(false);
        expect(matchesColumnFilter(ccyCol, row('USD', 100), f)).toBe(false);
    });

    it('treats an item with no bounds as "any amount of that currency"', () => {
        const f: FilterValue = {type: 'currency-stack', items: [{code: 'GBP'}]};
        expect(matchesColumnFilter(ccyCol, row('GBP', -5), f)).toBe(true);
    });

    it('excludes a row whose cell yields no currency value', () => {
        const nullCol = col({type: 'currency-stack', getCurrencyValue: () => null});
        expect(matchesColumnFilter(nullCol, row('EUR', 1), {type: 'currency-stack', items: [{code: 'EUR'}]})).toBe(false);
    });

    it('excludes every row when the column exposes no currency accessor', () => {
        const noAccessor = col({type: 'currency-stack'});
        expect(matchesColumnFilter(noAccessor, row('EUR', 1), {type: 'currency-stack', items: [{code: 'EUR'}]})).toBe(false);
    });
});

describe('compareRowsByColumn', () => {
    const numCol = col({type: 'number', getValue: (r) => r.qty});
    const r = (id: string, qty: number | null): Row => ({id, name: id, qty});

    it('orders two numbers by magnitude ascending, and flips for descending', () => {
        expect(compareRowsByColumn(numCol, r('a', 2), r('b', 10), 'asc')).toBeLessThan(0);
        expect(compareRowsByColumn(numCol, r('a', 2), r('b', 10), 'desc')).toBeGreaterThan(0);
    });

    it('orders two Dates by instant, not by their printed form', () => {
        const dCol = col({getValue: (row) => new Date(row.name)});
        const early: Row = {id: '1', name: '2020-01-01', qty: 0};
        const late: Row = {id: '2', name: '2020-12-31', qty: 0};
        expect(compareRowsByColumn(dCol, early, late, 'asc')).toBeLessThan(0);
    });

    it('orders anything else by localeCompare on its string form', () => {
        const tCol = col({getValue: (row) => row.name});
        expect(compareRowsByColumn(tCol, {id: '1', name: 'apple', qty: 0}, {id: '2', name: 'banana', qty: 0}, 'asc')).toBeLessThan(0);
    });

    it('sends an empty cell last in both directions', () => {
        expect(compareRowsByColumn(numCol, r('a', null), r('b', 5), 'asc')).toBe(1);
        expect(compareRowsByColumn(numCol, r('a', null), r('b', 5), 'desc')).toBe(1);
        expect(compareRowsByColumn(numCol, r('a', 5), r('b', null), 'asc')).toBe(-1);
    });

    it('leaves two empty cells in their given order', () => {
        expect(compareRowsByColumn(numCol, r('a', null), r('b', null), 'asc')).toBe(0);
    });

    it('treats an empty string as missing, not as the smallest string', () => {
        const tCol = col({getValue: (row) => row.name});
        expect(compareRowsByColumn(tCol, {id: '1', name: '', qty: 0}, {id: '2', name: 'z', qty: 0}, 'asc')).toBe(1);
    });

    it('reduces a typed cell through extractRawValue before comparing', () => {
        // No getValue: it reads `cell`, which returns a badge; sort is on its text.
        const badgeCol = col({cell: (row) => ({type: 'badge', text: row.name, variant: 'default'})});
        expect(compareRowsByColumn(badgeCol, {id: '1', name: 'Alpha', qty: 0}, {id: '2', name: 'Beta', qty: 0}, 'asc')).toBeLessThan(0);
    });
});

describe('getColumnMinMax', () => {
    it('spans the numeric values of a plain number column', () => {
        const c = col({type: 'number', getValue: (r) => r.qty});
        expect(getColumnMinMax(c, rowsOf(3, 1, 8, 5))).toEqual({min: 1, max: 8});
    });

    it('reads a size cell by its byte count', () => {
        const c = col({type: 'size', cell: (r) => ({type: 'size', bytes: r.qty ?? 0})});
        expect(getColumnMinMax(c, rowsOf(100, 900, 400))).toEqual({min: 100, max: 900});
    });

    it('coerces a non-size typed cell through extractRawValue', () => {
        const c = col({cell: (r) => ({type: 'badge', text: String(r.qty), variant: 'default'})});
        expect(getColumnMinMax(c, rowsOf(2, 6))).toEqual({min: 2, max: 6});
    });

    it('skips values that are not finite numbers', () => {
        const c = col({type: 'number', getValue: (r) => (r.qty === 0 ? NaN : r.qty)});
        // The 0-row yields NaN and is skipped; the interval is drawn from the rest.
        expect(getColumnMinMax(c, rowsOf(0, 4, 9))).toEqual({min: 4, max: 9});
    });

    it('falls back to {0, 1} when the column holds no usable number', () => {
        const c = col({type: 'number', getValue: () => NaN});
        expect(getColumnMinMax(c, rowsOf(1, 2))).toEqual({min: 0, max: 1});
    });

    it('widens a single distinct value so the slider keeps a span', () => {
        const c = col({type: 'number', getValue: (r) => r.qty});
        expect(getColumnMinMax(c, rowsOf(7, 7, 7))).toEqual({min: 7, max: 8});
    });

    it('handles an empty dataset', () => {
        const c = col({type: 'number', getValue: (r) => r.qty});
        expect(getColumnMinMax(c, [])).toEqual({min: 0, max: 1});
    });
});

describe('getMultiEnumOptions', () => {
    it('collects, de-dupes, sorts and drops blank/nullish values', () => {
        const c = col({getMultiValue: (r) => r.name.split(',')});
        const data: Row[] = [
            {id: '1', name: 'z,a', qty: 0},
            {id: '2', name: 'a,,m', qty: 0},
        ];
        expect(getMultiEnumOptions(c, data)).toEqual([
            {value: 'a', label: 'a'},
            {value: 'm', label: 'm'},
            {value: 'z', label: 'z'},
        ]);
    });

    it('yields nothing when the column has no multi-value accessor', () => {
        expect(getMultiEnumOptions(col(), rowsOf(1, 2))).toEqual([]);
    });
});

describe('getMultiEnumOptionsWithCounts', () => {
    const OPTS: EnumOption[] = [
        {value: 'x', label: 'X'},
        {value: 'y', label: 'Y'},
    ];

    it('returns the declared options untouched when there are none', () => {
        const c = col({enumOptions: []});
        expect(getMultiEnumOptionsWithCounts(c, rowsOf(1))).toEqual([]);
    });

    it('yields nothing when the column declares no options at all', () => {
        // `enumOptions ?? []`: a column with no static options is a normal shape.
        expect(getMultiEnumOptionsWithCounts(col(), rowsOf(1, 2))).toEqual([]);
    });

    it('counts how many rows carry each declared option', () => {
        const c = col({enumOptions: OPTS, getMultiValue: (r) => r.name.split(',')});
        const data: Row[] = [
            {id: '1', name: 'x,y', qty: 0},
            {id: '2', name: 'x', qty: 0},
        ];
        expect(getMultiEnumOptionsWithCounts(c, data)).toEqual([
            {value: 'x', label: 'X', count: 2},
            {value: 'y', label: 'Y', count: 1},
        ]);
    });

    it('counts zero for every option when there is no multi-value accessor', () => {
        const c = col({enumOptions: OPTS});
        expect(getMultiEnumOptionsWithCounts(c, rowsOf(1, 2))).toEqual([
            {value: 'x', label: 'X', count: 0},
            {value: 'y', label: 'Y', count: 0},
        ]);
    });
});

describe('getEnumOptionsWithCounts', () => {
    const OPTS: EnumOption[] = [
        {value: 'buy', label: 'Buy'},
        {value: 'sell', label: 'Sell'},
    ];

    it('returns the declared options untouched when there are none', () => {
        expect(getEnumOptionsWithCounts(col({enumOptions: []}), rowsOf(1))).toEqual([]);
    });

    it('yields nothing when the column declares no options at all', () => {
        expect(getEnumOptionsWithCounts(col(), rowsOf(1, 2))).toEqual([]);
    });

    it('counts a null value against the empty key', () => {
        // `String(getValue(row) ?? '')`: a row whose enum value is null folds onto
        // '', so neither declared option scores it.
        const c = col({type: 'enum', enumOptions: OPTS, getValue: () => null});
        expect(getEnumOptionsWithCounts(c, rowsOf(1))).toEqual([
            {value: 'buy', label: 'Buy', count: 0},
            {value: 'sell', label: 'Sell', count: 0},
        ]);
    });

    it('counts rows per single value through getValue', () => {
        const c = col({type: 'enum', enumOptions: OPTS, getValue: (r) => r.name});
        const data: Row[] = [
            {id: '1', name: 'buy', qty: 0},
            {id: '2', name: 'buy', qty: 0},
            {id: '3', name: 'sell', qty: 0},
        ];
        expect(getEnumOptionsWithCounts(c, data)).toEqual([
            {value: 'buy', label: 'Buy', count: 2},
            {value: 'sell', label: 'Sell', count: 1},
        ]);
    });

    it('counts against the empty key when the column has no getValue', () => {
        // Without getValue every row folds onto '', so declared options score zero.
        const c = col({type: 'enum', enumOptions: OPTS});
        expect(getEnumOptionsWithCounts(c, rowsOf(1, 2))).toEqual([
            {value: 'buy', label: 'Buy', count: 0},
            {value: 'sell', label: 'Sell', count: 0},
        ]);
    });
});

describe('getCurrencyOptions', () => {
    it('yields nothing without a currency accessor', () => {
        expect(getCurrencyOptions(col(), rowsOf(1))).toEqual([]);
    });

    it('collects the distinct codes present, sorted, skipping empty ones', () => {
        const c = col({getCurrencyValue: (r) => (r.qty === 0 ? null : {code: r.name, amount: r.qty ?? 0})});
        const data: Row[] = [
            {id: '1', name: 'USD', qty: 5},
            {id: '2', name: 'EUR', qty: 3},
            {id: '3', name: 'USD', qty: 9},
            {id: '4', name: 'skip', qty: 0}, // null cv → skipped
        ];
        expect(getCurrencyOptions(c, data)).toEqual(['EUR', 'USD']);
    });
});

describe('getCurrencyMinMaxByCode', () => {
    it('returns an empty map without a currency accessor', () => {
        expect(getCurrencyMinMaxByCode(col(), rowsOf(1)).size).toBe(0);
    });

    it('tracks a min and a max per currency code', () => {
        const c = col({getCurrencyValue: (r) => ({code: r.name, amount: r.qty ?? 0})});
        const data: Row[] = [
            {id: '1', name: 'EUR', qty: 10},
            {id: '2', name: 'EUR', qty: 4},
            {id: '3', name: 'EUR', qty: 30},
            {id: '4', name: 'USD', qty: 7},
        ];
        const out = getCurrencyMinMaxByCode(c, data);
        expect(out.get('EUR')).toEqual({min: 4, max: 30});
        expect(out.get('USD')).toEqual({min: 7, max: 8}); // single row widened
    });

    it('skips rows with no code or a non-finite amount', () => {
        const c = col({
            getCurrencyValue: (r) => {
                if (r.id === 'nocode') return {code: '', amount: 5};
                if (r.id === 'inf') return {code: 'EUR', amount: Infinity};
                return {code: 'EUR', amount: r.qty ?? 0};
            },
        });
        const data: Row[] = [
            {id: 'nocode', name: '', qty: 5},
            {id: 'inf', name: 'EUR', qty: 0},
            {id: 'ok', name: 'EUR', qty: 12},
        ];
        const out = getCurrencyMinMaxByCode(c, data);
        expect(out.get('EUR')).toEqual({min: 12, max: 13});
        expect(out.has('')).toBe(false);
    });
});

describe('formatCellDate', () => {
    const DAY = 24 * 60 * 60 * 1000;
    /** n days ago, offset a minute into the day so Math.floor lands cleanly on n. */
    const daysAgo = (n: number) => new Date(Date.now() - n * DAY - 60_000);

    it('renders the time-only format', () => {
        const d = new Date('2020-05-05T13:45:00Z');
        expect(formatCellDate(d, 'time')).toBe(d.toLocaleTimeString());
    });

    it('renders the datetime format', () => {
        const d = new Date('2020-05-05T13:45:00Z');
        const expected = d.toLocaleString(undefined, {year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'});
        expect(formatCellDate(d, 'datetime')).toBe(expected);
    });

    it('renders the default date format when no format is given', () => {
        const d = new Date('2020-05-05T13:45:00Z');
        expect(formatCellDate(d)).toBe(d.toLocaleDateString(undefined, {year: 'numeric', month: 'short', day: 'numeric'}));
    });

    it('accepts a string value, parsing it to a Date', () => {
        expect(formatCellDate('2020-05-05T13:45:00Z', 'time')).toBe(new Date('2020-05-05T13:45:00Z').toLocaleTimeString());
    });

    it('relative: says today for the current day using the supplied label', () => {
        expect(formatCellDate(daysAgo(0), 'relative', {today: 'OGGI', yesterday: 'IERI'})).toBe('OGGI');
    });

    it('relative: says yesterday for one day back using the supplied label', () => {
        expect(formatCellDate(daysAgo(1), 'relative', {today: 'OGGI', yesterday: 'IERI'})).toBe('IERI');
    });

    it('relative: says "Nd ago" for two to six days back', () => {
        expect(formatCellDate(daysAgo(3), 'relative')).toBe('3d ago');
    });

    it('relative: falls back to a full date once a week has passed', () => {
        const d = daysAgo(8);
        expect(formatCellDate(d, 'relative')).toBe(d.toLocaleDateString());
    });

    it('defaults the relative labels to English when none are passed', () => {
        expect(formatCellDate(daysAgo(0), 'relative')).toBe('Today');
        expect(formatCellDate(daysAgo(1), 'relative')).toBe('Yesterday');
    });
});

/**
 * Branches deliberately left uncovered — no caller can reach them, so forcing
 * them with a cast would test a state no user is ever in (Lane D rule: chase a
 * branch only if you can name the user who walks it).
 *
 *   - extractRawValue's `!('type' in cell)` guard. Every object member of
 *     CellContent carries a discriminant `type`; the only two call sites, the
 *     sort comparator and getColumnMinMax, gate on `'type' in value` before
 *     calling. The guard is defensive.
 *   - matchesColumnFilter, the object sub-paths of the `size` and `date` modes
 *     (`rawValue.type === 'size'` / `=== 'date'`). A typed cell is turned into
 *     `String(cellValue)` before the switch, so `rawValue` is a string on those
 *     arms and never the object they test for. Real size/date columns feed a
 *     plain bytes number / ISO string through getValue, which the covered string
 *     paths exercise. (These arms are effectively dead; noted here rather than
 *     touched, since the fix is a product decision, not a test one.)
 *   - matchesColumnFilter's text mode with a matchMode outside the four the type
 *     permits: the switch falls through to the trailing `return true`. Not
 *     reachable through the typed FilterValue.
 */

describe('compareRowsByColumn — a column that brings its own order', () => {
    interface Row {
        id: string;
        status: string;
    }
    // Triage order, not alphabetical order: what needs attention comes first.
    const PRIORITY: Record<string, number> = {before_opening: 0, unresolved: 1, pending_duplicate: 2, unique: 3};
    const col = {
        id: 'status',
        header: 'Status',
        type: 'text',
        cell: (r: Row) => r.status,
        sortFn: (a: Row, b: Row) => PRIORITY[a.status] - PRIORITY[b.status],
    } as unknown as ColumnDef<Row>;

    const rows: Row[] = [
        {id: 'a', status: 'unique'},
        {id: 'b', status: 'before_opening'},
        {id: 'c', status: 'pending_duplicate'},
        {id: 'd', status: 'unresolved'},
    ];

    it('sorts by the column function rather than by the rendered text', () => {
        // Alphabetically this is before_opening, pending_duplicate, unique,
        // unresolved — which puts the rows the user must act on either side of
        // the ones that are fine. `sortFn` exists precisely to say otherwise.
        const sorted = [...rows].sort((x, y) => compareRowsByColumn(col, x, y, 'asc')).map((r) => r.status);
        expect(sorted).toEqual(['before_opening', 'unresolved', 'pending_duplicate', 'unique']);
    });

    it('reverses that order on descending, without asking the column twice', () => {
        const sorted = [...rows].sort((x, y) => compareRowsByColumn(col, x, y, 'desc')).map((r) => r.status);
        expect(sorted).toEqual(['unique', 'pending_duplicate', 'unresolved', 'before_opening']);
    });

    it('differs from the default ordering, which is the whole point', () => {
        const plain = {id: 'status', header: 'Status', type: 'text', cell: (r: Row) => r.status} as unknown as ColumnDef<Row>;
        const withFn = [...rows].sort((x, y) => compareRowsByColumn(col, x, y, 'asc')).map((r) => r.status);
        const without = [...rows].sort((x, y) => compareRowsByColumn(plain, x, y, 'asc')).map((r) => r.status);
        expect(withFn).not.toEqual(without);
        // And the default really is alphabetical, so the divergence is not noise.
        expect(without).toEqual(['before_opening', 'pending_duplicate', 'unique', 'unresolved']);
    });

    it('leaves columns without one on the ordinary path', () => {
        const plain = {id: 'n', header: 'N', type: 'number', cell: (r: {n: number}) => r.n} as unknown as ColumnDef<{n: number}>;
        const nums = [{n: 3}, {n: 1}, {n: 2}];
        expect([...nums].sort((x, y) => compareRowsByColumn(plain, x, y, 'asc')).map((r) => r.n)).toEqual([1, 2, 3]);
    });
});
