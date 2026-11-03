/**
 * filterState — unit tests
 *
 * The deep-link contract of the transactions table. Three representations have
 * to agree: the query string in the address bar, the `TransactionFilterMap`
 * the page holds, and the `FilterValue` record the DataTable's column chips
 * render. A shared link is only worth sending if the round trip through all
 * three lands on the table the sender was looking at.
 *
 * That is why the centre of this file is a **round trip** rather than a list of
 * outputs: asserting that `parse` returns a particular object only pins today's
 * shape, while `build(parse(x)) === x` pins the property the feature exists
 * for. Where the round trip is deliberately lossy — defaults dropped, currency
 * codes upper-cased, unparseable bounds discarded — each case says so and
 * states what it normalises to, and the normal form is asserted to be a fixed
 * point so the URL cannot keep drifting on every navigation.
 *
 * All four functions are pure, so the whole grammar is reachable here. Doing
 * the same through Playwright would mean one page load per URL shape, to read
 * state that is never rendered.
 */
import {describe, expect, it} from 'vitest';

import {applyTransactionColumnFilters, buildTransactionsFiltersUrl, parseTransactionFilters, toTransactionColumnFilters, type TransactionFilterMap} from './filterState';
import type {FilterValue} from '$lib/components/table/types';

/** Parse a query string, write it back out, and return the query it produced. */
function roundTrip(query: string): string {
    const url = buildTransactionsFiltersUrl(parseTransactionFilters(new URLSearchParams(query)));
    const params = new URL(url, 'http://localhost').searchParams;
    params.sort();
    return params.toString();
}

/** The same query put through `URLSearchParams`, so encoding and order match. */
function canonical(query: string): string {
    const params = new URLSearchParams(query);
    params.sort();
    return params.toString();
}

describe('transaction without-asset filter', () => {
    const withoutAssetColumnFilter = {
        asset_id: {type: 'enum' as const, selected: ['__null__']},
    };

    it('stores the null sentinel without creating NaN', () => {
        const result = applyTransactionColumnFilters({}, withoutAssetColumnFilter);

        expect(result).not.toBeNull();
        expect(result?.without_asset).toBe(true);
        expect(result?.asset_id).toBeUndefined();
        expect(result?.asset_ids).toBeUndefined();
    });

    it('returns null when the same null filter is emitted again', () => {
        const first = applyTransactionColumnFilters({}, withoutAssetColumnFilter);
        expect(first).not.toBeNull();

        expect(applyTransactionColumnFilters(first!, withoutAssetColumnFilter)).toBeNull();
    });

    it('keeps null and numeric asset selections distinct', () => {
        const result = applyTransactionColumnFilters(
            {},
            {
                asset_id: {type: 'enum', selected: ['__null__', '5']},
            },
        );

        expect(result?.without_asset).toBe(true);
        expect(result?.asset_id).toBeUndefined();
        expect(result?.asset_ids).toEqual([5]);
    });

    it('restores the null sentinel in DataTable column filters', () => {
        expect(toTransactionColumnFilters({without_asset: true})).toEqual({
            asset_id: {type: 'enum', selected: ['__null__']},
        });
        expect(toTransactionColumnFilters({without_asset: true, asset_id: 42}).asset_id).toEqual({
            type: 'enum',
            selected: ['__null__', '42'],
        });
    });

    it('round-trips through the URL without asset_id=NaN', () => {
        const url = buildTransactionsFiltersUrl({without_asset: true});
        const query = new URL(url, 'http://localhost').searchParams;
        const parsed = parseTransactionFilters(query);

        expect(url).toBe('/transactions?without_asset=true');
        expect(url).not.toContain('NaN');
        expect(parsed.without_asset).toBe(true);
        expect(parsed.asset_id).toBeUndefined();
    });

    it('drops legacy malformed asset_id=NaN values', () => {
        const parsed = parseTransactionFilters(new URLSearchParams('asset_id=NaN'));

        expect(parsed.asset_id).toBeUndefined();
        expect(parsed.without_asset).toBeUndefined();
    });
});

// =============================================================================
//  The round trip — a shared link must reopen the same table
// =============================================================================

