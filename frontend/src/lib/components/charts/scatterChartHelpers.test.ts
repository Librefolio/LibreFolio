/**
 * scatterChartHelpers — unit tests.
 *
 * The scatter exists because `LineChart` cannot draw it: `LineChart` pins every
 * series to `{type: 'category', data: dates}`, and a risk/return plot has no
 * dates. So the first test here is not decorative — it pins the axis type, and
 * it fails the moment somebody "reuses" a time-series option builder for this
 * chart and reintroduces the very mismatch the component was created to avoid.
 *
 * The second thing pinned is the bubble encoding. Radius scales with the SQUARE
 * ROOT of the weight, because a bubble is read by area and area grows with the
 * square of the radius; a linear radius would make a 4× position look 16× as
 * big. That is a defect nobody reports, because the chart still looks like a
 * chart — so it gets an explicit test rather than a comment.
 */
import {describe, expect, it} from 'vitest';

import {buildScatterOption, capitalMarketLine, capitalMarketLineAnchor, colorForRole, isPlaceable, MAX_SYMBOL_PX, MIN_SYMBOL_PX, symbolSizeForWeight, type RiskReturnPoint, type RiskReturnRole, type ScatterOptionInput, type ScatterOptionResult} from './scatterChartHelpers';

const LABELS = {volatility: 'Volatility', return: 'Return', capitalMarketLine: 'CML'};

function point(overrides: Partial<RiskReturnPoint> & Pick<RiskReturnPoint, 'id' | 'role'>): RiskReturnPoint {
    return {name: overrides.id, volatility: 0.1, annualReturn: 0.05, ...overrides};
}

