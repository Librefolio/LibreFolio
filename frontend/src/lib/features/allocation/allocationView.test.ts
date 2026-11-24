/**
 * The answer read as things to draw: pie entries, map data, colour ranks and table rows.
 */
import {describe, expect, it} from 'vitest';
import {assetNamesOf, colorRanksOf, geoData, matrixModel, pieEntries, tableRows} from './allocationView';
import {makeView} from './allocation.fixture';

const geo = makeView({
    slices: [
        {
            key: 'USA',
            asset_id: null,
            amount: '23600.00',
            share_of_selection: '64.00',
            share_of_portfolio: '29.50',
            assets: [
                {asset_id: 1, amount: '19600.00', share_of_slice: '83.05'},
                {asset_id: 2, amount: '4000.00', share_of_slice: '16.95'},
            ],
        },
        {key: 'ITA', asset_id: null, amount: '3000.00', share_of_selection: '8.10', share_of_portfolio: '3.75', assets: [{asset_id: 3, amount: '3000.00', share_of_slice: '100.00'}]},
        {key: 'Unknown', asset_id: null, amount: '500.00', share_of_selection: '1.35', share_of_portfolio: '0.63', assets: []},
    ],
});

describe('pieEntries', () => {
    it('keeps the backend keys, the shares in percent and the amounts', () => {
        expect(pieEntries(geo).map((entry) => [entry.name, entry.value, entry.amount])).toEqual([
            ['USA', 64, 23600],
            ['ITA', 8.1, 3000],
            ['Unknown', 1.35, 500],
        ]);
    });

    it('names the slices of the asset dimension by their asset, with its icon and type', () => {
        const view = makeView({
            dimension: 'asset',
            slices: [
                {key: '2', asset_id: 2, amount: '4000.00', share_of_selection: '100.00', share_of_portfolio: '5.00', assets: []},
                {key: 'Liquidity', asset_id: null, amount: '10.00', share_of_selection: null, share_of_portfolio: null, assets: []},
            ],
        });
        const [asset, cash] = pieEntries(view);
        expect(asset).toMatchObject({name: 'Apple Inc.', id: 2, assetType: 'STOCK'});
        expect(cash, 'the cash has no asset: its key, no id, and a missing share is 0').toMatchObject({name: 'Liquidity', id: null, value: 0});
    });
});

describe('geoData', () => {
    it('is the weight (0–1) and the amount per country, without the buckets that are no country', () => {
        const {data, amounts} = geoData(geo);
        expect(data).toEqual({USA: 0.64, ITA: 0.081});
        expect(amounts).toEqual({USA: 23600, ITA: 3000});
    });
});

describe('colorRanksOf', () => {
    it('ranks the heaviest asset first, the same way for the pie and the history', () => {
        const view = makeView({
            dimension: 'asset',
            slices: [
                {key: '2', asset_id: 2, amount: '4000.00', share_of_selection: '20.00', share_of_portfolio: null, assets: []},
                {key: '1', asset_id: 1, amount: '16000.00', share_of_selection: '80.00', share_of_portfolio: null, assets: []},
            ],
        });
        const ranks = colorRanksOf(view);
        expect(ranks.get(1)).toBe(0);
        expect(ranks.get(2)).toBe(1);
    });
});

describe('tableRows', () => {
    it('lists the slices, then what is excluded, with no share for the excluded', () => {
        const view = makeView({
            ...geo,
            excluded: {
                amount: '9000.00',
                by_bucket: [{key: 'Unknown', amount: '4120.00'}],
                by_asset: [{asset_id: 2, amount: '4000.00'}],
                unattributable: [
                    {reason: 'in_transit', amount: '0.00'},
                    {reason: 'no_country', amount: '880.00'},
                ],
            },
        });
        const rows = tableRows(view, new Set());
        expect(rows.map((row) => row.id)).toEqual(['slice:USA', 'slice:ITA', 'slice:Unknown', 'excluded:bucket:Unknown', 'excluded:asset:2', 'excluded:fixed:no_country']);
        for (const row of rows.filter((r) => r.kind === 'excluded')) {
            expect([row.shareOfSelection, row.shareOfPortfolio]).toEqual([null, null]);
        }
    });

    it('counts the assets of a slice and lets only a slice with assets be opened', () => {
        const [usa, , unknown] = tableRows(geo, new Set());
        expect(usa).toMatchObject({assetCount: 2, expandable: true, expanded: false});
        expect(unknown).toMatchObject({assetCount: 0, expandable: false});
    });

    it('an open slice is followed by its assets, each with its share of the slice', () => {
        const rows = tableRows(geo, new Set(['USA']));
        expect(rows.slice(0, 3).map((row) => [row.id, row.kind])).toEqual([
            ['slice:USA', 'slice'],
            ['detail:USA:1', 'detail'],
            ['detail:USA:2', 'detail'],
        ]);
        expect(rows[1]).toMatchObject({assetId: 1, amount: 19600, shareOfSlice: '83.05'});
        expect(rows[0].expanded).toBe(true);
        expect(
            tableRows(geo, new Set(['Unknown'])).some((row) => row.kind === 'detail'),
            'a slice with no assets does not open',
        ).toBe(false);
    });

    it('the asset dimension and the cash show no count', () => {
        const view = makeView({
            dimension: 'asset',
            excluded: {amount: '0.00', by_bucket: [], by_asset: [], unattributable: []},
            slices: [
                {key: '1', asset_id: 1, amount: '10.00', share_of_selection: '50.00', share_of_portfolio: '5.00', assets: []},
                {key: 'Liquidity', asset_id: null, amount: '10.00', share_of_selection: '50.00', share_of_portfolio: '5.00', assets: []},
            ],
        });
        expect(tableRows(view, new Set()).map((row) => row.assetCount)).toEqual([null, null]);
    });
});

