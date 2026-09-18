// @vitest-environment jsdom
/**
 * RiskMetricCard — component test (Vitest + jsdom).
 *
 * The card exists to fix one measured defect: KpiSection cards 2 and 3 swap the
 * skeleton for the value with `{#if loading}{:else}`, so the value line is a
 * DIFFERENT element before and after loading and the layout jumps. This card
 * keeps ONE element and hides it with `class:invisible`.
 *
 * That distinction is invisible to a class assertion — `{#if}{:else}` can
 * produce markup that looks identical — so the central test here asserts NODE
 * IDENTITY: the very same DOM object is returned before and after the `loading`
 * flip. `rerender` updates props on the existing instance without remounting,
 * which is exactly the condition under which an `{#if}{:else}` would swap the
 * node and fail. Nothing weaker actually proves "nothing moved".
 *
 * The guarantee it does NOT give is pinned too: `caption` and the snippets live
 * behind `{#if}` inside the wrapper, so a caller who supplies them only after
 * loading still gets a jump. That is a caller-side contract (K5), and the test
 * records the shape so nobody later mistakes it for a bug in the card.
 *
 * Asserted on `data-testid` and on values the test passed in — never on a
 * translated string.
 */
import {describe, expect, it} from 'vitest';
import {createRawSnippet} from 'svelte';
import {render, screen, setupI18n, waitFor} from '$test/component';

import RiskMetricCard from './RiskMetricCard.svelte';

const BASE = {label: 'A bad day', technicalName: 'VaR 95%', value: '-2.10%', testId: 'card'};

/** A snippet built without a wrapper component, so the spec stays a single file. */
function probe(testId: string) {
    return createRawSnippet(() => ({render: () => `<span data-testid="${testId}">probe</span>`}));
}

