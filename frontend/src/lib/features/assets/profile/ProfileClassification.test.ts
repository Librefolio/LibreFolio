// @vitest-environment jsdom
/**
 * ProfileClassification (plan 68, E4): the countries and the sectors of the «Profilo» tab, with today's two components
 * (`GeographyMap`, `AllocationPieChart`).
 *
 * Pinned:
 * - the composition shown is the one of the day chosen in «dati al»: by default the newest day a composition changed in
 *   the period; choosing an older day draws that day's countries and sectors;
 * - a part with no composition that day says so (`data-state="unavailable"`) and draws no chart;
 * - with no composition in the period there is no «dati al» to choose;
 * - E6b2: beside the title of each part, the clock of the cards opens that voice's history (`onhistory`), when the voice
 *   has rows in the period and the page handles it.
 *
 * How it is tested: the real component, real i18n; the two charts stood in by recorders of their props.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const charts = vi.hoisted(() => {
    const maps: Array<Record<string, unknown>> = [];
    const pies: Array<Record<string, unknown>> = [];
    function recorder(list: Array<Record<string, unknown>>, id: string) {
        return (anchor: ChildNode, props: Record<string, unknown>): void => {
            const element = document.createElement('div');
            element.setAttribute('data-testid', id);
            anchor.before(element);
            list.push(props);
        };
    }
    return {maps, pies, GeographyMapStandIn: recorder(maps, 'stand-in-map'), AllocationPieChartStandIn: recorder(pies, 'stand-in-pie')};
});
vi.mock('$lib/components/charts/GeographyMap.svelte', () => ({default: charts.GeographyMapStandIn}));
vi.mock('$lib/components/charts/AllocationPieChart.svelte', () => ({default: charts.AllocationPieChartStandIn}));

import {fireEvent, render, screen, setupI18n} from '$test/component';
import type {ProfileStep, ProfileVoices} from './profileStore';
import ProfileClassification from './ProfileClassification.svelte';

function step(date: string, through: string, value: unknown): ProfileStep {
    return {date, through, value, source: 'justetf', update_id: 1} as ProfileStep;
}

const VOICES: ProfileVoices = {
    geography: [step('2025-11-17', '2026-03-31', {USA: '0.6', JPN: '0.4'}), step('2026-04-01', '2026-11-17', {USA: '0.62', JPN: '0.38'})],
    sector: [step('2025-11-17', '2026-11-17', {Technology: '0.3', Financials: '0.7'})],
};

/** The data a map last drew; the pie's, by name and value. */
const lastMap = () => (charts.maps.at(-1) as {data: Record<string, number>} | undefined)?.data;
const lastPie = () => (charts.pies.at(-1) as {data: Array<{name: string; value: number}>} | undefined)?.data.map(({name, value}) => [name, value]);

describe('ProfileClassification', () => {
    beforeAll(async () => {
        await setupI18n();
    });
    beforeEach(() => {
        charts.maps.length = 0;
        charts.pies.length = 0;
    });

    it('draws the composition of the newest day by default', () => {
        render(ProfileClassification, {props: {voices: VOICES}});
        expect(screen.getByTestId('profile-classification-day')).toHaveValue('2026-04-01');
        expect(screen.getByTestId('profile-classification-geography')).toHaveAttribute('data-state', 'value');
        expect(lastMap()).toEqual({USA: 0.62, JPN: 0.38});
        expect(lastPie()).toEqual([
            ['Technology', 30],
            ['Financials', 70],
        ]);
    });

    it('draws an older day when it is chosen', async () => {
        render(ProfileClassification, {props: {voices: VOICES}});
        await fireEvent.change(screen.getByTestId('profile-classification-day'), {target: {value: '2025-11-17'}});
        expect(lastMap()).toEqual({USA: 0.6, JPN: 0.4});
    });

    it('draws the end of the period by default, even when a part was emptied after the other changed', () => {
        const emptied: ProfileVoices = {...VOICES, sector: [step('2025-11-17', '2026-06-30', {Technology: '1'}), step('2026-07-01', '2026-11-17', null)]};
        render(ProfileClassification, {props: {voices: emptied}});
        expect(screen.getByTestId('profile-classification-day')).toHaveValue('2026-07-01');
        expect(screen.getByTestId('profile-classification-sector')).toHaveAttribute('data-state', 'unavailable');
        expect(lastMap()).toEqual({USA: 0.62, JPN: 0.38});
    });

    it('says a part has no composition, and draws no chart for it', () => {
        render(ProfileClassification, {props: {voices: {geography: VOICES.geography}}});
        expect(screen.getByTestId('profile-classification-sector')).toHaveAttribute('data-state', 'unavailable');
        expect(charts.pies).toHaveLength(0);
    });

    it('has no day to choose with one composition in the period, and says its date', () => {
        const one: ProfileVoices = {geography: [{...step('2025-11-17', '2026-11-17', {USA: '1'}), opened_on: '2025-10-04', source_date: '2025-09-30'} as ProfileStep]};
        render(ProfileClassification, {props: {voices: one}});
        expect(screen.queryByTestId('profile-classification-day')).toBeNull();
        expect(screen.getByTestId('profile-classification-as-of')).toHaveAttribute('data-kind', 'source_date');
        expect(screen.getByTestId('profile-classification-as-of')).toHaveAttribute('data-day', '2025-09-30');
    });

    it('says «before the profile» with no date for a legacy composition', () => {
        const legacy: ProfileVoices = {sector: [{...step('2025-11-17', '2026-11-17', {Technology: '1'}), opened_on: '2019-03-01', source: 'legacy'} as ProfileStep]};
        render(ProfileClassification, {props: {voices: legacy}});
        expect(screen.getByTestId('profile-classification-as-of')).toHaveAttribute('data-kind', 'legacy');
        expect(screen.getByTestId('profile-classification-as-of')).not.toHaveAttribute('data-day');
    });

    it('has no day to choose with no composition in the period', () => {
        render(ProfileClassification, {props: {voices: {}}});
        expect(screen.queryByTestId('profile-classification-day')).toBeNull();
        expect(screen.getByTestId('profile-classification-geography')).toHaveAttribute('data-state', 'unavailable');
        expect(charts.maps).toHaveLength(0);
    });

    it('opens the history of countries and sectors from the clock beside their titles (E6b2)', async () => {
        const onhistory = vi.fn();
        render(ProfileClassification, {props: {voices: VOICES, onhistory}});
        await fireEvent.click(screen.getByTestId('profile-classification-geography-history'));
        await fireEvent.click(screen.getByTestId('profile-classification-sector-history'));
        expect(onhistory.mock.calls).toEqual([['geography'], ['sector']]);
    });

    it('has no clock for a voice with no rows in the period, nor when the page does not handle it', () => {
        const view = render(ProfileClassification, {props: {voices: {geography: VOICES.geography}, onhistory: vi.fn()}});
        expect(screen.getByTestId('profile-classification-geography-history')).toBeInTheDocument();
        expect(screen.queryByTestId('profile-classification-sector-history')).toBeNull();
        view.unmount();
        render(ProfileClassification, {props: {voices: VOICES}});
        expect(screen.queryByTestId('profile-classification-geography-history')).toBeNull();
    });
});
