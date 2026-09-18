// @vitest-environment jsdom
/**
 * KpiDivergingFlowBar — component test (Vitest + jsdom).
 *
 * This bar was promoted out of `components/dashboard/` into `ui/display/` and
 * gained optional props on the way (`signedPct`, colours, height, layout,
 * `testId`). Both halves of that sentence are dangerous, and this file pins
 * them:
 *
 *   1. THE DEFAULTS MUST STILL RENDER THE DASHBOARD BAR. The dashboard is the
 *      only existing caller and it passes `depositPct`/`withdrawPct` and
 *      nothing else. If a future prop changes what that call produces, the move
 *      stopped being invisible and the change is wrong.
 *   2. `width` MUST SURVIVE A NON-FINITE INPUT. `width: NaN%` is invalid CSS,
 *      so the declaration is discarded and the fill silently keeps its previous
 *      width — showing a stale figure as a current one. The test asserts the
 *      rendered `style.width`, which is exactly where that failure appears:
 *      `''` when the declaration was dropped, `'0%'` when it was clamped.
 *
 * Asserted on rendered geometry and on classes that carry meaning — never on a
 * translated string.
 */
import {describe, expect, it} from 'vitest';
import {render, screen, setupI18n} from '$test/component';

import KpiDivergingFlowBar from './KpiDivergingFlowBar.svelte';

/**
 * The two fills, selected structurally — left (negative) then right (positive).
 *
 * Deliberately NOT selected via `[style*="width"]`: when the width is invalid
 * the declaration is rejected outright and the element would vanish from such a
 * query, turning a precise "the width was dropped" failure into a vague "an
 * element is missing" one. Selecting on the rounding classes keeps the fill
 * findable no matter what happened to its width, so the assertion can name the
 * real symptom.
 */
function fills(container: HTMLElement): {left: HTMLElement; right: HTMLElement} {
    const left = container.querySelector<HTMLElement>('div.absolute.rounded-l-full');
    const right = container.querySelector<HTMLElement>('div.absolute.rounded-r-full');
    if (!left || !right) throw new Error(`Fill elements not found (left: ${!!left}, right: ${!!right}).`);
    return {left, right};
}

function track(container: HTMLElement): HTMLElement {
    const node = container.querySelector<HTMLElement>('div.flex.relative, div.relative.flex');
    if (!node) throw new Error('Track element not found.');
    return node;
}

describe('KpiDivergingFlowBar', () => {
    describe('the dashboard rendering, which the promotion must not disturb', () => {
        it('renders the historical stacked geometry from a flow pair alone', async () => {
            await setupI18n();
            const {container} = render(KpiDivergingFlowBar, {props: {label: 'Net flow', value: '+120', depositPct: 60, withdrawPct: 25}});

            const {left, right} = fills(container);
            expect(right.style.width).toBe('60%');
            expect(left.style.width).toBe('25%');

            // The colours and the height are the visible identity of this bar.
            expect(right.className).toContain('bg-green-500');
            expect(left.className).toContain('bg-red-400');
            expect(track(container).className).toContain('h-1.5');
        });

        it('stacks label above bar by default, with the value on the label row', async () => {
            await setupI18n();
            const {container} = render(KpiDivergingFlowBar, {props: {label: 'Net flow', value: '+120', depositPct: 10, withdrawPct: 0, testId: 'flow'}});

            const root = screen.getByTestId('flow');
            expect(root.className).toContain('flex-col');
            expect(root.className).not.toContain('grid');
            expect(root).toHaveTextContent('+120');
            expect(fills(container).right.style.width).toBe('10%');
        });
    });

    describe('signedPct — one signed magnitude instead of two', () => {
        it('fills the right side for a positive value', async () => {
            await setupI18n();
            const {container} = render(KpiDivergingFlowBar, {props: {label: 'Contribution', value: '+18%', signedPct: 18}});

            const {left, right} = fills(container);
            expect(right.style.width).toBe('18%');
            expect(left.style.width).toBe('0%');
        });

        it('fills the left side for a negative value', async () => {
            await setupI18n();
            const {container} = render(KpiDivergingFlowBar, {props: {label: 'Contribution', value: '-18%', signedPct: -18}});

            const {left, right} = fills(container);
            expect(left.style.width).toBe('18%');
            expect(right.style.width).toBe('0%');
        });

        it('lets an explicit flow pair win, rather than guessing from the other prop', async () => {
            await setupI18n();
            // A caller that supplies one flow AND a signed value gets the flow it
            // wrote and a zero opposite it — the bar renders what was asked for.
            const {container} = render(KpiDivergingFlowBar, {props: {label: 'Mixed', value: 'x', depositPct: 30, signedPct: -90}});

            const {left, right} = fills(container);
            expect(right.style.width).toBe('30%');
            expect(left.style.width).toBe('0%');
        });
    });

    describe('inputs that should not be able to break the geometry', () => {
        it('clamps above 100 and below 0', async () => {
            await setupI18n();
            const {container} = render(KpiDivergingFlowBar, {props: {label: 'Clamp', value: 'x', depositPct: 420, withdrawPct: -50}});

            const {left, right} = fills(container);
            expect(right.style.width).toBe('100%');
            expect(left.style.width).toBe('0%');
        });

        it('renders 0% for a non-finite percentage instead of dropping the declaration', async () => {
            await setupI18n();
            const {container} = render(KpiDivergingFlowBar, {props: {label: 'Broken', value: 'x', depositPct: Number.NaN, withdrawPct: 40}});

            const {left, right} = fills(container);
            // Without the guard this is '' — `width: NaN%` is rejected by the CSS
            // parser, the declaration never lands, and the fill keeps whatever
            // width it had, which reads as real data.
            expect(right.style.width).toBe('0%');
            expect(right.style.width).not.toBe('');
            expect(left.style.width).toBe('40%');
        });

        it('survives a non-finite signed value the same way', async () => {
            await setupI18n();
            const {container} = render(KpiDivergingFlowBar, {props: {label: 'Broken', value: 'x', signedPct: Number.NaN}});

            const {left, right} = fills(container);
            expect(right.style.width).toBe('0%');
            expect(left.style.width).toBe('0%');
        });
    });

    describe('the props the risk panels needed', () => {
        it('puts testId on the root element', async () => {
            await setupI18n();
            render(KpiDivergingFlowBar, {props: {label: 'Row', value: 'x', signedPct: 5, testId: 'risk-contribution-row-7'}});

            expect(screen.getByTestId('risk-contribution-row-7')).toBeInTheDocument();
        });

        it('lays label, bar and value on one grid row when layout is inline', async () => {
            await setupI18n();
            render(KpiDivergingFlowBar, {props: {label: 'Row', value: '-3.20%', signedPct: -12, layout: 'inline', testId: 'row'}});

            const root = screen.getByTestId('row');
            expect(root.className).toContain('grid');
            expect(root.style.gridTemplateColumns).not.toBe('');
            expect(root).toHaveTextContent('-3.20%');
        });

        it('honours overridden colours and height without touching the geometry', async () => {
            await setupI18n();
            const {container} = render(KpiDivergingFlowBar, {
                props: {label: 'Row', value: 'x', signedPct: 44, positiveColor: 'bg-blue-500', negativeColor: 'bg-red-500', barHeight: 'h-5'},
            });

            const {right} = fills(container);
            expect(right.className).toContain('bg-blue-500');
            expect(right.className).not.toContain('bg-green-500');
            expect(right.style.width).toBe('44%');
            expect(track(container).className).toContain('h-5');
        });
    });
});
