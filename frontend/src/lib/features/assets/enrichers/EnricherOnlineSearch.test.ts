// @vitest-environment jsdom
/**
 * EnricherOnlineSearch (ENR-3): «Cerca online» on top of the enrichers' window.
 *
 * Pinned through the contract (the calls made, the states and data attributes published), never through translated text:
 * - a suggestion (asset name, ISIN, ticker) is searched with one touch, at once, with the pills that are on;
 * - typing waits for a pause and at least 2 characters; a pill turned off leaves the codes asked, and re-searches;
 * - a row appears with each enricher's answer; «+» hands the result over, the search stays open with its text;
 * - a result naming another ISIN than the asset's needs a second touch to confirm (R13);
 * - an ISIN added asks once the enrichers without a search that accept it (R12), the same ISIN never twice;
 * - what an enricher said that is not a result is a note per code: no results, identifier only, rate limited, error;
 * - a refusal and a failure are published as such.
 *
 * How it is tested: the real component, real i18n; the search a fake that answers from a script.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import EnricherOnlineSearch from './EnricherOnlineSearch.svelte';
import {addFromSearch, draftFrom, type EnricherInfo, type EnrichersDraft, type SearchHit} from './enrichersEditState';
import type {EnricherSearchEvent, EnricherSearchOutcome, EnricherSearchRequest} from './enricherSearchStream';

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
        voices: {ETF: ['ter']},
        default_priority: {ETF: 10},
        configured: true,
        missing_settings: [],
        ...extra,
    } as EnricherInfo;
}

const CATALOGUE: EnricherInfo[] = [info('yahoo', {accepted_identifier_types: ['TICKER', 'ISIN'], supports_search: true}), info('mockenrich', {accepted_identifier_types: ['TICKER', 'ISIN'], supports_search: true}), info('justetf'), info('esma')];

const ISIN = 'IE00BK5BQT80';
const OTHER_ISIN = 'US0378331005';
const hit = (type: string, identifier: string, name = `${identifier} result`): SearchHit => ({name, binding: {identifier_type: type, identifier}});
const answer = (code: string, results: SearchHit[], extra: Record<string, unknown> = {}): EnricherSearchEvent => ({event: 'enricher_results', code, status: 'ok', via: 'search', results, accepted_identifier_types: ['ISIN'], retry_after: null, error_code: null, ...extra}) as EnricherSearchEvent;

type Script = (request: EnricherSearchRequest) => EnricherSearchEvent[];

/** A search that answers each call from `script`, at once. */
function scripted(script: Script = () => []) {
    return vi.fn(async (request: EnricherSearchRequest, options: {onEvent: (event: EnricherSearchEvent) => void; signal?: AbortSignal}): Promise<EnricherSearchOutcome> => {
        for (const event of script(request)) options.onEvent(event);
        return {kind: 'done'};
    });
}

function mount(extra: Record<string, unknown> = {}) {
    const onadd = vi.fn();
    const search = (extra.search as ReturnType<typeof scripted> | undefined) ?? scripted();
    const props = {catalogue: CATALOGUE, assetType: 'ETF', draft: draftFrom({}), assetIdentifiers: {ISIN, TICKER: 'VWRA'} as Record<string, string>, assetName: 'Vanguard FTSE All-World', onadd, search, ...extra};
    const view = render(EnricherOnlineSearch, props);
    return {onadd, search, rerender: (next: Record<string, unknown>) => view.rerender({...props, ...next})};
}

const root = () => screen.getByTestId('enrichers-search');
const input = () => screen.getByTestId('enrichers-search-input') as HTMLInputElement;
const type = (value: string) => fireEvent.input(input(), {target: {value}});
const suggestion = (value: string) => screen.getAllByTestId(/^enrichers-search-suggestion-/).find((element) => element.dataset.value === value) as HTMLElement;
const ready = () => waitFor(() => expect(root().dataset.status).toBe('done'));

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
    vi.useRealTimers();
});