describe('the round trip through the URL', () => {
    it.each([
        ['a single broker', 'broker_id=3'],
        ['several brokers', 'broker_ids=3,7,11'],
        ['a single asset', 'asset_id=12'],
        ['several assets', 'asset_ids=12,15'],
        ['rows with no asset', 'without_asset=true'],
        ['transaction types', 'types=BUY,SELL'],
        ['a closed date range', 'date_start=2024-01-01&date_end=2024-12-31'],
        ['a date range open at the end', 'date_start=2024-01-01'],
        ['a date range open at the start', 'date_end=2024-12-31'],
        ['tags', 'tags=dividend,tax'],
        ['a currency', 'currency=EUR'],
        ['an id range', 'id_min=10&id_max=99'],
        ['a quantity range', 'qty_min=1&qty_max=500'],
        ['a cash bracket', 'cash=EUR:100:200'],
        ['a cash bracket open on one side', 'cash=EUR::200'],
        ['two cash brackets', 'cash=EUR::200,USD:5:'],
        ['a page other than the first', 'page=3'],
        ['a page size other than the default', 'page_size=100'],
        ['zero bounds, which are values and not absences', 'id_min=0&qty_min=0'],
        ['a negative cash bracket', 'cash=EUR:-500:-100'],
        ['everything at once', 'broker_ids=3,7&asset_id=12&types=BUY,SELL&date_start=2024-01-01&date_end=2024-12-31&tags=dividend&currency=EUR&id_min=10&qty_max=500&cash=EUR:100:200&page=2&page_size=25'],
    ])('survives %s', (_label, query) => {
        expect(roundTrip(query)).toBe(canonical(query));
    });

    describe('is deliberately lossy, and says what it normalises to', () => {
        it.each([
            ['the default page is not worth writing down', 'page=1', ''],
            ['nor is the default page size', 'page_size=50', ''],
            ['a filter that is off is simply absent', 'without_asset=false', ''],
            ['only the literal "true" turns the no-asset filter on', 'without_asset=1', ''],
            ['an empty list is not a list', 'types=&tags=', ''],
            ['a list of nothing but separators is empty too', 'types=,,', ''],
            ['stray whitespace around list entries is dropped', 'types=BUY, SELL', 'types=BUY%2CSELL'],
            ['a non-numeric id in a numeric list is dropped', 'broker_ids=3,abc', 'broker_ids=3'],
            ['a currency code is upper-cased', 'cash=eur:1:2', 'cash=EUR%3A1%3A2'],
            ['a cash bound that is not a number is dropped, the other is kept', 'cash=EUR:abc:2', 'cash=EUR%3A%3A2'],
            ['a cash entry with no bounds at all keeps its code', 'cash=EUR', 'cash=EUR%3A%3A'],
            ['a cash entry with no code is dropped entirely', 'cash=:1:2', ''],
            ['a key no filter declares is dropped', 'ghost=1', ''],
            ['a numeric parameter that is not a number is dropped', 'id_min=abc', ''],
        ])('%s', (_label, query, expected) => {
            expect(roundTrip(query)).toBe(expected);
        });

        it.each(['page=1', 'without_asset=false', 'types=BUY, SELL', 'broker_ids=3,abc', 'cash=eur:1:2', 'cash=EUR:abc:2', 'cash=EUR', 'ghost=1', 'id_min=abc'])('reaches a fixed point on %s', (query) => {
            // Normalisation has to settle in one pass. If it did not, the page
            // would rewrite the address bar on every navigation, and the back
            // button would walk through URLs the user never chose.
            const once = roundTrip(query);
            expect(roundTrip(once)).toBe(once);
        });
    });

    it('writes a bare path when nothing is filtered', () => {
        expect(buildTransactionsFiltersUrl({})).toBe('/transactions');
        expect(buildTransactionsFiltersUrl(parseTransactionFilters(new URLSearchParams('')))).toBe('/transactions');
    });

    it('writes a query only for what is set', () => {
        expect(buildTransactionsFiltersUrl({broker_id: 3})).toBe('/transactions?broker_id=3');
    });
});

// =============================================================================
//  parseTransactionFilters — the cash grammar, which is the only hand-written one
// =============================================================================

