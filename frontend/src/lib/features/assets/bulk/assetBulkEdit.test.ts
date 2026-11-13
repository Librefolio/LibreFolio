// @vitest-environment node
/**
 * assetBulkEdit — unit test (Vitest, node). Lane 65, lot F2.
 *
 * The pure half of the bulk edit modal (mockup-AB-v5): what the selected assets hold now, what the draft changes, the
 * payload of `PATCH /assets` and `POST /assets/validate`, and the rows of the summary. No catalogue, no DOM: the
 * modal translates and draws.
 *
 * Contract.
 * - `countValues(values)`: the distinct values with their counts, the most frequent first (ties by first appearance).
 *   Up to 4 distinct values are all shown; beyond 4 the first 3 are shown and `more` says how many are left (`+N`).
 * - `summarizeCurrent(assets)`: counts for the type (a missing type reads OTHER, the backend default), Attivo, Benchmark
 *   (missing = false), the unit (missing or below 1 reads 1), plus «N with icon / N without» and «N distinct URLs / N empty».
 * - A draft field says «leave as is» when it is `null`, `undefined`, an empty or blank text, or (the unit) not a whole
 *   number from 1. `touchedFields(draft)` lists the fields that are not «leave as is», in the order of the zones.
 * - `buildBulkPatch(assets, draft)`: one item per asset that changes, carrying `asset_id` and only the fields whose
 *   value differs from that asset's own current value («already Yes» is left out); an asset with nothing to change is
 *   left out. Items follow the order of the selection. Nothing is ever cleared (no `null` goes out): an empty URL or no
 *   icon is «leave as is».
 * - `summarizeChanges(assets, draft)`: per touched field how many assets change and which already have the value; and
 *   one row per changing asset, with a cell per touched field: before, after and `unchanged` («già …»).
 * - `validateQuoteBase(input)`: `empty`, `notInteger`, `belowOne` or `ok` for what the user typed.
 */
import {describe, expect, it} from 'vitest';
import {FIELD_ORDER, buildBulkPatch, countValues, hasChanges, summarizeChanges, summarizeCurrent, touchedFields, validateQuoteBase, type BulkAsset, type BulkDraft} from './assetBulkEdit';

function asset(id: number, over: Partial<BulkAsset> = {}): BulkAsset {
    return {id, display_name: `Asset ${id}`, asset_type: 'ETF', active: true, is_benchmark: false, quote_base_quantity: 1, icon_url: null, user_url: null, ...over};
}

describe('countValues', () => {
    it('counts distinct values, most frequent first, ties by first appearance', () => {
        const out = countValues(['ETF', 'ETF_STOCK', 'ETF', 'CROWDFUND_REAL_ESTATE', 'ETF']);
        expect(out.groups).toEqual([
            {value: 'ETF', count: 3},
            {value: 'ETF_STOCK', count: 1},
            {value: 'CROWDFUND_REAL_ESTATE', count: 1},
        ]);
        expect(out.distinct).toBe(3);
        expect(out.shown).toEqual(out.groups);
        expect(out.more).toBe(0);
    });

    it('shows up to four distinct values whole', () => {
        const out = countValues(['A', 'B', 'C', 'D']);
        expect(out.shown).toHaveLength(4);
        expect(out.more).toBe(0);
    });

    it('beyond four distinct values shows the first three and «+N» for the rest', () => {
        const out = countValues(['A', 'A', 'A', 'B', 'B', 'C', 'D', 'E', 'F']);
        expect(out.distinct).toBe(6);
        expect(out.shown.map((g) => g.value)).toEqual(['A', 'B', 'C']);
        expect(out.more).toBe(3);
    });

    it('an empty list has no group', () => {
        expect(countValues([])).toEqual({groups: [], shown: [], more: 0, distinct: 0});
    });

    it('counts booleans and numbers by value', () => {
        expect(countValues([true, false, false]).groups).toEqual([
            {value: false, count: 2},
            {value: true, count: 1},
        ]);
        expect(countValues([100, 100, 1]).groups[0]).toEqual({value: 100, count: 2});
    });
});

