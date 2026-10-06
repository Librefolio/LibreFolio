import {describe, expect, it} from 'vitest';

import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {buildRiskReturnPoints, buildRiskReturnRows, selectKpiWave} from './l3Helpers';

/**
 * Every figure below is invented here, on purpose.
 *
 * The mock dataset these levels are exercised against moves — its window is
 * relative to today and its seeding has been re-tuned more than once — so a spec
 * that asserted a number read from a live payload would be measuring the fixture
 * generator rather than this file. What is pinned here is behaviour: which wave
 * gets chosen, what the chosen perimeter is read from, and which points end up
 * on the chart.
 */
function kpiResult(mode: string | undefined, status: 'ok' | 'unavailable' = 'ok'): RiskAnalyticResult {
    return {
        analytic_code: 'historical_kpi',
        instance_id: `base-${mode ?? 'none'}-historical_kpi`,
        status,
        output: status === 'ok' ? {kind: 'kpi', sortino: 2, sharpe: 1, volatility: 0.1} : null,
        metadata: mode === undefined ? {} : {mode},
    } as unknown as RiskAnalyticResult;
}

function riskReturnResult(output: Record<string, unknown>): RiskAnalyticResult {
    return {
        analytic_code: 'asset_risk_return',
        instance_id: 'base-current_composition-asset_risk_return',
        status: 'ok',
        output: {kind: 'risk_return', ...output},
    } as unknown as RiskAnalyticResult;
}

function comparisonResult(output: Record<string, unknown>): RiskAnalyticResult {
    return {
        analytic_code: 'comparison',
        instance_id: 'single-comparison',
        status: 'ok',
        output: {kind: 'comparison', comparison_asset_id: 11, ...output},
    } as unknown as RiskAnalyticResult;
}

describe('selectKpiWave', () => {
    it('prefers the current composition, because that is the question L3 asks', () => {
        const wave = selectKpiWave([kpiResult('current_composition')], [kpiResult('historical')]);
        expect(wave.perimeter).toBe('current_composition');
        expect(wave.results[0].instance_id).toBe('base-current_composition-historical_kpi');
    });

    it('falls back to the historical wave when the backend does not offer the mode', () => {
        // An older install, or any scope where current composition does not apply:
        // the request is never even sent, so the current wave simply has no KPI.
        const wave = selectKpiWave([], [kpiResult('historical')]);
        expect(wave.perimeter).toBe('historical');
        expect(wave.results).toHaveLength(1);
    });

    it('falls back when the current-composition KPI came back without an output', () => {
        const wave = selectKpiWave([kpiResult('current_composition', 'unavailable')], [kpiResult('historical')]);
        expect(wave.perimeter).toBe('historical');
    });

    it('reads the perimeter from the payload, not from which array it came out of', () => {
        // Deliberately contradictory: a result sitting in the current wave that
        // declares itself historical. The payload wins, because the payload is the
        // one that knows what it measured.
        const wave = selectKpiWave([kpiResult('historical')], []);
        expect(wave.perimeter).toBe('historical');
    });

    it('declares nothing rather than guessing when the metadata carries no mode', () => {
        expect(selectKpiWave([kpiResult(undefined)], []).perimeter).toBeNull();
    });

    it('has nothing to declare when neither wave measured anything', () => {
        const historical: RiskAnalyticResult[] = [];
        const wave = selectKpiWave([], historical);
        expect(wave.perimeter).toBeNull();
        expect(wave.results).toBe(historical);
    });
});

