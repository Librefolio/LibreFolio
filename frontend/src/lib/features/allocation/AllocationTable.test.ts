// @vitest-environment jsdom
/**
 * AllocationTable — the slices as a table (Vitest + jsdom): a click opens a slice in place, what is excluded stays at the bottom
 * struck and with no share, and the amounts follow the privacy toggle in both directions.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';

vi.mock('$lib/stores/reference/countryStore', () => ({
    ensureCountriesLoaded: async () => {},
    getCountryInfo: (iso3: string) => ({iso3, iso2: '', name: `Country ${iso3}`, flag_emoji: '🏳'}),
}));
vi.mock('$lib/stores/reference/sectorStore', () => ({
    ensureSectorsLoaded: async () => {},
    getSectorEmoji: () => '🏭',
    sectorEmojiVersion: () => 0,
}));

import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import AllocationTable from './AllocationTable.svelte';
import {makeView} from './allocation.fixture';
import type {AllocationResponse} from './allocationQuery';

beforeAll(async () => {
    await setupI18n();
});
beforeEach(() => setPrivacyEnabled(false));
afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

const view = (overrides: Partial<AllocationResponse> = {}) =>
    makeView({
        dimension: 'geography',
        slices: [
            {
                key: 'USA',
                asset_id: null,
                amount: '23600.00',
                share_of_selection: '64.00',
                share_of_portfolio: '29.50',
                assets: [
                    {asset_id: 1, amount: '19600.00', share_of_slice: '83.05'},
                    {asset_id: 2, amount: '4000.00', share_of_slice: '16.95'},
                ],
            },
            {key: 'ITA', asset_id: null, amount: '3000.00', share_of_selection: '8.10', share_of_portfolio: '3.75', assets: [{asset_id: 3, amount: '3000.00', share_of_slice: '100.00'}]},
        ],
        excluded: {amount: '4120.00', by_bucket: [{key: 'Unknown', amount: '4120.00'}], by_asset: [], unattributable: []},
        ...overrides,
    });

const row = (id: string) => document.querySelector(`tr[data-row-id="${id}"]`) as HTMLElement | null;
const ids = () => [...document.querySelectorAll('tbody tr[data-row-id]')].map((tr) => tr.getAttribute('data-row-id'));

describe('rows', () => {
    it('lists the slices in the backend order, then what is excluded', () => {
        render(AllocationTable, {view: view(), testId: 't'});
        expect(ids()).toEqual(['slice:USA', 'slice:ITA', 'excluded:bucket:Unknown']);
        expect(screen.getByTestId('t')).toHaveAttribute('data-dimension', 'geography');
    });

    it('draws a slice with its two shares and its asset count, and the excluded row with none, struck', () => {
        render(AllocationTable, {view: view(), testId: 't'});
        const usa = row('slice:USA')!;
        expect(usa.textContent).toContain('Country USA');
        expect(usa.textContent).toContain('64');
        expect(usa.textContent).toContain('29');
        expect(within(usa).getAllByRole('cell').at(-1)!.textContent).toContain('2');

        const excluded = row('excluded:bucket:Unknown')!;
        expect(excluded.querySelector('.line-through'), 'struck').not.toBeNull();
        expect(excluded.textContent).toContain('—');
        expect(excluded.textContent).not.toContain('64');
    });

    it('shows «—» for a share the backend did not send', () => {
        render(AllocationTable, {view: view({slices: [{key: 'USA', asset_id: null, amount: '10.00', share_of_selection: null, share_of_portfolio: null, assets: []}]}), testId: 't'});
        expect(row('slice:USA')!.textContent).toContain('—');
    });
});

describe('opening a slice', () => {
    it('shows the assets that make it up under it, each with its share of the slice, and closes again', async () => {
        render(AllocationTable, {view: view(), testId: 't'});
        await fireEvent.click(row('slice:USA')!);
        expect(ids()).toEqual(['slice:USA', 'detail:USA:1', 'detail:USA:2', 'slice:ITA', 'excluded:bucket:Unknown']);
        expect(row('detail:USA:1')!.textContent).toContain('World ETF');
        expect(row('detail:USA:1')!.textContent).toContain('83');
        await fireEvent.click(row('slice:USA')!);
        expect(ids()).toEqual(['slice:USA', 'slice:ITA', 'excluded:bucket:Unknown']);
    });

    it('does nothing on a click on a slice with no assets, an excluded row or a detail row', async () => {
        render(AllocationTable, {view: view({slices: [{key: 'USA', asset_id: null, amount: '10.00', share_of_selection: '100.00', share_of_portfolio: '10.00', assets: []}]}), testId: 't'});
        await fireEvent.click(row('slice:USA')!);
        await fireEvent.click(row('excluded:bucket:Unknown')!);
        expect(ids()).toEqual(['slice:USA', 'excluded:bucket:Unknown']);
    });
});

describe('privacy', () => {
    it('masks the amounts, keeps the percentages, and shows the amounts again, in place', async () => {
        render(AllocationTable, {view: view(), testId: 't'});
        expect(row('slice:USA')!.textContent).not.toContain(PRIVACY_PLACEHOLDER);

        setPrivacyEnabled(true);
        await Promise.resolve();
        await vi.waitFor(() => expect(row('slice:USA')!.textContent).toContain(PRIVACY_PLACEHOLDER));
        expect(row('slice:USA')!.textContent).not.toContain('23');
        expect(row('slice:USA')!.textContent, 'the percentage stays').toContain('64');
        expect(row('excluded:bucket:Unknown')!.textContent).toContain(PRIVACY_PLACEHOLDER);

        setPrivacyEnabled(false);
        await Promise.resolve();
        await vi.waitFor(() => expect(row('slice:USA')!.textContent).not.toContain(PRIVACY_PLACEHOLDER));
        expect(row('slice:USA')!.textContent).toContain('23');
    });
});

describe('the hint', () => {
    it('says what the two % columns add up to, and drops the second when there is no share', () => {
        const {unmount} = render(AllocationTable, {view: view(), testId: 't'});
        expect(screen.getByTestId('t-hint').textContent).toContain('46');
        unmount();
        render(AllocationTable, {view: view({base_share_of_portfolio: null}), testId: 't'});
        expect(screen.getByTestId('t-hint').textContent).not.toContain('46');
    });
});