describe('summarizeCurrent', () => {
    it('reads the selection the way the modal shows it', () => {
        const rows = [
            asset(1, {asset_type: 'ETF', icon_url: 'https://x/a.png', user_url: 'https://u/1'}),
            asset(2, {asset_type: 'ETF', icon_url: 'https://x/b.png', user_url: 'https://u/2'}),
            asset(3, {asset_type: 'ETF_STOCK', icon_url: 'https://x/c.png', user_url: 'https://u/3'}),
            asset(4, {asset_type: 'CROWDFUND_REAL_ESTATE', is_benchmark: true}),
            asset(5, {asset_type: 'ETF'}),
        ];
        const out = summarizeCurrent(rows);
        expect(out.total).toBe(5);
        expect(out.asset_type.groups.map((g) => [g.value, g.count])).toEqual([
            ['ETF', 3],
            ['ETF_STOCK', 1],
            ['CROWDFUND_REAL_ESTATE', 1],
        ]);
        expect(out.active.groups).toEqual([{value: true, count: 5}]);
        expect(out.is_benchmark.groups).toEqual([
            {value: false, count: 4},
            {value: true, count: 1},
        ]);
        expect(out.quote_base_quantity.groups).toEqual([{value: 1, count: 5}]);
        expect(out.icon).toEqual({with: 3, without: 2});
        expect(out.user_url).toEqual({distinct: 3, empty: 2});
    });

    it('a missing type reads OTHER, a missing benchmark reads No, a missing or non-positive unit reads 1', () => {
        const out = summarizeCurrent([asset(1, {asset_type: undefined, is_benchmark: undefined, quote_base_quantity: undefined}), asset(2, {asset_type: null, is_benchmark: null, quote_base_quantity: 0}), asset(3, {quote_base_quantity: null})]);
        expect(out.asset_type.groups).toContainEqual({value: 'OTHER', count: 2});
        expect(out.is_benchmark.groups).toEqual([{value: false, count: 3}]);
        expect(out.quote_base_quantity.groups).toEqual([{value: 1, count: 3}]);
    });

    it('blank texts are empty, and the same URL on two assets is one distinct value', () => {
        const out = summarizeCurrent([asset(1, {user_url: 'https://u/same'}), asset(2, {user_url: 'https://u/same'}), asset(3, {user_url: '   '}), asset(4, {icon_url: ''})]);
        expect(out.user_url).toEqual({distinct: 1, empty: 2});
        expect(out.icon).toEqual({with: 0, without: 4});
    });
});

describe('touchedFields and hasChanges', () => {
    it('an empty draft touches nothing', () => {
        expect(touchedFields({})).toEqual([]);
        expect(touchedFields({asset_type: null, active: null, is_benchmark: undefined, quote_base_quantity: null, icon_url: '', user_url: '  '})).toEqual([]);
    });

    it('lists the touched fields in the order of the zones, not of the draft', () => {
        const draft: BulkDraft = {is_benchmark: true, user_url: 'https://u', asset_type: 'BOND', icon_url: 'https://i.png', quote_base_quantity: 100, active: false};
        expect(touchedFields(draft)).toEqual(['icon_url', 'user_url', 'asset_type', 'quote_base_quantity', 'active', 'is_benchmark']);
        expect(touchedFields(draft)).toEqual([...FIELD_ORDER]);
    });

    it('a unit that is not a whole number from 1 is «leave as is»', () => {
        for (const bad of [0, -5, 1.5, Number.NaN, Number.POSITIVE_INFINITY]) expect(touchedFields({quote_base_quantity: bad}), String(bad)).toEqual([]);
        expect(touchedFields({quote_base_quantity: 1})).toEqual(['quote_base_quantity']);
    });

    it('false is a choice, not «leave as is»', () => {
        expect(touchedFields({active: false, is_benchmark: false})).toEqual(['active', 'is_benchmark']);
    });

    it('hasChanges is false when the draft is empty or every chosen value is already there', () => {
        const rows = [asset(1), asset(2)];
        expect(hasChanges(rows, {})).toBe(false);
        expect(hasChanges(rows, {active: true, asset_type: 'ETF', quote_base_quantity: 1})).toBe(false);
        expect(hasChanges(rows, {is_benchmark: true})).toBe(true);
    });
});

