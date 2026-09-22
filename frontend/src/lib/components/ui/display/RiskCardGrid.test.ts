// @vitest-environment jsdom
/**
 * RiskCardGrid — component test (Vitest + jsdom).
 *
 * The grid exists to end a measured divergence: `components/risk/` holds 20 grid
 * declarations in 12 variants, and `RiskAnalysisPanel:632` still carries the
 * `1 → sm:2 → xl:5` jump that RiskMetricCard's own header argues against. So the
 * assertions here are not "does it render a grid" — they pin the two decisions
 * that make it worth being a component at all, and both are written so that the
 * obvious "simplification" turns them red:
 *
 *   1. NO BREAKPOINTS. The column count comes from `auto-fit`, because the card
 *      sizes its own number with `@container` and therefore needs the grid to
 *      state a minimum width, not a list of viewport widths. A future edit that
 *      helpfully restores `md:grid-cols-3` fails the class assertion.
 *   2. THE OVERFLOW GUARD. `minmax(min(16rem, 100%), 1fr)` — not
 *      `minmax(16rem, 1fr)`. The bare form keeps a 16rem track in a container
 *      narrower than 16rem and overflows sideways, so a narrow phone crops the
 *      cards instead of stacking them. That `min(...)` is one easily-deleted
 *      call, invisible in a screenshot at desktop width, so it gets its own test.
 *
 * Asserting the style string verbatim is only meaningful because jsdom keeps it:
 * probed before this spec was written, `cssstyle` round-trips
 * `repeat(auto-fit, minmax(min(16rem, 100%), 1fr))` unchanged, nested `min()`
 * included. Had it normalised or dropped the value, these assertions would have
 * been quietly testing the empty string.
 */
import {describe, expect, it} from 'vitest';
import {createRawSnippet} from 'svelte';
import {render, screen, setupI18n} from '$test/component';

import RiskCardGrid from './RiskCardGrid.svelte';

/** Three stand-in cards, built without a wrapper component so the spec stays one file. */
const threeCards = createRawSnippet(() => ({
    render: () => `<div><span data-testid="card-a">a</span><span data-testid="card-b">b</span><span data-testid="card-c">c</span></div>`,
}));

const oneCard = createRawSnippet(() => ({render: () => `<span data-testid="only">x</span>`}));

describe('RiskCardGrid', () => {
    describe('the column rule', () => {
        it('derives columns from auto-fit at the default minimum width', async () => {
            await setupI18n();
            render(RiskCardGrid, {props: {testId: 'grid', children: oneCard}});

            expect(screen.getByTestId('grid')).toHaveStyle({
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(16rem, 100%), 1fr))',
            });
        });

        it('lets the caller raise the minimum for cards that carry submetrics', async () => {
            await setupI18n();
            render(RiskCardGrid, {props: {minWidth: '22rem', testId: 'grid', children: oneCard}});

            expect(screen.getByTestId('grid')).toHaveStyle({
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(22rem, 100%), 1fr))',
            });
        });

        /**
         * The decision this component exists for. A responsive variant here means
         * somebody went back to enumerating viewport widths, which is the defect
         * the twenty existing declarations are made of.
         */
        it('carries no responsive column variant', async () => {
            await setupI18n();
            render(RiskCardGrid, {props: {testId: 'grid', children: oneCard}});

            const className = screen.getByTestId('grid').className;

            expect(className).toContain('grid');
            expect(className).not.toMatch(/\b(sm|md|lg|xl|2xl):/);
            expect(className).not.toMatch(/grid-cols-/);
        });
    });

    /**
     * Pinned apart from the happy path because deleting the `min(...)` leaves a
     * grid that looks correct at every width a developer is likely to try.
     */
    describe('the narrow-container guard', () => {
        it('caps the column floor at the container width so it cannot overflow', async () => {
            await setupI18n();
            render(RiskCardGrid, {props: {minWidth: '30rem', testId: 'grid', children: oneCard}});

            const columns = screen.getByTestId('grid').style.getPropertyValue('grid-template-columns');

            expect(columns).toContain('min(30rem, 100%)');
            expect(columns).not.toMatch(/minmax\(\s*30rem/);
        });
    });

    describe('the cards it is given', () => {
        it('renders them in the order they were supplied', async () => {
            await setupI18n();
            render(RiskCardGrid, {props: {testId: 'grid', children: threeCards}});

            const grid = screen.getByTestId('grid');
            const order = Array.from(grid.querySelectorAll('[data-testid^="card-"]')).map((node) => node.getAttribute('data-testid'));

            expect(order).toEqual(['card-a', 'card-b', 'card-c']);
        });

        it('keeps one spacing for every surface rather than exposing a second knob', async () => {
            await setupI18n();
            render(RiskCardGrid, {props: {testId: 'grid', children: oneCard}});

            expect(screen.getByTestId('grid').className).toContain('gap-4');
        });
    });

    describe('the selector', () => {
        it('omits the attribute entirely when no testId is given', async () => {
            await setupI18n();
            const {container} = render(RiskCardGrid, {props: {children: oneCard}});

            const grid = container.querySelector('div.grid');

            expect(grid).not.toBeNull();
            expect(grid?.hasAttribute('data-testid')).toBe(false);
        });
    });
});