describe('scatterChartHelpers', () => {
    describe('the axes', () => {
        it('puts both coordinates on a numeric axis, never a category one', () => {
            const {option} = buildScatterOption({points: [point({id: 'p', role: 'portfolio'})], labels: LABELS});

            expect(option.xAxis.type).toBe('value');
            expect(option.yAxis.type).toBe('value');
        });

        /** A category axis would silently reindex the data to 0,1,2… and still render. */
        it('never carries the date-series axis data that LineChart needs', () => {
            const {option} = buildScatterOption({points: [point({id: 'p', role: 'portfolio'})], labels: LABELS});

            expect(option.xAxis).not.toHaveProperty('data');
            expect(option.yAxis).not.toHaveProperty('data');
        });
    });

    describe('points it cannot place', () => {
        it('rejects a non-finite coordinate', () => {
            expect(isPlaceable(point({id: 'a', role: 'asset', volatility: Number.NaN}))).toBe(false);
            expect(isPlaceable(point({id: 'b', role: 'asset', annualReturn: Number.POSITIVE_INFINITY}))).toBe(false);
            expect(isPlaceable(point({id: 'c', role: 'asset'}))).toBe(true);
        });

        it('drops them and reports how many, instead of letting ECharts skip them in silence', () => {
            const {droppedCount, isEmpty, option} = buildScatterOption({
                points: [point({id: 'good', role: 'asset'}), point({id: 'bad', role: 'asset', volatility: Number.NaN}), point({id: 'worse', role: 'asset', annualReturn: Number.NaN})],
                labels: LABELS,
            });

            expect(droppedCount).toBe(2);
            expect(isEmpty).toBe(false);
            const assets = option.series.find((s: {id: string}) => s.id === 'scatter-asset');
            expect(assets.data).toHaveLength(1);
            expect(assets.data[0].id).toBe('good');
        });

        it('reports emptiness when nothing survives, so the caller can show an empty state', () => {
            const {isEmpty, droppedCount} = buildScatterOption({points: [point({id: 'bad', role: 'asset', volatility: Number.NaN})], labels: LABELS});

            expect(isEmpty).toBe(true);
            expect(droppedCount).toBe(1);
        });

        it('reports emptiness for no points at all', () => {
            const {isEmpty, option} = buildScatterOption({points: [], labels: LABELS});

            expect(isEmpty).toBe(true);
            expect(option.series).toEqual([]);
        });
    });

    describe('the bubble encoding', () => {
        it('scales area, not radius, with the weight', () => {
            const quarter = symbolSizeForWeight(0.25) - MIN_SYMBOL_PX;
            const whole = symbolSizeForWeight(1) - MIN_SYMBOL_PX;

            // 4x the weight must be 2x the excess diameter — not 4x.
            expect(quarter).toBeCloseTo(whole / 2, 10);
        });

        it('keeps a weightless point visible rather than collapsing it to nothing', () => {
            expect(symbolSizeForWeight(undefined)).toBe(MIN_SYMBOL_PX);
            expect(symbolSizeForWeight(0)).toBe(MIN_SYMBOL_PX);
            expect(symbolSizeForWeight(Number.NaN)).toBe(MIN_SYMBOL_PX);
            expect(symbolSizeForWeight(-0.3)).toBe(MIN_SYMBOL_PX);
        });

        it('never exceeds the ceiling, even for a weight above 1', () => {
            expect(symbolSizeForWeight(1)).toBe(MAX_SYMBOL_PX);
            expect(symbolSizeForWeight(5)).toBe(MAX_SYMBOL_PX);
        });
    });

    describe('the capital market line', () => {
        it('runs from the risk-free rate through the portfolio', () => {
            const line = capitalMarketLine([point({id: 'me', role: 'portfolio', volatility: 0.2, annualReturn: 0.1})], 0.02);

            expect(line).not.toBeNull();
            expect(line![0]).toEqual([0, 0.02]);
            // slope = (0.10 - 0.02) / 0.20 = 0.4, so at x = 0.20 the line is back on the portfolio.
            expect(line![1][0]).toBeCloseTo(0.2, 10);
            expect(line![1][1]).toBeCloseTo(0.1, 10);
        });

        it('extends to the widest volatility on the plot rather than stopping at the portfolio', () => {
            const line = capitalMarketLine([point({id: 'me', role: 'portfolio', volatility: 0.2, annualReturn: 0.1}), point({id: 'wild', role: 'asset', volatility: 0.5, annualReturn: 0.3})], 0.02);

            expect(line![1][0]).toBeCloseTo(0.5, 10);
            expect(line![1][1]).toBeCloseTo(0.02 + 0.4 * 0.5, 10);
        });

        /**
         * The benchmark anchors the line on any plot, a set of assets with no portfolio included
         * (developer's review of 06/10/2026, on Asset Global's lab: «non compare la retta tra 0 e
         * benchmark»): "better paid than the market" needs no aggregate to be true.
         */
        it('runs from the risk-free rate through the benchmark on a plot with no portfolio point', () => {
            const line = capitalMarketLine([point({id: 'a', role: 'asset', volatility: 0.1, annualReturn: 0.05}), point({id: 'b', role: 'benchmark', volatility: 0.2, annualReturn: 0.1})], 0.02);

            expect(line, 'a plot of assets and a benchmark draws no line').not.toBeNull();
            expect(line![0]).toEqual([0, 0.02]);
            // slope = (0.10 - 0.02) / 0.20 = 0.4; the benchmark is the widest dot, so the line ends on it.
            expect(line![1][0]).toBeCloseTo(0.2, 10);
            expect(line![1][1]).toBeCloseTo(0.1, 10);
        });

        it('is absent when the portfolio has no volatility, because the slope is undefined', () => {
            expect(capitalMarketLine([point({id: 'me', role: 'portfolio', volatility: 0})], 0.02)).toBeNull();
        });

        it('ignores a non-finite point when choosing how far to extend', () => {
            const line = capitalMarketLine([point({id: 'me', role: 'portfolio', volatility: 0.2, annualReturn: 0.1}), point({id: 'broken', role: 'asset', volatility: Number.NaN})], 0);

            expect(Number.isFinite(line![1][0])).toBe(true);
            expect(line![1][0]).toBeCloseTo(0.2, 10);
        });

        it('is omitted from the series when it cannot be drawn', () => {
            const {option} = buildScatterOption({points: [point({id: 'a', role: 'asset'})], labels: LABELS});

            expect(option.series.some((s: {id: string}) => s.id === 'capital-market-line')).toBe(false);
        });

        it('is drawn beneath the points and takes no pointer events', () => {
            const {option} = buildScatterOption({points: [point({id: 'me', role: 'portfolio', volatility: 0.2, annualReturn: 0.1})], labels: LABELS});
            const cml = option.series.find((s: {id: string}) => s.id === 'capital-market-line');

            expect(cml.silent).toBe(true);
            expect(cml.z).toBeLessThan(option.series.find((s: {id: string}) => s.id === 'scatter-portfolio').z);
        });

        /**
         * The dot the line runs through (`capitalMarketLineAnchor`): the benchmark wherever one is placed,
         * the portfolio only as the fallback, and nothing when neither has a volatility to give it a slope.
         */
        describe('the dot it runs through', () => {
            it('is the benchmark on a plot with no portfolio point — a set of assets', () => {
                expect(capitalMarketLineAnchor([point({id: 'asset-1', role: 'asset'}), point({id: 'benchmark', role: 'benchmark', volatility: 0.18, annualReturn: 0.07})])).toBe('benchmark');
            });

            it('falls back to the portfolio when no benchmark is placed', () => {
                expect(capitalMarketLineAnchor([point({id: 'portfolio', role: 'portfolio', volatility: 0.15, annualReturn: 0.08}), point({id: 'asset-1', role: 'asset'})])).toBe('portfolio');
            });

            it('is nothing on a plot with neither a benchmark nor a portfolio', () => {
                const plot = [point({id: 'asset-1', role: 'asset', volatility: 0.2}), point({id: 'asset-2', role: 'asset', volatility: 0.3})];

                expect(capitalMarketLineAnchor(plot)).toBeNull();
                expect(capitalMarketLine(plot, 0.02)).toBeNull();
            });

            it('is nothing when the benchmark has no volatility and no portfolio stands in for it', () => {
                const plot = [point({id: 'asset-1', role: 'asset', volatility: 0.2}), point({id: 'benchmark', role: 'benchmark', volatility: 0, annualReturn: 0.03})];

                expect(capitalMarketLineAnchor(plot), 'at zero volatility the slope is undefined: no vertical line').toBeNull();
                expect(capitalMarketLine(plot, 0.02)).toBeNull();
            });
        });
    });

    describe('the three roles', () => {
        it('separates them into their own series', () => {
            const {option} = buildScatterOption({
                points: [point({id: 'me', role: 'portfolio'}), point({id: 'bench', role: 'benchmark'}), point({id: 'a1', role: 'asset'}), point({id: 'a2', role: 'asset'})],
                labels: LABELS,
            });

            const ids = option.series.map((s: {id: string}) => s.id);
            expect(ids).toContain('scatter-portfolio');
            expect(ids).toContain('scatter-benchmark');
            expect(ids).toContain('scatter-asset');
            expect(option.series.find((s: {id: string}) => s.id === 'scatter-asset').data).toHaveLength(2);
        });

        it('draws the individual assets behind the portfolio and the benchmark', () => {
            const {option} = buildScatterOption({
                points: [point({id: 'me', role: 'portfolio'}), point({id: 'bench', role: 'benchmark'}), point({id: 'a1', role: 'asset'})],
                labels: LABELS,
            });

            const z = (id: string) => option.series.find((s: {id: string}) => s.id === id).z;
            expect(z('scatter-asset')).toBeLessThan(z('scatter-portfolio'));
            expect(z('scatter-asset')).toBeLessThan(z('scatter-benchmark'));
        });

        it('omits a series entirely when that role has no points', () => {
            const {option} = buildScatterOption({points: [point({id: 'a1', role: 'asset'})], labels: LABELS});

            expect(option.series.map((s: {id: string}) => s.id)).toEqual(['scatter-asset']);
        });

        it('keeps every series a scatter except the line', () => {
            const {option} = buildScatterOption({
                points: [point({id: 'me', role: 'portfolio', volatility: 0.2, annualReturn: 0.1}), point({id: 'a1', role: 'asset'})],
                labels: LABELS,
            });

            for (const series of option.series) {
                expect(series.type).toBe(series.id === 'capital-market-line' ? 'line' : 'scatter');
            }
        });
    });

    describe('the theme', () => {
        it('gives the three roles distinguishable colours', () => {
            const {option} = buildScatterOption({
                points: [point({id: 'me', role: 'portfolio'}), point({id: 'bench', role: 'benchmark'}), point({id: 'a1', role: 'asset'})],
                labels: LABELS,
            });

            const colorOf = (id: string) => option.series.find((s: {id: string}) => s.id === id).data[0].itemStyle.color;
            const colors = [colorOf('scatter-portfolio'), colorOf('scatter-benchmark'), colorOf('scatter-asset')];

            expect(new Set(colors).size).toBe(3);
        });

        it('changes the palette between light and dark', () => {
            const points = [point({id: 'me', role: 'portfolio'})];
            const light = buildScatterOption({points, labels: LABELS, dark: false});
            const dark = buildScatterOption({points, labels: LABELS, dark: true});

            const colorOf = (result: typeof light) => result.option.series.find((s: {id: string}) => s.id === 'scatter-portfolio').data[0].itemStyle.color;

            expect(colorOf(light)).not.toBe(colorOf(dark));
        });

        it('uses the axis titles it was given rather than inventing any', () => {
            const {option} = buildScatterOption({points: [point({id: 'a', role: 'asset'})], labels: LABELS});

            expect(option.xAxis.name).toBe('Volatility');
            expect(option.yAxis.name).toBe('Return');
        });
    });
});