describe('buildRiskReturnPoints', () => {
    const base = {
        assetNames: {1: 'Apple', 2: 'Bitcoin'},
        benchmarkName: 'MSCI World',
        portfolioLabel: 'Portfolio',
    };

    it('draws the portfolio, every asset and the benchmark, and nothing else', () => {
        const points = buildRiskReturnPoints({
            ...base,
            riskReturnResult: riskReturnResult({
                portfolio_volatility: 0.06,
                portfolio_expected_annual_return: 0.09,
                cash_weight: 0.5,
                items: [
                    {asset_id: 1, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15},
                    {asset_id: 2, weight: 0.2, volatility: 0.8, expected_annual_return: -0.1},
                ],
            }),
            comparisonResult: comparisonResult({comparison_volatility: 0.17, comparison_expected_annual_return: 0.12}),
        });

        expect(points.map((point) => point.role)).toEqual(['portfolio', 'asset', 'asset', 'benchmark']);
        expect(points.map((point) => point.name)).toEqual(['Portfolio', 'Apple', 'Bitcoin', 'MSCI World']);
    });

    it('sizes the portfolio as the whole of itself and the assets by their real weight', () => {
        const points = buildRiskReturnPoints({
            ...base,
            riskReturnResult: riskReturnResult({
                portfolio_volatility: 0.06,
                portfolio_expected_annual_return: 0.09,
                cash_weight: 0.5,
                items: [{asset_id: 1, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15}],
            }),
            comparisonResult: null,
        });

        expect(points[0].weight).toBe(1);
        // Not renormalised to the invested part: the asset bubbles are meant to fall
        // short of the whole, and the shortfall is the cash.
        expect(points[1].weight).toBe(0.3);
    });

    it('never places cash, even though the model says it returns exactly zero', () => {
        const result = riskReturnResult({
            portfolio_volatility: 0.06,
            portfolio_expected_annual_return: 0.09,
            cash_weight: 0.49,
            items: [{asset_id: 1, weight: 0.51, volatility: 0.2, expected_annual_return: 0.15}],
        });
        const points = buildRiskReturnPoints({...base, riskReturnResult: result, comparisonResult: null});

        expect(points.every((point) => point.volatility !== 0 || point.annualReturn !== 0)).toBe(true);
    });

    it('drops a point it cannot place instead of pinning it to an axis', () => {
        const points = buildRiskReturnPoints({
            ...base,
            riskReturnResult: riskReturnResult({
                portfolio_volatility: 0.06,
                portfolio_expected_annual_return: 0.09,
                items: [
                    {asset_id: 1, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15},
                    {asset_id: 2, weight: 0.2, volatility: null, expected_annual_return: -0.1},
                ],
            }),
            comparisonResult: null,
        });

        expect(points.map((point) => point.id)).toEqual(['portfolio', 'asset-1']);
    });

    it('waits for the comparison answer before drawing a benchmark', () => {
        const points = buildRiskReturnPoints({
            ...base,
            riskReturnResult: riskReturnResult({
                portfolio_volatility: 0.06,
                portfolio_expected_annual_return: 0.09,
                items: [{asset_id: 1, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15}],
            }),
            // A comparison that ran against an older backend carries beta but not the
            // reference's own risk and reward.
            comparisonResult: comparisonResult({beta: 0.2}),
        });

        expect(points.some((point) => point.role === 'benchmark')).toBe(false);
    });

    it('names an asset it has no name for rather than dropping it', () => {
        const points = buildRiskReturnPoints({
            ...base,
            assetNames: {},
            riskReturnResult: riskReturnResult({
                portfolio_volatility: 0.06,
                portfolio_expected_annual_return: 0.09,
                items: [{asset_id: 7, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15}],
            }),
            comparisonResult: null,
        });

        expect(points[1].name).toBe('#7');
    });

    it('draws nothing at all when the analytic did not run', () => {
        expect(buildRiskReturnPoints({...base, riskReturnResult: null, comparisonResult: null})).toEqual([]);
    });

    /**
     * A benchmark the reader holds is one dot, not two (developer's review of 05/10/2026), and since
     * the table's reference rows (06/10/2026) that dot keeps its holding's id, `asset-<id>`, so it
     * selects the holding's row; only its role says "benchmark".
     */
    it('draws a held benchmark once: its holding’s dot, asset-<id>, sized by its weight, in the benchmark’s role', () => {
        const points = buildRiskReturnPoints({
            ...base,
            riskReturnResult: riskReturnResult({
                portfolio_volatility: 0.06,
                portfolio_expected_annual_return: 0.09,
                items: [
                    {asset_id: 1, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15},
                    {asset_id: 11, weight: 0.2, volatility: 0.17, expected_annual_return: 0.12},
                ],
            }),
            // The comparison's own coordinates differ from the holding's, as they do on a real
            // calendar: the dot must sit where the holding sits.
            comparisonResult: comparisonResult({comparison_volatility: 0.16, comparison_expected_annual_return: 0.11}),
        });

        expect(points.map((point) => `${point.id}:${point.role}`)).toEqual(['portfolio:portfolio', 'asset-1:asset', 'asset-11:benchmark']);
        const held = points.find((point) => point.id === 'asset-11');
        expect(held, 'the held benchmark is its holding’s dot, with the holding’s coordinates and weight').toMatchObject({volatility: 0.17, annualReturn: 0.12, weight: 0.2});
    });

    it('puts what each dot is on its tooltip’s extra line: a holding’s weight, the benchmark held or not', () => {
        const details = {weight: (share: string) => `weighs ${share}`, benchmark: 'is the benchmark', heldBenchmark: (share: string) => `is the benchmark, held at ${share}`};
        const output = {
            portfolio_volatility: 0.06,
            portfolio_expected_annual_return: 0.09,
            items: [
                {asset_id: 1, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15},
                {asset_id: 2, weight: 0.2, volatility: 0.8, expected_annual_return: -0.1},
            ],
        };

        const unheld = buildRiskReturnPoints({...base, details, riskReturnResult: riskReturnResult(output), comparisonResult: comparisonResult({comparison_volatility: 0.17, comparison_expected_annual_return: 0.12})});
        expect(Object.fromEntries(unheld.map((point) => [point.id, point.detail ?? null]))).toEqual({portfolio: null, 'asset-1': 'weighs 30.0%', 'asset-2': 'weighs 20.0%', benchmark: 'is the benchmark'});

        const held = buildRiskReturnPoints({...base, details, riskReturnResult: riskReturnResult(output), comparisonResult: comparisonResult({comparison_asset_id: 2, comparison_volatility: 0.17, comparison_expected_annual_return: 0.12})});
        expect(Object.fromEntries(held.map((point) => [point.id, point.detail ?? null]))).toEqual({portfolio: null, 'asset-1': 'weighs 30.0%', 'asset-2': 'is the benchmark, held at 20.0%'});

        // Without the sentences, no dot carries a line: the tooltip says what it always said.
        const bare = buildRiskReturnPoints({...base, riskReturnResult: riskReturnResult(output), comparisonResult: comparisonResult({comparison_volatility: 0.17, comparison_expected_annual_return: 0.12})});
        expect(bare.filter((point) => 'detail' in point)).toEqual([]);
    });
});

