// @vitest-environment jsdom
/**
 * ProfileKeyFigureCard (plan 68, E4): one key figure of the «Profilo» tab.
 *
 * Pinned:
 * - the card publishes its state (`data-state`: value, emptied, unavailable) and shows the text it is given only with a
 *   value; otherwise its «not available» line (never asserted as text);
 * - a charted card draws its steps, as steps (`lineShape: 'steps'`), with the points it is given; a card with no chart
 *   draws nothing;
 * - the clock opens the voice's history (E6) with its key; no handler, or no value in the period: no clock.
 *
 * How it is tested: the real card, real i18n; the mini chart stood in by a recorder of its props (`AssetCard.test.ts`).
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const charts = vi.hoisted(() => {
    const mounts: Array<Record<string, unknown>> = [];
    function PriceChartCompactStandIn(anchor: ChildNode, props: Record<string, unknown>): void {
        const element = document.createElement('div');
        element.setAttribute('data-testid', 'stand-in-chart');
        anchor.before(element);
        mounts.push(props);
    }
    return {mounts, PriceChartCompactStandIn};
});
vi.mock('$lib/components/charts/PriceChartCompact.svelte', () => ({default: charts.PriceChartCompactStandIn}));

import {fireEvent, render, screen, setupI18n} from '$test/component';
import type {ProfileStep, ProfileVoice} from './profileStore';
import type {KeyFigureCard} from './profileTabState';
import ProfileKeyFigureCard from './ProfileKeyFigureCard.svelte';

const TER = {key: 'ter', shape: 'percentage', groups: ['key_figures'], key_figure: true, charted: true} as unknown as ProfileVoice;
const LAST = {date: '2026-03-02', through: '2026-11-17', value: '0.0019', source: 'justetf', update_id: 2} as ProfileStep;

function card(extra: Partial<KeyFigureCard> = {}): KeyFigureCard {
    return {key: 'ter', voice: TER, state: 'value', step: LAST, chart: null, ...extra};
}

describe('ProfileKeyFigureCard', () => {
    beforeAll(async () => {
        await setupI18n();
    });
    beforeEach(() => {
        charts.mounts.length = 0;
    });

    it('shows the value it is given, and publishes its state', () => {
        render(ProfileKeyFigureCard, {props: {card: card(), text: '0,19%'}});
        expect(screen.getByTestId('profile-key-figure-ter')).toHaveAttribute('data-state', 'value');
        expect(screen.getByTestId('profile-key-figure-ter-value')).toHaveTextContent('0,19%');
    });

    it('does not show a text for an emptied or unavailable voice', () => {
        render(ProfileKeyFigureCard, {props: {card: card({state: 'unavailable', step: null}), text: 'should not show'}});
        expect(screen.getByTestId('profile-key-figure-ter')).toHaveAttribute('data-state', 'unavailable');
        expect(screen.getByTestId('profile-key-figure-ter-value')).not.toHaveTextContent('should not show');
    });

    it('draws its steps as steps, with the points it is given', () => {
        const chart = [
            {date: '2025-11-17', value: 0.22},
            {date: '2026-03-02', value: 0.19},
            {date: '2026-11-17', value: 0.19},
        ];
        render(ProfileKeyFigureCard, {props: {card: card({chart}), text: '0,19%'}});
        expect(screen.getByTestId('profile-key-figure-ter-chart')).toBeInTheDocument();
        expect(charts.mounts).toHaveLength(1);
        expect(charts.mounts[0].data).toEqual(chart);
        expect(charts.mounts[0].lineShape).toBe('steps');
        // A falling TER is not a loss: the line is never coloured against its first point
        expect(charts.mounts[0].colorByBaseline).toBe(false);
    });

    it('draws nothing without a chart', () => {
        render(ProfileKeyFigureCard, {props: {card: card(), text: '0,19%'}});
        expect(screen.queryByTestId('profile-key-figure-ter-chart')).toBeNull();
        expect(charts.mounts).toHaveLength(0);
    });

    it('opens the history of its voice from the clock', async () => {
        const onhistory = vi.fn();
        render(ProfileKeyFigureCard, {props: {card: card(), text: '0,19%', onhistory}});
        await fireEvent.click(screen.getByTestId('profile-key-figure-ter-history'));
        expect(onhistory).toHaveBeenCalledWith('ter');
    });

    it('has no clock without a handler, or without a value in the period', () => {
        const {unmount} = render(ProfileKeyFigureCard, {props: {card: card(), text: '0,19%'}});
        expect(screen.queryByTestId('profile-key-figure-ter-history')).toBeNull();
        unmount();
        render(ProfileKeyFigureCard, {props: {card: card({state: 'unavailable', step: null}), text: '', onhistory: vi.fn()}});
        expect(screen.queryByTestId('profile-key-figure-ter-history')).toBeNull();
    });
});