describe('the cash grammar', () => {
    function cashOf(query: string) {
        return parseTransactionFilters(new URLSearchParams(query)).cash;
    }

    it('reads code, lower bound and upper bound', () => {
        expect(cashOf('cash=EUR:100:200')).toEqual([{code: 'EUR', min: 100, max: 200}]);
    });

    it('reads several brackets separated by commas', () => {
        expect(cashOf('cash=EUR:1:2,USD:3:4')).toEqual([
            {code: 'EUR', min: 1, max: 2},
            {code: 'USD', min: 3, max: 4},
        ]);
    });

    it.each([
        ['no lower bound', 'cash=EUR::200', {code: 'EUR', max: 200}],
        ['no upper bound', 'cash=EUR:100:', {code: 'EUR', min: 100}],
        ['no bounds at all', 'cash=EUR::', {code: 'EUR'}],
        ['no bounds and no separators', 'cash=EUR', {code: 'EUR'}],
        ['a zero bound, which is a bound', 'cash=EUR:0:0', {code: 'EUR', min: 0, max: 0}],
        ['a decimal bound', 'cash=EUR:1.5:2.5', {code: 'EUR', min: 1.5, max: 2.5}],
        ['a negative bound', 'cash=EUR:-5:-1', {code: 'EUR', min: -5, max: -1}],
    ])('accepts %s', (_label, query, expected) => {
        expect(cashOf(query)).toEqual([expected]);
    });

    it.each([
        ['a bound that is not a number', 'cash=EUR:abc:2', {code: 'EUR', max: 2}],
        ['a bound that is infinite', 'cash=EUR:Infinity:2', {code: 'EUR', max: 2}],
    ])('drops %s and keeps the rest of the bracket', (_label, query, expected) => {
        expect(cashOf(query)).toEqual([expected]);
    });

    it('upper-cases the currency code, because the backend expects it that way', () => {
        expect(cashOf('cash=usd:1:2')).toEqual([{code: 'USD', min: 1, max: 2}]);
    });

    it.each([
        ['the parameter is absent', ''],
        ['the parameter is empty', 'cash='],
        ['every entry is blank', 'cash=,,'],
        ['the only entry has no code', 'cash=:1:2'],
    ])('produces no cash filter when %s', (_label, query) => {
        expect(cashOf(query)).toBeUndefined();
    });

    it('drops only the code-less entry, not the whole parameter', () => {
        expect(cashOf('cash=:1:2,USD:3:4')).toEqual([{code: 'USD', min: 3, max: 4}]);
    });

    it('ignores whitespace around an entry', () => {
        expect(cashOf('cash=EUR:1:2, USD:3:4')).toEqual([
            {code: 'EUR', min: 1, max: 2},
            {code: 'USD', min: 3, max: 4},
        ]);
    });
});

// =============================================================================
//  toTransactionColumnFilters — filters as the table's column chips
// =============================================================================

