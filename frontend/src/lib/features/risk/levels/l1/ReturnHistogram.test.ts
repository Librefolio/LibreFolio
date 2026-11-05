// @vitest-environment jsdom
/**
 * ReturnHistogram — the section around the ECharts histogram (F-5, 05/11/2026; Vitest + jsdom).
 *
 * The bars were CSS divs with the app's tooltip on each; they are a chart now, and a canvas says nothing to a test, so the section
 * publishes what it drew. What the builder decides (edges, colours, the cut line) is pinned in `returnHistogramChartHelpers.test.ts`;
 * here the wiring the builder cannot see:
 *
 * - one entry per bin in the hidden list, each carrying its count and its cut flags, and the container its `data-bin-count`;
 * - what a bar's tooltip says, read from that list — the interval written by the same `axisPercent` the axis uses, so a bar and
 *   the axis never print one number two ways; how many days fell in it and their share, written by the share rule (`formatShare`,
 *   D-B6a); and where the bar lies against the VaR threshold (F-5), the three positions told apart;
 * - an empty bar has a tooltip too (an empty bin and a missing one must not look alike), with a share of zero;
 * - with no threshold published there is no position line, and a threshold of exactly zero is a real one;
 * - the two ends of the axis, as text.
 *
 * Only `echarts` is replaced, by a recorder: jsdom has no canvas. The expected sentences are the catalogue's, resolved through the
 * same `$_`, never a string written here.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('echarts', () => {
    const chart = () => {
        const instance = {
            setOption: () => {},
            on: () => instance,
            off: () => instance,
            resize: () => {},
            getDom: () => document.body,
            getWidth: () => 600,
            getHeight: () => 140,
            isDisposed: () => false,
            dispose: () => {},
            dispatchAction: () => {},
        };
        return instance;
    };
    return {init: chart};
});

import {get} from 'svelte/store';

import {_} from '$lib/i18n';
import {render, screen, setupI18n} from '$test/component';

import {formatShare} from '../shareFormat';
import {axisPercent, figurePercent, type ReturnHistogram as Histogram} from './l1Helpers';
import ReturnHistogram from './ReturnHistogram.svelte';

const HISTOGRAM: Histogram = {
    observations: 100,
    cut: -3,
    bins: [
        {lowerBound: -6, upperBound: -3, count: 4, share: 0.4, holdsCut: false, belowCut: true},
        {lowerBound: -3, upperBound: 0, count: 10, share: 1, holdsCut: true, belowCut: false},
        {lowerBound: 0, upperBound: 3, count: 0, share: 0, holdsCut: false, belowCut: false},
    ],
};

beforeAll(async () => {
    await setupI18n('en');
});

const BIN = (index: number) => `risk-l1-histogram-bin-${index}`;

function say(key: string, values: Record<string, string | number> = {}): string {
    return get(_)(key, {values});
}

/** The words of one bar, as its tooltip says them: the entries of the hidden list. */
function words(index: number): string {
    return screen.getByTestId(BIN(index)).textContent ?? '';
}

describe('ReturnHistogram — what it publishes of the chart', () => {
    it('keeps one entry per bin, each carrying its count and its cut flags', () => {
        render(ReturnHistogram, {props: {histogram: HISTOGRAM}});

        expect(screen.getByTestId('risk-l1-histogram-bars').getAttribute('data-bin-count')).toBe('3');
        expect(screen.getByTestId(BIN(1)).getAttribute('data-count')).toBe('10');
        expect(screen.getByTestId(BIN(1)).getAttribute('data-holds-cut')).toBe('true');
        expect(screen.getByTestId(BIN(0)).getAttribute('data-below-cut')).toBe('true');
        expect(screen.getByTestId(BIN(2)).getAttribute('data-holds-cut')).toBe('false');
        expect(screen.getByTestId(BIN(2)).getAttribute('data-below-cut')).toBe('false');
    });

    it('draws the chart, and no bar of CSS any more', () => {
        const {container} = render(ReturnHistogram, {props: {histogram: HISTOGRAM}});

        expect(screen.getByTestId('risk-l1-histogram-chart')).toBeTruthy();
        expect(container.querySelectorAll('[data-testid="risk-l1-histogram-bars"] [style*="flex:"]')).toHaveLength(0);
    });

    it('writes the two ends of the axis as text, one decimal, as the chart’s own labels', () => {
        render(ReturnHistogram, {props: {histogram: HISTOGRAM}});

        expect(screen.getByTestId('risk-l1-histogram-axis-min').textContent).toBe(axisPercent(-6));
        expect(screen.getByTestId('risk-l1-histogram-axis-max').textContent).toBe(axisPercent(3));
    });
});