/**
 * The selected point — the seam the Asset Global lab stands on.
 *
 * The lab sets a table beside this scatter, and a row picked in one has to be findable
 * in the other. So the builder takes the caller's `selectedId` and draws that ONE datum
 * differently: larger and fully opaque; an asset in the selection green, the portfolio
 * and the benchmark in their own role colour.
 *
 * Everything else is the contract of an ADDITIVE change, and it is where most of the
 * assertions below go: the Dashboard passes no selection, and its chart must not move.
 * "Nothing else changed" is asserted by putting the unselected datum back and comparing
 * the WHOLE result with the unselected one — the other points, the line, the axes, the
 * grid, the counts. A list of fields would stay green the day somebody dims the
 * neighbours, or nudges the grid to make room for the bigger dot.
 *
 * Every "changes nothing" case carries a presence barrier: on the same input a placed id
 * DOES change the drawing. Without it the equality would also hold for a builder that
 * ignores `selectedId` altogether — which is exactly today's.
 */
describe('scatterChartHelpers — the selected point', () => {
    /** The light theme's selection colour. The dark one is only required to differ from the dot it replaces. */
    const SELECTED_LIGHT = '#22c55e';
    const ROLES: RiskReturnRole[] = ['portfolio', 'benchmark', 'asset'];

    /**
     * Both surfaces in one set. The Dashboard's: a portfolio of weight 1 — already at
     * `MAX_SYMBOL_PX` — weighted assets, and the line. The lab's: a weightless asset at
     * `MIN_SYMBOL_PX` and the benchmark. Plus a point that cannot be placed.
     *
     * Two assets share a display name, as two share classes of one fund do: a selection
     * matched by name instead of id would light both.
     */
    const INPUT: ScatterOptionInput = {
        labels: LABELS,
        riskFreeRate: 0.02,
        points: [
            point({id: 'portfolio', role: 'portfolio', name: 'My portfolio', volatility: 0.15, annualReturn: 0.08, weight: 1}),
            point({id: 'asset-1', role: 'asset', name: 'Twin Fund', volatility: 0.12, annualReturn: 0.05, weight: 0.25}),
            point({id: 'asset-2', role: 'asset', name: 'Twin Fund', volatility: 0.3, annualReturn: 0.12, weight: 0.64}),
            point({id: 'asset-3', role: 'asset', name: 'Lone Stock', volatility: 0.22, annualReturn: -0.02}),
            point({id: 'benchmark', role: 'benchmark', name: 'World Index', volatility: 0.18, annualReturn: 0.07}),
            point({id: 'broken', role: 'asset', name: 'No History', volatility: Number.NaN, weight: 0.1}),
        ],
    };

    interface Datum {
        value: [number, number];
        name: string;
        symbolSize: number;
        itemStyle: {color: string; opacity: number};
        role: RiskReturnRole;
        id: string;
    }

    interface Series {
        id: string;
        type: string;
        data: unknown[];
    }

    /** Where the datum carrying `id` is drawn, and how. Fails unless it is drawn exactly once. */
    function locate(result: ScatterOptionResult, id: string): {seriesId: string; index: number; datum: Datum} {
        const hits = (result.option.series as Series[]).flatMap((series) => (series.type === 'scatter' ? (series.data as Datum[]).map((datum, index) => ({seriesId: series.id, index, datum})) : [])).filter((hit) => hit.datum.id === id);
        expect(hits, `point "${id}" should be drawn exactly once`).toHaveLength(1);
        return hits[0];
    }

    /** `result` with the datum carrying `id` swapped for `original` — whatever still differs from the unselected result, the selection changed and should not have. */
    function withDatum(result: ScatterOptionResult, id: string, original: Datum): ScatterOptionResult {
        const series = (result.option.series as Series[]).map((entry) => (entry.type === 'scatter' ? {...entry, data: (entry.data as Datum[]).map((datum) => (datum.id === id ? original : datum))} : entry));
        return {...result, option: {...result.option, series}};
    }

    it.each([
        {id: 'asset-1', what: 'a weighted asset', premise: (datum: Datum) => datum.symbolSize > MIN_SYMBOL_PX && datum.symbolSize < MAX_SYMBOL_PX},
        // The dot the lab draws: its assets carry no weight.
        {id: 'asset-3', what: 'a weightless asset', premise: (datum: Datum) => datum.symbolSize === MIN_SYMBOL_PX},
    ])('draws $what larger, green and opaque, and nothing else differs', ({id, what, premise}) => {
        const unselected = buildScatterOption(INPUT);
        const selected = buildScatterOption({...INPUT, selectedId: id});

        const before = locate(unselected, id);
        const after = locate(selected, id);
        expect(premise(before.datum), `fixture premise: ${what}`).toBe(true);

        // The highlight, measured against the same datum unselected.
        expect(after.datum.itemStyle.color).toBe(SELECTED_LIGHT);
        expect(after.datum.itemStyle.color).not.toBe(before.datum.itemStyle.color);
        expect(after.datum.itemStyle.opacity).toBe(1);
        expect(after.datum.symbolSize).toBeGreaterThan(before.datum.symbolSize);

        // Still the same point, where it was: a highlight moves, renames and re-files nothing.
        expect({seriesId: after.seriesId, index: after.index, value: after.datum.value, name: after.datum.name, role: after.datum.role}).toEqual({seriesId: before.seriesId, index: before.index, value: before.datum.value, name: before.datum.name, role: before.datum.role});

        // Put the unselected datum back and nothing is left to tell the two results apart.
        expect(withDatum(selected, id, before.datum)).toEqual(unselected);
    });

    /**
     * The portfolio and the benchmark keep their own colour when selected (developer's review of
     * 06/10/2026: «il simbolo nel grafico non deve cambiare colore»): the colour is what names them,
     * and in the selection green either would read as an asset. They grow and are drawn opaque.
     */
    it.each([
        {id: 'benchmark', role: 'benchmark' as const, what: 'the benchmark, already opaque', premise: (datum: Datum) => datum.itemStyle.opacity === 1},
        // "Larger than it would otherwise be" holds at the ceiling too: a highlight clamped
        // to MAX_SYMBOL_PX would leave the one bubble that is already largest its own size.
        {id: 'portfolio', role: 'portfolio' as const, what: 'the portfolio, at the size ceiling', premise: (datum: Datum) => datum.symbolSize === MAX_SYMBOL_PX},
    ])('draws $what larger and opaque, in its role colour, and nothing else differs', ({id, role, what, premise}) => {
        const unselected = buildScatterOption(INPUT);
        const selected = buildScatterOption({...INPUT, selectedId: id});

        const before = locate(unselected, id);
        const after = locate(selected, id);
        expect(premise(before.datum), `fixture premise: ${what}`).toBe(true);

        // The highlight, measured against the same datum unselected: the colour stays the role's.
        expect(after.datum.itemStyle.color, `${what}: a selection may not repaint the dot that names its role`).toBe(colorForRole(role, false));
        expect(after.datum.itemStyle.color).toBe(before.datum.itemStyle.color);
        expect(after.datum.itemStyle.color).not.toBe(SELECTED_LIGHT);
        expect(after.datum.itemStyle.opacity).toBe(1);
        expect(after.datum.symbolSize).toBeGreaterThan(before.datum.symbolSize);

        // Still the same point, where it was: a highlight moves, renames and re-files nothing.
        expect({seriesId: after.seriesId, index: after.index, value: after.datum.value, name: after.datum.name, role: after.datum.role}).toEqual({seriesId: before.seriesId, index: before.index, value: before.datum.value, name: before.datum.name, role: before.datum.role});

        // Put the unselected datum back and nothing is left to tell the two results apart.
        expect(withDatum(selected, id, before.datum)).toEqual(unselected);
    });

    it('keeps the highlight apart from the dot it replaces, and from every role colour, in the dark palette too', () => {
        const dark: ScatterOptionInput = {...INPUT, dark: true};
        const unselected = buildScatterOption(dark);
        const selected = buildScatterOption({...dark, selectedId: 'asset-2'});

        const before = locate(unselected, 'asset-2');
        const after = locate(selected, 'asset-2');

        expect(after.datum.itemStyle.color).not.toBe(before.datum.itemStyle.color);
        // Not merely "not grey": a selected asset in the portfolio's blue or the benchmark's amber would read as that role.
        expect(ROLES.map((role) => colorForRole(role, true))).not.toContain(after.datum.itemStyle.color);
        expect(after.datum.itemStyle.opacity).toBe(1);
        expect(after.datum.symbolSize).toBeGreaterThan(before.datum.symbolSize);

        expect(withDatum(selected, 'asset-2', before.datum)).toEqual(unselected);
    });

    it.each([
        {what: 'undefined', selectedId: undefined},
        {what: 'null', selectedId: null},
        {what: 'an id no point carries', selectedId: 'asset-999'},
        // The asset is in the caller's list, but without a volatility it was never placed.
        {what: 'the id of an unplaced point', selectedId: 'broken'},
    ])('changes nothing at all when the selection is $what', ({selectedId}) => {
        const unselected = buildScatterOption(INPUT);

        // Presence barrier: on this very input a placed id does change the drawing.
        expect(buildScatterOption({...INPUT, selectedId: 'asset-1'})).not.toEqual(unselected);

        expect(buildScatterOption({...INPUT, selectedId})).toEqual(unselected);
    });
});