describe('toTransactionColumnFilters', () => {
    it('produces nothing when nothing is filtered', () => {
        expect(toTransactionColumnFilters({})).toEqual({});
    });

    it.each([
        ['types', {types: []}],
        ['tags', {tags: []}],
        ['cash', {cash: []}],
        ['broker ids', {broker_ids: []}],
        ['asset ids', {asset_ids: []}],
    ])('produces no chip for an empty list of %s', (_label, filters) => {
        expect(toTransactionColumnFilters(filters)).toEqual({});
    });

    it('renders types as a single-choice enum and tags as a multi-enum', () => {
        expect(toTransactionColumnFilters({types: ['BUY', 'SELL'], tags: ['a', 'b']})).toEqual({
            types: {type: 'enum', selected: ['BUY', 'SELL']},
            tags: {type: 'multi-enum', selected: ['a', 'b']},
        });
    });

    it('renders a single broker as a one-entry selection', () => {
        expect(toTransactionColumnFilters({broker_id: 3}).broker_id).toEqual({type: 'enum', selected: ['3']});
    });

    it('renders several brokers as a multi-entry selection', () => {
        expect(toTransactionColumnFilters({broker_ids: [3, 7]}).broker_id).toEqual({type: 'enum', selected: ['3', '7']});
    });

    it('lets the single broker win when a link carries both forms', () => {
        // Only a hand-written URL can hold both; `applyTransactionColumnFilters`
        // never emits them together. The chip shows the singular one.
        expect(toTransactionColumnFilters({broker_id: 3, broker_ids: [7, 11]}).broker_id).toEqual({type: 'enum', selected: ['3']});
    });

    it('renders several assets as a multi-entry selection', () => {
        expect(toTransactionColumnFilters({asset_ids: [12, 15]}).asset_id).toEqual({type: 'enum', selected: ['12', '15']});
    });

    it('puts the no-asset sentinel first, ahead of any asset id', () => {
        expect(toTransactionColumnFilters({without_asset: true, asset_ids: [12]}).asset_id).toEqual({type: 'enum', selected: ['__null__', '12']});
    });

    it.each([
        ['both ends', {date_start: '2024-01-01', date_end: '2024-12-31'}, {type: 'date', from: '2024-01-01', to: '2024-12-31'}],
        ['a start alone', {date_start: '2024-01-01'}, {type: 'date', from: '2024-01-01', to: undefined}],
        ['an end alone', {date_end: '2024-12-31'}, {type: 'date', from: undefined, to: '2024-12-31'}],
    ])('renders a date range with %s', (_label, filters, expected) => {
        expect(toTransactionColumnFilters(filters).date).toEqual(expected);
    });

    it.each([
        ['id', 'id_min', 'id_max', 'id'],
        ['quantity', 'qty_min', 'qty_max', 'qty'],
    ] as const)('renders a %s range from either bound alone', (_label, minKey, maxKey, column) => {
        expect(toTransactionColumnFilters({[minKey]: 5})[column]).toEqual({type: 'number', min: 5, max: undefined});
        expect(toTransactionColumnFilters({[maxKey]: 9})[column]).toEqual({type: 'number', min: undefined, max: 9});
        expect(toTransactionColumnFilters({[minKey]: 0})[column]).toEqual({type: 'number', min: 0, max: undefined});
    });

    it('copies the cash brackets instead of sharing them', () => {
        // The chips are editable; sharing the array would let a chip edit
        // rewrite the filter map behind the page's back.
        const filters: TransactionFilterMap = {cash: [{code: 'EUR', min: 1, max: 2}]};
        const chips = toTransactionColumnFilters(filters);

        expect(chips.cash).toEqual({type: 'currency-stack', items: [{code: 'EUR', min: 1, max: 2}]});
        const items = (chips.cash as {items: Array<{code: string}>}).items;
        expect(items[0]).not.toBe(filters.cash![0]);
    });

    it('renders no currency chip, because currency is a page control and not a column', () => {
        expect(toTransactionColumnFilters({currency: 'EUR'})).toEqual({});
    });
});

// =============================================================================
//  applyTransactionColumnFilters — chips edited by the user, back into filters
// =============================================================================