describe('the suggestions', () => {
    it('offers the asset name, ISIN and ticker, each once; a touch searches at once with the pills on', async () => {
        const {search} = mount();
        expect(screen.getAllByTestId(/^enrichers-search-suggestion-/).map((element) => element.dataset.value)).toEqual(['Vanguard FTSE All-World', ISIN, 'VWRA']);
        await fireEvent.click(suggestion(ISIN));
        expect(search).toHaveBeenCalledTimes(1);
        expect(search.mock.calls[0][0]).toEqual({q: ISIN, codes: ['yahoo', 'mockenrich', 'justetf', 'esma'], assetType: 'ETF'});
        expect(input().value).toBe(ISIN);
        await ready();
    });

    it('leaves out a value that is missing, too short, or repeated', () => {
        mount({assetName: 'VWRA', assetIdentifiers: {TICKER: 'VWRA', ISIN: ' '}});
        expect(screen.getAllByTestId(/^enrichers-search-suggestion-/).map((element) => element.dataset.value)).toEqual(['VWRA']);
        cleanup();
        mount({assetName: 'x', assetIdentifiers: {}});
        expect(screen.queryAllByTestId(/^enrichers-search-suggestion-/)).toEqual([]);
    });

    it('a second touch while one is running replaces it: the first is aborted', async () => {
        let first: AbortSignal | undefined;
        const search = vi.fn(async (_request: EnricherSearchRequest, options: {signal?: AbortSignal}): Promise<EnricherSearchOutcome> => {
            first ??= options.signal;
            return new Promise(() => undefined);
        });
        mount({search});
        await fireEvent.click(suggestion(ISIN));
        await fireEvent.click(suggestion('VWRA'));
        expect(search).toHaveBeenCalledTimes(2);
        expect(first?.aborted).toBe(true);
        expect(root().dataset.busy).toBe('true');
    });
});

describe('typing', () => {
    it('waits for a pause and needs 2 characters', async () => {
        vi.useFakeTimers();
        const {search} = mount();
        await type('v');
        await vi.advanceTimersByTimeAsync(2000);
        expect(search).not.toHaveBeenCalled();

        await type('va');
        await vi.advanceTimersByTimeAsync(300);
        expect(search).not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(150);
        expect(search).toHaveBeenCalledTimes(1);
        expect(search.mock.calls[0][0].q).toBe('va');
    });

    it('a new key restarts the pause: one call, with the last text', async () => {
        vi.useFakeTimers();
        const {search} = mount();
        await type('vang');
        await vi.advanceTimersByTimeAsync(300);
        await type('vanguard');
        await vi.advanceTimersByTimeAsync(300);
        expect(search).not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(150);
        expect(search).toHaveBeenCalledTimes(1);
        expect(search.mock.calls[0][0].q).toBe('vanguard');
    });

    it('a text cut under 2 characters clears the answers', async () => {
        vi.useFakeTimers();
        const {search} = mount({search: scripted(() => [answer('yahoo', [hit('TICKER', 'VWRA')])])});
        await type('vwra');
        await vi.advanceTimersByTimeAsync(500);
        expect(screen.getByTestId('enrichers-search-row-yahoo-0')).toBeInTheDocument();
        await type('v');
        await vi.advanceTimersByTimeAsync(500);
        expect(search).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('enrichers-search-row-yahoo-0')).toBeNull();
        expect(root().dataset.status).toBe('idle');
    });
});

describe('the pills', () => {
    it('one per enricher not chosen, on; the ones without a search say identifier only; the chosen ones are on the excluded line', () => {
        mount({draft: draftFrom({justetf: {identifier_type: 'ISIN', identifier: ISIN}})});
        expect(screen.getAllByTestId(/^enrichers-search-pill-/).map((pill) => pill.dataset.testid?.replace('enrichers-search-pill-', ''))).toEqual(['yahoo', 'mockenrich', 'esma']);
        expect(screen.getByTestId('enrichers-search-pill-yahoo').dataset.on).toBe('true');
        expect(screen.getByTestId('enrichers-search-pill-yahoo').dataset.identifierOnly).toBeUndefined();
        expect(screen.getByTestId('enrichers-search-pill-esma').dataset.identifierOnly).toBe('true');
        expect(screen.getByTestId('enrichers-search-excluded')).toBeInTheDocument();
    });

    it('no excluded line when nothing is chosen', () => {
        mount();
        expect(screen.queryByTestId('enrichers-search-excluded')).toBeNull();
    });

    it('a pill turned off leaves the codes asked, and with a text a new search starts after the pause', async () => {
        vi.useFakeTimers();
        const {search} = mount();
        await fireEvent.click(screen.getByTestId('enrichers-search-pill-yahoo'));
        expect(screen.getByTestId('enrichers-search-pill-yahoo').dataset.on).toBe('false');
        expect(search, 'no text, nothing to ask').not.toHaveBeenCalled();

        await fireEvent.click(suggestion(ISIN));
        expect(search.mock.calls[0][0].codes).toEqual(['mockenrich', 'justetf', 'esma']);

        await fireEvent.click(screen.getByTestId('enrichers-search-pill-esma'));
        await vi.advanceTimersByTimeAsync(500);
        expect(search).toHaveBeenCalledTimes(2);
        expect(search.mock.calls[1][0]).toMatchObject({q: ISIN, codes: ['mockenrich', 'justetf']});
    });

    it('with every pill off nothing is asked', async () => {
        const {search} = mount({catalogue: [CATALOGUE[0]]});
        await fireEvent.click(screen.getByTestId('enrichers-search-pill-yahoo'));
        await fireEvent.click(suggestion(ISIN));
        expect(search).not.toHaveBeenCalled();
        expect(root().dataset.status).toBe('idle');
    });
});