describe('assetNamesOf', () => {
    it('maps the ids the answer lists to their names', () => {
        expect(assetNamesOf(makeView()).get(2)).toBe('Apple Inc.');
    });
});

describe('matrixModel', () => {
    const matrix = {
        rows: ['STOCK', 'BOND'],
        columns: ['USA', 'ITA', 'Unknown'],
        cells: [
            {asset_class: 'STOCK', key: 'USA', amount: '23600.00', share_of_portfolio: '29.50'},
            {asset_class: 'STOCK', key: 'ITA', amount: '3000.00', share_of_portfolio: '3.75'},
            {asset_class: 'BOND', key: 'ITA', amount: '10000.00', share_of_portfolio: '12.50'},
            {asset_class: 'BOND', key: 'Unknown', amount: '0.00', share_of_portfolio: '0.00'},
        ],
        unattributed: [{reason: 'no_country' as const, amount: '880.00'}],
    };
    const view = makeView({dimension: 'geography', matrix});
    const all = () => true;

    it('is nothing when the answer has no matrix (the asset dimension)', () => {
        expect(matrixModel(makeView({matrix: null}), all, new Set())).toBeNull();
    });

    it('is a grid in the order of the rows and the columns, an unlisted or zero cell empty', () => {
        const model = matrixModel(view, all, new Set())!;
        expect(model.rows).toEqual(['STOCK', 'BOND']);
        expect(model.columns).toEqual(['USA', 'ITA', 'Unknown']);
        expect(model.cells.map((row) => row.map((cell) => cell.present))).toEqual([
            [true, true, false],
            [false, true, false],
        ]);
        expect(model.cells[0][0]).toMatchObject({assetClass: 'STOCK', key: 'USA', shareOfPortfolio: '29.50', amount: 23600});
        expect(model.unattributed).toEqual([{reason: 'no_country', amount: 880}]);
    });

    it('tints in proportion to the heaviest cell, and not an empty one', () => {
        const model = matrixModel(view, all, new Set())!;
        expect(model.cells[0][0].intensity).toBe(1);
        expect(model.cells[1][1].intensity).toBeCloseTo(12.5 / 29.5, 5);
        expect(model.cells[1][0].intensity).toBe(0);
    });

    it('marks as selected the cells of a class that is on, outside the columns taken out', () => {
        const model = matrixModel(view, (assetClass) => assetClass === 'STOCK', new Set(['Unknown']))!;
        expect(model.cells.map((row) => row.map((cell) => cell.selected))).toEqual([
            [true, true, false],
            [false, false, false],
        ]);
    });

    it('tints one unit for all: a cell whose share rounds to 0.00 stays the lightest, never darker than a real share', () => {
        const mixed = makeView({
            matrix: {
                ...matrix,
                cells: [
                    {asset_class: 'STOCK', key: 'USA', amount: '23600.00', share_of_portfolio: '29.50'},
                    {asset_class: 'STOCK', key: 'ITA', amount: '40.00', share_of_portfolio: '0.00'},
                    {asset_class: 'BOND', key: 'ITA', amount: '10000.00', share_of_portfolio: '12.50'},
                ],
            },
        });
        const model = matrixModel(mixed, all, new Set())!;
        expect(model.cells[0][0].intensity).toBe(1);
        expect(model.cells[0][1].intensity, 'its 40 € is not weighed against percentages').toBe(0);
        expect(model.cells[0][1].present, 'it is still a cell that holds something').toBe(true);
        expect(model.cells[1][1].intensity).toBeCloseTo(12.5 / 29.5, 5);
    });

    it('counts an exclusion only in a dimension that has it: a saved «Other» does not frame-out a column in Area', () => {
        const inArea = makeView({dimension: 'geography', applicable_buckets: ['Unknown'], matrix: {...matrix, columns: ['USA', 'Other', 'Unknown']}});
        const model = matrixModel(inArea, all, new Set(['Other', 'Unknown']))!;
        expect(model.cells[0].map((cell) => [cell.key, cell.selected])).toEqual([
            ['USA', true],
            ['Other', true],
            ['Unknown', false],
        ]);
    });

    it('a row of shares the backend did not send (NAV at or below zero) is still drawn, from the amounts', () => {
        const noShare = makeView({matrix: {...matrix, cells: matrix.cells.map((cell) => ({...cell, share_of_portfolio: null}))}});
        const model = matrixModel(noShare, all, new Set())!;
        expect(model.cells[0][0]).toMatchObject({present: true, shareOfPortfolio: null, intensity: 1});
    });
});