/**
 * buildRiskReturnRows — L3's table on a portfolio page (developer's review of 06/10/2026: «leviamo le 4
 * card perchè si assorbono nella tabella»). The portfolio opens it, a benchmark nobody holds follows as a
 * row added for the comparison, and every holding the analytic measured comes after, heaviest first.
 *
 * Each row agrees with its own dot: the portfolio's volatility and return are its dot's pair
 * (`asset_risk_return`), its Sortino and Sharpe the KPI's, its beta and correlation the comparison's.
 * The fixtures make every one of those sources disagree with the others, so a row that read the wrong
 * one shows the wrong number rather than a coincidentally right one.
 */
describe('buildRiskReturnRows', () => {
    const base = {
        assetNames: {1: 'Apple', 2: 'Bitcoin', 3: 'Gold'},
        benchmarkName: 'MSCI World',
        portfolioLabel: 'Portfolio',
    };
    /** The KPI `selectKpiWave` picked: its volatility deliberately not the pair's. */
    const KPI = {sortino: 1.68, sharpe: 1.21, volatility: 0.142};
    const OUTPUT = {
        portfolio_volatility: 0.118,
        portfolio_expected_annual_return: 0.071,
        cash_weight: 0.05,
        items: [
            {asset_id: 2, weight: 0.35, volatility: 0.087, expected_annual_return: 0.041},
            {asset_id: 1, weight: 0.6, volatility: 0.152, expected_annual_return: 0.094},
        ],
    };
    /** A benchmark nobody holds: id 11, with its own figures and the portfolio's beta against it. */
    const UNHELD = {beta: 0.91, correlation: 0.62, comparison_volatility: 0.15, comparison_expected_annual_return: 0.058};

    it('opens with the portfolio: added, the whole of itself, under its own label', () => {
        const rows = buildRiskReturnRows({...base, riskReturnResult: riskReturnResult(OUTPUT), comparisonResult: null, portfolioKpi: KPI});

        expect(rows[0]).toMatchObject({assetId: 0, name: 'Portfolio', role: 'portfolio', added: true, weight: 1});
        expect(
            rows.filter((row) => row.role === 'portfolio'),
            'one portfolio row',
        ).toHaveLength(1);
    });

    it('takes the portfolio’s volatility and return from its dot, its Sortino and Sharpe from the KPI, its beta and correlation from the comparison', () => {
        const rows = buildRiskReturnRows({...base, riskReturnResult: riskReturnResult(OUTPUT), comparisonResult: comparisonResult(UNHELD), portfolioKpi: KPI});

        expect(rows[0]).toMatchObject({volatility: 0.118, expectedReturn: 0.071, sortino: 1.68, sharpe: 1.21, beta: 0.91, correlation: 0.62});
    });

    it('without the current-composition answer, keeps the KPI’s own volatility and no return', () => {
        const rows = buildRiskReturnRows({...base, riskReturnResult: null, comparisonResult: null, portfolioKpi: KPI});

        expect(rows, 'the portfolio alone: no holding was measured').toHaveLength(1);
        expect(rows[0]).toMatchObject({role: 'portfolio', volatility: 0.142, expectedReturn: null, sortino: 1.68, sharpe: 1.21});
    });

    it('has no portfolio row when nothing measured the portfolio', () => {
        expect(buildRiskReturnRows({...base, riskReturnResult: null, comparisonResult: null, portfolioKpi: {sortino: null, sharpe: null, volatility: null}})).toEqual([]);
    });

    it('leaves the portfolio’s beta and correlation not calculated without a comparison, and unmeasured when the comparison has none', () => {
        const without = buildRiskReturnRows({...base, riskReturnResult: riskReturnResult(OUTPUT), comparisonResult: null, portfolioKpi: KPI});
        expect(without[0].beta, 'no comparison asked: not calculated here').toBeUndefined();
        expect(without[0].correlation).toBeUndefined();

        const blank = buildRiskReturnRows({...base, riskReturnResult: riskReturnResult(OUTPUT), comparisonResult: comparisonResult({beta: null}), portfolioKpi: KPI});
        expect(blank[0].beta, 'a comparison that measured no beta: measured, and not measurable').toBeNull();
        expect(blank[0].correlation).toBeNull();
    });

    it('adds a benchmark nobody holds as a row of its own, second, with no weight, from the comparison', () => {
        const rows = buildRiskReturnRows({...base, riskReturnResult: riskReturnResult(OUTPUT), comparisonResult: comparisonResult(UNHELD), portfolioKpi: KPI});

        expect(rows.map((row) => `${row.assetId}:${row.role ?? 'asset'}`)).toEqual(['0:portfolio', '11:benchmark', '1:asset', '2:asset']);
        expect(rows[1]).toMatchObject({assetId: 11, name: 'MSCI World', role: 'benchmark', added: true, isReference: true, weight: null, volatility: 0.15, expectedReturn: 0.058});
        // Its ratios are the comparison's own when it sends them, and not calculated until then.
        expect(rows[1].sortino).toBeUndefined();
        expect(rows[1].sharpe).toBeUndefined();
        const withRatios = buildRiskReturnRows({...base, riskReturnResult: riskReturnResult(OUTPUT), comparisonResult: comparisonResult({...UNHELD, comparison_sortino: 0.52, comparison_sharpe: null}), portfolioKpi: KPI});
        expect(withRatios[1]).toMatchObject({sortino: 0.52, sharpe: null});
    });

    it('names an unheld benchmark by its name, else by the panel’s, else by its id', () => {
        const named = (benchmarkName: string | null, assetNames: Record<number, string>) => buildRiskReturnRows({...base, benchmarkName, assetNames, riskReturnResult: riskReturnResult(OUTPUT), comparisonResult: comparisonResult(UNHELD), portfolioKpi: KPI})[1].name;

        expect(named('MSCI World', {11: 'Panel name'})).toBe('MSCI World');
        expect(named(null, {11: 'Panel name'})).toBe('Panel name');
        expect(named(null, {})).toBe('#11');
    });

    it('marks a benchmark the reader holds on the holding’s own row, and adds none', () => {
        const rows = buildRiskReturnRows({...base, riskReturnResult: riskReturnResult(OUTPUT), comparisonResult: comparisonResult({...UNHELD, comparison_asset_id: 2}), portfolioKpi: KPI});

        expect(
            rows.filter((row) => row.added).map((row) => row.role),
            'only the portfolio is added: the benchmark is one of the holdings',
        ).toEqual(['portfolio']);
        const held = rows.filter((row) => row.role === 'benchmark');
        expect(held, 'one benchmark row').toHaveLength(1);
        // The holding's own figures, not the comparison's: the row agrees with its dot.
        expect(held[0]).toMatchObject({assetId: 2, name: 'Bitcoin', isReference: true, weight: 0.35, volatility: 0.087, expectedReturn: 0.041});
        expect(held[0].added, 'a held benchmark is not added').toBeFalsy();
        expect(rows.find((row) => row.assetId === 1)?.isReference, 'every other holding is no reference').toBe(false);
    });

    it('lists the holdings heaviest first, one without a weight last, ties by id', () => {
        const rows = buildRiskReturnRows({
            ...base,
            riskReturnResult: riskReturnResult({
                ...OUTPUT,
                items: [
                    {asset_id: 5, weight: 0.1, volatility: 0.2, expected_annual_return: 0.1},
                    {asset_id: 8, weight: null, volatility: 0.2, expected_annual_return: 0.1},
                    {asset_id: 4, weight: 0.4, volatility: 0.2, expected_annual_return: 0.1},
                    {asset_id: 1, weight: 0.2, volatility: 0.2, expected_annual_return: 0.1},
                    {asset_id: 3, weight: 0.4, volatility: 0.2, expected_annual_return: 0.1},
                ],
            }),
            comparisonResult: null,
            portfolioKpi: KPI,
        });

        expect(rows.map((row) => row.assetId)).toEqual([0, 3, 4, 1, 5, 8]);
    });

    it('reads a holding’s figures off its item, and names one it has no name for by its id', () => {
        const rows = buildRiskReturnRows({...base, assetNames: {1: 'Apple'}, riskReturnResult: riskReturnResult(OUTPUT), comparisonResult: null, portfolioKpi: KPI});

        expect(rows.find((row) => row.assetId === 1)).toMatchObject({name: 'Apple', weight: 0.6, volatility: 0.152, expectedReturn: 0.094});
        expect(rows.find((row) => row.assetId === 2)).toMatchObject({name: '#2', weight: 0.35, volatility: 0.087, expectedReturn: 0.041});
    });

    /**
     * Three readings of a ratio: a number; `null`, measured and not measurable — the dash with the blank
     * note; `undefined`, not calculated here — a plain dash that claims no attempt. Since Risk's k6
     * (06/10/2026) every item carries its holding's Sortino and Sharpe, a number or `null`; an answer from
     * before the fields carries neither, and only then is a holding's `undefined`.
     */
    it('tells a ratio the item does not carry from one it carries as null', () => {
        const rows = buildRiskReturnRows({
            ...base,
            riskReturnResult: riskReturnResult({
                ...OUTPUT,
                items: [
                    {asset_id: 1, weight: 0.6, volatility: 0.152, expected_annual_return: 0.094, sortino: 0.8, sharpe: null},
                    {asset_id: 2, weight: 0.35, volatility: 0.087, expected_annual_return: 0.041},
                    {asset_id: 3, weight: 0.01, volatility: 0.3, expected_annual_return: 0.2, sortino: undefined, sharpe: Number.NaN},
                ],
            }),
            comparisonResult: null,
            portfolioKpi: KPI,
        });
        const byId = new Map(rows.map((row) => [row.assetId, row]));

        expect(byId.get(1)?.sortino).toBe(0.8);
        expect(byId.get(1)?.sharpe, 'carried as null: measured and not measurable').toBeNull();
        expect(byId.get(2)?.sortino, 'not carried at all: not calculated here').toBeUndefined();
        expect(byId.get(2)?.sharpe).toBeUndefined();
        expect(byId.get(3)?.sortino, 'a field present but undefined is not carried either').toBeUndefined();
        expect(byId.get(3)?.sharpe, 'a field carried as a non-finite number is measured and not measurable').toBeNull();
    });

    /**
     * A holding's beta and correlation against the benchmark are the comparison's item for it (Risk's k6,
     * 06/10/2026: one item per holding, measured in the same request, on the same calendar and with the
     * same pairing as the portfolio's own beta), and they read the three ways every ratio reads:
     *
     *  - the holding has an item: its figures — a flat holding's included, whose beta is 0 and whose
     *    correlation is undefined, so `null`;
     *  - the list came and the holding is not on it: `null`, measured and not measurable — no prepared
     *    series, fewer than two pairs — so the dash with the blank note;
     *  - no comparison, or an answer from before the field: `undefined`, not calculated here.
     *
     * The comparison lists its items by asset id and the analytic its own way (holding 2 first in
     * `OUTPUT`), so a row that took the item at its own position would show its neighbour's figures.
     */
    it('takes each holding’s beta and correlation from the comparison’s item for it, by asset id, never by position', () => {
        const rows = buildRiskReturnRows({
            ...base,
            riskReturnResult: riskReturnResult(OUTPUT),
            comparisonResult: comparisonResult({
                ...UNHELD,
                items: [
                    {asset_id: 1, beta: 1.07, correlation: 0.74},
                    {asset_id: 2, beta: 0.38, correlation: 0.29},
                ],
            }),
            portfolioKpi: KPI,
        });
        const byId = new Map(rows.map((row) => [row.assetId, row]));

        expect(byId.get(1), 'holding 1: its own item’s figures').toMatchObject({beta: 1.07, correlation: 0.74});
        expect(byId.get(2), 'holding 2: its own item’s figures').toMatchObject({beta: 0.38, correlation: 0.29});
        // The portfolio's pair stays the comparison's own, and no item is its.
        expect(rows[0]).toMatchObject({role: 'portfolio', beta: 0.91, correlation: 0.62});
    });

    it('reads a holding the list leaves out as measured and not measurable, and a flat one as 0 and null — never one as the other', () => {
        const rows = buildRiskReturnRows({
            ...base,
            riskReturnResult: riskReturnResult({...OUTPUT, items: [...OUTPUT.items, {asset_id: 3, weight: 0.01, volatility: 0, expected_annual_return: 0}]}),
            comparisonResult: comparisonResult({
                ...UNHELD,
                items: [
                    {asset_id: 1, beta: 1.07, correlation: 0.74},
                    {asset_id: 3, beta: 0, correlation: null},
                ],
            }),
            portfolioKpi: KPI,
        });
        const byId = new Map(rows.map((row) => [row.assetId, row]));

        // Barrier: the list was read — the holding on it carries its own figures.
        expect(byId.get(1)).toMatchObject({beta: 1.07, correlation: 0.74});
        expect(byId.get(2)?.beta, 'left out of the list: measured, and not measurable — never "not calculated", never 0').toBeNull();
        expect(byId.get(2)?.correlation, 'left out of the list: measured, and not measurable').toBeNull();
        expect(byId.get(3)?.beta, 'a flat holding moves with nothing: its beta is 0, a figure, not a blank').toBe(0);
        expect(byId.get(3)?.correlation, 'and its correlation is undefined: null, measured and not measurable').toBeNull();
    });

    it('leaves every holding’s beta and correlation not calculated without a comparison, or with an answer from before the field', () => {
        const cases = [
            {what: 'no comparison', rows: buildRiskReturnRows({...base, riskReturnResult: riskReturnResult(OUTPUT), comparisonResult: null, portfolioKpi: KPI})},
            {what: 'a comparison without items', rows: buildRiskReturnRows({...base, riskReturnResult: riskReturnResult(OUTPUT), comparisonResult: comparisonResult(UNHELD), portfolioKpi: KPI})},
        ];
        for (const {what, rows} of cases) {
            const holdings = rows.filter((row) => !row.added);
            expect(
                holdings.map((row) => row.assetId),
                `${what}: barrier — both holdings have a row`,
            ).toEqual([1, 2]);
            for (const row of holdings) {
                expect(row.beta, `${what}: holding ${row.assetId}'s beta is not calculated here`).toBeUndefined();
                expect(row.correlation, `${what}: holding ${row.assetId}'s correlation is not calculated here`).toBeUndefined();
            }
        }
        // Barrier: the comparison without items was read — the portfolio carries its beta.
        expect(cases[1].rows[0]).toMatchObject({role: 'portfolio', beta: 0.91, correlation: 0.62});
    });

    it('gives a held benchmark no beta or correlation of its own — it is the reference — while every other holding takes its item', () => {
        // The benchmark itself is never an item (k6): held, its row is the reference, measured against nothing.
        const rows = buildRiskReturnRows({
            ...base,
            riskReturnResult: riskReturnResult(OUTPUT),
            comparisonResult: comparisonResult({...UNHELD, comparison_asset_id: 2, items: [{asset_id: 1, beta: 1.07, correlation: 0.74}]}),
            portfolioKpi: KPI,
        });
        const held = rows.find((row) => row.assetId === 2);

        // Barrier: the list was read — the other holding carries its item.
        expect(rows.find((row) => row.assetId === 1)).toMatchObject({beta: 1.07, correlation: 0.74, isReference: false});
        expect(held, 'the held benchmark is the holding’s own row, marked as the reference').toMatchObject({role: 'benchmark', isReference: true});
        expect(held?.beta, 'the reference has no beta against itself: no value, and no blank to explain either').toBeUndefined();
        expect(held?.correlation, 'the reference has no correlation against itself').toBeUndefined();
    });
});