describe('the rows', () => {
    it('appear with each answer, in the order they arrive', async () => {
        let release: () => void = () => undefined;
        let emit: (event: EnricherSearchEvent) => void = () => undefined;
        const search = vi.fn((_request: EnricherSearchRequest, options: {onEvent: (event: EnricherSearchEvent) => void}) => {
            emit = options.onEvent;
            return new Promise<EnricherSearchOutcome>((resolve) => (release = () => resolve({kind: 'done'})));
        });
        mount({search});
        await fireEvent.click(suggestion('VWRA'));
        expect(root().dataset.status).toBe('searching');
        expect(root().dataset.busy).toBe('true');
        expect(screen.queryByTestId('enrichers-search-results')).toBeNull();

        emit(answer('yahoo', [hit('TICKER', 'VWRA.L', 'First')]));
        const first = await screen.findByTestId('enrichers-search-row-yahoo-0');
        expect(first.dataset.code).toBe('yahoo');
        expect(screen.queryByTestId('enrichers-search-row-mockenrich-0')).toBeNull();

        emit(answer('mockenrich', [hit('TICKER', 'VWRA', 'Second'), hit('TICKER', 'VWRA2', 'Third')]));
        expect((await screen.findByTestId('enrichers-search-row-mockenrich-1')).dataset.code).toBe('mockenrich');
        expect(screen.getAllByTestId(/^enrichers-search-row-/)).toHaveLength(3);

        release();
        await ready();
        expect(root().dataset.busy).toBe('false');
    });

    it('«+» hands the result over, the search stays open with its text, and the enricher leaves rows and pills', async () => {
        const result = hit('TICKER', 'VWRA.L');
        const {onadd, rerender} = mount({search: scripted(() => [answer('yahoo', [result]), answer('mockenrich', [hit('TICKER', 'VWRA')])])});
        await fireEvent.click(suggestion('VWRA'));
        await ready();

        await fireEvent.click(screen.getByTestId('enrichers-search-add-yahoo-0'));
        expect(onadd).toHaveBeenCalledTimes(1);
        expect(onadd).toHaveBeenCalledWith('yahoo', result);
        expect(screen.queryByTestId('enrichers-search-added')).toBeNull();

        // The window put it in its list
        const draft: EnrichersDraft = addFromSearch(draftFrom({}), 'yahoo', result.binding);
        await rerender({draft});
        expect(root()).toBeInTheDocument();
        expect(input().value).toBe('VWRA');
        expect(screen.queryByTestId('enrichers-search-row-yahoo-0')).toBeNull();
        expect(screen.queryByTestId('enrichers-search-pill-yahoo')).toBeNull();
        expect(screen.getByTestId('enrichers-search-row-mockenrich-0')).toBeInTheDocument();
        expect(screen.getByTestId('enrichers-search-added').dataset.code).toBe('yahoo');
        expect(screen.getByTestId('enrichers-search-excluded')).toBeInTheDocument();
    });

    it('a result with the asset’s own ISIN is added at once, and so is a ticker', async () => {
        const {onadd} = mount({search: scripted(() => [answer('yahoo', [hit('ISIN', ISIN.toLowerCase())]), answer('mockenrich', [hit('TICKER', 'VWRA')])])});
        await fireEvent.click(suggestion('VWRA'));
        await ready();
        expect(screen.getByTestId('enrichers-search-row-yahoo-0').dataset.conflict).toBeUndefined();
        expect(screen.getByTestId('enrichers-search-row-mockenrich-0').dataset.conflict).toBeUndefined();
        await fireEvent.click(screen.getByTestId('enrichers-search-add-mockenrich-0'));
        expect(onadd).toHaveBeenCalledTimes(1);
    });

    it('a result naming another ISIN is flagged and needs a second touch (R13)', async () => {
        const result = hit('ISIN', OTHER_ISIN);
        const {onadd} = mount({search: scripted(() => [answer('yahoo', [result])])});
        await fireEvent.click(suggestion('VWRA'));
        await ready();

        expect(screen.getByTestId('enrichers-search-row-yahoo-0').dataset.conflict).toBe('true');
        expect(screen.getByTestId('enrichers-search-conflict-yahoo-0')).toBeInTheDocument();
        expect(screen.queryByTestId('enrichers-search-confirm-yahoo-0')).toBeNull();

        await fireEvent.click(screen.getByTestId('enrichers-search-add-yahoo-0'));
        expect(onadd).not.toHaveBeenCalled();
        expect(screen.queryByTestId('enrichers-search-add-yahoo-0')).toBeNull();

        await fireEvent.click(screen.getByTestId('enrichers-search-confirm-yahoo-0'));
        expect(onadd).toHaveBeenCalledTimes(1);
        expect(onadd).toHaveBeenCalledWith('yahoo', result);
    });

    it('a new search drops a confirmation waiting', async () => {
        const {onadd} = mount({search: scripted(() => [answer('yahoo', [hit('ISIN', OTHER_ISIN)])])});
        await fireEvent.click(suggestion('VWRA'));
        await ready();
        await fireEvent.click(screen.getByTestId('enrichers-search-add-yahoo-0'));
        expect(screen.getByTestId('enrichers-search-confirm-yahoo-0')).toBeInTheDocument();
        await fireEvent.click(suggestion(ISIN));
        await waitFor(() => expect(screen.getByTestId('enrichers-search-add-yahoo-0')).toBeInTheDocument());
        expect(screen.queryByTestId('enrichers-search-confirm-yahoo-0')).toBeNull();
        expect(onadd).not.toHaveBeenCalled();
    });
});

