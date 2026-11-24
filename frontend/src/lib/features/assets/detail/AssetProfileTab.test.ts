// @vitest-environment jsdom
/**
 * AssetProfileTab (plan 68, E3+E4): the «Profilo» tab of the asset page — classification, description, key figures and
 * details of one asset, for the period chosen at the top of the page.
 *
 * Pinned:
 * - it reads the profile of its asset for the page's period (`start: 'min'` for «Tutti»), and reads again when the period
 *   or `refreshKey` changes; a slower, older answer never replaces a newer one;
 * - it publishes its loading (`data-busy`, `aria-busy`) and its outcome (`data-status`: ready, failed, missing);
 * - the cards and the details come from the catalogue, the description from its voice;
 * - «Modifica i dati» is there only when the page handles it (E8);
 * - E6b2: the clock beside «Descrizione» opens its history, when it has rows and the page handles it;
 * - E6c: with enrichers, «Aggiorna» beside it says the last read and is busy while the page refreshes (never on the next
 *   asset); without any, the box «Nessun arricchitore configurato» with «Configura»; enrichers not known yet, neither;
 * - BI-PROF: a fiscal year's figure is written «<value> (fiscal year <year of its source date>)»; without a source date,
 *   the value alone; the company's website reaches the details as a link.
 *
 * How it is tested: the real tab and its parts, real i18n; the profile memory faked (`profileStore`), the charts stood in.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const store = vi.hoisted(() => ({
    loadProfileCatalogue: vi.fn(),
    readAssetProfile: vi.fn(),
}));
vi.mock('$lib/features/assets/profile/profileStore', () => store);
vi.mock('$lib/stores/reference/countryStore', () => ({
    ensureCountriesLoaded: vi.fn(async () => undefined),
    getCountryInfo: (iso3: string) => ({iso3, iso2: '', name: iso3, flag_emoji: ''}),
}));
vi.mock('$lib/stores/reference/currencyStore', () => ({
    ensureCurrenciesLoaded: vi.fn(),
    getCurrencyInfo: (code: string) => ({code, flag_emoji: ''}),
}));
const charts = vi.hoisted(() => ({
    standIn: (id: string) => (anchor: ChildNode) => {
        const element = document.createElement('div');
        element.setAttribute('data-testid', id);
        anchor.before(element);
    },
}));
vi.mock('$lib/components/charts/PriceChartCompact.svelte', () => ({default: charts.standIn('stand-in-chart')}));
vi.mock('$lib/components/charts/GeographyMap.svelte', () => ({default: charts.standIn('stand-in-map')}));
vi.mock('$lib/components/charts/AllocationPieChart.svelte', () => ({default: charts.standIn('stand-in-pie')}));

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import type {AssetProfileRead, ProfileStep, ProfileVoice} from '$lib/features/assets/profile/profileStore';
import AssetProfileTab from './AssetProfileTab.svelte';
import {softIdentifiers} from '$lib/utils/assetTypes';
import {get} from 'svelte/store';
import {_} from '$lib/i18n';

function voice(key: string, shape: string, extra: Partial<ProfileVoice> = {}): ProfileVoice {
    return {key, shape, sign: null, unit: null, groups: [], key_figure: false, charted: false, volatile: false, choices: [], map_keys: null, topic: 'structure', ...extra} as ProfileVoice;
}
function step(value: unknown, date = '2026-01-01', through = '2026-11-17'): ProfileStep {
    return {date, through, value, source: 'justetf', update_id: 1} as ProfileStep;
}

const CATALOGUE = [
    voice('geography', 'map', {map_keys: 'country', groups: ['classification']}),
    voice('sector', 'map', {map_keys: 'sector', groups: ['classification', 'company']}),
    voice('description', 'text'),
    voice('ter', 'percentage', {groups: ['key_figures'], key_figure: true, charted: true}),
    voice('maturity_date', 'date', {groups: ['key_figures'], key_figure: true}),
    voice('fund_provider', 'text', {groups: ['fund']}),
    voice('legal_form', 'choice', {groups: ['identity'], choices: ['ucits_fund']}),
];
const FOUND: AssetProfileRead = {
    kind: 'found',
    asOf: '2026-11-17T10:00:00Z',
    voices: {description: [step('A world equity fund')], ter: [step('0.0019')], fund_provider: [step('Vanguard')], geography: [step({USA: '1'})]},
    changes: null,
};
const PERIOD = {start: '2025-11-17', end: '2026-11-17', all: false};

/** A read the test answers when it wants. */
function deferred<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((done) => (resolve = done));
    return {promise, resolve};
}