/**
 * The benchmark's diamond and the plot's left margin (developer's reviews of 05/10/2026, T12–T15 and V6).
 *
 * `SYMBOL_BY_ROLE` was declared and never applied: every dot was a circle, and the benchmark told
 * itself apart by colour alone. It is a diamond now. A benchmark the reader holds arrives as its
 * holding's dot with a weight (`buildRiskReturnPoints`), so it is sized like a holding — and a diamond
 * fills half of the square ECharts fits it in where a circle fills π/4, so at one size the diamond
 * would cover a third less than the circle of the same weight beside it. A benchmark nobody holds has
 * no weight and keeps the fixed marker size it always had.
 *
 * V6: the left inset is relative, as on the growth chart, and the y-axis title starts at the axis
 * and runs right, so no pixel strip is kept empty for a centred title `containLabel` never measures.
 */
describe('scatterChartHelpers — the benchmark’s diamond and the plot’s margins', () => {
    interface Drawn {
        id: string;
        symbol?: string;
        symbolSize: number;
    }

    /** Every scatter datum carrying `id`, with the series it is filed in. */
    function drawn(result: ScatterOptionResult, id: string): {seriesId: string; datum: Drawn}[] {
        return (result.option.series as {id: string; type: string; data: unknown[]}[]).flatMap((series) => (series.type === 'scatter' ? (series.data as Drawn[]).filter((datum) => datum.id === id).map((datum) => ({seriesId: series.id, datum})) : []));
    }

    /** A held benchmark as `buildRiskReturnPoints` hands it over: its holding's dot, `asset-<id>`, with the holding's weight. */
    const HELD: RiskReturnPoint[] = [
        point({id: 'portfolio', role: 'portfolio', volatility: 0.15, annualReturn: 0.08, weight: 1}),
        point({id: 'asset-1', role: 'asset', volatility: 0.12, annualReturn: 0.05, weight: 0.35}),
        point({id: 'asset-2', role: 'benchmark', volatility: 0.18, annualReturn: 0.07, weight: 0.35}),
    ];

    it('draws the benchmark once, as a diamond, and every other dot as a circle — a held benchmark too', () => {
        const result = buildScatterOption({points: HELD, labels: LABELS});

        const benchmark = drawn(result, 'asset-2');
        expect(benchmark, 'the held benchmark must be drawn exactly once').toHaveLength(1);
        expect(benchmark[0].seriesId).toBe('scatter-benchmark');
        expect(benchmark[0].datum.symbol, 'the benchmark is told apart by its shape, not by its colour alone').toBe('diamond');
        expect(drawn(result, 'asset-1')[0].datum.symbol).toBe('circle');
        expect(drawn(result, 'portfolio')[0].datum.symbol).toBe('circle');
    });

    it('gives a weighted diamond the area of a circle of the same weight', () => {
        const result = buildScatterOption({points: HELD, labels: LABELS});
        const diamond = drawn(result, 'asset-2')[0].datum.symbolSize;
        const circle = drawn(result, 'asset-1')[0].datum.symbolSize;

        expect(circle, 'premise: the circle is sized by its weight').toBe(symbolSizeForWeight(0.35));
        // ECharts fits each symbol in a square of side `symbolSize`: a diamond covers half of it, a circle π/4.
        expect((diamond * diamond) / 2, 'a diamond of the same weight covers less ink than the circle beside it').toBeCloseTo((Math.PI * circle * circle) / 4, 9);
        expect(diamond / circle).toBeCloseTo(Math.sqrt(Math.PI / 2), 12);
    });

    it('keeps a benchmark nobody holds — no weight — at the fixed marker size it always had', () => {
        const result = buildScatterOption({points: [point({id: 'benchmark', role: 'benchmark', volatility: 0.18, annualReturn: 0.07}), point({id: 'asset-1', role: 'asset'})], labels: LABELS});
        const benchmark = drawn(result, 'benchmark');

        expect(benchmark).toHaveLength(1);
        expect(benchmark[0].datum.symbol).toBe('diamond');
        expect(benchmark[0].datum.symbolSize, 'a reference is not a holding: no weight, no area to match').toBe(MIN_SYMBOL_PX * 1.6);
    });

    it('insets the plot by a share of its width, and starts the y-axis title at the axis', () => {
        const {option} = buildScatterOption({points: HELD, labels: LABELS});

        expect(option.grid.left, 'a pixel inset was an empty strip before the y labels').toBe('3%');
        expect(option.grid.containLabel, 'the labels are added to the inset, so they still fit').toBe(true);
        expect(option.yAxis.nameTextStyle.align, 'a centred title hangs off the left edge, where containLabel does not measure').toBe('left');
    });
});
