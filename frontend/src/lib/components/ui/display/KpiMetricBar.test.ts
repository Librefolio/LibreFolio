// @vitest-environment jsdom
/**
 * KpiMetricBar — component test (Vitest + jsdom).
 *
 * Promoted out of `components/dashboard/` into `ui/display/` so the risk panels
 * can reuse it, most often as the `submetrics` rows of `RiskMetricCard`. The
 * move is only safe if the dashboard rendering is unchanged, so that is pinned
 * first.
 *
 * The second pin is the non-finite input. `width: NaN%` is rejected by the CSS
 * parser, so the declaration never lands and the fill keeps whatever width it
 * had — a stale figure presented as a current one. The dashboard never reached
 * that path because its caller divides by `|| 1`; the new consumers have no
 * such guard and no reason to suspect one is needed. The marker is guarded the
 * same way, but towards "no caret" rather than a caret pinned at 0%, which
 * would point at a position nobody computed.
 *
 * Asserted on rendered geometry and meaningful classes — never on a translated
 * string.
 */
import {describe, expect, it} from 'vitest';
import {render, screen, setupI18n, waitFor} from '$test/component';

import KpiMetricBar from './KpiMetricBar.svelte';

function fill(container: HTMLElement): HTMLElement {
    // Selected structurally, not via `[style*="width"]`: an invalid width is
    // dropped entirely, and the test must still find the element in order to
    // report *that* rather than "an element went missing".
    const node = container.querySelector<HTMLElement>('div.h-full.rounded-full');
    if (!node) throw new Error('Bar fill not found.');
    return node;
}

function caret(container: HTMLElement): HTMLElement | null {
    return container.querySelector<HTMLElement>('div[style*="left"]');
}

describe('KpiMetricBar', () => {
    describe('the dashboard rendering, which the promotion must not disturb', () => {
        it('draws the fill at the requested percentage with the default colour', async () => {
            await setupI18n();
            const {container} = render(KpiMetricBar, {props: {label: 'Equity', value: '42.5%', barPct: 42.5}});

            const bar = fill(container);
            expect(bar.style.width).toBe('42.5%');
            expect(bar.className).toContain('bg-slate-400');
        });

        it('shows a pre-formatted value verbatim', async () => {
            await setupI18n();
            const {container} = render(KpiMetricBar, {props: {label: 'Equity', value: '42.5%', barPct: 42.5}});

            expect(container).toHaveTextContent('42.5%');
        });

        it('animates a numeric value and settles on the formatted result', async () => {
            await setupI18n();
            const {container} = render(KpiMetricBar, {props: {label: 'Equity', value: '', numericValue: 61.25, formatValue: (v: number) => `${v.toFixed(2)}%`, barPct: 61.25}});

            // Poll the settled text: TweenedValue starts at 0 and animates.
            await waitFor(() => expect(container).toHaveTextContent('61.25%'), {timeout: 3000});
        });
    });

    describe('inputs that should not be able to break the geometry', () => {
        it('clamps above 100 and below 0', async () => {
            await setupI18n();
            const over = render(KpiMetricBar, {props: {label: 'Over', value: 'x', barPct: 420}});
            expect(fill(over.container).style.width).toBe('100%');
            over.unmount();

            const under = render(KpiMetricBar, {props: {label: 'Under', value: 'x', barPct: -30}});
            expect(fill(under.container).style.width).toBe('0%');
        });

        it('renders 0% for a non-finite percentage instead of dropping the declaration', async () => {
            await setupI18n();
            const {container} = render(KpiMetricBar, {props: {label: 'Broken', value: 'x', barPct: Number.NaN}});

            // Without the guard this is '': the declaration is rejected and the
            // fill silently keeps its previous width.
            expect(fill(container).style.width).toBe('0%');
            expect(fill(container).style.width).not.toBe('');
        });
    });

    describe('the reference marker', () => {
        it('positions the caret when a marker and its tooltip are given', async () => {
            await setupI18n();
            const {container} = render(KpiMetricBar, {props: {label: 'Equity', value: 'x', barPct: 50, marker: 30, markerTooltip: 'Start of period'}});

            const node = caret(container);
            expect(node).not.toBeNull();
            expect(node?.style.left).toBe('30%');
        });

        it('draws no caret for a non-finite marker rather than pinning one at zero', async () => {
            await setupI18n();
            const {container} = render(KpiMetricBar, {props: {label: 'Equity', value: 'x', barPct: 50, marker: Number.NaN, markerTooltip: 'Start of period'}});

            // This is a behaviour pin, not a regression catcher: removing the
            // `Number.isFinite` guard leaves it passing, because the template's
            // `clampedMarker > 0` test already rejects NaN. Pinned anyway, since
            // the behaviour is what callers depend on and it must survive a
            // rewrite of that condition.
            expect(caret(container)).toBeNull();
        });

        it('draws no caret when no marker is supplied', async () => {
            await setupI18n();
            const {container} = render(KpiMetricBar, {props: {label: 'Equity', value: 'x', barPct: 50}});

            expect(caret(container)).toBeNull();
        });
    });

    describe('the label', () => {
        it('exposes the full label as a title, since the visible text is truncated', async () => {
            await setupI18n();
            render(KpiMetricBar, {props: {label: 'Developed markets ex-US', value: 'x', barPct: 10}});

            expect(screen.getByTitle('Developed markets ex-US')).toBeInTheDocument();
        });
    });
});