describe('AssetProfileTab', () => {
    beforeAll(async () => {
        await setupI18n();
    });
    beforeEach(() => {
        store.loadProfileCatalogue.mockReset().mockResolvedValue(CATALOGUE);
        store.readAssetProfile.mockReset().mockResolvedValue(FOUND);
    });

    it('reads its asset for the period of the page, and shows cards, details and description', async () => {
        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: 'IE00BK5BQT80', ticker: null}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-busy', 'false');
        expect(store.readAssetProfile).toHaveBeenCalledWith(7, {start: '2025-11-17', end: '2026-11-17'});
        expect(screen.getByTestId('profile-key-figure-ter')).toHaveAttribute('data-state', 'value');
        expect(screen.getByTestId('profile-key-figure-maturity_date')).toHaveAttribute('data-state', 'unavailable');
        expect(screen.getByTestId('profile-detail-fund_provider')).toHaveTextContent('Vanguard');
        expect(screen.getByTestId('profile-detail-isin')).toHaveTextContent('IE00BK5BQT80');
        expect(screen.getByTestId('asset-profile-description')).toHaveAttribute('data-state', 'value');
        expect(screen.getByTestId('asset-profile-description')).toHaveTextContent('A world equity fund');
        expect(screen.getByTestId('profile-classification-geography')).toHaveAttribute('data-state', 'value');
    });

    // 81 U26b: the page hands the tab the asset's free identifiers, and they reach «Identità» as one row of chips.
    it('passes the free identifiers to the identity group as chips', async () => {
        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null, softIdentifiers: ['WKN A2PKXG']}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        expect(screen.getByTestId('profile-detail-soft-identifier-0')).toHaveTextContent('WKN A2PKXG');
    });

    it('reads from the first day of the profile for «Tutti»', async () => {
        render(AssetProfileTab, {props: {assetId: 7, period: {start: '2019-01-04', end: '2026-11-17', all: true}, isin: null, ticker: null}});
        await waitFor(() => expect(store.readAssetProfile).toHaveBeenCalledWith(7, {start: 'min', end: '2026-11-17'}));
    });

    it('reads again when the period or the refresh key changes', async () => {
        const view = render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null, refreshKey: 0}});
        await waitFor(() => expect(store.readAssetProfile).toHaveBeenCalledTimes(1));
        await view.rerender({assetId: 7, period: {start: '2026-05-17', end: '2026-11-17', all: false}, isin: null, ticker: null, refreshKey: 0});
        await waitFor(() => expect(store.readAssetProfile).toHaveBeenLastCalledWith(7, {start: '2026-05-17', end: '2026-11-17'}));
        await view.rerender({assetId: 7, period: {start: '2026-05-17', end: '2026-11-17', all: false}, isin: null, ticker: null, refreshKey: 1});
        await waitFor(() => expect(store.readAssetProfile).toHaveBeenCalledTimes(3));
    });

    it('keeps the newer answer when an older one arrives last', async () => {
        const slow = deferred<AssetProfileRead>();
        const fast = deferred<AssetProfileRead>();
        store.readAssetProfile.mockReturnValueOnce(slow.promise).mockReturnValueOnce(fast.promise);
        const view = render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null}});
        await waitFor(() => expect(store.readAssetProfile).toHaveBeenCalledTimes(1));
        await view.rerender({assetId: 7, period: {start: '2026-05-17', end: '2026-11-17', all: false}, isin: null, ticker: null});
        await waitFor(() => expect(store.readAssetProfile).toHaveBeenCalledTimes(2));
        fast.resolve({...FOUND, voices: {fund_provider: [step('Newer')]}});
        await waitFor(() => expect(screen.getByTestId('profile-detail-fund_provider')).toHaveTextContent('Newer'));
        slow.resolve({...FOUND, voices: {fund_provider: [step('Older')]}});
        await new Promise((done) => setTimeout(done, 0));
        expect(screen.getByTestId('profile-detail-fund_provider')).toHaveTextContent('Newer');
    });

    it('is busy while it reads', async () => {
        const pending = deferred<AssetProfileRead>();
        store.readAssetProfile.mockReturnValue(pending.promise);
        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-busy', 'true'));
        expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('aria-busy', 'true');
        pending.resolve(FOUND);
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-busy', 'false'));
    });

    it('says when the read failed, and when the asset no longer exists', async () => {
        store.readAssetProfile.mockRejectedValueOnce(new Error('network'));
        const view = render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'failed'));
        view.unmount();
        store.readAssetProfile.mockResolvedValueOnce({kind: 'missing', asOf: '2026-11-17T10:00:00Z'});
        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'missing'));
    });

    it('offers «Modifica i dati» only when the page handles it', async () => {
        const onedit = vi.fn();
        const view = render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        expect(screen.queryByTestId('asset-profile-edit')).toBeNull();
        view.unmount();
        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null, onedit}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        await fireEvent.click(screen.getByTestId('asset-profile-edit'));
        expect(onedit).toHaveBeenCalledOnce();
    });

    it('says «non aggiornato» on the card and the detail of a stale voice, and only there (D1d)', async () => {
        const stale = {...step('0.0019'), confirmed_on: '2026-09-18', stale: true} as ProfileStep;
        const fresh = {...step('Vanguard'), confirmed_on: '2026-11-10', stale: false} as ProfileStep;
        store.readAssetProfile.mockResolvedValue({...FOUND, voices: {...FOUND.voices, ter: [stale], fund_provider: [fresh]}});
        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        expect(screen.getByTestId('profile-key-figure-ter')).toHaveAttribute('data-stale', 'true');
        expect(screen.getByTestId('profile-key-figure-ter-stale')).toHaveTextContent('18');
        expect(screen.getByTestId('profile-detail-fund_provider')).toHaveAttribute('data-stale', 'false');
    });

    it('offers «Aggiorna» with the last read when the asset has enrichers, busy while the page refreshes (E6c)', async () => {
        const done = deferred<void>();
        const onrefresh = vi.fn(() => done.promise);
        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null, onedit: vi.fn(), enrichers: {count: 2, lastRead: '2026-11-08'}, onrefresh, onconfigure: vi.fn()}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        expect(screen.queryByTestId('asset-profile-no-enrichers')).toBeNull();
        const button = screen.getByTestId('asset-profile-refresh');
        expect(button).toHaveAttribute('data-last-read', '2026-11-08');
        expect(button).toHaveAttribute('data-state', 'idle');
        expect(button.getAttribute('aria-label'), 'the accessible name starts with the visible label').toMatch(/^Refresh · /);
        expect(button.getAttribute('title')).toContain('2026');

        await fireEvent.click(button);
        expect(onrefresh).toHaveBeenCalledOnce();
        expect(button).toHaveAttribute('data-state', 'running');
        expect(button).toBeDisabled();
        done.resolve();
        await waitFor(() => expect(button).toHaveAttribute('data-state', 'idle'));
        expect(button).not.toBeDisabled();
    });

    it('says «mai letto» in the hint of an asset never read', async () => {
        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null, enrichers: {count: 1, lastRead: null}, onrefresh: vi.fn(async () => undefined)}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        expect(screen.getByTestId('asset-profile-refresh')).toHaveAttribute('data-last-read', '');
    });

    it('does not carry a running «Aggiorna» to the next asset', async () => {
        const onrefresh = vi.fn(() => new Promise<void>(() => undefined));
        const props = {period: PERIOD, isin: null, ticker: null, enrichers: {count: 1, lastRead: null}, onrefresh};
        const view = render(AssetProfileTab, {props: {assetId: 7, ...props}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        await fireEvent.click(screen.getByTestId('asset-profile-refresh'));
        expect(screen.getByTestId('asset-profile-refresh')).toHaveAttribute('data-state', 'running');
        await view.rerender({assetId: 8, ...props});
        await waitFor(() => expect(screen.getByTestId('asset-profile-refresh')).toHaveAttribute('data-state', 'idle'));
    });

    it('without enrichers shows the box with «Configura» and no «Aggiorna»; before they are known, neither (E6c)', async () => {
        const onconfigure = vi.fn();
        const view = render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null, enrichers: {count: 0, lastRead: null}, onrefresh: vi.fn(), onconfigure}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        expect(screen.queryByTestId('asset-profile-refresh')).toBeNull();
        await fireEvent.click(screen.getByTestId('asset-profile-configure'));
        expect(onconfigure).toHaveBeenCalledOnce();
        view.unmount();

        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null, enrichers: null, onrefresh: vi.fn(), onconfigure}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        expect(screen.queryByTestId('asset-profile-refresh')).toBeNull();
        expect(screen.queryByTestId('asset-profile-no-enrichers')).toBeNull();
    });

    it('opens the history of the description from the clock beside its title (E6b2)', async () => {
        const onhistory = vi.fn();
        const view = render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null, onhistory}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        await fireEvent.click(screen.getByTestId('asset-profile-description-history'));
        expect(onhistory).toHaveBeenCalledWith('description');
        expect(screen.getByTestId('profile-classification-geography-history'), 'the tab hands the clock to the classification').toBeInTheDocument();
        view.unmount();

        store.readAssetProfile.mockResolvedValue({...FOUND, voices: {ter: [step('0.0019')]}});
        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null, onhistory}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        expect(screen.queryByTestId('asset-profile-description-history'), 'no rows, no history').toBeNull();
    });
});