describe('buildBulkPatch', () => {
    it('sends each asset only the fields that change for it: «already Yes» is left out, an unchanged asset does not go', () => {
        const rows = [asset(1, {asset_type: 'ETF', is_benchmark: false}), asset(2, {asset_type: 'ETF', is_benchmark: true}), asset(3, {asset_type: 'ETF_STOCK', is_benchmark: false}), asset(4, {asset_type: 'ETF_STOCK', is_benchmark: true})];
        const items = buildBulkPatch(rows, {asset_type: 'ETF_STOCK', is_benchmark: true});
        expect(items).toEqual([
            {asset_id: 1, asset_type: 'ETF_STOCK', is_benchmark: true},
            {asset_id: 2, asset_type: 'ETF_STOCK'},
            {asset_id: 3, is_benchmark: true},
        ]);
    });

    it('follows the order of the selection', () => {
        const items = buildBulkPatch([asset(9), asset(2), asset(5)], {active: false});
        expect(items.map((i) => i.asset_id)).toEqual([9, 2, 5]);
    });

    it('carries every kind of field', () => {
        const items = buildBulkPatch([asset(1)], {icon_url: 'https://i/new.png', user_url: ' https://u/new ', asset_type: 'BOND', quote_base_quantity: 100, active: false, is_benchmark: true});
        expect(items).toEqual([{asset_id: 1, icon_url: 'https://i/new.png', user_url: 'https://u/new', asset_type: 'BOND', quote_base_quantity: 100, active: false, is_benchmark: true}]);
    });

    it('an empty URL and no icon are «leave as is»: nothing is ever cleared, no null goes out', () => {
        const rows = [asset(1, {user_url: 'https://u/1', icon_url: 'https://i/1.png'})];
        expect(buildBulkPatch(rows, {user_url: '', icon_url: null})).toEqual([]);
        const items = buildBulkPatch(rows, {active: false, user_url: '   ', icon_url: ''});
        expect(items).toEqual([{asset_id: 1, active: false}]);
        expect(JSON.stringify(items)).not.toContain('null');
    });

    it('compares against the asset normalised as the backend reads it', () => {
        const rows = [asset(1, {asset_type: undefined, quote_base_quantity: null, is_benchmark: undefined})];
        expect(buildBulkPatch(rows, {asset_type: 'OTHER', quote_base_quantity: 1, is_benchmark: false})).toEqual([]);
    });

    it("a URL or icon equal to the asset's own is left out", () => {
        const rows = [asset(1, {user_url: 'https://u/same', icon_url: 'https://i/same.png'}), asset(2)];
        expect(buildBulkPatch(rows, {user_url: 'https://u/same', icon_url: 'https://i/same.png'})).toEqual([{asset_id: 2, user_url: 'https://u/same', icon_url: 'https://i/same.png'}]);
    });

    it('an empty selection sends nothing', () => {
        expect(buildBulkPatch([], {active: false})).toEqual([]);
    });

    it('does not read the draft of an unusable unit', () => {
        expect(buildBulkPatch([asset(1)], {quote_base_quantity: 0})).toEqual([]);
        expect(buildBulkPatch([asset(1)], {quote_base_quantity: 2.5})).toEqual([]);
    });
});