describe('ReturnHistogram — what a bar’s tooltip says', () => {
    it('opens with its interval, written as the axis writes it', () => {
        render(ReturnHistogram, {props: {histogram: HISTOGRAM}});

        expect(words(1)).toContain(axisPercent(-3));
        expect(words(1)).toContain(axisPercent(0));
    });

    it('says how many days fell in the bar and their share of the observations (D-B6a)', () => {
        render(ReturnHistogram, {props: {histogram: HISTOGRAM}});

        // 10 of 100 observed days; the share is the share rule's own text, not a number written here.
        expect(words(1)).toContain(say('risk.levels.l1.histogram.bin', {range: `${axisPercent(-3)} … ${axisPercent(0)}`, count: 10, share: formatShare(0.1, 1)}));
    });

    it('says an empty bar held no day, with a share of zero, and has its own entry', () => {
        render(ReturnHistogram, {props: {histogram: HISTOGRAM}});

        expect(screen.queryByTestId(BIN(2)), 'an empty bin has nothing to hover: it reads as a bin that is not there').not.toBeNull();
        expect(words(2)).toContain(formatShare(0, 1));
        // More than the interval alone, which is all the bar said before it carried its days.
        expect(words(2).trim()).not.toBe(`${axisPercent(0)} … ${axisPercent(3)}`);
    });

    it('tells the three positions against the VaR threshold apart, with the threshold written', () => {
        render(ReturnHistogram, {props: {histogram: HISTOGRAM}});
        const threshold = figurePercent(-3 / 100);

        expect(words(0)).toContain(say('risk.levels.l1.histogram.position.beyond', {value: threshold}));
        expect(words(1)).toContain(say('risk.levels.l1.histogram.position.holds', {value: threshold}));
        expect(words(2)).toContain(say('risk.levels.l1.histogram.position.above', {value: threshold}));
        // Each sentence only on its own bar.
        expect(words(0)).not.toContain(say('risk.levels.l1.histogram.position.holds', {value: threshold}));
        expect(words(2)).not.toContain(say('risk.levels.l1.histogram.position.beyond', {value: threshold}));
    });

    it('says nothing of a threshold when none was published', () => {
        render(ReturnHistogram, {props: {histogram: {...HISTOGRAM, cut: null, bins: HISTOGRAM.bins.map((bin) => ({...bin, holdsCut: false, belowCut: false}))}}});

        for (const position of ['beyond', 'holds', 'above']) expect(words(1)).not.toContain(say(`risk.levels.l1.histogram.position.${position}`, {value: ''}).replace(/\s*\(\)$/, ''));
        expect(screen.queryByTestId('risk-l1-histogram-cut')).toBeNull();
        expect(screen.queryByTestId('risk-l1-histogram-nocut')).not.toBeNull();
    });

    it('takes a threshold of exactly zero for a real one', () => {
        render(ReturnHistogram, {props: {histogram: {...HISTOGRAM, cut: 0}}});

        expect(screen.queryByTestId('risk-l1-histogram-cut'), 'a cut of 0 is break-even, not a missing cut').not.toBeNull();
        expect(words(1)).toContain(figurePercent(0));
    });
});

describe('ReturnHistogram — without a distribution', () => {
    it('says so, and draws no chart', () => {
        render(ReturnHistogram, {props: {histogram: null}});

        expect(screen.queryByTestId('risk-l1-histogram-empty')).not.toBeNull();
        expect(screen.queryByTestId('risk-l1-histogram-chart')).toBeNull();
    });
});