describe('the ISIN follow-up (R12)', () => {
    const answers = (request: EnricherSearchRequest): EnricherSearchEvent[] => {
        if (request.q === OTHER_ISIN) return [answer('esma', [hit('ISIN', OTHER_ISIN, 'From ESMA')]), answer('justetf', [], {status: 'not_configured'})];
        return [answer('yahoo', [hit('ISIN', OTHER_ISIN)]), answer('mockenrich', [hit('ISIN', OTHER_ISIN)])];
    };

    it('adding an ISIN result asks the enrichers without a search that accept it, and shows their rows', async () => {
        const search = scripted(answers);
        const {onadd} = mount({search, assetIdentifiers: {}});
        await fireEvent.click(suggestion('Vanguard FTSE All-World'));
        await ready();
        await fireEvent.click(screen.getByTestId('enrichers-search-add-yahoo-0'));
        expect(onadd).toHaveBeenCalledTimes(1);

        await waitFor(() => expect(search).toHaveBeenCalledTimes(2));
        expect(search.mock.calls[1][0]).toEqual({q: OTHER_ISIN, codes: ['justetf', 'esma'], assetType: 'ETF'});
        const row = await screen.findByTestId(`enrichers-search-row-isin-${OTHER_ISIN}-esma-0`);
        expect(row.dataset.code).toBe('esma');
        // The row of the first search is still there (its key counts the results of its own enricher)
        expect(screen.getByTestId('enrichers-search-row-mockenrich-0')).toBeInTheDocument();
        // A follow-up row is added like any other
        await fireEvent.click(screen.getByTestId(`enrichers-search-add-isin-${OTHER_ISIN}-esma-0`));
        expect(onadd).toHaveBeenLastCalledWith('esma', expect.objectContaining({name: 'From ESMA'}));
    });

    it('asks the same ISIN once, however many results carry it', async () => {
        const search = scripted(answers);
        const {onadd} = mount({search, assetIdentifiers: {}});
        await fireEvent.click(suggestion('Vanguard FTSE All-World'));
        await ready();
        await fireEvent.click(screen.getByTestId('enrichers-search-add-yahoo-0'));
        await waitFor(() => expect(search).toHaveBeenCalledTimes(2));
        await fireEvent.click(screen.getByTestId('enrichers-search-add-mockenrich-0'));
        expect(onadd).toHaveBeenCalledTimes(2);
        await waitFor(() => expect(screen.getByTestId(`enrichers-search-row-isin-${OTHER_ISIN}-esma-0`)).toBeInTheDocument());
        expect(search).toHaveBeenCalledTimes(2);
    });

    it('a ticker result asks nothing more', async () => {
        const search = scripted(() => [answer('yahoo', [hit('TICKER', 'VWRA.L')])]);
        mount({search});
        await fireEvent.click(suggestion('VWRA'));
        await ready();
        await fireEvent.click(screen.getByTestId('enrichers-search-add-yahoo-0'));
        expect(search).toHaveBeenCalledTimes(1);
    });

    it('a failed follow-up leaves the search as it was', async () => {
        const search = vi.fn(async (request: EnricherSearchRequest, options: {onEvent: (event: EnricherSearchEvent) => void}): Promise<EnricherSearchOutcome> => {
            if (request.q === OTHER_ISIN) throw new Error('boom');
            options.onEvent(answer('yahoo', [hit('ISIN', OTHER_ISIN)]));
            return {kind: 'done'};
        });
        const {onadd} = mount({search, assetIdentifiers: {}});
        await fireEvent.click(suggestion('Vanguard FTSE All-World'));
        await ready();
        await fireEvent.click(screen.getByTestId('enrichers-search-add-yahoo-0'));
        await waitFor(() => expect(search).toHaveBeenCalledTimes(2));
        expect(onadd).toHaveBeenCalledTimes(1);
        expect(root().dataset.status).toBe('done');
        expect(screen.queryByTestId('enrichers-search-failed')).toBeNull();
    });
});