describe('summarizeChanges', () => {
    const rows = [
        asset(1, {asset_type: 'ETF', is_benchmark: false}),
        asset(2, {asset_type: 'ETF', is_benchmark: true}),
        asset(3, {asset_type: 'ETF_STOCK', is_benchmark: false}),
        asset(4, {asset_type: 'CROWDFUND_REAL_ESTATE', is_benchmark: false}),
        asset(5, {asset_type: 'ETF_STOCK', is_benchmark: true}),
    ];
    const draft: BulkDraft = {asset_type: 'ETF_STOCK', is_benchmark: true};

    it('counts, per touched field, the assets that change and the ones that already have the value', () => {
        const out = summarizeChanges(rows, draft);
        expect(out.selected).toBe(5);
        expect(out.changing).toBe(4);
        expect(out.touched).toEqual(['asset_type', 'is_benchmark']);
        expect(out.fields).toEqual([
            {field: 'asset_type', after: 'ETF_STOCK', changing: 3, total: 5, alreadyIds: [3, 5]},
            {field: 'is_benchmark', after: true, changing: 3, total: 5, alreadyIds: [2, 5]},
        ]);
    });

    it('has one row per changing asset with a cell per touched field: before, after, «unchanged» where the value is already there', () => {
        const out = summarizeChanges(rows, draft);
        expect(out.rows.map((r) => r.id)).toEqual([1, 2, 3, 4]);
        expect(out.rows[0]).toEqual({
            id: 1,
            name: 'Asset 1',
            cells: [
                {field: 'asset_type', before: 'ETF', after: 'ETF_STOCK', unchanged: false},
                {field: 'is_benchmark', before: false, after: true, unchanged: false},
            ],
        });
        expect(out.rows[1].cells.map((c) => [c.field, c.unchanged])).toEqual([
            ['asset_type', false],
            ['is_benchmark', true],
        ]);
        expect(out.rows[2].cells.map((c) => [c.field, c.unchanged])).toEqual([
            ['asset_type', true],
            ['is_benchmark', false],
        ]);
    });

    it('an asset with nothing to change has no row and is not counted as changing', () => {
        const out = summarizeChanges(rows, draft);
        expect(out.rows.some((r) => r.id === 5)).toBe(false);
    });

    it('the rows are exactly the assets of the payload', () => {
        const items = buildBulkPatch(rows, draft);
        expect(summarizeChanges(rows, draft).rows.map((r) => r.id)).toEqual(items.map((i) => i.asset_id));
    });

    it('a field chosen that no asset changes is still listed, with changing 0', () => {
        const out = summarizeChanges([asset(1), asset(2)], {active: true, is_benchmark: true});
        expect(out.touched).toEqual(['active', 'is_benchmark']);
        expect(out.fields.find((f) => f.field === 'active')).toMatchObject({changing: 0, total: 2, alreadyIds: [1, 2]});
        expect(out.changing).toBe(2);
    });

    it('icon and URL cells carry the texts, null before when the asset had none', () => {
        const out = summarizeChanges([asset(1, {icon_url: 'https://i/old.png'}), asset(2)], {icon_url: 'https://i/new.png'});
        expect(out.rows[0].cells[0]).toEqual({field: 'icon_url', before: 'https://i/old.png', after: 'https://i/new.png', unchanged: false});
        expect(out.rows[1].cells[0]).toEqual({field: 'icon_url', before: null, after: 'https://i/new.png', unchanged: false});
    });

    it('an empty draft summarises nothing', () => {
        const out = summarizeChanges(rows, {});
        expect(out).toMatchObject({selected: 5, changing: 0, touched: [], fields: [], rows: []});
    });
});

describe('validateQuoteBase', () => {
    it.each([
        [null, 'empty'],
        [undefined, 'empty'],
        ['', 'empty'],
        ['   ', 'empty'],
        ['100', 'ok'],
        [100, 'ok'],
        [1, 'ok'],
        ['0', 'belowOne'],
        [0, 'belowOne'],
        ['-3', 'belowOne'],
        ['2.5', 'notInteger'],
        [2.5, 'notInteger'],
        ['abc', 'notInteger'],
        [Number.NaN, 'notInteger'],
    ] as const)('%j → %s', (input, expected) => {
        expect(validateQuoteBase(input)).toBe(expected);
    });
});
