// @vitest-environment jsdom
/**
 * AssetEnrichersModal (plan 68, E7b2): the «Arricchitori dell'asset» window, standalone (E8 opens it from the asset
 * window and saves what it hands back with the asset).
 *
 * Pinned through the contract (what `onapply` hands back, the calls made, the states the rows publish), never through
 * translated text:
 * - an untouched window hands back the same config, a binding to an enricher the instance does not serve included;
 * - the rows publish their position, whether the instance can use them, their last read and what they fill (topics);
 * - a not configured enricher is drawn off with «Configura»;
 * - removing a row moves it to «Non in elenco» as «removed by you», «+» puts it back at the end with its binding;
 * - a row opens: «Cerca su …» searches that enricher, a result fills type and identifier; «Testa Configurazione» tests
 *   the binding and says found (and what it would fill), not found, not configured;
 * - a row without an identifier blocks «Usa questi arricchitori».
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import AssetEnrichersModal from './AssetEnrichersModal.svelte';
import type {EnricherBinding, EnricherInfo} from './enrichersEditState';
import type {ProfileVoice} from '$lib/features/assets/profile/profileStore';
import type {PluginSettingsEntry} from '$lib/features/plugin-settings/pluginSettingsApi';

function info(code: string, extra: Partial<EnricherInfo> = {}): EnricherInfo {
    return {
        code,
        name: `${code} name`,
        icon: null,
        help_url: null,
        terms: 'open',
        accepted_identifier_types: ['ISIN'],
        params_schema: [],
        supports_search: false,
        voices: {ETF: ['ter', 'geography']},
        default_priority: {ETF: 10},
        configured: true,
        missing_settings: [],
        ...extra,
    } as EnricherInfo;
}

const CATALOGUE: EnricherInfo[] = [
    info('justetf', {voices: {ETF: ['ter', 'replication', 'geography', 'sector', 'fund_size']}}),
    info('yahoo', {accepted_identifier_types: ['TICKER', 'ISIN'], supports_search: true, voices: {ETF: ['fund_provider', 'sector']}, default_priority: {ETF: 20}}),
    info('keyed', {configured: false, missing_settings: ['api_key']}),
    info('esma', {voices: {ETF: ['legal_form']}, default_priority: {ETF: 40}}),
    info('borsa_italiana', {
        voices: {ETF: ['fund_currency']},
        default_priority: {ETF: 30},
        params_schema: [
            {key: 'language', type: 'select', options: ['en', 'it'], default: 'it', label: 'Language'},
            {key: 'mic', type: 'string', label: 'Market MIC'},
        ],
    }),
];

const PROFILE: ProfileVoice[] = [
    {key: 'ter', topic: 'costs'},
    {key: 'replication', topic: 'structure'},
    {key: 'geography', topic: 'countries'},
    {key: 'sector', topic: 'sectors'},
    {key: 'fund_size', topic: 'size'},
    {key: 'fund_provider', topic: 'manager'},
    {key: 'legal_form', topic: 'legal_form'},
] as unknown as ProfileVoice[];

const CONFIG: Record<string, EnricherBinding> = {
    justetf: {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'},
    switched_off: {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'},
    yahoo: {identifier_type: 'TICKER', identifier: 'VWRA.L'},
};

const STATE = {
    justetf: {read_at: '2026-11-08T03:00:00+00:00', status: 'ok', error_code: null},
    yahoo: {read_at: '2026-11-08T03:00:00+00:00', status: 'not_found', error_code: null},
};

function mount(extra: Record<string, unknown> = {}) {
    const onapply = vi.fn();
    const oncancel = vi.fn();
    const search = vi.fn().mockResolvedValue([]);
    const test = vi.fn();
    // Whether the caller may see an enricher's settings (`GET /settings/plugins`): by default it may
    const loadSettings = vi.fn(async (code: string) => ({plugin_code: code, plugin_name: code, configured: false}) as unknown as PluginSettingsEntry);
    render(AssetEnrichersModal, {
        open: true,
        asset: {name: 'Vanguard FTSE All-World', assetType: 'ETF', identifiers: {ISIN: 'IE00BK5BQT80'}},
        config: CONFIG,
        readState: STATE,
        catalogue: CATALOGUE,
        profileCatalogue: PROFILE,
        onapply,
        oncancel,
        search,
        test,
        loadSettings,
        ...extra,
    });
    return {onapply, oncancel, search, test, loadSettings};
}

function renderWith(extra: Record<string, unknown> = {}) {
    const onapply = vi.fn();
    const result = render(AssetEnrichersModal, {
        open: true,
        asset: {name: 'Vanguard FTSE All-World', assetType: 'ETF', identifiers: {ISIN: 'IE00BK5BQT80'}},
        config: CONFIG,
        readState: STATE,
        catalogue: CATALOGUE,
        profileCatalogue: PROFILE,
        onapply,
        loadSettings: vi.fn(async () => null),
        ...extra,
    });
    return {onapply, rerender: (props: Record<string, unknown>) => result.rerender(props)};
}

const chosen = (code: string) => screen.getByTestId(`enricher-row-${code}`);
const other = (code: string) => screen.getByTestId(`enricher-other-${code}`);

async function apply(onapply: ReturnType<typeof vi.fn>): Promise<Record<string, EnricherBinding>> {
    await fireEvent.click(screen.getByTestId('enrichers-apply'));
    expect(onapply).toHaveBeenCalledTimes(1);
    return onapply.mock.calls[0][0] as Record<string, EnricherBinding>;
}

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

describe('AssetEnrichersModal — the list', () => {
    it('an untouched window hands back the same config, the binding the instance does not serve included', async () => {
        const {onapply} = mount();
        const config = await apply(onapply);
        expect(Object.keys(config)).toEqual(['justetf', 'switched_off', 'yahoo']);
        expect(config).toEqual(CONFIG);
    });

    it('the rows say their position, whether they can be used, their last read and their topics', () => {
        mount();
        expect(chosen('justetf').dataset).toMatchObject({position: '1', availability: 'ok', lastRead: 'ok'});
        expect(chosen('switched_off').dataset).toMatchObject({position: '2', availability: 'off'});
        expect(chosen('switched_off').dataset.lastRead).toBeUndefined();
        expect(chosen('yahoo').dataset).toMatchObject({position: '3', lastRead: 'not_found'});
        expect(screen.getByTestId('enricher-topics-justetf').dataset).toMatchObject({topics: 'costs,structure,countries,sectors', more: '1'});
    });

    it('a not configured enricher is drawn off, with «Configura» when the caller may see its settings', async () => {
        mount({config: {keyed: {identifier_type: 'ISIN', identifier: 'X'}}});
        expect(chosen('keyed').dataset.availability).toBe('not_configured');
        expect(await within(chosen('keyed')).findByTestId('enricher-configure-keyed')).toBeInTheDocument();
    });

    it('no «Configura» when the caller may not see the settings (as the price providers, N3)', async () => {
        const loadSettings = vi.fn(async (): Promise<PluginSettingsEntry | null> => null);
        mount({config: {keyed: {identifier_type: 'ISIN', identifier: 'X'}}, loadSettings});
        await waitFor(() => expect(loadSettings).toHaveBeenCalledWith('keyed'));
        expect(within(chosen('keyed')).queryByTestId('enricher-configure-keyed')).toBeNull();
        expect(chosen('keyed').dataset.availability).toBe('not_configured');
    });

    it('an enricher added from «Non in elenco» with no matching identifier on the asset is empty and its row opens: the identifier alone unblocks', async () => {
        const {onapply} = mount({asset: {name: 'Vanguard', assetType: 'ETF', identifiers: {TICKER: 'VWCE'}}});
        await fireEvent.click(screen.getByTestId('enricher-add-esma'));
        expect(chosen('esma').dataset.expanded).toBe('true');
        expect((screen.getByTestId('enricher-identifier-esma') as HTMLInputElement).value).toBe('');
        await fireEvent.change(screen.getByTestId('enricher-identifier-esma'), {target: {value: 'IE00BK5BQT80'}});
        expect(chosen('esma').dataset.issue).toBeUndefined();
        expect((await apply(onapply)).esma).toEqual({identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'});
    });

    it('«+» fills the binding from the asset identifiers and the row stays closed', async () => {
        const {onapply} = mount();
        await fireEvent.click(screen.getByTestId('enricher-add-esma'));
        expect(chosen('esma').dataset.expanded).toBe('false');
        expect(chosen('esma').dataset.issue).toBeUndefined();
        expect((await apply(onapply)).esma).toEqual({identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'});
    });

    it('a removed row goes to «Non in elenco» as removed by you, and «+» puts it back at the end with its binding', async () => {
        const {onapply} = mount();
        await fireEvent.click(screen.getByTestId('enricher-remove-justetf'));
        expect(screen.queryByTestId('enricher-row-justetf')).toBeNull();
        expect(other('justetf').dataset.reason).toBe('removed');
        await fireEvent.click(screen.getByTestId('enricher-add-justetf'));
        const config = await apply(onapply);
        expect(Object.keys(config)).toEqual(['switched_off', 'yahoo', 'justetf']);
        expect(config.justetf).toEqual(CONFIG.justetf);
    });

    it('«Non in elenco» lists the others with their reason; one that cannot be added has no «+»', () => {
        mount();
        expect(other('keyed').dataset.reason).toBe('not_configured');
        expect(screen.queryByTestId('enricher-add-keyed')).toBeNull();
        expect(other('esma').dataset.reason).toBe('new');
    });

    it('a row without an identifier blocks «Usa questi arricchitori»', async () => {
        mount({asset: {name: 'Vanguard', assetType: 'ETF', identifiers: {}}});
        await fireEvent.click(screen.getByTestId('enricher-add-esma'));
        expect(chosen('esma').dataset.issue).toBe('no_identifier');
        expect(screen.getByTestId('enrichers-apply')).toBeDisabled();
    });
});

describe('AssetEnrichersModal — a row opened', () => {
    it('«Cerca su …» searches that enricher, and a result fills type and identifier', async () => {
        const {search, onapply} = mount();
        search.mockResolvedValue([{name: 'Vanguard FTSE All-World USD Acc', binding: {identifier_type: 'TICKER', identifier: 'VWRL.AS'}, asset_type: 'ETF', page_url: null}]);
        await fireEvent.click(screen.getByTestId('enricher-edit-yahoo'));
        const query = screen.getByTestId('enricher-search-yahoo') as HTMLInputElement;
        await fireEvent.input(query, {target: {value: 'IE00BK5BQT80'}});
        await fireEvent.keyDown(query, {key: 'Enter'});
        expect(search).toHaveBeenCalledWith('yahoo', 'IE00BK5BQT80');
        await fireEvent.click(await screen.findByTestId('enricher-result-yahoo-0'));
        expect((screen.getByTestId('enricher-identifier-yahoo') as HTMLInputElement).value).toBe('VWRL.AS');
        expect((await apply(onapply)).yahoo).toEqual({identifier_type: 'TICKER', identifier: 'VWRL.AS'});
    });

    it('the open row is drawn selected (the selection role of the design system), the others are not', async () => {
        mount();
        const tone = (code: string) => (chosen(code).closest('[data-tone]') as HTMLElement).dataset.tone;
        expect(tone('justetf')).toBe('default');
        await fireEvent.click(screen.getByTestId('enricher-edit-justetf'));
        expect(tone('justetf')).toBe('selected');
        expect(tone('yahoo')).toBe('default');
    });

    it('«Testa Configurazione» tests the binding and says what it found and would fill', async () => {
        const {test} = mount();
        test.mockResolvedValue({code: 'justetf', identifier_type: 'ISIN', identifier: 'IE00BK5BQT80', status: 'found', name: 'Vanguard', page_url: null, identifiers: {}, conflicts: {}, error: null});
        await fireEvent.click(screen.getByTestId('enricher-edit-justetf'));
        await fireEvent.click(screen.getByTestId('enricher-test-justetf'));
        expect(test).toHaveBeenCalledWith('justetf', CONFIG.justetf);
        await waitFor(() => expect(screen.getByTestId('enricher-test-result-justetf').dataset.status).toBe('found'));
    });

    it('a test refused because the enricher is not configured says so', async () => {
        const {test} = mount();
        test.mockRejectedValue({status: 422, data: {detail: {error_code: 'NOT_CONFIGURED', missing: ['api_key']}}});
        await fireEvent.click(screen.getByTestId('enricher-edit-justetf'));
        await fireEvent.click(screen.getByTestId('enricher-test-justetf'));
        await waitFor(() => expect(screen.getByTestId('enricher-test-result-justetf').dataset.status).toBe('not_configured'));
    });

    it('«Usa questi arricchitori» right after typing takes the identifier: no click lost waiting for the field to let the focus go (E7c)', async () => {
        // An asset with no identifier: «+» opens the row empty, the user types it (R3 would fill it from an ISIN)
        const {onapply} = mount({asset: {name: 'Vanguard', assetType: 'ETF', identifiers: {}}});
        await fireEvent.click(screen.getByTestId('enricher-add-esma'));
        // Typed only: no «change», no blur — the user clicks the button straight after the last key
        await fireEvent.input(screen.getByTestId('enricher-identifier-esma'), {target: {value: 'IE00BK5BQT80'}});
        const button = screen.getByTestId('enrichers-apply') as HTMLButtonElement;
        expect(button.disabled, 'the window must be valid as soon as the identifier is typed').toBe(false);
        await fireEvent.click(button);
        expect(onapply).toHaveBeenCalledOnce();
        expect(onapply.mock.calls[0][0].esma).toEqual({identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'});
    });

    it('typing the identifier by hand changes the binding', async () => {
        const {onapply} = mount();
        await fireEvent.click(screen.getByTestId('enricher-edit-justetf'));
        const input = screen.getByTestId('enricher-identifier-justetf') as HTMLInputElement;
        // The field commits on «change» (blur or Enter), as the browser fires it
        await fireEvent.change(input, {target: {value: 'IE00B3RBWM25'}});
        expect((await apply(onapply)).justetf).toEqual({identifier_type: 'ISIN', identifier: 'IE00B3RBWM25'});
    });
});

describe("AssetEnrichersModal — the plugin's parameters", () => {
    const BI = {borsa_italiana: {identifier_type: 'ISIN', identifier: 'IT0005565400'}};

    it('a parameter typed goes in the binding; emptied, it leaves it; a select left alone writes nothing', async () => {
        const {onapply} = mount({config: BI});
        await fireEvent.click(screen.getByTestId('enricher-edit-borsa_italiana'));
        const mic = screen.getByTestId('enricher-param-borsa_italiana-mic') as HTMLInputElement;
        await fireEvent.change(mic, {target: {value: 'ETFP'}});
        await fireEvent.change(mic, {target: {value: 'MTAA'}});
        expect((await apply(onapply)).borsa_italiana).toEqual({identifier_type: 'ISIN', identifier: 'IT0005565400', mic: 'MTAA'});
    });

    it('emptying a parameter removes it from the binding', async () => {
        const {onapply} = mount({config: {borsa_italiana: {...BI.borsa_italiana, mic: 'ETFP'}}});
        await fireEvent.click(screen.getByTestId('enricher-edit-borsa_italiana'));
        await fireEvent.change(screen.getByTestId('enricher-param-borsa_italiana-mic'), {target: {value: ''}});
        expect((await apply(onapply)).borsa_italiana).toEqual(BI.borsa_italiana);
    });
});

describe('AssetEnrichersModal — a search refused', () => {
    it('too many searches says so, not a generic failure', async () => {
        const {search} = mount();
        search.mockRejectedValue({status: 429, data: {detail: {error_code: 'RATE_LIMITED'}}});
        await fireEvent.click(screen.getByTestId('enricher-edit-yahoo'));
        const query = screen.getByTestId('enricher-search-yahoo') as HTMLInputElement;
        await fireEvent.input(query, {target: {value: 'IE00BK5BQT80'}});
        await fireEvent.keyDown(query, {key: 'Enter'});
        await waitFor(() => expect(screen.getByTestId('enricher-search-refused-yahoo').dataset.status).toBe('rate_limited'));
    });
});

const recognized = (code: string, status: string, extra: Record<string, unknown> = {}) => ({code, status, identifier_type: 'ISIN', identifier: 'IE00BK5BQT80', name: `${code} found`, page_url: null, identifiers: {}, conflicts: {}, error: null, ...extra});

describe('AssetEnrichersModal — the identifier type of a row', () => {
    it('one accepted type: a fixed badge, no select; two: the select', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('enricher-edit-justetf'));
        expect(screen.getByTestId('enricher-type-fixed-justetf').dataset.type).toBe('ISIN');
        expect(screen.queryByTestId('enricher-type-justetf')).toBeNull();
        await fireEvent.click(screen.getByTestId('enricher-edit-yahoo'));
        expect(screen.getByTestId('enricher-type-yahoo')).toBeInTheDocument();
        expect(screen.queryByTestId('enricher-type-fixed-yahoo')).toBeNull();
    });
});

describe('AssetEnrichersModal — the line of «Riconosci» (ENR-1)', () => {
    it('renders with its state and counts; absent when the caller gives none', () => {
        mount({line: {state: 'running', answered: 1, asked: 4, found: []}});
        const line = screen.getByTestId('enrichers-recognition');
        expect(line.dataset).toMatchObject({state: 'running', answered: '1', asked: '4'});
    });

    it('no line, no element', () => {
        mount();
        expect(screen.queryByTestId('enrichers-recognition')).toBeNull();
    });

    it('follows the state it is given', async () => {
        const {rerender} = renderWith({line: {state: 'running', answered: 0, asked: 2, found: []}});
        expect(screen.getByTestId('enrichers-recognition').dataset.state).toBe('running');
        await rerender({line: {state: 'found', answered: 2, asked: 2, found: ['esma']}});
        expect(screen.getByTestId('enrichers-recognition').dataset.state).toBe('found');
    });
});

describe("AssetEnrichersModal — «Riconosci»'s proposal (ENR-1, R2)", () => {
    const ISIN = {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'};

    it('a proposal arriving after the window opened enters «Scelti» when it adopts', async () => {
        const {rerender, onapply} = renderWith({config: {}, adopt: true, proposal: {}});
        expect(screen.queryByTestId('enricher-row-esma')).toBeNull();
        await rerender({proposal: {esma: ISIN}});
        await waitFor(() => expect(chosen('esma')).toBeInTheDocument());
        expect(screen.queryByTestId('enricher-other-esma')).toBeNull();
        expect((await apply(onapply)).esma).toEqual(ISIN);
    });

    it('without adopt the proposal stays out', async () => {
        const {rerender} = renderWith({config: {}, adopt: false, proposal: {}});
        await rerender({proposal: {esma: ISIN}});
        expect(screen.queryByTestId('enricher-row-esma')).toBeNull();
    });

    it('after a removal a new proposal does not re-add what the user took out, nor anything else', async () => {
        const {rerender} = renderWith({config: {}, adopt: true, proposal: {esma: ISIN}});
        await waitFor(() => expect(chosen('esma')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('enricher-remove-esma'));
        await rerender({proposal: {esma: ISIN, justetf: ISIN}});
        expect(screen.queryByTestId('enricher-row-esma')).toBeNull();
        expect(screen.queryByTestId('enricher-row-justetf')).toBeNull();
        expect(other('esma').dataset.reason).toBe('removed');
    });

    it('after the user typed a binding a new proposal does not enter', async () => {
        const {rerender} = renderWith({config: {}, adopt: true, proposal: {esma: ISIN}});
        await waitFor(() => expect(chosen('esma')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('enricher-edit-esma'));
        await fireEvent.change(screen.getByTestId('enricher-identifier-esma'), {target: {value: 'IE00B3RBWM25'}});
        await rerender({proposal: {esma: ISIN, justetf: ISIN}});
        expect(screen.queryByTestId('enricher-row-justetf')).toBeNull();
    });
});

describe('AssetEnrichersModal — «Non in elenco» after «Riconosci» (ENR-1)', () => {
    it('a ticker-only find is marked, shows the name it found, and «+» fills its ticker binding', async () => {
        const recognitions = {yahoo: recognized('yahoo', 'found', {identifier_type: 'TICKER', identifier: 'VWCE.DE', name: 'Vanguard FTSE All-World UCITS'})};
        const {onapply} = mount({config: {}, recognitions});
        expect(other('yahoo').dataset.tickerOnly).toBe('true');
        expect(screen.getByTestId('enricher-other-name-yahoo').textContent).toContain('Vanguard FTSE All-World UCITS');
        await fireEvent.click(screen.getByTestId('enricher-add-yahoo'));
        expect((await apply(onapply)).yahoo).toEqual({identifier_type: 'TICKER', identifier: 'VWCE.DE'});
    });

    it('a found one by ISIN is not marked ticker-only', () => {
        mount({config: {}, recognitions: {esma: recognized('esma', 'found')}});
        expect(other('esma').dataset.tickerOnly).toBeUndefined();
    });

    it('«+» on a not found one: the asked binding, the row open, the warning shown', async () => {
        mount({config: {}, recognitions: {esma: recognized('esma', 'not_found')}});
        await fireEvent.click(screen.getByTestId('enricher-add-esma'));
        expect(chosen('esma').dataset.expanded).toBe('true');
        expect(screen.getByTestId('enricher-not-found-with-esma')).toBeInTheDocument();
        expect((screen.getByTestId('enricher-identifier-esma') as HTMLInputElement).value).toBe('IE00BK5BQT80');
    });

    it('«+» on a conflict: the asked binding, the row closed, the warning shown', async () => {
        mount({config: {}, recognitions: {esma: recognized('esma', 'conflict', {conflicts: {LEI: 'OTHERLEI0000000000AA'}})}});
        await fireEvent.click(screen.getByTestId('enricher-add-esma'));
        expect(chosen('esma').dataset.expanded).toBe('false');
        expect(screen.getByTestId('enricher-conflict-with-esma')).toBeInTheDocument();
        expect(screen.queryByTestId('enricher-not-found-with-esma')).toBeNull();
    });

    it('«+» on an error: the asked binding, the row closed, no warning', async () => {
        mount({config: {}, recognitions: {esma: recognized('esma', 'error')}});
        await fireEvent.click(screen.getByTestId('enricher-add-esma'));
        expect(chosen('esma').dataset.expanded).toBe('false');
        expect(screen.queryByTestId('enricher-conflict-with-esma')).toBeNull();
        expect(screen.queryByTestId('enricher-not-found-with-esma')).toBeNull();
    });
});

describe('AssetEnrichersModal — the price assignment chip (ENR-2)', () => {
    it('renders the provider name and the identifier when given', () => {
        mount({price: {name: 'Yahoo Finance', identifier: 'SWDA.MI'}});
        const chip = screen.getByTestId('enrichers-asset-price');
        expect(chip.textContent).toContain('Yahoo Finance');
        expect(chip.textContent).toContain('SWDA.MI');
    });

    it('renders it even for an asset with no identifiers', () => {
        mount({price: {name: 'Yahoo Finance', identifier: 'SWDA.MI'}, asset: {name: 'X', assetType: 'ETF', identifiers: {}}});
        expect(screen.getByTestId('enrichers-asset-price')).toBeInTheDocument();
    });

    it('absent when there is none', () => {
        mount();
        expect(screen.queryByTestId('enrichers-asset-price')).toBeNull();
        cleanup();
        mount({price: null});
        expect(screen.queryByTestId('enrichers-asset-price')).toBeNull();
    });

    it('a ticker found by the price symbol is not «ticker only» in «Non in elenco»; another is', () => {
        const swda = (identifier: string) => ({code: 'yahoo', status: 'found', identifier_type: 'TICKER', identifier, name: 'iShares', page_url: null, identifiers: {}, conflicts: {}, error: null});
        mount({recognitions: {yahoo: swda('SWDA.MI')}, trustedTickers: ['SWDA.MI'], config: {}});
        expect(screen.getByTestId('enricher-other-yahoo').dataset.tickerOnly).toBeUndefined();
        cleanup();
        mount({recognitions: {yahoo: swda('SWDA')}, trustedTickers: ['SWDA.MI'], config: {}});
        expect(screen.getByTestId('enricher-other-yahoo').dataset.tickerOnly).toBe('true');
    });
});

describe('AssetEnrichersModal — «Cerca online» (ENR-3)', () => {
    const FOUND_ISIN = 'IE00B4L5Y983';
    const YAHOO_ONLY = {yahoo: {identifier_type: 'TICKER', identifier: 'VWRA.L'}};
    const searchResult = (code: string, identifier: string) => ({event: 'enricher_results', code, status: 'ok', via: 'search', results: [{name: `${code} result`, binding: {identifier_type: 'ISIN', identifier}}], accepted_identifier_types: ['ISIN'], retry_after: null, error_code: null});
    /** A «Cerca online» that answers esma with a result, and nobody else. */
    const onlineAnswering = (identifier: string) =>
        vi.fn(async (request: {q: string; codes: string[]}, options: {onEvent: (event: unknown) => void}) => {
            if (request.q !== identifier && request.codes.includes('esma')) options.onEvent(searchResult('esma', identifier));
            return {kind: 'done'};
        });
    const NO_ISIN = {name: 'Vanguard FTSE All-World', assetType: 'ETF', identifiers: {TICKER: 'VWRA'}};

    async function searchAndAdd(searchOnline: ReturnType<typeof onlineAnswering>) {
        await fireEvent.click(screen.getAllByTestId(/^enrichers-search-suggestion-/)[0]);
        await waitFor(() => expect(screen.getByTestId('enrichers-search').dataset.status).toBe('done'));
        const add = screen.getAllByTestId(/^enrichers-search-add-/).find((button) => button.dataset.testid?.includes('-esma-'));
        expect(add, 'esma has a row to add').toBeDefined();
        await fireEvent.click(add as HTMLElement);
        expect(searchOnline).toHaveBeenCalled();
    }

    it('mounts the search on top of the window', () => {
        mount();
        expect(screen.getByTestId('enrichers-search')).toBeInTheDocument();
        expect(screen.getByTestId('enrichers-search-input')).toBeInTheDocument();
    });

    it('«+» on a result puts the code in «Scelti», the row closed, and out of «Non in elenco» and the pills', async () => {
        const searchOnline = onlineAnswering(FOUND_ISIN);
        mount({config: YAHOO_ONLY, asset: NO_ISIN, searchOnline});
        expect(other('esma').dataset.reason).toBe('new');
        expect(screen.getByTestId('enrichers-search-pill-esma')).toBeInTheDocument();

        await searchAndAdd(searchOnline);
        await waitFor(() => expect(screen.getByTestId('enricher-row-esma')).toBeInTheDocument());
        expect(chosen('esma').dataset.expanded).toBe('false');
        expect(chosen('esma').dataset.position).toBe('2');
        expect(screen.queryByTestId('enricher-other-esma')).toBeNull();
        expect(screen.queryByTestId('enrichers-search-pill-esma')).toBeNull();
        // The search stays open
        expect(screen.getByTestId('enrichers-search')).toBeInTheDocument();
    });

    it('hands back the ISIN of a binding added from the search when the asset has none (R7)', async () => {
        const searchOnline = onlineAnswering(FOUND_ISIN);
        const {onapply} = mount({config: YAHOO_ONLY, asset: NO_ISIN, searchOnline});
        await searchAndAdd(searchOnline);
        await waitFor(() => expect(screen.getByTestId('enricher-row-esma')).toBeInTheDocument());
        const config = await apply(onapply);
        expect(config.esma).toEqual({identifier_type: 'ISIN', identifier: FOUND_ISIN});
        expect(onapply.mock.calls[0][1]).toEqual({identifiers: {ISIN: FOUND_ISIN}});
    });

    it('hands back nothing when the asset has the ISIN already', async () => {
        const searchOnline = onlineAnswering('IE00BK5BQT80');
        const {onapply} = mount({config: YAHOO_ONLY, searchOnline});
        await searchAndAdd(searchOnline);
        await waitFor(() => expect(screen.getByTestId('enricher-row-esma')).toBeInTheDocument());
        await apply(onapply);
        expect(onapply.mock.calls[0][1]).toEqual({identifiers: {}});
    });

    it('hands back nothing for a code that came from «Non in elenco», nor for a search result removed again', async () => {
        const searchOnline = onlineAnswering(FOUND_ISIN);
        const {onapply} = mount({config: YAHOO_ONLY, asset: NO_ISIN, searchOnline});
        await fireEvent.click(screen.getByTestId('enricher-add-esma'));
        await fireEvent.change(screen.getByTestId('enricher-identifier-esma'), {target: {value: FOUND_ISIN}});
        await apply(onapply);
        expect(onapply.mock.calls[0][1]).toEqual({identifiers: {}});

        cleanup();
        const second = mount({config: YAHOO_ONLY, asset: NO_ISIN, searchOnline});
        await searchAndAdd(searchOnline);
        await waitFor(() => expect(screen.getByTestId('enricher-row-esma')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('enricher-remove-esma'));
        await apply(second.onapply);
        expect(second.onapply.mock.calls[0][1]).toEqual({identifiers: {}});
    });
});
