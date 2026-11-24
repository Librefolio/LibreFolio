// @vitest-environment jsdom
/**
 * ProfileDetails (plan 68, E4): the «Dettagli» of the «Profilo» tab.
 *
 * Pinned:
 * - one section per group it is given, in that order, each with a row per voice (`data-state` value, emptied,
 *   unavailable); the text of a row is the one it is given, only with a value;
 * - the identity group adds the asset's ISIN and ticker, which are the asset's identifiers, not profile voices: a row
 *   each, «not available» without one;
 * - a row with a value opens the voice's history (E6) when the page handles it; otherwise it is plain text;
 * - BI-PROF: the company's `website` with an http(s) address is a link opened apart (`target=_blank`,
 *   `rel=noopener noreferrer`), also when the page handles the history (the link wins: no history control on that row);
 *   any other text of it, and an address in another voice, is not a link.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import type {ProfileStep, ProfileVoice} from './profileStore';
import type {DetailGroup, ProfileCell} from './profileTabState';
import ProfileDetails from './ProfileDetails.svelte';
import {get} from 'svelte/store';
import {_} from '$lib/i18n';

function websiteGroups(): DetailGroup[] {
    return [{group: 'company', cells: [cell('website', 'value'), cell('industry', 'value')]}];
}

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

    it('names the sector of the company «Sector», not after the map of the classification', () => {
        const company: DetailGroup[] = [{group: 'company', cells: [cell('sector', 'unavailable')]}];
        render(ProfileDetails, {props: {groups: company, texts: {}, isin: null, ticker: null}});
        expect(screen.getByTestId('profile-detail-sector')).toHaveTextContent(get(_)('assets.profile.tab.companySector'));
        expect(screen.getByTestId('profile-detail-sector')).not.toHaveTextContent(get(_)('assets.profile.voices.sector'));
    });

    it('adds the ISIN and the ticker to the identity group', () => {
        render(ProfileDetails, {props: {groups: GROUPS, texts: TEXTS, isin: 'IE00BK5BQT80', ticker: null}});
        const identity = screen.getByTestId('profile-details-group-identity');
        expect(within(identity).getByTestId('profile-detail-isin')).toHaveAttribute('data-state', 'value');
        expect(within(identity).getByTestId('profile-detail-isin')).toHaveTextContent('IE00BK5BQT80');
        expect(within(identity).getByTestId('profile-detail-ticker')).toHaveAttribute('data-state', 'unavailable');
    });

    it('adds the other identifiers of the asset after the ISIN and the ticker', () => {
        render(ProfileDetails, {
            props: {
                groups: GROUPS,
                texts: TEXTS,
                isin: null,
                ticker: 'VWCE',
                otherIdentifiers: [
                    ['FIGI', 'BBG00XYZ'],
                    ['CUSIP', '123456789'],
                ],
            },
        });
        const identity = screen.getByTestId('profile-details-group-identity');
        const rows = within(identity)
            .getAllByTestId(/^profile-detail-identifier-/)
            .map((node) => node.textContent);
        expect(rows).toHaveLength(2);
        expect(rows[0]).toContain('BBG00XYZ');
        expect(rows[1]).toContain('123456789');
    });

    // 81 U26b: the asset's «other» identifiers are free values, not a typed id: one row «Other identifiers» with a chip
    // each (the look of «Modifica asset»'s tag input, read-only), in monospace, never one row per value labelled «other».
    it('shows the free identifiers as chips in one row, read-only and in monospace', () => {
        render(ProfileDetails, {props: {groups: GROUPS, texts: TEXTS, isin: null, ticker: 'VWCE', softIdentifiers: ['WKN A2PKXG', 'LU-0001']}});
        const identity = screen.getByTestId('profile-details-group-identity');
        const row = within(identity).getByTestId('profile-detail-soft-identifiers');
        const chips = within(row).getAllByTestId(/^profile-detail-soft-identifier-/);
        expect(chips.map((chip) => chip.textContent?.trim())).toEqual(['WKN A2PKXG', 'LU-0001']);
        for (const chip of chips) {
            expect(chip.className, 'the value is not in monospace').toContain('font-mono');
            expect(chip.querySelector('button'), 'a read-only chip has no remove control').toBeNull();
        }
        expect(within(identity).queryAllByTestId(/^profile-detail-identifier-/), 'a row per free value is still drawn').toHaveLength(0);
    });

    it('draws no free-identifiers row when the asset has none', () => {
        render(ProfileDetails, {props: {groups: GROUPS, texts: TEXTS, isin: null, ticker: null}});
        expect(screen.queryByTestId('profile-detail-soft-identifiers')).toBeNull();
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

    it('says «non aggiornato» under a row it is given that line for, and publishes it (D1d)', () => {
        render(ProfileDetails, {props: {groups: GROUPS, texts: TEXTS, staleTexts: {fund_provider: 'Confirmed on 18/09/2026, not up to date'}, isin: null, ticker: null}});
        expect(screen.getByTestId('profile-detail-fund_provider')).toHaveAttribute('data-stale', 'true');
        expect(screen.getByTestId('profile-detail-fund_provider-stale')).toHaveTextContent('Confirmed on 18/09/2026, not up to date');
        expect(screen.getByTestId('profile-detail-legal_form')).toHaveAttribute('data-stale', 'false');
        expect(screen.queryByTestId('profile-detail-legal_form-stale')).toBeNull();
    });

    it('shows the company website as a link opened in a new tab (BI-PROF)', () => {
        const address = 'https://www.enel.com/investors/overview';
        render(ProfileDetails, {props: {groups: websiteGroups(), texts: {website: address, industry: 'Utilities'}, isin: null, ticker: null}});
        const row = screen.getByTestId('profile-detail-website');
        expect(row).toHaveAttribute('data-state', 'value');
        const link = within(row).getByTestId('profile-detail-website-link');
        expect(link.tagName).toBe('A');
        expect(link).toHaveAttribute('href', address);
        expect(link).toHaveAttribute('target', '_blank');
        expect(link).toHaveAttribute('rel', 'noopener noreferrer');
        expect(link).toHaveAttribute('title', get(_)('assets.profile.tab.openWebsite'));
        expect(link).toHaveTextContent(address);
        expect(row).toHaveTextContent(get(_)('assets.profile.voices.website'));
    });

    it('keeps the website a link when the page handles the history: that row has no history control', () => {
        const onhistory = vi.fn();
        render(ProfileDetails, {props: {groups: websiteGroups(), texts: {website: 'https://www.enel.com', industry: 'Utilities'}, isin: null, ticker: null, onhistory}});
        expect(screen.getByTestId('profile-detail-website-link')).toHaveAttribute('href', 'https://www.enel.com');
        expect(screen.queryByTestId('profile-detail-website-history')).toBeNull();
        expect(screen.getByTestId('profile-detail-industry-history'), 'barrier: the other rows of the group open their history').toBeInTheDocument();
    });

    it.each(['javascript:alert(1)', 'mailto:investor.relations@enel.com', 'www.enel.com'])('writes a website %j that is not an http address as text, never a link', (text) => {
        render(ProfileDetails, {props: {groups: websiteGroups(), texts: {website: text, industry: 'Utilities'}, isin: null, ticker: null}});
        const row = screen.getByTestId('profile-detail-website');
        expect(row).toHaveAttribute('data-state', 'value');
        expect(row).toHaveTextContent(text);
        expect(screen.queryByTestId('profile-detail-website-link')).toBeNull();
        expect(row.querySelector('a')).toBeNull();
    });

    it('never makes a link of an address in another voice', () => {
        render(ProfileDetails, {props: {groups: websiteGroups(), texts: {website: 'https://www.enel.com', industry: 'https://example.com'}, isin: null, ticker: null}});
        expect(screen.getByTestId('profile-detail-website-link'), 'barrier: the website is a link').toBeInTheDocument();
        expect(screen.getByTestId('profile-detail-industry').querySelector('a')).toBeNull();
        expect(screen.getAllByTestId('profile-detail-website-link')).toHaveLength(1);
    });
});