describe('RiskMetricCard', () => {
    describe('the double label', () => {
        it('shows the plain-language question and the technical name side by side', async () => {
            await setupI18n();
            render(RiskMetricCard, {props: BASE});

            expect(screen.getByTestId('card-label')).toHaveTextContent('A bad day');
            expect(screen.getByTestId('card-technical')).toHaveTextContent('VaR 95%');
        });

        it('omits the technical line when there is no technical name', async () => {
            await setupI18n();
            render(RiskMetricCard, {props: {label: 'A bad day', value: '-2.10%', testId: 'card'}});

            expect(screen.getByTestId('card-label')).toBeInTheDocument();
            expect(screen.queryByTestId('card-technical')).not.toBeInTheDocument();
        });

        it('links to the docs only when a path is given', async () => {
            await setupI18n();
            const {unmount} = render(RiskMetricCard, {props: BASE});
            expect(screen.queryByTestId('card-docs')).not.toBeInTheDocument();
            unmount();

            render(RiskMetricCard, {props: {...BASE, docsPath: 'user/risk/var'}});
            expect(screen.getByTestId('card-docs')).toBeInTheDocument();
        });
    });

    describe('loading — the reason this card exists', () => {
        it('keeps the value element mounted underneath the skeleton', async () => {
            await setupI18n();
            render(RiskMetricCard, {props: {...BASE, loading: true}});

            expect(screen.getByTestId('card-skeleton')).toBeInTheDocument();
            // Present, not removed: this is what stops the layout from collapsing.
            const valueNode = screen.getByTestId('card-value');
            expect(valueNode).toBeInTheDocument();
            expect(valueNode.parentElement?.className).toContain('invisible');
        });

        it('hands back the SAME node after loading resolves, not a replacement', async () => {
            await setupI18n();
            const rendered = render(RiskMetricCard, {props: {...BASE, loading: true}});

            const before = screen.getByTestId('card-value');
            await rendered.rerender({...BASE, loading: false});
            const after = screen.getByTestId('card-value');

            // Identity, not equality. An `{#if loading}{:else}` would put a new
            // object here and this is the only assertion that would notice.
            expect(after).toBe(before);
            expect(after.parentElement?.className).not.toContain('invisible');
            expect(screen.queryByTestId('card-skeleton')).not.toBeInTheDocument();
        });

        it('drops caption and snippets while loading — the caller-side half of the contract', async () => {
            await setupI18n();
            // Documented in K5: a caller who supplies these only once data has
            // arrived still gets a jump, because they sit behind `{#if}` INSIDE
            // the invisible wrapper. The card cannot reserve space for content
            // it was never given.
            render(RiskMetricCard, {props: {...BASE, loading: true, caption: 'vs 1.80% last month', sparkline: probe('probe-spark')}});

            expect(screen.getByTestId('card-caption')).toBeInTheDocument();
            expect(screen.getByTestId('card-sparkline')).toBeInTheDocument();

            // ...and absent when the caller omits them during loading, which is
            // precisely the shape that shifts once they appear.
            const bare = render(RiskMetricCard, {props: {...BASE, testId: 'bare', loading: true}});
            expect(bare.queryByTestId('bare-caption')).not.toBeInTheDocument();
            expect(bare.queryByTestId('bare-sparkline')).not.toBeInTheDocument();
        });
    });

    describe('sentiment', () => {
        it('draws no accent strip when the metric has no opinion', async () => {
            await setupI18n();
            render(RiskMetricCard, {props: BASE});

            // Neutral is the default: a risk number is often neither good nor bad.
            expect(screen.queryByTestId('card-accent')).not.toBeInTheDocument();
        });

        it('draws a green strip for positive and a red strip for negative', async () => {
            await setupI18n();
            const rendered = render(RiskMetricCard, {props: {...BASE, sentiment: 'positive'}});
            expect(screen.getByTestId('card-accent').className).toContain('bg-green-500');
            expect(screen.getByTestId('card-value').className).toContain('text-green-700');

            await rendered.rerender({...BASE, sentiment: 'negative'});
            expect(screen.getByTestId('card-accent').className).toContain('bg-red-500');
            expect(screen.getByTestId('card-value').className).toContain('text-red-700');
        });
    });

    describe('the value itself', () => {
        it('renders a pre-formatted string verbatim', async () => {
            await setupI18n();
            render(RiskMetricCard, {props: BASE});

            expect(screen.getByTestId('card-value')).toHaveTextContent('-2.10%');
        });

        it('animates a numeric value and settles on the formatted result', async () => {
            await setupI18n();
            render(RiskMetricCard, {props: {...BASE, value: undefined, numericValue: 12.5, formatValue: (v: number) => `${v.toFixed(2)}%`}});

            // Poll the settled text: TweenedValue starts at 0 and animates, so
            // asserting synchronously would pin the animation instead of the value.
            await waitFor(() => expect(screen.getByTestId('card-value')).toHaveTextContent('12.50%'), {timeout: 3000});
        });

        it('keeps digits from reflowing mid-animation', async () => {
            await setupI18n();
            render(RiskMetricCard, {props: BASE});

            // `tabular-nums` is the whole reason the number does not jitter while
            // it counts up; it is a behaviour, not a decoration.
            expect(screen.getByTestId('card-value').className).toContain('tabular-nums');
        });
    });

    describe('the optional slots', () => {
        it('renders submetrics and sparkline only when supplied', async () => {
            await setupI18n();
            const bare = render(RiskMetricCard, {props: BASE});
            expect(bare.queryByTestId('card-sparkline')).not.toBeInTheDocument();
            bare.unmount();

            render(RiskMetricCard, {props: {...BASE, sparkline: probe('probe-spark'), submetrics: probe('probe-sub')}});
            expect(screen.getByTestId('card-sparkline')).toBeInTheDocument();
            expect(screen.getByTestId('probe-spark')).toBeInTheDocument();
            expect(screen.getByTestId('probe-sub')).toBeInTheDocument();
        });
    });

    describe('container-relative sizing', () => {
        it('scales the value with its container rather than the viewport', async () => {
            await setupI18n();
            render(RiskMetricCard, {props: BASE});

            // jsdom has no layout engine, so the effect cannot be measured here —
            // only that the card asks for it. The `cqw` unit is meaningless
            // without `@container` on an ancestor, so both are pinned together.
            expect(screen.getByTestId('card').className).toContain('@container');
            expect(screen.getByTestId('card-value').className).toContain('cqw');
        });
    });
});