describe('AssetProfileTab — the company figures of a fiscal year (BI-PROF)', () => {
    const COMPANY = [
        ...CATALOGUE,
        voice('website', 'text', {groups: ['company'], topic: 'issuer'}),
        voice('revenue', 'amount', {groups: ['company'], topic: 'financials', sign: 'non_negative', period: 'fiscal_year'} as Partial<ProfileVoice>),
        voice('net_income', 'amount', {groups: ['company'], topic: 'financials', sign: 'any', period: 'fiscal_year'} as Partial<ProfileVoice>),
    ];
    const dated = (value: unknown, source_date: string | null) => ({...step(value), source_date}) as ProfileStep;

    beforeAll(async () => {
        await setupI18n();
    });
    beforeEach(() => {
        store.loadProfileCatalogue.mockReset().mockResolvedValue(COMPANY);
        store.readAssetProfile.mockReset();
    });

    it('names the fiscal year of each figure beside its value, from its source date', async () => {
        store.readAssetProfile.mockResolvedValue({
            ...FOUND,
            voices: {
                revenue: [dated({amount: '78057000000', currency: 'EUR'}, '2025-12-31')],
                net_income: [dated({amount: '5617000000', currency: 'EUR'}, '2024-12-31')],
                website: [dated('https://www.enel.com/investors/overview', '2026-10-23')],
            },
        });
        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        const year = (value: string) => `(${get(_)('assets.profile.tab.fiscalYear', {values: {year: value}})})`;
        const revenue = screen.getByTestId('profile-detail-revenue');
        expect(revenue).toHaveAttribute('data-state', 'value');
        expect(revenue).toHaveTextContent('EUR');
        expect(revenue).toHaveTextContent(year('2025'));
        expect(screen.getByTestId('profile-detail-net_income')).toHaveTextContent(year('2024'));
        expect(screen.getByTestId('profile-detail-net_income')).not.toHaveTextContent(year('2025'));
        const website = screen.getByTestId('profile-detail-website');
        expect(website, 'the website is no period figure: no year beside it').not.toHaveTextContent('(');
        expect(screen.getByTestId('profile-detail-website-link')).toHaveAttribute('href', 'https://www.enel.com/investors/overview');
    });

    it('writes the value alone when the figure has no source date, and no year for an emptied one', async () => {
        store.readAssetProfile.mockResolvedValue({
            ...FOUND,
            voices: {revenue: [dated({amount: '78057000000', currency: 'EUR'}, null)], net_income: [dated(null, '2025-12-31')]},
        });
        render(AssetProfileTab, {props: {assetId: 7, period: PERIOD, isin: null, ticker: null}});
        await waitFor(() => expect(screen.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready'));
        const revenue = screen.getByTestId('profile-detail-revenue');
        expect(revenue).toHaveTextContent('EUR');
        expect(revenue).not.toHaveTextContent('(');
        expect(screen.getByTestId('profile-detail-net_income')).toHaveAttribute('data-state', 'emptied');
        expect(screen.getByTestId('profile-detail-net_income')).not.toHaveTextContent('2025');
    });
});

// 81 U26b: the asset's free identifiers (type `OTHER`) as the page reads them from the asset.
describe('softIdentifiers', () => {
    it('lists the non-empty free values in order, and ignores a missing or non-text field', () => {
        expect(softIdentifiers({identifier_other: ['B', '', 'A', null, 3]})).toEqual(['B', 'A']);
        expect(softIdentifiers({identifier_other: null})).toEqual([]);
        expect(softIdentifiers({})).toEqual([]);
        expect(softIdentifiers({identifier_other: 'WKN'})).toEqual(['WKN']);
    });
});
