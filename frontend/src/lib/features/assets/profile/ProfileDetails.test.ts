// @vitest-environment jsdom
/**
 * ProfileDetails (plan 68, E4): the «Dettagli» of the «Profilo» tab.
 *
 * Pinned:
 * - one section per group it is given, in that order, each with a row per voice (`data-state` value, emptied,
 *   unavailable); the text of a row is the one it is given, only with a value;
 * - the identity group adds the asset's ISIN and ticker, which are the asset's identifiers, not profile voices: a row
 *   each, «not available» without one;
 * - a row with a value opens the voice's history (E6) when the page handles it; otherwise it is plain text.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import type {ProfileStep, ProfileVoice} from './profileStore';
import type {DetailGroup, ProfileCell} from './profileTabState';
import ProfileDetails from './ProfileDetails.svelte';

function cell(key: string, state: ProfileCell['state']): ProfileCell {
    const step = state === 'unavailable' ? null : ({date: '2026-01-01', through: '2026-11-17', value: state === 'value' ? 'x' : null, source: 'justetf', update_id: 1} as ProfileStep);
    return {key, voice: {key} as ProfileVoice, state, step};
}

const GROUPS: DetailGroup[] = [
    {group: 'fund', cells: [cell('fund_provider', 'value'), cell('index_name', 'unavailable')]},
    {group: 'company', cells: [cell('industry', 'emptied')]},
    {group: 'identity', cells: [cell('legal_form', 'value')]},
    {group: 'bond', cells: [cell('coupon_type', 'unavailable')]},
];
const TEXTS = {fund_provider: 'Vanguard', legal_form: 'Fondo UCITS', industry: 'should not show'};

describe('ProfileDetails', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it('shows a section per group, in order, with a row per voice and its state', () => {
        render(ProfileDetails, {props: {groups: GROUPS, texts: TEXTS, isin: 'IE00BK5BQT80', ticker: null}});
        const sections = screen.getAllByTestId(/^profile-details-group-/).map((node) => node.getAttribute('data-testid'));
        expect(sections).toEqual(['profile-details-group-fund', 'profile-details-group-company', 'profile-details-group-identity', 'profile-details-group-bond']);
        expect(screen.getByTestId('profile-detail-fund_provider')).toHaveAttribute('data-state', 'value');
        expect(screen.getByTestId('profile-detail-fund_provider')).toHaveTextContent('Vanguard');
        expect(screen.getByTestId('profile-detail-index_name')).toHaveAttribute('data-state', 'unavailable');
        expect(screen.getByTestId('profile-detail-industry')).toHaveAttribute('data-state', 'emptied');
        expect(screen.getByTestId('profile-detail-industry')).not.toHaveTextContent('should not show');
    });

    it('adds the ISIN and the ticker to the identity group', () => {
        render(ProfileDetails, {props: {groups: GROUPS, texts: TEXTS, isin: 'IE00BK5BQT80', ticker: null}});
        const identity = screen.getByTestId('profile-details-group-identity');
        expect(within(identity).getByTestId('profile-detail-isin')).toHaveAttribute('data-state', 'value');
        expect(within(identity).getByTestId('profile-detail-isin')).toHaveTextContent('IE00BK5BQT80');
        expect(within(identity).getByTestId('profile-detail-ticker')).toHaveAttribute('data-state', 'unavailable');
    });

    it('opens the history of a voice with a value, when the page handles it', async () => {
        const onhistory = vi.fn();
        render(ProfileDetails, {props: {groups: GROUPS, texts: TEXTS, isin: null, ticker: null, onhistory}});
        await fireEvent.click(screen.getByTestId('profile-detail-fund_provider-history'));
        expect(onhistory).toHaveBeenCalledWith('fund_provider');
        expect(screen.queryByTestId('profile-detail-index_name-history')).toBeNull();
    });

    it('has no history control without a handler', () => {
        render(ProfileDetails, {props: {groups: GROUPS, texts: TEXTS, isin: null, ticker: null}});
        expect(screen.queryByTestId('profile-detail-fund_provider-history')).toBeNull();
    });
});
