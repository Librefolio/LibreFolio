// @vitest-environment jsdom
/**
 * enricherRecognition (plan 68, E8a): the life of «Riconosci» in the asset window — when it starts, what it keeps, what
 * it proposes.
 *
 * Pinned (PROF, rounds 18, 21 and 28):
 * - it starts only with a strong identifier (an ISIN) in the form; the same type, identifiers and price provider never
 *   ask twice; a change asks again and drops the answers of the previous question, late ones too;
 * - every answer is kept by code, as it arrives (the enrichers' window shows them); the codes still being asked are
 *   the ones the window lists as «searching»;
 * - the proposal is the `default_order` of `done`, the found ones only, each bound to the identifier it was found by;
 * - a 429 is a state (`refused`, with its wait), an error a state too; `cancel` (Crea Asset, the window closing) drops
 *   the answers still in flight.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const stream = vi.hoisted(() => ({recognizeEnrichers: vi.fn()}));
vi.mock('./recognizeStream', () => stream);

import {createEnricherRecognitionState, type RecognitionInput} from './enricherRecognition.svelte';
import type {RecognizeEvent, RecognizeOutcome, RecognizeRequest} from './recognizeStream';

type Call = {request: RecognizeRequest; onEvent: (event: RecognizeEvent) => void; signal: AbortSignal; finish: (outcome: RecognizeOutcome) => void};
let calls: Call[] = [];

beforeEach(() => {
    calls = [];
    stream.recognizeEnrichers.mockReset().mockImplementation((request: RecognizeRequest, options: {onEvent: (event: RecognizeEvent) => void; signal: AbortSignal}) => {
        return new Promise<RecognizeOutcome>((finish) => calls.push({request, onEvent: options.onEvent, signal: options.signal, finish}));
    });
});
afterEach(() => vi.clearAllMocks());

const ETF: RecognitionInput = {assetType: 'ETF', identifiers: {ISIN: 'IE00BK5BQT80', TICKER: 'VWCE'}, priceProviderCode: 'justetf'};
const found = (code: string, identifier_type = 'ISIN', identifier = 'IE00BK5BQT80') => ({event: 'enricher_result' as const, code, identifier_type, identifier, status: 'found', name: `${code} name`, page_url: null, identifiers: {}, conflicts: {}, error: null});
const done = (default_order: string[], found_order = default_order) => ({event: 'done' as const, found_order, default_order, identifiers: {ISIN: 'IE00BK5BQT80'}});
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe('when «Riconosci» starts', () => {
    it('starts with an ISIN, asking with every identifier known and the price provider', () => {
        const state = createEnricherRecognitionState();
        expect(state.start(ETF)).toBe(true);
        expect(calls).toHaveLength(1);
        expect(calls[0].request).toEqual({asset_type: 'ETF', identifiers: {ISIN: 'IE00BK5BQT80', TICKER: 'VWCE'}, price_provider_code: 'justetf', seeds: []});
        expect(state.status).toBe('running');
    });

    it('does not start without a strong identifier', () => {
        const state = createEnricherRecognitionState();
        expect(state.start({assetType: 'STOCK', identifiers: {TICKER: 'AAPL'}, priceProviderCode: 'yfinance'})).toBe(false);
        expect(calls).toHaveLength(0);
        expect(state.status).toBe('idle');
    });

    it('waits for a whole ISIN: one being typed asks nothing (each question counts on the per-user limit)', () => {
        const state = createEnricherRecognitionState();
        for (const typed of ['I', 'IE00', 'IE00BK5BQT8', 'ie00bk5bqt80 ']) expect(state.start({...ETF, identifiers: {ISIN: typed}})).toBe(false);
        expect(calls).toHaveLength(0);
        expect(state.start({...ETF, identifiers: {ISIN: 'IE00BK5BQT80'}})).toBe(true);
    });

    it('never asks the same question twice, and asks again when it changes, dropping the old answers', async () => {
        const state = createEnricherRecognitionState();
        state.start(ETF);
        expect(state.start({...ETF, identifiers: {TICKER: 'VWCE', ISIN: 'IE00BK5BQT80'}})).toBe(false);
        expect(calls).toHaveLength(1);

        state.start({...ETF, assetType: 'STOCK'});
        expect(calls).toHaveLength(2);
        expect(calls[0].signal.aborted).toBe(true);
        calls[0].onEvent(found('justetf'));
        calls[0].finish({kind: 'done', done: done(['justetf'])});
        await flush();
        expect(state.recognitions).toEqual({});
        expect(state.status).toBe('running');
    });
});

describe('what it keeps and proposes', () => {
    it('keeps every answer by code as it arrives, and proposes the default order of the found ones', async () => {
        const state = createEnricherRecognitionState();
        state.start(ETF);
        calls[0].onEvent(found('yahoo_finance', 'TICKER', 'VWCE.DE'));
        expect(Object.keys(state.recognitions)).toEqual(['yahoo_finance']);
        calls[0].onEvent({...found('borsa_italiana'), status: 'not_found'});
        calls[0].onEvent(found('justetf'));
        calls[0].onEvent(done(['justetf', 'yahoo_finance', 'mockenrich'], ['yahoo_finance', 'justetf']));
        calls[0].finish({kind: 'done', done: done(['justetf', 'yahoo_finance', 'mockenrich'], ['yahoo_finance', 'justetf'])});
        await flush();
        expect(state.status).toBe('done');
        // A ticker alone does not enter by itself (ENR-1, R2): it may be another listing, the user reads its name first
        expect(state.proposal).toEqual({justetf: {identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'}});
        expect(state.recognitions.yahoo_finance.status, 'the answer itself is still kept, for «Non in elenco»').toBe('found');
    });

    it('proposes in the default order, by ISIN or LEI, never one found by a ticker', async () => {
        const state = createEnricherRecognitionState();
        state.start(ETF);
        calls[0].onEvent(found('yahoo_finance', 'TICKER', 'VWCE.DE'));
        calls[0].onEvent(found('gleif', 'LEI', 'EEXSPYGY7X8YAH8ZJF49'));
        calls[0].onEvent(found('justetf'));
        calls[0].onEvent(done(['justetf', 'yahoo_finance', 'gleif']));
        calls[0].finish({kind: 'done', done: done(['justetf', 'yahoo_finance', 'gleif'])});
        await flush();
        expect(Object.keys(state.proposal)).toEqual(['justetf', 'gleif']);
    });

    it('waits out a refusal for too many requests and asks again by itself, with no action of the user (PROF, E8c)', async () => {
        vi.useFakeTimers();
        try {
            const state = createEnricherRecognitionState();
            state.start(ETF);
            calls[0].finish({kind: 'refused', retryAfter: 12});
            await vi.advanceTimersByTimeAsync(0);
            expect(state.status).toBe('refused');
            expect(state.retryAfter).toBe(12);
            await vi.advanceTimersByTimeAsync(11_000);
            expect(calls).toHaveLength(1);
            await vi.advanceTimersByTimeAsync(1_000);
            expect(calls, 'the same question is asked again once the wait is over').toHaveLength(2);
            expect(calls[1].request).toEqual(calls[0].request);
            expect(state.status).toBe('running');
            calls[1].onEvent(found('justetf'));
            calls[1].finish({kind: 'done', done: done(['justetf'])});
            await vi.advanceTimersByTimeAsync(0);
            expect(state.status).toBe('done');
            expect(Object.keys(state.proposal)).toEqual(['justetf']);
        } finally {
            vi.useRealTimers();
        }
    });

    it('waits a minute when the refusal names no wait, and asks nothing more once cancelled', async () => {
        vi.useFakeTimers();
        try {
            const state = createEnricherRecognitionState();
            state.start(ETF);
            calls[0].finish({kind: 'refused', retryAfter: null});
            await vi.advanceTimersByTimeAsync(59_000);
            expect(calls).toHaveLength(1);
            state.cancel();
            await vi.advanceTimersByTimeAsync(5_000);
            expect(calls, 'a cancelled wait never asks again').toHaveLength(1);
        } finally {
            vi.useRealTimers();
        }
    });

    it('turns a failure into an error state, never a throw', async () => {
        stream.recognizeEnrichers.mockReset().mockRejectedValue(new Error('network'));
        const state = createEnricherRecognitionState();
        state.start(ETF);
        await flush();
        expect(state.status).toBe('error');
    });

    it('drops the answers still in flight when cancelled', async () => {
        const state = createEnricherRecognitionState();
        state.start(ETF);
        state.cancel();
        expect(calls[0].signal.aborted).toBe(true);
        calls[0].onEvent(found('justetf'));
        calls[0].finish({kind: 'done', done: done(['justetf'])});
        await flush();
        expect(state.recognitions).toEqual({});
        expect(state.status).toBe('idle');
    });
});

describe('an asset that exists asks with what its enrichers accept (ENR-1, R1)', () => {
    const TICKER_ONLY = {assetType: 'STOCK', identifiers: {TICKER: 'AAPL'}, priceProviderCode: null, acceptedTypes: ['TICKER']};

    it('asks without a whole ISIN: any identifier of an accepted type is enough, the whole set sent', () => {
        const state = createEnricherRecognitionState();
        expect(state.canRecognize(TICKER_ONLY)).toBe(true);
        expect(state.start(TICKER_ONLY)).toBe(true);
        expect(calls).toHaveLength(1);
        expect(calls[0].request).toEqual({asset_type: 'STOCK', identifiers: {TICKER: 'AAPL'}, price_provider_code: null, seeds: []});
    });

    it('a half-typed ISIN is enough when ISIN is accepted (the fields are not being typed)', () => {
        const state = createEnricherRecognitionState();
        expect(state.start({...ETF, identifiers: {ISIN: 'IE00'}, acceptedTypes: ['ISIN']})).toBe(true);
    });

    it('asks once per question: the same input started twice asks once', () => {
        const state = createEnricherRecognitionState();
        expect(state.start(TICKER_ONLY)).toBe(true);
        expect(state.start({...TICKER_ONLY})).toBe(false);
        expect(calls).toHaveLength(1);
    });

    it('no identifier of an accepted type: no question, state stays idle', () => {
        const state = createEnricherRecognitionState();
        const input = {...ETF, identifiers: {ISIN: 'IE00BK5BQT80'}, acceptedTypes: ['TICKER', 'LEI']};
        expect(state.canRecognize(input)).toBe(false);
        expect(state.start(input)).toBe(false);
        expect(calls).toHaveLength(0);
        expect(state.status).toBe('idle');
    });

    it('a blank identifier of an accepted type is not one; nor an empty list of accepted types, nor an asset with no type', () => {
        const state = createEnricherRecognitionState();
        expect(state.canRecognize({...TICKER_ONLY, identifiers: {TICKER: '  '}})).toBe(false);
        expect(state.canRecognize({...TICKER_ONLY, acceptedTypes: []})).toBe(false);
        expect(state.canRecognize({...TICKER_ONLY, assetType: ''})).toBe(false);
    });

    it('at creation (no accepted types) a whole ISIN is still needed', () => {
        const state = createEnricherRecognitionState();
        expect(state.canRecognize({assetType: 'STOCK', identifiers: {TICKER: 'AAPL'}, priceProviderCode: null})).toBe(false);
        expect(state.canRecognize(ETF)).toBe(true);
    });
});

describe('the price assignment as a seed (ENR-2)', () => {
    const SEED = {code: 'yfinance', identifier_type: 'TICKER', identifier: 'SWDA.MI', params: {mic: 'XMIL'}};
    const STOCK = {assetType: 'ETF', identifiers: {TICKER: 'SWDA'}, priceProviderCode: 'yfinance', acceptedTypes: ['TICKER', 'ISIN']};

    it('the request carries the seed, trimmed, its params copied', () => {
        const state = createEnricherRecognitionState();
        const params = {mic: 'XMIL'};
        expect(state.start({...ETF, seed: {...SEED, identifier: '  SWDA.MI ', params}})).toBe(true);
        expect(calls[0].request.seeds).toEqual([SEED]);
        expect(calls[0].request.seeds?.[0].params, 'a copy, not the form object').not.toBe(params);
    });

    it('no seed, or a blank one, sends an empty list', () => {
        const state = createEnricherRecognitionState();
        state.start({...ETF, seed: null});
        state.start({...ETF, seed: {...SEED, identifier: '  '}});
        expect(calls).toHaveLength(1);
        expect(calls[0].request.seeds).toEqual([]);
    });

    it('a different seed is a new question; the same seed is not', () => {
        const state = createEnricherRecognitionState();
        expect(state.start({...ETF, seed: SEED})).toBe(true);
        expect(state.start({...ETF, seed: {...SEED}})).toBe(false);
        expect(state.start({...ETF, seed: {...SEED, identifier: 'SWDA.L'}})).toBe(true);
        expect(state.start({...ETF, seed: null})).toBe(true);
        expect(calls).toHaveLength(3);
        expect(calls[0].signal.aborted).toBe(true);
    });

    it('an asset that exists asks with a seed alone when its type is accepted', () => {
        const state = createEnricherRecognitionState();
        const alone = {assetType: 'ETF', identifiers: {}, priceProviderCode: 'yfinance', acceptedTypes: ['TICKER'], seed: SEED};
        expect(state.canRecognize(alone)).toBe(true);
        expect(state.canRecognize({...alone, seed: {...SEED, identifier_type: 'ISIN'}}), 'a type no enricher accepts').toBe(false);
        expect(state.start(alone)).toBe(true);
        expect(calls[0].request).toEqual({asset_type: 'ETF', identifiers: {}, price_provider_code: 'yfinance', seeds: [SEED]});
    });

    it('at creation a seed without a whole ISIN asks nothing', () => {
        const state = createEnricherRecognitionState();
        expect(state.canRecognize({assetType: 'ETF', identifiers: {}, priceProviderCode: 'yfinance', seed: SEED})).toBe(false);
        expect(state.start({assetType: 'ETF', identifiers: {ISIN: 'IE00'}, priceProviderCode: 'yfinance', seed: SEED})).toBe(false);
        expect(calls).toHaveLength(0);
        expect(state.start({...ETF, seed: SEED})).toBe(true);
    });

    it("trustedTickers is the seed's identifier when TICKER, nothing otherwise or before asking", () => {
        const state = createEnricherRecognitionState();
        expect(state.trustedTickers).toEqual([]);
        state.start({...STOCK, seed: SEED});
        expect(state.trustedTickers).toEqual(['SWDA.MI']);
        state.start({...STOCK, seed: {...SEED, identifier_type: 'ISIN', identifier: 'IE00BK5BQT80'}});
        expect(state.trustedTickers).toEqual([]);
        state.cancel();
        expect(state.trustedTickers).toEqual([]);
    });

    it("a ticker found by the seed's symbol enters the proposal; one found by another ticker does not", async () => {
        const state = createEnricherRecognitionState();
        state.start({...STOCK, seed: SEED});
        calls[0].onEvent(found('yfinance', 'TICKER', 'SWDA.MI'));
        calls[0].onEvent(found('borsa_italiana', 'TICKER', 'SWDA'));
        calls[0].onEvent(found('justetf'));
        calls[0].finish({kind: 'done', done: done(['yfinance', 'borsa_italiana', 'justetf'])});
        await flush();
        expect(Object.keys(state.proposal)).toEqual(['yfinance', 'justetf']);
        expect(state.proposal.yfinance).toEqual({identifier_type: 'TICKER', identifier: 'SWDA.MI'});
    });

    it('without a seed the same ticker answer does not enter', async () => {
        const state = createEnricherRecognitionState();
        state.start(ETF);
        calls[0].onEvent(found('yfinance', 'TICKER', 'SWDA.MI'));
        calls[0].finish({kind: 'done', done: done(['yfinance'])});
        await flush();
        expect(state.proposal).toEqual({});
    });

    it('the proposal binding keeps the params of the answer', async () => {
        const state = createEnricherRecognitionState();
        state.start({...STOCK, seed: SEED});
        calls[0].onEvent({...found('yfinance', 'TICKER', 'SWDA.MI'), params: {mic: 'XMIL'}});
        calls[0].finish({kind: 'done', done: done(['yfinance'])});
        await flush();
        expect(state.proposal).toEqual({yfinance: {mic: 'XMIL', identifier_type: 'TICKER', identifier: 'SWDA.MI'}});
    });
});