describe('applyTransactionColumnFilters', () => {
    /** A filter map already in normal form, as parsing a sane link produces. */
    const NORMAL_FORM: Array<[string, string]> = [
        ['a single broker', 'broker_id=3'],
        ['several brokers', 'broker_ids=3,7'],
        ['a single asset', 'asset_id=12'],
        ['several assets', 'asset_ids=12,15'],
        ['no asset', 'without_asset=true'],
        ['no asset plus assets', 'without_asset=true&asset_ids=12'],
        ['types', 'types=BUY,SELL'],
        ['tags', 'tags=dividend'],
        ['a date range', 'date_start=2024-01-01&date_end=2024-12-31'],
        ['a cash bracket', 'cash=EUR:100:200'],
        ['an id range', 'id_min=10&id_max=99'],
        ['a quantity range', 'qty_min=0&qty_max=500'],
        ['everything at once', 'broker_ids=3,7&types=BUY&tags=x&date_start=2024-01-01&cash=EUR:1:2&id_min=1&qty_max=9'],
    ];

    it.each(NORMAL_FORM)('is a no-op when the chips it is given are the ones it just rendered — %s', (_label, query) => {
        // The page renders chips from its filters on every mount. If reading
        // them back changed anything, mounting the table would navigate.
        const filters = parseTransactionFilters(new URLSearchParams(query));

        expect(applyTransactionColumnFilters(filters, toTransactionColumnFilters(filters))).toBeNull();
    });

    it('is a no-op when there are no chips and no filters', () => {
        expect(applyTransactionColumnFilters({}, {})).toBeNull();
    });

    it('ignores a chip whose value is missing', () => {
        const record = {types: undefined as unknown as FilterValue};
        expect(applyTransactionColumnFilters({}, record)).toBeNull();
    });

    it('ignores a chip for a column it does not know', () => {
        expect(applyTransactionColumnFilters({}, {ghost: {type: 'enum', selected: ['1']}})).toBeNull();
    });

    it.each([
        ['types', {types: {type: 'text', value: 'x', matchMode: 'contains'}}],
        ['tags', {tags: {type: 'enum', selected: ['a']}}],
        ['broker_id', {broker_id: {type: 'multi-enum', selected: ['1']}}],
        ['asset_id', {asset_id: {type: 'text', value: '1', matchMode: 'contains'}}],
        ['date', {date: {type: 'text', value: '2024', matchMode: 'contains'}}],
        ['cash', {cash: {type: 'enum', selected: ['EUR']}}],
        ['id', {id: {type: 'enum', selected: ['1']}}],
        ['qty', {qty: {type: 'enum', selected: ['1']}}],
    ] as const)('ignores a %s chip carrying the wrong kind of value', (_label, record) => {
        expect(applyTransactionColumnFilters({}, record as unknown as Record<string, FilterValue>)).toBeNull();
    });

    describe('reading a chip back into filters', () => {
        it('takes a list of types', () => {
            expect(applyTransactionColumnFilters({}, {types: {type: 'enum', selected: ['BUY', 'SELL']}})?.types).toEqual(['BUY', 'SELL']);
        });

        it('takes a list of tags', () => {
            expect(applyTransactionColumnFilters({}, {tags: {type: 'multi-enum', selected: ['a']}})?.tags).toEqual(['a']);
        });

        it('takes one broker as the singular form', () => {
            const next = applyTransactionColumnFilters({}, {broker_id: {type: 'enum', selected: ['3']}});
            expect(next?.broker_id).toBe(3);
            expect(next?.broker_ids).toBeUndefined();
        });

        it('takes two brokers as the plural form', () => {
            const next = applyTransactionColumnFilters({}, {broker_id: {type: 'enum', selected: ['3', '7']}});
            expect(next?.broker_id).toBeUndefined();
            expect(next?.broker_ids).toEqual([3, 7]);
        });

        it('takes one asset as the singular form', () => {
            const next = applyTransactionColumnFilters({}, {asset_id: {type: 'enum', selected: ['12']}});
            expect(next?.asset_id).toBe(12);
            expect(next?.asset_ids).toBeUndefined();
        });

        it('takes two assets as the plural form', () => {
            expect(applyTransactionColumnFilters({}, {asset_id: {type: 'enum', selected: ['12', '15']}})?.asset_ids).toEqual([12, 15]);
        });

        it('drops an asset entry that is not a number', () => {
            expect(applyTransactionColumnFilters({}, {asset_id: {type: 'enum', selected: ['12', 'oops']}})?.asset_id).toBe(12);
        });

        it('takes a date range', () => {
            const next = applyTransactionColumnFilters({}, {date: {type: 'date', from: '2024-01-01', to: '2024-12-31'}});
            expect([next?.date_start, next?.date_end]).toEqual(['2024-01-01', '2024-12-31']);
        });

        it('takes cash brackets, copied rather than shared', () => {
            const items = [{code: 'EUR', min: 1, max: 2}];
            const next = applyTransactionColumnFilters({}, {cash: {type: 'currency-stack', items}});

            expect(next?.cash).toEqual(items);
            expect(next?.cash?.[0]).not.toBe(items[0]);
        });

        it.each([
            ['id', 'id', 'id_min', 'id_max'],
            ['quantity', 'qty', 'qty_min', 'qty_max'],
        ] as const)('takes a %s range, zero included', (_label, column, minKey, maxKey) => {
            const next = applyTransactionColumnFilters({}, {[column]: {type: 'number', min: 0, max: 9}});
            expect([next?.[minKey], next?.[maxKey]]).toEqual([0, 9]);
        });
    });

    describe('clearing a chip clears the filter', () => {
        it.each([
            ['types', 'types=BUY', {types: {type: 'enum', selected: []}}, 'types'],
            ['tags', 'tags=a', {tags: {type: 'multi-enum', selected: []}}, 'tags'],
            ['a single broker', 'broker_id=3', {broker_id: {type: 'enum', selected: []}}, 'broker_id'],
            ['several brokers', 'broker_ids=3,7', {broker_id: {type: 'enum', selected: []}}, 'broker_ids'],
            ['an asset', 'asset_id=12', {asset_id: {type: 'enum', selected: []}}, 'asset_id'],
            ['the no-asset sentinel', 'without_asset=true', {asset_id: {type: 'enum', selected: []}}, 'without_asset'],
        ] as const)('%s', (_label, query, record, cleared) => {
            const filters = parseTransactionFilters(new URLSearchParams(query));
            const next = applyTransactionColumnFilters(filters, record as unknown as Record<string, FilterValue>);

            expect(next).not.toBeNull();
            expect(next?.[cleared]).toBeUndefined();
        });

        it('clears a date range emptied from both ends', () => {
            const filters = parseTransactionFilters(new URLSearchParams('date_start=2024-01-01&date_end=2024-12-31'));
            const next = applyTransactionColumnFilters(filters, {date: {type: 'date', from: '', to: ''}});

            expect(next).not.toBeNull();
            expect([next?.date_start, next?.date_end]).toEqual([undefined, undefined]);
        });

        it('clears cash brackets emptied to none', () => {
            const filters = parseTransactionFilters(new URLSearchParams('cash=EUR:1:2'));
            const next = applyTransactionColumnFilters(filters, {cash: {type: 'currency-stack', items: []}});

            expect(next).not.toBeNull();
            expect(next?.cash).toBeUndefined();
        });

        it('clears a chip a caller simply stopped sending', () => {
            const filters = parseTransactionFilters(new URLSearchParams('types=BUY&tags=a&cash=EUR:1:2&id_min=1'));
            const next = applyTransactionColumnFilters(filters, {});

            expect(next).not.toBeNull();
            expect([next?.types, next?.tags, next?.cash, next?.id_min]).toEqual([undefined, undefined, undefined, undefined]);
        });
    });

    describe('what survives a filter change', () => {
        it('sends the reader back to the first page', () => {
            const filters = parseTransactionFilters(new URLSearchParams('page=7&types=BUY'));
            expect(applyTransactionColumnFilters(filters, {types: {type: 'enum', selected: ['SELL']}})?.page).toBe(1);
        });

        it('keeps the page when nothing changed, because nothing is returned at all', () => {
            const filters = parseTransactionFilters(new URLSearchParams('page=7&types=BUY'));
            expect(applyTransactionColumnFilters(filters, {types: {type: 'enum', selected: ['BUY']}})).toBeNull();
        });

        it('keeps the page size, which the chips do not control', () => {
            const filters = parseTransactionFilters(new URLSearchParams('page_size=25'));
            expect(applyTransactionColumnFilters(filters, {types: {type: 'enum', selected: ['BUY']}})?.page_size).toBe(25);
        });

        it('keeps the currency, which is a page control and not a column', () => {
            const filters = parseTransactionFilters(new URLSearchParams('currency=EUR'));
            expect(applyTransactionColumnFilters(filters, {types: {type: 'enum', selected: ['BUY']}})?.currency).toBe('EUR');
        });

        it('does not mutate the filters it was given', () => {
            const filters = parseTransactionFilters(new URLSearchParams('types=BUY&page=7'));
            const before = JSON.stringify(filters);

            applyTransactionColumnFilters(filters, {types: {type: 'enum', selected: ['SELL']}});

            expect(JSON.stringify(filters)).toBe(before);
        });
    });

    describe('a link that carries both the singular and the plural form', () => {
        // Nothing in the app emits these together; a hand-edited URL can. The
        // first pass through the chips normalises them to one form, which is a
        // visible change and therefore also resets the page.
        it.each([
            ['brokers', 'broker_id=3&broker_ids=7,11', 'broker_id', 3, 'broker_ids'],
            ['assets', 'asset_id=12&asset_ids=15', 'asset_id', 12, 'asset_ids'],
        ] as const)('collapses %s to the singular form', (_label, query, keptKey, keptValue, droppedKey) => {
            const filters = parseTransactionFilters(new URLSearchParams(query));
            const next = applyTransactionColumnFilters(filters, toTransactionColumnFilters(filters));

            expect(next).not.toBeNull();
            expect(next?.[keptKey]).toBe(keptValue);
            expect(next?.[droppedKey]).toBeUndefined();
        });

        it('turns a single asset into the plural form when the no-asset sentinel is also on', () => {
            const filters = parseTransactionFilters(new URLSearchParams('without_asset=true&asset_id=42'));
            const next = applyTransactionColumnFilters(filters, toTransactionColumnFilters(filters));

            expect(next?.without_asset).toBe(true);
            expect(next?.asset_id).toBeUndefined();
            expect(next?.asset_ids).toEqual([42]);
        });
    });
});