describe('what is not a result', () => {
    it('says each enricher’s state in a note of its own', async () => {
        mount({
            search: scripted(() => [answer('yahoo', [], {status: 'ok'}), answer('mockenrich', [], {status: 'error', error_code: 'X'}), answer('esma', [], {status: 'identifier_only', via: null, accepted_identifier_types: ['ISIN']}), answer('justetf', [], {status: 'rate_limited', retry_after: 5})]),
        });
        await fireEvent.click(suggestion('VWRA'));
        await ready();
        expect(screen.getByTestId('enrichers-search-note-yahoo').dataset.status).toBe('ok');
        expect(screen.getByTestId('enrichers-search-note-mockenrich').dataset.status).toBe('error');
        expect(screen.getByTestId('enrichers-search-note-esma').dataset.status).toBe('identifier_only');
        expect(screen.getByTestId('enrichers-search-note-justetf').dataset.status).toBe('rate_limited');
        expect(screen.queryByTestId('enrichers-search-results')).toBeNull();
    });

    it('an enricher with results has no note, and a note goes away with the enricher added', async () => {
        const {rerender} = mount({search: scripted(() => [answer('yahoo', [hit('TICKER', 'VWRA.L')]), answer('esma', [], {status: 'identifier_only'})])});
        await fireEvent.click(suggestion('VWRA'));
        await ready();
        expect(screen.queryByTestId('enrichers-search-note-yahoo')).toBeNull();
        expect(screen.getByTestId('enrichers-search-note-esma')).toBeInTheDocument();
        await rerender({draft: addFromSearch(draftFrom({}), 'esma', {identifier_type: 'ISIN', identifier: ISIN})});
        expect(screen.queryByTestId('enrichers-search-note-esma')).toBeNull();
    });

    it('a refusal (429) is published as refused', async () => {
        const search = vi.fn(async (): Promise<EnricherSearchOutcome> => ({kind: 'refused', retryAfter: 9}));
        mount({search});
        await fireEvent.click(suggestion('VWRA'));
        await waitFor(() => expect(root().dataset.status).toBe('refused'));
        expect(screen.getByTestId('enrichers-search-refused')).toBeInTheDocument();
        expect(screen.queryByTestId('enrichers-search-failed')).toBeNull();
    });

    it('a failure is published as an error', async () => {
        const search = vi.fn(async (): Promise<EnricherSearchOutcome> => {
            throw new Error('HTTP 500');
        });
        mount({search});
        await fireEvent.click(suggestion('VWRA'));
        await waitFor(() => expect(root().dataset.status).toBe('error'));
        expect(screen.getByTestId('enrichers-search-failed')).toBeInTheDocument();
    });
});
