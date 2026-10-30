// @vitest-environment jsdom
/**
 * ReturnHistogram — a real tooltip on the bars, not the browser's `title` (B6, V2 of A; Vitest + jsdom).
 *
 * Every bar carried `title="a … b"`: the browser's own tooltip, slow, unstyled, absent on touch and never in
 * the app's dark theme. The app has one tooltip (`components/ui/feedback/Tooltip`), so the bars use it.
 *
 * Pinned, on test ids and data attributes, never on translated text:
 *
 * - no bar carries a native `title` any more;
 * - opening the tooltip of a bar (a click opens it at once; a plain hover waits) shows that bar's interval, written by
 *   the same `axisPercent` the axis ends use, so a bar and the axis never print one number two ways;
 * - a bar with no observation has a tooltip too: an empty bin and a missing one must not look alike;
 * - the bars keep their weights: the width of a bar is still its real span, whatever wraps it.
 */
import {beforeAll, describe, expect, it} from 'vitest';

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';

import {axisPercent, type ReturnHistogram as Histogram} from './l1Helpers';
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
const TIP = (index: number) => `risk-l1-histogram-bin-${index}-tip`;

describe('ReturnHistogram — the bars use the app tooltip (B6)', () => {
    it('leaves no native title on the bars', () => {
        const {container} = render(ReturnHistogram, {props: {histogram: HISTOGRAM}});

        expect(container.querySelectorAll('[data-testid="risk-l1-histogram-bars"] [title]'), 'a bar still relies on the browser tooltip').toHaveLength(0);
    });

    it("opens a bar's tooltip with its interval, written as the axis writes it", async () => {
        render(ReturnHistogram, {props: {histogram: HISTOGRAM}});

        await fireEvent.click(screen.getByTestId(TIP(1)));

        const content = await waitFor(() => screen.getByTestId('tooltip-content'));
        expect(content.textContent).toContain(axisPercent(-3));
        expect(content.textContent).toContain(axisPercent(0));
    });

    it('gives a bar with no observation a tooltip too', () => {
        render(ReturnHistogram, {props: {histogram: HISTOGRAM}});

        expect(screen.queryByTestId(TIP(2)), 'an empty bin has nothing to hover: it reads as a bin that is not there').not.toBeNull();
    });

    it('keeps the bars as many as the bins, each still carrying its count and its cut flags', () => {
        render(ReturnHistogram, {props: {histogram: HISTOGRAM}});

        expect(screen.getByTestId('risk-l1-histogram-bars').getAttribute('data-bin-count')).toBe('3');
        expect(screen.getByTestId(BIN(1)).getAttribute('data-count')).toBe('10');
        expect(screen.getByTestId(BIN(1)).getAttribute('data-holds-cut')).toBe('true');
        expect(screen.getByTestId(BIN(0)).getAttribute('data-below-cut')).toBe('true');
    });
});
